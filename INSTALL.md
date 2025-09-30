# Installation Guide

This guide provides detailed instructions for installing Unified Intelligence CLI using multiple methods.

## Table of Contents

- [Quick Start](#quick-start)
- [Method 1: PyPI Installation (Recommended)](#method-1-pypi-installation-recommended)
- [Method 2: Docker Installation](#method-2-docker-installation)
- [Method 3: Development Installation](#method-3-development-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Quick Start

**For most users (PyPI):**
```bash
pip install unified-intelligence-cli
ui-cli --help
```

**For Docker users:**
```bash
docker pull username/unified-intelligence-cli:latest
docker run --rm -e XAI_API_KEY=your_key username/unified-intelligence-cli:latest --help
```

## Requirements

- **Python:** 3.10, 3.11, or 3.12
- **OS:** Linux, macOS, Windows (WSL recommended)
- **API Key:** xAI API key (get from https://x.ai/)

## Method 1: PyPI Installation (Recommended)

### Prerequisites

Ensure Python 3.10+ is installed:
```bash
python --version  # Should show 3.10 or higher
```

### Installation

**Option A: User Installation (Recommended)**
```bash
pip install --user unified-intelligence-cli
```

**Option B: Virtual Environment (Best Practice)**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install package
pip install unified-intelligence-cli
```

**Option C: System-Wide Installation**
```bash
pip install unified-intelligence-cli
```

### Verify Installation

```bash
# Check installation
ui-cli --version

# Run help
ui-cli --help

# Alternative command name
unified-intelligence-cli --help
```

### Upgrade

```bash
pip install --upgrade unified-intelligence-cli
```

### Uninstall

```bash
pip uninstall unified-intelligence-cli
```

## Method 2: Docker Installation

### Prerequisites

- Docker 20.10+ installed ([Get Docker](https://docs.docker.com/get-docker/))
- xAI API key

### Pull Image

```bash
docker pull username/unified-intelligence-cli:latest
```

### Run Container

**Basic Usage:**
```bash
docker run --rm \
  -e XAI_API_KEY=your_api_key_here \
  username/unified-intelligence-cli:latest \
  --help
```

**With Environment File:**
```bash
# Create .env file
cat > .env <<EOF
XAI_API_KEY=your_api_key_here
UI_CLI_PROVIDER=grok
EOF

# Run with env file
docker run --rm \
  --env-file .env \
  username/unified-intelligence-cli:latest \
  "Analyze the current state of AI"
```

**With Volume Mount (for file operations):**
```bash
docker run --rm \
  -e XAI_API_KEY=your_api_key_here \
  -v $(pwd)/workspace:/workspace \
  -w /workspace \
  username/unified-intelligence-cli:latest \
  "Create a plan"
```

### Docker Compose (Development)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  ui-cli:
    image: username/unified-intelligence-cli:latest
    environment:
      - XAI_API_KEY=${XAI_API_KEY}
    volumes:
      - ./workspace:/workspace
    working_dir: /workspace
    command: ["--help"]
```

Run with:
```bash
docker-compose run --rm ui-cli "Your task here"
```

## Method 3: Development Installation

### Prerequisites

- Git
- Python 3.10+
- Virtual environment tool (venv)

### Clone Repository

```bash
git clone https://github.com/yourusername/unified-intelligence-cli.git
cd unified-intelligence-cli
```

### Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Install Dependencies

**Production dependencies:**
```bash
pip install -r requirements.txt
```

**Development dependencies (for testing):**
```bash
pip install -r requirements-dev.txt
```

**Install in editable mode:**
```bash
pip install -e .
```

### Verify Development Installation

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=term

# Run CLI
ui-cli --help

# Or run directly
python -m src.main --help
```

## Configuration

### Environment Variables

Create `.env` file in your working directory:

```bash
# Required: xAI API Key
XAI_API_KEY=your_api_key_here

# Optional: Provider selection (default: grok)
UI_CLI_PROVIDER=grok

# Optional: Model selection (default: grok-beta)
UI_CLI_MODEL=grok-beta

# Optional: Debug mode
UI_CLI_DEBUG=false
```

### Get API Key

1. Go to https://x.ai/
2. Sign up or log in
3. Navigate to API section
4. Generate new API key
5. Copy key to `.env` file

**Security Note:** Never commit `.env` files to version control. The repository includes `.env` in `.gitignore`.

## Verification

### Test Basic Functionality

**1. Help Command:**
```bash
ui-cli --help
```
Expected: Usage information and available options

**2. Version Check:**
```bash
ui-cli --version
```
Expected: Version number (e.g., 1.0.0)

**3. Simple Task:**
```bash
export XAI_API_KEY=your_key_here
ui-cli "What is 2+2?"
```
Expected: AI response with calculation

**4. Multi-Task:**
```bash
ui-cli "Task 1: Explain AI" "Task 2: List benefits"
```
Expected: Responses for both tasks

### Test Advanced Features

**Task Orchestration:**
```bash
ui-cli --provider grok "Analyze: What is clean architecture?" "Synthesize: Summarize findings"
```

**Parallel Execution:**
```bash
ui-cli --parallel "Research topic A" "Research topic B" "Research topic C"
```

## Troubleshooting

### Issue: "command not found: ui-cli"

**Solution 1:** Add to PATH (user install)
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

**Solution 2:** Use full path
```bash
python -m src.main --help
```

**Solution 3:** Reinstall with --force-reinstall
```bash
pip install --force-reinstall unified-intelligence-cli
```

### Issue: "ModuleNotFoundError: No module named 'src'"

**Cause:** Package not installed or wrong directory

**Solution:**
```bash
# If in development:
pip install -e .

# If using PyPI:
pip install unified-intelligence-cli
```

### Issue: API Key Not Recognized

**Check 1:** Environment variable set
```bash
echo $XAI_API_KEY
```

**Check 2:** .env file exists
```bash
cat .env
```

**Check 3:** API key valid
```bash
curl https://api.x.ai/v1/models \
  -H "Authorization: Bearer $XAI_API_KEY"
```

### Issue: Permission Denied (Linux/macOS)

**Solution:** Use virtual environment or --user flag
```bash
pip install --user unified-intelligence-cli
```

### Issue: SSL Certificate Error

**Solution:** Update certificates
```bash
# On Ubuntu/Debian
sudo apt-get install ca-certificates

# On macOS
/Applications/Python\ 3.X/Install\ Certificates.command
```

### Issue: Tests Failing

**Check 1:** All dependencies installed
```bash
pip install -r requirements-dev.txt
```

**Check 2:** API key set for integration tests
```bash
export XAI_API_KEY=your_key
pytest tests/ -v
```

**Check 3:** Run only unit tests (no API)
```bash
pytest tests/ -m "not integration"
```

## Platform-Specific Notes

### Windows

- Use `venv\Scripts\activate` to activate virtual environment
- Use `set XAI_API_KEY=your_key` instead of `export`
- Windows Subsystem for Linux (WSL) recommended for best experience

### macOS

- May need to install Xcode Command Line Tools: `xcode-select --install`
- Use Homebrew for Python: `brew install python@3.12`

### Linux

- Debian/Ubuntu: `sudo apt-get install python3-pip python3-venv`
- RHEL/CentOS: `sudo yum install python3-pip`
- Arch: `sudo pacman -S python-pip`

## Next Steps

After installation:

1. **Configure API Key:** Set up `.env` file with your xAI API key
2. **Read Quickstart:** See `QUICKSTART.md` for usage examples
3. **Explore Examples:** Check `examples/` directory for sample tasks
4. **Join Community:** Report issues at https://github.com/yourusername/unified-intelligence-cli/issues

## Support

- **Documentation:** https://github.com/yourusername/unified-intelligence-cli
- **Issues:** https://github.com/yourusername/unified-intelligence-cli/issues
- **Security:** See SECURITY.md for reporting vulnerabilities

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
**Tested On:** Python 3.10, 3.11, 3.12 | Linux, macOS, Windows (WSL)
