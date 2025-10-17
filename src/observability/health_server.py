from __future__ import annotations

import json
import threading
import time
import os
import stat
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest
from urllib.parse import quote


class HealthMetricsHandler(BaseHTTPRequestHandler):
    server_ref: 'HealthServer' = None  # type: ignore

    def log_message(self, format: str, *args) -> None:  # noqa: N802
        # Silence default logging in tests
        return

    def _send_json(self, payload: Dict[str, Any], code: int = 200) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, code: int = 200) -> None:
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _aggregate_status(_cls, services: List[Dict[str, Any]]) -> str:  # accepts class for tests
        if not services:
            return "down"
        # If database is down, overall is down
        for s in services:
            if s.get("name") == "db" and not s.get("ok", False):
                return "down"
        oks = [s.get("ok", False) for s in services]
        if all(oks):
            return "ok"
        if any(oks):
            return "degraded"
        return "down"

    @staticmethod
    def _check_surrealdb(_cls, timeout_ms: int = 800) -> Dict[str, Any]:
        url = os.environ.get("SURREALDB_URL")
        try:
            if not url:
                raise ValueError("no_url")
            with urlrequest.urlopen(url, timeout=timeout_ms / 1000.0) as resp:
                ok = getattr(resp, "status", 0) == 200
            return {"name": "db", "ok": ok}
        except Exception as e:
            return {"name": "db", "ok": False, "reason": str(e)}

    @staticmethod
    def _check_redis(_cls, timeout_ms: int = 800) -> Dict[str, Any]:
        try:
            import redis  # type: ignore
        except Exception:
            redis = None  # type: ignore
        try:
            url = os.environ.get("REDIS_URL")
            if not url:
                host = os.environ.get("REDIS_HOST", "localhost")
                port = int(os.environ.get("REDIS_PORT", "6379"))
                password_file = os.environ.get("REDIS_PASSWORD_FILE")
                password = None
                if password_file and os.path.exists(password_file):
                    try:
                        password = open(password_file, "r", encoding="utf-8").read().strip()
                    except Exception:
                        password = None
                auth_part = f":{quote(password)}@" if password else ""
                url = f"redis://{auth_part}{host}:{port}/0"
            if not redis:
                raise RuntimeError("redis_not_installed")
            client = redis.from_url(url, socket_timeout=timeout_ms / 1000.0, socket_connect_timeout=timeout_ms / 1000.0)
            client.ping()
            return {"name": "cache", "ok": True}
        except Exception as e:
            return {"name": "cache", "ok": False, "reason": str(e)}

    @staticmethod
    def _check_ssh(_cls) -> Dict[str, Any]:
        path = os.environ.get("PB_SSH_KEY_PATH")
        if not path or not os.path.exists(path):
            return {"name": "ssh", "ok": False, "reason": "key_not_found"}
        try:
            mode = os.stat(path).st_mode
            # Require 0o600 or stricter
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                return {"name": "ssh", "ok": False, "reason": f"insecure_perms_{oct(stat.S_IMODE(mode))}"}
            return {"name": "ssh", "ok": True}
        except Exception as e:
            return {"name": "ssh", "ok": False, "reason": str(e)}

    def _check_services(self, timeout_ms: int = 800) -> List[Dict[str, Any]]:
        return [
            self._check_surrealdb(HealthMetricsHandler, timeout_ms),
            self._check_redis(HealthMetricsHandler, timeout_ms),
            self._check_ssh(HealthMetricsHandler),
        ]

    def do_GET(self) -> None:  # noqa: N802
        server: HealthServer = self.server_ref
        if self.path.startswith("/ready"):
            if server._ready:
                self._send_json({"ready": True, "timestamp": time.time()})
            else:
                # 503 when not ready
                self._send_json({"ready": False, "timestamp": time.time()}, code=503)
            return

        if self.path.startswith("/health"):
            services = self._check_services()
            status = self._aggregate_status(HealthMetricsHandler, services)
            body = {
                "status": status,
                "services": services,
                "uptime_seconds": time.time() - server._start_time,
                "version": "1.0",
                "timestamp": time.time(),
            }
            code = 200 if status in ("ok", "degraded") else 503
            self._send_json(body, code=code)
            return

        if self.path.startswith("/metrics"):
            uptime = time.time() - server._start_time
            text = (
                "# HELP project_builder_uptime_seconds Uptime of the project builder service in seconds\n"
                "# TYPE project_builder_uptime_seconds gauge\n"
                f"project_builder_uptime_seconds {uptime:.3f}\n"
            )
            # Append extra metrics if present
            names_map = {
                "projects_total": "project_builder_projects_total",
                "projects_success": "project_builder_projects_success",
                "projects_failed": "project_builder_projects_failed",
                "tasks_total": "project_builder_tasks_total",
                "tasks_completed": "project_builder_tasks_completed",
                "artifacts_total": "project_builder_artifacts_total",
                "avg_quality_score": "project_builder_quality_score_avg",
                "total_execution_time_s": "project_builder_execution_time_seconds_total",
            }
            extras = getattr(HealthServer, "_extra_metrics", {}) or {}
            for k, v in extras.items():
                if k in names_map:
                    text += f"{names_map[k]} {v}\n"
            self._send_text(text)
            return

        # Not found
        self.send_error(404)


class HealthServer:
    _extra_metrics: Dict[str, Any] = {}

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._ready: bool = False
        self._start_time: float = time.time()

    @classmethod
    def update_metrics(cls, metrics: Dict[str, Any]) -> None:
        cls._extra_metrics = dict(metrics or {})

    def start(self) -> None:
        def handler(*args, **kwargs):
            h = HealthMetricsHandler(*args, **kwargs)
            return h

        self.server = HTTPServer((self.host, self.port), handler)  # type: ignore[arg-type]
        HealthMetricsHandler.server_ref = self

        def run():
            assert self.server is not None
            self.server.serve_forever(poll_interval=0.1)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def set_ready(self, ready: bool) -> None:
        self._ready = ready

