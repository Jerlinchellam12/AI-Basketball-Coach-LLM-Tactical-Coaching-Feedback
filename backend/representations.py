"""Builds the four LLM input representations (raw 2D, raw 3D, structured JSON
summary, natural-language description) from Diar's pose data, for one
flagged moment at a time.

Data source note (deviates fro
m PROJECT.md's "always load npz, not CSV"):
named joint coordinates are read from pose_data.csv, not pose_data.npz.
Diar's npz stores raw 70-point/SMPL model output (pred_keypoints_2d/3d,
body_pose_params, etc.) with no name-to-index legend, and several of the
CSV's 32 named joints (pelvis, spine3, the foot/toe points) do not map
1:1 onto that raw array - they're derived by Diar's own export logic.
Reverse-engineering that derivation without his source would be
unverifiable guesswork, so the CSV (his own authoritative named export)
is used for joint coordinates instead. The npz is still used for `bbox`
(not present in the CSV), which drives the occlusion-reliability filter
below.

Player labelling note (deviates from PROJECT.md's "Player A / Player B"):
Diar's overlay video and pose data both label players as "Player 1" /
"Player 2" (track_id 1 / 2), never "A"/"B". Representations here use
"Player {id}" to match exactly what the user sees in the overlay video.

Occlusion note: during full occlusion, Diar's pipeline does not always
leave a frame empty - it can substitute a small fixed-size placeholder
pose under the correct (or a transient negative "-N") track id, which
looks like valid data but isn't. Confirmed by visual cross-check against
overlay_2d.mp4 for clip_084. Detected here via a bbox-height collapse
heuristic (see `compute_reliability_mask`) and excluded from all four
representations.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
CV_INPUT_DIR = ROOT_DIR / "cv_input"
LABEL_FORM_PATH = ROOT_DIR / "evaluation" / "self_label_form.xlsx"

# Fraction of a track's own median clip-wide bbox height below which a frame
# is treated as an occlusion placeholder/unreliable detection, not a real
# position. Derived empirically from clip_084 (real ~340px vs placeholder
# ~170px, i.e. ~50%) - see PROJECT.md-adjacent conversation history.
RELIABILITY_HEIGHT_RATIO = 0.5

# A below-threshold run only counts as an occlusion placeholder if it's
# shorter than this many seconds. The confirmed real case (clip_084) lasted
# ~0.2s; clip_033 has a genuine sustained bbox shrink lasting over a second
# (pelvis_z climbs steadily 3.4m->8.5m - the player driving away from the
# camera toward the basket, not an occlusion artifact) that must NOT be
# excluded. Without this cutoff the filter wrongly drops real end-of-drive
# frames - exactly the part of the moment most likely to matter.
MAX_UNRELIABLE_RUN_SEC = 0.35

# Raw 2D/3D representations are sampled at this rate rather than the source
# 60fps, to keep prompt size reasonable. This is a practical judgment call,
# not a spec requirement - revisit if raw-representation quality looks
# degraded in early comparisons. Lowered twice after measuring actual
# payload sizes against real constraints: 10fps with per-frame joint-name
# keys produced ~180k combined tokens for the longest clip (clip_070) -
# too large to fit a call at all. The flat (name-list-once) encoding below
# plus 5fps got individual calls to ~13-31k tokens - still too large once
# Google AI Studio's actual free-tier limit for gemma-4-31b turned out to
# be 16,000 *input tokens per minute* (revealed by a live 429 error -
# not published in any docs checked earlier). 2fps keeps every clip's
# worst-case single call (clip_070's raw_3d) at ~12.5k tokens, leaving
# headroom under 16k for the fixed prompt instructions + response. Still
# visibly dwarfs the JSON summary (~750 chars) and NL description (~350
# chars), which is the intended contrast between representations.
RAW_REPR_TARGET_FPS = 2.0

DEFAULT_PADDING_SEC = 0.5


def get_joint_names(clip_dir: Path) -> list[str]:
    with open(clip_dir / "pose_data.csv", newline="") as f:
        header = next(csv.reader(f))
    return [c[:-2] for c in header if c.endswith("_x")]


@dataclass
class ClipPoseData:
    clip_id: str
    joint_names: list[str]
    csv_df: pd.DataFrame  # long form: frame, time, id, <joint>_x/y/z/u/v...
    bbox_height: dict[int, dict[int, float]]  # track_id -> frame -> height_px
    reliable: dict[int, dict[int, bool]]  # track_id -> frame -> bool
    clip_duration_sec: float


def load_clip_pose_data(clip_id: str) -> ClipPoseData:
    clip_dir = CV_INPUT_DIR / clip_id
    if not clip_dir.exists():
        raise FileNotFoundError(f"No cv_input folder for {clip_id}: {clip_dir}")

    joint_names = get_joint_names(clip_dir)
    csv_df = pd.read_csv(clip_dir / "pose_data.csv")

    npz = np.load(clip_dir / "pose_data.npz", allow_pickle=True)
    records = npz["records"]

    bbox_height: dict[int, dict[int, float]] = {}
    frame_times: dict[int, float] = {}
    for rec in records:
        frame_times[int(rec["frame_index"])] = float(rec["timestamp_seconds"])
        for p in rec["people"]:
            tid = int(p["track_id"])
            bbox = p["bbox"]
            h = float(bbox[3] - bbox[1])
            bbox_height.setdefault(tid, {})[int(rec["frame_index"])] = h

    reliable = {
        tid: compute_reliability_mask(heights, frame_times)
        for tid, heights in bbox_height.items()
    }

    clip_duration_sec = float(records[-1]["timestamp_seconds"])

    return ClipPoseData(
        clip_id=clip_id,
        joint_names=joint_names,
        csv_df=csv_df,
        bbox_height=bbox_height,
        reliable=reliable,
        clip_duration_sec=clip_duration_sec,
    )


def compute_reliability_mask(
    frame_heights: dict[int, float],
    frame_times: dict[int, float],
    ratio: float = RELIABILITY_HEIGHT_RATIO,
    max_run_sec: float = MAX_UNRELIABLE_RUN_SEC,
) -> dict[int, bool]:
    """Flags frames whose bbox height collapses relative to this track's own
    median height in the clip AND which sit in a short run (< max_run_sec) -
    the signature of a brief occlusion placeholder detection, confirmed
    visually against clip_084's overlay video (see module docstring).

    The run-length check matters: a sustained multi-second bbox shrink (e.g.
    a player driving away from the camera, confirmed via steadily increasing
    pelvis_z in clip_033) looks identical to a placeholder on a single-frame
    basis but is real motion, not an occlusion artifact, and must not be
    excluded.
    """
    if not frame_heights:
        return {}
    median_h = float(np.median(list(frame_heights.values())))
    frames_sorted = sorted(frame_heights)
    below = {f: frame_heights[f] < ratio * median_h for f in frames_sorted}

    reliable = {f: True for f in frames_sorted}
    run: list[int] = []

    def flush(run_frames: list[int]) -> None:
        if not run_frames:
            return
        run_duration = frame_times[run_frames[-1]] - frame_times[run_frames[0]]
        if run_duration <= max_run_sec:
            for f in run_frames:
                reliable[f] = False

    for f in frames_sorted:
        if below[f]:
            run.append(f)
        else:
            flush(run)
            run = []
    flush(run)

    return reliable


def _parse_moment_time(value) -> float | None:
    """moment_start_sec/moment_end_sec are entered in the form as
    "HH:MM:SS" strings (e.g. "00:00:08"), not plain numeric seconds -
    Excel/openpyxl round-trips them as such. Returns None for blank
    cells, otherwise total seconds as a float. Also accepts a plain
    number (int/float or a numeric string) for robustness, in case the
    form's cell formatting changes later.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        parts = [float(p) for p in text.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)  # pad "MM:SS" -> "00:MM:SS"
        h, m, s = parts[-3:]
        return h * 3600 + m * 60 + s
    return float(text)


