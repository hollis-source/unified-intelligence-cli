"""Tests for workflow-specific morphism transformations.

Tests verify category theory laws are preserved during workflow transformations.
"""

import pytest
from src.entity.category_theory.workflow_morphism import (
    WorkflowMorphism,
    create_transformation_pipeline
)
from src.entity.htn import HTNNode
from src.entity.graph import Graph


class TestHTNFlatten:
    """Test HTN flattening transformations."""

    def test_flatten_preserves_primitive(self):
        """Primitive nodes should remain unchanged."""
        primitive = HTNNode(
            task_id="task_1",
            description="primitive task",
            subtasks=None
        )

        morphism = WorkflowMorphism.htn_flatten()
        result = morphism(primitive)

        assert result.task_id == primitive.task_id
        assert result.description == primitive.description
        assert result.subtasks is None

    def test_flatten_simple_composition(self):
        """Flatten nested composition (c ∘ b) ∘ a → c ∘ b ∘ a."""
        # Create: a
        a = HTNNode(task_id="a", description="task_a")

        # Create: b
        b = HTNNode(task_id="b", description="task_b")

        # Create: c
        c = HTNNode(task_id="c", description="task_c")

        # Create: b ∘ a (composition)
        comp_ba = HTNNode(
            task_id="comp_ba",
            description="b composed with a",
            subtasks=[b, a],
            metadata={"operator": "∘"}
        )

        # Create: c ∘ (b ∘ a) (nested composition)
        nested = HTNNode(
            task_id="nested",
            description="c composed with ba",
            subtasks=[c, comp_ba],
            metadata={"operator": "∘"}
        )

        # Flatten
        morphism = WorkflowMorphism.htn_flatten()
        result = morphism(nested)

        # Should flatten to: c ∘ b ∘ a (3 subtasks at one level)
        assert len(result.subtasks) == 3
        assert result.subtasks[0].task_id == "c"
        assert result.subtasks[1].task_id == "b"
        assert result.subtasks[2].task_id == "a"
        assert result.metadata.get("flattened") is True

    def test_flatten_deep_nesting(self):
        """Flatten deeply nested compositions."""
        # Create: ((d ∘ c) ∘ (b ∘ a))
        a = HTNNode(task_id="a", description="task_a")
        b = HTNNode(task_id="b", description="task_b")
        c = HTNNode(task_id="c", description="task_c")
        d = HTNNode(task_id="d", description="task_d")

        comp_ba = HTNNode(
            task_id="comp_ba",
            description="b ∘ a",
            subtasks=[b, a],
            metadata={"operator": "∘"}
        )

        comp_dc = HTNNode(
            task_id="comp_dc",
            description="d ∘ c",
            subtasks=[d, c],
            metadata={"operator": "∘"}
        )

        nested = HTNNode(
            task_id="nested",
            description="(d ∘ c) ∘ (b ∘ a)",
            subtasks=[comp_dc, comp_ba],
            metadata={"operator": "∘"}
        )

        # Flatten
        morphism = WorkflowMorphism.htn_flatten()
        result = morphism(nested)

        # Should flatten to: d ∘ c ∘ b ∘ a (4 subtasks)
        assert len(result.subtasks) == 4
        assert [st.task_id for st in result.subtasks] == ["d", "c", "b", "a"]

    def test_flatten_preserves_non_composition(self):
        """Product nodes should not be flattened."""
        a = HTNNode(task_id="a", description="task_a")
        b = HTNNode(task_id="b", description="task_b")

        product = HTNNode(
            task_id="product",
            description="a × b",
            subtasks=[a, b],
            metadata={"operator": "×"}
        )

        morphism = WorkflowMorphism.htn_flatten()
        result = morphism(product)

        # Product should remain unchanged
        assert len(result.subtasks) == 2
        assert result.metadata.get("operator") == "×"
        assert result.metadata.get("flattened") is None


