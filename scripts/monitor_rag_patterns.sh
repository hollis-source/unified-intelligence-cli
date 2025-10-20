#!/bin/bash
# Monitor RAG Pattern Collection Progress
# Usage: ./scripts/monitor_rag_patterns.sh

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# RAG Metrics API
API_BASE="http://localhost:8888/api/rag"

echo "================================================================================"
echo "RAG PATTERN COLLECTION MONITOR"
echo "================================================================================"
echo ""

# Function to get metrics
get_metrics() {
    curl -s "${API_BASE}/metrics" 2>/dev/null
}

# Function to get pattern count
get_pattern_count() {
    curl -s "${API_BASE}/patterns" 2>/dev/null | grep -o '"total":[0-9]*' | grep -o '[0-9]*'
}

# Function to get routing accuracy
get_accuracy() {
    curl -s "${API_BASE}/routing/accuracy" 2>/dev/null | grep -o '"rag":[0-9.]*' | grep -o '[0-9.]*'
}

# Function to get alerts
get_alerts() {
    curl -s "${API_BASE}/alerts" 2>/dev/null
}

# Main monitoring loop
while true; do
    clear
    
    echo "================================================================================"
    echo "RAG PATTERN COLLECTION MONITOR - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================================================"
    echo ""
    
    # Get pattern count
    PATTERN_COUNT=$(get_pattern_count)
    
    if [ -z "$PATTERN_COUNT" ]; then
        echo -e "${RED}❌ Cannot connect to RAG metrics API${NC}"
        echo "   Make sure the server is running: python start_rag_server.py"
        echo ""
        sleep 5
        continue
    fi
    
    # Progress bar
    TARGET=50
    PROGRESS=$((PATTERN_COUNT * 100 / TARGET))
    BAR_LENGTH=50
    FILLED=$((PATTERN_COUNT * BAR_LENGTH / TARGET))
    
    echo "PATTERN COLLECTION PROGRESS:"
    echo -n "["
    for ((i=0; i<BAR_LENGTH; i++)); do
        if [ $i -lt $FILLED ]; then
            echo -n "="
        else
            echo -n " "
        fi
    done
    echo -n "] ${PATTERN_COUNT}/${TARGET} (${PROGRESS}%)"
    echo ""
    echo ""
    
    # Status
    if [ $PATTERN_COUNT -ge $TARGET ]; then
        echo -e "${GREEN}✅ TARGET REACHED!${NC}"
    elif [ $PATTERN_COUNT -ge 25 ]; then
        echo -e "${YELLOW}⚠️  Halfway there...${NC}"
    else
        echo -e "${BLUE}🔄 In progress...${NC}"
    fi
    echo ""
    
    # Metrics
    echo "METRICS:"
    METRICS=$(get_metrics)
    
    if [ ! -z "$METRICS" ]; then
        echo "$METRICS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    metrics = data.get('metrics', {})
    print(f\"  Total Patterns: {metrics.get('total_patterns', 0)}\")
    print(f\"  Routing Decisions: {metrics.get('total_routing_decisions', 0)}\")
    print(f\"  RAG Accuracy: {metrics.get('rag_routing_accuracy', 0):.1f}%\")
    print(f\"  RAG Enabled: {metrics.get('rag_enabled', False)}\")
except:
    print('  Error parsing metrics')
"
    fi
    echo ""
    
    # Alerts
    echo "ALERTS:"
    ALERTS=$(get_alerts)
    
    if [ ! -z "$ALERTS" ]; then
        echo "$ALERTS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    alerts = data.get('alerts', {})
    total = alerts.get('total_alerts', 0)
    by_severity = alerts.get('by_severity', {})
    
    if total == 0:
        print('  ✅ No alerts')
    else:
        print(f\"  Total: {total}\")
        if by_severity.get('critical', 0) > 0:
            print(f\"  🔴 Critical: {by_severity['critical']}\")
        if by_severity.get('error', 0) > 0:
            print(f\"  🟠 Error: {by_severity['error']}\")
        if by_severity.get('warning', 0) > 0:
            print(f\"  🟡 Warning: {by_severity['warning']}\")
except:
    print('  Error parsing alerts')
"
    fi
    echo ""
    
    # Execution log
    if [ -f "logs/pattern_collection_results.json" ]; then
        echo "EXECUTION LOG:"
        python3 -c "
import json
try:
    with open('logs/pattern_collection_results.json', 'r') as f:
        results = json.load(f)
    
    total = len(results)
    success = sum(1 for r in results if r.get('status') == 'success')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    
    print(f\"  Total Executed: {total}\")
    print(f\"  ✅ Success: {success} ({success/total*100:.1f}%)\" if total > 0 else '  ✅ Success: 0')
    print(f\"  ❌ Failed: {failed} ({failed/total*100:.1f}%)\" if total > 0 else '  ❌ Failed: 0')
except:
    print('  No execution log yet')
"
        echo ""
    fi
    
    # Instructions
    echo "================================================================================"
    echo "Press Ctrl+C to exit"
    echo "Refreshing every 5 seconds..."
    echo "================================================================================"
    
    sleep 5
done

