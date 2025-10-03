"""
Team-based Agent Selector - Routes via teams.

Week 12: Adapter for team-based routing in composition root.

Clean Architecture: Adapter layer, implements IAgentSelector interface.
"""

import logging
from typing import List, Optional
from src.entities import Task, Agent, AgentTeam
from src.interfaces import IAgentSelector
from src.routing.team_router import TeamRouter


logger = logging.getLogger(__name__)


class TeamBasedSelector(IAgentSelector):
    """
    Team-based agent selector.

    Week 12: Implements IAgentSelector interface using team routing.

    Strategy:
    - Uses TeamRouter for two-phase routing (task → team → agent)
    - Stores teams internally
    - Returns individual agents (for backward compatibility with use cases)

    Clean Code: Adapter pattern - adapts TeamRouter to IAgentSelector interface.
    """

    def __init__(self, teams: List[AgentTeam], team_router: Optional[TeamRouter] = None):
        """
        Initialize team-based selector.

        Args:
            teams: Available agent teams
            team_router: Optional team router (creates default if not provided, Week 13: allows metrics injection)
        """
        self.teams = teams
        self.router = team_router or TeamRouter()
        logger.info(f"TeamBasedSelector initialized with {len(teams)} teams")

    def select_agent(self, task: Task, agents: List[Agent]) -> Optional[Agent]:
        """
        Select agent for task using team routing.

        Implements IAgentSelector interface.

        Args:
            task: Task to route
            agents: Available agents (ignored, uses teams instead)

        Returns:
            Selected agent from appropriate team

        Note: agents parameter is ignored because team routing uses teams.
        This maintains interface compatibility while using team-based logic.
        """
        try:
            agent = self.router.route(task, self.teams)
            return agent
        except ValueError as e:
            logger.error(f"Team routing failed: {e}")
            return None