def resolve_moment_window(
    form_row: pd.Series, clip_duration_sec: float, padding_sec: float = DEFAULT_PADDING_SEC
) -> tuple[float, float]:
    """Returns (start_sec, end_sec) in the clip's own 0-based timeline, with
    padding applied and clipped to the clip's actual bounds.

    moment_start_sec/moment_end_sec mark the specific sub-window the user
    flags for the frontend's "jump to moment"/loop feature - display
    metadata only. They are NOT used to restrict what pose data gets sent
    to the LLM (see `load_moment`, which always analyses the clip's full
    span); the user was explicit that trimming to this window undercounted
    real movement (e.g. a drive that continues past moment_end_sec).
    """
    duration_sec = float(form_row["duration_sec"])
    if abs(duration_sec - clip_duration_sec) > 0.5:
        print(
            f"WARNING [{form_row['clip_id']}]: form duration_sec={duration_sec} "
            f"differs from pose data's actual duration={clip_duration_sec:.2f}s by >0.5s"
        )

    start_sec = _parse_moment_time(form_row.get("moment_start_sec"))
    end_sec = _parse_moment_time(form_row.get("moment_end_sec"))
    start_sec = 0.0 if start_sec is None else start_sec
    end_sec = duration_sec if end_sec is None else end_sec

    start_sec = max(0.0, start_sec - padding_sec)
    end_sec = min(clip_duration_sec, end_sec + padding_sec)
    return start_sec, end_sec


