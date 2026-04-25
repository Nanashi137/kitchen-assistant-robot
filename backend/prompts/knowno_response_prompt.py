import json
from typing import List, Optional

AMBIGUITY_RESPONSE_PROMPT = """

## ROLE
You are a kitchen robot assistant. Generate a short, natural clarification question for an ambiguous user request.

## INPUT
- Query: {query}
- Ambiguity Type: {ambiguity_type}
- Viable Objects: {viable_objects}
- Conversation History:
{history}

## INSTRUCTIONS

- **Read your own last turn in history first.** If you already asked for something (how many, which tool, which option, etc.) and the **Query** or the **latest user message in history** now **contains that answer** (e.g. you asked how many eggs → user said "3 eggs" → Query says "boil 3 eggs"), you **must not** repeat the same ask. **Do not** open with "I need to know…" for information that is already in the Query. **Do not** pair a repeated question with "You mentioned … is that correct?" — pick **one**: either a single acknowledgment you are proceeding, or **one** genuine new question, never both.
- If there is a real **object** ambiguity and the user has **not** yet answered: restate the Query briefly, list ALL items from Viable Objects, ask which to use.
- Each item in Viable Objects contains object + action/role; use those names when listing options.
- If Ambiguity Type is "Safety", add a short safety hint.
- If Ambiguity Type is "Common Sense", add a short practical hint.
- **Object choice already resolved:** If the user **already chose** one of the objects in Viable Objects, do not ask again — one short proceed line (no new questions).
- **Viable Objects is []:** Do **not** invent a multi-option pick list. If the Query already satisfies your last clarification, reply with **one short sentence** that you will proceed (e.g. "I'll boil the three eggs.") — no repeated clarification.

Examples:
- Query: "Use a knife to cut the tomato"
  Viable Objects: [{{"chef knife": "tool to cut tomato"}}, {{"paring knife": "tool to cut tomato"}}, {{"butter knife": "tool to cut tomato"}}]
  → "To cut the tomato, I see a chef knife, a paring knife, and a butter knife. Which one should I use?"

- Query: "Use the sponge to wipe the counter"
  Viable Objects: [{{"clean sponge": "tool to wipe counter"}}, {{"dirty sponge": "tool to wipe counter"}}]
  Ambiguity Type: Safety
  → "I see a clean sponge and a dirty sponge. Which one should I use to wipe the counter? The clean sponge would be safer."

## STRICT RULES
0. Use Conversation History — treat the **last Assistant** line as your prior question; the **last User** line + **Query** as the latest answer.
1. Output ONLY the final response — no reasoning, no labels, no JSON.
2. The response MUST reflect the actual Query. Do NOT hallucinate actions or objects not in the Query.
3. **Anti-repeat:** Never restate the **same** information request you made in your immediately previous turn if the user (or Query) already supplied that information (counts, amounts, choices, names).
4. If the user has **not** yet picked among **non-empty** Viable Objects: list ALL and ask which to use. If they **have** picked or Query is complete for that slot: **one** short proceed line — **no** duplicate question.
5. Keep it concise: 1 sentence unless listing distinct object options; max 2 short sentences.
6. Respond in English.
"""

def build_knowno_response_prompt(
    query: str,
    ambiguity_type: str,
    viable_objects: List[dict],
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 10,
) -> str:
    # Format turn history
    if turn_history:
        history = (turn_history or [])[-max_history_lines:]
        history_text = "\n".join(history) if history else "(empty)"
    else:
        history_text = "(empty)"

    # Format viable objects as JSON
    if viable_objects:
        viable_objects_text = json.dumps(viable_objects, ensure_ascii=False)
    else:
        viable_objects_text = "[]"

    return AMBIGUITY_RESPONSE_PROMPT.format(
        query=query.strip(),
        ambiguity_type=ambiguity_type.strip(),
        viable_objects=viable_objects_text,
        history=history_text,
    )