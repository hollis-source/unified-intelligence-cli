#!/usr/bin/env python3
"""Consult Grok about Agent Executor interface design."""

from grok_session import GrokSession

# The interface we're designing
interface_code = '''
"""Agent Executor interface - ISP: Narrow interface for agent execution."""

from abc import ABC, abstractmethod
from typing import Any
from src.entities import Agent, Task


class IAgentExecutor(ABC):
    """
    Abstract interface for agent execution.
    ISP: Focused solely on executing agents with tasks.
    """

    @abstractmethod
    def execute(self, agent: Agent, task: Task) -> Any:
        """
        Execute a task using an agent.

        Args:
            agent: Agent to execute the task
            task: Task to be executed

        Returns:
            Execution result (varies by implementation)
        """
        pass
'''

context = '''
We're building a Unified Intelligence CLI following Clean Architecture.
We already have:
1. Entities: Agent (with role & capabilities) and Task (with description & priority)
2. LLM interfaces: ITextGenerator and IToolSupportedProvider (based on your earlier feedback)

Now we need an interface for executing agents. The use case will:
- Coordinate multiple specialized agents (coder, tester, reviewer)
- Distribute tasks to appropriate agents based on capabilities
- Potentially use LLMs to power agent execution

Following your earlier advice about ISP (Interface Segregation), we want narrow, focused interfaces.
'''

question = '''
Review this IAgentExecutor interface design. Consider:

1. Is returning "Any" a violation of LSP/ISP? Should we define a Result type?
2. Should the interface know about the LLM dependency, or keep it hidden?
3. For a multi-agent system, should we have:
   - IAgentExecutor for single agent execution
   - IAgentCoordinator for orchestrating multiple agents
   - IAgentSelector for choosing which agent handles a task?
4. How should we handle async execution for potentially long-running agent tasks?
5. Should agent state/context be passed separately from the Agent entity?

Provide specific recommendations based on Clean Architecture and multi-agent patterns.
Consider how CrewAI, LangChain, or AutoGen handle similar abstractions.
'''

# Consult Grok
session = GrokSession(
    system_prompt="You are Grok. Analyze this multi-agent system architecture critically. Draw from patterns in CrewAI, LangChain, AutoGen, and similar frameworks.",
    enable_logging=False
)

print("Consulting Grok about Agent Executor interface...")
print("=" * 60)

full_query = f"Context:\n{context}\n\nInterface Code:\n```python\n{interface_code}\n```\n\nQuestion:\n{question}"

result = session.send_message(full_query)
print(result['response'])