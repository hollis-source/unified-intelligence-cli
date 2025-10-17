"""Qwen-Agent adapter for ATADO - Wraps official Qwen-Agent framework.

This adapter maintains ATADO's Clean Architecture while leveraging
Qwen-Agent's optimized function calling and tool handling for Qwen3 models.

Architecture:
    ATADO Use Cases
        ↓ depends on
    ITextGenerator (interface)
        ↓ implements
    QwenAgentAdapter (this file) ← Wrapper
        ↓ wraps
    Qwen-Agent framework
        ↓ uses
    Qwen3-Next-80B-A3B (model)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import os
import warnings

try:
    from qwen_agent.agents import Assistant
    from qwen_agent.tools.base import BaseTool, register_tool
    QWEN_AGENT_AVAILABLE = True
except ImportError:
    QWEN_AGENT_AVAILABLE = False
    warnings.warn(
        "qwen-agent not installed. Install with: pip install -U 'qwen-agent[gui,rag,code_interpreter,mcp]'",
        ImportWarning
    )

from src.interface.llm_provider import ITextGenerator
from src.entity.agent import Task


@dataclass
class QwenAgentConfig:
    """Configuration for Qwen-Agent adapter."""
    model: str = "Qwen/Qwen3-Next-80B-A3B-Instruct"
    model_server: str = "http://localhost:8000/v1"  # vLLM or HF endpoint
    api_key: str = "EMPTY"
    thinking_mode: bool = False
    max_tokens: int = 16384
    temperature: float = 0.7


class QwenAgentAdapter(ITextGenerator):
    """Adapter wrapping Qwen-Agent for Qwen3 models.

    This adapter maintains ATADO's Clean Architecture while leveraging
    Qwen-Agent's optimized function calling and tool handling.

    Features:
    - Hermes-style function calling (Qwen3-optimized)
    - Parallel tool calls
    - MCP support
    - Built-in Qwen-Agent tools (code_interpreter, etc.)

    Example:
        >>> config = QwenAgentConfig(model="Qwen/Qwen3-Next-80B-A3B-Instruct")
        >>> adapter = QwenAgentAdapter(config)
        >>> result = adapter.generate("Hello, how are you?")
    """

    def __init__(self, config: QwenAgentConfig):
        """Initialize Qwen-Agent adapter.

        Args:
            config: Qwen-Agent configuration

        Raises:
            ImportError: If qwen-agent is not installed
        """
        if not QWEN_AGENT_AVAILABLE:
            raise ImportError(
                "qwen-agent is required for QwenAgentAdapter. "
                "Install with: pip install -U 'qwen-agent[gui,rag,code_interpreter,mcp]'"
            )

        self.config = config
        self._llm_cfg = self._create_llm_config()
        self._bot = None  # Lazy initialization
        self._custom_tools = {}  # Registry for ATADO tools

    def _create_llm_config(self) -> Dict[str, Any]:
        """Create Qwen-Agent LLM configuration."""
        return {
            'model': self.config.model,
            'model_server': self.config.model_server,
            'api_key': self.config.api_key,
            'generate_cfg': {
                'max_tokens': self.config.max_tokens,
                'temperature': self.config.temperature,
            }
        }

    def _create_qwen_agent(
        self,
        tools: Optional[List[str]] = None,
        system_message: Optional[str] = None
    ) -> 'Assistant':
        """Create Qwen-Agent Assistant instance.

        Args:
            tools: List of tool names or tool objects
            system_message: Optional system message

        Returns:
            Configured Assistant instance
        """
        return Assistant(
            llm=self._llm_cfg,
            function_list=tools or [],
            system_message=system_message or self._default_system_message()
        )

    def _default_system_message(self) -> str:
        """Default system message for ATADO agents."""
        return """You are an AI agent in the ATADO (Autonomous Task-Agent Dev Orchestration) system.
Your purpose is to help with software development tasks through intelligent tool use and reasoning.

When given a task:
1. Analyze the requirements carefully
2. Plan your approach step-by-step
3. Use available tools as needed
4. Provide clear, actionable results

