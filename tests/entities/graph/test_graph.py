"""Unit tests for Graph entity.

Tests cover graph construction, node/edge management, traversal algorithms,
cycle detection, and topological sorting.
"""

import pytest
from src.entity.graph import Graph, GraphNode


class TestGraphNodeCreation:
    """Test GraphNode creation and properties."""

    def test_create_node_minimal(self):
        """Test creating node with just ID."""
        node = GraphNode(node_id="task_1")

        assert node.node_id == "task_1"
        assert node.data is None
        assert node.metadata == {}

    def test_create_node_with_data(self):
        """Test creating node with data payload."""
        data = {"name": "Build project", "priority": "high"}
        node = GraphNode(node_id="task_1", data=data)

        assert node.node_id == "task_1"
        assert node.data == data

    def test_create_node_with_metadata(self):
        """Test creating node with metadata."""
        node = GraphNode(
            node_id="task_1",
            metadata={"created": "2025-01-01", "owner": "alice"}
        )

        assert node.metadata["created"] == "2025-01-01"
        assert node.metadata["owner"] == "alice"

    def test_node_equality(self):
        """Test nodes are equal based on ID."""
        node1 = GraphNode(node_id="task_1", data="data1")
        node2 = GraphNode(node_id="task_1", data="data2")
        node3 = GraphNode(node_id="task_2", data="data1")

        assert node1 == node2  # Same ID
        assert node1 != node3  # Different ID

    def test_node_hashable(self):
        """Test nodes can be used in sets/dicts."""
        node1 = GraphNode(node_id="task_1")
        node2 = GraphNode(node_id="task_2")

        node_set = {node1, node2}
        assert len(node_set) == 2
        assert node1 in node_set


class TestGraphConstruction:
    """Test graph creation and basic operations."""

    def test_create_empty_graph(self):
        """Test creating empty graph."""
        graph = Graph()

        assert graph.node_count() == 0
        assert graph.edge_count() == 0

    def test_add_single_node(self):
        """Test adding a single node."""
        graph = Graph()
        node = graph.add_node("task_1", data="Build project")

        assert graph.node_count() == 1
        assert node.node_id == "task_1"
        assert node.data == "Build project"

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_node("task_3")

        assert graph.node_count() == 3

    def test_add_duplicate_node_fails(self):
        """Test adding duplicate node raises error."""
        graph = Graph()
        graph.add_node("task_1")

        with pytest.raises(ValueError) as exc_info:
            graph.add_node("task_1")

        assert "already exists" in str(exc_info.value)

    def test_get_existing_node(self):
        """Test retrieving existing node."""
        graph = Graph()
        graph.add_node("task_1", data="test")

        node = graph.get_node("task_1")

        assert node is not None
        assert node.node_id == "task_1"
        assert node.data == "test"

    def test_get_nonexistent_node(self):
        """Test retrieving nonexistent node returns None."""
        graph = Graph()

        node = graph.get_node("missing")

        assert node is None

    def test_has_node(self):
        """Test checking node existence."""
        graph = Graph()
        graph.add_node("task_1")

        assert graph.has_node("task_1") is True
        assert graph.has_node("task_2") is False


