#!/usr/bin/env python3
"""Integration test script for PriorityWorker deployment validation.

This script performs a smoke test on factory.create_from_config() workflow,
validating component wiring without executing daemons. Uses pytest with mocking
to avoid external dependencies like Redis and Git.

Test Strategy:
- Unit test style (pytest) with mocking
- Validate dependency injection chain
- Check factory returns PriorityWorker instance (not dict)
- Verify protocol compliance

Adapted from ULTRATHINK (testing-lead) on 2025-10-04.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import components to test
from src.priority_queue.factory import PriorityWorkerFactory
from src.priority_queue.entities import Task, Metrics


@pytest.fixture
def mock_config_file():
    """
    Fixture providing a minimal YAML configuration for testing.

    Creates a temporary YAML file with minimal PriorityWorker config.
    """
    config = {
        'priority_worker': {
            'daemon': {
                'cycle_hours': 24,
                'max_retries': 3,
                'base_delay': 1.0
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'git': {
                'repo_path': '.'
            },
            'dsl': {
                'cwd': '.',
                'timeout': 300
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            },
            'priority_queue': {
                'queue_file': 'test_priorities.yaml'
            }
        }
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name

    yield config_path

    # Cleanup
    Path(config_path).unlink()


@pytest.fixture
def mock_external_dependencies():
    """
    Fixture for mocking external dependencies (Redis, Git, subprocess).

    Patches redis.Redis and GitAdapter to return mock objects,
    preventing actual external connections during testing.
    """
    with patch('redis.Redis') as mock_redis, \
         patch('subprocess.run') as mock_subprocess, \
         patch('src.priority_queue.adapters.priority_queue_adapter.PriorityQueueAdapter.poll_tasks') as mock_poll:

        # Mock Redis client
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.set.return_value = True
        mock_redis.return_value = mock_redis_instance

        # Mock subprocess (for git commands)
        mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')

        # Mock task polling (return empty list for smoke test)
        mock_poll.return_value = []

        yield {
            'redis': mock_redis_instance,
            'subprocess': mock_subprocess,
            'poll_tasks': mock_poll
        }


def test_factory_returns_priority_worker_instance(mock_config_file, mock_external_dependencies):
    """
    Test that factory.create_from_config() returns PriorityWorker instance.

    Validates:
    - Factory returns an object (not dict)
    - Object has expected PriorityWorker attributes
    - All protocol dependencies are wired
    """
    factory = PriorityWorkerFactory()

    # Create PriorityWorker from config
    worker = factory.create_from_config(mock_config_file)

    # Assert factory returns an instance, not dict
    assert not isinstance(worker, dict), "Factory should return PriorityWorker instance, not dict"
    assert hasattr(worker, 'run'), "PriorityWorker should have run() method"

    # Validate protocol dependencies are wired
    assert hasattr(worker, 'task_poller'), "PriorityWorker should have task_poller"
    assert hasattr(worker, 'task_claimer'), "PriorityWorker should have task_claimer"
    assert hasattr(worker, 'status_updater'), "PriorityWorker should have status_updater"
    assert hasattr(worker, 'branch_manager'), "PriorityWorker should have branch_manager"
    assert hasattr(worker, 'workflow_executor'), "PriorityWorker should have workflow_executor"
    assert hasattr(worker, 'metrics_tracker'), "PriorityWorker should have metrics_tracker"
    assert hasattr(worker, 'shutdown_handler'), "PriorityWorker should have shutdown_handler"
    assert hasattr(worker, 'config'), "PriorityWorker should have config"


def test_task_poller_protocol_compliance(mock_config_file, mock_external_dependencies):
    """
    Test that task_poller adheres to TaskPoller protocol.

    Validates:
    - task_poller has poll_tasks() method
    - poll_tasks() returns list of dicts
    """
    factory = PriorityWorkerFactory()
    worker = factory.create_from_config(mock_config_file)

    # Validate protocol compliance
    assert hasattr(worker.task_poller, 'poll_tasks'), "task_poller should have poll_tasks() method"

    # Test polling (should return empty list from mock)
    tasks = worker.task_poller.poll_tasks()
    assert isinstance(tasks, list), "poll_tasks() should return a list"
    assert all(isinstance(t, dict) for t in tasks), "poll_tasks() should return list of dicts"


def test_use_case_dependency_injection(mock_config_file, mock_external_dependencies):
    """
    Test that use cases receive correct dependencies via DI.

    Validates:
    - Use cases are instantiated
    - Dependencies (adapters) are injected
    - Mocked Redis client is used (no real connections)
    """
    factory = PriorityWorkerFactory()
    worker = factory.create_from_config(mock_config_file)

    # Validate task_claimer has claim_task method (ClaimTaskUseCase wrapper)
    assert hasattr(worker.task_claimer, 'claim_task'), "task_claimer should have claim_task() method"

    # Validate status_updater has update_status method
    assert hasattr(worker.status_updater, 'update_status'), "status_updater should have update_status() method"

    # Validate workflow_executor has execute_workflow method
    assert hasattr(worker.workflow_executor, 'execute_workflow'), "workflow_executor should have execute_workflow() method"

    # Redis mock should have been called (validating DI chain)
    mock_external_dependencies['redis'].ping.assert_called()


def test_config_parsing_and_wiring(mock_config_file, mock_external_dependencies):
    """
    Test that config is correctly parsed and propagated to components.

    Validates:
    - Daemon config (cycle_seconds) is set
    - Redis config is passed to adapter
    - Git config is passed to adapter
    """
    factory = PriorityWorkerFactory()
    worker = factory.create_from_config(mock_config_file)

    # Validate daemon config
    assert worker.config['cycle_seconds'] == 24 * 3600, "cycle_seconds should be 24 hours (86400s)"
    assert worker.config['max_retries'] == 3, "max_retries should be 3"

    # Validate config sections are present
    assert 'redis' in worker.config, "Redis config should be present"
    assert 'git' in worker.config, "Git config should be present"
    assert 'dsl' in worker.config, "DSL config should be present"


if __name__ == '__main__':
    # Allow running script directly for quick validation
    pytest.main([__file__, '-v', '-s'])
