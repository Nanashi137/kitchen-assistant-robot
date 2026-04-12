"""entities_predictor: ranked potential entities from the standalone request."""

from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_potential_entities_prompt

from .base import BaseNode
from .black_board import Blackboard
from .llm_json import parse_llm_json_object


class PredictEntityNode(BaseNode):
    """
    LLM extracts ``potential_entities`` for vector grounding.

    Reads:
      - standalone_question
    Writes:
      - potential_entities (list[str])
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        topk: int = 5,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._topk = topk
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="potential_entities", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_potential_entities_prompt(
                user_request=str(sq).strip(),
                topk=self._topk,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)
            raw_list = data.get("potential_entities")
            out: List[str] = []
            if isinstance(raw_list, list):
                for x in raw_list:
                    s = str(x).strip().lower() if x is not None else ""
                    if s:
                        out.append(s)
            # dedupe keep order
            seen = set()
            deduped = []
            for e in out:
                if e not in seen:
                    seen.add(e)
                    deduped.append(e)

            self._client.potential_entities = deduped
            file_logger.info(
                f"PredictEntityNode: potential_entities={deduped!r}"
            )
            self.bb.append_bot_trace_step("Predicted potential entities", "ok")
            return py_trees.common.Status.SUCCESS
        except Exception as e:
            file_logger.error(f"PredictEntityNode error: {type(e).__name__}: {e}")
            self._client.potential_entities = []
            self.bb.append_bot_trace_step("Predicted potential entities", "fail")
            return py_trees.common.Status.SUCCESS
