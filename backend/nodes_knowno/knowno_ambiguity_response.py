from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts.knowno_response_prompt import build_knowno_response_prompt

from nodes.base import BaseNode
from nodes.black_board import Blackboard


class KnownoAmbiguityResponseNode(BaseNode):
    """
    Ambiguous branch: assistant clarification using knowno_response_prompt.

    Reads:
      - standalone_question
      - turn_history
      - knowno_ambiguity_type
      - knowno_viable_objects
    Writes:
      - answer
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
            key="ambiguity_type", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="viable_objects", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            amb_type = getattr(self._client, "knowno_ambiguity_type", None) or "None"
            viable = getattr(self._client, "knowno_viable_objects", None) or []

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            viable_list: List[dict] = list(viable) if isinstance(viable, list) else []
            prompt = build_knowno_response_prompt(
                query=str(sq),
                ambiguity_type=str(amb_type),
                viable_objects=viable_list,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            response = self._llm.invoke(prompt).content.strip()
            self._client.answer = response or "Which option should I use?"
            file_logger.info("KnownoAmbiguityResponseNode: generated clarification")
            self.bb.append_bot_trace_step("Generated clarification question", "ok")
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            file_logger.error(
                f"KnownoAmbiguityResponseNode error: {type(e).__name__}: {e}"
            )
            self._client.answer = "Which option should I use?"
            self.bb.append_bot_trace_step("Generated clarification question", "fail")
            return py_trees.common.Status.SUCCESS
