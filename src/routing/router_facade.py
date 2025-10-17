"""Routing Facade

Unifies domain classification and hierarchical routing behind a stable, minimal
interface for use by adapters (e.g., DSL CLITaskExecutor) without exposing
internal router details.

Clean Architecture:
- Use Case/Adapter boundary helper (no heavy dependencies)
- DIP: depends on provided classifier/router abstractions via duck typing

This does NOT import concrete router implementations to avoid hard coupling
and circular imports. Pass concrete instances when constructing RouterFacade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RoutingDecision:
    """Stable structure capturing a routing decision outcome."""
    selected_agent: Optional[Any]
    # High-level metadata (best-effort; may be None if provider doesn't supply)
    domain: Optional[str] = None
    tier: Optional[int] = None
    mode: Optional[str] = None  # e.g., "hierarchical", "flat"
    scores: Dict[str, float] = field(default_factory=dict)
    top_candidates: List[Any] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class RouterFacade:
    """Lightweight facade over domain classifier + hierarchical router.

    Expected duck-typed interfaces:
    - classifier.classify(task) -> str | dict (returns domain or richer info)
    - router.route(task, agents, domain=...) -> (agent, metadata: dict)

    Both components are optional. If none are provided, the facade will pick the
    first agent as a trivial fallback.
    """

    def __init__(self, classifier: Any = None, router: Any = None):
        self._classifier = classifier
        self._router = router

    def route(self, task: Any, agents: List[Any]) -> RoutingDecision:
        """Select an agent for the given task and return decision metadata.

        Args:
            task: Task-like object or dict with at least a description/name
            agents: Available agent objects
        """
        domain = None
        classification: Any = None
        if self._classifier is not None and hasattr(self._classifier, "classify"):
            try:
                classification = self._classifier.classify(task)
                # Accept either a string domain or a richer dict
                if isinstance(classification, str):
                    domain = classification
                elif isinstance(classification, dict):
                    domain = classification.get("domain")
            except Exception:
                # Non-fatal: fall back to None domain
                classification = None
                domain = None

        selected_agent = None
        meta: Dict[str, Any] = {}
        if self._router is not None and hasattr(self._router, "route"):
            try:
                selected_agent, meta = self._router.route(task, agents, domain=domain)
            except Exception:
                selected_agent = agents[0] if agents else None
                meta = {}
        else:
            selected_agent = agents[0] if agents else None

        # Normalize metadata into RoutingDecision
        tier = meta.get("tier") if isinstance(meta, dict) else None
        mode = meta.get("mode") if isinstance(meta, dict) else None
        scores = meta.get("scores", {}) if isinstance(meta, dict) else {}
        top_candidates = meta.get("top_candidates", []) if isinstance(meta, dict) else []

        extra: Dict[str, Any] = {}
        # Preserve raw classification and meta for debugging/observability
        if classification is not None:
            extra["classification"] = classification
        if isinstance(meta, dict):
            # Copy any additional keys that aren't normalized
            for k, v in meta.items():
                if k not in {"tier", "mode", "scores", "top_candidates"}:
                    extra.setdefault("router_meta", {})[k] = v

        return RoutingDecision(
            selected_agent=selected_agent,
            domain=domain,
            tier=tier,
            mode=mode,
            scores=scores,
            top_candidates=top_candidates,
            extra=extra,
        )

    def route_batch(self, tasks: List[Any], agents: List[Any]) -> List[RoutingDecision]:
        """Route a batch of tasks. Simple convenience wrapper."""
        return [self.route(task, agents) for task in tasks]

