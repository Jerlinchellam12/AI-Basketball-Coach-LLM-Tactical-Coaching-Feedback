# AI Basketball Coach — LLM Input Representation Comparison for Personalised Tactical Coaching Feedback

## Project Overview
This system generates
personalised, tactical basketball coaching feedback from pose-tracking data
of 1-vs-1 basketball clips, using an LLM. The core research contribution is
a **controlled comparison of how different input data representations
affect the quality of LLM-generated coaching feedback**, validated against
real basketball coach feedback on the same clips.

**Deadline: prototype + dissertation submission in approximately 2 weeks
from Aug 8, 2026.** Every scope decision below is made with this constraint
in mind — see "Priority Roadmap."

**This is a pivot from an earlier, more ambitious direction** (building a
full custom computer vision pipeline from scratch — player tracking, ball
tracking, pose estimation, event detection). That work is real, validated,
and documented, but lives in a separate folder (`AI_Basketball_Coach/`,
kept untouched) as background/exploratory work for the dissertation's
methodology and discussion sections — **not** part of this submission
repo's codebase. See "Relationship to Prior CV Pipeline Work" below.

## Research Question
> How does the input data representation (raw 2D pose, raw 3D pose, a
> structured JSON feature summary, vs. a natural-language description of
> that same pose data) affect the quality, accuracy, and personalisation
> of LLM-generated basketball coaching feedback — and how does that
> feedback compare to a human coach's assessment of the same moments?

This directly addresses the original project's core gap: existing
basketball AI tools mostly analyse individual skills (e.g. shooting form)
in isolation, not tactical attacker-defender interaction. The
representation-comparison design turns that gap into a testable,
examinable research question rather than only an engineering build.

## Origin & Pivot Rationale
- **Original idea (July 22 meeting, Angel + Diar):** build a full CV
  pipeline (player tracking, ball tracking, event detection) from either
  online 1v1 clips or original recordings, feed structured JSON + a
  reference spreadsheet of common moves to an LLM, generate feedback with
  ~3 alternative move suggestions per mistake, always in beginner-friendly
  language. Not one "correct" answer — multiple possible moves.
- **Supervisor-proposed alternative (July 31 meeting, Danielle + Eyal +
  Diar):** due to time constraints, adapt Diar's existing CV pipeline
  (built for squash/cricket) instead of building one from scratch; record
  original footage; generate multiple data representations (2D, 3D, pose
  skeletons, frame images); evaluate how LLM feedback quality varies by
  representation; validate against a real coach's feedback on the same
  clips.
- **What actually happened:** the CV-pipeline-from-scratch path was
  pursued first and got genuinely far — Stage 1 (player tracking), Stage 2
  (ball detection + gap-filling + contest attribution), and Stage 3 (pose
  estimation with a validated shoulder-orientation-reliability mechanism)
  were all built and empirically validated against real footage. This
  produced real findings (see prior-work summary below) but consumed
  significant time relative to the 3-week window.
- **Final decision:** pivot fully to the July 31 alternative. Diar has
  already run his existing pipeline against 99 collected 1v1 clips and
  delivered pose data + overlay videos for all of them (see "Diar's
  Delivered Outputs" below). This removes the need to build or validate
  any CV pipeline at all — the remaining work is entirely clip selection,
  the LLM comparison, evaluation methodology, and a demo frontend.

## Relationship to Prior CV Pipeline Work
The `AI_Basketball_Coach/` folder (separate from this repo) contains fully
validated, documented work:
- **Stage 1:** YOLO11m + ByteTrack player tracking with identity-lock and
  ID-switch recovery
- **Stage 2:** Basketball-specific YOLOv8 ball detection @1920px +
  short-gap interpolation + long-gap "contested" attribution to nearest
  locked player
- **Stage 3:** YOLO11-pose hip/shoulder orientation extraction, including a
  real investigated-and-solved confound (shoulder-width collapsing to
  near-zero under two distinct mechanisms — duplicate detection on bent
  poses, and small-crop keypoint-precision limits — plus a separate
  arms-raised confound), resulting in an explicit
  `shoulder_orientation_reliable` flag (87.8% reliable for Player A, 64.5%
  for Player B)
- **Stage 4 (partial):** shot-attempt state machine, dribble detection,
  and a genuine robustness-testing exercise across held-out clips that
  surfaced two real generalisation bugs (hardcoded hoop coordinates;
  possession/re-catch detection not transferring to closer camera framing)

**Do not attempt to reuse or integrate this code directly into the new
repo.** It's architecturally a different problem (raw video → custom CV)
from this project's actual scope now (pre-computed pose data → LLM
comparison). Its value is as **documented methodology and discussion
material** — it demonstrates independent technical capability, a rigorous
empirical validation habit (test on real footage, don't trust confidence
scores alone, reject wrong hypotheses when evidence contradicts them), and
a legitimate, defensible reason for the pivot. Reference it in the
dissertation write-up; don't build on top of it in code.

