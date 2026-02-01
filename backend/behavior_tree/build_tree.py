import py_trees
from clients import MilvusHybridEntityStore
from langchain_openai import ChatOpenAI
from nodes import (AmbiguityDetectorNode, AmbiguousPlaceholderNode, AnswerNode,
                   Blackboard, CheckNotAmbiguousNode, VectorSearchNode)


def build_tree(
    bb: Blackboard,
    llm: ChatOpenAI,
    vecdb: MilvusHybridEntityStore,
) -> py_trees.trees.BehaviourTree:

    # Root sequence: always runs ambiguity detection first
    root = py_trees.composites.Sequence(name="Root", memory=True)

    # Step 1: Detect ambiguity
    ambiguity_detector = AmbiguityDetectorNode(
        name="AmbiguityDetector",
        bb=bb,
        llm=llm,
        max_history_lines=10,
    )
    root.add_child(ambiguity_detector)

    # Step 2: Selector (Fallback) - choose between clear path and ambiguous path
    path_selector = py_trees.composites.Selector(name="PathSelector", memory=False)

    # Clear path: if not ambiguous, search and answer
    clear_path = py_trees.composites.Sequence(name="ClearPath", memory=True)

    # Check that question is not ambiguous
    check_not_ambiguous = CheckNotAmbiguousNode(
        name="CheckNotAmbiguous",
        bb=bb,
    )
    clear_path.add_child(check_not_ambiguous)

    # Vector search for related entities
    vector_search = VectorSearchNode(
        name="VectorSearch",
        bb=bb,
        vecdb=vecdb,
        max_history_lines=12,
    )
    clear_path.add_child(vector_search)

    # Generate answer using entities
    answer_node = AnswerNode(
        name="Answer",
        bb=bb,
        llm=llm,
        max_history_lines=10,
    )
    clear_path.add_child(answer_node)

    # Ambiguous path: placeholder response
    ambiguous_placeholder = AmbiguousPlaceholderNode(
        name="AmbiguousPlaceholder",
        bb=bb,
    )

    # Add both paths to selector (clear path first, then ambiguous)
    path_selector.add_child(clear_path)
    path_selector.add_child(ambiguous_placeholder)

    # Add selector to root
    root.add_child(path_selector)

    return py_trees.trees.BehaviourTree(root)
