"""In-memory alert manager adapter for testing and development.

Stores alerts and rules in memory without requiring external database.
Useful for unit tests and local development.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from ..interfaces import IAlertManager
from ..entities import Alert, AlertRule, AlertSeverity

logger = logging.getLogger(__name__)


class InMemoryAlertManager(IAlertManager):
    """In-memory alert manager implementation for testing.

    Stores alerts and rules in memory with filtering and rule management.
    Provides simple implementation of IAlertManager contract without
    requiring external dependencies (SQLite, PostgreSQL, etc.).

    Thread-safe for single-threaded test environments.
    For production, use SQLiteAlertManager or PostgreSQLAlertManager.
    """

    def __init__(self):
        """Initialize empty alert and rule storage."""
        self._alerts: List[Alert] = []
        self._rules: Dict[str, AlertRule] = {}  # rule_id -> rule
        self._last_triggered: Dict[str, datetime] = {}  # rule_id -> last trigger time

    def record_alert(self, alert: Alert) -> None:
        """Record an alert.

        Args:
            alert: Alert to store

        Raises:
            ValueError: If alert is invalid
        """
        if not isinstance(alert, Alert):
            raise ValueError(f"Expected Alert, got {type(alert)}")

        self._alerts.append(alert)
        # Keep sorted by timestamp (newest first)
        self._alerts.sort(key=lambda a: a.timestamp, reverse=True)

        ack_status = "acknowledged" if alert.acknowledged else "unacknowledged"
        logger.debug(
            f"Recorded alert: [{alert.severity.value.upper()}] {alert.source} - "
            f"{alert.message} ({ack_status})"
        )

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Alert]:
        """Get alerts matching filters."""
        filtered = self._filter_alerts(
            severity, source, acknowledged, start_time, end_time
        )

        # Apply limit
        if limit is not None:
            filtered = filtered[:limit]

        return filtered

    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID."""
        for alert in self._alerts:
            if alert.id == alert_id:
                return alert
        return None

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """Acknowledge an alert."""
        # Find alert
        alert = self.get_alert_by_id(alert_id)
        if alert is None:
            raise ValueError(f"Alert not found: {alert_id}")

        # Create acknowledged copy
        acknowledged_alert = alert.acknowledge(acknowledged_by)

        # Replace in storage
        for i, a in enumerate(self._alerts):
            if a.id == alert_id:
                self._alerts[i] = acknowledged_alert
                break

        logger.info(
            f"Acknowledged alert {alert_id} by {acknowledged_by}: {alert.message}"
        )
        return acknowledged_alert

    def get_unacknowledged_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Alert]:
        """Get unacknowledged alerts matching filters."""
        return self.get_alerts(
            severity=severity,
            source=source,
            acknowledged=False,
            start_time=start_time,
            end_time=end_time,
        )

    def delete_alerts(self, before: datetime) -> int:
        """Delete alerts before specified time."""
        # Find alerts to delete
        to_delete = [a for a in self._alerts if a.timestamp < before]

        # Remove from storage
        for alert in to_delete:
            self._alerts.remove(alert)

        deleted_count = len(to_delete)
        logger.info(f"Deleted {deleted_count} alerts before {before.isoformat()}")
        return deleted_count

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        if not isinstance(rule, AlertRule):
            raise ValueError(f"Expected AlertRule, got {type(rule)}")

        self._rules[rule.id] = rule
        status = "enabled" if rule.enabled else "disabled"
        logger.debug(
            f"Added alert rule: {rule.name} [{rule.severity.value}] ({status})"
        )

    def get_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """Get alert rules."""
        rules = list(self._rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def enable_rule(self, rule_id: str) -> None:
        """Enable an alert rule."""
        if rule_id not in self._rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self._rules[rule_id]
        self._rules[rule_id] = rule.enable()
        logger.info(f"Enabled alert rule: {rule.name}")

    def disable_rule(self, rule_id: str) -> None:
        """Disable an alert rule."""
        if rule_id not in self._rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self._rules[rule_id]
        self._rules[rule_id] = rule.disable()
        logger.info(f"Disabled alert rule: {rule.name}")

    def delete_rule(self, rule_id: str) -> None:
        """Delete an alert rule."""
        if rule_id not in self._rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self._rules.pop(rule_id)
        # Clean up last triggered tracking
        if rule_id in self._last_triggered:
            del self._last_triggered[rule_id]

        logger.info(f"Deleted alert rule: {rule.name}")

    def can_trigger_rule(self, rule_id: str) -> bool:
        """Check if rule can be triggered (cooldown elapsed)."""
        # Check if rule exists and is enabled
        if rule_id not in self._rules:
            return False

        rule = self._rules[rule_id]
        if not rule.enabled:
            return False

        # Check cooldown
        if rule_id in self._last_triggered:
            last_trigger = self._last_triggered[rule_id]
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            if datetime.now() - last_trigger < cooldown_delta:
                return False

        return True

    def mark_rule_triggered(self, rule_id: str) -> None:
        """Mark rule as triggered (for cooldown tracking).

        Args:
            rule_id: Rule ID that was triggered

        Note:
            Not part of IAlertManager interface. Useful for testing.
        """
        self._last_triggered[rule_id] = datetime.now()

    def _filter_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Alert]:
        """Filter alerts by specified criteria.

        Args:
            severity: Filter by severity level
            source: Filter by source
            acknowledged: Filter by acknowledgment status
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (exclusive)

        Returns:
            List of Alert objects matching all filters
        """
        filtered = self._alerts

        if severity is not None:
            filtered = [a for a in filtered if a.severity == severity]

        if source is not None:
            filtered = [a for a in filtered if a.source == source]

        if acknowledged is not None:
            filtered = [a for a in filtered if a.acknowledged == acknowledged]

        if start_time is not None:
            filtered = [a for a in filtered if a.timestamp >= start_time]

        if end_time is not None:
            filtered = [a for a in filtered if a.timestamp < end_time]

        return filtered

    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts (no filtering).

        Returns:
            List of all Alert objects

        Note:
            Not part of IAlertManager interface. Useful for testing.
        """
        return self._alerts.copy()

    def get_all_rules(self) -> List[AlertRule]:
        """Get all rules (no filtering).

        Returns:
            List of all AlertRule objects

        Note:
            Not part of IAlertManager interface. Useful for testing.
        """
        return list(self._rules.values())

    def clear_alerts(self) -> None:
        """Clear all alerts.

        Note:
            Not part of IAlertManager interface. Useful for test cleanup.
        """
        count = len(self._alerts)
        self._alerts.clear()
        logger.debug(f"Cleared {count} alerts")

    def clear_rules(self) -> None:
        """Clear all rules.

        Note:
            Not part of IAlertManager interface. Useful for test cleanup.
        """
        count = len(self._rules)
        self._rules.clear()
        self._last_triggered.clear()
        logger.debug(f"Cleared {count} rules")
