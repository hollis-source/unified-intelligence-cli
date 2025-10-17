# tests/unit/entity/test_metrics_comprehensive.py
import json
import threading
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List
import pytest

from src.entity.metrics import (
    RoutingMetric,
    ModelSelectionMetric,
    TeamUtilizationMetric,
    MetricsCollector
)


@pytest.fixture
def sample_routing_metric():
    """Fixture for a basic RoutingMetric instance."""
    return RoutingMetric(
        timestamp="2023-12-01T10:00:00",
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001",
        expected_domain="support",
        expected_team="customer_support",
        is_correct=True
    )


@pytest.fixture
def sample_model_metric():
    """Fixture for a basic ModelSelectionMetric instance."""
    return ModelSelectionMetric(
        timestamp="2023-12-01T10:00:00",
        task_description="Test task",
        criteria="BALANCED",
        selected_model="gpt-4",
        fallback_chain=["gpt-3.5", "claude-2"],
        fallback_used=False,
        latency_seconds=1.2,
        success=True,
        error=None
    )


@pytest.fixture
def sample_team_metric():
    """Fixture for a basic TeamUtilizationMetric instance."""
    return TeamUtilizationMetric(
        timestamp="2023-12-01T10:00:00",
        team_name="customer_support",
        tasks_handled=15,
        agents_used=["agent_001", "agent_002"],
        average_latency=0.8,
        success_rate=0.95
    )


@pytest.fixture
def metrics_collector(tmp_path):
    """Fixture for MetricsCollector with temporary storage path."""
    return MetricsCollector(storage_path=str(tmp_path / "metrics"))


def test_routing_metric_creation(sample_routing_metric):
    """Test RoutingMetric creation with all fields."""
    metric = sample_routing_metric
    assert metric.timestamp == "2023-12-01T10:00:00"
    assert metric.task_description == "Test task"
    assert metric.classified_domain == "support"
    assert metric.domain_score == 0.95
    assert metric.target_team == "customer_support"
    assert metric.target_agent == "agent_001"
    assert metric.expected_domain == "support"
    assert metric.expected_team == "customer_support"
    assert metric.is_correct is True


def test_routing_metric_to_dict(sample_routing_metric):
    """Test RoutingMetric.to_dict() converts to expected dictionary format."""
    result = sample_routing_metric.to_dict()
    expected = {
        "timestamp": "2023-12-01T10:00:00",
        "task_description": "Test task",
        "classified_domain": "support",
        "domain_score": 0.95,
        "target_team": "customer_support",
        "target_agent": "agent_001",
        "expected_domain": "support",
        "expected_team": "customer_support",
        "is_correct": True
    }
    assert result == expected


def test_routing_metric_optional_fields():
    """Test RoutingMetric with optional fields as None."""
    metric = RoutingMetric(
        timestamp="2023-12-01T10:00:00",
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001"
    )
    assert metric.expected_domain is None
    assert metric.expected_team is None
    assert metric.is_correct is None


def test_model_selection_metric_creation(sample_model_metric):
    """Test ModelSelectionMetric creation with all fields."""
    metric = sample_model_metric
    assert metric.timestamp == "2023-12-01T10:00:00"
    assert metric.task_description == "Test task"
    assert metric.criteria == "BALANCED"
    assert metric.selected_model == "gpt-4"
    assert metric.fallback_chain == ["gpt-3.5", "claude-2"]
    assert metric.fallback_used is False
    assert metric.latency_seconds == 1.2
    assert metric.success is True
    assert metric.error is None


def test_model_selection_metric_to_dict(sample_model_metric):
    """Test ModelSelectionMetric.to_dict() converts to expected dictionary format."""
    result = sample_model_metric.to_dict()
    expected = {
        "timestamp": "2023-12-01T10:00:00",
        "task_description": "Test task",
        "criteria": "BALANCED",
        "selected_model": "gpt-4",
        "fallback_chain": ["gpt-3.5", "claude-2"],
        "fallback_used": False,
        "latency_seconds": 1.2,
        "success": True,
        "error": None
    }
    assert result == expected