## Diar's Delivered Outputs
Diar ran his existing sports-analysis pipeline (originally built for
squash/cricket — no ball-tracking component, purely player-motion/pose
based) against 99 collected 1v1 clips. Per clip, the output folder
contains:

| File | Contents | Use |
|---|---|---|
| `compare_frame_2d.jpg` / `compare_frame_3d.jpg` | Single still frame with pose overlay | Fast visual triage — screening clips for tracking quality |
| `overlay_2d.mp4` / `overlay_3d.mp4` | Full video with skeleton overlay | Confirms tracking quality throughout; used to identify key moments/timestamps |
| `pose_data.csv` | Per-joint x/y/z (3D) + u/v (2D projection) coordinates, human-readable, organised per player (labeled Player 1 / Player 2 — see "Player identification" below) | **Actual primary data source for named-joint code** (see Key Decisions & Constraints — several named joints don't map 1:1 onto npz's raw keypoint array) |
| `pose_data.npz` | Same joint data, compressed binary, plus raw 70-point/SMPL model output (no name-to-index legend) and per-person `bbox` | Used in code only for `bbox` (drives the occlusion-reliability filter) — not for named joint coordinates |
| `render_timing_2d.json` / `.tmp` | Diar's internal render-timing bookkeeping | Not relevant to this project — ignore |
| `run_summary.json` | Possibly contains detection/tracking-quality stats per clip | **Check contents first** — if it has per-clip quality metrics, useful context, but not a substitute for manual clip selection (see below) |

**Known limitation, per Diar directly:** many clips have occlusion issues
(one player blocking the other), so not all 99 are usable — only clips
where both players stay visible and are well-tracked throughout should be
selected.

**No ball-tracking data exists in any of these outputs.** This is a
structural pipeline limitation (inherited from squash, where there's no
ball-tracking equivalent), not a gap in what Diar sent. Practical
consequence: this project cannot automatically detect shot attempts,
makes/misses, or dribble counts from this data. Key moments (shot
attempts, defensive stops, crossovers, etc.) must be **manually identified
by timestamp**, then pose data for that specific moment is used for
tactical LLM reasoning about *how* the moment unfolded — not for
detecting *whether* a scoring event occurred.

**Player identification:** Diar's pipeline already distinguishes and
labels the two players per clip as **Player 1** and **Player 2**
(numeric `track_id` 1/2 in the pose data, and the literal on-screen
"Player 1"/"Player 2" labels burned into the overlay videos — not the
literal strings "A"/"B" this doc originally assumed; corrected once the
data was actually opened). This labeling should be preserved and used
consistently throughout this project's representations, prompts, and LLM
feedback — the LLM should attribute observations and suggestions to the
correct player using these
same identifiers.

## Clip Selection — Manual, Not Automated
**Clip selection is done manually.** I (Jerlin) watch through the 99
processed clips myself and decide which ones have clean, usable tracking
(both players visible, well-tracked skeletons throughout, no major
occlusion). Claude Code is **not** responsible for choosing or ranking
clips — its role starts once selected clips and their outputs have been
placed in the project folders (see Repository Structure below).

