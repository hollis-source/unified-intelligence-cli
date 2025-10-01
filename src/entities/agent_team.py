"""
Agent Team Entity - Groups of agents with internal workflow logic.

Week 12: Team-based architecture for scalable agent routing.

Clean Architecture: Core domain entity with no external dependencies.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from src.entities.agent import Agent, Task


@dataclass
class AgentTeam:
    """
    Agent team with internal workflow and routing logic.

    Week 12: Core abstraction for team-based agent architecture.

    Key Concepts:
    - Teams handle groups of related agents
    - Internal routing logic encapsulated per team
    - Lead-based hierarchy (lead delegates to specialists)
    - Domain-specific workflow patterns

    Benefits:
    - Simplified global routing (6 teams vs 12 agents)
    - Encapsulated team-specific logic
    - Scalable (add agents to teams, not router)
    - Natural hierarchy (mirrors real organizations)
    """

    name: str                           # Team name (e.g., "Frontend Team")
    domain: str                         # Primary domain (e.g., "frontend")
    agents: List[Agent]                 # All agents in team
    lead_agent: Optional[Agent] = None  # Team lead (if hierarchical)
    tier: int = 2                       # Primary tier (1=orchestration, 2=domain, 3=execution)

    def route_internally(self, task: Task) -> Agent:
        """
        Route task to appropriate agent within team.

        Override in subclasses for team-specific routing logic.
        Default: Route to lead if available, else first agent.

        Args:
            task: Task to route

        Returns:
            Agent within team to handle task

        Design Pattern: Strategy pattern - each team implements its own routing
        """
        # Default strategy: lead-based delegation
        if self.lead_agent:
            return self.lead_agent

        # Fallback: first agent in team
        return self.agents[0] if self.agents else None

    def get_agent(self, role: str) -> Optional[Agent]:
        """
        Get specific agent by role within team.

        Args:
            role: Agent role identifier

        Returns:
            Agent with matching role, or None
        """
        return next((agent for agent in self.agents if agent.role == role), None)

    def can_handle(self, task: Task) -> bool:
        """
        Check if team can handle task.

        Team can handle if any agent can handle.

        Args:
            task: Task to check

        Returns:
            True if at least one agent can handle task
        """
        return any(agent.can_handle(task) for agent in self.agents)

    def get_all_capabilities(self) -> List[str]:
        """
        Get combined capabilities of all team members.

        Returns:
            Unique list of all capabilities across team
        """
        capabilities = set()
        for agent in self.agents:
            capabilities.update(agent.capabilities)
        return sorted(capabilities)

    def __repr__(self) -> str:
        """String representation for debugging."""
        agent_roles = [a.role for a in self.agents]
        lead_str = f" (lead: {self.lead_agent.role})" if self.lead_agent else ""
        return f"AgentTeam('{self.name}', domain='{self.domain}', agents={agent_roles}{lead_str})"


@dataclass
class FrontendTeam(AgentTeam):
    """
    Frontend team: UI/UX development.

    Team Structure:
    - frontend-lead (Tier 2): Designs UI architecture
    - javascript-typescript-specialist (Tier 3): Implements components

    Workflow:
    - Design tasks → Lead
    - Implementation tasks → Specialist
    """

    def route_internally(self, task: Task) -> Agent:
        """Route frontend tasks based on design vs implementation."""
        desc = task.description.lower()

        # Design/architecture → Lead
        design_keywords = ['design', 'architecture', 'architect', 'layout', 'structure']
        if any(kw in desc for kw in design_keywords):
            return self.lead_agent or self.agents[0]

        # Implementation → Specialist
        specialist = self.get_agent("javascript-typescript-specialist")
        if specialist:
            impl_keywords = ['implement', 'write', 'create', 'code', 'build']
            if any(kw in desc for kw in impl_keywords):
                return specialist

        # Default: Lead handles (can delegate later)
        return self.lead_agent or self.agents[0]


@dataclass
class BackendTeam(AgentTeam):
    """
    Backend team: API, database, server-side logic.

    Team Structure:
    - backend-lead (Tier 2): Designs APIs and architecture
    - python-specialist (Tier 3): Implements backend code

    Workflow:
    - Design tasks → Lead
    - Implementation tasks → Specialist
    """

    def route_internally(self, task: Task) -> Agent:
        """Route backend tasks based on design vs implementation."""
        desc = task.description.lower()

        # Design/architecture → Lead
        design_keywords = ['design', 'architecture', 'architect', 'schema', 'api design']
        if any(kw in desc for kw in design_keywords):
            return self.lead_agent or self.agents[0]

        # Implementation → Specialist
        specialist = self.get_agent("python-specialist")
        if specialist:
            impl_keywords = ['implement', 'write', 'create', 'code', 'build', 'function']
            if any(kw in desc for kw in impl_keywords):
                return specialist

        # Default: Lead handles
        return self.lead_agent or self.agents[0]


@dataclass
class TestingTeam(AgentTeam):
    """
    Testing team: All testing concerns (unit, integration, E2E).

    Team Structure:
    - testing-lead (Tier 2): Test strategy and planning
    - unit-test-engineer (Tier 3): Unit tests, mocking
    - integration-test-engineer (Tier 3): Integration tests, E2E

    Workflow:
    - Strategy/planning → Lead
    - Unit tests → Unit engineer
    - Integration/E2E → Integration engineer

    Week 12: Solves integration-test-engineer underutilization by encapsulating
    test-specific routing logic within team.
    """

    def route_internally(self, task: Task) -> Agent:
        """
        Route testing tasks based on test type.

        This is where team-based architecture shines:
        - Team understands nuanced differences (unit vs integration)
        - Domain-specific keywords work better in context
        - No fuzzy matching overlap issues
        """
        desc = task.description.lower()

        # Strategy/planning → Lead
        strategy_keywords = ['strategy', 'planning', 'plan', 'approach', 'coverage']
        if any(kw in desc for kw in strategy_keywords):
            return self.lead_agent or self.agents[0]

        # Unit tests → Unit engineer (specific)
        unit_engineer = self.get_agent("unit-test-engineer")
        if unit_engineer:
            unit_keywords = ['unit', 'unittest', 'mock', 'fixture', 'stub', 'spy']
            if any(kw in desc for kw in unit_keywords):
                return unit_engineer

        # Integration/E2E → Integration engineer (broad)
        integration_engineer = self.get_agent("integration-test-engineer")
        if integration_engineer:
            integration_keywords = [
                'integration', 'e2e', 'end-to-end', 'end to end',
                'selenium', 'cypress', 'postman', 'api test'
            ]
            if any(kw in desc for kw in integration_keywords):
                return integration_engineer

        # Generic "test" → Default to unit engineer (most common)
        if 'test' in desc and unit_engineer:
            return unit_engineer

        # Fallback: Lead triages
        return self.lead_agent or self.agents[0]


@dataclass
class InfrastructureTeam(AgentTeam):
    """
    Infrastructure team: DevOps, deployment, CI/CD.

    Team Structure:
    - devops-lead (Tier 2): Infrastructure architecture

    Workflow:
    - All DevOps tasks → Lead (single-agent team)
    """

    def route_internally(self, task: Task) -> Agent:
        """Route to DevOps lead (single-agent team)."""
        return self.lead_agent or self.agents[0]


@dataclass
class ResearchTeam(AgentTeam):
    """
    Research & Documentation team: Knowledge management.

    Team Structure:
    - research-lead (Tier 2): Research strategy, ADRs
    - technical-writer (Tier 3): Documentation, tutorials

    Workflow:
    - Research/strategy → Lead
    - Documentation writing → Technical writer
    """

    def route_internally(self, task: Task) -> Agent:
        """Route research tasks based on research vs documentation."""
        desc = task.description.lower()

        # Documentation writing → Technical writer
        writer = self.get_agent("technical-writer")
        if writer:
            doc_keywords = [
                'document', 'write', 'tutorial', 'guide',
                'readme', 'changelog', 'api docs'
            ]
            if any(kw in desc for kw in doc_keywords):
                return writer

        # Research/strategy → Lead
        return self.lead_agent or self.agents[0]


@dataclass
class OrchestrationTeam(AgentTeam):
    """
    Orchestration team: High-level planning and coordination.

    Team Structure:
    - master-orchestrator (Tier 1): Planning, coordination

    Workflow:
    - All planning tasks → Orchestrator (single-agent team)
    """

    def route_internally(self, task: Task) -> Agent:
        """Route to orchestrator (single-agent team)."""
        return self.lead_agent or self.agents[0]


@dataclass
class QualityAssuranceTeam(AgentTeam):
    """
    Quality Assurance team: Code review, architecture validation.

    Team Structure:
    - qa-lead (Tier 1): Review, audit, quality validation

    Workflow:
    - All QA tasks → QA Lead (single-agent team)
    """

    def route_internally(self, task: Task) -> Agent:
        """Route to QA lead (single-agent team)."""
        return self.lead_agent or self.agents[0]
