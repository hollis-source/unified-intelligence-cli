#!/usr/bin/env python3
"""
Interactive Grok session with tool use for refactoring investigation.
Allows Grok to actively investigate the codebase using tools.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.grok_session import GrokSession


# Define tools for Grok to use
INVESTIGATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the complete contents of a file in the codebase",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file relative to project root (e.g., 'src/main.py')"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List all files and directories in a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path relative to project root (e.g., 'src/use_cases')"
                    }
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern across all Python files",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Optional: Limit search to specific directory (default: 'src')"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_lines",
            "description": "Count lines in a file or all Python files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path or directory to analyze"
                    }
                },
                "required": ["path"]
            }
        }
    }
]


def read_file(file_path: str) -> str:
    """Read a file and return numbered contents."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        content = full_path.read_text()
        lines = content.split('\n')
        numbered = '\n'.join(f"{i+1:4d}: {line}" for i, line in enumerate(lines))
        return f"=== {file_path} ===\n\n{numbered}"
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def list_directory(directory: str) -> str:
    """List directory contents."""
    project_root = Path(__file__).parent.parent
    dir_path = project_root / directory

    if not dir_path.exists():
        return f"Error: Directory not found: {directory}"

    try:
        items = []
        for item in sorted(dir_path.iterdir()):
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")

        return f"=== {directory}/ ===\n\n" + '\n'.join(items)
    except Exception as e:
        return f"Error listing {directory}: {str(e)}"


def search_code(pattern: str, directory: str = "src") -> str:
    """Search for pattern in Python files."""
    project_root = Path(__file__).parent.parent
    search_dir = project_root / directory

    if not search_dir.exists():
        return f"Error: Directory not found: {directory}"

    try:
        matches = []
        for py_file in search_dir.rglob("*.py"):
            content = py_file.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if pattern.lower() in line.lower():
                    rel_path = py_file.relative_to(project_root)
                    matches.append(f"{rel_path}:{i}: {line.strip()}")
                    if len(matches) >= 50:  # Limit results
                        matches.append("\n... (truncated, 50+ matches)")
                        return '\n'.join(matches)

        if not matches:
            return f"No matches found for '{pattern}' in {directory}/"

        return f"Found {len(matches)} matches for '{pattern}':\n\n" + '\n'.join(matches)
    except Exception as e:
        return f"Error searching: {str(e)}"


def count_lines(path: str) -> str:
    """Count lines in file(s)."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / path

    if not full_path.exists():
        return f"Error: Path not found: {path}"

    try:
        if full_path.is_file():
            lines = len(full_path.read_text().split('\n'))
            return f"{path}: {lines} lines"

        # Directory - count all Python files
        total = 0
        files = []
        for py_file in full_path.rglob("*.py"):
            line_count = len(py_file.read_text().split('\n'))
            total += line_count
            rel_path = py_file.relative_to(project_root)
            files.append(f"  {rel_path}: {line_count} lines")

        result = f"Total: {total} lines across {len(files)} Python files in {path}/\n\n"
        result += '\n'.join(files)
        return result
    except Exception as e:
        return f"Error counting lines: {str(e)}"


def run_interactive_investigation():
    """Run interactive refactoring investigation with Grok."""
    print("=" * 80)
    print("GROK INTERACTIVE REFACTORING INVESTIGATION")
    print("=" * 80)
    print()
    print("Grok will investigate the codebase using tools to find refactoring opportunities.")
    print()
    print("Available tools:")
    for tool in INVESTIGATION_TOOLS:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    print()
    print("=" * 80)
    print()

    # Initialize session with grok-code-fast-1 (current model with function calling)
    session = GrokSession(
        model="grok-code-fast-1",
        system_prompt="""You are Grok, an expert in Clean Architecture and SOLID principles.

You have tools to investigate a codebase. Use them to find refactoring opportunities.

**Investigation Strategy:**
1. Start by exploring the structure (list directories)
2. Read key files to understand architecture
3. Search for code smells (duplication, long methods, violations)
4. Count lines to find overly complex files

**Look for:**
- SOLID violations
- Clean Architecture boundary violations
- Code duplication
- Missing abstractions
- Complex conditionals
- Error handling gaps
- Testing opportunities

**Provide evidence-based recommendations:**
- Specific file:line references
- Code examples
- Expected benefits (cite industry data when possible)
- Implementation difficulty (low/medium/high)
- Priority (high/medium/low)

Use tools actively. Be thorough."""
    )

    # Set tools and register functions
    session.tools = INVESTIGATION_TOOLS
    session.tool_functions = {
        "read_file": read_file,
        "list_directory": list_directory,
        "search_code": search_code,
        "count_lines": count_lines
    }

    # Investigation prompt
    investigation_prompt = """# Refactoring Investigation Task

