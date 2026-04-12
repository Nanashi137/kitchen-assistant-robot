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
    ):
        super().__init__(name=name, bb=bb)
        self._vecdb = vecdb
        self._max_history_lines = max_history_lines
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
            top_k=5,
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

            sq_text = str(standalone_question).strip()
            used_entity_queries = bool(potential_entities)
            search_queries = (
                potential_entities if potential_entities else [sq_text]
            )

            search_results_per_entity = asyncio.run(
                self._search_all_entities(search_queries)
            )

            related_entities = []
            for entity_query, result in zip(search_queries, search_results_per_entity):
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

            if (
                not related_entities
                and used_entity_queries
                and sq_text
                and sq_text not in search_queries
            ):
                file_logger.info(
                    "VectorSearchNode: empty results from entity queries; "
                    "fallback search with standalone request"
                )
                fallback = asyncio.run(self._search_one_entity(sq_text))
                if not isinstance(fallback, Exception):
                    for item in fallback:
                        entity_name = getattr(item, "entity", None)
                        if entity_name:
                            related_entities.append(entity_name)
                related_entities = self._dedupe_keep_order(related_entities)

            self._client.current_related_entities = related_entities
            file_logger.info(
                f"VectorSearchNode: Found {len(related_entities)} related entities "
                f"from {len(search_queries)} search queries"
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
