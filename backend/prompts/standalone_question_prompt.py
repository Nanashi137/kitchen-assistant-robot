from typing import List, Optional

STANDALONE_QUESTION_PROMPT = """
You are a helpful assistant that rewrites a user's message into a SINGLE standalone question.

Given:
- USER_QUESTION: the current user question/message
- TURN_HISTORY: previous conversation turns (user + assistant). This may include the referenced subject, constraints, preferences, and clarifications.

Goal:
Rewrite USER_QUESTION into a standalone question that can be understood with ZERO additional context.

Rules:
1. Use TURN_HISTORY only to resolve references and fill in missing details (e.g., pronouns like "it/that/they", ellipsis, "the second one", "same as before").
2. Preserve the user's intent, scope, and constraints from the conversation (dietary restrictions, serving size, tools available, time limits, etc.).
3. Do NOT add new assumptions or new constraints that were not stated. If a crucial detail is missing and cannot be inferred from TURN_HISTORY, keep it generic (do not invent specifics).
4. Keep it concise. Output exactly ONE question.
5. Do NOT answer the question. Do NOT include analysis, notes, or multiple options.

Few-shot examples:

Example 1
TURN_HISTORY:
User: I have chicken thighs and broccoli. I want something spicy.
Assistant: Do you want a stir-fry or an oven bake?
User: Stir-fry.
USER_QUESTION: How long should I cook it?
STANDALONE: How long should I stir-fry chicken thighs and broccoli to make a spicy dish?

Example 2
TURN_HISTORY:
User: I’m baking cookies. I only have baking soda, not baking powder.
Assistant: What type of cookies are you making?
User: Chocolate chip.
USER_QUESTION: Can I swap it 1:1?
STANDALONE: Can I substitute baking soda for baking powder in chocolate chip cookies at a 1:1 ratio?

Now do the task.

TURN_HISTORY:
{turn_history}

USER_QUESTION:
{user_question}

Output:
Return only the standalone question text.
""".strip()


def build_standalone_question_prompt(
    user_question: str,
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 12,
) -> str:
    # Format turn history
    if turn_history:
        history = (turn_history or [])[-max_history_lines:]
        history_text = "\n".join(history).strip() if history else "(empty)"
    else:
        history_text = "(empty)"

    return STANDALONE_QUESTION_PROMPT.format(
        turn_history=history_text,
        user_question=user_question.strip(),
    )
