"""
Hierarchical Router - Routes tasks to appropriate agents in 3-tier architecture.

Clean Architecture: Strategy pattern for multi-level routing.
Week 11: Core infrastructure for 15-agent scaling.
"""

import re
import logging
from typing import List, Optional, Tuple
from src.entities import Task, Agent
from src.routing.orchestrator_router import OrchestratorRouter
from src.routing.domain_classifier import DomainClassifier


logger = logging.getLogger(__name__)


class HierarchicalRouter:
    """
    Routes tasks through 3-tier hierarchical agent architecture.

    Routing Strategy:
        Phase 1: Orchestration mode (SDK vs simple)
        Phase 2: Domain classification (frontend, backend, testing, etc.)
        Phase 3: Tier selection (1=orchestration, 2=domain lead, 3=specialist)
        Phase 4: Agent selection (specific agent for task)

    3-Tier Architecture:
        Tier 1: Planning & Coordination (2 agents)
            - Master Orchestrator
            - QA Lead
        Tier 2: Domain Leads (5 agents)
            - Frontend Lead, Backend Lead, Testing Lead, Research Lead, DevOps Lead
        Tier 3: Specialized Executors (8 agents)
            - Python Specialist, JS/TS Specialist, Unit Test Engineer, etc.

    Clean Code: Single responsibility - hierarchical routing logic only.
    """

    # Patterns for tier selection
    TIER_1_PATTERNS = [
        # Planning & coordination (Master Orchestrator)
        r"\bplan\b", r"planning", r"\borganize\b", r"coordinate",
        r"orchestrate", r"\bmanage\b", r"prioritize", r"schedule",
        r"delegate", r"overall", r"roadmap",
        r"overall.*strategy", r"project.*strategy", r"sprint.*backlog",
        # Quality assurance & review (QA Lead)
        r"\breview\b", r"code review", r"\baudit\b", r"auditing",
        r"inspect", r"assess", r"evaluate.*quality", r"quality.*check",
        r"\bsolid\b", r"clean code", r"clean architecture",
        r"architecture.*review", r"best practices", r"standards",
        r"\bqa\b lead", r"quality assurance"
    ]

    TIER_2_PATTERNS = [
        # Domain-specific design & architecture
        r"\bdesign\b", r"architecture", r"architecting",
        r"system design", r"high-level", r"approach",
        # Domain-specific strategy (more specific than Tier 1)
        r"test strategy", r"testing strategy", r"qa strategy",
        r"test planning", r"test architecture",
        r"frontend.*design", r"backend.*design", r"api.*design",
        r"database.*design", r"infrastructure.*design",
        r"documentation strategy", r"research.*approach"
    ]

    # Tier 3 is default for implementation tasks (no explicit patterns needed)

    def __init__(self, orchestrator_router: Optional[OrchestratorRouter] = None,
                 domain_classifier: Optional[DomainClassifier] = None):
        """
        Initialize hierarchical router.

        Args:
            orchestrator_router: Router for orchestration mode (optional, creates default)
            domain_classifier: Classifier for domain detection (optional, creates default)
        """
        self.orchestrator_router = orchestrator_router or OrchestratorRouter()
        self.domain_classifier = domain_classifier or DomainClassifier()

        # Compile tier patterns
        self._tier_1_regex = [re.compile(p, re.IGNORECASE) for p in self.TIER_1_PATTERNS]
        self._tier_2_regex = [re.compile(p, re.IGNORECASE) for p in self.TIER_2_PATTERNS]

        logger.info("HierarchicalRouter initialized (3-tier architecture)")

    def route(self, task: Task, agents: List[Agent]) -> Agent:
        """
        Route task to appropriate agent in hierarchy.

        Args:
            task: Task to route
            agents: Available agents

        Returns:
            Selected agent

        Raises:
            ValueError: If no suitable agent found

        Strategy:
            1. Determine orchestration mode (SDK vs simple)
            2. Classify domain (frontend, backend, etc.)
            3. Select tier (1, 2, or 3)
            4. Find agent matching (domain, tier, capabilities)
        """
        # Phase 1: Orchestration mode (informational, doesn't affect agent selection)
        mode = self.orchestrator_router.route(task)
        logger.debug(f"Task routed to '{mode}' orchestration mode")

        # Phase 2: Domain classification
        domain = self.domain_classifier.classify(task)
        logger.debug(f"Task classified as domain '{domain}'")

        # Phase 3: Tier selection
        tier = self._determine_tier(task, domain)
        logger.debug(f"Task requires tier {tier} agent")

        # Phase 4: Agent selection
        agent = self._select_agent(task, agents, domain, tier)

        if agent:
            logger.info(
                f"Task '{task.description[:50]}...' routed to "
                f"{agent.role} (tier={agent.tier}, domain={domain}, mode={mode})"
            )
            return agent

        # Fallback: Use capability-based matching (backward compatibility)
        logger.warning(f"No tier-{tier} agent found for domain '{domain}', using capability fallback")
        return self._fallback_agent_selection(task, agents)

    def _determine_tier(self, task: Task, domain: str) -> int:
        """
        Determine which tier should handle task.

        Args:
            task: Task to analyze
            domain: Classified domain

        Returns:
            Tier number (1, 2, or 3)

        Strategy:
            - Tier 1: Planning, coordination, high-level strategy
            - Tier 2: Domain-level design, architecture
            - Tier 3: Implementation, execution (default)
        """
        description = task.description.lower()

        # Check Tier 1 patterns (orchestration, planning)
        for pattern in self._tier_1_regex:
            if pattern.search(description):
                logger.debug(f"Tier 1 pattern matched: {pattern.pattern}")
                return 1

        # Check Tier 2 patterns (design, architecture)
        for pattern in self._tier_2_regex:
            if pattern.search(description):
                logger.debug(f"Tier 2 pattern matched: {pattern.pattern}")
                return 2

        # Default: Tier 3 (implementation, execution)
        logger.debug("No tier-specific patterns matched, defaulting to Tier 3")
        return 3

    def _select_agent(self, task: Task, agents: List[Agent],
                      domain: str, tier: int) -> Optional[Agent]:
        """
        Select specific agent based on domain, tier, and capabilities.

        Args:
            task: Task to route
            agents: Available agents
            domain: Task domain
            tier: Target tier

        Returns:
            Selected agent or None

        Selection Priority:
            1. Exact match: tier + domain + can_handle
            2. Tier + can_handle (ignore domain)
            3. None (triggers fallback)
        """
        # Priority 1: Exact match (tier + domain + can_handle)
        candidates = [
            agent for agent in agents
            if agent.tier == tier
            and (agent.specialization == domain or domain == "general")
            and agent.can_handle(task)
        ]

        if candidates:
            # Return first candidate (could add load balancing here)
            agent = candidates[0]
            logger.debug(f"Exact match: {agent.role} (tier={tier}, domain={domain})")
            return agent

        # Priority 2: Tier + can_handle (ignore domain)
        candidates = [
            agent for agent in agents
            if agent.tier == tier and agent.can_handle(task)
        ]

        if candidates:
            agent = candidates[0]
            logger.debug(f"Tier match: {agent.role} (tier={tier}, domain mismatch)")
            return agent

        # No match
        logger.debug(f"No agent found for tier={tier}, domain={domain}")
        return None

    def _fallback_agent_selection(self, task: Task, agents: List[Agent]) -> Agent:
        """
        Fallback agent selection using capability matching only.

        Args:
            task: Task to route
            agents: Available agents

        Returns:
            Agent with best capability match

        Raises:
            ValueError: If no agent can handle task

        Backward Compatibility: Ensures existing 5-agent system still works.
        """
        candidates = [agent for agent in agents if agent.can_handle(task)]

        if not candidates:
            raise ValueError(
                f"No agent found for task: '{task.description[:50]}...'. "
                f"Available agents: {[a.role for a in agents]}"
            )

        # Return Tier 3 agent if available (execution priority)
        tier_3_candidates = [a for a in candidates if a.tier == 3]
        if tier_3_candidates:
            agent = tier_3_candidates[0]
            logger.warning(f"Fallback selected: {agent.role} (tier={agent.tier})")
            return agent

        # Otherwise return first candidate
        agent = candidates[0]
        logger.warning(f"Fallback selected: {agent.role} (tier={agent.tier})")
        return agent

    def route_batch(self, tasks: List[Task], agents: List[Agent]) -> List[Tuple[Task, Agent]]:
        """
        Route multiple tasks to agents.

        Args:
            tasks: Tasks to route
            agents: Available agents

        Returns:
            List of (task, agent) tuples

        Use case: Batch routing for parallel execution planning.
        """
        return [(task, self.route(task, agents)) for task in tasks]

    def get_routing_stats(self, tasks: List[Task], agents: List[Agent]) -> dict:
        """
        Get routing statistics for batch of tasks.

        Args:
            tasks: Tasks to analyze
            agents: Available agents

        Returns:
            Dict with routing statistics

        Stats:
            - tier_distribution: Count of tasks per tier
            - domain_distribution: Count of tasks per domain
            - agent_utilization: Count of tasks per agent
        """
        routes = self.route_batch(tasks, agents)

        # Tier distribution
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, agent in routes:
            tier_counts[agent.tier] += 1

        # Domain distribution
        domain_counts = self.domain_classifier.get_statistics(tasks)

        # Agent utilization
        agent_counts = {}
        for _, agent in routes:
            agent_counts[agent.role] = agent_counts.get(agent.role, 0) + 1

        return {
            "total_tasks": len(tasks),
            "tier_distribution": tier_counts,
            "domain_distribution": domain_counts,
            "agent_utilization": agent_counts,
            "tier_1_percentage": (tier_counts[1] / len(tasks) * 100) if tasks else 0,
            "tier_2_percentage": (tier_counts[2] / len(tasks) * 100) if tasks else 0,
            "tier_3_percentage": (tier_counts[3] / len(tasks) * 100) if tasks else 0,
        }
