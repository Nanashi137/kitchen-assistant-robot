import json
from typing import Dict, List

AMBIG_CLASSIFY_PROMPT = """
## ROLE
You are an ambiguity detection system for a kitchen robot.
You will receive a user message containing the current query context. Follow the steps below strictly.

## TASK

### Step 0 — Check Conversation History (objects AND non-object details)

**0a — Object / OR-choice clarification**  
If history shows the assistant asked the user to **choose a specific object or tool** among options, AND the Current Query answers that (names the object, short label, or "yes" to the last option), treat it as resolved → **Unambiguous** with appropriate `viable_objects` (dicts from Entity-action for chosen keys only). Do not re-run ambiguity on that settled choice.

**0b — Quantity, count, amount, duration, or other parameter**  
If history shows the assistant asked for a **detail that is not object-disambiguation** — e.g. **how many**, how much, what size, how long, doneness, temperature — and the **Current Query supplies that detail** (e.g. "3 eggs", "two minutes", "medium rare"):
- Treat that clarification slot as **resolved**.
- Return **Unambiguous** with `"ambiguity_type": "None"` and `viable_objects` built only from Entity-action keys that are still **actually ambiguous** for physical selection. If nothing object-related is ambiguous anymore, use **`[]`**.
- **Do not** stay **Ambiguous** just because the task still mentions generic words like "egg" — the count/detail question was already answered.

Only proceed to Step 1 if neither 0a nor 0b applies.

### Step 1 — Find the most relevant objects from Entity-action

Entity-action contains candidate objects as keys and their possible action/role as values.

For the Current Query, identify which objects in Entity-action are the most semantically relevant and could realistically satisfy the user's request.

- Prioritize objects explicitly mentioned in the Current Query.
- Then consider highly relevant substitutes or alternatives from Entity-action if they fit the same intent.
- Ignore objects in Entity-action that are unrelated to the Current Query.
- Skip non-physical items (locations, quantities, abstract concepts) from Entity-action — they are not selectable objects.

### Step 2 — Determine Viable Objects

An object from Entity-action is **Viable** if it can fulfill the user's request safely, hygienically, effectively, and appropriately in a kitchen context.

An object is **NOT viable** if it:
- Poses safety or hygiene risks (e.g., dirty item when clean needed, metal in microwave)
- Contradicts a **specific descriptor** in the Current Query (color, material, type, cleanliness, function)
  - "clean sponge" ≠ "dirty sponge" | "bread knife" ≠ "butter knife" | "oat milk" ≠ "cow milk"
  - "dark chocolate tablet" ≠ "milk chocolate tablet" | "ceramic bowl" ≠ "plastic bowl"
  - **Rule**: Specific descriptors express clear user intent — substitution is NOT allowed.
- Is significantly suboptimal or inappropriate for the task

### Step 3 — Classify

Evaluate the viable objects selected from Entity-action:

| Viable objects | Result |
|----------------|--------|
| 0 viable       | Unambiguous |
| 1 viable       | Unambiguous |
| 2+ viable      | **Ambiguous** |

If the result is **Unambiguous**, set `"ambiguity_type"` to `"None"`.

**viable_objects in output:** collect all viable objects that contribute to ambiguity, as a list of object-action dictionaries.

### Step 4 — Classify Type (only if Ambiguous)

Inspect the ambiguous viable objects and choose one label (priority: Safety > Common Sense > Preference):

- **Safety**: Wrong substitution could cause danger (e.g., metal in microwave, flammable near heat). Robot should NOT ask — choose the safe option.
- **Common Sense**: Resolved by everyday practical knowledge (e.g., large bowl for leftovers, not a tiny dipping bowl). Robot is generally not expected to ask.
- **Preference**: Equally valid options; choice is purely subjective (e.g., which chocolate type, which mug color). Robot MUST ask the user.

## EXAMPLES

**Example 1: Unambiguous — specific material descriptor**
- Query: "Use the ceramic bowl to melt the chocolate"
- Entity-action: {{"ceramic bowl": "container for melting chocolate", "plastic bowl": "container for melting chocolate", "metal bowl": "container for melting chocolate"}}
  - "ceramic bowl" is explicitly mentioned and matches exactly
  - plastic/metal contradict the specific material descriptor
  - 1 viable → Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": [{{"ceramic bowl": "container for melting chocolate"}}]}}

**Example 2: Unambiguous — hygiene constraint**
- Query: "Use the clean sponge to wipe down the counter"
- Entity-action: {{"clean sponge": "tool for wiping down counter", "dirty sponge": "tool for wiping down counter"}}
  - "clean sponge" is explicitly requested
  - "dirty sponge" is not viable due to hygiene
  - 1 viable → Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": [{{"clean sponge": "tool for wiping down counter"}}]}}

**Example 3: Ambiguous — Common Sense**
- Query: "Put the leftovers in the bowl"
- Entity-action: {{"large mixing bowl": "container for leftovers", "tiny dipping bowl": "container for leftovers", "plate": "surface for serving"}}
  - Both bowls are relevant to "bowl"
  - Both are viable candidates from Entity-action
  - 2 viable → Ambiguous

{{"classification": "Ambiguous", "ambiguity_type": "Common Sense", "viable_objects": [{{"large mixing bowl": "container for leftovers"}}, {{"tiny dipping bowl": "container for leftovers"}}]}}

**Example 4: Ambiguous — Preference**
- Query: "Bring me the mug"
- Entity-action: {{"blue mug": "object to bring to user", "red mug": "object to bring to user", "plate": "object to bring to user"}}
  - Both mugs are relevant and viable
  - The plate is unrelated to "mug"
  - 2 viable → Ambiguous

{{"classification": "Ambiguous", "ambiguity_type": "Preference", "viable_objects": [{{"blue mug": "object to bring to user"}}, {{"red mug": "object to bring to user"}}]}}

**Example 5: Unambiguous — no relevant alternative**
- Query: "Retrieve the dark chocolate tablet and ceramic bowl"
- Entity-action: {{"dark chocolate tablet": "ingredient to retrieve", "ceramic bowl": "container to retrieve", "milk chocolate tablet": "ingredient to retrieve", "plastic bowl": "container to retrieve"}}
  - "dark chocolate tablet" and "ceramic bowl" match the specific descriptors
  - "milk chocolate tablet" and "plastic bowl" contradict the request
  - 1 viable per requested object → Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": [{{"dark chocolate tablet": "ingredient to retrieve"}}, {{"ceramic bowl": "container to retrieve"}}]}}

**Example 6: Ambiguous — generic descriptor allows multiple matches**
- Query: "Retrieve the chocolate tablet"
- Entity-action: {{"dark chocolate tablet": "ingredient to retrieve", "milk chocolate tablet": "ingredient to retrieve", "almond milk chocolate tablet": "ingredient to retrieve", "ceramic bowl": "container to retrieve"}}
  - "chocolate tablet" is generic
  - all chocolate tablets are relevant and viable
  - the bowl is unrelated
  - 3 viable → Ambiguous

{{"classification": "Ambiguous", "ambiguity_type": "Preference", "viable_objects": [{{"dark chocolate tablet": "ingredient to retrieve"}}, {{"milk chocolate tablet": "ingredient to retrieve"}}, {{"almond milk chocolate tablet": "ingredient to retrieve"}}]}}

**Example 7: Ambiguous — location ignored, object resolved from Entity-action**
- Query: "Get the chocolate tablet and cream cheese from the refrigerator"
- Entity-action: {{"dark chocolate tablet": "ingredient to get", "milk chocolate tablet": "ingredient to get", "fresh cream cheese": "ingredient to get", "expired cream cheese": "ingredient to get", "refrigerator": "source location"}}
  - "refrigerator" is a location, not a selectable object
  - "chocolate tablet" is generic, so dark/milk are both viable
  - "cream cheese" allows fresh, but expired is not viable due to hygiene
  - overall ambiguous due to chocolate tablet

{{"classification": "Ambiguous", "ambiguity_type": "Preference", "viable_objects": [{{"dark chocolate tablet": "ingredient to get"}}, {{"milk chocolate tablet": "ingredient to get"}}]}}

**Example 8: Unambiguous — user answered "how many eggs"**
- Conversation: Assistant asked how many eggs to boil; user said "3 eggs".
- Current Query: "Boil 3 eggs" (or equivalent one line including the count).
- Entity-action may list pot, egg, etc. — **no** remaining object ambiguity from the count question; count is settled.

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": []}}

## OUTPUT ##
Return ONLY a JSON object with no extra text.
If the result is **Unambiguous**, set `"ambiguity_type"` to `"None"`.

{{
  "classification": "Ambiguous | Unambiguous",
  "ambiguity_type": "None | Safety | Common Sense | Preference",
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


def build_knowno_ambig_classify_prompt(
    query: str,
    entity_action: Dict[str, str],
    turn_history: List[str],
    max_history_lines: int = 16,
) -> str:
    history_lines = list(turn_history or [])[-max_history_lines:]
    history_text = "\n".join(history_lines) if history_lines else "(empty)"
    ea_text = json.dumps(entity_action or {}, ensure_ascii=False)
    return AMBIG_CLASSIFY_PROMPT.format(
        history=history_text,
        query=query.strip(),
        entity_action=ea_text,
    )