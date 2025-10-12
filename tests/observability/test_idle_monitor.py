"""Tests for Idle Monitor functionality.

Sprint 1: Production Deployment - P1.2
Tests idle detection, metrics reporting, and scale-down signaling.
"""

import time
import pytest
from src.observability.idle_monitor import IdleMonitor, IdleConfig, get_idle_monitor


def test_idle_monitor_initialization():
    """Test idle monitor initializes with default config."""
    config = IdleConfig()
    monitor = IdleMonitor(config)

    assert monitor.config.idle_threshold_seconds == 300
    assert monitor.config.check_interval_seconds == 30
    assert monitor.config.grace_period_seconds == 60
    assert monitor.config.enable_auto_scale is True


def test_idle_monitor_record_activity():
    """Test activity recording resets idle timer."""
    config = IdleConfig(idle_threshold_seconds=1)
    monitor = IdleMonitor(config)

    # Record activity
    monitor.record_activity()
    initial_duration = monitor.get_idle_duration()

    # Wait a bit
    time.sleep(0.5)
    duration_after_wait = monitor.get_idle_duration()

    # Record activity again
    monitor.record_activity()
    duration_after_reset = monitor.get_idle_duration()

    assert initial_duration < 0.1  # Near zero
    assert duration_after_wait >= 0.5  # At least 0.5 seconds
    assert duration_after_reset < 0.1  # Reset to near zero


def test_idle_monitor_grace_period():
    """Test grace period prevents false idle detection during startup."""
    config = IdleConfig(
        idle_threshold_seconds=1,  # Short threshold
        grace_period_seconds=5  # 5 second grace period
    )
    monitor = IdleMonitor(config)

    # Don't record any activity
    time.sleep(1.5)  # Wait longer than threshold

    # Should not be idle due to grace period
    assert not monitor.is_idle()


def test_idle_monitor_becomes_idle():
    """Test monitor correctly detects idle state."""
    config = IdleConfig(
        idle_threshold_seconds=1,  # 1 second threshold
        grace_period_seconds=0  # No grace period for testing
    )
    monitor = IdleMonitor(config)

    # Initially not idle
    assert not monitor.is_idle()

    # Wait for threshold
    time.sleep(1.2)

    # Should now be idle
    assert monitor.is_idle()


def test_idle_monitor_metrics():
    """Test idle metrics are correctly reported."""
    config = IdleConfig(
        idle_threshold_seconds=5,
        grace_period_seconds=0
    )
    monitor = IdleMonitor(config)

    # Record some activity
    monitor.record_activity()
    monitor.record_activity()
    monitor.record_activity()

    metrics = monitor.get_metrics()

    assert 'idle_duration_seconds' in metrics
    assert 'is_idle' in metrics
    assert 'idle_threshold_seconds' in metrics
    assert 'request_count_total' in metrics
    assert 'uptime_seconds' in metrics
    assert 'last_activity_timestamp' in metrics
    assert 'auto_scale_enabled' in metrics

    assert metrics['request_count_total'] == 3
    assert metrics['idle_threshold_seconds'] == 5
    assert metrics['auto_scale_enabled'] is True
    assert not metrics['is_idle']  # Should not be idle yet


def test_idle_monitor_callback():
    """Test idle callback is invoked when idle."""
    config = IdleConfig(
        idle_threshold_seconds=1,
        check_interval_seconds=1,
        grace_period_seconds=0
    )
    monitor = IdleMonitor(config)

    # Track callback invocations
    callback_invoked = []

    def test_callback():
        callback_invoked.append(time.time())

    monitor.register_idle_callback(test_callback)
    monitor.start_monitoring()

    try:
        # Wait for idle detection and callback
        time.sleep(2.5)

        # Callback should have been invoked at least once
        assert len(callback_invoked) >= 1

    finally:
        monitor.stop_monitoring()


def test_idle_monitor_singleton():
    """Test get_idle_monitor returns singleton instance."""
    # Create a fresh monitor for this test (reset global)
    from src.observability import idle_monitor
    idle_monitor._global_monitor = None

    config1 = IdleConfig(idle_threshold_seconds=100)
    monitor1 = get_idle_monitor(config1)

    # Second call should return same instance
    monitor2 = get_idle_monitor()

    assert monitor1 is monitor2
    # Config should be from first call
    assert monitor1.config.idle_threshold_seconds == 100

    # Reset for other tests
    idle_monitor._global_monitor = None


def test_idle_monitor_start_stop():
    """Test monitor can be started and stopped cleanly."""
    config = IdleConfig()
    monitor = IdleMonitor(config)

    # Start monitoring
    monitor.start_monitoring()
    assert monitor._running is True
    assert monitor._monitor_thread is not None

    # Stop monitoring
    monitor.stop_monitoring()
    assert monitor._running is False

    # Should be able to restart
    monitor.start_monitoring()
    assert monitor._running is True

    # Cleanup
    monitor.stop_monitoring()
