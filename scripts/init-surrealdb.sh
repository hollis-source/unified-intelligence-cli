#!/bin/bash
# SurrealDB Schema Initialization Script
# Production Deployment - P1.1
#
# Applies init-surreal.surql schema to SurrealDB instance.
# Idempotent: Safe to run multiple times.

set -euo pipefail

# Configuration
SURREAL_HOST="${SURREAL_HOST:-localhost}"
SURREAL_PORT="${SURREAL_PORT:-8000}"
SURREAL_USER="${SURREAL_USER:-root}"
SURREAL_PASS="${SURREAL_PASS:-root}"
SURREAL_NS="${SURREAL_NS:-project_builder}"
SURREAL_DB="${SURREAL_DB:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="${SCHEMA_FILE:-$SCRIPT_DIR/init-surreal.surql}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if SurrealDB is reachable
check_surreal_connection() {
    log_info "Checking SurrealDB connection at $SURREAL_HOST:$SURREAL_PORT..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://$SURREAL_HOST:$SURREAL_PORT/health" > /dev/null 2>&1; then
            log_info "SurrealDB is reachable (attempt $attempt/$max_attempts)"
            return 0
        fi

        log_warn "SurrealDB not ready yet (attempt $attempt/$max_attempts), waiting 2s..."
        sleep 2
        ((attempt++))
    done

    log_error "SurrealDB not reachable after $max_attempts attempts"
    return 1
}

# Apply schema using surreal CLI or HTTP API
apply_schema() {
    log_info "Applying schema from $SCHEMA_FILE..."

    # Check if surreal CLI is available
    if command -v surreal &> /dev/null; then
        log_info "Using surreal CLI to apply schema..."
        surreal import \
            --conn "http://$SURREAL_HOST:$SURREAL_PORT" \
            --user "$SURREAL_USER" \
            --pass "$SURREAL_PASS" \
            --ns "$SURREAL_NS" \
            --db "$SURREAL_DB" \
            "$SCHEMA_FILE"
    else
        # Fallback: Use HTTP API with curl
        log_info "Using HTTP API to apply schema (surreal CLI not found)..."

        # Read schema file and execute via HTTP
        local response
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "NS: $SURREAL_NS" \
            -H "DB: $SURREAL_DB" \
            -u "$SURREAL_USER:$SURREAL_PASS" \
            -d @"$SCHEMA_FILE" \
            "http://$SURREAL_HOST:$SURREAL_PORT/sql")

        # Check if any errors in response
        if echo "$response" | grep -q '"status":"ERR"'; then
            log_error "Schema application failed:"
            echo "$response" | jq '.'
            return 1
        fi

        log_info "Schema applied successfully"
    fi
}

# Verify schema was applied
verify_schema() {
    log_info "Verifying schema..."

    # Query to check if tables exist
    local tables_query='INFO FOR DB;'

    local response
    response=$(curl -s -X POST \
        -H "Content-Type: text/plain" \
        -H "NS: $SURREAL_NS" \
        -H "DB: $SURREAL_DB" \
        -H "Accept: application/json" \
        -u "$SURREAL_USER:$SURREAL_PASS" \
        -d "$tables_query" \
        "http://$SURREAL_HOST:$SURREAL_PORT/sql")

    # Check for expected tables
    if echo "$response" | grep -q "projects"; then
        log_info "✓ Table 'projects' exists"
    else
        log_warn "✗ Table 'projects' not found"
        return 1
    fi

    if echo "$response" | grep -q "tasks"; then
        log_info "✓ Table 'tasks' exists"
    else
        log_warn "✗ Table 'tasks' not found"
        return 1
    fi

    if echo "$response" | grep -q "artifacts"; then
        log_info "✓ Table 'artifacts' exists"
    else
        log_warn "✗ Table 'artifacts' not found"
        return 1
    fi

    log_info "Schema verification passed"
    return 0
}

# Main execution
main() {
    log_info "SurrealDB Schema Initialization"
    log_info "================================"
    log_info "Host: $SURREAL_HOST:$SURREAL_PORT"
    log_info "Namespace: $SURREAL_NS"
    log_info "Database: $SURREAL_DB"
    log_info "Schema File: $SCHEMA_FILE"
    echo

    # Check if schema file exists
    if [ ! -f "$SCHEMA_FILE" ]; then
        log_error "Schema file not found: $SCHEMA_FILE"
        exit 1
    fi

    # Check SurrealDB connection
    if ! check_surreal_connection; then
        log_error "Failed to connect to SurrealDB"
        exit 1
    fi

    # Apply schema
    if ! apply_schema; then
        log_error "Failed to apply schema"
        exit 1
    fi

    # Verify schema
    if ! verify_schema; then
        log_warn "Schema verification failed (may be incomplete)"
        exit 1
    fi

    log_info ""
    log_info "✅ SurrealDB schema initialization complete"
}

# Run main function
main "$@"
