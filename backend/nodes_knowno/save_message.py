"""
Save user message and assistant message to the database.
On error, assistant content is "Error during generation".
"""

from typing import Optional

import py_trees
from logger import file_logger
from utils.db import insert_message

from .base import BaseNode
from .black_board import Blackboard


class SaveMessageNode(BaseNode):
    """
    Inserts the current user message and assistant reply into the message table.

    Reads:
      - conversation_id
      - user_question
      - answer
      - is_ambiguous
      - bot_trace (from blackboard)
    """

    def __init__(self, name: str, bb: Blackboard):
        super().__init__(name=name, bb=bb)

        self._client.register_key(
            key="conversation_id", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="user_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.READ)
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="bot_trace", access=py_trees.common.Access.READ)

    def update(self) -> py_trees.common.Status:
        try:
            conversation_id: Optional[str] = getattr(
                self._client, "conversation_id", None
            )
            if not conversation_id or not str(conversation_id).strip():
                file_logger.warning(
                    "SaveMessageNode: conversation_id missing, skip save"
                )
                return py_trees.common.Status.SUCCESS

            user_question = getattr(self._client, "user_question", None) or ""
            answer = getattr(self._client, "answer", None)
            is_ambiguous = getattr(self._client, "is_ambiguous", None)
            bot_trace = self.bb.get_bot_trace()

            content = (
                answer.strip() if answer and str(answer).strip() else None
            ) or "Error during generation"
            ambiguous = bool(is_ambiguous)

            insert_message(
                conversation_id=str(conversation_id).strip(),
                role="user",
                content=user_question.strip() or "(empty)",
            )
            trace_for_db = list(bot_trace) if bot_trace else []
            insert_message(
                conversation_id=str(conversation_id).strip(),
                role="assistant",
                content=content,
                ambiguous=ambiguous,
                bot_trace=trace_for_db,
            )
            file_logger.info(
                f"SaveMessageNode: saved user + assistant for conversation {conversation_id}"
            )
            return py_trees.common.Status.SUCCESS
        except Exception as e:
            file_logger.error(f"SaveMessageNode error: {type(e).__name__}: {e}")
            return py_trees.common.Status.FAILURE
