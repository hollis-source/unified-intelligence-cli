"""SLO Definitions - Service Level Objectives for ATADO.

Defines SLOs for latency, accuracy, cost, and availability.
Provides validation and compliance checking.

Clean Architecture: Entities layer
SOLID: SRP - Single responsibility for SLO definitions
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class SLOStatus(Enum):
    """SLO compliance status."""
    COMPLIANT = "compliant"  # Within SLO
    WARNING = "warning"  # Approaching violation (80-100%)
    VIOLATED = "violated"  # SLO violated


class SLOSeverity(Enum):
    """SLO violation severity."""
    CRITICAL = "critical"  # P0 - immediate action required
    HIGH = "high"  # P1 - action required within 1 hour
    MEDIUM = "medium"  # P2 - action required within 4 hours
    LOW = "low"  # P3 - action required within 24 hours


@dataclass
class SLOTarget:
    """A single SLO target."""
    name: str
    metric: str  # e.g., "p95_latency_ms", "accuracy", "cost_per_task"
    target_value: float
    comparison: str  # "lt" (less than), "gt" (greater than), "eq" (equal)
    warning_threshold: float  # Percentage of target (e.g., 0.8 = 80%)
    severity: SLOSeverity
    description: str
    
    def check_compliance(self, actual_value: float) -> SLOStatus:
        """
        Check if actual value meets SLO target.
        
        Args:
            actual_value: Actual measured value
            
        Returns:
            SLOStatus (COMPLIANT, WARNING, or VIOLATED)
        """
        if self.comparison == "lt":
            # Lower is better (e.g., latency, cost)
            if actual_value <= self.target_value:
                return SLOStatus.COMPLIANT
            elif actual_value <= self.target_value / self.warning_threshold:
                return SLOStatus.WARNING
            else:
                return SLOStatus.VIOLATED
        
        elif self.comparison == "gt":
            # Higher is better (e.g., accuracy, availability)
            if actual_value >= self.target_value:
                return SLOStatus.COMPLIANT
            elif actual_value >= self.target_value * self.warning_threshold:
                return SLOStatus.WARNING
            else:
                return SLOStatus.VIOLATED
        
        elif self.comparison == "eq":
            # Equal is best
            tolerance = self.target_value * (1 - self.warning_threshold)
            if abs(actual_value - self.target_value) <= tolerance:
                return SLOStatus.COMPLIANT
            else:
                return SLOStatus.VIOLATED
        
        return SLOStatus.VIOLATED


@dataclass
class SLOViolation:
    """Record of an SLO violation."""
    slo_name: str
    metric: str
    target_value: float
    actual_value: float
    status: SLOStatus
    severity: SLOSeverity
    timestamp: str
    duration_seconds: Optional[int] = None
    description: str = ""


class SLODefinitions:
    """
    Standard SLO definitions for ATADO.
    
    Targets:
    - P95 latency: <500ms (critical)
    - P99 latency: <1000ms (high)
    - Accuracy: >85% (critical)
    - Cost per task: <$0.10 (medium)
    - Availability: >99.5% (critical)
    - Error rate: <5% (high)
    """
    
    # Standard SLO targets
    LATENCY_P95_MS = SLOTarget(
        name="latency_p95",
        metric="p95_latency_ms",
        target_value=500.0,
        comparison="lt",
        warning_threshold=0.8,  # Warn at 400ms (80% of 500ms)
        severity=SLOSeverity.CRITICAL,
        description="95th percentile latency must be under 500ms",
    )
    
    LATENCY_P99_MS = SLOTarget(
        name="latency_p99",
        metric="p99_latency_ms",
        target_value=1000.0,
        comparison="lt",
        warning_threshold=0.8,  # Warn at 800ms
        severity=SLOSeverity.HIGH,
        description="99th percentile latency must be under 1000ms",
    )
    
    ACCURACY_PCT = SLOTarget(
        name="accuracy",
        metric="accuracy_pct",
        target_value=85.0,
        comparison="gt",
        warning_threshold=0.9,  # Warn at 76.5% (90% of 85%)
        severity=SLOSeverity.CRITICAL,
        description="Task accuracy must be above 85%",
    )
    
    COST_PER_TASK = SLOTarget(
        name="cost_per_task",
        metric="cost_usd",
        target_value=0.10,
        comparison="lt",
        warning_threshold=0.8,  # Warn at $0.08
        severity=SLOSeverity.MEDIUM,
        description="Cost per task must be under $0.10",
    )
    
    AVAILABILITY_PCT = SLOTarget(
        name="availability",
        metric="availability_pct",
        target_value=99.5,
        comparison="gt",
        warning_threshold=0.995,  # Warn at 99.0%
        severity=SLOSeverity.CRITICAL,
        description="System availability must be above 99.5%",
    )
    
    ERROR_RATE_PCT = SLOTarget(
        name="error_rate",
        metric="error_rate_pct",
        target_value=5.0,
        comparison="lt",
        warning_threshold=0.8,  # Warn at 4%
        severity=SLOSeverity.HIGH,
        description="Error rate must be under 5%",
    )
    
    @classmethod
    def get_all_slos(cls) -> List[SLOTarget]:
        """Get all standard SLO targets."""
        return [
            cls.LATENCY_P95_MS,
            cls.LATENCY_P99_MS,
            cls.ACCURACY_PCT,
            cls.COST_PER_TASK,
            cls.AVAILABILITY_PCT,
            cls.ERROR_RATE_PCT,
        ]
    
    @classmethod
    def get_slo_by_name(cls, name: str) -> Optional[SLOTarget]:
        """Get SLO target by name."""
        slo_map = {
            "latency_p95": cls.LATENCY_P95_MS,
            "latency_p99": cls.LATENCY_P99_MS,
            "accuracy": cls.ACCURACY_PCT,
            "cost_per_task": cls.COST_PER_TASK,
            "availability": cls.AVAILABILITY_PCT,
            "error_rate": cls.ERROR_RATE_PCT,
        }
        return slo_map.get(name)
    
    @classmethod
    def check_all_slos(cls, metrics: Dict[str, float]) -> List[SLOViolation]:
        """
        Check all SLOs against current metrics.
        
        Args:
            metrics: Dict of metric_name -> value
            
        Returns:
            List of SLOViolation objects (empty if all compliant)
        """
        violations = []
        
        for slo in cls.get_all_slos():
            if slo.metric not in metrics:
                continue
            
            actual_value = metrics[slo.metric]
            status = slo.check_compliance(actual_value)
            
            if status in [SLOStatus.WARNING, SLOStatus.VIOLATED]:
                violation = SLOViolation(
                    slo_name=slo.name,
                    metric=slo.metric,
                    target_value=slo.target_value,
                    actual_value=actual_value,
                    status=status,
                    severity=slo.severity,
                    timestamp="",  # Set by caller
                    description=slo.description,
                )
                violations.append(violation)
        
        return violations
    
    @classmethod
    def get_slo_summary(cls, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Get summary of SLO compliance.
        
        Args:
            metrics: Dict of metric_name -> value
            
        Returns:
            Summary dict with compliance stats
        """
        violations = cls.check_all_slos(metrics)
        
        total_slos = len(cls.get_all_slos())
        violated_count = sum(1 for v in violations if v.status == SLOStatus.VIOLATED)
        warning_count = sum(1 for v in violations if v.status == SLOStatus.WARNING)
        compliant_count = total_slos - violated_count - warning_count
        
        return {
            "total_slos": total_slos,
            "compliant": compliant_count,
            "warnings": warning_count,
            "violations": violated_count,
            "compliance_rate": compliant_count / total_slos if total_slos > 0 else 0.0,
            "violation_details": [
                {
                    "slo": v.slo_name,
                    "metric": v.metric,
                    "target": v.target_value,
                    "actual": v.actual_value,
                    "status": v.status.value,
                    "severity": v.severity.value,
                }
                for v in violations
            ],
        }


# Convenience functions
def check_slo_compliance(metrics: Dict[str, float]) -> bool:
    """Check if all SLOs are compliant (no violations)."""
    violations = SLODefinitions.check_all_slos(metrics)
    return all(v.status != SLOStatus.VIOLATED for v in violations)


def get_critical_violations(metrics: Dict[str, float]) -> List[SLOViolation]:
    """Get only critical SLO violations."""
    violations = SLODefinitions.check_all_slos(metrics)
    return [
        v for v in violations
        if v.severity == SLOSeverity.CRITICAL and v.status == SLOStatus.VIOLATED
    ]

