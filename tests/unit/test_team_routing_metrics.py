"""
Unit tests for team routing metrics (Week 14, Priority 2.1).

Tests TeamRoutingMetric dataclass, MetricsCollector.record_team_routing(),
and TeamRouter timing/confidence tracking.
"""

import pytest
import json
from pathlib import Path
from src.entity.metrics import MetricsCollector, TeamRoutingMetric
from src.entity import Task, Agent, AgentTeam
from src.routing.team_router import TeamRouter
from src.routing.domain_classifier import DomainClassifier


def create_task(description: str, task_id: str = None) -> Task:
    """Helper to create Task with correct parameter names."""
    return Task(description=description, task_id=task_id or "test-task")


def create_test_agent(role: str, tier: int = 2) -> Agent:
    """Helper to create test agent."""
    return Agent(role=role, capabilities=["test"], tier=tier)


def create_test_team(name: str, domain: str, agents: list) -> AgentTeam:
    """Helper to create test team."""
    team = AgentTeam(
        name=name,
        domain=domain,
        lead_agent=agents[0] if agents else create_test_agent("lead"),
        agents=agents
    )
    return team


class TestTeamRoutingMetric:
    """Test suite for TeamRoutingMetric dataclass."""

    def test_create_team_routing_metric(self):
        """TeamRoutingMetric should be created with all fields."""
        metric = TeamRoutingMetric(
            timestamp="2025-10-20T12:00:00",
            task_description="Test task",
            domain="backend",
            domain_score=5.5,
            domain_confidence=0.55,
            team="Backend",
            team_confidence=1.0,
            agent="backend-lead",
            routing_time_ms=15.5,
            cache_hit=False
        )

        assert metric.timestamp == "2025-10-20T12:00:00"
        assert metric.task_description == "Test task"
        assert metric.domain == "backend"
        assert metric.domain_score == 5.5
        assert metric.domain_confidence == 0.55
        assert metric.team == "Backend"
        assert metric.team_confidence == 1.0
        assert metric.agent == "backend-lead"
        assert metric.routing_time_ms == 15.5
        assert metric.cache_hit is False

    def test_team_routing_metric_to_dict(self):
        """TeamRoutingMetric.to_dict() should convert to dictionary."""
        metric = TeamRoutingMetric(
            timestamp="2025-10-20T12:00:00",
            task_description="Test task",
            domain="testing",
            domain_score=7.2,
            domain_confidence=0.72,
            team="Testing",
            team_confidence=1.0,
            agent="unit-test-engineer",
            routing_time_ms=12.3,
            cache_hit=True
        )

        result = metric.to_dict()

        assert result["timestamp"] == "2025-10-20T12:00:00"
        assert result["task_description"] == "Test task"
        assert result["domain"] == "testing"
        assert result["domain_score"] == 7.2
        assert result["domain_confidence"] == 0.72
        assert result["team"] == "Testing"
        assert result["team_confidence"] == 1.0
        assert result["agent"] == "unit-test-engineer"
        assert result["routing_time_ms"] == 12.3
        assert result["cache_hit"] is True

    def test_team_routing_metric_cache_hit_optional(self):
        """cache_hit should be optional (None by default)."""
        metric = TeamRoutingMetric(
            timestamp="2025-10-20T12:00:00",
            task_description="Test",
            domain="frontend",
            domain_score=6.0,
            domain_confidence=0.6,
            team="Frontend",
            team_confidence=1.0,
            agent="frontend-lead",
            routing_time_ms=10.0
        )

        assert metric.cache_hit is None


