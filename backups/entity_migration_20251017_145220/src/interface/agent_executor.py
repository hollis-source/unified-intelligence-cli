"""Agent execution interfaces - ISP: Segregated interfaces for different responsibilities."""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.entities import Agent, Task
from src.entities.execution import ExecutionResult, ExecutionContext


class IAgentExecutor(ABC):
    """
    Interface for single agent execution.
    ISP: Focused solely on executing one agent with one task.
    """

    @abstractmethod
    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute a task using an agent.

        Args:
            agent: Agent to execute the task
            task: Task to be executed
            context: Optional execution context (state/history)

        Returns:
            ExecutionResult with typed output and status
        """
        pass


class IAgentSelector(ABC):
    """
    Interface for agent selection logic.
    ISP: Separate responsibility for choosing appropriate agents.
    """

    @abstractmethod
    def select_agent(
        self,
        task: Task,
        agents: List[Agent]
    ) -> Optional[Agent]:
        """
        Select the best agent for a given task.

        Args:
            task: Task to be executed
            agents: Available agents to choose from

        Returns:
            Selected agent, or None if no suitable agent
        """
        pass


class IAgentCoordinator(ABC):
    """
    Interface for coordinating multiple agents.
    ISP: High-level orchestration of agent teams.
    """

    @abstractmethod
    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate multiple agents to complete tasks.

        Args:
            tasks: List of tasks to complete
            agents: Available agents
            context: Optional shared execution context

        Returns:
            List of execution results for each task
        """
        pass