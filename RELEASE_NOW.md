# Release v1.0.0 NOW - Quick Fix Guide

**Status:** All pre-flight checks passed! ✓  
**Issue:** GitHub token missing `workflow` scope  
**Solution:** Re-authenticate (2 minutes)

---

## Problem

Your GitHub CLI token doesn't have the `workflow` scope needed to trigger GitHub Actions when pushing tags.

**Error:**
```
refusing to allow an OAuth App to create or update workflow 
`.github/workflows/release.yml` without `workflow` scope
```

---

## Solution (2 Steps)

### Step 1: Re-authenticate with Workflow Scope

```bash
./scripts/fix-github-auth.sh
```

**Or manually:**
```bash
gh auth logout
gh auth login --scopes "repo,workflow"
```

When prompted:
1. ✓ Login with web browser (recommended)
2. ✓ Select **both** `repo` and `workflow` scopes
3. ✓ Complete authentication in browser

### Step 2: Run Release Again

```bash
./scripts/release-wrapper.sh
```

That's it!

---

## Alternative: Manual Tag Push

If you prefer to push the tag manually (workflows still work):

```bash
# The workflow file needs to be committed first
git push origin master

# Then create and push tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

The GitHub Actions workflow will trigger automatically when the tag is pushed (regardless of how it's pushed), as long as the workflow file is in the repository.

---

## Why This Happens

GitHub's security model requires explicit permission to trigger workflows. The default `repo` scope allows:
- ✓ Push code
- ✓ Create releases
- ✗ Trigger workflows (requires `workflow` scope)

This is a security feature to prevent accidental workflow execution.

---

## Quick Start

**Fastest path:**
```bash
./scripts/fix-github-auth.sh   # 2 minutes
./scripts/release-wrapper.sh   # 10 minutes
```

**All systems ready!** 🚀

---

## Verification

After re-authenticating, verify scopes:
```bash
gh auth status
```

Should show:
```
✓ Logged in to github.com
✓ Token scopes: repo, workflow
```

---

## Next Steps After Release

1. Monitor GitHub Actions: `gh run list`
2. Verify PyPI: https://pypi.org/project/autonomous-task-agent-dev-orchestration/
3. Test install: `pip install autonomous-task-agent-dev-orchestration`
4. Begin alpha rollout (Week 3-4)

Ready? Run: `./scripts/fix-github-auth.sh`
