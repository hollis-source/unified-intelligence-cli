"""Tests for ExecutionCoordinator - Task routing and execution.

Tests cover:
- Task routing to agent teams via TeamRouter
- Adaptive model selection
- DSL workflow execution (Composition, Product)
- Parallel execution support
- Timeout handling and graceful degradation
- Precondition checking and effect application
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.project_builder.execution.coordinator import ExecutionCoordinator
from src.interfaces import ProjectState, ExecutionResult, TaskStatus
from src.entities.htn.htn_node import HTNNode
from src.entities import Task, Agent, AgentTeam
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.routing.adaptive_interfaces import SelectionStrategy


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_team_router():
    """Mock TeamRouter for agent routing."""
    router = Mock()
    # Return mock agent
    mock_agent = Agent(
        role="Backend Engineer",
        capabilities=["coding", "api"]
    )
    router.route = Mock(return_value=mock_agent)
    return router


@pytest.fixture
def mock_model_selector():
    """Mock AdaptiveModelSelector for model selection."""
    selector = Mock()
    selector.select_model = Mock(return_value="qwen3-hf-inference")
    return selector


@pytest.fixture
def mock_teams():
    """Mock agent teams."""
    backend_team = AgentTeam(
        name="Backend Team",
        domain="backend",
        agents=[
            Agent(role="Backend Engineer", capabilities=["coding"])
        ]
    )
    return [backend_team]


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for real execution."""
    provider = Mock()
    provider.generate = Mock(return_value="Generated code")
    return provider


@pytest.fixture
def coordinator(mock_team_router, mock_model_selector, mock_teams):
    """Create ExecutionCoordinator with mocked dependencies."""
    return ExecutionCoordinator(
        team_router=mock_team_router,
        model_selector=mock_model_selector,
        teams=mock_teams,
        llm_provider=None,  # Use mock execution
        prompt_mode="manual"
    )


@pytest.fixture
def coordinator_with_llm(mock_team_router, mock_model_selector, mock_teams, mock_llm_provider):
    """Create ExecutionCoordinator with real LLM execution."""
    return ExecutionCoordinator(
        team_router=mock_team_router,
        model_selector=mock_model_selector,
        teams=mock_teams,
        llm_provider=mock_llm_provider,
        prompt_mode="manual"
    )


@pytest.fixture
def sample_state():
    """Create sample ProjectState."""
    htn_graph = HTNNode(
        task_id="root",
        description="Root task",
        subtasks=[
            HTNNode(
                task_id="task1",
                description="Task 1",
                preconditions={},
                effects={"artifact": "result1"}
            ),
            HTNNode(
                task_id="task2",
                description="Task 2",
                preconditions={"artifact": None},
                effects={"final": "done"}
            )
        ]
    )
    
    state = Mock(spec=ProjectState)
    state.project_id = "test-project"
    state.htn_graph = htn_graph
    state.world_state = {}
    state.task_status = {}
    
    return state


# ============================================================================
# Test Classes
# ============================================================================

class TestExecutionCoordinatorInit:
    """Tests for ExecutionCoordinator initialization."""
    
    def test_init_with_all_dependencies(self, coordinator):
        """Test initialization with all dependencies."""
        assert coordinator.team_router is not None
        assert coordinator.model_selector is not None
        assert len(coordinator.teams) == 1
        assert coordinator.llm_executor is None  # No LLM provider
    
    def test_init_with_llm_provider(self, coordinator_with_llm):
        """Test initialization with LLM provider."""
        assert coordinator_with_llm.llm_executor is not None
    
    def test_init_with_remote_fs(
        self,
        mock_team_router,
        mock_model_selector,
        mock_teams
    ):
        """Test initialization with remote filesystem."""
        mock_remote_fs = Mock()
        coord = ExecutionCoordinator(
            team_router=mock_team_router,
            model_selector=mock_model_selector,
            teams=mock_teams,
            remote_fs=mock_remote_fs
        )
        assert coord.remote_fs is mock_remote_fs


