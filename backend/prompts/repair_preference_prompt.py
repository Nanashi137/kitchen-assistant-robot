from typing import List

PREFERENCE_REPAIR_PROMPT = """
You are a conversation-repair assistant for a kitchen robot.

SITUATION
The user's request may involve taste, style, or subjective preferences.
USER_REQUEST is the **current user request** for this turn (use only this as the current request text).

YOUR JOB (strict)
- **Ask the user back**: respond with clarifying question(s) so preferences can be pinned down in the **next** user message.
- Do **not** “self-repair” by picking defaults and giving a full recommendation or acting as if preferences are already known.
- Use TURN_HISTORY to avoid repeating questions the user already answered.

SCOPE
- Ask 1–3 short, concrete questions, or one focused question with clear options (A/B/C).
- If USER_REQUEST + TURN_HISTORY already fully specify preferences, you may ask a single confirmation question instead of new preference questions—but still do **not** give a long prescriptive answer.

STYLE
- Concise, friendly, direct.

OUTPUT FORMAT (STRICT)
Return ONLY the assistant’s next message (no JSON, no markdown, no labels).

TURN_HISTORY:
{turn_history}

USER_REQUEST:
{user_request}

RELATED_ENTITIES (optional, may be empty):
{current_related_entities}
"""


def build_preference_repair_prompt(
    user_request: str,
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
        user_request=user_request.strip(),
        current_related_entities=current_related_entities,
    )
