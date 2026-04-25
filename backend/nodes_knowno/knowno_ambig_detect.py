from typing import Dict, List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_knowno_ambig_detect_prompt

from .base import BaseNode
from .black_board import Blackboard
from .llm_json import parse_llm_json_object


class KnownoAmbigDetectNode(BaseNode):
    """
    LLM: binary ambiguous vs unambiguous from query, history, and viable objects.

    Reads:
      - standalone_question, turn_history, viable_objects
      - knowno_viable_extraction_failed (if True, skips LLM; treats as ambiguous)
    Writes:
      - is_ambiguous
      - current_ambiguous_type (cleared when unambiguous; set on extraction failure only)
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
        try:
            if bool(
                getattr(self._client, "knowno_viable_extraction_failed", False)
            ):
                self._client.is_ambiguous = True
                self._client.current_ambiguous_type = "Common sense"
                self.bb.append_bot_trace_step(
                    "Ambiguity detect: Ambiguous (viable extraction failed)",
                    "ok",
                )
                return py_trees.common.Status.SUCCESS

            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            raw_vo = getattr(self._client, "viable_objects", None) or []
            viable: List[Dict[str, str]] = [
                dict(x) for x in raw_vo if isinstance(x, dict) and x
            ]

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_knowno_ambig_detect_prompt(
                query=str(sq),
                viable_objects=viable,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)
            classification = str(data.get("classification", "")).strip()
            brief = str(data.get("brief_reason", "")).strip()

            is_ambiguous = "ambiguous" in classification.lower()
            self._client.is_ambiguous = is_ambiguous
            if not is_ambiguous:
                self._client.current_ambiguous_type = None

            label = "Ambiguous" if is_ambiguous else "Unambiguous"
            file_logger.info(
                f"KnownoAmbigDetectNode: {label} reason={brief!r}"
            )
            trace_msg = f"Ambiguity detect: {label}"
            if brief:
                trace_msg = f"{trace_msg} ({brief})"
            self.bb.append_bot_trace_step(trace_msg, "ok")
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"KnownoAmbigDetectNode error: {error_msg}")
            self._client.is_ambiguous = True
            self._client.current_ambiguous_type = "Common sense"
            self.bb.append_bot_trace_step("Ambiguity detect (LLM)", "fail")
            return py_trees.common.Status.SUCCESS
