"""Alert domain entities.

Entities for error alerting and notification:
- Alert: Individual alert record
- AlertRule: Configurable alert condition
- AlertSeverity: Alert severity levels

All entities are immutable (frozen dataclasses) following Clean Architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import uuid


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"  # System-wide failure, immediate action required
    ERROR = "error"  # Error condition, prompt action needed
    WARNING = "warning"  # Warning condition, investigation recommended
    INFO = "info"  # Informational alert, no action required


@dataclass(frozen=True)
class Alert:
    """Individual alert record.

    Immutable entity tracking a single alert event.
    Records severity, source, message, and acknowledgment status.
    """

    id: str
    severity: AlertSeverity
    message: str
    source: str  # e.g., "usage_tracker", "cost_tracker", "tracer"
    timestamp: datetime

    # Acknowledgment tracking
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    # Rule association
    rule_id: Optional[str] = None  # Link to AlertRule if triggered by rule

    # Context metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate alert data."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Alert ID cannot be empty")

        # Validate message
        if not self.message or not self.message.strip():
            raise ValueError("Alert message cannot be empty")

        # Validate source
        if not self.source or not self.source.strip():
            raise ValueError("Alert source cannot be empty")

        # Validate severity
        if not isinstance(self.severity, AlertSeverity):
            raise ValueError(f"Invalid severity: {self.severity}")

        # Validate acknowledgment consistency
        if self.acknowledged and self.acknowledged_at is None:
            raise ValueError("Acknowledged alert must have acknowledged_at timestamp")

        if self.acknowledged_at is not None and not self.acknowledged:
            raise ValueError("Alert with acknowledged_at must be marked as acknowledged")

    @staticmethod
    def create(
        severity: AlertSeverity,
        message: str,
        source: str,
        rule_id: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> "Alert":
        """Factory method to create an alert with generated ID.

        Args:
            severity: Alert severity level
            message: Alert message
            source: Alert source (e.g., "cost_tracker")
            rule_id: Optional rule ID if triggered by rule
            metadata: Optional context metadata

        Returns:
            New Alert with generated ID
        """
        return Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            message=message,
            source=source,
            timestamp=datetime.now(),
            acknowledged=False,
            rule_id=rule_id,
            metadata=metadata or {},
        )

    def acknowledge(self, acknowledged_by: str) -> "Alert":
        """Create acknowledged copy of this alert.

        Args:
            acknowledged_by: User/system acknowledging the alert

        Returns:
            New Alert with acknowledged=True
        """
        return Alert(
            id=self.id,
            severity=self.severity,
            message=self.message,
            source=self.source,
            timestamp=self.timestamp,
            acknowledged=True,
            acknowledged_at=datetime.now(),
            acknowledged_by=acknowledged_by,
            rule_id=self.rule_id,
            metadata=self.metadata,
        )

    def is_critical(self) -> bool:
        """Check if alert is critical severity.

        Returns:
            True if severity is CRITICAL
        """
        return self.severity == AlertSeverity.CRITICAL

    def is_error(self) -> bool:
        """Check if alert is error severity.

        Returns:
            True if severity is ERROR
        """
        return self.severity == AlertSeverity.ERROR

    def requires_action(self) -> bool:
        """Check if alert requires action.

        Returns:
            True if severity is CRITICAL or ERROR
        """
        return self.severity in (AlertSeverity.CRITICAL, AlertSeverity.ERROR)

    def to_dict(self) -> Dict[str, any]:
        """Serialize alert to dictionary.

        Returns:
            Dictionary representation of alert
        """
        return {
            "id": self.id,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "rule_id": self.rule_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AlertRule:
    """Configurable alert condition.

    Immutable entity defining when and how to trigger alerts.
    """

    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # Human-readable condition (e.g., "cost > $100")
    threshold: float  # Numeric threshold for condition
    enabled: bool = True
    cooldown_minutes: int = 60  # Prevent alert spam

    # Optional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate alert rule data."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Rule ID cannot be empty")

        # Validate name
        if not self.name or not self.name.strip():
            raise ValueError("Rule name cannot be empty")

        # Validate description
        if not self.description or not self.description.strip():
            raise ValueError("Rule description cannot be empty")

        # Validate condition
        if not self.condition or not self.condition.strip():
            raise ValueError("Rule condition cannot be empty")

        # Validate severity
        if not isinstance(self.severity, AlertSeverity):
            raise ValueError(f"Invalid severity: {self.severity}")

        # Validate cooldown
        if self.cooldown_minutes < 0:
            raise ValueError(f"Cooldown cannot be negative: {self.cooldown_minutes}")

    @staticmethod
    def create(
        name: str,
        description: str,
        severity: AlertSeverity,
        condition: str,
        threshold: float,
        enabled: bool = True,
        cooldown_minutes: int = 60,
        metadata: Optional[Dict[str, any]] = None,
    ) -> "AlertRule":
        """Factory method to create an alert rule with generated ID.

        Args:
            name: Rule name
            description: Rule description
            severity: Alert severity for this rule
            condition: Human-readable condition
            threshold: Numeric threshold
            enabled: Whether rule is enabled
            cooldown_minutes: Cooldown period in minutes
            metadata: Optional metadata

        Returns:
            New AlertRule with generated ID
        """
        return AlertRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            severity=severity,
            condition=condition,
            threshold=threshold,
            enabled=enabled,
            cooldown_minutes=cooldown_minutes,
            metadata=metadata or {},
        )

    def enable(self) -> "AlertRule":
        """Create enabled copy of this rule.

        Returns:
            New AlertRule with enabled=True
        """
        return AlertRule(
            id=self.id,
            name=self.name,
            description=self.description,
            severity=self.severity,
            condition=self.condition,
            threshold=self.threshold,
            enabled=True,
            cooldown_minutes=self.cooldown_minutes,
            metadata=self.metadata,
        )

    def disable(self) -> "AlertRule":
        """Create disabled copy of this rule.

        Returns:
            New AlertRule with enabled=False
        """
        return AlertRule(
            id=self.id,
            name=self.name,
            description=self.description,
            severity=self.severity,
            condition=self.condition,
            threshold=self.threshold,
            enabled=False,
            cooldown_minutes=self.cooldown_minutes,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, any]:
        """Serialize rule to dictionary.

        Returns:
            Dictionary representation of rule
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes,
            "metadata": self.metadata,
        }
