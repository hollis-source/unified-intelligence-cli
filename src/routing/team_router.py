"""
Team Router - Routes tasks to teams, teams route internally to agents.

Week 12: Simplified two-phase routing architecture.

Clean Architecture: Strategy pattern for team-based routing.
"""

import logging
from typing import List, Optional
from src.entities import Task, Agent, AgentTeam
from src.routing.domain_classifier import DomainClassifier


logger = logging.getLogger(__name__)


class TeamRouter:
    """
    Routes tasks to teams using two-phase strategy.

    Week 12: Core router for team-based agent architecture.

    Routing Strategy:
        Phase 1: Route task to appropriate team (domain-based)
        Phase 2: Team routes internally to specific agent

    Benefits vs Individual Agent Routing:
    - 50% fewer routing decisions (7 teams vs 12 agents)
    - Encapsulated team logic (team knows best how to distribute work)
    - Reduced overlap issues (teams handle nuanced differences)
    - Better scalability (add agents to teams, not router)

    Clean Code: Single responsibility - team selection only.
    """

    def __init__(self, domain_classifier: Optional[DomainClassifier] = None):
        """
        Initialize team router.

        Args:
            domain_classifier: Classifier for domain detection (optional, creates default)
        """
        self.domain_classifier = domain_classifier or DomainClassifier()
        logger.info("TeamRouter initialized (two-phase routing)")

    def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
        """
        Route task to agent via two-phase strategy.

        Phase 1: Select team based on domain
        Phase 2: Team's internal routing selects specific agent

        Args:
            task: Task to route
            teams: Available agent teams

        Returns:
            Selected agent (from chosen team)

        Raises:
            ValueError: If no suitable team/agent found

        Strategy:
            1. Classify task domain
            2. Find team matching domain
            3. Let team route internally to agent
        """
        # Phase 1: Route to team
        team = self._select_team(task, teams)
        logger.debug(f"Task routed to team: {team.name}")

        # Phase 2: Team's internal routing
        agent = team.route_internally(task)

        if not agent:
            raise ValueError(
                f"Team '{team.name}' could not route task: '{task.description[:50]}...'. "
                f"This is likely a bug in team's internal routing logic."
            )

        logger.info(
            f"Task '{task.description[:50]}...' → {team.name} → {agent.role}"
        )
        return agent

    def _select_team(self, task: Task, teams: List[AgentTeam]) -> AgentTeam:
        """
        Select team based on task domain.

        Week 12: Simple domain → team mapping.

        Strategy:
            1. Classify task domain (8 domains)
            2. Find team with matching domain
            3. Fallback to orchestration team for general/unknown

        Args:
            task: Task to route
            teams: Available teams

        Returns:
            Selected team

        Raises:
            ValueError: If no suitable team found
        """
        # Classify task domain
        domain = self.domain_classifier.classify(task)
        logger.debug(f"Task classified as domain: {domain}")

        # Direct domain → team mapping
        domain_to_team = {
            "frontend": "Frontend",
            "backend": "Backend",
            "testing": "Testing",
            "devops": "Infrastructure",
            "research": "Research",
            "documentation": "Research",  # Documentation → Research team
            "security": "Backend",  # Security → Backend team (for now)
            "performance": "Backend",  # Performance → Backend team (for now)
            "general": "Orchestration"  # General → Orchestration team
        }

        target_team_name = domain_to_team.get(domain, "Orchestration")

        # Find team by name
        team = self._get_team_by_name(teams, target_team_name)
        if team:
            return team

        # Fallback 1: Try domain match
        team = self._get_team_by_domain(teams, domain)
        if team:
            logger.debug(f"Fallback: Found team by domain '{domain}'")
            return team

        # Fallback 2: Orchestration team (general purpose)
        orchestration_team = self._get_orchestration_team(teams)
        if orchestration_team:
            logger.warning(
                f"No specific team for domain '{domain}', using Orchestration team"
            )
            return orchestration_team

        # Fallback 3: First team that can handle task
        for team in teams:
            if team.can_handle(task):
                logger.warning(
                    f"Using first team that can handle: {team.name}"
                )
                return team

        # No suitable team found
        raise ValueError(
            f"No suitable team found for task: '{task.description[:50]}...'. "
            f"Domain: '{domain}'. Available teams: {[t.name for t in teams]}"
        )

    def _get_team_by_name(self, teams: List[AgentTeam], name: str) -> Optional[AgentTeam]:
        """Get team by name."""
        return next((team for team in teams if team.name == name), None)

    def _get_team_by_domain(self, teams: List[AgentTeam], domain: str) -> Optional[AgentTeam]:
        """Get team by domain."""
        return next((team for team in teams if team.domain == domain), None)

    def _get_orchestration_team(self, teams: List[AgentTeam]) -> Optional[AgentTeam]:
        """Get orchestration team (fallback)."""
        return next(
            (team for team in teams if team.name == "Orchestration" or team.domain == "general"),
            None
        )

    def route_batch(self, tasks: List[Task], teams: List[AgentTeam]) -> List[tuple]:
        """
        Route multiple tasks to teams/agents.

        Args:
            tasks: Tasks to route
            teams: Available teams

        Returns:
            List of (task, team, agent) tuples
        """
        results = []
        for task in tasks:
            try:
                agent = self.route(task, teams)
                # Find which team this agent belongs to
                team = next((t for t in teams if agent in t.agents), None)
                results.append((task, team, agent))
            except ValueError as e:
                logger.error(f"Failed to route task: {e}")
                results.append((task, None, None))

        return results

    def get_routing_stats(self, tasks: List[Task], teams: List[AgentTeam]) -> dict:
        """
        Get routing statistics for batch of tasks.

        Args:
            tasks: Tasks to analyze
            teams: Available teams

        Returns:
            Dict with routing statistics
        """
        routes = self.route_batch(tasks, teams)

        # Team distribution
        team_counts = {}
        for _, team, _ in routes:
            if team:
                team_counts[team.name] = team_counts.get(team.name, 0) + 1

        # Agent utilization
        agent_counts = {}
        for _, _, agent in routes:
            if agent:
                agent_counts[agent.role] = agent_counts.get(agent.role, 0) + 1

        # Tier distribution
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, _, agent in routes:
            if agent:
                tier_counts[agent.tier] += 1

        # Success rate
        successful = sum(1 for _, team, agent in routes if team and agent)
        success_rate = (successful / len(tasks) * 100) if tasks else 0

        return {
            "total_tasks": len(tasks),
            "successful_routes": successful,
            "success_rate": success_rate,
            "team_distribution": team_counts,
            "agent_utilization": agent_counts,
            "tier_distribution": tier_counts,
            "unique_teams_used": len(team_counts),
            "unique_agents_used": len(agent_counts)
        }
