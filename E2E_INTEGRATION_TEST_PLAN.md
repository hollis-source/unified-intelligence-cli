# End-to-End Integration Test Plan: Project Builder

**Version:** 1.0
**Date:** 2025-10-12
**Status:** Draft → Implementation Ready

---

## Executive Summary

End-to-end integration test that validates the complete Project Builder pipeline from natural language goal to generated project output. Uses hybrid mocking strategy (mock LLMs, real internal components) for fast, reliable testing.

**Test File:** `tests/integration/test_project_builder_e2e.py`
**Execution Time:** < 5 seconds
**Coverage:** Complete pipeline (8 components)

---

## Pipeline Under Test

```
┌─────────────────────────────────────────────────────────────────┐
│                    Project Builder Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Natural Language Goal                                        │
│     "Create Python CLI with tests"                              │
│          ↓                                                       │
│  2. ProjectOrchestrator (lifecycle coordinator)                 │
│     • PLAN → VERIFY → DECOMPOSE → EXECUTE → COMPLETE           │
│          ↓                                                       │
│  3. GoalDecomposer (NL → HTN) [MOCKED]                         │
│     • Uses Qwen3-Next-80B (mocked for speed)                   │
│          ↓                                                       │
│  4. HTNDSLTranslator (HTN → DSL) [REAL]                        │
│     • Graph theory → Category theory functor                    │
│     • Automatic parallelization detection                       │
│          ↓                                                       │
│  5. DSL Interpreter (DSL → execution) [REAL]                   │
│     • Evaluates category theory operators (∘, ×, +, Δ)         │
│          ↓                                                       │
│  6. ExecutionCoordinator (task → agents) [MOCKED]              │
│     • Routes tasks to agent teams (mocked responses)            │
│          ↓                                                       │
│  7. FeedbackLoopHandler (failures → replan) [REAL]             │
│     • Intelligent replanning on failures                        │
│          ↓                                                       │
│  8. StateManager (persistence) [REAL - SQLite]                 │
│     • Immutable state snapshots at each phase                   │
│          ↓                                                       │
│  9. Generated Project Output                                    │
│     • Files, artifacts, metadata                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Test Strategy: Hybrid Mocking

### Mock External Dependencies
- **GoalDecomposer (LLM calls)**: Mock with predefined HTN JSON
- **ExecutionCoordinator (agent execution)**: Mock with success/failure responses
- **Reason**: Fast execution (5s vs 30s+), no API costs, deterministic

### Use Real Internal Components
- **HTNDSLTranslator**: Already 98.84% tested, critical functor
- **DSL Interpreter**: Core execution engine
- **FeedbackLoopHandler**: Critical replanning logic
- **StateManager**: Validates persistence (SQLite for isolation)
- **Reason**: Validates real integration points, tests production code paths

---

## Test Scenarios

### Scenario 1: Happy Path (Simple Project)
**Goal:** "Create Python hello world CLI"

**Test Steps:**
1. Initialize ProjectOrchestrator with mocked dependencies
2. Mock GoalDecomposer to return simple HTN:
   ```json
   {
     "task_id": "root",
     "description": "Create Python hello world CLI",
     "subtasks": [
       {
         "task_id": "create_main",
         "description": "Create main.py file",
         "preconditions": {},
         "effects": {"main_py_created": true}
       },
       {
         "task_id": "create_cli",
         "description": "Create CLI entry point",
         "preconditions": {"main_py_created": true},
         "effects": {"cli_created": true}
       }
     ]
   }
   ```
3. Mock ExecutionCoordinator to return success for all tasks
4. Execute: `orchestrator.execute_project("create_python_cli", goal)`
5. **Assert:**
   - ✅ Lifecycle state: `COMPLETE`
   - ✅ All phases completed: PLAN, VERIFY, DECOMPOSE, EXECUTE
   - ✅ HTN structure correct (2 sequential subtasks)
   - ✅ DSL workflow: Composition (create_cli ∘ create_main)
   - ✅ State persisted at each phase
   - ✅ No errors or exceptions

**Expected Execution Time:** < 1 second

---

### Scenario 2: Complex Nested Hierarchy
**Goal:** "Create web app with React frontend, FastAPI backend, and pytest tests"

**Test Steps:**
1. Mock GoalDecomposer to return nested HTN:
   ```json
   {
     "task_id": "root",
     "description": "Create full-stack web app",
     "subtasks": [
       {
         "task_id": "frontend",
         "description": "Build React frontend",
         "subtasks": [
           {"task_id": "setup_react", "description": "Setup React app"},
           {"task_id": "create_components", "description": "Create components"}
         ]
       },
       {
         "task_id": "backend",
         "description": "Build FastAPI backend",
         "subtasks": [
           {"task_id": "setup_fastapi", "description": "Setup FastAPI"},
           {"task_id": "create_endpoints", "description": "Create API endpoints"}
         ]
       },
       {
         "task_id": "tests",
         "description": "Create pytest tests",
         "preconditions": {"backend_created": true, "frontend_created": true}
       }
     ]
   }
   ```
2. **Assert:**
   - ✅ HTN depth: 2 levels (compound → primitive)
   - ✅ Parallel detection: frontend × backend (independent tasks)
   - ✅ DSL workflow: `tests ∘ (frontend × backend)`
   - ✅ Execution order: frontend & backend parallel, then tests sequentially

**Expected Execution Time:** < 2 seconds

---

### Scenario 3: Failure and Replanning
**Goal:** "Create API with authentication"

**Test Steps:**
1. Mock GoalDecomposer to return HTN with 3 tasks
2. Mock ExecutionCoordinator to **fail** on task 2 (simulate LLM timeout)
3. FeedbackLoopHandler should:
   - Classify failure: `TIMEOUT`
   - Generate replan strategy: `RETRY_WITH_SIMPLER_PROMPT`
   - Update task description
4. Mock ExecutionCoordinator to **succeed** on retry
5. **Assert:**
   - ✅ First attempt: task 2 fails with TIMEOUT
   - ✅ FeedbackHandler invoked
   - ✅ Replanning strategy applied
   - ✅ Retry succeeds
   - ✅ Final state: COMPLETE (despite initial failure)
   - ✅ Failure history recorded in state

**Expected Execution Time:** < 2 seconds

---

### Scenario 4: Parallel Task Execution
**Goal:** "Create API with security scan and performance test"

**Test Steps:**
1. Mock GoalDecomposer to return HTN with independent tasks:
   ```json
   {
     "task_id": "root",
     "subtasks": [
       {
         "task_id": "create_api",
         "effects": {"api_created": true}
       },
       {
         "task_id": "security_scan",
         "preconditions": {"api_created": true},
         "effects": {"security_validated": true}
       },
       {
         "task_id": "performance_test",
         "preconditions": {"api_created": true},
         "effects": {"performance_validated": true}
       }
     ]
   }
   ```
2. HTNDSLTranslator should detect:
   - `security_scan` and `performance_test` are independent (both require `api_created`, no dependencies between them)
3. **Assert:**
   - ✅ HTNDSLTranslator detects parallelization opportunity
   - ✅ DSL workflow: `(security_scan × performance_test) ∘ create_api`
   - ✅ Execution metadata: `{"operator": "×", "execution": "parallel"}`

**Expected Execution Time:** < 1 second

---

### Scenario 5: State Persistence Across Phases
**Goal:** "Create simple Python script"

**Test Steps:**
1. Execute complete pipeline
2. **Query StateManager** at each phase:
   - After PLAN: State contains goal
   - After VERIFY: State contains validated goal
   - After DECOMPOSE: State contains HTN + DSL workflow
   - After EXECUTE: State contains execution results
3. **Assert:**
   - ✅ State version increments at each phase
   - ✅ State snapshots immutable (no mutation)
   - ✅ World state tracks preconditions/effects
   - ✅ Task status tracked: PENDING → IN_PROGRESS → COMPLETED
   - ✅ SQLite database persists state correctly

**Expected Execution Time:** < 2 seconds

---

## Test Implementation Structure

### File: `tests/integration/test_project_builder_e2e.py`

```python
"""End-to-end integration tests for Project Builder.

Tests complete pipeline from natural language goal to project generation
using hybrid mocking strategy (mock LLMs, real internal components).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.project_builder.orchestrator import ProjectOrchestrator
from src.project_builder.state.factory import create_state_repository
from src.entities.htn.htn_node import HTNNode
from src.entities.lifecycle import LifecycleState
from src.interfaces import TaskStatus


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary SQLite database for test isolation."""
    db_path = tmp_path / "test_state.db"
    return str(db_path)


