# tests/unit/entity/graph/test_graph_comprehensive.py
import pytest
from src.entity.graph.graph import GraphNode, Graph
from collections import deque
import warnings


@pytest.fixture
def simple_linear_graph():
    """A linear graph: A -> B -> C"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    return graph


@pytest.fixture
def simple_tree_graph():
    """A tree graph: A -> B, A -> C, B -> D, C -> E"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_node("E")
    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "E")
    return graph


@pytest.fixture
def cyclic_graph():
    """A cyclic graph: A -> B -> C -> A"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    return graph


@pytest.fixture
def self_loop_graph():
    """A graph with self-loop: A -> A"""
    graph = Graph()
    graph.add_node("A")
    graph.add_edge("A", "A")
    return graph


@pytest.fixture
def disconnected_graph():
    """A graph with disconnected components: A->B, C->D, E"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_node("E")
    graph.add_edge("A", "B")
    graph.add_edge("C", "D")
    return graph


@pytest.fixture
def empty_graph():
    """An empty graph with no nodes"""
    return Graph()


@pytest.fixture
def multiple_roots_graph():
    """Graph with multiple roots: A, B -> C, D -> E"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_node("E")
    graph.add_edge("B", "C")
    graph.add_edge("D", "E")
    return graph


@pytest.fixture
def multiple_leaves_graph():
    """Graph with multiple leaves: A -> B -> C, A -> D"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_node("D")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("A", "D")
    return graph


