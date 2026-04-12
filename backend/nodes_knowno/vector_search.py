import asyncio
from typing import Optional

import py_trees
from clients import MilvusHybridEntityStore
from logger import file_logger

from .base import BaseNode
from .black_board import Blackboard
from .bot_trace_format import retrieving_entities_context, searching_entities_line


class VectorSearchNode(BaseNode):
    """
    Reads:
      - standalone_question
      - potential_entities
    Writes:
      - current_related_entities (list)

    Return:
      - SUCCESS always (safe fallback behavior)
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        vecdb: MilvusHybridEntityStore,
        max_history_lines: int = 12,
        top_k: int = 5,
        fallback_to_question: bool = False,
    ):
        super().__init__(name=name, bb=bb)
        self._vecdb = vecdb
        self._max_history_lines = max_history_lines
        self._top_k = top_k
        self._fallback_to_question = fallback_to_question
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_related_entities", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="potential_entities", access=py_trees.common.Access.READ
        )

    async def _search_one_entity(self, entity: str):
        return await asyncio.to_thread(
            self._vecdb.search,
            query=entity,
            top_k=1,
            dense_weight=0.4,
            sparse_weight=0.6,
            min_score=0.6,
        )

    async def _search_all_entities(self, potential_entities: list[str]):
        tasks = [
            self._search_one_entity(entity)
            for entity in potential_entities
            if isinstance(entity, str) and entity.strip()
        ]
        if not tasks:
            return []
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _dedupe_keep_order(items: list[str]) -> list[str]:
        seen = set()
        output = []
        for item in items:
            if item not in seen:
                seen.add(item)
                output.append(item)
        return output

    def update(self) -> py_trees.common.Status:
        try:
            standalone_question: Optional[str] = getattr(
                self._client, "standalone_question", None
            )
            potential_entities: Optional[list] = getattr(
                self._client, "potential_entities", None
            )

            if not standalone_question or not str(standalone_question).strip():
                raise ValueError("blackboard.standalone_question is missing/empty")

            potential_entities = potential_entities or []
            potential_entities = self._dedupe_keep_order(
                [
                    x.strip()
                    for x in potential_entities
                    if isinstance(x, str) and x.strip()
                ]
            )

            if not potential_entities:
                file_logger.info(
                    "VectorSearchNode: No potential_entities found, using safe fallback"
                )
                self._client.current_related_entities = []
                self.bb.append_bot_trace_step(searching_entities_line(0), "ok")
                return py_trees.common.Status.SUCCESS

            search_results_per_entity = asyncio.run(
                self._search_all_entities(potential_entities)
            )

            if not search_results_per_entity:
                file_logger.info(
                    "VectorSearchNode: Could not ground potential_entities, using safe fallback"
                )
                if self._fallback_to_question:
                    search_results_per_entity = asyncio.run(
                        self._search_all_entities([standalone_question])
                    )
                else:
                    self._client.current_related_entities = []
                    self.bb.append_bot_trace_step(searching_entities_line(0), "ok")
                    return py_trees.common.Status.SUCCESS

            related_entities = []
            for entity_query, result in zip(potential_entities, search_results_per_entity):
                if isinstance(result, Exception):
                    file_logger.warning(
                        f"VectorSearchNode: search failed for '{entity_query}': "
                        f"{type(result).__name__}: {result}"
                    )
                    continue

                for item in result:
                    entity_name = getattr(item, "entity", None)
                    if entity_name:
                        related_entities.append(entity_name)

            related_entities = self._dedupe_keep_order(related_entities)

            self._client.current_related_entities = related_entities
            file_logger.info(
                f"VectorSearchNode: Found {len(related_entities)} related entities "
                f"from {len(potential_entities)} potential entities"
            )

            self.bb.append_bot_trace_step(
                searching_entities_line(len(related_entities)), "ok"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"VectorSearchNode error: {error_msg}")
            self._client.current_related_entities = []
            self.bb.append_bot_trace_step(retrieving_entities_context(), "ok")
            self.bb.append_bot_trace_step(searching_entities_line(0), "fail")
            return py_trees.common.Status.SUCCESS
