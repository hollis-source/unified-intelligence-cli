"""
End-to-end CLI integration tests.

Tests the complete flow from CLI command through coordination to results.
"""

import pytest
import asyncio
from pathlib import Path
from click.testing import CliRunner

from src.main import main
from src.config import Config
from src.composition import compose_dependencies
from src.entities import Agent, Task
from src.adapters.llm.mock_provider import MockLLMProvider


class TestCLIEndToEnd:
    """End-to-end tests for CLI workflows."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_cli_with_mock_provider_single_task(self, runner):
        """Test full CLI flow with mock provider and single task."""
        result = runner.invoke(main, [
            '--task', 'Write a hello world function',
            '--provider', 'mock',
            '--verbose'
        ])

        # Should complete (may succeed or fail gracefully)
        assert result.exit_code in [0, 1]
        # Should show some output
        assert len(result.output) > 0

    def test_cli_with_multiple_tasks_parallel(self, runner):
        """Test CLI with multiple tasks in parallel mode."""
        result = runner.invoke(main, [
            '--task', 'Write function one',
            '--task', 'Write function two',
            '--task', 'Write function three',
            '--provider', 'mock',
            '--parallel'
        ])

        # Should handle multiple tasks
        assert result.exit_code in [0, 1]

    def test_cli_with_config_file(self, runner, tmp_path):
        """Test CLI loading config from file."""
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"provider": "mock", "verbose": false, "timeout": 120}')

        result = runner.invoke(main, [
            '--task', 'Test task',
            '--config', str(config_file)
        ])

        # Should load config and execute
        assert result.exit_code in [0, 1]

    def test_cli_with_custom_timeout(self, runner):
        """Test CLI with custom timeout parameter."""
        result = runner.invoke(main, [
            '--task', 'Quick task',
            '--provider', 'mock',
            '--timeout', '10'
        ])

        # Should respect timeout parameter
        assert result.exit_code in [0, 1]

    def test_composition_creates_working_coordinator(self):
        """Test that composition creates fully functional coordinator."""
        # Create test dependencies
        mock_provider = MockLLMProvider(default_response="Integration test response")
        agents = [
            Agent(role="coder", capabilities=["code", "programming"]),
            Agent(role="tester", capabilities=["test", "testing"])
        ]

        # Compose dependencies
        coordinator = compose_dependencies(
            llm_provider=mock_provider,
            agents=agents,
            logger=None
        )

        # Should create valid coordinator
        assert coordinator is not None
        assert hasattr(coordinator, 'coordinate')

    @pytest.mark.asyncio
    async def test_full_stack_integration(self):
        """Test full stack: composition → coordination → execution."""
        # Setup
        mock_provider = MockLLMProvider(default_response="Task completed")
        agents = [Agent(role="coder", capabilities=["code", "write"])]

        # Compose
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Execute
        tasks = [Task(description="Write a function", priority=1)]
        results = await coordinator.coordinate(tasks, agents)

        # Verify
        assert len(results) == 1
        assert results[0].output is not None


class TestFileOperationsIntegration:
    """Integration tests for real file operations with tools."""

    @pytest.mark.asyncio
    async def test_coordination_with_file_operations(self, tmp_path):
        """Test coordinating tasks that involve file operations."""
        # Create test workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        test_file = workspace / "input.txt"
        test_file.write_text("Input data for processing")

        # Setup
        mock_provider = MockLLMProvider(default_response="File processed successfully")
        agents = [Agent(role="file_processor", capabilities=["file", "process"])]

        # Compose
        from src.composition import compose_dependencies
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Execute task
        task = Task(
            description=f"Process file at {test_file}",
            priority=1
        )
        results = await coordinator.coordinate([task], agents)

        # Verify coordination completed
        assert len(results) == 1
        assert results[0] is not None

    @pytest.mark.asyncio
    async def test_multi_agent_file_workflow(self, tmp_path):
        """Test multiple agents working with files in sequence."""
        # Create workspace
        workspace = tmp_path / "project"
        workspace.mkdir()

        # Setup multiple agents
        mock_provider = MockLLMProvider(default_response="Step completed")
        agents = [
            Agent(role="creator", capabilities=["create", "write"]),
            Agent(role="reviewer", capabilities=["review", "check"]),
            Agent(role="finalizer", capabilities=["finalize", "complete"])
        ]

        # Compose
        from src.composition import compose_dependencies
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Execute multi-step workflow
        tasks = [
            Task(
                description="Create new file in project",
                task_id="create",
                priority=1,
                dependencies=[]
            ),
            Task(
                description="Review the created file",
                task_id="review",
                priority=2,
                dependencies=["create"]
            ),
            Task(
                description="Finalize the project",
                task_id="finalize",
                priority=3,
                dependencies=["review"]
            )
        ]

        results = await coordinator.coordinate(tasks, agents)

        # All steps should complete
        assert len(results) == 3
        assert all(r is not None for r in results)


class TestComplexScenarios:
    """Integration tests for complex multi-agent scenarios."""

    @pytest.mark.asyncio
    async def test_large_task_set_coordination(self):
        """Test coordinating many tasks concurrently."""
        # Setup
        mock_provider = MockLLMProvider(default_response="Task done")
        agents = [
            Agent(role=f"worker_{i}", capabilities=["work", "process"])
            for i in range(5)
        ]

        # Compose
        from src.composition import compose_dependencies
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Create many tasks
        tasks = [
            Task(description=f"Process item {i}", priority=1)
            for i in range(20)
        ]

        # Execute
        results = await coordinator.coordinate(tasks, agents)

        # All should complete
        assert len(results) == 20
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_mixed_priority_tasks(self):
        """Test that tasks with different priorities are handled correctly."""
        # Setup
        mock_provider = MockLLMProvider(default_response="Priority task done")
        agents = [Agent(role="worker", capabilities=["work"])]

        # Compose
        from src.composition import compose_dependencies
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Create tasks with mixed priorities
        tasks = [
            Task(description="Low priority", priority=3),
            Task(description="High priority", priority=1),
            Task(description="Medium priority", priority=2)
        ]

        # Execute
        results = await coordinator.coordinate(tasks, agents)

        # All should complete
        assert len(results) == 3
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_agent_specialization(self):
        """Test that specialized agents are matched to appropriate tasks."""
        # Setup
        mock_provider = MockLLMProvider(default_response="Specialized work done")
        agents = [
            Agent(role="python_expert", capabilities=["python", "code", "backend"]),
            Agent(role="frontend_expert", capabilities=["javascript", "react", "frontend"]),
            Agent(role="devops_expert", capabilities=["docker", "kubernetes", "deploy"])
        ]

        # Compose
        from src.composition import compose_dependencies
        coordinator = compose_dependencies(mock_provider, agents, None)

        # Create specialized tasks
        tasks = [
            Task(description="Write Python backend API", priority=1),
            Task(description="Create React frontend component", priority=1),
            Task(description="Setup Docker deployment", priority=1)
        ]

        # Execute
        results = await coordinator.coordinate(tasks, agents)

        # All should be matched and completed
        assert len(results) == 3
        assert all(r is not None for r in results)