class TestExecuteWorkflowsBasic:
    """Tests for basic workflow execution."""
    
    @pytest.mark.asyncio
    async def test_execute_workflows_single_task(
        self,
        coordinator,
        sample_state
    ):
        """Test execution of single task workflow."""
        workflow = Literal("task1")
        
        results = await coordinator.execute_workflows(workflow, sample_state)
        
        assert len(results) == 1
        assert results[0].task_id == "task1"
        assert results[0].success is True
    
    @pytest.mark.asyncio
    async def test_execute_workflows_composition(
        self,
        coordinator,
        sample_state
    ):
        """Test execution of composition (sequential) workflow."""
        # task1 ∘ task2 (executes task2 then task1)
        workflow = Composition(
            left=Literal("task1"),
            right=Literal("task2")
        )
        
        results = await coordinator.execute_workflows(workflow, sample_state)
        
        assert len(results) == 2
        # Composition executes right-to-left
        assert results[0].task_id == "task2"
        assert results[1].task_id == "task1"
    
    @pytest.mark.asyncio
    async def test_execute_workflows_product(
        self,
        coordinator,
        sample_state
    ):
        """Test execution of product (parallel) workflow."""
        # task1 × task2 (Phase 2: executes sequentially)
        workflow = Product(
            left=Literal("task1"),
            right=Literal("task2")
        )
        
        results = await coordinator.execute_workflows(workflow, sample_state)
        
        assert len(results) == 2
        # Product executes left then right (Phase 2)
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"
    
    @pytest.mark.asyncio
    async def test_execute_workflows_applies_effects(
        self,
        coordinator,
        sample_state
    ):
        """Test that task effects are applied to state."""
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        # Effects should be applied to world_state
        assert "artifact" in sample_state.world_state
        assert sample_state.world_state["artifact"] == "result1"


class TestTaskRouting:
    """Tests for task routing to agent teams."""
    
    @pytest.mark.asyncio
    async def test_execute_workflows_routes_to_team(
        self,
        coordinator,
        mock_team_router,
        sample_state
    ):
        """Test that tasks are routed to appropriate teams."""
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        # Should call router.route
        mock_team_router.route.assert_called_once()
        call_args = mock_team_router.route.call_args
        assert isinstance(call_args[0][0], Task)
    
    @pytest.mark.asyncio
    async def test_execute_workflows_infers_task_type(
        self,
        coordinator,
        sample_state
    ):
        """Test that task type is inferred from description."""
        # Modify HTN node description to trigger type inference
        sample_state.htn_graph.subtasks[0].description = "Write test for API"
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        # Task type should be inferred as 'testing'
        call_args = coordinator.team_router.route.call_args
        task = call_args[0][0]
        assert task.task_type == "testing"
    
    @pytest.mark.asyncio
    async def test_execute_workflows_creates_task_entity(
        self,
        coordinator,
        mock_team_router,
        sample_state
    ):
        """Test that Task entity is created correctly."""
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        call_args = mock_team_router.route.call_args
        task = call_args[0][0]
        assert isinstance(task, Task)
        assert task.description == "Task 1"
        assert task.task_id == "task1"


class TestModelSelection:
    """Tests for adaptive model selection."""
    
    @pytest.mark.asyncio
    async def test_execute_workflows_selects_model(
        self,
        coordinator,
        mock_model_selector,
        sample_state
    ):
        """Test that model is selected for each task."""
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        mock_model_selector.select_model.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_model_selection_strategy_for_design_tasks(
        self,
        coordinator,
        mock_model_selector,
        sample_state
    ):
        """Test that design tasks use MAXIMIZE_QUALITY strategy."""
        sample_state.htn_graph.subtasks[0].description = "Design API schema"
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        call_args = mock_model_selector.select_model.call_args
        requirements = call_args[1]['requirements']
        assert requirements.strategy == SelectionStrategy.MAXIMIZE_QUALITY
    
    @pytest.mark.asyncio
    async def test_model_selection_strategy_for_testing_tasks(
        self,
        coordinator,
        mock_model_selector,
        sample_state
    ):
        """Test that testing tasks use MINIMIZE_LATENCY strategy."""
        sample_state.htn_graph.subtasks[0].description = "Run unit tests"
        workflow = Literal("task1")
        
        await coordinator.execute_workflows(workflow, sample_state)
        
        call_args = mock_model_selector.select_model.call_args
        requirements = call_args[1]['requirements']
        assert requirements.strategy == SelectionStrategy.MINIMIZE_LATENCY

    @pytest.mark.asyncio
    async def test_model_selection_fallback_on_error(
        self,
        coordinator,
        mock_model_selector,
        sample_state
    ):
        """Test fallback to default model on selection error."""
        mock_model_selector.select_model = Mock(
            side_effect=ValueError("No suitable model")
        )
        workflow = Literal("task1")

        results = await coordinator.execute_workflows(workflow, sample_state)

        # Should still succeed with fallback model
        assert len(results) == 1
        assert results[0].success is True


