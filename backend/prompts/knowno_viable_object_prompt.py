import json
from typing import Dict, List


EXTRACT_VIABLE_OBJECTS_PROMPT = """
## ROLE
You are a viable object extraction system for a kitchen robot.

You will receive:
- Conversation History
- Current Query
- Entity-action JSON

Your job is to identify which objects from Entity-action are truly viable for the user's current request.

## TASK

### Step 0 — Check Conversation History for already resolved clarification

**0a — Object / OR-choice clarification**  
If the history shows the assistant previously asked the user to choose a specific object or tool among options, and the Current Query answers that choice directly (for example by naming one option, giving a short label, or saying "yes" to the latest offered option), then treat that object choice as resolved.

In that case:
- Keep only the chosen object(s) from Entity-action if they exist there.
- Do not reintroduce other alternatives that were already ruled out by the clarification.

**0b — Non-object clarification already resolved**  
If the history shows the assistant previously asked for a non-object detail such as quantity, amount, size, duration, doneness, or temperature, and the Current Query supplies that detail, treat that clarification as resolved.

Important:
- Do not treat this as object ambiguity.
- Only extract physical objects that are still relevant and viable for physical execution.

If neither 0a nor 0b applies, continue normally.

### Step 1 — Find relevant objects from Entity-action

Entity-action contains candidate objects as keys and their possible action/role as values.

For the Current Query:
- Prioritize objects explicitly mentioned in the Current Query.
- Then include highly relevant alternatives from Entity-action only if they could realistically satisfy the same request.
- Ignore unrelated objects.
- Ignore non-physical items such as locations, quantities, or abstract concepts.

### Step 2 — Determine whether each relevant object is viable

An object is **viable** if it can fulfill the user's request safely, hygienically, effectively, and appropriately in a kitchen context.

An object is **not viable** if it:
- creates safety or hygiene problems
- contradicts a specific descriptor in the Current Query
- is clearly inappropriate or significantly suboptimal for the task

Specific descriptors must be respected strictly.  
Examples:
- "clean sponge" does not allow "dirty sponge"
- "ceramic bowl" does not allow "plastic bowl"
- "dark chocolate tablet" does not allow "milk chocolate tablet"
- "bread knife" does not allow "butter knife"

### Step 3 — Output viable objects only

Return all viable physical objects from Entity-action as a list of object-action dictionaries.

Rules:
- Include only viable objects
- Include only physical selectable objects
- Exclude locations, quantities, and abstract items
- Preserve the original object names and actions from Entity-action
- If no viable object exists, return an empty list
- Return JSON only

## EXAMPLES

### Example 1
Current Query: "Use the ceramic bowl to melt the chocolate"  
Entity-action: {{"ceramic bowl": "container for melting chocolate", "plastic bowl": "container for melting chocolate", "metal bowl": "container for melting chocolate"}}

Output:
{{
  "viable_objects": [
    {{"ceramic bowl": "container for melting chocolate"}}
  ]
}}

### Example 2
Current Query: "Bring me the mug"  
Entity-action: {{"blue mug": "object to bring to user", "red mug": "object to bring to user", "plate": "object to bring to user"}}

Output:
{{
  "viable_objects": [
    {{"blue mug": "object to bring to user"}},
    {{"red mug": "object to bring to user"}}
  ]
}}

### Example 3
Current Query: "Get the chocolate tablet and cream cheese from the refrigerator"  
Entity-action: {{"dark chocolate tablet": "ingredient to get", "milk chocolate tablet": "ingredient to get", "fresh cream cheese": "ingredient to get", "expired cream cheese": "ingredient to get", "refrigerator": "source location"}}

Output:
{{
  "viable_objects": [
    {{"dark chocolate tablet": "ingredient to get"}},
    {{"milk chocolate tablet": "ingredient to get"}},
    {{"fresh cream cheese": "ingredient to get"}}
  ]
}}

## OUTPUT
Return ONLY a JSON object with no extra text.

{{
  "viable_objects": [
    {{"object1": "action1"}},
    {{"object2": "action2"}}
  ]
}}

---USER---
Conversation History:
{history}

Current Query: {query}
Entity-action JSON: {entity_action}
"""

def build_knowno_viable_object_prompt(
    query: str,
    entity_action: Dict[str, str],
    turn_history: List[str],
    max_history_lines: int = 16,
) -> str:
    history_lines = list(turn_history or [])[-max_history_lines:]
    history_text = "\n".join(history_lines) if history_lines else "(empty)"
    entity_action_text = json.dumps(entity_action or {}, ensure_ascii=False)

    return EXTRACT_VIABLE_OBJECTS_PROMPT.format(
        history=history_text,
        query=(query or "").strip(),
        entity_action=entity_action_text,
    )
