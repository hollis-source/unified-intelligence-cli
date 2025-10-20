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
        path_str = str(self.file_path).lower()
        if 'qa' in path_str:
            return 'qa'
        elif 'test' in path_str:
            return 'testing'
        elif 'devops' in path_str:
            return 'devops'
        elif 'database' in path_str or 'python' in path_str:
            return 'backend'
        elif 'architect' in path_str:
            return 'architecture'
        elif 'frontend' in path_str:
            return 'frontend'
        elif 'research' in path_str:
            return 'research'

        # From metadata tags
        tags = [str(t).lower() for t in self.metadata.get('tags', [])]
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
        elif 'research' in tags or 'adr' in tags or 'benchmarking' in tags:
            return 'research'
        elif 'architecture' in tags:
            return 'architecture'

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
        parallel: int = 6,
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
    
    async def _get_db_domain_counts(self) -> Dict[str, int]:
        """Try to read existing pattern counts by domain from SurrealDB.
        Returns {} on failure.
        """
        try:
            from src.adapters.llm.rag_config import RAGConfig  # type: ignore
            from src.adapters.rag.surrealdb_store import SurrealDBStore  # type: ignore
            import os, asyncio
            cfg = RAGConfig()
            store = SurrealDBStore(
                url=os.getenv("SURREALDB_URL", "ws://localhost:8000"),
                namespace=cfg.db_namespace,
                database=cfg.db_database,
                user=cfg.db_user,
                password=cfg.db_password,
            )
            async def _go():
                try:
                    await store.connect()
                except Exception:
                    return {}
                rows = await store.query("SELECT task_domain, count() as count FROM execution_log GROUP BY task_domain;")
                out: Dict[str, int] = {}
                for r in rows or []:
                    d = r.get("task_domain") or "unknown"
                    out[d] = int(r.get("count", 0))
                return out
            try:
                return await _go()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(_go())
                finally:
                    loop.close()
        except Exception:
            return {}

    def _allocate_by_underrepresentation(self, by_domain: Dict[str, List[TaskTemplate]], target_count: int, domain_counts: Dict[str, int]) -> Dict[str, int]:
        """Compute allocation per domain, prioritizing under-represented domains.
        Rule: prefer domains below 0.8×mean; de-emphasize above 1.2×mean.
        Fallback to even if counts empty.
        """
        domains = list(by_domain.keys())
        if not domains:
            return {}
        if not domain_counts:
            # Even allocation
            base = target_count // len(domains)
            rem = target_count % len(domains)
            alloc = {d: base for d in domains}
            for d in sorted(domains)[:rem]:
                alloc[d] += 1
            # cap to availability
            for d in domains:
                alloc[d] = min(alloc[d], len(by_domain[d]))
            return alloc
        # Compute mean across present domains; default 0 if missing
        values = [domain_counts.get(d, 0) for d in domains]
        mean = (sum(values) / max(len(values), 1)) if values else 0.0
        low_thr = 0.8 * mean
        high_thr = 1.2 * mean
        # Score = how underrepresented: max(mean - count, 0) + 1e-6 to avoid 0
        scores: Dict[str, float] = {}
        for d in domains:
            c = float(domain_counts.get(d, 0))
            # Emphasize below low threshold; dampen above high
            if c < low_thr:
                s = (mean - c) + 1.0
            elif c > high_thr:
                s = max(0.2, 0.5 * (mean / (c + 1e-6)))
            else:
                s = 1.0
            # availability cap weight
            if len(by_domain[d]) == 0:
                s = 0.0
            scores[d] = max(0.0, s)
        total_score = sum(scores.values()) or 1.0
        alloc: Dict[str, int] = {}
        # Initial fractional allocation
        fracs: Dict[str, float] = {d: (scores[d] / total_score) * target_count for d in domains}
        # Round down first
        used = 0
        for d in domains:
            alloc[d] = min(int(fracs[d]), len(by_domain[d]))
            used += alloc[d]
        # Distribute remainder by largest fractional parts
        remainder = target_count - used
        order = sorted(domains, key=lambda d: (fracs[d] - int(fracs[d])), reverse=True)
        for d in order:
            if remainder <= 0:
                break
            if alloc[d] < len(by_domain[d]):
                alloc[d] += 1
                remainder -= 1
        return alloc

    async def select_balanced_tasks(
        self,
        tasks: List[TaskTemplate],
        count: int,
        balance_source: str = "db"
    ) -> List[TaskTemplate]:
        """Select balanced set of tasks across domains.
        If balance_source == 'db', uses SurrealDB domain counts to favor under-represented domains;
        otherwise uses even allocation. Caps domains within availability and aims to reduce skew towards over-represented ones.
        """
        # Group by domain
        by_domain: Dict[str, List[TaskTemplate]] = {}
        for task in tasks:
            by_domain.setdefault(task.domain, []).append(task)
        if not by_domain:
            print("\u26a0\ufe0f No tasks available for the selected domain(s).")
            return []
        domain_counts: Dict[str, int] = {}
        if balance_source == "db":
            try:
                domain_counts = await self._get_db_domain_counts()
            except Exception:
                domain_counts = {}
        alloc = self._allocate_by_underrepresentation(by_domain, count, domain_counts)
        # Build selection deterministically per domain
        selected: List[TaskTemplate] = []
        for d in sorted(by_domain.keys()):
            n = max(0, min(alloc.get(d, 0), len(by_domain[d])))
            selected.extend(by_domain[d][:n])
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
        default=6,
        help='Number of parallel executions (default: 6)'
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
    parser.add_argument(
        '--balance-source',
        type=str,
        default='db',
        choices=['db', 'even'],
        help="Balance selection using 'db' (SurrealDB domain counts) or 'even' allocation"
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
    print(f"Balance source: {args.balance_source}")
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
    selected_tasks = await collector.select_balanced_tasks(all_tasks, args.target, args.balance_source)
    print(f"✅ Selected {len(selected_tasks)} tasks")

    if not selected_tasks:
        print("Nothing to execute. Exiting.")
        return

    # Optional: advise generating drafts for underrepresented domains
    if args.balance_source == 'db':
        try:
            domain_counts = await collector._get_db_domain_counts()
            if domain_counts:
                mean = sum(domain_counts.values()) / max(len(domain_counts), 1)
                low_thr = 0.8 * mean
                low_domains = sorted([d for d,c in domain_counts.items() if c < low_thr])
                if low_domains:
                    print("\nTip: Some domains are under-represented:", ", ".join(low_domains))
                    print("You can pre-generate DRAFT templates: \n  python scripts/generate_missing_templates.py --min 5 --domains " + ",".join(low_domains))
        except Exception:
            pass

    # Execute
    print(f"\nStarting execution...")
    results = await collector.execute_batch(selected_tasks)

    # Summary
    collector.print_summary(results)


if __name__ == '__main__':
    asyncio.run(main())

