#!/bin/bash
# Health Check Script for PriorityWorker Production Daemon
# Verifies process health, log activity, and Redis connectivity
# Exit codes: 0 = healthy, 1 = unhealthy, 2 = warning

set -euo pipefail

# Configuration
PID_FILE="/tmp/priority_worker_production.pid"
LOG_FILE="/home/ui-cli_jake/unified-intelligence-cli/logs/priority_worker_production.log"
MAX_LOG_AGE_SECONDS=300  # 5 minutes
REDIS_HOST="localhost"
REDIS_PORT=6379

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Health status
HEALTH_STATUS=0
WARNINGS=()
ERRORS=()

# Function to check process status
check_process() {
    if [[ ! -f "$PID_FILE" ]]; then
        ERRORS+=("PID file not found: $PID_FILE")
        HEALTH_STATUS=1
        return
    fi

    local pid=$(cat "$PID_FILE")
    if ! ps -p "$pid" > /dev/null 2>&1; then
        ERRORS+=("Process not running (PID: $pid)")
        HEALTH_STATUS=1
        return
    fi

    # Check process uptime
    local uptime=$(ps -p "$pid" -o etime= | tr -d ' ')
    echo -e "${GREEN}✓${NC} Process running (PID: $pid, uptime: $uptime)"
}

# Function to check log activity
check_log_activity() {
    if [[ ! -f "$LOG_FILE" ]]; then
        WARNINGS+=("Log file not found: $LOG_FILE")
        [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
        return
    fi

    # Check last modification time
    local last_mod=$(stat -c %Y "$LOG_FILE" 2>/dev/null || stat -f %m "$LOG_FILE" 2>/dev/null)
    local now=$(date +%s)
    local age=$((now - last_mod))

    if [[ $age -gt $MAX_LOG_AGE_SECONDS ]]; then
        WARNINGS+=("Log inactive for ${age}s (max: ${MAX_LOG_AGE_SECONDS}s)")
        [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
    else
        echo -e "${GREEN}✓${NC} Log activity recent (${age}s ago)"
    fi

    # Check for errors in last 100 lines
    local error_count=$(tail -100 "$LOG_FILE" | grep -ci "error" || true)
    if [[ $error_count -gt 0 ]]; then
        WARNINGS+=("Found $error_count errors in recent logs")
        [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
    fi
}

# Function to check Redis connectivity
check_redis() {
    if command -v redis-cli > /dev/null 2>&1; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Redis accessible (${REDIS_HOST}:${REDIS_PORT})"
        else
            ERRORS+=("Redis not responding (${REDIS_HOST}:${REDIS_PORT})")
            HEALTH_STATUS=1
        fi
    else
        # Try docker if redis-cli not available
        if docker ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
            echo -e "${GREEN}✓${NC} Redis container running"
        else
            WARNINGS+=("Cannot verify Redis (redis-cli not available)")
            [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
        fi
    fi
}

# Function to check memory usage
check_memory() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            local mem_kb=$(ps -p "$pid" -o rss= | tr -d ' ')
            local mem_mb=$((mem_kb / 1024))

            if [[ $mem_mb -gt 500 ]]; then
                WARNINGS+=("High memory usage: ${mem_mb}MB")
                [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
            else
                echo -e "${GREEN}✓${NC} Memory usage normal (${mem_mb}MB)"
            fi
        fi
    fi
}

# Function to check disk space for logs
check_disk_space() {
    local log_dir=$(dirname "$LOG_FILE")
    local avail_mb=$(df -m "$log_dir" | tail -1 | awk '{print $4}')

    if [[ $avail_mb -lt 100 ]]; then
        WARNINGS+=("Low disk space: ${avail_mb}MB available")
        [[ $HEALTH_STATUS -eq 0 ]] && HEALTH_STATUS=2
    else
        echo -e "${GREEN}✓${NC} Disk space sufficient (${avail_mb}MB available)"
    fi
}

# Main health check
main() {
    echo "PriorityWorker Health Check - $(date)"
    echo "========================================="

    check_process
    check_log_activity
    check_redis
    check_memory
    check_disk_space

    echo ""

    # Report warnings
    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        echo -e "${YELLOW}Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo -e "  ${YELLOW}⚠${NC} $warning"
        done
        echo ""
    fi

    # Report errors
    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        echo -e "${RED}Errors:${NC}"
        for error in "${ERRORS[@]}"; do
            echo -e "  ${RED}✗${NC} $error"
        done
        echo ""
    fi

    # Final status
    case $HEALTH_STATUS in
        0)
            echo -e "${GREEN}Status: HEALTHY${NC}"
            exit 0
            ;;
        1)
            echo -e "${RED}Status: UNHEALTHY${NC}"
            exit 1
            ;;
        2)
            echo -e "${YELLOW}Status: WARNING${NC}"
            exit 2
            ;;
    esac
}

main
