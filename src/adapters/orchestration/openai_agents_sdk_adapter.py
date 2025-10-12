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
    from agents import Agent as SDKAgent, Runner, OpenAIChatCompletionsModel
    from openai import AsyncOpenAI
    AGENTS_SDK_AVAILABLE = True
except ImportError:
    AGENTS_SDK_AVAILABLE = False
    SDKAgent = None
    Runner = None
    AsyncOpenAI = None
    OpenAIChatCompletionsModel = None


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

        Phase 2: Custom OpenAI client for llama-cpp-server integration.
        """
        if not AGENTS_SDK_AVAILABLE:
            raise ImportError(
                "OpenAI Agents SDK not installed. "
                "Run: pip install openai-agents"
            )

        self.llm_provider = llm_provider
        self.agents = agents
        self.max_turns = max_turns

        # Phase 2: Create custom OpenAI client for llama-cpp-server
        custom_client = AsyncOpenAI(
            base_url="http://localhost:8080/v1",
            api_key="not-needed"  # Local server doesn't require authentication
        )

        # Create chat completions model (uses /v1/chat/completions endpoint)
        self.model = OpenAIChatCompletionsModel(
            model="tongyi",  # Model name for llama-cpp-server
            openai_client=custom_client
        )

        # Convert our agents to SDK agents (two-pass for handoffs)
        # Pass 1: Create agents without handoffs
        self.sdk_agents = self._convert_agents_to_sdk_basic(agents)

        # Pass 2: Add handoffs to agents (TEMPORARY: Disabled due to llama-cpp-server compatibility)
        # TODO: Investigate llama-cpp-server tool call format compatibility
        # self._add_handoffs_to_agents()

        logger.info(f"OpenAIAgentsSDKAdapter initialized with chat completions model ({len(agents)} agents)")
        logger.warning("Handoffs temporarily disabled due to llama-cpp-server compatibility issues")

    def _convert_agents_to_sdk_basic(self, agents: List[Agent]) -> Dict[str, SDKAgent]:
        """
        Convert our Agent entities to SDK Agent objects (Pass 1: without handoffs).

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

            # Create SDK agent with chat completions model (no handoffs yet)
            sdk_agent = SDKAgent(
                name=agent.role,
                instructions=instructions,
                model=self.model,  # Use chat completions model
                # Handoffs added in Pass 2
            )

            sdk_agents[agent.role] = sdk_agent

            logger.debug(f"Converted agent (Pass 1): {agent.role}")

        return sdk_agents

    def _add_handoffs_to_agents(self) -> None:
        """
        Add handoff objects to SDK agents (Pass 2).

        Must be called after all agents are created to avoid circular dependencies.
        """
        handoff_objs = self._create_handoff_functions()

        for agent_role, sdk_agent in self.sdk_agents.items():
            # Get handoffs for this agent
            handoffs = handoff_objs.get(agent_role, [])

            if handoffs:
                # Set handoffs attribute on agent (SDK dataclass field)
                sdk_agent.handoffs = handoffs
                logger.debug(f"Added {len(handoffs)} handoffs to agent: {agent_role}")
            else:
                logger.debug(f"No handoffs configured for agent: {agent_role}")

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
        return SDKAgent(name=agent.role, instructions=instructions, model=self.model)

    def _load_handoff_config(self) -> Dict[str, Any]:
        """Load handoff configuration from JSON file."""
        import json
        from pathlib import Path

        config_path = Path("config/agent_handoffs.json")
        if not config_path.exists():
            logger.warning("agent_handoffs.json not found, using empty config")
            return {}

        with open(config_path) as f:
            return json.load(f)

    def _create_handoff_functions(self) -> Dict[str, List[Any]]:
        """
        Create handoff functions for SDK agents.

        Returns dict: {agent_role: [handoff_objects]}
        """
        from agents import handoff

        config = self._load_handoff_config()
        handoff_objs = {}

        for agent_role, agent_config in config.items():
            handoffs = []

            for handoff_spec in agent_config.get("handoffs", []):
                target_role = handoff_spec["target"]
                description = handoff_spec["description"]

                # Get target SDK agent
                target_agent = self.sdk_agents.get(target_role)

                if target_agent:
                    # Create handoff using SDK's handoff function
                    handoff_obj = handoff(
                        agent=target_agent,
                        tool_description_override=description
                    )
                    handoffs.append(handoff_obj)
                    logger.debug(f"Created handoff: {agent_role} → {target_role}")
                else:
                    logger.warning(f"Target agent '{target_role}' not found for handoff from '{agent_role}'")

            handoff_objs[agent_role] = handoffs

        return handoff_objs

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
        Execute single task using SDK (Phase 2: Proper SDK integration).

        Strategy:
        1. Select starting agent based on task description
        2. Run SDK with selected agent and custom client
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

        # Run SDK with custom client (Phase 2)
        try:
            logger.info(f"Executing task {task.task_id} with SDK agent '{starting_agent.role}'")

            # Run SDK asynchronously using global default client
            result = await Runner.run(
                starting_agent=sdk_agent,
                input=task.description,
                max_turns=self.max_turns
            )

            # Convert SDK result to our ExecutionResult
            output = result.final_output if hasattr(result, 'final_output') else str(result)

            logger.info(f"Task {task.task_id} completed via SDK")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=output,
                errors=[],
                metadata={
                    "agent_role": starting_agent.role,
                    "task_id": task.task_id,
                    "orchestrator": "openai-agents-sdk",
                    "phase": "2-integrated"
                }
            )

        except Exception as e:
            logger.error(f"SDK execution failed for task {task.task_id}: {e}")
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