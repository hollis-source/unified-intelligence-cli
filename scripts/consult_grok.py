#!/usr/bin/env python3
"""
Simple consultation interface for Grok.
Use this to get Grok's perspective on problems during development.
"""

import sys
import json
from grok_session import GrokSession
import logging

# Reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("grok_session").setLevel(logging.WARNING)


def consult_grok(question: str, context: str = "", verbose: bool = False) -> str:
    """
    Get Grok's perspective on a question.

    Args:
        question: What to ask Grok
        context: Additional context (code, requirements, etc.)
        verbose: Whether to show detailed output

    Returns:
        Grok's response
    """
    # Initialize session
    session = GrokSession(
        system_prompt="You are Grok. Provide direct, analytical responses. Focus on accuracy and alternative perspectives.",
        enable_logging=verbose
    )

    # Build the query
    if context:
        full_query = f"Context:\n{context}\n\nQuestion:\n{question}"
    else:
        full_query = question

    # Get response
    result = session.send_message(full_query)

    if not result['success']:
        return f"Error consulting Grok: {result['response']}"

    if verbose:
        print(f"\n[Debug] Message count: {result['message_count']}")
        print(f"[Debug] Time taken: {result['elapsed_time']:.2f}s")
        if result['tool_results']:
            print(f"[Debug] Tools used: {[t['tool'] for t in result['tool_results']]}")

    return result['response']


def interactive_mode():
    """Interactive consultation mode."""
    print("=== Grok Consultation Interface ===")
    print("Type your questions (or 'exit' to quit)\n")

    session = GrokSession(
        system_prompt="You are Grok. Be helpful and analytical.",
        enable_logging=False
    )

    while True:
        try:
            question = input("\nYou: ").strip()
            if question.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break

            if not question:
                continue

            result = session.send_message(question)
            print(f"\nGrok: {result['response']}")

            if result['tool_results']:
                print(f"\n[Tools used: {', '.join(t['tool'] for t in result['tool_results'])}]")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


# CLI interface
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            interactive_mode()
        else:
            # Direct question mode
            question = " ".join(sys.argv[1:])
            print("Consulting Grok...")
            response = consult_grok(question)
            print(f"\n{response}")
    else:
        print("Usage:")
        print("  python consult_grok.py 'your question here'")
        print("  python consult_grok.py --interactive")
        print("\nExample:")
        print("  python consult_grok.py 'What are the SOLID principles?'")