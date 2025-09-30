#!/bin/bash
#
# Automated Release Master Script
#
# This script orchestrates the entire release process:
# 1. Installs dependencies
# 2. Runs pre-flight checks
# 3. Verifies/sets up secrets
# 4. Executes release
# 5. Verifies deployment
#
# Usage:
#   ./scripts/automate-release.sh                    # Interactive mode
#   ./scripts/automate-release.sh --auto             # Fully automated
#   ./scripts/automate-release.sh --version 1.0.0    # Specify version

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Parse arguments
AUTO_MODE=false
VERSION=""
DOCKER_USERNAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --docker-username)
            DOCKER_USERNAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--auto] [--version X.Y.Z] [--docker-username USERNAME]"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "\n${BOLD}${CYAN}======================================================================${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}======================================================================${NC}\n"
}

print_step() {
    echo -e "\n${BOLD}${BLUE}▸ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

confirm() {
    if [ "$AUTO_MODE" = true ]; then
        return 0
    fi
    
    local prompt="$1"
    local default="${2:-n}"
    
    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" -r
    REPLY=${REPLY:-$default}
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Welcome
print_header "Unified Intelligence CLI - Automated Release"

echo "This script will guide you through the complete release process."
echo ""
echo "Steps:"
echo "  1. Install/verify dependencies"
echo "  2. Run pre-flight checks"
echo "  3. Setup/verify GitHub secrets"
echo "  4. Create and push release tag"
echo "  5. Monitor GitHub Actions workflow"
echo "  6. Verify deployment"
echo ""

if [ "$AUTO_MODE" = false ]; then
    if ! confirm "Ready to proceed?" "y"; then
        print_info "Release cancelled"
        exit 0
    fi
fi

# Step 1: Check dependencies
print_header "Step 1: Check Dependencies"

print_step "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python installed: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

print_step "Checking Git..."
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    print_success "Git installed: $GIT_VERSION"
else
    print_error "Git not found. Please install Git"
    exit 1
fi

print_step "Checking GitHub CLI..."
if command -v gh &> /dev/null; then
    GH_VERSION=$(gh --version | head -n1)
    print_success "GitHub CLI installed: $GH_VERSION"
else
    print_error "GitHub CLI not found. Please install: https://cli.github.com/"
    exit 1
fi

print_step "Checking GitHub CLI authentication..."
if gh auth status &> /dev/null; then
    print_success "GitHub CLI authenticated"
else
    print_error "GitHub CLI not authenticated. Please run: gh auth login"
    exit 1
fi

print_step "Installing/updating Python dependencies..."
if python3 -m pip install -r requirements-dev.txt --quiet; then
    print_success "Dependencies installed"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Step 2: Pre-flight checks
print_header "Step 2: Pre-Flight Checks"

print_info "Running automated checks (tests, coverage, security, build)..."
print_info "This may take 1-2 minutes..."
echo ""

VERSION_ARG=""
if [ -n "$VERSION" ]; then
    VERSION_ARG="--version $VERSION"
fi

if python3 scripts/preflight.py $VERSION_ARG; then
    print_success "All pre-flight checks passed!"
else
    print_error "Pre-flight checks failed"
    
    if [ "$AUTO_MODE" = false ]; then
        if ! confirm "Continue anyway? (NOT RECOMMENDED)" "n"; then
            exit 1
        fi
    else
        exit 1
    fi
fi

# Step 3: Setup/verify secrets
print_header "Step 3: GitHub Secrets"

print_info "Verifying GitHub repository secrets..."
echo ""

if python3 scripts/setup-secrets.py --verify-only; then
    print_success "All required secrets configured!"
else
    print_warning "Some secrets are missing"
    
    if [ "$AUTO_MODE" = false ]; then
        if confirm "Do you want to set up secrets now?" "y"; then
            echo ""
            python3 scripts/setup-secrets.py
        else
            print_error "Cannot proceed without secrets. Exiting."
            exit 1
        fi
    else
        print_error "Cannot proceed in auto mode without secrets configured"
        print_info "Run: python3 scripts/setup-secrets.py"
        exit 1
    fi
fi

# Step 4: Release
print_header "Step 4: Execute Release"

if [ "$AUTO_MODE" = false ]; then
    echo ""
    print_warning "This will create a release tag and trigger GitHub Actions!"
    print_warning "Once started, this cannot be easily undone."
    echo ""
    
    if ! confirm "Proceed with release?" "y"; then
        print_info "Release cancelled"
        exit 0
    fi
fi

echo ""
print_info "Starting release automation..."
echo ""

RELEASE_ARGS=""
if [ "$AUTO_MODE" = true ]; then
    RELEASE_ARGS="--auto"
fi
if [ -n "$VERSION" ]; then
    RELEASE_ARGS="$RELEASE_ARGS --version $VERSION"
fi

if python3 scripts/release.py $RELEASE_ARGS; then
    print_success "Release process completed!"
else
    print_error "Release process failed"
    print_info "Check the output above for details"
    print_info "You can also check GitHub Actions: gh run list"
    exit 1
fi

# Step 5: Verify deployment
print_header "Step 5: Verify Deployment"

if [ "$AUTO_MODE" = false ]; then
    if ! confirm "Run deployment verification?" "y"; then
        print_info "Skipping verification. You can run it later:"
        print_info "  python3 scripts/verify-release.py"
        exit 0
    fi
fi

echo ""
print_info "Verifying deployment on PyPI, Docker Hub, and GitHub..."
print_info "This may take 1-2 minutes..."
echo ""

VERIFY_ARGS=""
if [ -n "$VERSION" ]; then
    VERIFY_ARGS="--version $VERSION"
fi
if [ -n "$DOCKER_USERNAME" ]; then
    VERIFY_ARGS="$VERIFY_ARGS --docker-username $DOCKER_USERNAME"
fi

if python3 scripts/verify-release.py $VERIFY_ARGS; then
    print_success "Deployment verified successfully!"
else
    print_warning "Some verifications failed"
    print_info "Check the output above for details"
fi

# Done!
print_header "Release Complete!"

echo "Next steps:"
echo ""
echo "  1. Test installation:"
echo "     ${BOLD}pip install unified-intelligence-cli${NC}"
echo ""
echo "  2. Verify package works:"
echo "     ${BOLD}ui-cli --help${NC}"
echo ""
echo "  3. Update documentation (if needed)"
echo ""
echo "  4. Announce the release"
echo ""
echo "  5. Begin alpha rollout (Week 3-4)"
echo "     - Recruit 10 alpha users"
echo "     - Collect feedback"
echo "     - Iterate based on data"
echo ""

print_success "Automated release process completed successfully!"
echo ""
