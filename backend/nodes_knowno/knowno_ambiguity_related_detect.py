from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_ambiguity_prompt

from .base import BaseNode
from .black_board import Blackboard


class KnownoAmbiguityRelatedDetectNode(BaseNode):
    """
    Fallback ambiguity detection when viable objects are unavailable (empty or
    extraction failed). Mirrors ``nodes.ambiguous_detection.AmbiguityDetectorNode``:
    uses ``build_ambiguity_prompt`` with standalone_question, turn_history, and
    ``current_related_entities``; parses first-line CLEAR / AMBIGUOUS.

    Reads:
      - standalone_question, turn_history, current_related_entities
    Writes:
      - is_ambiguous
      - current_ambiguous_type (cleared when unambiguous)

    Always returns SUCCESS so the root sequence does not abort (on parse errors,
    defaults to ambiguous like other knowno nodes).
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
            key="current_related_entities", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            turn_history = getattr(self._client, "turn_history", None) or []
            related = getattr(self._client, "current_related_entities", None) or []
            related_list: List[str] = (
                [str(x) for x in related] if isinstance(related, list) else []
            )

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_ambiguity_prompt(
                user_request=str(standalone_question),
                turn_history=list(turn_history),
                max_lines=self._max_history_lines,
                related_entities=related_list,
            )

            raw = self._llm.invoke(prompt).content.strip()
            response = raw.split("\n")[0].strip().upper() if raw else ""

            if "AMBIGUOUS" in response:
                self._client.is_ambiguous = True
                file_logger.info(
                    "KnownoAmbiguityRelatedDetectNode: AMBIGUOUS (related path)"
                )
                self.bb.append_bot_trace_step(
                    "Ambiguity detect (related entities): Ambiguous",
                    "ok",
                )
                return py_trees.common.Status.SUCCESS

            if "CLEAR" in response:
                self._client.is_ambiguous = False
                self._client.current_ambiguous_type = None
                file_logger.info(
                    "KnownoAmbiguityRelatedDetectNode: CLEAR (related path)"
                )
                self.bb.append_bot_trace_step(
                    "Ambiguity detect (related entities): Unambiguous",
                    "ok",
                )
                return py_trees.common.Status.SUCCESS

            raise ValueError(f"LLM returned unexpected output: {response[:80]!r}")

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(
                f"KnownoAmbiguityRelatedDetectNode error: {error_msg}"
            )
            self._client.is_ambiguous = True
            self._client.current_ambiguous_type = "Common sense"
            self.bb.append_bot_trace_step(
                "Ambiguity detect (related entities): error, default ambiguous",
                "fail",
            )
            return py_trees.common.Status.SUCCESS
