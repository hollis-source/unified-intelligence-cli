#!/usr/bin/env python3
"""Build RAG Pattern Database - Automated Task Execution Framework.

This script automates the execution of tasks to build the RAG pattern database.
It follows ATADO's philosophy of autonomous, task-centric execution.

Usage:
    python scripts/build_rag_patterns.py --target 50 --parallel 5
    python scripts/build_rag_patterns.py --domain frontend --count 20
    python scripts/build_rag_patterns.py --dry-run
"""

import asyncio
import argparse
import sys
import os
import yaml
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TaskTemplate:
    """Represents a task template from YAML file."""
    
    def __init__(self, file_path: Path, data: Dict[str, Any]):
        """Initialize task template.
        
        Args:
            file_path: Path to YAML file
            data: Parsed YAML data
        """
        self.file_path = file_path
        self.id = data.get('id', file_path.stem)
        self.agent = data.get('agent', 'unknown')
        self.prompt = data.get('prompt', '')
        self.checks = data.get('checks', [])
        self.metadata = data.get('metadata', {})
        self.domain = self._infer_domain()
    
    def _infer_domain(self) -> str:
        """Infer domain from file path or metadata."""
        # From file path
        if 'qa' in str(self.file_path):
            return 'qa'
        elif 'test' in str(self.file_path):
            return 'testing'
        elif 'devops' in str(self.file_path):
            return 'devops'
        elif 'database' in str(self.file_path):
            return 'backend'
        elif 'python' in str(self.file_path):
            return 'backend'
        elif 'architect' in str(self.file_path):
            return 'architecture'
        
        # From metadata tags
        tags = self.metadata.get('tags', [])
        if 'frontend' in tags or 'react' in tags or 'ui' in tags:
            return 'frontend'
        elif 'backend' in tags or 'api' in tags or 'database' in tags:
            return 'backend'
        elif 'qa' in tags or 'acceptance' in tags:
            return 'qa'
        elif 'test' in tags or 'testing' in tags:
            return 'testing'
        elif 'devops' in tags or 'ci' in tags or 'deployment' in tags:
            return 'devops'
        
        return 'unknown'
    
    def to_command(self, provider: str = 'qwen3') -> List[str]:
        """Convert to command line arguments.

        Args:
            provider: LLM provider to use (default: qwen3 for 47-95x speedup)
        """
        return [
            'python', '-m', 'src.main',
            '--task', self.prompt.strip(),
            '--provider', provider,
            '--enable-rag',
            '--agents', 'scaled',
            '--routing', 'team',
            '--verbose'
        ]


