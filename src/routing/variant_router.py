from __future__ import annotations

import asyncio
import logging
import os
from typing import List

from src.entity import Task, Agent, AgentTeam
from src.routing.bandit import EpsilonGreedyBandit

logger = logging.getLogger(__name__)


class VariantRouter:
    """
    VariantRouter: Selects between routing variants (e.g., baseline vs RAG)
    using a simple bandit for exploration/exploitation.

    Design:
    - Compose existing routers: baseline_router (e.g., TrackingTeamRouter) and rag_router (RAGTeamRouter)
    - Choose a variant each routing call; call the appropriate router
    - RAG calls are async (route_with_rag); baseline is sync; we bridge with a helper
    - Rewards can be reported back via update() when task success is known
    """

    def __init__(self, baseline_router, rag_router, epsilon: float = 0.1):
        self.baseline_router = baseline_router
        self.rag_router = rag_router
        variants = [v for v in ("baseline", "rag") if v]
        self.bandit = EpsilonGreedyBandit(variants=variants, epsilon=epsilon)

    def _run_async(self, coro):
        """Bridge synchronous route() to async route_with_rag()."""
        try:
            # Try to get the running loop
            loop = asyncio.get_running_loop()
            # If we're here, there's a running loop - create a new one in a thread
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(coro)

    def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
        # Allow overriding variant via env for debugging
        force_variant = os.getenv("RAG_FORCE_VARIANT", "").strip().lower()
        if force_variant in ("baseline", "rag"):
            variant = force_variant
        else:
            variant = self.bandit.select()

        if variant == "rag":
            try:
                agent = self._run_async(self.rag_router.route_with_rag(task, teams))
                logger.info(f"VariantRouter: chose RAG → {getattr(agent, 'role', '?')}")
                return agent
            except Exception as e:
                logger.warning(f"VariantRouter RAG failed ({e}); falling back to baseline")
                # Fall through to baseline
        agent = self.baseline_router.route(task, teams)
        logger.info(f"VariantRouter: chose BASELINE → {getattr(agent, 'role', '?')}")
        return agent

    def update(self, variant: str, success: bool) -> None:
        reward = 1.0 if success else 0.0
        self.bandit.update(variant, reward)

