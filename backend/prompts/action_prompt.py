from typing import List

ENTITY_ACTIONS_PROMPT = """
You are given:
1. a standalone user request
2. a list of related entities

Your task is to infer the most likely action, role, or expected use of each entity in the context of the user's request.

Instructions:
1. Return one short phrase for each entity.
2. The phrase must describe the most likely action, role, or intended use of that entity for handling the user's request.
3. Keep each phrase concise, specific, and grounded in the request.
4. Do not add information unrelated to the request.
5. If an entity is mentioned but its role is unclear, provide the most likely useful role based on the request context.
6. Use the entity names exactly as provided in the input list as JSON keys.
7. Output must be valid JSON only.
8. Do not include markdown fences or any extra text.
9. If the user request **commits to specific items** (names a particular tool, bowl, ingredient, etc.), **omit** JSON keys for other entities that are only **mutually exclusive alternatives** to an unchosen option (e.g. if the request says "balloon whisk", do not include "flat whisk" unless the request still needs both).

Example:
User request: "boil me 3 eggs"
Related entities: ["egg", "pot", "stove"]

Output:
{{
  "egg": "ingredient to boil",
  "pot": "container for boiling eggs",
  "stove": "heat source for boiling"
}}

USER_REQUEST:
{user_request}

RELATED_ENTITIES:
{related_entities}
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