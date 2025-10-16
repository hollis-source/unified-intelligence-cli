"""
LLM-powered agent executor - Adapter layer implementation.

Week 1: Enhanced with error_details propagation for better debugging.
Week 9: Added passive data collection for model training pipeline.
SYD2 Fix: Added LLM response caching to reduce latency for expensive ULTRATHINK tasks.
"""

import time
from typing import Optional, Any, Union
from src.entity import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interface import IAgentExecutor, ITextGenerator, LLMConfig
from src.interface.async_text_generator import IAsyncTextGenerator
from src.exceptions import ToolExecutionError
from src.adapters.agent.llm_cache import LLMResponseCache, CacheConfig


class LLMAgentExecutor(IAgentExecutor):
    """
    Execute agents using LLM for task completion.
    DIP: Depends on ITextGenerator abstraction.
    Week 9: Optionally collects execution data for model training.
    """

    def __init__(
        self,
        llm_provider: Union[ITextGenerator, IAsyncTextGenerator],
        default_config: Optional[LLMConfig] = None,
        data_collector: Optional[Any] = None,
        provider_name: str = "unknown",
        orchestrator: str = "simple",
        cache_config: Optional[CacheConfig] = None,
        enable_cache: bool = True,
        enable_ultrathink: bool = True
    ):
        """
        Initialize with LLM provider.

        Args:
            llm_provider: LLM for agent intelligence (sync or async)
            default_config: Default LLM configuration
            data_collector: Optional DataCollector for training data (Week 9)
            provider_name: LLM provider name (mock, grok, tongyi) (Week 9)
            orchestrator: Orchestrator mode (simple, openai-agents) (Week 9)
            cache_config: Optional cache configuration (SYD2 fix)
            enable_cache: Enable response caching (SYD2 fix)
            enable_ultrathink: Enable ULTRATHINK prompts (Phase 4B: disable for Granite)
        """
        self.llm_provider = llm_provider
        self.is_async_provider = isinstance(llm_provider, IAsyncTextGenerator)
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=1024  # Qwen3 HF Space limit (was 500, too restrictive)
        )
        self.data_collector = data_collector
        self.provider_name = provider_name
        self.orchestrator = orchestrator
        self.enable_ultrathink = enable_ultrathink

        # SYD2 FIX: Initialize response cache for expensive ULTRATHINK tasks
        if enable_cache:
            self.cache = LLMResponseCache(cache_config)
        else:
            self.cache = None

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

        # SYD2 FIX: Check cache before expensive LLM call
        cache_hit = False
        response_text = None
        usage = {}

        if self.cache:
            # Extract task description for cache keying
            task_desc = self._extract_task_description(task)
            response_text = self.cache.get(
                messages=messages,
                task_description=task_desc,
                model_name=self.provider_name
            )
            cache_hit = response_text is not None

            # Phase 2: Estimate usage for cache hits (no actual API call made)
            if cache_hit:
                estimated_tokens = len(response_text) // 4
                usage = {
                    "prompt_tokens": 0,  # Unknown for cache hit
                    "completion_tokens": estimated_tokens,
                    "total_tokens": estimated_tokens,
                    "cached": True  # Flag to indicate estimation
                }

        try:
            if not cache_hit:
                # Generate response using LLM (cache miss or disabled)
                # Support both sync and async providers
                if self.is_async_provider:
                    result = await self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )
                else:
                    result = self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )

                # Extract content and usage from GenerationResult
                response_text = result.content
                usage = result.usage

                # Store in cache for future requests
                if self.cache:
                    task_desc = self._extract_task_description(task)
                    self.cache.set(
                        messages=messages,
                        response=response_text,
                        task_description=task_desc,
                        model_name=self.provider_name
                    )

            # Calculate execution duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Update context if provided
            if context:
                context.history.append({
                    "role": "assistant",
                    "content": response_text,
                    "agent": agent.role
                })

            # Week 9: Log successful interaction for training data
            if self.data_collector:
                self.data_collector.log_interaction(
                    task=task,
                    agent=agent,
                    messages=messages,
                    output=response_text,
                    status="success",
                    duration_ms=duration_ms,
                    llm_config=self.default_config,
                    provider=self.provider_name,
                    orchestrator=self.orchestrator,
                    context_history_length=len(context.history) if context else 0
                )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=response_text,
                errors=[],
                metadata={
                    "agent_role": agent.role,
                    "task_id": task.task_id,
                    "cache_hit": cache_hit,  # SYD2 FIX: Track cache performance
                    "duration_ms": duration_ms,
                    "usage": usage  # Phase 2: Actual token usage from LLM
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
        Build message list for LLM with optional ultrathink capability.

        SRP: Message construction logic.
        Week 13: Added chain-of-thought prompting for deeper analysis.
        Phase 4B: Made ULTRATHINK optional (disable for models with language issues).
        """
        messages = []

        if self.enable_ultrathink:
            # System message with ULTRATHINK instructions
            system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.

ULTRATHINK MODE: You MUST think step-by-step through problems before answering.
- Use <think></think> tags to show your reasoning process
- Break down complex problems into smaller steps
- Analyze multiple approaches before selecting the best one
- Verify your logic and check for errors
- Be thorough and rigorous in your analysis

IMPORTANT: When providing responses, include specific file:line references.
- Format: path/to/file.py:line_number - description
- Example: "src/adapters/llm/grok_adapter.py:42 - Update return type to GenerationResult"
- Example: "tests/unit/test_adapter.py:15 - Add test for token usage extraction"
- Reference actual code locations where changes should be made

Complete the given task using your expertise and deep analytical thinking."""

            task_prompt = f"""Task: {task.description}

IMPORTANT: Think through this problem step-by-step using <think></think> tags before providing your final answer. Consider:
1. What is being asked?
2. What information do I need?
3. What are the potential approaches?
4. What are the constraints and requirements?
5. What is the optimal solution?

REQUIRED FORMAT: Include specific file:line references in your response.
- Use format: path/to/file.py:line_number
- Example: "src/main.py:42" or "tests/test_adapter.py:15"
- Provide at least 2-3 specific file locations relevant to this task

Think deeply, then provide your response with file:line references."""
        else:
            # Simple system message (for models with ULTRATHINK compatibility issues)
            system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.

IMPORTANT: When providing responses, include specific file:line references.
- Format: path/to/file.py:line_number - description
- Example: "src/main.py:85 - Add error handling"

Complete the given task using your expertise and professional knowledge."""

            task_prompt = f"""Task: {task.description}

Provide a clear, professional response based on your expertise."""

        messages.append({"role": "system", "content": system_prompt})

        # Add context history if available
        if context and context.history:
            messages.extend(context.history[-5:])  # Last 5 messages for context

        # Add task as user message
        messages.append({
            "role": "user",
            "content": task_prompt
        })

        return messages

    def _extract_task_description(self, task: Task) -> str:
        """
        Extract task description for cache keying.

        SYD2 FIX: Improves cache hit rate by using semantic task description.
        BUGFIX: Removed task_id to enable cache hits across similar tasks.

        Args:
            task: Task entity

        Returns:
            Task description string (semantic category, not unique ID)
        """
        desc = task.description.lower()

        # Normalize ULTRATHINK tasks for better cache hit rate
        if "ultrathink" in desc:
            # Extract key components: category only (removed task_id)
            # e.g., "ULTRATHINK: Plan refactoring for router" -> "ultrathink:refactoring"
            # This enables cache hits for all refactoring tasks
            if "refactoring" in desc or "refactor" in desc:
                category = "refactoring"
            elif "architecture" in desc:
                category = "architecture"
            elif "scalability" in desc:
                category = "scalability"
            elif "testing" in desc or "test" in desc:
                category = "testing"
            elif "performance" in desc:
                category = "performance"
            else:
                category = "analysis"

            # FIX: Removed task.task_id[:8] - was causing 0% hit rate
            return f"ultrathink:{category}"

        return desc[:100]  # Limit length for cache key