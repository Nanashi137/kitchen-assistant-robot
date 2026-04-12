from typing import List, Optional, Set

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_entity_resolve_prompt

from .base import BaseNode
from .black_board import Blackboard
from .llm_json import parse_llm_json_object
from .or_choice_sanitize import sanitize_or_choice_conflicts


def _filter_to_predicted_order(
    predicted: List[str], kept_labels_lower: Set[str]
) -> List[str]:
    """Keep only predicted names whose lowercased form is in kept_labels_lower; preserve predicted order."""
    out: List[str] = []
    for name in predicted:
        s = str(name).strip()
        if not s:
            continue
        if s.lower() in kept_labels_lower:
            out.append(s)
    return out


class EntityResolveNode(BaseNode):
    """
    After entity prediction: drop entities already settled by standalone request + history.

    Reads:
      - standalone_question
      - turn_history
      - potential_entities
    Writes:
      - potential_entities (filtered list; unchanged on parse failure)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
        max_history_lines: int = 24,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm
        self._max_history_lines = max_history_lines

        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="potential_entities", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="potential_entities", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            raw_pe = getattr(self._client, "potential_entities", None) or []

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            predicted: List[str] = [
                str(x).strip() for x in raw_pe if isinstance(x, str) and str(x).strip()
            ]
            if not predicted:
                self.bb.append_bot_trace_step("Entity resolve: nothing to filter", "ok")
                return py_trees.common.Status.SUCCESS

            prompt = build_entity_resolve_prompt(
                standalone_request=str(sq),
                predicted_entities=predicted,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            response = self._llm.invoke(prompt).content
            data = parse_llm_json_object(response)
            kept = data.get("potential_entities")
            if not isinstance(kept, list):
                raise ValueError("potential_entities is not a list")

            kept_lower = {
                str(x).strip().lower() for x in kept if str(x).strip()
            }
            filtered = _filter_to_predicted_order(predicted, kept_lower)
            filtered = sanitize_or_choice_conflicts(
                filtered, list(turn_history), str(sq)
            )

            self._client.potential_entities = filtered
            file_logger.info(
                "EntityResolveNode: %s -> %s entities after resolve",
                len(predicted),
                len(filtered),
            )
            self.bb.append_bot_trace_step(
                f"Entity resolve: {len(predicted)} → {len(filtered)} entities",
                "ok",
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"EntityResolveNode error: {error_msg}")
            try:
                sq_fb: Optional[str] = getattr(self._client, "standalone_question", None)
                th_fb = list(getattr(self._client, "turn_history", None) or [])
                raw_fb = getattr(self._client, "potential_entities", None) or []
                pred_fb: List[str] = [
                    str(x).strip()
                    for x in raw_fb
                    if isinstance(x, str) and str(x).strip()
                ]
                if sq_fb and pred_fb:
                    self._client.potential_entities = sanitize_or_choice_conflicts(
                        pred_fb, th_fb, str(sq_fb)
                    )
                    self.bb.append_bot_trace_step(
                        "Entity resolve: LLM failed; applied OR-choice sanitizer",
                        "fail",
                    )
                else:
                    self.bb.append_bot_trace_step(
                        "Entity resolve: kept predictions unchanged", "fail"
                    )
            except Exception:
                self.bb.append_bot_trace_step(
                    "Entity resolve: kept predictions unchanged", "fail"
                )
            return py_trees.common.Status.SUCCESS
