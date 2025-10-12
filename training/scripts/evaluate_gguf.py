#!/usr/bin/env python3
"""
Evaluate GGUF Model using llama.cpp Inference

Evaluates GGUF models (Q5_K_M, Q4_K_M, f16) on test set using llama.cpp.
Compares speed and quality across quantization levels.

Usage:
    python3 evaluate_gguf.py --model training/models/Qwen3-8B-Q5_K_M.gguf
    python3 evaluate_gguf.py --model training/models/qwen3-8b-merged-q4-k-m.gguf --name Q4_K_M
"""

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


# Baseline metrics
BASELINE_SUCCESS_RATE = 98.7  # %
BASELINE_AVG_LATENCY = 20.1   # seconds

# llama.cpp binary path
LLAMA_CPP_DIR = Path.home() / "llama.cpp"
LLAMA_CLI = LLAMA_CPP_DIR / "build/bin/llama-cli"


def load_test_data(test_file: Path) -> List[Dict[str, Any]]:
    """Load test dataset from JSONL file."""
    print(f"\n📂 Loading test data from: {test_file}")

    examples = []
    with open(test_file, 'r') as f:
        for line in f:
            examples.append(json.loads(line))

    print(f"✓ Loaded {len(examples)} test examples")
    return examples


def extract_prompt_and_expected(example: Dict[str, Any]) -> tuple:
    """
    Extract prompt and expected response from test example.

    Format: <|im_start|>system\n...\n<|im_end|>\n<|im_start|>user\n...\n<|im_end|>\n<|im_start|>assistant\n...\n<|im_end|>
    """
    text = example["text"]

    # Split by <|im_end|>
    parts = text.split("<|im_end|>")

    # Extract system + user messages (prompt)
    system_msg = parts[0] + "<|im_end|>"  # system
    user_msg = parts[1] + "<|im_end|>"    # user
    prompt = system_msg + user_msg + "\n<|im_start|>assistant\n"

    # Extract expected response
    assistant_part = parts[2].strip()
    expected_response = assistant_part.replace("<|im_start|>assistant\n", "")

    return prompt, expected_response


def run_llama_inference(
    model_path: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.0
) -> tuple:
    """
    Run inference using llama.cpp.

    Returns:
        (generated_text, latency_seconds)
    """
    cmd = [
        str(LLAMA_CLI),
        "-m", model_path,
        "-p", prompt,
        "-n", str(max_tokens),
        "--temp", str(temperature),
        "--log-disable",  # Disable logging for clean output
        "-ngl", "0",       # CPU only
        "-t", "48"         # Use 48 threads
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout per example
            check=False
        )
        latency = time.time() - start_time

        # Extract generated text from output
        # llama-cli outputs the full prompt + generation
        output = result.stdout

        # Find where assistant response starts
        if "<|im_start|>assistant" in output:
            generated = output.split("<|im_start|>assistant")[-1]
            # Remove any trailing tokens
            generated = generated.split("<|im_end|>")[0].strip()
        else:
            generated = output.strip()

        return generated, latency

    except subprocess.TimeoutExpired:
        latency = time.time() - start_time
        return "", latency
    except Exception as e:
        print(f"   ⚠️  Inference error: {e}")
        return "", 0.0


def check_success(generated: str, expected: str) -> bool:
    """
    Check if generation is successful.

    Simple heuristic: generation length should be within 50-200% of expected.
    For production, use more sophisticated metrics (BLEU, ROUGE, etc.)
    """
    if not generated:
        return False

    gen_len = len(generated)
    exp_len = len(expected)

    if exp_len == 0:
        return gen_len > 0

    ratio = gen_len / exp_len
    return 0.5 <= ratio <= 2.0


def evaluate_model(
    model_path: str,
    test_data: List[Dict[str, Any]],
    model_name: str = "GGUF"
) -> Dict[str, Any]:
    """
    Evaluate GGUF model on test set.

    Returns:
        Evaluation results dictionary
    """
    print(f"\n🔍 Evaluating model: {model_path}")
    print(f"   Model name: {model_name}")
    print(f"   Test examples: {len(test_data)}")

    results = {
        "model_path": str(model_path),
        "model_name": model_name,
        "detailed_results": [],
        "agent_breakdown": defaultdict(lambda: {"total": 0, "successes": 0, "latencies": []})
    }

    for i, example in enumerate(test_data, 1):
        print(f"\n📝 Evaluating example {i}/{len(test_data)}")

        prompt, expected = extract_prompt_and_expected(example)
        agent = example.get("agent", "unknown")
        task_id = example.get("task_id", f"task_{i}")

        # Run inference
        generated, latency = run_llama_inference(model_path, prompt)
        success = check_success(generated, expected)

        # Record result
        result = {
            "task_id": task_id,
            "agent": agent,
            "success": success,
            "latency": latency,
            "generated_length": len(generated),
            "expected_length": len(expected)
        }
        results["detailed_results"].append(result)

        # Update agent breakdown
        results["agent_breakdown"][agent]["total"] += 1
        if success:
            results["agent_breakdown"][agent]["successes"] += 1
        results["agent_breakdown"][agent]["latencies"].append(latency)

        print(f"   Agent: {agent}")
        print(f"   Success: {'✓' if success else '✗'}")
        print(f"   Latency: {latency:.2f}s")
        print(f"   Generated: {len(generated)} chars | Expected: {len(expected)} chars")

    return results


