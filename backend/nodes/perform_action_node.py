"""
Clear-path node: produce assistant message via a pluggable ActionExecutor (no LLM by default).

Swap `executor` for a Gazebo-backed implementation later; keep the same __call__(client) contract.
"""

from typing import Callable, Optional, Union

import py_trees

from logger import file_logger

from .action_executor import ActionExecutor, PlainMessageActionExecutor, default_action_executor
from .base import BaseNode
from .black_board import Blackboard


class PerformActionNode(BaseNode):
    """
    Reads:
      - standalone_question (via client)
    Writes:
      - answer (str)

    The executor receives the py_trees blackboard client so it can read any registered keys
    (e.g. standalone_question, turn_history, future: pose, tool_id).
    """

    def __init__(
        self,
        name: str,
        bb: Blackboard,
        executor: Optional[Union[ActionExecutor, Callable[[object], str]]] = None,
    ):
        super().__init__(name=name, bb=bb)
        self._executor: Union[ActionExecutor, Callable[[object], str]] = (
            executor if executor is not None else default_action_executor()
        )
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.READ
        )
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    def update(self) -> py_trees.common.Status:
        try:
            msg = self._executor(self._client)
            self._client.answer = msg if msg is not None else ""
            file_logger.info(
                f"PerformActionNode: action message length={len(self._client.answer or '')}"
            )
            self._log_trace(py_trees.common.Status.SUCCESS)
            return py_trees.common.Status.SUCCESS
        except Exception as e:
            file_logger.error(f"PerformActionNode error: {type(e).__name__}: {e}")
            self._client.answer = ""
            self._log_trace(py_trees.common.Status.FAILURE)
            return py_trees.common.Status.FAILURE
