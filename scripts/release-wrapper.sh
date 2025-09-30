#!/bin/bash
#
# Release Wrapper Script
# Automatically handles virtual environment setup and activation
# Then runs the complete release automation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Check if we're already in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    VENV_DIR="venv-automation"
    
    # Check if venv exists
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found: $VENV_DIR"
        echo ""
        print_info "Run setup first:"
        echo "  ${BOLD}./scripts/setup-automation-env.sh${NC}"
        exit 1
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment: $VENV_DIR"
    source "$VENV_DIR/bin/activate"
fi

# Run the automation script
exec ./scripts/automate-release.sh "$@"
