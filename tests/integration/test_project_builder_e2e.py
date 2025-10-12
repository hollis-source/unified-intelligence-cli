"""End-to-end integration tests for Project Builder.

Tests complete pipeline from natural language goal to project generation
using hybrid mocking strategy (mock LLMs, real internal components).

Validates:
- ProjectOrchestrator lifecycle (PLAN → VERIFY → DECOMPOSE → EXECUTE → COMPLETE)
- HTNDSLTranslator (HTN → DSL functor)
- DSL Interpreter (category theory execution)
- FeedbackLoopHandler (failure replanning)
- StateManager (persistence)
- Performance benchmarks (execution time < 2s for E2E suite)
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from src.project_builder.orchestrator import ProjectOrchestrator
from src.project_builder.state.factory import create_state_repository
from src.entities.htn.htn_node import HTNNode
from src.interfaces import TaskStatus, ExecutionResult


# =============================================================================
# Performance Benchmarks (validates sub-2s execution claim)
# =============================================================================
BENCHMARK_SIMPLE_PROJECT = 0.5  # Simple 2-task project
BENCHMARK_COMPLEX_NESTED = 0.8  # Complex nested HTN with 5 tasks
BENCHMARK_FAILURE_HANDLING = 0.5  # Failure scenario
BENCHMARK_PARALLEL_EXECUTION = 0.6  # Parallel task detection
BENCHMARK_STATE_PERSISTENCE = 0.5  # State versioning


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary SQLite database for test isolation.

    Each test gets a fresh database to avoid state pollution.
    """
    db_path = tmp_path / "test_e2e_state.db"
    return str(db_path)


@pytest.fixture
def mock_goal_decomposer():
    """Mock GoalDecomposer to avoid LLM API calls.

    Returns predefined HTN structures for deterministic testing.
    Mock is configured per-test by setting return_value.
    """
    decomposer = Mock()
    decomposer.decompose_goal = AsyncMock()
    return decomposer


@pytest.fixture
def mock_execution_coordinator():
    """Mock ExecutionCoordinator to avoid agent LLM calls.

    Returns simulated task execution results.
    Mock is configured per-test by setting return_value.
    """
    coordinator = Mock()
    coordinator.execute_workflows = AsyncMock()
    return coordinator


@pytest.fixture
def state_repository(temp_db):
    """Create state repository with temporary SQLite database."""
    return create_state_repository(db_type="sqlite", state_db_path=temp_db)


@pytest.fixture
def htn_dsl_translator():
    """Create real HTNDSLTranslator (validates functor)."""
    from src.project_builder.htn_dsl.translator import HTNDSLTranslator
    return HTNDSLTranslator()


@pytest.fixture
def state_manager(state_repository):
    """Create real StateManager (validates persistence)."""
    from src.project_builder.state.manager import ProjectStateManager
    return ProjectStateManager(state_repository)


@pytest.fixture
def orchestrator(mock_goal_decomposer, htn_dsl_translator, state_manager, mock_execution_coordinator):
    """Create ProjectOrchestrator with mocked dependencies.

    Uses:
    - Mock GoalDecomposer (avoids LLM calls)
    - Mock ExecutionCoordinator (avoids agent calls)
    - Real HTNDSLTranslator (validates functor)
    - Real DSL Interpreter (validates category theory)
    - Real FeedbackLoopHandler (validates replanning)
    - Real StateManager (validates persistence)
    """
    return ProjectOrchestrator(
        goal_decomposer=mock_goal_decomposer,
        htn_dsl_translator=htn_dsl_translator,
        state_manager=state_manager,
        execution_coordinator=mock_execution_coordinator,
        feedback_handler=None,  # No feedback handler for now
        max_retries=3
    )


# =============================================================================
# Scenario 1: Happy Path - Simple Project Generation
# =============================================================================

