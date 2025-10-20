"""
Specialist Agent Definitions for Domain-Specific Codebase Analysis

Defines 5 specialist agents for deep, expert-level analysis:
1. Python Engineer - Code quality, patterns, refactoring
2. DSL Engineer - Language design, parsers, grammars
3. Category Theory Specialist - Mathematical abstractions, morphisms
4. HTN Expert - Hierarchical planning, graph theory, DAGs
5. Algorithms Expert - Complexity analysis, optimization, Big O

These complement existing generalist agents (architect, integration-architect, etc.)
for comprehensive multi-agent codebase analysis.

Usage:
    from specialist_agents import create_specialist_agents, create_theory_team

    specialists = create_specialist_agents()
    theory_team = create_theory_team(specialists)

    # Use with LLMAgentExecutor
    executor.execute(specialists["python_engineer"], task)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.entity import Agent, AgentTeam


def create_specialist_agents() -> dict[str, Agent]:
    """
    Create 5 domain specialist agents.

    Returns:
        dict: Mapping of specialist name to Agent instance
            Keys: python_engineer, dsl_engineer, category_theory_specialist,
                  htn_expert, algorithms_expert
    """

    specialists = {
        "python_engineer": Agent(
            role="python-engineer",
            capabilities=[
                "python",
                "code-quality",
                "refactoring",
                "patterns",
                "type-hints",
                "pythonic-idioms",
                "clean-code"
            ],
            tier=3
        ),

        "dsl_engineer": Agent(
            role="dsl-engineer",
            capabilities=[
                "dsl",
                "parsers",
                "grammars",
                "compilers",
                "lark",
                "language-design",
                "syntax-analysis"
            ],
            tier=3
        ),

        "category_theory_specialist": Agent(
            role="category-theory-specialist",
            capabilities=[
                "category-theory",
                "morphisms",
                "functors",
                "composition",
                "mathematical-abstractions",
                "type-theory"
            ],
            tier=3
        ),

        "htn_expert": Agent(
            role="htn-expert",
            capabilities=[
                "htn",
                "hierarchical-planning",
                "graph-theory",
                "dag",
                "topological-sort",
                "planning-algorithms",
                "graph-algorithms"
            ],
            tier=3
        ),

        "algorithms_expert": Agent(
            role="algorithms-expert",
            capabilities=[
                "algorithms",
                "complexity-analysis",
                "optimization",
                "big-o",
                "performance",
                "data-structures",
                "computational-complexity"
            ],
            tier=3
        ),

        "software_architect": Agent(
            role="software-architect",
            capabilities=[
                "architecture",
                "clean-architecture",
                "design-patterns",
                "solid-principles",
                "dependency-inversion",
                "system-design",
                "modularity"
            ],
            tier=3
        ),

        "integration_architect": Agent(
            role="integration-architect",
            capabilities=[
                "integration",
                "api-design",
                "tooling",
                "automation",
                "workflow-optimization",
                "feature-discovery",
                "extensibility"
            ],
            tier=3
        )
    }

    return specialists


def create_theory_team(specialists: dict[str, Agent]) -> AgentTeam:
    """
    Create Theory Team with 4 theoretical specialists.

    Python Engineer stays in Backend Team (practical engineering).
    Theory Team groups mathematical/CS theory experts together.

    Args:
        specialists: Dict of specialist agents from create_specialist_agents()

    Returns:
        AgentTeam: Theory Team instance with 4 specialists
    """

    theory_team = AgentTeam(
        name="Theory Team",
        domain="theoretical-cs",
        agents=[
            specialists["dsl_engineer"],
            specialists["category_theory_specialist"],
            specialists["htn_expert"],
            specialists["algorithms_expert"]
        ],
        lead_agent=specialists["algorithms_expert"]  # Most broadly applicable
    )

    return theory_team


def print_specialist_summary():
    """Print summary of specialist agents (for verification)."""

    specialists = create_specialist_agents()

    print("=" * 80)
    print("SPECIALIST AGENTS")
    print("=" * 80)
    print()

    for name, agent in specialists.items():
        print(f"Agent: {agent.role}")
        print(f"  Capabilities: {', '.join(agent.capabilities[:4])}...")
        print(f"  Tier: {agent.tier}")
        print()

    print("=" * 80)
    print(f"Total Specialists: {len(specialists)}")
    print("=" * 80)


if __name__ == "__main__":
    # Verification: Print specialist summary
    print_specialist_summary()

    # Test team creation
    specialists = create_specialist_agents()
    theory_team = create_theory_team(specialists)

    print(f"\nTheory Team: {theory_team.name}")
    print(f"  Domain: {theory_team.domain}")
    print(f"  Members: {len(theory_team.agents)}")
    print(f"  Lead: {theory_team.lead_agent.role}")
