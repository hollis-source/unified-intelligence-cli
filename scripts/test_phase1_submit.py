#!/usr/bin/env python3
"""Test Phase 1 hierarchical priority system - task submission with parent tracking."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.priority_queue.adapters.redis_adapter import RedisAdapter

def main():
    """Test Phase 1 task submission with parent priority tracking."""

    print("=" * 70)
    print("Phase 1 Test: Task Submission with Parent Tracking")
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
        'worker_id': 'test-phase1'
    }

    adapter = RedisAdapter(redis_config)
    print(f"✅ Connected to Redis ({redis_host}:{redis_port})")

    # Step 1: Verify default priority exists
    priority_id = 'autonomous-container'
    priority = adapter.get_priority(priority_id)

    if not priority:
        print(f"❌ Priority '{priority_id}' not found - run migration first")
        sys.exit(1)

    print(f"✅ Found priority: {priority.title}")
    print(f"   Context hash: {priority.context_hash[:16]}...")
    print()

    # Step 2: Submit test task with parent tracking
    test_task_id = 'test-phase1-hierarchical'
    success = adapter.submit_task(
        task_id=test_task_id,
        priority=1,
        description='Test Phase 1 hierarchical priority system task submission',
        metadata={
            'test': True,
            'phase': 1,
            'feature': 'hierarchical-priorities'
        },
        parent_priority_id=priority_id,
        spawned_by='test'
    )

    if success:
        print(f"✅ Task submitted: {test_task_id}")
    else:
        print(f"⚠️  Task may be duplicate (already exists)")
    print()

    # Step 3: Verify task has correct parent tracking
    task_status_key = f"task_status:{test_task_id}"
    task_data = adapter.client.hgetall(task_status_key)

    if not task_data:
        print(f"❌ Task data not found in Redis")
        sys.exit(1)

    print("📋 Task data verification:")
    print(f"   ID: {task_data.get('id', 'N/A')}")
    print(f"   Status: {task_data.get('status', 'N/A')}")
    print(f"   Parent Priority ID: {task_data.get('parent_priority_id', 'N/A')}")
    print(f"   Parent Context Hash: {task_data.get('parent_context_hash', 'N/A')[:16]}...")
    print(f"   Is Stale: {task_data.get('is_stale', 'N/A')}")
    print(f"   Spawned By: {task_data.get('spawned_by', 'N/A')}")
    print()

    # Step 4: Verify task appears in priority children
    children = adapter.get_priority_children(priority_id)
    print(f"📊 Priority children ({len(children)} total):")
    for child in children:
        print(f"   - {child}")
    print()

    # Validation
    assert task_data.get('parent_priority_id') == priority_id, "Parent priority ID mismatch"
    assert task_data.get('parent_context_hash') == priority.context_hash, "Context hash mismatch"
    assert task_data.get('is_stale') == 'false', "Task should not be stale"
    assert task_data.get('spawned_by') == 'test', "Spawned by should be 'test'"
    assert test_task_id in children, "Task should be in parent's children list"

    print("=" * 70)
    print("✅ Phase 1 Test PASSED - All validations successful!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Monitor worker processing: docker-compose logs -f priority-worker")
    print("  2. Test staleness detection (Phase 2)")
    print("  3. Test context change triggers staleness")

if __name__ == '__main__':
    main()
