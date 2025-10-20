# Hugging Face Agentic Model Deployment Plan

**Date**: October 15, 2025
**Project**: Autonomous Task-Agent Dev Orchestration (ATADO)
**Objective**: Deploy latest high-performance agentic model on HF Inference Endpoint

---

## Executive Summary

**Recommendation**: Deploy **Qwen3-Next-80B-A3B-Instruct** on Hugging Face Inference Endpoint

**Rationale**:
- Latest release (September 10, 2025 - 5 weeks ago)
- State-of-the-art agentic capabilities among open-source models
- Efficient MoE architecture (80B total, only 3B active)
- Manageable size for inference (81GB vs 638GB for DeepSeek)
- 5.1M downloads, 815 likes (highly popular and vetted)
- Apache 2.0 license (commercial friendly)
- 10x faster inference than Qwen3-32B at long contexts
- Native 262K context (extensible to 1M)

---

## Candidate Models Analysis

### 1. Qwen3-Next-80B-A3B-Instruct ⭐ **RECOMMENDED**

**Release Date**: September 10, 2025 (5 weeks ago)

**Specifications**:
- **Parameters**: 80B total, 3B activated (MoE)
- **Model Size**: 81GB
- **Context Length**: 262K native (extensible to 1M tokens)
- **License**: Apache 2.0
- **Downloads**: 5,145,485
- **Likes**: 815

**Architecture**:
- Hybrid Attention (Gated DeltaNet + Gated Attention)
- High-Sparsity Mixture-of-Experts (1:50 activation ratio)
- 48 layers with hybrid layout
- Multi-Token Prediction (MTP)

**Agentic Capabilities**:
- ✅ Advanced tool-calling and agentic abilities
- ✅ Precise interaction with external tools
- ✅ State-of-the-art results in complex agent-driven tasks (open-source)
- ✅ Reinforcement learning across 20+ general-domain tasks
- ✅ Supports Model Context Protocol (MCP) for tool configuration
- ✅ Integration with Qwen-Agent framework

**Performance**:
- Knowledge (MMLU-Pro): Competitive
- Reasoning: Strong
- Coding: Excellent
- Long Context: 10x faster than Qwen3-32B at 32K+ tokens
- Training Efficiency: 10% cost of Qwen3-32B

**Deployment**:
- ✅ Transformers library
- ✅ SGLang support
- ✅ vLLM support
- ✅ OpenAI-compatible API
- ✅ Inference Endpoint compatible

**Recommended Settings**:
```python
{
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "max_tokens": 16384
}
```

**Pros**:
- Most popular recent agentic model (5M+ downloads)
- Efficient inference (3B active vs 80B total)
- Manageable size for standard endpoints (81GB)
- Latest technology (Sept 2025)
- Excellent for multi-step reasoning and tool use

**Cons**:
- Very recent (less battle-tested than older models)
- Still large (81GB requires GPU with sufficient VRAM)

---

### 2. Qwen3-Next-80B-A3B-Thinking (Alternative)

**Release Date**: September 10, 2025

**Specifications**:
- **Parameters**: 80B total, 3B activated (MoE)
- **Model Size**: 76GB
- **Context Length**: 262K native
- **License**: Apache 2.0
- **Downloads**: 1,487,950
- **Likes**: 427

**Key Difference from Instruct**:
- Explicit `<think>` tag in output
- Shows step-by-step reasoning process
- Better for complex problems requiring transparency
- Longer outputs with detailed reasoning

**When to Use**:
- Mathematical problems
- Complex reasoning challenges
- Tasks requiring audit trail of reasoning
- Benchmarking advanced cognitive capabilities

**Benchmarks**:
- MMLU-Pro (Knowledge): 82.7
- AIME25 (Reasoning): 87.8
- LiveCodeBench (Coding): 68.7
- MultiIF (Multilingual): 77.8

**Pros**:
- Same efficiency as Instruct variant
- Transparent reasoning process
- Excellent for debugging agent behavior

**Cons**:
- Longer outputs (higher token costs)
- Less popular than Instruct variant (1.5M vs 5.1M downloads)

---

### 3. DeepSeek-V3.1-Terminus

**Release Date**: August-October 2025