def test_model_selection_metric_with_error():
    """Test ModelSelectionMetric with error field populated."""
    metric = ModelSelectionMetric(
        timestamp="2023-12-01T10:00:00",
        task_description="Test task",
        criteria="SPEED",
        selected_model="gpt-4",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=0.5,
        success=False,
        error="Connection timeout"
    )
    assert metric.success is False
    assert metric.error == "Connection timeout"


def test_team_utilization_metric_creation(sample_team_metric):
    """Test TeamUtilizationMetric creation with all fields."""
    metric = sample_team_metric
    assert metric.timestamp == "2023-12-01T10:00:00"
    assert metric.team_name == "customer_support"
    assert metric.tasks_handled == 15
    assert metric.agents_used == ["agent_001", "agent_002"]
    assert metric.average_latency == 0.8
    assert metric.success_rate == 0.95


def test_team_utilization_metric_to_dict(sample_team_metric):
    """Test TeamUtilizationMetric.to_dict() converts to expected dictionary format."""
    result = sample_team_metric.to_dict()
    expected = {
        "timestamp": "2023-12-01T10:00:00",
        "team_name": "customer_support",
        "tasks_handled": 15,
        "agents_used": ["agent_001", "agent_002"],
        "average_latency": 0.8,
        "success_rate": 0.95
    }
    assert result == expected


def test_metrics_collector_initialization(tmp_path):
    """Test MetricsCollector initializes with correct storage path and session ID."""
    storage_path = tmp_path / "test_metrics"
    collector = MetricsCollector(storage_path=str(storage_path))
    
    # Verify directory was created
    assert storage_path.exists()
    assert storage_path.is_dir()
    
    # Verify session_id format (YYYYMMDD_HHMMSS)
    assert len(collector.session_id) == 15  # 8+1+6 = 15
    assert collector.session_id[:8].isdigit()  # YYYYMMDD
    assert collector.session_id[8] == '_'
    assert collector.session_id[9:].isdigit()  # HHMMSS
    
    # Verify session file path
    expected_session_file = storage_path / f"session_{collector.session_id}.json"
    assert collector.session_file == expected_session_file
    
    # Verify empty initial state
    assert len(collector.routing_metrics) == 0
    assert len(collector.model_metrics) == 0
    assert len(collector.team_metrics) == 0


def test_record_routing_basic(metrics_collector):
    """Test basic recording of routing metric."""
    metrics_collector.record_routing(
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001"
    )
    
    assert len(metrics_collector.routing_metrics) == 1
    metric = metrics_collector.routing_metrics[0]
    assert metric.task_description == "Test task"
    assert metric.classified_domain == "support"
    assert metric.domain_score == 0.95
    assert metric.target_team == "customer_support"
    assert metric.target_agent == "agent_001"
    assert metric.expected_domain is None
    assert metric.expected_team is None
    assert metric.is_correct is None


def test_record_routing_with_validation_correct(metrics_collector):
    """Test routing metric with correct validation (is_correct=True)."""
    metrics_collector.record_routing(
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001",
        expected_domain="support",
        expected_team="customer_support"
    )
    
    assert len(metrics_collector.routing_metrics) == 1
    metric = metrics_collector.routing_metrics[0]
    assert metric.is_correct is True


def test_record_routing_with_validation_incorrect(metrics_collector):
    """Test routing metric with incorrect validation (is_correct=False)."""
    metrics_collector.record_routing(
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001",
        expected_domain="billing",
        expected_team="finance"
    )
    
    assert len(metrics_collector.routing_metrics) == 1
    metric = metrics_collector.routing_metrics[0]
    assert metric.is_correct is False


