# Quick Installation Guide

## Requirements
- Python 3.10 or higher
- pip (Python package installer)
- Git
- xAI API key for Grok (get from https://x.ai)

## Installation Steps

### 1. Install the CLI

```bash
pip install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

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

### Missing API Key Error
If you see "XAI_API_KEY not found", make sure you created the `.env` file with your API key.

### Import Errors
If you see "ModuleNotFoundError", reinstall:
```bash
pip uninstall unified-intelligence-cli
pip install git+https://github.com/hollis-source/unified-intelligence-cli.git
```

### Permission Errors
If you get permission errors, use:
```bash
pip install --user git+https://github.com/hollis-source/unified-intelligence-cli.git
```

## Updating

To get the latest version:

```bash
pip install --upgrade git+https://github.com/hollis-source/unified-intelligence-cli.git
```

## Support

- Issues: https://github.com/hollis-source/unified-intelligence-cli/issues
- Documentation: See README.md in the repository
