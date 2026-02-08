from typing import Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_standalone_question_prompt

from .base import BaseNode
from .black_board import Blackboard


class StandaloneQuestionNode(BaseNode):
    """
    Rewrites user_question into a standalone question using turn_history for context.
    Runs first; all downstream nodes should use standalone_question instead of user_question.

    Reads:
      - user_question
      - turn_history
    Writes:
      - standalone_question (str)

    Return:
      - SUCCESS when standalone_question is set (from LLM or fallback to user_question)
      - FAILURE on errors (safe default; sets standalone_question = user_question)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        max_history_lines: int = 12,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._max_history_lines = max_history_lines

        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="user_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            user_question: Optional[str] = getattr(self._client, "user_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []

            if not user_question or not str(user_question).strip():
                raise ValueError("blackboard.user_question is missing/empty")

            prompt = build_standalone_question_prompt(
                user_question=str(user_question),
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )

            response = self._llm.invoke(prompt).content.strip()
            standalone = response if response else str(user_question).strip()
            self._client.standalone_question = standalone

            file_logger.info(
                f"StandaloneQuestionNode: formed standalone question: {standalone}"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"StandaloneQuestionNode error: {error_msg}")
            user_question = getattr(self._client, "user_question", None) or ""
            self._client.standalone_question = str(user_question).strip()
            return py_trees.common.Status.FAILURE
