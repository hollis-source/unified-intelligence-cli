#!/bin/bash
# Workflow: Setup Automated Redis Backups
# Configures cron job for daily Redis priority queue backups

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_SCRIPT="$PROJECT_ROOT/scripts/backup_redis_priorities.sh"
CRON_TIME="0 2 * * *"  # Daily at 2 AM

echo "================================================================="
echo "Setting up Automated Redis Backups"
echo "================================================================="
echo

# Step 1: Verify backup script exists
echo "Step 1: Verifying backup script exists"
echo "-----------------------------------------------------------------"
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ Backup script not found: $BACKUP_SCRIPT"
    exit 1
fi

# Make backup script executable
chmod +x "$BACKUP_SCRIPT"
echo "✅ Backup script verified: $BACKUP_SCRIPT"
echo

# Step 2: Create cron job entry
echo "Step 2: Creating cron job entry"
echo "-----------------------------------------------------------------"
CRON_ENTRY="$CRON_TIME cd $PROJECT_ROOT && bash $BACKUP_SCRIPT >> $PROJECT_ROOT/logs/backup_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT" > /dev/null; then
    echo "✅ Cron job already exists for backup script"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✅ Cron job added: $CRON_TIME"
fi
echo

# Step 3: Create logs directory
echo "Step 3: Setting up logs directory"
echo "-----------------------------------------------------------------"
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"
echo "✅ Logs directory created: $LOGS_DIR"
echo

# Step 4: Verify cron job
echo "Step 4: Verifying cron configuration"
echo "-----------------------------------------------------------------"
if crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT" > /dev/null; then
    echo "✅ Cron job verified:"
    crontab -l | grep -F "$BACKUP_SCRIPT"
else
    echo "❌ Cron job verification failed"
    exit 1
fi
echo

# Step 5: Run initial backup test
echo "Step 5: Running initial backup test"
echo "-----------------------------------------------------------------"
if bash "$BACKUP_SCRIPT"; then
    echo "✅ Initial backup test successful"
else
    echo "❌ Initial backup test failed"
    exit 1
fi
echo

# Step 6: Create backup retention policy documentation
echo "Step 6: Creating backup retention policy"
echo "-----------------------------------------------------------------"
RETENTION_DOC="$PROJECT_ROOT/data/redis_backups/RETENTION_POLICY.md"
mkdir -p "$(dirname "$RETENTION_DOC")"

cat > "$RETENTION_DOC" << 'EOF'
# Redis Backup Retention Policy

**Schedule:** Daily at 2:00 AM (cron)
**Location:** `data/redis_backups/`
**Format:** JSON (priority_backup_YYYYMMDD_HHMMSS.json)

## Retention Rules

- **Daily backups:** Keep last 7 days
- **Weekly backups:** Keep last 4 weeks (Sunday backups)
- **Monthly backups:** Keep last 12 months (1st of month)

## Manual Cleanup

To remove old backups:
```bash
# Remove backups older than 30 days
find data/redis_backups/ -name "priority_backup_*.json" -mtime +30 -delete
```

## Restore Procedure

```bash
# List available backups
ls -lt data/redis_backups/

# Restore from backup
bash scripts/restore_redis_priorities.sh data/redis_backups/priority_backup_YYYYMMDD_HHMMSS.json
```

## Monitoring

- Check cron logs: `tail -f logs/backup_cron.log`
- Verify backups exist: `ls -lh data/redis_backups/`
- Last backup timestamp: `ls -lt data/redis_backups/ | head -2`
EOF

echo "✅ Retention policy created: $RETENTION_DOC"
echo

echo "================================================================="
echo "✅ Automated Redis Backups Setup Complete"
echo "================================================================="
echo
echo "Summary:"
echo "  - Cron schedule: Daily at 2:00 AM"
echo "  - Backup script: $BACKUP_SCRIPT"
echo "  - Logs location: $LOGS_DIR/backup_cron.log"
echo "  - Backups location: $PROJECT_ROOT/data/redis_backups/"
echo "  - Retention policy: $RETENTION_DOC"
echo
echo "Next Steps:"
echo "  1. Monitor first scheduled backup: tail -f logs/backup_cron.log"
echo "  2. Verify backup files: ls -lh data/redis_backups/"
echo "  3. Test restore procedure: bash scripts/restore_redis_priorities.sh"
echo

exit 0
