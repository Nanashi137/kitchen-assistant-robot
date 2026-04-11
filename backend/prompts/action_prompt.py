from typing import List

AMBIG_CLASSIFY_PROMPT = """
## ROLE
You are an ambiguity detection system for a kitchen robot.
You will receive a user message containing the current query context. Follow the steps below strictly.

## TASK

### Step 0 — Check Conversation History

If the Conversation History shows that the robot previously asked the user to clarify which object to use, AND the Current Query contains a direct answer (e.g., naming one or more specific objects, or confirming with "yes"), treat that answer as the user's final selection.
- Identify ALL selected objects from the user's answer.
- If every selected object matches a candidate in Top K → return **Unambiguous** with those objects as viable_objects.
- Do NOT re-evaluate ambiguity on the user's confirmed selection — it is resolved.
- Only proceed to Step 1 if no such prior clarification exchange is found.

### Step 1 — Group candidates by Entity

For each entity in Entity-action, identify which Top K Candidates are semantically related to it (i.e., could be a substitute or alternative).

- A candidate is "related" if it belongs to the same general category as the entity (e.g., "dark chocolate tablet" is related to "chocolate tablet"; "plastic bowl" is related to "ceramic bowl").
- Ignore candidates that are completely unrelated to any entity.
- Skip non-physical items (locations, quantities, abstract concepts) from Entity-action — they have no candidates.

### Step 2 — Determine Viable Candidates (per Entity)

For each (entity → related candidate) pair, a candidate is **Viable** if it can substitute the entity for the given action/role in Entity-action safely, hygienically, effectively, and appropriately in a kitchen context.

A candidate is **NOT viable** if it:
- Poses safety or hygiene risks (e.g., dirty item when clean needed, metal in microwave)
- Contradicts a **specific descriptor** in the entity (color, material, type, cleanliness, function)
  - "clean sponge" ≠ "dirty sponge" | "bread knife" ≠ "butter knife" | "oat milk" ≠ "cow milk"
  - "dark chocolate tablet" ≠ "milk chocolate tablet" | "ceramic bowl" ≠ "plastic bowl"
  - **Rule**: Specific descriptors express clear user intent — substitution is NOT allowed.
- Is significantly suboptimal or inappropriate for the task

### Step 3 — Classify (per Entity, then overall)

Evaluate each entity independently:

| Viable candidates for this entity | Entity-level result |
|----------------------------------|---------------------|
| 0 viable                         | Unambiguous (no match found) |
| 1 viable                         | Unambiguous (clear match) |
| 2+ viable                        | **Ambiguous** (needs clarification) |

**Overall classification rule:**
- If **ANY** entity is Ambiguous → overall result is **Ambiguous**
- If ALL entities are Unambiguous → overall result is **Unambiguous**

**viable_objects in output:** collect ALL viable candidates from every entity that contributes to ambiguity, as a list of objects with their inferred action/role.

### Step 4 — Classify Type (only if overall Ambiguous)

Inspect the ambiguous viable candidates and choose one label (priority: Safety > Common Sense > Preferences):

- **Safety**: Wrong substitution could cause danger (e.g., metal in microwave, flammable near heat). Robot should NOT ask — choose the safe option.
- **Common Sense**: Resolved by everyday practical knowledge (e.g., wooden spoon for hot soup, not plastic). Robot is generally not expected to ask.
- **Preferences**: Equally valid options; choice is purely subjective (e.g., which chocolate type, which mug color). Robot MUST ask the user.

## EXAMPLES

**Example 1: Unambiguous — specific material descriptor**
- Query: "Use the ceramic bowl to melt the chocolate"
- Entity-action: {{"ceramic bowl": "container for melting chocolate"}}
- Top K: ["plastic bowl", "metal bowl", "ceramic bowl"]
  - "ceramic bowl": exact match → 1 viable → Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": [{{"ceramic bowl": "container for melting chocolate"}}]}}

**Example 2: Unambiguous — hygiene constraint**
- Query: "Use the clean sponge to wipe down the counter"
- Entity-action: {{"clean sponge": "tool for wiping down counter"}}
- Top K: ["clean sponge", "dirty sponge"]
  - "clean sponge": dirty sponge ≠ clean sponge (hygiene) → only clean sponge viable → 1 viable → Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": [{{"clean sponge": "tool for wiping down counter"}}]}}

**Example 3: Ambiguous — Common Sense**
- Query: "Put the leftovers in the bowl"
- Entity-action: {{"bowl": "container for leftovers"}}
- Top K: ["large mixing bowl", "tiny dipping bowl"]
  - "bowl" (generic): large mixing bowl viable, tiny dipping bowl viable → 2 viable → Ambiguous

{{"classification": "Ambiguous", "ambiguity_type": "Common Sense", "viable_objects": [{{"large mixing bowl": "container for leftovers"}}, {{"tiny dipping bowl": "container for leftovers"}}]}}

**Example 4: Ambiguous — Preferences**
- Query: "Bring me the mug"
- Entity-action: {{"mug": "object to bring to user"}}
- Top K: ["blue mug", "red mug"]
  - "mug" (generic): both mugs viable → 2 viable → Ambiguous

{{"classification": "Ambiguous", "ambiguity_type": "Preferences", "viable_objects": [{{"blue mug": "object to bring to user"}}, {{"red mug": "object to bring to user"}}]}}

**Example 5: Unambiguous — specific type blocks all candidates (multi-entity)**
- Query: "Retrieve the dark chocolate tablet and ceramic bowl"
- Entity-action: {{"dark chocolate tablet": "ingredient to retrieve", "ceramic bowl": "container to retrieve"}}
- Top K: ["milk chocolate tablet", "almond milk chocolate tablet", "plastic bowl", "metal bowl"]
  - "dark chocolate tablet": milk/almond ≠ dark → 0 viable → Unambiguous
  - "ceramic bowl": plastic/metal ≠ ceramic → 0 viable → Unambiguous
  - Overall: Unambiguous

{{"classification": "Unambiguous", "ambiguity_type": "None", "viable_objects": []}}

**Example 6: Ambiguous — generic descriptor allows substitution (multi-entity)**
- Query: "Retrieve the chocolate tablet and ceramic bowl"
- Entity-action: {{"chocolate tablet": "ingredient to retrieve", "ceramic bowl": "container to retrieve"}}
- Top K: ["dark chocolate tablet", "milk chocolate tablet", "almond milk chocolate tablet", "plastic bowl", "metal bowl"]
  - "chocolate tablet" (generic, no qualifier): dark/milk/almond chocolate all viable → 3 viable → **Ambiguous**
  - "ceramic bowl": plastic/metal ≠ ceramic → 0 viable → Unambiguous
  - Overall: **Ambiguous** (due to "chocolate tablet")

{{"classification": "Ambiguous", "ambiguity_type": "Preferences", "viable_objects": [{{"dark chocolate tablet": "ingredient to retrieve"}}, {{"milk chocolate tablet": "ingredient to retrieve"}}, {{"almond milk chocolate tablet": "ingredient to retrieve"}}]}}

**Example 7: Ambiguous — location ignored, generic object triggers ambiguity**
- Query: "Get the chocolate tablet and cream cheese from the refrigerator"
- Entity-action: {{"chocolate tablet": "ingredient to get", "cream cheese": "ingredient to get", "refrigerator": "source location"}}
- Top K: ["dark chocolate tablet", "milk chocolate tablet", "fresh cream cheese", "expired cream cheese"]
  - "refrigerator": location, not a physical kitchen object to be selected from Top K → skip
  - "chocolate tablet" (generic): dark/milk both viable → 2 viable → **Ambiguous**
  - "cream cheese": fresh ≠ expired (hygiene) → only fresh viable → 1 viable → Unambiguous
  - Overall: **Ambiguous** (due to "chocolate tablet")

{{"classification": "Ambiguous", "ambiguity_type": "Preferences", "viable_objects": [{{"dark chocolate tablet": "ingredient to get"}}, {{"milk chocolate tablet": "ingredient to get"}}]}}

## OUTPUT ##
Return ONLY a JSON object with no extra text.

{{
  "classification": "Ambiguous | Unambiguous",
  "ambiguity_type": "None | Safety | Common Sense | Preferences",
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

def build_entity_actions_prompt(
    user_request: str,
    related_entities: List[str],
) -> str:
    normalized_entities = [
        str(entity).strip()
        for entity in related_entities
        if str(entity).strip()
    ]

    return ENTITY_ACTIONS_PROMPT.format(
        user_request=user_request.strip(),
        related_entities=normalized_entities,
    )