# Timeout Handling - Recommended Fixes

This document provides specific code examples for implementing the recommendations from `TIMEOUT_HANDLING_REVIEW.md`.

---

## Fix 1: Add Cancellation Handling in llm_executor.py

**Priority**: High  
**Estimated Effort**: 2 hours  
**Impact**: Prevents resource leaks on timeout

### Current Code (llm_executor.py:72-150)
```python
async def execute(
    self,
    agent: Agent,
    task: Task,
    context: Optional[ExecutionContext] = None
) -> ExecutionResult:
    start_time = time.time()
    
    # ... existing logic ...
    
    response = self.llm_provider.generate(
        messages=messages,
        config=self.default_config
    )
    
    # If cancelled here, cache.set() may not execute
    if self.cache:
        self.cache.set(messages=messages, response=response, ...)
```

### Recommended Fix
```python
async def execute(
    self,
    agent: Agent,
    task: Task,
    context: Optional[ExecutionContext] = None
) -> ExecutionResult:
    start_time = time.time()
    
    try:
        # ... existing logic ...
        
        response = self.llm_provider.generate(
            messages=messages,
            config=self.default_config
        )
        
        # Store in cache for future requests
        if self.cache:
            task_desc = self._extract_task_description(task)
            self.cache.set(
                messages=messages,
                response=response,
                task_description=task_desc,
                model_name=self.provider_name
            )
        
        # ... rest of existing logic ...
        
    except asyncio.CancelledError:
        # Task was cancelled (likely due to timeout)
        logger.info(
            f"Task execution cancelled (likely timeout): {task.description[:100]}",
            extra={
                "task_description": task.description,
                "agent_role": agent.role,
                "elapsed_ms": int((time.time() - start_time) * 1000)
            }
        )
        
        # Cleanup: Ensure cache is in consistent state
        # (Don't write partial results to cache)
        
        # Re-raise to propagate cancellation up the stack
        raise
```

**Benefits**:
- Prevents partial cache writes
- Logs cancellation events for debugging
- Allows proper cleanup of resources
- Maintains asyncio cancellation semantics

---

## Fix 2: Add Comprehensive Unit Tests

**Priority**: High  
**Estimated Effort**: 4 hours  
**Impact**: Ensures correctness and prevents regressions

### Test File: `tests/project_builder/execution/test_coordinator_timeout.py`

