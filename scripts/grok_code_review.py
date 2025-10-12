#!/usr/bin/env python3
"""
Interactive code review with Grok-Code-Fast-1.

Iteratively reviews new orchestration code and applies improvements.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factories.provider_factory import ProviderFactory


def read_code_files():
    """Read the orchestration code files."""
    files = {
        "model_selector.py": "src/routing/model_selector.py",
        "model_orchestrator.py": "src/adapters/llm/model_orchestrator.py",
        "provider_factory.py (changes)": "src/factories/provider_factory.py"
    }

    code_content = {}
    for name, path in files.items():
        with open(path, 'r') as f:
            code_content[name] = f.read()

    return code_content


def format_code_for_review(code_content):
    """Format code content for Grok review."""
    review_text = """# CODE REVIEW REQUEST

I've implemented intelligent multi-model orchestration with automatic selection and fallback. Please review the implementation focusing on:

1. **Clean Architecture Compliance**: DIP, SRP, OCP, LSP, ISP
2. **SOLID Principles**: Any violations or improvements
3. **Code Quality**: Naming, complexity, maintainability
4. **Potential Issues**: Edge cases, error handling, performance
5. **Security**: Any security concerns
6. **Testing**: Gaps in test coverage or test improvements

## Context

This orchestration system:
- Selects optimal model based on criteria (speed, quality, cost, privacy, balanced)
- Uses actual evaluation data for scoring (Qwen3: 100% success/13.8s, Tongyi: 98.7%/20.1s, Grok: 95%/5s)
- Provides automatic 3-level fallback on failures
- Implements ITextGenerator interface for drop-in compatibility

## Code Files

"""

    for filename, content in code_content.items():
        review_text += f"\n### {filename}\n\n```python\n{content}\n```\n\n"

    review_text += """
## Specific Questions

1. Is the scoring algorithm in ModelSelector optimal for the criteria?
2. Should ModelOrchestrator cache provider instances differently?
3. Are there any race conditions in the fallback logic?
4. Should task description analysis be more sophisticated?
5. Any architectural improvements to suggest?

Please provide:
- Critical issues (must fix)
- Improvement suggestions (nice to have)
- Code examples for recommended changes
"""

    return review_text


def review_with_grok(review_text):
    """Send code to Grok for review."""
    print("=" * 80)
    print("GROK CODE REVIEW SESSION")
    print("=" * 80)
    print()
    print("Initializing Grok-Code-Fast-1...")

    # Create factory and get Grok provider
    factory = ProviderFactory()
    grok = factory.create_provider("grok")

    print("✓ Grok initialized")
    print()
    print("Sending code for review...")
    print()

    # Create messages for review
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert code reviewer specializing in Clean Architecture, "
                "SOLID principles, and Python best practices. Provide detailed, "
                "actionable feedback with code examples. Focus on critical issues first, "
                "then improvements. Be specific and cite line numbers when possible."
            )
        },
        {
            "role": "user",
            "content": review_text
        }
    ]

    # Get review
    response = grok.generate(messages)

    print("=" * 80)
    print("GROK REVIEW RESULTS")
    print("=" * 80)
    print()
    print(response)
    print()

    return response


def interactive_followup(grok, initial_review):
    """Interactive follow-up questions with Grok."""
    print()
    print("=" * 80)
    print("FOLLOW-UP ROUND")
    print("=" * 80)
    print()

    followup_questions = [
        "Are there any performance optimizations you'd recommend for the scoring algorithm?",
        "Should the fallback chain be configurable or always automatic?",
        "Any concerns about the ModelCapabilities dataclass structure?",
        "Would you recommend adding caching to the model selection logic?"
    ]

    conversation = [
        {
            "role": "system",
            "content": (
                "You are an expert code reviewer. Continue the code review discussion "
                "with specific, actionable recommendations."
            )
        },
        {
            "role": "user",
            "content": format_code_for_review(read_code_files())
        },
        {
            "role": "assistant",
            "content": initial_review
        }
    ]

    for question in followup_questions:
        print(f"Q: {question}")
        print()

        conversation.append({
            "role": "user",
            "content": question
        })

        response = grok.generate(conversation)

        print(f"A: {response}")
        print()
        print("-" * 80)
        print()

        conversation.append({
            "role": "assistant",
            "content": response
        })

    return conversation


def summarize_review(conversation):
    """Ask Grok to summarize critical changes."""
    print("=" * 80)
    print("REVIEW SUMMARY")
    print("=" * 80)
    print()
    print("Requesting summary of critical changes...")
    print()

    factory = ProviderFactory()
    grok = factory.create_provider("grok")

    conversation.append({
        "role": "user",
        "content": (
            "Please provide a concise summary of:\n"
            "1. Critical issues that MUST be fixed (with priority)\n"
            "2. Top 3 improvement suggestions (with code examples)\n"
            "3. Overall assessment (pass/needs work/major issues)\n\n"
            "Format as actionable items."
        )
    })

    summary = grok.generate(conversation)

    print(summary)
    print()

    return summary


def main():
    """Run interactive code review session."""
    try:
        # Read code
        print("Reading orchestration code...")
        code_content = read_code_files()
        print(f"✓ Loaded {len(code_content)} files")
        print()

        # Format for review
        review_text = format_code_for_review(code_content)
        print(f"✓ Formatted {len(review_text)} chars for review")
        print()

        # Initial review
        print("=" * 80)
        print("ROUND 1: Initial Review")
        print("=" * 80)
        print()

        initial_review = review_with_grok(review_text)

        # Interactive follow-up
        print("=" * 80)
        print("ROUND 2: Follow-up Questions")
        print("=" * 80)
        print()

        factory = ProviderFactory()
        grok = factory.create_provider("grok")

        conversation = interactive_followup(grok, initial_review)

        # Summary
        print("=" * 80)
        print("ROUND 3: Summary & Action Items")
        print("=" * 80)
        print()

        summary = summarize_review(conversation)

        # Save review results
        review_output = {
            "timestamp": "2025-10-03",
            "files_reviewed": list(code_content.keys()),
            "initial_review": initial_review,
            "followup_conversation": [
                msg for msg in conversation if msg["role"] in ["user", "assistant"]
            ],
            "summary": summary
        }

        output_file = "docs/grok_code_review_orchestration.json"
        with open(output_file, 'w') as f:
            json.dump(review_output, f, indent=2)

        print("=" * 80)
        print("✅ CODE REVIEW COMPLETE")
        print("=" * 80)
        print()
        print(f"Full review saved to: {output_file}")
        print()
        print("Next steps:")
        print("  1. Review critical issues from summary")
        print("  2. Implement high-priority fixes")
        print("  3. Consider improvement suggestions")
        print("  4. Re-run tests after changes")
        print()

    except Exception as e:
        print(f"❌ Review failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