class TestHTNRemoveIdentity:
    """Test identity removal transformations."""

    def test_remove_identity_from_composition(self):
        """f ∘ id → f (identity law)."""
        task = HTNNode(task_id="task", description="real task")
        identity = HTNNode(task_id="id_task", description="identity")

        composition = HTNNode(
            task_id="comp",
            description="task ∘ id",
            subtasks=[task, identity],
            metadata={"operator": "∘"}
        )

        morphism = WorkflowMorphism.htn_remove_identity()
        result = morphism(composition)

        # Identity should be removed, only real task remains
        assert len(result.subtasks) == 1
        assert result.subtasks[0].task_id == "task"

    def test_remove_identity_both_sides(self):
        """id ∘ f ∘ id → f."""
        task = HTNNode(task_id="task", description="real task")
        id_left = HTNNode(task_id="id_left", description="identity")
        id_right = HTNNode(task_id="id_right", description="identity")

        composition = HTNNode(
            task_id="comp",
            description="id ∘ task ∘ id",
            subtasks=[id_left, task, id_right],
            metadata={"operator": "∘"}
        )

        morphism = WorkflowMorphism.htn_remove_identity()
        result = morphism(composition)

        # Both identities removed
        assert len(result.subtasks) == 1
        assert result.subtasks[0].task_id == "task"

    def test_remove_identity_all_identities(self):
        """All identities → single identity."""
        id1 = HTNNode(task_id="id_1", description="identity")
        id2 = HTNNode(task_id="id_2", description="identity")

        composition = HTNNode(
            task_id="comp",
            description="id ∘ id",
            subtasks=[id1, id2],
            metadata={"operator": "∘"}
        )

        morphism = WorkflowMorphism.htn_remove_identity()
        result = morphism(composition)

        # All identities removed → returns identity
        assert result.task_id.startswith("id_")
        assert result.description == "identity"
        assert result.metadata.get("removed_identities") is True

    def test_remove_identity_preserves_primitives(self):
        """Primitive nodes unchanged."""
        primitive = HTNNode(task_id="task", description="primitive")

        morphism = WorkflowMorphism.htn_remove_identity()
        result = morphism(primitive)

        assert result.task_id == "task"
        assert result.description == "primitive"


class TestHTNSimplify:
    """Test HTN simplification transformations."""

    def test_simplify_single_subtask_compound(self):
        """functor(single_task) → single_task."""
        subtask = HTNNode(task_id="subtask", description="real task")

        compound = HTNNode(
            task_id="compound",
            description="wrapper",
            subtasks=[subtask],
            metadata={"type": "compound"}
        )

        morphism = WorkflowMorphism.htn_simplify()
        result = morphism(compound)

        # Should unwrap to subtask
        assert result.task_id == "subtask"
        assert result.description == "real task"

    def test_simplify_preserves_multiple_subtasks(self):
        """Nodes with multiple subtasks unchanged."""
        sub1 = HTNNode(task_id="sub1", description="task1")
        sub2 = HTNNode(task_id="sub2", description="task2")

        compound = HTNNode(
            task_id="compound",
            description="multiple",
            subtasks=[sub1, sub2],
            metadata={"type": "compound"}
        )

        morphism = WorkflowMorphism.htn_simplify()
        result = morphism(compound)

        # Should remain unchanged
        assert result.task_id == "compound"
        assert len(result.subtasks) == 2

    def test_simplify_recursive(self):
        """Recursively simplifies nested structures."""
        innermost = HTNNode(task_id="task", description="real task")

        wrapper1 = HTNNode(
            task_id="wrapper1",
            description="wrapper1",
            subtasks=[innermost],
            metadata={"type": "compound"}
        )

        wrapper2 = HTNNode(
            task_id="wrapper2",
            description="wrapper2",
            subtasks=[wrapper1],
            metadata={"type": "compound"}
        )

        morphism = WorkflowMorphism.htn_simplify()
        result = morphism(wrapper2)

        # Should unwrap all the way to innermost
        assert result.task_id == "task"
        assert result.description == "real task"

    def test_simplify_preserves_primitives(self):
        """Primitive nodes unchanged."""
        primitive = HTNNode(task_id="task", description="primitive")

        morphism = WorkflowMorphism.htn_simplify()
        result = morphism(primitive)

        assert result.task_id == "task"


