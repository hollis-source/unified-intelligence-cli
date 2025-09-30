# Release Automation Scripts

Comprehensive CLI tools for automating the release process, following Clean Architecture principles.

## Architecture

```
scripts/
├── lib/                          # Core library (Clean Architecture)
│   ├── __init__.py
│   ├── entities.py               # Domain entities (Check, Release, Secret)
│   ├── adapters.py               # External service adapters (Git, GitHub, PyPI, Test)
│   ├── usecases.py               # Business logic (RunPreflightChecks, CreateReleaseTag, etc.)
│   └── ui.py                     # UI utilities (colors, prompts, progress)
├── preflight.py                  # Pre-flight checks CLI
├── setup-secrets.py              # GitHub secrets setup CLI
├── release.py                    # Main release orchestrator
├── verify-release.py             # Post-release verification
└── README.md                     # This file
```

### Clean Architecture Layers

1. **Entities** (`lib/entities.py`): Core business objects
   - `Check`: Represents a single pre-release check
   - `Release`: Represents a software release
   - `Secret`: Represents a configuration secret

2. **Use Cases** (`lib/usecases.py`): Application-specific business rules
   - `RunPreflightChecks`: Execute all pre-release checks
   - `CreateReleaseTag`: Create and push git tag
   - `VerifyDeployment`: Verify package deployment
   - `SetupSecrets`: Configure GitHub repository secrets

3. **Adapters** (`lib/adapters.py`): External service interfaces
   - `GitAdapter`: Git operations
   - `GitHubAdapter`: GitHub CLI operations
   - `TestAdapter`: Test execution (pytest, bandit)
   - `BuildAdapter`: Package building

4. **UI** (`lib/ui.py`): Presentation layer
   - Pretty printing, colors, progress indicators
   - User prompts and confirmations

## Scripts

### 1. preflight.py - Pre-Flight Checks

Run all automated checks before release:

```bash
# Run checks for version in pyproject.toml
python scripts/preflight.py

# Run checks for specific version
python scripts/preflight.py --version 1.0.0

# Verbose output
python scripts/preflight.py --verbose
```

**Checks performed:**
- ✓ Working directory is clean
- ✓ All tests pass
- ✓ Coverage ≥ 85%
- ✓ No security issues (bandit)
- ✓ Package builds successfully
- ✓ Package passes validation (twine)
- ✓ GitHub CLI authenticated (optional)

### 2. setup-secrets.py - GitHub Secrets Setup

Interactive setup for GitHub repository secrets:

```bash
# Interactive mode (recommended)
python scripts/setup-secrets.py

# Verify existing secrets only
python scripts/setup-secrets.py --verify-only

# Non-interactive mode
python scripts/setup-secrets.py --non-interactive
```

