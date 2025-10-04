#!/usr/bin/env python3
"""Migration script for Phase 1 hierarchical priority system.

Migrates existing Redis tasks to include parent priority tracking.
Creates default priority 'autonomous-container' for orphaned tasks.

Run after Phase 1 implementation to update Redis data model.

Usage:
    python3 scripts/migrate_phase1_hierarchy.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.priority_queue.adapters.redis_adapter import RedisAdapter
from src.priority_queue.entities import Priority


def main():
    """Migrate existing tasks to Phase 1 hierarchical model."""

    print("=" * 70)
    print("Phase 1 Hierarchical Priority System Migration")
    print("=" * 70)
    print()

    # Initialize Redis adapter (use env vars if in container, else localhost)
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', '6379'))
    redis_db = int(os.environ.get('REDIS_DB', '0'))
    redis_config = {
        'host': redis_host,
        'port': redis_port,
        'db': redis_db,
        'lock_ttl': 3600,  # 1 hour
        'worker_id': 'migration-script'
    }

    adapter = RedisAdapter(redis_config)
    print(f"✅ Connected to Redis ({redis_host}:{redis_port})")

    # Step 1: Create default priority for existing tasks
    default_priority = Priority(
        id='autonomous-container',
        title='Autonomous Container Deployment',
        context='Deploy PriorityWorker in Docker for autonomous parallel work with 3-5x throughput improvement',
        status='active'
    )

    print(f"\n📋 Creating default priority: {default_priority.id}")
    print(f"   Title: {default_priority.title}")
    print(f"   Context hash: {default_priority.context_hash[:16]}...")

    created = adapter.create_priority(default_priority)
    if created:
        print("   ✅ Priority created")
    else:
        print("   ⚠️  Priority already exists (skipping)")

    # Step 2: Get all existing tasks from Redis
    print("\n📋 Scanning for existing tasks in Redis...")

    # Known task IDs from previous submission
    known_task_ids = [
        'implement-redis-deduplication',
        'multi-worker-scaling-test',
        'quality-gates-autonomous',
        'monitoring-alerts-integration'
    ]

    migrated = 0
    skipped = 0

    for task_id in known_task_ids:
        status_key = f"task_status:{task_id}"
        task_data = adapter.client.hgetall(status_key)

        if not task_data:
            print(f"   ⚠️  Task {task_id} not found in Redis (may have been processed)")
            skipped += 1
            continue

        # Check if already has parent fields
        if task_data.get('parent_priority_id'):
            print(f"   ⚠️  Task {task_id} already migrated (parent_priority_id exists)")
            skipped += 1
            continue

        # Add parent tracking fields
        print(f"   🔄 Migrating task: {task_id}")
        adapter.client.hset(status_key, mapping={
            'parent_priority_id': default_priority.id,
            'parent_context_hash': default_priority.context_hash,
            'is_stale': 'False',  # Redis stores as string
            'spawned_by': 'user',
            'description': task_data.get('description', '')
        })

        # Link task to priority (parent-child index)
        adapter.link_task_to_priority(task_id, default_priority.id)

        migrated += 1
        print(f"      ✅ Linked to priority: {default_priority.id}")

    # Step 3: Summary
    print("\n" + "=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Tasks migrated: {migrated}")
    print(f"Tasks skipped: {skipped}")
    print(f"Default priority: {default_priority.id}")

    # Verify parent-child links
    children = adapter.get_priority_children(default_priority.id)
    print(f"\nChildren linked to '{default_priority.id}': {len(children)}")
    for child_id in children:
        print(f"  - {child_id}")

    print("\n✅ Phase 1 migration complete!")
    print("\nNext steps:")
    print("  1. Verify tasks with: redis-cli HGETALL task_status:<task_id>")
    print("  2. Check priority: redis-cli HGETALL priority:autonomous-container")
    print("  3. List children: redis-cli SMEMBERS priority_children:autonomous-container")
    print("  4. Restart priority-worker container to process updated tasks")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
