#!/usr/bin/env python3
"""Simple integration test for the CLI components."""

import asyncio
from src.entities import Agent, Task, ExecutionContext
from src.adapters.llm.mock_provider import MockLLMProvider
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.use_cases.coordinator import CoordinateAgentsUseCase


async def test_basic_coordination():
    """Test basic coordination flow."""

    # Create agents
    agents = [
        Agent(role="coder", capabilities=["code_gen", "debug"]),
        Agent(role="tester", capabilities=["test", "validate"])
    ]

    # Create tasks
    tasks = [
        Task(
            description="code_gen for hello world",  # Match capability
            task_id="task1",
            priority=1,
            dependencies=[]  # No dependencies
        )
    ]

    # Create dependencies
    llm_provider = MockLLMProvider("Code generated successfully")
    agent_executor = LLMAgentExecutor(llm_provider)
    agent_selector = CapabilityBasedSelector()

    # Create coordinator
    coordinator = CoordinateAgentsUseCase(
        llm_provider=llm_provider,
        agent_executor=agent_executor,
        agent_selector=agent_selector
    )

    # Execute
    print("Starting coordination...")
    results = await coordinator.coordinate(tasks, agents)

    # Display results
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Status: {result.status.value}")
        print(f"  Output: {result.output}")
        print(f"  Errors: {result.errors}")
        print(f"  Metadata: {result.metadata}")


if __name__ == "__main__":
    asyncio.run(test_basic_coordination())