**Required secrets:**
- `PYPI_API_TOKEN`: PyPI API token (https://pypi.org/manage/account/token/)
- `DOCKER_USERNAME`: Docker Hub username
- `DOCKER_PASSWORD`: Docker Hub access token (https://hub.docker.com/settings/security)

**Prerequisites:**
- GitHub CLI (`gh`) installed and authenticated
- Run: `gh auth login`

### 3. release.py - Main Release Orchestrator

Orchestrates the entire release process:

```bash
# Interactive mode (recommended)
python scripts/release.py

# Specify version
python scripts/release.py --version 1.0.0

# Fully automated (no prompts)
python scripts/release.py --auto

# Skip certain steps (not recommended)
python scripts/release.py --skip-preflight
python scripts/release.py --skip-secrets-check
```

**Release process:**
1. **Pre-flight checks**: Run all automated tests and validations
2. **Verify secrets**: Ensure GitHub secrets are configured
3. **Create tag**: Create and push git tag (triggers CI/CD)
4. **Monitor workflow**: Watch GitHub Actions workflow
5. **Verify deployment**: Check PyPI, Docker Hub, GitHub Releases

### 4. verify-release.py - Post-Release Verification

Verify that the release was successfully deployed:

```bash
# Verify version in pyproject.toml
python scripts/verify-release.py

# Verify specific version
python scripts/verify-release.py --version 1.0.0

# Verify with Docker check
python scripts/verify-release.py --docker-username YOUR_USERNAME

# Skip installation test
python scripts/verify-release.py --skip-installation-test
```

**Verifications:**
- ✓ Package available on PyPI
- ✓ Docker image available on Docker Hub
- ✓ GitHub Release created
- ✓ Package installs successfully (in clean venv)

## Quick Start

### First-Time Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Authenticate GitHub CLI:**
   ```bash
   gh auth login
   ```

3. **Setup secrets:**
   ```bash
   python scripts/setup-secrets.py
   ```

### Release a New Version

1. **Update version in `pyproject.toml`:**
   ```toml
   [project]
   version = "1.0.1"  # Increment version
   ```

2. **Commit changes:**
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 1.0.1"
   git push origin master
   ```

3. **Run release automation:**
   ```bash
   python scripts/release.py
   ```

4. **Verify deployment:**
   ```bash
   python scripts/verify-release.py --docker-username YOUR_USERNAME
   ```

That's it! The scripts handle:
- Pre-flight checks
- Tag creation and pushing
- GitHub Actions workflow monitoring
- Deployment verification

## SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each adapter has one responsibility (Git, GitHub, Test, Build)
- Each use case has one business rule
- Each script has one CLI function

### Open-Closed Principle (OCP)
- Adapters can be extended without modifying use cases
- New checks can be added without changing check execution logic

### Liskov Substitution Principle (LSP)
- `CommandExecutor` abstraction allows any executor implementation
- Adapters can be substituted with mocks for testing

### Interface Segregation Principle (ISP)
- Small, focused interfaces (GitAdapter, TestAdapter, etc.)
- Use cases depend only on methods they need

### Dependency Inversion Principle (DIP)
- High-level modules (use cases) depend on abstractions (adapters)
- Adapters can be injected for testing or alternative implementations

## Error Handling

All scripts use explicit error handling:

- Return codes: 0 (success), 1 (failure)
- Colored output: Green (success), Red (error), Yellow (warning)
- Descriptive error messages
- Failed checks show error details

## Testing

The architecture supports easy testing:

```python
from scripts.lib.adapters import SubprocessExecutor, GitAdapter
from scripts.lib.entities import Release
from scripts.lib.usecases import CreateReleaseTag

# Mock executor for testing
class MockExecutor(SubprocessExecutor):
    def run(self, cmd, capture=True):
        # Mock implementation
        return 0, "success", ""

# Test with mock
git = GitAdapter(executor=MockExecutor())
use_case = CreateReleaseTag(git)
release = Release(version="1.0.0", tag_name="v1.0.0")
result = use_case.execute(release)
```

## Dependencies

Required Python packages:
- `toml`: Read pyproject.toml
- `pytest`: Test execution
- `pytest-cov`: Coverage measurement
- `bandit`: Security scanning
- `build`: Package building
- `twine`: Package validation

Required CLI tools:
- `git`: Git operations
- `gh`: GitHub CLI (https://cli.github.com/)
- `docker`: Docker operations (optional, for Docker verification)

## Troubleshooting

### "GitHub CLI not authenticated"

```bash
gh auth login
```

### "Failed to create tag: tag already exists"

Delete the tag and try again:
```bash
git tag -d v1.0.0
git push --delete origin v1.0.0
```

### "Secrets not set"

Run the secrets setup script:
```bash
python scripts/setup-secrets.py
```

### "Tests failed" during pre-flight

Fix the failing tests first:
```bash
pytest tests/ -v
```

### "Coverage below 85%"

Increase test coverage:
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html to see coverage details
```

## Advanced Usage

### Custom Check Implementation

Add custom checks by extending `RunPreflightChecks`:

```python
# In lib/usecases.py
checks.append(Check("custom_check", "My custom check", required=True))

# In execute() method
elif check.name == "custom_check":
    # Your custom check logic
    if custom_condition():
        check.mark_passed()
    else:
        check.mark_failed("Custom check failed")
```

### Integration with CI/CD

Use in CI/CD pipelines:

```yaml
# .github/workflows/pre-release-check.yml
- name: Run Pre-Flight Checks
  run: python scripts/preflight.py
```

### Non-Interactive Automation

For fully automated releases:

```bash
# Automated release (requires all secrets configured)
python scripts/release.py --auto --version 1.0.0
```

## Support

For issues or questions:
- Check script output for detailed error messages
- Review GitHub Actions logs: `gh run list`
- Consult main documentation: [RELEASE.md](../RELEASE.md)

---

**Last Updated:** 2025-09-30
**Architecture:** Clean Architecture + SOLID Principles
**Language:** Python 3.10+
