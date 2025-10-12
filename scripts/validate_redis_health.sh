#!/bin/bash
# Redis Health & Data Integrity Validation
# Runs periodic checks on priority queue data

echo "==================================================================="
echo "Redis Health & Data Integrity Check"
echo "==================================================================="
echo

# Check 1: Redis connectivity
echo "Check 1: Redis Connectivity"
echo "-------------------------------------------------------------------"
if docker exec priority-worker-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis responding to PING"
else
    echo "❌ Redis not responding"
    exit 1
fi

# Check 2: AOF persistence enabled
echo
echo "Check 2: AOF Persistence Configuration"
echo "-------------------------------------------------------------------"
AOF_STATUS=$(docker exec priority-worker-redis redis-cli CONFIG GET appendonly | tail -1)
if [ "$AOF_STATUS" = "yes" ]; then
    echo "✅ AOF (Append-Only File) enabled"
else
    echo "⚠️  AOF disabled - data may not persist"
fi

# Check 3: Volume mount verified
echo
echo "Check 3: Volume Mount Verification"
echo "-------------------------------------------------------------------"
VOLUME_MOUNT=$(docker inspect priority-worker-redis --format '{{ range .Mounts }}{{ if eq .Destination "/data" }}{{ .Source }}{{ end }}{{ end }}')
if [ -n "$VOLUME_MOUNT" ]; then
    echo "✅ Volume mounted at: $VOLUME_MOUNT"
else
    echo "❌ No volume mount found for /data"
    exit 1
fi

# Check 4: Data integrity
echo
echo "Check 4: Priority Data Integrity"
echo "-------------------------------------------------------------------"
source venv/bin/activate && python3 << 'EOFPYTHON'
from src.priority_queue.adapters.redis_adapter import RedisAdapter

adapter = RedisAdapter({
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'lock_ttl': 3600,
    'worker_id': 'validator'
})

# Check all priorities are valid
all_priority_keys = adapter.client.keys('priority:*')
valid_priorities = 0
invalid_priorities = 0

for key in all_priority_keys:
    priority_id = key.split(':')[1]
    priority = adapter.get_priority(priority_id)
    
    if priority and priority.is_valid_status():
        valid_priorities += 1
        
        # Verify children integrity
        children = adapter.get_priority_children(priority_id)
        orphaned_children = 0
        
        for child_id in children:
            task_data = adapter.client.hgetall(f'task_status:{child_id}')
            if not task_data:
                orphaned_children += 1
        
        if orphaned_children > 0:
            print(f"⚠️  Priority {priority_id} has {orphaned_children} orphaned children")
    else:
        invalid_priorities += 1
        print(f"❌ Invalid priority: {priority_id}")

print(f"✅ Valid priorities: {valid_priorities}")
if invalid_priorities > 0:
    print(f"❌ Invalid priorities: {invalid_priorities}")
    exit(1)
EOFPYTHON

# Check 5: Disk space
echo
echo "Check 5: Disk Space"
echo "-------------------------------------------------------------------"
DISK_USAGE=$(df -h /var/lib/docker/volumes/ | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo "✅ Disk usage: ${DISK_USAGE}% (healthy)"
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo "⚠️  Disk usage: ${DISK_USAGE}% (warning)"
else
    echo "❌ Disk usage: ${DISK_USAGE}% (critical)"
    exit 1
fi

echo
echo "==================================================================="
echo "✅ All health checks passed"
echo "==================================================================="
