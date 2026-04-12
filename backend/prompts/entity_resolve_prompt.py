import json
from typing import List, Optional

ENTITY_RESOLVE_PROMPT = """
You filter a list of **predicted entities** for a kitchen robot. Some items may already be **fully resolved** by the standalone request plus conversation history (user chose a specific tool, container, method, etc.).

## INPUT
- **Standalone request:** one consolidated line for what the user wants now.
- **Conversation history:** prior user and assistant turns.
- **Predicted entities:** candidate physical objects/tools/ingredients the pipeline may still need to ground in the database.

## TASK
Return only entities that are **still unresolved** — i.e. still needed for disambiguation, retrieval, or execution **given** the standalone request and history.

**Remove** an entity if:
- The user (or standalone request) already **committed** to a specific option among alternatives (e.g. chose "balloon whisk" → drop "flat whisk" if it was only the other choice).
- The entity is **no longer relevant** because the request + history settled that part of the task.
- The assistant already **confirmed** a single object and the user did not reopen that choice.

**Keep** an entity if:
- The standalone request or history still leaves that category **open** or **ambiguous**.
- The entity is still **required** for the next step and is not superseded by a prior choice.

## RULES
1. Output **only** names that refer to entries in **Predicted entities** (match **case-insensitively**; use the exact spelling from Predicted entities in your output).
2. Preserve the **relative order** of Predicted entities for those you keep.
3. If every predicted entity is resolved, return an empty list.
4. Output **valid JSON only**, no markdown fences or extra text.

Output format:
{{
  "potential_entities": ["entity1", "entity2"]
}}

---DATA---
Conversation history:
{turn_history}

Standalone request:
{standalone_request}

Predicted entities (JSON array):
{predicted_entities_json}
"""


def build_entity_resolve_prompt(
    standalone_request: str,
    predicted_entities: List[str],
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 16,
) -> str:
    if turn_history:
        lines = list(turn_history or [])[-max_history_lines:]
        history_text = "\n".join(lines).strip() if lines else "(empty)"
    else:
        history_text = "(empty)"

    normalized = [
        str(x).strip() for x in (predicted_entities or []) if str(x).strip()
    ]
    predicted_json = json.dumps(normalized, ensure_ascii=False)

    return ENTITY_RESOLVE_PROMPT.format(
        turn_history=history_text,
        standalone_request=standalone_request.strip(),
        predicted_entities_json=predicted_json,
    )