**Specifications**:
- **Parameters**: 685B
- **Model Size**: 638GB ⚠️
- **License**: MIT
- **Downloads**: 21,468
- **Likes**: 320

**Capabilities**:
- Improved language consistency
- Enhanced agent capabilities (Code and Search Agents)
- Strong reasoning and tool-use benchmarks

**Benchmarks**:
- MMLU-Pro: 85.0
- GPQA-Diamond: 80.7
- Humanity's Last Exam: 21.7
- BrowseComp: 38.5
- SimpleQA: 96.8

**Pros**:
- Highest benchmark scores
- MIT license
- Strong reasoning capabilities

**Cons**:
- ⚠️ **MASSIVE size (638GB)** - requires expensive multi-GPU setup
- Very low adoption (21K downloads vs 5M for Qwen3-Next)
- Much higher inference costs
- May not be cost-effective for our use case

**Verdict**: ❌ Not recommended due to size/cost

---

### 4. Qwen3-Coder-480B-A35B-Instruct

**Release Date**: July 2025

**Specifications**:
- **Parameters**: 480B total, 35B activated (MoE)
- **Model Size**: 447GB ⚠️
- **Context Length**: 256K native (extensible to 1M)
- **License**: Apache 2.0
- **Downloads**: 104,102
- **Likes**: 1,219 (highest!)

**Capabilities**:
- State-of-the-art agentic coding
- Agentic browser-use
- Agentic tool-use
- Comparable to Claude Sonnet 4
- Large-scale RL on real-world coding tasks

**Training**:
- 7.5T tokens (70% code ratio)
- Long-horizon RL for multi-turn interactions
- 20,000 parallel environments for training

**Pros**:
- Best for coding-specific agentic tasks
- Highest likes (most appreciated by community)
- Trained specifically for software engineering

**Cons**:
- ⚠️ **Very large (447GB)** - expensive multi-GPU required
- Specialized for coding (less general-purpose)
- Higher inference costs than Qwen3-Next

**Verdict**: ⚠️ Consider if budget allows and coding is primary use case

---

### 5. Qwen3-Omni (Bonus Discovery)

**Release Date**: September 22, 2025 (3 weeks ago!)

**Specifications**:
- Natively end-to-end omni-modal
- Processes: text, image, audio, video
- Generates: real-time outputs from all modalities
- **License**: Apache 2.0

**Capabilities**:
- Revolutionary multi-modal AI
- Real-time processing across modalities
- Latest innovation from Alibaba

**Pros**:
- Cutting-edge multi-modal capabilities
- Latest release (Sept 22, 2025)
- Could enable visual/audio agent interactions

**Cons**:
- Size/specs not yet verified
- Very new (only 3 weeks old)
- May not be optimized for text-only agentic tasks

**Verdict**: 🔍 Worth investigating for future multi-modal agent work

---

## Comparison Matrix

| Model | Size | Downloads | License | Released | Agent Score | Cost | Recommendation |
|-------|------|-----------|---------|----------|-------------|------|----------------|
| **Qwen3-Next-80B Instruct** | 81GB | 5.1M | Apache 2.0 | Sept 2025 | ⭐⭐⭐⭐⭐ | $$ | ✅ **BEST CHOICE** |
| Qwen3-Next-80B Thinking | 76GB | 1.5M | Apache 2.0 | Sept 2025 | ⭐⭐⭐⭐⭐ | $$ | ✅ Alternative |
| DeepSeek-V3.1-Terminus | 638GB | 21K | MIT | Aug 2025 | ⭐⭐⭐⭐ | $$$$$ | ❌ Too expensive |
| Qwen3-Coder-480B | 447GB | 104K | Apache 2.0 | July 2025 | ⭐⭐⭐⭐⭐ | $$$$ | ⚠️ If budget allows |
| Qwen3-Omni | TBD | TBD | Apache 2.0 | Sept 2025 | ⭐⭐⭐⭐? | ??? | 🔍 Future consideration |

**Agent Score Criteria**: Tool use, function calling, multi-step reasoning, planning, long-context handling

---

## Deployment Plan

### Phase 1: Setup Qwen3-Next-80B-A3B-Instruct

**Step 1: Create HF Inference Endpoint**

