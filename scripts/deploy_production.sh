#!/bin/bash
# Production Deployment Script for PriorityWorker
# Transitions from pilot to continuous 24/7 operation
# Generated on 2025-10-04

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/priority_worker_production.yaml"
LOG_FILE="${PROJECT_ROOT}/logs/priority_worker_production.log"
PID_FILE="/tmp/priority_worker_production.pid"
STOP_FILE="/tmp/priority_worker_stop"

# Logging functions
log() {
    local level=$1
    shift
    echo -e "${GREEN}[${level}]${NC} $*"
}

error_exit() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# Function to check if PriorityWorker is already running
check_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Running
        else
            # Stale PID file
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Function to setup venv and install dependencies (PEP 668 compliant)
setup_venv() {
    log "INFO" "Setting up virtual environment..."

    # Create venv if it doesn't exist
    if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
        log "INFO" "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv" || error_exit "Failed to create venv."
    else
        log "INFO" "Virtual environment already exists."
    fi

    # Activate venv
    source "$PROJECT_ROOT/venv/bin/activate" || error_exit "Failed to activate venv."
    log "INFO" "Virtual environment activated."

    # Install dependencies from requirements.txt
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        log "INFO" "Installing dependencies from requirements.txt..."
        pip install --upgrade pip > /dev/null 2>&1
        pip install -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1 || error_exit "Failed to install dependencies."
        log "INFO" "Dependencies installed successfully."
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    # Check Python version
    python3 --version > /dev/null 2>&1 || error_exit "Python 3 is not installed."

    # Check Redis
    if ! docker ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
        log "INFO" "Redis is not running. Will start via Docker."
    else
        log "INFO" "Redis is already running."
    fi

    # Check config file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error_exit "Configuration file not found: $CONFIG_FILE"
    fi

    log "INFO" "Prerequisites check passed."
}

# Function to ensure Redis is running
ensure_redis() {
    if ! docker ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
        log "INFO" "Starting Redis container..."
        docker run -d --name redis -p 6379:6379 redis:latest > /dev/null || error_exit "Failed to start Redis."
        sleep 2  # Wait for Redis to initialize
        log "INFO" "Redis started successfully."
    else
        log "INFO" "Redis is already running. Skipping start."
    fi
}

# Function to create log directory
setup_logging() {
    log "INFO" "Setting up logging..."

    mkdir -p "$(dirname "$LOG_FILE")"

    # Rotate old log if it exists and is large
    if [[ -f "$LOG_FILE" ]]; then
        local size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
        if [[ $size -gt 10485760 ]]; then  # 10MB
            mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S)"
            log "INFO" "Rotated old log file."
        fi
    fi

    log "INFO" "Logging configured."
}

# Function to start PriorityWorker in background
start_worker() {
    log "INFO" "Starting PriorityWorker in production mode..."

    # Remove stop file if it exists
    rm -f "$STOP_FILE"

    # Start worker in background with nohup
    nohup "$PROJECT_ROOT/venv/bin/python3" "$PROJECT_ROOT/scripts/priority_worker.py" \
        --config "$CONFIG_FILE" \
        --loop \
        >> "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait a moment and check if it's still running
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        log "INFO" "PriorityWorker started successfully with PID: $pid"
        log "INFO" "Logs: $LOG_FILE"
        log "INFO" "To stop: touch $STOP_FILE or kill $pid"
    else
        error_exit "PriorityWorker failed to start. Check logs: $LOG_FILE"
    fi
}

# Function to monitor worker (first 60 seconds)
monitor_worker() {
    log "INFO" "Monitoring PriorityWorker for the first 60 seconds..."

    local pid=$(cat "$PID_FILE")
    local count=0

    while [[ $count -lt 12 ]]; do  # 12 * 5 = 60 seconds
        if ! ps -p "$pid" > /dev/null 2>&1; then
            error_exit "PriorityWorker stopped unexpectedly. Check logs: $LOG_FILE"
        fi

        # Show last 5 lines of log
        if [[ -f "$LOG_FILE" ]]; then
            echo -e "\n${GREEN}[LOG TAIL]${NC}"
            tail -n 5 "$LOG_FILE"
        fi

        sleep 5
        count=$((count + 1))
    done

    log "INFO" "PriorityWorker is stable and running in background."
}

# Function to display status
show_status() {
    if check_running; then
        local pid=$(cat "$PID_FILE")
        log "INFO" "PriorityWorker is RUNNING (PID: $pid)"
        log "INFO" "Logs: $LOG_FILE"
        log "INFO" "To stop: touch $STOP_FILE or kill $pid"
    else
        log "INFO" "PriorityWorker is NOT running"
    fi
}

# Function to stop worker
stop_worker() {
    if check_running; then
        local pid=$(cat "$PID_FILE")
        log "INFO" "Stopping PriorityWorker (PID: $pid)..."

        # Create stop file for graceful shutdown
        touch "$STOP_FILE"

        # Wait up to 30 seconds for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 30 ]]; do
            sleep 1
            count=$((count + 1))
        done

        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            warn "Graceful shutdown timed out. Force killing..."
            kill -9 "$pid"
        fi

        rm -f "$PID_FILE"
        rm -f "$STOP_FILE"
        log "INFO" "PriorityWorker stopped."
    else
        log "INFO" "PriorityWorker is not running."
    fi
}

# Main execution
main() {
    local action="${1:-start}"

    case "$action" in
        start)
            log "INFO" "Starting PriorityWorker production deployment..."

            if check_running; then
                error_exit "PriorityWorker is already running. Use 'stop' first."
            fi

            check_prerequisites
            setup_venv
            ensure_redis
            setup_logging
            start_worker
            monitor_worker

            echo ""
            log "INFO" "Production deployment complete!"
            log "INFO" "PriorityWorker is now running in 24/7 continuous mode."
            ;;

        stop)
            stop_worker
            ;;

        status)
            show_status
            ;;

        restart)
            stop_worker
            sleep 2
            "$0" start
            ;;

        logs)
            if [[ -f "$LOG_FILE" ]]; then
                tail -f "$LOG_FILE"
            else
                error_exit "Log file not found: $LOG_FILE"
            fi
            ;;

        *)
            echo "Usage: $0 {start|stop|status|restart|logs}"
            exit 1
            ;;
    esac
}

main "$@"
