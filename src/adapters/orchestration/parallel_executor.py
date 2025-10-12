"""
Parallel Agent Executor

Runs potentially blocking agent executions on a worker pool to enable true
parallelism under asyncio.gather().

Design:
- Decorator over an existing IAgentExecutor (e.g., LLMAgentExecutor)
- Offloads each execute() call to a ThreadPool so event loop isn't blocked
- Safe default (threads). ProcessPool is risky due to pickling provider state

Target speedup: 3-5x for independent agent tasks that perform blocking I/O
"""

from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict

from src.entities import Agent, Task, ExecutionResult, ExecutionContext
from src.interfaces import IAgentExecutor

# Metrics file path
PARALLEL_METRICS_PATH = Path.home() / ".claude" / "parallel_metrics.json"


def _load_parallel_metrics() -> Dict:
    """Load parallel execution metrics."""
    try:
        if PARALLEL_METRICS_PATH.exists():
            with open(PARALLEL_METRICS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "total_executions": 0,
        "execution_latencies": [],
        "concurrent_executions": 0,
    }


def _save_parallel_metrics(metrics: Dict) -> None:
    """Save parallel execution metrics."""
    try:
        PARALLEL_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PARALLEL_METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


def _update_parallel_metric(latency_ms: float) -> None:
    """Record parallel execution with latency."""
    metrics = _load_parallel_metrics()
    metrics["total_executions"] = metrics.get("total_executions", 0) + 1
    latencies = metrics.get("execution_latencies", [])
    latencies.append(latency_ms)
    metrics["execution_latencies"] = latencies[-100:]  # Keep last 100
    _save_parallel_metrics(metrics)


class ParallelAgentExecutor(IAgentExecutor):
    """
    Wraps a base IAgentExecutor and executes it on a thread pool.

    Rationale: Many provider calls are synchronous (blocking). When used with
    asyncio.gather(), such blocking code prevents concurrency. By offloading
    each call to a thread, we allow multiple agent executions to progress in
    parallel, delivering significant wall-clock speedups.
    """

    def __init__(self, base_executor: IAgentExecutor, max_workers: int = 4):
        self._base = base_executor
        # Single shared pool across calls for efficiency
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="agent-exec")

    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute using base executor on a background thread.

        Notes:
        - base_executor.execute is async; we run it inside a fresh loop in the
          worker thread via asyncio.run().
        - Return value is proxied back to the caller's event loop.
        """
        start_time = time.time()

        def _run_sync() -> ExecutionResult:
            # Create and run an event loop in the worker thread
            async def _run() -> ExecutionResult:
                return await self._base.execute(agent=agent, task=task, context=context)

            return asyncio.run(_run())

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(self._pool, _run_sync)

        # Record execution latency
        latency_ms = (time.time() - start_time) * 1000
        _update_parallel_metric(latency_ms)

        return result

