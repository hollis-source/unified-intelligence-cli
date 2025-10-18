"""RAG Alerting System.

This module provides alerting for RAG system issues including:
- RAG failures
- Low accuracy
- High latency
- Pattern drift
- Insufficient data
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents an alert."""
    
    def __init__(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize alert.
        
        Args:
            alert_type: Type of alert (e.g., "low_accuracy", "high_latency")
            severity: Alert severity level
            message: Human-readable alert message
            details: Additional alert details
            timestamp: Alert timestamp (defaults to now)
        """
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"[{self.severity.value.upper()}] {self.alert_type}: {self.message}"


class RAGAlerting:
    """RAG alerting system."""
    
    def __init__(
        self,
        db_store,
        accuracy_threshold: float = 70.0,
        latency_threshold_ms: float = 1000.0,
        drift_threshold: float = 0.3,
        min_patterns: int = 50
    ):
        """Initialize alerting system.
        
        Args:
            db_store: SurrealDBStore instance
            accuracy_threshold: Minimum acceptable accuracy (%)
            latency_threshold_ms: Maximum acceptable latency (ms)
            drift_threshold: Maximum acceptable drift score
            min_patterns: Minimum required patterns
        """
        self.db_store = db_store
        self.accuracy_threshold = accuracy_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.drift_threshold = drift_threshold
        self.min_patterns = min_patterns
        self.alert_handlers: List[Callable[[Alert], None]] = []
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler function.
        
        Args:
            handler: Function that takes an Alert and handles it
        """
        self.alert_handlers.append(handler)
    
    async def _emit_alert(self, alert: Alert) -> None:
        """Emit an alert to all handlers.
        
        Args:
            alert: Alert to emit
        """
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")
    
    async def check_accuracy(self) -> List[Alert]:
        """Check routing accuracy and generate alerts if needed.
        
        Returns:
            List of alerts
        """
        alerts = []
        
        try:
            # Get RAG accuracy
            rag_accuracy = await self.db_store.get_routing_accuracy(strategy="rag", limit=100)
            
            if rag_accuracy < self.accuracy_threshold:
                alert = Alert(
                    alert_type="low_accuracy",
                    severity=AlertSeverity.WARNING if rag_accuracy > 50 else AlertSeverity.ERROR,
                    message=f"RAG routing accuracy is low: {rag_accuracy:.1f}% (threshold: {self.accuracy_threshold:.1f}%)",
                    details={
                        "current_accuracy": rag_accuracy,
                        "threshold": self.accuracy_threshold,
                        "difference": rag_accuracy - self.accuracy_threshold
                    }
                )
                alerts.append(alert)
                await self._emit_alert(alert)
        
        except Exception as e:
            alert = Alert(
                alert_type="accuracy_check_failed",
                severity=AlertSeverity.ERROR,
                message=f"Failed to check accuracy: {str(e)}",
                details={"error": str(e)}
            )
            alerts.append(alert)
            await self._emit_alert(alert)
        
        return alerts
    
    async def check_pattern_count(self) -> List[Alert]:
        """Check pattern count and generate alerts if needed.
        
        Returns:
            List of alerts
        """
        alerts = []
        
        try:
            # Get pattern count
            sql = "SELECT count() as total FROM execution_log GROUP ALL;"
            result = await self.db_store.query(sql)
            
            total_patterns = 0
            if result and isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "total" in result[0]:
                    total_patterns = result[0]["total"]
            
            if total_patterns < self.min_patterns:
                alert = Alert(
                    alert_type="insufficient_patterns",
                    severity=AlertSeverity.WARNING,
                    message=f"Insufficient patterns: {total_patterns} (minimum: {self.min_patterns})",
                    details={
                        "current_patterns": total_patterns,
                        "minimum_required": self.min_patterns,
                        "needed": self.min_patterns - total_patterns
                    }
                )
                alerts.append(alert)
                await self._emit_alert(alert)
        
        except Exception as e:
            alert = Alert(
                alert_type="pattern_count_check_failed",
                severity=AlertSeverity.ERROR,
                message=f"Failed to check pattern count: {str(e)}",
                details={"error": str(e)}
            )
            alerts.append(alert)
            await self._emit_alert(alert)
        
        return alerts
    
    async def check_drift(self) -> List[Alert]:
        """Check for pattern drift and generate alerts if needed.
        
        Returns:
            List of alerts
        """
        alerts = []
        
        try:
            from src.routing.drift_detector import DriftDetector
            
            detector = DriftDetector(db_store=self.db_store, drift_threshold=self.drift_threshold)
            drift_result = await detector.detect_drift()
            
            if drift_result.get("drift_detected"):
                drift_score = drift_result.get("drift_score", 0)
                alert = Alert(
                    alert_type="pattern_drift",
                    severity=AlertSeverity.WARNING,
                    message=f"Pattern drift detected: {drift_score:.2f} (threshold: {self.drift_threshold})",
                    details={
                        "drift_score": drift_score,
                        "threshold": self.drift_threshold,
                        "recommendation": drift_result.get("recommendation", "")
                    }
                )
                alerts.append(alert)
                await self._emit_alert(alert)
        
        except Exception as e:
            alert = Alert(
                alert_type="drift_check_failed",
                severity=AlertSeverity.ERROR,
                message=f"Failed to check drift: {str(e)}",
                details={"error": str(e)}
            )
            alerts.append(alert)
            await self._emit_alert(alert)
        
        return alerts
    
    async def check_database_connection(self) -> List[Alert]:
        """Check database connection and generate alerts if needed.

        Returns:
            List of alerts
        """
        alerts = []

        try:
            # Try a simple query (SurrealDB requires FROM clause)
            result = await self.db_store.query("SELECT count() as total FROM execution_log GROUP ALL;")

            if not result:
                alert = Alert(
                    alert_type="database_connection_issue",
                    severity=AlertSeverity.CRITICAL,
                    message="Database connection issue: query returned no results",
                    details={}
                )
                alerts.append(alert)
                await self._emit_alert(alert)

        except Exception as e:
            alert = Alert(
                alert_type="database_connection_failed",
                severity=AlertSeverity.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                details={"error": str(e)}
            )
            alerts.append(alert)
            await self._emit_alert(alert)

        return alerts
    
    async def run_all_checks(self) -> Dict[str, List[Alert]]:
        """Run all health checks and return alerts.
        
        Returns:
            Dictionary mapping check name to list of alerts
        """
        results = {
            "database": await self.check_database_connection(),
            "accuracy": await self.check_accuracy(),
            "patterns": await self.check_pattern_count(),
            "drift": await self.check_drift()
        }
        
        return results
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts.
        
        Returns:
            Dictionary with alert summary
        """
        results = await self.run_all_checks()
        
        all_alerts = []
        for check_alerts in results.values():
            all_alerts.extend(check_alerts)
        
        # Count by severity
        severity_counts = {
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0
        }
        
        for alert in all_alerts:
            severity_counts[alert.severity.value] += 1
        
        return {
            "total_alerts": len(all_alerts),
            "by_severity": severity_counts,
            "alerts": [alert.to_dict() for alert in all_alerts],
            "checks_run": list(results.keys()),
            "timestamp": datetime.now().isoformat()
        }


# Built-in alert handlers

def console_alert_handler(alert: Alert) -> None:
    """Print alert to console.
    
    Args:
        alert: Alert to print
    """
    print(f"🚨 {alert}")


def log_alert_handler(alert: Alert, log_file: str = "/tmp/rag_alerts.log") -> None:
    """Write alert to log file.
    
    Args:
        alert: Alert to log
        log_file: Path to log file
    """
    try:
        with open(log_file, "a") as f:
            f.write(f"{alert.timestamp.isoformat()} - {alert}\n")
    except Exception as e:
        print(f"Failed to write alert to log: {e}")