class TestGraphEdges:
    """Test edge management."""

    def test_add_edge(self):
        """Test adding edge between nodes."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")

        graph.add_edge("task_1", "task_2")

        assert graph.edge_count() == 1
        assert graph.has_edge("task_1", "task_2") is True

    def test_add_multiple_edges(self):
        """Test adding multiple edges."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_node("task_3")

        graph.add_edge("task_1", "task_2")
        graph.add_edge("task_2", "task_3")
        graph.add_edge("task_1", "task_3")

        assert graph.edge_count() == 3

    def test_add_edge_missing_source_fails(self):
        """Test adding edge with missing source node fails."""
        graph = Graph()
        graph.add_node("task_2")

        with pytest.raises(ValueError) as exc_info:
            graph.add_edge("task_1", "task_2")

        assert "Source node" in str(exc_info.value)

    def test_add_edge_missing_target_fails(self):
        """Test adding edge with missing target node fails."""
        graph = Graph()
        graph.add_node("task_1")

        with pytest.raises(ValueError) as exc_info:
            graph.add_edge("task_1", "task_2")

        assert "Target node" in str(exc_info.value)

    def test_add_duplicate_edge_fails(self):
        """Test adding duplicate edge fails."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_edge("task_1", "task_2")

        with pytest.raises(ValueError) as exc_info:
            graph.add_edge("task_1", "task_2")

        assert "already exists" in str(exc_info.value)

    def test_has_edge(self):
        """Test edge existence checking."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_edge("task_1", "task_2")

        assert graph.has_edge("task_1", "task_2") is True
        assert graph.has_edge("task_2", "task_1") is False  # Directed

    def test_get_successors(self):
        """Test getting successor nodes."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_node("task_3")
        graph.add_edge("task_1", "task_2")
        graph.add_edge("task_1", "task_3")

        successors = graph.get_successors("task_1")

        assert len(successors) == 2
        assert "task_2" in successors
        assert "task_3" in successors

    def test_get_predecessors(self):
        """Test getting predecessor nodes."""
        graph = Graph()
        graph.add_node("task_1")
        graph.add_node("task_2")
        graph.add_node("task_3")
        graph.add_edge("task_1", "task_3")
        graph.add_edge("task_2", "task_3")

        predecessors = graph.get_predecessors("task_3")

        assert len(predecessors) == 2
        assert "task_1" in predecessors
        assert "task_2" in predecessors


class TestGraphTraversal:
    """Test DFS and BFS traversal."""

    def test_dfs_linear_chain(self):
        """Test DFS on linear chain."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        result = graph.dfs("a")

        assert result == ["a", "b", "c"]

    def test_dfs_branching(self):
        """Test DFS on branching graph."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")

        result = graph.dfs("a")

        # DFS should visit all reachable nodes
        assert len(result) == 4
        assert result[0] == "a"  # Start node first

    def test_dfs_with_visit_function(self):
        """Test DFS with visit callback."""
        graph = Graph()
        graph.add_node("a", data=1)
        graph.add_node("b", data=2)
        graph.add_edge("a", "b")

        visited_data = []

        def collect_data(node):
            visited_data.append(node.data)

        graph.dfs("a", visit_fn=collect_data)

        assert visited_data == [1, 2]

    def test_dfs_missing_node_fails(self):
        """Test DFS with missing start node fails."""
        graph = Graph()

        with pytest.raises(ValueError):
            graph.dfs("missing")

    def test_bfs_linear_chain(self):
        """Test BFS on linear chain."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        result = graph.bfs("a")

        assert result == ["a", "b", "c"]

    def test_bfs_branching(self):
        """Test BFS on branching graph (level-order)."""
        graph = Graph()
        for node in ["a", "b", "c", "d", "e"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")
        graph.add_edge("c", "e")

        result = graph.bfs("a")

        # BFS should visit level by level: a, then b,c, then d,e
        assert result[0] == "a"
        assert set(result[1:3]) == {"b", "c"}
        assert set(result[3:5]) == {"d", "e"}

    def test_bfs_with_visit_function(self):
        """Test BFS with visit callback."""
        graph = Graph()
        graph.add_node("a", data=1)
        graph.add_node("b", data=2)
        graph.add_edge("a", "b")

        visited_data = []

        def collect_data(node):
            visited_data.append(node.data)

        graph.bfs("a", visit_fn=collect_data)

        assert visited_data == [1, 2]


class TestGraphCycleDetection:
    """Test cycle detection."""

    def test_acyclic_graph_no_cycle(self):
        """Test acyclic graph returns False."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        assert graph.has_cycle() is False

    def test_simple_cycle_detected(self):
        """Test simple cycle is detected."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")  # Cycle

        assert graph.has_cycle() is True

    def test_self_loop_detected(self):
        """Test self-loop is detected as cycle."""
        graph = Graph()
        graph.add_node("a")
        graph.add_edge("a", "a")  # Self-loop

        assert graph.has_cycle() is True

    def test_complex_cycle_detected(self):
        """Test cycle in complex graph is detected."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", "d")
        graph.add_edge("d", "b")  # Cycle: b -> c -> d -> b

        assert graph.has_cycle() is True

    def test_empty_graph_no_cycle(self):
        """Test empty graph has no cycle."""
        graph = Graph()

        assert graph.has_cycle() is False


class TestGraphTopologicalSort:
    """Test topological sorting."""

    def test_topological_sort_linear(self):
        """Test topological sort on linear chain."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_node("c")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")

        result = graph.topological_sort()

        # Should be in dependency order
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_topological_sort_dag(self):
        """Test topological sort on DAG."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "c")
        graph.add_edge("b", "c")
        graph.add_edge("c", "d")

        result = graph.topological_sort()

        # a and b should come before c, c before d
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("c")
        assert result.index("c") < result.index("d")

    def test_topological_sort_with_cycle_fails(self):
        """Test topological sort fails on cyclic graph."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")

        with pytest.raises(ValueError) as exc_info:
            graph.topological_sort()

        assert "cycle" in str(exc_info.value)