Once a clip is selected:
1. The **original, unprocessed `.mp4`** for that clip goes into
   `original_input/`
2. **All of Diar's processed outputs** for that same clip (overlay videos,
   pose CSV/npz, compare-frame images, run summary) go into `cv_input/`,
   ideally in a per-clip subfolder so outputs stay grouped and unambiguous
   (e.g. `cv_input/clip_014/`)

Claude Code should treat both folders as read-only source data once
populated, and should never be asked to pick which of the 99 clips to
use — only to process whatever has already been placed there.

## System Pipeline / Flow
1. **Screen and select clips (manual, by Jerlin)** — from the 99, select
   4-6 with clean, unoccluded tracking of both players throughout; place
   files into `original_input/` and `cv_input/` as described above
2. **Manually identify key moments** — watch selected clips, log
   timestamp + brief description of what happened (attempted move,
   approximate outcome), and which player (A/B) is the focus of that
   moment — this is what replaces automated event detection
3. **Build four input representations** per flagged moment, from the same
   underlying pose data:
   - Raw 2D pose data (u,v pixel coordinates, per joint, per frame)
   - Raw 3D pose data (x,y,z coordinates, per joint, per frame)
   - Structured JSON feature summary (derived signals: hip position,
     lateral movement direction, similar in spirit to the Stage 3 work
     from the prior CV pipeline, but computed from Diar's pose data)
   - Natural-language description (pose data converted to descriptive
     text before LLM input — this specific technique is directly
     validated by Diar's own squash-analysis paper, which found Gemma
     integration consistently improved expert-rated label quality over
     baseline pipeline output)

   **Important distinction:** CSV vs. npz is a *file storage format*, not
   a representation — both contain identical data. The four representations
   above are the only meaningful comparison axis; do not treat CSV/npz as
   separate arms of the comparison.

4. **Generate LLM feedback** per representation, per flagged moment, using
   Gemma via the Groq API
   - **Critical constraint: the prompt instructions and requested output
     format must be IDENTICAL across all four representations.** Only the
     input data changes. This is what makes the comparison scientifically
     valid — varying the prompt alongside the representation would
     confound the results.
   - **Output structure constraint** (see LLM Strategy and Frontend
     sections below): every feedback response, regardless of
     representation, must follow the same fixed structure — one positive
     observation, followed by exactly three alternative tactical moves —
     and must correctly attribute actions to Player 1 or Player 2 as
     labeled in Diar's pose data.
5. **Collect human coach feedback** on the same clips/moments (via
   `coach_feedback_form.xlsx`), independently of the LLM output
6. **Compare** — coach feedback vs. LLM feedback across all four
   representations. This comparison is the dissertation's primary
   evaluation/results section.
7. **Demo frontend** — web app implementing the full user journey: watch
   yourself → jump to a flagged mistake/moment → understand what happened
   → see AI coaching across representations → compare with expert
   coaching. See "Frontend / Demo Plan" below for full detail.

## LLM Strategy
- **Primary model: Gemma, via Google AI Studio's Gemini API** (aistudio.google.com),
  not Groq. **Update (Aug 11, 2026): Groq discontinued Gemma support
  entirely** — `gemma2-9b-it` was shut down Oct 8, 2025 with no successor
  Gemma model on Groq (their official recommended replacement is
  `llama-3.1-8b-instant`, a different model family). Verified directly
  against Groq's live `/models` list and their deprecations page.
  Google AI Studio serves Gemma directly and for free instead — current
  model IDs are `gemma-4-31b-it` and `gemma-4-26b-a4b-it` (Gemma 3 has
  itself since been superseded by Gemma 4). No numeric free-tier
  RPM/RPD/TPM caps are published for Gemma specifically (it runs at the
  same undocumented limit on free and paid tiers, per Google AI Studio's
  own developer forum); check actual personal quota at
  aistudio.google.com/rate-limit once a key exists. Given this project's
  scale (a few dozen total calls across 4-6 clips × a handful of flagged
  moments × 4 representations), this is expected to be comfortably
  sufficient regardless.
- **This is a deliberate methodological choice, not just a cost-saving
  one:** Diar/Angel's own squash-analysis paper used Gemma specifically
  (an instruction-tuned model) and found it consistently improved
  expert-rated label quality over baseline pipeline output across both
  their tested representation families (location-based probabilistic and
  kinematic pose-based). Using the same model family here creates a
  direct, citable link to that prior work in the dissertation's
  related-work and methodology sections. Since Groq no longer offers any
  Gemma model, Google AI Studio is now the only free path that preserves
  this link — not a fallback/substitute choice anymore, but the primary
  and only viable route to the actual Gemma model family.
- **Claude API is explicitly ruled out on cost grounds** — Anthropic does
  not offer a free API tier (confirmed), only pay-per-token billing
  separate from the Pro subscription. Not used in this project's backend.
- **No local LLM hosting.** Even though Ollama/local inference is free,
  it's deliberately avoided given this project's history of CPU-only,
  low-disk-space environment fragility during the earlier CV pipeline
  work (numpy/opencv conflicts, repeated disk-space firefighting). A
  hosted free API avoids repeating that risk.
- **Groq retained as a possible stretch/secondary-model provider only**
  (see "Secondary/stretch comparison" below) — e.g. `llama-3.1-8b-instant`
  — since Groq access is already set up and working, but it is no longer
  a Gemma source and is not the primary model provider.
- **Fixed prompt, fixed output structure:** one single, carefully engineered
  prompt template is used across all four representations and all
  flagged moments. The prompt must instruct the model to always return:
  1. **One positive observation** — something the player (A or B, as
     relevant) did well in that moment
  2. **Exactly three alternative tactical moves** the player could have
     made instead, written in simple, beginner-friendly language
  This matches the original project's feedback design exactly (never one
  "correct" answer — always a positive note plus a small set of real
  alternatives) and keeps the four-way representation comparison fair,
  since only the input changes, never the requested output shape.
