"""Cost and Usage Tracking for LLM Operations.

Sprint 1: Production Deployment - P1.3 Observability
Tracks token usage, API costs, and usage analytics per project.

Clean Architecture: Use case layer (observability concern).
SOLID: SRP - Single responsibility for cost tracking.
"""

import time
import threading
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# Model pricing (USD per 1M tokens)
# Source: Provider pricing pages as of Jan 2025
MODEL_PRICING = {
    # OpenAI
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},

    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},

    # Open source (estimated compute costs)
    "llama-2-7b": {"input": 0.10, "output": 0.10},
    "llama-2-13b": {"input": 0.20, "output": 0.20},
    "mixtral-8x7b": {"input": 0.40, "output": 0.40},
    "qwen-7b": {"input": 0.10, "output": 0.10},

    # xAI
    "grok-2": {"input": 5.00, "output": 15.00},
    "grok-beta": {"input": 5.00, "output": 15.00},

    # Default fallback
    "default": {"input": 1.00, "output": 2.00},
}


@dataclass
class UsageMetrics:
    """Metrics for a single LLM operation."""
    project_id: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


class CostTracker:
    """Tracks LLM costs and usage metrics per project.

    Thread-safe for concurrent project tracking.
    Provides Prometheus-formatted metrics export.
    """

    def __init__(self):
        """Initialize cost tracker."""
        self._lock = threading.RLock()
        self._project_metrics: Dict[str, List[UsageMetrics]] = defaultdict(list)
        self._global_tokens_input = 0
        self._global_tokens_output = 0
        self._global_cost_usd = 0.0
        self._request_count = 0
        self._error_count = 0

    def record_usage(
        self,
        project_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Record LLM usage for a project.

        Args:
            project_id: Unique project identifier
            model: Model name (e.g., "gpt-4", "claude-3-sonnet")
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            latency_ms: Request latency in milliseconds
            error: Optional error message if request failed
        """
        with self._lock:
            # Create metrics record
            metrics = UsageMetrics(
                project_id=project_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                error=error
            )

            # Store per-project
            self._project_metrics[project_id].append(metrics)

            # Update global counters
            self._global_tokens_input += input_tokens
            self._global_tokens_output += output_tokens
            self._request_count += 1

            if error:
                self._error_count += 1
            else:
                # Calculate cost
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                self._global_cost_usd += cost

            logger.debug(
                f"Cost tracking: project={project_id}, model={model}, "
                f"tokens={input_tokens + output_tokens}, latency={latency_ms:.0f}ms"
            )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage.

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        # Normalize model name (handle versioning)
        model_lower = model.lower()

        # Find pricing
        pricing = None
        for key in MODEL_PRICING:
            if key in model_lower:
                pricing = MODEL_PRICING[key]
                break

        if pricing is None:
            pricing = MODEL_PRICING["default"]
            logger.warning(f"Unknown model '{model}', using default pricing")

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_project_metrics(self, project_id: str) -> Dict:
        """Get metrics for a specific project.

        Args:
            project_id: Project identifier

        Returns:
            Dictionary with project metrics
        """
        with self._lock:
            metrics_list = self._project_metrics.get(project_id, [])

            if not metrics_list:
                return {
                    "project_id": project_id,
                    "request_count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "error_count": 0,
                }

            total_input = sum(m.input_tokens for m in metrics_list)
            total_output = sum(m.output_tokens for m in metrics_list)
            total_cost = sum(
                self._calculate_cost(m.model, m.input_tokens, m.output_tokens)
                for m in metrics_list if m.error is None
            )
            error_count = sum(1 for m in metrics_list if m.error is not None)
            avg_latency = sum(m.latency_ms for m in metrics_list) / len(metrics_list)

            return {
                "project_id": project_id,
                "request_count": len(metrics_list),
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_cost_usd": round(total_cost, 4),
                "error_count": error_count,
                "avg_latency_ms": round(avg_latency, 2),
            }

    def get_global_metrics(self) -> Dict:
        """Get global cost and usage metrics.

        Returns:
            Dictionary with global metrics
        """
        with self._lock:
            return {
                "total_requests": self._request_count,
                "total_input_tokens": self._global_tokens_input,
                "total_output_tokens": self._global_tokens_output,
                "total_tokens": self._global_tokens_input + self._global_tokens_output,
                "total_cost_usd": round(self._global_cost_usd, 4),
                "error_count": self._error_count,
                "error_rate": round(self._error_count / max(self._request_count, 1), 4),
                "project_count": len(self._project_metrics),
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        with self._lock:
            global_metrics = self.get_global_metrics()

            lines = []

            # Global metrics
            lines.extend([
                "# HELP llm_requests_total Total LLM API requests",
                "# TYPE llm_requests_total counter",
                f"llm_requests_total {global_metrics['total_requests']}",
                "",
                "# HELP llm_input_tokens_total Total input tokens consumed",
                "# TYPE llm_input_tokens_total counter",
                f"llm_input_tokens_total {global_metrics['total_input_tokens']}",
                "",
                "# HELP llm_output_tokens_total Total output tokens generated",
                "# TYPE llm_output_tokens_total counter",
                f"llm_output_tokens_total {global_metrics['total_output_tokens']}",
                "",
                "# HELP llm_cost_usd_total Total LLM cost in USD",
                "# TYPE llm_cost_usd_total counter",
                f"llm_cost_usd_total {global_metrics['total_cost_usd']}",
                "",
                "# HELP llm_errors_total Total LLM errors",
                "# TYPE llm_errors_total counter",
                f"llm_errors_total {global_metrics['error_count']}",
                "",
                "# HELP llm_error_rate LLM error rate",
                "# TYPE llm_error_rate gauge",
                f"llm_error_rate {global_metrics['error_rate']}",
                "",
                "# HELP llm_active_projects Number of projects with LLM usage",
                "# TYPE llm_active_projects gauge",
                f"llm_active_projects {global_metrics['project_count']}",
                "",
            ])

            # Per-project metrics (top 10 by cost)
            project_costs = []
            for project_id in self._project_metrics:
                pm = self.get_project_metrics(project_id)
                project_costs.append((project_id, pm['total_cost_usd']))

            project_costs.sort(key=lambda x: x[1], reverse=True)
            top_projects = project_costs[:10]

            if top_projects:
                lines.extend([
                    "# HELP llm_project_cost_usd Cost per project in USD (top 10)",
                    "# TYPE llm_project_cost_usd gauge",
                ])
                for project_id, cost in top_projects:
                    lines.append(f'llm_project_cost_usd{{project="{project_id}"}} {cost}')
                lines.append("")

            return "\n".join(lines)


# Global singleton instance
_global_tracker: Optional[CostTracker] = None
_tracker_lock = threading.Lock()


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance (singleton).

    Returns:
        Global CostTracker instance
    """
    global _global_tracker

    with _tracker_lock:
        if _global_tracker is None:
            _global_tracker = CostTracker()
        return _global_tracker
