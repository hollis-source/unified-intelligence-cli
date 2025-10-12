"""
Metrics - Domain entities for tracking system performance.

Week 13: Priority 3 - Monitoring & Metrics infrastructure.

Clean Architecture: Core domain entities with no external dependencies.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json
import threading
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class RoutingMetric:
    """
    Single routing decision metric.

    Tracks domain classification and team routing for analysis.
    """
    timestamp: str
    task_description: str
    classified_domain: str
    domain_score: float
    target_team: str
    target_agent: str
    expected_domain: Optional[str] = None  # For validation
    expected_team: Optional[str] = None    # For validation
    is_correct: Optional[bool] = None      # True if routing matched expectation

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ModelSelectionMetric:
    """
    Model selection metric.

    Tracks intelligent model orchestration decisions.
    """
    timestamp: str
    task_description: str
    criteria: str  # SPEED, QUALITY, COST, PRIVACY, BALANCED
    selected_model: str
    fallback_chain: List[str]
    fallback_used: bool
    latency_seconds: float
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class TeamUtilizationMetric:
    """
    Team utilization snapshot.

    Tracks which teams are being used and how often.
    """
    timestamp: str
    team_name: str
    tasks_handled: int
    agents_used: List[str]
    average_latency: float
    success_rate: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MetricsCollector:
    """
    Collects and stores system metrics.

    Week 13: Core metrics infrastructure for monitoring routing accuracy,
    model selection, and team utilization.

    Clean Architecture: Domain entity with no external dependencies.
    Thread Safety: Uses threading.Lock for concurrent access.

    Responsibilities:
    - Collect routing decisions
    - Collect model selections
    - Collect team utilization
    - Persist to JSON storage

    Design:
    - Single JSON file per session (append-only)
    - Thread-safe writes
    - No external dependencies (pure Python)
    """

    def __init__(self, storage_path: str = "data/metrics"):
        """
        Initialize metrics collector.

        Args:
            storage_path: Directory for metrics storage (default: data/metrics)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Metrics storage
        self.routing_metrics: List[RoutingMetric] = []
        self.model_metrics: List[ModelSelectionMetric] = []
        self.team_metrics: List[TeamUtilizationMetric] = []

        # Thread safety
        self._lock = threading.Lock()

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.storage_path / f"session_{self.session_id}.json"

        logger.info(f"MetricsCollector initialized (session: {self.session_id})")

    def record_routing(
        self,
        task_description: str,
        classified_domain: str,
        domain_score: float,
        target_team: str,
        target_agent: str,
        expected_domain: Optional[str] = None,
        expected_team: Optional[str] = None
    ) -> None:
        """
        Record a routing decision.

        Args:
            task_description: Task description (truncated to 100 chars)
            classified_domain: Domain classifier result
            domain_score: Weighted score for classification
            target_team: Team selected by router
            target_agent: Agent selected by team
            expected_domain: Expected domain (for validation)
            expected_team: Expected team (for validation)
        """
        with self._lock:
            # Determine if routing is correct
            is_correct = None
            if expected_domain and expected_team:
                is_correct = (
                    classified_domain == expected_domain and
                    target_team == expected_team
                )

            metric = RoutingMetric(
                timestamp=datetime.now().isoformat(),
                task_description=task_description[:100],
                classified_domain=classified_domain,
                domain_score=domain_score,
                target_team=target_team,
                target_agent=target_agent,
                expected_domain=expected_domain,
                expected_team=expected_team,
                is_correct=is_correct
            )

            self.routing_metrics.append(metric)
            logger.debug(f"Recorded routing: {classified_domain} → {target_team} → {target_agent}")

    def record_model_selection(
        self,
        task_description: str,
        criteria: str,
        selected_model: str,
        fallback_chain: List[str],
        fallback_used: bool,
        latency_seconds: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Record a model selection decision.

        Args:
            task_description: Task description (truncated to 100 chars)
            criteria: Selection criteria (SPEED, QUALITY, etc.)
            selected_model: Model that was used
            fallback_chain: Fallback models available
            fallback_used: Whether fallback was triggered
            latency_seconds: Execution latency
            success: Whether execution succeeded
            error: Error message if failed
        """
        with self._lock:
            metric = ModelSelectionMetric(
                timestamp=datetime.now().isoformat(),
                task_description=task_description[:100],
                criteria=criteria,
                selected_model=selected_model,
                fallback_chain=fallback_chain,
                fallback_used=fallback_used,
                latency_seconds=latency_seconds,
                success=success,
                error=error
            )

            self.model_metrics.append(metric)
            logger.debug(f"Recorded model selection: {selected_model} ({criteria})")

    def record_team_utilization(
        self,
        team_name: str,
        tasks_handled: int,
        agents_used: List[str],
        average_latency: float,
        success_rate: float
    ) -> None:
        """
        Record team utilization snapshot.

        Args:
            team_name: Team name
            tasks_handled: Number of tasks handled
            agents_used: List of agents that handled tasks
            average_latency: Average task latency
            success_rate: Success rate (0.0-1.0)
        """
        with self._lock:
            metric = TeamUtilizationMetric(
                timestamp=datetime.now().isoformat(),
                team_name=team_name,
                tasks_handled=tasks_handled,
                agents_used=agents_used,
                average_latency=average_latency,
                success_rate=success_rate
            )

            self.team_metrics.append(metric)
            logger.debug(f"Recorded team utilization: {team_name} ({tasks_handled} tasks)")

    def save(self) -> None:
        """
        Save all metrics to JSON file.

        Thread-safe persistence to session file.
        """
        with self._lock:
            data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "routing_metrics": [m.to_dict() for m in self.routing_metrics],
                "model_metrics": [m.to_dict() for m in self.model_metrics],
                "team_metrics": [m.to_dict() for m in self.team_metrics],
                "summary": self._calculate_summary()
            }

            with open(self.session_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Metrics saved to {self.session_file}")

    def _calculate_summary(self) -> dict:
        """Calculate summary statistics."""
        # Routing accuracy
        routing_total = len(self.routing_metrics)
        routing_correct = sum(
            1 for m in self.routing_metrics
            if m.is_correct is True
        )
        routing_accuracy = (
            (routing_correct / routing_total * 100)
            if routing_total > 0 else 0.0
        )

        # Model selection breakdown
        model_counts = {}
        for m in self.model_metrics:
            model_counts[m.selected_model] = model_counts.get(m.selected_model, 0) + 1

        # Fallback usage
        fallback_count = sum(1 for m in self.model_metrics if m.fallback_used)
        fallback_rate = (
            (fallback_count / len(self.model_metrics) * 100)
            if self.model_metrics else 0.0
        )

        # Team utilization
        team_counts = {}
        for m in self.team_metrics:
            team_counts[m.team_name] = m.tasks_handled

        return {
            "routing_accuracy": round(routing_accuracy, 2),
            "total_routing_decisions": routing_total,
            "correct_routing_decisions": routing_correct,
            "model_selection_breakdown": model_counts,
            "fallback_usage_rate": round(fallback_rate, 2),
            "team_utilization": team_counts,
            "total_model_selections": len(self.model_metrics),
            "total_team_snapshots": len(self.team_metrics)
        }

    def get_summary(self) -> dict:
        """Get current summary statistics."""
        with self._lock:
            return self._calculate_summary()
