#!/bin/bash
#
# Setup automation environment with virtual environment
# This ensures clean, isolated dependencies for release automation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "\n${BOLD}${CYAN}======================================================================${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}======================================================================${NC}\n"
}

print_step() {
    echo -e "${BOLD}${CYAN}▸${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_header "Setup Release Automation Environment"

echo "This script will create a virtual environment for release automation."
echo "This ensures clean, isolated dependencies without affecting system Python."
echo ""

# Check if venv already exists
VENV_DIR="venv-automation"

if [ -d "$VENV_DIR" ]; then
    print_info "Virtual environment already exists: $VENV_DIR"
    
    read -p "Recreate it? [y/N]: " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        print_info "Using existing virtual environment"
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
        exit 0
    fi
fi

# Check Python version
print_step "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
    print_error "Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION (OK)"

# Create virtual environment
print_step "Creating virtual environment..."
if python3 -m venv "$VENV_DIR"; then
    print_success "Virtual environment created: $VENV_DIR"
else
    print_error "Failed to create virtual environment"
    echo ""
    print_info "On Debian/Ubuntu, you may need to install python3-venv:"
    echo "  ${BOLD}sudo apt install python3-venv${NC}"
    echo ""
    print_info "On other systems, ensure python3-venv is available"
    exit 1
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

# Upgrade pip
print_step "Upgrading pip..."
python -m pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install dependencies
print_step "Installing release automation dependencies..."
echo ""
print_info "Installing: pytest, pytest-cov, bandit, build, twine, toml..."

if pip install -r requirements-dev.txt --quiet; then
    print_success "Dependencies installed"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Verify installation
print_step "Verifying installation..."
python -c "import pytest, bandit, build, twine, toml" 2>/dev/null
print_success "All dependencies verified"

echo ""
print_header "Setup Complete!"

echo "Virtual environment created and activated: ${BOLD}$VENV_DIR${NC}"
echo ""
echo "To use the automation scripts:"
echo ""
echo "  1. Activate the virtual environment:"
echo "     ${BOLD}source $VENV_DIR/bin/activate${NC}"
echo ""
echo "  2. Run automation scripts:"
echo "     ${BOLD}python scripts/preflight.py${NC}"
echo "     ${BOLD}python scripts/release.py${NC}"
echo ""
echo "  3. Or use the wrapper (automatically activates):"
echo "     ${BOLD}./scripts/release-wrapper.sh${NC}"
echo ""
echo "  4. To deactivate when done:"
echo "     ${BOLD}deactivate${NC}"
echo ""

print_success "Ready for release automation!"