```python
"""Unit tests for ExecutionCoordinator timeout handling."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.project_builder.execution.coordinator import ExecutionCoordinator
from src.entities import Task, Agent
from src.entities.htn.htn_node import HTNNode
from src.interfaces import ProjectState, TaskStatus


class TestResolveTaskType:
    """Test _resolve_task_type() method."""
    
    def test_resolve_from_task_type_attribute(self):
        """Test resolution from task.task_type."""
        coordinator = create_test_coordinator()
        task = Task(description="Test", task_type="validation")
        agent = Agent(role="generic")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "validation"
    
    def test_resolve_from_agent_role_testing(self):
        """Test resolution from agent role containing 'test'."""
        coordinator = create_test_coordinator()
        task = Task(description="Test")  # No task_type
        agent = Agent(role="test-engineer")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "testing"
    
    def test_resolve_from_agent_role_validation(self):
        """Test resolution from agent role containing 'validat'."""
        coordinator = create_test_coordinator()
        task = Task(description="Test")
        agent = Agent(role="validation-specialist")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "validation"
    
    def test_resolve_from_agent_role_documentation(self):
        """Test resolution from agent role containing 'doc'."""
        coordinator = create_test_coordinator()
        task = Task(description="Test")
        agent = Agent(role="technical-writer")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "documentation"
    
    def test_resolve_from_metadata_domain(self):
        """Test resolution from task.metadata['domain']."""
        coordinator = create_test_coordinator()
        task = Task(description="Test", metadata={"domain": "testing"})
        agent = Agent(role="generic")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "testing"
    
    def test_resolve_defaults_to_implementation(self):
        """Test default resolution to 'implementation'."""
        coordinator = create_test_coordinator()
        task = Task(description="Test")
        agent = Agent(role="generic")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "implementation"
    
    def test_resolve_normalizes_coding_to_implementation(self):
        """Test 'coding' task type normalized to 'implementation'."""
        coordinator = create_test_coordinator()
        task = Task(description="Test", task_type="coding")
        agent = Agent(role="generic")
        
        task_type = coordinator._resolve_task_type(task, agent)
        
        assert task_type == "implementation"


class TestBuildTimeoutResult:
    """Test _build_timeout_result() method."""
    
    def test_validation_task_returns_partial_success(self):
        """Test validation task timeout returns partial success."""
        coordinator = create_test_coordinator()
        task = Task(description="Validate code", metadata={"task_id": "validate_1"})
        agent = Agent(role="validator")
        htn_node = HTNNode(
            task_id="validate_1",
            description="Validate code",
            effects={"artifact_validation": "validation_report.txt"}
        )
        
        result = coordinator._build_timeout_result(
            task=task,
            agent=agent,
            model_id="test-model",
            htn_node=htn_node,
            task_type="validation",
            timeout_seconds=300
        )
        
        assert result.success == True  # Graceful degradation
        assert result.metadata["partial"] == True
        assert result.metadata["timeout"] == True
        assert result.metadata["timeout_seconds"] == 300
        assert result.effects[htn_node.task_id] == "partial"
        assert "validation_status" in result.effects
        assert result.effects["validation_status"] == "timeout"
    
    def test_testing_task_returns_partial_success(self):
        """Test testing task timeout returns partial success."""
        coordinator = create_test_coordinator()
        task = Task(description="Run tests", metadata={"task_id": "test_1"})
        agent = Agent(role="tester")
        htn_node = HTNNode(task_id="test_1", description="Run tests", effects={})
        
        result = coordinator._build_timeout_result(
            task=task,
            agent=agent,
            model_id="test-model",
            htn_node=htn_node,
            task_type="testing",
            timeout_seconds=300
        )
        
        assert result.success == True
        assert result.metadata["partial"] == True
    
    def test_documentation_task_returns_partial_success(self):
        """Test documentation task timeout returns partial success."""
        coordinator = create_test_coordinator()
        task = Task(description="Write docs", metadata={"task_id": "doc_1"})
        agent = Agent(role="writer")
        htn_node = HTNNode(task_id="doc_1", description="Write docs", effects={})
        
        result = coordinator._build_timeout_result(
            task=task,
            agent=agent,
            model_id="test-model",
            htn_node=htn_node,
            task_type="documentation",
            timeout_seconds=180
        )
        
        assert result.success == True
        assert result.metadata["partial"] == True
    
    def test_implementation_task_returns_hard_failure(self):
        """Test implementation task timeout returns hard failure."""
        coordinator = create_test_coordinator()
        task = Task(description="Write code", metadata={"task_id": "impl_1"})
        agent = Agent(role="coder")
        htn_node = HTNNode(task_id="impl_1", description="Write code", effects={})
        
        result = coordinator._build_timeout_result(
            task=task,
            agent=agent,
            model_id="test-model",
            htn_node=htn_node,
            task_type="implementation",
            timeout_seconds=120
        )
        
        assert result.success == False  # Hard failure
        assert result.metadata["timeout"] == True
        assert result.effects == {}  # No effects on failure
        assert "timed out after 120 seconds" in result.error


@pytest.mark.asyncio
class TestExecuteTaskTimeout:
    """Test _execute_task() timeout scenarios."""
    
    async def test_validation_task_timeout_graceful_degradation(self):
        """Test validation task timeout triggers graceful degradation."""
        coordinator = create_test_coordinator()
        
        # Mock llm_executor to simulate timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than test timeout
            return MagicMock()
        
        coordinator.llm_executor = MagicMock()
        coordinator.llm_executor.execute = slow_execute
        
        task = Task(description="Validate code", task_type="validation", metadata={"task_id": "val_1"})
        agent = Agent(role="validator")
        htn_node = HTNNode(task_id="val_1", description="Validate", preconditions={}, effects={})
        state = create_test_state()
        
        # Override timeout to 1 second for fast test
        with patch.object(coordinator, 'TASK_TIMEOUTS', {"validation": 1, "default": 1}):
            result = await coordinator._execute_task(task, agent, "test-model", htn_node, state)
        
        assert result.success == True  # Graceful degradation
        assert result.metadata["partial"] == True
        assert result.metadata["timeout"] == True
    
    async def test_implementation_task_timeout_hard_failure(self):
        """Test implementation task timeout triggers hard failure."""
        coordinator = create_test_coordinator()
        
        # Mock llm_executor to simulate timeout
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock()
        
        coordinator.llm_executor = MagicMock()
        coordinator.llm_executor.execute = slow_execute
        
        task = Task(description="Write code", task_type="implementation", metadata={"task_id": "impl_1"})
        agent = Agent(role="coder")
        htn_node = HTNNode(task_id="impl_1", description="Write code", preconditions={}, effects={})
        state = create_test_state()
        
        with patch.object(coordinator, 'TASK_TIMEOUTS', {"implementation": 1, "default": 1}):
            result = await coordinator._execute_task(task, agent, "test-model", htn_node, state)
        
        assert result.success == False  # Hard failure
        assert result.metadata["timeout"] == True


# Helper functions
def create_test_coordinator():
    """Create ExecutionCoordinator for testing."""
    team_router = MagicMock()
    model_selector = MagicMock()
    teams = []
    return ExecutionCoordinator(team_router, model_selector, teams)


def create_test_state():
    """Create ProjectState for testing."""
    return ProjectState(
        project_id="test-project",
        htn_graph=HTNNode(task_id="root", description="Root", preconditions={}, effects={}),
        world_state={},
        task_status={}
    )
```