class TestMetricsCollectorTeamRouting:
    """Test suite for MetricsCollector.record_team_routing()."""

    def test_record_team_routing(self, tmp_path):
        """record_team_routing() should append TeamRoutingMetric to list."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_team_routing(
            task_description="Implement user authentication",
            domain="backend",
            domain_score=6.5,
            domain_confidence=0.65,
            team="Backend",
            team_confidence=1.0,
            agent="backend-lead",
            routing_time_ms=18.5,
            cache_hit=False
        )

        assert len(collector.team_routing_metrics) == 1
        metric = collector.team_routing_metrics[0]

        assert metric.task_description == "Implement user authentication"
        assert metric.domain == "backend"
        assert metric.domain_score == 6.5
        assert metric.domain_confidence == 0.65
        assert metric.team == "Backend"
        assert metric.team_confidence == 1.0
        assert metric.agent == "backend-lead"
        assert metric.routing_time_ms == 18.5
        assert metric.cache_hit is False

    def test_record_team_routing_truncates_description(self, tmp_path):
        """record_team_routing() should truncate task description to 100 chars."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        long_description = "A" * 150  # 150 characters

        collector.record_team_routing(
            task_description=long_description,
            domain="testing",
            domain_score=7.0,
            domain_confidence=0.7,
            team="Testing",
            team_confidence=1.0,
            agent="unit-test-engineer",
            routing_time_ms=10.0
        )

        metric = collector.team_routing_metrics[0]
        assert len(metric.task_description) == 100
        assert metric.task_description == "A" * 100

    def test_record_multiple_team_routing_metrics(self, tmp_path):
        """Multiple team routing metrics should be appended."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_team_routing(
            task_description="Task 1",
            domain="backend",
            domain_score=6.0,
            domain_confidence=0.6,
            team="Backend",
            team_confidence=1.0,
            agent="backend-lead",
            routing_time_ms=15.0
        )

        collector.record_team_routing(
            task_description="Task 2",
            domain="frontend",
            domain_score=7.5,
            domain_confidence=0.75,
            team="Frontend",
            team_confidence=1.0,
            agent="frontend-lead",
            routing_time_ms=12.0
        )

        assert len(collector.team_routing_metrics) == 2
        assert collector.team_routing_metrics[0].task_description == "Task 1"
        assert collector.team_routing_metrics[1].task_description == "Task 2"

    def test_save_includes_team_routing_metrics(self, tmp_path):
        """save() should include team_routing_metrics in JSON output."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        collector.record_team_routing(
            task_description="Test task",
            domain="testing",
            domain_score=8.0,
            domain_confidence=0.8,
            team="Testing",
            team_confidence=1.0,
            agent="unit-test-engineer",
            routing_time_ms=10.5,
            cache_hit=True
        )

        collector.save()

        # Load saved JSON
        session_file = collector.session_file
        assert session_file.exists()

        with open(session_file, 'r') as f:
            data = json.load(f)

        assert "team_routing_metrics" in data
        assert len(data["team_routing_metrics"]) == 1

        metric = data["team_routing_metrics"][0]
        assert metric["task_description"] == "Test task"
        assert metric["domain"] == "testing"
        assert metric["domain_confidence"] == 0.8
        assert metric["team_confidence"] == 1.0
        assert metric["cache_hit"] is True

    def test_summary_includes_team_routing_statistics(self, tmp_path):
        """Summary should include team routing statistics."""
        collector = MetricsCollector(storage_path=str(tmp_path / "metrics"))

        # Add some team routing metrics
        collector.record_team_routing(
            task_description="Task 1",
            domain="backend",
            domain_score=6.0,
            domain_confidence=0.6,
            team="Backend",
            team_confidence=1.0,
            agent="backend-lead",
            routing_time_ms=15.0,
            cache_hit=True
        )

        collector.record_team_routing(
            task_description="Task 2",
            domain="frontend",
            domain_score=8.0,
            domain_confidence=0.8,
            team="Frontend",
            team_confidence=1.0,
            agent="frontend-lead",
            routing_time_ms=12.0,
            cache_hit=False
        )

        summary = collector.get_summary()

        assert "team_routing_statistics" in summary
        stats = summary["team_routing_statistics"]

        assert stats["total_decisions"] == 2
        assert stats["avg_domain_confidence"] == 0.7  # (0.6 + 0.8) / 2
        assert stats["avg_team_confidence"] == 1.0
        assert stats["avg_routing_time_ms"] == 13.5  # (15.0 + 12.0) / 2
        assert stats["cache_hit_rate"] == 50.0  # 1/2 = 50%


