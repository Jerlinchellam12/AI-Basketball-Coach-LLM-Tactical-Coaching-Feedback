"""Checkpointed batch runner: generates LLM feedback for all four
representations of a set of clips, saving each (clip, representation)
result to disk as soon as it completes.

Safe to re-run: any checkpoint file that already contains a successful
result is skipped, so a partial failure (rate limit, network blip) only
costs the calls that hadn't completed yet, not the whole batch.

Usage: python batch_generate.py [clip_id ...]
       (defaults to DEFAULT_CLIPS if none given)
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import representations as R
from llm_feedback import (
    RepresentationResult,
    format_data_block,
    build_prompt,
    call_gemma,
    parse_feedback,
    check_move_type_match,
    get_outcome_context,
    _assert_prompts_share_identical_instructions,
    _assert_move_type_not_in_data,
    _require_move_description,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
FRONTEND_DATA_DIR = OUTPUT_DIR / "frontend_data"

REPR_NAMES = ["raw_2d", "raw_3d", "json_summary", "nl_description"]

# Final 6-clip working set (narrowed from the original 10; see
# evaluation/comparison_notes.md for exclusion reasons). Covers all 5
# move_type terms (crossover x2, dribble, stepback, between-the-legs,
# spin_move) and includes a shot_made example, better coverage than the
# earlier 4-clip test batch on both axes.
DEFAULT_CLIPS = ["clip_033", "clip_038", "clip_051", "clip_062", "clip_084", "clip_093"]

# Small pause between calls, on top of the retry-aware backoff already in
# call_gemma, to reduce how often we hit the 16k-tokens/minute ceiling in
# the first place rather than relying purely on reactive retries.
PACING_SEC = 3.0


def checkpoint_path(clip_id: str, representation: str) -> Path:
    return CHECKPOINT_DIR / f"{clip_id}__{representation}.json"


def load_checkpoint(clip_id: str, representation: str) -> dict | None:
    path = checkpoint_path(clip_id, representation)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if not data.get("error") else None  # only trust successful checkpoints


def save_checkpoint(clip_id: str, representation: str, result: RepresentationResult) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path(clip_id, representation), "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2)


def run_clip(clip_id: str) -> dict[str, dict]:
    form_row = R.get_form_row(clip_id)
    moment = R.load_moment(clip_id, form_row)
    reprs = R.build_all_representations(clip_id, form_row)
    outcome_context = get_outcome_context(form_row)
    actual_move_type = str(form_row["move_type"])
    actual_move_description = _require_move_description(form_row)

    prompts = {
        name: build_prompt(moment.attacker_id, moment.defender_id, outcome_context, format_data_block(name, payload))
        for name, payload in reprs.items()
    }
    _assert_prompts_share_identical_instructions(prompts)
    _assert_move_type_not_in_data(prompts, actual_move_type, actual_move_description)

    results = {}
    for name in REPR_NAMES:
        cached = load_checkpoint(clip_id, name)
        if cached:
            print(f"  [{clip_id}] {name}: cached, skipping")
            results[name] = cached
            continue

        print(f"  [{clip_id}] {name}: calling Gemma...")
        prompt = prompts[name]
        try:
            raw = call_gemma(prompt)
            parsed = parse_feedback(raw)
            kw_match = check_move_type_match(parsed["identified_move"], actual_move_type)
            result = RepresentationResult(
                name, prompt, raw, parsed, None,
                actual_move_type, actual_move_description, kw_match,
            )
            print(f"  [{clip_id}] {name}: OK (identified='{parsed['identified_move']}', keyword={kw_match} - manual review still needed)")
        except Exception as e:
            result = RepresentationResult(
                name, prompt, "", None, f"{type(e).__name__}: {e}",
                actual_move_type, actual_move_description, None,
            )
            print(f"  [{clip_id}] {name}: FAILED - {result.error}")

        save_checkpoint(clip_id, name, result)
        results[name] = asdict(result)
        time.sleep(PACING_SEC)

    return results


def build_frontend_data(clip_id: str, results: dict[str, dict]) -> dict | None:
    if any(r.get("error") for r in results.values()):
        print(f"  [{clip_id}] incomplete - not writing frontend_data (has errors)")
        return None

    form_row = R.get_form_row(clip_id)
    moment = R.load_moment(clip_id, form_row)
    reprs = R.build_all_representations(clip_id, form_row)

    data = {
        "clip_id": clip_id,
        "video_src": f"videos/{clip_id}.mp4",
        "overlay_2d_src": f"overlays/{clip_id}_overlay_2d.mp4",
        "overlay_3d_src": f"overlays/{clip_id}_overlay_3d.mp4",
        "attacker_id": moment.attacker_id,
        "defender_id": moment.defender_id,
        "attacker_label": f"Player {moment.attacker_id}",
        "defender_label": f"Player {moment.defender_id}",
        "moment_start_sec": round(moment.moment_start_sec, 3),
        "moment_end_sec": round(moment.moment_end_sec, 3),
        "outcome": str(form_row["what happened"]),
        "contested": str(form_row["was it contested"]),
        "shot_location": str(form_row["where the shot was taken from"]),
        "actual_move_type": str(form_row["move_type"]),
        "actual_move_description": _require_move_description(form_row),
        "representations": {
            "raw_2d": {"preview": _raw_preview(reprs["raw_2d"]), "frame_count": len(next(iter(reprs["raw_2d"]["players"].values())))},
            "raw_3d": {"preview": _raw_preview(reprs["raw_3d"]), "frame_count": len(next(iter(reprs["raw_3d"]["players"].values())))},
            "json_summary": reprs["json_summary"],
            "nl_description": reprs["nl_description"],
        },
        "feedback": {
            name: {
                "identified_move": r["parsed"]["identified_move"],
                "positive_observation": r["parsed"]["positive_observation"],
                "alternative_moves": r["parsed"]["alternative_moves"],
                # Provisional until a manual review pass sets
                # move_type_match_manual (see comparison_notes.md for the
                # review methodology) - defaults to the cheap keyword
                # check so the field isn't just blank, but this is NOT
                # the authoritative accuracy signal. An LLM-judge second
                # call was tried and retired (disagreed with careful
                # manual reading on real cases without being more
                # reliable) - removed from the pipeline, not just hidden.
                "move_type_match": r["move_type_match_keyword"],
                "move_type_match_keyword": r["move_type_match_keyword"],
                "move_type_match_manual": r.get("move_type_match_manual"),
                "move_type_match_manual_reason": r.get("move_type_match_manual_reason"),
            }
            for name, r in results.items()
        },
    }

    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FRONTEND_DATA_DIR / f"{clip_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  [{clip_id}] frontend_data written")
    return data


def _raw_preview(raw_repr: dict, n_frames: int = 3) -> dict:
    """First/last few frames only - the full raw payload (dozens of frames
    x 32 joints) isn't meant to be dumped wholesale into the UI, just shown
    as a representative sample of how verbose this representation is."""
    preview = {"joint_order": raw_repr["joint_order"], "value_order_per_joint": raw_repr["value_order_per_joint"], "players": {}}
    for label, frames in raw_repr["players"].items():
        preview["players"][label] = frames[:n_frames] + (["..."] if len(frames) > n_frames else [])
    return preview


def build_manifest(clip_ids: list[str]) -> None:
    available = [c for c in clip_ids if (FRONTEND_DATA_DIR / f"{c}.json").exists()]
    with open(FRONTEND_DATA_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump({"clips": available}, f, indent=2)
    print(f"manifest.json: {available}")


if __name__ == "__main__":
    clips = sys.argv[1:] or DEFAULT_CLIPS
    print(f"Running batch for: {clips}")
    for clip_id in clips:
        print(f"=== {clip_id} ===")
        results = run_clip(clip_id)
        build_frontend_data(clip_id, results)
    build_manifest(clips)
