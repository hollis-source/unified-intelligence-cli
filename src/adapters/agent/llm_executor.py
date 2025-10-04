"""
LLM-powered agent executor - Adapter layer implementation.

Week 1: Enhanced with error_details propagation for better debugging.
Week 9: Added passive data collection for model training pipeline.
"""

import time
from typing import Optional, Any
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import IAgentExecutor, ITextGenerator, LLMConfig
from src.exceptions import ToolExecutionError


class LLMAgentExecutor(IAgentExecutor):
    """
    Execute agents using LLM for task completion.
    DIP: Depends on ITextGenerator abstraction.
    Week 9: Optionally collects execution data for model training.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        default_config: Optional[LLMConfig] = None,
        data_collector: Optional[Any] = None,
        provider_name: str = "unknown",
        orchestrator: str = "simple"
    ):
        """
        Initialize with LLM provider.

        Args:
            llm_provider: LLM for agent intelligence
            default_config: Default LLM configuration
            data_collector: Optional DataCollector for training data (Week 9)
            provider_name: LLM provider name (mock, grok, tongyi) (Week 9)
            orchestrator: Orchestrator mode (simple, openai-agents) (Week 9)
        """
        self.llm_provider = llm_provider
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=1024  # Qwen3 HF Space limit (was 500, too restrictive)
        )
        self.data_collector = data_collector
        self.provider_name = provider_name
        self.orchestrator = orchestrator

    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute task using agent's role and LLM.

        Clean Code: Clear async execution pattern.
        Week 9: Logs interaction data for model training if enabled.

        Args:
            agent: Agent to execute
            task: Task to complete
            context: Optional execution context

        Returns:
            ExecutionResult with LLM output
        """
        # Week 9: Track execution time for data collection
        start_time = time.time()

        # Build prompt based on agent role and task
        messages = self._build_messages(agent, task, context)

        try:
            # Generate response using LLM
            response = self.llm_provider.generate(
                messages=messages,
                config=self.default_config
            )

            # Calculate execution duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Update context if provided
            if context:
                context.history.append({
                    "role": "assistant",
                    "content": response,
                    "agent": agent.role
                })

            # Week 9: Log successful interaction for training data
            if self.data_collector:
                self.data_collector.log_interaction(
                    task=task,
                    agent=agent,
                    messages=messages,
                    output=response,
                    status="success",
                    duration_ms=duration_ms,
                    llm_config=self.default_config,
                    provider=self.provider_name,
                    orchestrator=self.orchestrator,
                    context_history_length=len(context.history) if context else 0
                )

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
            # Calculate execution duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Week 1: Propagate tool errors with full context
            error_details = None

            # Check if it's a ToolExecutionError with structured details
            if isinstance(e, ToolExecutionError):
                error_details = e.to_error_details()
            else:
                # Generic exception - create basic error_details
                error_details = {
                    "error_type": "ExecutionError",
                    "component": "LLMAgentExecutor",
                    "input": {
                        "task_description": task.description,
                        "agent_role": agent.role
                    },
                    "root_cause": str(e),
                    "user_message": f"Task execution failed: {str(e)}",
                    "suggestion": "Check the error message and task description. Use --verbose for more details.",
                    "context": {
                        "exception_type": type(e).__name__,
                        "agent_role": agent.role,
                        "task_id": task.task_id
                    }
                }

            # Week 9: Log failed interaction for training data
            if self.data_collector:
                self.data_collector.log_interaction(
                    task=task,
                    agent=agent,
                    messages=messages,
                    output=None,
                    status="failure",
                    duration_ms=duration_ms,
                    llm_config=self.default_config,
                    provider=self.provider_name,
                    errors=[str(e)],
                    error_details=error_details,
                    orchestrator=self.orchestrator,
                    context_history_length=len(context.history) if context else 0
                )

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=None,
                errors=[str(e)],
                error_details=error_details,
                metadata={"agent_role": agent.role}
            )

    def _build_messages(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> list:
        """
        Build message list for LLM with ultrathink capability.

        SRP: Message construction logic.
        Week 13: Added chain-of-thought prompting for deeper analysis.
        """
        messages = []

        # System message with ultrathink instructions
        system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.

ULTRATHINK MODE: You MUST think step-by-step through problems before answering.
- Use <think></think> tags to show your reasoning process
- Break down complex problems into smaller steps
- Analyze multiple approaches before selecting the best one
- Verify your logic and check for errors
- Be thorough and rigorous in your analysis

Complete the given task using your expertise and deep analytical thinking."""

        messages.append({"role": "system", "content": system_prompt})

        # Add context history if available
        if context and context.history:
            messages.extend(context.history[-5:])  # Last 5 messages for context

        # Add task as user message with ultrathink trigger
        task_prompt = f"""Task: {task.description}

IMPORTANT: Think through this problem step-by-step using <think></think> tags before providing your final answer. Consider:
1. What is being asked?
2. What information do I need?
3. What are the potential approaches?
4. What are the constraints and requirements?
5. What is the optimal solution?

Think deeply, then provide your response."""

        messages.append({
            "role": "user",
            "content": task_prompt
        })

        return messages