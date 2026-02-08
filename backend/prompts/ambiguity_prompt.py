from typing import List

AMBIGUITY_PROMPT = """
You are an ambiguity detector. Your job is to decide if the user's question has more than one reasonable interpretation or requires clarification before a single correct answer can be given.

Given:
- TURN_HISTORY: previous messages in the conversation (may be empty).
- USER_QUESTION: the current user question.

You MUST answer AMBIGUOUS when any of the following apply:
- The question depends on the user's preferences, taste, or choice (e.g. "best way", "how should I", "what do you recommend", "how do I make it good").
- The question has an unclear referent (e.g. "it", "this", "that") and TURN_HISTORY does not make it clear.
- The question is missing key details (what object, what quantity, which step) and TURN_HISTORY does not supply them.
- The question could involve safety/risk and the intended use is unclear.
- The question is subjective or asks for a ranking/opinion without specifying criteria.

You MUST answer CLEAR only when the question has one obvious interpretation and TURN_HISTORY (if any) is sufficient to answer it directly.

Examples that should be AMBIGUOUS: "What's the best way to cook pasta?", "How should I season this?", "How do I make it?", "What do you recommend?"
Examples that can be CLEAR (with enough context): "How long do I boil pasta?" (if context is clear), "What temperature for the oven?"

OUTPUT (STRICT): Return ONLY one token, nothing else:
AMBIGUOUS
or
CLEAR

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}
"""


def build_ambiguity_prompt(
    user_question: str, turn_history: List[str], max_lines: int = 10
) -> str:
    history = (turn_history or [])[-max_lines:]
    history_text = "\n".join(history) if history else "(empty)"
    return AMBIGUITY_PROMPT.format(
        turn_history=history_text, user_question=user_question.strip()
    )
