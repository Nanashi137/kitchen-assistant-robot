"""Human-readable bot_trace lines (stored as step strings; no load/save noise)."""

from typing import Optional

# Indent so sub-steps align under "Branching: ..." in monospace UI
_SUB = "  "

# Fallback when request text is empty
_TRACE_ACTION_PHRASE = "i performed the request, what's next"


def branching_resolving() -> str:
    return "Branching: Resolving ambiguous:"


def retrieving_entities_context() -> str:
    """Shared vector search before ambiguity routing (not yet on a branch)."""
    return "Retrieving related environment entities (for routing)"


def branching_acting() -> str:
    return "Branching: Acting"


def searching_entities_line(n: int) -> str:
    return (
        f"{_SUB}Searching related environment entities: retrieved {n} entities"
    )


def determine_type_line(canonical_type: str) -> str:
    """Map Safety / Common sense / Preference → safety|common_sense|preference."""
    t = (canonical_type or "").strip().lower()
    if "safety" in t:
        token = "safety"
    elif "preference" in t:
        token = "preference"
    else:
        token = "common_sense"
    return f"{_SUB}Determine ambiguous type: {token}"


def constructing_response_line() -> str:
    """Fixed short trace line (full reply is in message content, not trace)."""
    return f"{_SUB}Constructing response to solve ambiguity"


def performing_request_line(user_request: Optional[str] = None) -> str:
    """
    One line: user's request as stated (no textwrap — avoids broken alignment in UI).
    """
    text = (user_request or "").strip() or _TRACE_ACTION_PHRASE
    return f"{_SUB}Performing request: {text}"


def performing_request_error_line() -> str:
    return f"{_SUB}Performing request: error"
