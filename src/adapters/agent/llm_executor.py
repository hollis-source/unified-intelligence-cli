"""
LLM-powered agent executor - Adapter layer implementation.

Week 1: Enhanced with error_details propagation for better debugging.
Week 9: Added passive data collection for model training pipeline.
SYD2 Fix: Added LLM response caching to reduce latency for expensive ULTRATHINK tasks.
"""

import time
from typing import Optional, Any
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import IAgentExecutor, ITextGenerator, LLMConfig
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
        llm_provider: ITextGenerator,
        default_config: Optional[LLMConfig] = None,
        data_collector: Optional[Any] = None,
        provider_name: str = "unknown",
        orchestrator: str = "simple",
        cache_config: Optional[CacheConfig] = None,
        enable_cache: bool = True
    ):
        """
        Initialize with LLM provider.

        Args:
            llm_provider: LLM for agent intelligence
            default_config: Default LLM configuration
            data_collector: Optional DataCollector for training data (Week 9)
            provider_name: LLM provider name (mock, grok, tongyi) (Week 9)
            orchestrator: Orchestrator mode (simple, openai-agents) (Week 9)
            cache_config: Optional cache configuration (SYD2 fix)
            enable_cache: Enable response caching (SYD2 fix)
        """
        self.llm_provider = llm_provider
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=1024  # Qwen3 HF Space limit (was 500, too restrictive)
        )
        self.data_collector = data_collector
        self.provider_name = provider_name
        self.orchestrator = orchestrator

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
        response = None

        if self.cache:
            # Extract task description for cache keying
            task_desc = self._extract_task_description(task)
            response = self.cache.get(
                messages=messages,
                task_description=task_desc,
                model_name=self.provider_name
            )
            cache_hit = response is not None

        try:
            if not cache_hit:
                # Generate response using LLM (cache miss or disabled)
                response = self.llm_provider.generate(
                    messages=messages,
                    config=self.default_config
                )

                # Store in cache for future requests
                if self.cache:
                    task_desc = self._extract_task_description(task)
                    self.cache.set(
                        messages=messages,
                        response=response,
                        task_description=task_desc,
                        model_name=self.provider_name
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
                    "task_id": task.task_id,
                    "cache_hit": cache_hit,  # SYD2 FIX: Track cache performance
                    "duration_ms": duration_ms
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
        # Handle both ExecutionContext objects and dict contexts
        if context:
            if hasattr(context, 'history') and context.history:
                messages.extend(context.history[-5:])  # Last 5 messages for context
            elif isinstance(context, dict) and 'history' in context and context['history']:
                messages.extend(context['history'][-5:])  # Last 5 messages for context

        # Add task as user message with task-type-specific instructions
        task_prompt = self._build_task_prompt(task, context)

        messages.append({
            "role": "user",
            "content": task_prompt
        })

        return messages

    def _build_task_prompt(self, task: Task, context: Optional[ExecutionContext]) -> str:
        """
        Build task-type-specific prompt that instructs LLM to generate artifacts.

        Args:
            task: Task to execute
            context: Optional execution context

        Returns:
            Formatted prompt string
        """
        task_type = task.task_type if hasattr(task, 'task_type') else 'general'

        # Get context data if available
        world_state = {}
        if context:
            if hasattr(context, 'llm_state'):
                world_state = context.llm_state or {}
            elif isinstance(context, dict) and 'llm_state' in context:
                world_state = context['llm_state'] or {}

        # Build task-type-specific instructions
        if task_type in ['implementation', 'coding']:
            prompt = f"""Task: {task.description}

You are generating actual code. DO NOT explain how to write code - WRITE THE ACTUAL CODE.

Context:
{self._format_world_state(world_state)}

INSTRUCTIONS:
1. Generate the complete, working code for this task
2. Use proper syntax and best practices
3. Include necessary imports and error handling
4. Return ONLY the code wrapped in ```python or appropriate language tags
5. Do not include explanations unless they are code comments

Generate the code now:"""

        elif task_type == 'design':
            prompt = f"""Task: {task.description}

You are creating a design specification. DO NOT explain design principles - CREATE THE ACTUAL DESIGN.

Context:
{self._format_world_state(world_state)}

INSTRUCTIONS:
1. Create the complete design specification (API schema, architecture diagram, data model, etc.)
2. Use proper notation (JSON schema, UML, etc.)
3. Be specific and implementable
4. Return the design artifact in structured format

Generate the design specification now:"""

        elif task_type == 'testing':
            prompt = f"""Task: {task.description}

You are writing actual test code. DO NOT explain testing strategies - WRITE THE ACTUAL TESTS.

Context:
{self._format_world_state(world_state)}

INSTRUCTIONS:
1. Generate complete, runnable test code
2. Include test cases with assertions
3. Use appropriate testing framework (pytest, unittest, etc.)
4. Return ONLY the test code wrapped in ```python tags

Generate the test code now:"""

        elif task_type == 'documentation':
            prompt = f"""Task: {task.description}

You are writing actual documentation. DO NOT explain documentation principles - WRITE THE ACTUAL DOCS.

Context:
{self._format_world_state(world_state)}

INSTRUCTIONS:
1. Generate complete, user-ready documentation
2. Use proper markdown formatting
3. Include examples where appropriate
4. Be clear and concise

Generate the documentation now:"""

        else:
            # General tasks - still directive but less specific
            prompt = f"""Task: {task.description}

Context:
{self._format_world_state(world_state)}

INSTRUCTIONS:
Generate the specific artifact or output required for this task. Be concrete and actionable.
If code is needed, provide actual code. If a document is needed, provide the actual document.
DO NOT provide explanations of how to do the task - DO THE TASK.

Complete the task now:"""

        return prompt

    def _format_world_state(self, world_state: dict) -> str:
        """Format world state for inclusion in prompt."""
        if not world_state:
            return "No previous context available."

        formatted = []
        for key, value in world_state.items():
            if isinstance(value, str) and len(value) > 200:
                formatted.append(f"- {key}: {value[:200]}... (truncated)")
            else:
                formatted.append(f"- {key}: {value}")

        return "\n".join(formatted) if formatted else "No previous context available."

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