# Unified Intelligence CLI

A modular CLI for multi-agent orchestration: A coordinator distributes tasks to specialized agents (e.g., coder, tester) for optimal execution, inspired by *AI Agents in Action*.

## Quick Start

1. `source .venv/bin/activate`
2. `pip install -e .` (editable install)
3. `python src/main.py --help` (CLI bootstrap)

## Structure

- `src/`: Production layers (Clean Architecture).
- `dev/`: Prototypes (e.g., agent network sims).
- `tests/`: TDD-first (mirror src/).

See `docs/architecture.md` for details. Iterate: Add entities next.