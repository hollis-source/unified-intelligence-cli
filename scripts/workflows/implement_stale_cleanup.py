#!/usr/bin/env python3
"""
Workflow: Implement Stale Task Cleanup
Adds cleanup_stale_tasks() method to RedisAdapter for archiving stale tasks after TTL.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def implement_cleanup():
    """Add cleanup_stale_tasks() method to RedisAdapter."""

    adapter_file = project_root / 'src/priority_queue/adapters/redis_adapter.py'

    # Read current content
    with open(adapter_file, 'r') as f:
        content = f.read()

    # Check if already implemented
    if 'def cleanup_stale_tasks' in content:
        print("✅ cleanup_stale_tasks() already exists")
        return True

    # Find insertion point (after mark_children_stale method)
    cleanup_method = '''
    def cleanup_stale_tasks(self, max_age_hours: int = 24) -> int:
        """Archive stale tasks older than max_age_hours.

        Phase 2: Stale task cleanup and archival.

        Args:
            max_age_hours: Maximum age in hours before archiving (default: 24)

        Returns:
            Number of tasks archived
        """
        import time
        try:
            # Get all task IDs from queue
            all_task_keys = self.client.keys(f'{self.STATUS_PREFIX}*')

            archived_count = 0
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for task_key in all_task_keys:
                task_data = self.client.hgetall(task_key)

                # Only process stale tasks
                if task_data.get('status') != 'stale':
                    continue

                # Check if task has timestamp (added in Phase 2)
                timestamp = task_data.get('stale_timestamp')
                if not timestamp:
                    # No timestamp - mark with current time for future cleanup
                    self.client.hset(task_key, 'stale_timestamp', current_time)
                    continue

                # Check if past TTL
                age_seconds = current_time - float(timestamp)
                if age_seconds < max_age_seconds:
                    continue

                # Archive task
                task_id = task_data.get('id')
                archive_key = f'archived_task:{task_id}'

                # Copy to archive with timestamp
                archive_data = dict(task_data)
                archive_data['archived_at'] = current_time
                self.client.hset(archive_key, mapping=archive_data)

                # Delete from active storage
                self.client.delete(task_key)

                # Remove from queue if present
                self.client.lrem(self.QUEUE_KEY, 0, task_id)

                # Remove from parent children set
                parent_id = task_data.get('parent_priority_id')
                if parent_id:
                    children_key = f'{self.PRIORITY_CHILDREN_PREFIX}{parent_id}'
                    self.client.srem(children_key, task_id)

                archived_count += 1

            return archived_count

        except redis.RedisError as e:
            raise ValueError(f"Failed to cleanup stale tasks: {e}") from e
'''

    # Find the mark_children_stale method end
    insertion_point = content.find('    # Phase 1: Parent-child relationship tracking')

    if insertion_point == -1:
        print("❌ Could not find insertion point in RedisAdapter")
        return False

    # Insert the new method before the Phase 1 comment
    new_content = content[:insertion_point] + cleanup_method + '\n' + content[insertion_point:]

    # Write updated content
    with open(adapter_file, 'w') as f:
        f.write(new_content)

    print("✅ Added cleanup_stale_tasks() method to RedisAdapter")
    print(f"   Location: {adapter_file}")
    print(f"   Method: cleanup_stale_tasks(max_age_hours=24)")

    return True

if __name__ == '__main__':
    success = implement_cleanup()
    sys.exit(0 if success else 1)
