#!/usr/bin/env python3
"""
Workflow: Implement Staleness Metrics Dashboard
Adds staleness metrics endpoint to MetricsDashboard for monitoring context changes.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def implement_staleness_metrics():
    """Add staleness metrics endpoint to MetricsDashboard."""

    dashboard_file = project_root / 'src/priority_queue/adapters/metrics_dashboard.py'

    # Read current content
    with open(dashboard_file, 'r') as f:
        content = f.read()

    # Check if already implemented
    if 'handle_staleness' in content:
        print("✅ Staleness metrics endpoint already exists")
        return True

    # Step 1: Add route registration
    route_addition = "        self.app.router.add_get('/metrics/staleness', self.handle_staleness)"

    if route_addition.strip() in content:
        print("✅ Staleness route already registered")
    else:
        # Find the route registration section
        route_marker = "        self.app.router.add_get('/metrics/prometheus', self.handle_prometheus)"
        if route_marker in content:
            content = content.replace(
                route_marker,
                route_marker + '\n' + route_addition
            )
            print("✅ Added staleness metrics route")
        else:
            print("❌ Could not find route registration section")
            return False

    # Step 2: Add Redis adapter to __init__
    init_addition = """        self.redis_adapter = config.get('redis_adapter')  # For staleness metrics"""

    if "self.redis_adapter" not in content:
        # Find __init__ method and add after self.pid_file
        init_marker = "        self.pid_file = Path(config.get('pid_file', '/tmp/priority_worker_production.pid'))"
        if init_marker in content:
            content = content.replace(
                init_marker,
                init_marker + '\n' + init_addition
            )
            print("✅ Added redis_adapter to __init__")
        else:
            print("⚠️  Could not find __init__ marker, continuing...")

    # Step 3: Add handler method
    handler_method = '''
    async def handle_staleness(self, request: web.Request) -> web.Response:
        """GET /metrics/staleness - Staleness detection metrics.

        Phase 2: Context change and task staleness monitoring.
        Returns:
            - total_stale_tasks: Current count of stale tasks
            - stale_task_rate: Percentage of tasks marked stale
            - context_changes: Number of context changes (if tracked)
            - stale_tasks_by_priority: Breakdown by parent priority
        """
        try:
            if not self.redis_adapter:
                return web.json_response({
                    'error': 'Redis adapter not configured'
                }, status=503)

            # Query Redis for stale task metrics
            all_task_keys = self.redis_adapter.client.keys('task_status:*')

            total_tasks = len(all_task_keys)
            stale_tasks = 0
            stale_by_priority = {}

            for task_key in all_task_keys:
                task_data = self.redis_adapter.client.hgetall(task_key)

                if task_data.get('status') == 'stale' or task_data.get('is_stale') == 'true':
                    stale_tasks += 1

                    # Track by parent priority
                    parent_id = task_data.get('parent_priority_id', 'unknown')
                    stale_by_priority[parent_id] = stale_by_priority.get(parent_id, 0) + 1

            # Calculate staleness rate
            stale_rate = (stale_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Query for context change tracking (if available)
            context_changes = 0
            priorities = self.redis_adapter.client.keys('priority:*')
            for priority_key in priorities:
                priority_data = self.redis_adapter.client.hgetall(priority_key)
                # Count priorities that have been updated (would need update_count field)
                # For now, just count total priorities as proxy
                context_changes = len(priorities)

            metrics = {
                'total_stale_tasks': stale_tasks,
                'total_tasks': total_tasks,
                'stale_task_rate_percent': round(stale_rate, 2),
                'context_changes_tracked': context_changes,
                'stale_tasks_by_priority': stale_by_priority,
                'timestamp': datetime.utcnow().isoformat()
            }

            return web.json_response(metrics)

        except Exception as e:
            return web.json_response({
                'error': f'Failed to fetch staleness metrics: {str(e)}'
            }, status=500)
'''

    # Find insertion point (after handle_prometheus method)
    insertion_marker = '    async def _get_pid(self) -> Optional[int]:'

    if insertion_marker in content:
        content = content.replace(
            insertion_marker,
            handler_method + '\n' + insertion_marker
        )
        print("✅ Added handle_staleness() method")
    else:
        print("❌ Could not find insertion point for handler method")
        return False

    # Write updated content
    with open(dashboard_file, 'w') as f:
        f.write(content)

    print("✅ Staleness metrics dashboard implementation complete")
    print(f"   Location: {dashboard_file}")
    print(f"   Endpoint: GET /metrics/staleness")
    print(f"   Metrics: stale_tasks, stale_rate, context_changes, breakdown")

    return True

if __name__ == '__main__':
    success = implement_staleness_metrics()
    sys.exit(0 if success else 1)
