import warnings
from typing import List, Optional
import json

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_potential_entities_prompt


from .base import BaseNode
from .black_board import Blackboard
from .bot_trace_format import retrieving_entities_context, searching_entities_line
from .or_choice_sanitize import sanitize_or_choice_conflicts


class EntitiesPredictorNode(BaseNode):
    """
    Reads:
      - standalone_question
      - turn_history
    Writes:
      - potential_entities (list)

    Return:
      - SUCCESS if retrieved entities
      - FAILURE on errors (safe default)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        top_k: int = 5,
        max_history_lines: int = 24,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._top_k = top_k
        self._max_history_lines = max_history_lines

        # register bb keys used by this node
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="potential_entities", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            turn_history: List[str] = list(
                getattr(self._client, "turn_history", None) or []
            )

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_potential_entities_prompt(
                user_request=standalone_question,
                topk=self._top_k,
                turn_history=turn_history,
                max_history_lines=self._max_history_lines,
            )

            response = self._llm.invoke(prompt).content.strip()

            parsed = json.loads(response)
            related_entities = parsed["potential_entities"]
            if not isinstance(related_entities, list):
                raise ValueError("potential_entities is not a list")
            related_entities = [
                str(x).strip()
                for x in related_entities
                if isinstance(x, str) and str(x).strip()
            ]
            related_entities = sanitize_or_choice_conflicts(
                related_entities,
                turn_history,
                str(standalone_question),
            )

            self._client.potential_entities = related_entities
            file_logger.info(
                f"PotentialEntitiesNode: Found {len(related_entities)} potential entities: {related_entities}"
            )
            n = len(related_entities)
            self.bb.append_bot_trace_step(f"Predicting entities: {n} entities predicted", "ok")
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"PotentialEntitiesNode error: {error_msg}")
            self._client.potential_entities = []  # safe fallback; routing continues
            self.bb.append_bot_trace_step(f"Predicting entities: 0 entities predicted", "fail")
            return py_trees.common.Status.SUCCESS
