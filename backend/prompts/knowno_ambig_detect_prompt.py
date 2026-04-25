import json
from typing import Dict, List

DETECT_AMBIGUOUS_PROMPT = """
You are an ambiguity detector for a kitchen robot.

Inputs:
- Conversation History: prior user/assistant turns; may contain earlier clarifications.
- Current Query: the request for this turn.
- Viable Objects: a list of already-filtered viable object-role dictionaries. This may be null, empty, or contain multiple candidates.

Task:
Decide whether the Current Query is ambiguous.

Rules:
1. Judge ambiguity based on what is still unresolved for the current request.
2. If history contains an earlier clarification that has already been resolved, do not treat that past ambiguity as still active. Focus on whether the Current Query still leaves an important execution choice unresolved.
3. If Viable Objects contains multiple equally plausible candidates for the same still-unresolved choice, return Ambiguous.
4. If Viable Objects contains exactly one relevant candidate, return Unambiguous.
5. If Viable Objects is null or empty, rely on Conversation History and Current Query:
   - return Unambiguous if the request is specific enough for execution
   - return Ambiguous if an important execution choice is still missing
6. Do not mark the request Ambiguous just because the query is short, high-level, or viable_objects is null.
7. brief_reason must be a very short logging phrase based on the current unresolved state.

## OUTPUT FORMAT

Return exactly one JSON object:

{{
  "classification": "Ambiguous | Unambiguous",
  "brief_reason": "one short phrase for logging"
}}

---USER---
Conversation History:
{history}

Current Query: {query}

Viable Objects (JSON):
{viable_objects}
"""

def build_knowno_ambig_detect_prompt(
    query: str,
    viable_objects: List[Dict[str, str]],
    turn_history: List[str],
    max_history_lines: int = 16,
) -> str:
    history_lines = list(turn_history or [])[-max_history_lines:]
    history_text = "\n".join(history_lines) if history_lines else "(empty)"
    viable_text = json.dumps(viable_objects or [], ensure_ascii=False)

    return DETECT_AMBIGUOUS_PROMPT.format(
        history=history_text,
        query=(query or "").strip(),
        viable_objects=viable_text,
    )