@pytest.fixture
def mock_goal_decomposer():
    """Mock GoalDecomposer to avoid LLM API calls."""
    decomposer = Mock()
    decomposer.decompose = AsyncMock()
    return decomposer


@pytest.fixture
def mock_execution_coordinator():
    """Mock ExecutionCoordinator to avoid agent LLM calls."""
    coordinator = Mock()
    coordinator.execute_tasks = AsyncMock()
    return coordinator


@pytest.fixture
def orchestrator(temp_db, mock_goal_decomposer, mock_execution_coordinator):
    """Create ProjectOrchestrator with mocked dependencies."""
    state_repo = create_state_repository(db_type="sqlite", state_db_path=temp_db)

    return ProjectOrchestrator(
        goal_decomposer=mock_goal_decomposer,
        execution_coordinator=mock_execution_coordinator,
        state_repository=state_repo,
        enable_feedback=True  # Test feedback loop
    )


class TestProjectBuilderE2EHappyPath:
    """Test Scenario 1: Happy path with simple project."""

    @pytest.mark.asyncio
    async def test_simple_project_generation_success(
        self,
        orchestrator,
        mock_goal_decomposer,
        mock_execution_coordinator
    ):
        """Test complete pipeline: simple goal → HTN → DSL → execution → success."""
        # Arrange: Mock GoalDecomposer
        simple_htn = HTNNode(
            task_id="root",
            description="Create Python hello world CLI",
            subtasks=[
                HTNNode(
                    task_id="create_main",
                    description="Create main.py",
                    preconditions={},
                    effects={"main_py_created": True}
                ),
                HTNNode(
                    task_id="create_cli",
                    description="Create CLI entry point",
                    preconditions={"main_py_created": True},
                    effects={"cli_created": True}
                )
            ]
        )
        mock_goal_decomposer.decompose.return_value = simple_htn

        # Mock ExecutionCoordinator to return success
        mock_execution_coordinator.execute_tasks.return_value = [
            {"task_id": "create_main", "status": "success", "output": "main.py created"},
            {"task_id": "create_cli", "status": "success", "output": "CLI created"}
        ]

        # Act: Execute complete pipeline
        result = await orchestrator.execute_project(
            project_id="test_simple_project",
            goal="Create Python hello world CLI"
        )

        # Assert: Pipeline completed successfully
        assert result.success is True
        assert result.lifecycle.current_state == LifecycleState.COMPLETE
        assert "PLAN" in result.phases_completed
        assert "VERIFY" in result.phases_completed
        assert "DECOMPOSE" in result.phases_completed
        assert "EXECUTE" in result.phases_completed

        # Assert: HTN structure correct
        decomposed_state = result.lifecycle.get_state_data(LifecycleState.DECOMPOSE)
        assert decomposed_state["htn_root"].task_id == "root"
        assert len(decomposed_state["htn_decomposed"]) == 2

        # Assert: DSL workflow correct (sequential composition)
        dsl_workflow = decomposed_state["dsl_workflow"]
        assert dsl_workflow.__class__.__name__ == "Composition"

        # Assert: State persisted
        final_state = orchestrator.state_manager.get_current_state()
        assert final_state.task_status["create_main"] == TaskStatus.COMPLETED
        assert final_state.task_status["create_cli"] == TaskStatus.COMPLETED


