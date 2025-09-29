"""LLM-powered agent executor - Adapter layer implementation."""

from typing import Optional
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import IAgentExecutor, ITextGenerator, LLMConfig


class LLMAgentExecutor(IAgentExecutor):
    """
    Execute agents using LLM for task completion.
    DIP: Depends on ITextGenerator abstraction.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        default_config: Optional[LLMConfig] = None
    ):
        """
        Initialize with LLM provider.

        Args:
            llm_provider: LLM for agent intelligence
            default_config: Default LLM configuration
        """
        self.llm_provider = llm_provider
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=500
        )

    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute task using agent's role and LLM.

        Clean Code: Clear async execution pattern.

        Args:
            agent: Agent to execute
            task: Task to complete
            context: Optional execution context

        Returns:
            ExecutionResult with LLM output
        """
        # Build prompt based on agent role and task
        messages = self._build_messages(agent, task, context)

        try:
            # Generate response using LLM
            response = self.llm_provider.generate(
                messages=messages,
                config=self.default_config
            )

            # Update context if provided
            if context:
                context.history.append({
                    "role": "assistant",
                    "content": response,
                    "agent": agent.role
                })

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=response,
                errors=[],
                metadata={
                    "agent_role": agent.role,
                    "task_id": task.task_id
                }
            )

        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=None,
                errors=[str(e)],
                metadata={"agent_role": agent.role}
            )

    def _build_messages(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> list:
        """
        Build message list for LLM.

        SRP: Message construction logic.
        """
        messages = []

        # System message based on agent role
        system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.
Complete the given task using your expertise."""

        messages.append({"role": "system", "content": system_prompt})

        # Add context history if available
        if context and context.history:
            messages.extend(context.history[-5:])  # Last 5 messages for context

        # Add task as user message
        messages.append({
            "role": "user",
            "content": f"Task: {task.description}"
        })

        return messages