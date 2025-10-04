#!/bin/bash
# Monitor SYD2 Autonomous Agent
# Usage: ./scripts/monitor_syd2.sh

set -e

HOST="root@syd2.jacobhollis.com"
LOG_FILE="/opt/unified-intelligence-cli/logs/syd2_agent_24h.log"
METRICS_DIR="/opt/unified-intelligence-cli/data/syd2_metrics"

echo "==================================================="
echo "SYD2 Autonomous Agent Monitor"
echo "==================================================="
echo

# Check process status
echo "Process Status:"
ssh $HOST "ps aux | grep syd2_agent.py | grep -v grep | awk '{print \$2, \$9, \$10, \$11, \$12, \$13}'" || echo "Agent not running"
echo

# Check recent logs
echo "Recent Activity (last 50 lines):"
ssh $HOST "tail -50 $LOG_FILE"
echo

# Check metrics
echo "Metrics Summary:"
ssh $HOST "ls -lh $METRICS_DIR/ 2>/dev/null | tail -10" || echo "No metrics yet"
echo

# Count tasks
echo "Task Statistics:"
TOTAL_TASKS=$(ssh $HOST "grep -c '\[Task' $LOG_FILE 2>/dev/null" || echo "0")
SUCCESS_TASKS=$(ssh $HOST "grep -c 'Completed: SUCCESS' $LOG_FILE 2>/dev/null" || echo "0")
FAILED_TASKS=$(ssh $HOST "grep -c 'Completed: FAILED' $LOG_FILE 2>/dev/null" || echo "0")

echo "  Total Tasks: $TOTAL_TASKS"
echo "  Successful: $SUCCESS_TASKS"
echo "  Failed: $FAILED_TASKS"

if [ "$TOTAL_TASKS" -gt "0" ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS_TASKS * 100 / $TOTAL_TASKS" | bc)
    echo "  Success Rate: $SUCCESS_RATE%"
fi

echo
echo "==================================================="
echo "To view live logs: ssh $HOST 'tail -f $LOG_FILE'"
echo "==================================================="
