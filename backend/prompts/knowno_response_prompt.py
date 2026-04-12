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

- Restate the Query briefly, then list ALL items from Viable Objects and ask the user to pick one.
- Each item in Viable Objects contains both the object and its action/role. Use the object names when asking the clarification question.
- If Ambiguity Type is "Safety", add a short safety hint.
- If Ambiguity Type is "Common Sense", add a short practical hint.
- **Already resolved:** If Conversation History shows the user **already chose** one of the objects listed in Viable Objects (or clearly confirmed a single option), **do not** ask again. Give one short line that you will proceed with that choice (use the Query + history; no new questions).

Examples:
- Query: "Use a knife to cut the tomato"
  Viable Objects: [{{"chef knife": "tool to cut tomato"}}, {{"paring knife": "tool to cut tomato"}}, {{"butter knife": "tool to cut tomato"}}]
  → "To cut the tomato, I see a chef knife, a paring knife, and a butter knife. Which one should I use?"

- Query: "Use the sponge to wipe the counter"
  Viable Objects: [{{"clean sponge": "tool to wipe counter"}}, {{"dirty sponge": "tool to wipe counter"}}]
  Ambiguity Type: Safety
  → "I see a clean sponge and a dirty sponge. Which one should I use to wipe the counter? The clean sponge would be safer."

## STRICT RULES
0. Use Conversation History to understand context — especially if the user is answering a previous clarification question.
1. Output ONLY the final response — no reasoning, no labels, no JSON.
2. The response MUST reflect the actual Query. Do NOT hallucinate actions or objects not in the Query.
3. If the user has **not** yet picked among Viable Objects: list ALL of them and ask which to use. If they **have** picked (per history and Query), confirm and proceed — **do not** repeat the same list-and-choose question.
4. Keep it concise: 1-2 sentences max.
5. Respond in English.
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