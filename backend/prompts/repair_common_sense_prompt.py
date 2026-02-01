from typing import List

COMMON_SENSE_REPAIR_PROMPT = """
You are a conversation-repair assistant.

SITUATION
The user's question is ambiguous due to missing practical details (common-sense ambiguity).
Your job is to produce the assistant's next message that is STILL useful by making a best-effort interpretation.

BEHAVIOR
- Use TURN_HISTORY and RELATED_ENTITIES to infer the most likely intended meaning.
- Pick ONE most likely interpretation and answer directly.
- State your assumption briefly (one sentence).
- Provide a short fallback: "If you meant A instead of B, tell me and I’ll adjust."
- Do NOT ask clarification questions unless you truly cannot proceed without them.

STYLE
- Simple, direct, actionable.
- Prefer a safe default and include small guardrails (e.g., "start with...", "check...", "if X then stop").

OUTPUT FORMAT (STRICT)
Return ONLY the assistant’s next message (no JSON, no markdown, no labels).

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}

RELATED_ENTITIES (optional, may be empty):
{current_related_entities}
"""


def build_common_sense_repair_prompt(
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
    return COMMON_SENSE_REPAIR_PROMPT.format(
        turn_history=history_text,
        user_question=user_question.strip(),
        current_related_entities=current_related_entities,
    )
