# AI Basketball Coach — Personalised Post-Session Coaching Using Computer Vision and LLMs

## Project Overview
Builds an AI-assisted basketball
coaching system that analyses a 1-vs-1 basketball game and gives the player
personalised, tactical coaching feedback after the session — not just event counts
(shots made/missed) but **why** something worked or didn't, and what the player
could have done differently.

**Deadline: prototype submission in 3 weeks from Aug 3, 2026.** The deadline itself
hasn't moved. What changed (Aug 5) is how time within it is allocated — see
"Priority Roadmap" for the revised sequencing and reasoning.

## Objective & Research Gap
Most existing basketball AI tools analyse isolated individual skills (e.g. shot form,
shooting percentage). They don't reason about **attacker-defender interaction** —
who has the ball, what move the attacker tried, how the defender reacted, and
whether a different decision would have worked better. That interaction-level
tactical reasoning is the gap this project fills.

## Core Concept — Input/Output Flow
1. Player opens the app, opens the camera inside it, and starts recording before
   the 1v1 game begins.
2. While recording, computer vision runs in the background, extracting structured
   game data (positions, movement, ball possession, events) and packaging it as JSON.
3. When the player stops recording, the JSON (with timestamps) is sent to an LLM.
4. The LLM returns feedback that:
   - Opens with **positive feedback** for what went well (e.g. a shot made).
   - Flags **mistake timestamps** — the video seeks to that exact moment.
   - Offers **~3 alternative moves** the player could have made at that moment
     (never just one "correct" answer — there are many ways to beat a defender).
   - Is delivered in **simple, beginner-friendly language**, as text and
     (optionally) audio.

## System Pipeline
1. **Player detection & tracking** (attacker + defender identified and tracked
   through the clip)
2. **Ball tracking** (possession, passes, shot release)
3. **Court calibration / homography** (map pixel coordinates to real court
   coordinates — 2pt line, 3pt line, key/layup zone)
4. **Event detection** (dribble, crossover, hesitation, fake, drive, pass, shot,
   make/miss) — derived from geometry/heuristics rather than a trained classifier,
   given the time budget
5. **Structured JSON output** (see schema below)
6. **LLM coaching layer** (JSON + supporting data → personalised feedback)
7. **Video UI** — feedback synced to timestamps in the original clip, with
   text + optional audio

## JSON Schema — Data to Extract
Per frame / per event, capture:
- Player (attacker) position, Defender position, Ball position, Basket position
- Court zone lines if available: 2-point line, 3-point line, layup/key area
  (needed so the LLM knows *where* on the court an action happened)
- Attacker speed, Defender speed
- Defender's hip movement direction (left/right) — used to infer defensive
  reaction to a fake/crossover
- Ball possession flag (who has the ball, frame by frame)
- Shot outcome: made / missed, and which zone it was taken from (2pt/3pt/layup)
- Whether the defender contested/got the ball (steal, deflection, block)
- Timestamps for every detected event, for LLM reference and video seek

> Attacker/defender role assignment depends entirely on ball possession — so
> ball tracking is the component that unlocks most of the rest of this schema.

## LLM Feedback Layer
Inputs the LLM should receive, in order of value:
1. **JSON data with timestamps** (core structured signal)
2. **Annotated reference spreadsheet** — a hand-built sheet of common
   attacker moves (fake, crossover, hesitation, and other deceptive moves) with
   plain-language names/descriptions, used as domain knowledge the LLM can draw on
3. **A small set of hand-written feedback examples**, written by the project
   author in layman's terms, as style/tone reference for the LLM's output
4. **Video/clip data**, if feasible within context/size limits, for extra grounding
5. A carefully designed system prompt tying all of the above together

**Important framing for the LLM's reasoning:** most missed baskets are *not*
purely "the defender stopped them" — often it's ball-handling, a missed pass to
a teammate, or a shooting mechanics issue. The feedback logic must not default to
blaming the defender for every miss; it should reason across all plausible causes
visible in the data.

