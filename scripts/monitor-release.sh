#!/bin/bash
#
# Monitor Release Workflow
#
# Check GitHub Actions workflow status and wait for completion

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

print_header "Monitor Release v$VERSION"

# Get repository info
REPO_URL=$(git remote get-url origin)
if [[ $REPO_URL =~ github.com[:/](.+)\.git ]]; then
    REPO_PATH="${BASH_REMATCH[1]}"
elif [[ $REPO_URL =~ github.com[:/](.+) ]]; then
    REPO_PATH="${BASH_REMATCH[1]}"
else
    print_error "Could not parse GitHub repository URL"
    exit 1
fi

print_info "Repository: $REPO_PATH"
print_info "Tag: $TAG"
echo ""

# Check if tag exists on remote
print_info "Verifying tag on GitHub..."
if git ls-remote --tags origin | grep -q "$TAG"; then
    print_success "Tag $TAG exists on GitHub"
else
    print_error "Tag $TAG not found on GitHub"
    echo ""
    print_info "Push the tag first:"
    echo "  ${BOLD}git push origin $TAG${NC}"
    exit 1
fi

echo ""

# Provide direct links
print_header "GitHub Actions Status"

ACTIONS_URL="https://github.com/$REPO_PATH/actions"
WORKFLOWS_URL="https://github.com/$REPO_PATH/actions/workflows/release.yml"
RELEASE_URL="https://github.com/$REPO_PATH/releases/tag/$TAG"

echo "Check workflow status:"
echo "  ${BOLD}$ACTIONS_URL${NC}"
echo ""
echo "Specific workflow:"
echo "  ${BOLD}$WORKFLOWS_URL${NC}"
echo ""
echo "Expected release (after workflow completes):"
echo "  ${BOLD}$RELEASE_URL${NC}"
echo ""

# Try to get workflow runs via API (may fail due to auth)
print_info "Attempting to check workflow runs..."
echo ""

unset GITHUB_TOKEN  # Avoid token conflicts

if gh run list --workflow=release.yml --limit 1 2>/dev/null; then
    echo ""
    print_info "Use 'gh run watch' to monitor the workflow:"
    echo "  ${BOLD}gh run watch${NC}"
    echo ""
else
    print_warning "Could not fetch workflow runs via CLI"
    echo ""
    print_info "Check workflow status in your browser:"
    echo "  ${BOLD}$ACTIONS_URL${NC}"
    echo ""
fi

# Provide timeline expectations
print_header "Expected Timeline"

echo "The GitHub Actions workflow includes:"
echo ""
echo "  1. Build & Test (Python 3.10, 3.11, 3.12)    ~3-4 minutes"
echo "  2. Publish to PyPI                           ~1-2 minutes"
echo "  3. Build Docker image (multi-arch)           ~2-3 minutes"
echo "  4. Create GitHub Release                     ~30 seconds"
echo ""
echo "  ${BOLD}Total expected time: 7-10 minutes${NC}"
echo ""

print_info "The package will be available on PyPI once the workflow completes:"
echo "  ${BOLD}https://pypi.org/project/unified-intelligence-cli/$VERSION/${NC}"
echo ""

# Wait for workflow
print_info "Waiting for workflow to complete..."
echo ""

# Try to watch workflow
if command -v gh &> /dev/null; then
    read -p "Watch workflow in real-time? [Y/n]: " -r
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        unset GITHUB_TOKEN
        if gh run watch 2>/dev/null; then
            echo ""
            print_success "Workflow completed!"
        else
            print_warning "Could not watch workflow automatically"
            echo ""
            print_info "Monitor manually at:"
            echo "  ${BOLD}$ACTIONS_URL${NC}"
        fi
    fi
else
    print_warning "GitHub CLI not available"
    echo ""
    print_info "Monitor workflow at:"
    echo "  ${BOLD}$ACTIONS_URL${NC}"
fi

echo ""
print_header "Post-Release Verification"

echo "Once the workflow completes, verify:"
echo ""
echo "  1. PyPI:"
echo "     ${BOLD}pip install unified-intelligence-cli==$VERSION${NC}"
echo ""
echo "  2. Docker Hub:"
echo "     ${BOLD}docker pull YOUR_USERNAME/unified-intelligence-cli:$VERSION${NC}"
echo ""
echo "  3. GitHub Release:"
echo "     ${BOLD}$RELEASE_URL${NC}"
echo ""

print_success "Release monitoring complete!"
echo ""
print_info "The workflow is running. Check back in ~10 minutes."