class PatternCollector:
    """Collects patterns by executing tasks."""

    def __init__(
        self,
        tasks_dir: Path,
        target_count: int = 50,
        parallel: int = 1,
        dry_run: bool = False,
        provider: str = 'qwen3'
    ):
        """Initialize pattern collector.

        Args:
            tasks_dir: Directory containing task YAML files
            target_count: Target number of patterns to collect
            parallel: Number of parallel executions
            dry_run: If True, don't actually execute tasks
            provider: LLM provider to use (default: qwen3 for 47-95x speedup)
        """
        self.tasks_dir = tasks_dir
        self.target_count = target_count
        self.parallel = parallel
        self.dry_run = dry_run
        self.provider = provider
        self.results: List[Dict[str, Any]] = []
    
    def load_tasks(self, domain: Optional[str] = None) -> List[TaskTemplate]:
        """Load task templates from YAML files.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of task templates
        """
        tasks = []
        
        for yaml_file in self.tasks_dir.rglob('*.yaml'):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                    task = TaskTemplate(yaml_file, data)
                    
                    # Filter by domain if specified
                    if domain is None or task.domain == domain:
                        tasks.append(task)
            
            except Exception as e:
                print(f"⚠️  Failed to load {yaml_file}: {e}")
        
        return tasks
    
    def select_balanced_tasks(
        self,
        tasks: List[TaskTemplate],
        count: int
    ) -> List[TaskTemplate]:
        """Select balanced set of tasks across domains.
        
        Args:
            tasks: Available tasks
            count: Number of tasks to select
            
        Returns:
            Balanced list of tasks
        """
        # Group by domain
        by_domain: Dict[str, List[TaskTemplate]] = {}
        for task in tasks:
            if task.domain not in by_domain:
                by_domain[task.domain] = []
            by_domain[task.domain].append(task)
        
        # Calculate per-domain allocation
        num_domains = len(by_domain)
        per_domain = count // num_domains
        remainder = count % num_domains
        
        selected = []
        for i, (domain, domain_tasks) in enumerate(sorted(by_domain.items())):
            # Add extra task to first domains for remainder
            domain_count = per_domain + (1 if i < remainder else 0)
            domain_count = min(domain_count, len(domain_tasks))
            
            selected.extend(domain_tasks[:domain_count])
        
        return selected[:count]
    
    async def execute_task(
        self,
        task: TaskTemplate,
        index: int,
        total: int
    ) -> Dict[str, Any]:
        """Execute a single task.
        
        Args:
            task: Task template to execute
            index: Task index (1-based)
            total: Total number of tasks
            
        Returns:
            Execution result
        """
        print(f"\n{'='*80}")
        print(f"[{index}/{total}] Executing: {task.id} (domain: {task.domain})")
        print(f"{'='*80}")
        
        if self.dry_run:
            print("🔍 DRY RUN - Would execute:")
            print(f"   Command: {' '.join(task.to_command(self.provider))}")
            return {
                'task_id': task.id,
                'domain': task.domain,
                'status': 'dry_run',
                'timestamp': datetime.now().isoformat()
            }

        start_time = time.time()

        try:
            # Execute task
            result = subprocess.run(
                task.to_command(self.provider),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            elapsed = time.time() - start_time
            success = result.returncode == 0
            
            print(f"\n{'✅' if success else '❌'} Task {task.id}: "
                  f"{'SUCCESS' if success else 'FAILED'} ({elapsed:.1f}s)")
            
            if not success:
                print(f"   Error: {result.stderr[:200]}")
            
            return {
                'task_id': task.id,
                'domain': task.domain,
                'status': 'success' if success else 'failed',
                'elapsed': elapsed,
                'timestamp': datetime.now().isoformat(),
                'returncode': result.returncode
            }
        
        except subprocess.TimeoutExpired:
            print(f"⏱️  Task {task.id}: TIMEOUT (> 5 minutes)")
            return {
                'task_id': task.id,
                'domain': task.domain,
                'status': 'timeout',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ Task {task.id}: ERROR - {e}")
            return {
                'task_id': task.id,
                'domain': task.domain,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def execute_batch(
        self,
        tasks: List[TaskTemplate]
    ) -> List[Dict[str, Any]]:
        """Execute tasks in batches.
        
        Args:
            tasks: Tasks to execute
            
        Returns:
            List of execution results
        """
        results = []
        total = len(tasks)
        
        # Execute in batches
        for i in range(0, total, self.parallel):
            batch = tasks[i:i + self.parallel]
            batch_results = []
            
            for j, task in enumerate(batch):
                result = await self.execute_task(task, i + j + 1, total)
                batch_results.append(result)
                results.append(result)
            
            # Small delay between batches
            if i + self.parallel < total:
                await asyncio.sleep(2)
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print execution summary.
        
        Args:
            results: Execution results
        """
        print(f"\n{'='*80}")
        print("EXECUTION SUMMARY")
        print(f"{'='*80}\n")
        
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'failed')
        timeout = sum(1 for r in results if r['status'] == 'timeout')
        error = sum(1 for r in results if r['status'] == 'error')
        
        print(f"Total tasks: {total}")
        print(f"✅ Success: {success} ({success/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"⏱️  Timeout: {timeout} ({timeout/total*100:.1f}%)")
        print(f"🔥 Error: {error} ({error/total*100:.1f}%)")
        
        # By domain
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for result in results:
            domain = result['domain']
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(result)
        
        print(f"\nBy Domain:")
        for domain, domain_results in sorted(by_domain.items()):
            domain_success = sum(1 for r in domain_results if r['status'] == 'success')
            print(f"  {domain}: {domain_success}/{len(domain_results)} success")
        
        # Save results
        results_file = Path('logs/pattern_collection_results.json')
        results_file.parent.mkdir(exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Results saved to: {results_file}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build RAG pattern database through automated task execution'
    )
    parser.add_argument(
        '--target',
        type=int,
        default=50,
        help='Target number of patterns to collect (default: 50)'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=1,
        help='Number of parallel executions (default: 1)'
    )
    parser.add_argument(
        '--domain',
        type=str,
        help='Filter by domain (frontend, backend, qa, testing, devops, etc.)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - show what would be executed without actually running'
    )
    parser.add_argument(
        '--provider',
        type=str,
        default='qwen3',
        choices=['qwen3', 'granite'],
        help='LLM provider to use (default: qwen3 for 47-95x speedup, fallback: granite)'
    )

    args = parser.parse_args()

    # Setup
    tasks_dir = Path(__file__).parent.parent / 'tasks'

    print(f"{'='*80}")
    print("RAG PATTERN DATABASE BUILDER")
    print(f"{'='*80}\n")
    print(f"Tasks directory: {tasks_dir}")
    print(f"Target patterns: {args.target}")
    print(f"Parallel execution: {args.parallel}")
    print(f"Domain filter: {args.domain or 'all'}")
    print(f"Provider: {args.provider}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Load and select tasks
    collector = PatternCollector(
        tasks_dir=tasks_dir,
        target_count=args.target,
        parallel=args.parallel,
        dry_run=args.dry_run,
        provider=args.provider
    )
    
    print("Loading tasks...")
    all_tasks = collector.load_tasks(domain=args.domain)
    print(f"✅ Loaded {len(all_tasks)} tasks")
    
    print("Selecting balanced task set...")
    selected_tasks = collector.select_balanced_tasks(all_tasks, args.target)
    print(f"✅ Selected {len(selected_tasks)} tasks")
    
    # Execute
    print(f"\nStarting execution...")
    results = await collector.execute_batch(selected_tasks)
    
    # Summary
    collector.print_summary(results)


if __name__ == '__main__':
    asyncio.run(main())

