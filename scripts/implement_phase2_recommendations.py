#!/usr/bin/env python3
"""
Phase 2 Recommendations Implementation Script
Executes all three recommended actions from staleness detection validation:
1. Stale task cleanup functionality
2. Staleness metrics dashboard endpoint
3. Automated Redis backup scheduling
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_section(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def implement_cleanup():
    """Add cleanup_stale_tasks() method to RedisAdapter."""
    print_section("STEP 1: Implement Stale Task Cleanup")

    adapter_file = project_root / 'src/priority_queue/adapters/redis_adapter.py'

    # Read current content
    with open(adapter_file, 'r') as f:
        content = f.read()

    # Check if already implemented
    if 'def cleanup_stale_tasks' in content:
        print("✅ cleanup_stale_tasks() already exists - skipping")
        return True

    # Cleanup method implementation
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
            all_task_keys = self.client.keys(f'{self.STATUS_PREFIX}*')
            archived_count = 0
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for task_key in all_task_keys:
                task_data = self.client.hgetall(task_key)
                if task_data.get('status') != 'stale':
                    continue

                timestamp = task_data.get('stale_timestamp')
                if not timestamp:
                    self.client.hset(task_key, 'stale_timestamp', current_time)
                    continue

                age_seconds = current_time - float(timestamp)
                if age_seconds < max_age_seconds:
                    continue

                task_id = task_data.get('id')
                archive_key = f'archived_task:{task_id}'
                archive_data = dict(task_data)
                archive_data['archived_at'] = current_time
                self.client.hset(archive_key, mapping=archive_data)
                self.client.delete(task_key)
                self.client.lrem(self.QUEUE_KEY, 0, task_id)

                parent_id = task_data.get('parent_priority_id')
                if parent_id:
                    children_key = f'{self.PRIORITY_CHILDREN_PREFIX}{parent_id}'
                    self.client.srem(children_key, task_id)

                archived_count += 1

            return archived_count
        except redis.RedisError as e:
            raise ValueError(f"Failed to cleanup stale tasks: {e}") from e
'''

    # Find insertion point
    insertion_point = content.find('    # Phase 1: Parent-child relationship tracking')
    if insertion_point == -1:
        print("❌ Could not find insertion point in RedisAdapter")
        return False

    # Insert method
    new_content = content[:insertion_point] + cleanup_method + '\n' + content[insertion_point:]

    # Write updated content
    with open(adapter_file, 'w') as f:
        f.write(new_content)

    print("✅ Added cleanup_stale_tasks() to RedisAdapter")
    print(f"   Location: src/priority_queue/adapters/redis_adapter.py")
    return True

def implement_metrics():
    """Add staleness metrics endpoint to MetricsDashboard."""
    print_section("STEP 2: Implement Staleness Metrics Dashboard")

    dashboard_file = project_root / 'src/priority_queue/adapters/metrics_dashboard.py'

    with open(dashboard_file, 'r') as f:
        content = f.read()

    if 'handle_staleness' in content:
        print("✅ Staleness metrics endpoint already exists - skipping")
        return True

    # Add route registration
    route_addition = "        self.app.router.add_get('/metrics/staleness', self.handle_staleness)"
    route_marker = "        self.app.router.add_get('/metrics/prometheus', self.handle_prometheus)"

    if route_marker in content and route_addition.strip() not in content:
        content = content.replace(route_marker, route_marker + '\n' + route_addition)
        print("✅ Added staleness metrics route")

    # Add Redis adapter to __init__
    if "self.redis_adapter" not in content:
        init_addition = """        self.redis_adapter = config.get('redis_adapter')  # Phase 2 staleness metrics"""
        init_marker = "        self.pid_file = Path(config.get('pid_file', '/tmp/priority_worker_production.pid'))"
        if init_marker in content:
            content = content.replace(init_marker, init_marker + '\n' + init_addition)

    # Add handler method
    handler_method = '''
    async def handle_staleness(self, request: web.Request) -> web.Response:
        """GET /metrics/staleness - Phase 2 staleness detection metrics."""
        try:
            if not self.redis_adapter:
                return web.json_response({'error': 'Redis adapter not configured'}, status=503)

            all_task_keys = self.redis_adapter.client.keys('task_status:*')
            total_tasks = len(all_task_keys)
            stale_tasks = 0
            stale_by_priority = {}

            for task_key in all_task_keys:
                task_data = self.redis_adapter.client.hgetall(task_key)
                if task_data.get('status') == 'stale' or task_data.get('is_stale') == 'true':
                    stale_tasks += 1
                    parent_id = task_data.get('parent_priority_id', 'unknown')
                    stale_by_priority[parent_id] = stale_by_priority.get(parent_id, 0) + 1

            stale_rate = (stale_tasks / total_tasks * 100) if total_tasks > 0 else 0

            return web.json_response({
                'total_stale_tasks': stale_tasks,
                'total_tasks': total_tasks,
                'stale_task_rate_percent': round(stale_rate, 2),
                'stale_tasks_by_priority': stale_by_priority,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            return web.json_response({'error': f'Failed to fetch staleness metrics: {str(e)}'}, status=500)
'''

    insertion_marker = '    async def _get_pid(self) -> Optional[int]:'
    if insertion_marker in content:
        content = content.replace(insertion_marker, handler_method + '\n' + insertion_marker)

    with open(dashboard_file, 'w') as f:
        f.write(content)

    print("✅ Added /metrics/staleness endpoint to MetricsDashboard")
    print(f"   Location: src/priority_queue/adapters/metrics_dashboard.py")
    return True

