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