- **Secondary/stretch comparison (only if time allows):** a second
  open-weight model also available for free via Groq (e.g. Llama or
  Mistral) could extend the comparison to 2 models × 4 representations.
  This remains a bonus extension on top of the core 4-representations ×
  1-model comparison, not a parallel core requirement — don't let it
  dilute focus from the primary comparison.

## Frontend / Demo Plan
Web app (not mobile — prioritise buildable-in-time over platform reach).
This is not a results dashboard — it's designed around a specific user
journey: **watch yourself → jump to a flagged mistake/moment → understand
what happened → see AI coaching across representations → compare with
expert coaching.**

**Note on video seeking (updated once `self_label_form.xlsx` was actually
opened):** each clip in `original_input/`/`cv_input/` is already a
standalone trimmed moment (starts at 0 internally) — there is no longer
video to seek within. The form's `start`/`end` columns are raw-footage
provenance only (timestamps in the original long recording before
trimming for Diar), not seek points. Selecting a flagged moment means
selecting *which clip* to play in full, not seeking within a longer
video. Fine-grained sub-clip timing instead comes from
`moment_start_sec`/`moment_end_sec` (0-based within the trimmed clip;
default to the clip's full span `[0, duration_sec]` since all 10
currently-selected clips are single-moment clips — see
`representations.py`/`resolve_moment_window`).

**Core interaction flow:**
1. **Select a clip** — user picks from the 10 curated 1v1 clips (from
   `original_input/`); the clip loads and plays in full
