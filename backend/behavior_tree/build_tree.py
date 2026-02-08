import py_trees
from clients import MilvusHybridEntityStore
from langchain_openai import ChatOpenAI
from nodes import (AmbiguityClassifierNode, AmbiguityDetectorNode,
                   AmbiguousRepairNode, AnswerNode, Blackboard,
                   CheckNotAmbiguousNode, PostRepairRouterNode,
                   StandaloneQuestionNode, VectorSearchNode)


def build_tree(
    bb: Blackboard,
    llm: ChatOpenAI,
    vecdb: MilvusHybridEntityStore,
) -> py_trees.trees.BehaviourTree:

    # Root sequence: standalone question first, then ambiguity detection
    root = py_trees.composites.Sequence(name="Root", memory=True)

    # Step 1: Form standalone question (all downstream nodes use this)
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
    post_repair_router = PostRepairRouterNode(
        name="PostRepairRouter",
        bb=bb,
        max_preference_turns=3,
    )
    ambiguous_path.add_child(post_repair_router)

    # Add both paths to selector (clear path first, then ambiguous)
    path_selector.add_child(clear_path)
    path_selector.add_child(ambiguous_path)

    # Add selector to root
    root.add_child(path_selector)

    return py_trees.trees.BehaviourTree(root)
