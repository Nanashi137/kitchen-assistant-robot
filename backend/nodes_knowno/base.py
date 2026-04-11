import py_trees

from .black_board import Blackboard


class BaseNode(py_trees.behaviour.Behaviour):

    def __init__(self, name: str, bb: Blackboard):
        super().__init__(name=name)
        self.bb = bb

        self._client = py_trees.blackboard.Client(name=f"{name}_client")

    def initialise(self) -> None:
        pass

    def terminate(self, new_status: py_trees.common.Status) -> None:
        pass

    def _log_trace(self, status: py_trees.common.Status) -> None:
        """Legacy: append node name. Prefer _log_trace_step with a human label."""
        status_str = status.name if hasattr(status, "name") else str(status)
        self.bb.append_bot_trace(self.name, status_str)

    def _log_trace_step(self, status: py_trees.common.Status, step: str) -> None:
        """Append an explainable step for the assistant message trace (UI)."""
        ok = status == py_trees.common.Status.SUCCESS
        self.bb.append_bot_trace_step(step, "ok" if ok else "fail")
