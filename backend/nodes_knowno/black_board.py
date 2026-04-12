from typing import Any, List, Optional, Dict

import py_trees

AMBIGUITY_TYPES = [
    "Safety",
    "Common sense",
    "Preference",
]


class Blackboard:
    def __init__(self, name: str = "bt"):
        self._client = py_trees.blackboard.Client(name=name)

        # Standalone request line from StandaloneQuestionNode (LLM rewrite of user message + history)
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
            key="potential_entities", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="current_related_entities", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="entity_action", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="viable_objects", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(
            key="repaired_response", access=py_trees.common.Access.WRITE
        )

        # Answer node keys
        self._client.register_key(key="answer", access=py_trees.common.Access.WRITE)

        # Conversation / persistence
        self._client.register_key(
            key="conversation_id", access=py_trees.common.Access.WRITE
        )
        self._client.register_key(key="user_id", access=py_trees.common.Access.WRITE)
        self._client.register_key(key="bot_trace", access=py_trees.common.Access.WRITE)

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

    @property
    def potential_entities(self) -> List:
        return list(getattr(self._client, "potential_entities", []) or [])

    @potential_entities.setter
    def potential_entities(self, value: List) -> None:
        self._client.potential_entities = list(value or [])

    @property
    def entity_action(self) -> Dict:
        return dict(getattr(self._client, "entity_action", {}) or {})

    @entity_action.setter
    def entity_action(self, value: Dict) -> None:
        self._client.entity_action = dict(value or [])

    @property
    def viable_objects(self) -> List[Dict[str, Any]]:
        return list(getattr(self._client, "viable_objects", []) or [])

    @viable_objects.setter
    def viable_objects(self, value: List[Dict[str, Any]]) -> None:
        self._client.viable_objects = list(value or [])

    def raw_client(self) -> py_trees.blackboard.Client:
        return self._client

    @property
    def conversation_id(self) -> Optional[str]:
        val = getattr(self._client, "conversation_id", None)
        return str(val) if val is not None else None

    @conversation_id.setter
    def conversation_id(self, value: Optional[str]) -> None:
        self._client.conversation_id = value

    @property
    def user_id(self) -> Optional[str]:
        val = getattr(self._client, "user_id", None)
        return str(val) if val is not None else None

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        self._client.user_id = value

    def append_bot_trace(self, node_name: str, status: str) -> None:
        """Legacy: technical node name. Prefer append_bot_trace_step for explainable UI traces."""
        try:
            trace = list(getattr(self._client, "bot_trace", None) or [])
        except KeyError:
            trace = []
        trace.append({"node": node_name, "status": status})
        self._client.bot_trace = trace

    def append_bot_trace_step(self, step: str, status: str = "ok") -> None:
        """Append a human-readable reasoning step for explainable traces."""
        try:
            trace = list(getattr(self._client, "bot_trace", None) or [])
        except KeyError:
            trace = []
        trace.append({"step": step.strip(), "status": status})
        self._client.bot_trace = trace

    def get_bot_trace(self) -> List[dict]:
        """Return current bot_trace list (for saving to DB)."""
        try:
            t = getattr(self._client, "bot_trace", None) or []
            return list(t) if isinstance(t, list) else []
        except KeyError:
            return []

    def clear_for_new_question(self) -> None:
        """Reset blackboard state for a new top-level question (e.g. after showing answer or starting fresh)."""
        self._client.user_question = None
        self._client.standalone_question = None
        self._client.turn_history = []
        self._client.is_ambiguous = None
        self._client.current_related_entities = []
        self._client.answer = None
        self._client.bot_trace = []
        self._client.viable_objects = []
        try:
            self._client.used_ambiguous_types = []
        except KeyError:
            pass
        self._client.current_ambiguous_type = None
