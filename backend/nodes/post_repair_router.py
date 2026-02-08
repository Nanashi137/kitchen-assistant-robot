"""
Post-repair router: after ambiguous repair, either await user (preference) or clear state (safety/common sense).
"""

from typing import Optional

import py_trees
from logger import file_logger

from .base import BaseNode
from .black_board import Blackboard

DEFAULT_MAX_PREFERENCE_TURNS = 3
PREFERENCE_LIMIT_MESSAGE = (
    "I've asked a few questions to narrow things down but couldn't get there. "
    "Please ask again with a bit more detail about what you prefer."
)


class PostRepairRouterNode(BaseNode):
    """
    Runs after AmbiguousRepair. Routes by current_ambiguous_type:

    - Preference and under turn limit: set awaiting_user_response=True, increment
      preference_turn_count; runner keeps state and re-ticks after user responds.
    - Preference at limit: clear ambiguous state, reset preference_turn_count,
      set a fallback answer; runner clears state after showing.
    - Safety / Common sense: clear ambiguous state; runner clears state after showing.

    Reads:
      - current_ambiguous_type
      - preference_turn_count
      - max_preference_turns
      - answer
    Writes:
      - awaiting_user_response
      - preference_turn_count
      - used_ambiguous_types, current_ambiguous_type (cleared when not awaiting)
      - answer (overridden only when preference at limit)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        max_preference_turns: int = DEFAULT_MAX_PREFERENCE_TURNS,
    ):
        super().__init__(name=name, bb=bb)
        self._max_preference_turns = max_preference_turns

        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="preference_turn_count", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="max_preference_turns", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="awaiting_user_response", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="preference_turn_count", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="used_ambiguous_types", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def _get_preference_turn_count(self) -> int:
        try:
            return int(getattr(self._client, "preference_turn_count", 0) or 0)
        except KeyError:
            return 0

    def _get_max_preference_turns(self) -> int:
        try:
            n = int(getattr(self._client, "max_preference_turns", 0) or 0)
            return n if n > 0 else self._max_preference_turns
        except KeyError:
            return self._max_preference_turns

    def _clear_ambiguous_state(self) -> None:
        try:
            self._client.used_ambiguous_types = []
        except KeyError:
            pass
        self._client.current_ambiguous_type = None
        self._client.preference_turn_count = 0

    def update(self) -> py_trees.common.Status:
        try:
            ambiguous_type: Optional[str] = (
                getattr(self._client, "current_ambiguous_type", None) or ""
            )
            t = ambiguous_type.strip().lower()
            count = self._get_preference_turn_count()
            max_turns = self._get_max_preference_turns()

            if "preference" in t:
                if count < max_turns:
                    self._client.awaiting_user_response = True
                    self._client.preference_turn_count = count + 1
                    file_logger.info(
                        f"PostRepairRouter: Preference under limit ({count + 1}/{max_turns}), awaiting user response"
                    )
                    return py_trees.common.Status.SUCCESS
                else:
                    self._client.awaiting_user_response = False
                    self._client.answer = PREFERENCE_LIMIT_MESSAGE
                    self._clear_ambiguous_state()
                    file_logger.info(
                        f"PostRepairRouter: Preference at limit ({max_turns}), cleared state"
                    )
                    return py_trees.common.Status.SUCCESS
            else:
                # Safety or Common sense: repairable without user; clear state
                self._client.awaiting_user_response = False
                self._clear_ambiguous_state()
                file_logger.info("PostRepairRouter: Safety/Common sense, cleared state")
                return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"PostRepairRouter error: {error_msg}")
            self._client.awaiting_user_response = False
            self._clear_ambiguous_state()
            return py_trees.common.Status.FAILURE
