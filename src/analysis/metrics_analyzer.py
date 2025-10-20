"""
Metrics Trend Analyzer for ATADO

Analyzes historical metrics to detect degrading trends, anomalies, and improvement opportunities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MetricTrend:
    """Trend analysis for a metric."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # improving, degrading, stable
    severity: str  # critical, warning, info
    recommendation: str


@dataclass
class MetricAnomaly:
    """Detected anomaly in a metric."""
    metric_name: str
    timestamp: str
    value: float
    expected_range: Tuple[float, float]
    deviation: float
    severity: str


@dataclass
class MetricsAnalysis:
    """Results of metrics analysis."""
    degrading_metrics: List[MetricTrend]
    improving_metrics: List[MetricTrend]
    anomalies: List[MetricAnomaly]
    correlations: Dict[str, List[str]]  # metric -> correlated metrics
    recommendations: List[str]
    analysis_period_days: int
    timestamp: str


class MetricsAnalyzer:
    """
    Analyzes historical metrics to identify trends and anomalies.
    
    Features:
    - Detect degrading trends (accuracy, latency, cost)
    - Identify anomalies (sudden spikes/drops)
    - Correlate metrics with code changes
    - Generate improvement recommendations
    """
    
    # Metric thresholds for severity
    THRESHOLDS = {
        'routing_accuracy': {'critical': 0.80, 'warning': 0.85},
        'p95_latency_ms': {'critical': 1000.0, 'warning': 750.0},
        'cost_per_task': {'critical': 0.20, 'warning': 0.15},
        'error_rate': {'critical': 0.10, 'warning': 0.05},
    }
    
    def __init__(self, db_store: Optional[any] = None):
        """
        Initialize metrics analyzer.
        
        Args:
            db_store: Database store for retrieving historical metrics
        """
        self.db_store = db_store
    
    async def analyze(self, days: int = 30) -> MetricsAnalysis:
        """
        Analyze metrics for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            MetricsAnalysis with trends, anomalies, and recommendations
        """
        # Get historical metrics
        metrics_history = await self._get_metrics_history(days)
        
        if not metrics_history:
            logger.warning("No metrics history available")
            return self._empty_analysis(days)
        
        # Analyze trends
        degrading, improving = self._analyze_trends(metrics_history)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(metrics_history)
        
        # Find correlations
        correlations = self._find_correlations(metrics_history)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(degrading, anomalies)
        
        return MetricsAnalysis(
            degrading_metrics=degrading,
            improving_metrics=improving,
            anomalies=anomalies,
            correlations=correlations,
            recommendations=recommendations,
            analysis_period_days=days,
            timestamp=datetime.now(UTC).isoformat()
        )
    
    async def _get_metrics_history(self, days: int) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get historical metrics from database.
        
        Returns:
            Dict of metric_name -> [(timestamp, value), ...]
        """
        if not self.db_store:
            # Return mock data for testing
            return self._get_mock_metrics(days)
        
        # In production, query from SurrealDB
        # For now, return mock data
        return self._get_mock_metrics(days)
    
    def _get_mock_metrics(self, days: int) -> Dict[str, List[Tuple[str, float]]]:
        """Generate mock metrics for testing."""
        metrics = {}
        
        # Generate daily data points
        for metric_name in ['routing_accuracy', 'p95_latency_ms', 'cost_per_task', 'error_rate']:
            data = []
            for i in range(days):
                timestamp = (datetime.now() - timedelta(days=days-i)).isoformat()
                
                # Generate realistic values with trends
                if metric_name == 'routing_accuracy':
                    value = 0.75 - (i * 0.001)  # Slight degradation
                elif metric_name == 'p95_latency_ms':
                    value = 500 + (i * 5)  # Increasing latency
                elif metric_name == 'cost_per_task':
                    value = 0.10 + (i * 0.001)  # Increasing cost
                else:  # error_rate
                    value = 0.05 + np.random.normal(0, 0.01)  # Stable with noise
                
                data.append((timestamp, max(0, value)))
            
            metrics[metric_name] = data
        
        return metrics
    
    def _analyze_trends(
        self,
        metrics_history: Dict[str, List[Tuple[str, float]]]
    ) -> Tuple[List[MetricTrend], List[MetricTrend]]:
        """Analyze metric trends."""
        degrading = []
        improving = []
        
        for metric_name, data in metrics_history.items():
            if len(data) < 2:
                continue
            
            # Get current and previous values (average of last 7 days vs previous 7 days)
            current_values = [v for _, v in data[-7:]]
            previous_values = [v for _, v in data[-14:-7]] if len(data) >= 14 else [v for _, v in data[:-7]]
            
            if not previous_values:
                continue
            
            current_avg = np.mean(current_values)
            previous_avg = np.mean(previous_values)
            
            # Calculate change
            change_percent = ((current_avg - previous_avg) / previous_avg * 100) if previous_avg != 0 else 0
            
            # Determine trend direction (depends on metric type)
            is_lower_better = metric_name in ['p95_latency_ms', 'cost_per_task', 'error_rate']
            
            if is_lower_better:
                trend = 'improving' if change_percent < -5 else 'degrading' if change_percent > 5 else 'stable'
            else:
                trend = 'improving' if change_percent > 5 else 'degrading' if change_percent < -5 else 'stable'
            
            # Determine severity
            severity = self._determine_severity(metric_name, current_avg)
            
            # Generate recommendation
            recommendation = self._generate_metric_recommendation(metric_name, trend, change_percent)
            
            metric_trend = MetricTrend(
                metric_name=metric_name,
                current_value=current_avg,
                previous_value=previous_avg,
                change_percent=change_percent,
                trend=trend,
                severity=severity,
                recommendation=recommendation
            )
            
            if trend == 'degrading':
                degrading.append(metric_trend)
            elif trend == 'improving':
                improving.append(metric_trend)
        
        return degrading, improving
    
    def _detect_anomalies(
        self,
        metrics_history: Dict[str, List[Tuple[str, float]]]
    ) -> List[MetricAnomaly]:
        """Detect anomalies using statistical methods."""
        anomalies = []
        
        for metric_name, data in metrics_history.items():
            if len(data) < 7:
                continue
            
            values = [v for _, v in data]
            
            # Calculate mean and std dev
            mean = np.mean(values)
            std = np.std(values)
            
            # Detect outliers (>2 std devs from mean)
            for timestamp, value in data[-7:]:  # Check last 7 days
                deviation = abs(value - mean) / std if std > 0 else 0
                
                if deviation > 2.0:
                    expected_range = (mean - 2*std, mean + 2*std)
                    severity = 'critical' if deviation > 3.0 else 'warning'
                    
                    anomalies.append(MetricAnomaly(
                        metric_name=metric_name,
                        timestamp=timestamp,
                        value=value,
                        expected_range=expected_range,
                        deviation=deviation,
                        severity=severity
                    ))
        
        return anomalies
    
    def _find_correlations(
        self,
        metrics_history: Dict[str, List[Tuple[str, float]]]
    ) -> Dict[str, List[str]]:
        """Find correlated metrics."""
        correlations = {}
        
        metric_names = list(metrics_history.keys())
        
        for i, metric1 in enumerate(metric_names):
            correlated = []
            values1 = [v for _, v in metrics_history[metric1]]
            
            for metric2 in metric_names[i+1:]:
                values2 = [v for _, v in metrics_history[metric2]]
                
                # Calculate correlation (simple Pearson)
                if len(values1) == len(values2) and len(values1) > 1:
                    corr = np.corrcoef(values1, values2)[0, 1]
                    
                    if abs(corr) > 0.7:  # Strong correlation
                        correlated.append(metric2)
            
            if correlated:
                correlations[metric1] = correlated
        
        return correlations
    
    def _determine_severity(self, metric_name: str, value: float) -> str:
        """Determine severity based on thresholds."""
        if metric_name not in self.THRESHOLDS:
            return 'info'
        
        thresholds = self.THRESHOLDS[metric_name]
        
        # For metrics where lower is better
        if metric_name in ['p95_latency_ms', 'cost_per_task', 'error_rate']:
            if value >= thresholds['critical']:
                return 'critical'
            elif value >= thresholds['warning']:
                return 'warning'
        else:  # For metrics where higher is better
            if value <= thresholds['critical']:
                return 'critical'
            elif value <= thresholds['warning']:
                return 'warning'
        
        return 'info'
    
    def _generate_metric_recommendation(self, metric_name: str, trend: str, change_percent: float) -> str:
        """Generate recommendation for a metric."""
        if trend == 'stable':
            return f"Monitor {metric_name} - currently stable"
        
        if metric_name == 'routing_accuracy' and trend == 'degrading':
            return f"Routing accuracy degraded by {abs(change_percent):.1f}% - review pattern quality and collect more training data"
        elif metric_name == 'p95_latency_ms' and trend == 'degrading':
            return f"Latency increased by {abs(change_percent):.1f}% - optimize routing logic and consider caching"
        elif metric_name == 'cost_per_task' and trend == 'degrading':
            return f"Cost increased by {abs(change_percent):.1f}% - review model selection and consider cheaper alternatives"
        elif metric_name == 'error_rate' and trend == 'degrading':
            return f"Error rate increased by {abs(change_percent):.1f}% - investigate recent failures and add error handling"
        else:
            return f"{metric_name} {trend} by {abs(change_percent):.1f}%"
    
    def _generate_recommendations(
        self,
        degrading_metrics: List[MetricTrend],
        anomalies: List[MetricAnomaly]
    ) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        # Recommendations based on degrading metrics
        for metric in degrading_metrics:
            if metric.severity in ['critical', 'warning']:
                recommendations.append(metric.recommendation)
        
        # Recommendations based on anomalies
        if anomalies:
            critical_anomalies = [a for a in anomalies if a.severity == 'critical']
            if critical_anomalies:
                recommendations.append(f"Investigate {len(critical_anomalies)} critical anomalies detected")
        
        return recommendations[:10]  # Top 10
    
    def _empty_analysis(self, days: int) -> MetricsAnalysis:
        """Return empty analysis when no data available."""
        return MetricsAnalysis(
            degrading_metrics=[],
            improving_metrics=[],
            anomalies=[],
            correlations={},
            recommendations=[],
            analysis_period_days=days,
            timestamp=datetime.now(UTC).isoformat()
        )

