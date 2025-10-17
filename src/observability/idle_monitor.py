from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class IdleConfig:
    idle_threshold_seconds: int = 300
    check_interval_seconds: int = 30
    grace_period_seconds: int = 60
    enable_auto_scale: bool = True


class IdleMonitor:
    def __init__(self, config: IdleConfig) -> None:
        self.config = config
        self._last_activity: float = time.time()
        self._start_time: float = time.time()
        self._request_count: int = 0
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[], None]] = []

    def record_activity(self) -> None:
        self._last_activity = time.time()
        self._request_count += 1

    def get_idle_duration(self) -> float:
        return max(0.0, time.time() - self._last_activity)

    def is_idle(self) -> bool:
        # During grace period after start, never consider idle
        if (time.time() - self._start_time) < self.config.grace_period_seconds:
            return False
        return (time.time() - self._last_activity) >= self.config.idle_threshold_seconds

    def get_metrics(self) -> dict:
        now = time.time()
        return {
            'idle_duration_seconds': max(0.0, now - self._last_activity),
            'is_idle': self.is_idle(),
            'idle_threshold_seconds': self.config.idle_threshold_seconds,
            'request_count_total': self._request_count,
            'uptime_seconds': now - self._start_time,
            'last_activity_timestamp': self._last_activity,
            'auto_scale_enabled': self.config.enable_auto_scale,
        }

    def register_idle_callback(self, cb: Callable[[], None]) -> None:
        self._callbacks.append(cb)

    def _run_loop(self) -> None:
        # Respect grace period on start
        start = time.time()
        while self._running:
            if (time.time() - start) < self.config.grace_period_seconds:
                time.sleep(min(0.1, self.config.check_interval_seconds))
                continue
            if self.is_idle():
                for cb in list(self._callbacks):
                    try:
                        cb()
                    except Exception:
                        pass
            time.sleep(self.config.check_interval_seconds)

    def start_monitoring(self) -> None:
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)


_global_monitor: Optional[IdleMonitor] = None


def get_idle_monitor(config: Optional[IdleConfig] = None) -> IdleMonitor:
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = IdleMonitor(config or IdleConfig())
    return _global_monitor

