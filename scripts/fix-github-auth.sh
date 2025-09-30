#!/bin/bash
#
# Fix GitHub CLI Authentication with Workflow Scope
#
# The release automation requires 'workflow' scope to trigger
# GitHub Actions workflows when pushing tags.

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

print_header "Fix GitHub CLI Authentication"

echo "The release automation failed because your GitHub token doesn't have"
echo "the 'workflow' scope required to trigger GitHub Actions workflows."
echo ""
echo "We need to re-authenticate with the correct scopes."
echo ""

print_info "Current authentication status:"
gh auth status 2>&1 | grep -E "(Logged in|Token:|Scopes:)" || true
echo ""

print_warning "You will be prompted to authenticate again."
echo ""
echo "When asked for scopes, make sure to include:"
echo "  - ${BOLD}repo${NC} (full repository access)"
echo "  - ${BOLD}workflow${NC} (workflow management)"
echo ""

read -p "Ready to re-authenticate? [Y/n]: " -r
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
    print_info "Authentication cancelled"
    exit 0
fi

echo ""
print_info "Logging out current session..."
gh auth logout 2>/dev/null || true

echo ""
print_info "Starting new authentication..."
echo ""
print_warning "IMPORTANT: When prompted, select:"
echo "  1. Login with a web browser (recommended)"
echo "  2. Choose: ${BOLD}repo${NC} and ${BOLD}workflow${NC} scopes"
echo ""

# Authenticate with required scopes
if gh auth login --scopes "repo,workflow"; then
    echo ""
    print_success "Authentication successful!"
    echo ""
    
    print_info "New authentication status:"
    gh auth status
    echo ""
    
    print_success "GitHub CLI is now configured with workflow scope!"
    echo ""
    print_info "You can now run the release automation:"
    echo "  ${BOLD}./scripts/release-wrapper.sh${NC}"
    echo ""
else
    echo ""
    print_error "Authentication failed"
    echo ""
    print_info "You can try again manually:"
    echo "  ${BOLD}gh auth login --scopes 'repo,workflow'${NC}"
    echo ""
    exit 1
fi
