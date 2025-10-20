"""Workflow-specific morphisms for category-theoretic transformations.

Provides specialized morphisms for transforming workflow structures (HTN, Graph)
while preserving semantic correctness through category theory laws.
"""

from typing import List
from src.entity.category_theory import Morphism
from src.entity.htn import HTNNode
from src.entity.graph import Graph


class WorkflowMorphism:
    """Factory for creating workflow-specific morphisms.

    Provides transformations for:
    - HTN structure (flatten, simplify, normalize)
    - Graph structure (parallelize, optimize, reorder)
    - Workflow optimization (remove redundant nodes)

    All transformations preserve workflow semantics via category laws.
    """

    @staticmethod
    def flatten_htn() -> Morphism[HTNNode, HTNNode]:
        """Flatten nested composition into single level.

        Transformation:
            (c ∘ b) ∘ a  →  c ∘ b ∘ a

        Preserves:
            - Execution order
            - Task dependencies
            - Composition semantics

        Returns:
            Morphism that flattens HTN composition
        """
        def flatten_transform(htn: HTNNode) -> HTNNode:
            """Flatten nested composition nodes."""
            if htn.subtasks is None or htn.is_primitive():
                return htn

            # Check if this is a composition with nested composition
            if htn.metadata.get("operator") == "∘" and htn.subtasks:
                flattened_subtasks = []

                for subtask in htn.subtasks:
                    # Recursively flatten subtask
                    flattened = flatten_transform(subtask)

                    # If subtask is also a composition, merge its subtasks
                    if flattened.metadata.get("operator") == "∘" and flattened.subtasks:
                        flattened_subtasks.extend(flattened.subtasks)
                    else:
                        flattened_subtasks.append(flattened)

                # Create new HTN with flattened subtasks
                return HTNNode(
                    task_id=htn.task_id,
                    description=htn.description,
                    subtasks=flattened_subtasks,
                    metadata={**htn.metadata, "flattened": True}
                )

            # For products or functors, recursively flatten subtasks
            if htn.subtasks:
                flattened_subtasks = [flatten_transform(st) for st in htn.subtasks]
                return HTNNode(
                    task_id=htn.task_id,
                    description=htn.description,
                    subtasks=flattened_subtasks,
                    metadata=htn.metadata
                )

            return htn

        return Morphism(
            name="htn_flatten",
            source="HTNNode",
            target="HTNNode",
            transform=flatten_transform
        )

    @staticmethod
    def remove_htn_identity() -> Morphism[HTNNode, HTNNode]:
        """Remove identity transformations from HTN.

        Transformation:
            f ∘ id  →  f
            id ∘ f  →  f

        Category Law:
            Identity morphism id satisfies: f ∘ id = id ∘ f = f

        Returns:
            Morphism that removes identity nodes
        """
        def remove_identity_transform(htn: HTNNode) -> HTNNode:
            """Remove identity nodes from composition."""
            if htn.is_primitive():
                return htn

            if htn.subtasks:
                # Filter out identity subtasks
                filtered_subtasks = []
                for subtask in htn.subtasks:
                    # Recursively process
                    processed = remove_identity_transform(subtask)

                    # Skip if it's an identity (id_* pattern or empty)
                    if processed.task_id.startswith("id_") or processed.description == "identity":
                        continue

                    filtered_subtasks.append(processed)

                # If all subtasks removed, return identity
                if not filtered_subtasks:
                    return HTNNode(
                        task_id=f"id_{htn.task_id}",
                        description="identity",
                        metadata={"removed_identities": True}
                    )

                # Return with filtered subtasks
                return HTNNode(
                    task_id=htn.task_id,
                    description=htn.description,
                    subtasks=filtered_subtasks,
                    metadata=htn.metadata
                )

            return htn

        return Morphism(
            name="htn_remove_identity",
            source="HTNNode",
            target="HTNNode",
            transform=remove_identity_transform
        )


    # Backward compatibility alias (deprecated)
    @staticmethod
    def htn_flatten() -> Morphism[HTNNode, HTNNode]:
        """DEPRECATED: Use flatten_htn() instead."""
        import warnings
        warnings.warn(
            "htn_flatten() is deprecated, use flatten_htn() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return WorkflowMorphism.flatten_htn()

    # Backward compatibility alias (deprecated)
    @staticmethod
    def htn_remove_identity() -> Morphism[HTNNode, HTNNode]:
        """DEPRECATED: Use remove_htn_identity() instead."""
        import warnings
        warnings.warn(
            "htn_remove_identity() is deprecated, use remove_htn_identity() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return WorkflowMorphism.remove_htn_identity()
    @staticmethod
    def simplify_htn() -> Morphism[HTNNode, HTNNode]:
        """Simplify HTN by removing single-subtask nodes.

        Transformation:
            functor(single_task)  →  single_task

        Preserves execution semantics while reducing nesting.

        Returns:
            Morphism that simplifies HTN structure
        """
        def simplify_transform(htn: HTNNode) -> HTNNode:
            """Simplify by unwrapping single-subtask nodes."""
            if htn.is_primitive():
                return htn

            if htn.subtasks:
                # Recursively simplify subtasks
                simplified_subtasks = [simplify_transform(st) for st in htn.subtasks]

                # If compound node with single subtask, unwrap it
                if len(simplified_subtasks) == 1 and htn.is_compound():
                    return simplified_subtasks[0]

                return HTNNode(
                    task_id=htn.task_id,
                    description=htn.description,
                    subtasks=simplified_subtasks,
                    metadata=htn.metadata
                )

            return htn

        return Morphism(
            name="htn_simplify",
            source="HTNNode",
            target="HTNNode",
            transform=simplify_transform
        )

    # Backward compatibility alias (deprecated)
    @staticmethod
    def htn_simplify() -> Morphism[HTNNode, HTNNode]:
        """DEPRECATED: Use simplify_htn() instead."""
        import warnings
        warnings.warn(
            "htn_simplify() is deprecated, use simplify_htn() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return WorkflowMorphism.simplify_htn()

    @staticmethod
    def graph_remove_isolated_nodes() -> Morphism[Graph, Graph]:
        """Remove isolated nodes from graph (no edges).

        Transformation:
            Graph with isolated nodes  →  Graph without isolated nodes

        Preserves:
            - All connected components
            - Dependency relationships
            - Topological order

        Returns:
            Morphism that removes isolated graph nodes
        """
        def remove_isolated_transform(graph: Graph) -> Graph:
            """Remove nodes with no incoming or outgoing edges."""
            # Find isolated nodes (no edges)
            isolated = []
            for node_id in graph.nodes.keys():
                has_predecessors = any(
                    node_id in successors
                    for successors in graph.edges.values()
                )
                has_successors = len(graph.edges.get(node_id, set())) > 0

                if not has_predecessors and not has_successors:
                    isolated.append(node_id)

            # Create new graph without isolated nodes
            new_graph = Graph()
            for node_id, node in graph.nodes.items():
                if node_id not in isolated:
                    new_graph.add_node(node_id, data=node.data)

            # Copy all edges
            for from_node, successors in graph.edges.items():
                if from_node not in isolated:
                    for to_node in successors:
                        if to_node not in isolated:
                            new_graph.add_edge(from_node, to_node)

            return new_graph

        return Morphism(
            name="graph_remove_isolated",
            source="Graph",
            target="Graph",
            transform=remove_isolated_transform
        )

    @staticmethod
    def graph_deduplicate() -> Morphism[Graph, Graph]:
        """Remove duplicate edges from graph.

        Transformation:
            Graph with duplicate edges  →  Graph with unique edges

        Preserves:
            - Node structure
            - Dependency relationships (each unique edge once)

        Returns:
            Morphism that deduplicates graph edges
        """
        def deduplicate_transform(graph: Graph) -> Graph:
            """Remove duplicate edges (already handled by Graph.edges as set)."""
            # Graph.edges are already sets, so duplicates automatically removed
            # But we rebuild to ensure clean structure

            new_graph = Graph()

            # Copy all nodes
            for node_id, node in graph.nodes.items():
                new_graph.add_node(node_id, data=node.data)

            # Copy unique edges (sets handle duplicates)
            for from_node, successors in graph.edges.items():
                for to_node in successors:
                    new_graph.add_edge(from_node, to_node)

            return new_graph

        return Morphism(
            name="graph_deduplicate",
            source="Graph",
            target="Graph",
            transform=deduplicate_transform
        )

    @staticmethod
    def optimize_workflow() -> Morphism[HTNNode, HTNNode]:
        """Composite transformation: flatten + remove identity + simplify.

        Applies multiple optimization steps in sequence using morphism composition.

        Returns:
            Composed morphism representing full optimization pipeline
        """
        from src.entity.category_theory.morphism import compose_chain

        # Create individual transformation morphisms
        flatten = WorkflowMorphism.flatten_htn()
        remove_id = WorkflowMorphism.remove_htn_identity()
        simplify = WorkflowMorphism.simplify_htn()

        # Compose: simplify ∘ remove_id ∘ flatten
        # (flatten first, then remove identities, then simplify)
        return compose_chain(flatten, remove_id, simplify)

    # Backward compatibility alias (deprecated)
    @staticmethod
    def workflow_optimize() -> Morphism[HTNNode, HTNNode]:
        """DEPRECATED: Use optimize_workflow() instead."""
        import warnings
        warnings.warn(
            "workflow_optimize() is deprecated, use optimize_workflow() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return WorkflowMorphism.optimize_workflow()


def create_transformation_pipeline(
    transformations: List[str]
) -> Morphism:
    """Create a transformation pipeline from named transformations.

    Args:
        transformations: List of transformation names (e.g., ["htn_flatten", "htn_simplify"])

    Returns:
        Composed morphism representing the transformation pipeline

    Raises:
        ValueError: If transformation name is unknown

    Example:
        pipeline = create_transformation_pipeline(["htn_flatten", "htn_simplify"])
        optimized_htn = pipeline(original_htn)
    """
    from src.entity.category_theory.morphism import compose_chain

    # Map transformation names to factory methods
    transform_map = {
        "htn_flatten": WorkflowMorphism.htn_flatten,
        "htn_remove_identity": WorkflowMorphism.htn_remove_identity,
        "htn_simplify": WorkflowMorphism.htn_simplify,
        "graph_remove_isolated_nodes": WorkflowMorphism.graph_remove_isolated_nodes,
        "graph_deduplicate": WorkflowMorphism.graph_deduplicate,
        "workflow_optimize": WorkflowMorphism.workflow_optimize,
    }

    # Create morphisms from names
    morphisms = []
    for name in transformations:
        if name not in transform_map:
            raise ValueError(
                f"Unknown transformation '{name}'. "
                f"Available: {list(transform_map.keys())}"
            )
        morphisms.append(transform_map[name]())

    if not morphisms:
        raise ValueError("No transformations specified")

    if len(morphisms) == 1:
        return morphisms[0]

    # Compose all transformations
    return compose_chain(*morphisms)
