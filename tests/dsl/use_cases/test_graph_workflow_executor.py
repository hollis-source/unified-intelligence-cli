"""Tests for GraphWorkflowExecutor - HTN to graph conversion and execution.

Tests cover:
- HTN to graph conversion (composition, product, functors)
- DAG validation (cycle detection)
- Topological execution order
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, Mock
from src.dsl.use_cases.graph_workflow_executor import GraphWorkflowExecutor
from src.entities.htn import HTNNode
from src.entities.graph import Graph


@pytest.fixture
def mock_task_executor():
    """Create mock task executor."""
    executor = Mock()
    executor.execute_task = AsyncMock(return_value={"status": "success", "output": "completed"})
    return executor


@pytest.fixture
def graph_executor(mock_task_executor):
    """Create GraphWorkflowExecutor with mock executor."""
    return GraphWorkflowExecutor(mock_task_executor)


class TestHTNToGraphConversion:
    """Tests for HTN to graph conversion."""

    def test_htn_to_graph_simple_literal(self, graph_executor):
        """Test converting simple literal HTN to graph."""
        htn = HTNNode(task_id="build", description="Execute build")

        graph = graph_executor.htn_to_graph(htn)

        assert len(graph.nodes) == 1
        assert graph.has_node("build")
        node = graph.get_node("build")
        assert node.data["description"] == "Execute build"
        assert node.data["is_primitive"] == True

    def test_htn_to_graph_simple_composition(self, graph_executor):
        """Test converting composition (∘) to graph with dependencies."""
        # deploy ∘ build (build first, then deploy)
        htn = HTNNode(
            task_id="composition",
            description="Sequential composition (∘)",
            subtasks=[
                HTNNode(task_id="build", description="Execute build"),
                HTNNode(task_id="deploy", description="Execute deploy")
            ],
            metadata={"operator": "∘", "execution": "sequential"}
        )

        graph = graph_executor.htn_to_graph(htn)

        # Should have 3 nodes: composition, build, deploy
        assert len(graph.nodes) == 3
        assert graph.has_node("composition")
        assert graph.has_node("build")
        assert graph.has_node("deploy")

        # Should have edge: build → deploy (sequential dependency)
        successors_build = graph.get_successors("build")
        assert "deploy" in successors_build

    def test_htn_to_graph_three_stage_composition(self, graph_executor):
        """Test 3-stage composition: deploy ∘ test ∘ build."""
        # Inner composition: test ∘ build
        inner_comp = HTNNode(
            task_id="inner_comp",
            description="Sequential composition (∘)",
            subtasks=[
                HTNNode(task_id="build", description="Execute build"),
                HTNNode(task_id="test", description="Execute test")
            ],
            metadata={"operator": "∘"}
        )

        # Outer composition: deploy ∘ (test ∘ build)
        htn = HTNNode(
            task_id="pipeline",
            description="Sequential composition (∘)",
            subtasks=[
                inner_comp,
                HTNNode(task_id="deploy", description="Execute deploy")
            ],
            metadata={"operator": "∘"}
        )

        graph = graph_executor.htn_to_graph(htn)

        # Verify dependency chain: build → test → deploy
        assert graph.has_node("build")
        assert graph.has_node("test")
        assert graph.has_node("deploy")

        # Check edges
        assert "test" in graph.get_successors("build")
        assert "deploy" in graph.get_successors("inner_comp")

    def test_htn_to_graph_parallel_product(self, graph_executor):
        """Test converting product (×) to parallel branches."""
        # frontend × backend (parallel execution)
        htn = HTNNode(
            task_id="product",
            description="Parallel product (×)",
            subtasks=[
                HTNNode(task_id="frontend", description="Execute frontend"),
                HTNNode(task_id="backend", description="Execute backend")
            ],
            metadata={"operator": "×", "execution": "parallel"}
        )

        graph = graph_executor.htn_to_graph(htn)

        # Should have 3 nodes: product, frontend, backend
        assert len(graph.nodes) == 3

        # Parallel tasks should have NO edges between them
        successors_frontend = graph.get_successors("frontend")
        successors_backend = graph.get_successors("backend")

        assert "backend" not in successors_frontend
        assert "frontend" not in successors_backend

    def test_htn_to_graph_functor(self, graph_executor):
        """Test converting functor to graph."""
        htn = HTNNode(
            task_id="ci_pipeline",
            description="Functor: ci_pipeline",
            subtasks=[
                HTNNode(task_id="build", description="Execute build")
            ],
            metadata={"type": "functor"}
        )

        graph = graph_executor.htn_to_graph(htn)

        assert len(graph.nodes) == 2
        assert graph.has_node("ci_pipeline")
        assert graph.has_node("build")

    def test_htn_to_graph_mixed_structure(self, graph_executor):
        """Test converting mixed composition + product structure."""
        # (test × lint) ∘ build
        product = HTNNode(
            task_id="product",
            description="Parallel product (×)",
            subtasks=[
                HTNNode(task_id="test", description="Execute test"),
                HTNNode(task_id="lint", description="Execute lint")
            ],
            metadata={"operator": "×"}
        )

        htn = HTNNode(
            task_id="composition",
            description="Sequential composition (∘)",
            subtasks=[
                HTNNode(task_id="build", description="Execute build"),
                product
            ],
            metadata={"operator": "∘"}
        )

        graph = graph_executor.htn_to_graph(htn)

        # Should have nodes: composition, build, product, test, lint
        assert len(graph.nodes) == 5
        assert graph.has_node("build")
        assert graph.has_node("test")
        assert graph.has_node("lint")

        # Build should execute before product
        successors_build = graph.get_successors("build")
        assert "product" in successors_build


class TestDAGValidation:
    """Tests for DAG validation."""

    def test_validate_dag_empty_graph(self, graph_executor):
        """Test validation detects empty graph."""
        graph = Graph()

        issues = graph_executor.validate_dag(graph)

        assert len(issues) == 1
        assert "empty" in issues[0].lower()

    def test_validate_dag_no_cycles(self, graph_executor):
        """Test validation passes for acyclic graph."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")

        issues = graph_executor.validate_dag(graph)

        assert len(issues) == 0  # No issues, valid DAG

    def test_validate_dag_detects_simple_cycle(self, graph_executor):
        """Test validation detects simple cycle."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")  # Creates cycle

        issues = graph_executor.validate_dag(graph)

        assert len(issues) == 1
        assert "circular" in issues[0].lower() or "cycle" in issues[0].lower()

    def test_validate_dag_detects_complex_cycle(self, graph_executor):
        """Test validation detects longer cycle."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        graph.add_node("D")
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "D")
        graph.add_edge("D", "A")  # Creates cycle: A → B → C → D → A

        issues = graph_executor.validate_dag(graph)

        assert len(issues) == 1
        assert "cycle" in issues[0].lower()


