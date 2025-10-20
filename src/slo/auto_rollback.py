"""Auto-Rollback - Automatic rollback on SLO violations.

Monitors SLO compliance and triggers automatic rollback when violations persist.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for auto-rollback logic
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from src.slo.slo_monitor import SLOMonitor
from src.slo.slo_definitions import SLOViolation, SLOSeverity

logger = logging.getLogger(__name__)


class AutoRollback:
    """
    Automatic rollback on SLO violations.
    
    Triggers rollback when:
    - Critical SLO violated for >5 minutes
    - Multiple high-severity SLOs violated simultaneously
    - Error rate >10% for >2 minutes
    
    Usage:
        rollback = AutoRollback(monitor=slo_monitor, rollback_fn=do_rollback)
        rollback.check_and_rollback()
    """
    
    def __init__(
        self,
        monitor: SLOMonitor,
        rollback_fn: Optional[Callable[[], bool]] = None,
        dry_run: bool = False,
    ):
        """
        Initialize auto-rollback.
        
        Args:
            monitor: SLOMonitor instance
            rollback_fn: Function to call for rollback (returns success bool)
            dry_run: If True, log rollback actions but don't execute
        """
        self.monitor = monitor
        self.rollback_fn = rollback_fn
        self.dry_run = dry_run
        
        # Rollback history
        self.rollback_history: list[Dict[str, Any]] = []
        self.last_rollback_time: Optional[datetime] = None
        
        # Cooldown period (prevent repeated rollbacks)
        self.cooldown_minutes = 30
    
    def check_and_rollback(self) -> bool:
        """
        Check SLO violations and trigger rollback if needed.
        
        Returns:
            True if rollback was triggered
        """
        # Check if in cooldown period
        if self._in_cooldown():
            logger.debug("Auto-rollback in cooldown period, skipping check")
            return False
        
        # Check if rollback should be triggered
        if not self.monitor.should_trigger_rollback():
            return False
        
        # Get violation details
        violations = self.monitor.get_active_violations()
        critical_violations = self.monitor.get_critical_violations()
        
        # Build rollback reason
        reason = self._build_rollback_reason(violations, critical_violations)
        
        logger.critical(f"AUTO-ROLLBACK TRIGGERED: {reason}")
        
        # Execute rollback
        success = self._execute_rollback(reason, violations)
        
        # Record rollback
        self._record_rollback(reason, violations, success)
        
        return success
    
    def _in_cooldown(self) -> bool:
        """Check if in cooldown period after last rollback."""
        if self.last_rollback_time is None:
            return False
        
        elapsed = (datetime.now() - self.last_rollback_time).total_seconds() / 60
        return elapsed < self.cooldown_minutes
    
    def _build_rollback_reason(
        self,
        violations: list[SLOViolation],
        critical_violations: list[SLOViolation],
    ) -> str:
        """Build human-readable rollback reason."""
        reasons = []
        
        # Critical violations
        for v in critical_violations:
            if v.duration_seconds and v.duration_seconds >= self.monitor.violation_threshold_seconds:
                reasons.append(
                    f"Critical SLO '{v.slo_name}' violated for {v.duration_seconds}s "
                    f"(target: {v.target_value}, actual: {v.actual_value})"
                )
        
        # Multiple high-severity violations
        high_severity = [
            v for v in violations
            if v.severity in [SLOSeverity.CRITICAL, SLOSeverity.HIGH]
        ]
        
        if len(high_severity) >= 3:
            reasons.append(f"{len(high_severity)} high-severity SLO violations")
        
        return "; ".join(reasons) if reasons else "Unknown reason"
    
    def _execute_rollback(
        self,
        reason: str,
        violations: list[SLOViolation],
    ) -> bool:
        """Execute rollback."""
        if self.dry_run:
            logger.warning(f"DRY RUN: Would trigger rollback - {reason}")
            return True
        
        if self.rollback_fn is None:
            logger.error("No rollback function configured, cannot execute rollback")
            return False
        
        try:
            logger.critical(f"Executing rollback: {reason}")
            success = self.rollback_fn()
            
            if success:
                logger.info("Rollback executed successfully")
            else:
                logger.error("Rollback execution failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Rollback execution error: {e}", exc_info=True)
            return False
    
    def _record_rollback(
        self,
        reason: str,
        violations: list[SLOViolation],
        success: bool,
    ):
        """Record rollback in history."""
        rollback_record = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "success": success,
            "violations": [
                {
                    "slo": v.slo_name,
                    "metric": v.metric,
                    "target": v.target_value,
                    "actual": v.actual_value,
                    "severity": v.severity.value,
                    "duration_seconds": v.duration_seconds,
                }
                for v in violations
            ],
        }
        
        self.rollback_history.append(rollback_record)
        self.last_rollback_time = datetime.now()
        
        logger.info(f"Rollback recorded: {rollback_record}")
    
    def get_rollback_history(self) -> list[Dict[str, Any]]:
        """Get rollback history."""
        return self.rollback_history
    
    def reset_cooldown(self):
        """Reset cooldown period (for testing)."""
        self.last_rollback_time = None
        logger.info("Rollback cooldown reset")


def create_rollback_function(
    weights_cli_path: str = "scripts/weights_cli.py",
) -> Callable[[], bool]:
    """
    Create rollback function that calls weights_cli.py rollback.
    
    Args:
        weights_cli_path: Path to weights CLI script
        
    Returns:
        Rollback function
    """
    def rollback() -> bool:
        """Execute rollback via weights CLI."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["python3", weights_cli_path, "rollback", "--confirm"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                logger.info(f"Rollback successful: {result.stdout}")
                return True
            else:
                logger.error(f"Rollback failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Rollback execution error: {e}")
            return False
    
    return rollback


# Convenience function for integration
def setup_auto_rollback(
    monitor: SLOMonitor,
    dry_run: bool = False,
) -> AutoRollback:
    """
    Setup auto-rollback with default configuration.
    
    Args:
        monitor: SLOMonitor instance
        dry_run: If True, log rollback actions but don't execute
        
    Returns:
        Configured AutoRollback instance
    """
    rollback_fn = create_rollback_function() if not dry_run else None
    
    return AutoRollback(
        monitor=monitor,
        rollback_fn=rollback_fn,
        dry_run=dry_run,
    )

