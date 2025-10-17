#!/bin/bash

LOG_FILE="naming_refactoring_phase2.log"
CHECK_INTERVAL=30

echo "=== Phase 2 Naming Refactoring Monitor ==="
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo ""

check_count=0
last_size=0

while true; do
    check_count=$((check_count + 1))
    
    # Get current log size
    if [ -f "$LOG_FILE" ]; then
        current_size=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
        line_count=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    else
        current_size=0
        line_count=0
    fi
    
    # Check if file is still growing
    if [ "$current_size" -eq "$last_size" ] && [ "$last_size" -gt 0 ]; then
        status_indicator="📊"
    else
        status_indicator="🔄"
    fi
    
    echo "╔════════════════════════════════════════════════════════════════"
    echo "║ Check #${check_count} @ $(date +%H:%M:%S) ${status_indicator}"
    echo "╠════════════════════════════════════════════════════════════════"
    
    # Check execution type
    if grep -q "execution=LOCAL" "$LOG_FILE" 2>/dev/null; then
        echo "║ Execution: execution=LOCAL"
    fi
    
    # Check iteration
    if grep -q "Iteration" "$LOG_FILE" 2>/dev/null; then
        iteration=$(grep "Iteration" "$LOG_FILE" | tail -1 | grep -oP "Iteration \K\d+")
        echo "║ Progress: Iteration $iteration of 4"
    fi
    
    echo "║ Log size: ${current_size} bytes (${line_count} lines)"
    
    # Check for errors
    if grep -q "PermissionError\|WorkerExecutionError\|Failed to start" "$LOG_FILE" 2>/dev/null; then
        echo "║ Status: ❌ ERROR DETECTED"
    elif grep -q "Result: SUCCESS" "$LOG_FILE" 2>/dev/null; then
        success_count=$(grep -c "Result: SUCCESS" "$LOG_FILE" 2>/dev/null)
        echo "║ Status: ✅ $success_count iteration(s) completed"
    elif [ "$current_size" -gt 0 ]; then
        echo "║ Status: ⏳ Running..."
    else
        echo "║ Status: 🔄 Starting..."
    fi
    
    echo "║"
    echo "║ Recent activity:"
    if [ -f "$LOG_FILE" ] && [ "$current_size" -gt 0 ]; then
        echo "║   =========================================================="
        tail -5 "$LOG_FILE" 2>/dev/null | sed 's/^/║   /'
    else
        echo "║   (No output yet)"
    fi
    echo "╚════════════════════════════════════════════════════════════════"
    echo ""
    
    last_size=$current_size
    sleep $CHECK_INTERVAL
done
