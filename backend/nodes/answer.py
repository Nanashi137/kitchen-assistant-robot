from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI

from logger import file_logger
from prompts import build_answer_prompt

from .base import BaseNode
from .black_board import Blackboard


class AnswerNode(BaseNode):
    """
    Reads:
      - user_question
      - current_related_entities
      - turn_history (optional)
    Writes:
      - answer (str)

    Return:
      - SUCCESS if answer generated successfully
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
            key="current_related_entities", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def update(self) -> py_trees.common.Status:
        try:
            user_question: Optional[str] = getattr(self._client, "user_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            related_entities = (
                getattr(self._client, "current_related_entities", None) or []
            )

            if not user_question or not str(user_question).strip():
                raise ValueError("blackboard.user_question is missing/empty")

            # Convert related_entities to list of strings
            if related_entities and isinstance(related_entities, list):
                entity_list = [str(entity) for entity in related_entities if entity]
            else:
                entity_list = []

            prompt = build_answer_prompt(
                user_question=str(user_question),
                related_entities=entity_list,
                turn_history=list(turn_history) if turn_history else None,
                max_history_lines=self._max_history_lines,
            )

            response = self._llm.invoke(prompt).content.strip()

            if not response:
                raise ValueError("LLM returned empty answer")

            # Store the answer in blackboard
            self._client.answer = response
            file_logger.info(
                f"AnswerNode: Generated answer for question: {user_question[:50]}..."
            )

            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"AnswerNode error: {error_msg}")
            self._client.answer = ""  # safe fallback
            return py_trees.common.Status.FAILURE
