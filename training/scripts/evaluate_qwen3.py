#!/usr/bin/env python3
"""
Evaluate Qwen3-8B Fine-Tuned Model on Test Set

Week 9 Phase 4: Post-training evaluation and comparison with baseline.

Usage:
    python3 evaluate_qwen3.py --model training/models/qwen3-8b-instruct-lora/final_model
    python3 evaluate_qwen3.py --model training/models/qwen3-8b-merged --merged
"""

import argparse
import json
import time
import torch
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Baseline metrics from Week 9 Phase 2
BASELINE_SUCCESS_RATE = 98.7  # %
BASELINE_AVG_LATENCY = 20.1   # seconds
TARGET_SUCCESS_RATE = 98.0    # % (goal: ≥98%)
TARGET_AVG_LATENCY = 12.0     # seconds (goal: <12s)


def load_model(model_path: str, is_merged: bool = False):
    """
    Load fine-tuned model (LoRA or merged).

    Args:
        model_path: Path to model (LoRA checkpoint or merged model)
        is_merged: True if model is already merged (no LoRA adapters)

    Returns:
        (model, tokenizer)
    """
    print(f"\n📥 Loading model from: {model_path}")
    print(f"   Model type: {'Merged' if is_merged else 'LoRA adapters'}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_path if is_merged else "Qwen/Qwen3-8B",
        trust_remote_code=True
    )

    if is_merged:
        # Load merged model directly
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True
        )
        print("✓ Merged model loaded")
    else:
        # Load base model + LoRA adapters
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-8B",
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True
        )
        model = PeftModel.from_pretrained(base_model, model_path)
        print("✓ Base model + LoRA adapters loaded")

    model.eval()  # Evaluation mode
    return model, tokenizer


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

    # Extract expected assistant response
    assistant_msg = parts[2].replace("<|im_start|>assistant\n", "").strip()

    return prompt, assistant_msg


def run_inference(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int = 512
) -> tuple:
    """
    Run inference and measure latency.

    Returns:
        (generated_text, latency_seconds)
    """
    inputs = tokenizer(prompt, return_tensors="pt")

    start_time = time.time()

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # Greedy decoding for consistency
            pad_token_id=tokenizer.eos_token_id
        )

    latency = time.time() - start_time

    # Decode only the generated tokens (exclude prompt)
    generated_text = tokenizer.decode(
        outputs[0][inputs['input_ids'].shape[1]:],
        skip_special_tokens=True
    )

    return generated_text, latency


def evaluate_quality(generated: str, expected: str) -> bool:
    """
    Simple quality check: Does generated text contain key concepts from expected?

    This is a heuristic - for production, use more sophisticated metrics.
    """
    # Normalize
    gen_lower = generated.lower()
    exp_lower = expected.lower()

    # Extract key concepts (simple heuristic: words >4 chars)
    expected_concepts = set(w for w in exp_lower.split() if len(w) > 4)

    if not expected_concepts:
        return True  # No concepts to check

    # Check if at least 30% of key concepts present
    matches = sum(1 for concept in expected_concepts if concept in gen_lower)
    coverage = matches / len(expected_concepts)

    return coverage >= 0.3