def compute_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    """Compute aggregated metrics from results."""
    detailed = results["detailed_results"]

    total_examples = len(detailed)
    successful = sum(1 for r in detailed if r["success"])
    failed = total_examples - successful

    latencies = [r["latency"] for r in detailed]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0

    success_rate = (successful / total_examples * 100) if total_examples > 0 else 0

    # Agent breakdown
    agent_breakdown = {}
    for agent, data in results["agent_breakdown"].items():
        agent_success_rate = (data["successes"] / data["total"] * 100) if data["total"] > 0 else 0
        agent_avg_latency = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0

        agent_breakdown[agent] = {
            "total": data["total"],
            "success_rate": agent_success_rate,
            "avg_latency": agent_avg_latency
        }

    return {
        "success_rate": success_rate,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "total_examples": total_examples,
        "successful_examples": successful,
        "failed_examples": failed,
        "agent_breakdown": agent_breakdown
    }


def compare_to_baseline(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compare results to baseline."""
    success_delta = metrics["success_rate"] - BASELINE_SUCCESS_RATE
    latency_delta = metrics["avg_latency"] - BASELINE_AVG_LATENCY
    latency_improvement_pct = (latency_delta / BASELINE_AVG_LATENCY) * 100 if BASELINE_AVG_LATENCY > 0 else 0

    meets_success = metrics["success_rate"] >= 98.0
    meets_latency = metrics["avg_latency"] <= 12.0

    return {
        "baseline_success_rate": BASELINE_SUCCESS_RATE,
        "baseline_avg_latency": BASELINE_AVG_LATENCY,
        "success_delta": success_delta,
        "latency_delta": latency_delta,
        "latency_improvement_pct": latency_improvement_pct,
        "meets_success_target": meets_success,
        "meets_latency_target": meets_latency,
        "overall_pass": meets_success and meets_latency
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate GGUF model with llama.cpp")
    parser.add_argument("--model", "-m", type=str, required=True,
                        help="Path to GGUF model file")
    parser.add_argument("--test-data", type=str, default="training/data/test.jsonl",
                        help="Test data JSONL file")
    parser.add_argument("--output", "-o", type=str, default="training/gguf_evaluation_results.json",
                        help="Output JSON file")
    parser.add_argument("--name", type=str, default=None,
                        help="Model name (default: extracted from filename)")

    args = parser.parse_args()

    # Verify model file
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"❌ Error: Model file not found: {model_path}")
        return 1

    # Verify llama.cpp
    if not LLAMA_CLI.exists():
        print(f"❌ Error: llama-cli not found at {LLAMA_CLI}")
        print("   Please build llama.cpp first:")
        print("   cd ~/llama.cpp && cmake -B build && cmake --build build")
        return 1

    # Load test data
    test_file = Path(args.test_data)
    if not test_file.exists():
        print(f"❌ Error: Test data not found: {test_file}")
        return 1

    test_data = load_test_data(test_file)

    # Extract model name
    model_name = args.name if args.name else model_path.stem

    # Run evaluation
    print("\n" + "=" * 80)
    print("GGUF MODEL EVALUATION")
    print("=" * 80)

    results = evaluate_model(str(model_path), test_data, model_name)

    # Compute metrics
    metrics = compute_metrics(results)
    comparison = compare_to_baseline(metrics)

    # Build final output
    output = {
        "model_name": model_name,
        "model_path": str(model_path),
        "evaluation_metrics": metrics,
        "baseline_comparison": comparison,
        "detailed_results": results["detailed_results"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Save results
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)

    print(f"\n📊 Results ({model_name}):")
    print(f"   Success Rate:  {metrics['success_rate']:.2f}% (target: ≥98%)")
    print(f"   Avg Latency:   {metrics['avg_latency']:.2f}s (target: <12s)")
    print(f"   Min Latency:   {metrics['min_latency']:.2f}s")
    print(f"   Max Latency:   {metrics['max_latency']:.2f}s")

    print(f"\n📈 vs Baseline:")
    print(f"   Success Delta: {comparison['success_delta']:+.2f}%")
    print(f"   Latency Delta: {comparison['latency_delta']:+.2f}s")
    print(f"   Speed Change:  {comparison['latency_improvement_pct']:+.1f}%")

    print(f"\n💾 Results saved to: {output_path}")

    # Recommendation
    if comparison["overall_pass"]:
        print("\n✅ PASS: Model meets both success and latency targets")
        return 0
    elif comparison["meets_success_target"]:
        print("\n⚠️  PARTIAL: Quality good, but latency needs improvement")
        return 1
    elif comparison["meets_latency_target"]:
        print("\n⚠️  PARTIAL: Speed good, but quality needs improvement")
        return 1
    else:
        print("\n❌ FAIL: Neither target met")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
