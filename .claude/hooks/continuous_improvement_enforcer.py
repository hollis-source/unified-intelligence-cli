#!/usr/bin/env python3
"""
Continuous Improvement Philosophy Enforcer

Catches language that implies "done-ness" and suggests reframing
toward continuous improvement mindset.

Enforces: Everything is always in production, always improving.
No "final" versions, no "production ready" gates, no phases.

See: docs/CONTINUOUS_IMPROVEMENT_PHILOSOPHY.md
"""

import sys
import re

# Patterns that imply "done-ness" (anti-pattern)
DONE_PATTERNS = [
    (r'\bproduction[- ]ready\b', 'current functionality: X%'),
    (r'\bfinal\s+version\b', 'iteration N'),
    (r'\bcomplete(?:d)?\b(?!\s+in\b)', 'baseline established / next target'),
    (r'\bfinish(?:ed)?\b', 'current state / next iteration'),
    (r'\bdone\b', 'continuous improvement'),
    (r'\bPhase\s+\d+:', 'Iteration N:'),
    (r'\bvalidate\s+before\s+proceeding\b', 'measure continuously'),
    (r'\bprove\s+.+\s+before\s+', 'build in parallel, measure all'),
    (r'\bwait(?:ing)?\s+for\s+.+\s+before\b', 'ship continuously'),
    (r'\bblocking\s+issue\b', 'current limitation (workaround: X)'),
    (r'\bmust\s+be\s+.+\s+before\b', 'improves with'),
    (r'\bnot\s+ready\s+for\s+production\b', 'currently at X% functionality'),
    (r'\bwhen\s+.+\s+is\s+complete\b', 'as X improves'),
    (r'\bafter\s+we\s+finish\b', 'while we improve'),
    (r'\bis\s+broken\b', 'currently at X% functionality'),
]

# Philosophy summary
PHILOSOPHY = """
╔════════════════════════════════════════════════════════════════╗
║  CONTINUOUS IMPROVEMENT PHILOSOPHY                             ║
║                                                                ║
║  • Everything is always in production                          ║
║  • No "final" versions - only current iterations               ║
║  • No "done" - only "current functionality: X%"                ║
║  • Build → Measure → Improve → Repeat (forever)               ║
║  • Ship continuously, improve continuously                     ║
║  • Tools to build tools to build tools (meta-development)      ║
║                                                                ║
║  "The only final target is continual improvement"              ║
╚════════════════════════════════════════════════════════════════╝
"""

def check_message(text: str) -> list[dict]:
    """Check text for done-ness language."""
    violations = []

    for pattern, suggestion in DONE_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            violations.append({
                'match': match.group(0),
                'suggestion': suggestion,
                'position': match.start()
            })

    return violations

def format_violations(violations: list[dict]) -> str:
    """Format violations for display."""
    output = []

    output.append(PHILOSOPHY)
    output.append("\n⚠️  Detected language implying 'done-ness':\n")

    # Show first 5 violations
    for v in violations[:5]:
        output.append(f"  • '{v['match']}' → Consider: '{v['suggestion']}'")

    if len(violations) > 5:
        output.append(f"\n  ... and {len(violations) - 5} more")

    output.append("\n💡 Reframe: What's the current state? Next improvement target?")
    output.append(f"\n📖 See: docs/CONTINUOUS_IMPROVEMENT_PHILOSOPHY.md\n")

    return "\n".join(output)

def main():
    """Main entry point for hook."""
    # Read stdin (Claude's response)
    text = sys.stdin.read()

    violations = check_message(text)

    if violations:
        print(format_violations(violations), file=sys.stderr)

    # Always pass through (informational only, never block)
    print(text)
    sys.exit(0)

if __name__ == '__main__':
    main()
