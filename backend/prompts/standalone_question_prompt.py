from typing import List, Optional

STANDALONE_REQUEST_PROMPT = """
You rewrite the user's current message into ONE **standalone request**—a single clear instruction of what they want done (or what they need), using conversation context.

Given:
- USER_REQUEST: the user's current message (may be a fragment, short reply, or question)
- TURN_HISTORY: prior turns (user + assistant). Use only to resolve references and merge missing details.

Goal:
Produce **one line**: a **standalone request** that can be understood with **no other context**. This is **not** an answer and **not** a chat reply—only the consolidated request text downstream modules will use.

Form (important — avoid confusing the model):
- **Default to imperative / task-style**: e.g. "Take the whisk and small bowl from the cabinet", "Beat two eggs in the small bowl until combined", "Stir-fry chicken thighs and broccoli for 5 minutes for a spicy dish."
- **Do NOT force a question** unless the user is genuinely asking for information (e.g. "Can I substitute baking soda for baking powder in chocolate chip cookies at a 1:1 ratio?"). If they are giving commands or tasks, keep them as **requests/instructions**, not "How do I…?" unless that was their literal ask.
- If the user asked a real question, you may output it as a clear standalone sentence (still one line).

Rules:
1. Use TURN_HISTORY only to resolve "it/that/this", ellipsis, prior choices, and to merge short follow-ups into the full task.
2. If USER_REQUEST is a short answer to the assistant's last message, merge it with the ongoing task from earlier turns.
3. Preserve intent, constraints, and scope; do not invent details not supported by USER_REQUEST + TURN_HISTORY.
4. Keep it concise: exactly **one** line.
5. Do NOT answer the user. Do NOT add analysis, bullets, or multiple options.

Few-shot examples:

Example 1 (task → standalone request, not a question)
TURN_HISTORY:
User: I need eggs beaten for the cake.
Assistant: Which bowl should I use?
User: The small glass one.
USER_REQUEST: Use the small glass one.
STANDALONE: Beat eggs for the cake in the small glass bowl.

Example 2 (real question stays a question)
TURN_HISTORY:
User: I'm baking cookies. I only have baking soda, not baking powder.
Assistant: What type of cookies are you making?
User: Chocolate chip.
USER_REQUEST: Can I swap it 1:1?
STANDALONE: Can I substitute baking soda for baking powder in chocolate chip cookies at a 1:1 ratio?

Example 3 (imperative user message stays imperative)
TURN_HISTORY: (empty)
USER_REQUEST: Get the whisk from the drawer and the bowl from the cabinet.
STANDALONE: Get the whisk from the drawer and the bowl from the cabinet.

Now do the task.

TURN_HISTORY:
{turn_history}

USER_REQUEST:
{user_request}

Output:
Return only the standalone request text (one line, no quotes or labels).
""".strip()


def build_standalone_question_prompt(
    user_request: str,
    turn_history: Optional[List[str]] = None,
    max_history_lines: int = 12,
) -> str:
    """Build prompt for a single standalone **request** line (blackboard key remains ``standalone_question``)."""
    if turn_history:
        history = (turn_history or [])[-max_history_lines:]
        history_text = "\n".join(history).strip() if history else "(empty)"
    else:
        history_text = "(empty)"

    return STANDALONE_REQUEST_PROMPT.format(
        turn_history=history_text,
        user_request=user_request.strip(),
    )
