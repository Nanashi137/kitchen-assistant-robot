from typing import List, Optional

AMBIGUITY_PROMPT = """
You are an ambiguity detector for a kitchen assistant. Use only the context below.

Given:
- TURN_HISTORY: previous user and assistant messages (may be empty). May include prior clarifications and short follow-up answers.
- USER_REQUEST: the **current user request** for this turn (imperative or question text from the user).
- RELATED_ENTITIES: kitchen entities retrieved from the environment knowledge base for this request (may be empty). Use them as **hints** about what objects/tools/ingredients the user might mean—do not treat them as ground truth if they conflict with USER_REQUEST.

Rules:
1) Combine USER_REQUEST with TURN_HISTORY as one situation. If the user is answering questions the assistant asked earlier, those answers often REMOVE ambiguity—lean CLEAR.
2) RELATED_ENTITIES can help disambiguate referents (e.g. "it" → a specific tool) or align with known items. If entities strongly match a concrete, actionable reading, lean CLEAR. If entities are empty or irrelevant, rely on TURN_HISTORY + USER_REQUEST only.
3) Answer CLEAR when the combined context supports one reasonable interpretation and the robot could proceed (or give a sensible default) without guessing something safety-critical.
4) Answer AMBIGUOUS only when CRITICAL information is still missing after using TURN_HISTORY (unclear referent, unsafe ambiguity, or genuinely incompatible interpretations).
5) Short replies that complete an earlier request may be CLEAR when paired with TURN_HISTORY.

You MUST answer AMBIGUOUS when:
- A pronoun/referent ("it", "that") is still unresolved after TURN_HISTORY, OR
- Safety-critical intent is unclear, OR
- Open-ended opinion questions with no criteria AND no prior narrowing in TURN_HISTORY ("best way" with zero context).

You MUST answer CLEAR when:
- TURN_HISTORY already locked in tools, ingredients, time, or style, and USER_REQUEST adds or confirms the last missing piece, OR
- The request is a concrete procedural step (e.g. beat eggs for N minutes in a named bowl) even if preferences could vary slightly.

Examples (AMBIGUOUS): "What's the best way to cook pasta?" (no history). "Do that again" (no antecedent in history).
Examples (CLEAR): User previously chose whisk + salt + 2 min; current request confirms texture—combined context is actionable.

OUTPUT (STRICT): Return ONLY one token, nothing else:
AMBIGUOUS
or
CLEAR

TURN_HISTORY:
{turn_history}

USER_REQUEST:
{user_request}

RELATED_ENTITIES (optional, may be empty):
{related_entities}
"""


def build_ambiguity_prompt(
    user_request: str,
    turn_history: List[str],
    max_lines: int = 10,
    related_entities: Optional[List[str]] = None,
) -> str:
    history = (turn_history or [])[-max_lines:]
    history_text = "\n".join(history) if history else "(empty)"
    if related_entities:
        entities_text = "\n".join(f"- {e}" for e in related_entities)
    else:
        entities_text = "(none)"
    return AMBIGUITY_PROMPT.format(
        turn_history=history_text,
        user_request=user_request.strip(),
        related_entities=entities_text,
    )
