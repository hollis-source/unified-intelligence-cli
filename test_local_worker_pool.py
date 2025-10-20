#!/usr/bin/env python3
"""Simple test for LocalWorkerPool to verify it works correctly."""

import sys
import time
from pathlib import Path

from src.claude_orchestrator.entities.worker import WorkerPoolConfig, WorkerStatus
from src.claude_orchestrator.adapters.local_worker_pool import LocalWorkerPool
from src.claude_orchestrator.entities.generated_task import GeneratedTask


def test_local_worker_pool_basic():
    """Test basic LocalWorkerPool functionality."""
    print("Testing LocalWorkerPool...")

    # Create config
    config = WorkerPoolConfig(
        pool_type="local",
        max_workers=1,
        working_dir="/home/ui-cli_jake/unified-intelligence-cli",
        model_name="sonnet4",
    )

    # Create pool
    pool = LocalWorkerPool(config)
    print("✓ LocalWorkerPool created")

    # Check worker is idle
    assert pool.worker.status == WorkerStatus.IDLE
    print("✓ Worker is idle")

    # Check available workers
    available = pool.get_available_workers()
    assert len(available) == 1
    print("✓ One worker available")

    # Shutdown
    pool.shutdown()
    print("✓ Pool shutdown successfully")

    print("\nAll tests passed!")


def test_local_worker_pool_task_submission():
    """Test task submission (without actually running auggie)."""
    print("\nTesting LocalWorkerPool task submission...")

    config = WorkerPoolConfig(
        pool_type="local",
        max_workers=1,
        working_dir="/home/ui-cli_jake/unified-intelligence-cli",
        model_name="sonnet4",
    )

    pool = LocalWorkerPool(config)

    # Create a simple test task
    task = GeneratedTask.create(
        goal_id="test-goal",
        instruction="Print 'Hello World' to stdout and exit with success",
        rationale="Testing local execution",
        priority="P1",
        estimated_minutes=1,
    )

    print(f"✓ Task created: {task.id}")

    # Test that we can create task files without running auggie
    # (We'll manually check that the mechanism works)
    try:
        # This would normally assign and run the task
        # For now, just verify the pool structure
        print(f"✓ Worker type: {pool.worker.worker_type}")
        print(f"✓ Worker capabilities: {pool.worker.capabilities}")
        print(f"✓ Worker status: {pool.worker.status}")

        pool.shutdown()
        print("✓ Test completed successfully")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        pool.shutdown()
        raise


if __name__ == "__main__":
    try:
        test_local_worker_pool_basic()
        test_local_worker_pool_task_submission()
        print("\n✅ All LocalWorkerPool tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
