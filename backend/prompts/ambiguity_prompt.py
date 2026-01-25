from typing import List

AMBIGUITY_PROMPT = """
You are an ambiguity detector.
    
Given:
- TURN_HISTORY: a list of strings like "User: ...", "Bot: ..."
- USER_QUESTION: the current user question

Decide if USER_QUESTION is ambiguous *given TURN_HISTORY*.

OUTPUT (STRICT):
Return ONLY one token:
- AMBIGUOUS
or
- CLEAR

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
