"""Idle Detection Monitor for Scale-to-Zero.

Sprint 1: Production Deployment - P1.2
Monitors service activity and signals when service is idle for scale-down.

Clean Architecture: Use case layer (observability concern).
SOLID: SRP - Single responsibility for idle detection.
"""

import time
import threading
import logging
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IdleConfig:
    """Configuration for idle detection."""
    idle_threshold_seconds: int = 300  # 5 minutes default
    check_interval_seconds: int = 30  # Check every 30 seconds
    grace_period_seconds: int = 60  # Grace period after startup
    enable_auto_scale: bool = True


class IdleMonitor:
    """Monitors service activity and detects idle state.

    Tracks request activity and signals when service has been idle
    beyond configured threshold. Useful for scale-to-zero scenarios.

    Thread-safe for concurrent request tracking.
    """

    def __init__(self, config: Optional[IdleConfig] = None):
        """Initialize idle monitor.

        Args:
            config: Idle detection configuration
        """
        self.config = config or IdleConfig()
        self._last_activity = time.time()
        self._start_time = time.time()
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._idle_callbacks: list[Callable[[], None]] = []
        self._request_count = 0
        self._last_idle_check = time.time()

    def record_activity(self) -> None:
        """Record activity (request received).

        Call this method whenever a request is processed to reset idle timer.
        Thread-safe.
        """
        with self._lock:
            self._last_activity = time.time()
            self._request_count += 1

    def get_idle_duration(self) -> float:
        """Get current idle duration in seconds.

        Returns:
            Seconds since last activity
        """
        with self._lock:
            return time.time() - self._last_activity

    def is_idle(self) -> bool:
        """Check if service is currently idle.

        Returns:
            True if idle duration exceeds threshold
        """
        # Grace period: Don't consider idle during startup
        uptime = time.time() - self._start_time
        if uptime < self.config.grace_period_seconds:
            return False

        return self.get_idle_duration() >= self.config.idle_threshold_seconds

    def get_metrics(self) -> dict:
        """Get idle monitoring metrics.

        Returns:
            Dictionary with idle metrics
        """
        with self._lock:
            uptime = time.time() - self._start_time
            idle_duration = self.get_idle_duration()

            return {
                'idle_duration_seconds': round(idle_duration, 2),
                'is_idle': self.is_idle(),
                'idle_threshold_seconds': self.config.idle_threshold_seconds,
                'request_count_total': self._request_count,
                'uptime_seconds': round(uptime, 2),
                'last_activity_timestamp': self._last_activity,
                'auto_scale_enabled': self.config.enable_auto_scale,
            }

    def register_idle_callback(self, callback: Callable[[], None]) -> None:
        """Register callback to be called when service becomes idle.

        Args:
            callback: Function to call when idle threshold exceeded
        """
        with self._lock:
            self._idle_callbacks.append(callback)

    def start_monitoring(self) -> None:
        """Start background monitoring thread.

        Periodically checks idle status and invokes callbacks if idle.
        """
        if self._running:
            logger.warning("Idle monitor already running")
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="idle-monitor",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(
            f"Idle monitor started (threshold={self.config.idle_threshold_seconds}s, "
            f"check_interval={self.config.check_interval_seconds}s)"
        )

    def stop_monitoring(self) -> None:
        """Stop background monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Idle monitor stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop (runs in thread)."""
        while self._running:
            try:
                # Check idle status
                if self.is_idle() and self.config.enable_auto_scale:
                    # Only log/callback once per idle period
                    time_since_last_check = time.time() - self._last_idle_check
                    if time_since_last_check >= self.config.check_interval_seconds:
                        logger.info(
                            f"Service idle for {self.get_idle_duration():.0f}s "
                            f"(threshold: {self.config.idle_threshold_seconds}s)"
                        )
                        self._last_idle_check = time.time()

                        # Invoke callbacks
                        for callback in self._idle_callbacks:
                            try:
                                callback()
                            except Exception as e:
                                logger.error(f"Idle callback failed: {e}")

                # Sleep until next check
                time.sleep(self.config.check_interval_seconds)

            except Exception as e:
                logger.error(f"Idle monitor error: {e}")
                time.sleep(self.config.check_interval_seconds)


# Global instance for singleton pattern
_global_monitor: Optional[IdleMonitor] = None
_monitor_lock = threading.Lock()


def get_idle_monitor(config: Optional[IdleConfig] = None) -> IdleMonitor:
    """Get global idle monitor instance (singleton).

    Args:
        config: Configuration (only used on first call)

    Returns:
        Global IdleMonitor instance
    """
    global _global_monitor

    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = IdleMonitor(config)
        return _global_monitor


def signal_scale_down():
    """Signal that service should scale down (idle callback).

    This function is called when service is idle. In production:
    - K8s: Reduces replicas to 0 (handled by HPA or custom controller)
    - systemd: Stops service (can be configured with systemd timer)

    Current implementation: Just logs (actual scale-down handled externally).
    """
    logger.warning("Service idle - signaling scale-down opportunity")

    # In production, could:
    # 1. Write signal file for external monitor
    # 2. Call K8s API to scale down
    # 3. Update HPA metrics to trigger scale-down
    # 4. Gracefully shutdown (for systemd with socket activation)

    # Example: Write signal file
    signal_file = "/tmp/scale-down-signal"
    try:
        with open(signal_file, 'w') as f:
            f.write(f"{time.time()}\n")
        logger.info(f"Scale-down signal written to {signal_file}")
    except Exception as e:
        logger.error(f"Failed to write scale-down signal: {e}")
