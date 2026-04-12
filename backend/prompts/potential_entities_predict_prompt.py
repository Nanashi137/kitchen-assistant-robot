from typing import List, Optional

POTENTIAL_ENTITIES_PROMPT = """
You are given:
1. a standalone user request
2. recent conversation history

Your task is to extract a ranked list of potential physical entities, objects, tools, containers, appliances, ingredients, or manipulable items that may be needed to understand or execute the current request.

Use the conversation history to understand which entities were already identified, clarified, selected, or resolved in earlier turns.
Do NOT repeat previously resolved entities unless they are still necessary for the current request and remain unresolved at this step.

Rules:
1. Prioritize entities that are explicitly mentioned in the current request.
2. After that, include highly likely implied entities only if they are strongly necessary or commonly required to complete the current request.
3. Use conversation history to avoid repeating entities that were already resolved, selected, or confirmed in earlier turns.
4. Only include entities that are still relevant for the current step of the interaction.
5. Prefer concrete nouns over abstract concepts, actions, or attributes.
6. Do not include verbs, adjectives, or generic task words unless they clearly refer to a physical entity.
7. Keep entity names short, lowercase, and singular where natural.
8. Remove duplicates.
9. Return at most {topk} entities.
10. If fewer than {topk} relevant entities exist, return a shorter list.
11. Output must be valid JSON only.
12. Do not include markdown fences or any extra text.

Guidance on using history:
- If an entity was already chosen by the user, do not extract it again unless the current request introduces a new unresolved choice around it.
- If the current request is only answering a clarification question, extract only the remaining unresolved entities for the current step.
- If everything needed for the current request is already resolved, return an empty list.

Output format:
{{
  "potential_entities": ["entity1", "entity2"]
}}

Example 1:
Conversation History:
User: cook the eggs
Bot: fry, scramble, or boil?
Current Request:
boil
Output:
{{
  "potential_entities": ["pot", "kettle"]
}}

Example 2:
Conversation History:
User: cook the eggs
Bot: fry, scramble, or boil?
User: boil
Bot: use kettle or pot?
Current Request:
kettle
Output:
{{
  "potential_entities": []
}}

Example 3:
Conversation History:
User: put the leftovers in a bowl
Bot: use the large mixing bowl or the tiny dipping bowl?
Current Request:
large mixing bowl
Output:
{{
  "potential_entities": []
}}

CONVERSATION_HISTORY:
{turn_history}

CURRENT_USER_REQUEST:
{user_request}
"""

def build_potential_entities_prompt(
    user_request: str,
    topk: int = 5,
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 10,
) -> str:
    if turn_history:
        history = (turn_history or [])[-max_history_lines:]
        history_text = "\n".join(history).strip() if history else "(empty)"
    else:
        history_text = "(empty)"

    return POTENTIAL_ENTITIES_PROMPT.format(
        user_request=user_request.strip(),
        topk=topk,
        turn_history=history_text,
    )