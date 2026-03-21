from typing import Optional

import py_trees
from clients import MilvusHybridEntityStore
from langchain_openai import ChatOpenAI
from nodes import (AmbiguityClassifierNode, AmbiguityDetectorNode,
                   AmbiguousRepairNode, Blackboard,
                   CheckNotAmbiguousNode, LoadHistoryNode, SaveMessageNode,
                   StandaloneQuestionNode, VectorSearchNode)
from nodes.action_executor import ActionExecutor
from nodes.perform_action_node import PerformActionNode


def build_tree(
    bb: Blackboard,
    llm: ChatOpenAI,
    vecdb: MilvusHybridEntityStore,
    *,
    action_executor: Optional[ActionExecutor] = None,
) -> py_trees.trees.BehaviourTree:
    """
    Build the main behaviour tree.

    Clear path (not ambiguous): PerformActionNode — no LLM answer; uses pluggable
    `action_executor` (default: plain text "I performed the {user_request}").
    Swap `action_executor` for Gazebo/simulation later.

    Ambiguous path: optional vector search + classifier + repair (LLM).
    """

    # Root sequence: load history, standalone question, ambiguity, path, save
    root = py_trees.composites.Sequence(name="Root", memory=True)

    # Step 1: Load previous messages for conversation (sets turn_history)
    load_history = LoadHistoryNode(
        name="LoadHistory",
        bb=bb,
        top_k=20,
    )
    root.add_child(load_history)

    # Step 2: Form standalone question (all downstream nodes use this)
    standalone_question_node = StandaloneQuestionNode(
        name="StandaloneQuestion",
        bb=bb,
        llm=llm,
        max_history_lines=12,
    )
    root.add_child(standalone_question_node)

    # Step 2: Detect ambiguity (uses standalone_question)
    ambiguity_detector = AmbiguityDetectorNode(
        name="AmbiguityDetector",
        bb=bb,
        llm=llm,
        max_history_lines=10,
    )
    root.add_child(ambiguity_detector)

    # Step 3: Selector (Fallback) - choose between clear path and ambiguous path
    path_selector = py_trees.composites.Selector(name="PathSelector", memory=False)

    # Clear path: if not ambiguous, perform action (template or custom executor)
    clear_path = py_trees.composites.Sequence(name="ClearPath", memory=True)

    # Check that question is not ambiguous
    check_not_ambiguous = CheckNotAmbiguousNode(
        name="CheckNotAmbiguous",
        bb=bb,
    )
    clear_path.add_child(check_not_ambiguous)

    perform_action = PerformActionNode(
        name="PerformAction",
        bb=bb,
        executor=action_executor,
    )
    clear_path.add_child(perform_action)

    # Ambiguous path: optional entities, then classify type, then repair
    ambiguous_path = py_trees.composites.Sequence(name="AmbiguousPath", memory=True)
    # Optional: try to get related entities for repair
    optional_entities = py_trees.composites.Selector(
        name="OptionalEntities", memory=False
    )
    ambiguous_vector_search = VectorSearchNode(
        name="AmbiguousVectorSearch",
        bb=bb,
        vecdb=vecdb,
        max_history_lines=12,
    )
    optional_entities.add_child(ambiguous_vector_search)
    optional_entities.add_child(py_trees.behaviours.Success(name="NoEntities"))
    ambiguous_path.add_child(optional_entities)
    ambiguous_classifier = AmbiguityClassifierNode(
        name="AmbiguityClassifier",
        bb=bb,
        llm=llm,
        max_history_lines=10,
    )
    ambiguous_path.add_child(ambiguous_classifier)
    ambiguous_repair = AmbiguousRepairNode(
        name="AmbiguousRepair",
        bb=bb,
        llm=llm,
        max_history_lines=10,
    )
    ambiguous_path.add_child(ambiguous_repair)

    # Add both paths to selector (clear path first, then ambiguous)
    path_selector.add_child(clear_path)
    path_selector.add_child(ambiguous_path)

    root.add_child(path_selector)

    # Step 5: Save user + assistant messages to DB (with bot_trace)
    save_message = SaveMessageNode(name="SaveMessage", bb=bb)
    root.add_child(save_message)

    return py_trees.trees.BehaviourTree(root)
