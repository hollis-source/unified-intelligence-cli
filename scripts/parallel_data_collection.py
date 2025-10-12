#!/usr/bin/env python3
"""
Parallel Data Collection Script - Week 9 Phase 1

Executes tasks in parallel across multiple providers for efficient data collection.
Utilizes system resources: 48 cores, 1TB RAM with hybrid local+GPU inference.

Usage:
    python3 scripts/parallel_data_collection.py --tasks 20 --batch-size 10
    python3 scripts/parallel_data_collection.py --random 100 --batch-size 20
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_tasks(count: int, random: bool = True) -> List[str]:
    """Extract tasks from catalog."""
    script = Path(__file__).parent / "extract_tasks.py"

    if random:
        cmd = ["python3", str(script), "--random", str(count)]
    else:
        cmd = ["python3", str(script), "--range", f"1-{count}"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to extract tasks: {result.stderr}")

    # Parse task lines (format: "123. Task description")
    tasks = []
    for line in result.stdout.strip().split('\n'):
        if line and line[0].isdigit():
            # Extract description after number
            task = line.split('. ', 1)[1] if '. ' in line else line
            tasks.append(task)

    return tasks


def execute_task(task: str, provider: str, collect_data: bool = True) -> Dict:
    """Execute a single task (runs in subprocess for parallelism)."""
    # Use venv python to have access to replicate package
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python3"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    cmd = [
        python_cmd,
        "-m", "src.main",
        "--task", task,
        "--provider", provider,
        "--verbose"
    ]

    if collect_data:
        cmd.append("--collect-data")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env={"PYTHONPATH": str(Path.cwd())}
        )

        elapsed = time.time() - start_time

        return {
            "task": task,
            "provider": provider,
            "status": "success" if result.returncode == 0 else "failed",
            "elapsed": elapsed,
            "stdout": result.stdout[-500:] if result.stdout else "",  # Last 500 chars
            "stderr": result.stderr[-500:] if result.stderr else ""
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            "task": task,
            "provider": provider,
            "status": "timeout",
            "elapsed": elapsed,
            "stdout": "",
            "stderr": "Task timed out after 300s"
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "task": task,
            "provider": provider,
            "status": "error",
            "elapsed": elapsed,
            "stdout": "",
            "stderr": str(e)
        }


def run_parallel_batch(
    tasks: List[str],
    batch_size: int = 10,
    tongyi_ratio: float = 0.5
) -> List[Dict]:
    """
    Run tasks in parallel batches across Tongyi and Replicate.

    Args:
        tasks: List of task descriptions
        batch_size: Number of parallel tasks per batch
        tongyi_ratio: Proportion of tasks to run on Tongyi (rest on Replicate)

    Returns:
        List of execution results
    """
    results = []
    total_tasks = len(tasks)

    print(f"📊 Parallel Data Collection")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Batch size: {batch_size}")
    print(f"  Tongyi/Replicate split: {tongyi_ratio:.0%}/{1-tongyi_ratio:.0%}")
    print(f"  Expected batches: {(total_tasks + batch_size - 1) // batch_size}")
    print()

    # Process in batches
    for batch_idx in range(0, total_tasks, batch_size):
        batch = tasks[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1

        print(f"🚀 Batch {batch_num}: Processing {len(batch)} tasks in parallel...")
        batch_start = time.time()

        # Assign providers (alternate for diversity)
        task_assignments = []
        for i, task in enumerate(batch):
            # Handle edge cases: 0% or 100% for single provider
            if tongyi_ratio == 0.0:
                provider = "replicate"
            elif tongyi_ratio == 1.0:
                provider = "tongyi"
            else:
                # Proportional assignment with alternation
                provider = "tongyi" if i < len(batch) * tongyi_ratio else "replicate"
            task_assignments.append((task, provider))

        # Execute in parallel using ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(execute_task, task, provider, True): (task, provider)
                for task, provider in task_assignments
            }

            batch_results = []
            for future in as_completed(futures):
                result = future.result()
                batch_results.append(result)

                # Live progress
                status_icon = "✓" if result["status"] == "success" else "✗"
                print(f"  {status_icon} [{result['provider']:9s}] {result['elapsed']:.1f}s - {result['task'][:60]}...")

        batch_elapsed = time.time() - batch_start
        successful = sum(1 for r in batch_results if r["status"] == "success")

        print(f"  Batch completed: {successful}/{len(batch)} successful in {batch_elapsed:.1f}s")
        print()

        results.extend(batch_results)

    return results


def print_summary(results: List[Dict]):
    """Print execution summary."""
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    timeout = sum(1 for r in results if r["status"] == "timeout")
    errors = sum(1 for r in results if r["status"] == "error")

    avg_time = sum(r["elapsed"] for r in results) / total if total > 0 else 0

    tongyi_count = sum(1 for r in results if r["provider"] == "tongyi")
    replicate_count = sum(1 for r in results if r["provider"] == "replicate")

    print("=" * 80)
    print("PARALLEL COLLECTION SUMMARY")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"  Total tasks:     {total}")
    print(f"  ✓ Successful:    {successful} ({successful/total*100:.1f}%)")
    print(f"  ✗ Failed:        {failed}")
    print(f"  ⏱ Timeout:        {timeout}")
    print(f"  ⚠ Errors:         {errors}")
    print(f"\n⚡ Performance:")
    print(f"  Average time:    {avg_time:.1f}s per task")
    print(f"  Total wall time: {sum(r['elapsed'] for r in results):.1f}s")
    print(f"\n🔌 Provider Distribution:")
    print(f"  Tongyi:          {tongyi_count} tasks")
    print(f"  Replicate:       {replicate_count} tasks")
    print()


def main():
    parser = argparse.ArgumentParser(description="Parallel data collection for model training")
    parser.add_argument("--tasks", type=int, help="Number of tasks to execute")
    parser.add_argument("--random", action="store_true", help="Select random tasks")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of parallel tasks per batch")
    parser.add_argument("--tongyi-ratio", type=float, default=0.5, help="Proportion of tasks for Tongyi (0.0-1.0)")

    args = parser.parse_args()

    if not args.tasks:
        print("Error: --tasks required")
        return 1

    # Extract tasks
    print(f"📝 Extracting {args.tasks} tasks...")
    tasks = extract_tasks(args.tasks, random=args.random)
    print(f"✓ Extracted {len(tasks)} tasks\n")

    # Run parallel collection
    results = run_parallel_batch(
        tasks,
        batch_size=args.batch_size,
        tongyi_ratio=args.tongyi_ratio
    )

    # Print summary
    print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