**Finding from the Aug 5 JSON → LLM proof-of-concept** (`scripts/llm_poc.py`,
local Ollama + llama3.2:3b, event JSON only — outcome + timestamp, no
mechanism): the plumbing works (coherent, correctly-formatted output), but
the model hallucinated specific causes not present in the input — e.g.
inventing "blocked," "off-balance jump," and "rushed move" for shots where
the JSON only says `MISS`, and once mislabeling a `MISS` shot attempt as an
"intercepted pass" (an event type not present anywhere in the input). This
is expected behaviour when an LLM is asked to explain "why" from data too
sparse to support a real reason, not a prompt-wording bug — it's a concrete
argument for why the shot-zone/defender-reaction/decision-quality signals
are worth building before investing in the real feedback-loop prompt: richer
grounding data should reduce confabulation, but this should be re-checked
once those signals exist rather than assumed.

Stretch ideas (mention in thesis discussion, not required for prototype):
- RAG over basketball coaching knowledge, if time allows (suggested by Daniele)
- World models as an alternative to LLM reasoning — noted as an idea but too
  expensive/complex for this timeframe; discuss as future work only, don't build


## Priority Roadmap (given the 3-week deadline)
Originally sequenced so there's always a working end-to-end demo, even a rough
one, rather than polishing one stage in isolation. **Revised Aug 5, 2026:** the
deadline hasn't moved, but the time within it is now being allocated
differently — CV accuracy/completeness is the priority for most of the
remaining time, rather than moving fast toward a polished demo. A quick, rough
JSON → LLM proof is still done early, not because the JSON → LLM concept is in
doubt, but to have something concrete for supervisor visibility and to confirm
the integration works before committing the rest of the time to CV work.

1. **Quick JSON → LLM proof-of-concept** (bounded, <1hr): feed the existing
   possession/dribble/shot/make-miss JSON for the validation clip into a basic
   prompt, call a local LLM, and produce feedback text for a handful of sample
   events. No UI, no Unity/avatar integration, no prompt optimization — just
   confirms the JSON → LLM step produces coherent output.
2. **Ball detection & tracking accuracy (Stage 2)** — top priority for the
   remainder of the time. Push raw detection rate and occlusion handling as
   far as practical.
3. **Pose accuracy (Stage 3)** — done (Aug 7): production extraction script
   built, hardened, and quantitatively validated (see Known Limitations).
   Dribble re-verification against the Aug 5 detector swap (item below)
   is still outstanding and should happen before trusting Stage 2/4
   numbers downstream.
