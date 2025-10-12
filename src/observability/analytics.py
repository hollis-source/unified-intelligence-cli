"""Usage analytics utilities for pattern detection and trend analysis.

Provides analytics functions for usage data including:
- Time-series analysis
- Model usage patterns
- Token distribution statistics
- Efficiency metrics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from .entities import UsageEntry, UsagePattern


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""

    timestamp: datetime
    value: int  # tokens or count


@dataclass
class ModelStats:
    """Statistics for a specific model."""

    model_name: str
    provider: str
    total_tokens: int
    total_calls: int
    success_count: int
    failure_count: int
    avg_tokens_per_call: float
    avg_input_tokens: float
    avg_output_tokens: float
    success_rate: float


class UsageAnalytics:
    """Analytics engine for usage data.

    Provides statistical analysis and pattern detection for usage entries.
    """

    @staticmethod
    def get_time_series(
        entries: List[UsageEntry],
        interval: timedelta = timedelta(hours=1),
        metric: str = "tokens"  # "tokens" or "calls"
    ) -> List[TimeSeriesPoint]:
        """Generate time series data from entries.

        Args:
            entries: List of usage entries
            interval: Time interval for aggregation
            metric: Metric to aggregate ("tokens" or "calls")

        Returns:
            List of TimeSeriesPoint objects
        """
        if not entries:
            return []

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda e: e.timestamp)

        # Determine time range
        start_time = sorted_entries[0].timestamp
        end_time = sorted_entries[-1].timestamp

        # Generate time buckets
        points = []
        current = start_time

        while current <= end_time:
            bucket_end = current + interval

            # Filter entries in this bucket
            bucket_entries = [
                e for e in sorted_entries
                if current <= e.timestamp < bucket_end
            ]

            # Calculate value
            if metric == "tokens":
                value = sum(e.total_tokens for e in bucket_entries)
            elif metric == "calls":
                value = len(bucket_entries)
            else:
                raise ValueError(f"Invalid metric: {metric}")

            points.append(TimeSeriesPoint(timestamp=current, value=value))
            current = bucket_end

        return points

    @staticmethod
    def get_model_stats(entries: List[UsageEntry]) -> List[ModelStats]:
        """Calculate statistics per model.

        Args:
            entries: List of usage entries

        Returns:
            List of ModelStats objects
        """
        if not entries:
            return []

        # Group by model
        by_model: Dict[str, List[UsageEntry]] = defaultdict(list)
        for entry in entries:
            by_model[entry.model_name].append(entry)

        # Calculate stats for each model
        stats_list = []
        for model_name, model_entries in by_model.items():
            provider = model_entries[0].provider
            total_tokens = sum(e.total_tokens for e in model_entries)
            total_calls = len(model_entries)
            success_count = sum(1 for e in model_entries if e.success)
            failure_count = total_calls - success_count

            avg_tokens = total_tokens / total_calls
            avg_input = sum(e.input_tokens for e in model_entries) / total_calls
            avg_output = sum(e.output_tokens for e in model_entries) / total_calls
            success_rate = (success_count / total_calls) * 100.0

            stats = ModelStats(
                model_name=model_name,
                provider=provider,
                total_tokens=total_tokens,
                total_calls=total_calls,
                success_count=success_count,
                failure_count=failure_count,
                avg_tokens_per_call=avg_tokens,
                avg_input_tokens=avg_input,
                avg_output_tokens=avg_output,
                success_rate=success_rate,
            )
            stats_list.append(stats)

        # Sort by total tokens (descending)
        stats_list.sort(key=lambda s: s.total_tokens, reverse=True)
        return stats_list

    @staticmethod
    def detect_peak_hours(
        entries: List[UsageEntry],
        threshold_percentile: float = 75.0
    ) -> List[int]:
        """Detect peak usage hours (0-23).

        Args:
            entries: List of usage entries
            threshold_percentile: Percentile threshold for peak detection

        Returns:
            List of peak hours (0-23)
        """
        if not entries:
            return []

        # Count tokens by hour
        tokens_by_hour: Dict[int, int] = defaultdict(int)
        for entry in entries:
            hour = entry.timestamp.hour
            tokens_by_hour[hour] += entry.total_tokens

        # Calculate threshold
        values = list(tokens_by_hour.values())
        if not values:
            return []

        values_sorted = sorted(values)
        threshold_idx = int(len(values_sorted) * threshold_percentile / 100.0)
        threshold = values_sorted[threshold_idx] if threshold_idx < len(values_sorted) else values_sorted[-1]

        # Find peak hours
        peak_hours = [
            hour for hour, tokens in tokens_by_hour.items()
            if tokens >= threshold
        ]
        peak_hours.sort()
        return peak_hours

    @staticmethod
    def detect_model_preferences(
        entries: List[UsageEntry],
        by_agent: bool = True
    ) -> Dict[str, str]:
        """Detect preferred models by agent or project.

        Args:
            entries: List of usage entries
            by_agent: Group by agent if True, by project if False

        Returns:
            Dict mapping agent/project to preferred model
        """
        if not entries:
            return {}

        # Group entries
        groups: Dict[str, List[UsageEntry]] = defaultdict(list)
        for entry in entries:
            key = entry.agent_name if by_agent else entry.project_id
            if key:
                groups[key].append(entry)

        # Find most-used model per group
        preferences = {}
        for key, group_entries in groups.items():
            model_tokens: Dict[str, int] = defaultdict(int)
            for entry in group_entries:
                model_tokens[entry.model_name] += entry.total_tokens

            if model_tokens:
                preferred_model = max(model_tokens.items(), key=lambda x: x[1])[0]
                preferences[key] = preferred_model

        return preferences

    @staticmethod
    def calculate_efficiency_score(entry: UsageEntry) -> float:
        """Calculate efficiency score for an entry.

        Efficiency based on:
        - Tokens per second (if available)
        - Success (1.0 for success, 0.0 for failure)

        Args:
            entry: Usage entry

        Returns:
            Efficiency score (0.0 to 1.0)
        """
        if not entry.success:
            return 0.0

        if entry.duration_ms is None or entry.duration_ms == 0:
            return 0.5  # Neutral if no duration data

        # Calculate tokens per second
        tokens_per_sec = entry.tokens_per_second()

        # Normalize (assume 100 tokens/sec = 1.0 efficiency)
        normalized = min(tokens_per_sec / 100.0, 1.0)

        return normalized

    @staticmethod
    def get_token_distribution(
        entries: List[UsageEntry],
        bins: int = 10
    ) -> List[Tuple[int, int]]:
        """Calculate token usage distribution.

        Args:
            entries: List of usage entries
            bins: Number of bins for histogram

        Returns:
            List of (bin_start, count) tuples
        """
        if not entries:
            return []

        # Get token counts
        token_counts = [e.total_tokens for e in entries]
        min_tokens = min(token_counts)
        max_tokens = max(token_counts)

        if min_tokens == max_tokens:
            return [(min_tokens, len(entries))]

        # Calculate bin width
        bin_width = (max_tokens - min_tokens) / bins

        # Create bins
        distribution = []
        for i in range(bins):
            bin_start = min_tokens + (i * bin_width)
            bin_end = bin_start + bin_width

            # Count entries in bin
            count = sum(
                1 for tokens in token_counts
                if bin_start <= tokens < bin_end or (i == bins - 1 and tokens == max_tokens)
            )

            distribution.append((int(bin_start), count))

        return distribution

    @staticmethod
    def detect_anomalies(
        entries: List[UsageEntry],
        std_threshold: float = 2.0
    ) -> List[UsageEntry]:
        """Detect anomalous usage entries.

        Anomalies are entries with token counts beyond std_threshold
        standard deviations from the mean.

        Args:
            entries: List of usage entries
            std_threshold: Standard deviation threshold

        Returns:
            List of anomalous entries
        """
        if len(entries) < 3:
            return []

        # Calculate mean and std dev
        token_counts = [e.total_tokens for e in entries]
        mean = sum(token_counts) / len(token_counts)
        variance = sum((x - mean) ** 2 for x in token_counts) / len(token_counts)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return []

        # Find anomalies
        anomalies = [
            entry for entry in entries
            if abs(entry.total_tokens - mean) > (std_threshold * std_dev)
        ]

        return anomalies

    @staticmethod
    def generate_usage_patterns(
        entries: List[UsageEntry],
        confidence_threshold: float = 0.75
    ) -> List[UsagePattern]:
        """Generate usage patterns from entries.

        Args:
            entries: List of usage entries
            confidence_threshold: Minimum confidence for patterns

        Returns:
            List of detected UsagePattern objects
        """
        patterns = []

        if not entries:
            return patterns

        # Detect peak hours
        peak_hours = UsageAnalytics.detect_peak_hours(entries)
        if peak_hours:
            patterns.append(UsagePattern(
                pattern_type="peak_usage",
                description=f"Peak usage hours: {', '.join(f'{h}:00' for h in peak_hours)}",
                confidence=0.85,
                data={"peak_hours": peak_hours}
            ))

        # Detect model preferences
        agent_prefs = UsageAnalytics.detect_model_preferences(entries, by_agent=True)
        if agent_prefs:
            patterns.append(UsagePattern(
                pattern_type="model_preference",
                description=f"Agent model preferences detected for {len(agent_prefs)} agents",
                confidence=0.80,
                data={"agent_preferences": agent_prefs}
            ))

        # Detect anomalies
        anomalies = UsageAnalytics.detect_anomalies(entries)
        if anomalies:
            anomaly_ratio = len(anomalies) / len(entries)
            if anomaly_ratio > 0.05:  # More than 5% anomalies
                patterns.append(UsagePattern(
                    pattern_type="anomaly_detected",
                    description=f"{len(anomalies)} anomalous usage entries detected",
                    confidence=0.75,
                    data={
                        "anomaly_count": len(anomalies),
                        "anomaly_ratio": anomaly_ratio
                    }
                ))

        # Filter by confidence
        patterns = [p for p in patterns if p.confidence >= confidence_threshold]

        return patterns
