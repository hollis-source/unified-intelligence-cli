"""Batch processing for Project Builder.

Implements Research → Plan → Implement architecture for 3–4x throughput by
processing multiple projects concurrently with shared LLM rate limiting.

Notes:
- Uses a token-bucket RateLimiter and a concurrency gate to respect provider
  rate limits while maximizing utilization.
- Creates per-project SQLite state DBs to avoid write-lock contention.
- Reuses provider instances via a small pool to reduce setup overhead.

This module is intentionally dependency-light and mirrors component wiring in
src/project_builder/cli/command.py to avoid tight coupling with CLI.
"""

from __future__ import annotations

import asyncio
import json
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

from src.interfaces import (
    ITextGenerator,
    ProjectResult,
)

# Metrics file path
BATCH_METRICS_PATH = Path.home() / ".claude" / "batch_metrics.json"


def _load_batch_metrics() -> Dict:
    """Load batch processing metrics."""
    try:
        if BATCH_METRICS_PATH.exists():
            with open(BATCH_METRICS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "total_batches": 0,
        "total_projects": 0,
        "batch_latencies": [],
        "throughputs": [],  # projects/sec per batch
    }


def _save_batch_metrics(metrics: Dict) -> None:
    """Save batch processing metrics."""
    try:
        BATCH_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BATCH_METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


def _update_batch_metric(num_projects: int, batch_latency_s: float) -> None:
    """Record batch processing metrics."""
    metrics = _load_batch_metrics()
    metrics["total_batches"] = metrics.get("total_batches", 0) + 1
    metrics["total_projects"] = metrics.get("total_projects", 0) + num_projects

    latencies = metrics.get("batch_latencies", [])
    latencies.append(batch_latency_s)
    metrics["batch_latencies"] = latencies[-100:]  # Keep last 100

    if batch_latency_s > 0:
        throughput = num_projects / batch_latency_s
        throughputs = metrics.get("throughputs", [])
        throughputs.append(throughput)
        metrics["throughputs"] = throughputs[-100:]

    _save_batch_metrics(metrics)


from src.factories.provider_factory import ProviderFactory
from src.factories.team_factory import TeamFactory
from src.routing.team_router import TeamRouter
from src.routing.summary_repository import ModelSummaryRepository
from src.routing.adaptive_selector import AdaptiveModelSelector
from src.adapters.files import LocalBackend, SSHBackend, UnifiedFileStore
from src.adapters.mcp.paramiko_ssh_adapter import create_paramiko_ssh_adapter
from src.project_builder import (
    ProjectOrchestrator,
    ProjectStateManager,
    create_state_repository,
    GoalDecomposer,
    HTNDSLTranslator,
)
from src.project_builder.execution.resource_resolver import ResourceResolver


@dataclass
class ProjectSpec:
    goal: str
    project_id: str
    model: str = "auto"
    parallel: bool = True
    prompt_mode: str = "manual"
    state_db_dir: str = "data"
    output_dir: str = "projects"
    remote_host: Optional[str] = None


class RateLimiter:
    """Simple token-bucket limiter for requests/sec with burst capacity.

    Thread-safe and compatible with synchronous provider.generate calls.
    """

    def __init__(self, rate_per_sec: float, burst: Optional[int] = None):
        self.rate = max(rate_per_sec, 0.001)
        self.capacity = max(int(burst or rate_per_sec), 1)
        self.tokens = self.capacity
        self.lock = threading.Lock()
        self.last = time.monotonic()

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last
            refill = elapsed * self.rate
            if refill > 0:
                self.tokens = min(self.capacity, self.tokens + refill)
                self.last = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Need to wait; compute time to next token
            needed = 1 - self.tokens
            wait_s = needed / self.rate

        # Sleep outside lock to avoid blocking other waiters
        time.sleep(max(wait_s, 0.0))
        # After sleeping, try again recursively (small, bounded recursion)
        self.acquire()


class RateLimitedProvider(ITextGenerator):
    """ITextGenerator wrapper that enforces global rate limiting and backoff.

    Also gates max concurrent in-flight requests via an asyncio.Semaphore shared
    across instances.
    """

    def __init__(
        self,
        inner: ITextGenerator,
        limiter: RateLimiter,
        concurrency_gate: asyncio.Semaphore,
        backoff_base_s: float = 0.5,
        backoff_max_s: float = 8.0,
        max_retries: int = 3,
    ) -> None:
        self.inner = inner
        self.limiter = limiter
        self.gate = concurrency_gate
        self.backoff_base_s = backoff_base_s
        self.backoff_max_s = backoff_max_s
        self.max_retries = max_retries

    def generate(self, messages, config=None) -> str:  # type: ignore[override]
        attempt = 0
        # Global RPS limiting
        while True:
            self.limiter.acquire()

            # Concurrency gate: acquire (may block event loop; acceptable due to sync provider)
            loop = None
            try:
                self.gate.acquire_nowait()
            except AttributeError:
                # Python <3.12 fallback
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.gate.acquire())
            except Exception:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.gate.acquire())

            try:
                return self.inner.generate(messages=messages, config=config)
            except Exception as e:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                msg = str(e).lower()
                if ("rate" in msg and "limit" in msg) or ("429" in msg):
                    delay = min(self.backoff_base_s * (2 ** (attempt - 1)), self.backoff_max_s)
                    time.sleep(delay)
                    continue
                raise
            finally:
                try:
                    self.gate.release()
                except Exception:
                    pass


