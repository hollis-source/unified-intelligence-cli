#!/bin/bash
# Continuous monitoring script for Phase 1 naming refactoring

LOG_FILE="naming_refactoring_phase1.log"
CHECK_INTERVAL=30  # seconds

echo "=== Phase 1 Naming Refactoring Monitor ==="
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo ""

iteration=0
last_size=0

while true; do
    iteration=$((iteration + 1))
    timestamp=$(date '+%H:%M:%S')
    
    # Check if log file exists
    if [ ! -f "$LOG_FILE" ]; then
        echo "[$timestamp] Waiting for log file to appear..."
        sleep $CHECK_INTERVAL
        continue
    fi
    
    # Get current file size and line count
    current_size=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    line_count=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    
    # Check if file is still growing
    if [ "$current_size" -eq "$last_size" ] && [ "$last_size" -gt 0 ]; then
        status_indicator="📊"
    else
        status_indicator="🔄"
    fi
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════"
    echo "║ Check #$iteration @ $timestamp $status_indicator"
    echo "╠════════════════════════════════════════════════════════════════"
    
    # Extract key information from log
    execution_mode=$(grep "Starting autonomous run" "$LOG_FILE" | tail -1 | grep -o "execution=[^ ]*" || echo "execution=unknown")
    current_iteration=$(grep -E "^Iteration [0-9]+ @" "$LOG_FILE" | tail -1 | grep -o "Iteration [0-9]*" || echo "Iteration ?")
    
    echo "║ Execution: $execution_mode"
    echo "║ Progress: $current_iteration of 3"
    echo "║ Log size: $current_size bytes ($line_count lines)"
    
    # Check for errors
    if grep -q "PermissionError\|WorkerExecutionError\|Failed to start" "$LOG_FILE" 2>/dev/null; then
        echo "║ Status: ❌ ERROR DETECTED"
        error_line=$(grep -E "PermissionError|WorkerExecutionError|Failed to start" "$LOG_FILE" | tail -1)
        echo "║ Error: ${error_line:0:60}..."
    elif grep -q "Result: SUCCESS" "$LOG_FILE" 2>/dev/null; then
        success_count=$(grep -c "Result: SUCCESS" "$LOG_FILE")
        echo "║ Status: ✅ $success_count iteration(s) completed"
    else
        echo "║ Status: ⏳ Running..."
    fi
    
    # Show recent activity (last 5 lines with content)
    echo "║"
    echo "║ Recent activity:"
    tail -15 "$LOG_FILE" | grep -v "^$" | tail -5 | while IFS= read -r line; do
        # Truncate long lines
        short_line="${line:0:58}"
        echo "║   ${short_line}"
    done
    
    # Check if process completed
    if grep -q "All.*iterations complete\|Shutting down" "$LOG_FILE" 2>/dev/null; then
        echo "╠════════════════════════════════════════════════════════════════"
        echo "║ 🎉 PHASE 1 COMPLETED!"
        echo "╚════════════════════════════════════════════════════════════════"
        
        # Show final summary
        echo ""
        echo "=== FINAL SUMMARY ==="
        grep -E "Total iterations:|Success rate:|Result: SUCCESS|Result: FAILURE" "$LOG_FILE" | tail -10
        
        break
    fi
    
    # Check if process is still running
    if ! pgrep -f "naming_refactoring_phase_1.*--working-dir" > /dev/null; then
        echo "╠════════════════════════════════════════════════════════════════"
        echo "║ ⚠️  Process not found - may have completed or crashed"
        echo "╚════════════════════════════════════════════════════════════════"
        break
    fi
    
    echo "╚════════════════════════════════════════════════════════════════"
    
    last_size=$current_size
    sleep $CHECK_INTERVAL
done

echo ""
echo "Monitor stopped at: $(date)"
