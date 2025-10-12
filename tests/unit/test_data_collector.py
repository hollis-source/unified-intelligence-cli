"""Unit tests for DataCollector (Week 9: Model training pipeline)."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil
from src.utils.data_collector import DataCollector
from src.entities import Task, Agent
from src.interfaces import LLMConfig


class TestDataCollector:
    """Test DataCollector class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing."""
        return Task(
            description="Write a function to calculate fibonacci numbers",
            task_id="task_1",
            priority=1
        )

    @pytest.fixture
    def sample_agent(self):
        """Create sample agent for testing."""
        return Agent(
            role="coder",
            capabilities=["code", "programming", "python"]
        )

    @pytest.fixture
    def sample_config(self):
        """Create sample LLM config."""
        return LLMConfig(temperature=0.7, max_tokens=500)

    def test_data_collector_initialization(self, temp_dir):
        """Test DataCollector initialization."""
        collector = DataCollector(data_dir=temp_dir, enabled=True)

        assert collector.enabled is True
        assert collector.data_dir == Path(temp_dir)
        assert collector.log_file.name.startswith("interactions_")
        # Log file created lazily on first write, so just check the path

    def test_data_collector_disabled(self, temp_dir):
        """Test DataCollector when disabled."""
        collector = DataCollector(data_dir=temp_dir, enabled=False)

        # Should not create log file when disabled
        assert collector.enabled is False

    def test_log_successful_interaction(
        self, temp_dir, sample_task, sample_agent, sample_config
    ):
        """Test logging successful interaction."""
        collector = DataCollector(data_dir=temp_dir, enabled=True)

        messages = [
            {"role": "system", "content": "You are a coder agent."},
            {"role": "user", "content": "Task: Write fibonacci function"}
        ]

        collector.log_interaction(
            task=sample_task,
            agent=sample_agent,
            messages=messages,
            output="def fibonacci(n): ...",
            status="success",
            duration_ms=1234,
            llm_config=sample_config,
            provider="tongyi",
            orchestrator="simple",
            context_history_length=0
        )

        # Verify data was written
        with open(collector.log_file, 'r') as f:
            line = f.readline()
            record = json.loads(line)

        assert record["task"]["task_id"] == "task_1"
        assert record["task"]["description"] == "Write a function to calculate fibonacci numbers"
        assert record["agent"]["role"] == "coder"
        assert record["agent"]["capabilities"] == ["code", "programming", "python"]
        assert record["llm"]["provider"] == "tongyi"
        assert record["llm"]["config"]["temperature"] == 0.7
        assert record["llm"]["config"]["max_tokens"] == 500
        assert record["execution"]["status"] == "success"
        assert record["execution"]["duration_ms"] == 1234
        assert record["execution"]["output"] == "def fibonacci(n): ..."
        assert len(record["execution"]["input_messages"]) == 2
        assert record["context"]["orchestrator"] == "simple"

    def test_log_failed_interaction(
        self, temp_dir, sample_task, sample_agent, sample_config
    ):
        """Test logging failed interaction."""
        collector = DataCollector(data_dir=temp_dir, enabled=True)

        messages = [
            {"role": "system", "content": "You are a coder agent."},
            {"role": "user", "content": "Task: Invalid task"}
        ]

        error_details = {
            "error_type": "ExecutionError",
            "component": "LLMAgentExecutor",
            "root_cause": "Connection timeout"
        }

        collector.log_interaction(
            task=sample_task,
            agent=sample_agent,
            messages=messages,
            output=None,
            status="failure",
            duration_ms=5000,
            llm_config=sample_config,
            provider="tongyi",
            errors=["Connection timeout"],
            error_details=error_details,
            orchestrator="simple",
            context_history_length=0
        )

        # Verify failure was logged
        with open(collector.log_file, 'r') as f:
            line = f.readline()
            record = json.loads(line)

        assert record["execution"]["status"] == "failure"
        assert record["execution"]["output"] is None
        assert record["execution"]["errors"] == ["Connection timeout"]
        assert record["execution"]["error_details"]["error_type"] == "ExecutionError"

    def test_get_statistics(
        self, temp_dir, sample_task, sample_agent, sample_config
    ):
        """Test getting collection statistics."""
        collector = DataCollector(data_dir=temp_dir, enabled=True)

        messages = [{"role": "user", "content": "Test"}]

        # Log 3 successful and 2 failed interactions
        for i in range(3):
            collector.log_interaction(
                task=sample_task,
                agent=sample_agent,
                messages=messages,
                output="success",
                status="success",
                duration_ms=1000,
                llm_config=sample_config,
                provider="mock"
            )

        for i in range(2):
            collector.log_interaction(
                task=sample_task,
                agent=sample_agent,
                messages=messages,
                output=None,
                status="failure",
                duration_ms=2000,
                llm_config=sample_config,
                provider="mock",
                errors=["Error"]
            )

        stats = collector.get_statistics()

        assert stats["total_interactions"] == 5
        assert stats["success_count"] == 3
        assert stats["failure_count"] == 2
        assert stats["success_rate"] == 0.6
        assert stats["enabled"] is True

    def test_load_interactions(
        self, temp_dir, sample_task, sample_agent, sample_config
    ):
        """Test loading interactions from log file."""
        collector = DataCollector(data_dir=temp_dir, enabled=True)

        messages = [{"role": "user", "content": "Test"}]

        # Log multiple interactions
        for i in range(5):
            collector.log_interaction(
                task=sample_task,
                agent=sample_agent,
                messages=messages,
                output=f"Output {i}",
                status="success" if i % 2 == 0 else "failure",
                duration_ms=1000,
                llm_config=sample_config,
                provider="mock"
            )

        # Load all interactions
        interactions = collector.load_interactions()
        assert len(interactions) == 5

        # Load with limit
        interactions = collector.load_interactions(limit=3)
        assert len(interactions) == 3

        # Load with status filter
        interactions = collector.load_interactions(status_filter="success")
        assert len(interactions) == 3
        assert all(i["execution"]["status"] == "success" for i in interactions)

    def test_log_interaction_when_disabled(
        self, temp_dir, sample_task, sample_agent, sample_config
    ):
        """Test that logging does nothing when disabled."""
        collector = DataCollector(data_dir=temp_dir, enabled=False)

        messages = [{"role": "user", "content": "Test"}]

        collector.log_interaction(
            task=sample_task,
            agent=sample_agent,
            messages=messages,
            output="test",
            status="success",
            duration_ms=1000,
            llm_config=sample_config,
            provider="mock"
        )

        # Should not create log file
        stats = collector.get_statistics()
        assert stats["total_interactions"] == 0
        assert stats["enabled"] is False