class LLMConnectionPool:
    """Simple pool of provider instances sharing a limiter and concurrency gate."""

    def __init__(self, provider_name: str, size: int, rps: float, concurrency: int):
        self.size = max(1, size)
        self._factory = ProviderFactory()
        self._providers: List[ITextGenerator] = []
        self._limiter = RateLimiter(rate_per_sec=rps, burst=int(rps))
        self._gate = asyncio.Semaphore(concurrency)

        for _ in range(self.size):
            base = self._factory.create_provider(provider_name, {"timeout": 600})
            wrapped = RateLimitedProvider(base, self._limiter, self._gate)
            self._providers.append(wrapped)

        self._rr = 0
        self._lock = threading.Lock()

    def acquire(self) -> ITextGenerator:
        with self._lock:
            prov = self._providers[self._rr]
            self._rr = (self._rr + 1) % self.size
            return prov


class ProjectBatchProcessor:
    """Batch processor for concurrent multi-project execution."""

    def __init__(
        self,
        max_workers: int = 4,
        llm_pool_size: int = 4,
        llm_rps: float = 4.0,
        llm_max_concurrency: int = 8,
    ) -> None:
        self.max_workers = max(1, max_workers)
        self.llm_pool_size = max(1, llm_pool_size)
        self.llm_rps = max(0.1, llm_rps)
        self.llm_max_concurrency = max(1, llm_max_concurrency)

        # Pool created lazily per model name to allow heterogeneous batches
        self._pools: dict[str, LLMConnectionPool] = {}

        # Project-level gate to cap concurrent active projects
        self._project_gate = asyncio.Semaphore(self.max_workers)

    async def process_batch(self, projects: List[ProjectSpec]) -> List[ProjectResult]:
        start = time.time()

        async def run_one(spec: ProjectSpec) -> ProjectResult:
            async with self._project_gate:
                return await self._process_single_project(spec)

        results = await asyncio.gather(*(run_one(p) for p in projects), return_exceptions=False)

        batch_latency_s = time.time() - start
        self.total_time_s = batch_latency_s  # type: ignore[attr-defined]
        self.num_projects = len(results)  # type: ignore[attr-defined]

        # Record batch processing metrics
        _update_batch_metric(len(results), batch_latency_s)

        return results

    async def _process_single_project(self, spec: ProjectSpec) -> ProjectResult:
        # Create per-project state DB to avoid SQLite write-lock contention
        state_db_dir = Path(spec.state_db_dir)
        state_db_dir.mkdir(parents=True, exist_ok=True)
        state_db_path = state_db_dir / f"{spec.project_id}.db"

        state_repo = create_state_repository(state_db_path=str(state_db_path))
        state_manager = ProjectStateManager(state_repo)

        # LLM provider via shared pool (per model)
        pool = self._pools.get(spec.model)
        if pool is None:
            pool = LLMConnectionPool(
                provider_name=spec.model,
                size=self.llm_pool_size,
                rps=self.llm_rps,
                concurrency=self.llm_max_concurrency,
            )
            self._pools[spec.model] = pool

        llm_provider = pool.acquire()

        # Goal decomposer & HTN-DSL
        goal_decomposer = GoalDecomposer(llm_provider)
        htn_dsl_translator = HTNDSLTranslator(enable_parallel=spec.parallel)

        # Teams, routing, model selector
        team_factory = TeamFactory()
        teams = team_factory.create_scaled_teams()
        team_router = TeamRouter()
        summary_repo = ModelSummaryRepository()
        model_selector = AdaptiveModelSelector(summary_repo=summary_repo)

        # Optional SSH
        remote_fs = None
        if spec.remote_host:
            remote_fs = create_paramiko_ssh_adapter(default_host=spec.remote_host)
            await remote_fs.connect()

        # File stores and resource resolver
        backends = [LocalBackend()]
        if remote_fs:
            backends.append(SSHBackend(remote_fs))
        file_store = UnifiedFileStore(backends)
        resource_resolver = ResourceResolver(file_store)

        # Coordinator and orchestrator
        from src.project_builder.execution.coordinator import ExecutionCoordinator

        coordinator = ExecutionCoordinator(
            team_router=team_router,
            model_selector=model_selector,
            teams=teams,
            llm_provider=llm_provider,
            prompt_mode=spec.prompt_mode,
            remote_fs=remote_fs,
            resource_resolver=resource_resolver,
        )

        orchestrator = ProjectOrchestrator(
            goal_decomposer=goal_decomposer,
            htn_dsl_translator=htn_dsl_translator,
            state_manager=state_manager,
            execution_coordinator=coordinator,
        )

        # Execute and persist artifacts to output dir
        result = await orchestrator.execute_project(goal=spec.goal, project_id=spec.project_id)

        out_dir = Path(spec.output_dir) / spec.project_id
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, data in (result.artifacts or {}).items():
            (out_dir / name).write_text(str(data))

        # Close remote connection if any
        if remote_fs:
            try:
                await remote_fs.close()
            except Exception:
                pass

        return result