2. **Flagged-moment list** — below/beside the video, each clip's flagged
   moment(s) are listed (currently one per clip) showing the move type
   and the player involved (e.g. "clip_033 — Player 2 crossover, shot
   missed")
3. **Click a moment → video seeks to `moment_start_sec`** — since these
   are short local clips (4-15s), this is a simple `video.currentTime`
   assignment, no streaming/complex seeking infrastructure needed. A
   **"replay this moment" loop button** repeats playback between
   `moment_start_sec` and `moment_end_sec`
4. **Pose visualisation alongside the action** — the skeleton-overlay
   video (`overlay_2d.mp4` / `overlay_3d.mp4`, from `cv_input/`) plays
   alongside the original footage at the same in-clip timestamp, so the
   user can see the detected pose data driving the analysis, not just
   trust it blindly
5. **Four representations, side-by-side** — the interface displays the
   2D / 3D / JSON-summary / natural-language representations for that
   specific flagged moment, each next to its own LLM-generated coaching
   feedback. Representations are built from `[moment_start_sec,
   moment_end_sec]` (plus a small padding window for context), not the
   whole clip, once multi-moment clips exist
6. **Consistent feedback structure across all four** — every one of the
   four feedback outputs was generated from the exact same fixed prompt,
   so each always follows the same shape: one positive observation about
   what the player (correctly identified as Player 1 or Player 2) did
   well, followed by exactly three alternative tactical moves they could
   have made, in plain beginner-friendly language. This consistency is
   what makes the four side-by-side outputs directly, fairly comparable
   at a glance — only the underlying representation differs, never the
   feedback format
7. **Coach comparison** — the human coach's independent feedback for the
   same moment (from `coach_feedback_form.xlsx`) is displayed alongside
   the four LLM outputs, so the user can directly compare AI coaching
   against expert coaching for that exact moment

**In short:** every flagged moment is a self-contained, timestamp-anchored
unit — video seek + pose overlay + four representations + four
identically-structured feedback outputs + coach feedback — so the demo can
walk an examiner through one concrete mistake at a time, start to finish,
rather than presenting disconnected outputs.

**Optional, lowest priority, cut first if time is short:** text-to-speech
audio playback of the feedback text (matches original spec's "optional
audio feedback").

## Repository Structure
AI_Basketball_Coach_Prototype/
├── PROJECT.md
├── README.md
├── original_input/ # original, unprocessed .mp4 clips (manually selected by Jerlin)
│ ├── clip_014.mp4
│ ├── clip_037.mp4
│ └── ...
├── cv_input/ # Diar's processed outputs, per selected clip only
│ ├── clip_014/
│ │ ├── compare_frame_2d.jpg
│ │ ├── compare_frame_3d.jpg
│ │ ├── overlay_2d.mp4
│ │ ├── overlay_3d.mp4
│ │ ├── pose_data.csv
│ │ ├── pose_data.npz
│ │ └── run_summary.json
│ └── ...
├── backend/
│ ├── representations.py # builds 2D / 3D / JSON-summary / NL-text from pose data
│ ├── llm_feedback.py # sends each representation through the identical fixed prompt, via Groq/Gemma
│ └── server.py # API layer connecting frontend to backend
├── frontend/
│ └── (React web app — video player + timestamped timeline + pose overlay + representation/feedback panels)
├── evaluation/
│ ├── self_label_form.xlsx # manually flagged moments + timestamps + player (A/B)
│ ├── coach_feedback_form.xlsx # human coach's independent feedback
│ └── comparison_notes.md # working notes on representation comparison findings
└── docs/
└── architecture.md


## Current Status (as of Aug 12, 2026)
- Clip selection done: 10 clips originally selected, narrowed to a final
  **6-clip working set** (clip_033, clip_038, clip_051, clip_062,
  clip_084, clip_093) after reviewing tracking-quality/vocabulary-
  coverage trade-offs. Full reasoning in `evaluation/comparison_notes.md`.
  Excluded clips (clip_063, clip_066, clip_069, clip_070) archived to
  `excluded_clips/`, not deleted.
- `original_input/`/`cv_input/` populated for the working set;
  `self_label_form.xlsx` filled in for all 6 clips, including
  `moment_start_sec`/`moment_end_sec` (the specific sub-window within
  each trimmed clip where the flagged action happens - the real
  analysis window, not the whole clip) and `move_description` (full
  human-written sentences, the primary ground truth for accuracy
  scoring - `move_type` is now a secondary/coarse multi-term label).
- `backend/representations.py`, `llm_feedback.py`, `batch_generate.py`
  built and working: builds the four representations per moment, sends
  each through one shared prompt (byte-for-byte identical instructions,
  verified programmatically), scores the result against held-out ground
  truth two ways (keyword match + LLM-as-judge semantic match).
- **Full real batch run complete twice**, first restricted to the flagged
  moment window, then (user-caught methodology fix, 2026-08-13) re-run
  from each clip's **full span** after the user clarified
  `moment_start_sec`/`moment_end_sec` are frontend "jump to moment"/loop
  display metadata only, never meant to restrict what pose data the LLM
  sees. 6 clips x 4 representations (24 Gemma calls, 0 errors) each
  round. An LLM-judge second call (Gemma judging itself) was tried in the
  first round, scored 8/24 (33%), then **retired from the active
  pipeline** - `move_type_match` in generated data now reflects the
  authoritative manual/semantic review (`move_type_match_manual`), not
  the raw keyword substring check, to avoid a false-red bug class caught
  and fixed for clip_033 in the first round. Manual evaluation landed at
  11/24 (46%) on the moment-window round, then **12/24 (50%)** on the
  full-clip round - representation scores flattened to 3/6 each (raw_2d,
  raw_3d, json_summary, nl_description all tied) rather than the
  moment-window round's raw_2d-strongest/raw_3d-weakest split.
  `clip_051` and `clip_093` (reversal/deceptive moves: stepback,
  hesitation/spin/fake) stayed fully incorrect in both rounds - pose
  signals alone appear to struggle with these regardless of window size.
  Full per-clip results for both rounds, the judge-retirement rationale,
  and methodology decisions (glossary iteration, ground-truth upgrade,
  ViSTAR related-work context) are all in `evaluation/comparison_notes.md`
  - that file is the primary record of findings, kept up to date as work
  continues.
- API: Google AI Studio key set up and working (`gemma-4-31b-it` - Groq
  dropped Gemma support entirely, see LLM Strategy above). Groq key kept
  only as an unused fallback for a possible secondary-model comparison.
- Frontend: React/Vite app built (light/cream theme with orange accent,
  basketball logo, 3D tilt interactions), reads only static JSON (no
  live API calls when viewing), works offline. Synced with all 6 working-
  set clips, including moment-window-based sampling (`moment_start_sec`/
  `moment_end_sec` define the analysis window, not the whole clip) and a
  single "Jump to moment" control that seeks and loops the flagged
  moment (the earlier separate replay-loop button was removed).
- Coach for expert validation: **still not confirmed** - `coach_feedback_form.xlsx`
  exists but is empty. Not blocking current work; frontend/evaluation
  structure is being kept ready to slot it in additively once available.

## Priority Roadmap (given ~2 weeks remaining)
1. **Set up Groq API access** (free, Gemma model) — blocking, needed
   before any LLM calls can happen
2. **Manually screen and select 4-6 clips (Jerlin, not Claude Code)** —
   place originals in `original_input/` and matching Diar outputs in
   `cv_input/`
3. **Manually flag key moments** on the selected clips, with precise
   timestamps and player (A/B) attribution — these timestamps are the
   anchor for the entire frontend experience, so log them carefully and
   consistently
4. **Build all four representations for ONE moment first** — validate the
   full pipeline (pose data → representation → fixed prompt → LLM →
   structured feedback) works end-to-end on a single example before
   scaling to all flagged moments
5. **In parallel: reach out to arrange a basketball coach for expert
   validation** — this depends on someone else's availability and should
   not be left until the build is finished
6. Scale representation-building and LLM-feedback generation across all
   flagged moments on all selected clips
7. Build the frontend once backend output is proven correct — implement
   the full timestamp-seek → pose overlay → four representations → coach
   comparison flow described above
8. Collect coach feedback, run the comparison, write up findings
9. Stretch, only if time remains: second model comparison; audio feedback

## Key Decisions & Constraints
- **Clip selection is manual, done by Jerlin — Claude Code never chooses
  or ranks clips**, only processes what's already placed in
  `original_input/` and `cv_input/`
- CSV/npz are storage formats, not representations — only 2D, 3D, JSON,
  and natural-language count as the four comparison arms
- **The four representations intentionally use different source frame
  rates, not the clip's native ~60fps uniformly** (confirmed in
  `representations.py`: raw 2D/3D sample at 10fps for prompt-size
  reasons — 651 raw frames/player would be an unrealistic amount to
  actually hand an LLM; JSON summary/NL description compute their
  aggregate stats — total lateral movement, avg inter-player distance,
  etc. — from every reliable frame at native fps, since downsampling
  before aggregating would just make the summary less accurate for no
  benefit, and this is standard practice for building an aggregate
  feature). This was examined deliberately, not an oversight: the
  difference reflects what "raw" vs. "summary" representations actually
  are, not an arbitrary inconsistency. Worth naming explicitly as a
  limitation in the dissertation's methodology/limitations section,
  since it means the four arms don't hold "amount of underlying
  information used" constant — only their answer to "how should this
  representation type be constructed" is held constant.
- Prompt wording and output format must stay identical across all four
  representations — only the input changes
- **LLM feedback output is always structured as: one positive observation
  + exactly three alternative tactical moves**, in beginner-friendly
  language, correctly attributed to Player 1 or Player 2
- LLM is Gemma via Google AI Studio's free API (Groq dropped Gemma
  support entirely, Oct 2025 — see LLM Strategy) — no cost, and directly
  matches the
  model used in Diar/Angel's own related squash-analysis paper