def evaluate_model(
    model,
    tokenizer,
    test_examples: List[Dict[str, Any]],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Evaluate model on test set.

    Returns:
        Dictionary with evaluation metrics
    """
    print("\n🚀 Starting evaluation...")
    print(f"   Test examples: {len(test_examples)}")
    print(f"   Target success rate: ≥{TARGET_SUCCESS_RATE}%")
    print(f"   Target avg latency: <{TARGET_AVG_LATENCY}s\n")

    results = []
    latencies = []
    successes = 0

    # Per-agent metrics
    agent_metrics = defaultdict(lambda: {"total": 0, "success": 0, "latencies": []})

    for i, example in enumerate(test_examples, 1):
        task_id = example.get("task_id", f"task_{i}")
        agent = example.get("agent", "unknown")

        print(f"[{i}/{len(test_examples)}] Evaluating {task_id} (agent: {agent})...")

        # Extract prompt and expected response
        prompt, expected = extract_prompt_and_expected(example)

        # Run inference
        try:
            generated, latency = run_inference(model, tokenizer, prompt)

            # Evaluate quality
            is_success = evaluate_quality(generated, expected)

            if is_success:
                successes += 1

            latencies.append(latency)

            # Per-agent tracking
            agent_metrics[agent]["total"] += 1
            agent_metrics[agent]["success"] += (1 if is_success else 0)
            agent_metrics[agent]["latencies"].append(latency)

            result = {
                "task_id": task_id,
                "agent": agent,
                "success": is_success,
                "latency": latency,
                "generated_length": len(generated),
                "expected_length": len(expected)
            }

            results.append(result)

            if verbose:
                print(f"  → Success: {is_success}, Latency: {latency:.2f}s")
            else:
                status_icon = "✓" if is_success else "✗"
                print(f"  {status_icon} {latency:.2f}s")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "task_id": task_id,
                "agent": agent,
                "success": False,
                "latency": 0,
                "error": str(e)
            })

    # Calculate aggregate metrics
    success_rate = (successes / len(test_examples)) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0

    # Per-agent summary
    agent_summary = {}
    for agent, metrics in agent_metrics.items():
        agent_success_rate = (metrics["success"] / metrics["total"]) * 100
        agent_avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"])
        agent_summary[agent] = {
            "total": metrics["total"],
            "success_rate": agent_success_rate,
            "avg_latency": agent_avg_latency
        }

    return {
        "success_rate": success_rate,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "total_examples": len(test_examples),
        "successful_examples": successes,
        "failed_examples": len(test_examples) - successes,
        "agent_breakdown": agent_summary,
        "detailed_results": results
    }


def compare_with_baseline(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compare evaluation metrics with baseline."""
    success_rate = metrics["success_rate"]
    avg_latency = metrics["avg_latency"]

    success_delta = success_rate - BASELINE_SUCCESS_RATE
    latency_delta = avg_latency - BASELINE_AVG_LATENCY
    latency_improvement = ((BASELINE_AVG_LATENCY - avg_latency) / BASELINE_AVG_LATENCY) * 100

    meets_success_target = success_rate >= TARGET_SUCCESS_RATE
    meets_latency_target = avg_latency < TARGET_AVG_LATENCY

    return {
        "baseline_success_rate": BASELINE_SUCCESS_RATE,
        "baseline_avg_latency": BASELINE_AVG_LATENCY,
        "success_delta": success_delta,
        "latency_delta": latency_delta,
        "latency_improvement_pct": latency_improvement,
        "meets_success_target": meets_success_target,
        "meets_latency_target": meets_latency_target,
        "overall_pass": meets_success_target and meets_latency_target
    }


def print_evaluation_report(metrics: Dict[str, Any], comparison: Dict[str, Any]):
    """Print comprehensive evaluation report."""
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)

    # Overall metrics
    print("\n📊 Overall Metrics:")
    print(f"   Success Rate:    {metrics['success_rate']:.1f}% ({metrics['successful_examples']}/{metrics['total_examples']})")
    print(f"   Avg Latency:     {metrics['avg_latency']:.2f}s")
    print(f"   Min Latency:     {metrics['min_latency']:.2f}s")
    print(f"   Max Latency:     {metrics['max_latency']:.2f}s")

    # Comparison with baseline
    print("\n📈 Comparison with Baseline:")
    print(f"   Baseline Success: {comparison['baseline_success_rate']:.1f}%")
    print(f"   Baseline Latency: {comparison['baseline_avg_latency']:.1f}s")
    print(f"   Success Delta:    {comparison['success_delta']:+.1f}%")
    print(f"   Latency Delta:    {comparison['latency_delta']:+.1f}s")
    print(f"   Speed Improvement: {comparison['latency_improvement_pct']:+.1f}%")

    # Target achievement
    print("\n🎯 Target Achievement:")
    success_icon = "✅" if comparison['meets_success_target'] else "❌"
    latency_icon = "✅" if comparison['meets_latency_target'] else "❌"
    overall_icon = "✅" if comparison['overall_pass'] else "❌"

    print(f"   Success ≥{TARGET_SUCCESS_RATE}%:  {success_icon} {metrics['success_rate']:.1f}%")
    print(f"   Latency <{TARGET_AVG_LATENCY}s:   {latency_icon} {metrics['avg_latency']:.1f}s")
    print(f"   Overall:       {overall_icon} {'PASS' if comparison['overall_pass'] else 'FAIL'}")

    # Per-agent breakdown
    print("\n📋 Per-Agent Breakdown:")
    for agent, stats in sorted(metrics['agent_breakdown'].items()):
        print(f"   {agent:20s}: {stats['success_rate']:5.1f}% success, {stats['avg_latency']:5.1f}s avg ({stats['total']} examples)")

    # Recommendation
    print("\n💡 Recommendation:")
    if comparison['overall_pass']:
        print("   ✅ DEPLOY: Model meets both success and latency targets")
    elif comparison['meets_success_target']:
        print("   ⚠️  ITERATE: Quality good, but latency needs improvement")
        print(f"       Try: Q5_K_M quantization or prompt optimization")
    elif comparison['meets_latency_target']:
        print("   ⚠️  ITERATE: Speed good, but quality needs improvement")
        print(f"       Try: More training epochs or better data")
    else:
        print("   ❌ ABORT: Neither target met, consider alternative approach")

    print("\n" + "=" * 80)


def save_results(
    metrics: Dict[str, Any],
    comparison: Dict[str, Any],
    output_file: Path
):
    """Save evaluation results to JSON file."""
    results = {
        "evaluation_metrics": metrics,
        "baseline_comparison": comparison,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Qwen3-8B fine-tuned model")
    parser.add_argument("--model", type=str, required=True,
                        help="Path to model (LoRA checkpoint or merged model)")
    parser.add_argument("--test-data", type=str, default="training/data/test.jsonl",
                        help="Path to test data JSONL file")
    parser.add_argument("--merged", action="store_true",
                        help="Model is already merged (no LoRA adapters)")
    parser.add_argument("--output", type=str, default="training/evaluation_results.json",
                        help="Output file for results")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    model_path = Path(args.model)
    test_file = Path(args.test_data)
    output_file = Path(args.output)

    if not model_path.exists():
        print(f"Error: Model not found: {model_path}")
        return 1

    if not test_file.exists():
        print(f"Error: Test data not found: {test_file}")
        return 1

    # Load model
    model, tokenizer = load_model(str(model_path), is_merged=args.merged)

    # Load test data
    test_examples = load_test_data(test_file)

    # Evaluate
    metrics = evaluate_model(model, tokenizer, test_examples, verbose=args.verbose)

    # Compare with baseline
    comparison = compare_with_baseline(metrics)

    # Print report
    print_evaluation_report(metrics, comparison)

    # Save results
    save_results(metrics, comparison, output_file)

    # Exit code: 0 if pass, 1 if fail
    return 0 if comparison['overall_pass'] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