class TestGraphRootsAndLeaves:
    """Test finding root and leaf nodes."""

    def test_find_roots_single(self):
        """Test finding single root node."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b")

        roots = graph.find_roots()

        assert roots == ["a"]

    def test_find_roots_multiple(self):
        """Test finding multiple root nodes."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "c")
        graph.add_edge("b", "d")

        roots = graph.find_roots()

        assert set(roots) == {"a", "b"}

    def test_find_leaves_single(self):
        """Test finding single leaf node."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b")

        leaves = graph.find_leaves()

        assert leaves == ["b"]

    def test_find_leaves_multiple(self):
        """Test finding multiple leaf nodes."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("a", "c")

        leaves = graph.find_leaves()

        assert set(leaves) == {"b", "c", "d"}  # b, c, d have no outgoing edges

    def test_isolated_node_is_root_and_leaf(self):
        """Test isolated node is both root and leaf."""
        graph = Graph()
        graph.add_node("a")

        roots = graph.find_roots()
        leaves = graph.find_leaves()

        assert "a" in roots
        assert "a" in leaves


class TestGraphSubgraph:
    """Test subgraph extraction."""

    def test_subgraph_with_nodes(self):
        """Test creating subgraph with specific nodes."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", "d")

        sub = graph.subgraph(["a", "b", "c"])

        assert sub.node_count() == 3
        assert sub.has_node("a")
        assert sub.has_node("b")
        assert sub.has_node("c")
        assert not sub.has_node("d")

    def test_subgraph_preserves_edges(self):
        """Test subgraph preserves edges between included nodes."""
        graph = Graph()
        for node in ["a", "b", "c", "d"]:
            graph.add_node(node)
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", "d")

        sub = graph.subgraph(["a", "b", "c"])

        assert sub.has_edge("a", "b")
        assert sub.has_edge("b", "c")
        assert not sub.has_edge("c", "d")  # d not in subgraph

    def test_subgraph_missing_node_fails(self):
        """Test subgraph with missing node fails."""
        graph = Graph()
        graph.add_node("a")

        with pytest.raises(ValueError):
            graph.subgraph(["a", "missing"])


class TestGraphRepresentation:
    """Test string representation."""

    def test_repr_empty_graph(self):
        """Test __repr__() for empty graph."""
        graph = Graph()

        repr_str = repr(graph)

        assert "nodes=0" in repr_str
        assert "edges=0" in repr_str

    def test_repr_with_nodes_and_edges(self):
        """Test __repr__() for graph with content."""
        graph = Graph()
        graph.add_node("a")
        graph.add_node("b")
        graph.add_edge("a", "b")

        repr_str = repr(graph)

        assert "nodes=2" in repr_str
        assert "edges=1" in repr_str