class TestProjectBuilderE2EComplexNested:
    """Test Scenario 2: Complex nested hierarchy with parallelization."""

    # Implementation...


class TestProjectBuilderE2EFailureReplanning:
    """Test Scenario 3: Failure handling and replanning."""

    # Implementation...


class TestProjectBuilderE2EParallelExecution:
    """Test Scenario 4: Parallel task execution detection."""

    # Implementation...


class TestProjectBuilderE2EStatePersistence:
    """Test Scenario 5: State persistence across all phases."""

    # Implementation...
```

---

## Mock Data Templates

### Simple HTN (2 sequential tasks)
```python
HTNNode(
    task_id="root",
    description="Create Python CLI",
    subtasks=[
        HTNNode(task_id="task1", description="...", effects={"step1": True}),
        HTNNode(task_id="task2", description="...", preconditions={"step1": True})
    ]
)
```

### Complex HTN (nested with parallelization)
```python
HTNNode(
    task_id="root",
    subtasks=[
        HTNNode(  # Compound task
            task_id="frontend",
            subtasks=[
                HTNNode(task_id="setup", ...),
                HTNNode(task_id="components", ...)
            ]
        ),
        HTNNode(  # Compound task (parallel)
            task_id="backend",
            subtasks=[...]
        )
    ]
)
```

### Execution Coordinator Success Response
```python
[
    {
        "task_id": "task1",
        "status": "success",
        "output": "Task completed successfully",
        "duration_ms": 1234,
        "agent": "backend-team"
    }
]
```

### Execution Coordinator Failure Response
```python
[
    {
        "task_id": "task2",
        "status": "failure",
        "error": "Timeout: LLM did not respond within 30s",
        "error_type": "TIMEOUT",
        "duration_ms": 30000
    }
]
```

---

## Assertions Checklist

### For Every Test
- [ ] Lifecycle state progression correct
- [ ] No unhandled exceptions
- [ ] Execution time < 5 seconds
- [ ] State persisted to SQLite

### Happy Path Specific
- [ ] All phases completed (PLAN → COMPLETE)
- [ ] HTN structure matches expected
- [ ] DSL workflow correct (Composition/Product)
- [ ] All tasks status = COMPLETED

### Failure & Replanning Specific
- [ ] FeedbackHandler invoked on failure
- [ ] Failure classified correctly
- [ ] Replanning strategy applied
- [ ] Retry succeeds
- [ ] Failure history recorded

### Parallelization Specific
- [ ] Independent tasks detected
- [ ] DSL uses Product operator (×)
- [ ] Execution metadata correct

### State Persistence Specific
- [ ] State snapshots at each phase
- [ ] State version increments
- [ ] World state tracks preconditions/effects
- [ ] Task status transitions correct

---

## Running the Tests

### Fast Mode (Mocked)
```bash
# Default: Uses mocked LLMs and agents (< 5 seconds)
source venv/bin/activate
pytest tests/integration/test_project_builder_e2e.py -v
```

### Slow Mode (Real LLMs - Optional)
```bash
# Set environment variable to use real LLMs (30+ seconds)
export PB_E2E_USE_REAL_LLMS=true
pytest tests/integration/test_project_builder_e2e.py -v --slow
```

### Coverage Report
```bash
pytest tests/integration/test_project_builder_e2e.py \
  --cov=src.project_builder \
  --cov-report=html