def test_record_routing_with_validation_partial(metrics_collector):
    """Test routing metric with only one validation field (is_correct=None)."""
    # Only expected_domain provided
    metrics_collector.record_routing(
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001",
        expected_domain="support",
        expected_team=None
    )
    
    assert len(metrics_collector.routing_metrics) == 1
    metric = metrics_collector.routing_metrics[0]
    assert metric.is_correct is None


def test_record_model_selection_basic(metrics_collector):
    """Test basic recording of model selection metric."""
    metrics_collector.record_model_selection(
        task_description="Test task",
        criteria="SPEED",
        selected_model="gpt-4",
        fallback_chain=["gpt-3.5", "claude-2"],
        fallback_used=False,
        latency_seconds=1.2,
        success=True
    )
    
    assert len(metrics_collector.model_metrics) == 1
    metric = metrics_collector.model_metrics[0]
    assert metric.task_description == "Test task"
    assert metric.criteria == "SPEED"
    assert metric.selected_model == "gpt-4"
    assert metric.fallback_chain == ["gpt-3.5", "claude-2"]
    assert metric.fallback_used is False
    assert metric.latency_seconds == 1.2
    assert metric.success is True
    assert metric.error is None


def test_record_model_selection_with_error(metrics_collector):
    """Test model selection recording with error."""
    metrics_collector.record_model_selection(
        task_description="Test task",
        criteria="QUALITY",
        selected_model="gpt-3.5",
        fallback_chain=["gpt-4"],
        fallback_used=True,
        latency_seconds=2.1,
        success=False,
        error="Model timeout"
    )
    
    assert len(metrics_collector.model_metrics) == 1
    metric = metrics_collector.model_metrics[0]
    assert metric.success is False
    assert metric.error == "Model timeout"


def test_record_team_utilization_basic(metrics_collector):
    """Test basic recording of team utilization metric."""
    metrics_collector.record_team_utilization(
        team_name="customer_support",
        tasks_handled=10,
        agents_used=["agent_001", "agent_002"],
        average_latency=0.8,
        success_rate=0.9
    )
    
    assert len(metrics_collector.team_metrics) == 1
    metric = metrics_collector.team_metrics[0]
    assert metric.team_name == "customer_support"
    assert metric.tasks_handled == 10
    assert metric.agents_used == ["agent_001", "agent_002"]
    assert metric.average_latency == 0.8
    assert metric.success_rate == 0.9


def test_save_creates_json_file(metrics_collector):
    """Test save() creates JSON file with expected structure."""
    # Add some metrics
    metrics_collector.record_routing(
        task_description="Test task",
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001",
        expected_domain="support",
        expected_team="customer_support"
    )
    
    metrics_collector.record_model_selection(
        task_description="Test task",
        criteria="BALANCED",
        selected_model="gpt-4",
        fallback_chain=["gpt-3.5"],
        fallback_used=False,
        latency_seconds=1.0,
        success=True
    )
    
    metrics_collector.record_team_utilization(
        team_name="customer_support",
        tasks_handled=5,
        agents_used=["agent_001"],
        average_latency=0.7,
        success_rate=0.95
    )
    
    # Save
    metrics_collector.save()
    
    # Verify file exists
    assert metrics_collector.session_file.exists()
    
    # Load and verify JSON structure
    with open(metrics_collector.session_file, 'r') as f:
        data = json.load(f)
    
    # Verify top-level structure
    assert "session_id" in data
    assert "timestamp" in data
    assert "routing_metrics" in data
    assert "model_metrics" in data
    assert "team_metrics" in data
    assert "summary" in data
    
    # Verify metrics content
    assert len(data["routing_metrics"]) == 1
    assert len(data["model_metrics"]) == 1
    assert len(data["team_metrics"]) == 1


def test_calculate_summary_routing_accuracy_100(metrics_collector):
    """Test summary calculation with 100% routing accuracy."""
    # Record 3 correct routing decisions
    for i in range(3):
        metrics_collector.record_routing(
            task_description=f"Task {i}",
            classified_domain="support",
            domain_score=0.9,
            target_team="customer_support",
            target_agent=f"agent_{i}",
            expected_domain="support",
            expected_team="customer_support"
        )
    
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_routing_decisions"] == 3
    assert summary["correct_routing_decisions"] == 3
    assert summary["routing_accuracy"] == 100.0


