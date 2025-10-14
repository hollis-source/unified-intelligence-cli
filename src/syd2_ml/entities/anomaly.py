"""Anomaly Entity.

Represents an ML-detected anomaly in SYD2 metrics.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for anomaly representation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from datetime import datetime


class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies."""

    LOW = "low"  # Minor deviation, informational
    MEDIUM = "medium"  # Moderate concern, monitor
    HIGH = "high"  # Significant issue, investigate
    CRITICAL = "critical"  # Urgent action required


class AnomalyType(str, Enum):
    """Types of anomalies detected by ML models."""

    LATENCY_SPIKE = "latency_spike"  # Unusual increase in latency
    FAILURE_PATTERN = "failure_pattern"  # Unexpected failure cluster
    PERFORMANCE_DEGRADATION = "performance_degradation"  # Gradual decline
    OUTLIER = "outlier"  # Statistical outlier
    TEMPORAL_ANOMALY = "temporal_anomaly"  # Time-based pattern break
    ROUTING_ANOMALY = "routing_anomaly"  # Routing behavior anomaly
    UNKNOWN = "unknown"  # Unclassified anomaly


@dataclass(frozen=True)
class Anomaly:
    """
    Represents an ML-detected anomaly in SYD2 system.

    Immutable design ensures anomalies are not modified after detection.
    Can be stored, logged, and analyzed without concern for mutation.

    Example:
        anomaly = Anomaly.create(
            task_id="task_123",
            anomaly_type=AnomalyType.LATENCY_SPIKE,
            severity=AnomalySeverity.HIGH,
            score=0.95,
            description="Latency 3.2x higher than normal baseline",
            features={"latency_ms": 5000, "expected_ms": 1560}
        )
    """

    # Identifiers
    task_id: str
    timestamp: datetime

    # Anomaly classification
    anomaly_type: AnomalyType
    severity: AnomalySeverity

    # Detection details
    anomaly_score: float  # 0.0-1.0, higher = more anomalous
    model_name: str  # e.g., "isolation_forest_v1", "autoencoder_v2"
    model_confidence: float  # 0.0-1.0, model's confidence in detection

    # Context
    description: str
    detected_features: Dict[str, float]  # Features that triggered anomaly
    expected_range: Optional[Dict[str, tuple[float, float]]] = None  # Expected min/max

    # Related data
    related_task_ids: list[str] = None  # Other tasks in same anomaly cluster
    root_cause_hypothesis: Optional[str] = None  # ML model's guess at cause

    # Metadata
    detection_timestamp: datetime = None  # When anomaly was detected
    detector_version: str = "1.0"

    def __post_init__(self):
        """Set detection timestamp if not provided."""
        if self.detection_timestamp is None:
            object.__setattr__(self, "detection_timestamp", datetime.now())
        if self.related_task_ids is None:
            object.__setattr__(self, "related_task_ids", [])

    @staticmethod
    def create(
        task_id: str,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        score: float,
        description: str,
        features: Dict[str, float],
        model_name: str = "ml_detector",
        confidence: float = 0.8,
        expected_range: Optional[Dict[str, tuple[float, float]]] = None,
        related_tasks: Optional[list[str]] = None,
        root_cause: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> "Anomaly":
        """
        Factory method to create Anomaly with validation.

        Args:
            task_id: ID of task with anomaly
            anomaly_type: Type of anomaly detected
            severity: Severity level
            score: Anomaly score (0.0-1.0)
            description: Human-readable description
            features: Dict of feature values that triggered detection
            model_name: Name of detection model
            confidence: Model confidence (0.0-1.0)
            expected_range: Expected value ranges for features
            related_tasks: List of related task IDs in cluster
            root_cause: Hypothesis about root cause
            timestamp: Timestamp of anomalous task

        Returns:
            Anomaly instance

        Raises:
            ValueError: If score or confidence not in [0, 1]
        """
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"Anomaly score must be in [0, 1], got {score}")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence must be in [0, 1], got {confidence}")

        return Anomaly(
            task_id=task_id,
            timestamp=timestamp or datetime.now(),
            anomaly_type=anomaly_type,
            severity=severity,
            anomaly_score=score,
            model_name=model_name,
            model_confidence=confidence,
            description=description,
            detected_features=features,
            expected_range=expected_range,
            related_task_ids=related_tasks or [],
            root_cause_hypothesis=root_cause,
        )

    def to_dict(self) -> Dict:
        """Convert anomaly to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "anomaly_score": self.anomaly_score,
            "model_name": self.model_name,
            "model_confidence": self.model_confidence,
            "description": self.description,
            "detected_features": self.detected_features,
            "expected_range": self.expected_range,
            "related_task_ids": self.related_task_ids,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "detection_timestamp": self.detection_timestamp.isoformat(),
            "detector_version": self.detector_version,
        }

    def is_critical(self) -> bool:
        """Check if anomaly requires immediate attention."""
        return self.severity == AnomalySeverity.CRITICAL

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if model is highly confident in detection."""
        return self.model_confidence >= threshold
