# Qwen-Agent Integration Strategy for ATADO

**Date**: October 15, 2025
**Context**: Integration plan for Qwen-Agent framework with ATADO architecture
**Reference**: [Qwen-Agent GitHub](https://github.com/QwenLM/Qwen-Agent)

---

## Executive Summary

**Recommendation**: **Wrap Qwen-Agent within our Clean Architecture** (Option 2)

**Rationale**:
- Maintains our Clean Architecture and SOLID principles
- Leverages Qwen-specific optimizations (Hermes-style templates, parallel tool calls)
- Allows multi-provider support (Qwen-Agent for Qwen3, our adapters for others)
- Follows Dependency Inversion Principle (Qwen-Agent as implementation detail)
- Gets official support and updates from Qwen team

---

## What is Qwen-Agent?

### Overview
Qwen-Agent is the **official agent framework** from the Qwen team for building LLM applications with:
- Function calling (Hermes-style, optimized for Qwen3)
- Parallel tool calls
- RAG, Code Interpreter, Browser Assistant
- Model Context Protocol (MCP) support
- Built-in tools ecosystem

### Architecture Components

```
Qwen-Agent Architecture:
┌─────────────────────────────────────┐
│           Application               │
├─────────────────────────────────────┤
│  Agent (FnCallAgent, ReActChat)     │ <- High-level agent orchestration
├─────────────────────────────────────┤
│  BaseChatModel                      │ <- LLM abstraction (function calling)
│  BaseTool                           │ <- Tool abstraction
├─────────────────────────────────────┤
│  Tool Calling Templates (Hermes)    │ <- Qwen3-optimized prompts
└─────────────────────────────────────┘
```

**Key Classes**:
- `BaseChatModel`: LLM abstraction with function calling
- `BaseTool`: Tool definition interface
- `Agent`: High-level agent orchestration (Assistant, FnCallAgent, ReActChat)

---

## Integration Options Analysis

### Option 1: Replace Our Architecture with Qwen-Agent ❌

**Approach**: Use Qwen-Agent as primary architecture, deprecate our adapters

```python
# Direct Qwen-Agent usage
from qwen_agent.agents import Assistant

llm_cfg = {'model': 'Qwen/Qwen3-Next-80B-A3B-Instruct'}
tools = ['code_interpreter', 'image_gen']

bot = Assistant(llm=llm_cfg, function_list=tools)
responses = bot.run(messages=[{'role': 'user', 'content': task}])
```

**Pros**:
- ✅ Simplest integration path
- ✅ Full access to Qwen-Agent features
- ✅ Maintained by Qwen team

**Cons**:
- ❌ **Violates Clean Architecture** - tight coupling to Qwen-Agent
- ❌ **Vendor lock-in** - hard to support other models (Grok, DeepSeek, etc.)
- ❌ **Lost investment** - our existing adapter layer wasted
- ❌ **Less flexible** - Qwen-Agent's opinions override ours

**Verdict**: ❌ **Rejected** - Violates our architectural principles

---

### Option 2: Wrap Qwen-Agent (Adapter Pattern) ✅ **RECOMMENDED**

**Approach**: Qwen-Agent as implementation detail behind `ITextGenerator`

```python
# ATADO Architecture (unchanged)
ITextGenerator (interface)
    ├── GrokAdapter
    ├── TongyiAdapter
    └── QwenAgentAdapter  <- NEW: Wraps Qwen-Agent

# Usage (unchanged)
provider = create_provider('qwen-agent', config)
result = provider.generate(prompt, tools=tools)
```

**Architecture**:
```
ATADO Clean Architecture:
┌──────────────────────────────────────────┐
│  Use Cases (TaskCoordinator)             │
│  ↓ depends on                            │
│  ITextGenerator (interface)              │ <- Our abstraction
│  ↓ implements                            │
│  QwenAgentAdapter (adapter)              │ <- New adapter
│  ↓ wraps                                 │
│  Qwen-Agent (Assistant, BaseTool)        │ <- External framework
└──────────────────────────────────────────┘
```

**Pros**:
- ✅ **Maintains Clean Architecture** - Qwen-Agent is implementation detail
- ✅ **Gets Qwen optimizations** - Hermes templates, parallel calls, MCP
- ✅ **Multi-provider support** - Qwen-Agent alongside Grok, Tongyi, etc.
- ✅ **Dependency Inversion** - Our code depends on our interface, not Qwen-Agent
- ✅ **Easy testing** - Can mock ITextGenerator, swap implementations
- ✅ **Future-proof** - Can migrate away from Qwen-Agent if needed

**Cons**:
- ⚠️ **Wrapper complexity** - Translation layer between our API and Qwen-Agent's
- ⚠️ **Potential feature gaps** - May not expose all Qwen-Agent features
- ⚠️ **Maintenance** - Need to update wrapper when Qwen-Agent changes

**Verdict**: ✅ **RECOMMENDED** - Best balance of optimization and architecture

---

### Option 3: Learn from Qwen-Agent, Implement Our Own ⚠️

**Approach**: Study Qwen-Agent's patterns, implement similar in our adapter

```python
# Our own implementation inspired by Qwen-Agent
class Qwen3NextAdapter(ITextGenerator):
    def _format_tools_hermes_style(self, tools):
        # Implement Hermes-style tool formatting
        pass

    def _parse_tool_calls(self, response):
        # Implement Qwen-Agent's parsing logic
        pass
```

**Pros**:
- ✅ **Full control** - No external dependency
- ✅ **Clean Architecture** - Pure ATADO design
- ✅ **Optimized for our use cases** - Only implement what we need

**Cons**:
- ❌ **Reinventing wheel** - Qwen-Agent already solves this
- ❌ **Miss optimizations** - Qwen team has deep Qwen3 knowledge
- ❌ **Maintenance burden** - We maintain Qwen-specific logic
- ❌ **No official updates** - Miss Qwen-Agent improvements

**Verdict**: ⚠️ **Not Recommended** - Too much work for marginal benefits

---

## Recommended Implementation: Option 2 (Wrapper)

### Architecture Design

**Adapter Pattern**:
```python
# Our interface (unchanged)
class ITextGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_with_tools(self, task: Task, tools: List[Tool]) -> AgentResponse:
        pass


# New adapter wrapping Qwen-Agent
class QwenAgentAdapter(ITextGenerator):
    """Adapter wrapping Qwen-Agent framework for Qwen3 models."""

    def __init__(self, config: QwenAgentConfig):
        self.config = config
        # Initialize Qwen-Agent's Assistant
        self._bot = self._create_qwen_agent()

    def generate(self, prompt: str, **kwargs) -> str:
        # Convert to Qwen-Agent message format
        messages = [{'role': 'user', 'content': prompt}]
        responses = self._bot.run(messages=messages)
        return responses[-1]['content']

    def generate_with_tools(self, task: Task, tools: List[Tool]) -> AgentResponse:
        # Convert our Tool format to Qwen-Agent BaseTool format
        qwen_tools = [self._convert_tool(t) for t in tools]

        # Recreate bot with tools
        self._bot = self._create_qwen_agent(tools=qwen_tools)

        # Execute
        messages = self._format_task_as_messages(task)
        responses = self._bot.run(messages=messages)

        # Parse response
        return self._parse_qwen_response(responses)
```

---

### Implementation Plan

#### Phase 1: Basic Wrapper (Week 1)

**File**: `src/adapters/llm/qwen_agent_adapter.py`

```python
"""Qwen-Agent adapter for ATADO - Wraps official Qwen-Agent framework."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import os

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

from src.interface.llm_provider import ITextGenerator
from src.entity import Task, Agent


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
    """

    def __init__(self, config: QwenAgentConfig):
        """Initialize Qwen-Agent adapter.

        Args:
            config: Qwen-Agent configuration
        """
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
    ) -> Assistant:
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
            **kwargs: Override configuration

        Returns:
            Generated text
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
            List of Qwen-Agent compatible tools
        """
        qwen_tools = []

        for tool in tools:
            # Register custom tool in Qwen-Agent
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)

            # Create dynamic BaseTool subclass
            @register_tool(tool_name)
            class DynamicATADOTool(BaseTool):
                description = tool.description if hasattr(tool, 'description') else f"ATADO tool: {tool_name}"
                parameters = self._convert_tool_params(tool)

                def call(self, params: str, **kwargs) -> str:
                    # Delegate to ATADO tool
                    return tool.execute(params) if hasattr(tool, 'execute') else str(tool)

            # Store reference
            self._custom_tools[tool_name] = DynamicATADOTool

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
    """
    config = QwenAgentConfig(
        model=model,
        model_server=endpoint_url or os.getenv('QWEN_ENDPOINT', 'http://localhost:8000/v1'),
        api_key=os.getenv('HF_TOKEN', 'EMPTY'),
        thinking_mode=thinking_mode
    )

    return QwenAgentAdapter(config)
```

---

#### Phase 2: Factory Integration (Week 1)

**File**: `src/factories/llm_provider_factory.py` (update)

```python
def create_provider(provider_name: str, config: Optional[Dict] = None) -> ITextGenerator:
    """Create LLM provider by name.

    Args:
        provider_name: Provider identifier
        config: Optional configuration

    Returns:
        ITextGenerator implementation
    """
    config = config or {}

    if provider_name == "qwen-agent":
        from src.adapters.llm.qwen_agent_adapter import create_qwen_agent_adapter
        return create_qwen_agent_adapter(
            model=config.get("model", "Qwen/Qwen3-Next-80B-A3B-Instruct"),
            endpoint_url=config.get("endpoint_url"),
            thinking_mode=config.get("thinking_mode", False)
        )

    elif provider_name == "grok":
        # Existing Grok adapter
        pass

    # ... other providers

    raise ValueError(f"Unknown provider: {provider_name}")
```

---

#### Phase 3: Configuration (Week 1)

**File**: `config/llm_providers.yaml` (new)

```yaml
providers:
  qwen-agent:
    type: qwen-agent
    model: "Qwen/Qwen3-Next-80B-A3B-Instruct"
    endpoint_url: "${QWEN_ENDPOINT}"  # From env
    thinking_mode: false
    max_tokens: 16384
    temperature: 0.7

  qwen-agent-thinking:
    type: qwen-agent
    model: "Qwen/Qwen3-Next-80B-A3B-Thinking"
    endpoint_url: "${QWEN_ENDPOINT}"
    thinking_mode: true
    max_tokens: 32768
    temperature: 0.7

  grok:
    type: grok
    # ... existing config

  tongyi:
    type: tongyi
    # ... existing config
```

---

### Phase 4: Testing (Week 2)

**File**: `tests/adapters/llm/test_qwen_agent_adapter.py`

```python
"""Tests for Qwen-Agent adapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.adapters.llm.qwen_agent_adapter import (
    QwenAgentAdapter,
    QwenAgentConfig,
    create_qwen_agent_adapter
)
from src.entity import Task


@pytest.fixture
def mock_qwen_agent():
    """Mock Qwen-Agent Assistant."""
    with patch('src.adapters.llm.qwen_agent_adapter.Assistant') as mock:
        instance = MagicMock()
        instance.run.return_value = [
            {'role': 'assistant', 'content': 'Test response'}
        ]
        mock.return_value = instance
        yield mock


def test_adapter_initialization():
    """Test adapter initializes correctly."""
    config = QwenAgentConfig(model="Qwen/Qwen3-8B")
    adapter = QwenAgentAdapter(config)

    assert adapter.config.model == "Qwen/Qwen3-8B"
    assert adapter._bot is None  # Lazy init


def test_generate_basic(mock_qwen_agent):
    """Test basic generation."""
    config = QwenAgentConfig()
    adapter = QwenAgentAdapter(config)

    result = adapter.generate("Test prompt")

    assert result == "Test response"
    mock_qwen_agent.assert_called_once()


def test_generate_with_tools(mock_qwen_agent):
    """Test tool-calling generation."""
    config = QwenAgentConfig()
    adapter = QwenAgentAdapter(config)

    task = Task(id="test", description="Refactor code")

    # Mock tool
    tool = Mock()
    tool.name = "analyze_code"
    tool.description = "Analyze code quality"
    tool.parameters = [{'name': 'code', 'type': 'string'}]

    # Mock response with tool call
    mock_qwen_agent.return_value.run.return_value = [
        {
            'role': 'assistant',
            'content': 'Analysis complete',
            'function_call': {'name': 'analyze_code', 'arguments': '{"code": "..."}'}
        }
    ]

    result = adapter.generate_with_tools(task, [tool])

    assert 'content' in result
    assert 'tool_calls' in result
    assert len(result['tool_calls']) > 0


def test_thinking_mode_enabled():
    """Test thinking mode configuration."""
    config = QwenAgentConfig(
        model="Qwen/Qwen3-Next-80B-A3B-Thinking",
        thinking_mode=True
    )
    adapter = QwenAgentAdapter(config)

    assert adapter.config.thinking_mode is True
```

**File**: `tests/integration/test_qwen_agent_real.py`

```python
"""Integration test with real Qwen-Agent (requires endpoint)."""

import pytest
import os

from src.adapters.llm.qwen_agent_adapter import create_qwen_agent_adapter
from src.entity import Task


@pytest.mark.skipif(
    not os.getenv("QWEN_ENDPOINT"),
    reason="Requires QWEN_ENDPOINT environment variable"
)
def test_qwen_agent_real_inference():
    """Test real inference with Qwen-Agent."""
    adapter = create_qwen_agent_adapter(
        endpoint_url=os.getenv("QWEN_ENDPOINT")
    )

    response = adapter.generate("What is 2+2? Be concise.")

    assert "4" in response
    assert len(response) > 0


@pytest.mark.skipif(
    not os.getenv("QWEN_ENDPOINT"),
    reason="Requires QWEN_ENDPOINT environment variable"
)
def test_qwen_agent_tool_calling_real():
    """Test real tool calling."""
    adapter = create_qwen_agent_adapter(
        endpoint_url=os.getenv("QWEN_ENDPOINT")
    )

    task = Task(
        id="test-math",
        description="Calculate the factorial of 5"
    )

    # Simple mock tool
    class CalculatorTool:
        name = "calculator"
        description = "Perform mathematical calculations"
        parameters = [{'name': 'expression', 'type': 'string', 'required': True}]

        def execute(self, params):
            return "120"  # 5! = 120

    result = adapter.generate_with_tools(task, [CalculatorTool()])

    assert '120' in result['content']
    # May have tool calls
    if result['tool_calls']:
        assert result['tool_calls'][0]['name'] == 'calculator'
```

---

## Benefits of This Approach

### 1. Best of Both Worlds ✅
- **Qwen Optimizations**: Hermes-style templates, parallel calls, MCP
- **Our Architecture**: Clean Architecture, SOLID principles, testability

### 2. Multi-Provider Support ✅
```python
# Can use Qwen-Agent for Qwen3 models
qwen_provider = create_provider('qwen-agent', config)

# And still use other providers
grok_provider = create_provider('grok', config)
tongyi_provider = create_provider('tongyi', config)
```

### 3. Dependency Inversion ✅
```
Use Cases → ITextGenerator ← QwenAgentAdapter → Qwen-Agent
                            ← GrokAdapter → Grok API
                            ← TongyiAdapter → Tongyi API
```
**Our code depends on our abstraction, not Qwen-Agent**

### 4. Easy Testing ✅
```python
# Unit test with mock
def test_coordinator_with_mock_provider():
    mock_provider = Mock(spec=ITextGenerator)
    coordinator = TaskCoordinator(provider=mock_provider)
    # Test without real Qwen-Agent

# Integration test with real Qwen-Agent
def test_coordinator_with_qwen_agent():
    real_provider = create_qwen_agent_adapter()
    coordinator = TaskCoordinator(provider=real_provider)
    # Test with actual Qwen-Agent
```

### 5. Future-Proof ✅
- If Qwen-Agent changes API, only update adapter
- If we want to switch frameworks, swap adapter
- No ripple effects through codebase

---

## Comparison: Original Plan vs Qwen-Agent Integration

| Aspect | Original Plan (Custom Adapter) | Qwen-Agent Integration (Wrapper) |
|--------|-------------------------------|-----------------------------------|
| **Function Calling** | Custom implementation | Hermes-style (Qwen3-optimized) ✅ |
| **Parallel Tool Calls** | Sequential | Native parallel support ✅ |
| **MCP Support** | Would need to implement | Built-in ✅ |
| **Tool Ecosystem** | Custom tools only | Built-in + custom tools ✅ |
| **Maintenance** | We maintain Qwen-specific logic | Qwen team maintains ✅ |
| **Updates** | Manual tracking | Automatic with Qwen-Agent updates ✅ |
| **Architecture** | Clean Architecture ✅ | Clean Architecture ✅ |
| **Flexibility** | Full control ✅ | Wrapped, slightly constrained |
| **Complexity** | Lower (direct implementation) | Slightly higher (wrapper layer) |

**Winner**: Qwen-Agent Integration - Gets optimizations without sacrificing architecture

---

## Migration Path

### Week 1: Setup
1. Install Qwen-Agent: `pip install -U "qwen-agent[gui,rag,code_interpreter,mcp]"`
2. Implement `QwenAgentAdapter`
3. Update factory
4. Write unit tests

### Week 2: Testing
1. Integration tests with real endpoint
2. Benchmark against custom adapter
3. Validate tool calling accuracy

### Week 3: Deployment
1. Deploy alongside existing providers
2. Route Qwen3 tasks to Qwen-Agent adapter
3. Monitor performance and costs

### Week 4: Optimization
1. Fine-tune configuration
2. Add Qwen-Agent built-in tools (code_interpreter, etc.)
3. Explore MCP capabilities

---

## Next Steps

1. ✅ Research complete - Qwen-Agent understood
2. ⏳ Install Qwen-Agent framework
3. ⏳ Implement QwenAgentAdapter wrapper
4. ⏳ Write tests
5. ⏳ Deploy and validate

---

## Conclusion

**Wrapping Qwen-Agent within our Clean Architecture** is the optimal solution:

- ✅ Maintains SOLID principles and Clean Architecture
- ✅ Leverages Qwen team's optimizations (Hermes templates, parallel calls)
- ✅ Supports multiple providers (Qwen-Agent, Grok, Tongyi)
- ✅ Future-proof and testable
- ✅ Best performance without architectural compromise

**This is how Qwen-Agent fits into ATADO**: As a powerful implementation detail behind our `ITextGenerator` interface, giving us the best of both worlds.

---

**Prepared by**: Claude Code (Sonnet 4.5)
**Date**: October 15, 2025
**Status**: Ready for implementation
