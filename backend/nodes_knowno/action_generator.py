import json
from typing import List, Optional

import py_trees
from langchain_openai import ChatOpenAI
from logger import file_logger
from prompts import build_entity_actions_prompt

from .base import BaseNode
from .black_board import Blackboard
from .bot_trace_format import determine_type_line


class EntityActionGeneratorNode(BaseNode):
    """
    Generates actions for entities based on the user's request.

    Reads:
      - standalone_question
      - current_related_entities (list of entities related to the user's request)
    Writes:
      - entity_actions (list of actions for each entity)

    Return:
      - SUCCESS when actions are generated
      - FAILURE on errors (safe default)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        llm: ChatOpenAI,
    ):
        super().__init__(name=name, bb=bb)
        self._llm = llm


        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )

        self._client.register_key(
            key="current_related_entities", access=py_trees.common.Access.READ
        )

        self._client.register_key(
            key="entity_action", access=py_trees.common.Access.WRITE
        )

    def _get_current_related_entities(self) -> List[str]:
        """Read current_related_entities from blackboard; default to [] if key does not exist yet."""
        try:
            entities = getattr(self._client, "current_related_entities", None) or []
        except KeyError:
            return []
        return list(entities) if isinstance(entities, list) else []

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            current_related_entities = self._get_current_related_entities()

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            prompt = build_entity_actions_prompt(
                user_request=str(standalone_question),
                related_entities=current_related_entities,
            )

            response = self._llm.invoke(prompt).content.strip()
            parsed = json.loads(response)

            self._client.entity_action = parsed


            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"EntityActionGeneratorNode error: {error_msg}")

            return py_trees.common.Status.FAILURE
