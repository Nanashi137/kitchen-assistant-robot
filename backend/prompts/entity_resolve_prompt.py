import json
from typing import List, Optional

ENTITY_RESOLVE_PROMPT = """
You are a **strict filter** for **predicted_entities**. Wrong output causes the robot to **repeat the same question** — treat errors as unacceptable.

## INPUT
- **Standalone request:** consolidated current task line.
- **Conversation history:** prior user and assistant turns (read the **last** assistant question and the **latest** user answer carefully).
- **Predicted entities:** strings from upstream prediction (may still wrongly include rejected alternatives).

## MANDATORY RULES (non-negotiable)

**M1 — OR-choice resolution**  
If history shows the assistant asked the user to pick **one of several named options** (tools, containers, types, etc.) and the user’s reply **commits to one** (by name, short label, or obvious match):
- **Remove every other option from that same choice** from your output (e.g. asked "whisk or fork", user said "whisk" → you MUST NOT keep "fork").
- If nothing from **predicted_entities** is still needed after that commitment, return **{{"potential_entities": []}}**.

**M2 — Match standalone request**  
If the standalone request **names** a specific object/tool, drop predicted entities that **contradict** or **duplicate** an already settled choice (e.g. standalone says "using a whisk" → remove "fork" if present).

**M3 — Substring / synonym OK for matching**  
User may say "whisk" while predicted list has "balloon whisk" — treat as **resolved** for the whisk-vs-fork style question: keep at most whisk-like entries if still needed for **further** grounding; **never** keep the fork line when user rejected fork.

**M4 — Output hygiene**  
- Only output names that appear in **predicted_entities** (case-insensitive match; echo **exact spelling** from predicted_entities).
- Preserve **order** of predicted_entities for kept items.
- Valid JSON only, no markdown.

**M5 — Parameter / quantity already answered**  
If the assistant asked for **how many, how much, how long**, etc., and the **standalone request** already encodes the answer (e.g. "boil 3 eggs"), drop any predicted entities that only served an **already-answered** detail. Prefer **{{"potential_entities": []}}** when nothing object-related is still open.

## TASK (after M1–M5)
Return **potential_entities**: the subset of predicted_entities that are **still unresolved** for disambiguation/retrieval **given** history + standalone request.

Output format:
{{
  "potential_entities": ["entity1", "entity2"]
}}

## Example

History: Assistant asked "whisk or fork?"; User: "whisk".
Predicted entities: ["whisk", "fork", "egg"]
Standalone: "Scramble the eggs using a whisk."
Correct output (fork and eggs must be removed; all gone):
{{
  "potential_entities": []
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
    max_history_lines: int = 24,
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