def load_label_form() -> pd.DataFrame:
    df = pd.read_excel(LABEL_FORM_PATH)
    missing = df[df["attacker_id"].isna() | df["defender_id"].isna()]
    if not missing.empty:
        raise ValueError(
            f"attacker_id/defender_id missing for rows: {missing['clip_id'].tolist()}"
        )
    return df


def get_form_row(clip_id: str, form: pd.DataFrame | None = None) -> pd.Series:
    form = form if form is not None else load_label_form()
    rows = form[form["clip_id"] == clip_id]
    if len(rows) == 0:
        raise ValueError(f"No row for {clip_id} in {LABEL_FORM_PATH}")
    if len(rows) > 1:
        raise ValueError(
            f"{len(rows)} rows for {clip_id} - multi-moment clips need a specific "
            f"row selected explicitly, not the whole-clip default path"
        )
    return rows.iloc[0]


@dataclass
class Moment:
    clip_id: str
    attacker_id: int
    defender_id: int
    start_sec: float  # analysis window for representations - full clip span
    end_sec: float
    moment_start_sec: float  # flagged sub-window - frontend display/loop only
    moment_end_sec: float
    pose: ClipPoseData
    frame_rows: pd.DataFrame  # csv_df rows within [start_sec, end_sec]


def load_moment(clip_id: str, form_row: pd.Series | None = None) -> Moment:
    """The analysis window (start_sec/end_sec, used to build every
    representation) is always the clip's full span [0, duration] - the
    user was explicit that moment_start_sec/moment_end_sec are frontend
    display metadata only, not a restriction on what pose data the LLM
    sees. The flagged moment_start_sec/moment_end_sec are still resolved
    separately and carried on the Moment for the frontend's jump-to-moment
    feature, unaffected by this."""
    form_row = form_row if form_row is not None else get_form_row(clip_id)
    pose = load_clip_pose_data(clip_id)
    start_sec, end_sec = 0.0, pose.clip_duration_sec
    moment_start_sec, moment_end_sec = resolve_moment_window(form_row, pose.clip_duration_sec)

    df = pose.csv_df
    frame_rows = df[(df["time"] >= start_sec) & (df["time"] <= end_sec)]

    return Moment(
        clip_id=clip_id,
        attacker_id=int(form_row["attacker_id"]),
        defender_id=int(form_row["defender_id"]),
        start_sec=start_sec,
        end_sec=end_sec,
        moment_start_sec=moment_start_sec,
        moment_end_sec=moment_end_sec,
        pose=pose,
        frame_rows=frame_rows,
    )


def _sampled_frames(moment: Moment, track_id: int) -> pd.DataFrame:
    """Reliable frames for one track within the moment window, downsampled
    to RAW_REPR_TARGET_FPS for the raw 2D/3D representations."""
    rows = moment.frame_rows[moment.frame_rows["id"] == track_id].sort_values("time")
    reliable = moment.pose.reliable.get(track_id, {})
    rows = rows[rows["frame"].map(lambda f: reliable.get(int(f), False))]
    if rows.empty:
        return rows

    step = 1.0 / RAW_REPR_TARGET_FPS
    keep_idx = []
    next_t = rows["time"].iloc[0]
    for idx, t in zip(rows.index, rows["time"]):
        if t >= next_t:
            keep_idx.append(idx)
            next_t = t + step
    return rows.loc[keep_idx]


