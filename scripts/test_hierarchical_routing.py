#!/usr/bin/env python3
"""
Test Hierarchical Routing - Verify 3-tier routing with 8 agents.

Week 11 Phase 1: Validation script for hierarchical agent scaling.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task
from src.factories.agent_factory import AgentFactory
from src.routing import HierarchicalRouter


def test_routing():
    """Test hierarchical routing with 8-agent system."""

    print("="*70)
    print("HIERARCHICAL ROUTING TEST - 8 AGENTS")
    print("="*70)

    # Create 8-agent system
    agent_factory = AgentFactory()
    agents = agent_factory.create_extended_agents()

    print(f"\n✅ Created {len(agents)} agents:")
    for agent in agents:
        print(f"  - {agent.role} (tier={agent.tier}, specialization={agent.specialization})")

    # Create hierarchical router
    router = HierarchicalRouter()

    # Test tasks covering all tiers and domains
    test_tasks = [
        # Tier 1: Planning (should route to master-orchestrator)
        Task(description="Plan the overall architecture for a microservices system"),
        Task(description="Organize and prioritize the sprint backlog"),

        # Tier 1: QA (should route to qa-lead)
        Task(description="Review code for SOLID principles and clean architecture"),
        Task(description="Audit the codebase for quality issues"),

        # Tier 2: Frontend (should route to frontend-lead)
        Task(description="Design a React dashboard with responsive layout"),
        Task(description="Architect the state management approach for the UI"),

        # Tier 2: Backend (should route to backend-lead)
        Task(description="Design a REST API for user authentication"),
        Task(description="Architect the database schema for microservices"),

        # Tier 2: DevOps (should route to devops-lead)
        Task(description="Design a CI/CD pipeline for deployment"),
        Task(description="Plan the Kubernetes infrastructure architecture"),

        # Tier 3: Python implementation (should route to python-specialist)
        Task(description="Implement a FastAPI endpoint for user login"),
        Task(description="Write Python function to process async requests"),

        # Tier 3: Testing (should route to unit-test-engineer)
        Task(description="Write unit tests for the authentication service"),
        Task(description="Create test fixtures and mocks for the API"),

        # Tier 3: Documentation (should route to technical-writer)
        Task(description="Document the REST API endpoints"),
        Task(description="Write a tutorial for getting started with the system"),
    ]

    print(f"\n{'='*70}")
    print(f"ROUTING {len(test_tasks)} TEST TASKS")
    print("="*70)

    for i, task in enumerate(test_tasks, 1):
        print(f"\n{i}. Task: \"{task.description}\"")

        try:
            agent = router.route(task, agents)
            print(f"   ✅ Routed to: {agent.role} (tier={agent.tier}, spec={agent.specialization})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Get routing statistics
    print(f"\n{'='*70}")
    print("ROUTING STATISTICS")
    print("="*70)

    stats = router.get_routing_stats(test_tasks, agents)

    print(f"\nTotal tasks: {stats['total_tasks']}")

    print(f"\nTier Distribution:")
    print(f"  Tier 1 (Orchestration): {stats['tier_distribution'][1]} tasks ({stats['tier_1_percentage']:.1f}%)")
    print(f"  Tier 2 (Domain Leads):  {stats['tier_distribution'][2]} tasks ({stats['tier_2_percentage']:.1f}%)")
    print(f"  Tier 3 (Specialists):   {stats['tier_distribution'][3]} tasks ({stats['tier_3_percentage']:.1f}%)")

    print(f"\nDomain Distribution:")
    for domain, count in sorted(stats['domain_distribution'].items()):
        if count > 0:
            print(f"  {domain}: {count} tasks")

    print(f"\nAgent Utilization:")
    for agent_role, count in sorted(stats['agent_utilization'].items()):
        print(f"  {agent_role}: {count} tasks")

    # Validation checks
    print(f"\n{'='*70}")
    print("VALIDATION")
    print("="*70)

    tier_1_count = stats['tier_distribution'][1]
    tier_2_count = stats['tier_distribution'][2]
    tier_3_count = stats['tier_distribution'][3]

    checks = []

    # Check 1: All tasks routed
    if stats['total_tasks'] == len(test_tasks):
        checks.append(("All tasks routed", True))
    else:
        checks.append(("All tasks routed", False))

    # Check 2: Tier 1 agents used
    if tier_1_count > 0:
        checks.append(("Tier 1 agents utilized", True))
    else:
        checks.append(("Tier 1 agents utilized", False))

    # Check 3: Tier 2 agents used
    if tier_2_count > 0:
        checks.append(("Tier 2 agents utilized", True))
    else:
        checks.append(("Tier 2 agents utilized", False))

    # Check 4: Tier 3 agents used
    if tier_3_count > 0:
        checks.append(("Tier 3 agents utilized", True))
    else:
        checks.append(("Tier 3 agents utilized", False))

    # Check 5: All 8 agents used
    if len(stats['agent_utilization']) == 8:
        checks.append(("All 8 agents utilized", True))
    else:
        checks.append(("All 8 agents utilized", False))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")

    all_passed = all(passed for _, passed in checks)

    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED")
    else:
        print("❌ SOME VALIDATION CHECKS FAILED")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = test_routing()
    sys.exit(0 if success else 1)