class TestPreconditionChecking:
    """Tests for precondition validation."""

    @pytest.mark.asyncio
    async def test_execute_task_checks_preconditions(
        self,
        coordinator,
        sample_state
    ):
        """Test that preconditions are checked before execution."""
        # task2 has precondition: {"artifact": null}
        workflow = Literal("task2")

        results = await coordinator.execute_workflows(workflow, sample_state)

        # Should fail because precondition not satisfied
        assert results[0].success is False
        assert "Preconditions not satisfied" in results[0].error

    @pytest.mark.asyncio
    async def test_execute_task_succeeds_with_satisfied_preconditions(
        self,
        coordinator,
        sample_state
    ):
        """Test that task succeeds when preconditions are satisfied."""
        # Satisfy precondition
        sample_state.world_state["artifact"] = "result1"
        workflow = Literal("task2")

        results = await coordinator.execute_workflows(workflow, sample_state)

        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_execute_workflows_applies_effects_sequentially(
        self,
        coordinator,
        sample_state
    ):
        """Test that effects from earlier tasks satisfy later preconditions."""
        # task1 produces "artifact", task2 requires "artifact"
        # Composition (task2 ∘ task1) executes task1 first, then task2
        workflow = Composition(
            left=Literal("task2"),  # Executes second (after task1)
            right=Literal("task1")  # Executes first
        )

        results = await coordinator.execute_workflows(workflow, sample_state)

        # Both tasks should succeed
        assert len(results) == 2
        assert results[0].success is True  # task1 (executed first)
        assert results[1].success is True  # task2 (executed second, precondition satisfied)


class TestTimeoutHandling:
    """Tests for task timeout handling."""

    @pytest.mark.asyncio
    async def test_execute_task_timeout_for_validation_tasks(
        self,
        coordinator_with_llm,
        sample_state
    ):
        """Test timeout handling for validation tasks (graceful degradation)."""
        # Mock LLM executor to timeout
        with patch.object(coordinator_with_llm.llm_executor, 'execute') as mock_exec:
            mock_exec.side_effect = asyncio.TimeoutError()

            sample_state.htn_graph.subtasks[0].description = "Validate API schema"
            workflow = Literal("task1")

            results = await coordinator_with_llm.execute_workflows(workflow, sample_state)

            # Validation tasks should succeed with partial status
            assert results[0].success is True
            assert results[0].metadata.get("partial") is True
            assert results[0].metadata.get("timeout") is True

    @pytest.mark.asyncio
    async def test_execute_task_timeout_for_implementation_tasks(
        self,
        coordinator_with_llm,
        sample_state
    ):
        """Test timeout handling for implementation tasks (hard failure)."""
        with patch.object(coordinator_with_llm.llm_executor, 'execute') as mock_exec:
            mock_exec.side_effect = asyncio.TimeoutError()

            sample_state.htn_graph.subtasks[0].description = "Implement API endpoint"
            workflow = Literal("task1")

            results = await coordinator_with_llm.execute_workflows(workflow, sample_state)

            # Implementation tasks should fail on timeout
            assert results[0].success is False
            assert "timed out" in results[0].error.lower()

    def test_task_timeout_configuration(self, coordinator):
        """Test that different task types have different timeouts."""
        assert coordinator.TASK_TIMEOUTS["validation"] == 300
        assert coordinator.TASK_TIMEOUTS["testing"] == 300
        assert coordinator.TASK_TIMEOUTS["implementation"] == 120
        assert coordinator.TASK_TIMEOUTS["documentation"] == 180


