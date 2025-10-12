"""Adapters for endpoint monitoring service.

Adapters implement interfaces and connect to external systems (HF API, Prometheus, etc.).
"""

from .hf_inference_health_adapter import HFInferenceHealthAdapter
from .hf_inference_waker import HFInferenceWaker
from .prometheus_metrics_adapter import PrometheusMetricsAdapter

__all__ = [
    "HFInferenceHealthAdapter",
    "HFInferenceWaker",
    "PrometheusMetricsAdapter",
]
