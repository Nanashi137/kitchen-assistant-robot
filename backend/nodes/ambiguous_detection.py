from typing import Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_ambiguity_prompt

from .base import BaseNode
from .black_board import Blackboard


class AmbiguityDetectorNode(BaseNode):
    """
    Reads:
      - standalone_question
      - turn_history
    Writes:
      - is_ambiguous (bool)

    Return:
      - SUCCESS after setting is_ambiguous.
      - FAILURE only on errors.
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        max_history_lines: int = 10,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._max_history_lines = max_history_lines

        # register bb keys used by this node
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            turn_history = getattr(self._client, "turn_history", None) or []

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_ambiguity_prompt(
                user_question=str(standalone_question),
                turn_history=list(turn_history),
                max_lines=self._max_history_lines,
            )

            raw = self._llm.invoke(prompt).content.strip()
            # Use first line/token only so trailing explanation does not affect routing
            response = raw.split("\n")[0].strip().upper() if raw else ""

            if "AMBIGUOUS" in response:
                self._client.is_ambiguous = True
                file_logger.info("AmbiguityDetector: Question is ambiguous")
                return py_trees.common.Status.SUCCESS

            if "CLEAR" in response:
                self._client.is_ambiguous = False
                file_logger.info("AmbiguityDetector: Question is clear")
                return py_trees.common.Status.SUCCESS

            raise ValueError(f"LLM returned unexpected output: {response[:80]!r}")

        except Exception as e:
            self._client.is_ambiguous = True  # safe fallback
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"AmbiguityDetector error: {error_msg}")
            return py_trees.common.Status.FAILURE
