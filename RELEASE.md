# Release Process

This document describes how to create a new release of Unified Intelligence CLI.

## Prerequisites

### GitHub Secrets

Configure the following secrets in GitHub repository settings (Settings → Secrets → Actions):

1. **PYPI_API_TOKEN**: PyPI API token for package publishing
   - Create at: https://pypi.org/manage/account/token/
   - Scope: "Entire account" or specific to this project
   
2. **DOCKER_USERNAME**: Docker Hub username
3. **DOCKER_PASSWORD**: Docker Hub access token or password
   - Create token at: https://hub.docker.com/settings/security

### Local Setup

Ensure you have:
- Git with proper authentication
- Python 3.10+ installed
- Docker installed (for local testing)

## Automated Release (Recommended)

The release process is automated via GitHub Actions when you push a version tag.

### Step 1: Update Version

Update version in `pyproject.toml`:
```toml
[project]
version = "1.0.1"  # Increment version
```

### Step 2: Commit Changes

```bash
git add pyproject.toml
git commit -m "chore: bump version to 1.0.1"
git push origin master
```

### Step 3: Create and Push Tag

```bash
# Create annotated tag
git tag -a v1.0.1 -m "Release version 1.0.1"

# Push tag to trigger release workflow
git push origin v1.0.1
```

### Step 4: Monitor Release

1. Go to Actions tab in GitHub
2. Watch "Release to PyPI and Docker Hub" workflow
3. Workflow will:
   - Run tests on Python 3.10, 3.11, 3.12
   - Build and publish to PyPI
   - Build and publish Docker image (multi-arch)
   - Create GitHub Release with changelog

### Step 5: Verify Release

**PyPI:**
```bash
pip install unified-intelligence-cli==1.0.1
ui-cli --help
```

**Docker:**
```bash
docker pull username/unified-intelligence-cli:1.0.1
docker run username/unified-intelligence-cli:1.0.1 --help
```

**GitHub:**
- Check Releases page for new release
- Verify changelog is populated

## Manual Release (Fallback)

If automated release fails, you can publish manually.

### Build Package

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*
```

### Publish to PyPI

```bash
# Upload to PyPI (requires API token)
twine upload dist/*
```

### Build Docker Image

```bash
# Build multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 \
  -t username/unified-intelligence-cli:1.0.1 \
  -t username/unified-intelligence-cli:latest \
  --push .
```

### Create GitHub Release

```bash
# Install GitHub CLI
gh --version

# Create release
gh release create v1.0.1 \
  --title "Release 1.0.1" \
  --notes "Release notes here" \
  dist/*
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

## Release Checklist

Before releasing:

- [ ] All tests passing locally (`pytest tests/`)
- [ ] Coverage at or above 85% (`pytest --cov`)
- [ ] No security vulnerabilities (`bandit -r src/`)
- [ ] CHANGELOG updated (if maintained separately)
- [ ] Version bumped in `pyproject.toml`
- [ ] Documentation updated (if needed)
- [ ] Breaking changes documented

## Rollback

If a release has issues:

### PyPI Rollback

```bash
# You cannot delete PyPI releases, but you can yank them
twine upload --repository pypi dist/*
```

Note: PyPI doesn't allow deleting versions, only "yanking" (hiding from pip install).

### Docker Rollback

```bash
# Re-tag previous version as latest
docker pull username/unified-intelligence-cli:1.0.0
docker tag username/unified-intelligence-cli:1.0.0 username/unified-intelligence-cli:latest
docker push username/unified-intelligence-cli:latest
```

### GitHub Rollback

```bash
# Delete release and tag
gh release delete v1.0.1 --yes
git push --delete origin v1.0.1
git tag -d v1.0.1
```

## Troubleshooting

### "Permission denied" on PyPI upload

- Verify PYPI_API_TOKEN secret is set correctly
- Ensure token has "upload" permissions
- Check if package name is available on PyPI

### Docker push fails

- Verify DOCKER_USERNAME and DOCKER_PASSWORD secrets
- Check Docker Hub repository exists
- Ensure Buildx is configured for multi-arch

### GitHub Actions workflow fails

- Check Actions logs for specific error
- Verify all secrets are configured
- Ensure branch protection rules allow tag pushes

## First-Time Setup

### PyPI Setup

1. Create PyPI account: https://pypi.org/account/register/
2. Verify email
3. Create API token: https://pypi.org/manage/account/token/
4. Add token as GitHub secret: `PYPI_API_TOKEN`

### Docker Hub Setup

1. Create Docker Hub account: https://hub.docker.com/signup
2. Create repository: `unified-intelligence-cli`
3. Create access token: https://hub.docker.com/settings/security
4. Add credentials as GitHub secrets:
   - `DOCKER_USERNAME`: your-dockerhub-username
   - `DOCKER_PASSWORD`: your-access-token

### Test Release

Before v1.0.0, test the release process:

```bash
# Test with a pre-release version
git tag -a v0.1.0-alpha.1 -m "Test release"
git push origin v0.1.0-alpha.1
```

Monitor the workflow and verify everything works.

## Post-Release

After successful release:

1. Update project README badges (if version badges used)
2. Announce release (social media, mailing list, etc.)
3. Monitor GitHub issues for bug reports
4. Plan next release based on feedback

---

**Last Updated:** 2025-09-30
**Release Automation:** GitHub Actions
**Current Version:** 1.0.0