class TestTeamRouterTimingAndConfidence:
    """Test suite for TeamRouter timing and confidence tracking."""

    def test_route_tracks_timing(self):
        """route() should track routing time in milliseconds."""
        # Create test setup
        classifier = DomainClassifier()
        collector = MetricsCollector(storage_path="data/metrics")
        classifier.metrics_collector = collector

        router = TeamRouter(domain_classifier=classifier)

        backend_agent = create_test_agent("backend-lead", tier=2)
        backend_team = create_test_team("Backend", "backend", [backend_agent])

        task = create_task("Implement REST API endpoint")

        # Route task
        agent = router.route(task, [backend_team])

        # Verify metrics recorded
        assert len(collector.team_routing_metrics) == 1
        metric = collector.team_routing_metrics[0]

        # Timing should be positive (milliseconds)
        assert metric.routing_time_ms > 0
        assert metric.routing_time_ms < 1000  # Should be fast (<1 second)

    def test_route_calculates_domain_confidence(self):
        """route() should calculate normalized domain confidence (0-1)."""
        classifier = DomainClassifier()
        collector = MetricsCollector(storage_path="data/metrics")
        classifier.metrics_collector = collector

        router = TeamRouter(domain_classifier=classifier)

        testing_agent = create_test_agent("unit-test-engineer", tier=3)
        testing_team = create_test_team("Testing", "testing", [testing_agent])

        task = create_task("Write unit tests for authentication")

        agent = router.route(task, [testing_team])

        metric = collector.team_routing_metrics[0]

        # Domain confidence should be normalized to 0-1
        assert 0.0 <= metric.domain_confidence <= 1.0
        assert metric.domain_score >= 0.0  # Raw score

    def test_route_calculates_team_confidence(self):
        """route() should calculate team confidence based on match quality."""
        classifier = DomainClassifier()
        collector = MetricsCollector(storage_path="data/metrics")
        classifier.metrics_collector = collector

        router = TeamRouter(domain_classifier=classifier)

        frontend_agent = create_test_agent("frontend-lead", tier=2)
        frontend_team = create_test_team("Frontend", "frontend", [frontend_agent])

        task = create_task("Build React component for user dashboard")

        agent = router.route(task, [frontend_team])

        metric = collector.team_routing_metrics[0]

        # Team confidence should be 1.0 for perfect match
        assert metric.team_confidence == 1.0
        assert metric.team == "Frontend"

    def test_normalize_confidence(self):
        """_normalize_confidence() should normalize scores to 0-1 range."""
        router = TeamRouter()

        # Test cases
        assert router._normalize_confidence(0.0) == 0.0
        assert router._normalize_confidence(5.0) == 0.5  # 5/10 = 0.5
        assert router._normalize_confidence(10.0) == 1.0
        assert router._normalize_confidence(15.0) == 1.0  # Clamped to max
        assert router._normalize_confidence(-5.0) == 0.0  # Clamped to min

    def test_select_team_with_confidence_perfect_match(self):
        """_select_team_with_confidence() should return 1.0 for perfect match."""
        router = TeamRouter()

        backend_agent = create_test_agent("backend-lead", tier=2)
        backend_team = create_test_team("Backend", "backend", [backend_agent])

        task = create_task("Implement database migration")

        team, confidence = router._select_team_with_confidence(task, [backend_team])

        assert team.name == "Backend"
        assert confidence == 1.0  # Perfect match

    def test_select_team_with_confidence_fallback(self):
        """_select_team_with_confidence() should return lower confidence for fallback."""
        router = TeamRouter()

        # Create team with different name than mapped (triggers fallback by domain)
        backend_agent = create_test_agent("backend-engineer", tier=3)
        backend_team = create_test_team("Backend Infrastructure", "backend", [backend_agent])

        # Task classified as "backend" but team name is "Backend Infrastructure" not "Backend"
        task = create_task("Implement database schema migration")

        team, confidence = router._select_team_with_confidence(task, [backend_team])

        assert team.name == "Backend Infrastructure"
        assert confidence == 0.8  # Domain match confidence (not perfect name match)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
