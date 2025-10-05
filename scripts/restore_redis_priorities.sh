#!/bin/bash
# Redis Priority Data Restore Script
# Restores hierarchical priority system data from JSON backup

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 data/redis_backups/priority_backup_20251005_010000.json"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "==================================================================="
echo "Redis Priority Data Restore"
echo "==================================================================="
echo
echo "⚠️  WARNING: This will restore data from backup."
echo "   Existing priorities/tasks may be overwritten."
echo
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

source venv/bin/activate && python3 << EOFPYTHON
import json
from src.priority_queue.adapters.redis_adapter import RedisAdapter
from src.priority_queue.entities import Priority

adapter = RedisAdapter({
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'lock_ttl': 3600,
    'worker_id': 'restore'
})

# Load backup
with open('${BACKUP_FILE}', 'r') as f:
    backup_data = json.load(f)

print(f"Backup from: {backup_data['timestamp']}")
print(f"Priorities: {len(backup_data['priorities'])}")
print(f"Tasks: {len(backup_data['tasks'])}")
print()

# Restore priorities
for priority_data in backup_data['priorities']:
    priority = Priority.from_dict(priority_data)
    adapter.create_priority(priority)
    print(f"✅ Restored priority: {priority.id}")

# Restore tasks
for task_id, task_data in backup_data['tasks'].items():
    # Restore task data to Redis
    adapter.client.hset(f'task_status:{task_id}', mapping=task_data)
    
    # Re-link to parent
    parent_id = task_data.get('parent_priority_id')
    if parent_id:
        adapter.link_task_to_priority(task_id, parent_id)
    
    print(f"✅ Restored task: {task_id}")

print()
print("=================================================================")
print("✅ Restore complete")
print("=================================================================")
EOFPYTHON
