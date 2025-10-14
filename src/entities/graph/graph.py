"""Graph entity for task dependency representation.

Implements directed graph with adjacency list representation for modeling
task dependencies, hierarchies, and execution flows.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable
from collections import deque


@dataclass
class GraphNode:
    """Represents a node in the graph.

    Attributes:
        node_id: Unique identifier for this node
        data: Associated data payload
        metadata: Additional node-specific information
    """

    node_id: str
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Make node hashable for use in sets/dicts."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Check equality based on node_id."""
        if not isinstance(other, GraphNode):
            return False
        return self.node_id == other.node_id

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"GraphNode(id='{self.node_id}')"


class Graph:
    """Directed graph with adjacency list representation.

    Supports DAG (Directed Acyclic Graph) operations for task dependencies,
    including cycle detection, topological sorting, and traversal.

    Attributes:
        nodes: Mapping from node_id to GraphNode
        edges: Adjacency list (node_id -> list of successor node_ids)
        reverse_edges: Reverse adjacency list for predecessor lookups
    """

    def __init__(self):
        """Initialize empty graph."""
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, List[str]] = {}
        self.reverse_edges: Dict[str, List[str]] = {}

    def add_node(self, node_id: str, data: Any = None, **metadata) -> GraphNode:
        """Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            data: Optional data payload
            **metadata: Additional node attributes

        Returns:
            The created GraphNode

        Raises:
            ValueError: If node_id already exists
        """
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already exists in graph")

        node = GraphNode(node_id=node_id, data=data, metadata=metadata)
        self.nodes[node_id] = node
        self.edges[node_id] = []
        self.reverse_edges[node_id] = []

        return node

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID.

        Args:
            node_id: Node identifier

        Returns:
            GraphNode if found, None otherwise
        """
        return self.nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if node exists in graph.

        Args:
            node_id: Node identifier

        Returns:
            True if node exists
        """
        return node_id in self.nodes

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge from one node to another.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Raises:
            ValueError: If either node doesn't exist or edge already exists
        """
        if not self.has_node(from_node):
            raise ValueError(f"Source node '{from_node}' not found in graph")
        if not self.has_node(to_node):
            raise ValueError(f"Target node '{to_node}' not found in graph")

        if to_node in self.edges[from_node]:
            raise ValueError(
                f"Edge from '{from_node}' to '{to_node}' already exists"
            )

        self.edges[from_node].append(to_node)
        self.reverse_edges[to_node].append(from_node)

    def has_edge(self, from_node: str, to_node: str) -> bool:
        """Check if directed edge exists.

        Args:
            from_node: Source node ID
            to_node: Target node ID

        Returns:
            True if edge exists
        """
        return (
            from_node in self.edges and
            to_node in self.edges[from_node]
        )

    def get_successors(self, node_id: str) -> List[str]:
        """Get all successor nodes (outgoing edges).

        Args:
            node_id: Node identifier

        Returns:
            List of successor node IDs
        """
        return self.edges.get(node_id, []).copy()

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get all predecessor nodes (incoming edges).

        Args:
            node_id: Node identifier

        Returns:
            List of predecessor node IDs
        """
        return self.reverse_edges.get(node_id, []).copy()

    def count_nodes(self) -> int:
        """Get total number of nodes."""
        return len(self.nodes)

    def count_edges(self) -> int:
        """Get total number of edges."""
        return sum(len(successors) for successors in self.edges.values())


    # Backward compatibility alias (deprecated)
    def node_count(self) -> int:
        """DEPRECATED: Use count_nodes() instead."""
        import warnings
        warnings.warn(
            "node_count() is deprecated, use count_nodes() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.count_nodes()

    # Backward compatibility alias (deprecated)
    def edge_count(self) -> int:
        """DEPRECATED: Use count_edges() instead."""
        import warnings
        warnings.warn(
            "edge_count() is deprecated, use count_edges() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.count_edges()
    def traverse_dfs(
        self,
        start_node: str,
        visit_fn: Optional[Callable[[GraphNode], None]] = None
    ) -> List[str]:
        """Depth-first search traversal from start node.

        Args:
            start_node: Starting node ID
            visit_fn: Optional function to call on each visited node

        Returns:
            List of node IDs in DFS order

        Raises:
            ValueError: If start node doesn't exist
        """
        if not self.has_node(start_node):
            raise ValueError(f"Start node '{start_node}' not found in graph")

        visited: Set[str] = set()
        result: List[str] = []

        def _dfs_recursive(node_id: str) -> None:
            if node_id in visited:
                return

            visited.add(node_id)
            result.append(node_id)

            if visit_fn:
                visit_fn(self.nodes[node_id])

            for successor in self.edges[node_id]:
                _dfs_recursive(successor)

        _dfs_recursive(start_node)
        return result

    # Backward compatibility alias (deprecated)
    def dfs(
        self,
        start_node: str,
        visit_fn: Optional[Callable[[GraphNode], None]] = None
    ) -> List[str]:
        """DEPRECATED: Use traverse_dfs() instead."""
        import warnings
        warnings.warn(
            "dfs() is deprecated, use traverse_dfs() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.traverse_dfs(start_node, visit_fn)

    def bfs(
        self,
        start_node: str,
        visit_fn: Optional[Callable[[GraphNode], None]] = None
    ) -> List[str]:
        """Breadth-first search traversal from start node.

        Args:
            start_node: Starting node ID
            visit_fn: Optional function to call on each visited node

        Returns:
            List of node IDs in BFS order

        Raises:
            ValueError: If start node doesn't exist
        """
        if not self.has_node(start_node):
            raise ValueError(f"Start node '{start_node}' not found in graph")

        visited: Set[str] = set()
        result: List[str] = []
        queue: deque = deque([start_node])

        while queue:
            node_id = queue.popleft()

            if node_id in visited:
                continue

            visited.add(node_id)
            result.append(node_id)

            if visit_fn:
                visit_fn(self.nodes[node_id])

            for successor in self.edges[node_id]:
                if successor not in visited:
                    queue.append(successor)

        return result

    def has_cycle(self) -> bool:
        """Detect if graph contains any cycles.

        Uses DFS-based cycle detection with three states:
        - WHITE (0): Not visited
        - GRAY (1): Being processed (in current DFS path)
        - BLACK (2): Fully processed

        Returns:
            True if graph contains a cycle
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node_id: WHITE for node_id in self.nodes}

        def _has_cycle_recursive(node_id: str) -> bool:
            color[node_id] = GRAY

            for successor in self.edges[node_id]:
                if color[successor] == GRAY:
                    # Back edge found - cycle detected
                    return True
                if color[successor] == WHITE:
                    if _has_cycle_recursive(successor):
                        return True

            color[node_id] = BLACK
            return False

        # Check all nodes (handle disconnected components)
        for node_id in self.nodes:
            if color[node_id] == WHITE:
                if _has_cycle_recursive(node_id):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """Topological sort of nodes (valid only for DAGs).

        Returns nodes in order such that for every edge (u, v),
        u appears before v in the ordering.

        Returns:
            List of node IDs in topological order

        Raises:
            ValueError: If graph contains a cycle
        """
        if self.has_cycle():
            raise ValueError("Cannot perform topological sort on graph with cycles")

        visited: Set[str] = set()
        stack: List[str] = []

        def _topological_recursive(node_id: str) -> None:
            visited.add(node_id)

            for successor in self.edges[node_id]:
                if successor not in visited:
                    _topological_recursive(successor)

            stack.append(node_id)

        # Process all nodes (handle disconnected components)
        for node_id in self.nodes:
            if node_id not in visited:
                _topological_recursive(node_id)

        # Return reversed stack (reverse postorder)
        return list(reversed(stack))

    def find_roots(self) -> List[str]:
        """Find all root nodes (nodes with no incoming edges).

        Returns:
            List of root node IDs
        """
        roots = []
        for node_id in self.nodes:
            if len(self.reverse_edges[node_id]) == 0:
                roots.append(node_id)
        return roots

    def find_leaves(self) -> List[str]:
        """Find all leaf nodes (nodes with no outgoing edges).

        Returns:
            List of leaf node IDs
        """
        leaves = []
        for node_id in self.nodes:
            if len(self.edges[node_id]) == 0:
                leaves.append(node_id)
        return leaves

    def subgraph(self, node_ids: List[str]) -> "Graph":
        """Create subgraph containing only specified nodes.

        Args:
            node_ids: List of node IDs to include

        Returns:
            New Graph containing only specified nodes and edges between them

        Raises:
            ValueError: If any node_id doesn't exist
        """
        # Validate all nodes exist
        for node_id in node_ids:
            if not self.has_node(node_id):
                raise ValueError(f"Node '{node_id}' not found in graph")

        # Create new graph
        sub = Graph()
        node_set = set(node_ids)

        # Add nodes
        for node_id in node_ids:
            node = self.nodes[node_id]
            sub.add_node(node_id, data=node.data, **node.metadata)

        # Add edges (only between nodes in subgraph)
        for from_node in node_ids:
            for to_node in self.edges[from_node]:
                if to_node in node_set:
                    sub.add_edge(from_node, to_node)

        return sub

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Graph(nodes={self.node_count()}, edges={self.edge_count()})"
        )
