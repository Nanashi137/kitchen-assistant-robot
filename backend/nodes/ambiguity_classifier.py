from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_ambiguity_discriminator_prompt

from .base import BaseNode
from .black_board import Blackboard

# Canonical types returned by the discriminator prompt (priority: Safety > Common sense > Preference)
AMBIGUITY_TYPES = ["Safety", "Common sense", "Preference"]


class AmbiguityClassifierNode(BaseNode):
    """
    Classifies the type of ambiguity using an LLM.

    Reads:
      - standalone_question
      - turn_history
      - used_ambiguous_types (list of already-tried types)
    Writes:
      - current_ambiguous_type (one of "Safety", "Common sense", "Preference")
      - used_ambiguous_types (appends the classified type)

    Return:
      - SUCCESS when a type was classified
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
            key="used_ambiguous_types", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="used_ambiguous_types", access=py_trees.common.Access.WRITE
        )

    def _get_used_ambiguous_types(self) -> List[str]:
        """Read used_ambiguous_types from blackboard; default to [] if key does not exist yet."""
        try:
            used = getattr(self._client, "used_ambiguous_types", None) or []
        except KeyError:
            return []
        return list(used) if isinstance(used, list) else []

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            turn_history = getattr(self._client, "turn_history", None) or []
            used_list = self._get_used_ambiguous_types()

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_ambiguity_discriminator_prompt(
                user_question=str(standalone_question),
                turn_history=list(turn_history),
                max_lines=self._max_history_lines,
                used_ambiguous_types=used_list,
            )

            raw = self._llm.invoke(prompt).content.strip()
            response = raw.split("\n")[0].strip() if raw else ""

            classified = None
            resp_lower = response.lower()
            for t in AMBIGUITY_TYPES:
                if t.lower() in resp_lower or resp_lower in t.lower():
                    classified = t
                    break
            if not classified:
                first = response.split()[0] if response else ""
                for t in AMBIGUITY_TYPES:
                    if (
                        t.lower().startswith(first.lower())
                        or first.lower() in t.lower()
                    ):
                        classified = t
                        break
            if not classified:
                classified = "Common sense"

            self._client.current_ambiguous_type = classified
            current_used = self._get_used_ambiguous_types()
            self._client.used_ambiguous_types = current_used + [classified]

            file_logger.info(
                f"AmbiguityClassifierNode: classified type = {classified!r}"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"AmbiguityClassifierNode error: {error_msg}")
            self._client.current_ambiguous_type = "Common sense"  # fallback
            return py_trees.common.Status.FAILURE
