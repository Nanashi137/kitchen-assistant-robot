from typing import Optional

import py_trees

from .base import BaseNode
from .black_board import Blackboard


class CheckNotAmbiguousNode(BaseNode):
    """
    Condition node that checks if the question is not ambiguous.

    Reads:
      - is_ambiguous (bool)

    Return:
      - SUCCESS if is_ambiguous is False (question is clear)
      - FAILURE if is_ambiguous is True (question is ambiguous)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
    ):
        super().__init__(name=name, bb=bb)

        # register bb keys used by this node
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.READ
        )

    def update(self) -> py_trees.common.Status:
        is_ambiguous: Optional[bool] = getattr(self._client, "is_ambiguous", None)

        # If ambiguous flag is not set, treat as ambiguous (safe default)
        if is_ambiguous is None:
            return py_trees.common.Status.FAILURE

        # Return SUCCESS if not ambiguous, FAILURE if ambiguous
        if is_ambiguous:
            return py_trees.common.Status.FAILURE
        else:
            return py_trees.common.Status.SUCCESS
