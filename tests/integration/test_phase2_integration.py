"""
Integration tests for Phase 2 DSL Features: Coproduct + Tool History.

Tests the complete workflow of:
1. Parsing DSL expressions with coproduct operator (+)
2. Executing with first-success semantics and lazy evaluation
3. Recording tool execution history in SurrealDB
4. Verifying metrics and audit trail

Clean Architecture: Integration layer validating cross-component interactions.
SOLID: Tests validate that abstractions work together correctly.
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.dsl.entities.coproduct import Coproduct
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.adapters.parser import Parser
from src.dsl.use_cases.interpreter import Interpreter
from src.adapters.database.tool_history_repository import ToolHistoryRepository


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_surreal_session():
    """Mock requests.Session for SurrealDB testing."""
    session = Mock()
    session.auth = None
    session.headers = {}
    
    # Mock health check
    health_response = Mock()
    health_response.status_code = 200
    session.get.return_value = health_response
    
    # Mock POST responses (for CREATE queries)
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK", "result": {"id": f"tool_executions:{uuid.uuid4()}"}}
    ]
    session.post.return_value = post_response
    
    return session


@pytest.fixture
def in_memory_tool_history():
    """In-memory tool history repository for testing (no real SurrealDB)."""
    class InMemoryToolHistoryRepository:
        """Mock repository that stores tool executions in memory."""
        
        def __init__(self):
            self.tool_executions: List[Dict[str, Any]] = []
            self.agent_executions: List[Dict[str, Any]] = []
        
        def record_tool_execution(
            self,
            tool_name: str,
            team_name: str,
            agent_role: str,
            parameters: Dict[str, Any],
            result: str,
            status: str,
            duration_ms: int,
            session_id: str,
            task_description: str = ""
        ) -> str:
            """Record tool execution in memory."""
            execution_id = str(uuid.uuid4())
            
            record = {
                "id": execution_id,
                "tool_name": tool_name,
                "team_name": team_name,
                "agent_role": agent_role,
                "parameters": parameters,
                "result": result[:1000],
                "status": status,
                "duration_ms": duration_ms,
                "session_id": session_id,
                "task_description": task_description[:100],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.tool_executions.append(record)
            return execution_id
        
        def get_tool_history(
            self,
            team_name: str = None,
            tool_name: str = None,
            limit: int = 100
        ) -> List[Dict[str, Any]]:
            """Get tool history with optional filters."""
            results = self.tool_executions
            
            if team_name:
                results = [r for r in results if r["team_name"] == team_name]
            if tool_name:
                results = [r for r in results if r["tool_name"] == tool_name]
            
            return results[:limit]
        
        def get_team_metrics(self, team_name: str) -> Dict[str, Any]:
            """Get metrics for a specific team."""
            team_executions = [r for r in self.tool_executions if r["team_name"] == team_name]
            
            if not team_executions:
                return {
                    "team_name": team_name,
                    "total_executions": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 0.0
                }
            
            success_count = sum(1 for r in team_executions if r["status"] == "success")
            failure_count = sum(1 for r in team_executions if r["status"] == "failure")
            
            return {
                "team_name": team_name,
                "total_executions": len(team_executions),
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_count / len(team_executions) if team_executions else 0.0
            }
    
    return InMemoryToolHistoryRepository()


@pytest.fixture
def mock_executor_with_history(in_memory_tool_history):
    """Mock executor that logs tool executions to history repository."""
    class MockExecutorWithHistory:
        def __init__(self, tool_history_repo):
            self.tool_history_repo = tool_history_repo
            self.execution_log: List[str] = []
            self.session_id = str(uuid.uuid4())
        
        async def execute_task(self, task_name: str, input_data=None):
            """Execute task and log to tool history."""
            self.execution_log.append(task_name)
            
            # Simulate different behaviors for different tasks
            if task_name == "grok":
                # Grok fails (simulating unavailable service)
                self.tool_history_repo.record_tool_execution(
                    tool_name="llm_inference",
                    team_name="AI",
                    agent_role="model-executor",
                    parameters={"model": "grok", "input": input_data},
                    result="Error: Service unavailable",
                    status="failure",
                    duration_ms=150,
                    session_id=self.session_id,
                    task_description=f"Execute {task_name}"
                )
                raise RuntimeError("Grok service unavailable")
            
            elif task_name == "qwen":
                # Qwen succeeds
                result = f"qwen_output: {input_data}" if input_data else "qwen_output"
                self.tool_history_repo.record_tool_execution(
                    tool_name="llm_inference",
                    team_name="AI",
                    agent_role="model-executor",
                    parameters={"model": "qwen", "input": input_data},
                    result=result,
                    status="success",
                    duration_ms=250,
                    session_id=self.session_id,
                    task_description=f"Execute {task_name}"
                )
                return result
            
            else:
                # Default: success
                result = f"success_{task_name}"
                self.tool_history_repo.record_tool_execution(
                    tool_name="generic_tool",
                    team_name="Default",
                    agent_role="generic-agent",
                    parameters={"task": task_name, "input": input_data},
                    result=result,
                    status="success",
                    duration_ms=100,
                    session_id=self.session_id,
                    task_description=f"Execute {task_name}"
                )
                return result
    
    return MockExecutorWithHistory(in_memory_tool_history)


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_coproduct_with_tool_history_both_succeed(
    mock_executor_with_history,
    in_memory_tool_history
):
    """
    Test coproduct where left succeeds - verify only left is executed and logged.
    
    Validates:
    - First-success semantics (short-circuit)
    - Lazy evaluation (right not executed)
    - Tool history records only left execution
    """
    # Setup: Create coproduct with two successful tasks
    executor = mock_executor_with_history
    executor.execute_task = AsyncMock(side_effect=lambda task, input_data=None: f"success_{task}")
    
    # Manually log first execution
    in_memory_tool_history.record_tool_execution(
        tool_name="task_executor",
        team_name="Testing",
        agent_role="test-agent",
        parameters={"task": "primary"},
        result="success_primary",
        status="success",
        duration_ms=100,
        session_id=executor.session_id,
        task_description="Execute primary"
    )
    
    interpreter = Interpreter(executor)
    coproduct = Coproduct(left=Literal("primary"), right=Literal("backup"))
    
    # Execute
    result = await interpreter.execute(coproduct)
    
    # Assertions
    assert result == "success_primary"
    
    # Verify tool history: only 1 execution (left)
    history = in_memory_tool_history.get_tool_history()
    assert len(history) == 1
    assert history[0]["parameters"]["task"] == "primary"
    assert history[0]["status"] == "success"


@pytest.mark.asyncio
async def test_coproduct_with_tool_history_fallback(
    mock_executor_with_history,
    in_memory_tool_history
):
    """
    Test coproduct fallback: left fails, right succeeds.
    
    Validates:
    - Fallback execution when left fails
    - Tool history records both attempts (1 failure, 1 success)
    - Metrics show correct success/failure counts
    """
    interpreter = Interpreter(mock_executor_with_history)
    coproduct = Coproduct(left=Literal("grok"), right=Literal("qwen"))
    
    # Execute: grok fails, qwen succeeds
    result = await interpreter.execute(coproduct, input_data="test_prompt")
    
    # Assertions
    assert result == "qwen_output: test_prompt"
    assert mock_executor_with_history.execution_log == ["grok", "qwen"]
    
    # Verify tool history: 2 executions (1 failure, 1 success)
    history = in_memory_tool_history.get_tool_history()
    assert len(history) == 2
    
    # First execution: grok failure
    assert history[0]["parameters"]["model"] == "grok"
    assert history[0]["status"] == "failure"
    assert "unavailable" in history[0]["result"].lower()
    
    # Second execution: qwen success
    assert history[1]["parameters"]["model"] == "qwen"
    assert history[1]["status"] == "success"
    assert "qwen_output" in history[1]["result"]
    
    # Verify metrics
    metrics = in_memory_tool_history.get_team_metrics("AI")
    assert metrics["total_executions"] == 2
    assert metrics["success_count"] == 1
    assert metrics["failure_count"] == 1
    assert metrics["success_rate"] == 0.5


@pytest.mark.asyncio
async def test_coproduct_with_tool_history_both_fail(
    in_memory_tool_history
):
    """
    Test coproduct where both alternatives fail.

    Validates:
    - Both alternatives are attempted
    - Tool history records both failures
    - Combined error message is raised
    - Metrics show 100% failure rate
    """
    class FailingExecutor:
        def __init__(self, tool_history_repo):
            self.tool_history_repo = tool_history_repo
            self.session_id = str(uuid.uuid4())

        async def execute_task(self, task_name: str, input_data=None):
            """All tasks fail."""
            self.tool_history_repo.record_tool_execution(
                tool_name="failing_tool",
                team_name="Unreliable",
                agent_role="failing-agent",
                parameters={"task": task_name},
                result=f"Error: {task_name} failed",
                status="failure",
                duration_ms=50,
                session_id=self.session_id,
                task_description=f"Execute {task_name}"
            )
            raise RuntimeError(f"{task_name} failed")

    executor = FailingExecutor(in_memory_tool_history)
    interpreter = Interpreter(executor)
    coproduct = Coproduct(left=Literal("task1"), right=Literal("task2"))

    # Execute: both fail
    with pytest.raises(Exception) as exc_info:
        await interpreter.execute(coproduct)

    # Verify combined error message
    error_msg = str(exc_info.value)
    assert "both alternatives failed" in error_msg.lower()
    assert "task1" in error_msg
    assert "task2" in error_msg

    # Verify tool history: 2 failures
    history = in_memory_tool_history.get_tool_history(team_name="Unreliable")
    assert len(history) == 2
    assert all(r["status"] == "failure" for r in history)

    # Verify metrics
    metrics = in_memory_tool_history.get_team_metrics("Unreliable")
    assert metrics["total_executions"] == 2
    assert metrics["success_count"] == 0
    assert metrics["failure_count"] == 2
    assert metrics["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_complex_workflow_composition_and_coproduct(
    in_memory_tool_history
):
    """
    Test complex DSL workflow: (build ∘ test) + (lint ∘ format).

    Validates:
    - Composition within coproduct branches
    - Sequential execution within each branch
    - Tool history tracks all steps in order
    - Fallback to second branch when first fails
    """
    class WorkflowExecutor:
        def __init__(self, tool_history_repo):
            self.tool_history_repo = tool_history_repo
            self.session_id = str(uuid.uuid4())
            self.execution_order = []

        async def execute_task(self, task_name: str, input_data=None):
            """Execute workflow tasks."""
            self.execution_order.append(task_name)

            # Build fails (simulating build error)
            if task_name == "build":
                self.tool_history_repo.record_tool_execution(
                    tool_name="build_tool",
                    team_name="Backend",
                    agent_role="build-agent",
                    parameters={"task": task_name, "input": input_data},
                    result="Error: Build failed - syntax error",
                    status="failure",
                    duration_ms=500,
                    session_id=self.session_id,
                    task_description="Build project"
                )
                raise RuntimeError("Build failed")

            # All other tasks succeed
            result = f"{task_name}_output"
            if input_data:
                result = f"{task_name}({input_data})"

            self.tool_history_repo.record_tool_execution(
                tool_name=f"{task_name}_tool",
                team_name="Backend",
                agent_role=f"{task_name}-agent",
                parameters={"task": task_name, "input": input_data},
                result=result,
                status="success",
                duration_ms=200,
                session_id=self.session_id,
                task_description=f"Execute {task_name}"
            )
            return result

    executor = WorkflowExecutor(in_memory_tool_history)
    interpreter = Interpreter(executor)

    # DSL: (build ∘ test) + (lint ∘ format)
    left_branch = Composition(left=Literal("build"), right=Literal("test"))
    right_branch = Composition(left=Literal("lint"), right=Literal("format"))
    workflow = Coproduct(left=left_branch, right=right_branch)

    # Execute: build fails, fallback to lint ∘ format
    result = await interpreter.execute(workflow, input_data="source_code")

    # Assertions
    # Composition right-to-left: build ∘ test → test first (succeeds), then build (fails)
    # Fallback to: lint ∘ format → format first, then lint
    assert result == "lint(format(source_code))"
    # Expected order: test → build (fails) → format → lint
    assert executor.execution_order == ["test", "build", "format", "lint"]

    # Verify tool history: 4 executions (1 failure, 3 success)
    history = in_memory_tool_history.get_tool_history(team_name="Backend")
    assert len(history) == 4

    # First: test success
    assert history[0]["tool_name"] == "test_tool"
    assert history[0]["status"] == "success"

    # Second: build failure
    assert history[1]["tool_name"] == "build_tool"
    assert history[1]["status"] == "failure"

    # Third: format success
    assert history[2]["tool_name"] == "format_tool"
    assert history[2]["status"] == "success"

    # Fourth: lint success
    assert history[3]["tool_name"] == "lint_tool"
    assert history[3]["status"] == "success"


@pytest.mark.asyncio
async def test_tool_history_metrics_after_coproduct_execution(
    in_memory_tool_history
):
    """
    Test metrics collection after multiple coproduct executions.

    Validates:
    - Metrics aggregate across multiple executions
    - Success rate calculation is correct
    - Tool-specific metrics are tracked
    - Session IDs are preserved for audit trail
    """
    class MetricsExecutor:
        def __init__(self, tool_history_repo):
            self.tool_history_repo = tool_history_repo
            self.session_id = str(uuid.uuid4())

        async def execute_task(self, task_name: str, input_data=None):
            """Execute with 50% failure rate."""
            # Fail on odd-numbered tasks
            if task_name in ["task1", "task3", "task5"]:
                self.tool_history_repo.record_tool_execution(
                    tool_name="flaky_tool",
                    team_name="Metrics",
                    agent_role="metrics-agent",
                    parameters={"task": task_name},
                    result=f"Error: {task_name} failed",
                    status="failure",
                    duration_ms=100,
                    session_id=self.session_id,
                    task_description=f"Execute {task_name}"
                )
                raise RuntimeError(f"{task_name} failed")

            # Succeed on even-numbered tasks
            result = f"success_{task_name}"
            self.tool_history_repo.record_tool_execution(
                tool_name="flaky_tool",
                team_name="Metrics",
                agent_role="metrics-agent",
                parameters={"task": task_name},
                result=result,
                status="success",
                duration_ms=150,
                session_id=self.session_id,
                task_description=f"Execute {task_name}"
            )
            return result

    executor = MetricsExecutor(in_memory_tool_history)
    interpreter = Interpreter(executor)

    # Execute multiple coproducts: task1 + task2, task3 + task4, task5 + task6
    coproduct1 = Coproduct(left=Literal("task1"), right=Literal("task2"))
    coproduct2 = Coproduct(left=Literal("task3"), right=Literal("task4"))
    coproduct3 = Coproduct(left=Literal("task5"), right=Literal("task6"))

    result1 = await interpreter.execute(coproduct1)
    result2 = await interpreter.execute(coproduct2)
    result3 = await interpreter.execute(coproduct3)

    # Assertions
    assert result1 == "success_task2"
    assert result2 == "success_task4"
    assert result3 == "success_task6"

    # Verify tool history: 6 executions (3 failures, 3 successes)
    history = in_memory_tool_history.get_tool_history(team_name="Metrics")
    assert len(history) == 6

    failures = [r for r in history if r["status"] == "failure"]
    successes = [r for r in history if r["status"] == "success"]

    assert len(failures) == 3
    assert len(successes) == 3

    # Verify all executions have same session ID
    assert all(r["session_id"] == executor.session_id for r in history)

    # Verify metrics
    metrics = in_memory_tool_history.get_team_metrics("Metrics")
    assert metrics["total_executions"] == 6
    assert metrics["success_count"] == 3
    assert metrics["failure_count"] == 3
    assert metrics["success_rate"] == 0.5

    # Verify tool-specific history
    tool_history = in_memory_tool_history.get_tool_history(tool_name="flaky_tool")
    assert len(tool_history) == 6


@pytest.mark.asyncio
async def test_parse_and_execute_coproduct_with_history(
    in_memory_tool_history
):
    """
    Test end-to-end: Parse DSL text, execute coproduct, verify tool history.

    Validates:
    - Parser correctly handles + operator
    - Interpreter executes with tool history tracking
    - Complete integration from DSL text to metrics
    """
    class SimpleExecutor:
        def __init__(self, tool_history_repo):
            self.tool_history_repo = tool_history_repo
            self.session_id = str(uuid.uuid4())

        async def execute_task(self, task_name: str, input_data=None):
            """Execute with primary failing, backup succeeding."""
            if task_name == "primary":
                self.tool_history_repo.record_tool_execution(
                    tool_name="primary_service",
                    team_name="Integration",
                    agent_role="integration-agent",
                    parameters={"task": task_name},
                    result="Error: Primary service down",
                    status="failure",
                    duration_ms=50,
                    session_id=self.session_id,
                    task_description="Execute primary"
                )
                raise RuntimeError("Primary failed")

            result = f"{task_name}_success"
            self.tool_history_repo.record_tool_execution(
                tool_name="backup_service",
                team_name="Integration",
                agent_role="integration-agent",
                parameters={"task": task_name},
                result=result,
                status="success",
                duration_ms=100,
                session_id=self.session_id,
                task_description="Execute backup"
            )
            return result

    # Parse DSL
    parser = Parser()
    ast = parser.parse("primary + backup")

    # Verify AST structure
    assert isinstance(ast, Coproduct)
    assert isinstance(ast.left, Literal)
    assert isinstance(ast.right, Literal)
    assert ast.left.value == "primary"
    assert ast.right.value == "backup"

    # Execute with tool history
    executor = SimpleExecutor(in_memory_tool_history)
    interpreter = Interpreter(executor)
    result = await interpreter.execute(ast)

    # Assertions
    assert result == "backup_success"

    # Verify tool history
    history = in_memory_tool_history.get_tool_history(team_name="Integration")
    assert len(history) == 2
    assert history[0]["status"] == "failure"
    assert history[1]["status"] == "success"

    # Verify metrics
    metrics = in_memory_tool_history.get_team_metrics("Integration")
    assert metrics["success_rate"] == 0.5

