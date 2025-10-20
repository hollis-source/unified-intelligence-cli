"""Metric Features Entity.

Represents engineered features extracted from raw SYD2 metrics
for ML model consumption.

Clean Architecture: Core entity (immutable, no dependencies)
SOLID: SRP - single responsibility for feature representation
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass(frozen=True)
class MetricFeatures:
    """
    Engineered features from SYD2 metrics for ML models.

    Features include:
    - Temporal: hour_of_day, day_of_week, is_weekend
    - Performance: latency, success_rate_window, latency_percentiles
    - Categorical: category (encoded), error_type (encoded)
    - Derived: latency_zscore, failure_streak, recent_success_rate

    Immutable design prevents accidental modification during training.
    """

    # Raw identifiers
    task_id: str
    timestamp: datetime

    # Temporal features
    hour_of_day: int  # 0-23
    day_of_week: int  # 0-6 (Monday=0)
    is_weekend: bool

    # Performance features
    latency_ms: float
    is_success: bool

    # Categorical features (one-hot encoded)
    category_encoded: Dict[str, float]  # e.g., {"agent_creation": 1.0, ...}
    error_type_encoded: Optional[Dict[str, float]] = None

    # Derived/statistical features
    latency_zscore: Optional[float] = None  # Z-score relative to recent window
    success_rate_recent_10: Optional[float] = None  # Success rate in last 10 tasks
    failure_streak: int = 0  # Consecutive failures before this task

    # Context features
    routing_team: Optional[str] = None
    routing_confidence: Optional[float] = None

    # Metadata
    feature_version: str = "1.0"  # For model versioning

    @staticmethod
    def from_metric(
        metric: Dict,
        window_stats: Optional[Dict] = None,
        failure_streak: int = 0
    ) -> "MetricFeatures":
        """
        Create MetricFeatures from raw SYD2 metric.

        Args:
            metric: Raw metric dict with keys: task_id, timestamp, category,
                   success, latency, routing_info, error_type
            window_stats: Statistical context from recent metrics window
            failure_streak: Number of consecutive failures before this task

        Returns:
            MetricFeatures instance
        """
        timestamp = datetime.fromisoformat(metric["timestamp"])

        # Temporal features
        hour_of_day = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = day_of_week >= 5

        # Category encoding (one-hot)
        categories = [
            "agent_creation", "dsl_workflow", "model_fallback",
            "code_analysis", "testing", "deployment", "other"
        ]
        category = metric.get("category", "other")
        category_encoded = {cat: 1.0 if cat == category else 0.0 for cat in categories}

        # Error type encoding (if failure)
        error_type_encoded = None
        if not metric["success"] and metric.get("error_type"):
            error_types = ["timeout", "ssh_error", "parsing_error", "execution_error", "other_error"]
            error_type = metric["error_type"]
            error_type_encoded = {et: 1.0 if et == error_type else 0.0 for et in error_types}

        # Derived features from window stats
        latency_zscore = None
        success_rate_recent = None
        if window_stats:
            latency_mean = window_stats.get("latency_mean", metric["latency"])
            latency_std = window_stats.get("latency_std", 1.0)
            latency_zscore = (metric["latency"] - latency_mean) / latency_std if latency_std > 0 else 0.0

            success_rate_recent = window_stats.get("success_rate", None)

        # Routing features
        routing_team = None
        routing_confidence = None
        if metric.get("routing_info"):
            routing_team = metric["routing_info"].get("team")
            routing_confidence = metric["routing_info"].get("confidence")

        return MetricFeatures(
            task_id=metric["task_id"],
            timestamp=timestamp,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            latency_ms=metric["latency"],
            is_success=metric["success"],
            category_encoded=category_encoded,
            error_type_encoded=error_type_encoded,
            latency_zscore=latency_zscore,
            success_rate_recent_10=success_rate_recent,
            failure_streak=failure_streak,
            routing_team=routing_team,
            routing_confidence=routing_confidence,
        )

    def to_vector(self) -> list[float]:
        """
        Convert features to numerical vector for ML models.

        Returns:
            List of float values ready for sklearn/numpy
        """
        vector = [
            # Temporal (3 features)
            float(self.hour_of_day) / 24.0,  # Normalize to [0, 1]
            float(self.day_of_week) / 7.0,
            float(self.is_weekend),

            # Performance (2 features)
            self.latency_ms,
            float(self.is_success),

            # Categorical - category (7 features)
            *self.category_encoded.values(),
        ]

        # Error type (5 features, optional)
        if self.error_type_encoded:
            vector.extend(self.error_type_encoded.values())
        else:
            vector.extend([0.0] * 5)

        # Derived features (3 features)
        vector.extend([
            self.latency_zscore or 0.0,
            self.success_rate_recent_10 or 1.0,
            float(self.failure_streak),
        ])

        # Routing features (1 feature)
        vector.append(self.routing_confidence or 0.5)

        return vector

    @staticmethod
    def feature_names() -> list[str]:
        """Return feature names matching to_vector() order."""
        names = [
            "hour_of_day_norm",
            "day_of_week_norm",
            "is_weekend",
            "latency_ms",
            "is_success",
        ]

        # Category one-hot
        categories = [
            "cat_agent_creation", "cat_dsl_workflow", "cat_model_fallback",
            "cat_code_analysis", "cat_testing", "cat_deployment", "cat_other"
        ]
        names.extend(categories)

        # Error type one-hot
        error_types = [
            "err_timeout", "err_ssh_error", "err_parsing_error",
            "err_execution_error", "err_other_error"
        ]
        names.extend(error_types)

        # Derived features
        names.extend([
            "latency_zscore",
            "success_rate_recent_10",
            "failure_streak",
            "routing_confidence",
        ])

        return names
