from typing import Dict, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_entity_action_predict_prompt

from nodes.base import BaseNode
from nodes.black_board import Blackboard

from .llm_json import parse_llm_json_object


class PredictEntityNode(BaseNode):
    """
    entities_predictor: LLM extracts entity → role map for the current standalone query.

    Reads:
      - standalone_question
      - turn_history
    Writes:
      - entity_action (dict[str, str])
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        max_history_lines: int = 20,
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
            key="entity_action", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_entity_action_predict_prompt(
                query=str(sq),
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)
            ea = data.get("entity_action")
            entity_action: Dict[str, str] = {}
            if isinstance(ea, dict):
                for k, v in ea.items():
                    ks = str(k).strip()
                    if ks:
                        entity_action[ks] = str(v).strip() if v is not None else ""

            self._client.entity_action = entity_action
            file_logger.info(
                f"PredictEntityNode: entity_action keys={list(entity_action.keys())!r}"
            )
            self.bb.append_bot_trace_step("Predicted entities for request", "ok")
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"PredictEntityNode error: {error_msg}")
            self._client.entity_action = {}
            self.bb.append_bot_trace_step("Predicted entities for request", "fail")
            return py_trees.common.Status.SUCCESS
