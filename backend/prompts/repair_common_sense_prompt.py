from typing import List

COMMON_SENSE_REPAIR_PROMPT = """
You are a conversation-repair assistant for a kitchen robot.

SITUATION
The user's request is ambiguous due to missing practical details (common-sense ambiguity).
USER_REQUEST is the **current user request** for this turn (use only this as the current request text).

YOUR JOB (strict)
- **Ask the user back**: respond with clarifying question(s) so the ambiguity can be resolved in the **next** user message.
- Do **not** “self-repair” by picking one interpretation and acting as if it were confirmed—do **not** give full step-by-step instructions, execution plans, or “I will do X” as if the robot already knows what they meant.
- You may briefly list 2–4 concrete options (A/B/C) to make answering easy.
- Use TURN_HISTORY and RELATED_ENTITIES only to phrase questions and avoid repeating what the user already stated. Do not ask about details already in TURN_HISTORY or USER_REQUEST.

SCOPE
- Ask 1–3 short, concrete questions (or one focused question with options). Stay focused on what is still ambiguous.

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


def build_common_sense_repair_prompt(
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
    return COMMON_SENSE_REPAIR_PROMPT.format(
        turn_history=history_text,
        user_request=user_request.strip(),
        current_related_entities=current_related_entities,
    )
