#!/usr/bin/env python3
"""
Create benchmark suite from 293 well-formed tasks.

Week 9 Phase 2: Extract tasks, categorize by agent, create test/eval splits.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
import random

# Agent type classification rules
AGENT_RULES = {
    "coder": [
        "implement", "create", "design", "refactor", "extract", "write code",
        "code", "function", "class", "entity", "adapter", "interface",
        "factory", "builder", "pattern"
    ],
    "tester": [
        "test", "testing", "pytest", "unit test", "integration test",
        "mock", "coverage", "TDD", "test-driven", "assertion", "fixture"
    ],
    "reviewer": [
        "review", "audit", "security", "performance", "quality",
        "SOLID", "clean code", "code smell", "violation", "compliance"
    ],
    "researcher": [
        "research", "analyze", "investigate", "compare", "evaluate",
        "benchmark", "measure", "calculate", "study", "document best practices"
    ],
    "coordinator": [
        "plan", "coordinate", "organize", "manage", "decompose",
        "break down", "prioritize", "roadmap", "sprint", "workflow"
    ]
}


def classify_agent(task: str) -> str:
    """
    Classify which agent should handle this task.

    Returns agent type or 'coder' as default.
    """
    task_lower = task.lower()

    # Score each agent type
    scores = {agent: 0 for agent in AGENT_RULES}

    for agent, keywords in AGENT_RULES.items():
        for keyword in keywords:
            if keyword in task_lower:
                scores[agent] += 1

    # Return highest scoring agent (ties go to coder)
    max_score = max(scores.values())
    if max_score == 0:
        return "coder"  # Default

    # Get agent with highest score
    for agent, score in scores.items():
        if score == max_score:
            return agent

    return "coder"


def extract_tasks_from_markdown(md_file: Path) -> List[Tuple[int, str, str]]:
    """
    Extract numbered tasks from markdown file.

    Returns: List of (task_id, task_description, category)
    """
    tasks = []
    current_category = "Unknown"

    with open(md_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Track category headers
            if line.startswith("## Category"):
                current_category = line.split(":", 1)[0].replace("## Category", "").strip()

            # Match numbered tasks: "123. Task description"
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                task_id = int(match.group(1))
                task_desc = match.group(2).strip()
                tasks.append((task_id, task_desc, current_category))

    return tasks


def create_benchmark_files(tasks: List[Tuple[int, str, str]], output_dir: Path):
    """
    Split tasks by agent and create benchmark JSONL files.

    Creates:
    - benchmarks/{agent}/benchmark_all.jsonl
    - benchmarks/{agent}/benchmark_eval.jsonl (20% held out for evaluation)
    """
    # Categorize by agent
    agent_tasks: Dict[str, List[Dict]] = {
        "coder": [],
        "tester": [],
        "reviewer": [],
        "researcher": [],
        "coordinator": []
    }

    for task_id, task_desc, category in tasks:
        agent = classify_agent(task_desc)

        agent_tasks[agent].append({
            "task_id": task_id,
            "description": task_desc,
            "category": category,
            "agent": agent
        })

    # Save benchmark files for each agent
    for agent, agent_task_list in agent_tasks.items():
        agent_dir = output_dir / agent
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Shuffle for randomness
        random.shuffle(agent_task_list)

        # 80/20 split: all vs eval-only
        split_idx = int(len(agent_task_list) * 0.8)
        train_tasks = agent_task_list[:split_idx]
        eval_tasks = agent_task_list[split_idx:]

        # Save all tasks
        all_file = agent_dir / "benchmark_all.jsonl"
        with open(all_file, 'w') as f:
            for task in agent_task_list:
                f.write(json.dumps(task) + "\n")

        # Save eval-only subset (held out for final evaluation)
        eval_file = agent_dir / "benchmark_eval.jsonl"
        with open(eval_file, 'w') as f:
            for task in eval_tasks:
                f.write(json.dumps(task) + "\n")

        print(f"✓ {agent:12s}: {len(agent_task_list):3d} total, {len(eval_tasks):3d} eval-only")

    # Print summary
    total_tasks = sum(len(tasks) for tasks in agent_tasks.values())
    print(f"\n📊 Total: {total_tasks} tasks across {len(agent_tasks)} agents")

    return agent_tasks


def main():
    # Paths
    tasks_md = Path(__file__).parent.parent / "docs" / "DATA_COLLECTION_TASKS_293.md"
    benchmarks_dir = Path(__file__).parent.parent / "benchmarks"

    print("📝 Extracting tasks from markdown...")
    tasks = extract_tasks_from_markdown(tasks_md)
    print(f"✓ Extracted {len(tasks)} tasks\n")

    print("🔧 Creating benchmark files...")
    agent_tasks = create_benchmark_files(tasks, benchmarks_dir)

    print("\n✅ Benchmark suite created!")
    print(f"📁 Location: {benchmarks_dir}/")
    print("\nFiles created:")
    print("  - benchmarks/{agent}/benchmark_all.jsonl   (all tasks for that agent)")
    print("  - benchmarks/{agent}/benchmark_eval.jsonl  (20% eval subset)")


if __name__ == "__main__":
    random.seed(42)  # Reproducible splits
    main()
