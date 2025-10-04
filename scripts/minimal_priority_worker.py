#!/usr/bin/env python3
"""
Minimal Priority Worker Prototype
Demonstrates autonomous priority execution concept.

Usage:
    python scripts/minimal_priority_worker.py --once   # Execute one priority
    python scripts/minimal_priority_worker.py --loop   # Continuous loop
"""

import argparse
import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


class MinimalPriorityWorker:
    """
    Minimal autonomous priority worker.

    Demonstrates:
    - Loading priority queue from YAML
    - Atomic claiming via git commits
    - DSL workflow execution
    - Simple coordination without external dependencies
    """

    def __init__(self, priorities_file: str = "priorities.yaml"):
        self.priorities_file = Path(priorities_file)
        self.worker_id = "prototype-worker"
        self.repo_root = Path(__file__).parent.parent

    def load_priorities(self) -> dict:
        """Load priority queue from YAML file."""
        if not self.priorities_file.exists():
            raise FileNotFoundError(f"Priority file not found: {self.priorities_file}")

        with open(self.priorities_file) as f:
            return yaml.safe_load(f)

    def save_priorities(self, data: dict) -> None:
        """Save priority queue to YAML file."""
        with open(self.priorities_file, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def claim_priority(self) -> dict | None:
        """
        Try to claim next open priority atomically via git.

        Returns:
            Priority dict if claimed, None if no work available

        Algorithm:
            1. Pull latest
            2. Find first open priority
            3. Mark as claimed
            4. Try to commit + push (atomic)
            5. If push fails (race condition), retry
        """
        max_attempts = 3

        for attempt in range(max_attempts):
            print(f"🔍 Attempt {attempt + 1}/{max_attempts} to claim priority...")

            # Pull latest state
            try:
                subprocess.run(
                    ['git', 'pull', '--rebase'],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Git pull failed: {e.stderr.decode()}")
                continue

            # Load current priorities
            data = self.load_priorities()

            # Find first open priority (respecting dependencies)
            claimed_priority = None
            for priority in data['priorities']:
                if priority['status'] != 'open':
                    continue

                # Check dependencies
                if priority.get('dependencies'):
                    deps_complete = all(
                        any(p['id'] == dep_id and p['status'] == 'completed'
                            for p in data['priorities'])
                        for dep_id in priority['dependencies']
                    )
                    if not deps_complete:
                        continue

                # Try to claim this one
                priority['status'] = 'claimed'
                priority['claimed_by'] = self.worker_id
                priority['claimed_at'] = datetime.now().isoformat()

                claimed_priority = priority
                break

            if not claimed_priority:
                print("ℹ️  No available priorities (all claimed or have unmet dependencies)")
                return None

            # Save updated priorities
            self.save_priorities(data)

            # Try to commit (atomic operation)
            try:
                subprocess.run(
                    ['git', 'add', str(self.priorities_file)],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True
                )

                commit_msg = (
                    f"Claim priority: {claimed_priority['id']} by {self.worker_id}\n\n"
                    f"Priority: {claimed_priority['title']}\n"
                    f"Effort: {claimed_priority['effort_hours']}h\n"
                    f"Workflow: {claimed_priority.get('workflow', 'N/A')}"
                )

                subprocess.run(
                    ['git', 'commit', '-m', commit_msg],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True
                )

                # Try to push (this is the atomic test)
                subprocess.run(
                    ['git', 'push'],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True
                )

                # Success! We claimed it
                print(f"✅ Claimed: {claimed_priority['title']}")
                print(f"   ID: {claimed_priority['id']}")
                print(f"   Priority: {claimed_priority['priority']}")
                print(f"   Effort: {claimed_priority['effort_hours']}h")

                return claimed_priority

            except subprocess.CalledProcessError as e:
                # Race condition - someone else claimed first
                print(f"⚠️  Claim failed (race condition), retrying...")

                # Reset to previous state
                try:
                    subprocess.run(
                        ['git', 'reset', '--hard', 'HEAD~1'],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True
                    )
                except subprocess.CalledProcessError:
                    # If we didn't commit, just reset the file
                    subprocess.run(
                        ['git', 'restore', str(self.priorities_file)],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True
                    )

                # Wait a bit before retrying
                asyncio.sleep(1)
                continue

        print("❌ Failed to claim priority after max attempts")
        return None

    async def execute_workflow(self, workflow_path: str) -> dict:
        """
        Execute DSL workflow.

        Args:
            workflow_path: Path to .ct workflow file

        Returns:
            Dict with success, output, error
        """
        workflow_full_path = self.repo_root / workflow_path

        if not workflow_full_path.exists():
            return {
                'success': False,
                'output': '',
                'error': f"Workflow file not found: {workflow_path}"
            }

        print(f"🚀 Executing workflow: {workflow_path}")

        cmd = [
            'python',
            str(self.repo_root / 'src' / 'dsl' / 'cli_integration.py'),
            str(workflow_full_path)
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.repo_root
            )

            stdout, stderr = await proc.communicate()

            return {
                'success': proc.returncode == 0,
                'output': stdout.decode('utf-8'),
                'error': stderr.decode('utf-8') if proc.returncode != 0 else None
            }

        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }

    def update_priority_status(
        self,
        priority_id: str,
        status: str,
        **updates
    ) -> None:
        """
        Update priority status and other fields.

        Args:
            priority_id: Priority ID to update
            status: New status (in_progress, completed, failed)
            **updates: Additional fields to update
        """
        data = self.load_priorities()

        for priority in data['priorities']:
            if priority['id'] == priority_id:
                priority['status'] = status
                priority.update(updates)
                break

        # Update metadata
        data['metadata']['last_updated'] = datetime.now().isoformat()
        if status == 'completed':
            data['metadata']['completed'] = data['metadata'].get('completed', 0) + 1
        elif status == 'in_progress':
            data['metadata']['in_progress'] = data['metadata'].get('in_progress', 0) + 1

        self.save_priorities(data)

        # Commit update
        try:
            subprocess.run(
                ['git', 'add', str(self.priorities_file)],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            subprocess.run(
                ['git', 'commit', '-m', f"Update priority {priority_id}: {status}"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            subprocess.run(
                ['git', 'push'],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            print(f"✅ Updated priority status: {status}")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Status update commit failed: {e.stderr.decode()}")

    async def run_once(self) -> bool:
        """
        Execute one priority (for testing).

        Returns:
            True if work was done, False if no work available
        """
        print(f"\n{'='*60}")
        print(f"🤖 Minimal Priority Worker - Single Execution")
        print(f"   Worker ID: {self.worker_id}")
        print(f"   Time: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        # 1. Claim priority
        priority = self.claim_priority()
        if not priority:
            print("\n❌ No work available")
            return False

        # 2. Update to in_progress
        self.update_priority_status(
            priority['id'],
            'in_progress',
            started_at=datetime.now().isoformat()
        )

        # 3. Execute workflow (if specified)
        if priority.get('workflow'):
            print(f"\n📋 Workflow: {priority['workflow']}")

            result = await self.execute_workflow(priority['workflow'])

            if result['success']:
                print(f"\n✅ Workflow executed successfully!")
                print(f"\nOutput preview (first 500 chars):")
                print(result['output'][:500])

                # Update to completed
                self.update_priority_status(
                    priority['id'],
                    'completed',
                    completed_at=datetime.now().isoformat(),
                    success=True,
                    error=None
                )

            else:
                print(f"\n❌ Workflow failed!")
                print(f"Error: {result['error']}")

                # Update to failed
                self.update_priority_status(
                    priority['id'],
                    'failed',
                    completed_at=datetime.now().isoformat(),
                    success=False,
                    error=result['error']
                )

        else:
            # No workflow - just mark as completed (manual task)
            print(f"\n⚠️  No workflow specified - marking as completed")
            self.update_priority_status(
                priority['id'],
                'completed',
                completed_at=datetime.now().isoformat(),
                success=True,
                notes="Manual task - no automated workflow"
            )

        print(f"\n{'='*60}")
        print(f"🎉 Priority execution complete: {priority['id']}")
        print(f"{'='*60}\n")

        return True

    async def run_loop(self, check_interval: int = 60) -> None:
        """
        Continuous loop - keep executing priorities.

        Args:
            check_interval: Seconds to wait between checks
        """
        print(f"\n{'='*60}")
        print(f"🤖 Minimal Priority Worker - Continuous Mode")
        print(f"   Worker ID: {self.worker_id}")
        print(f"   Check interval: {check_interval}s")
        print(f"   Started: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")

        iterations = 0

        try:
            while True:
                iterations += 1
                print(f"\n--- Iteration {iterations} ---")

                worked = await self.run_once()

                if worked:
                    print(f"\n⏸️  Waiting {check_interval}s before next check...")
                else:
                    print(f"\n💤 No work available, waiting {check_interval}s...")

                await asyncio.sleep(check_interval)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user")
            print(f"   Total iterations: {iterations}")
            print(f"   Duration: {datetime.now().isoformat()}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Minimal Priority Worker - Autonomous Task Execution"
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Execute one priority and exit'
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Continuous loop (check every 60s)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval for loop mode (seconds)'
    )

    args = parser.parse_args()

    if not args.once and not args.loop:
        print("Error: Must specify either --once or --loop")
        parser.print_help()
        sys.exit(1)

    worker = MinimalPriorityWorker()

    try:
        if args.once:
            worked = await worker.run_once()
            sys.exit(0 if worked else 1)
        else:
            await worker.run_loop(args.interval)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
