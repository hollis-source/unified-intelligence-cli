#!/bin/bash
#
# Quick Release Status Check
# Simple, fast status verification

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

VERSION="1.0.0"

echo ""
echo "${BOLD}Release v$VERSION - Quick Status Check${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Check local tag
echo "1. Local tag:"
if git tag -l "v$VERSION" | grep -q "v$VERSION"; then
    echo "   ${GREEN}✓${NC} v$VERSION exists locally"
else
    echo "   ${YELLOW}✗${NC} v$VERSION not found locally"
fi

# 2. Check remote tag
echo ""
echo "2. Remote tag:"
if git ls-remote --tags origin 2>/dev/null | grep -q "v$VERSION"; then
    echo "   ${GREEN}✓${NC} v$VERSION pushed to GitHub"
    TAG_PUSHED=true
else
    echo "   ${YELLOW}✗${NC} v$VERSION not on GitHub"
    TAG_PUSHED=false
fi

# 3. Check PyPI
echo ""
echo "3. PyPI availability:"
if curl -s "https://pypi.org/pypi/unified-intelligence-cli/$VERSION/json" | grep -q "\"version\":"; then
    echo "   ${GREEN}✓${NC} Package available on PyPI"
    PYPI_AVAILABLE=true
else
    echo "   ${YELLOW}⏳${NC} Package not yet on PyPI (workflow still running)"
    PYPI_AVAILABLE=false
fi

# 4. Check GitHub Release
echo ""
echo "4. GitHub Release:"
REPO_URL=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\).git/\1/')
RELEASE_URL="https://github.com/$REPO_URL/releases/tag/v$VERSION"

if curl -s "$RELEASE_URL" 2>/dev/null | grep -q "Release v$VERSION"; then
    echo "   ${GREEN}✓${NC} GitHub Release created"
    RELEASE_CREATED=true
else
    echo "   ${YELLOW}⏳${NC} GitHub Release pending"
    RELEASE_CREATED=false
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Summary
if [ "$PYPI_AVAILABLE" = true ] && [ "$RELEASE_CREATED" = true ]; then
    echo "${GREEN}${BOLD}✓ RELEASE COMPLETE!${NC}"
    echo ""
    echo "Install now:"
    echo "  ${CYAN}pip install unified-intelligence-cli==$VERSION${NC}"
    echo ""
elif [ "$TAG_PUSHED" = true ]; then
    echo "${YELLOW}${BOLD}⏳ WORKFLOW RUNNING${NC}"
    echo ""
    echo "The GitHub Actions workflow is processing the release."
    echo "This typically takes 7-10 minutes."
    echo ""
    echo "Monitor at:"
    echo "  ${CYAN}https://github.com/$REPO_URL/actions${NC}"
    echo ""
    echo "Check again in a few minutes:"
    echo "  ${CYAN}./scripts/check-release.sh${NC}"
    echo ""
else
    echo "${YELLOW}${BOLD}⚠ TAG NOT PUSHED${NC}"
    echo ""
    echo "Push the tag to trigger release:"
    echo "  ${CYAN}git push origin v$VERSION${NC}"
    echo ""
fi
