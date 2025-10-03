#!/usr/bin/env python3
"""
Test script for ModelOrchestrator - Smart multi-model selection.

Week 13: Demonstrates intelligent model selection and fallback behavior.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factories.provider_factory import ProviderFactory
from src.routing.model_selector import SelectionCriteria


def test_orchestrator_basic():
    """Test basic orchestrator functionality."""
    print("=" * 70)
    print("TEST 1: Basic Orchestrator")
    print("=" * 70)
    print()

    # Create factory
    factory = ProviderFactory()

    # Create orchestrator with balanced criteria
    orchestrator = factory.create_provider("auto")

    print("✓ Orchestrator created successfully")
    print(f"  Default criteria: BALANCED")
    print(f"  Available providers: qwen3_zerogpu, tongyi-local, grok")
    print()

    # Test model info
    print("Model Capabilities:")
    for provider in ["qwen3_zerogpu", "tongyi-local", "grok"]:
        info = orchestrator.get_model_info(provider)
        if info:
            print(f"\n  {info['name']}:")
            print(f"    Success Rate: {info['success_rate']*100:.1f}%")
            print(f"    Avg Latency: {info['avg_latency']}s")
            print(f"    Cost: ${info['cost_per_month']}/month")
            print(f"    Offline: {'Yes' if not info['requires_internet'] else 'No'}")

    print()


def test_selection_criteria():
    """Test different selection criteria."""
    print("=" * 70)
    print("TEST 2: Selection Criteria")
    print("=" * 70)
    print()

    factory = ProviderFactory()

    test_cases = [
        ("speed", "What is Clean Architecture?"),
        ("quality", "Explain SOLID principles in detail"),
        ("cost", "Simple question"),
        ("privacy", "Analyze this confidential data offline"),
        ("balanced", "Standard query")
    ]

    for criteria_name, task in test_cases:
        config = {"criteria": criteria_name}
        orchestrator = factory.create_provider("auto", config)

        # Test selection
        from src.routing.model_selector import ModelSelector
        selector = ModelSelector()

        criteria_enum = {
            "speed": SelectionCriteria.SPEED,
            "quality": SelectionCriteria.QUALITY,
            "cost": SelectionCriteria.COST,
            "privacy": SelectionCriteria.PRIVACY,
            "balanced": SelectionCriteria.BALANCED
        }[criteria_name]

        selected = selector.select_model(
            criteria=criteria_enum,
            available_providers=["qwen3_zerogpu", "tongyi-local", "grok"],
            task_description=task
        )

        print(f"Criteria: {criteria_name.upper()}")
        print(f"  Task: {task}")
        print(f"  Selected: {selected}")
        print()


def test_fallback_chain():
    """Test fallback chain logic."""
    print("=" * 70)
    print("TEST 3: Fallback Chain")
    print("=" * 70)
    print()

    from src.routing.model_selector import ModelSelector

    selector = ModelSelector()

    print("Fallback chains for different primary models:\n")

    for primary in ["qwen3_zerogpu", "tongyi-local", "grok"]:
        chain = selector.get_fallback_chain(
            primary=primary,
            criteria=SelectionCriteria.BALANCED
        )
        print(f"Primary: {primary}")
        print(f"  Chain: {' → '.join(chain)}")
        print()


def test_scoring():
    """Test model scoring for different criteria."""
    print("=" * 70)
    print("TEST 4: Model Scoring")
    print("=" * 70)
    print()

    from src.routing.model_selector import ModelSelector, SelectionCriteria

    selector = ModelSelector()

    criteria_list = [
        SelectionCriteria.SPEED,
        SelectionCriteria.QUALITY,
        SelectionCriteria.COST,
        SelectionCriteria.PRIVACY,
        SelectionCriteria.BALANCED
    ]

    for criteria in criteria_list:
        print(f"\nCriteria: {criteria.value.upper()}")
        print("-" * 60)

        scores = []
        for provider_name, caps in selector.models.items():
            score = caps.get_score(criteria)
            scores.append((provider_name, score))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        for provider, score in scores:
            print(f"  {provider:20s}: {score:6.2f}")


def test_configuration():
    """Test different orchestrator configurations."""
    print("=" * 70)
    print("TEST 5: Configuration Options")
    print("=" * 70)
    print()

    factory = ProviderFactory()

    configs = [
        {
            "name": "Speed optimized",
            "config": {
                "criteria": "speed",
                "available_providers": ["qwen3_zerogpu", "grok"],
                "enable_fallback": True
            }
        },
        {
            "name": "Offline only",
            "config": {
                "criteria": "privacy",
                "available_providers": ["tongyi-local"],
                "enable_fallback": False
            }
        },
        {
            "name": "Cost optimized",
            "config": {
                "criteria": "cost",
                "available_providers": ["qwen3_zerogpu", "tongyi-local"],
                "max_fallback_attempts": 2
            }
        }
    ]

    for test_case in configs:
        print(f"\n{test_case['name']}:")
        print(f"  Config: {test_case['config']}")

        orchestrator = factory.create_provider("auto", test_case['config'])

        print(f"  ✓ Orchestrator created successfully")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MODEL ORCHESTRATOR TEST SUITE")
    print("=" * 70)
    print()

    try:
        test_orchestrator_basic()
        test_selection_criteria()
        test_fallback_chain()
        test_scoring()
        test_configuration()

        print("=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print()

        print("Next steps:")
        print("  1. Use orchestrator in CLI: --provider auto")
        print("  2. Configure criteria: --provider auto --config '{\"criteria\": \"speed\"}'")
        print("  3. Test with real queries to validate model selection")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
