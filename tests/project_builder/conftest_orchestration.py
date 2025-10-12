"""
Shared fixtures and utilities for task orchestration tests.

This module provides common fixtures, mocks, and utilities used across
all task orchestration test files.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_simple_project():
    """Fixture providing a simple project for testing."""
    return {
        "id": "simple-project-1",
        "name": "Simple Test Project",
        "goal": "Implement basic user authentication",
        "description": "Add login and logout functionality",
        "priority": "high",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_complex_project():
    """Fixture providing a complex project with multiple phases."""
    return {
        "id": "complex-project-1",
        "name": "Complex Multi-Phase Project",
        "goal": "Build complete e-commerce platform",
        "description": "Full-featured e-commerce system with payment integration",
        "priority": "critical",
        "phases": ["design", "implementation", "testing", "deployment"],
        "constraints": {
            "deadline": (datetime.now() + timedelta(days=90)).isoformat(),
            "budget": 100000,
            "team_size": 5,
        },
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_task():
    """Fixture providing a sample task."""
    return {
        "id": "task-1",
        "name": "Implement login endpoint",
        "description": "Create REST API endpoint for user login",
        "priority": 1,
        "estimated_duration": 120,  # minutes
        "dependencies": [],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_task_list():
    """Fixture providing a list of related tasks."""
    return [
        {
            "id": "task-1",
            "name": "Design database schema",
            "priority": 1,
            "dependencies": [],
            "estimated_duration": 60,
        },
        {
            "id": "task-2",
            "name": "Implement user model",
            "priority": 2,
            "dependencies": ["task-1"],
            "estimated_duration": 90,
        },
        {
            "id": "task-3",
            "name": "Create authentication service",
            "priority": 3,
            "dependencies": ["task-2"],
            "estimated_duration": 120,
        },
        {
            "id": "task-4",
            "name": "Add login endpoint",
            "priority": 4,
            "dependencies": ["task-3"],
            "estimated_duration": 60,
        },
        {
            "id": "task-5",
            "name": "Write tests",
            "priority": 5,
            "dependencies": ["task-4"],
            "estimated_duration": 90,
        },
    ]


@pytest.fixture
def sample_feedback():
    """Fixture providing sample feedback data."""
    return {
        "task_id": "task-1",
        "status": "completed",
        "actual_duration": 135,  # minutes
        "estimated_duration": 120,
        "success": True,
        "performance_metrics": {
            "cpu_usage": 45.2,
            "memory_usage": 512,
            "execution_time": 135,
        },
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_execution_result():
    """Fixture providing sample execution result."""
    return {
        "task_id": "task-1",
        "status": "success",
        "output": "Task completed successfully",
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(minutes=120)).isoformat(),
        "resources_used": {
            "cpu_cores": 2,
            "memory_mb": 512,
        },
    }


# ============================================================================
# Mock Component Fixtures
# ============================================================================

@pytest.fixture
def mock_goal_decomposer():
    """Fixture providing a mocked GoalDecomposer."""
    decomposer = AsyncMock()
    
    async def mock_decompose(goal):
        """Mock decomposition that returns sample tasks."""
        return [
            {"id": f"task-{i}", "name": f"Task {i}", "priority": i}
            for i in range(1, 4)
        ]
    
    decomposer.decompose = mock_decompose
    decomposer.validate_decomposition = AsyncMock(return_value=True)
    decomposer.estimate_effort = AsyncMock(return_value=360)  # minutes
    
    return decomposer


@pytest.fixture
def mock_execution_coordinator():
    """Fixture providing a mocked ExecutionCoordinator."""
    coordinator = AsyncMock()
    
    async def mock_execute(task):
        """Mock execution that returns success."""
        return {
            "task_id": task.get("id"),
            "status": "success",
            "duration": task.get("estimated_duration", 60),
        }
    
    coordinator.execute_task = mock_execute
    coordinator.schedule_task = AsyncMock(return_value=True)
    coordinator.cancel_task = AsyncMock(return_value=True)
    coordinator.get_task_status = AsyncMock(return_value="running")
    
    return coordinator


@pytest.fixture
def mock_feedback_handler():
    """Fixture providing a mocked FeedbackLoopHandler."""
    handler = AsyncMock()
    
    handler.collect_feedback = AsyncMock(return_value=True)
    handler.process_feedback = AsyncMock(return_value={"insights": []})
    handler.get_recommendations = AsyncMock(return_value=[])
    handler.update_learning_model = AsyncMock(return_value=True)
    
    return handler


@pytest.fixture
def mock_project_orchestrator():
    """Fixture providing a mocked ProjectOrchestrator."""
    orchestrator = AsyncMock()
    
    orchestrator.accept_project = AsyncMock(return_value={"success": True})
    orchestrator.get_project_status = AsyncMock(return_value="running")
    orchestrator.cancel_project = AsyncMock(return_value=True)
    orchestrator.get_metrics = AsyncMock(return_value={})
    
    return orchestrator


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def default_orchestrator_config():
    """Fixture providing default orchestrator configuration."""
    return {
        "max_concurrent_projects": 10,
        "task_timeout": 3600,  # seconds
        "retry_attempts": 3,
        "retry_delay": 5,  # seconds
        "enable_feedback_loop": True,
        "state_persistence_interval": 60,  # seconds
    }


@pytest.fixture
def default_decomposer_config():
    """Fixture providing default decomposer configuration."""
    return {
        "max_task_depth": 5,
        "min_task_duration": 15,  # minutes
        "max_task_duration": 480,  # minutes
        "enable_optimization": True,
        "decomposition_strategy": "hierarchical",
    }


@pytest.fixture
def default_coordinator_config():
    """Fixture providing default coordinator configuration."""
    return {
        "max_concurrent_tasks": 20,
        "executor_pool_size": 10,
        "task_timeout": 1800,  # seconds
        "enable_resource_management": True,
        "scheduling_strategy": "priority",
    }


@pytest.fixture
def default_feedback_config():
    """Fixture providing default feedback handler configuration."""
    return {
        "collection_interval": 10,  # seconds
        "retention_period": 30,  # days
        "enable_learning": True,
        "feedback_processors": ["performance", "quality", "resource"],
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def event_loop():
    """Fixture providing an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """Fixture providing a mocked logger."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def mock_metrics_collector():
    """Fixture providing a mocked metrics collector."""
    collector = Mock()
    collector.record_metric = Mock()
    collector.increment_counter = Mock()
    collector.record_timing = Mock()
    collector.get_metrics = Mock(return_value={})
    return collector


@pytest.fixture
def mock_state_manager():
    """Fixture providing a mocked state manager."""
    manager = AsyncMock()
    manager.save_state = AsyncMock(return_value=True)
    manager.load_state = AsyncMock(return_value={})
    manager.clear_state = AsyncMock(return_value=True)
    return manager


# ============================================================================
# Test Helper Functions
# ============================================================================

def create_task_with_dependencies(task_count: int = 5) -> List[Dict[str, Any]]:
    """
    Helper function to create a list of tasks with dependencies.
    
    Args:
        task_count: Number of tasks to create
        
    Returns:
        List of task dictionaries with dependencies
    """
    tasks = []
    for i in range(task_count):
        task = {
            "id": f"task-{i+1}",
            "name": f"Task {i+1}",
            "priority": i + 1,
            "estimated_duration": 60 + (i * 30),
            "dependencies": [f"task-{i}"] if i > 0 else [],
            "status": "pending",
        }
        tasks.append(task)
    return tasks


def create_parallel_tasks(task_count: int = 5) -> List[Dict[str, Any]]:
    """
    Helper function to create a list of independent parallel tasks.
    
    Args:
        task_count: Number of tasks to create
        
    Returns:
        List of independent task dictionaries
    """
    tasks = []
    for i in range(task_count):
        task = {
            "id": f"parallel-task-{i+1}",
            "name": f"Parallel Task {i+1}",
            "priority": 1,
            "estimated_duration": 60,
            "dependencies": [],
            "status": "pending",
        }
        tasks.append(task)
    return tasks


def assert_task_order_respects_dependencies(
    executed_tasks: List[str],
    task_dependencies: Dict[str, List[str]]
) -> bool:
    """
    Helper function to verify task execution order respects dependencies.
    
    Args:
        executed_tasks: List of task IDs in execution order
        task_dependencies: Dictionary mapping task IDs to their dependencies
        
    Returns:
        True if order is valid, False otherwise
    """
    executed_set = set()
    for task_id in executed_tasks:
        dependencies = task_dependencies.get(task_id, [])
        for dep in dependencies:
            if dep not in executed_set:
                return False
        executed_set.add(task_id)
    return True


# ============================================================================
# Parametrize Fixtures
# ============================================================================

@pytest.fixture(params=["simple", "complex", "parallel"])
def project_type(request):
    """Parametrized fixture for different project types."""
    if request.param == "simple":
        return {
            "type": "simple",
            "task_count": 3,
            "has_dependencies": False,
        }
    elif request.param == "complex":
        return {
            "type": "complex",
            "task_count": 10,
            "has_dependencies": True,
        }
    else:  # parallel
        return {
            "type": "parallel",
            "task_count": 5,
            "has_dependencies": False,
        }


@pytest.fixture(params=["success", "failure", "timeout"])
def execution_outcome(request):
    """Parametrized fixture for different execution outcomes."""
    return request.param