def test_calculate_summary_routing_accuracy_50(metrics_collector):
    """Test summary calculation with 50% routing accuracy."""
    # Record 2 correct and 2 incorrect
    metrics_collector.record_routing(
        task_description="Correct 1",
        classified_domain="support",
        domain_score=0.9,
        target_team="customer_support",
        target_agent="agent_1",
        expected_domain="support",
        expected_team="customer_support"
    )
    
    metrics_collector.record_routing(
        task_description="Correct 2",
        classified_domain="billing",
        domain_score=0.8,
        target_team="finance",
        target_agent="agent_2",
        expected_domain="billing",
        expected_team="finance"
    )
    
    metrics_collector.record_routing(
        task_description="Incorrect 1",
        classified_domain="support",
        domain_score=0.9,
        target_team="customer_support",
        target_agent="agent_3",
        expected_domain="billing",  # Wrong expected domain
        expected_team="finance"
    )
    
    metrics_collector.record_routing(
        task_description="Incorrect 2",
        classified_domain="billing",
        domain_score=0.8,
        target_team="finance",
        target_agent="agent_4",
        expected_domain="support",  # Wrong expected domain
        expected_team="customer_support"
    )
    
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_routing_decisions"] == 4
    assert summary["correct_routing_decisions"] == 2
    assert summary["routing_accuracy"] == 50.0


def test_calculate_summary_routing_accuracy_0(metrics_collector):
    """Test summary calculation with 0% routing accuracy."""
    # Record 3 incorrect routing decisions
    for i in range(3):
        metrics_collector.record_routing(
            task_description=f"Task {i}",
            classified_domain="support",
            domain_score=0.9,
            target_team="customer_support",
            target_agent=f"agent_{i}",
            expected_domain="billing",  # Wrong expected domain
            expected_team="finance"
        )
    
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_routing_decisions"] == 3
    assert summary["correct_routing_decisions"] == 0
    assert summary["routing_accuracy"] == 0.0


def test_calculate_summary_routing_accuracy_empty(metrics_collector):
    """Test summary calculation with empty routing metrics (division by zero)."""
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_routing_decisions"] == 0
    assert summary["correct_routing_decisions"] == 0
    assert summary["routing_accuracy"] == 0.0


def test_calculate_summary_model_selection_breakdown(metrics_collector):
    """Test summary calculation with multiple model selections."""
    # Record multiple model selections
    metrics_collector.record_model_selection(
        task_description="Task 1",
        criteria="SPEED",
        selected_model="gpt-4",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=1.0,
        success=True
    )
    
    metrics_collector.record_model_selection(
        task_description="Task 2",
        criteria="QUALITY",
        selected_model="gpt-4",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=1.5,
        success=True
    )
    
    metrics_collector.record_model_selection(
        task_description="Task 3",
        criteria="COST",
        selected_model="claude-2",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=2.0,
        success=True
    )
    
    metrics_collector.record_model_selection(
        task_description="Task 4",
        criteria="BALANCED",
        selected_model="gpt-3.5",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=1.2,
        success=True
    )
    
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_model_selections"] == 4
    assert summary["model_selection_breakdown"] == {
        "gpt-4": 2,
        "claude-2": 1,
        "gpt-3.5": 1
    }


def test_calculate_summary_fallback_usage_rate(metrics_collector):
    """Test summary calculation with fallback usage."""
    # Record 5 model selections: 2 with fallback used
    for i in range(5):
        fallback_used = (i < 2)  # First 2 use fallback
        metrics_collector.record_model_selection(
            task_description=f"Task {i}",
            criteria="BALANCED",
            selected_model="gpt-4",
            fallback_chain=["gpt-3.5"],
            fallback_used=fallback_used,
            latency_seconds=1.0,
            success=True
        )

    summary = metrics_collector._calculate_summary()

    assert summary["total_model_selections"] == 5
    assert summary["fallback_usage_rate"] == 40.0  # 2/5 = 0.4


