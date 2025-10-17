#!/bin/bash
# Quick start script for agent performance measurement
# Usage: ./measure_agents.sh [baseline|test|compare|dashboard]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories
DATA_DIR="data/agent_performance"
BASELINE_FILE="$DATA_DIR/baseline.json"

# Functions
print_header() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}================================${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Create data directory
mkdir -p "$DATA_DIR"

# Main commands
case "${1:-help}" in
    baseline)
        print_header "Running Baseline Measurement"
        print_info "This will test all 5 agents with 20 tasks each (~10-15 minutes)"
        print_info "Results will be saved as baseline.json"
        echo ""
        
        python3 test_agent_performance.py --agent all --save-baseline
        
        print_success "Baseline measurement complete!"
        print_info "View results: ./measure_agents.sh dashboard"
        ;;
    
    test)
        AGENT="${2:-all}"
        print_header "Running Performance Test"
        print_info "Testing agent: $AGENT"
        echo ""
        
        python3 test_agent_performance.py --agent "$AGENT"
        
        print_success "Test complete!"
        print_info "View results: ./measure_agents.sh dashboard"
        ;;
    
    compare)
        if [ ! -f "$BASELINE_FILE" ]; then
            print_error "No baseline found. Run: ./measure_agents.sh baseline"
            exit 1
        fi
        
        # Find most recent results file
        LATEST=$(ls -t "$DATA_DIR"/results_*.json 2>/dev/null | head -1)
        
        if [ -z "$LATEST" ]; then
            print_error "No test results found. Run: ./measure_agents.sh test"
            exit 1
        fi
        
        print_header "Comparing Results"
        print_info "Baseline: $BASELINE_FILE"
        print_info "Current:  $LATEST"
        echo ""
        
        python3 test_agent_performance.py --compare "$BASELINE_FILE" "$LATEST"
        ;;
    
    dashboard)
        print_header "Agent Performance Dashboard"
        echo ""
        
        python3 agent_metrics_dashboard.py
        ;;
    
    export)
        OUTPUT="${2:-agent_performance_report.html}"
        print_header "Exporting Dashboard"
        print_info "Output: $OUTPUT"
        echo ""
        
        python3 agent_metrics_dashboard.py --export "$OUTPUT"
        
        print_success "Dashboard exported!"
        print_info "Open in browser: open $OUTPUT"
        ;;
    
    clean)
        print_header "Cleaning Results"
        print_info "This will delete all results except baseline.json"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            find "$DATA_DIR" -name "results_*.json" -delete
            print_success "Results cleaned!"
        else
            print_info "Cancelled"
        fi
        ;;
    
    help|*)
        cat << EOF
Agent Performance Measurement System

Usage: ./measure_agents.sh [command] [options]

Commands:
  baseline              Run baseline measurement (all agents, save as baseline.json)
  test [agent]          Run performance test (default: all agents)
  compare               Compare latest results with baseline
  dashboard             View performance dashboard
  export [file]         Export dashboard to HTML (default: agent_performance_report.html)
  clean                 Delete all results except baseline
  help                  Show this help message

Examples:
  ./measure_agents.sh baseline                    # Initial baseline
  ./measure_agents.sh test python-engineer        # Test single agent
  ./measure_agents.sh test all                    # Test all agents
  ./measure_agents.sh compare                     # Compare with baseline
  ./measure_agents.sh dashboard                   # View dashboard
  ./measure_agents.sh export report.html          # Export to HTML

Agents:
  - python-engineer      Code quality, refactoring, SOLID principles
  - software-architect   System design, Clean Architecture
  - test-engineer        Unit, integration, E2E test generation
  - devops-engineer      CI/CD, deployment, monitoring
  - research-analyst     Documentation, investigation, planning

Workflow:
  1. Run baseline:  ./measure_agents.sh baseline
  2. View results:  ./measure_agents.sh dashboard
  3. Make changes:  (improve prompts, add examples, etc.)
  4. Re-test:       ./measure_agents.sh test
  5. Compare:       ./measure_agents.sh compare
  6. Iterate!

Documentation: See AGENT_METRICS.md for details

EOF
        ;;
esac

