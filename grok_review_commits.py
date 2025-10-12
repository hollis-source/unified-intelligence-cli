#!/usr/bin/env python3
"""
Grok Code Review - Direct Analysis

Provides commit data directly to Grok for comprehensive review.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from grok_session import GrokSession


def run_git_command(cmd):
    """Run git command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout if result.stdout else result.stderr


def main():
    """Run comprehensive code review."""

    print("=" * 80)
    print("GROK CODE REVIEW - COMMIT ANALYSIS")
    print("=" * 80)
    print()

    if not os.getenv("XAI_API_KEY"):
        print("❌ Error: XAI_API_KEY not set")
        return 1

    print("📊 Gathering commit data...")

    # Get recent commits
    commits_log = run_git_command("git log --oneline --no-merges -9")

    # Get detailed info for recent commits
    detailed_commits = []
    for line in commits_log.strip().split('\n')[:9]:
        commit_hash = line.split()[0]
        commit_details = run_git_command(f"git show --stat {commit_hash}")
        detailed_commits.append(commit_details)

    # Get test results
    print("🧪 Running test suite...")
    test_results = run_git_command(
        f"cd {Path.cwd()} && . venv/bin/activate && "
        "python3 -c \"import sys; sys.path.insert(0, '.'); import pytest; "
        "pytest.main(['-v', 'tests/', '--tb=short'])\" 2>&1 | tail -30"
    )

    # Get coverage
    print("📈 Checking coverage...")
    coverage_results = run_git_command(
        f"cd {Path.cwd()} && . venv/bin/activate && "
        "python3 -c \"import sys; sys.path.insert(0, '.'); import pytest; "
        "pytest.main(['tests/', '--cov=src', '--cov-report=term'])\" 2>&1 | tail -25"
    )

    print("✓ Data collected")
    print()

    # Create Grok session
    print("🤖 Initializing Grok review session...")
    session = GrokSession(model="grok-code-fast-1", enable_logging=True)

    # System prompt
    system_msg = """You are an expert code reviewer specializing in:
- Clean Code principles (Robert C. Martin)
- Clean Architecture (dependency rule, layers)
- SOLID principles (SRP, OCP, LSP, ISP, DIP)
- Python best practices and PEP 8
- Test-Driven Development (TDD)

Provide detailed, constructive feedback with specific examples."""

    session.messages.append({"role": "system", "content": system_msg})

    # Build comprehensive review request
    review_request = f"""Please review the recent commits to this Python project following the unified-intelligence-cli roadmap.

## PROJECT CONTEXT
This is a multi-agent task orchestration CLI built with Clean Architecture.
- Uses Click for CLI
- Async task coordination
- LLM providers (Mock, Grok) with tool support
- TDD approach with pytest

## RECENT COMMITS (Last 9)

{commits_log}

## DETAILED COMMIT INFORMATION

{"=" * 80}
""" + "\n\n".join(detailed_commits) + f"""

## TEST RESULTS

{test_results}

## COVERAGE ANALYSIS

{coverage_results}

## REVIEW CRITERIA

Please provide a comprehensive code review covering:

1. **Architecture Quality**
   - Is Clean Architecture maintained? (dependency rule)
   - Layer separation (entities, use cases, interfaces, adapters)
   - Dependency Inversion Principle compliance

2. **Code Quality**
   - SOLID principles adherence
   - Clean Code guidelines (functions, naming, complexity)
   - Python best practices and PEP 8

3. **Testing**
   - Test coverage adequacy (currently ~65-70%)
   - Test quality and TDD adherence
   - Integration vs unit test balance

4. **Documentation**
   - README completeness
   - Code comments and docstrings
   - Commit message quality

5. **Implementation**
   - Feature completeness per roadmap
   - Error handling
   - Security considerations

## FORMAT

Please structure your review as:

### Overall Assessment
(High-level strengths and concerns)

### Detailed Analysis by Commit
(Review each major commit)

### Code Quality Metrics
(Quantitative assessment)

### Recommendations
(Specific, actionable improvements)

### Violations & Concerns
(Any principle violations or red flags)

Be thorough, specific, and constructive. Reference specific commits, files, and line numbers where applicable."""

    print("📤 Sending review request to Grok...")
    print("   (This may take 30-60 seconds)")
    print()

    result = session.send_message(
        user_message=review_request,
        temperature=0.3,
        use_tools=False  # Don't need tools, we provided all data
    )

    print("=" * 80)
    print("GROK CODE REVIEW RESULTS")
    print("=" * 80)
    print()
    print(result["response"])
    print()

    # Save to file
    output_file = Path("GROK_CODE_REVIEW.md")
    with open(output_file, 'w') as f:
        f.write("# Grok Code Review - Recent Commits\n\n")
        f.write(f"**Model:** grok-code-fast-1\n")
        f.write(f"**Commits Reviewed:** 9\n")
        f.write(f"**Test Results:** Included\n")
        f.write(f"**Coverage:** Included\n\n")
        f.write("---\n\n")
        f.write(result["response"])

    print(f"✓ Review saved to {output_file}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())