Always prioritize:
- Clean Code principles
- Correctness over speed
- Explicit reasoning
"""

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion for prompt.

        Args:
            prompt: Input prompt
            **kwargs: Override configuration (temperature, max_tokens, etc.)

        Returns:
            Generated text

        Example:
            >>> adapter.generate("What is 2+2?")
            "2 + 2 = 4"
        """
        # Create bot if not exists
        if self._bot is None:
            self._bot = self._create_qwen_agent()

        # Convert to Qwen-Agent message format
        messages = [{'role': 'user', 'content': prompt}]

        # Execute
        responses = []
        for response in self._bot.run(messages=messages):
            responses.append(response)

        # Return last response content
        if responses and len(responses) > 0:
            last_response = responses[-1]
            if isinstance(last_response, dict):
                return last_response.get('content', '')
            return str(last_response)

        return ""

    def generate_with_tools(
        self,
        task: Task,
        tools: List[Any]  # ATADO Tool objects
    ) -> Dict[str, Any]:
        """Generate with tool-calling capabilities.

        Args:
            task: ATADO Task entity
            tools: List of ATADO Tool objects

        Returns:
            Response dict with content, tool_calls, reasoning

        Example:
            >>> task = Task(id="test", description="Analyze code")
            >>> tools = [CodeAnalysisTool()]
            >>> result = adapter.generate_with_tools(task, tools)
            >>> print(result['content'])
        """
        # Convert ATADO tools to Qwen-Agent tools
        qwen_tools = self._convert_atado_tools_to_qwen(tools)

        # Create bot with tools
        self._bot = self._create_qwen_agent(
            tools=qwen_tools,
            system_message=self._task_system_message(task)
        )

        # Format task as messages
        messages = [
            {'role': 'user', 'content': self._format_task_prompt(task)}
        ]

        # Execute with tool calling
        responses = []
        for response in self._bot.run(messages=messages):
            responses.append(response)

        # Parse and return
        return self._parse_qwen_responses(responses)

    def _convert_atado_tools_to_qwen(self, tools: List[Any]) -> List[str]:
        """Convert ATADO Tool objects to Qwen-Agent tool format.

        Args:
            tools: ATADO Tool objects

        Returns:
            List of Qwen-Agent compatible tool names
        """
        qwen_tools = []

        for tool in tools:
            # Get tool name
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)

            # Create dynamic BaseTool subclass
            tool_description = tool.description if hasattr(tool, 'description') else f"ATADO tool: {tool_name}"
            tool_params = self._convert_tool_params(tool)

            # Create closure to capture tool reference
            def create_tool_class(tool_ref, desc, params):
                @register_tool(tool_name)
                class DynamicATADOTool(BaseTool):
                    description = desc
                    parameters = params

                    def call(self, params_str: str, **kwargs) -> str:
                        # Delegate to ATADO tool
                        if hasattr(tool_ref, 'execute'):
                            return str(tool_ref.execute(params_str))
                        return str(tool_ref)

                return DynamicATADOTool

            # Create and store tool class
            tool_class = create_tool_class(tool, tool_description, tool_params)
            self._custom_tools[tool_name] = tool_class

            qwen_tools.append(tool_name)

        return qwen_tools

    def _convert_tool_params(self, tool: Any) -> List[Dict[str, Any]]:
        """Convert ATADO tool parameters to Qwen-Agent format."""
        # Default parameters if not specified
        if not hasattr(tool, 'parameters'):
            return [
                {
                    'name': 'input',
                    'type': 'string',
                    'description': 'Tool input',
                    'required': True
                }
            ]

        # Convert from ATADO format to Qwen-Agent format
        params = []
        for param in tool.parameters:
            params.append({
                'name': param.get('name', 'param'),
                'type': param.get('type', 'string'),
                'description': param.get('description', ''),
                'required': param.get('required', False)
            })

        return params

    def _task_system_message(self, task: Task) -> str:
        """Generate system message for specific task."""
        base = self._default_system_message()

        if hasattr(task, 'context') and task.context:
            base += f"\n\nTask Context:\n{task.context}"

        return base

    def _format_task_prompt(self, task: Task) -> str:
        """Format ATADO Task as prompt for Qwen-Agent."""
        prompt = f"Task: {task.description}"

        if hasattr(task, 'requirements') and task.requirements:
            prompt += f"\n\nRequirements:\n"
            for req in task.requirements:
                prompt += f"- {req}\n"

        if hasattr(task, 'constraints') and task.constraints:
            prompt += f"\n\nConstraints:\n"
            for constraint in task.constraints:
                prompt += f"- {constraint}\n"

        return prompt

    def _parse_qwen_responses(self, responses: List[Any]) -> Dict[str, Any]:
        """Parse Qwen-Agent responses into ATADO format.

        Args:
            responses: List of response dicts from Qwen-Agent

        Returns:
            Parsed response with content, tool_calls, reasoning
        """
        result = {
            'content': '',
            'tool_calls': [],
            'reasoning': [],
            'raw_responses': responses
        }

        for response in responses:
            if not isinstance(response, dict):
                continue

            # Extract content
            if 'content' in response:
                result['content'] += response['content'] + '\n'

            # Extract tool calls (Qwen-Agent format)
            if 'function_call' in response:
                result['tool_calls'].append(response['function_call'])

            # Extract reasoning (if thinking mode)
            if 'reasoning_content' in response:
                result['reasoning'].append(response['reasoning_content'])

        result['content'] = result['content'].strip()
        return result


# Factory function
def create_qwen_agent_adapter(
    model: str = "Qwen/Qwen3-Next-80B-A3B-Instruct",
    endpoint_url: Optional[str] = None,
    thinking_mode: bool = False
) -> QwenAgentAdapter:
    """Create Qwen-Agent adapter.

    Args:
        model: Qwen model ID
        endpoint_url: Optional inference endpoint URL
        thinking_mode: Enable thinking mode

    Returns:
        Configured QwenAgentAdapter

    Example:
        >>> adapter = create_qwen_agent_adapter(
        ...     model="Qwen/Qwen3-Next-80B-A3B-Instruct",
        ...     endpoint_url="https://your-endpoint.hf.space/v1"
        ... )
    """
    config = QwenAgentConfig(
        model=model,
        model_server=endpoint_url or os.getenv('QWEN_ENDPOINT', 'http://localhost:8000/v1'),
        api_key=os.getenv('HF_TOKEN', 'EMPTY'),
        thinking_mode=thinking_mode
    )

    return QwenAgentAdapter(config)