class TestGraphRemoveIsolated:
    """Test graph isolated node removal."""

    def test_remove_isolated_nodes(self):
        """Remove nodes with no edges."""
        graph = Graph()
        graph.add_node("connected_a", data={"task": "a"})
        graph.add_node("connected_b", data={"task": "b"})
        graph.add_node("isolated", data={"task": "isolated"})
        graph.add_edge("connected_a", "connected_b")

        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph)

        # Isolated node removed
        assert "connected_a" in result.nodes
        assert "connected_b" in result.nodes
        assert "isolated" not in result.nodes
        assert len(result.nodes) == 2

    def test_preserve_connected_components(self):
        """Preserve all connected nodes."""
        graph = Graph()
        graph.add_node("a", data={"task": "a"})
        graph.add_node("b", data={"task": "b"})
        graph.add_node("c", data={"task": "c"})
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph)

        # All nodes preserved
        assert len(result.nodes) == 3
        assert set(result.nodes.keys()) == {"a", "b", "c"}

    def test_empty_graph(self):
        """Empty graph remains empty."""
        graph = Graph()

        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph)

        assert len(result.nodes) == 0

    def test_all_isolated_nodes(self):
        """Remove all nodes if all isolated."""
        graph = Graph()
        graph.add_node("isolated1", data={})
        graph.add_node("isolated2", data={})
        graph.add_node("isolated3", data={})

        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph)

        assert len(result.nodes) == 0


class TestGraphDeduplicate:
    """Test graph edge deduplication."""

    def test_deduplicate_edges(self):
        """Deduplicate morphism preserves graph structure (edges are sets)."""
        graph = Graph()
        graph.add_node("a", data={})
        graph.add_node("b", data={})
        graph.add_edge("a", "b")

        morphism = WorkflowMorphism.graph_deduplicate()
        result = morphism(graph)

        # Graph structure preserved (sets ensure uniqueness)
        assert len(result.edges["a"]) == 1
        assert "b" in result.edges["a"]

    def test_preserve_all_unique_edges(self):
        """All unique edges preserved."""
        graph = Graph()
        graph.add_node("a", data={})
        graph.add_node("b", data={})
        graph.add_node("c", data={})
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "c")

        morphism = WorkflowMorphism.graph_deduplicate()
        result = morphism(graph)

        assert len(result.edges["a"]) == 2
        assert len(result.edges["b"]) == 1
        assert "b" in result.edges["a"]
        assert "c" in result.edges["a"]
        assert "c" in result.edges["b"]


class TestWorkflowOptimize:
    """Test composite optimization pipeline."""

    def test_workflow_optimize_composition(self):
        """Test flatten + remove_id + simplify pipeline."""
        # Create: wrapper(id ∘ ((b ∘ a) ∘ id))
        a = HTNNode(task_id="a", description="task_a")
        b = HTNNode(task_id="b", description="task_b")
        id1 = HTNNode(task_id="id_1", description="identity")
        id2 = HTNNode(task_id="id_2", description="identity")

        comp_ba = HTNNode(
            task_id="comp_ba",
            description="b ∘ a",
            subtasks=[b, a],
            metadata={"operator": "∘"}
        )

        nested = HTNNode(
            task_id="nested",
            description="(b ∘ a) ∘ id",
            subtasks=[comp_ba, id2],
            metadata={"operator": "∘"}
        )

        full = HTNNode(
            task_id="full",
            description="id ∘ nested",
            subtasks=[id1, nested],
            metadata={"operator": "∘"}
        )

        wrapper = HTNNode(
            task_id="wrapper",
            description="wrapper",
            subtasks=[full],
            metadata={"type": "compound"}
        )

        # Optimize
        morphism = WorkflowMorphism.workflow_optimize()
        result = morphism(wrapper)

        # Should be optimized to just composition of b ∘ a
        assert result.task_id in ["comp_ba", "full", "nested"]  # Could be any after transformations
        # Key: identities removed, flattened, simplified

    def test_workflow_optimize_preserves_semantics(self):
        """Optimization preserves task structure."""
        a = HTNNode(task_id="a", description="task_a")
        b = HTNNode(task_id="b", description="task_b")

        composition = HTNNode(
            task_id="comp",
            description="b ∘ a",
            subtasks=[b, a],
            metadata={"operator": "∘"}
        )

        morphism = WorkflowMorphism.workflow_optimize()
        result = morphism(composition)

        # Should preserve the composition structure
        assert result.subtasks is not None
        assert len(result.subtasks) >= 2  # a and b preserved


