import json
from typing import Dict, List

DETECT_AMBIGUITY_TYPE_PROMPT = """
## ROLE
You are an ambiguity type classifier for a kitchen robot.

You will receive:
- Conversation History
- Current Query
- Viable Objects

Your job is only to determine the ambiguity type for the given viable objects.

Important:
- Do NOT decide whether the request is ambiguous or unambiguous.
- Assume this prompt is called only after ambiguity has already been detected separately.
- Focus only on assigning the most appropriate ambiguity type label.

## TASK

Given the Current Query, Conversation History, and Viable Objects, classify the ambiguity into exactly one of these types:

- **Safety**
- **Common Sense**
- **Preference**

### Type definitions

**Safety**
- Choosing the wrong object could cause danger, damage, contamination, or a serious safety issue.
- Example: metal vs ceramic for microwave use, clean vs dirty item for food handling.

**Common Sense**
- Multiple objects may technically work, but ordinary practical reasoning strongly favors one.
- Example: large bowl vs tiny bowl for leftovers.

**Preference**
- Multiple objects are all reasonable and the choice mainly depends on user taste, style, or subjective preference.
- Example: red mug vs blue mug.

### Priority rule

If more than one type seems possible, use this priority:

Safety > Common Sense > Preference

### Additional rules

- Use the Current Query and Conversation History to interpret intent.
- Respect any resolved context from history.
- Focus on why the remaining viable objects differ.
- Return exactly one label.
- Return JSON only.

## EXAMPLES

### Example 1
Current Query: "Bring me the mug"  
Viable Objects:
[
  {{"blue mug": "object to bring to user"}},
  {{"red mug": "object to bring to user"}}
]

Output:
{{
  "ambiguity_type": "Preference"
}}

### Example 2
Current Query: "Put the leftovers in the bowl"  
Viable Objects:
[
  {{"large mixing bowl": "container for leftovers"}},
  {{"tiny dipping bowl": "container for leftovers"}}
]

Output:
{{
  "ambiguity_type": "Common Sense"
}}

### Example 3
Current Query: "Use a bowl to heat this in the microwave"  
Viable Objects:
[
  {{"ceramic bowl": "container for microwave heating"}},
  {{"metal bowl": "container for microwave heating"}}
]

Output:
{{
  "ambiguity_type": "Safety"
}}

## OUTPUT
Return ONLY a JSON object with no extra text.

{{
  "ambiguity_type": "Safety | Common Sense | Preference"
}}

---USER---
Conversation History:
{history}

Current Query: {query}
Viable Objects:
{viable_objects}
"""

def build_knowno_ambig_type_prompt(
    query: str,
    viable_objects: List[Dict[str, str]],
    turn_history: List[str],
    max_history_lines: int = 16,
) -> str:
    history_lines = list(turn_history or [])[-max_history_lines:]
    history_text = "\n".join(history_lines) if history_lines else "(empty)"
    viable_objects_text = json.dumps(viable_objects or [], ensure_ascii=False)

    return DETECT_AMBIGUITY_TYPE_PROMPT.format(
        history=history_text,
        query=(query or "").strip(),
        viable_objects=viable_objects_text,
    )