Investigate our Unified Intelligence CLI for additional refactoring opportunities.

## Context

We recently completed major refactoring:
- Split CoordinateAgentsUseCase → TaskPlannerUseCase + TaskCoordinatorUseCase (SRP)
- Added IAgentFactory and IProviderFactory interfaces (DIP)
- Extracted methods to <20 lines (Clean Code)
- All tests passing, CLI functional

Latest commit: 5d334e6

## Your Mission

Use your tools to systematically investigate:

1. **Architecture Overview**:
   - list_directory("src") - see overall structure
   - read_file("src/main.py") - understand entry point
   - read_file("src/composition.py") - understand DI wiring

2. **Deep Dive by Layer**:
   - list_directory("src/entities") and read key files
   - list_directory("src/use_cases") and read key files
   - list_directory("src/interfaces") and read key files
   - list_directory("src/adapters") and read adapters

3. **Search for Issues**:
   - search_code("TODO") - find pending work
   - search_code("FIXME") - find known issues
   - count_lines("src/use_cases") - check complexity

4. **After investigation, provide**:
   - Summary of findings
   - Prioritized refactoring recommendations
   - Specific file:line references
   - Expected benefits with evidence

**IMPORTANT**: After using tools, provide your complete analysis and recommendations. Don't stop after tool use!"""

    print("Sending investigation request to Grok...")
    print("(Grok will use tools iteratively until investigation is complete)")
    print()
    print("=" * 80)
    print()

    # Initial investigation request
    result = session.send_message(investigation_prompt)

    # Track all tool calls across rounds
    all_tool_calls = []
    if result['tool_results']:
        all_tool_calls.extend(result['tool_results'])

    # Display first round
    round_num = 1
    if result['tool_results']:
        print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
        for i, tool_result in enumerate(result['tool_results'], 1):
            tool_name = tool_result['tool']
            args = tool_result.get('args', {})
            print(f"  {i}. {tool_name}({json.dumps(args)})")
        print()

    # Continue investigation rounds until Grok stops using tools
    max_rounds = 15  # Safety limit
    while result['tool_results'] and round_num < max_rounds:
        round_num += 1

        # Ask Grok to continue investigating or provide final analysis
        follow_up = """Continue your investigation using more tools to gather additional information,
OR if you have gathered sufficient information, provide your complete analysis and recommendations.

Remember to be thorough in your final analysis:
- Summarize all findings
- List prioritized refactoring opportunities
- Provide specific file:line references
- Explain expected benefits with evidence"""

        result = session.send_message(follow_up)

        if result['tool_results']:
            all_tool_calls.extend(result['tool_results'])
            print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
            for i, tool_result in enumerate(result['tool_results'], 1):
                tool_name = tool_result['tool']
                args = tool_result.get('args', {})
                print(f"  {i}. {tool_name}({json.dumps(args)})")
            print()

    # Display completion message
    if round_num >= max_rounds:
        print(f"\nReached maximum rounds ({max_rounds}). Stopping investigation.")
    else:
        print(f"\nInvestigation complete after {round_num} rounds.")

    print()
    print("=" * 80)
    print("GROK'S FINDINGS AND RECOMMENDATIONS")
    print("=" * 80)
    print()
    print(result['response'])
    print()
    print("=" * 80)
    print()

    # Save results
    output_file = Path("docs/grok_refactoring_investigation.md")
    with open(output_file, 'w') as f:
        f.write("# Grok's Interactive Refactoring Investigation\n\n")
        f.write("## Session Summary\n\n")
        f.write(f"- Model: grok-code-fast-1\n")
        f.write(f"- Investigation rounds: {round_num}\n")
        f.write(f"- Total tool calls: {len(all_tool_calls)}\n")
        f.write(f"- Total messages: {len(session.messages)}\n")
        f.write(f"- Success: {result['success']}\n\n")

        if all_tool_calls:
            f.write("## Tools Called\n\n")
            for i, tr in enumerate(all_tool_calls, 1):
                f.write(f"{i}. **{tr['tool']}**")
                if tr.get('args'):
                    f.write(f" - `{json.dumps(tr['args'])}`")
                f.write("\n")
            f.write("\n")

        f.write("## Investigation Findings\n\n")
        f.write(result['response'])

    print(f"Results saved to: {output_file}")
    print()

    return result


if __name__ == "__main__":
    try:
        run_interactive_investigation()
    except KeyboardInterrupt:
        print("\n\nInvestigation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)