"""
Prompt metrics store adapters (Phase 4: SurrealDB Metrics Integration).

Clean Architecture: Adapter layer
- NoOpPromptMetricsStore: default no-op
- InMemoryPromptMetricsStore: testing
- SurrealDBPromptMetricsStore: optional HTTP-based writer (stdlib only)
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import asdict
from typing import List, Optional
from urllib import request, error

from src.interface.prompt_metrics_store import IPromptMetricsStore, PromptMetrics

logger = logging.getLogger(__name__)


class NoOpPromptMetricsStore(IPromptMetricsStore):
    """No-op metrics store (default)."""

    def log(self, metrics: PromptMetrics) -> None:
        logger.debug("NoOp store: metrics ignored")

    def health(self) -> bool:
        return True


class InMemoryPromptMetricsStore(IPromptMetricsStore):
    """In-memory metrics store for tests and local dev."""

    def __init__(self) -> None:
        self._records: List[PromptMetrics] = []

    def log(self, metrics: PromptMetrics) -> None:
        self._records.append(metrics)

    def health(self) -> bool:
        return True

    # Convenience for tests
    def count(self) -> int:
        return len(self._records)

    def last(self) -> Optional[PromptMetrics]:
        return self._records[-1] if self._records else None


class SurrealDBPromptMetricsStore(IPromptMetricsStore):
    """
    Minimal SurrealDB HTTP client using stdlib (no third-party deps).

    Auth: Basic auth with username/password.
    API: /sql endpoint with CONTENT application/json and SQL insert.

    Note: This is best-effort and optional. Prefer a dedicated client in production.
    """

    def __init__(
        self,
        base_url: str,
        namespace: str,
        database: str,
        username: str,
        password: str,
        table: str = "prompt_metrics",
        timeout: int = 5,
    ) -> None:
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.table = table
        self.timeout = timeout
        self._health_cache: Optional[bool] = None

    def _auth_header(self) -> str:
        token = f"{self.username}:{self.password}".encode()
        return "Basic " + base64.b64encode(token).decode()

    def _sql(self, query: str, vars: Optional[dict] = None) -> bool:
        url = f"{self.base_url}/sql"
        payload = {
            "query": query,
            "vars": vars or {},
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        req.add_header("NS", self.namespace)
        req.add_header("DB", self.database)
        req.add_header("Authorization", self._auth_header())

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning(f"SurrealDB non-2xx response: {resp.status}")
                return False
        except error.URLError as e:
            logger.warning(f"SurrealDB request failed: {e}")
            return False

    def log(self, metrics: PromptMetrics) -> None:
        record = asdict(metrics)
        # Build INSERT query with parameterized vars
        query = f"CREATE {self.table} SET timestamp = $timestamp, domain = $domain, agent_type = $agent_type, template_used = $template_used, validation_score = $validation_score, specificity = $specificity, clarity = $clarity, completeness = $completeness, task_success = $task_success, metadata = $metadata;"
        ok = self._sql(query, vars=record)
        if not ok:
            logger.warning("Failed to write prompt metrics to SurrealDB")

    def health(self) -> bool:
        if self._health_cache is not None:
            return self._health_cache
        ok = self._sql("RETURN true;")
        self._health_cache = ok
        return ok