- No local LLM hosting — free hosted API only
- No ball-tracking or automated event detection in this pipeline — key
  moments are identified manually, pose data is used for tactical
  reasoning about a moment, not for detecting whether the moment occurred
- Timestamps from manual flagging are the anchor for both the LLM input
  (which window of pose data to use) and the frontend UX (where the video
  seeks to) — keep timestamp logging precise and consistent across clips
- Web app frontend, not mobile — prioritises finishing over platform reach
- This repo is kept separate and clean for GitLab dissertation submission;
  the prior CV pipeline work stays in its own separate folder and is not
  merged into this codebase
- All work in this new repo happens through VS Code's integrated terminal
  running the `claude` CLI — same tool used throughout the project so far.
  Do not use Claude Code Desktop app for this project; running the same
  project across multiple disconnected tool sessions has caused real
  context-fragmentation problems earlier in this project and should not be
  repeated.

## Open Questions / Not Yet Decided
- Whether the department/GitLab submission process expects a single
  clean repo only, or accepts a main repo plus a linked
  appendix/exploration repo for the prior CV pipeline work — confirm with
  Angel, don't assume
- Exact contents/fields of `run_summary.json` — unconfirmed until opened
- Whether `self_label_form.xlsx` (from the earlier Diar-adjacent dataset
  task) already has a schema usable for manually flagging key moments and
  player attribution, or needs to be built fresh
- Coach identity/availability for expert validation — not yet arranged
- Exact final count of usable clips once Jerlin finishes manual screening
  — Diar flagged that many of the 99 have visibility issues

## Working Principles Carried Forward From Prior Work
- **Validate empirically, not theoretically** — test each new piece
  (representation quality, LLM feedback quality) against real data before
  assuming it works
- **Don't trust confidence/success signals blindly** — the prior work
  found multiple cases (shoulder_conf staying high on degenerate data; a
  script's "make/miss" flip being treated as proof without visual
  verification) where an output looked authoritative but was wrong.
  Verify against ground truth (watch the actual clip) before accepting a
  result, especially for anything going into the dissertation's evaluation
  section
- **When a hypothesis is tested and contradicted by evidence, say so and
  investigate the real cause** rather than defending the original claim —
  this happened twice in the prior pipeline work and both corrections are
  worth documenting explicitly as examples of rigorous methodology
- **One continuous working session per tool, per project folder** — avoid
  the context-fragmentation problems experienced earlier in this project