```

---

## Success Criteria

### Test Suite
- [ ] All 5 scenarios implemented
- [ ] All tests passing (5/5)
- [ ] Execution time < 10 seconds total
- [ ] No flaky tests (deterministic mocking)

### Coverage
- [ ] ProjectOrchestrator: >90%
- [ ] Lifecycle transitions: 100%
- [ ] Integration points: >85%

### Quality
- [ ] Tests are independent (no shared state)
- [ ] Mocks are realistic (match production behavior)
- [ ] Assertions are comprehensive (not just "no errors")
- [ ] Test names are descriptive

---

## Next Steps

1. **Wait for orchestration tests** (todo #10) to complete
2. **Implement E2E test file** following this plan
3. **Run and validate** all 5 scenarios
4. **Document results** in test report
5. **Update Phase 1 documentation** with E2E validation

---

## Appendix: Why Hybrid Mocking?

### Alternative 1: All Real (Rejected)
- **Pro**: True end-to-end validation
- **Con**: Slow (30+ seconds), expensive (API costs), flaky (network issues)
- **Verdict**: Reserve for CI/CD system tests

### Alternative 2: All Mocked (Rejected)
- **Pro**: Fastest (< 1 second)
- **Con**: Doesn't validate real integration points
- **Verdict**: Too disconnected from production behavior

### Alternative 3: Hybrid (SELECTED) ✅
- **Pro**: Fast (< 5 seconds), reliable, validates internal integration
- **Con**: Doesn't test LLM integration (acceptable trade-off)
- **Verdict**: Optimal balance for developer workflow

---

**End of Plan**