def test_calculate_summary_fallback_usage_rate_empty(metrics_collector):
    """Test summary calculation with empty model metrics (division by zero)."""
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_model_selections"] == 0
    assert summary["fallback_usage_rate"] == 0.0


def test_calculate_summary_team_utilization(metrics_collector):
    """Test summary calculation with multiple team utilization snapshots."""
    # Record team utilization for different teams
    metrics_collector.record_team_utilization(
        team_name="customer_support",
        tasks_handled=10,
        agents_used=["agent_1", "agent_2"],
        average_latency=0.8,
        success_rate=0.95
    )

    metrics_collector.record_team_utilization(
        team_name="billing",
        tasks_handled=5,
        agents_used=["agent_3"],
        average_latency=1.2,
        success_rate=0.9
    )

    metrics_collector.record_team_utilization(
        team_name="customer_support",  # Same team again
        tasks_handled=8,
        agents_used=["agent_1"],
        average_latency=0.7,
        success_rate=0.98
    )

    summary = metrics_collector._calculate_summary()

    assert summary["total_team_snapshots"] == 3
    # Note: team_utilization dict stores last tasks_handled value per team (not sum)
    assert summary["team_utilization"] == {
        "customer_support": 8,  # Last value recorded
        "billing": 5
    }


def test_calculate_summary_team_utilization_empty(metrics_collector):
    """Test summary calculation with empty team metrics (division by zero)."""
    summary = metrics_collector._calculate_summary()
    
    assert summary["total_team_snapshots"] == 0
    assert summary["team_utilization"] == {}


def test_get_summary_thread_safe(metrics_collector):
    """Test get_summary() returns correct data and is thread-safe."""
    # Add some metrics
    metrics_collector.record_routing(
        task_description="Task 1",
        classified_domain="support",
        domain_score=0.9,
        target_team="customer_support",
        target_agent="agent_1",
        expected_domain="support",
        expected_team="customer_support"
    )
    
    # Call get_summary in another thread
    result = []
    def get_summary_thread():
        summary = metrics_collector.get_summary()
        result.append(summary)
    
    thread = threading.Thread(target=get_summary_thread)
    thread.start()
    thread.join()
    
    assert len(result) == 1
    summary = result[0]
    assert summary["total_routing_decisions"] == 1
    assert summary["correct_routing_decisions"] == 1
    assert summary["routing_accuracy"] == 100.0


def test_thread_safety_concurrent_records(metrics_collector):
    """Test thread safety with concurrent record calls."""
    # Define function to record multiple metrics
    def record_multiple():
        for i in range(10):
            metrics_collector.record_routing(
                task_description=f"Task {i}",
                classified_domain="support",
                domain_score=0.9,
                target_team="customer_support",
                target_agent=f"agent_{i}",
                expected_domain="support",
                expected_team="customer_support"
            )
            metrics_collector.record_model_selection(
                task_description=f"Task {i}",
                criteria="BALANCED",
                selected_model="gpt-4",
                fallback_chain=[],
                fallback_used=False,
                latency_seconds=1.0,
                success=True
            )
            metrics_collector.record_team_utilization(
                team_name="customer_support",
                tasks_handled=1,
                agents_used=[f"agent_{i}"],
                average_latency=0.8,
                success_rate=0.95
            )
    
    # Create and start multiple threads
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=record_multiple)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all metrics were recorded without race conditions
    assert len(metrics_collector.routing_metrics) == 50  # 5 threads * 10
    assert len(metrics_collector.model_metrics) == 50   # 5 threads * 10
    assert len(metrics_collector.team_metrics) == 50    # 5 threads * 10


