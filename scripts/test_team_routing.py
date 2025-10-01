#!/usr/bin/env python3
"""
Test Team-Based Routing - Validate team routing with 12-agent system.

Week 12: Validation script for team-based agent architecture.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entities import Task
from src.factories import TeamFactory
from src.routing.team_router import TeamRouter


def test_team_routing():
    """Test team-based routing with 12-agent system."""

    print("="*70)
    print("TEAM-BASED ROUTING TEST")
    print("="*70)

    # Create teams
    team_factory = TeamFactory()
    teams = team_factory.create_scaled_teams()

    print(f"\n✅ Created {len(teams)} teams:")
    for team in teams:
        agent_count = len(team.agents)
        agent_roles = [a.role for a in team.agents]
        lead_info = f" (lead: {team.lead_agent.role})" if team.lead_agent else ""
        print(f"  - {team.name}: {agent_count} agents{lead_info}")
        for role in agent_roles:
            print(f"      • {role}")

    # Get total agent count
    total_agents = sum(len(team.agents) for team in teams)
    print(f"\n✅ Total agents across teams: {total_agents}")

    # Create router
    router = TeamRouter()

    # Test tasks covering all teams
    test_tasks = [
        # Orchestration Team
        Task(description="Plan the overall architecture for a microservices system"),
        Task(description="Organize and prioritize the sprint backlog"),

        # QA Team
        Task(description="Review code for SOLID principles and clean architecture"),
        Task(description="Audit the codebase for quality issues"),

        # Frontend Team (design → lead, implementation → specialist)
        Task(description="Design a React dashboard with responsive layout"),
        Task(description="Implement a React component for user profile"),
        Task(description="Write TypeScript interfaces for the API client"),

        # Backend Team (design → lead, implementation → specialist)
        Task(description="Design a REST API for user authentication"),
        Task(description="Implement a FastAPI endpoint for user login"),
        Task(description="Write Python function to process async requests"),

        # Testing Team (strategy → lead, unit → unit engineer, integration → integration engineer)
        Task(description="Design a comprehensive test strategy for the system"),
        Task(description="Write unit tests with pytest for the authentication service"),
        Task(description="Create test fixtures and mocks for unit testing the API"),
        Task(description="Write end-to-end tests for the login flow"),
        Task(description="Create API integration tests with Postman"),

        # Infrastructure Team
        Task(description="Design a CI/CD pipeline for deployment"),
        Task(description="Plan the Kubernetes infrastructure architecture"),

        # Research Team (research → lead, documentation → writer)
        Task(description="Research best practices for microservices architecture"),
        Task(description="Document the REST API endpoints"),
        Task(description="Write a tutorial for getting started with the system"),
    ]

    print(f"\n{'='*70}")
    print(f"ROUTING {len(test_tasks)} TEST TASKS")
    print("="*70)

    results = []
    for i, task in enumerate(test_tasks, 1):
        print(f"\n{i}. Task: \"{task.description}\"")

        try:
            agent = router.route(task, teams)

            # Find which team this agent belongs to
            team = next((t for t in teams if agent in t.agents), None)
            team_name = team.name if team else "Unknown"

            print(f"   ✅ Routed to: {team_name} → {agent.role}")
            results.append((task, team, agent, True))
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append((task, None, None, False))

    # Get routing statistics
    print(f"\n{'='*70}")
    print("ROUTING STATISTICS")
    print("="*70)

    stats = router.get_routing_stats(test_tasks, teams)

    print(f"\nTotal tasks: {stats['total_tasks']}")
    print(f"Successful routes: {stats['successful_routes']}/{stats['total_tasks']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")

    print(f"\nTeam Distribution:")
    for team_name, count in sorted(stats['team_distribution'].items()):
        percentage = (count / stats['total_tasks'] * 100) if stats['total_tasks'] > 0 else 0
        print(f"  {team_name}: {count} tasks ({percentage:.1f}%)")

    print(f"\nAgent Utilization:")
    for agent_role, count in sorted(stats['agent_utilization'].items()):
        print(f"  {agent_role}: {count} tasks")

    print(f"\nTier Distribution:")
    for tier, count in sorted(stats['tier_distribution'].items()):
        percentage = (count / stats['total_tasks'] * 100) if stats['total_tasks'] > 0 else 0
        print(f"  Tier {tier}: {count} tasks ({percentage:.1f}%)")

    # Validation checks
    print(f"\n{'='*70}")
    print("VALIDATION")
    print("="*70)

    checks = []

    # Check 1: All tasks routed
    if stats['successful_routes'] == len(test_tasks):
        checks.append(("All tasks routed successfully", True))
    else:
        checks.append((f"All tasks routed (got {stats['successful_routes']}/{len(test_tasks)})", False))

    # Check 2: All teams utilized
    if stats['unique_teams_used'] == len(teams):
        checks.append(("All teams utilized", True))
    else:
        checks.append((f"All teams utilized (got {stats['unique_teams_used']}/{len(teams)})", False))

    # Check 3: Reasonable agent utilization (at least 75% of agents)
    agent_utilization_rate = stats['unique_agents_used'] / total_agents * 100
    if agent_utilization_rate >= 75:
        checks.append((f"Good agent utilization ({agent_utilization_rate:.0f}%)", True))
    else:
        checks.append((f"Agent utilization low ({agent_utilization_rate:.0f}%)", False))

    # Check 4: Proper tier distribution
    tier_1_pct = stats['tier_distribution'][1] / stats['total_tasks'] * 100 if stats['total_tasks'] > 0 else 0
    tier_2_pct = stats['tier_distribution'][2] / stats['total_tasks'] * 100 if stats['total_tasks'] > 0 else 0
    tier_3_pct = stats['tier_distribution'][3] / stats['total_tasks'] * 100 if stats['total_tasks'] > 0 else 0

    if tier_1_pct > 0 and tier_2_pct > 0 and tier_3_pct > 0:
        checks.append(("All tiers utilized", True))
    else:
        checks.append(("All tiers utilized", False))

    # Check 5: Testing team internal routing (unit vs integration)
    unit_engineer_used = 'unit-test-engineer' in stats['agent_utilization']
    integration_engineer_used = 'integration-test-engineer' in stats['agent_utilization']
    if unit_engineer_used and integration_engineer_used:
        checks.append(("Testing team internal routing working (both engineers used)", True))
    else:
        if unit_engineer_used:
            checks.append(("Testing team: unit-test-engineer used", True))
        if integration_engineer_used:
            checks.append(("Testing team: integration-test-engineer used", True))
        if not unit_engineer_used and not integration_engineer_used:
            checks.append(("Testing team internal routing", False))

    # Check 6: Frontend team internal routing (lead vs specialist)
    frontend_lead_used = 'frontend-lead' in stats['agent_utilization']
    js_specialist_used = 'javascript-typescript-specialist' in stats['agent_utilization']
    if frontend_lead_used and js_specialist_used:
        checks.append(("Frontend team internal routing working (lead and specialist used)", True))
    else:
        checks.append(("Frontend team internal routing", False))

    # Print results
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")

    all_passed = all(passed for _, passed in checks)

    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED")
    else:
        print("⚠️  SOME VALIDATION CHECKS NEED ATTENTION")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    success = test_team_routing()
    sys.exit(0 if success else 1)
