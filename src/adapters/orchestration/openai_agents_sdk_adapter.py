"""
OpenAI Agents SDK Adapter - Week 7, Phase 1.

Implements IAgentCoordinator using OpenAI Agents SDK for agent handoffs.
Uses Adapter Pattern to preserve Clean Architecture and DIP compliance.

Architecture:
- DIP: Implements IAgentCoordinator interface (our abstraction)
- Adapter: Wraps OpenAI Agents SDK (framework detail)
- Provider-agnostic: Works with any LLM via SDK configuration

Status: Phase 1 - Basic implementation (handoffs in Phase 2)
"""

import logging
from typing import List, Optional, Dict, Any

from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import IAgentCoordinator, ITextGenerator

# OpenAI Agents SDK imports
try:
    from agents import Agent as SDKAgent, Runner
    AGENTS_SDK_AVAILABLE = True
except ImportError:
    AGENTS_SDK_AVAILABLE = False
    SDKAgent = None
    Runner = None


logger = logging.getLogger(__name__)


class OpenAIAgentsSDKAdapter(IAgentCoordinator):
    """
    Adapter for OpenAI Agents SDK.

    DIP: Implements IAgentCoordinator (depends on our interface, not framework).
    Adapter Pattern: Translates between our entities and SDK objects.

    Phase 1: Basic agent execution
    Phase 2: Handoffs, guardrails, tracing
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        agents: List[Agent],
        max_turns: int = 10
    ):
        """
        Initialize adapter with our entities.

        Args:
            llm_provider: Our ITextGenerator (Tongyi, Mock, etc.)
            agents: List of our Agent entities
            max_turns: Maximum SDK turns (default 10)

        Note: Phase 1 uses SDK with default model. Phase 2 will integrate llm_provider.
        """
        if not AGENTS_SDK_AVAILABLE:
            raise ImportError(
                "OpenAI Agents SDK not installed. "
                "Run: pip install openai-agents"
            )

        self.llm_provider = llm_provider
        self.agents = agents
        self.max_turns = max_turns

        # Convert our agents to SDK agents
        self.sdk_agents = self._convert_agents_to_sdk(agents)

        logger.info(f"OpenAIAgentsSDKAdapter initialized with {len(agents)} agents")

    def _convert_agents_to_sdk(self, agents: List[Agent]) -> Dict[str, SDKAgent]:
        """
        Convert our Agent entities to SDK Agent objects.

        Clean Code: Single responsibility - entity conversion.

        Args:
            agents: List of our Agent entities

        Returns:
            Dict mapping role → SDK Agent
        """
        sdk_agents = {}

        for agent in agents:
            # Convert capabilities to instructions
            instructions = self._capabilities_to_instructions(agent.capabilities)

            # Create SDK agent
            sdk_agent = SDKAgent(
                name=agent.role,
                instructions=instructions,
                # Phase 2: Add handoffs, tools
            )

            sdk_agents[agent.role] = sdk_agent

            logger.debug(f"Converted agent: {agent.role}")

        return sdk_agents

    def _capabilities_to_instructions(self, capabilities: List[str]) -> str:
        """
        Convert capability list to SDK instructions (system prompt).

        Example:
            ["research", "analyze", "document"]
            → "You are an agent with these capabilities: research, analyze, document.
               Use these capabilities to complete tasks assigned to you."

        Args:
            capabilities: List of capability strings

        Returns:
            Instructions string for SDK
        """
        if not capabilities:
            return "You are a helpful AI agent."

        caps_str = ", ".join(capabilities)
        return (
            f"You are an agent with these capabilities: {caps_str}. "
            f"Use these capabilities to complete tasks assigned to you. "
            f"Be concise and focused."
        )

    def _convert_to_sdk_agent(self, agent: Agent) -> SDKAgent:
        """
        Convert single agent to SDK agent.

        Used by tests for validation.

        Args:
            agent: Our Agent entity

        Returns:
            SDK Agent object
        """
        instructions = self._capabilities_to_instructions(agent.capabilities)
        return SDKAgent(name=agent.role, instructions=instructions)

    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> List[ExecutionResult]:
        """
        Coordinate task execution using OpenAI Agents SDK.

        Implements IAgentCoordinator.coordinate() contract.

        Phase 1: Sequential execution with basic agent selection
        Phase 2: Add handoffs, parallel execution

        Args:
            tasks: Tasks to execute
            agents: Available agents
            context: Optional execution context

        Returns:
            List of ExecutionResult (one per task)
        """
        logger.info(f"Coordinating {len(tasks)} tasks with OpenAI Agents SDK")

        results = []

        for task in tasks:
            try:
                result = await self._execute_single_task(task, agents, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Task {task.task_id} failed: {e}")
                results.append(self._create_failure_result(task, str(e)))

        logger.info(f"Coordination complete: {len(results)} results")
        return results

    async def _execute_single_task(
        self,
        task: Task,
        agents: List[Agent],
        context: Optional[ExecutionContext]
    ) -> ExecutionResult:
        """
        Execute single task using SDK.

        Strategy:
        1. Select starting agent based on task description
        2. Run SDK with selected agent
        3. Convert SDK result to our ExecutionResult

        Args:
            task: Task to execute
            agents: Available agents
            context: Optional context

        Returns:
            ExecutionResult
        """
        # Select starting agent
        starting_agent = self._select_starting_agent(task, agents)

        if not starting_agent:
            return self._create_failure_result(
                task,
                "No suitable agent found for task"
            )

        logger.debug(f"Selected agent '{starting_agent.role}' for task {task.task_id}")

        # Get SDK agent
        sdk_agent = self.sdk_agents.get(starting_agent.role)

        if not sdk_agent:
            return self._create_failure_result(
                task,
                f"SDK agent '{starting_agent.role}' not found"
            )

        # Run SDK (Phase 1: Synchronous wrapper)
        try:
            # Phase 1: Use Runner.run_sync with task description as input
            # Note: This requires OPENAI_API_KEY or custom client (Phase 2)

            # For Phase 1, we'll catch the error and return mock result
            # Phase 2 will integrate llm_provider properly

            logger.warning(
                "Phase 1: SDK execution not fully integrated. "
                "Using fallback (Phase 2 will add llm_provider integration)"
            )

            # Fallback: Use our llm_provider directly
            return await self._execute_with_llm_provider(task, starting_agent)

        except Exception as e:
            logger.error(f"SDK execution failed: {e}")
            return self._create_failure_result(task, str(e))

    async def _execute_with_llm_provider(
        self,
        task: Task,
        agent: Agent
    ) -> ExecutionResult:
        """
        Fallback: Execute using our llm_provider directly.

        Phase 1: Direct execution (no SDK benefits)
        Phase 2: Integrate SDK properly with custom client

        Args:
            task: Task to execute
            agent: Selected agent

        Returns:
            ExecutionResult
        """
        try:
            # Build messages for LLM
            system_prompt = self._capabilities_to_instructions(agent.capabilities)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.description}
            ]

            # Call LLM provider
            output = self.llm_provider.generate(messages, config=None)

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=output,
                errors=[],
                metadata={
                    "agent_role": agent.role,
                    "task_id": task.task_id,
                    "orchestrator": "openai-agents-sdk-adapter",
                    "phase": "1-fallback"
                }
            )

        except Exception as e:
            return self._create_failure_result(task, str(e))

    def _select_starting_agent(
        self,
        task: Task,
        agents: List[Agent]
    ) -> Optional[Agent]:
        """
        Select starting agent for task.

        Phase 1: Simple keyword matching (reuse existing agent.can_handle logic)
        Phase 2: Use SDK's agent selection

        Args:
            task: Task to assign
            agents: Available agents

        Returns:
            Selected agent or None
        """
        # Use our existing agent.can_handle() logic
        for agent in agents:
            if agent.can_handle(task):
                return agent

        # Fallback: Return first agent
        return agents[0] if agents else None

    def _create_failure_result(self, task: Task, error_message: str) -> ExecutionResult:
        """
        Create failure result for task.

        Args:
            task: Failed task
            error_message: Error description

        Returns:
            ExecutionResult with FAILURE status
        """
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output=None,
            errors=[error_message],
            error_details={
                "error_type": "ExecutionError",
                "component": "OpenAIAgentsSDKAdapter",
                "task_id": task.task_id,
                "root_cause": error_message,
                "user_message": f"Task execution failed: {error_message}",
                "suggestion": "Check task description and agent capabilities",
                "phase": "1"
            },
            metadata={"orchestrator": "openai-agents-sdk-adapter"}
        )