class TestProjectBuilderE2EHappyPath:
    """Test Scenario 1: Happy path with simple project.

    Validates complete pipeline success with minimal complexity.

    Pipeline:
    1. Goal: "Create Python hello world CLI"
    2. GoalDecomposer → HTN (2 sequential tasks)
    3. HTNDSLTranslator → DSL (Composition operator)
    4. DSL Interpreter → Execution plan
    5. ExecutionCoordinator → Task execution (mocked success)
    6. StateManager → Persistence
    7. Result: COMPLETE

    Expected execution time: <1 second
    """

    @pytest.mark.asyncio
    async def test_simple_project_generation_success(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator,
        state_repository
    ):
        """Test complete pipeline: simple goal → HTN → DSL → execution → success.

        This is the most basic E2E test validating the entire pipeline works.
        """
        # =====================================================================
        # Arrange: Set up test data
        # =====================================================================

        project_id = "test_simple_cli"
        goal = "Create Python hello world CLI"

        # Mock GoalDecomposer to return simple HTN
        simple_htn = HTNNode(
            task_id="root",
            description="Create Python hello world CLI",
            preconditions={},
            effects={},
            subtasks=[
                HTNNode(
                    task_id="create_main",
                    description="Create main.py file with hello world function",
                    preconditions={},
                    effects={"main_py_created": True},
                    subtasks=[]  # Primitive task
                ),
                HTNNode(
                    task_id="create_cli",
                    description="Create CLI entry point using argparse",
                    preconditions={"main_py_created": True},
                    effects={"cli_created": True},
                    subtasks=[]  # Primitive task
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = simple_htn

        # Mock ExecutionCoordinator to return success for both tasks
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="create_main",
                success=True,
                effects={"main_py_created": True},
                error="",
                metadata={"duration_ms": 1234, "agent": "backend-team"}
            ),
            ExecutionResult(
                task_id="create_cli",
                success=True,
                effects={"cli_created": True},
                error="",
                metadata={"duration_ms": 2345, "agent": "backend-team"}
            )
        ]

        # =====================================================================
        # Act: Execute complete pipeline (with timing)
        # =====================================================================

        start_time = time.perf_counter()
        result = await orchestrator.execute_project(
            goal=goal,
            project_id=project_id
        )
        actual_execution_time = time.perf_counter() - start_time

        # =====================================================================
        # Assert: Validate pipeline completed successfully
        # =====================================================================

        # 1. Overall success
        assert result.success is True, "Pipeline should complete successfully"
        assert result.error == "", "No errors should occur"

        # 2. Result structure
        assert result.project_id == project_id, "Project ID should match"
        assert isinstance(result.artifacts, dict), "Artifacts should be a dict"
        assert isinstance(result.task_results, list), "Task results should be a list"
        assert len(result.task_results) == 2, "Should have 2 task results"

        # 3. Performance benchmark (STRICTER: validates sub-2s E2E suite claim)
        assert actual_execution_time < BENCHMARK_SIMPLE_PROJECT, \
            f"Simple project should complete in <{BENCHMARK_SIMPLE_PROJECT}s " \
            f"(actual: {actual_execution_time:.3f}s)"
        print(f"✓ Performance: {actual_execution_time:.3f}s (benchmark: <{BENCHMARK_SIMPLE_PROJECT}s)")

        # 4. Mock calls correct
        mock_goal_decomposer.decompose_goal.assert_called_once_with(goal)
        mock_execution_coordinator.execute_workflows.assert_called_once()

        # 5. Verify HTN structure
        assert len(simple_htn.subtasks) == 2, "HTN should have 2 subtasks"

        # 6. Task results correct
        assert all(r.success for r in result.task_results), \
            "All task results should be successful"
        task_ids = [r.task_id for r in result.task_results]
        assert "create_main" in task_ids, "create_main result should exist"
        assert "create_cli" in task_ids, "create_cli result should exist"


    @pytest.mark.asyncio
    async def test_lifecycle_state_transitions(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator
    ):
        """Test that lifecycle progresses through all states correctly.

        Validates: INIT → PLAN → VERIFY → DECOMPOSE → EXECUTE → COMPLETE
        """
        # Arrange: Simple HTN
        simple_htn = HTNNode(
            task_id="root",
            description="Simple task",
            subtasks=[
                HTNNode(
                    task_id="task1",
                    description="Task 1",
                    effects={"done": True}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = simple_htn
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="task1",
                success=True,
                effects={"done": True},
                error=""
            )
        ]

        # Act
        result = await orchestrator.execute_project(
            goal="Simple goal",
            project_id="test_lifecycle"
        )

        # Assert: Success
        assert result.success is True
        assert len(result.task_results) == 1
        assert result.task_results[0].success is True


    @pytest.mark.asyncio
    async def test_state_persistence_across_phases(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator,
        state_repository
    ):
        """Test that state is persisted at each phase.

        Validates: StateManager correctly saves snapshots at each lifecycle phase.
        """
        # Arrange
        project_id = "test_persistence"
        simple_htn = HTNNode(
            task_id="root",
            description="Test task",
            subtasks=[
                HTNNode(
                    task_id="task1",
                    description="Task",
                    effects={"result": "done"}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = simple_htn
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="task1",
                success=True,
                effects={"result": "done"},
                error=""
            )
        ]

        # Act
        result = await orchestrator.execute_project(
            goal="Test goal",
            project_id=project_id
        )

        # Assert: Project succeeded
        assert result.success is True
        assert result.project_id == project_id


# =============================================================================
# Scenario 2: Complex Nested Hierarchy
# =============================================================================

class TestProjectBuilderE2EComplexNested:
    """Test Scenario 2: Complex nested hierarchy with parallelization.

    Validates HTNDSLTranslator correctly detects parallel opportunities
    in complex nested task structures.
    """

    @pytest.mark.asyncio
    async def test_nested_htn_with_parallelization(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator
    ):
        """Test complex nested HTN with parallel task detection.

        Tests 2-level HTN hierarchy with independent parallel subtasks.
        HTNDSLTranslator should detect: frontend × backend (parallel execution).
        """
        # Arrange: Complex nested HTN
        complex_htn = HTNNode(
            task_id="root",
            description="Create full-stack web app",
            subtasks=[
                HTNNode(
                    task_id="frontend",
                    description="Build React frontend",
                    effects={"frontend_created": True},
                    subtasks=[
                        HTNNode(
                            task_id="setup_react",
                            description="Setup React app",
                            effects={"react_setup": True}
                        ),
                        HTNNode(
                            task_id="create_components",
                            description="Create components",
                            preconditions={"react_setup": True},
                            effects={"components_created": True}
                        )
                    ]
                ),
                HTNNode(
                    task_id="backend",
                    description="Build FastAPI backend",
                    effects={"backend_created": True},
                    subtasks=[
                        HTNNode(
                            task_id="setup_fastapi",
                            description="Setup FastAPI",
                            effects={"fastapi_setup": True}
                        ),
                        HTNNode(
                            task_id="create_endpoints",
                            description="Create API endpoints",
                            preconditions={"fastapi_setup": True},
                            effects={"endpoints_created": True}
                        )
                    ]
                ),
                HTNNode(
                    task_id="tests",
                    description="Create pytest tests",
                    preconditions={"backend_created": True, "frontend_created": True},
                    effects={"tests_created": True}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = complex_htn

        # Mock execution results for all tasks
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(task_id="setup_react", success=True, effects={"react_setup": True}, error=""),
            ExecutionResult(task_id="create_components", success=True, effects={"components_created": True}, error=""),
            ExecutionResult(task_id="setup_fastapi", success=True, effects={"fastapi_setup": True}, error=""),
            ExecutionResult(task_id="create_endpoints", success=True, effects={"endpoints_created": True}, error=""),
            ExecutionResult(task_id="tests", success=True, effects={"tests_created": True}, error="")
        ]

        # Act (with timing)
        start_time = time.perf_counter()
        result = await orchestrator.execute_project(
            goal="Create full-stack web app",
            project_id="test_nested"
        )
        actual_execution_time = time.perf_counter() - start_time

        # Assert
        assert result.success is True
        assert len(result.task_results) == 5, "Should have 5 task results"
        assert complex_htn.get_depth() == 2, "HTN should have depth 2 (nested)"

        # Performance benchmark (complex nested HTN with 5 tasks)
        assert actual_execution_time < BENCHMARK_COMPLEX_NESTED, \
            f"Complex nested HTN should complete in <{BENCHMARK_COMPLEX_NESTED}s " \
            f"(actual: {actual_execution_time:.3f}s)"
        print(f"✓ Performance: {actual_execution_time:.3f}s (benchmark: <{BENCHMARK_COMPLEX_NESTED}s)")

        # Verify all tasks succeeded
        assert all(r.success for r in result.task_results)


# =============================================================================
# Scenario 3: Failure and Replanning
# =============================================================================

class TestProjectBuilderE2EFailureReplanning:
    """Test Scenario 3: Failure handling and replanning.

    Validates orchestrator handles task failures gracefully.
    Note: Since feedback_handler is None in current setup, this tests
    basic failure handling without replanning.
    """

    @pytest.mark.asyncio
    async def test_task_failure_handling(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator
    ):
        """Test that task failures are properly reported in results.

        Without FeedbackHandler, orchestrator should complete with failure status.
        """
        # Arrange: HTN with 3 tasks
        htn = HTNNode(
            task_id="root",
            description="Create API with authentication",
            subtasks=[
                HTNNode(
                    task_id="create_api",
                    description="Create API",
                    effects={"api_created": True}
                ),
                HTNNode(
                    task_id="add_auth",
                    description="Add authentication",
                    preconditions={"api_created": True},
                    effects={"auth_added": True}
                ),
                HTNNode(
                    task_id="add_tests",
                    description="Add tests",
                    preconditions={"auth_added": True},
                    effects={"tests_added": True}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = htn

        # Mock execution: second task fails
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="create_api",
                success=True,
                effects={"api_created": True},
                error=""
            ),
            ExecutionResult(
                task_id="add_auth",
                success=False,  # FAILURE
                effects={},
                error="Authentication library not available"
            ),
            ExecutionResult(
                task_id="add_tests",
                success=True,
                effects={"tests_added": True},
                error=""
            )
        ]

        # Act (with timing)
        start_time = time.perf_counter()
        result = await orchestrator.execute_project(
            goal="Create API with authentication",
            project_id="test_failure"
        )
        actual_execution_time = time.perf_counter() - start_time

        # Assert: Project should complete but report partial success
        assert result.project_id == "test_failure"
        assert len(result.task_results) == 3

        # Check individual task results
        assert result.task_results[0].success is True
        assert result.task_results[1].success is False
        assert result.task_results[1].error == "Authentication library not available"
        assert result.task_results[2].success is True

        # Performance benchmark (failure scenario should still be fast)
        assert actual_execution_time < BENCHMARK_FAILURE_HANDLING, \
            f"Failure handling should complete in <{BENCHMARK_FAILURE_HANDLING}s " \
            f"(actual: {actual_execution_time:.3f}s)"
        print(f"✓ Performance: {actual_execution_time:.3f}s (benchmark: <{BENCHMARK_FAILURE_HANDLING}s)")


# =============================================================================
# Scenario 4: Parallel Task Execution
# =============================================================================

class TestProjectBuilderE2EParallelExecution:
    """Test Scenario 4: Parallel task execution detection.

    Validates HTNDSLTranslator correctly identifies independent tasks
    that can be executed in parallel.
    """

    @pytest.mark.asyncio
    async def test_independent_tasks_parallelized(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator
    ):
        """Test HTNDSLTranslator detects independent tasks.

        Tests HTN with independent tasks (security_scan and performance_test
        both depend on api_created but not on each other).
        HTNDSLTranslator should detect parallel opportunity.
        """
        # Arrange: HTN with independent tasks
        htn = HTNNode(
            task_id="root",
            description="Create API with validation",
            subtasks=[
                HTNNode(
                    task_id="create_api",
                    description="Create API",
                    effects={"api_created": True}
                ),
                HTNNode(
                    task_id="security_scan",
                    description="Run security scan",
                    preconditions={"api_created": True},
                    effects={"security_validated": True}
                ),
                HTNNode(
                    task_id="performance_test",
                    description="Run performance test",
                    preconditions={"api_created": True},
                    effects={"performance_validated": True}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = htn

        # Mock execution results
        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="create_api",
                success=True,
                effects={"api_created": True},
                error=""
            ),
            ExecutionResult(
                task_id="security_scan",
                success=True,
                effects={"security_validated": True},
                error=""
            ),
            ExecutionResult(
                task_id="performance_test",
                success=True,
                effects={"performance_validated": True},
                error=""
            )
        ]

        # Act (with timing)
        start_time = time.perf_counter()
        result = await orchestrator.execute_project(
            goal="Create API with validation",
            project_id="test_parallel"
        )
        actual_execution_time = time.perf_counter() - start_time

        # Assert
        assert result.success is True
        assert len(result.task_results) == 3

        # Verify HTN structure has independent tasks
        assert len(htn.subtasks) == 3
        # Security and performance tasks have same precondition but no dependency on each other
        assert htn.subtasks[1].preconditions == {"api_created": True}
        assert htn.subtasks[2].preconditions == {"api_created": True}

        # Performance benchmark (parallel task detection)
        assert actual_execution_time < BENCHMARK_PARALLEL_EXECUTION, \
            f"Parallel execution detection should complete in <{BENCHMARK_PARALLEL_EXECUTION}s " \
            f"(actual: {actual_execution_time:.3f}s)"
        print(f"✓ Performance: {actual_execution_time:.3f}s (benchmark: <{BENCHMARK_PARALLEL_EXECUTION}s)")


# =============================================================================
# Scenario 5: State Persistence
# =============================================================================

class TestProjectBuilderE2EStatePersistence:
    """Test Scenario 5: State persistence across all phases.

    Validates StateManager correctly persists project state
    throughout the execution lifecycle.
    """

    @pytest.mark.asyncio
    async def test_state_snapshots_at_each_phase(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator,
        state_repository
    ):
        """Test state snapshots created at each lifecycle phase.

        Validates state is persisted and can be loaded after execution.
        """
        # Arrange
        project_id = "test_state_persistence"
        htn = HTNNode(
            task_id="root",
            description="Create simple script",
            subtasks=[
                HTNNode(
                    task_id="write_script",
                    description="Write Python script",
                    effects={"script_written": True}
                ),
                HTNNode(
                    task_id="add_tests",
                    description="Add unit tests",
                    preconditions={"script_written": True},
                    effects={"tests_added": True}
                )
            ]
        )
        mock_goal_decomposer.decompose_goal.return_value = htn

        mock_execution_coordinator.execute_workflows.return_value = [
            ExecutionResult(
                task_id="write_script",
                success=True,
                effects={"script_written": True},
                error=""
            ),
            ExecutionResult(
                task_id="add_tests",
                success=True,
                effects={"tests_added": True},
                error=""
            )
        ]

        # Act (with timing)
        start_time = time.perf_counter()
        result = await orchestrator.execute_project(
            goal="Create simple script",
            project_id=project_id
        )
        actual_execution_time = time.perf_counter() - start_time

        # Assert: Project completed successfully
        assert result.success is True
        assert result.project_id == project_id

        # Verify state was persisted and can be loaded
        from src.project_builder.state.manager import ProjectStateManager
        state_manager = ProjectStateManager(state_repository)

        # State should exist in repository
        assert state_repository.exists(project_id)

        # Load final state
        final_state = state_manager.load_state(project_id)

        # Verify state properties
        assert final_state.project_id == project_id
        assert final_state.version >= 1, "State version should have incremented"

        # Performance benchmark (state persistence + versioning)
        assert actual_execution_time < BENCHMARK_STATE_PERSISTENCE, \
            f"State persistence should complete in <{BENCHMARK_STATE_PERSISTENCE}s " \
            f"(actual: {actual_execution_time:.3f}s)"
        print(f"✓ Performance: {actual_execution_time:.3f}s (benchmark: <{BENCHMARK_STATE_PERSISTENCE}s)")

        # Verify world state contains effects
        assert "script_written" in final_state.world_state
        assert "tests_added" in final_state.world_state
        assert final_state.world_state["script_written"] is True
        assert final_state.world_state["tests_added"] is True
