#!/bin/bash
#
# Fix Release - Push commits and retrigger workflow
#

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

print_header "Fix Release - Push Commits and Trigger Workflow"

echo "Issue detected: 31 commits (including workflow file) not pushed to GitHub"
echo "This is why GitHub Actions didn't trigger."
echo ""

# Step 1: Check status
UNPUSHED=$(git log --oneline origin/master..master | wc -l)
print_info "Commits to push: $UNPUSHED"
echo ""

if [ "$UNPUSHED" -eq 0 ]; then
    print_success "All commits already pushed"
else
    print_warning "Need to push $UNPUSHED commits including the workflow file"
fi

echo ""
read -p "Push all commits to GitHub now? [Y/n]: " -r
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
    print_info "Cancelled"
    exit 0
fi

# Step 2: Push commits
print_info "Pushing commits to origin/master..."
echo ""

if git push origin master; then
    print_success "Commits pushed successfully!"
else
    print_error "Failed to push commits"
    exit 1
fi

echo ""

# Step 3: Check if tag needs to be re-pushed
print_info "Checking tag v1.0.0..."

# Delete remote tag and re-push to trigger workflow
print_warning "Need to re-push tag to trigger GitHub Actions workflow"
echo ""
read -p "Delete and re-push tag v1.0.0 to trigger workflow? [Y/n]: " -r
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    
    print_info "Deleting remote tag v1.0.0..."
    if git push --delete origin v1.0.0 2>/dev/null; then
        print_success "Remote tag deleted"
    else
        print_warning "Remote tag might not exist or already deleted"
    fi
    
    echo ""
    print_info "Pushing tag v1.0.0..."
    if git push origin v1.0.0; then
        print_success "Tag pushed successfully!"
        echo ""
        print_success "GitHub Actions workflow should now trigger!"
    else
        print_error "Failed to push tag"
        exit 1
    fi
fi

echo ""
print_header "Workflow Triggered!"

REPO_URL=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\).git/\1/')

echo "Monitor the workflow:"
echo "  ${CYAN}https://github.com/$REPO_URL/actions${NC}"
echo ""
echo "The workflow will:"
echo "  1. Build & test (3-4 min)"
echo "  2. Publish to PyPI (1-2 min)"
echo "  3. Build Docker image (2-3 min)"
echo "  4. Create GitHub Release (30 sec)"
echo ""
echo "Total time: ~7-10 minutes"
echo ""

print_info "Check status periodically:"
echo "  ${BOLD}./scripts/check-release.sh${NC}"
echo ""

print_success "Release workflow initiated!"