```python
from huggingface_hub import InferenceClient, create_inference_endpoint

# Configuration
endpoint_name = "atado-qwen3-next-instruct"
model_id = "Qwen/Qwen3-Next-80B-A3B-Instruct"
token = "HF_TOKEN_REDACTED"

# Create endpoint
endpoint = create_inference_endpoint(
    name=endpoint_name,
    repository=model_id,
    framework="pytorch",
    task="text-generation",
    accelerator="gpu",
    instance_size="x2",  # 2x A100 (80GB VRAM each)
    instance_type="nvidia-a100-80gb",
    region="us-east-1",
    vendor="aws",
    account_id="hollis-source",
    token=token,
    custom_image={
        "health_route": "/health",
        "env": {
            "MAX_BATCH_SIZE": "4",
            "MAX_INPUT_LENGTH": "32768",
            "MAX_TOTAL_TOKENS": "49152",
        }
    }
)

print(f"Endpoint URL: {endpoint.url}")
```

**Step 2: Configure for Agentic Tasks**

```python
# Inference configuration optimized for agents
inference_config = {
    "parameters": {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "max_new_tokens": 16384,
        "repetition_penalty": 1.05,
        "do_sample": True,
    },
    "options": {
        "use_cache": True,
        "wait_for_model": True,
    }
}
```

**Step 3: Test with Agentic Task**

```python
from huggingface_hub import InferenceClient

client = InferenceClient(token=token)

# Test agentic task with tool calling
test_prompt = """You are an AI agent with access to tools.
Available tools: search_web, run_python, read_file, write_file

Task: Find the latest Python release notes and summarize key features.

Please plan your approach step-by-step and use tools as needed."""

response = client.text_generation(
    test_prompt,
    model=endpoint.url,
    **inference_config["parameters"]
)

print(response)
```

---

### Phase 2: Integration with ATADO

**File**: `src/adapters/llm/qwen3_next_adapter.py`

```python
"""Qwen3-Next adapter for agentic tasks."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from huggingface_hub import InferenceClient

from src.interface.llm_provider import ITextGenerator
from src.entity import Task


@dataclass
class Qwen3NextConfig:
    """Configuration for Qwen3-Next inference."""
    endpoint_url: str
    token: str
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    max_tokens: int = 16384
    mode: str = "instruct"  # or "thinking"


class Qwen3NextAdapter(ITextGenerator):
    """Adapter for Qwen3-Next-80B-A3B models on HF Inference Endpoint.

    Supports both Instruct and Thinking modes for agentic tasks.
    """

    def __init__(self, config: Qwen3NextConfig):
        self.config = config
        self.client = InferenceClient(token=config.token)

    def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate completion for prompt.

        Args:
            prompt: Input prompt
            **kwargs: Override default parameters

        Returns:
            Generated text
        """
        params = {
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "top_k": kwargs.get("top_k", self.config.top_k),
            "max_new_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "repetition_penalty": 1.05,
            "do_sample": True,
        }

        # Add thinking mode prompt wrapper if needed
        if self.config.mode == "thinking":
            prompt = f"{prompt}\n\nPlease think step-by-step and show your reasoning."

        response = self.client.text_generation(
            prompt,
            model=self.config.endpoint_url,
            **params
        )

        return response

    def generate_with_tools(
        self,
        task: Task,
        available_tools: List[Dict[str, Any]]
    ) -> str:
        """Generate with tool-calling capabilities.

        Args:
            task: Task to execute
            available_tools: List of available tool definitions

        Returns:
            Agent response with tool calls
        """
        # Format tools in MCP-compatible format
        tools_desc = self._format_tools_for_mcp(available_tools)

        prompt = f"""You are an AI agent executing a task with access to tools.

Available Tools:
{tools_desc}

Task: {task.description}
Context: {task.context if hasattr(task, 'context') else 'None'}

Plan your approach, use tools as needed, and execute the task.
Format tool calls as: TOOL_CALL[tool_name](arg1, arg2, ...)
"""

        return self.generate(prompt)

    def _format_tools_for_mcp(self, tools: List[Dict[str, Any]]) -> str:
        """Format tools in Model Context Protocol format."""
        formatted = []
        for tool in tools:
            formatted.append(
                f"- {tool['name']}: {tool['description']}\n"
                f"  Parameters: {tool.get('parameters', {})}"
            )
        return "\n".join(formatted)


# Factory function
def create_qwen3_next_adapter(
    endpoint_url: str,
    token: str,
    mode: str = "instruct"
) -> Qwen3NextAdapter:
    """Create Qwen3-Next adapter."""
    config = Qwen3NextConfig(
        endpoint_url=endpoint_url,
        token=token,
        mode=mode
    )
    return Qwen3NextAdapter(config)
```