4. Once all CV stages (ball tracking, pose, possession, dribble, shot/
   make-miss) are fully validated and accurate — homography/court-zone
   detection, defender-reaction, attacker-approach, and decision-quality
   signals (combining shot zone + defender reaction + attacker separation
   into e.g. "open 3 after clean separation" vs. "contested long 2 off a
   stalled drive").
5. A fuller, polished LLM feedback loop and video-seek UI come after all of
   the above — the quick proof in step 1 is a bounded insurance check and
   demo artifact, not the real build.
6. Treat multi-representation LLM evaluation, RAG, and coach-validation
   studies as thesis-analysis extensions, not prototype blockers.

## Known Limitations (CV pipeline, found via validation against real footage)
These are open, unresolved gaps — not bugs pending a fix, but structural
limits of the current approach that should inform thesis discussion and
any future footage collection:
- **Static-object false-positive rejection only catches STATIONARY
  distractors.** Stage 2 ball tracking clusters raw ball-class detections
  across a clip and excludes any cluster that stays fixed in place for a
  long stretch (this caught a real bystander object near a bench that was
  corrupting 30%+ of frames). A MOVING false positive — e.g. a bystander
  idly bouncing a second ball near the sideline while the game continues —
  would not be caught, since it never forms a low-variance static cluster.
  Would need a complementary signal (e.g. restricting valid candidates to
  a court-area region, or preferring candidates near one of the two
  Stage-1-locked players) to handle that case.
- **Tight, sustained defensive contact produces a total ball-tracking
  blind spot.** In the validation clip, the one sustained close-defense
  stretch (~2.9s, both players within ~120px of each other) had ZERO real
  ball detections for its entire duration — the ball was fully occluded
  by the two players' bodies the whole time, so Stage 2 fell back entirely
  to occlusion-attribution (nearest player's own position), not real ball
  observations. This means event detection (dribbles, crossovers) has the
  least reliable signal during exactly the tight-defense moments the
  coaching-feedback concept cares about most (defender reaction to a
  move under pressure). Not a detection bug — a genuine visibility limit
  of a single fixed camera angle.
- **Dribble detection cannot distinguish a real floor bounce from a
  bounce-shaped trajectory that occurs while the ball never actually
  left the holder's hand, or while it's in flight during a fast, flat
  pass.** Found via a full manual review of 32 flagged dribbles against
  the source video (project owner, not a spot-check): (1) a shot
  pump-fake dip produces the identical rise-fall-rise y-shape as a real
  bounce, with `ball_held` staying True the whole time — no possession
  discontinuity exists for the detector to key off; (2) a quick, flat
  bounce pass can travel far enough to visually leave the passer's hand
  while never pushing the ball-to-player distance ratio past
  `POSSESS_RATIO` within the attribution window, so it never registers
  as "released" either. Tested and explicitly rejected as a fix:
  tightening `POSSESS_RATIO` (0.5 → 0.45/0.40/0.35) against confirmed-real
  dribbles as ground truth. Result: it does NOT solve the pass case (the
  release span it does detect sits just outside the dribble-peak's
  frame, a boundary-alignment problem, not a threshold problem) while
  causing severe collateral damage — at 0.40 an entire real ~150-frame
  dribbling sequence got swallowed into one bogus `shot_attempt` event;
  at 0.35 that grew to 234 frames. Do not revisit this specific fix
  without a different approach to the boundary-alignment issue.
  **Potential future improvement**: the Stage 3 pose pipeline already
  extracts hip/shoulder keypoints per frame; a pump-fake likely has a
  distinct wrist/hand velocity or arm-angle signature even while the
  ball stays gripped, which a pure ball-trajectory signal can never see.
  Not implemented — would need wrist keypoints added to the Stage 3
  extraction (currently only hip/shoulder are captured).
- **Two remaining false-positive dribbles from the 32-clip manual review,
  investigated but not fixed:**
  - Frame 151: no reliable numeric signal found. Hypothesized that an
    asymmetric bounce shape (small pre-peak dip, large post-peak rise)
    might distinguish it from a real dribble — disproven by testing
    against confirmed-real dribbles as ground truth: frame 504 (real)
    scores MORE asymmetric (0.12) than frame 151's 0.20, so a threshold
    on this ratio would reject good dribbles while missing this one.
    Logged as a one-off artifact with no known cause.
  - Frame 396: mechanism identified, but only one confirmed example.
    The flagged "peak" sits inside a 15-frame (the maximum) linear
    interpolation bridging a real-detection gap, right where that
    interpolated stretch meets a hard cut into `contested` fallback data
    one frame later (position jumps 118px in a single frame). The
    5-frame smoothing kernel blends in the upcoming discontinuity,
    shifting the apparent peak 1-2 frames before the interpolated
    segment's true (non-bounce) maximum. This is a real, understood
    mechanism — but building a general rule off a single instance risks
    overfitting to this one clip. Needs 2-3 more confirmed examples
    (from future footage) before a fix is safe to generalize.
- **Specialized basketball ball-trackers (WASB, TrackNetV2) were benchmarked
  against the current YOLO11m detector on this footage (Aug 4) and are a
  dead end here, not an upgrade path.** `scripts/stage2_wasb_track.py`
  vendors the WASB-SBDT authors' model architectures and reimplements their
  exact pre/postprocessing. Raw per-frame detection rate on
  `raw_clip_bench.mp4` (2700 frames, score threshold 0.5, their default):
  WASB (HRNet) 0.3% (9 frames), TrackNetV2 (UNet) 4.8% (130 frames) — vs.
  57.4% for the current generic YOLO11m@1280 pipeline. Likely a domain
  mismatch between their training data and this gym/camera setup rather
  than a fundamental limit of specialized trackers in general, but not
  investigated further given the gap's size. Do not revisit swapping the
  detector architecture without new evidence the domain-mismatch
  explanation is wrong (e.g. a threshold sweep showing usable detections
  exist below their 0.5 default).
- **Stage 2 detector swapped (Aug 5) to `basketball_ball_hoop_yolov8.pt` @
  imgsz=1920, replacing generic YOLO11m@1280.** Root cause of most raw
  detection gaps was investigated first: of 21 long (>15 frame) gaps under
  the old detector, only 2 were explained by the documented tight-defense
  occlusion blind spot below — the other 19 happened while players were far
  apart, because play mostly happens at the far end of the court from this
  baseline-mounted camera, so the ball is small/low-contrast at that
  distance most of the time. Full-clip benchmark (same production
  methodology — ByteTrack + static-cluster ghost exclusion + proximity-gated
  selection — applied identically to both): raw detection 57.4% (old) →
  70.4% (new), contested/tautological fallback 20.3% → 6.8%, long gaps 21 →
  9, and zero ghost-cluster contamination (the new model doesn't fire on the
  sideline bystander object at all, vs. 1 flagged cluster for the old one).
  A single-frame spot-check on 6 of the old unexplained gap frames was mixed
  (new model caught 2/6, old model caught 3/6, neither caught 1/6) —
  confirmed not a frame-extraction artifact; doesn't contradict the
  aggregate win since a net +13pp improvement across 2700 frames doesn't
  require winning every individual borderline frame.
  **IMPORTANT — downstream numbers from this new detector are UNVALIDATED
  as of this swap** (70.4% detection, 26-30 dribbles depending on which
  Stage 4 revision, 63.7%/32.1% A/B possession split, 22 possession
  switches). These moved substantially from the previously
  manually-verified state (22 dribbles confirmed real via full clip-by-clip
  review, 50.0%/45.7% possession, 12 switches) — expected, since
  possession/event detection are built downstream of raw ball position, but
  NOT yet confirmed correct. Do not cite the new numbers as ground truth
  until they go through the same clip-by-clip manual review the dribble
  count and shot outcomes already went through once. Dribble
  re-verification still pending.
- **Shot-attempt detection redesigned (Aug 5) from a flat hoop-proximity
  check to a persistent up/down state machine**, after comparing against a
  reference implementation
  (avishah3/AI-Basketball-Shot-Detection-Tracker) surfaced two confirmed
  bugs in the old approach (classify_events() calling a held-based release
  span a "shot_attempt" the instant the ball came within a flat 161px
  radius of the hoop, no directionality required):
  1. DOUBLE-COUNTING: a real shot's held-based release span could fragment
     on a brief spurious ball_held blip mid-arc (confirmed case: frames
     946-1032, a single-frame 173px misdetection at 973 locked onto a
     near-static false position for 6 frames -- one frame short of
     MERGE_GAP -- splitting one physical shot into two counted attempts).
  2. FALSE ATTEMPTS: the flat radius has no directionality, so non-shot
     motion that merely wanders within it (confirmed case: frames 909-916,
     a loose-ball bobble that never rises above the rim, picked up by the
     OTHER player 1 frame later) got misclassified as a shot -- and since
     there's no real arc, classify_make_miss then defaults to "miss",
     inflating the miss count specifically.
  Fix: detect_shot_attempts() runs an independent up/down latch (zones
  derived from our own calibrated HOOP_BOX) directly on the ball's own
  trajectory, decoupled from ball_held entirely, so a held-status glitch
  can no longer fragment one event. classify_events() no longer produces
  "shot_attempt"; reconcile_events() merges the two sources, letting the
  shot detector's call override the held-based classifier wherever their
  ranges overlap (needed, or a real shot's fragment falls through to a
  wrong dribble/pass label once the shot branch is removed from the
  held-based path).
  Two bugs found and fixed DURING this implementation, before trusting the
  result (same discipline as everything else this session):
  - build_trusted_ball_trajectory()'s first version copied
    classify_make_miss's FLAT jump-plausibility cap, reasoning it was the
    same kind of continuity check. It isn't: that cap was tuned for a
    short ~45-frame post-shot window; applied as a persistent full-clip
    scan, one legitimately large real gap gets rejected and (since the
    anchor never updates) every subsequent point compares against an
    increasingly stale anchor -- found causing a 463-frame stretch to be
    rejected almost entirely, silently blinding shot detection across a
    third of the clip. Fixed by scaling the cap by elapsed frames since
    the last trusted point, matching stage2_ball_track.py's own
    already-validated MAX_JUMP_FRAC=0.25 pattern for the identical
    underlying question.
  - The down-zone trigger's first version was bare zone membership (y past
    a threshold), which the frame-973 glitch satisfied on its own (174px
    jump lands deep in the down-zone, and jump distance alone can't reject
    it -- 174px is well within plausible real ball motion). Compared
    directly against the confirmed real make at frames 1955-1958 (smooth,
    monotonic 2.6-6.3px/frame y-increase): the glitch's frozen aftermath
    drifts under 0.3px/frame, sub-pixel noise, not motion. Fixed by
    requiring MIN_DOWN_CONFIRM_STEPS consecutive frames each moving at
    least MIN_DOWN_STEP_PX further into the zone -- reusing the same
    consecutive-genuine-descent philosophy classify_make_miss already
    uses, since a bare non-decreasing check would still pass on noise
    drifting upward by chance over a few frames.
  Result after both fixes: 6 shot attempts, 3 make, 3 miss -- an exact
  match to manual count (6 attempts, 3/3). Strong signal, not yet
  confirmed: aggregate count matching doesn't guarantee every individual
  event is correct. Clip-by-clip manual review still pending.
- **Constant-velocity extrapolation (added to Stage 2's long-gap
  handling) improves ball POSITION accuracy during short occlusions —
  it does NOT recover dribble-bounce EVENT detection during long
  occlusion.** This distinction matters for thesis framing: the fix
  reduces position error for whichever frames it applies to (empirically
  validated via holdout testing: median 15.8px error at a 5-frame horizon
  vs 170.9px for the previous centroid-only fallback, crossing over
  around ~20 frames where extrapolation starts to drift), which helps
  possession/role-assignment accuracy broadly. But the sustained
  tight-defense blind spot logged above (2.9s, zero real detections) is
  far longer than the ~20-frame window where extrapolation is trustworthy
  — beyond that window the fix still falls back to the same
  centroid-attribution approach (empirically the better of the two
  beyond ~20 frames, not a fallback of desperation). No amount of
  motion-model extrapolation recovers real dribble-bounce shape during a
  multi-second occlusion; that is a fundamental limit of vision-only
  ball tracking from a single fixed camera, not something this fix
  addresses.
- **Stage 3 production pose extraction (`scripts/stage3_pose_production.py`,
  Aug 7) completed** — hip position, windowed lateral direction, shoulder
  position/orientation, and per-keypoint confidence, all keyed to Stage-1
  locked player identities (crops come from the Stage-1 box; a second
  person appearing in a padded crop is resolved by proximity to crop
  center, not assumed to be index 0). Supersedes
  `stage3_direction_smooth.py`'s output, which had dropped shoulder
  data. hip_conf and shoulder_conf are both consistently high (means
  0.97-1.00, 0% of frames below 0.5) for both players — but this
  confidence figure does NOT reliably flag when shoulder_width_px (the
  squareness-to-camera proxy behind shoulder_angle_deg) has collapsed
  to noise. Investigated directly against raw model output rather than
  assumed (an initial "close-contact contamination" hypothesis was
  checked and rejected — only 7.1% of degenerate-width frames coincide
  with Stage 2 contested status, 27.1% with players within 200px):
  two distinct real mechanisms found, a duplicate/overlapping detection
  on an atypical bent-over pose, and a keypoint-precision limit on
  small (~126x228px) crops, plus a separately-confirmed arms-raised
  confound during shooting/catching (wrist above shoulder pulls the
  keypoints). Mitigated with crop upscaling below 200px and an
  explicit `shoulder_orientation_reliable` flag (arms-raised OR
  shoulder_width_ratio below the clip's empirical p10 = 0.03).
  Result: reliable 87.8% of frames for player A, 64.5% for player B
  (B raises its arms far more often in this clip — 24.2% vs 5.3% of
  frames). Notably, the two known tight-defense contest frames
  (890, 920) are flagged unreliable for both players simultaneously —
  the same close-contact moments that blind ball tracking (above) also
  degrade pose reliability, for a related but distinct reason (active
  contesting motion, not occlusion).
- **Cross-clip robustness check (Aug 8): the pipeline does not generalize
  to new footage without changes.** Screened a 99-clip external 1v1
  dataset for camera stability (border-region motion score vs. our own
  clip's 6.9 reference) before picking test clips, since the product only
  ever sees static/tripod footage. Finding in itself: the dataset's
  static-camera subset collapsed to only ~2 genuinely independent venues
  (a "maroon gym" cluster of ~20 clips all one source, and an outdoor
  driveway pair) — one candidate venue turned out to be the exact same
  physical gym as our own `raw_clip_bench.mp4` (identical ceiling stain
  pattern, scoreboard, ladder), not new data at all. Tested against:
  `clip_063.mp4` (maroon gym), `clip_021.mp4` (outdoor, bright sunlight),
  and a new user-recorded clip (`video1.mp4`, close-up/low-angle,
  camera resting on floor near the hoop rather than full-court).
  Raw ball detection rate varied enormously by condition: 70.4% (our
  clip) vs. 66.4% (maroon gym, similar full-court distance) vs. **12.8%**
  (outdoor, bright sunlight — 65.6% of frames fell back to the
  tautological `contested` occlusion-attribution) vs. 55.7% (close-up).
  Two real generalization bugs found, not just accuracy drops:
  1. `HOOP_CENTER`/`HOOP_BOX` in `stage4_events.py` are hardcoded pixel
     coordinates calibrated once for our own clip — silently wrong on any
     other footage. Confirmed real and still a genuine bug, but an
     earlier version of this entry overclaimed the evidence for it:
     recalibrating the hoop position for `clip_063` flipped the pipeline's
     call on one event from "miss" to "make", and that flip was reported
     as confirmation the fix worked -- WITHOUT visually checking the
     footage first. The project owner watched the clip directly: the shot
     was a real miss, rebounded by the defender. Checked afterward
     against the actual frames: recalibrating the hoop position also
     shifted the up/down zone geometry enough to bridge TWO separate
     physical events into one fake "shot" -- Player A's real jump-shot
     release (~frame 220) and Player B's unrelated rebound grab under the
     rim ~87 frames later (~frame 307) -- since the up/down latch has no
     player-identity awareness and no defense against an intervening
     rebound/second-touch, only a 90-frame timeout that this case fell
     just inside of. The reported "make" at frame 328 was independently
     wrong too: by that frame Player B is already dribbling away from the
     hoop, nowhere near the net, so the descent-detection also matched
     something spurious -- most likely the unvalidated proportional
     rescaling of `NET_ZONE_DEPTH`/`MARGIN_X` used for this test.
     Net effect: the hoop-position bug is still real (a wrong hoop
     location is still wrong), but the specific "miss→make, proof the fix
     worked" claim was false, and there's a SEPARATE, more serious gap --
     the up/down state machine can silently merge two different players'
     actions into one fabricated event, with only a timeout (not a real
     safeguard) preventing it. `scripts/_robustness_stage4_wrapper.py`
     (recalibrates hoop position per clip, scales `HOOP_NEAR`/`NET_ZONE_*`
     by hoop-diagonal ratio) is a rough approximation for testing only,
     not validated, and should not be trusted for outcome calls without
     frame-by-frame confirmation -- learned that the hard way here.
     A real fix needs per-video-derived thresholds (same pattern as
     `POSSESS_RATIO`) AND a rebound/second-touch guard on the up/down
     latch, not just position recalibration.
  2. Found on the close-up clip: a real shot (visually confirmed a miss
     by inspecting the frames directly — ball arcs well left of the rim)
     was followed by a normal recovery/dribble a player clearly holding
     the ball again by ~1.5s later — but Stage 4 possession never
     detected the ball being re-held, leaving the event "unresolved"
     entirely rather than misclassified. Not diagnosed further, but the
     leading hypothesis is `POSSESS_RATIO`'s distance gate (tuned against
     our own clip's camera-to-player distance) not transferring to a much
     closer camera framing.
  Net conclusion: the CV pipeline as it stands is validated for one
  camera setup, not proven portable. Before trusting it on new footage,
  hoop calibration and possession-distance thresholds need to become
  per-video (derived from the footage itself) rather than hardcoded
  constants tuned once. Test artifacts kept in `data/output/robustness_test/`
  for reference.

## Open Questions / Not Yet Decided
- Target demographic (e.g. children vs. adult beginners) — flagged by
  supervisors as something to narrow down, not yet decided
- Video data source: originally planned to start from online 1v1 clips
  (faster to gather, no need to book court time) before optionally recording
  original footage later — revisit given the compressed timeline

## Fallback Plan — Supervisor's Alternative Direction (backup only, not the primary plan)
On July 31, supervisors (Danielle, Eyal, Diar) proposed a different, lower-risk
direction due to time constraints. This is **not** the plan being pursued right
now, but is kept here in case the original approach above hits a wall close to
the deadline:
- Record original 1v1 footage instead of using online clips
- Reuse/adapt an existing computer vision pipeline (built by Diar for squash
  and cricket) rather than building the CV pipeline from scratch
- Generate multiple data representations from footage: frame images, JSON,
  2D and 3D player representations, per-frame pose skeletons
- Evaluate how LLM feedback quality changes depending on which representation
  is fed in (JSON vs. pose vs. 2D vs. 3D), as a comparative study
- Get a basketball coach to independently give feedback on the same clips,
  then compare coach feedback vs. LLM feedback as a validation/evaluation
  section in the final report


## Project structure
AI BASKETBALL_COACH

arrie

१० 16

> data

PROBLEMS

OU

models

basketball_ball_hoop_yolov8.pt

pose_landmarker_heavy.task

tracknetv2_basketball_best.pth.tar

OPS C:\Users\

wasb_basketball_best.pth.tar

yolo11m-pose.pt

yolo11m.pt

>_pycache_

> dataset_prep

_robustness_stage4_wrapper.py

U

extract_dribble_clips.py

extract_shot_clips.py

U

Ilm_poc.py

U

stage1_identity_lock.py

stage1_track_test.py

stage2@ball_track.py

M

stage2_wasb_track.py

stage3_direction_smooth.py

stage3_pose_compare.py

stage3_pose_production.py

U

stage4_events.py

M

stage4_possession.py

stage4_render_preview.py

> third_party

◆gitignore

PROJECT,md