def _player_label(track_id: int, moment: Moment) -> str:
    role = (
        "attacker" if track_id == moment.attacker_id
        else "defender" if track_id == moment.defender_id
        else "unknown"
    )
    return f"Player {track_id} ({role})"


def _build_raw(moment: Moment, axes: list[str], decimals: int) -> dict:
    """Shared builder for raw 2D (axes=['u','v']) and raw 3D (axes=['x','y','z']).

    Joint names are declared once in `joint_order`; each frame is a flat
    array in that fixed order (joint0_axis0, joint0_axis1, ..., joint1_axis0,
    ...) rather than repeating joint names as a dict key on every frame -
    the per-frame-key form measured ~2x larger for no benefit (see
    RAW_REPR_TARGET_FPS comment for the full sizing story).
    """
    joints = moment.pose.joint_names
    out = {
        "clip_id": moment.clip_id,
        "window_sec": [round(moment.start_sec, 3), round(moment.end_sec, 3)],
        "joint_order": joints,
        "value_order_per_joint": axes,
        "players": {},
    }
    cols = [f"{j}_{a}" for j in joints for a in axes]
    for track_id in (moment.attacker_id, moment.defender_id):
        rows = _sampled_frames(moment, track_id)
        out["players"][_player_label(track_id, moment)] = [
            {"t": round(float(row["time"]), 3), "v": [round(float(row[c]), decimals) for c in cols]}
            for _, row in rows.iterrows()
        ]
    return out


def build_raw_2d(moment: Moment) -> dict:
    return _build_raw(moment, axes=["u", "v"], decimals=1)


def build_raw_3d(moment: Moment) -> dict:
    return _build_raw(moment, axes=["x", "y", "z"], decimals=4)


def _full_reliable_frames(moment: Moment, track_id: int) -> pd.DataFrame:
    """Every reliable frame (not downsampled) - used for derived features,
    where we want the true frame-to-frame motion, not a thinned sample."""
    rows = moment.frame_rows[moment.frame_rows["id"] == track_id].sort_values("time")
    reliable = moment.pose.reliable.get(track_id, {})
    return rows[rows["frame"].map(lambda f: reliable.get(int(f), False))]


def build_json_summary(moment: Moment) -> dict:
    attacker_rows = _full_reliable_frames(moment, moment.attacker_id)
    defender_rows = _full_reliable_frames(moment, moment.defender_id)

    def player_signals(rows: pd.DataFrame) -> dict:
        if len(rows) < 2:
            return {"note": "insufficient reliable frames for motion signals"}
        pelvis = rows[["pelvis_x", "pelvis_y", "pelvis_z"]].to_numpy()
        lateral_delta = np.diff(pelvis[:, 0])
        total_lateral_m = float(np.sum(np.abs(lateral_delta)))
        net_lateral_m = float(pelvis[-1, 0] - pelvis[0, 0])
        return {
            "total_lateral_movement_m": round(total_lateral_m, 3),
            "net_lateral_movement_m": round(net_lateral_m, 3),
            "net_lateral_direction": "left_to_right" if net_lateral_m > 0 else "right_to_left" if net_lateral_m < 0 else "none",
            "start_pelvis_xyz": [round(float(v), 3) for v in pelvis[0]],
            "end_pelvis_xyz": [round(float(v), 3) for v in pelvis[-1]],
        }

    distances = []
    merged = pd.merge(
        attacker_rows[["frame", "time", "pelvis_x", "pelvis_y", "pelvis_z"]],
        defender_rows[["frame", "time", "pelvis_x", "pelvis_y", "pelvis_z"]],
        on="frame", suffixes=("_atk", "_def"),
    )
    if not merged.empty:
        d = np.sqrt(
            (merged["pelvis_x_atk"] - merged["pelvis_x_def"]) ** 2
            + (merged["pelvis_y_atk"] - merged["pelvis_y_def"]) ** 2
            + (merged["pelvis_z_atk"] - merged["pelvis_z_def"]) ** 2
        )
        distances = d.tolist()

    total_frames = len(moment.frame_rows["frame"].unique())
    unreliable_atk = total_frames - len(attacker_rows)
    unreliable_def = total_frames - len(defender_rows)

    return {
        "clip_id": moment.clip_id,
        "window_sec": [round(moment.start_sec, 3), round(moment.end_sec, 3)],
        "attacker": {"player_label": _player_label(moment.attacker_id, moment), **player_signals(attacker_rows)},
        "defender": {"player_label": _player_label(moment.defender_id, moment), **player_signals(defender_rows)},
        "distance_between_players_m": {
            "avg": round(float(np.mean(distances)), 3) if distances else None,
            "min": round(float(np.min(distances)), 3) if distances else None,
            "max": round(float(np.max(distances)), 3) if distances else None,
        },
        "data_quality": {
            "total_frames_in_window": total_frames,
            "attacker_unreliable_frames_excluded": unreliable_atk,
            "defender_unreliable_frames_excluded": unreliable_def,
        },
    }


