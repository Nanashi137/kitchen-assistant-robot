import warnings
from typing import Optional

import py_trees
from clients import MilvusHybridEntityStore
from logger import file_logger

from .base import BaseNode
from .black_board import Blackboard


class VectorSearchNode(BaseNode):
    """
    Reads:
      - user_question
    Writes:
      - current_entities (list)

    Return:
      - SUCCESS if retrieved entities
      - FAILURE on errors (safe default)
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

        # register bb keys used by this node
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="user_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(
            key="current_related_entities", access=py_trees.common.Access.WRITE
        )

    def update(self) -> py_trees.common.Status:
        try:
            user_question: Optional[str] = getattr(self._client, "user_question", None)

            if not user_question or not str(user_question).strip():
                raise ValueError("blackboard.user_question is missing/empty")

            # Use search_sync which handles async internally with asyncio.run()
            # Suppress RuntimeWarning about coroutines - search_sync properly handles async
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*coroutine.*was never awaited.*",
                    category=RuntimeWarning,
                )
                search_results = self._vecdb.search(
                    query=str(user_question),
                    top_k=5,
                    dense_weight=0.4,
                    sparse_weight=0.6,
                    min_score=0.6,
                )

            related_entities = [result.entity for result in search_results]

            self._client.current_related_entities = related_entities
            file_logger.info(
                f"VectorSearchNode: Found {len(related_entities)} related entities"
            )
            return py_trees.common.Status.SUCCESS

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            file_logger.error(f"VectorSearchNode error: {error_msg}")
            self._client.current_related_entities = []  # safe fallback
            return py_trees.common.Status.FAILURE
