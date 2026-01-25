from typing import List, Optional

import py_trees

AMBIGUITY_TYPES = [
    "Safety",
    "Common sense",
    "Preference",
]


class Blackboard:
    def __init__(self, name: str = "bt"):
        self._client = py_trees.blackboard.Client(name=name)

        # Ambiguous detector keys
        self._client.register_key(
            key="turn_history", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="user_question", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="is_ambiguous", access=py_trees.common.Access.WRITE
        )

        # Ambiguous classifier keys
        self._client.register_key(
            key="used_ambiguous_types", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="current_ambiguous_type", access=py_trees.common.Access.WRITE
        )

        # Ambiguous resolver keys
        self._client.register_key(
            key="current_related_entities", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="repaired_response", access=py_trees.common.Access.WRITE
        )

        # Answer node keys
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

    @property
    def answer(self) -> Optional[str]:
        return getattr(self._client, "answer", None)

    @answer.setter
    def answer(self, value: Optional[str]) -> None:
        self._client.answer = value

    @property
    def used_ambiguous_types(self) -> List[str]:
        return list(getattr(self._client, "used_ambiguous_types", []) or [])

    @used_ambiguous_types.setter
    def used_ambiguous_types(self, value: List[str]) -> None:
        self._client.used_ambiguous_types.append(value)

    @property
    def turn_history(self) -> List[str]:
        return list(getattr(self._client, "turn_history", []) or [])

    @turn_history.setter
    def turn_history(self, value: List[str]) -> None:
        self._client.turn_history = list(value or [])

    @property
    def user_question(self) -> Optional[str]:
        return getattr(self._client, "user_question", None)

    @user_question.setter
    def user_question(self, value: Optional[str]) -> None:
        self._client.user_question = value

    @property
    def is_ambiguous(self) -> Optional[bool]:
        return getattr(self._client, "is_ambiguous", None)

    @is_ambiguous.setter
    def is_ambiguous(self, value: Optional[bool]) -> None:
        self._client.is_ambiguous = value

    def raw_client(self) -> py_trees.blackboard.Client:
        return self._client
