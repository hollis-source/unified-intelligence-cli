#!/bin/bash
# Shell wrapper to run DSL example with proper PYTHONPATH

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" venv/bin/python3 examples/dsl_example.py
