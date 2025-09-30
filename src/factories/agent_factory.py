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

        Enhanced capabilities based on user simulation testing.
        Includes natural language keywords users actually use in task descriptions.

        Future: Load from config file.
        """
        return [
            Agent(
                role="coder",
                capabilities=[
                    # Core coding terms
                    "code", "coding", "program", "programming",
                    # Actions
                    "write", "create", "build", "develop", "implement", "fix",
                    # Artifacts
                    "function", "class", "method", "script", "application", "feature",
                    # Languages (common ones)
                    "python", "javascript", "java", "typescript",
                    # Maintenance
                    "refactor", "debug", "optimize", "improve"
                ]
            ),
            Agent(
                role="tester",
                capabilities=[
                    "test", "testing", "tests",
                    "validate", "verify", "check",
                    "qa", "quality", "unit", "integration"
                ]
            ),
            Agent(
                role="reviewer",
                capabilities=[
                    "review", "reviewing", "reviews",
                    "analyze", "inspect", "evaluate", "assess",
                    "approve", "feedback", "critique"
                ]
            ),
            Agent(
                role="coordinator",
                capabilities=[
                    "plan", "planning", "organize", "coordinate",
                    "delegate", "manage", "schedule", "prioritize"
                ]
            ),
            Agent(
                role="researcher",
                capabilities=[
                    "research", "investigate", "study", "explore",
                    "analyze", "document", "find", "search", "learn"
                ]
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