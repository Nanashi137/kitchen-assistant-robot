from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import (build_common_sense_repair_prompt,
                     build_preference_repair_prompt,
                     build_safety_repair_prompt)

from .base import BaseNode
from .black_board import Blackboard


class AmbiguousRepairNode(BaseNode):
    """
    Produces a repair response based on the classified ambiguous type.

    Reads:
      - standalone_question
      - turn_history
      - current_ambiguous_type ("Safety", "Common sense", "Preference")
      - current_related_entities (optional)
    Writes:
      - repaired_response (str)
      - answer (str) — same as repaired_response for downstream use

    Return:
      - SUCCESS when a response was generated
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

        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_related_entities",
            access=py_trees.common.Access.READ,
        )
        self._client.register_key(
            key="repaired_response", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            turn_history = getattr(self._client, "turn_history", None) or []
            ambiguous_type: Optional[str] = (
                getattr(self._client, "current_ambiguous_type", None) or "Common sense"
            )
            related = getattr(self._client, "current_related_entities", None) or []
            related_list: List[str] = list(related) if isinstance(related, list) else []

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            t = ambiguous_type.strip()
            t_lower = t.lower()

            if "safety" in t_lower:
                prompt = build_safety_repair_prompt(
                    user_question=str(standalone_question),
                    turn_history=list(turn_history),
                    related_entities=related_list,
                    max_lines=self._max_history_lines,
                )
            elif "preference" in t_lower:
                prompt = build_preference_repair_prompt(
                    user_question=str(standalone_question),
                    turn_history=list(turn_history),
                    related_entities=related_list,
                    max_lines=self._max_history_lines,
                )
            else:
                prompt = build_common_sense_repair_prompt(
                    user_question=str(standalone_question),
                    turn_history=list(turn_history),
                    related_entities=related_list,
                    max_lines=self._max_history_lines,
                )

            response = self._llm.invoke(prompt).content.strip()
            self._client.repaired_response = response
            self._client.answer = response

            file_logger.info(
                f"AmbiguousRepairNode: produced repair for type {ambiguous_type!r}"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"AmbiguousRepairNode error: {error_msg}")
            fallback = (
                "I need a bit more detail to help you safely. "
                "Could you clarify what you're trying to do?"
            )
            self._client.repaired_response = fallback
            self._client.answer = fallback
            return py_trees.common.Status.FAILURE
