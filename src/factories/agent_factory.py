"""Agent factory - Creates agents from configuration."""

from typing import List, Dict, Any
from src.entities import Agent


class AgentFactory:
    """
    Factory for creating agents.

    Clean Code: Extract creation logic from main.
    SRP: Single responsibility - agent creation.
    """

    @staticmethod
    def create_default_agents() -> List[Agent]:
        """
        Create default agent team.

        Future: Load from config file.
        """
        return [
            Agent(
                role="coder",
                capabilities=["code_gen", "refactor", "debug", "implement"]
            ),
            Agent(
                role="tester",
                capabilities=["test", "validate", "verify", "quality_check"]
            ),
            Agent(
                role="reviewer",
                capabilities=["review", "analyze", "approve", "suggest"]
            ),
            Agent(
                role="coordinator",
                capabilities=["plan", "organize", "delegate", "prioritize"]
            ),
            Agent(
                role="researcher",
                capabilities=["research", "analyze", "summarize", "investigate"]
            )
        ]

    @staticmethod
    def create_from_config(config: List[Dict[str, Any]]) -> List[Agent]:
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