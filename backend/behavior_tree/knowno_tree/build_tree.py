from typing import Optional

import py_trees
from clients import MilvusHybridEntityStore
from langchain_openai import ChatOpenAI
from nodes_knowno import (KnownoAmbiguityResponseNode, KnownoAmbiguousClassifierNode,
                   Blackboard, EntitiesPredictorNode, EntityResolveNode,
                   EntityActionGeneratorNode, CheckNotAmbiguousNode, LoadHistoryNode,
                   SaveMessageNode, StandaloneQuestionNode, VectorSearchNode)
from nodes_knowno.action_executor import ActionExecutor
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

    Flow: after standalone request, entities are predicted then **resolved** (history +
    standalone drop already-settled names), then vector search grounds what remains.
    The same ``current_related_entities`` list is reused for ambiguity + both routes.
    """

    # Root sequence: load history, standalone request, vector search, ambiguity, path, save
    root = py_trees.composites.Sequence(name="Root", memory=True)

    # Step 1: Load previous messages for conversation (sets turn_history)
    load_history = LoadHistoryNode(
        name="LoadHistory",
        bb=bb,
        top_k=30,
    )
    root.add_child(load_history)

    # Step 2: LLM — one standalone request line (blackboard key: standalone_question)
    standalone_question_node = StandaloneQuestionNode(
        name="StandaloneQuestion",
        bb=bb,
        llm=llm,
        max_history_lines=20,
    )
    root.add_child(standalone_question_node)

    # Step 2.5: Generate potential entity actions for question
    entity_prediction_node = EntitiesPredictorNode(
        name="EntitiesPredictor",
        bb=bb,
        llm=llm,
    )
    root.add_child(entity_prediction_node)

    entity_resolve_node = EntityResolveNode(
        name="EntityResolve",
        bb=bb,
        llm=llm,
        max_history_lines=20,
    )
    root.add_child(entity_resolve_node)

    # Step 3: Vector search once — populates current_related_entities for ambiguity + both routes
    vector_search = VectorSearchNode(
        name="VectorSearch",
        bb=bb,
        vecdb=vecdb,
        max_history_lines=16,
    )
    root.add_child(vector_search)

    # Step 3.5: Generate entity actions for grounded entities
    entity_action_generation_node = EntityActionGeneratorNode(
        name="EntityActionGeneration",
        bb=bb,
        llm=llm,
    )
    root.add_child(entity_action_generation_node)

    # Step 4: Detect ambiguity (uses standalone_question + turn_history + related entities)
    ambiguity_detector = KnownoAmbiguousClassifierNode(
        name="AmbiguityDetector",
        bb=bb,
        llm=llm,
        max_history_lines=16,
    )
    root.add_child(ambiguity_detector)

    # Step 5: Selector (Fallback) — clear path vs ambiguous path
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

    # Ambiguous path: entities already on blackboard; classify type, then repair
    ambiguous_path = py_trees.composites.Sequence(name="AmbiguousPath", memory=True)
    ambiguous_repair = KnownoAmbiguityResponseNode(
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

    # Step 6: Save user + assistant messages to DB (with bot_trace)
    save_message = SaveMessageNode(name="SaveMessage", bb=bb)
    root.add_child(save_message)

    return py_trees.trees.BehaviourTree(root)
