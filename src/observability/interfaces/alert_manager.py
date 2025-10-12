"""Alert manager interface for error alerting and notification.

Defines the contract for alert manager implementations following
Dependency Inversion Principle. Use cases depend on this
interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..entities import Alert, AlertRule, AlertSeverity


class IAlertManager(ABC):
    """Interface for alert management and notification.

    Abstracts alert storage and rule management implementation details.
    Implementations can use SQLite, PostgreSQL, in-memory, etc.

    Contract:
    - record_alert() stores an alert
    - get_alerts() retrieves alerts with filters
    - get_alert_by_id() retrieves specific alert
    - acknowledge_alert() marks alert as acknowledged
    - get_unacknowledged_alerts() retrieves unacknowledged alerts
    - delete_alerts() removes old alerts
    - add_rule() adds an alert rule
    - get_rules() retrieves rules
    - enable_rule() enables a rule
    - disable_rule() disables a rule
    - delete_rule() removes a rule
    """

    @abstractmethod
    def record_alert(self, alert: Alert) -> None:
        """Record an alert.

        Args:
            alert: Alert to store

        Raises:
            ValueError: If alert validation fails
            RuntimeError: If storage fails
        """
        pass

    @abstractmethod
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Alert]:
        """Get alerts matching filters.

        Args:
            severity: Filter by severity level
            source: Filter by source
            acknowledged: Filter by acknowledgment status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)
            limit: Maximum number of alerts to return

        Returns:
            List of Alert objects matching filters

        Note:
            Alerts are returned in reverse chronological order (newest first).
        """
        pass

    @abstractmethod
    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert if found, None otherwise
        """
        pass

    @abstractmethod
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User/system acknowledging the alert

        Returns:
            Updated Alert with acknowledged=True

        Raises:
            ValueError: If alert not found
        """
        pass

    @abstractmethod
    def get_unacknowledged_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Alert]:
        """Get unacknowledged alerts matching filters.

        Args:
            severity: Filter by severity level
            source: Filter by source
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            List of unacknowledged Alert objects

        Note:
            Equivalent to get_alerts(..., acknowledged=False)
        """
        pass

    @abstractmethod
    def delete_alerts(self, before: datetime) -> int:
        """Delete alerts before specified time.

        Args:
            before: Delete alerts before this time

        Returns:
            Number of alerts deleted

        Note:
            Use with caution. Primarily for cleanup.
        """
        pass

    @abstractmethod
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule.

        Args:
            rule: AlertRule to add

        Raises:
            ValueError: If rule validation fails
        """
        pass

    @abstractmethod
    def get_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """Get alert rules.

        Args:
            enabled_only: Only return enabled rules

        Returns:
            List of AlertRule objects
        """
        pass

    @abstractmethod
    def enable_rule(self, rule_id: str) -> None:
        """Enable an alert rule.

        Args:
            rule_id: Rule ID to enable

        Raises:
            ValueError: If rule not found
        """
        pass

    @abstractmethod
    def disable_rule(self, rule_id: str) -> None:
        """Disable an alert rule.

        Args:
            rule_id: Rule ID to disable

        Raises:
            ValueError: If rule not found
        """
        pass

    @abstractmethod
    def delete_rule(self, rule_id: str) -> None:
        """Delete an alert rule.

        Args:
            rule_id: Rule ID to delete

        Raises:
            ValueError: If rule not found
        """
        pass

    def can_trigger_rule(self, rule_id: str) -> bool:
        """Check if rule can be triggered (cooldown elapsed).

        Args:
            rule_id: Rule ID to check

        Returns:
            True if rule can trigger, False if in cooldown

        Note:
            This is an optional method with default implementation.
            Implementations can override with cooldown tracking logic.
        """
        return True  # Default: always allow triggering
