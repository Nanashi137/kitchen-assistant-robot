from typing import List

AMBIGUITY_DISCRIMINATOR_PROMPT = """
You are a classifier. Classify the user's ambiguity into exactly ONE type, using this priority:
Safety > Common sense > Preference.

Definitions:
- Safety: ambiguity relates to potentially harmful/illegal/medical-risk actions or policy-sensitive guidance.
  If there is any reasonable chance it is Safety, choose Safety.
- Common sense: ambiguity is due to missing factual/semantic details needed to act correctly
  (which object, which step, what quantity/time/unit/parameter, unclear referent).
- Preference: ambiguity depends on the user's taste/choice (style, option, ranking, subjective criteria).

OUTPUT (STRICT): return only one token:
Safety
OR
Common sense
OR
Preference

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}


Already tried types (avoid if possible, but still obey priority Safety > Common sense > Preference):
{used_ambiguous_types}
"""


def build_ambiguity_discriminator_prompt(
    user_question: str,
    turn_history: List[str],
    max_lines: int = 10,
    used_ambiguous_types: List[str] = [],
) -> str:
    history = (turn_history or [])[-max_lines:]
    history_text = "\n".join(history) if history else "(empty)"
    return AMBIGUITY_DISCRIMINATOR_PROMPT.format(
        turn_history=history_text,
        user_question=user_question.strip(),
        used_ambiguous_types=", ".join(used_ambiguous_types),
    )
