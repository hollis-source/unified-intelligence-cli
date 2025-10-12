"""Tests for ProjectOrchestrator - Project execution lifecycle coordinator.

Tests cover:
- Lifecycle progression: PLAN → VERIFY → DECOMPOSE → EXECUTE
- Integration with GoalDecomposer, HTNDSLTranslator, StateManager, ExecutionCoordinator, FeedbackHandler
- Error handling and retry logic
- State persistence and artifact finalization
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time

from src.project_builder.orchestrator import ProjectOrchestrator
from src.interfaces import (
    ProjectResult,
    ExecutionResult,
    TaskStatus,
    ProjectState
)
from src.entities.htn.htn_node import HTNNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_goal_decomposer():
    """Mock GoalDecomposer with async decompose_goal."""
    decomposer = Mock()
    # Create simple HTN graph
    htn_graph = HTNNode(
        task_id="root",
        description="Root task",
        subtasks=[
            HTNNode(task_id="task1", description="Task 1", effects={"artifact": "result1"}),
            HTNNode(task_id="task2", description="Task 2", effects={"artifact": "result2"})
        ]
    )
    decomposer.decompose_goal = AsyncMock(return_value=htn_graph)
    return decomposer


@pytest.fixture
def mock_htn_dsl_translator():
    """Mock HTNDSLTranslator with translate method."""
    translator = Mock()
    # Return simple DSL workflow (task1 ∘ task2)
    dsl_workflow = Composition(
        left=Literal("task2"),
        right=Literal("task1")
    )
    translator.translate = Mock(return_value=dsl_workflow)
    return translator


@pytest.fixture
def mock_state_manager():
    """Mock StateManager with all required methods."""
    manager = Mock()
    
    # Create mock state
    mock_state = Mock(spec=ProjectState)
    mock_state.project_id = "test-project"
    mock_state.htn_graph = HTNNode(task_id="root", description="Root")
    mock_state.world_state = {}
    mock_state.task_status = {}
    mock_state.version = 1
    
    manager.initialize = Mock(return_value=mock_state)
    manager.validate_current_state = Mock(return_value=True)
    manager.apply_effects = Mock()
    manager.mark_task_status = Mock()
    manager.finalize_artifacts = Mock(return_value={"code": "generated_code.py"})
    manager.get_current_state = Mock(return_value=mock_state)
    manager.load_state = Mock(return_value=mock_state)
    manager.current_state = mock_state
    
    return manager


@pytest.fixture
def mock_execution_coordinator():
    """Mock ExecutionCoordinator with async execute_workflows."""
    coordinator = Mock()
    
    # Return successful execution results
    results = [
        ExecutionResult(
            task_id="task1",
            success=True,
            effects={"artifact": "result1"},
            metadata={"cost": 0.001}
        ),
        ExecutionResult(
            task_id="task2",
            success=True,
            effects={"artifact": "result2"},
            metadata={"cost": 0.002}
        )
    ]
    coordinator.execute_workflows = AsyncMock(return_value=results)
    return coordinator


@pytest.fixture
def mock_feedback_handler():
    """Mock FeedbackHandler with replan method."""
    handler = Mock()
    
    # Return updated state after replanning
    new_state = Mock(spec=ProjectState)
    new_state.task_status = {"task1": TaskStatus.PENDING}
    handler.replan = Mock(return_value=new_state)
    
    return handler


@pytest.fixture
def orchestrator(
    mock_goal_decomposer,
    mock_htn_dsl_translator,
    mock_state_manager,
    mock_execution_coordinator,
    mock_feedback_handler
):
    """Create ProjectOrchestrator with all mocked dependencies."""
    return ProjectOrchestrator(
        goal_decomposer=mock_goal_decomposer,
        htn_dsl_translator=mock_htn_dsl_translator,
        state_manager=mock_state_manager,
        execution_coordinator=mock_execution_coordinator,
        feedback_handler=mock_feedback_handler,
        max_retries=3
    )


@pytest.fixture
def orchestrator_no_coordinator(
    mock_goal_decomposer,
    mock_htn_dsl_translator,
    mock_state_manager
):
    """Create ProjectOrchestrator without ExecutionCoordinator (Phase 1 mode)."""
    return ProjectOrchestrator(
        goal_decomposer=mock_goal_decomposer,
        htn_dsl_translator=mock_htn_dsl_translator,
        state_manager=mock_state_manager,
        execution_coordinator=None,
        feedback_handler=None,
        max_retries=3
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestProjectOrchestratorInit:
    """Tests for ProjectOrchestrator initialization."""
    
    def test_init_with_all_dependencies(self, orchestrator):
        """Test initialization with all dependencies."""
        assert orchestrator.goal_decomposer is not None
        assert orchestrator.htn_dsl_translator is not None
        assert orchestrator.state_manager is not None
        assert orchestrator.execution_coordinator is not None
        assert orchestrator.feedback_handler is not None
        assert orchestrator.max_retries == 3
    
    def test_init_without_optional_dependencies(self, orchestrator_no_coordinator):
        """Test initialization without optional ExecutionCoordinator and FeedbackHandler."""
        assert orchestrator_no_coordinator.goal_decomposer is not None
        assert orchestrator_no_coordinator.htn_dsl_translator is not None
        assert orchestrator_no_coordinator.state_manager is not None
        assert orchestrator_no_coordinator.execution_coordinator is None
        assert orchestrator_no_coordinator.feedback_handler is None
    
    def test_init_custom_max_retries(
        self,
        mock_goal_decomposer,
        mock_htn_dsl_translator,
        mock_state_manager
    ):
        """Test initialization with custom max_retries."""
        orch = ProjectOrchestrator(
            goal_decomposer=mock_goal_decomposer,
            htn_dsl_translator=mock_htn_dsl_translator,
            state_manager=mock_state_manager,
            max_retries=5
        )
        assert orch.max_retries == 5


class TestExecuteProjectHappyPath:
    """Tests for successful project execution (happy path)."""
    
    @pytest.mark.asyncio
    async def test_execute_project_success(self, orchestrator, mock_goal_decomposer):
        """Test successful project execution through all phases."""
        result = await orchestrator.execute_project(
            goal="Create a REST API",
            project_id="test-project-1"
        )
        
        # Verify result
        assert result.success is True
        assert result.project_id == "test-project-1"
        assert result.artifacts == {"code": "generated_code.py"}
        assert result.execution_time > 0
        assert result.cost == 0.003  # 0.001 + 0.002
        assert len(result.task_results) == 2
        assert result.error == ""
    
    @pytest.mark.asyncio
    async def test_execute_project_calls_decomposer(
        self,
        orchestrator,
        mock_goal_decomposer
    ):
        """Test that execute_project calls goal decomposer."""
        await orchestrator.execute_project("Create API", "proj-1")
        
        mock_goal_decomposer.decompose_goal.assert_called_once_with("Create API")
    
    @pytest.mark.asyncio
    async def test_execute_project_initializes_state(
        self,
        orchestrator,
        mock_state_manager,
        mock_goal_decomposer
    ):
        """Test that execute_project initializes state with HTN graph."""
        await orchestrator.execute_project("Create API", "proj-1")

        # Verify state initialization
        mock_state_manager.initialize.assert_called_once()
        call_args = mock_state_manager.initialize.call_args
        assert call_args[0][0] == "proj-1"  # project_id
        assert isinstance(call_args[0][1], HTNNode)  # htn_graph

    @pytest.mark.asyncio
    async def test_execute_project_validates_state(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that execute_project validates initial state."""
        await orchestrator.execute_project("Create API", "proj-1")

        mock_state_manager.validate_current_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_project_translates_htn_to_dsl(
        self,
        orchestrator,
        mock_htn_dsl_translator
    ):
        """Test that execute_project translates HTN to DSL."""
        await orchestrator.execute_project("Create API", "proj-1")

        mock_htn_dsl_translator.translate.assert_called_once()
        call_args = mock_htn_dsl_translator.translate.call_args
        assert isinstance(call_args[0][0], HTNNode)

    @pytest.mark.asyncio
    async def test_execute_project_executes_workflow(
        self,
        orchestrator,
        mock_execution_coordinator
    ):
        """Test that execute_project executes DSL workflow."""
        await orchestrator.execute_project("Create API", "proj-1")

        mock_execution_coordinator.execute_workflows.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_project_applies_effects(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that execute_project applies task effects to state."""
        await orchestrator.execute_project("Create API", "proj-1")

        # Should apply effects for both successful tasks
        assert mock_state_manager.apply_effects.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_project_marks_task_status(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that execute_project marks task status."""
        await orchestrator.execute_project("Create API", "proj-1")

        # Should mark both tasks as completed
        assert mock_state_manager.mark_task_status.call_count == 2
        calls = mock_state_manager.mark_task_status.call_args_list
        assert calls[0][0][1] == TaskStatus.COMPLETED
        assert calls[1][0][1] == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_project_finalizes_artifacts(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that execute_project finalizes artifacts."""
        result = await orchestrator.execute_project("Create API", "proj-1")

        mock_state_manager.finalize_artifacts.assert_called_once()
        assert result.artifacts == {"code": "generated_code.py"}


class TestExecuteProjectWithFilePathExtraction:
    """Tests for file path extraction from goals."""

    @pytest.mark.asyncio
    async def test_execute_project_extracts_file_paths(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that execute_project extracts file paths from goal."""
        goal = "Create API in /opt/project/api.py"
        await orchestrator.execute_project(goal, "proj-1")

        # Verify file_path was added to world_state
        state = mock_state_manager.initialize.return_value
        assert "file_path" in state.world_state
        assert state.world_state["file_path"] == "/opt/project/api.py"

    @pytest.mark.asyncio
    async def test_execute_project_extracts_multiple_file_paths(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test extraction of multiple file paths."""
        goal = "Copy /opt/source.py to /opt/dest.py"
        await orchestrator.execute_project(goal, "proj-1")

        state = mock_state_manager.initialize.return_value
        assert "file_paths" in state.world_state
        assert len(state.world_state["file_paths"]) == 2


class TestExecuteProjectErrorHandling:
    """Tests for error handling during project execution."""

    @pytest.mark.asyncio
    async def test_execute_project_handles_decomposition_failure(
        self,
        orchestrator,
        mock_goal_decomposer
    ):
        """Test handling of goal decomposition failure."""
        mock_goal_decomposer.decompose_goal = AsyncMock(
            side_effect=ValueError("Invalid goal")
        )

        result = await orchestrator.execute_project("Invalid goal", "proj-1")

        assert result.success is False
        assert "Invalid goal" in result.error
        assert result.artifacts == {}

    @pytest.mark.asyncio
    async def test_execute_project_handles_validation_failure(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test handling of state validation failure."""
        mock_state_manager.validate_current_state = Mock(return_value=False)

        result = await orchestrator.execute_project("Create API", "proj-1")

        assert result.success is False
        assert "validation failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_project_handles_translation_failure(
        self,
        orchestrator,
        mock_htn_dsl_translator
    ):
        """Test handling of HTN to DSL translation failure."""
        mock_htn_dsl_translator.translate = Mock(
            side_effect=RuntimeError("Translation error")
        )

        result = await orchestrator.execute_project("Create API", "proj-1")

        assert result.success is False
        assert "Translation error" in result.error

    @pytest.mark.asyncio
    async def test_execute_project_handles_execution_failure(
        self,
        orchestrator,
        mock_execution_coordinator
    ):
        """Test handling of task execution failure."""
        # Return failed task result
        mock_execution_coordinator.execute_workflows = AsyncMock(
            return_value=[
                ExecutionResult(
                    task_id="task1",
                    success=False,
                    effects={},
                    error="Execution failed",
                    metadata={}
                )
            ]
        )

        result = await orchestrator.execute_project("Create API", "proj-1")

        assert result.success is False
        assert "Some tasks failed" in result.error


class TestFeedbackLoopIntegration:
    """Tests for feedback loop and retry logic."""

    @pytest.mark.asyncio
    async def test_execute_project_retries_on_failure(
        self,
        orchestrator,
        mock_execution_coordinator,
        mock_feedback_handler
    ):
        """Test that failed tasks trigger feedback loop retry."""
        # First execution fails, second succeeds
        mock_execution_coordinator.execute_workflows = AsyncMock(
            side_effect=[
                [ExecutionResult(task_id="task1", success=False, effects={}, error="Failed", metadata={})],
                [ExecutionResult(task_id="task1", success=True, effects={"artifact": "result"}, metadata={"cost": 0.001})]
            ]
        )

        result = await orchestrator.execute_project("Create API", "proj-1")

        # Should call execute_workflows twice (initial + retry)
        assert mock_execution_coordinator.execute_workflows.call_count == 2
        # Should call replan once
        mock_feedback_handler.replan.assert_called_once()
        # Should have both results (failed + successful retry)
        assert len(result.task_results) == 2
        # Last result should be successful
        assert result.task_results[-1].success is True

    @pytest.mark.asyncio
    async def test_execute_project_respects_max_retries(
        self,
        orchestrator,
        mock_execution_coordinator,
        mock_feedback_handler
    ):
        """Test that max_retries limit is respected."""
        # Always fail
        mock_execution_coordinator.execute_workflows = AsyncMock(
            return_value=[
                ExecutionResult(task_id="task1", success=False, effects={}, error="Failed", metadata={})
            ]
        )

        result = await orchestrator.execute_project("Create API", "proj-1")

        # Should try max_retries + 1 times (initial + 3 retries)
        assert mock_execution_coordinator.execute_workflows.call_count == 4
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_project_without_feedback_handler(
        self,
        orchestrator_no_coordinator,
        mock_state_manager
    ):
        """Test execution without feedback handler (no retries)."""
        # Mock execution to return failure
        with patch.object(orchestrator_no_coordinator, '_execute_tasks_mock') as mock_exec:
            mock_exec.return_value = [
                ExecutionResult(task_id="task1", success=False, effects={}, error="Failed", metadata={})
            ]

            result = await orchestrator_no_coordinator.execute_project("Create API", "proj-1")

            # Should only execute once (no retries without feedback handler)
            assert mock_exec.call_count == 1
            assert result.success is False


class TestResumeProject:
    """Tests for resuming previously started projects."""

    @pytest.mark.asyncio
    async def test_resume_project_loads_state(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test that resume_project loads existing state."""
        result = await orchestrator.resume_project("existing-project")

        mock_state_manager.load_state.assert_called_once_with("existing-project")

    @pytest.mark.asyncio
    async def test_resume_project_retranslates_htn(
        self,
        orchestrator,
        mock_htn_dsl_translator
    ):
        """Test that resume_project re-translates HTN to DSL."""
        await orchestrator.resume_project("existing-project")

        mock_htn_dsl_translator.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_project_continues_execution(
        self,
        orchestrator,
        mock_execution_coordinator
    ):
        """Test that resume_project continues execution."""
        result = await orchestrator.resume_project("existing-project")

        mock_execution_coordinator.execute_workflows.assert_called_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_resume_project_handles_load_failure(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test handling of state load failure."""
        mock_state_manager.load_state = Mock(
            side_effect=ValueError("Project not found")
        )

        result = await orchestrator.resume_project("nonexistent-project")

        assert result.success is False
        assert "Resume failed" in result.error


class TestMockExecution:
    """Tests for mock execution (Phase 1 fallback)."""

    @pytest.mark.asyncio
    async def test_execute_tasks_mock_executes_primitives(
        self,
        orchestrator_no_coordinator,
        mock_state_manager
    ):
        """Test that mock execution executes all primitive tasks."""
        # Create HTN with 3 primitive tasks
        htn_graph = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[
                HTNNode(task_id="task1", description="Task 1", effects={"a": "1"}),
                HTNNode(task_id="task2", description="Task 2", effects={"b": "2"}),
                HTNNode(task_id="task3", description="Task 3", effects={"c": "3"})
            ]
        )

        results = await orchestrator_no_coordinator._execute_tasks_mock(
            htn_graph,
            mock_state_manager.current_state
        )

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_tasks_mock_marks_in_progress(
        self,
        orchestrator_no_coordinator,
        mock_state_manager
    ):
        """Test that mock execution marks tasks as in progress."""
        htn_graph = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[HTNNode(task_id="task1", description="Task 1")]
        )

        await orchestrator_no_coordinator._execute_tasks_mock(
            htn_graph,
            mock_state_manager.current_state
        )

        # Should mark task as IN_PROGRESS
        mock_state_manager.mark_task_status.assert_called_with("task1", TaskStatus.IN_PROGRESS)

    def test_get_primitive_tasks_extracts_leaves(self, orchestrator):
        """Test extraction of primitive (leaf) tasks from HTN."""
        # Create nested HTN
        htn_graph = HTNNode(
            task_id="root",
            description="Root",
            subtasks=[
                HTNNode(
                    task_id="compound1",
                    description="Compound 1",
                    subtasks=[
                        HTNNode(task_id="leaf1", description="Leaf 1"),
                        HTNNode(task_id="leaf2", description="Leaf 2")
                    ]
                ),
                HTNNode(task_id="leaf3", description="Leaf 3")
            ]
        )

        primitives = orchestrator._get_primitive_tasks(htn_graph)

        assert len(primitives) == 3
        assert {p.task_id for p in primitives} == {"leaf1", "leaf2", "leaf3"}


class TestLifecycleProgression:
    """Tests for lifecycle phase progression."""

    @pytest.mark.asyncio
    async def test_lifecycle_plan_phase(
        self,
        orchestrator,
        mock_goal_decomposer
    ):
        """Test PLAN phase execution."""
        await orchestrator.execute_project("Create API", "proj-1")

        # PLAN phase should call decompose_goal
        mock_goal_decomposer.decompose_goal.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_verify_phase(
        self,
        orchestrator,
        mock_state_manager
    ):
        """Test VERIFY phase execution."""
        await orchestrator.execute_project("Create API", "proj-1")

        # VERIFY phase should validate state
        mock_state_manager.validate_current_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_decompose_phase(
        self,
        orchestrator,
        mock_htn_dsl_translator
    ):
        """Test DECOMPOSE phase execution."""
        await orchestrator.execute_project("Create API", "proj-1")

        # DECOMPOSE phase should translate HTN to DSL
        mock_htn_dsl_translator.translate.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_execute_phase(
        self,
        orchestrator,
        mock_execution_coordinator
    ):
        """Test EXECUTE phase execution."""
        await orchestrator.execute_project("Create API", "proj-1")

        # EXECUTE phase should execute workflows
        mock_execution_coordinator.execute_workflows.assert_called_once()

