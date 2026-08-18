"""Generates coaching feedback from each of the four representations of a
flagged moment, using Gemma via Google AI Studio.

Core experimental-validity requirement (from PROJECT.md): the prompt
instructions and requested output format must be byte-for-byte identical
across all four representations - only the input data block changes. This
is enforced structurally, not just by convention: PROMPT_TEMPLATE is a
single string built once per moment, and the four calls differ only in the
{data_block} substitution. `_assert_prompts_share_identical_instructions`
verifies this at runtime rather than trusting it by inspection.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

import representations as R
from representations import Moment, build_all_representations, load_moment

load_dotenv()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GEMMA_MODEL = "gemma-4-31b-it"
GEMMA_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent"

DATA_BLOCK_START = "<<<DATA_START>>>"
DATA_BLOCK_END = "<<<DATA_END>>>"

# Input/output split (explicit per instruction):
# - IN the prompt: pose-derived representation data, plus shot outcome,
#   contested, and shot location - these stay in because there's no
#   ball-tracking data, so the LLM has no other way to know them.
# - NEVER in the prompt: move_type. The whole point is for the LLM to
#   infer what move happened from the pose data itself; telling it the
#   answer would make the "does the LLM correctly infer what happened"
#   metric meaningless. move_type is read only after generation, to score
#   the model's own "identified_move" output against it - see
#   check_move_type_match / generate_feedback_for_moment.
def get_outcome_context(form_row) -> dict:
    return {
        "outcome": str(form_row["what happened"]),
        "contested": str(form_row["was it contested"]),
        "shot_location": str(form_row["where the shot was taken from"]),
    }


# Fixed, identical across all four representations - only {attacker_id},
# {defender_id}, {outcome}, {contested}, {shot_location} (constant per
# moment, not per representation) and {data_block} (the one thing that's
# allowed to differ) are substituted.
PROMPT_TEMPLATE = """You are a basketball coach analysing a single tracked moment from a 1-vs-1 basketball clip, based on pose-tracking data of two players' movement.

Player {attacker_id} is the attacker (has the ball) in this moment. Player {defender_id} is the defender.

Known outcome of this moment (there is no ball-tracking data, so this is provided; everything else must come from the movement data below): result = {outcome}, contested = {contested}, shot location = {shot_location}.

Here is data describing the players' movement during this moment:

{DATA_BLOCK_START}
{data_block}
{DATA_BLOCK_END}

For reference, here is what each of these basketball techniques fundamentally is, in terms of body movement: a crossover is a quick lateral redirection of the body's direction of travel, executed by planting and pushing off one foot to move diagonally the other way while the torso continues facing forward rather than turning. A spin move is a full turn of the body, pivoting on one foot, that reverses the direction the torso faces while the player continues moving forward along a new path. A stepback is a backward shift of the body away from the direction it had just been moving, pushing off to create distance before settling into a stationary stance. A between-the-legs move is one hand reaching briefly downward and across the body into the space between the knees, after which the body continues moving in a new direction. A dribble, in the general sense, is ordinary sustained forward or lateral movement of the body, without a sharp redirection, a full rotation, a backward shift, or a downward reach across the body. Base your identification on the whole sequence of movement described below, not only its starting and ending position.

Based on this movement data (and the known outcome above), analyse the attacker's play, Player {attacker_id}. Your response must contain exactly:
1. Your best identification of the specific tactical move Player {attacker_id} used in this moment (a short phrase describing the footwork/ball-handling technique), based only on the movement data.
2. One positive observation - something Player {attacker_id} did well during this moment.
3. Exactly three alternative tactical moves Player {attacker_id} could have made instead, written in simple, beginner-friendly language a new player could understand.

Always refer to the players as "Player {attacker_id}" and "Player {defender_id}" - never use any other name or label for them. Do not include any section, heading, or commentary other than the three items above.