---

## Fix 3: Document Partial Success Semantics

**Priority**: High  
**Estimated Effort**: 2 hours  
**Impact**: Clarifies behavior for maintainers

### Add to `src/project_builder/execution/coordinator.py` docstring

```python
class ExecutionCoordinator(IExecutionCoordinator):
    """Coordinator for task execution with agent routing and model selection.
    
    ... existing docstring ...
    
    Timeout Handling and Graceful Degradation:
    ------------------------------------------
    Tasks are executed with type-specific timeouts (see TASK_TIMEOUTS).
    When a timeout occurs, the coordinator applies graceful degradation:
    
    1. **Validation/Testing/Documentation Tasks** (Non-Critical):
       - Marked as partial success (success=True, metadata["partial"]=True)
       - Effects include task_id='partial' for precondition checking
       - Pipeline continues to subsequent tasks
       - Rationale: These tasks enhance quality but aren't blocking
    
    2. **Implementation Tasks** (Critical):
       - Marked as hard failure (success=False)
       - No effects applied
       - Pipeline stops (subsequent tasks with preconditions fail)
       - Rationale: Core functionality must complete successfully
    
    Partial Success Semantics:
    --------------------------
    When a task completes with partial success:
    - world_state[task_id] = 'partial' (vs. 'completed' for full success)
    - Dependent tasks can check preconditions:
      * If precondition requires 'completed', it will fail
      * If precondition checks task_id existence, it will pass
    - Parent task effects are NOT applied until all subtasks fully complete
    - Task status remains IN_PROGRESS (not COMPLETED)
    
    Example:
        Task A (validation) times out → partial success
        Task B depends on Task A → precondition check:
          - If B requires A.status == 'completed': FAILS
          - If B requires A.task_id in world_state: PASSES
    """
```

---

## Fix 4: Add Metrics Collection

**Priority**: Medium  
**Estimated Effort**: 3 hours  
**Impact**: Enables performance monitoring and optimization

### Add to `coordinator.py`

```python
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List

@dataclass
class TimeoutMetrics:
    """Metrics for timeout monitoring and analysis."""
    timeouts_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    execution_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    partial_successes: int = 0
    hard_failures: int = 0
    total_tasks: int = 0
    
    def record_timeout(self, task_type: str, is_partial: bool):
        """Record a timeout event."""
        self.timeouts_by_type[task_type] += 1
        if is_partial:
            self.partial_successes += 1
        else:
            self.hard_failures += 1
    
    def record_execution(self, task_type: str, duration_seconds: float):
        """Record successful execution time."""
        self.execution_times[task_type].append(duration_seconds)
        self.total_tasks += 1
    
    def get_timeout_rate(self, task_type: str) -> float:
        """Get timeout rate for task type."""
        timeouts = self.timeouts_by_type.get(task_type, 0)
        executions = len(self.execution_times.get(task_type, []))
        total = timeouts + executions
        return timeouts / total if total > 0 else 0.0
    
    def get_avg_execution_time(self, task_type: str) -> float:
        """Get average execution time for task type."""
        times = self.execution_times.get(task_type, [])
        return sum(times) / len(times) if times else 0.0
    
    def summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_tasks": self.total_tasks,
            "total_timeouts": sum(self.timeouts_by_type.values()),
            "partial_successes": self.partial_successes,
            "hard_failures": self.hard_failures,
            "timeout_rates": {
                task_type: self.get_timeout_rate(task_type)
                for task_type in self.timeouts_by_type.keys()
            },
            "avg_execution_times": {
                task_type: self.get_avg_execution_time(task_type)
                for task_type in self.execution_times.keys()
            }
        }


class ExecutionCoordinator(IExecutionCoordinator):
    def __init__(self, ...):
        # ... existing init ...
        self.timeout_metrics = TimeoutMetrics()
    
    async def _execute_task(self, ...):
        # ... existing code ...
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.llm_executor.execute(agent, task, context),
                timeout=timeout
            )
            
            # Record successful execution
            execution_time = time.time() - start_time
            self.timeout_metrics.record_execution(task_type, execution_time)
            
            # ... rest of existing code ...
            
        except asyncio.TimeoutError:
            # Record timeout
            is_partial = task_type in ['validation', 'testing', 'documentation']
            self.timeout_metrics.record_timeout(task_type, is_partial)
            
            return self._build_timeout_result(...)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get timeout metrics summary for monitoring."""
        return self.timeout_metrics.summary()
```