class TestGraphExecution:
    """Tests for graph execution."""

    @pytest.mark.asyncio
    async def test_execute_graph_simple_linear(self, graph_executor, mock_task_executor):
        """Test executing simple linear graph."""
        graph = Graph()
        graph.add_node("A", data={"is_primitive": True})
        graph.add_node("B", data={"is_primitive": True})
        graph.add_edge("A", "B")

        results = await graph_executor.execute_graph(graph)

        # Should execute both tasks
        assert "A" in results
        assert "B" in results

        # Should call executor twice
        assert mock_task_executor.execute_task.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_graph_respects_topological_order(self, graph_executor, mock_task_executor):
        """Test execution respects topological order."""
        execution_order = []

        async def track_execution(task_name, input_data=None):
            execution_order.append(task_name)
            return {"status": "success"}

        mock_task_executor.execute_task = AsyncMock(side_effect=track_execution)

        graph = Graph()
        graph.add_node("build", data={"is_primitive": True})
        graph.add_node("test", data={"is_primitive": True})
        graph.add_node("deploy", data={"is_primitive": True})
        graph.add_edge("build", "test")
        graph.add_edge("test", "deploy")

        await graph_executor.execute_graph(graph)

        # Execution order should respect dependencies
        assert execution_order.index("build") < execution_order.index("test")
        assert execution_order.index("test") < execution_order.index("deploy")

    @pytest.mark.asyncio
    async def test_execute_graph_skips_compound_nodes(self, graph_executor, mock_task_executor):
        """Test execution skips compound (non-primitive) nodes."""
        graph = Graph()
        graph.add_node("composition", data={"is_primitive": False})  # Compound
        graph.add_node("task1", data={"is_primitive": True})  # Primitive
        graph.add_edge("composition", "task1")

        results = await graph_executor.execute_graph(graph)

        # Should only execute task1, mark composition as skipped
        assert "task1" in results
        assert "composition" in results  # Marked as skipped
        assert results["composition"]["skipped"] == True
        assert results["composition"]["reason"] == "compound_node"
        assert mock_task_executor.execute_task.call_count == 1  # Only task1 executed

    @pytest.mark.asyncio
    async def test_execute_graph_fails_on_cycle(self, graph_executor):
        """Test execution fails when graph has cycle."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")

        with pytest.raises(ValueError, match="cycle"):
            await graph_executor.execute_graph(graph)

    @pytest.mark.asyncio
    async def test_execute_graph_propagates_effects(self, graph_executor, mock_task_executor):
        """Test execution propagates effects to state."""
        graph = Graph()
        graph.add_node("A", data={
            "is_primitive": True,
            "effects": {"build_artifact": "app.jar"}
        })
        graph.add_node("B", data={"is_primitive": True})
        graph.add_edge("A", "B")

        await graph_executor.execute_graph(graph)

        # Second task should receive state with effects from first task
        # Check the second call's input_data
        calls = mock_task_executor.execute_task.call_args_list
        assert len(calls) == 2
        second_call_input = calls[1][1]["input_data"]
        assert "build_artifact" in second_call_input
        assert second_call_input["build_artifact"] == "app.jar"

    @pytest.mark.asyncio
    async def test_execute_graph_verbose_output(self, graph_executor, capsys):
        """Test verbose mode prints execution progress."""
        graph = Graph()
        graph.add_node("task1", data={"is_primitive": True})

        await graph_executor.execute_graph(graph, verbose=True)

        captured = capsys.readouterr()
        assert "Execution order" in captured.out
        assert "Executing: task1" in captured.out
        assert "✓ Completed: task1" in captured.out


class TestExecutionPlan:
    """Tests for execution plan generation."""

    def test_get_execution_plan_simple_graph(self, graph_executor):
        """Test execution plan for simple graph."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")

        plan = graph_executor.get_execution_plan(graph)

        assert plan["total_tasks"] == 3
        assert len(plan["execution_order"]) == 3
        assert plan["execution_order"][0] == "A"  # A has no dependencies
        assert "A" in plan["independent_tasks"]  # A is independent
        assert plan["max_dependencies"] == 1  # C depends on B (1 dep)

    def test_get_execution_plan_parallel_tasks(self, graph_executor):
        """Test execution plan identifies parallel opportunities."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        # A and B are independent, both feed into C
        graph.add_edge("A", "C")
        graph.add_edge("B", "C")

        plan = graph_executor.get_execution_plan(graph)

        # A and B are both independent (can run in parallel)
        assert len(plan["independent_tasks"]) == 2
        assert "A" in plan["independent_tasks"]
        assert "B" in plan["independent_tasks"]
        # C depends on 2 tasks
        assert plan["dependency_counts"]["C"] == 2
        assert plan["max_dependencies"] == 2

    def test_get_execution_plan_fails_on_cycle(self, graph_executor):
        """Test execution plan fails for graph with cycle."""
        graph = Graph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")

        with pytest.raises(ValueError, match="Invalid graph"):
            graph_executor.get_execution_plan(graph)
