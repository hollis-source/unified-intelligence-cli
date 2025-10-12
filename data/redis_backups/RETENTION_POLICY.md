# Redis Backup Retention Policy

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

## Manual Cleanup
```bash
# Remove backups older than 30 days
find data/redis_backups/ -name "priority_backup_*.json" -mtime +30 -delete
```
