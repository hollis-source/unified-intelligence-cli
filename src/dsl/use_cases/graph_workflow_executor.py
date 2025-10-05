"""Graph Workflow Executor - HTN to dependency graph conversion and execution.

Converts HTN (Hierarchical Task Network) to explicit dependency graphs for:
- DAG validation (cycle detection)
- Topological execution order
- Dependency tracking and visualization

Clean Architecture: Use Case layer (orchestrates graph conversion and execution)
SOLID: SRP (single responsibility: graph-based workflow execution)
"""

from typing import Any, Dict, List, Optional
from src.entities.graph import Graph
from src.entities.htn import HTNNode


class GraphWorkflowExecutor:
    """Converts HTN to dependency graph and executes in topological order.

    This executor enhances HTN-based workflows by:
    1. Converting hierarchical task networks to explicit dependency graphs
    2. Validating workflows as DAGs (detecting cycles before execution)
    3. Executing tasks in topological order (respecting dependencies)

    Example:
        executor = GraphWorkflowExecutor(task_executor)
        graph = executor.htn_to_graph(htn_root)
        issues = executor.validate_dag(graph)
        if not issues:
            results = await executor.execute_graph(graph)
    """

    def __init__(self, task_executor):
        """Initialize with task executor.

        Args:
            task_executor: Task executor for running individual tasks
                          (CLITaskExecutor or PoolTaskExecutor)
        """
        self.task_executor = task_executor

    def htn_to_graph(self, htn: HTNNode) -> Graph:
        """Convert HTN to dependency graph.

        Converts hierarchical task network to explicit dependency graph where:
        - Nodes: Individual tasks (HTN task_ids)
        - Edges: Dependencies between tasks

        Composition semantics:
        - Sequential composition (∘): Creates dependency chain (right-to-left)
        - Parallel product (×): Creates parallel branches (no inter-dependencies)
        - Functor: Wraps subtasks with named container

        Args:
            htn: Root HTN node to convert

        Returns:
            Graph with task nodes and dependency edges

        Example:
            # HTN: deploy ∘ test ∘ build
            # Graph: build → test → deploy (dependency chain)
        """
        graph = Graph()
        visited = set()  # Track visited nodes to avoid duplicates

        def add_htn_to_graph(node: HTNNode, parent_id: Optional[str] = None) -> str:
            """Recursively add HTN nodes to graph.

            Args:
                node: Current HTN node
                parent_id: Parent task ID (for dependency edges)

            Returns:
                Task ID of the added node
            """
            task_id = node.task_id

            # Add node if not already present
            if task_id not in visited:
                visited.add(task_id)
                graph.add_node(
                    node_id=task_id,
                    data={
                        "description": node.description,
                        "preconditions": node.preconditions,
                        "effects": node.effects,
                        "metadata": node.metadata,
                        "is_primitive": node.is_primitive()
                    }
                )

            # Handle compound nodes (compositions, products, functors)
            if node.is_compound() and node.subtasks:
                operator = node.metadata.get("operator")

                # Sequential composition (∘): right-to-left dependency chain
                if operator == "∘":
                    # Subtasks already in right-to-left order
                    # Create chain: subtasks[0] → subtasks[1] → ... → subtasks[n-1]
                    prev_task_id = None
                    for i, subtask in enumerate(node.subtasks):
                        subtask_id = add_htn_to_graph(subtask, parent_id=task_id)

                        # Add dependency from previous task to current
                        if prev_task_id:
                            graph.add_edge(from_node=prev_task_id, to_node=subtask_id)

                        prev_task_id = subtask_id

                # Parallel product (×): all subtasks depend on parent, no inter-deps
                elif operator == "×":
                    for subtask in node.subtasks:
                        subtask_id = add_htn_to_graph(subtask, parent_id=task_id)
                        # No edges between subtasks (parallel execution)

                # Functor or generic compound: sequential dependencies
                else:
                    prev_task_id = None
                    for subtask in node.subtasks:
                        subtask_id = add_htn_to_graph(subtask, parent_id=task_id)

                        if prev_task_id:
                            graph.add_edge(from_node=prev_task_id, to_node=subtask_id)

                        prev_task_id = subtask_id

            return task_id

        # Build graph from HTN root
        add_htn_to_graph(htn)

        return graph

    def validate_dag(self, graph: Graph) -> List[str]:
        """Validate graph is a DAG (Directed Acyclic Graph).

        Checks:
        1. No circular dependencies (cycles)
        2. Graph is executable (has at least one node)

        Args:
            graph: Dependency graph to validate

        Returns:
            List of validation issues (empty list if valid)

        Example:
            issues = executor.validate_dag(graph)
            if issues:
                print(f"Validation failed: {', '.join(issues)}")
        """
        issues = []

        # Check 1: Graph must have nodes
        if len(graph.nodes) == 0:
            issues.append("Graph is empty (no tasks to execute)")
            return issues

        # Check 2: Detect cycles (DAG requirement)
        if graph.has_cycle():
            issues.append("Workflow contains circular dependencies (cycle detected)")

        return issues

    async def execute_graph(
        self,
        graph: Graph,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Execute graph in topological order.

        Executes tasks respecting dependency order:
        1. Validates graph is a DAG
        2. Computes topological sort (dependency order)
        3. Executes tasks sequentially in sorted order
        4. Propagates results as state to dependent tasks

        Args:
            graph: Dependency graph to execute
            verbose: Enable verbose output

        Returns:
            Dictionary mapping task_id → execution result

        Raises:
            ValueError: If graph has cycles or dependencies not met

        Example:
            results = await executor.execute_graph(graph, verbose=True)
            # results = {"build": {...}, "test": {...}, "deploy": {...}}
        """
        # Validate graph is a DAG
        issues = self.validate_dag(graph)
        if issues:
            raise ValueError(f"Cannot execute graph: {', '.join(issues)}")

        # Get topological order (dependency-respecting execution order)
        try:
            execution_order = graph.topological_sort()
        except ValueError as e:
            raise ValueError(f"Failed to compute execution order: {e}")

        if verbose:
            print(f"  Execution order: {' → '.join(execution_order)}")

        # Execute tasks in topological order
        results = {}
        state = {}  # Shared state for effects propagation

        for task_id in execution_order:
            node = graph.get_node(task_id)

            if not node:
                # Skip if node doesn't exist (shouldn't happen)
                continue

            # Check dependencies met (all predecessors executed)
            predecessors = graph.get_predecessors(task_id)
            dependencies_met = all(pred in results for pred in predecessors)

            if not dependencies_met:
                missing = [p for p in predecessors if p not in results]
                raise ValueError(
                    f"Dependencies not met for {task_id}: missing {missing}"
                )

            # Skip compound nodes (only execute primitives), but mark as completed
            if node.data and not node.data.get("is_primitive", True):
                if verbose:
                    print(f"  Skipping compound node: {task_id}")
                # Mark as completed so dependent tasks can proceed
                results[task_id] = {"skipped": True, "reason": "compound_node"}
                continue

            # Execute task via task executor
            if verbose:
                print(f"  Executing: {task_id}")

            try:
                result = await self.task_executor.execute_task(
                    task_name=task_id,
                    input_data=state
                )
                results[task_id] = result

                # Update state with task effects (if specified)
                if node.data and "effects" in node.data:
                    effects = node.data["effects"]
                    if isinstance(effects, dict):
                        state.update(effects)

                if verbose:
                    print(f"    ✓ Completed: {task_id}")

            except Exception as e:
                if verbose:
                    print(f"    ✗ Failed: {task_id} - {e}")
                raise ValueError(f"Task {task_id} failed: {e}")

        return results

    def get_execution_plan(self, graph: Graph) -> Dict[str, Any]:
        """Get execution plan without executing.

        Analyzes graph and returns execution metadata:
        - Execution order
        - Dependency count per task
        - Critical path
        - Parallelization opportunities

        Args:
            graph: Dependency graph

        Returns:
            Dictionary with execution plan details

        Raises:
            ValueError: If graph has cycles
        """
        # Validate DAG
        issues = self.validate_dag(graph)
        if issues:
            raise ValueError(f"Invalid graph: {', '.join(issues)}")

        # Get topological order
        execution_order = graph.topological_sort()

        # Calculate dependency counts
        dependency_counts = {}
        for node_id in graph.nodes:
            predecessors = graph.get_predecessors(node_id)
            dependency_counts[node_id] = len(predecessors)

        # Identify independent tasks (no dependencies)
        independent_tasks = [
            node_id for node_id, count in dependency_counts.items()
            if count == 0
        ]

        return {
            "execution_order": execution_order,
            "total_tasks": len(graph.nodes),
            "dependency_counts": dependency_counts,
            "independent_tasks": independent_tasks,
            "max_dependencies": max(dependency_counts.values()) if dependency_counts else 0
        }
