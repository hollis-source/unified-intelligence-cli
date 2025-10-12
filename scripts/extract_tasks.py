#!/usr/bin/env python3
"""
Extract tasks from DATA_COLLECTION_TASKS_293.md for execution.

Usage:
    python3 scripts/extract_tasks.py                    # List all tasks
    python3 scripts/extract_tasks.py --random 10        # Get 10 random tasks
    python3 scripts/extract_tasks.py --category 1       # Get Category 1 tasks
    python3 scripts/extract_tasks.py --agent coder      # Get coder-targeted tasks
    python3 scripts/extract_tasks.py --range 1-50       # Get tasks 1-50
"""

import re
import random
import argparse
from pathlib import Path
from typing import List, Dict


def extract_tasks_from_md(md_file: str) -> List[Dict[str, str]]:
    """
    Extract all numbered tasks from markdown file.

    Returns:
        List of dicts with 'number', 'text', 'category' keys
    """
    tasks = []
    current_category = ""
    current_subcategory = ""

    with open(md_file, 'r') as f:
        for line in f:
            # Track category
            if line.startswith("## Category"):
                current_category = line.strip().replace("## ", "")
            elif line.startswith("###"):
                current_subcategory = line.strip().replace("### ", "").replace(" (8 tasks)", "").replace(" (7 tasks)", "").replace(" (6 tasks)", "").replace(" (4 tasks)", "")

            # Match numbered task lines: "123. Task description here"
            match = re.match(r'^(\d+)\.\s+(.+)$', line.strip())
            if match:
                task_num = int(match.group(1))
                task_text = match.group(2)

                tasks.append({
                    'number': task_num,
                    'text': task_text,
                    'category': current_category,
                    'subcategory': current_subcategory
                })

    return tasks


def infer_agent_from_task(task_text: str) -> str:
    """
    Infer likely agent based on task keywords.

    Returns:
        Agent role (coder, tester, researcher, coordinator, reviewer)
    """
    text_lower = task_text.lower()

    # Keyword matching
    if any(kw in text_lower for kw in ['implement', 'create', 'write', 'build', 'develop', 'code', 'refactor', 'fix']):
        return 'coder'
    elif any(kw in text_lower for kw in ['test', 'verify', 'validate', 'check', 'coverage', 'qa']):
        return 'tester'
    elif any(kw in text_lower for kw in ['research', 'analyze', 'investigate', 'study', 'explore', 'document']):
        return 'researcher'
    elif any(kw in text_lower for kw in ['plan', 'coordinate', 'organize', 'manage', 'prioritize', 'estimate']):
        return 'coordinator'
    elif any(kw in text_lower for kw in ['review', 'evaluate', 'assess', 'inspect', 'critique']):
        return 'reviewer'
    else:
        # Default based on first verb
        if any(kw in text_lower for kw in ['design']):
            return 'coder'
        return 'researcher'


def main():
    parser = argparse.ArgumentParser(description='Extract tasks from DATA_COLLECTION_TASKS_293.md')
    parser.add_argument('--random', type=int, metavar='N', help='Get N random tasks')
    parser.add_argument('--category', type=int, metavar='NUM', help='Get tasks from category NUM (1-9)')
    parser.add_argument('--agent', choices=['coder', 'tester', 'researcher', 'coordinator', 'reviewer'], help='Filter by agent type')
    parser.add_argument('--range', metavar='START-END', help='Get tasks in range (e.g., 1-50)')
    parser.add_argument('--output', choices=['text', 'bash', 'markdown'], default='text', help='Output format')
    parser.add_argument('--count', action='store_true', help='Just count tasks')

    args = parser.parse_args()

    # Load tasks
    md_file = Path(__file__).parent.parent / 'docs' / 'DATA_COLLECTION_TASKS_293.md'
    if not md_file.exists():
        print(f"Error: {md_file} not found")
        return 1

    all_tasks = extract_tasks_from_md(str(md_file))

    if args.count:
        print(f"Total tasks: {len(all_tasks)}")
        return 0

    # Filter tasks
    filtered_tasks = all_tasks

    if args.category:
        filtered_tasks = [t for t in filtered_tasks if f"Category {args.category}:" in t['category']]

    if args.agent:
        filtered_tasks = [t for t in filtered_tasks if infer_agent_from_task(t['text']) == args.agent]

    if args.range:
        start, end = map(int, args.range.split('-'))
        filtered_tasks = [t for t in filtered_tasks if start <= t['number'] <= end]

    if args.random:
        filtered_tasks = random.sample(filtered_tasks, min(args.random, len(filtered_tasks)))
        # Sort by number for readability
        filtered_tasks.sort(key=lambda x: x['number'])

    # Output
    if args.output == 'text':
        for task in filtered_tasks:
            print(f"{task['number']}. {task['text']}")
    elif args.output == 'markdown':
        print("# Selected Tasks\n")
        for task in filtered_tasks:
            print(f"{task['number']}. **{task['subcategory']}**: {task['text']}")
    elif args.output == 'bash':
        print("#!/bin/bash")
        print("# Run selected tasks with data collection")
        print()
        for task in filtered_tasks:
            print(f"# Task {task['number']}: {task['subcategory']}")
            print(f'python3 src/main.py --task "{task["text"]}" --provider tongyi --collect-data --verbose')
            print()

    return 0


if __name__ == '__main__':
    exit(main())