Respond with ONLY this JSON object, no other text:
{{
  "identified_move": "<short phrase>",
  "positive_observation": "<one sentence>",
  "alternative_moves": ["<move 1>", "<move 2>", "<move 3>"]
}}""".replace("{DATA_BLOCK_START}", DATA_BLOCK_START).replace("{DATA_BLOCK_END}", DATA_BLOCK_END)


def format_data_block(representation_name: str, payload) -> str:
    if representation_name == "nl_description":
        return payload  # already plain text
    return json.dumps(payload, separators=(",", ":"))


def build_prompt(attacker_id: int, defender_id: int, outcome_context: dict, data_block: str) -> str:
    return PROMPT_TEMPLATE.format(
        attacker_id=attacker_id,
        defender_id=defender_id,
        outcome=outcome_context["outcome"],
        contested=outcome_context["contested"],
        shot_location=outcome_context["shot_location"],
        data_block=data_block,
    )


def _assert_prompts_share_identical_instructions(prompts: dict[str, str]) -> None:
    """Hard runtime check (not just construction-by-convention) that the
    non-data portion of every prompt is byte-for-byte identical."""
    stripped = {}
    for name, prompt in prompts.items():
        before, _, rest = prompt.partition(DATA_BLOCK_START)
        _, _, after = rest.partition(DATA_BLOCK_END)
        stripped[name] = before + after
    values = list(stripped.values())
    if any(v != values[0] for v in values):
        raise AssertionError(
            f"Prompt instructions differ across representations: {list(stripped.keys())}"
        )


def _assert_move_type_not_in_data(prompts: dict[str, str], actual_move_type: str, actual_move_description: str) -> None:
    """Checks the held-out labels don't leak into the *representation
    data* specifically (the one thing that varies per moment/per call).

    Not the same check as originally built: the shared instructions now
    deliberately contain all 5 move_type terms (the glossary), so a
    blanket "term absent from the whole prompt" check would always fail
    and is no longer meaningful. What still matters is that the DATA
    block itself - built from pose numbers, never from the label - never
    happens to contain the literal word/sentence, so this checks only the
    data block, not the static shared instructions.

    The move_description check is inherently weaker than the move_type
    one: an exact-substring check on a whole sentence only catches a
    verbatim leak, not a rephrased partial one. Documented limitation,
    not solved further - the real defense is that data blocks are built
    purely from pose numbers (representations.py never reads move_type
    or move_description at all), so a leak would require a real bug.
    """
    for name, prompt in prompts.items():
        _, _, rest = prompt.partition(DATA_BLOCK_START)
        data_only, _, _ = rest.partition(DATA_BLOCK_END)
        assert actual_move_type not in data_only, (
            f"move_type leaked into the {name} representation DATA itself - this must never happen"
        )
        if actual_move_description and str(actual_move_description).strip():
            assert str(actual_move_description) not in data_only, (
                f"move_description leaked into the {name} representation DATA itself - this must never happen"
            )


def _retry_delay_sec(response: requests.Response, default: float = 5.0) -> float:
    """Google's 429 body includes the actual required wait in a RetryInfo
    detail (observed values: 10-25s) - use that instead of guessing, since a
    fixed short backoff (originally 2s/4s) is nowhere near long enough for
    this API's real per-minute quota window."""
    try:
        details = response.json()["error"]["details"]
        for d in details:
            if d.get("@type", "").endswith("RetryInfo"):
                return float(d["retryDelay"].rstrip("s")) + 1.0  # +1s safety buffer
    except (ValueError, KeyError, TypeError):
        pass
    return default


