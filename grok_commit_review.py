#!/usr/bin/env python3
"""
Interactive Grok Code Review - Recent Commits Analysis

Uses Grok with tool support to comprehensively review recent commits.
Grok can use tools to inspect files, diffs, run tests, etc.
"""

import os
import sys
from pathlib import Path

# Add scripts to path for GrokSession
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from grok_session import GrokSession
from src.tools import DEV_TOOLS, TOOL_FUNCTIONS


def main():
    """Run interactive Grok code review session."""

    print("=" * 80)
    print("GROK CODE REVIEW - INTERACTIVE SESSION")
    print("=" * 80)
    print()

    # Check API key
    if not os.getenv("XAI_API_KEY"):
        print("❌ Error: XAI_API_KEY not set")
        print("Please set your XAI API key in .env file")
        return 1

    # Create Grok session with tools
    print("Initializing Grok session with dev tools...")
    session = GrokSession(
        model="grok-code-fast-1",
        enable_logging=True
    )

    # Register dev tools
    for tool in DEV_TOOLS:
        tool_name = tool["function"]["name"]
        if tool not in session.tools:
            session.tools.append(tool)
        if tool_name in TOOL_FUNCTIONS:
            session.tool_functions[tool_name] = TOOL_FUNCTIONS[tool_name]

    print(f"✓ Tools enabled: {', '.join(t['function']['name'] for t in DEV_TOOLS)}")
    print()

    # System message - set Grok's role
    system_msg = """You are an expert code reviewer specializing in Clean Architecture, SOLID principles, and Python best practices.

Your task is to comprehensively review the recent commits in this repository. Use the available tools to:
1. Read git log to see recent commits
2. Examine git diffs to understand changes
3. Read modified files to understand implementation
4. Check test files to validate test coverage
5. Run tests if needed to verify functionality

Review criteria:
- Clean Code principles (meaningful names, small functions, clear intent)
- Clean Architecture (dependency rule, layer separation)
- SOLID principles (SRP, OCP, LSP, ISP, DIP)
- Test coverage and quality
- Documentation completeness
- Commit message quality
- Code consistency and maintainability

Provide:
1. Overall assessment (strengths and concerns)
2. Specific feedback on each major commit
3. Code quality metrics
4. Recommendations for improvement
5. Highlight any violations of principles

Be thorough and use tools extensively to inspect the actual code, not just commit messages."""

    session.messages.append({"role": "system", "content": system_msg})

    # Initial review request
    review_request = """Please perform a comprehensive code review of the recent commits in this repository.

Recent commits to review (use tools to inspect):
1. 111cb64 - Doc: Roadmap Completion Report - 100% Achievement
2. 6bc44d3 - Polish: Add Missing Type Hints to Core Modules (Low Priority #1)
3. 7602827 - Feat: Implement --config Flag for Runtime Configuration (Low Priority #2)
4. f7fef80 - Doc: Add Comprehensive Contributing Guidelines
5. e7430ab - Doc: Comprehensive README Update with Multi-Task CLI Examples
6. fb4dae8 - Doc: Refactoring Assessment - Pragmatic Code Quality Review
7. 6ba29c9 - Feat: Complete End-to-End Dev Workflow Demo (High Priority #3)
8. e3db30a - Feat: Complete IToolSupportedProvider with Dev Tools (High Priority #2)
9. cb8f403 - Feat: Multi-Task CLI & Improved Agent Selection (High Priority #1 & Coverage)

Focus areas:
1. Architecture quality - Is Clean Architecture maintained?
2. Code quality - SOLID principles, Clean Code guidelines
3. Testing - Coverage, quality, TDD adherence
4. Documentation - Completeness, clarity
5. Implementation - Correctness, maintainability

Please use the available tools to:
- Read git log for full commit details
- Examine diffs with `git show <commit>`
- Read key files that were changed
- Check test files
- Run tests if you want to verify functionality

Start your analysis and provide comprehensive feedback."""

    print("=" * 80)
    print("REVIEW REQUEST SENT TO GROK")
    print("=" * 80)
    print()
    print("Grok is now analyzing commits with tool support...")
    print("This may take several minutes as Grok inspects files and diffs...")
    print()

    # Send request with tools enabled
    result = session.send_message(
        user_message=review_request,
        temperature=0.3,  # Lower temperature for more focused analysis
        use_tools=True
    )

    print("=" * 80)
    print("GROK CODE REVIEW RESULTS")
    print("=" * 80)
    print()

    if result["response"]:
        print(result["response"])
    else:
        print("⚠️  Initial response was empty. Grok may need more context.")
        print("Asking Grok to provide the review now...")

        # Follow-up to get actual review
        result = session.send_message(
            user_message="Please provide your comprehensive code review now based on what you discovered.",
            temperature=0.3,
            use_tools=True
        )
        print(result["response"])

    print()

    if result.get("tool_calls"):
        print()
        print("=" * 80)
        print(f"TOOLS USED: {len(result['tool_calls'])} calls")
        print("=" * 80)
        for i, call in enumerate(result['tool_calls'], 1):
            tool_name = call.get('function', {}).get('name', 'unknown')
            tool_args = call.get('function', {}).get('arguments', '')
            print(f"{i}. {tool_name}({tool_args[:100]}...)")
        print()

    # Save review to file
    output_file = Path("GROK_CODE_REVIEW.md")
    with open(output_file, 'w') as f:
        f.write("# Grok Code Review - Recent Commits\n\n")
        f.write(f"**Date:** {Path.cwd()}\n")
        f.write(f"**Model:** grok-code-fast-1\n")
        f.write(f"**Tools Used:** {len(result.get('tool_calls', []))} tool calls\n\n")
        f.write("---\n\n")
        f.write(result["response"])

    print(f"\n✓ Review saved to {output_file}")

    # Interactive follow-up (optional, with better error handling)
    print()
    print("=" * 80)
    print("INTERACTIVE FOLLOW-UP (Optional)")
    print("=" * 80)
    print("Press Ctrl+C to skip, or ask follow-up questions.")
    print()

    try:
        while True:
            try:
                user_input = input("\n📝 Your question (or 'quit'): ").strip()

                if user_input.lower() in ['exit', 'quit', 'q', '']:
                    print("\n✓ Review session ended.")
                    break

                print("\n⏳ Grok is analyzing...")
                result = session.send_message(
                    user_message=user_input,
                    temperature=0.3,
                    use_tools=True
                )

                print()
                print("🤖 Grok:")
                print("-" * 80)
                print(result["response"])
                print()

            except EOFError:
                print("\n✓ No interactive input available. Review complete.")
                break

    except KeyboardInterrupt:
        print("\n\n✓ Review session ended.")

    return 0


if __name__ == "__main__":
    sys.exit(main())