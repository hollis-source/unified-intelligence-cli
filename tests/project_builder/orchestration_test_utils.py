"""
Utility classes and functions for task orchestration testing.

This module provides helper classes, builders, and utilities to make
writing orchestration tests easier and more maintainable.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import random
import string


# ============================================================================
# Builder Classes
# ============================================================================

class ProjectBuilder:
    """Builder class for creating test projects."""
    
    def __init__(self):
        self._project = {
            "id": self._generate_id(),
            "name": "Test Project",
            "goal": "Test goal",
            "created_at": datetime.now().isoformat(),
        }
    
    def with_id(self, project_id: str) -> 'ProjectBuilder':
        """Set project ID."""
        self._project["id"] = project_id
        return self
    
    def with_name(self, name: str) -> 'ProjectBuilder':
        """Set project name."""
        self._project["name"] = name
        return self
    
    def with_goal(self, goal: str) -> 'ProjectBuilder':
        """Set project goal."""
        self._project["goal"] = goal
        return self
    
    def with_priority(self, priority: str) -> 'ProjectBuilder':
        """Set project priority."""
        self._project["priority"] = priority
        return self
    
    def with_constraints(self, constraints: Dict[str, Any]) -> 'ProjectBuilder':
        """Set project constraints."""
        self._project["constraints"] = constraints
        return self
    
    def with_deadline(self, days_from_now: int) -> 'ProjectBuilder':
        """Set project deadline."""
        deadline = datetime.now() + timedelta(days=days_from_now)
        if "constraints" not in self._project:
            self._project["constraints"] = {}
        self._project["constraints"]["deadline"] = deadline.isoformat()
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the project."""
        return self._project.copy()
    
    @staticmethod
    def _generate_id() -> str:
        """Generate a random project ID."""
        return f"project-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