@pytest.fixture
def no_leaves_graph():
    """Graph with no leaves (all nodes have outgoing edges): A -> B -> C -> A"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    return graph


@pytest.fixture
def no_roots_graph():
    """Graph with no roots (all nodes have incoming edges): A -> B -> C -> A"""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_node("C")
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")
    return graph


# GraphNode tests
def test_graph_node_creation_with_data_and_metadata():
    """Test GraphNode creation with data and metadata."""
    node = GraphNode("node1", data="payload", metadata={"type": "task", "priority": 1})
    assert node.node_id == "node1"
    assert node.data == "payload"
    assert node.metadata == {"type": "task", "priority": 1}


def test_graph_node_hash_returns_node_id_hash():
    """Test that __hash__() returns hash of node_id."""
    node1 = GraphNode("node1")
    node2 = GraphNode("node2")
    assert hash(node1) == hash("node1")
    assert hash(node2) == hash("node2")
    assert hash(node1) != hash(node2)


def test_graph_node_eq_compares_node_ids():
    """Test that __eq__() compares based on node_id."""
    node1 = GraphNode("node1")
    node2 = GraphNode("node1")
    node3 = GraphNode("node2")
    assert node1 == node2
    assert node1 != node3
    assert node1 != "not a node"


def test_graph_node_repr_format():
    """Test that __repr__() has correct format."""
    node = GraphNode("node1", data="test", metadata={"key": "value"})
    assert repr(node) == "GraphNode(id='node1')"


def test_graph_node_in_set_and_dict():
    """Test that GraphNode can be used in sets and dicts due to hash/equality."""
    node1 = GraphNode("node1")
    node2 = GraphNode("node1")  # same id
    node3 = GraphNode("node2")
    
    # Test set uniqueness
    node_set = {node1, node2, node3}
    assert len(node_set) == 2  # node1 and node2 are considered same
    
    # Test dict key
    node_dict = {node1: "value1", node3: "value2"}
    assert node_dict[node1] == "value1"
    assert node_dict[node3] == "value2"
    assert node_dict[node2] == "value1"  # node2 equals node1


# Graph Initialization test
def test_graph_initialization_empty():
    """Test that graph initializes with empty structures."""
    graph = Graph()
    assert graph.nodes == {}
    assert graph.edges == {}
    assert graph.reverse_edges == {}


# Node Operations tests
def test_add_node_with_data_and_metadata():
    """Test add_node with data and metadata."""
    graph = Graph()
    node = graph.add_node("node1", data="test_data", priority="high", category="task")
    
    assert node.node_id == "node1"
    assert node.data == "test_data"
    assert node.metadata == {"priority": "high", "category": "task"}
    assert graph.nodes["node1"] is node
    assert graph.edges["node1"] == []
    assert graph.reverse_edges["node1"] == []


def test_add_node_duplicate_raises_valueerror():
    """Test that adding duplicate node_id raises ValueError."""
    graph = Graph()
    graph.add_node("node1")
    with pytest.raises(ValueError, match="Node 'node1' already exists in graph"):
        graph.add_node("node1")


def test_get_node_existing_and_missing():
    """Test get_node returns node when exists, None when missing."""
    graph = Graph()
    graph.add_node("node1")
    graph.add_node("node2")
    
    assert graph.get_node("node1") is not None
    assert graph.get_node("node1").node_id == "node1"
    assert graph.get_node("node3") is None


def test_has_node_existing_and_missing():
    """Test has_node returns True for existing, False for missing."""
    graph = Graph()
    graph.add_node("node1")
    
    assert graph.has_node("node1") is True
    assert graph.has_node("node2") is False


# Edge Operations tests
def test_add_edge_updates_both_directions(simple_linear_graph):
    """Test add_edge updates both edges and reverse_edges."""
    graph = simple_linear_graph
    graph.add_node("D")
    graph.add_edge("C", "D")  # Add new edge

    assert "D" in graph.edges["C"]
    assert "C" in graph.reverse_edges["D"]
    assert graph.has_edge("C", "D")


def test_add_edge_missing_source_raises_valueerror():
    """Test adding edge with missing source node raises ValueError."""
    graph = Graph()
    graph.add_node("B")
    with pytest.raises(ValueError, match="Source node 'A' not found in graph"):
        graph.add_edge("A", "B")


def test_add_edge_missing_target_raises_valueerror():
    """Test adding edge with missing target node raises ValueError."""
    graph = Graph()
    graph.add_node("A")
    with pytest.raises(ValueError, match="Target node 'B' not found in graph"):
        graph.add_edge("A", "B")


def test_add_edge_duplicate_raises_valueerror(simple_linear_graph):
    """Test adding duplicate edge raises ValueError."""
    graph = simple_linear_graph
    with pytest.raises(ValueError, match="Edge from 'A' to 'B' already exists"):
        graph.add_edge("A", "B")


def test_has_edge_existing_and_missing(simple_linear_graph):
    """Test has_edge returns True for existing, False for missing."""
    graph = simple_linear_graph
    assert graph.has_edge("A", "B") is True
    assert graph.has_edge("B", "C") is True
    assert graph.has_edge("A", "C") is False
    assert graph.has_edge("C", "A") is False
    assert graph.has_edge("X", "Y") is False


def test_get_successors_and_predecessors_return_copies(simple_linear_graph):
    """Test get_successors and get_predecessors return copies, not references."""
    graph = simple_linear_graph
    successors = graph.get_successors("A")
    predecessors = graph.get_predecessors("B")
    
    # Modify the returned lists
    successors.append("Z")
    predecessors.append("X")
    
    # Original graph should be unchanged
    assert graph.edges["A"] == ["B"]
    assert graph.reverse_edges["B"] == ["A"]
    assert "Z" not in graph.edges["A"]
    assert "X" not in graph.reverse_edges["B"]


# Counting tests
def test_count_nodes_and_edges(simple_linear_graph):
    """Test count_nodes and count_edges return correct counts."""
    graph = simple_linear_graph
    assert graph.count_nodes() == 3
    assert graph.count_edges() == 2


def test_node_count_deprecated_warning():
    """Test node_count() raises deprecation warning."""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_edge("A", "B")
    
    with pytest.warns(DeprecationWarning, match="node_count\\(\\) is deprecated"):
        result = graph.node_count()
        assert result == 2


def test_edge_count_deprecated_warning():
    """Test edge_count() raises deprecation warning."""
    graph = Graph()
    graph.add_node("A")
    graph.add_node("B")
    graph.add_edge("A", "B")
    
    with pytest.warns(DeprecationWarning, match="edge_count\\(\\) is deprecated"):
        result = graph.edge_count()
        assert result == 1


# Traversals tests
def test_traverse_dfs_linear_order(simple_linear_graph):
    """Test DFS traversal returns correct order for linear graph A->B->C."""
    graph = simple_linear_graph
    result = graph.traverse_dfs("A")
    assert result == ["A", "B", "C"]


def test_traverse_dfs_with_visit_function(simple_linear_graph):
    """Test DFS traversal with visit function tracks calls."""
    graph = simple_linear_graph
    visited_nodes = []
    
    def visit(node):
        visited_nodes.append(node.node_id)
    
    result = graph.traverse_dfs("A", visit_fn=visit)
    assert result == ["A", "B", "C"]
    assert visited_nodes == ["A", "B", "C"]


def test_traverse_dfs_missing_start_raises_valueerror():
    """Test DFS with missing start node raises ValueError."""
    graph = Graph()
    graph.add_node("A")
    with pytest.raises(ValueError, match="Start node 'B' not found in graph"):
        graph.traverse_dfs("B")


def test_dfs_deprecated_warning(simple_linear_graph):
    """Test dfs() raises deprecation warning."""
    graph = simple_linear_graph
    with pytest.warns(DeprecationWarning, match="dfs\\(\\) is deprecated"):
        result = graph.dfs("A")
        assert result == ["A", "B", "C"]


def test_traverse_bfs_tree_order(simple_tree_graph):
    """Test BFS traversal returns correct order for tree graph."""
    graph = simple_tree_graph
    result = graph.traverse_bfs("A")
    # BFS should visit A, then B and C (in order), then D and E
    # Order of B/C and D/E may vary, but A must be first, then children
    assert result[0] == "A"
    assert "B" in result[1:3]
    assert "C" in result[1:3]
    assert "D" in result[3:5]
    assert "E" in result[3:5]


def test_traverse_bfs_with_visit_function(simple_tree_graph):
    """Test BFS traversal with visit function tracks calls."""
    graph = simple_tree_graph
    visited_nodes = []
    
    def visit(node):
        visited_nodes.append(node.node_id)
    
    result = graph.traverse_bfs("A", visit_fn=visit)
    assert result[0] == "A"
    assert visited_nodes == result


def test_traverse_bfs_missing_start_raises_valueerror():
    """Test BFS with missing start node raises ValueError."""
    graph = Graph()
    graph.add_node("A")
    with pytest.raises(ValueError, match="Start node 'B' not found in graph"):
        graph.traverse_bfs("B")


def test_bfs_deprecated_warning(simple_tree_graph):
    """Test bfs() raises deprecation warning."""
    graph = simple_tree_graph
    with pytest.warns(DeprecationWarning, match="bfs\\(\\) is deprecated"):
        result = graph.bfs("A")
        assert result[0] == "A"


# Cycle Detection tests
def test_has_cycle_acyclic_graph(simple_linear_graph):
    """Test has_cycle returns False for acyclic graph."""
    graph = simple_linear_graph
    assert graph.has_cycle() is False


def test_has_cycle_cyclic_graph(cyclic_graph):
    """Test has_cycle returns True for cyclic graph."""
    graph = cyclic_graph
    assert graph.has_cycle() is True


def test_has_cycle_self_loop(self_loop_graph):
    """Test has_cycle returns True for self-loop."""
    graph = self_loop_graph
    assert graph.has_cycle() is True


def test_has_cycle_disconnected_components(disconnected_graph):
    """Test has_cycle handles disconnected components (mixed acyclic/cyclic)."""
    graph = disconnected_graph
    # Add a cycle in one component
    graph.add_edge("D", "C")
    assert graph.has_cycle() is True


def test_has_cycle_empty_graph(empty_graph):
    """Test has_cycle returns False for empty graph."""
    graph = empty_graph
    assert graph.has_cycle() is False


# Topological Sort tests
def test_sort_topologically_valid_dag(simple_linear_graph):
    """Test topological sort returns correct order for DAG."""
    graph = simple_linear_graph
    result = graph.sort_topologically()
    # A must come before B, B before C
    assert result.index("A") < result.index("B") < result.index("C")


def test_sort_topologically_cyclic_raises_valueerror(cyclic_graph):
    """Test topological sort raises ValueError for cyclic graph."""
    graph = cyclic_graph
    with pytest.raises(ValueError, match="Cannot perform topological sort on graph with cycles"):
        graph.sort_topologically()


def test_sort_topologically_disconnected_components(disconnected_graph):
    """Test topological sort works with disconnected components."""
    graph = disconnected_graph
    result = graph.sort_topologically()
    # A before B, C before D, E can be anywhere
    assert result.index("A") < result.index("B")
    assert result.index("C") < result.index("D")
    # E can be anywhere since it has no edges
    assert len(result) == 5


def test_topological_sort_deprecated_warning(simple_linear_graph):
    """Test topological_sort() raises deprecation warning."""
    graph = simple_linear_graph
    with pytest.warns(DeprecationWarning, match="topological_sort\\(\\) is deprecated"):
        result = graph.topological_sort()
        assert result.index("A") < result.index("B") < result.index("C")


# Roots/Leaves tests
def test_find_roots_single_root(simple_linear_graph):
    """Test find_roots returns single root for linear graph."""
    graph = simple_linear_graph
    roots = graph.find_roots()
    assert roots == ["A"]


def test_find_roots_multiple_roots(multiple_roots_graph):
    """Test find_roots returns multiple roots when present."""
    graph = multiple_roots_graph
    roots = graph.find_roots()
    # A, B, and D all have no incoming edges
    assert set(roots) == {"A", "B", "D"}


def test_find_roots_no_roots(no_roots_graph):
    """Test find_roots returns empty list when no roots exist."""
    graph = no_roots_graph
    roots = graph.find_roots()
    assert roots == []


def test_find_leaves_multiple_leaves(multiple_leaves_graph):
    """Test find_leaves returns multiple leaves."""
    graph = multiple_leaves_graph
    leaves = graph.find_leaves()
    assert set(leaves) == {"C", "D"}  # C and D have no outgoing edges


def test_find_leaves_no_leaves(no_leaves_graph):
    """Test find_leaves returns empty list when no leaves exist."""
    graph = no_leaves_graph
    leaves = graph.find_leaves()
    assert leaves == []


# Subgraph tests
def test_extract_subgraph_valid_nodes_preserves_edges(simple_tree_graph):
    """Test extract_subgraph preserves nodes and edges between them."""
    graph = simple_tree_graph
    sub_nodes = ["A", "B", "C", "D"]
    subgraph = graph.extract_subgraph(sub_nodes)

    assert subgraph.count_nodes() == 4
    # Edges: A->B, A->C, B->D (C->E excluded because E not in subgraph)
    assert subgraph.count_edges() == 3
    assert subgraph.has_edge("A", "B")
    assert subgraph.has_edge("A", "C")
    assert subgraph.has_edge("B", "D")
    assert not subgraph.has_edge("C", "E")


def test_extract_subgraph_missing_node_raises_valueerror(simple_linear_graph):
    """Test extract_subgraph with missing node raises ValueError."""
    graph = simple_linear_graph
    with pytest.raises(ValueError, match="Node 'Z' not found in graph"):
        graph.extract_subgraph(["A", "B", "Z"])


def test_subgraph_deprecated_warning(simple_linear_graph):
    """Test subgraph() raises deprecation warning."""
    graph = simple_linear_graph
    with pytest.warns(DeprecationWarning, match="subgraph\\(\\) is deprecated"):
        subgraph = graph.subgraph(["A", "B"])
        assert subgraph.count_nodes() == 2
        assert subgraph.has_edge("A", "B")


# Other test
def test_graph_repr_format(simple_linear_graph):
    """Test __repr__() format with counts."""
    graph = simple_linear_graph
    repr_str = repr(graph)
    assert "Graph(nodes=3, edges=2)" in repr_str