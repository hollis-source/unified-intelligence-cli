# Agent Tool-Use Architecture

**Status**: Design Phase
**Goal**: Make multi-agent system useful by adding tool capabilities
**Date**: 2025-10-12

## Problem Statement

Current agent system is limited to text generation:
- ❌ Cannot read files
- ❌ Cannot execute code
- ❌ Cannot write files
- ❌ Cannot search codebases
- ❌ Cannot interact with external systems

**Result**: Agents are glorified text generators, not autonomous workers.

## Solution: ReAct Pattern + Tool Registry

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Request                         │
│         "Analyze Clean Architecture book chunk"          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   LLM Executor        │
         │   (ReAct Pattern)     │
         └───────┬───────────────┘
                 │
                 │ Think → Act → Observe
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│FileRead│  │  Bash  │  │ Write  │
│  Tool  │  │  Tool  │  │  Tool  │
└────────┘  └────────┘  └────────┘
     │           │           │
     └───────────┴───────────┘
                 │
                 ▼
         ┌───────────────┐
         │    Result     │
         └───────────────┘
```

### Components

#### 1. Tool Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class AgentTool(ABC):
    """Base interface for agent tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM to reference"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this tool does (for LLM context)"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema of tool parameters"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute tool and return result"""
        pass
```

#### 2. Concrete Tools

```python
class FileReaderTool(AgentTool):
    """Reads file contents"""

    name = "read_file"
    description = "Read contents of a file at given path"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to file"
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum lines to read (optional)",
                "default": 10000
            }
        },
        "required": ["file_path"]
    }

    def execute(self, file_path: str, max_lines: int = 10000) -> str:
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()[:max_lines]
            return ''.join(lines)
        except Exception as e:
            return f"Error reading file: {str(e)}"


class BashExecutorTool(AgentTool):
    """Executes bash commands"""

    name = "bash"
    description = "Execute bash command and return output"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Bash command to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["command"]
    }

    def execute(self, command: str, timeout: int = 30) -> str:
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"


class FileWriterTool(AgentTool):
    """Writes content to file"""

    name = "write_file"
    description = "Write content to file at given path"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to file"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            }
        },
        "required": ["file_path", "content"]
    }

    def execute(self, file_path: str, content: str) -> str:
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} chars to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
```

#### 3. Tool Registry

```python
class ToolRegistry:
    """Manages available tools for agents"""

    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> AgentTool:
        """Get tool by name"""
        return self.tools.get(name)

    def get_tool_descriptions(self) -> str:
        """Format tool descriptions for LLM context"""
        descriptions = []
        for tool in self.tools.values():
            descriptions.append(
                f"Tool: {tool.name}\n"
                f"Description: {tool.description}\n"
                f"Parameters: {tool.parameters}\n"
            )
        return "\n".join(descriptions)
```

#### 4. ReAct Executor

```python
class ReActExecutor:
    """Executes agent tasks using ReAct pattern"""

    def __init__(self, llm_provider, tool_registry: ToolRegistry):
        self.llm = llm_provider
        self.tools = tool_registry
        self.max_iterations = 10

    def execute(self, task: str) -> str:
        """Execute task using Think→Act→Observe loop"""

        context = f"""You are an autonomous agent with access to tools.

Available tools:
{self.tools.get_tool_descriptions()}

Task: {task}

Use this format:
Thought: [your reasoning]
Action: tool_name(param1="value1", param2="value2")
Observation: [tool result will appear here]
... (repeat Thought/Action/Observation as needed)
Final Answer: [your final response]
"""

        history = []
        for iteration in range(self.max_iterations):
            # Get LLM response
            response = self.llm.generate(context + "\n".join(history))
            history.append(response)

            # Parse action
            if "Final Answer:" in response:
                return response.split("Final Answer:")[1].strip()

            if "Action:" in response:
                action_line = response.split("Action:")[1].split("\n")[0].strip()
                tool_name, params = self._parse_action(action_line)

                # Execute tool
                tool = self.tools.get_tool(tool_name)
                if tool:
                    result = tool.execute(**params)
                    observation = f"Observation: {result}"
                    history.append(observation)
                else:
                    history.append(f"Observation: Error - tool '{tool_name}' not found")

        return "Max iterations reached without final answer"

    def _parse_action(self, action_line: str):
        """Parse action string to extract tool name and parameters"""
        # Simple parsing: tool_name(param1="value1", param2="value2")
        # TODO: Implement robust parsing
        pass
```

### Integration with Current System

#### Location in Codebase