class TestParentEffectsApplication:
    """Tests for parent task effects application."""

    @pytest.mark.asyncio
    async def test_apply_parent_effects_when_subtasks_complete(
        self,
        coordinator,
        sample_state
    ):
        """Test that parent effects are applied when all subtasks complete."""
        # Add parent effects
        sample_state.htn_graph.effects = {"project_complete": True}

        # Execute all subtasks
        workflow = Composition(
            left=Literal("task1"),
            right=Literal("task2")
        )

        # Mark tasks as completed
        sample_state.task_status = {
            "task1": TaskStatus.COMPLETED,
            "task2": TaskStatus.COMPLETED
        }

        await coordinator.execute_workflows(workflow, sample_state)

        # Parent effects should be applied
        assert "project_complete" in sample_state.world_state


class TestErrorHandling:
    """Tests for error handling during execution."""

    @pytest.mark.asyncio
    async def test_execute_workflows_handles_missing_htn_node(
        self,
        coordinator,
        sample_state
    ):
        """Test handling of missing HTN node for task."""
        workflow = Literal("nonexistent_task")

        results = await coordinator.execute_workflows(workflow, sample_state)

        # Should return empty results (task skipped)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_task_handles_execution_error(
        self,
        coordinator_with_llm,
        sample_state
    ):
        """Test handling of execution errors."""
        with patch.object(coordinator_with_llm.llm_executor, 'execute') as mock_exec:
            mock_exec.side_effect = RuntimeError("Execution failed")

            workflow = Literal("task1")

            results = await coordinator_with_llm.execute_workflows(workflow, sample_state)

            assert results[0].success is False
            assert "Execution failed" in results[0].error


class TestTaskTypeInference:
    """Tests for task type inference from descriptions."""

    @pytest.mark.parametrize("description,expected_type", [
        ("Design API schema", "design"),
        ("Implement user authentication", "implementation"),
        ("Write unit tests", "testing"),
        ("Document the API", "documentation"),
        ("Research best practices", "research"),
        ("Deploy to production", "deployment"),
        ("Validate input data", "testing"),
        ("Create database table", "implementation")  # Changed from "schema" which triggers "design"
    ])
    def test_infer_task_type(self, coordinator, description, expected_type):
        """Test task type inference from various descriptions."""
        htn_node = HTNNode(task_id="test", description=description)

        task_type = coordinator._infer_task_type(htn_node)

        assert task_type == expected_type

    def test_infer_task_type_default(self, coordinator):
        """Test default task type for unknown descriptions."""
        htn_node = HTNNode(task_id="test", description="Do something")

        task_type = coordinator._infer_task_type(htn_node)

        assert task_type == "general"


class TestExecutionOrderExtraction:
    """Tests for execution order extraction from DSL."""

    def test_get_execution_order_literal(self, coordinator):
        """Test execution order for single literal."""
        workflow = Literal("task1")

        order = coordinator._get_execution_order(workflow)

        assert order == ["task1"]

    def test_get_execution_order_composition(self, coordinator):
        """Test execution order for composition (right-to-left)."""
        workflow = Composition(
            left=Literal("task1"),
            right=Literal("task2")
        )

        order = coordinator._get_execution_order(workflow)

        # Composition executes right then left
        assert order == ["task2", "task1"]

    def test_get_execution_order_product(self, coordinator):
        """Test execution order for product (left-to-right in Phase 2)."""
        workflow = Product(
            left=Literal("task1"),
            right=Literal("task2")
        )

        order = coordinator._get_execution_order(workflow)

        # Product executes left then right (Phase 2)
        assert order == ["task1", "task2"]

    def test_get_execution_order_nested(self, coordinator):
        """Test execution order for nested workflows."""
        # (task1 ∘ task2) × task3
        workflow = Product(
            left=Composition(
                left=Literal("task1"),
                right=Literal("task2")
            ),
            right=Literal("task3")
        )

        order = coordinator._get_execution_order(workflow)

        # Should be: task2, task1, task3
        assert order == ["task2", "task1", "task3"]
