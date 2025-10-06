#!/usr/bin/env python3
"""
Benchmark script to compare qwen3_hf_inference vs qwen3_zerogpu performance.

Tests:
- Same tasks across both providers
- Measure latency for each task
- Calculate average, min, max latencies
- Compare speedup

Clean Architecture: Standalone benchmark script, minimal dependencies.
"""

import time
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from src.adapters.llm.qwen3_hf_inference_adapter import Qwen3HFInferenceAdapter
from src.adapters.llm.qwen3_zerogpu_adapter import Qwen3InferenceAdapter


def benchmark_provider(provider, provider_name: str, tasks: list) -> dict:
    """
    Benchmark a provider with given tasks.

    Args:
        provider: ITextGenerator instance
        provider_name: Display name
        tasks: List of task messages

    Returns:
        Dict with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {provider_name}")
    print(f"{'='*60}")

    latencies = []
    results = []

    for i, task_msg in enumerate(tasks, 1):
        print(f"\nTask {i}/{len(tasks)}: {task_msg[0]['content'][:50]}...")

        start = time.time()
        try:
            response = provider.generate(task_msg)
            elapsed = time.time() - start
            latencies.append(elapsed)

            print(f"  ✅ Success: {elapsed:.2f}s")
            print(f"  Response: {response[:100]}...")
            results.append({
                "task": i,
                "status": "success",
                "latency": elapsed,
                "response": response[:200]
            })
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ Error: {e}")
            results.append({
                "task": i,
                "status": "error",
                "latency": elapsed,
                "error": str(e)
            })

    # Calculate statistics
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        success_rate = len([r for r in results if r["status"] == "success"]) / len(tasks)
    else:
        avg_latency = min_latency = max_latency = 0
        success_rate = 0

    print(f"\n{'-'*60}")
    print(f"Results for {provider_name}:")
    print(f"  Success Rate: {success_rate*100:.1f}%")
    print(f"  Avg Latency: {avg_latency:.2f}s")
    print(f"  Min Latency: {min_latency:.2f}s")
    print(f"  Max Latency: {max_latency:.2f}s")
    print(f"{'-'*60}")

    return {
        "provider": provider_name,
        "success_rate": success_rate,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "latencies": latencies,
        "results": results
    }


def main():
    """Run benchmark comparison."""

    # Test tasks (varied to test different scenarios)
    tasks = [
        [{"role": "user", "content": "What is 2+2? Answer with just the number."}],
        [{"role": "user", "content": "Name 3 programming languages. List them separated by commas."}],
        [{"role": "user", "content": "Write a function to check if a number is prime in Python."}],
        [{"role": "user", "content": "Explain Clean Architecture in one sentence."}],
        [{"role": "user", "content": "What is the capital of France? One word answer."}],
    ]

    print("\n" + "="*60)
    print("HF Inference vs ZeroGPU Benchmark")
    print("="*60)
    print(f"Testing {len(tasks)} tasks across 2 providers")

    # Initialize providers
    print("\nInitializing providers...")
    hf_inference = Qwen3HFInferenceAdapter()
    zerogpu = Qwen3InferenceAdapter()

    # Benchmark HF Inference
    hf_results = benchmark_provider(hf_inference, "qwen3_hf_inference", tasks)

    # Benchmark ZeroGPU
    zerogpu_results = benchmark_provider(zerogpu, "qwen3_zerogpu", tasks)

    # Compare results
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    print(f"\n{'Metric':<30} {'HF Inference':<20} {'ZeroGPU':<20}")
    print("-"*70)
    print(f"{'Success Rate':<30} {hf_results['success_rate']*100:.1f}%{'':<15} {zerogpu_results['success_rate']*100:.1f}%")
    print(f"{'Avg Latency':<30} {hf_results['avg_latency']:.2f}s{'':<15} {zerogpu_results['avg_latency']:.2f}s")
    print(f"{'Min Latency':<30} {hf_results['min_latency']:.2f}s{'':<15} {zerogpu_results['min_latency']:.2f}s")
    print(f"{'Max Latency':<30} {hf_results['max_latency']:.2f}s{'':<15} {zerogpu_results['max_latency']:.2f}s")

    if hf_results['avg_latency'] > 0 and zerogpu_results['avg_latency'] > 0:
        speedup = zerogpu_results['avg_latency'] / hf_results['avg_latency']
        print(f"\n{'Speedup':<30} {speedup:.1f}x faster than ZeroGPU")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if hf_results['avg_latency'] < zerogpu_results['avg_latency']:
        winner = "HF Inference"
        improvement = ((zerogpu_results['avg_latency'] - hf_results['avg_latency']) / zerogpu_results['avg_latency']) * 100
        print(f"✅ {winner} is {improvement:.1f}% faster on average")
    else:
        winner = "ZeroGPU"
        improvement = ((hf_results['avg_latency'] - zerogpu_results['avg_latency']) / hf_results['avg_latency']) * 100
        print(f"✅ {winner} is {improvement:.1f}% faster on average")

    print("\nRecommendation:")
    if hf_results['avg_latency'] < 10 and hf_results['success_rate'] >= 0.8:
        print("  → Use qwen3_hf_inference as primary provider (fast + reliable)")
    elif zerogpu_results['success_rate'] > hf_results['success_rate']:
        print("  → Use qwen3_zerogpu as primary (more reliable)")
    else:
        print("  → Hybrid approach: qwen3_hf_inference primary, qwen3_zerogpu fallback")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