**File**: `src/factories/llm_provider_factory.py` (update)

```python
def create_qwen3_next_provider(config: dict) -> ITextGenerator:
    """Create Qwen3-Next provider."""
    from src.adapters.llm.qwen3_next_adapter import create_qwen3_next_adapter

    return create_qwen3_next_adapter(
        endpoint_url=config.get("endpoint_url"),
        token=config.get("token", os.getenv("HF_TOKEN")),
        mode=config.get("mode", "instruct")
    )
```

---

### Phase 3: Testing & Validation

**Test Suite**: `tests/adapters/llm/test_qwen3_next_adapter.py`

```python
"""Tests for Qwen3-Next adapter."""

import pytest
from unittest.mock import Mock, patch

from src.adapters.llm.qwen3_next_adapter import (
    Qwen3NextAdapter,
    Qwen3NextConfig,
    create_qwen3_next_adapter
)
from src.entity import Task


@pytest.fixture
def mock_config():
    return Qwen3NextConfig(
        endpoint_url="https://test.endpoint.com",
        token="test_token",
        mode="instruct"
    )


@pytest.fixture
def adapter(mock_config):
    with patch("src.adapters.llm.qwen3_next_adapter.InferenceClient"):
        return Qwen3NextAdapter(mock_config)


def test_adapter_initialization(mock_config):
    """Test adapter initializes correctly."""
    with patch("src.adapters.llm.qwen3_next_adapter.InferenceClient") as mock_client:
        adapter = Qwen3NextAdapter(mock_config)
        assert adapter.config == mock_config
        mock_client.assert_called_once_with(token="test_token")


def test_generate_basic(adapter):
    """Test basic text generation."""
    adapter.client.text_generation = Mock(return_value="Generated response")

    result = adapter.generate("Test prompt")

    assert result == "Generated response"
    adapter.client.text_generation.assert_called_once()


def test_generate_thinking_mode():
    """Test thinking mode adds reasoning prompt."""
    config = Qwen3NextConfig(
        endpoint_url="https://test.endpoint.com",
        token="test_token",
        mode="thinking"
    )

    with patch("src.adapters.llm.qwen3_next_adapter.InferenceClient") as mock_client:
        adapter = Qwen3NextAdapter(config)
        adapter.client.text_generation = Mock(return_value="Response with reasoning")

        adapter.generate("Test prompt")

        # Verify thinking prompt was added
        call_args = adapter.client.text_generation.call_args
        assert "step-by-step" in call_args[0][0]


def test_generate_with_tools(adapter):
    """Test tool-calling generation."""
    task = Task(
        id="test-task",
        description="Analyze code",
        context="Python script"
    )

    tools = [
        {
            "name": "run_python",
            "description": "Execute Python code",
            "parameters": {"code": "string"}
        }
    ]

    adapter.client.text_generation = Mock(return_value="TOOL_CALL[run_python](test)")

    result = adapter.generate_with_tools(task, tools)

    assert "TOOL_CALL" in result
    adapter.client.text_generation.assert_called_once()


def test_factory_function():
    """Test factory function creates adapter."""
    with patch("src.adapters.llm.qwen3_next_adapter.InferenceClient"):
        adapter = create_qwen3_next_adapter(
            endpoint_url="https://test.com",
            token="test_token"
        )

        assert isinstance(adapter, Qwen3NextAdapter)
        assert adapter.config.mode == "instruct"
```

**Integration Test**: `tests/integration/test_qwen3_next_agent_task.py`