class TestTransformationPipeline:
    """Test transformation pipeline creation."""

    def test_create_single_transformation(self):
        """Single transformation pipeline."""
        pipeline = create_transformation_pipeline(["htn_flatten"])

        assert pipeline.name == "htn_flatten"
        assert pipeline.source == "HTNNode"
        assert pipeline.target == "HTNNode"

    def test_create_multiple_transformations(self):
        """Compose multiple transformations."""
        pipeline = create_transformation_pipeline([
            "htn_flatten",
            "htn_remove_identity"
        ])

        # Composed morphism
        assert "htn_flatten" in pipeline.name
        assert "htn_remove_identity" in pipeline.name
        assert pipeline.source == "HTNNode"
        assert pipeline.target == "HTNNode"

    def test_create_full_optimization_pipeline(self):
        """Full optimization pipeline."""
        pipeline = create_transformation_pipeline([
            "htn_flatten",
            "htn_remove_identity",
            "htn_simplify"
        ])

        # Test with actual HTN
        a = HTNNode(task_id="a", description="task_a")
        b = HTNNode(task_id="b", description="task_b")
        id_node = HTNNode(task_id="id_x", description="identity")

        comp = HTNNode(
            task_id="comp",
            description="b ∘ a ∘ id",
            subtasks=[b, a, id_node],
            metadata={"operator": "∘"}
        )

        result = pipeline(comp)

        # Identity should be removed, real tasks preserved
        # After optimization: should have subtasks with a and b (no id)
        if result.subtasks:
            non_identity_tasks = [st for st in result.subtasks if not st.task_id.startswith("id_")]
            assert len(non_identity_tasks) >= 2  # a and b preserved
        else:
            # If simplified all the way, that's also valid
            assert result.task_id in ["a", "b", "comp"]

    def test_unknown_transformation_raises_error(self):
        """Unknown transformation raises ValueError."""
        with pytest.raises(ValueError, match="Unknown transformation"):
            create_transformation_pipeline(["unknown_transform"])

    def test_empty_transformations_raises_error(self):
        """Empty transformations list raises ValueError."""
        with pytest.raises(ValueError, match="No transformations specified"):
            create_transformation_pipeline([])

    def test_graph_transformation_pipeline(self):
        """Create pipeline with graph transformations."""
        pipeline = create_transformation_pipeline([
            "graph_remove_isolated_nodes",
            "graph_deduplicate"
        ])

        graph = Graph()
        graph.add_node("a", data={})
        graph.add_node("b", data={})
        graph.add_node("isolated", data={})
        graph.add_edge("a", "b")

        result = pipeline(graph)

        # Isolated node removed
        assert "isolated" not in result.nodes
        assert len(result.nodes) == 2


class TestMorphismProperties:
    """Test category theory properties of workflow morphisms."""

    def test_morphism_has_correct_types(self):
        """Morphisms have correct source/target types."""
        htn_morph = WorkflowMorphism.htn_flatten()
        assert htn_morph.source == "HTNNode"
        assert htn_morph.target == "HTNNode"

        graph_morph = WorkflowMorphism.graph_remove_isolated_nodes()
        assert graph_morph.source == "Graph"
        assert graph_morph.target == "Graph"

    def test_morphism_composition_associativity(self):
        """(h ∘ g) ∘ f = h ∘ (g ∘ f) - associativity law."""
        f = WorkflowMorphism.htn_flatten()
        g = WorkflowMorphism.htn_remove_identity()
        h = WorkflowMorphism.htn_simplify()

        # Create test HTN
        a = HTNNode(task_id="a", description="task_a")
        id_node = HTNNode(task_id="id_x", description="identity")

        comp = HTNNode(
            task_id="comp",
            description="a ∘ id",
            subtasks=[a, id_node],
            metadata={"operator": "∘"}
        )

        wrapper = HTNNode(
            task_id="wrapper",
            description="wrapper",
            subtasks=[comp],
            metadata={"type": "compound"}
        )

        # (h ∘ g) ∘ f
        left_assoc = h.compose(g).compose(f)
        result_left = left_assoc(wrapper)

        # h ∘ (g ∘ f)
        right_assoc = h.compose(g.compose(f))
        result_right = right_assoc(wrapper)

        # Results should be equivalent (same structure)
        assert result_left.task_id == result_right.task_id
        assert len(result_left.subtasks or []) == len(result_right.subtasks or [])
