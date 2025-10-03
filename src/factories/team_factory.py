"""
Team Factory - Creates agent teams from individual agents.

Week 12: Team-based architecture factory.

Clean Architecture: Factory pattern for team creation.
"""

from typing import List
from src.entities import (
    Agent,
    AgentTeam,
    FrontendTeam,
    BackendTeam,
    TestingTeam,
    InfrastructureTeam,
    ResearchTeam,
    OrchestrationTeam,
    QualityAssuranceTeam,
    CategoryTheoryTeam,
    DSLTeam
)
from src.factories.agent_factory import AgentFactory


class TeamFactory:
    """
    Factory for creating agent teams.

    Week 12: Core factory for team-based agent architecture.

    Responsibilities:
    - Create agent teams from individual agents
    - Group agents by domain
    - Establish team hierarchies (lead → specialists)

    Benefits:
    - Encapsulates team creation logic
    - Reuses existing AgentFactory
    - Maintains backward compatibility
    """

    def __init__(self, agent_factory: AgentFactory = None):
        """
        Initialize team factory.

        Args:
            agent_factory: Optional agent factory (creates default if not provided)
        """
        self.agent_factory = agent_factory or AgentFactory()

    def create_scaled_teams(self) -> List[AgentTeam]:
        """
        Create 9 teams from 16-agent scaled system.

        Week 12: Primary team creation method (7 teams, 12 agents).
        Week 13: Added Category Theory & DSL teams (9 teams, 16 agents).

        Team Structure:
        1. Orchestration Team (1 agent) - Planning
        2. Quality Assurance Team (1 agent) - Review
        3. Frontend Team (2 agents) - UI development
        4. Backend Team (2 agents) - API development
        5. Testing Team (3 agents) - All testing
        6. Infrastructure Team (1 agent) - DevOps
        7. Research Team (2 agents) - Research & docs
        8. Category Theory Team (2 agents) - DSL composition & mathematical foundations
        9. DSL Team (2 agents) - DSL deployment & task engineering

        Total: 16 agents across 9 teams

        Returns:
            List of 9 agent teams
        """
        # Get all 16 agents (Week 13: includes Category Theory & DSL specialists)
        agents = self.agent_factory.create_scaled_agents()
        agent_map = {agent.role: agent for agent in agents}

        teams = []

        # Team 1: Orchestration (Tier 1)
        orchestrator = agent_map.get("master-orchestrator")
        if orchestrator:
            teams.append(OrchestrationTeam(
                name="Orchestration",
                domain="general",
                agents=[orchestrator],
                lead_agent=orchestrator,
                tier=1
            ))

        # Team 2: Quality Assurance (Tier 1)
        qa_lead = agent_map.get("qa-lead")
        if qa_lead:
            teams.append(QualityAssuranceTeam(
                name="Quality Assurance",
                domain="quality",
                agents=[qa_lead],
                lead_agent=qa_lead,
                tier=1
            ))

        # Team 3: Frontend (Tier 2 lead + Tier 3 specialist)
        frontend_lead = agent_map.get("frontend-lead")
        js_specialist = agent_map.get("javascript-typescript-specialist")
        if frontend_lead:
            frontend_agents = [frontend_lead]
            if js_specialist:
                frontend_agents.append(js_specialist)

            teams.append(FrontendTeam(
                name="Frontend",
                domain="frontend",
                agents=frontend_agents,
                lead_agent=frontend_lead,
                tier=2
            ))

        # Team 4: Backend (Tier 2 lead + Tier 3 specialist)
        backend_lead = agent_map.get("backend-lead")
        python_specialist = agent_map.get("python-specialist")
        if backend_lead:
            backend_agents = [backend_lead]
            if python_specialist:
                backend_agents.append(python_specialist)

            teams.append(BackendTeam(
                name="Backend",
                domain="backend",
                agents=backend_agents,
                lead_agent=backend_lead,
                tier=2
            ))

        # Team 5: Testing (Tier 2 lead + 2 Tier 3 specialists)
        testing_lead = agent_map.get("testing-lead")
        unit_engineer = agent_map.get("unit-test-engineer")
        integration_engineer = agent_map.get("integration-test-engineer")
        if testing_lead:
            testing_agents = [testing_lead]
            if unit_engineer:
                testing_agents.append(unit_engineer)
            if integration_engineer:
                testing_agents.append(integration_engineer)

            teams.append(TestingTeam(
                name="Testing",
                domain="testing",
                agents=testing_agents,
                lead_agent=testing_lead,
                tier=2
            ))

        # Team 6: Infrastructure (Tier 2 DevOps)
        devops_lead = agent_map.get("devops-lead")
        if devops_lead:
            teams.append(InfrastructureTeam(
                name="Infrastructure",
                domain="devops",
                agents=[devops_lead],
                lead_agent=devops_lead,
                tier=2
            ))

        # Team 7: Research & Documentation (Tier 2 lead + Tier 3 specialist)
        research_lead = agent_map.get("research-lead")
        tech_writer = agent_map.get("technical-writer")
        if research_lead:
            research_agents = [research_lead]
            if tech_writer:
                research_agents.append(tech_writer)

            teams.append(ResearchTeam(
                name="Research",
                domain="research",
                agents=research_agents,
                lead_agent=research_lead,
                tier=2
            ))

        # Team 8: Category Theory (Week 13: DSL & mathematical foundations)
        ct_expert = agent_map.get("category-theory-expert")
        dsl_architect = agent_map.get("dsl-architect")
        if ct_expert:
            ct_agents = [ct_expert]
            if dsl_architect:
                ct_agents.append(dsl_architect)

            teams.append(CategoryTheoryTeam(
                name="Category Theory",
                domain="category-theory",
                agents=ct_agents,
                lead_agent=ct_expert,
                tier=2
            ))

        # Team 9: DSL Implementation (Week 13: DSL deployment & task engineering)
        dsl_specialist = agent_map.get("dsl-deployment-specialist")
        dsl_engineer = agent_map.get("dsl-task-engineer")
        if dsl_specialist:
            dsl_agents = [dsl_specialist]
            if dsl_engineer:
                dsl_agents.append(dsl_engineer)

            teams.append(DSLTeam(
                name="DSL",
                domain="dsl",
                agents=dsl_agents,
                lead_agent=dsl_specialist,
                tier=2
            ))

        return teams

    def create_extended_teams(self) -> List[AgentTeam]:
        """
        Create teams from 8-agent extended system.

        Week 12: Backward compatibility with Phase 1.

        Team Structure:
        1. Orchestration Team (1 agent)
        2. Quality Assurance Team (1 agent)
        3. Frontend Team (1 agent) - No specialist yet
        4. Backend Team (2 agents) - Lead + Python specialist
        5. Infrastructure Team (1 agent)
        6. Research Team (2 agents) - Lead + Technical writer

        Total: 8 agents across 6 teams (Testing team not yet created in Phase 1)

        Returns:
            List of 6 agent teams
        """
        # Get 8 agents from extended mode
        agents = self.agent_factory.create_extended_agents()
        agent_map = {agent.role: agent for agent in agents}

        teams = []

        # Team 1: Orchestration
        orchestrator = agent_map.get("master-orchestrator")
        if orchestrator:
            teams.append(OrchestrationTeam(
                name="Orchestration",
                domain="general",
                agents=[orchestrator],
                lead_agent=orchestrator,
                tier=1
            ))

        # Team 2: Quality Assurance
        qa_lead = agent_map.get("qa-lead")
        if qa_lead:
            teams.append(QualityAssuranceTeam(
                name="Quality Assurance",
                domain="quality",
                agents=[qa_lead],
                lead_agent=qa_lead,
                tier=1
            ))

        # Team 3: Frontend (just lead, no specialist yet in Phase 1)
        frontend_lead = agent_map.get("frontend-lead")
        if frontend_lead:
            teams.append(FrontendTeam(
                name="Frontend",
                domain="frontend",
                agents=[frontend_lead],
                lead_agent=frontend_lead,
                tier=2
            ))

        # Team 4: Backend
        backend_lead = agent_map.get("backend-lead")
        python_specialist = agent_map.get("python-specialist")
        if backend_lead:
            backend_agents = [backend_lead]
            if python_specialist:
                backend_agents.append(python_specialist)

            teams.append(BackendTeam(
                name="Backend",
                domain="backend",
                agents=backend_agents,
                lead_agent=backend_lead,
                tier=2
            ))

        # Team 5: Infrastructure
        devops_lead = agent_map.get("devops-lead")
        if devops_lead:
            teams.append(InfrastructureTeam(
                name="Infrastructure",
                domain="devops",
                agents=[devops_lead],
                lead_agent=devops_lead,
                tier=2
            ))

        # Team 6: Research (In Phase 1, unit-test-engineer and technical-writer
        # don't have proper leads, so we treat them as single-agent teams)
        unit_engineer = agent_map.get("unit-test-engineer")
        tech_writer = agent_map.get("technical-writer")

        # Note: Phase 1 didn't have testing-lead or research-lead
        # So we create ad-hoc teams for these agents
        if unit_engineer:
            teams.append(TestingTeam(
                name="Testing",
                domain="testing",
                agents=[unit_engineer],
                lead_agent=unit_engineer,  # Self-lead
                tier=3
            ))

        if tech_writer:
            teams.append(ResearchTeam(
                name="Research",
                domain="research",
                agents=[tech_writer],
                lead_agent=tech_writer,  # Self-lead
                tier=3
            ))

        return teams

    def create_default_teams(self) -> List[AgentTeam]:
        """
        Create teams from 5-agent default system.

        Week 12: Backward compatibility with baseline.

        Note: Default mode (5 agents) doesn't use teams.
        This method exists for API consistency but returns
        individual agents wrapped as single-agent teams.

        Team Structure:
        - Each agent becomes its own team
        - No lead hierarchy
        - Simple flat structure

        Returns:
            List of 5 single-agent teams
        """
        # Get 5 default agents
        agents = self.agent_factory.create_default_agents()

        # Wrap each agent in a generic team
        teams = []
        for agent in agents:
            # Determine domain from agent role
            domain_map = {
                "coder": "backend",
                "tester": "testing",
                "reviewer": "quality",
                "coordinator": "general",
                "researcher": "research"
            }
            domain = domain_map.get(agent.role, "general")

            teams.append(AgentTeam(
                name=agent.role.title(),
                domain=domain,
                agents=[agent],
                lead_agent=agent,
                tier=agent.tier
            ))

        return teams

    def get_all_agents_from_teams(self, teams: List[AgentTeam]) -> List[Agent]:
        """
        Extract all individual agents from teams.

        Utility method for backward compatibility with agent-based code.

        Args:
            teams: List of agent teams

        Returns:
            Flat list of all agents across all teams
        """
        agents = []
        for team in teams:
            agents.extend(team.agents)
        return agents

    def get_team_summary(self, teams: List[AgentTeam]) -> dict:
        """
        Get summary statistics for teams.

        Args:
            teams: List of agent teams

        Returns:
            Dictionary with team statistics
        """
        total_agents = sum(len(team.agents) for team in teams)
        teams_with_leads = sum(1 for team in teams if team.lead_agent)

        tier_distribution = {1: 0, 2: 0, 3: 0}
        for team in teams:
            for agent in team.agents:
                tier_distribution[agent.tier] += 1

        return {
            "team_count": len(teams),
            "total_agents": total_agents,
            "teams_with_leads": teams_with_leads,
            "tier_distribution": tier_distribution,
            "average_team_size": total_agents / len(teams) if teams else 0
        }
