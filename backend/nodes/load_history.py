"""
Load previous top-k messages for a conversation and set turn_history.
"""

from typing import Optional

import py_trees
from logger import file_logger
from utils.db import load_messages, messages_to_turn_history

from .base import BaseNode
from .black_board import Blackboard


class LoadHistoryNode(BaseNode):
    """
    Loads the last k messages for the conversation and sets turn_history.

    Reads:
      - conversation_id
    Writes:
      - turn_history (from DB messages)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        top_k: int = 20,
    ):
        super().__init__(name=name, bb=bb)
        self._top_k = top_k

        self._client.register_key(
            key="conversation_id", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            conversation_id: Optional[str] = getattr(
                self._client, "conversation_id", None
            )
            if not conversation_id or not str(conversation_id).strip():
                return py_trees.common.Status.SUCCESS

            messages = load_messages(
                conversation_id=str(conversation_id).strip(),
                top_k=self._top_k,
            )
            turn_history = messages_to_turn_history(messages)
            self._client.turn_history = turn_history
            file_logger.info(
                f"LoadHistoryNode: loaded {len(turn_history)} turns for conversation {conversation_id}"
            )
            return py_trees.common.Status.SUCCESS
        except Exception as e:
            file_logger.error(f"LoadHistoryNode error: {type(e).__name__}: {e}")
            return py_trees.common.Status.FAILURE
