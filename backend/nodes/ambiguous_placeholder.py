import py_trees
from logger import file_logger

from .base import BaseNode
from .black_board import Blackboard


class AmbiguousPlaceholderNode(BaseNode):
    """
    Placeholder node for handling ambiguous questions.

    Reads:
      - user_question
      - is_ambiguous
    Writes:
      - answer (str) - placeholder message

    Return:
      - SUCCESS (always returns success with placeholder message)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
    ):
        super().__init__(name=name, bb=bb)

        # register bb keys used by this node
        self._client.register_key(
            key="user_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def update(self) -> py_trees.common.Status:
        user_question = getattr(self._client, "user_question", None) or "the question"

        placeholder_message = (
            f"I need more information to answer your question about '{user_question}'. "
            "Could you please provide more details or clarify what you're looking for?"
        )

        self._client.answer = placeholder_message
        file_logger.info(
            f"AmbiguousPlaceholderNode: Generated placeholder response for ambiguous question"
        )

        return py_trees.common.Status.SUCCESS
