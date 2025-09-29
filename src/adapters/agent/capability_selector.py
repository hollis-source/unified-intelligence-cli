"""Capability-based agent selector - Simple implementation."""

from typing import List, Optional
from src.entities import Agent, Task
from src.interfaces import IAgentSelector


class CapabilityBasedSelector(IAgentSelector):
    """
    Select agents based on capability matching.
    Clean Code: Simple, focused implementation.
    """

    def select_agent(
        self,
        task: Task,
        agents: List[Agent]
    ) -> Optional[Agent]:
        """
        Select agent whose capabilities best match the task.

        SRP: Single responsibility - capability matching.

        Args:
            task: Task to be executed
            agents: Available agents

        Returns:
            Best matching agent or None
        """
        if not agents:
            return None

        # Find agents that can handle the task
        capable_agents = [
            agent for agent in agents
            if agent.can_handle(task)
        ]

        if not capable_agents:
            return None

        # Return agent with most capabilities (more specialized)
        return max(capable_agents, key=lambda a: len(a.capabilities))