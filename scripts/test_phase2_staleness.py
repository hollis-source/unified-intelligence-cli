#!/usr/bin/env python3
"""Test Phase 2 hierarchical priority system - staleness detection.

Tests that tasks are automatically marked stale when parent priority
context changes, and that stale tasks are filtered from worker polling.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.priority_queue.adapters.redis_adapter import RedisAdapter
from src.priority_queue.entities import Priority

def main():
    """Test Phase 2 staleness detection on priority context change."""

    print("=" * 70)
    print("Phase 2 Test: Staleness Detection on Context Change")
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
        'lock_ttl': 3600,
        'worker_id': 'test-phase2'
    }

    adapter = RedisAdapter(redis_config)
    print(f"✅ Connected to Redis ({redis_host}:{redis_port})")
    print()

    # Step 1: Create a test priority with initial context
    priority_id = 'test-priority-staleness'
    initial_priority = Priority(
        id=priority_id,
        title='Test Priority for Staleness Detection',
        context='Initial context - focus on Docker deployment',
        status='active'
    )

    # Clean up if exists
    adapter.delete_priority(priority_id)

    created = adapter.create_priority(initial_priority)
    if created:
        print(f"✅ Created priority: {priority_id}")
        print(f"   Initial context hash: {initial_priority.context_hash[:16]}...")
    else:
        print(f"❌ Failed to create priority")
        sys.exit(1)
    print()

    # Step 2: Submit tasks linked to this priority
    task1_id = 'test-task-staleness-1'
    task2_id = 'test-task-staleness-2'

    success1 = adapter.submit_task(
        task_id=task1_id,
        priority=1,
        description='Test task 1 - should become stale',
        metadata={'test': True, 'phase': 2},
        parent_priority_id=priority_id,
        spawned_by='test'
    )

    success2 = adapter.submit_task(
        task_id=task2_id,
        priority=2,
        description='Test task 2 - should become stale',
        metadata={'test': True, 'phase': 2},
        parent_priority_id=priority_id,
        spawned_by='test'
    )

    if success1 and success2:
        print(f"✅ Submitted 2 tasks linked to priority")
        print(f"   - {task1_id}")
        print(f"   - {task2_id}")
    else:
        print(f"❌ Failed to submit tasks")
        sys.exit(1)
    print()

    # Step 3: Verify tasks are initially NOT stale
    tasks_before = adapter.poll_tasks(status='open', limit=10, include_stale=False)
    task_ids_before = [t['id'] for t in tasks_before]

    print(f"📋 Before context change - polled {len(tasks_before)} non-stale open tasks:")
    for task in tasks_before:
        if task['id'] in [task1_id, task2_id]:
            print(f"   - {task['id']}: is_stale={task['is_stale']}, status={task['status']}")

    assert task1_id in task_ids_before, "Task 1 should be in non-stale poll"
    assert task2_id in task_ids_before, "Task 2 should be in non-stale poll"
    print()

    # Step 4: Update priority context (should trigger staleness)
    updated_priority = Priority(
        id=priority_id,
        title='Test Priority for Staleness Detection',
        context='UPDATED context - pivot to systemd deployment instead',  # CHANGED
        status='active'
    )

    print(f"🔄 Updating priority context...")
    print(f"   Old hash: {initial_priority.context_hash[:16]}...")
    print(f"   New hash: {updated_priority.context_hash[:16]}...")

    updated = adapter.update_priority(updated_priority)
    if updated:
        print(f"✅ Priority context updated")
    else:
        print(f"❌ Failed to update priority")
        sys.exit(1)
    print()

    # Step 5: Verify tasks are marked stale in Redis
    task1_data = adapter.client.hgetall(f"task_status:{task1_id}")
    task2_data = adapter.client.hgetall(f"task_status:{task2_id}")

    print(f"📋 Task status after context change:")
    print(f"   Task 1: is_stale={task1_data.get('is_stale')}, status={task1_data.get('status')}")
    print(f"   Task 2: is_stale={task2_data.get('is_stale')}, status={task2_data.get('status')}")
    print()

    # Step 6: Verify stale tasks are filtered from poll
    tasks_after = adapter.poll_tasks(status='open', limit=10, include_stale=False)
    task_ids_after = [t['id'] for t in tasks_after]

    print(f"📋 After context change - polled {len(tasks_after)} non-stale open tasks")
    print(f"   (should NOT include {task1_id} or {task2_id})")
    print()

    # Step 7: Verify stale tasks ARE included when requested
    tasks_with_stale = adapter.poll_tasks(status='stale', limit=10, include_stale=True)
    stale_task_ids = [t['id'] for t in tasks_with_stale]

    print(f"📋 Polling for stale tasks (include_stale=True):")
    print(f"   Found {len(tasks_with_stale)} stale tasks")
    for task in tasks_with_stale:
        if task['id'] in [task1_id, task2_id]:
            print(f"   - {task['id']}: is_stale={task['is_stale']}, status={task['status']}")
    print()

    # Assertions
    assert task1_data.get('is_stale') == 'true', "Task 1 should be marked stale"
    assert task2_data.get('is_stale') == 'true', "Task 2 should be marked stale"
    assert task1_data.get('status') == 'stale', "Task 1 status should be stale"
    assert task2_data.get('status') == 'stale', "Task 2 status should be stale"
    assert task1_id not in task_ids_after, "Task 1 should NOT be in non-stale poll"
    assert task2_id not in task_ids_after, "Task 2 should NOT be in non-stale poll"
    assert task1_id in stale_task_ids, "Task 1 should be in stale poll"
    assert task2_id in stale_task_ids, "Task 2 should be in stale poll"

    print("=" * 70)
    print("✅ Phase 2 Test PASSED - Staleness detection working!")
    print("=" * 70)
    print()
    print("Summary:")
    print("  1. ✅ Priority created with initial context")
    print("  2. ✅ Tasks submitted and linked to priority")
    print("  3. ✅ Tasks initially NOT stale, appear in poll")
    print("  4. ✅ Priority context updated (hash changed)")
    print("  5. ✅ Tasks automatically marked stale")
    print("  6. ✅ Stale tasks filtered from default poll")
    print("  7. ✅ Stale tasks visible when include_stale=True")
    print()
    print("Next steps:")
    print("  - Worker will skip stale tasks during normal polling")
    print("  - Phase 3: ULTRATHINK auto-tagging with spawned_by")

if __name__ == '__main__':
    main()