def test_save_empty_metrics(metrics_collector):
    """Test save() works with empty metrics (no errors)."""
    metrics_collector.save()
    
    assert metrics_collector.session_file.exists()
    
    with open(metrics_collector.session_file, 'r') as f:
        data = json.load(f)
    
    # Verify structure is correct even with empty metrics
    assert data["session_id"] == metrics_collector.session_id
    assert len(data["routing_metrics"]) == 0
    assert len(data["model_metrics"]) == 0
    assert len(data["team_metrics"]) == 0
    assert data["summary"]["total_routing_decisions"] == 0
    assert data["summary"]["total_model_selections"] == 0
    assert data["summary"]["total_team_snapshots"] == 0


def test_save_overwrites_existing_file(metrics_collector):
    """Test save() overwrites existing session file."""
    # First save
    metrics_collector.record_routing(
        task_description="First task",
        classified_domain="support",
        domain_score=0.9,
        target_team="customer_support",
        target_agent="agent_1",
        expected_domain="support",
        expected_team="customer_support"
    )
    metrics_collector.save()
    
    # Check file size
    first_size = metrics_collector.session_file.stat().st_size
    
    # Add more metrics and save again
    metrics_collector.record_routing(
        task_description="Second task",
        classified_domain="billing",
        domain_score=0.8,
        target_team="finance",
        target_agent="agent_2",
        expected_domain="billing",
        expected_team="finance"
    )
    metrics_collector.save()
    
    # Verify file was overwritten (new size should be larger)
    second_size = metrics_collector.session_file.stat().st_size
    assert second_size > first_size
    
    # Verify content has both metrics
    with open(metrics_collector.session_file, 'r') as f:
        data = json.load(f)
    
    assert len(data["routing_metrics"]) == 2


def test_record_routing_truncates_long_description(metrics_collector):
    """Test record_routing truncates task_description to 100 characters."""
    long_desc = "x" * 150
    metrics_collector.record_routing(
        task_description=long_desc,
        classified_domain="support",
        domain_score=0.95,
        target_team="customer_support",
        target_agent="agent_001"
    )
    
    assert len(metrics_collector.routing_metrics[0].task_description) == 100
    assert metrics_collector.routing_metrics[0].task_description == "x" * 100


def test_record_model_selection_truncates_long_description(metrics_collector):
    """Test record_model_selection truncates task_description to 100 characters."""
    long_desc = "y" * 150
    metrics_collector.record_model_selection(
        task_description=long_desc,
        criteria="SPEED",
        selected_model="gpt-4",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=1.0,
        success=True
    )
    
    assert len(metrics_collector.model_metrics[0].task_description) == 100
    assert metrics_collector.model_metrics[0].task_description == "y" * 100


@pytest.mark.parametrize("criteria", ["SPEED", "QUALITY", "COST", "PRIVACY", "BALANCED"])
def test_record_model_selection_valid_criteria(metrics_collector, criteria):
    """Test record_model_selection accepts all valid criteria values."""
    metrics_collector.record_model_selection(
        task_description="Test task",
        criteria=criteria,
        selected_model="gpt-4",
        fallback_chain=[],
        fallback_used=False,
        latency_seconds=1.0,
        success=True
    )
    
    assert len(metrics_collector.model_metrics) == 1
    assert metrics_collector.model_metrics[0].criteria == criteria


def test_get_summary_returns_latest_data(metrics_collector):
    """Test get_summary() returns the latest aggregated data after updates."""
    # Initial state
    summary1 = metrics_collector.get_summary()
    assert summary1["total_routing_decisions"] == 0
    
    # Add a routing metric
    metrics_collector.record_routing(
        task_description="Test",
        classified_domain="support",
        domain_score=0.9,
        target_team="customer_support",
        target_agent="agent_1",
        expected_domain="support",
        expected_team="customer_support"
    )
    
    # Get summary again - should reflect new data
    summary2 = metrics_collector.get_summary()
    assert summary2["total_routing_decisions"] == 1
    assert summary2["correct_routing_decisions"] == 1
    assert summary2["routing_accuracy"] == 100.0