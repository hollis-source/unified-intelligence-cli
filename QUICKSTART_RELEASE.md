# Quick Start: Release v1.0.0

**2-Step Process to Release** (with proper virtual environment setup)

---

## Why Virtual Environment?

The automation scripts use a **virtual environment** to ensure:
- ✓ Clean, isolated dependencies
- ✓ No conflicts with system Python packages
- ✓ Reproducible environment
- ✓ No root/sudo required
- ✓ Best practice for Python development

This is especially important on Debian/Ubuntu systems where system Python is protected.

---

## Quick Release (2 Steps)

### Step 1: Setup Automation Environment (One-time)

```bash
./scripts/setup-automation-env.sh
```

This creates `venv-automation/` with all required dependencies.

**What it does:**
- Creates isolated Python virtual environment
- Installs pytest, pytest-cov, bandit, build, twine, toml
- Verifies all dependencies
- Takes ~1 minute

### Step 2: Run Release Automation

```bash
./scripts/release-wrapper.sh
```

This automatically:
- Activates the virtual environment
- Runs the complete release process
- Handles everything end-to-end

**What it does:**
- Pre-flight checks (tests, coverage, security, build)
- GitHub secrets verification/setup
- Tag creation and push
- GitHub Actions monitoring
- Deployment verification

---

## Alternative: Manual Activation

If you prefer manual control:

```bash
# Activate virtual environment
source venv-automation/bin/activate

# Run automation
./scripts/automate-release.sh

# When done
deactivate
```

---

## Alternative: Step-by-Step Release

For more control, run individual scripts:

```bash
# Activate venv first
source venv-automation/bin/activate

# Step 1: Pre-flight checks
python scripts/preflight.py

# Step 2: Setup secrets (first time only)
python scripts/setup-secrets.py

# Step 3: Execute release
python scripts/release.py

# Step 4: Verify deployment
python scripts/verify-release.py

# Deactivate when done
deactivate
```

---

## Troubleshooting

### "python3-venv not found"

**On Debian/Ubuntu:**
```bash
sudo apt install python3-venv
```

**On RHEL/CentOS:**
```bash
sudo yum install python3-venv
```

**On macOS (Homebrew):**
```bash
brew install python@3.12
```

### "Virtual environment not found"

Run setup first:
```bash
./scripts/setup-automation-env.sh
```

### "GitHub CLI not authenticated"

```bash
gh auth login
```

### "Secrets not configured"

The automation will prompt you. Or run:
```bash
source venv-automation/bin/activate
python scripts/setup-secrets.py
```

---

## Complete Example Session

Here's a complete example from scratch:

```bash
# 1. Setup automation environment (one-time)
./scripts/setup-automation-env.sh

# Output:
# ======================================================================
#   Setup Release Automation Environment
# ======================================================================
# 
# ✓ Python 3.12.3 (OK)
# ✓ Virtual environment created: venv-automation
# ✓ Virtual environment activated
# ✓ pip upgraded
# ✓ Dependencies installed
# ✓ All dependencies verified
# 
# ======================================================================
#   Setup Complete!
# ======================================================================

# 2. Run release (uses venv automatically)
./scripts/release-wrapper.sh

# Output:
# ℹ Activating virtual environment: venv-automation
# 
# ======================================================================
#   Autonomous Task-Agent Dev Orchestration (ATADO) - Automated Release
# ======================================================================
# 
# ✓ Python installed: Python 3.12.3
# ✓ Git installed: git version 2.43.0
# ✓ GitHub CLI installed: gh version 2.62.0
# ✓ GitHub CLI authenticated
# ✓ pip is available
# ✓ Dependencies installed
# 
# ======================================================================
#   Step 2: Pre-Flight Checks
# ======================================================================
# 
# [Runs all checks...]
# 
# ✓ All pre-flight checks passed!
# 
# [Continues with release...]
```

---

## What Gets Created

After setup, you'll have:

```
project/
├── venv-automation/          # Virtual environment (gitignored)
│   ├── bin/
│   │   ├── python
│   │   ├── pip
│   │   ├── pytest
│   │   └── ...
│   └── lib/
│       └── python3.12/
│           └── site-packages/
└── scripts/
    ├── setup-automation-env.sh    # Setup script
    ├── release-wrapper.sh         # Wrapper (auto-activates venv)
    └── automate-release.sh        # Main automation
```

The `venv-automation/` directory:
- Is **NOT** committed to git (in .gitignore)
- Is local to your machine
- Can be recreated anytime with `setup-automation-env.sh`
- Is separate from any project venv

---

## Summary: Fastest Path to Release

**First time:**
```bash
./scripts/setup-automation-env.sh   # One-time setup (~1 min)
./scripts/release-wrapper.sh        # Release (~10 min)
```

**Subsequent releases:**
```bash
./scripts/release-wrapper.sh        # Just this! (~10 min)
```

**That's it!** The scripts handle everything else automatically.

---

## Next Steps After Release

Once the release completes:

1. ✓ Verify on PyPI: https://pypi.org/project/autonomous-task-agent-dev-orchestration/
2. ✓ Test installation: `pip install autonomous-task-agent-dev-orchestration`
3. ✓ Verify Docker Hub (if applicable)
4. ✓ Check GitHub Release: https://github.com/YOUR_USER/autonomous-task-agent-dev-orchestration/releases
5. ✓ Begin alpha rollout (Week 3-4)

---

**Ready to release v1.0.0!** 🚀

Run: `./scripts/setup-automation-env.sh`
