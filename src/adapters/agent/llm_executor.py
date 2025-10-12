"""
LLM-powered agent executor - Adapter layer implementation.

Week 1: Enhanced with error_details propagation for better debugging.
Week 9: Added passive data collection for model training pipeline.
SYD2 Fix: Added LLM response caching to reduce latency for expensive ULTRATHINK tasks.
Sprint 1: Added DSPy prompt optimization mode.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Any, Dict
from src.entities import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.interfaces import IAgentExecutor, ITextGenerator, LLMConfig
from src.exceptions import ToolExecutionError
from src.adapters.agent.llm_cache import LLMResponseCache, CacheConfig
from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter

# Metrics file path
CACHE_METRICS_PATH = Path.home() / ".claude" / "cache_metrics.json"


def _load_cache_metrics() -> Dict:
    """Load cache metrics from file."""
    try:
        if CACHE_METRICS_PATH.exists():
            with open(CACHE_METRICS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "cache_hits": 0,
        "cache_misses": 0,
        "cache_hit_latencies": [],
        "cache_miss_latencies": [],
    }


def _save_cache_metrics(metrics: Dict) -> None:
    """Save cache metrics to file."""
    try:
        CACHE_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


def _update_cache_hit_metric(latency_ms: float) -> None:
    """Record cache hit with latency."""
    metrics = _load_cache_metrics()
    metrics["cache_hits"] = metrics.get("cache_hits", 0) + 1
    latencies = metrics.get("cache_hit_latencies", [])
    latencies.append(latency_ms)
    metrics["cache_hit_latencies"] = latencies[-100:]  # Keep last 100
    _save_cache_metrics(metrics)


def _update_cache_miss_metric(latency_ms: float) -> None:
    """Record cache miss with latency."""
    metrics = _load_cache_metrics()
    metrics["cache_misses"] = metrics.get("cache_misses", 0) + 1
    latencies = metrics.get("cache_miss_latencies", [])
    latencies.append(latency_ms)
    metrics["cache_miss_latencies"] = latencies[-100:]  # Keep last 100
    _save_cache_metrics(metrics)


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
        enable_cache: bool = True,
        prompt_mode: str = "manual",
        tool_history_repo: Optional[Any] = None,
        logger: Optional[Any] = None
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
            prompt_mode: Prompt generation mode - "manual" or "dspy" (Sprint 1)
            tool_history_repo: Optional ToolHistoryRepository for Phase 2b audit trail
            logger: Optional logger (defaults to module logger)
        """
        self.llm_provider = llm_provider
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=1024  # Qwen3 HF Space limit (was 500, too restrictive)
        )
        self.data_collector = data_collector
        self.provider_name = provider_name
        self.orchestrator = orchestrator
        self.prompt_mode = prompt_mode

        # Phase 2b: Tool execution history tracking
        self.tool_history_repo = tool_history_repo
        import logging
        self.logger = logger or logging.getLogger(__name__)

        # SYD2 FIX: Initialize response cache for expensive ULTRATHINK tasks
        if enable_cache:
            self.cache = LLMResponseCache(cache_config)
        else:
            self.cache = None

        # Sprint 1: Initialize DSPy adapter if DSPy mode enabled
        if prompt_mode == "dspy":
            self.dspy_adapter = DSPyPromptAdapter(llm_provider, use_chain_of_thought=True)
        else:
            self.dspy_adapter = None

        # ReAct tool-use (Phase 1): optional tool registry and settings (off by default)
        self.tool_registry = None  # Will be set via enable_react(tool_registry=...)
        self.react_enabled = False
        self.react_max_iterations = 10

    def enable_react(self, tool_registry, max_iterations: int = 10) -> None:
        """Enable ReAct tool-use mode with the given registry."""
        self.tool_registry = tool_registry
        self.react_enabled = True
        self.react_max_iterations = max(1, int(max_iterations))

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

        # Phase 1: If ReAct tool-use is enabled, run Think→Act→Observe loop
        react_taken = False
        if self.react_enabled and getattr(self, "tool_registry", None):
            try:
                response, messages = self._execute_react(agent, task, context)
                cache_hit = False
                react_taken = True
            except Exception as e:
                # If ReAct fails, fall back to normal generation path
                react_taken = False

        if not react_taken:
            # Sprint 1: Route to DSPy adapter if enabled
            if self.prompt_mode == "dspy" and self.dspy_adapter:
                try:
                    response = self.dspy_adapter.generate_for_task(task, context)
                    cache_hit = False  # DSPy has its own caching
                    messages = []  # DSPy handles message building internally
                except Exception:
                    # Fallback to manual prompts if DSPy fails
                    messages = self._build_messages(agent, task, context)
                    response = self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )
                    cache_hit = False
            else:
                # Manual prompt mode (existing behavior)
                # Build prompt based on agent role and task
                messages = self._build_messages(agent, task, context)

                # SYD2 FIX: Check cache before expensive LLM call
                cache_hit = False
                response = None

                # Only use cache for ULTRATHINK-class tasks to avoid masking provider calls in tests
                use_cache = self.cache is not None and "ultrathink" in (task.description or "").lower()

                if use_cache:
                    # Extract task description for cache keying
                    task_desc = self._extract_task_description(task)
                    cache_check_start = time.time()
                    response = self.cache.get(
                        messages=messages,
                        task_description=task_desc,
                        model_name=self.provider_name
                    )
                    cache_hit = response is not None

                    if cache_hit:
                        # Record cache hit with latency
                        hit_latency_ms = (time.time() - cache_check_start) * 1000
                        _update_cache_hit_metric(hit_latency_ms)

                if not cache_hit:
                    # Generate response using LLM (cache miss or cache disabled)
                    miss_start = time.time()
                    response = self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )

                    # Record cache miss with latency (only if cache was enabled)
                    if use_cache:
                        miss_latency_ms = (time.time() - miss_start) * 1000
                        _update_cache_miss_metric(miss_latency_ms)

                    # Store in cache for future requests (only for ULTRATHINK tasks)
                    if use_cache:
                        task_desc = self._extract_task_description(task)
                        self.cache.set(
                            messages=messages,
                            response=response,
                            task_description=task_desc,
                            model_name=self.provider_name
                        )

        try:

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

    def _build_react_context(self, task: Task) -> str:
        """Construct the ReAct system prompt context with available tools."""
        tool_desc = self.tool_registry.get_tool_descriptions() if self.tool_registry else ""
        return (
            "You are an autonomous agent with access to tools.\n\n"
            f"Available tools:\n{tool_desc}\n\n"
            f"Task: {task.description}\n\n"
            "Use this format:\n"
            "Thought: [your reasoning]\n"
            "Action: tool_name(param1=\"value1\", param2=\"value2\")\n"
            "Observation: [tool result will appear here]\n"
            "... (repeat Thought/Action/Observation as needed)\n"
            "Final Answer: [your final response]\n"
        )

    def _parse_action(self, action_line: str) -> tuple[str, dict]:
        """Parse 'tool_name(k=v, ...)' into (name, params). Best-effort, simple types only."""
        import re
        name_match = re.match(r"^\s*([A-Za-z_][\w\-]*)\s*\((.*)\)\s*$", action_line)
        if not name_match:
            return action_line.strip(), {}
        tool_name = name_match.group(1)
        inside = name_match.group(2).strip()
        if not inside:
            return tool_name, {}
        params = {}
        # Split on commas not inside quotes
        parts = re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", inside)
        for part in parts:
            if not part.strip():
                continue
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            key = k.strip()
            val = v.strip()
            # Strip surrounding quotes if present
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            else:
                # Try int
                try:
                    val = int(val)
                except Exception:
                    # leave as string
                    pass
            params[key] = val
        return tool_name, params

    def _execute_react(self, agent: Agent, task: Task, context: Optional[ExecutionContext]) -> tuple[str, list]:
        """Run a simple ReAct loop using plain-text action parsing and the tool registry."""
        messages = []
        # Seed with ReAct instructions and task
        react_context = self._build_react_context(task)
        messages.append({"role": "system", "content": react_context})
        if context and getattr(context, "history", None):
            messages.extend(context.history[-3:])

        for _ in range(self.react_max_iterations):
            response = self.llm_provider.generate(messages=messages, config=self.default_config)
            messages.append({"role": "assistant", "content": response})

            if "Final Answer:" in response:
                final = response.split("Final Answer:", 1)[1].strip()
                return final, messages

            if "Action:" in response:
                action_line = response.split("Action:", 1)[1].split("\n", 1)[0].strip()
                tool_name, params = self._parse_action(action_line)

                # Phase 2a: Pass team_name to get_tool if using TeamAwareToolRegistry
                # Check if registry supports team_name parameter (duck typing)
                tool = None
                if self.tool_registry:
                    # Try team-aware get_tool with team_name from context
                    team_name = context.team_name if context and hasattr(context, 'team_name') else ""
                    try:
                        # TeamAwareToolRegistry accepts team_name parameter
                        tool = self.tool_registry.get_tool(tool_name, team_name=team_name)
                    except TypeError:
                        # Base ToolRegistry doesn't accept team_name - fallback to positional arg
                        tool = self.tool_registry.get_tool(tool_name)

                if tool is None:
                    messages.append({"role": "user", "content": f"Observation: Error - tool '{tool_name}' not found"})
                    # Phase 2b: Record failed tool access (tool not found)
                    if self.tool_history_repo and context:
                        try:
                            import time
                            self.tool_history_repo.record_tool_execution(
                                tool_name=tool_name,
                                team_name=context.team_name if hasattr(context, 'team_name') else "",
                                agent_role=agent.role,
                                parameters=params,
                                result=f"Error: tool '{tool_name}' not found",
                                status="failure",
                                duration_ms=0,
                                session_id=context.session_id if hasattr(context, 'session_id') else "",
                                task_description=task.description[:100]
                            )
                        except Exception as e:
                            # Logging tool execution failures should not break agent execution
                            self.logger.warning(f"Failed to record tool execution history: {e}")
                    continue

                # Phase 2b: Track tool execution time
                import time
                start_time = time.time()
                try:
                    result = tool.execute(**params)
                    status = "success"
                except Exception as e:  # Tools should return str, but guard anyway
                    result = f"Error: {e}"
                    status = "failure"
                duration_ms = int((time.time() - start_time) * 1000)

                # Phase 2b: Record tool execution history
                if self.tool_history_repo and context:
                    try:
                        self.tool_history_repo.record_tool_execution(
                            tool_name=tool_name,
                            team_name=context.team_name if hasattr(context, 'team_name') else "",
                            agent_role=agent.role,
                            parameters=params,
                            result=result[:1000] if len(result) > 1000 else result,  # Truncate large results
                            status=status,
                            duration_ms=duration_ms,
                            session_id=context.session_id if hasattr(context, 'session_id') else "",
                            task_description=task.description[:100]
                        )
                    except Exception as e:
                        # Logging tool execution failures should not break agent execution
                        self.logger.warning(f"Failed to record tool execution history: {e}")

                messages.append({"role": "user", "content": f"Observation: {result}"})
                continue

            # If neither action nor final answer provided, treat response as final
            return response.strip(), messages

        return "Max iterations reached without final answer", messages

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

IMPORTANT: You must generate the actual artifact/output, NOT explain how to do it.

INSTRUCTIONS:
1. If the task requires code: Write the complete, working code (NO explanations)
2. If the task requires a document: Write the complete document (NO meta-discussion)
3. If the task requires configuration: Provide the actual config file content
4. DO NOT write "I need to...", "Let's think...", or "First, I should..." - JUST DO IT
5. Return ONLY the requested artifact

Generate the output now:"""

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