POTENTIAL_ENTITIES_PROMPT = """
You are given a standalone user request.

Your task is to extract a ranked list of potential physical entities, objects, tools, containers, appliances, ingredients, or manipulable items that may be needed to understand or execute the request.

Prioritize entities that are explicitly mentioned in the request.
After that, include highly likely implied entities only if they are strongly necessary or commonly required to complete the request.

Rules:
1. Rank explicit entities before implied entities.
2. Prefer concrete nouns over abstract concepts, actions, or attributes.
3. Do not include verbs, adjectives, or generic task words unless they clearly refer to a physical entity.
4. Only include entities relevant to handling the request.
5. Keep entity names short, lowercase, and singular where natural.
6. Remove duplicates.
7. Return at most {topk} entities.
8. If fewer than {topk} relevant entities exist, return a shorter list.
9. Output must be valid JSON only.
10. Do not include markdown fences or any extra text.

Output format:
{{
  "potential_entities": ["entity1", "entity2"]
}}

Example:
User request: "boil me 3 eggs"
Output:
{{
  "potential_entities": ["egg", "pot"]
}}

USER_REQUEST:
{user_request}
"""


def build_potential_entities_prompt(
    user_request: str,
    topk: int = 5,
) -> str:

    return POTENTIAL_ENTITIES_PROMPT.format(
        user_request=user_request.strip(),
        topk=topk,
    )
