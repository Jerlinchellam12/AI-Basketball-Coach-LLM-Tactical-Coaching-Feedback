# AI Basketball Coach — Representation Comparison for LLM Coaching Feedback

MSc Computer Science final project. This system generates personalised,
tactical basketball coaching feedback from pose-tracking data of 1-vs-1
basketball clips, using an LLM (Gemma). Its core research contribution is a
**controlled comparison of how different input data representations affect
the quality of LLM-generated coaching feedback**, validated against real
basketball coach feedback on the same clips.

> **Research question:** How does the input data representation (raw 2D
> pose, raw 3D pose, a structured JSON feature summary, vs. a
> natural-language description of that same pose data) affect the quality,
> accuracy, and personalisation of LLM-generated basketball coaching
> feedback — and how does that feedback compare to a human coach's
> assessment of the same moments?

## How it works

1. Six 1-vs-1 clips were manually selected and pose-tracked (positions
   provided pre-computed by a collaborator's existing sports-analysis
   pipeline — see [Credits](#credits)). One tactical "moment" per clip
   (e.g. a crossover, a stepback) was manually flagged with a timestamp and
   ground-truth description.
2. `backend/representations.py` builds **four different representations**
   of the same underlying pose data for each flagged moment:
   - Raw 2D pose (pixel `u,v` per joint, per frame)
   - Raw 3D pose (`x,y,z` per joint, per frame)
   - A structured JSON feature summary (hip position, lateral movement,
     inter-player distance, etc.)
   - A natural-language description of the same signals
3. `backend/llm_feedback.py` sends each representation through **one
   byte-for-byte identical prompt** (verified at runtime, not just by
   convention) to Gemma via the Google AI Studio API, so only the input
   representation varies — never the instructions or requested output
   shape. Every response is forced into the same structure: one positive
   observation + exactly three alternative tactical moves, attributed to
   the correct player.
4. `backend/batch_generate.py` runs this across all six clips × four
   representations, checkpointing each result so a partial failure never
   costs a full re-run, and exports the results as static JSON for the
   frontend.
5. The React frontend (`frontend/`) lets you pick a clip, jump to its
   flagged moment, watch the pose-overlay video alongside the original
   footage, and see all four representations side-by-side with their
   generated feedback — for direct, at-a-glance comparison.
6. Independent human coach feedback on the same moments
   (`evaluation/coach_feedback_form.xlsx`) is the validation baseline the
   dissertation's comparison is measured against.

Findings, clip-selection rationale, and evaluation methodology are tracked
in detail in [`evaluation/comparison_notes.md`](evaluation/comparison_notes.md);
full project scope, decisions, and constraints are in
[`PROJECT.md`](PROJECT.md).

## Repository structure

```
├── backend/
│   ├── representations.py   # builds the 4 representations from pose data
│   ├── llm_feedback.py      # sends a representation through the shared prompt via Gemma
│   ├── batch_generate.py    # checkpointed batch runner across all clips/representations
│   └── output/              # generated feedback (checkpoints/ + frontend_data/)
├── frontend/                 # React + Vite demo app (reads static JSON, no live API calls)
├── original_input/           # original, unprocessed .mp4 clips
├── cv_input/                 # per-clip pose data (CSV/NPZ) + skeleton-overlay videos
├── evaluation/                # self-labelled moments, coach feedback form, findings notes
└── PROJECT.md                 # full project scope, decisions, and constraints
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- A free [Google AI Studio](https://aistudio.google.com/apikey) API key
  (used to call Gemma) — only needed to *generate* new feedback, not to run
  the frontend demo against already-generated data

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the project root and fill in your key:

```
GOOGLE_API_KEY=your_key_here
```

Generate feedback for the default 6-clip working set:

```bash
python batch_generate.py
```

Or for specific clips:

```bash
python batch_generate.py clip_033 clip_038
```

Results are checkpointed to `backend/output/checkpoints/` and exported for
the frontend to `backend/output/frontend_data/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app reads pre-generated JSON from `frontend/public/data/` and plays
video/overlay files from `frontend/public/videos/` and
`frontend/public/overlays/` — no backend server needs to be running to view
the demo.

## Tech stack

- **Backend:** Python, pandas/numpy (pose data processing), Gemma via the
  Google AI Studio API
- **Frontend:** React + Vite

## Credits

Pose-tracking data (2D/3D joint positions, skeleton-overlay videos) for the
1v1 clips was generated by an existing sports-analysis pipeline built by a
collaborator (originally developed for squash/cricket analysis), adapted
for this project's basketball footage.
