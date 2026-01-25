from typing import List, Optional

ANSWER_PROMPT = """
You are a helpful kitchen assistant. Your role is to answer user questions about kitchen-related topics using the provided related entities as external information.

Given:
- USER_QUESTION: the current user question
- RELATED_ENTITIES: a list of relevant kitchen entities (ingredients, tools, techniques, etc.) retrieved from the knowledge base
- TURN_HISTORY: previous conversation turns for context (optional)

Instructions:
1. Use the RELATED_ENTITIES as your primary source of information to answer the question
2. If the entities are relevant, incorporate them naturally into your answer
3. If the entities don't fully answer the question, use your general knowledge to provide a helpful response
4. Be concise, accurate, and helpful
5. If the question is about something not covered by the entities, acknowledge this and provide the best answer you can
6. Maintain conversational context from TURN_HISTORY if provided

Output:
Provide a clear, helpful answer to the user's question. Do not include any prefixes like "Answer:" or "Response:" - just provide the answer directly.

TURN_HISTORY:
{turn_history}

RELATED_ENTITIES:
{related_entities}

USER_QUESTION:
{user_question}
"""


def build_answer_prompt(
    user_question: str,
    related_entities: List[str],
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 10,
) -> str:
    # Format turn history
    if turn_history:
        history = (turn_history or [])[-max_history_lines:]
        history_text = "\n".join(history) if history else "(empty)"
    else:
        history_text = "(empty)"

    # Format related entities
    if related_entities:
        entities_text = "\n".join(f"- {entity}" for entity in related_entities)
    else:
        entities_text = "(no related entities found)"

    return ANSWER_PROMPT.format(
        turn_history=history_text,
        related_entities=entities_text,
        user_question=user_question.strip(),
    )
