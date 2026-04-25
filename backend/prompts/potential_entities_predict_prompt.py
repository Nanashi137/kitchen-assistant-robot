from typing import List, Optional

POTENTIAL_ENTITIES_PROMPT = """
You extract **potential_entities**: physical kitchen objects/tools/ingredients that still need grounding for the **current** turn.

You MUST use **both** CONVERSATION_HISTORY and CURRENT_USER_REQUEST. If you ignore history, the robot will repeat the same clarification — that is a failure.

## MANDATORY RULES (apply before anything else)

**R1 — Disambiguation already answered (OR / which-one questions)**  
If CONVERSATION_HISTORY shows the assistant asked the user to choose **between alternatives** (e.g. "whisk or fork", "A or B", "which one", "use X or Y") and the user's **latest** message (or CURRENT_USER_REQUEST) **selects one option**:
- You MUST **NOT** include any **unchosen** alternative as a potential entity (e.g. user chose whisk → never output "fork").
- You MUST **NOT** output both alternatives together for that same choice.
- If the chosen option alone fully satisfies what was being asked, output **{{"potential_entities": []}}** — do not re-list the chosen tool unless a **new** unresolved sub-choice still exists.

**R2 — Short reply = answer to last bot question**  
If CURRENT_USER_REQUEST is a short fragment (one or two words like "whisk", "scramble", "the blue one") and history shows it **answers** the assistant's last question, extract entities **only** for what is **still open after** that answer — often **none**.

**R3 — Standalone request already specifies the tool/object**  
If CURRENT_USER_REQUEST clearly names the instrument or object (e.g. "scramble eggs using a whisk"), do not add competing tools the user did not ask about.

**R4 — Empty list is valid**  
When nothing is left to disambiguate or retrieve for this step, return **{{"potential_entities": []}}**.

**R5 — Parameter questions (how many, how much, how long, …)**  
If CONVERSATION_HISTORY shows the assistant asked for a **number, quantity, amount, duration, size, or similar detail** (not "which physical object") and CURRENT_USER_REQUEST **answers it** (e.g. "3 eggs", "two cups", "5 minutes"), return **{{"potential_entities": []}}** unless a **new** unresolved **object** choice still exists. Do not keep predicting entities that only existed to justify re-asking that detail.

## General rules (after R1–R5)

1. Prefer entities **explicitly** in CURRENT_USER_REQUEST only if they still need retrieval and are not fully settled by history.
2. Short, lowercase, singular where natural; no duplicates; at most {topk} items.
3. Output **valid JSON only** — no markdown, no commentary.

Output format:
{{
  "potential_entities": ["entity1", "entity2"]
}}

## Examples

Example A — user chose whisk; fork must not appear
CONVERSATION_HISTORY:
User: can you cook the eggs
Assistant: scrambled, fried, or boiled?
User: scramble
Assistant: whisk or fork?
CURRENT_USER_REQUEST:
whisk
Output:
{{
  "potential_entities": []
}}

Example B — user chose kettle after pot/kettle question
CONVERSATION_HISTORY:
User: cook the eggs
Assistant: fry, scramble, or boil?
User: boil
Assistant: kettle or pot?
CURRENT_USER_REQUEST:
kettle
Output:
{{
  "potential_entities": []
}}

Example D — user answered how many eggs (R5)
CONVERSATION_HISTORY:
User: can you cook the eggs
Assistant: scrambled, fried, or boiled?
User: boiled
Assistant: how many eggs would you like to cook?
CURRENT_USER_REQUEST:
3 eggs
Output:
{{
  "potential_entities": []
}}

Example C — still need container after method chosen (hypothetical)
CONVERSATION_HISTORY:
User: scramble the eggs
Assistant: which bowl?
CURRENT_USER_REQUEST:
use the small glass bowl
Output:
{{
  "potential_entities": ["small glass bowl"]
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
    max_history_lines: int = 24,
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
