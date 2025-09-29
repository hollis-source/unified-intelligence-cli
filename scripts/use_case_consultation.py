#!/usr/bin/env python3
"""Consult Grok about CoordinateAgentsUseCase implementation."""

from grok_session import GrokSession

# The use case implementation
use_case_code = '''
"""Coordinate agents use case - Clean Architecture use case layer."""

from typing import List, Optional
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import (
    IAgentCoordinator,
    IAgentExecutor,
    IAgentSelector,
    ITextGenerator
)


class CoordinateAgentsUseCase(IAgentCoordinator):
    """
    Use case for coordinating multiple agents.
    DIP: Depends on abstractions, not concretions.
    SRP: Single responsibility - orchestrate agent execution.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        agent_executor: IAgentExecutor,
        agent_selector: IAgentSelector
    ):
        """Initialize with injected dependencies."""
        self.llm_provider = llm_provider
        self.agent_executor = agent_executor
        self.agent_selector = agent_selector

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate multiple agents to complete tasks.
        Each task is assigned to the most suitable agent.
        """
        results = []

        for task in tasks:
            result = await self._execute_task(task, agents, context)
            results.append(result)

        return results

    async def _execute_task(
        self,
        task: Task,
        agents: List[Agent],
        context: Optional[ExecutionContext]
    ) -> ExecutionResult:
        """Execute a single task with appropriate agent."""
        # Select appropriate agent
        agent = self.agent_selector.select_agent(task, agents)

        if agent is None:
            return self._create_failure_result(
                f"No suitable agent found for task: {task.description}"
            )

        # Execute with selected agent
        try:
            result = await self.agent_executor.execute(
                agent=agent,
                task=task,
                context=context
            )
            return result
        except Exception as e:
            return self._create_failure_result(str(e))

    def _create_failure_result(self, error_message: str) -> ExecutionResult:
        """Create a failure result."""
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output=None,
            errors=[error_message],
            metadata={}
        )
'''

context = '''
We're implementing a multi-agent orchestration system following Clean Architecture.
Based on your earlier feedback, we've created:
1. Split interfaces (ITextGenerator, IToolSupportedProvider, IAgentExecutor, IAgentSelector, IAgentCoordinator)
2. Strong typing with ExecutionResult instead of Any
3. Async execution support
4. Separate ExecutionContext from Agent entity

This CoordinateAgentsUseCase implements the IAgentCoordinator interface.
It's in the use cases layer and depends only on abstractions (interfaces).
'''

question = '''
Review this CoordinateAgentsUseCase implementation. Consider:

1. Is the dependency injection properly implemented for Clean Architecture?
2. Should the LLM provider be used within the coordination logic, or just passed to executors?
3. Is sequential task execution appropriate, or should we support parallel execution?
4. How should we handle task dependencies (e.g., test task depends on code task)?
5. Should we add a planning phase where the coordinator uses LLM to determine execution order?
6. Is the error handling sufficient for production use?
7. How does this compare to CrewAI's Crew class or LangChain's agent execution?

Provide specific improvements based on multi-agent patterns and Clean Architecture.
Focus on making this production-ready for real agent coordination scenarios.
'''

# Consult Grok
session = GrokSession(
    system_prompt="You are Grok. Review this multi-agent coordination implementation critically. Draw from CrewAI, LangChain, AutoGen patterns and Clean Architecture principles.",
    enable_logging=False
)

print("Consulting Grok about CoordinateAgentsUseCase...")
print("=" * 60)

full_query = f"Context:\n{context}\n\nUse Case Code:\n```python\n{use_case_code}\n```\n\nQuestion:\n{question}"

result = session.send_message(full_query)
print(result['response'])