def call_gemma(prompt: str, max_retries: int = 3) -> str:
    last_error = None
    for attempt in range(max_retries + 1):
        response = requests.post(
            GEMMA_URL,
            headers={"x-goog-api-key": GOOGLE_API_KEY, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        if response.status_code == 200:
            break
        last_error = f"{response.status_code}: {response.text}"
        if attempt < max_retries:
            wait = _retry_delay_sec(response) if response.status_code == 429 else 3.0
            time.sleep(wait)
    else:
        raise RuntimeError(f"Gemma call failed after {max_retries + 1} attempts: {last_error}")

    data = response.json()
    parts = data["candidates"][0]["content"]["parts"]
    # gemma-4-31b-it returns reasoning as a separate part tagged thought:true -
    # only the non-thought part(s) are the actual answer.
    text_parts = [p["text"] for p in parts if not p.get("thought")]
    return "".join(text_parts).strip()


def parse_feedback(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    parsed = json.loads(text)
    required = {"identified_move", "positive_observation", "alternative_moves"}
    if not required.issubset(parsed):
        raise ValueError(f"Missing required keys in parsed feedback: {parsed}")
    if len(parsed["alternative_moves"]) != 3:
        raise ValueError(f"Expected exactly 3 alternative moves, got {len(parsed['alternative_moves'])}: {parsed}")
    return parsed


# Keyword heuristic for scoring the model's free-text `identified_move`
# against the form's move_type label. This is NOT a rigorous accuracy
# metric - it's a simple, transparent first pass (substring match), kept
# only as a cheap automated pre-check. The real accuracy signal is a
# manual/semantic review against move_description (move_type_match_manual,
# set separately after generation - see comparison_notes.md) - always
# report the raw identified_move text alongside so that review is
# possible, per PROJECT.md's "don't trust confidence signals blindly"
# principle.
#
# An LLM-as-judge second call (Gemma judging its own answer) was tried and
# then retired: it disagreed with careful manual reading on real cases
# (clip_062) without being more reliable - having the model grade itself
# isn't a shortcut around actually checking the answer. Removed from the
# active pipeline; the historical judge data and full reasoning for
# dropping it are kept in comparison_notes.md, not deleted from the record.
#
# move_type is now a comma-separated multi-term structured label (e.g.
# "crossover, between-the-legs") rather than one fixed 5-term vocabulary
# word, so this splits on commas and checks each term as a plain
# substring - a hardcoded synonym dict no longer fits the label format
# (new terms like "fast dribble", "hesitation", "layup drive" appear that
# weren't part of the original 5-term vocabulary).
def check_move_type_match(identified_move: str, actual_move_type: str) -> bool:
    terms = [t.strip().lower() for t in actual_move_type.split(",") if t.strip()]
    text = identified_move.lower()
    return any(term in text for term in terms)


@dataclass
class RepresentationResult:
    representation: str
    prompt: str
    raw_response: str
    parsed: dict | None
    error: str | None
    actual_move_type: str | None = None
    actual_move_description: str | None = None
    move_type_match_keyword: bool | None = None
    # Filled in by a separate manual/semantic review pass after generation,
    # not computed automatically - see comparison_notes.md for the review
    # methodology and the full 24-row (soon more) evaluation table.
    move_type_match_manual: bool | None = None
    move_type_match_manual_reason: str | None = None


def _require_move_description(form_row) -> str:
    desc = form_row.get("move_description")
    if desc is None or (isinstance(desc, float) and desc != desc) or not str(desc).strip():
        raise ValueError(
            f"move_description is blank for clip_id={form_row['clip_id']!r} - fill in "
            f"self_label_form.xlsx's move_description column before generating feedback for this clip. "
            f"(move_type stays as the secondary keyword-match signal; move_description is now the "
            f"primary semantic ground truth for the LLM-judge.)"
        )
    return str(desc).strip()


def generate_feedback_for_moment(clip_id: str) -> list[RepresentationResult]:
    form_row = R.get_form_row(clip_id)
    moment: Moment = load_moment(clip_id, form_row)
    reprs = build_all_representations(clip_id, form_row)
    outcome_context = get_outcome_context(form_row)
    actual_move_type = str(form_row["move_type"])  # held out - used only post-hoc, never in the prompt
    actual_move_description = _require_move_description(form_row)  # held out - same rule

    prompts = {
        name: build_prompt(
            moment.attacker_id, moment.defender_id, outcome_context, format_data_block(name, payload)
        )
        for name, payload in reprs.items()
    }
    _assert_prompts_share_identical_instructions(prompts)
    _assert_move_type_not_in_data(prompts, actual_move_type, actual_move_description)

    results = []
    for name, prompt in prompts.items():
        try:
            raw = call_gemma(prompt)
            parsed = parse_feedback(raw)
            kw_match = check_move_type_match(parsed["identified_move"], actual_move_type)
            results.append(RepresentationResult(
                name, prompt, raw, parsed, None,
                actual_move_type, actual_move_description, kw_match,
            ))
        except Exception as e:
            results.append(RepresentationResult(
                name, prompt, "", None, f"{type(e).__name__}: {e}",
                actual_move_type, actual_move_description,
            ))
    return results


if __name__ == "__main__":
    # Validate the full pipeline end-to-end on one moment before scaling,
    # per PROJECT.md's roadmap step 4 - now including the actual LLM call.
    clip_id = "clip_033"
    results = generate_feedback_for_moment(clip_id)

    for r in results:
        print(f"=== {r.representation} ===")
        if r.error:
            print(f"ERROR: {r.error}")
        else:
            print(json.dumps(r.parsed, indent=2))
            print(f"actual move_type (held out): {r.actual_move_type}")
            print(f"keyword match (secondary, automated): {r.move_type_match_keyword}")
            print("manual review pending - see comparison_notes.md")
        print()
