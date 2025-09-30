"""
Realistic User Scenarios - Based on actual use cases.

These scenarios simulate how real users would interact with ui-cli.
"""

import asyncio
from user_agent import UserSimulationAgent, UserAction


async def run_all_scenarios():
    """Run all realistic user scenarios."""

    agent = UserSimulationAgent(provider="mock", verbose=True)

    print("\n" + "="*80)
    print("USER SIMULATION TESTING - Finding Real Issues")
    print("="*80 + "\n")

    # Scenario 1: New User - First Task
    print("\n--- Scenario 1: New User First Experience ---")
    await agent.simulate_scenario(
        scenario_name="new_user_first_task",
        actions=[
            UserAction(
                action_type="submit_task",
                task_description="Write a Python function to calculate fibonacci numbers",
                expected_outcome="fibonacci"
            )
        ]
    )

    # Scenario 2: Code Review Workflow
    print("\n--- Scenario 2: Code Review Workflow ---")
    await agent.simulate_scenario(
        scenario_name="code_review_workflow",
        actions=[
            UserAction(
                action_type="multi_task_workflow",
                task_description="Review code, suggest improvements, run tests",
                expected_outcome="review"
            )
        ]
    )

    # Scenario 3: Research Task
    print("\n--- Scenario 3: Research Task ---")
    await agent.simulate_scenario(
        scenario_name="research_task",
        actions=[
            UserAction(
                action_type="submit_task",
                task_description="Research best practices for Python async programming",
                expected_outcome="async"
            )
        ]
    )

    # Scenario 4: Tool Usage (File Operations)
    print("\n--- Scenario 4: Tool Usage ---")
    await agent.simulate_scenario(
        scenario_name="tool_usage",
        actions=[
            UserAction(
                action_type="submit_task",
                task_description="List all Python files in the current directory",
                expected_outcome=".py"
            )
        ]
    )

    # Scenario 5: Stress Test
    print("\n--- Scenario 5: Stress Test (10 concurrent tasks) ---")
    await agent.simulate_scenario(
        scenario_name="stress_test",
        actions=[
            UserAction(
                action_type="stress_test",
                task_description="10 concurrent tasks",
                expected_outcome="completed"
            )
        ]
    )

    # Scenario 6: Error Handling
    print("\n--- Scenario 6: Error Handling ---")
    await agent.simulate_scenario(
        scenario_name="error_handling",
        actions=[
            UserAction(
                action_type="submit_task",
                task_description="",  # Empty task - should fail gracefully
                expected_outcome="error"
            )
        ]
    )

    # Generate comprehensive report
    print("\n" + "="*80)
    print("GENERATING TEST REPORT")
    print("="*80 + "\n")

    report = agent.generate_report(output_file="user_simulation_report.json")

    # Print summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    print(f"Scenarios Run: {report['summary']['scenarios_run']}")
    print(f"Total Actions: {report['summary']['total_actions']}")
    print(f"Successes: {report['summary']['total_successes']}")
    print(f"Failures: {report['summary']['total_failures']}")
    print(f"Success Rate: {report['summary']['success_rate'] * 100:.1f}%")
    print(f"Total Errors: {report['summary']['total_errors']}")

    if report['critical_issues']:
        print("\n" + "-"*80)
        print("CRITICAL ISSUES FOUND:")
        print("-"*80)
        for i, issue in enumerate(report['critical_issues'], 1):
            print(f"\n{i}. {issue}")

    print("\n" + "="*80)
    print(f"Full report saved to: user_simulation_report.json")
    print("="*80 + "\n")

    return report


if __name__ == "__main__":
    asyncio.run(run_all_scenarios())