def build_nl_description(summary: dict) -> str:
    """Deterministic template text built from the JSON summary - not an LLM
    call. PROJECT.md's cited squash paper used Gemma to convert pipeline
    output to text; this module stays a pure, reproducible data
    transformation and leaves any LLM-based NL generation as a separate,
    explicit choice for llm_feedback.py if wanted later."""
    atk, dfn = summary["attacker"], summary["defender"]
    dist = summary["distance_between_players_m"]
    dur = summary["window_sec"][1] - summary["window_sec"][0]

    def movement_phrase(sig: dict) -> str:
        if "note" in sig:
            return "not enough reliable tracking data to describe movement"
        direction = sig["net_lateral_direction"].replace("_", " ")
        return (
            f"moved {direction} (net {abs(sig['net_lateral_movement_m']):.2f}m), "
            f"covering {sig['total_lateral_movement_m']:.2f}m of lateral movement in total"
        )

    lines = [
        f"Over this {dur:.1f}-second sequence from {summary['clip_id']}, "
        f"{atk['player_label']} {movement_phrase(atk)}.",
        f"{dfn['player_label']} {movement_phrase(dfn)}.",
    ]
    if dist["avg"] is not None:
        lines.append(
            f"The distance between the two players averaged {dist['avg']:.2f}m "
            f"(ranging from {dist['min']:.2f}m to {dist['max']:.2f}m) over the sequence."
        )
    quality = summary["data_quality"]
    if quality["attacker_unreliable_frames_excluded"] or quality["defender_unreliable_frames_excluded"]:
        lines.append(
            f"Note: {quality['attacker_unreliable_frames_excluded']} attacker frame(s) and "
            f"{quality['defender_unreliable_frames_excluded']} defender frame(s) were excluded "
            f"from this window due to occlusion."
        )
    return " ".join(lines)


def build_all_representations(clip_id: str, form_row: pd.Series | None = None) -> dict:
    moment = load_moment(clip_id, form_row)
    summary = build_json_summary(moment)
    return {
        "raw_2d": build_raw_2d(moment),
        "raw_3d": build_raw_3d(moment),
        "json_summary": summary,
        "nl_description": build_nl_description(summary),
    }


if __name__ == "__main__":
    # Validate the full pipeline end-to-end on one moment before scaling,
    # per PROJECT.md's roadmap step 4.
    clip_id = "clip_033"
    reprs = build_all_representations(clip_id)

    print(f"=== {clip_id} ===")
    print(f"raw_2d: {len(reprs['raw_2d']['players'])} players, "
          f"{[len(v) for v in reprs['raw_2d']['players'].values()]} sampled frames each")
    print(f"raw_3d: {len(reprs['raw_3d']['players'])} players, "
          f"{[len(v) for v in reprs['raw_3d']['players'].values()]} sampled frames each")
    print()
    print("json_summary:")
    print(json.dumps(reprs["json_summary"], indent=2))
    print()
    print("nl_description:")
    print(reprs["nl_description"])
