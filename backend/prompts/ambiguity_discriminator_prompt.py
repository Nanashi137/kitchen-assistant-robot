from typing import List

AMBIGUITY_DISCRIMINATOR_PROMPT = """
You are a classifier. Classify the user's ambiguity into exactly ONE type. Use this priority: Safety > Common sense > Preference.

Definitions (apply the FIRST that fits):

1) Safety: the question could involve harm, illegal activity, medical/legal risk, or policy-sensitive advice. If there is any reasonable chance of this, choose Safety.

2) Common sense: the question is unclear due to missing factual details—which object ("it", "this"), which step, what quantity/time/unit, or unclear referent. The answer would be a single factual procedure once those details are known. NOT about taste or "best" or "recommend".

3) Preference: the question depends on the user's taste, choice, or subjective criteria. Choose Preference when the question includes or implies:
   - "best" / "best way" / "good way" / "how should I" / "what do you recommend"
   - style, doneness, seasoning level, type of cuisine
   - ranking, comparison, or opinion without fixed criteria
   - "how do I make it" / "how do I cook this" without specifying what outcome they want
Examples that MUST be Preference: "What's the best way to cook pasta?", "How should I season this?", "What do you recommend for dinner?", "How do I make it taste good?"

OUTPUT (STRICT): Return exactly one token, nothing else—no punctuation, no explanation:
Safety
OR
Common sense
OR
Preference

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}

Already tried types (avoid repeating if possible; still obey Safety > Common sense > Preference):
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
