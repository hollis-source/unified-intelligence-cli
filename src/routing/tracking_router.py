"""
TrackingTeamRouter: wraps TeamRouter to persist baseline routing decisions behind a flag.

Design:
- Extends TeamRouter and calls SurrealDBStore.store_routing_decision after routing
- Safe: best-effort, failures are logged and do not affect routing
- Strategy recorded as "baseline" with rag_used=False
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Optional, Any

from src.entity import Task, Agent, AgentTeam
from src.routing.team_router import TeamRouter

logger = logging.getLogger(__name__)


class TrackingTeamRouter(TeamRouter):
    def __init__(self, domain_classifier, db_store: Any):
        super().__init__(domain_classifier)
        self.db_store = db_store

    def _find_team_for_agent(self, teams: List[AgentTeam], agent: Agent) -> Optional[AgentTeam]:
        return next((t for t in teams if agent in getattr(t, "agents", [])), None)

    def _run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop to avoid RuntimeError in running loop
                new_loop = asyncio.new_event_loop()
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No current event loop
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
        agent = super().route(task, teams)
        # Best-effort tracking (do not fail routing if store call fails)
        try:
            if not getattr(self, "db_store", None):
                return agent
            domain = getattr(self, "_last_classified_domain", "")
            team = self._find_team_for_agent(teams, agent)
            confidence = float(getattr(self.domain_classifier, "last_classification_score", 0.0) or 0.0)
            self._run_async(
                self.db_store.store_routing_decision(
                    task_id=getattr(task, "task_id", ""),
                    task_description=task.description,
                    task_domain=domain,
                    selected_agent=agent.role,
                    selected_team=getattr(team, "name", None),
                    routing_strategy="baseline",
                    confidence=confidence,
                    success=None,
                    actual_agent=agent.role,
                    fallback_used=False,
                    metadata={
                        "rag_used": False,
                        "pattern_count": 0,
                        "routing_hints": {},
                    },
                )
            )
        except Exception as e:
            logger.debug(f"Baseline tracking failed (non-fatal): {e}")
        return agent

