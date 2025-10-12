#!/bin/bash
# Redis Priority Data Backup Script
# Backs up hierarchical priority system data to JSON

BACKUP_DIR="data/redis_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/priority_backup_${TIMESTAMP}.json"

mkdir -p "${BACKUP_DIR}"

echo "==================================================================="
echo "Redis Priority Data Backup"
echo "==================================================================="
echo

source venv/bin/activate && python3 << EOFPYTHON
import json
from datetime import datetime
from src.priority_queue.adapters.redis_adapter import RedisAdapter

adapter = RedisAdapter({
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'lock_ttl': 3600,
    'worker_id': 'backup'
})

backup_data = {
    'timestamp': datetime.utcnow().isoformat(),
    'priorities': [],
    'tasks': {}
}

# Backup all priorities
all_priority_keys = adapter.client.keys('priority:*')
print(f"Found {len(all_priority_keys)} priorities to backup")

for key in all_priority_keys:
    priority_id = key.split(':')[1]
    priority = adapter.get_priority(priority_id)
    
    if priority:
        backup_data['priorities'].append(priority.to_dict())
        
        # Backup children tasks
        children = adapter.get_priority_children(priority_id)
        for child_id in children:
            task_data = adapter.client.hgetall(f'task_status:{child_id}')
            if task_data:
                backup_data['tasks'][child_id] = dict(task_data)
        
        print(f"✅ Backed up priority: {priority_id} ({len(children)} children)")

# Save to file
with open('${BACKUP_FILE}', 'w') as f:
    json.dump(backup_data, f, indent=2)

print(f"\n✅ Backup saved to: ${BACKUP_FILE}")
print(f"   Priorities: {len(backup_data['priorities'])}")
print(f"   Tasks: {len(backup_data['tasks'])}")
EOFPYTHON

echo
echo "==================================================================="
echo "Backup complete: ${BACKUP_FILE}"
echo "==================================================================="
