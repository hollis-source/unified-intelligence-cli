# tests/unit/entity/category_theory/test_workflow_morphism_comprehensive.py
import pytest
from src.entity.category_theory.workflow_morphism import (
    WorkflowMorphism,
    create_transformation_pipeline
)
from src.entity.category_theory.morphism import Morphism
from src.entity.htn.htn_node import HTNNode
from src.entity.graph.graph import Graph


@pytest.fixture
def primitive_htn():
    """Create a primitive HTN node (no subtasks)."""
    return HTNNode(task_id="task1", description="primitive task", subtasks=None, metadata={})


@pytest.fixture
def nested_composition_htn():
    """Create a nested composition: ((c ∘ b) ∘ a)"""
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    c = HTNNode(task_id="c", description="task c", subtasks=None, metadata={})
    
    # (b ∘ a)
    inner = HTNNode(
        task_id="inner",
        description="composition",
        subtasks=[b, a],
        metadata={"operator": "∘"}
    )
    
    # ((c ∘ b) ∘ a) = (c ∘ inner)
    outer = HTNNode(
        task_id="outer",
        description="composition",
        subtasks=[c, inner],
        metadata={"operator": "∘"}
    )
    
    return outer


@pytest.fixture
def non_composition_compound_htn():
    """Create a compound node that is not a composition (e.g., sequence or parallel)."""
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    c = HTNNode(task_id="c", description="task c", subtasks=None, metadata={})
    
    return HTNNode(
        task_id="sequence",
        description="sequence",
        subtasks=[a, b, c],
        metadata={"operator": "sequence"}
    )


@pytest.fixture
def deep_nested_composition_htn():
    """Create deeply nested composition: (((d ∘ c) ∘ b) ∘ a)"""
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    c = HTNNode(task_id="c", description="task c", subtasks=None, metadata={})
    d = HTNNode(task_id="d", description="task d", subtasks=None, metadata={})
    
    # (c ∘ b)
    level1 = HTNNode(task_id="level1", description="composition", subtasks=[c, b], metadata={"operator": "∘"})
    
    # ((d ∘ c) ∘ b) = (d ∘ level1)
    level2 = HTNNode(task_id="level2", description="composition", subtasks=[d, level1], metadata={"operator": "∘"})
    
    # (((d ∘ c) ∘ b) ∘ a) = (level2 ∘ a)
    outer = HTNNode(task_id="outer", description="composition", subtasks=[level2, a], metadata={"operator": "∘"})
    
    return outer