---

## Fix 5: Make Timeouts Configurable

**Priority**: Medium  
**Estimated Effort**: 2 hours  
**Impact**: Enables environment-specific tuning

### Add configuration support

```python
import os

class ExecutionCoordinator(IExecutionCoordinator):
    # Default timeouts (can be overridden by environment variables)
    DEFAULT_TASK_TIMEOUTS = {
        "validation": 300,
        "testing": 300,
        "documentation": 180,
        "implementation": 120,
        "default": 120
    }
    
    def __init__(self, ...):
        # ... existing init ...
        
        # Load timeouts from environment or use defaults
        self.TASK_TIMEOUTS = self._load_timeout_config()
    
    def _load_timeout_config(self) -> Dict[str, int]:
        """Load timeout configuration from environment variables.
        
        Environment variables:
            PB_TIMEOUT_VALIDATION: Timeout for validation tasks (seconds)
            PB_TIMEOUT_TESTING: Timeout for testing tasks (seconds)
            PB_TIMEOUT_DOCUMENTATION: Timeout for documentation tasks (seconds)
            PB_TIMEOUT_IMPLEMENTATION: Timeout for implementation tasks (seconds)
            PB_TIMEOUT_DEFAULT: Default timeout (seconds)
        
        Returns:
            Dictionary of task type to timeout (seconds)
        """
        timeouts = dict(self.DEFAULT_TASK_TIMEOUTS)
        
        # Override with environment variables if present
        env_mappings = {
            "validation": "PB_TIMEOUT_VALIDATION",
            "testing": "PB_TIMEOUT_TESTING",
            "documentation": "PB_TIMEOUT_DOCUMENTATION",
            "implementation": "PB_TIMEOUT_IMPLEMENTATION",
            "default": "PB_TIMEOUT_DEFAULT"
        }
        
        for task_type, env_var in env_mappings.items():
            if env_var in os.environ:
                try:
                    timeout = int(os.environ[env_var])
                    if timeout > 0:
                        timeouts[task_type] = timeout
                        logger.info(f"Loaded timeout for {task_type}: {timeout}s from {env_var}")
                    else:
                        logger.warning(f"Invalid timeout value for {env_var}: {timeout} (must be > 0)")
                except ValueError:
                    logger.warning(f"Invalid timeout value for {env_var}: {os.environ[env_var]} (must be integer)")
        
        return timeouts
```

### Usage example

```bash
# In production environment
export PB_TIMEOUT_VALIDATION=600  # 10 minutes for thorough validation
export PB_TIMEOUT_TESTING=450     # 7.5 minutes for comprehensive tests
export PB_TIMEOUT_IMPLEMENTATION=180  # 3 minutes for complex implementations

python -m src.project_builder.cli.command "goal: refactor authentication module"
```

---

## Summary

These fixes address the key recommendations from the review:

1. **Fix 1**: Prevents resource leaks (High Priority)
2. **Fix 2**: Ensures correctness through testing (High Priority)
3. **Fix 3**: Improves maintainability through documentation (High Priority)
4. **Fix 4**: Enables monitoring and optimization (Medium Priority)
5. **Fix 5**: Allows environment-specific tuning (Medium Priority)

**Estimated Total Effort**: 13 hours  
**Recommended Sprint**: Implement Fixes 1-3 in next sprint, Fixes 4-5 in following sprint

