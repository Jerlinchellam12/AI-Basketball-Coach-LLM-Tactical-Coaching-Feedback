# Comparison Notes — working notes on representation-comparison methodology

This file tracks methodology decisions that affect how the four
representations (raw 2D, raw 3D, JSON summary, natural-language
description) and their evaluation should be read — the "why", not just
the "what", so it can go straight into the dissertation's methodology/
limitations sections rather than being reconstructed after the fact.

## Clip set: 10 selected clips narrowed to 6

Original selection: clip_033, clip_038, clip_051, clip_062, clip_063,
clip_066, clip_069, clip_070, clip_084, clip_093.

Final working set: **clip_033, clip_038, clip_051, clip_062, clip_084, clip_093**
(6 clips). Excluded: clip_063, clip_066, clip_069, clip_070. Excluded
clips' files moved to `excluded_clips/` (mirroring `original_input/` /
`cv_input/` structure) rather than deleted.

**Why each was excluded:**
- **clip_066 / clip_069** — both have a real end-of-clip tracking dropout
  (the defender in 066, the attacker in 069, each missing the last
  ~0.5s/~30 frames of the clip, confirmed via `representations.py`'s
  reliability filter and cross-checked against the overlay video). This
  was investigated and the decision at the time was "keep as-is" since
  the flagged moment's key action didn't appear to fall in that window.
  Excluding these two clips from the working set **sidesteps** the
  question rather than resolving it — a deliberate scope trade-off given
  time constraints, not a claim that the dropout was proven harmless.
- **clip_063 / clip_051** — of the remaining 8 clips, these two had the
  messiest internal tracking gaps (several short reliability-filter
  exclusions each, see `representations.py`'s occlusion filter). Dropped
  proactively to keep the working set on the cleanest-tracked data,
  independent of the 066/069 dropout question.
  - **clip_051 was then explicitly restored** after review, because it's
    the *only* `stepback` example and one of only two `shot_made`-outcome
    clips in the whole 10-clip pool — excluding it alongside clip_066
    (the other `shot_made` clip) would have left the working set with
    zero successful-shot examples and no stepback coverage at all.
- **clip_070 dropped in its place** to keep the set at 6: both clip_070
  and clip_062 have perfectly clean tracking (zero reliability-filter
  exclusions), but clip_070 is a third `crossover` example (already
  covered by clip_033 and clip_084) while clip_062 is the *only*
  `between the legs` example in the pool. Dropping the redundant one
  preserves more vocabulary coverage than dropping the unique one.

**Net effect**: the final 6 clips cover all 5 `move_type` terms
(crossover x2: 033, 084; dribble: 038; stepback: 051; between the legs:
062; spin_move: 093) and include a `shot_made` outcome (051) alongside
shot_missed, steal, and blocked — broader coverage on both axes than the
original 4-clip test batch used earlier in development.

## Ground truth upgrade: `move_type` + `move_description`

`self_label_form.xlsx`'s `move_type` column (originally single word:
crossover, dribble, stepback, between the legs, spin_move) is uneven —
`dribble` in particular is far more generic than the other four terms,
since almost any possession involves dribbling. A `move_description`
column (full sentence describing what actually happened) was added
alongside it, not replacing it:
- `move_type` stays as a secondary/coarse signal, scored via a literal
  keyword match (`check_move_type_match` / `MOVE_TYPE_KEYWORDS` in
  `llm_feedback.py`).
- `move_description` is the primary ground truth, scored via a genuine
  LLM-as-judge semantic comparison (`judge_move_match`) — does the
  model's own `identified_move` substantively capture the same action,
  regardless of exact wording.

Both scores are kept and saved per representation, never collapsed into
one silent boolean — consistent with this project's running principle of
not trusting a single automated signal blindly.

## Prompt glossary: three iterations

The prompt's move-type reference paragraph went through three drafts
before settling:
1. **Checklist-style** ("a crossover typically shows a sharp lateral
   change...") — rejected: reads as a detection instruction (what
   pattern to search for in the data) rather than a definition of the
   term, edging toward the pipeline doing interpretation for the model.
