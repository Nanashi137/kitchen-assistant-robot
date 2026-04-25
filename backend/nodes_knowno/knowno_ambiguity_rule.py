from typing import Any, List, Optional

import py_trees

from .base import BaseNode
from .black_board import Blackboard


class KnownoAmbiguityRuleNode(BaseNode):
    """
    Rule-based ambiguity from viable object count (and extraction failure).

    Reads:
      - viable_objects
      - knowno_viable_extraction_failed
    Writes:
      - is_ambiguous
      - current_ambiguous_type (cleared when unambiguous)
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
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        failed = bool(
            getattr(self._client, "knowno_viable_extraction_failed", False)
        )
        raw_vo = getattr(self._client, "viable_objects", None)
        viable: List[Any] = list(raw_vo) if isinstance(raw_vo, list) else []

        if failed:
            self._client.is_ambiguous = True
            self._client.current_ambiguous_type = "Common sense"
            label = "Ambiguous (extraction failed)"
        else:
            ambiguous = len(viable) >= 2
            self._client.is_ambiguous = ambiguous
            if not ambiguous:
                self._client.current_ambiguous_type = None
            label = "Ambiguous" if ambiguous else "Unambiguous"

        self.bb.append_bot_trace_step(
            f"Ambiguity: {label} ({len(viable)} viable)",
            "ok",
        )
        return py_trees.common.Status.SUCCESS
