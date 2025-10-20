"""
Alert Manager for ATADO Metrics

Monitors metrics and sends alerts on regressions or anomalies.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents a metric alert."""
    alert_id: str
    timestamp: str
    severity: str  # critical, warning, info
    metric_name: str
    current_value: float
    threshold: float
    message: str
    metadata: Dict[str, Any]


@dataclass
class AlertRule:
    """Defines an alert rule."""
    rule_id: str
    metric_name: str
    threshold: float
    comparison: str  # gt, lt, gte, lte
    severity: str
    message_template: str


class AlertManager:
    """
    Manages metric alerts and notifications.
    
    Features:
    - Define alert rules for metrics
    - Evaluate metrics against rules
    - Send notifications (Slack, email)
    - Track alert history
    """
    
    # Default alert rules
    DEFAULT_RULES = [
        AlertRule(
            rule_id="accuracy_drop",
            metric_name="routing_accuracy",
            threshold=0.80,
            comparison="lt",
            severity="critical",
            message_template="Routing accuracy dropped to {current_value:.1%} (threshold: {threshold:.1%})"
        ),
        AlertRule(
            rule_id="latency_spike",
            metric_name="p95_latency_ms",
            threshold=1000.0,
            comparison="gt",
            severity="warning",
            message_template="P95 latency spiked to {current_value:.0f}ms (threshold: {threshold:.0f}ms)"
        ),
        AlertRule(
            rule_id="cost_spike",
            metric_name="cost_per_task",
            threshold=0.20,
            comparison="gt",
            severity="warning",
            message_template="Cost per task increased to ${current_value:.4f} (threshold: ${threshold:.4f})"
        ),
        AlertRule(
            rule_id="error_rate_high",
            metric_name="error_rate",
            threshold=0.10,
            comparison="gt",
            severity="critical",
            message_template="Error rate increased to {current_value:.1%} (threshold: {threshold:.1%})"
        ),
    ]
    
    def __init__(self, slack_webhook_url: Optional[str] = None):
        """
        Initialize alert manager.
        
        Args:
            slack_webhook_url: Slack webhook URL for notifications
        """
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.rules: List[AlertRule] = self.DEFAULT_RULES.copy()
        self.alerts: List[Alert] = []
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule."""
        self.rules.append(rule)
    
    def evaluate_metric(
        self,
        metric_name: str,
        current_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Evaluate a metric against all applicable rules.
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            metadata: Additional context
            
        Returns:
            List of triggered alerts
        """
        triggered = []
        metadata = metadata or {}
        
        for rule in self.rules:
            if rule.metric_name != metric_name:
                continue
            
            # Evaluate condition
            violated = False
            if rule.comparison == "gt":
                violated = current_value > rule.threshold
            elif rule.comparison == "lt":
                violated = current_value < rule.threshold
            elif rule.comparison == "gte":
                violated = current_value >= rule.threshold
            elif rule.comparison == "lte":
                violated = current_value <= rule.threshold
            
            if violated:
                alert = Alert(
                    alert_id=f"alert_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{rule.rule_id}",
                    timestamp=datetime.now(UTC).isoformat(),
                    severity=rule.severity,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold=rule.threshold,
                    message=rule.message_template.format(
                        current_value=current_value,
                        threshold=rule.threshold
                    ),
                    metadata=metadata
                )
                
                triggered.append(alert)
                self.alerts.append(alert)
                
                logger.warning(f"Alert triggered: {alert.message}")
        
        return triggered
    
    def send_alert(self, alert: Alert) -> bool:
        """
        Send alert notification.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if sent successfully
        """
        if self.slack_webhook_url:
            return self._send_slack_alert(alert)
        else:
            logger.info(f"No notification channel configured for alert: {alert.message}")
            return False
    
    def _send_slack_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            import requests
            
            # Format Slack message
            color = {
                "critical": "danger",
                "warning": "warning",
                "info": "good"
            }.get(alert.severity, "warning")
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 ATADO Alert: {alert.metric_name}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp,
                                "short": True
                            }
                        ],
                        "footer": "ATADO Alert Manager"
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            
            logger.info(f"Slack alert sent: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def get_recent_alerts(self, limit: int = 20, severity: Optional[str] = None) -> List[Alert]:
        """
        Get recent alerts, optionally filtered by severity.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity
            
        Returns:
            List of recent alerts
        """
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]
    
    def clear_alerts(self) -> None:
        """Clear alert history."""
        self.alerts = []

