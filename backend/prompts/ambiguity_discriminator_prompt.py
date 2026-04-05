from typing import List

AMBIGUITY_DISCRIMINATOR_PROMPT = """
You are a classifier for a kitchen assistant. Use only TURN_HISTORY and USER_REQUEST below. USER_REQUEST is the **current user request** for this turn. Classify the ambiguity into exactly ONE type. Priority: Safety > Common sense > Preference.

Types (use these exact labels):
Safety, Common sense, or Preference.

Definitions (apply the FIRST that fits):

1) Safety: the request could involve harm, illegal activity, medical/legal risk, or policy-sensitive advice. If there is any reasonable chance of this, choose Safety.

2) Common sense: missing factual details—which object ("it"), which step, quantity/time/unit, OR concrete procedural cooking steps (beat, mix, chop) with named items—even if technique could vary slightly. Recipe-style requests ("beat eggs until combined", "fry for 3 minutes") are Common sense unless they explicitly ask for recommendations or "best".

3) Preference: depends on taste, style choice, or open recommendations. Choose Preference when the user asks for the "best" way, open-ended seasoning/meal ideas, rankings, or subjective picks WITHOUT enough constraint in TURN_HISTORY+USER_REQUEST to pick defaults.
Do NOT choose Preference for: straightforward task steps the user already specified (e.g. beat N eggs in named bowl until combined); short answers that complete a prior clarification (merge context mentally).

Examples (Preference): "What's the best pasta recipe?", "What should I make for dinner?", "How do I make it taste amazing?" (no prior narrowing).
Examples (Common sense): "Beat two eggs in the small bowl until smooth", "Dice the onion fine", user follow-ups listing tools/times after one clarification round.

OUTPUT (STRICT): Return exactly one token, nothing else—no punctuation, no explanation:
Safety
OR
Common sense
OR
Preference

TURN_HISTORY:
{turn_history}

USER_REQUEST:
{user_request}

Already tried types (avoid repeating if possible; still obey Safety > Common sense > Preference):
{used_ambiguous_types}
"""


def build_ambiguity_discriminator_prompt(
    user_request: str,
    turn_history: List[str],
    max_lines: int = 10,
    used_ambiguous_types: List[str] = [],
) -> str:
    history = (turn_history or [])[-max_lines:]
    history_text = "\n".join(history) if history else "(empty)"
    return AMBIGUITY_DISCRIMINATOR_PROMPT.format(
        turn_history=history_text,
        user_request=user_request.strip(),
        used_ambiguous_types=", ".join(used_ambiguous_types),
    )