2. **Ball-centric dictionary** ("a crossover is switching the ball
   hand-to-hand...") — rejected: references the ball, which the model
   never has data for (no ball-tracking anywhere in Diar's pipeline), so
   the definition gives it nothing it can actually connect to what it
   observes.
3. **Body-movement-grounded (final, live in `PROMPT_TEMPLATE`)** — each
   term defined by what the body itself mechanically does (footwork,
   rotation, weight shift), tested against: does each sentence describe
   what the technique fundamentally *is*, or what signal to detect? Only
   "is" statements were kept.

## Explicitly not done (methodological boundary, not an oversight)

An earlier proposal to add derived pose-based features directly into the
JSON/NL representations (e.g. counting wrist-crossing events as a
crossover proxy, or hip/shoulder rotation magnitude as a spin-move proxy)
was **rejected**: computing those signals in `representations.py` would
mean the *pipeline* interprets the movement before the LLM sees it,
undermining the core research question ("what can the LLM infer from
each representation itself"). `representations.py` remains untouched -
only the prompt's *instructions* (the glossary) were extended, never the
representation *data*.

## Related work: ViSTAR (CHI 2026) as context, not a template

ViSTAR (arXiv:2602.22077, "Virtual Skill Training with Augmented Reality
with 3D Avatars and LLM coaching agent") is directly relevant prior work
for the methodology section, but its architecture is the *opposite* of
what this project's `raw_2d`/`raw_3d` arms deliberately test: ViSTAR's
LLM never receives raw joint coordinates or rotations at all. A separate
statistical pipeline (DTW alignment against an expert reference, then
Random Forest prioritisation) does all the movement interpretation first,
and the LLM's only role is narrating an already-verbalized list of errors
("move your left knee rightward") into readable, prioritised coaching
text. The paper states this directly: LLMs "are not designed to handle
raw joint angles."

This is useful, citable context rather than a prompt to copy: it means
the published literature actively avoids the exact comparison this
project makes (LLM directly interpreting raw pose vs. a pre-summarized
representation). If `raw_2d`/`raw_3d` underperform `json_summary`/
`nl_description` in this project's results, that would be a
literature-consistent finding, not a surprising one - and testing it at
all fills a gap ViSTAR's own design choices sidestepped. ViSTAR's actual
prompt text wasn't reused here since it solves a structurally different
task (correcting form against a known-good reference performance, not
identifying a tactical move with no reference and no ball data).

## `move_type` evolved into multi-term structured labels

When the user filled in `move_description`, `move_type` was independently
upgraded too — from one word per row to a comma-separated list of terms
(e.g. `"crossover, between-the-legs"`, `"hesitation, spin move, fake"`,
`"crossover, fast dribble, layup drive"`). New terms appear that weren't
in the original 5-term vocabulary (`fast dribble`, `layup drive`,
`hesitation`, `fake`). `check_move_type_match`/`MOVE_TYPE_KEYWORDS`
(`llm_feedback.py`) was rewritten to split on commas and check each term
as a plain substring, replacing the old hardcoded 5-term synonym dict,
which no longer fit the label format. `move_type` remains the secondary/
coarse signal; `move_description` + the LLM-judge stayed the primary one
throughout this change.

## `moment_start_sec` / `moment_end_sec`: format and what they control

These mark the specific sub-window within each already-trimmed clip where
the flagged action actually happens (the move, shot, block, steal - not
just "the whole clip"), and are now the real analysis window used by
`representations.py` (`resolve_moment_window`) for both representation-
building and (eventually) frontend seeking.

**Format note, worth knowing if this file is read without the code**:
the form stores these as `"HH:MM:SS"` strings (e.g. `"00:00:08"`), not
plain numeric seconds - Excel round-trips manually-entered time-formatted
cells this way. `representations.py` has a `_parse_moment_time()` helper
that converts this (and plain numbers, for robustness) into seconds.
Windows are padded by `DEFAULT_PADDING_SEC` (0.5s) on each side and
clamped to the clip's real bounds.

Resulting windows for the 6 clips (after padding, in seconds within each
clip's own 0-based timeline):

| Clip | Window (s) | Clip duration (s) |
|---|---|---|
| clip_033 | 7.50 – 10.98 | 10.98 |
| clip_038 | 0.50 – 4.97 | 4.97 |
| clip_051 | 3.50 – 6.50 | 7.98 |
| clip_062 | 4.50 – 7.98 | 7.98 |
| clip_084 | 1.50 – 3.97 | 3.97 |
| clip_093 | 8.50 – 12.98 | 12.98 |

A useful side effect: narrowing the representation-building window to the
actual flagged moment (rather than the whole trimmed clip, as the earlier
4-clip test batch did) kept every prompt comfortably small - the largest
prompt across all 6 clips' 4 representations was ~16k characters
(~4k tokens), nowhere near the 16,000-input-tokens/minute Gemma ceiling
found earlier. No token-budget engineering was needed for this batch.

## Real batch run results — 6 clips × 4 representations (48 Gemma calls)

Run after the fixes above, on the finalized 6-clip set with real
`move_description` ground truth. All 24 representations succeeded (0
errors) across 24 main identification calls + 24 judge calls.

**Full results** (`identified_move` / keyword match / judge match / judge's reason):

**clip_033** — `move_type`: crossover, between-the-legs
- raw_2d: "drive to the basket" — kw=False, judge=**True** — "encompasses the specific dribble moves and layup attempt described"
- raw_3d: "direct drive to the basket" — kw=False, judge=**False** — "emphasizes deceptive dribbling moves like crossovers, which contradicts... 'direct'"
- json_summary: "aggressive drive to the basket" — kw=False, judge=**True** — "substantively encompasses the act of using dribble moves"
- nl_description: "drive to the basket" — kw=False, judge=**True** — "is the definition of a drive to the basket"

**clip_038** — `move_type`: fast dribble
- raw_2d: "Crossover dribble" — kw=False, judge=**False** — "focuses on a shot attempt being stolen, not the execution of a crossover"
- raw_3d: "crossover" — kw=False, judge=**False** — "depicts a shot attempt being stolen/blocked"
- json_summary: "crossover" — kw=False, judge=**False** — "depicts a shot attempt and a defensive steal"
- nl_description: "crossover dribble" — kw=False, judge=**False** — "describes a shot attempt and a steal"

**clip_051** — `move_type`: stepback
- raw_2d: "driving dribble" — kw=False, judge=**False** — "described action is a step-back move to create space"
- raw_3d: "Drive and pull-up jumper" — kw=False, judge=**False** — "'step-back' involves moving away from the defender/basket... 'drive' involves moving toward"
- json_summary: "crossover drive to the left" — kw=False, judge=**False** — "actual action was a step-back shot to create space"
- nl_description: "lateral dribble drive" — kw=False, judge=**False** — "step-back... is the opposite of a 'drive'"

**clip_062** — `move_type`: between-the-legs, crossover
- raw_2d: "stepback" — kw=False, judge=**True** — "the culminating and primary move that leads to the shot"
- raw_3d: "dribble" — kw=False, judge=**False** — "too generic, fails to capture the specific sequence"
- json_summary: "crossover" — kw=**True**, judge=**False** — "only identified one element of a complex sequence"
- nl_description: "crossover" — kw=**True**, judge=**False** — "identified only one part of a sequence"

**clip_084** — `move_type`: crossover, fast dribble, layup drive
- raw_2d: "dribble drive to the basket" — kw=False, judge=**True** — "encompasses the crossover and fast dribbling described"
- raw_3d: "Drive to the basket" — kw=False, judge=**True** — "is the core move described"
- json_summary: "drive to the basket" — kw=False, judge=**True** — "is the definition of a drive to the basket"
- nl_description: "dribble drive to the basket" — kw=False, judge=**True** — "accurately describes the core action"

**clip_093** — `move_type`: hesitation, spin move, fake
- raw_2d: "stepback" — kw=False, judge=**False** — "stepback is a specific move... [not what happened]"
- raw_3d: "stepback" — kw=False, judge=**False** — "none of which constitute a stepback"
- json_summary: "crossover dribble" — kw=False, judge=**False** — "significantly different from a simple crossover dribble"
- nl_description: "lateral dribbling" — kw=False, judge=**False** — "distinct and more specific actions"

**Totals**: judge 8/24 (33%), keyword 2/24 (8%). Judge outscores keyword
overall, as expected (catches semantically-correct-but-differently-worded
answers keyword can't). One case where **keyword exceeded judge**
(clip_062, json_summary/nl_description): both answered "crossover" -
literally present in the label, so keyword-matched - but the judge
correctly declined, since "crossover" alone doesn't substantively cover
the full described sequence (crossover -> between-the-legs -> another
crossover -> step-back shot). A clean demonstration that the judge does
genuine semantic-completeness assessment rather than keyword-spotting.

## Representation-level breakdown — the core research-question result

| Representation | Judge matches | Rate |
|---|---|---|
| **raw_2d** | 3/6 | **50%** |
| raw_3d | 1/6 | **17%** |
| json_summary | 2/6 | 33% |
| nl_description | 2/6 | 33% |

`raw_3d` is the weakest performer, `raw_2d` the strongest. This is
directionally consistent with an earlier single-clip observation
(clip_033 alone: raw_3d was the only representation that failed) - the
pattern held up once extended to 6 clips, not an artifact of one example.
**Caveat for the write-up**: n=6 per representation is small; this is
suggestive, not statistically conclusive. The consistent direction across
both the single-clip and 6-clip views is worth noting as more than
one-off noise, but should not be overstated as a proven effect.

## Judge reasoning capture - why it was added, and what it showed

The judge originally returned only a bare yes/no with no justification
saved anywhere. When asked to justify why two clips' judge calls looked
inconsistent (clip_084: all 4 representations' answers were generic
"drive to the basket"-style phrases and all judged True; clip_093:
similarly partial-looking answers like "stepback" were all judged False),
there was no reasoning on record to check - a real transparency gap given
this metric is meant to go in a dissertation. `judge_move_match` was
rewritten to return `(match, reason)` via a structured JSON response
instead of a single word, and all 24 judge calls were re-run (reusing the
already-generated `identified_move` answers, no need to redo the 24 main
identification calls) to capture reasoning uniformly. All 24 verdicts
came back identical to the original single-word version - no flip-
flopping from the prompt change, which is reassuring for the judge's
stability.

**On inspection, the apparent inconsistency wasn't one**: clip_084's
`move_description` is fundamentally one continuous action (a drive to
the rim, executed with some dribble technique) - "drive to the basket"
is the *correct general category*, just missing footwork detail.
clip_093's answers ("stepback", "crossover dribble") aren't incomplete
versions of the right answer - they're specific named techniques that
don't appear in that clip's ground truth at all (no stepback happened in
clip_093; no crossover either). Same judge rule applied both times
("does this substantively capture the core action") - the difference is
that clip_084's imprecise answers still land on the correct core action,
and clip_093's don't. Worth stating this explicitly in the dissertation
as something that was checked, not assumed, per this project's running
"don't trust a confidence/quality signal without verifying it" principle.

## Independent manual/semantic evaluation (not the LLM-judge)

After the LLM-judge results above, a separate manual evaluation was done:
Claude read all 24 saved `identified_move` answers directly against
`move_type`/`move_description` and judged correctness itself, using a
rubric supplied by the user - explicitly *not* reusing
`move_type_match_llm_judge` or the keyword metric. No new Gemma calls
were made for this pass; it's a second, independent read of the same 24
saved answers, done by a different judge (Claude directly, following a
human-specified rubric) than the one that produced the 33% figure above
(Gemma itself, as LLM-judge). Rubric: partial-but-correct answers count
when they identify the core action (e.g. "crossover + fast dribble +
layup drive" -> "dribble drive to the basket" = Correct); answers naming
a different, unsupported specific technique count as Incorrect (e.g.
"hesitation + spin move + fake" -> "stepback" = Incorrect).

**Full 24-row result:**

| clip_id | representation | gemma_identified_move | correct/incorrect | reason |
|---|---|---|---|---|
| clip_033 | raw_2d | "drive to the basket" | Correct | general but accurate description of the core action |
| clip_033 | raw_3d | "direct drive to the basket" | **Correct** (corrected, was Incorrect) | core claim ("drive to the basket") matches the other three; "direct" is a style modifier, not an assertion of a different technique - see correction note below |
| clip_033 | json_summary | "aggressive drive to the basket" | Correct | general but accurate |
| clip_033 | nl_description | "drive to the basket" | Correct | same as raw_2d |
| clip_038 | raw_2d | "Crossover dribble" | Incorrect | names a technique (crossover) not mentioned/implied in the description |
| clip_038 | raw_3d | "crossover" | Incorrect | same |
| clip_038 | json_summary | "crossover" | Incorrect | same |
| clip_038 | nl_description | "crossover dribble" | Incorrect | same |
| clip_051 | raw_2d | "driving dribble" | Incorrect | "driving" implies toward the basket; actual move (stepback) is away - opposite direction |
| clip_051 | raw_3d | "Drive and pull-up jumper" | Incorrect | "drive" again implies wrong direction; no stepback captured |
| clip_051 | json_summary | "crossover drive to the left" | Incorrect | names unsupported "crossover" + wrong direction; no stepback |
| clip_051 | nl_description | "lateral dribble drive" | Incorrect | sideways movement, not the backward stepback that's the actual move |
| clip_062 | raw_2d | "stepback" | Correct | names the real, final, shot-creating move in the sequence |
| clip_062 | raw_3d | "dribble" | Incorrect | too generic - true of nearly any possession, names none of the actual distinguishing moves |
| clip_062 | json_summary | "crossover" | Correct | names a real, specific, repeated move in the actual sequence |
| clip_062 | nl_description | "crossover" | Correct | same as json_summary |
| clip_084 | raw_2d | "dribble drive to the basket" | Correct | captures the core action (the rubric's own worked example) |
| clip_084 | raw_3d | "Drive to the basket" | Correct | same |
| clip_084 | json_summary | "drive to the basket" | Correct | same |
| clip_084 | nl_description | "dribble drive to the basket" | Correct | same |
| clip_093 | raw_2d | "stepback" | Incorrect | the rubric's own worked Incorrect example - stepback isn't mentioned/implied |
| clip_093 | raw_3d | "stepback" | Incorrect | same |
| clip_093 | json_summary | "crossover dribble" | Incorrect | names an unsupported technique - no crossover in the description |
| clip_093 | nl_description | "lateral dribbling" | Incorrect | too generic/vague, captures neither the hesitation/fakes nor the spin-move |

**Totals: 11/24 correct (46%)** (originally scored 10/24 - see correction
below), vs. the retired LLM-judge's 8/24 (33%).

**By representation** (manual eval, corrected): raw_2d 3/6, **raw_3d
2/6**, json_summary 3/6, nl_description 3/6. Same relative ranking as the
original LLM-judge pass (raw_3d weakest, raw_2d strongest).

**Where the two evaluations diverge**: `clip_062`'s `json_summary` and
`nl_description` (both answered "crossover") - the LLM-judge marked these
Incorrect ("only identified one element of a complex sequence") while the
manual evaluation marked them Correct, for consistency with `clip_062`'s
`raw_2d` ("stepback"), which the LLM-judge *did* accept as capturing "the
culminating and primary move." Both "crossover" and "stepback" name one
real, accurate component of the same multi-move sequence; the manual
evaluation held them to the same standard rather than accepting one
partial answer and rejecting the other. This is a genuinely borderline
rubric call, not a clear error in either evaluation - worth stating
explicitly in the dissertation as an example of evaluator disagreement on
a partial-match case, rather than treating either number as the single
correct one.

**Correction found during review (user-caught): `clip_033`'s `raw_3d`
was inconsistently scored.** All four of clip_033's answers are variants
of "drive to the basket" ("direct drive...", "aggressive drive...",
plain "drive..."); three were marked Correct and `raw_3d` ("direct drive
to the basket") was marked Incorrect, reasoning that "direct" contradicts
the deceptive nature of a crossover/between-the-legs move. On review this
was inconsistent application of the rubric: the Incorrect test is
"identifies a *different basketball technique*" (e.g. calling a spin-move
a stepback), and "direct" is a style modifier on an otherwise-identical
core claim, not an assertion of a different technique - it does not
belong in the same category as, say, `clip_038`'s "crossover dribble"
naming a specific unsupported technique. Corrected to Correct; totals
above reflect the fix. **Lesson for the write-up**: this is itself
evidence that manual/semantic evaluation - not just automated
keyword/LLM-judge metrics - needs its own review pass for internal
consistency; a single evaluator's first read isn't automatically the
ground truth either. Caught via user review, not a self-check.

**Also raised during review and deliberately kept as-is**: `clip_038`
(actual: "fast dribble") - all four answers include the word "dribble"
("Crossover dribble" x2, "crossover" x2) but were scored Incorrect
because they specifically assert "crossover," a distinct named technique
not supported by the description ("Player 2 uses fast dribbling and
shoots... Player 1 steals the ball" - no direction-change/hand-switch
described). Judging this Correct purely because the substring "dribble"
appears in both would reintroduce the literal keyword-matching approach
this project deliberately moved away from. Distinguished from the
clip_033 correction above: "direct" doesn't compete with "drive" as an
alternative technique name, but "crossover" does compete with (and isn't
supported by) plain "dribble." Kept Incorrect after this reasoning was
discussed directly with the user.

**Ground-truth update: `clip_033`'s `move_type` gained "drive"** (user
edit to `self_label_form.xlsx`, 2026-08-13). Original label was
`"crossover, between-the-legs"`; the user added a third term because a
drive to the basket is genuinely part of what happens in the clip (the
crossover/between-the-legs moves lead directly into a drive for the
layup), matching `move_description`'s existing wording ("...and driving
for layup..."). This is a label correction, not a re-interpretation - all
four `identified_move` answers already say "drive to the basket" in some
form and were already scored Correct in the manual evaluation above (the
11/24 total is unaffected). It does change the cheap automated
`move_type_match_keyword` signal, which previously read False for all
four clip_033 answers (none contained the literal substrings "crossover"
or "between-the-legs") and now reads **True** for all four (all contain
"drive"), bringing keyword and manual evaluation into agreement on this
clip for the first time. `actual_move_type`, `actual_move_description`,
and `move_type_match_keyword`/`move_type_match` were patched directly in
`backend/output/checkpoints/clip_033__*.json`,
`backend/output/frontend_data/clip_033.json`, and
`frontend/public/data/clip_033.json` to reflect the corrected label - no
new Gemma calls were needed since no generated answer changed, only the
ground truth it's compared against.

## LLM-judge retired from the active pipeline

The LLM-as-judge second call (`judge_move_match` in `llm_feedback.py`,
Gemma judging its own `identified_move` against `move_description`) has
been **removed from `llm_feedback.py`/`batch_generate.py`** - it no
longer runs for new generations. Reasons:
1. It disagreed with careful manual reading on a real case (`clip_062`,
   above) without being demonstrably more reliable - having the model
   grade itself isn't a shortcut around actually checking the answer.
2. The `clip_033` correction above shows even careful manual evaluation
   needs a review pass; an opaque automated judge call offers no way to
   audit *why* it decided what it decided beyond the reason string, and
   even with reasons captured, the judge's own reasoning was sometimes
   the thing found to be wrong (`clip_062`).
3. Removing it roughly halves the API calls needed per batch (no more
   second call per representation).

The historical judge data (all 24 verdicts + reasons) is kept in this
file and in already-generated `frontend_data`/checkpoint JSON, not
deleted - it's a real part of the methodology journey (keyword match ->
LLM-judge -> manual review) worth documenting, even though it's no longer
computed for new clips. Going forward, `move_type_match` in generated
data defaults to the keyword check (cheap, automated, clearly
provisional) until a manual review pass sets `move_type_match_manual`,
the same process used for these 6 clips.

## Full-clip re-run: analysis window changed from moment-only to whole clip

User-caught methodology issue (2026-08-13): `moment_start_sec`/`moment_end_sec`
were being used to *restrict* what pose data every representation was built
from (padded moment window only, e.g. clip_033's 3.5s window out of its
11s total). The user clarified this was never the intent - those fields
were added purely for the frontend's "jump to moment"/loop UI, not as a
data-trimming instruction, and restricting the LLM's input window can cut
off real movement relevant to identifying the move (e.g. a drive that
continues past `moment_end_sec`).

**Fix**: `representations.py`'s `load_moment()` now always builds every
representation (raw_2d, raw_3d, json_summary, nl_description) from the
clip's full span `[0, duration_sec]`. The flagged `moment_start_sec`/
`moment_end_sec` window is still resolved (via the same `resolve_moment_window`,
padding included) and carried on `Moment`, but only for the frontend's
metadata (`VideoStage.jsx`'s "Jump to moment" loop) - the two are now
fully decoupled where they previously were conflated into one field.
Normal video playback (clip selection, Original/2D/3D toggle) now plays
the whole clip; only clicking "Jump to moment" seeks and loops the flagged
sub-window.

**Token budget re-checked before running**: worst case is `clip_093` at
13s full length, raw_3d payload ~9.9k tokens (26 sampled frames/player at
`RAW_REPR_TARGET_FPS=2.0`) - still comfortably under the 16k-tokens/minute
ceiling, so no fps change was needed.

**Re-ran the full batch** (24 real Gemma calls, 0 errors) with full-clip
data. Old moment-window checkpoints/`frontend_data` were archived (not
deleted) to `backend/output/checkpoints_moment_window_archive/` and
`backend/output/frontend_data_moment_window_archive/` for methodology
comparison. A fresh manual/semantic review pass (same rubric as the
moment-window round) was applied to the new 24 answers:

| clip_id | representation | gemma_identified_move | correct/incorrect | reason |
|---|---|---|---|---|
| clip_033 | raw_2d | "crossover drive" | Correct | names both a real component (crossover) and drive, matching move_type directly |
| clip_033 | raw_3d | "drive to the basket" | Correct | drive is now an explicit move_type term, directly supported by move_description |
| clip_033 | json_summary | "Crossover drive to the basket" | Correct | names crossover and drive, both real components |
| clip_033 | nl_description | "dribble drive to the basket" | Correct | drive matches move_type/move_description; no unsupported technique named |
| clip_038 | raw_2d | "crossover dribble" | Incorrect | names crossover, unsupported by move_description |
| clip_038 | raw_3d | "crossover" | Incorrect | same |
| clip_038 | json_summary | "crossover" | Incorrect | same |
| clip_038 | nl_description | "lateral dribbling" | Correct | "lateral" is a directional modifier on the correct base action (fast dribble is the whole ground truth here); doesn't assert a competing technique |
| clip_051 | raw_2d | "sustained drive to the left" | Incorrect | "drive" implies toward the basket; actual (stepback) is backward - opposite direction |
| clip_051 | raw_3d | "dribble drive to the mid-range" | Incorrect | same direction conflict |
| clip_051 | json_summary | "Crossover drive" | Incorrect | unsupported crossover + wrong-direction drive |
| clip_051 | nl_description | "lateral dribble drive" | Incorrect | drive again contradicts the backward stepback |
| clip_062 | raw_2d | "crossover dribble" | Correct | crossover is a real, repeated component of the actual sequence |
| clip_062 | raw_3d | "crossover" | Correct | same |
| clip_062 | json_summary | "crossover" | Correct | same |
| clip_062 | nl_description | "lateral dribbling" | Incorrect | too generic - names none of the actual distinguishing moves (crossover x2, between-the-legs, step-back) |
| clip_084 | raw_2d | "drive to the basket" | Correct | matches move_type's "layup drive" term and the description directly |
| clip_084 | raw_3d | "drive to the basket" | Correct | same |
| clip_084 | json_summary | "Drive to the basket" | Correct | same |
| clip_084 | nl_description | "Drive to the basket" | Correct | same |
| clip_093 | raw_2d | "crossover" | Incorrect | not supported anywhere in move_type or move_description (actual: hesitation, spin move, fake) |
| clip_093 | raw_3d | "drive to the basket" | Incorrect | a real but incidental action mentioned in passing in move_description; not one of the three defining techniques the human labeler named, misses all three - same too-generic/misses-the-distinguishing-move category as clip_062/clip_051's "drive"/"dribble" |
| clip_093 | json_summary | "Crossover" | Incorrect | unsupported |
| clip_093 | nl_description | "lateral dribbling" | Incorrect | too generic, names none of hesitation/spin move/fake |

**Totals: 12/24 correct (50%)**, up from the moment-window round's 11/24
(46%). By representation: raw_2d 3/6, raw_3d 3/6, json_summary 3/6,
nl_description 3/6 - flatter across representations than the
moment-window round (which had raw_3d as a clear weak point at 2/6).
`clip_051` and `clip_093` remain fully incorrect (0/4) in both rounds -
both involve reversals/deceptive moves (stepback, hesitation/spin/fake)
that plain lateral-movement pose signals struggle to distinguish from an
ordinary drive, regardless of how much of the clip is shown. `clip_084`
remains fully correct (4/4) in both rounds. `clip_038` improved from 0/4
(moment-window) to 1/4 (full-clip) and `clip_033` improved from 3/4 to
4/4 (partly because `move_type` itself gained the "drive" term in
between the two rounds, not purely a data-window effect - see the
ground-truth update note above).

As before, `move_type_match` in the synced `frontend_data`/
`frontend/public/data` JSON reflects the manual verdict (authoritative),
not the raw keyword substring check, to avoid the same false-red bug
class caught and fixed earlier for clip_033.

## Coach validation data — not yet available

`coach_feedback_form.xlsx` exists but is not yet filled in. Not blocking
current work. When it is ready, the plan is to add it as an additional,
optional field in the frontend's per-clip JSON output (e.g.
`coach_feedback`, absent/null until then) rather than restructuring
anything that exists now - this note exists so that future addition is
remembered as additive, not a redesign.
