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

        # Standalone question (rewritten from user_question + turn_history)
        self._client.register_key(
            key="standalone_question", access=py_trees.common.Access.WRITE
        )

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

        # Await-user keys (post-repair router)
        self._client.register_key(
            key="awaiting_user_response", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="preference_turn_count", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="max_preference_turns", access=py_trees.common.Access.WRITE
        )

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
    def standalone_question(self) -> Optional[str]:
        return getattr(self._client, "standalone_question", None)

    @standalone_question.setter
    def standalone_question(self, value: Optional[str]) -> None:
        self._client.standalone_question = value

    @property
    def is_ambiguous(self) -> Optional[bool]:
        return getattr(self._client, "is_ambiguous", None)

    @is_ambiguous.setter
    def is_ambiguous(self, value: Optional[bool]) -> None:
        self._client.is_ambiguous = value

    @property
    def current_related_entities(self) -> List:
        return list(getattr(self._client, "current_related_entities", []) or [])

    @current_related_entities.setter
    def current_related_entities(self, value: List) -> None:
        self._client.current_related_entities = list(value or [])

    def raw_client(self) -> py_trees.blackboard.Client:
        return self._client

    @property
    def awaiting_user_response(self) -> bool:
        return bool(getattr(self._client, "awaiting_user_response", False))

    @awaiting_user_response.setter
    def awaiting_user_response(self, value: bool) -> None:
        self._client.awaiting_user_response = value

    @property
    def preference_turn_count(self) -> int:
        return int(getattr(self._client, "preference_turn_count", 0) or 0)

    @preference_turn_count.setter
    def preference_turn_count(self, value: int) -> None:
        self._client.preference_turn_count = value

    @property
    def max_preference_turns(self) -> int:
        return int(getattr(self._client, "max_preference_turns", 0) or 0)

    @max_preference_turns.setter
    def max_preference_turns(self, value: int) -> None:
        self._client.max_preference_turns = value

    def clear_for_new_question(self) -> None:
        """Reset blackboard state for a new top-level question (e.g. after showing answer or starting fresh)."""
        self._client.user_question = None
        self._client.standalone_question = None
        self._client.turn_history = []
        self._client.is_ambiguous = None
        self._client.current_related_entities = []
        self._client.answer = None
        self._client.awaiting_user_response = False
        self._client.preference_turn_count = 0
        try:
            self._client.used_ambiguous_types = []
        except KeyError:
            pass
        self._client.current_ambiguous_type = None