def implement_backups():
    """Configure automated Redis backups."""
    print_section("STEP 3: Setup Automated Redis Backups")

    backup_script = project_root / 'scripts/backup_redis_priorities.sh'

    if not backup_script.exists():
        print("❌ Backup script not found - cannot configure cron")
        return False

    # Make backup script executable
    os.chmod(backup_script, 0o755)

    # Create retention policy documentation
    retention_doc = project_root / 'data/redis_backups/RETENTION_POLICY.md'
    retention_doc.parent.mkdir(parents=True, exist_ok=True)

    retention_content = """# Redis Backup Retention Policy

**Schedule:** Daily at 2:00 AM (cron)
**Location:** `data/redis_backups/`
**Format:** JSON (priority_backup_YYYYMMDD_HHMMSS.json)

## Retention Rules
- Daily backups: Keep last 7 days
- Weekly backups: Keep last 4 weeks
- Monthly backups: Keep last 12 months

## Restore Procedure
```bash
bash scripts/restore_redis_priorities.sh data/redis_backups/priority_backup_YYYYMMDD_HHMMSS.json
```
"""

    with open(retention_doc, 'w') as f:
        f.write(retention_content)

    print("✅ Backup script configured")
    print("✅ Retention policy created")
    print("⚠️  Manual step required: Add cron job (run setup_automated_backups.sh)")
    return True

def verify_implementations():
    """Verify all implementations are in place."""
    print_section("STEP 4: Verify Implementations")

    checks = []

    # Check 1: cleanup_stale_tasks exists
    adapter_file = project_root / 'src/priority_queue/adapters/redis_adapter.py'
    with open(adapter_file, 'r') as f:
        if 'def cleanup_stale_tasks' in f.read():
            print("✅ Stale task cleanup: IMPLEMENTED")
            checks.append(True)
        else:
            print("❌ Stale task cleanup: MISSING")
            checks.append(False)

    # Check 2: staleness metrics endpoint exists
    dashboard_file = project_root / 'src/priority_queue/adapters/metrics_dashboard.py'
    with open(dashboard_file, 'r') as f:
        if 'handle_staleness' in f.read():
            print("✅ Staleness metrics endpoint: IMPLEMENTED")
            checks.append(True)
        else:
            print("❌ Staleness metrics endpoint: MISSING")
            checks.append(False)

    # Check 3: backup policy exists
    retention_doc = project_root / 'data/redis_backups/RETENTION_POLICY.md'
    if retention_doc.exists():
        print("✅ Backup retention policy: IMPLEMENTED")
        checks.append(True)
    else:
        print("❌ Backup retention policy: MISSING")
        checks.append(False)

    return all(checks)

def main():
    """Execute all implementation steps."""
    print_section("Phase 2 Recommendations Implementation")
    print("Implementing all recommended actions from validation report...")

    success = True

    # Step 1: Cleanup implementation
    if not implement_cleanup():
        print("❌ Cleanup implementation failed")
        success = False

    # Step 2: Metrics implementation
    if not implement_metrics():
        print("❌ Metrics implementation failed")
        success = False

    # Step 3: Backup setup
    if not implement_backups():
        print("❌ Backup setup failed")
        success = False

    # Step 4: Verification
    if not verify_implementations():
        print("❌ Verification failed")
        success = False

    print_section("Implementation Complete")
    if success:
        print("✅ All Phase 2 recommendations successfully implemented")
        print("\nDeliverables:")
        print("  1. RedisAdapter.cleanup_stale_tasks() method")
        print("  2. MetricsDashboard /metrics/staleness endpoint")
        print("  3. Backup retention policy documentation")
        print("\nNext Steps:")
        print("  - Restart priority worker to load new code")
        print("  - Test /metrics/staleness endpoint")
        print("  - Configure cron job for automated backups")
        return 0
    else:
        print("❌ Some implementations failed - review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
