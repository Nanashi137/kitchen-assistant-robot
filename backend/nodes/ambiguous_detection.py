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
      - user_question
      - turn_history
    Writes:
      - is_ambiguous (bool)

    Return:
      - FAILURE if ambiguous
      - SUCCESS if clear
      - FAILURE on errors (safe default)
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
            key="user_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            user_question: Optional[str] = getattr(self._client, "user_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []

            if not user_question or not str(user_question).strip():
                raise ValueError("blackboard.user_question is missing/empty")

            prompt = build_ambiguity_prompt(
                user_question=str(user_question),
                turn_history=list(turn_history),
                max_lines=self._max_history_lines,
            )

            response = self._llm.invoke(prompt).content.strip().upper()

            if "AMBIGUOUS" in response:
                self._client.is_ambiguous = True
                file_logger.info("AmbiguityDetector: Question is ambiguous")
                return py_trees.common.Status.FAILURE

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
