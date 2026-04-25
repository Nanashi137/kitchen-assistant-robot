from typing import Dict, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_knowno_viable_object_prompt

from .base import BaseNode
from .black_board import Blackboard
from .llm_json import parse_llm_json_object
from .viable_objects_util import normalize_viable_objects


class KnownoViableObjectsNode(BaseNode):
    """
    LLM step: extract viable object-action dicts from entity_action for the current query.

    Reads:
      - standalone_question, turn_history, entity_action
    Writes:
      - viable_objects
      - knowno_viable_extraction_failed (bool; True if LLM/parse failed)
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
            key="entity_action", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="viable_objects", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="knowno_viable_extraction_failed",
            access=py_trees.common.Access.WRITE,
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            ea_raw = getattr(self._client, "entity_action", None) or {}
            entity_action: Dict[str, str] = (
                dict(ea_raw) if isinstance(ea_raw, dict) else {}
            )

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            self._client.knowno_viable_extraction_failed = False

            prompt = build_knowno_viable_object_prompt(
                query=str(sq),
                entity_action=entity_action,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)
            viable_raw = data.get("viable_objects")
            self._client.viable_objects = normalize_viable_objects(
                viable_raw, entity_action
            )
            file_logger.info(
                f"KnownoViableObjectsNode: count={len(self._client.viable_objects or [])}"
            )
            self.bb.append_bot_trace_step(
                f"Viable objects: {len(self._client.viable_objects or [])}",
                "ok",
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"KnownoViableObjectsNode error: {error_msg}")
            self._client.viable_objects = []
            self._client.knowno_viable_extraction_failed = True
            self.bb.append_bot_trace_step("Viable object extraction", "fail")
            return py_trees.common.Status.SUCCESS
