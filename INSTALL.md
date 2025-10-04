# Quick Installation Guide

## Requirements
- Python 3.10 or higher
- Git
- xAI API key for Grok (get from https://x.ai)

## Installation Steps

### Method 1: pipx (Recommended - Automatic Isolated Environment)

**Install pipx first (if not already installed):**
```bash
# On Debian/Ubuntu
sudo apt update && sudo apt install -y pipx
pipx ensurepath

# On other systems
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

**Then install unified-intelligence-cli:**
```bash
pipx install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

That's it! pipx automatically creates an isolated environment and adds `ui-cli` to your PATH.

### Method 2: Virtual Environment (Alternative)

If you prefer manual control:

```bash
# Create virtual environment
python3 -m venv ~/ui-cli-env

# Activate it
source ~/ui-cli-env/bin/activate

# Install
pip install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

**Note**: You'll need to activate the venv (`source ~/ui-cli-env/bin/activate`) each time before using `ui-cli`.

### 2. Set Up API Key

Create a `.env` file in your working directory:

```bash
echo "XAI_API_KEY=your-xai-api-key-here" > .env
```

Replace `your-xai-api-key-here` with your actual xAI API key.

### 3. Verify Installation

```bash
ui-cli --help
```

You should see the help menu with all available options.

## Basic Usage

### Simple Task

```bash
ui-cli --task "Analyze this code and suggest improvements" --provider auto --routing team --agents scaled
```

### With Metrics Collection

```bash
ui-cli --task "Research best practices for Python testing" \
       --provider auto \
       --routing team \
       --agents scaled \
       --collect-metrics \
       --verbose
```

### Multiple Tasks (Parallel Execution)

```bash
ui-cli --task "Task 1 description" \
       --task "Task 2 description" \
       --task "Task 3 description" \
       --provider auto \
       --routing team \
       --agents scaled
```

## Common Options

- `--provider auto` - Automatically select best LLM model (Grok, Qwen3, etc.)
- `--routing team` - Use team-based routing (recommended for scaled agents)
- `--agents scaled` - Use all 16 agents across 9 teams
- `--collect-metrics` - Track performance metrics
- `--verbose` or `-v` - Show detailed output
- `--timeout 900` - Set timeout in seconds (default: 60)

## Troubleshooting

### Externally Managed Environment Error
If you see this error:
```
error: externally-managed-environment
```

**Solution**: Use pipx (Method 1 above) instead of pip. pipx automatically handles isolated environments.

### Missing API Key Error
If you see "XAI_API_KEY not found", make sure you created the `.env` file with your API key.

### Command Not Found After pipx Install
If `ui-cli` command is not found after pipx install:
```bash
# Ensure pipx path is added
pipx ensurepath
# Then restart your terminal or run:
source ~/.bashrc  # or source ~/.zshrc if using zsh
```

### Import Errors
If you see "ModuleNotFoundError":

**With pipx:**
```bash
pipx uninstall unified-intelligence-cli
pipx install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

**With venv:**
```bash
source ~/ui-cli-env/bin/activate
pip uninstall unified-intelligence-cli
pip install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

## Updating

To get the latest version:

**With pipx:**
```bash
pipx upgrade unified-intelligence-cli
# or to force reinstall from GitHub:
pipx install --force git+https://github.com/hollis-source/unified-intelligence-cli.git
```

**With venv:**
```bash
source ~/ui-cli-env/bin/activate
pip install --upgrade git+https://github.com/hollis-source/unified-intelligence-cli.git
```

## Support

- Issues: https://github.com/hollis-source/unified-intelligence-cli/issues
- Documentation: See README.md in the repository