```
src/adapters/agent/
├── llm_executor.py          # Current executor
├── react_executor.py        # NEW: ReAct pattern executor
└── tools/
    ├── __init__.py
    ├── base.py              # AgentTool interface
    ├── file_reader.py       # FileReaderTool
    ├── bash_executor.py     # BashExecutorTool
    ├── file_writer.py       # FileWriterTool
    └── registry.py          # ToolRegistry
```

#### Composition Changes

```python
# src/composition.py

from src.adapters.agent.tools.registry import ToolRegistry
from src.adapters.agent.tools.file_reader import FileReaderTool
from src.adapters.agent.tools.bash_executor import BashExecutorTool
from src.adapters.agent.react_executor import ReActExecutor

def compose_dependencies(config):
    # ... existing code ...

    # Create tool registry
    tool_registry = ToolRegistry()
    tool_registry.register(FileReaderTool())
    tool_registry.register(BashExecutorTool())
    tool_registry.register(FileWriterTool())

    # Create ReAct executor
    react_executor = ReActExecutor(llm_provider, tool_registry)

    # Use ReAct executor for agents
    agent_executor = LLMAgentExecutor(
        llm_provider=llm_provider,
        react_executor=react_executor,  # NEW
        cache=cache
    )

    # ... rest of composition ...
```

## HuggingFace Model Selection

### Requirements for Tool-Use

1. **Function Calling**: Model must support structured outputs
2. **Reasoning**: Strong reasoning for tool selection
3. **Context Length**: 8K+ tokens (for multiple tool calls)
4. **Speed**: Fast inference for real-time agent work

### Candidate Models

| Model | Size | Context | Function Call | Speed | Notes |
|-------|------|---------|---------------|-------|-------|
| Qwen2.5-7B-Instruct | 7B | 32K | ✅ | Fast | Currently using |
| Qwen2.5-14B-Instruct | 14B | 32K | ✅ | Medium | Better reasoning |
| Llama-3.1-8B-Instruct | 8B | 128K | ✅ | Fast | Long context |
| Mistral-7B-Instruct-v0.3 | 7B | 32K | ✅ | Fast | Strong function calls |
| DeepSeek-Coder-V2-Lite | 16B | 16K | ✅ | Medium | Code-focused |

### GPU Configuration (HF Pro)

| GPU Tier | Cost/hr | VRAM | Models | Use Case |
|----------|---------|------|--------|----------|
| A10G | $1.00 | 24GB | 7B-14B | Development/testing |
| A100 (40GB) | $3.50 | 40GB | 14B-30B | Production |
| A100 (80GB) | $5.00 | 80GB | 30B-70B | Large models |
| H100 | $8.00 | 80GB | Any | Maximum speed |

**Recommendation**: Start with A10G + Qwen2.5-14B for development, upgrade to A100 for production.

## Implementation Plan

### Phase 1: Core Tool System (2-3 hours)
1. ✅ Create AgentTool interface
2. ✅ Implement FileReaderTool, BashExecutorTool, FileWriterTool
3. ✅ Create ToolRegistry
4. ✅ Unit tests for each tool

### Phase 2: ReAct Executor (3-4 hours)
1. ✅ Implement ReActExecutor with Think→Act→Observe loop
2. ✅ Add action parsing logic
3. ✅ Integrate with existing LLMAgentExecutor
4. ✅ Test with simple tasks

### Phase 3: Model Optimization (2-3 hours)
1. ✅ Test Qwen2.5-14B vs current 7B model
2. ✅ Configure HF inference endpoint (A10G)
3. ✅ Benchmark: speed, accuracy, cost
4. ✅ Select optimal model + GPU tier

### Phase 4: Clean Architecture Analysis (1 hour)
1. ✅ Use tool-enabled agents to analyze book chunks
2. ✅ Verify FileReaderTool works correctly
3. ✅ Generate comprehensive content map
4. ✅ Validate against original goal

## Success Metrics

1. **Tool Execution**: Agents successfully use read_file, bash, write_file
2. **Task Completion**: Clean Architecture analysis completes successfully
3. **Performance**: <30s per chunk analysis (7 chunks total)
4. **Quality**: Content map covers ALL major principles from book

## Next Steps

1. Implement Phase 1 (Core Tool System)
2. Test with simple file reading task
3. Proceed to ReAct pattern if Phase 1 succeeds
4. Optimize model selection once tool-use works

---

**Key Insight**: The breakthrough isn't better prompts or models—it's giving agents the ability to **ACT** (tools) not just **THINK** (text generation).
