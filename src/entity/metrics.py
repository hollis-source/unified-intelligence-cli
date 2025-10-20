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


@dataclass
class TeamRoutingMetric:
    """
    Team-level routing decision metric (Week 14, Priority 2.1).

    Tracks detailed team→agent routing decisions with confidence scores
    and timing information.

    Purpose:
    - Monitor team routing quality (confidence scores)
    - Identify routing bottlenecks (timing)
    - Track team→agent decision patterns
    - Debug routing errors

    Attributes:
        timestamp: ISO format timestamp
        task_description: Task description (truncated to 100 chars)
        domain: Classified domain
        domain_score: Domain classification score (raw, may be >1)
        domain_confidence: Normalized confidence 0-1 (domain_score / max_possible)
        team: Selected team name
        team_confidence: Team selection confidence 0-1
        agent: Final agent role
        routing_time_ms: Total routing time in milliseconds
        cache_hit: Whether domain classification was cache hit (optional)
    """
    timestamp: str
    task_description: str
    domain: str
    domain_score: float
    domain_confidence: float
    team: str
    team_confidence: float
    agent: str
    routing_time_ms: float
    cache_hit: Optional[bool] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class OutputValidationMetric:
    """
    Output validation metric (Week 14, Priority 2.2).

    Tracks post-execution validation of agent outputs for quality assurance.

    Purpose:
    - Monitor output quality (syntax errors, validation failures)
    - Track validation pass/fail rates by type
    - Identify agents producing low-quality outputs
    - Debug generation issues

    Attributes:
        timestamp: ISO format timestamp
        task_description: Task description (truncated to 100 chars)
        agent: Agent that generated the output
        validation_type: Type of validation (python, json, markdown, yaml, generic)
        passed: Whether validation passed
        error_message: Error message if validation failed (optional)
        error_line: Line number of error (optional)
        error_column: Column number of error (optional)
        warning_count: Number of warnings (even if passed)
        output_length: Length of output in characters
    """
    timestamp: str
    task_description: str
    agent: str
    validation_type: str
    passed: bool
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    warning_count: int = 0
    output_length: int = 0

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
        self.team_routing_metrics: List[TeamRoutingMetric] = []  # Week 14, Priority 2.1
        self.output_validation_metrics: List[OutputValidationMetric] = []  # Week 14, Priority 2.2

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

    def record_team_routing(
        self,
        task_description: str,
        domain: str,
        domain_score: float,
        domain_confidence: float,
        team: str,
        team_confidence: float,
        agent: str,
        routing_time_ms: float,
        cache_hit: Optional[bool] = None
    ) -> None:
        """
        Record team-level routing decision (Week 14, Priority 2.1).

        Args:
            task_description: Task description (will be truncated to 100 chars)
            domain: Classified domain
            domain_score: Domain classification score (raw, may be >1)
            domain_confidence: Normalized confidence 0-1
            team: Selected team name
            team_confidence: Team selection confidence 0-1
            agent: Final agent role
            routing_time_ms: Total routing time in milliseconds
            cache_hit: Whether domain classification was cache hit (optional)
        """
        with self._lock:
            metric = TeamRoutingMetric(
                timestamp=datetime.now().isoformat(),
                task_description=task_description[:100],
                domain=domain,
                domain_score=domain_score,
                domain_confidence=domain_confidence,
                team=team,
                team_confidence=team_confidence,
                agent=agent,
                routing_time_ms=routing_time_ms,
                cache_hit=cache_hit
            )

            self.team_routing_metrics.append(metric)
            logger.debug(
                f"Recorded team routing: {domain} ({domain_confidence:.2f}) → "
                f"{team} ({team_confidence:.2f}) → {agent} ({routing_time_ms:.1f}ms)"
            )

    def record_output_validation(
        self,
        task_description: str,
        agent: str,
        validation_type: str,
        passed: bool,
        error_message: Optional[str] = None,
        error_line: Optional[int] = None,
        error_column: Optional[int] = None,
        warning_count: int = 0,
        output_length: int = 0
    ) -> None:
        """
        Record output validation result (Week 14, Priority 2.2).

        Args:
            task_description: Task description (will be truncated to 100 chars)
            agent: Agent that generated the output
            validation_type: Type of validation (python, json, markdown, yaml, generic)
            passed: Whether validation passed
            error_message: Error message if validation failed (optional)
            error_line: Line number of error (optional)
            error_column: Column number of error (optional)
            warning_count: Number of warnings (even if passed)
            output_length: Length of output in characters
        """
        with self._lock:
            metric = OutputValidationMetric(
                timestamp=datetime.now().isoformat(),
                task_description=task_description[:100],
                agent=agent,
                validation_type=validation_type,
                passed=passed,
                error_message=error_message,
                error_line=error_line,
                error_column=error_column,
                warning_count=warning_count,
                output_length=output_length
            )

            self.output_validation_metrics.append(metric)
            status = "PASS" if passed else "FAIL"
            logger.debug(
                f"Recorded output validation: {agent} → {validation_type} → {status} "
                f"({warning_count} warnings, {output_length} chars)"
            )

    def save(self) -> None:
        """
        Save all metrics to JSON file.

        Thread-safe persistence to session file.
        """
        with self._lock:
            data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "routing_metrics": [metric.to_dict() for metric in self.routing_metrics],
                "model_metrics": [metric.to_dict() for metric in self.model_metrics],
                "team_metrics": [metric.to_dict() for metric in self.team_metrics],
                "team_routing_metrics": [metric.to_dict() for metric in self.team_routing_metrics],
                "output_validation_metrics": [metric.to_dict() for metric in self.output_validation_metrics],
                "summary": self._calculate_summary()
            }

            with open(self.session_file, "w") as file_handle:
                json.dump(data, file_handle, indent=2)

            logger.info(f"Metrics saved to {self.session_file}")

    def _calculate_summary(self) -> dict:
        """Calculate summary statistics."""
        # Routing accuracy
        routing_total = len(self.routing_metrics)
        routing_correct = sum(
            1 for routing_metric in self.routing_metrics
            if routing_metric.is_correct is True
        )
        routing_accuracy = (
            (routing_correct / routing_total * 100)
            if routing_total > 0 else 0.0
        )

        # Model selection breakdown
        model_counts = {}
        for model_metric in self.model_metrics:
            model_counts[model_metric.selected_model] = model_counts.get(model_metric.selected_model, 0) + 1

        # Fallback usage
        fallback_count = sum(1 for model_metric in self.model_metrics if model_metric.fallback_used)
        fallback_rate = (
            (fallback_count / len(self.model_metrics) * 100)
            if self.model_metrics else 0.0
        )

        # Team utilization
        team_counts = {}
        for team_metric in self.team_metrics:
            team_counts[team_metric.team_name] = team_metric.tasks_handled

        # Team routing statistics (Week 14, Priority 2.1)
        team_routing_stats = {}
        if self.team_routing_metrics:
            avg_domain_confidence = sum(m.domain_confidence for m in self.team_routing_metrics) / len(self.team_routing_metrics)
            avg_team_confidence = sum(m.team_confidence for m in self.team_routing_metrics) / len(self.team_routing_metrics)
            avg_routing_time_ms = sum(m.routing_time_ms for m in self.team_routing_metrics) / len(self.team_routing_metrics)

            cache_hits = sum(1 for m in self.team_routing_metrics if m.cache_hit is True)
            cache_hit_rate = (cache_hits / len(self.team_routing_metrics) * 100) if self.team_routing_metrics else 0.0

            team_routing_stats = {
                "total_decisions": len(self.team_routing_metrics),
                "avg_domain_confidence": round(avg_domain_confidence, 3),
                "avg_team_confidence": round(avg_team_confidence, 3),
                "avg_routing_time_ms": round(avg_routing_time_ms, 2),
                "cache_hit_rate": round(cache_hit_rate, 2)
            }

        # Output validation statistics (Week 14, Priority 2.2)
        output_validation_stats = {}
        if self.output_validation_metrics:
            total_validations = len(self.output_validation_metrics)
            passed_validations = sum(1 for m in self.output_validation_metrics if m.passed)
            failed_validations = total_validations - passed_validations
            pass_rate = (passed_validations / total_validations * 100) if total_validations > 0 else 0.0

            # Breakdown by validation type
            validation_type_breakdown = {}
            for metric in self.output_validation_metrics:
                vtype = metric.validation_type
                if vtype not in validation_type_breakdown:
                    validation_type_breakdown[vtype] = {"total": 0, "passed": 0, "failed": 0}
                validation_type_breakdown[vtype]["total"] += 1
                if metric.passed:
                    validation_type_breakdown[vtype]["passed"] += 1
                else:
                    validation_type_breakdown[vtype]["failed"] += 1

            # Average warnings
            total_warnings = sum(m.warning_count for m in self.output_validation_metrics)
            avg_warnings = total_warnings / total_validations if total_validations > 0 else 0.0

            output_validation_stats = {
                "total_validations": total_validations,
                "passed": passed_validations,
                "failed": failed_validations,
                "pass_rate": round(pass_rate, 2),
                "avg_warnings_per_output": round(avg_warnings, 2),
                "validation_type_breakdown": validation_type_breakdown
            }

        return {
            "routing_accuracy": round(routing_accuracy, 2),
            "total_routing_decisions": routing_total,
            "correct_routing_decisions": routing_correct,
            "model_selection_breakdown": model_counts,
            "fallback_usage_rate": round(fallback_rate, 2),
            "team_utilization": team_counts,
            "total_model_selections": len(self.model_metrics),
            "total_team_snapshots": len(self.team_metrics),
            "team_routing_statistics": team_routing_stats,
            "output_validation_statistics": output_validation_stats
        }

    def get_summary(self) -> dict:
        """Get current summary statistics."""
        with self._lock:
            return self._calculate_summary()
