#!/usr/bin/env python3
"""
Test Qwen3-Next-80B-Thinking with complex architectural priority task.

This test leverages the model's full reasoning capabilities on a real
priority task for our unified-intelligence-cli project.
"""

import os
import time
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from src.adapters.llm.qwen3_next_80b_thinking_adapter import Qwen3Next80BThinkingAdapter
from src.interfaces import LLMConfig


def test_complex_architectural_task():
    """Test with complex architectural reasoning task."""

    print("="*80)
    print("Testing Qwen3-Next-80B-Thinking with Architectural Priority Task")
    print("="*80)

    # Initialize adapter
    print("\n1. Initializing adapter...")
    adapter = Qwen3Next80BThinkingAdapter()
    print(f"   ✅ Connected to: {adapter.endpoint_url}")
    print(f"   Model: {adapter.model_name}")

    # Define complex architectural task (real priority for our project)
    task = """
You are an expert software architect with deep knowledge of Clean Architecture, SOLID principles, and AI/ML systems.

**Context**: Our unified-intelligence-cli project has:
- Multi-agent orchestration system with 5-16 agents
- ModelSelector for intelligent model selection (speed, quality, cost, privacy criteria)
- Provider factory pattern with multiple LLM providers:
  * qwen3_hf_inference: 0.6-1.2s, $2/month free
  * qwen3_zerogpu: 14s, free unlimited
  * qwen3_next_80b_thinking: 10-20s, $10/hour (this model)
  * tongyi-local: 20s, $32/month TCO
  * grok: 5s, $50/month
- Team-based routing (12 teams for 16+ agents)
- Clean Architecture with DIP, OCP, SRP compliance

**Current Limitations**:
1. ModelSelector uses static capabilities (hardcoded success rates, latencies)
2. No learning from historical performance data
3. No cost optimization based on actual usage patterns
4. No dynamic adaptation to changing workload characteristics

**Priority Task**: Design an adaptive architecture that:
1. **Learns** from historical interactions (task types, actual latencies, success rates)
2. **Optimizes** model selection dynamically based on learned patterns
3. **Minimizes** cost while maintaining quality thresholds
4. **Maintains** Clean Architecture principles (no tight coupling)
5. **Scales** to handle 50+ models and 100+ agents in future

**Requirements**:
- Use SOLID principles throughout
- Preserve existing ModelSelector interface (LSP compliance)
- Add new capabilities without breaking changes (OCP)
- Support both real-time learning and offline analysis
- Include concrete implementation strategy

**Deliverables**:
1. High-level architecture diagram (described textually)
2. Key components and responsibilities (SRP)
3. Interface definitions
4. Data flow for learning and optimization
5. Integration strategy with existing codebase
6. Performance and cost impact analysis

Please reason step by step about the architectural trade-offs, then provide a comprehensive design.
"""

    messages = [
        {
            "role": "system",
            "content": "You are an expert software architect specializing in Clean Architecture, SOLID principles, and adaptive AI systems. You always reason step-by-step about trade-offs before proposing solutions."
        },
        {
            "role": "user",
            "content": task
        }
    ]

    # Configure for complex reasoning
    # Note: top_p and top_k are handled by adapter (not in LLMConfig)
    config = LLMConfig(
        temperature=0.6,
        max_tokens=32768  # Allow detailed reasoning
    )

    print("\n2. Sending complex architectural task...")
    print("   (This may take 2-3 minutes if endpoint was scaled to zero)")
    print("   (Warm requests take 10-20 seconds)")

    start = time.time()

    try:
        # Generate with thinking exposed
        response = adapter.generate_with_thinking(messages, config)
        elapsed = time.time() - start

        print(f"\n✅ Response received in {elapsed:.1f}s")

        # Display thinking process
        print("\n" + "="*80)
        print("THINKING PROCESS (Reasoning)")
        print("="*80)
        thinking_preview = response.thinking[:2000] if len(response.thinking) > 2000 else response.thinking
        print(thinking_preview)
        if len(response.thinking) > 2000:
            print(f"\n... (truncated, full thinking: {len(response.thinking)} chars)")

        # Display final answer
        print("\n" + "="*80)
        print("FINAL ARCHITECTURAL DESIGN")
        print("="*80)
        answer_preview = response.answer[:3000] if len(response.answer) > 3000 else response.answer
        print(answer_preview)
        if len(response.answer) > 3000:
            print(f"\n... (truncated, full answer: {len(response.answer)} chars)")

        # Save full output
        output_file = "qwen3_thinking_architecture_output.txt"
        with open(output_file, "w") as f:
            f.write("="*80 + "\n")
            f.write("THINKING PROCESS\n")
            f.write("="*80 + "\n\n")
            f.write(response.thinking)
            f.write("\n\n" + "="*80 + "\n")
            f.write("FINAL ARCHITECTURAL DESIGN\n")
            f.write("="*80 + "\n\n")
            f.write(response.answer)

        print(f"\n💾 Full output saved to: {output_file}")

        # Analysis
        print("\n" + "="*80)
        print("ANALYSIS")
        print("="*80)
        print(f"Latency: {elapsed:.1f}s")
        print(f"Thinking length: {len(response.thinking):,} chars")
        print(f"Answer length: {len(response.answer):,} chars")
        print(f"Total output: {len(response.raw):,} chars")
        print(f"Cost estimate: ${(elapsed / 3600) * 10:.4f} for this query")

        thinking_word_count = len(response.thinking.split())
        answer_word_count = len(response.answer.split())
        print(f"\nThinking: ~{thinking_word_count:,} words")
        print(f"Answer: ~{answer_word_count:,} words")

        if thinking_word_count > 0:
            ratio = answer_word_count / thinking_word_count
            print(f"Answer/Thinking ratio: {ratio:.2f}x")

        print("\n✅ Test completed successfully!")
        print("\n📊 Quality Assessment:")
        print("   - Does the thinking show deep reasoning? (check output file)")
        print("   - Is the architecture practical and implementable?")
        print("   - Does it maintain Clean Architecture principles?")
        print("   - Is it better than what we could design without 80B reasoning?")

        return response

    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ Error after {elapsed:.1f}s: {e}")
        print("\nTroubleshooting:")
        print("  - Check endpoint is still running")
        print("  - First request takes 2-3 min if scaled to zero")
        print("  - Complex reasoning may take up to 60s")
        raise


if __name__ == "__main__":
    test_complex_architectural_task()
