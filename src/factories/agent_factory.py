"""Agent factory - Creates agents from configuration."""

from typing import List, Dict, Any
from src.entities import Agent
from src.interfaces import IAgentFactory


class AgentFactory(IAgentFactory):
    """
    Factory for creating agents.

    Clean Code: Extract creation logic from main.
    SRP: Single responsibility - agent creation.
    """

    def create_default_agents(self) -> List[Agent]:
        """
        Create default agent team.

        Future: Load from config file.
        """
        return [
            Agent(
                role="coder",
                capabilities=["code", "coding", "implement", "develop", "program", "refactor", "debug", "build"]
            ),
            Agent(
                role="tester",
                capabilities=["test", "testing", "validate", "verify", "qa", "quality"]
            ),
            Agent(
                role="reviewer",
                capabilities=["review", "reviewing", "analyze", "inspect", "evaluate", "approve"]
            ),
            Agent(
                role="coordinator",
                capabilities=["plan", "planning", "organize", "coordinate", "delegate", "manage"]
            ),
            Agent(
                role="researcher",
                capabilities=["research", "investigate", "study", "explore", "analyze", "document"]
            )
        ]

    def create_from_config(self, config: List[Dict[str, Any]]) -> List[Agent]:
        """
        Create agents from configuration.

        Args:
            config: List of agent configurations

        Returns:
            List of configured agents
        """
        agents = []
        for agent_config in config:
            agent = Agent(
                role=agent_config["role"],
                capabilities=agent_config["capabilities"]
            )
            agents.append(agent)
        return agents