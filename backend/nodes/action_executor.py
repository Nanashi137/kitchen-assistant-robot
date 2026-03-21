"""
Pluggable action execution for the clear (non-ambiguous) path.

Default: a plain text message (no LLM). Replace with a Gazebo-backed executor later
by passing a custom callable to PerformActionNode / build_tree.

Contract: callable(blackboard_client) -> str
  - blackboard_client is py_trees.blackboard.Client (same as BaseNode._client).
  - Return the assistant message shown to the user.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from logger import file_logger


@runtime_checkable
class ActionExecutor(Protocol):
    """Implement __call__(client) -> str to plug in robot / simulation."""

    def __call__(self, client: object) -> str: ...


class PlainMessageActionExecutor:
    """
    Default executor: formats a fixed template with the user's standalone request.
    No LLM, no external robot — suitable until Gazebo or hardware is wired in.

    Template placeholders:
      {user_request} — standalone_question text (rewritten user message).

    Override template via env ACTION_MESSAGE_TEMPLATE or constructor.
    """

    def __init__(self, template: str | None = None) -> None:
        self.template = template or os.getenv(
            "ACTION_MESSAGE_TEMPLATE",
            "I performed the {user_request}",
        )

    def __call__(self, client: object) -> str:
        sq = getattr(client, "standalone_question", None) or ""
        text = str(sq).strip()
        try:
            return self.template.format(user_request=text)
        except KeyError as e:
            file_logger.warning(
                f"PlainMessageActionExecutor: template missing key {e}, using fallback"
            )
            return f"I performed the {text}"


def default_action_executor() -> PlainMessageActionExecutor:
    """Factory used by build_tree when no executor is passed."""
    return PlainMessageActionExecutor()
