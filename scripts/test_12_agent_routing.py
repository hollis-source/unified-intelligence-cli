#!/usr/bin/env python3
"""
Test 12-Agent Hierarchical Routing - Verify 3-tier routing with 12 agents.

Week 11 Phase 2: Validation script for scaled agent system.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task
from src.factories.agent_factory import AgentFactory
from src.routing import HierarchicalRouter


def test_routing():
    """Test hierarchical routing with 12-agent system."""

    print("="*70)
    print("12-AGENT HIERARCHICAL ROUTING TEST")
    print("="*70)

    # Create 12-agent system
    agent_factory = AgentFactory()
    agents = agent_factory.create_scaled_agents()

    print(f"\n✅ Created {len(agents)} agents:")

    # Group by tier
    tier_1 = [a for a in agents if a.tier == 1]
    tier_2 = [a for a in agents if a.tier == 2]
    tier_3 = [a for a in agents if a.tier == 3]

    print(f"\n Tier 1 (Orchestration): {len(tier_1)} agents")
    for agent in tier_1:
        print(f"    - {agent.role}")

    print(f"\n Tier 2 (Domain Leads): {len(tier_2)} agents")
    for agent in tier_2:
        print(f"    - {agent.role} (specialization={agent.specialization})")

    print(f"\n Tier 3 (Specialists): {len(tier_3)} agents")
    for agent in tier_3:
        print(f"    - {agent.role} (parent={agent.parent_agent}, spec={agent.specialization})")

    # Create hierarchical router
    router = HierarchicalRouter()

    # Test tasks covering all tiers and domains
    test_tasks = [
        # Tier 1: Planning (master-orchestrator)
        Task(description="Plan the overall architecture for a microservices system"),
        Task(description="Organize and prioritize the sprint backlog"),

        # Tier 1: QA (qa-lead)
        Task(description="Review code for SOLID principles and clean architecture"),
        Task(description="Audit the codebase for quality issues"),

        # Tier 2: Frontend Lead
        Task(description="Design a React dashboard with responsive layout"),
        Task(description="Architect the state management approach for the UI"),

        # Tier 2: Backend Lead
        Task(description="Design a REST API for user authentication"),
        Task(description="Architect the database schema for microservices"),

        # Tier 2: Testing Lead (NEW)
        Task(description="Design a comprehensive test strategy for the system"),
        Task(description="Plan test automation and coverage goals"),

        # Tier 2: Research Lead (NEW)
        Task(description="Research best practices for microservices architecture"),
        Task(description="Document the architecture decision records"),

        # Tier 2: DevOps Lead
        Task(description="Design a CI/CD pipeline for deployment"),
        Task(description="Plan the Kubernetes infrastructure architecture"),

        # Tier 3: Python Specialist
        Task(description="Implement a FastAPI endpoint for user login"),
        Task(description="Write Python function to process async requests"),

        # Tier 3: JS/TS Specialist (NEW)
        Task(description="Implement a React component for user profile"),
        Task(description="Write TypeScript interfaces for the API client"),

        # Tier 3: Unit Test Engineer
        Task(description="Write unit tests with pytest for the authentication service"),
        Task(description="Create test fixtures and mocks for unit testing the API"),

        # Tier 3: Integration Test Engineer (NEW)
        Task(description="Write end-to-end tests for the login flow"),
        Task(description="Create API integration tests with Postman"),

        # Tier 3: Technical Writer
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

    # Check 5: All 12 agents used
    if len(stats['agent_utilization']) == 12:
        checks.append(("All 12 agents utilized", True))
    else:
        checks.append((f"All 12 agents utilized (got {len(stats['agent_utilization'])})", False))

    # Check 6: New Tier 2 agents used
    new_tier_2 = ["testing-lead", "research-lead"]
    new_tier_2_used = all(agent in stats['agent_utilization'] for agent in new_tier_2)
    if new_tier_2_used:
        checks.append(("New Tier 2 agents (Testing, Research) utilized", True))
    else:
        checks.append(("New Tier 2 agents (Testing, Research) utilized", False))

    # Check 7: New Tier 3 agents used
    new_tier_3 = ["javascript-typescript-specialist", "integration-test-engineer"]
    new_tier_3_used = all(agent in stats['agent_utilization'] for agent in new_tier_3)
    if new_tier_3_used:
        checks.append(("New Tier 3 agents (JS/TS, Integration Test) utilized", True))
    else:
        checks.append(("New Tier 3 agents (JS/TS, Integration Test) utilized", False))

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