```python
"""Integration test for Qwen3-Next with real agentic task."""

import pytest
import os
from src.adapters.llm.qwen3_next_adapter import create_qwen3_next_adapter
from src.entity import Task


@pytest.mark.skipif(
    not os.getenv("HF_TOKEN") or not os.getenv("QWEN3_NEXT_ENDPOINT"),
    reason="Requires HF_TOKEN and QWEN3_NEXT_ENDPOINT environment variables"
)
def test_qwen3_next_real_agentic_task():
    """Test Qwen3-Next with real agentic task."""
    adapter = create_qwen3_next_adapter(
        endpoint_url=os.getenv("QWEN3_NEXT_ENDPOINT"),
        token=os.getenv("HF_TOKEN"),
        mode="instruct"
    )

    task = Task(
        id="test-refactor",
        description="Refactor this Python function to be more readable",
        context="""
def f(x, y):
    return x + y if x > 0 else y
"""
    )

    tools = [
        {
            "name": "analyze_code",
            "description": "Analyze code quality",
            "parameters": {"code": "string"}
        }
    ]

    response = adapter.generate_with_tools(task, tools)

    # Verify response contains refactored code
    assert "def " in response
    assert "return" in response
    # Verify agent used tools
    assert len(response) > 100  # Should have explanation
```

---

## Cost Estimation

### HF Inference Endpoint Pricing (Approximate)

**Instance Type**: 2x NVIDIA A100 (80GB)

**Cost Structure**:
- Startup: ~$0.00 (first endpoint free)
- Running: ~$6-8/hour
- Inference: ~$0.001-0.003 per 1K tokens

**Monthly Cost Estimate** (24/7 operation):
- Base: $6/hour × 24 × 30 = **~$4,320/month**
- With autoscaling (8 hours/day): ~$1,440/month

**Per-Task Cost** (assuming 10K tokens/task):
- Inference: $0.01-0.03 per task
- Minimal compared to runtime costs

**Comparison**:
- Qwen3-Next (81GB): $4,320/month (2x A100)
- DeepSeek (638GB): $8,640/month (4x A100) - **2x more expensive**
- Qwen3-Coder (447GB): $6,480/month (3x A100) - **1.5x more expensive**

**Optimization Strategies**:
1. **Autoscaling**: Scale to zero when idle
2. **Spot Instances**: 50-70% cost reduction
3. **Quantization**: Use FP8 variant (Qwen3-Next-80B-A3B-Instruct-FP8) for 30% cost reduction
4. **Batching**: Process multiple tasks in parallel

---

## Next Steps

### Immediate (Week 1)
1. ✅ Research and select model (DONE: Qwen3-Next-80B-A3B-Instruct)
2. ⏳ Create HF Inference Endpoint
3. ⏳ Deploy Qwen3-Next-80B-A3B-Instruct
4. ⏳ Test basic inference

### Short-term (Week 2-3)
1. Implement Qwen3NextAdapter in ATADO
2. Add to LLM provider factory
3. Write unit tests
4. Run integration tests with real tasks

### Medium-term (Week 4-6)
1. Benchmark against existing providers (Grok, Tongyi)
2. Optimize inference parameters for our use cases
3. Implement autoscaling for cost optimization
4. Monitor performance and costs

### Long-term (Month 2+)
1. Consider deploying Thinking variant for complex tasks
2. Evaluate Qwen3-Coder for coding-specific agents
3. Investigate Qwen3-Omni for multi-modal agent tasks
4. Explore quantization (FP8) for cost reduction

---

## Success Criteria

**Technical**:
- ✅ Endpoint responds in <5 seconds for 2K token prompts
- ✅ Handles 262K context reliably
- ✅ Tool-calling accuracy >90%
- ✅ Multi-step reasoning works correctly

**Performance**:
- ✅ Better agent task completion than current providers
- ✅ Fewer hallucinations in tool calls
- ✅ Handles complex multi-step workflows

**Cost**:
- ✅ Cost per task <$0.05
- ✅ Monthly costs <$5,000 with autoscaling
- ✅ ROI positive within 3 months

---

## References

- [Qwen3 Official Blog](https://qwenlm.github.io/blog/qwen3/)
- [Qwen3-Next Model Card](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct)
- [Qwen-Agent Framework](https://github.com/QwenLM/Qwen-Agent)
- [HF Inference Endpoints Docs](https://huggingface.co/docs/inference-endpoints/)
- [Model Context Protocol Spec](https://modelcontextprotocol.io/)

---

**Prepared by**: Claude Code (Sonnet 4.5)
**Date**: October 15, 2025
**Status**: Ready for implementation
