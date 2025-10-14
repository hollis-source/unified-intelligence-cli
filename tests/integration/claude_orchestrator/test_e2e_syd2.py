"""End-to-End Integration Test with SYD2.

Tests real task execution on SYD2 server via SSH.

IMPORTANT: This test requires:
1. SSH access to SYD2 (ui-cli_jake@syd2.jacobhollis.com)
2. Auggie installed on SYD2
3. Working directory exists on SYD2

Run with: pytest tests/integration/claude_orchestrator/test_e2e_syd2.py -v -s
"""

import pytest
from datetime import datetime

from src.claude_orchestrator.entities.worker import WorkerPoolConfig
from src.claude_orchestrator.entities.generated_task import GeneratedTask
from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.orchestrators.minimal_orchestrator import MinimalOrchestrator
from src.claude_orchestrator.interfaces.worker_pool import TaskExecutionStatus


class TestE2ESyd2Integration:
    """End-to-end integration tests with real SYD2 execution."""

    @pytest.fixture
    def syd2_config(self):
        """Create SYD2 worker pool configuration."""
        return WorkerPoolConfig(
            pool_type="ssh",
            max_workers=1,
            ssh_host="root@208.87.135.78",
            working_dir="/root",
            model_name="sonnet4",
        )

    @pytest.fixture
    def orchestrator(self, syd2_config):
        """Create orchestrator with SYD2 pool."""
        pool = SingleWorkerPool(syd2_config)
        return MinimalOrchestrator(pool)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_simple_file_creation_task(self, orchestrator):
        """
        Test: Execute simple file creation task on SYD2.

        Task: Create a test file with timestamp.
        Expected: File created successfully, logs captured.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        task = GeneratedTask.create(
            id=f"test-simple-{timestamp}",
            instruction=f"""Create a file at /tmp/orchestrator_test_{timestamp}.txt with the following content:

Hello from Claude Orchestrator!
Task ID: test-simple-{timestamp}
Timestamp: {timestamp}
Status: SUCCESS

This file was created by the Claude Orchestrator MVP test.""",
            rationale="End-to-end integration test for orchestrator MVP",
            goal_id="testing",
            estimated_minutes=2,
            priority="P0",
        )

        # Execute task
        result = orchestrator.execute_task(task, timeout_minutes=5)

        # Verify results
        assert result.status == TaskExecutionStatus.COMPLETED
        assert result.exit_code == 0
        assert result.task_id == task.id
        assert len(result.stdout) > 0

        # Verify execution summary
        summary = orchestrator.get_execution_summary()
        assert summary["total_tasks"] == 1
        assert summary["completed"] == 1
        assert summary["success_rate"] == 1.0

        print("\n=== TEST PASSED ===")
        print(f"Task: {task.id}")
        print(f"Status: {result.status}")
        print(f"Output length: {len(result.stdout)} chars")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_task_timeout_handling(self, orchestrator):
        """
        Test: Task timeout handling.

        Task: Sleep for long time (exceeds timeout).
        Expected: TaskTimeoutError raised.
        """
        from src.claude_orchestrator.interfaces.worker_pool import TaskTimeoutError

        task = GeneratedTask.create(
            id=f"test-timeout-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            instruction="Sleep for 300 seconds (5 minutes) using: sleep 300",
            rationale="Test timeout handling",
            goal_id="testing",
            estimated_minutes=5,
            priority="P0",
        )

        # Execute with short timeout
        with pytest.raises(TaskTimeoutError):
            orchestrator.execute_task(task, timeout_minutes=1)

        print("\n=== TEST PASSED (Timeout Correctly Raised) ===")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_tasks_sequential(self, orchestrator):
        """
        Test: Execute multiple tasks sequentially.

        Tasks: 3 simple tasks executed one after another.
        Expected: All complete successfully, worker reused.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        tasks = [
            GeneratedTask.create(
                id=f"test-seq-{i}-{timestamp}",
                instruction=f"Create file /tmp/orchestrator_seq_{i}_{timestamp}.txt with content: 'Task {i} completed'",
                rationale=f"Sequential test task {i}",
                goal_id="testing",
                estimated_minutes=2,
                priority="P0",
            )
            for i in range(1, 4)
        ]

        # Execute all tasks
        results = orchestrator.execute_tasks_sequential(tasks, timeout_minutes=5)

        # Verify all completed
        assert len(results) == 3
        assert all(r.status == TaskExecutionStatus.COMPLETED for r in results)
        assert all(r.exit_code == 0 for r in results)

        # Verify execution summary
        summary = orchestrator.get_execution_summary()
        assert summary["total_tasks"] == 3
        assert summary["completed"] == 3
        assert summary["success_rate"] == 1.0

        print("\n=== TEST PASSED ===")
        print(f"Tasks executed: {len(results)}")
        print(f"Success rate: {summary['success_rate'] * 100}%")

    def teardown_method(self, method):
        """Cleanup after each test."""
        # Orchestrator shutdown handled by pytest fixture cleanup
        pass


# Standalone test runner for manual execution
if __name__ == "__main__":
    print("=== Claude Orchestrator E2E Test ===\n")

    # Configure SYD2
    config = WorkerPoolConfig(
        pool_type="ssh",
        max_workers=1,
        ssh_host="root@208.87.135.78",
        working_dir="/root",
        model_name="sonnet4",
    )

    # Create orchestrator
    pool = SingleWorkerPool(config)
    orchestrator = MinimalOrchestrator(pool)

    # Create test task
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task = GeneratedTask.create(
        id=f"manual-test-{timestamp}",
        instruction=f"""Create a test file at /tmp/orchestrator_manual_test_{timestamp}.txt with content:

        Claude Orchestrator Manual Test
        Timestamp: {timestamp}
        Status: SUCCESS

        This verifies the full end-to-end flow works correctly.""",
        rationale="Manual E2E test",
        goal_id="testing",
        estimated_minutes=2,
        priority="P0",
    )

    # Execute
    try:
        print("Executing task...")
        result = orchestrator.execute_task(task, timeout_minutes=5)

        print("\n=== RESULTS ===")
        print(f"Task ID: {result.task_id}")
        print(f"Status: {result.status}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Output:\n{result.stdout[:500]}...")

        if result.status == TaskExecutionStatus.COMPLETED:
            print("\n✅ TEST PASSED")
        else:
            print("\n❌ TEST FAILED")

    finally:
        orchestrator.shutdown()
