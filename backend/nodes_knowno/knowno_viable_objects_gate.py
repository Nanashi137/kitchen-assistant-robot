from typing import Any, List, Optional

import py_trees

from .base import BaseNode
from .black_board import Blackboard


class KnownoViableObjectsAvailableNode(BaseNode):
    """
    Condition: SUCCESS when viable-based ambiguity detection should run.

    SUCCESS when viable extraction succeeded and there is at least one viable object.
    FAILURE otherwise (route to related-entities ambiguity detector).
    """

    def __init__(self, name: str, bb: Blackboard):
        super().__init__(name=name, bb=bb)
        self._client.register_key(
            key="viable_objects", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="knowno_viable_extraction_failed",
            access=py_trees.common.Access.READ,
        )

    def update(self) -> py_trees.common.Status:
        failed = bool(
            getattr(self._client, "knowno_viable_extraction_failed", False)
        )
        raw_vo = getattr(self._client, "viable_objects", None)
        viable: List[Any] = list(raw_vo) if isinstance(raw_vo, list) else []

        if failed or len(viable) == 0:
            self.bb.append_bot_trace_step(
                "Ambiguity route: no viable objects (use related-entities detect)",
                "ok",
            )
            return py_trees.common.Status.FAILURE

        self.bb.append_bot_trace_step(
            "Ambiguity route: viable objects present (use viable detect)",
            "ok",
        )
        return py_trees.common.Status.SUCCESS
