"""Drop predicted entities that lost an 'X or Y' choice in the last assistant turn."""

from __future__ import annotations

import re
from typing import List

_ASSIST_PREFIX = "assistant:"


def sanitize_or_choice_conflicts(
    predicted_entities: List[str],
    turn_history: List[str],
    standalone_request: str,
) -> List[str]:
    """
    If the last assistant message asked for a choice between two single-token options
    (e.g. 'whisk or fork') and the standalone request commits to one, remove the other
    from predicted_entities (case-insensitive).
    """
    if not predicted_entities or not turn_history:
        return list(predicted_entities)

    last_assistant = ""
    for line in reversed(turn_history):
        low = line.strip().lower()
        if low.startswith(_ASSIST_PREFIX):
            last_assistant = line.split(":", 1)[1].strip().lower()
            break

    if " or " not in last_assistant:
        return list(predicted_entities)

    sq = (standalone_request or "").lower()
    # e.g. "whisk or fork", "a whisk or a fork"
    pair_pat = re.compile(
        r"\b(?:a\s+)?([a-z][a-z0-9\-]{1,32})\s+or\s+(?:a\s+)?([a-z][a-z0-9\-]{1,32})\b",
        re.IGNORECASE,
    )
    pairs = pair_pat.findall(last_assistant)
    if not pairs:
        return list(predicted_entities)

    out = list(predicted_entities)
    for a, b in pairs:
        a, b = a.lower(), b.lower()
        a_pat = re.compile(rf"\b{re.escape(a)}\b")
        b_pat = re.compile(rf"\b{re.escape(b)}\b")
        a_in = bool(a_pat.search(sq))
        b_in = bool(b_pat.search(sq))
        if a_in and not b_in:
            out = [x for x in out if str(x).strip().lower() != b]
        elif b_in and not a_in:
            out = [x for x in out if str(x).strip().lower() != a]
    return out
