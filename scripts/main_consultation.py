#!/usr/bin/env python3
"""Consult Grok about main.py DI implementation."""

from grok_session import GrokSession

# The main.py implementation
main_code = '''
import click
import asyncio
import os
from typing import List

# Clean Architecture: Dependencies point inward
from src.entities import Agent, Task
from src.use_cases.coordinator import CoordinateAgentsUseCase
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.llm.mock_provider import MockLLMProvider


@click.command()
@click.argument("task_description")
@click.option("--use-mock", is_flag=True, help="Use mock LLM provider for testing")
@click.option("--use-grok", is_flag=True, help="Use Grok LLM (requires XAI_API_KEY)")
def main(task_description: str, use_mock: bool, use_grok: bool):
    """
    Unified Intelligence CLI: Orchestrate agents for tasks.
    Clean Architecture: Main composes dependencies (DI root).
    """
    # Setup agents (in production, load from config)
    agents = create_default_agents()

    # Create task from description
    task = Task(
        description=task_description,
        task_id="task_1",
        priority=1
    )

    # DIP: Wire dependencies based on flags
    llm_provider = create_llm_provider(use_mock, use_grok)
    agent_executor = LLMAgentExecutor(llm_provider)
    agent_selector = CapabilityBasedSelector()

    # Create use case with injected dependencies
    coordinator = CoordinateAgentsUseCase(
        llm_provider=llm_provider,
        agent_executor=agent_executor,
        agent_selector=agent_selector
    )

    # Execute coordination (async)
    results = asyncio.run(
        coordinator.coordinate(
            tasks=[task],
            agents=agents
        )
    )

    # Display results
    for i, result in enumerate(results):
        click.echo(f"\\n--- Result {i+1} ---")
        click.echo(f"Status: {result.status.value}")
        if result.output:
            click.echo(f"Output: {result.output[:200]}...")
        if result.errors:
            click.echo(f"Errors: {', '.join(result.errors)}")


def create_default_agents() -> List[Agent]:
    """Create default agent team."""
    return [
        Agent(role="coder", capabilities=["code_gen", "refactor", "debug"]),
        Agent(role="tester", capabilities=["test", "validate", "verify"]),
        Agent(role="reviewer", capabilities=["review", "analyze", "approve"]),
        Agent(role="coordinator", capabilities=["plan", "organize", "delegate"])
    ]


def create_llm_provider(use_mock: bool, use_grok: bool):
    """Factory method for LLM provider. DIP: Return interface, hide implementation."""
    if use_grok:
        # Check for API key
        if not os.getenv("XAI_API_KEY"):
            click.echo("Error: XAI_API_KEY not set. Use --use-mock for testing.")
            raise click.Abort()

        from src.adapters.llm.grok_adapter import GrokAdapter
        click.echo("Using Grok LLM provider")
        return GrokAdapter()
    else:
        # Default to mock for testing
        click.echo("Using Mock LLM provider")
        return MockLLMProvider(default_response="Task completed by mock agent")
'''

context = '''
This is the main.py entry point for our Unified Intelligence CLI following Clean Architecture.
We've implemented:
1. Entities: Agent, Task with dependencies
2. Use Cases: CoordinateAgentsUseCase with planning and parallel execution
3. Interfaces: ITextGenerator, IToolSupportedProvider, IAgentExecutor, IAgentSelector, IAgentCoordinator
4. Adapters: MockLLMProvider, GrokAdapter, CapabilityBasedSelector, LLMAgentExecutor

The main.py is the composition root where we wire all dependencies together.
'''

question = '''
Review this main.py implementation as the DI composition root. Consider:

1. Is this the correct place for dependency wiring in Clean Architecture?
2. Should we use a DI container (like dependency-injector) instead of manual wiring?
3. Is the factory pattern for LLM providers appropriate?
4. Should agent creation be moved to a separate factory or repository?
5. How should we handle configuration (currently hardcoded agents)?
6. Is asyncio.run() the right approach for the CLI entry point?
7. Should we add more CLI options (verbose, parallel, planning mode)?
8. How does this compare to DI roots in other Clean Architecture projects?

Provide specific improvements for production readiness.
Consider how this would scale with more providers, agents, and use cases.
'''

# Consult Grok
session = GrokSession(
    system_prompt="You are Grok. Review this dependency injection implementation critically. Focus on Clean Architecture's composition root pattern and production CLI best practices.",
    enable_logging=False
)

print("Consulting Grok about main.py DI implementation...")
print("=" * 60)

full_query = f"Context:\n{context}\n\nMain.py Code:\n```python\n{main_code}\n```\n\nQuestion:\n{question}"

result = session.send_message(full_query)
print(result['response'])