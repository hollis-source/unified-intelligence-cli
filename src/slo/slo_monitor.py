"""SLO Monitor - Real-time SLO compliance monitoring.

Tracks SLO metrics, detects violations, and triggers alerts.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for SLO monitoring
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque

from src.slo.slo_definitions import (
    SLODefinitions,
    SLOTarget,
    SLOViolation,
    SLOStatus,
    SLOSeverity,
)

logger = logging.getLogger(__name__)


class SLOMonitor:
    """
    Real-time SLO compliance monitor.
    
    Features:
    - Continuous metric tracking
    - Violation detection
    - Alert triggering
    - Historical tracking
    - Compliance reporting
    
    Usage:
        monitor = SLOMonitor()
        monitor.record_metric("p95_latency_ms", 450.0)
        violations = monitor.check_violations()
    """
    
    def __init__(
        self,
        window_size: int = 100,  # Number of samples to keep
        violation_threshold_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize SLO monitor.
        
        Args:
            window_size: Number of metric samples to keep in memory
            violation_threshold_seconds: Seconds before triggering alert
        """
        self.window_size = window_size
        self.violation_threshold_seconds = violation_threshold_seconds
        
        # Metric history: metric_name -> deque of (timestamp, value)
        self.metric_history: Dict[str, deque] = {}
        
        # Active violations: slo_name -> SLOViolation
        self.active_violations: Dict[str, SLOViolation] = {}
        
        # Violation history
        self.violation_history: List[SLOViolation] = []
        
        # Statistics
        self.total_checks = 0
        self.total_violations = 0
        self.total_warnings = 0
    
    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """
        Record a metric value.
        
        Args:
            metric_name: Name of metric (e.g., "p95_latency_ms")
            value: Metric value
            timestamp: Optional timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Initialize deque if needed
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = deque(maxlen=self.window_size)
        
        # Add to history
        self.metric_history[metric_name].append((timestamp, value))
        
        logger.debug(f"Recorded metric: {metric_name}={value}")
    
    def get_current_metrics(self) -> Dict[str, float]:
        """
        Get current metric values (latest from each metric).
        
        Returns:
            Dict of metric_name -> latest_value
        """
        metrics = {}
        
        for metric_name, history in self.metric_history.items():
            if history:
                _, latest_value = history[-1]
                metrics[metric_name] = latest_value
        
        return metrics
    
    def get_aggregated_metrics(self, window_minutes: int = 5) -> Dict[str, float]:
        """
        Get aggregated metrics over time window.
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            Dict of metric_name -> aggregated_value (mean)
        """
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        metrics = {}
        
        for metric_name, history in self.metric_history.items():
            # Filter to window
            recent_values = [
                value for timestamp, value in history
                if timestamp >= cutoff_time
            ]
            
            if recent_values:
                # Use mean for aggregation
                metrics[metric_name] = sum(recent_values) / len(recent_values)
        
        return metrics
    
    def check_violations(self, use_aggregated: bool = True) -> List[SLOViolation]:
        """
        Check for SLO violations.
        
        Args:
            use_aggregated: Use aggregated metrics (5-min window) vs latest
            
        Returns:
            List of current SLOViolation objects
        """
        self.total_checks += 1
        
        # Get metrics
        if use_aggregated:
            metrics = self.get_aggregated_metrics(window_minutes=5)
        else:
            metrics = self.get_current_metrics()
        
        if not metrics:
            return []
        
        # Check all SLOs
        violations = SLODefinitions.check_all_slos(metrics)
        
        # Update statistics
        for violation in violations:
            if violation.status == SLOStatus.VIOLATED:
                self.total_violations += 1
            elif violation.status == SLOStatus.WARNING:
                self.total_warnings += 1
        
        # Update active violations
        self._update_active_violations(violations)
        
        return violations
    
    def _update_active_violations(self, violations: List[SLOViolation]):
        """Update active violations and trigger alerts if needed."""
        current_time = datetime.now()
        
        # Track which SLOs are currently violated
        violated_slos = {v.slo_name for v in violations if v.status == SLOStatus.VIOLATED}
        
        # Check for new violations
        for violation in violations:
            if violation.status != SLOStatus.VIOLATED:
                continue
            
            slo_name = violation.slo_name
            
            if slo_name not in self.active_violations:
                # New violation
                violation.timestamp = current_time.isoformat()
                violation.duration_seconds = 0
                self.active_violations[slo_name] = violation
                logger.warning(f"NEW SLO VIOLATION: {slo_name} - {violation.description}")
            
            else:
                # Existing violation - update duration
                existing = self.active_violations[slo_name]
                start_time = datetime.fromisoformat(existing.timestamp)
                duration = (current_time - start_time).total_seconds()
                existing.duration_seconds = int(duration)
                existing.actual_value = violation.actual_value  # Update value
                
                # Check if violation duration exceeds threshold
                if duration >= self.violation_threshold_seconds:
                    logger.error(
                        f"SUSTAINED SLO VIOLATION: {slo_name} for {duration:.0f}s "
                        f"(threshold: {self.violation_threshold_seconds}s)"
                    )
        
        # Clear resolved violations
        resolved_slos = set(self.active_violations.keys()) - violated_slos
        for slo_name in resolved_slos:
            violation = self.active_violations.pop(slo_name)
            self.violation_history.append(violation)
            logger.info(f"SLO VIOLATION RESOLVED: {slo_name} after {violation.duration_seconds}s")
    
    def get_active_violations(self) -> List[SLOViolation]:
        """Get currently active violations."""
        return list(self.active_violations.values())
    
    def get_critical_violations(self) -> List[SLOViolation]:
        """Get active critical violations."""
        return [
            v for v in self.active_violations.values()
            if v.severity == SLOSeverity.CRITICAL
        ]
    
    def should_trigger_rollback(self) -> bool:
        """
        Determine if automatic rollback should be triggered.
        
        Triggers rollback if:
        - Any critical SLO violated for >5 minutes
        - Multiple high-severity SLOs violated
        
        Returns:
            True if rollback should be triggered
        """
        critical_violations = self.get_critical_violations()
        
        # Check for sustained critical violations
        for violation in critical_violations:
            if violation.duration_seconds and violation.duration_seconds >= self.violation_threshold_seconds:
                logger.critical(
                    f"ROLLBACK TRIGGER: Critical SLO {violation.slo_name} violated for "
                    f"{violation.duration_seconds}s (threshold: {self.violation_threshold_seconds}s)"
                )
                return True
        
        # Check for multiple high-severity violations
        high_violations = [
            v for v in self.active_violations.values()
            if v.severity in [SLOSeverity.CRITICAL, SLOSeverity.HIGH]
        ]
        
        if len(high_violations) >= 3:
            logger.critical(f"ROLLBACK TRIGGER: {len(high_violations)} high-severity SLO violations")
            return True
        
        return False
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """
        Generate SLO compliance report.
        
        Returns:
            Report dict with compliance statistics
        """
        metrics = self.get_aggregated_metrics(window_minutes=5)
        summary = SLODefinitions.get_slo_summary(metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "compliance_summary": summary,
            "active_violations": [
                {
                    "slo": v.slo_name,
                    "metric": v.metric,
                    "target": v.target_value,
                    "actual": v.actual_value,
                    "severity": v.severity.value,
                    "duration_seconds": v.duration_seconds,
                }
                for v in self.active_violations.values()
            ],
            "statistics": {
                "total_checks": self.total_checks,
                "total_violations": self.total_violations,
                "total_warnings": self.total_warnings,
                "violation_rate": self.total_violations / max(1, self.total_checks),
            },
        }
    
    def reset_statistics(self):
        """Reset monitoring statistics."""
        self.total_checks = 0
        self.total_violations = 0
        self.total_warnings = 0
        logger.info("SLO monitor statistics reset")