@pytest.fixture
def identity_htn():
    """Create HTN with identity nodes."""
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    id_a = HTNNode(task_id="id_a", description="identity", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    
    # (b ∘ id_a ∘ a)
    return HTNNode(
        task_id="composite",
        description="composite",
        subtasks=[b, id_a, a],
        metadata={"operator": "∘"}
    )


@pytest.fixture
def identity_only_htn():
    """Create HTN with only identity subtasks."""
    id1 = HTNNode(task_id="id_1", description="identity", subtasks=None, metadata={})
    id2 = HTNNode(task_id="id_2", description="identity", subtasks=None, metadata={})
    
    return HTNNode(
        task_id="all_id",
        description="all identity",
        subtasks=[id1, id2],
        metadata={"operator": "∘"}
    )


@pytest.fixture
def single_subtask_htn():
    """Create compound node with single subtask."""
    inner = HTNNode(task_id="inner", description="inner task", subtasks=None, metadata={})
    outer = HTNNode(
        task_id="outer",
        description="compound",
        subtasks=[inner],
        metadata={"operator": "sequence"}
    )
    return outer


@pytest.fixture
def multi_subtask_htn():
    """Create compound node with multiple subtasks."""
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    c = HTNNode(task_id="c", description="task c", subtasks=None, metadata={})
    
    return HTNNode(
        task_id="multi",
        description="multi",
        subtasks=[a, b, c],
        metadata={"operator": "sequence"}
    )


@pytest.fixture
def nested_simplify_htn():
    """Create nested structure for recursive simplification."""
    # Innermost: primitive
    inner = HTNNode(task_id="inner", description="inner", subtasks=None, metadata={})
    
    # Middle: compound with single subtask
    middle = HTNNode(
        task_id="middle",
        description="middle",
        subtasks=[inner],
        metadata={"operator": "sequence"}
    )
    
    # Outer: compound with single subtask (middle)
    outer = HTNNode(
        task_id="outer",
        description="outer",
        subtasks=[middle],
        metadata={"operator": "sequence"}
    )
    
    return outer


@pytest.fixture
def graph_with_isolated_nodes():
    """Create graph with isolated and connected nodes."""
    graph = Graph()
    graph.add_node("node1", data={"type": "task"})
    graph.add_node("node2", data={"type": "task"})
    graph.add_node("node3", data={"type": "task"})
    graph.add_node("isolated1", data={"type": "isolated"})
    graph.add_node("isolated2", data={"type": "isolated"})
    
    # Add edges: node1 -> node2, node2 -> node3
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", "node3")
    
    return graph


@pytest.fixture
def graph_no_isolated_nodes():
    """Create graph with no isolated nodes."""
    graph = Graph()
    graph.add_node("node1", data={"type": "task"})
    graph.add_node("node2", data={"type": "task"})
    graph.add_node("node3", data={"type": "task"})
    
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", "node3")
    
    return graph


@pytest.fixture
def graph_all_isolated():
    """Create graph where all nodes are isolated."""
    graph = Graph()
    graph.add_node("node1", data={"type": "task"})
    graph.add_node("node2", data={"type": "task"})
    graph.add_node("node3", data={"type": "task"})
    
    return graph


@pytest.fixture
def empty_graph():
    """Create empty graph."""
    return Graph()


@pytest.fixture
def complex_htn_for_optimize():
    """Create complex HTN for optimize_workflow test."""
    # Create: ((id_a ∘ b) ∘ id_c) with single subtask wrapper
    a = HTNNode(task_id="a", description="task a", subtasks=None, metadata={})
    b = HTNNode(task_id="b", description="task b", subtasks=None, metadata={})
    c = HTNNode(task_id="c", description="task c", subtasks=None, metadata={})
    
    # id_a and id_c
    id_a = HTNNode(task_id="id_a", description="identity", subtasks=None, metadata={})
    id_c = HTNNode(task_id="id_c", description="identity", subtasks=None, metadata={})
    
    # (b ∘ id_c) → becomes (b) after remove_id
    inner = HTNNode(
        task_id="inner",
        description="composition",
        subtasks=[b, id_c],
        metadata={"operator": "∘"}
    )
    
    # (id_a ∘ inner) → becomes (inner) after remove_id
    middle = HTNNode(
        task_id="middle",
        description="composition",
        subtasks=[id_a, inner],
        metadata={"operator": "∘"}
    )
    
    # Wrap in single-subtask compound
    outer = HTNNode(
        task_id="outer",
        description="wrapper",
        subtasks=[middle],
        metadata={"operator": "sequence"}
    )
    
    return outer


class TestWorkflowMorphism:
    def test_flatten_htn_nested_composition(self, nested_composition_htn):
        """Test flattening of nested composition: ((c ∘ b) ∘ a) → (c ∘ b ∘ a)"""
        morphism = WorkflowMorphism.flatten_htn()
        result = morphism(nested_composition_htn)
        
        # Should be flattened to 3 subtasks: c, b, a
        assert len(result.subtasks) == 3
        assert result.subtasks[0].task_id == "c"
        assert result.subtasks[1].task_id == "b"
        assert result.subtasks[2].task_id == "a"
        assert result.metadata.get("flattened") is True
        assert result.task_id == "outer"  # original task_id preserved
        assert result.description == "composition"  # original description preserved

    def test_flatten_htn_primitive_unchanged(self, primitive_htn):
        """Test that primitive HTN node remains unchanged."""
        morphism = WorkflowMorphism.flatten_htn()
        result = morphism(primitive_htn)
        
        assert result == primitive_htn
        assert result.subtasks is None
        assert "flattened" not in result.metadata

    def test_flatten_htn_non_composition_unchanged(self, non_composition_compound_htn):
        """Test that non-composition compound nodes remain unchanged."""
        morphism = WorkflowMorphism.flatten_htn()
        result = morphism(non_composition_compound_htn)
        
        assert len(result.subtasks) == 3
        assert result.metadata.get("operator") == "sequence"
        assert "flattened" not in result.metadata

    def test_flatten_htn_deeply_nested(self, deep_nested_composition_htn):
        """Test flattening of deeply nested composition."""
        morphism = WorkflowMorphism.flatten_htn()
        result = morphism(deep_nested_composition_htn)
        
        # Should be flattened to 4 subtasks: d, c, b, a
        assert len(result.subtasks) == 4
        assert [node.task_id for node in result.subtasks] == ["d", "c", "b", "a"]
        assert result.metadata.get("flattened") is True

    def test_flatten_htn_metadata_added(self, nested_composition_htn):
        """Test that flattened metadata is correctly added."""
        morphism = WorkflowMorphism.flatten_htn()
        result = morphism(nested_composition_htn)
        
        assert result.metadata.get("flattened") is True
        assert "operator" in result.metadata  # original metadata preserved

    def test_remove_htn_identity_removes_id_nodes(self, identity_htn):
        """Test removal of id_* nodes and description='identity' nodes."""
        morphism = WorkflowMorphism.remove_htn_identity()
        result = morphism(identity_htn)
        
        # id_a and id_c should be removed
        assert len(result.subtasks) == 2
        assert result.subtasks[0].task_id == "b"
        assert result.subtasks[1].task_id == "a"
        assert result.metadata.get("removed_identities") is True

    def test_remove_htn_identity_no_identities_unchanged(self, non_composition_compound_htn):
        """Test that node with no identity subtasks remains unchanged."""
        morphism = WorkflowMorphism.remove_htn_identity()
        result = morphism(non_composition_compound_htn)
        
        assert result == non_composition_compound_htn
        assert "removed_identities" not in result.metadata

    def test_remove_htn_identity_all_identities_returns_identity(self, identity_only_htn):
        """Test that when all subtasks are identities, returns identity node."""
        morphism = WorkflowMorphism.remove_htn_identity()
        result = morphism(identity_only_htn)
        
        assert result.task_id.startswith("id_")
        assert result.description == "identity"
        assert result.subtasks is None
        assert result.metadata.get("removed_identities") is True

    def test_remove_htn_identity_recursive(self, identity_htn):
        """Test recursive removal in nested structure."""
        # Create nested identity
        inner_id = HTNNode(task_id="id_inner", description="identity", subtasks=None, metadata={})
        outer_id = HTNNode(task_id="id_outer", description="identity", subtasks=[inner_id], metadata={"operator": "∘"})
        
        morphism = WorkflowMorphism.remove_htn_identity()
        result = morphism(outer_id)
        
        # Both inner and outer identity should be removed
        assert result.task_id.startswith("id_")
        assert result.description == "identity"
        assert result.subtasks is None

    def test_simplify_htn_unwrap_single_subtask(self, single_subtask_htn):
        """Test unwrapping of compound node with single subtask."""
        morphism = WorkflowMorphism.simplify_htn()
        result = morphism(single_subtask_htn)
        
        # Should be unwrapped to inner node
        assert result.task_id == "inner"
        assert result.description == "inner task"
        assert result.subtasks is None
        assert result.metadata == {}  # metadata should be from inner node

    def test_simplify_htn_multi_subtask_unchanged(self, multi_subtask_htn):
        """Test that compound node with multiple subtasks remains unchanged."""
        morphism = WorkflowMorphism.simplify_htn()
        result = morphism(multi_subtask_htn)
        
        assert result == multi_subtask_htn
        assert len(result.subtasks) == 3

    def test_simplify_htn_primitive_unchanged(self, primitive_htn):
        """Test that primitive HTN node remains unchanged."""
        morphism = WorkflowMorphism.simplify_htn()
        result = morphism(primitive_htn)
        
        assert result == primitive_htn

    def test_simplify_htn_recursive(self, nested_simplify_htn):
        """Test recursive simplification of nested single-subtask structures."""
        morphism = WorkflowMorphism.simplify_htn()
        result = morphism(nested_simplify_htn)
        
        # Should be unwrapped all the way to innermost node
        assert result.task_id == "inner"
        assert result.description == "inner"
        assert result.subtasks is None

    def test_simplify_htn_empty_subtasks_unchanged(self):
        """Test that node with empty subtasks remains unchanged."""
        htn = HTNNode(task_id="empty", description="empty", subtasks=[], metadata={})
        morphism = WorkflowMorphism.simplify_htn()
        result = morphism(htn)
        
        assert result == htn
        assert result.subtasks == []

    def test_graph_remove_isolated_nodes_removes_isolated(self, graph_with_isolated_nodes):
        """Test removal of nodes with no incoming or outgoing edges."""
        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph_with_isolated_nodes)
        
        # Isolated nodes should be removed
        assert len(result.nodes) == 3
        assert "node1" in result.nodes
        assert "node2" in result.nodes
        assert "node3" in result.nodes
        assert "isolated1" not in result.nodes
        assert "isolated2" not in result.nodes
        
        # Edges should be preserved
        assert "node1" in result.edges
        assert "node2" in result.edges["node1"]
        assert "node2" in result.edges
        assert "node3" in result.edges["node2"]
        assert len(result.edges["node1"]) == 1
        assert len(result.edges["node2"]) == 1

    def test_graph_remove_isolated_nodes_no_isolated_unchanged(self, graph_no_isolated_nodes):
        """Test that graph with no isolated nodes remains unchanged."""
        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph_no_isolated_nodes)

        assert len(result.nodes) == 3
        assert result.count_edges() == 2

    def test_graph_remove_isolated_nodes_all_isolated_returns_empty(self, graph_all_isolated):
        """Test that graph with all isolated nodes returns empty graph."""
        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph_all_isolated)
        
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_graph_remove_isolated_nodes_preserves_connected_components(self, graph_with_isolated_nodes):
        """Test that connected components are preserved after removing isolated nodes."""
        morphism = WorkflowMorphism.graph_remove_isolated_nodes()
        result = morphism(graph_with_isolated_nodes)
        
        # Verify topological order is preserved
        assert "node1" in result.edges
        assert "node2" in result.edges["node1"]
        assert "node2" in result.edges
        assert "node3" in result.edges["node2"]
        assert "node1" not in result.edges["node2"]
        assert "node3" not in result.edges["node1"]

    def test_graph_deduplicate_unique_edges_unchanged(self, graph_no_isolated_nodes):
        """Test that graph with unique edges is copied correctly."""
        morphism = WorkflowMorphism.graph_deduplicate()
        result = morphism(graph_no_isolated_nodes)

        # Note: Graph enforces uniqueness at add_edge() time, so deduplicate just copies
        assert len(result.nodes) == 3
        assert len(result.edges) == len(graph_no_isolated_nodes.edges)

    def test_graph_deduplicate_empty_graph(self, empty_graph):
        """Test deduplication on empty graph."""
        morphism = WorkflowMorphism.graph_deduplicate()
        result = morphism(empty_graph)
        
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_optimize_workflow_composite_applies_all_steps(self, complex_htn_for_optimize):
        """Test that optimize_workflow applies flatten, remove_id, and simplify in sequence."""
        morphism = WorkflowMorphism.optimize_workflow()
        result = morphism(complex_htn_for_optimize)
        
        # After flatten: ((id_a ∘ b) ∘ id_c) → (id_a ∘ b ∘ id_c)
        # After remove_id: (id_a ∘ b ∘ id_c) → (b)
        # After simplify: (b) → b (primitive)
        
        assert result.task_id == "b"
        assert result.description == "task b"
        assert result.subtasks is None
        assert result.metadata == {}  # Should be primitive

    def test_optimize_workflow_returns_composed_morphism(self):
        """Test that optimize_workflow returns a Morphism object."""
        morphism = WorkflowMorphism.optimize_workflow()

        assert isinstance(morphism, Morphism)
        # Composed morphism has format "name3 ∘ name2 ∘ name1"
        assert "∘" in morphism.name
        assert morphism.source == "HTNNode"
        assert morphism.target == "HTNNode"

    def test_optimize_workflow_composition_order(self, complex_htn_for_optimize):
        """Verify composition order: flatten → remove_id → simplify."""
        # Create individual morphisms
        flatten = WorkflowMorphism.flatten_htn()
        remove_id = WorkflowMorphism.remove_htn_identity()
        simplify = WorkflowMorphism.simplify_htn()
        
        # Apply manually in order
        step1 = flatten(complex_htn_for_optimize)
        step2 = remove_id(step1)
        step3 = simplify(step2)
        
        # Apply optimized workflow
        optimized = WorkflowMorphism.optimize_workflow()(complex_htn_for_optimize)
        
        # Should be equivalent
        assert step3.task_id == optimized.task_id
        assert step3.description == optimized.description
        assert step3.subtasks == optimized.subtasks
        assert step3.metadata == optimized.metadata

    def test_htn_flatten_deprecation_warning(self):
        """Test that htn_flatten() raises deprecation warning."""
        with pytest.warns(DeprecationWarning, match="htn_flatten\\(\\) is deprecated, use flatten_htn\\(\\) instead"):
            morphism = WorkflowMorphism.htn_flatten()
            assert isinstance(morphism, Morphism)
            assert morphism.name == "htn_flatten"

    def test_htn_remove_identity_deprecation_warning(self):
        """Test that htn_remove_identity() raises deprecation warning."""
        with pytest.warns(DeprecationWarning, match="htn_remove_identity\\(\\) is deprecated, use remove_htn_identity\\(\\) instead"):
            morphism = WorkflowMorphism.htn_remove_identity()
            assert isinstance(morphism, Morphism)
            assert morphism.name == "htn_remove_identity"

    def test_htn_simplify_deprecation_warning(self):
        """Test that htn_simplify() raises deprecation warning."""
        with pytest.warns(DeprecationWarning, match="htn_simplify\\(\\) is deprecated, use simplify_htn\\(\\) instead"):
            morphism = WorkflowMorphism.htn_simplify()
            assert isinstance(morphism, Morphism)
            assert morphism.name == "htn_simplify"

    def test_workflow_optimize_deprecation_warning(self):
        """Test that workflow_optimize() raises deprecation warning."""
        with pytest.warns(DeprecationWarning, match="workflow_optimize\\(\\) is deprecated, use optimize_workflow\\(\\) instead"):
            morphism = WorkflowMorphism.workflow_optimize()
            assert isinstance(morphism, Morphism)
            assert "∘" in morphism.name  # Composed morphism

    def test_create_transformation_pipeline_single(self):
        """Test creating pipeline with single transformation."""
        pipeline = create_transformation_pipeline(["htn_flatten"])
        
        assert isinstance(pipeline, Morphism)
        assert pipeline.name == "htn_flatten"

    def test_create_transformation_pipeline_multiple(self):
        """Test creating pipeline with multiple transformations."""
        pipeline = create_transformation_pipeline(["htn_flatten", "htn_remove_identity", "htn_simplify"])

        assert isinstance(pipeline, Morphism)
        assert "∘" in pipeline.name  # Should be composed

    def test_create_transformation_pipeline_unknown_name_raises(self):
        """Test that unknown transformation name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown transformation 'invalid_name'"):
            create_transformation_pipeline(["invalid_name"])

    def test_create_transformation_pipeline_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="No transformations specified"):
            create_transformation_pipeline([])

    def test_create_transformation_pipeline_graph_transformations(self):
        """Test creating pipeline with graph transformations."""
        pipeline = create_transformation_pipeline(["graph_remove_isolated_nodes", "graph_deduplicate"])

        assert isinstance(pipeline, Morphism)
        assert "∘" in pipeline.name  # Composed morphism

    def test_create_transformation_pipeline_mixed_transformations(self):
        """Test that mixing incompatible transformation types raises ValueError."""
        # HTN transformations (HTNNode -> HTNNode) cannot compose with
        # Graph transformations (Graph -> Graph) due to type incompatibility
        with pytest.raises(ValueError, match="Cannot compose morphisms"):
            create_transformation_pipeline(["htn_flatten", "graph_remove_isolated_nodes"])

    def test_create_transformation_pipeline_workflow_optimize(self):
        """Test that workflow_optimize can be used in pipeline."""
        pipeline = create_transformation_pipeline(["workflow_optimize"])

        assert isinstance(pipeline, Morphism)
        # workflow_optimize itself returns a composed morphism
        assert "∘" in pipeline.name