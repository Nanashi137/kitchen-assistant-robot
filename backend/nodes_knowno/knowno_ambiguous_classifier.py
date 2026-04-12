from typing import Any, Dict, List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_knowno_ambig_classify_prompt

from .base import BaseNode
from .black_board import Blackboard

from .llm_json import parse_llm_json_object


def _normalize_viable_objects(
    viable_raw: Any,
    entity_action: Dict[str, str],
) -> List[dict]:
    """Map classifier viable_objects (strings or dicts) to list[dict] for clarification prompt."""
    if viable_raw is None:
        return []
    if not isinstance(viable_raw, list):
        return []

    out: List[dict] = []
    for item in viable_raw:
        if isinstance(item, dict) and item:
            out.append(item)
            continue
        name = str(item).strip()
        if not name:
            continue
        role = "alternative for this request"
        matched = False
        for ent, r in entity_action.items():
            if name.lower() == ent.lower():
                role = r
                matched = True
                break
        if not matched:
            for ent, r in entity_action.items():
                el, nl = ent.lower(), name.lower()
                if el in nl or nl in el:
                    role = r
                    break
        out.append({name: role})
    return out


class KnownoAmbiguousClassifierNode(BaseNode):
    """
    Knowno ambiguity: uses vector Top-K + entity_action + query/history; sets is_ambiguous.

    Reads:
      - standalone_question
      - turn_history
      - entity_action
      - current_related_entities
    Writes:
      - is_ambiguous
      - knowno_ambiguity_type
      - knowno_viable_objects (for clarification response)
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
            key="current_related_entities", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="knowno_ambiguity_type", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="knowno_viable_objects", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            sq: Optional[str] = getattr(self._client, "standalone_question", None)
            turn_history = getattr(self._client, "turn_history", None) or []
            related = getattr(self._client, "current_related_entities", None) or []
            ea_raw = getattr(self._client, "entity_action", None) or {}
            entity_action: Dict[str, str] = (
                dict(ea_raw) if isinstance(ea_raw, dict) else {}
            )

            if not sq or not str(sq).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            top_k = [str(x) for x in related if str(x).strip()]

            prompt = build_knowno_ambig_classify_prompt(
                query=str(sq),
                entity_action=entity_action,
                top_k_candidates=top_k,
                turn_history=list(turn_history),
                max_history_lines=self._max_history_lines,
            )
            raw = self._llm.invoke(prompt).content
            data = parse_llm_json_object(raw)

            classification = str(data.get("classification", "")).strip()
            amb_type = str(data.get("ambiguity_type", "None")).strip() or "None"
            viable_raw = data.get("viable_objects")

            is_ambiguous = "ambiguous" in classification.lower()
            self._client.is_ambiguous = is_ambiguous
            self._client.knowno_ambiguity_type = amb_type
            self._client.knowno_viable_objects = _normalize_viable_objects(
                viable_raw, entity_action
            )

            label = "Ambiguous" if is_ambiguous else "Unambiguous"
            file_logger.info(
                f"KnownoAmbiguousClassifierNode: {label}, type={amb_type!r}"
            )
            self.bb.append_bot_trace_step(
                f"Knowno classification: {label} ({amb_type})", "ok"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"KnownoAmbiguousClassifierNode error: {error_msg}")
            self._client.is_ambiguous = True
            self._client.knowno_ambiguity_type = "Common Sense"
            self._client.knowno_viable_objects = []
            self.bb.append_bot_trace_step("Knowno classification", "fail")
            return py_trees.common.Status.SUCCESS
