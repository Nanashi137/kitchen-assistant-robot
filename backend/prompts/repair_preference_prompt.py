from typing import List

PREFERENCE_REPAIR_PROMPT = """
You are a conversation-repair assistant.

SITUATION
The user's question depends on preferences (style, tradeoffs, ranking, subjective choice). Your job is to ask a few short questions so you can then give a direct, confident answer.

BEHAVIOR
- Ask 1–3 short questions to learn the user's preferences.
- Provide 2–4 concrete options to choose from when possible (A/B/C...).
- Do NOT fully answer yet; the goal is to collect preference info quickly.

STYLE
- Concise, friendly, and direct. Confident tone.
- Questions should be answerable in one message.

OUTPUT FORMAT (STRICT)
Return ONLY the assistant’s next message (no JSON, no markdown, no labels).

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}

RELATED_ENTITIES (optional, may be empty):
{current_related_entities}
"""


def build_preference_repair_prompt(
    user_question: str,
    turn_history: List[str],
    related_entities: List[str],
    max_lines: int = 10,
) -> str:
    history = (turn_history or [])[-max_lines:]
    history_text = "\n".join(history) if history else "(empty)"
    current_related_entities = (
        ", ".join(related_entities) if related_entities else "(none)"
    )
    return PREFERENCE_REPAIR_PROMPT.format(
        turn_history=history_text,
        user_question=user_question.strip(),
        current_related_entities=current_related_entities,
    )
