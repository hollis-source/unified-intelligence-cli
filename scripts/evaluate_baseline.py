#!/usr/bin/env python3
"""
Baseline Model Evaluation Script

Week 9 Phase 2: Evaluate Tongyi-30B on benchmark suite to establish baseline.
Measures: success rate, quality scores, latency (tokens/sec).
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics


def load_benchmark(benchmark_file: Path) -> List[Dict]:
    """Load benchmark tasks from JSONL file."""
    tasks = []
    with open(benchmark_file, 'r') as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks


def execute_task(task: Dict, provider: str = "tongyi", timeout: int = 300) -> Dict[str, Any]:
    """
    Execute a single task and measure performance.

    Returns:
        {
            "task_id": int,
            "status": "success" | "failed" | "timeout",
            "duration_ms": float,
            "output": str,
            "error": str (if failed)
        }
    """
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python3"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    cmd = [
        python_cmd,
        "-m", "src.main",
        "--task", task["description"],
        "--provider", provider,
        "--verbose"
    ]

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
            env={"PYTHONPATH": str(Path.cwd())}
        )

        duration_ms = (time.time() - start_time) * 1000

        return {
            "task_id": task["task_id"],
            "description": task["description"],
            "status": "success" if result.returncode == 0 else "failed",
            "duration_ms": duration_ms,
            "output": result.stdout[-1000:] if result.stdout else "",  # Last 1KB
            "error": result.stderr[-500:] if result.stderr else ""
        }

    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "task_id": task["task_id"],
            "description": task["description"],
            "status": "timeout",
            "duration_ms": duration_ms,
            "output": "",
            "error": f"Task timed out after {timeout}s"
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "task_id": task["task_id"],
            "description": task["description"],
            "status": "error",
            "duration_ms": duration_ms,
            "output": "",
            "error": str(e)
        }


def evaluate_benchmark(
    benchmark_file: Path,
    provider: str,
    sample_size: int = None,
    output_file: Path = None
) -> Dict[str, Any]:
    """
    Evaluate model on benchmark suite.

    Args:
        benchmark_file: Path to benchmark JSONL
        provider: LLM provider (tongyi, replicate, etc.)
        sample_size: Number of tasks to sample (None = all)
        output_file: Where to save results (JSONL)

    Returns:
        Summary metrics
    """
    # Load tasks
    tasks = load_benchmark(benchmark_file)

    # Sample if requested
    if sample_size and sample_size < len(tasks):
        import random
        tasks = random.sample(tasks, sample_size)

    print(f"📊 Evaluating {len(tasks)} tasks with {provider}...")
    print(f"📁 Benchmark: {benchmark_file.name}")
    print()

    # Execute tasks
    results = []
    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] Task {task['task_id']}: {task['description'][:60]}...", end=" ", flush=True)

        result = execute_task(task, provider)
        results.append(result)

        # Live feedback
        if result["status"] == "success":
            print(f"✓ ({result['duration_ms']/1000:.1f}s)")
        elif result["status"] == "timeout":
            print(f"⏱ TIMEOUT")
        else:
            print(f"✗ FAILED")

    # Calculate metrics
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    timeouts = [r for r in results if r["status"] == "timeout"]

    metrics = {
        "benchmark": str(benchmark_file),
        "provider": provider,
        "timestamp": datetime.now().isoformat(),
        "total_tasks": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "timeouts": len(timeouts),
        "success_rate": len(successful) / len(results) if results else 0.0,
        "avg_duration_ms": statistics.mean([r["duration_ms"] for r in successful]) if successful else 0.0,
        "median_duration_ms": statistics.median([r["duration_ms"] for r in successful]) if successful else 0.0,
        "min_duration_ms": min([r["duration_ms"] for r in successful]) if successful else 0.0,
        "max_duration_ms": max([r["duration_ms"] for r in successful]) if successful else 0.0,
        "total_time_s": sum([r["duration_ms"] for r in results]) / 1000
    }

    # Save detailed results
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        print(f"\n💾 Detailed results saved to: {output_file}")

    return metrics


def print_summary(metrics: Dict[str, Any]):
    """Print evaluation summary."""
    print("\n" + "=" * 80)
    print("BASELINE EVALUATION SUMMARY")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"  Total tasks:     {metrics['total_tasks']}")
    print(f"  ✓ Successful:    {metrics['successful']} ({metrics['success_rate']:.1%})")
    print(f"  ✗ Failed:        {metrics['failed']}")
    print(f"  ⏱ Timeouts:       {metrics['timeouts']}")
    print(f"\n⚡ Performance:")
    print(f"  Avg duration:    {metrics['avg_duration_ms']/1000:.1f}s")
    print(f"  Median duration: {metrics['median_duration_ms']/1000:.1f}s")
    print(f"  Min/Max:         {metrics['min_duration_ms']/1000:.1f}s / {metrics['max_duration_ms']/1000:.1f}s")
    print(f"  Total time:      {metrics['total_time_s']/60:.1f} minutes")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate baseline model on benchmark suite")
    parser.add_argument("--benchmark", required=True, help="Path to benchmark JSONL file")
    parser.add_argument("--provider", default="tongyi", help="LLM provider (default: tongyi)")
    parser.add_argument("--sample", type=int, help="Sample N tasks (default: all)")
    parser.add_argument("--output", help="Output file for detailed results (JSONL)")

    args = parser.parse_args()

    benchmark_file = Path(args.benchmark)
    if not benchmark_file.exists():
        print(f"Error: Benchmark file not found: {benchmark_file}")
        sys.exit(1)

    output_file = Path(args.output) if args.output else None

    # Run evaluation
    metrics = evaluate_benchmark(
        benchmark_file=benchmark_file,
        provider=args.provider,
        sample_size=args.sample,
        output_file=output_file
    )

    # Print summary
    print_summary(metrics)

    # Save summary
    if output_file:
        summary_file = output_file.parent / f"{output_file.stem}_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"📄 Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
