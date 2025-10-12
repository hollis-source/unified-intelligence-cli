#!/usr/bin/env python3
"""Query Grok about Qwen3-8B-Instruct LoRA fine-tuning and GGUF pipeline."""

from consult_grok import consult_grok

# Detailed query with context
query = """
I'm planning to fine-tune Qwen3-8B-Instruct using LoRA for a multi-agent code generation system.

Current context:
- Date: October 2025
- Hardware: 48-core AMD EPYC CPU, 110GB RAM, NO GPU
- Training data: 298 examples (238 train, 29 val, 31 test) from 5 agent types (coder, tester, researcher, coordinator, reviewer)
- Task distribution: 58% code generation, 42% non-coding (testing, research, planning)
- Baseline performance: 98.7% success rate, 20.1s avg latency (using Tongyi-30B)
- Goal: Improve speed to <12s avg latency while maintaining ≥98% quality

Questions:

1. **LoRA Fine-tuning Pipeline for Qwen3-8B-Instruct (October 2025)**:
   - What are the recommended LoRA hyperparameters (rank, alpha, dropout, target modules)?
   - Has Qwen3 architecture changed from Qwen2.5 in ways that affect LoRA?
   - Any known issues with CPU-only LoRA training on Qwen3-8B?
   - Recommended batch size and gradient accumulation for 110GB RAM?

2. **GGUF Conversion for llama.cpp**:
   - What's the best tool/method to convert Qwen3-8B-Instruct + LoRA adapters to GGUF as of Oct 2025?
   - Should I merge LoRA adapters first, or convert separately?
   - Recommended quantization levels (Q4_K_M, Q5_K_M, Q8_0) for balancing speed vs quality?
   - Any Qwen3-specific considerations for llama.cpp compatibility?

3. **Expected Performance**:
   - What inference speed can I realistically expect for Qwen3-8B GGUF on 48-core CPU?
   - Will Qwen3-8B likely maintain 98%+ quality on mixed coding+non-coding tasks?
   - Is Qwen3-8B a good choice for this use case, or should I consider alternatives?

4. **Common Pitfalls**:
   - What are the most common mistakes when fine-tuning Qwen3 models?
   - Any breaking changes from Qwen2.5 to Qwen3 that affect fine-tuning workflows?

Please provide actionable, concrete recommendations based on October 2025 best practices.
"""

print("=" * 80)
print("CONSULTING GROK: Qwen3-8B-Instruct LoRA + GGUF Pipeline")
print("=" * 80)
print()

response = consult_grok(query, verbose=True)

print("\n" + "=" * 80)
print("GROK'S RESPONSE:")
print("=" * 80)
print()
print(response)
print()