class TaskBuilder:
    """Builder class for creating test tasks."""
    
    def __init__(self):
        self._task = {
            "id": self._generate_id(),
            "name": "Test Task",
            "description": "Test task description",
            "priority": 1,
            "estimated_duration": 60,
            "dependencies": [],
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
    
    def with_id(self, task_id: str) -> 'TaskBuilder':
        """Set task ID."""
        self._task["id"] = task_id
        return self
    
    def with_name(self, name: str) -> 'TaskBuilder':
        """Set task name."""
        self._task["name"] = name
        return self
    
    def with_priority(self, priority: int) -> 'TaskBuilder':
        """Set task priority."""
        self._task["priority"] = priority
        return self
    
    def with_duration(self, minutes: int) -> 'TaskBuilder':
        """Set estimated duration."""
        self._task["estimated_duration"] = minutes
        return self
    
    def with_dependencies(self, dependencies: List[str]) -> 'TaskBuilder':
        """Set task dependencies."""
        self._task["dependencies"] = dependencies
        return self
    
    def with_status(self, status: str) -> 'TaskBuilder':
        """Set task status."""
        self._task["status"] = status
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the task."""
        return self._task.copy()
    
    @staticmethod
    def _generate_id() -> str:
        """Generate a random task ID."""
        return f"task-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


class FeedbackBuilder:
    """Builder class for creating test feedback."""
    
    def __init__(self):
        self._feedback = {
            "task_id": "task-1",
            "status": "completed",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }
    
    def for_task(self, task_id: str) -> 'FeedbackBuilder':
        """Set task ID."""
        self._feedback["task_id"] = task_id
        return self
    
    def with_status(self, status: str) -> 'FeedbackBuilder':
        """Set status."""
        self._feedback["status"] = status
        return self
    
    def with_success(self, success: bool) -> 'FeedbackBuilder':
        """Set success flag."""
        self._feedback["success"] = success
        return self
    
    def with_duration(self, actual: int, estimated: int) -> 'FeedbackBuilder':
        """Set duration information."""
        self._feedback["actual_duration"] = actual
        self._feedback["estimated_duration"] = estimated
        return self
    
    def with_metrics(self, metrics: Dict[str, Any]) -> 'FeedbackBuilder':
        """Set performance metrics."""
        self._feedback["performance_metrics"] = metrics
        return self
    
    def with_error(self, error: str) -> 'FeedbackBuilder':
        """Set error information."""
        self._feedback["error"] = error
        self._feedback["success"] = False
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the feedback."""
        return self._feedback.copy()


# ============================================================================
# Mock Factories
# ============================================================================

class MockComponentFactory:
    """Factory for creating mock components with configurable behavior."""
    
    @staticmethod
    def create_goal_decomposer(
        decompose_result: Optional[List[Dict]] = None,
        should_fail: bool = False,
        delay_seconds: float = 0
    ) -> AsyncMock:
        """
        Create a mock GoalDecomposer with configurable behavior.
        
        Args:
            decompose_result: Result to return from decompose()
            should_fail: Whether decompose should raise an exception
            delay_seconds: Delay before returning result
            
        Returns:
            Configured AsyncMock
        """
        mock = AsyncMock()
        
        async def decompose(goal):
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            if should_fail:
                raise Exception("Decomposition failed")
            return decompose_result or [
                {"id": "task-1", "name": "Task 1"},
                {"id": "task-2", "name": "Task 2"},
            ]
        
        mock.decompose = decompose
        return mock
    
    @staticmethod
    def create_execution_coordinator(
        execution_result: Optional[Dict] = None,
        should_fail: bool = False,
        delay_seconds: float = 0
    ) -> AsyncMock:
        """
        Create a mock ExecutionCoordinator with configurable behavior.
        
        Args:
            execution_result: Result to return from execute_task()
            should_fail: Whether execution should fail
            delay_seconds: Delay before returning result
            
        Returns:
            Configured AsyncMock
        """
        mock = AsyncMock()
        
        async def execute_task(task):
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            if should_fail:
                raise Exception("Execution failed")
            return execution_result or {
                "task_id": task.get("id"),
                "status": "success",
            }
        
        mock.execute_task = execute_task
        return mock
    
    @staticmethod
    def create_feedback_handler(
        feedback_result: Optional[Dict] = None,
        should_fail: bool = False
    ) -> AsyncMock:
        """
        Create a mock FeedbackLoopHandler with configurable behavior.
        
        Args:
            feedback_result: Result to return from process_feedback()
            should_fail: Whether processing should fail
            
        Returns:
            Configured AsyncMock
        """
        mock = AsyncMock()
        
        async def process_feedback(feedback):
            if should_fail:
                raise Exception("Feedback processing failed")
            return feedback_result or {"insights": [], "recommendations": []}
        
        mock.process_feedback = process_feedback
        return mock


# ============================================================================
# Test Data Generators
# ============================================================================

class TestDataGenerator:
    """Generator for creating various test data scenarios."""
    
    @staticmethod
    def generate_task_graph(
        node_count: int,
        max_dependencies: int = 2,
        ensure_acyclic: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate a task dependency graph.
        
        Args:
            node_count: Number of tasks to generate
            max_dependencies: Maximum dependencies per task
            ensure_acyclic: Ensure no circular dependencies
            
        Returns:
            List of tasks with dependencies
        """
        tasks = []
        for i in range(node_count):
            dependencies = []
            if i > 0 and ensure_acyclic:
                # Only depend on earlier tasks to ensure acyclic
                num_deps = min(random.randint(0, max_dependencies), i)
                if num_deps > 0:
                    dependencies = random.sample(
                        [f"task-{j}" for j in range(i)],
                        num_deps
                    )
            
            task = TaskBuilder() \
                .with_id(f"task-{i}") \
                .with_name(f"Task {i}") \
                .with_priority(i + 1) \
                .with_dependencies(dependencies) \
                .build()
            tasks.append(task)
        
        return tasks
    
    @staticmethod
    def generate_execution_timeline(
        tasks: List[Dict[str, Any]],
        success_rate: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        Generate execution results for a list of tasks.
        
        Args:
            tasks: List of tasks
            success_rate: Probability of task success (0.0 to 1.0)
            
        Returns:
            List of execution results
        """
        results = []
        for task in tasks:
            success = random.random() < success_rate
            result = {
                "task_id": task["id"],
                "status": "success" if success else "failed",
                "actual_duration": task.get("estimated_duration", 60) + random.randint(-10, 30),
                "timestamp": datetime.now().isoformat(),
            }
            if not success:
                result["error"] = "Random failure for testing"
            results.append(result)
        
        return results


# ============================================================================
# Assertion Helpers
# ============================================================================

class OrchestrationAssertions:
    """Helper class for common orchestration assertions."""
    
    @staticmethod
    def assert_valid_task_structure(task: Dict[str, Any]) -> None:
        """Assert that a task has valid structure."""
        required_fields = ["id", "name", "priority", "dependencies"]
        for field in required_fields:
            assert field in task, f"Task missing required field: {field}"
        
        assert isinstance(task["dependencies"], list), "Dependencies must be a list"
        assert isinstance(task["priority"], int), "Priority must be an integer"
    
    @staticmethod
    def assert_tasks_respect_dependencies(
        executed_order: List[str],
        tasks: List[Dict[str, Any]]
    ) -> None:
        """Assert that task execution order respects dependencies."""
        task_map = {task["id"]: task for task in tasks}
        executed_set = set()
        
        for task_id in executed_order:
            task = task_map.get(task_id)
            if task:
                for dep in task.get("dependencies", []):
                    assert dep in executed_set, \
                        f"Task {task_id} executed before dependency {dep}"
            executed_set.add(task_id)
    
    @staticmethod
    def assert_feedback_contains_metrics(feedback: Dict[str, Any]) -> None:
        """Assert that feedback contains expected metrics."""
        assert "task_id" in feedback, "Feedback missing task_id"
        assert "status" in feedback, "Feedback missing status"
        assert "timestamp" in feedback, "Feedback missing timestamp"
    
    @staticmethod
    def assert_execution_result_valid(result: Dict[str, Any]) -> None:
        """Assert that execution result is valid."""
        assert "task_id" in result, "Result missing task_id"
        assert "status" in result, "Result missing status"
        assert result["status"] in ["success", "failed", "timeout"], \
            f"Invalid status: {result['status']}"


# ============================================================================
# Async Test Helpers
# ============================================================================

class AsyncTestHelper:
    """Helper class for async testing scenarios."""
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """
        Wait for a condition to become true.
        
        Args:
            condition: Callable that returns bool
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds
            
        Returns:
            True if condition met, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)
        return False
    
    @staticmethod
    async def run_with_timeout(
        coro,
        timeout: float = 5.0
    ):
        """
        Run a coroutine with timeout.
        
        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds
            
        Returns:
            Result of coroutine
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        return await asyncio.wait_for(coro, timeout=timeout)


# ============================================================================
# Performance Testing Utilities
# ============================================================================

class PerformanceMetrics:
    """Class for collecting and analyzing performance metrics."""
    
    def __init__(self):
        self.metrics = []
    
    def record(self, name: str, value: float, unit: str = "ms"):
        """Record a performance metric."""
        self.metrics.append({
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        })
    
    def get_average(self, name: str) -> Optional[float]:
        """Get average value for a metric."""
        values = [m["value"] for m in self.metrics if m["name"] == name]
        return sum(values) / len(values) if values else None
    
    def get_percentile(self, name: str, percentile: float) -> Optional[float]:
        """Get percentile value for a metric."""
        values = sorted([m["value"] for m in self.metrics if m["name"] == name])
        if not values:
            return None
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]
    
    def assert_performance(
        self,
        name: str,
        max_value: float,
        percentile: float = 95.0
    ):
        """Assert that performance meets threshold."""
        value = self.get_percentile(name, percentile)
        assert value is not None, f"No metrics found for {name}"
        assert value <= max_value, \
            f"{name} p{percentile} ({value}) exceeds threshold ({max_value})"

