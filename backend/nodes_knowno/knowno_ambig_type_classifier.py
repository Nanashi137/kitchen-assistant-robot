from typing import Dict, List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_knowno_ambig_type_prompt

from .base import BaseNode
from .black_board import Blackboard
from .llm_json import parse_llm_json_object
from .viable_objects_util import normalize_knowno_ambiguity_type_label


class KnownoAmbigTypeNode(BaseNode):
    """
    Ambiguous branch only: classify ambiguity type from viable objects + query/history.

    Reads:
      - standalone_question, turn_history, viable_objects
    Writes:
      - current_ambiguous_type
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        max_history_lines: int = 16,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._max_history_lines = max_history_lines

        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="viable_objects", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            vo_raw = getattr(self._client, "viable_objects", None) or []
            viable: List[Dict[str, str]] = [
                dict(x) for x in vo_raw if isinstance(x, dict) and x
            ]

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_knowno_ambig_type_prompt(
                query=str(sq),
                viable_objects=viable,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)
            amb_type = str(data.get("ambiguity_type", "")).strip()
            self._client.current_ambiguous_type = normalize_knowno_ambiguity_type_label(
                amb_type
            )
            file_logger.info(
                f"KnownoAmbigTypeNode: type={self._client.current_ambiguous_type!r}"
            )
            self.bb.append_bot_trace_step(
                f"Ambiguity type: {self._client.current_ambiguous_type}",
                "ok",
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            file_logger.error(
                f"KnownoAmbigTypeNode error: {type(e).__name__}: {e}"
            )
            self._client.current_ambiguous_type = "Common sense"
            self.bb.append_bot_trace_step("Ambiguity type classification", "fail")
            return py_trees.common.Status.SUCCESS
