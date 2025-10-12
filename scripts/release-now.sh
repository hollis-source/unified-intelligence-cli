#!/bin/bash
#
# Complete Release Script with Auto-Retry
#
# This script handles the complete v1.0.0 release including:
# - GitHub authentication check
# - Tag cleanup (if needed)
# - Release execution
# - Retry logic

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

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

VERSION="1.0.0"
TAG="v$VERSION"

print_header "Release v$VERSION - Complete Automation"

# Step 1: Check GitHub authentication scopes
print_info "Checking GitHub CLI authentication..."

if ! gh auth status &> /dev/null; then
    print_error "GitHub CLI not authenticated"
    echo ""
    print_info "Please authenticate first:"
    echo "  ${BOLD}gh auth login --scopes 'repo,workflow'${NC}"
    exit 1
fi

# Check if workflow scope is present
if ! gh auth status 2>&1 | grep -q "workflow"; then
    print_warning "GitHub token missing 'workflow' scope"
    echo ""
    print_info "The 'workflow' scope is required to trigger GitHub Actions."
    echo ""
    read -p "Fix authentication now? [Y/n]: " -r
    
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        if ./scripts/fix-github-auth.sh; then
            print_success "Authentication fixed!"
        else
            print_error "Authentication fix failed"
            exit 1
        fi
    else
        print_warning "Continuing without workflow scope (manual push required)"
    fi
fi

print_success "GitHub CLI authenticated"
echo ""

# Step 2: Check and clean up existing tags
print_info "Checking for existing tags..."

if git tag -l "$TAG" | grep -q "$TAG"; then
    print_warning "Local tag $TAG already exists"
    
    # Check if it exists on remote
    if git ls-remote --tags origin | grep -q "$TAG"; then
        print_error "Tag $TAG already exists on remote"
        echo ""
        print_info "To re-release, you need to delete the remote tag first:"
        echo "  ${BOLD}git push --delete origin $TAG${NC}"
        echo "  ${BOLD}git tag -d $TAG${NC}"
        exit 1
    else
        print_info "Deleting local tag (not on remote)..."
        git tag -d "$TAG"
        print_success "Local tag deleted"
    fi
fi

echo ""

# Step 3: Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    VENV_DIR="venv-automation"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found: $VENV_DIR"
        echo ""
        print_info "Run setup first:"
        echo "  ${BOLD}./scripts/setup-automation-env.sh${NC}"
        exit 1
    fi
    
    print_info "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
fi

echo ""

# Step 4: Quick pre-flight check
print_info "Running quick pre-flight check..."
echo ""

if python scripts/preflight.py --version "$VERSION"; then
    print_success "Pre-flight checks passed!"
else
    print_error "Pre-flight checks failed"
    echo ""
    print_info "Fix issues and try again"
    exit 1
fi

echo ""

# Step 5: Verify secrets
print_info "Verifying GitHub secrets..."

if python scripts/setup-secrets.py --verify-only --non-interactive; then
    print_success "All secrets configured"
else
    print_error "Some secrets are missing"
    echo ""
    print_info "Configure secrets:"
    echo "  ${BOLD}python scripts/setup-secrets.py${NC}"
    exit 1
fi

echo ""

# Step 6: Execute release
print_header "Executing Release"

if python scripts/release.py --version "$VERSION"; then
    print_success "Release completed successfully!"
    echo ""
    
    print_header "Release Summary"
    echo ""
    echo "  Version:     ${BOLD}$VERSION${NC}"
    echo "  Tag:         ${BOLD}$TAG${NC}"
    echo "  Status:      ${GREEN}✓ RELEASED${NC}"
    echo ""
    
    print_info "Verify deployment:"
    echo "  PyPI:        ${BOLD}https://pypi.org/project/unified-intelligence-cli/$VERSION/${NC}"
    echo "  GitHub:      ${BOLD}https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\).git/\1/')/releases/tag/$TAG${NC}"
    echo ""
    
    print_info "Test installation:"
    echo "  ${BOLD}pip install unified-intelligence-cli==$VERSION${NC}"
    echo ""
    
    print_success "🎉 Release v$VERSION complete! 🎉"
    echo ""
    
else
    print_error "Release failed"
    echo ""
    print_info "Check the output above for details"
    print_info "You can also check GitHub Actions:"
    echo "  ${BOLD}gh run list${NC}"
    exit 1
fi
