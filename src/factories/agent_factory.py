"""Agent factory - Creates agents from configuration."""

from typing import List, Dict, Any
from src.entities import Agent
from src.interfaces import IAgentFactory


class AgentFactory(IAgentFactory):
    """
    Factory for creating agents.

    Clean Code: Extract creation logic from main.
    SRP: Single responsibility - agent creation.
    """

    def create_default_agents(self) -> List[Agent]:
        """
        Create default agent team (5 agents, backward compatible).

        Enhanced capabilities based on user simulation testing.
        Includes natural language keywords users actually use in task descriptions.

        For 8-agent hierarchical system, use create_extended_agents().
        """
        return [
            Agent(
                role="coder",
                capabilities=[
                    # Core coding terms
                    "code", "coding", "program", "programming",
                    # Actions
                    "write", "create", "build", "develop", "implement", "fix",
                    # Artifacts
                    "function", "class", "method", "script", "application", "feature",
                    # Languages (common ones)
                    "python", "javascript", "java", "typescript",
                    # Maintenance
                    "refactor", "debug", "optimize", "improve"
                ],
                tier=3,  # Tier 3: Execution (default)
                parent_agent=None,
                specialization="backend"
            ),
            Agent(
                role="tester",
                capabilities=[
                    "test", "testing", "tests",
                    "validate", "verify", "check",
                    "qa", "quality", "unit", "integration"
                ],
                tier=3,
                parent_agent=None,
                specialization="testing"
            ),
            Agent(
                role="reviewer",
                capabilities=[
                    "review", "reviewing", "reviews",
                    "analyze", "inspect", "evaluate", "assess",
                    "approve", "feedback", "critique"
                ],
                tier=1,  # Tier 1: Quality Assurance Lead
                parent_agent=None,
                specialization=None
            ),
            Agent(
                role="coordinator",
                capabilities=[
                    "plan", "planning", "organize", "coordinate",
                    "delegate", "manage", "schedule", "prioritize"
                ],
                tier=1,  # Tier 1: Master Orchestrator
                parent_agent=None,
                specialization=None
            ),
            Agent(
                role="researcher",
                capabilities=[
                    "research", "investigate", "study", "explore",
                    "analyze", "document", "find", "search", "learn"
                ],
                tier=3,
                parent_agent=None,
                specialization="research"
            )
        ]

    def create_extended_agents(self) -> List[Agent]:
        """
        Create extended agent team with 3-tier hierarchy (8 agents for Phase 1).

        Week 11 Phase 1: Hierarchical agent scaling.

        Architecture:
            Tier 1 (2 agents): Orchestration & Quality Assurance
            Tier 2 (3 agents): Domain Leads (Frontend, Backend, DevOps)
            Tier 3 (3 agents): Specialists (Python, Unit Test, Technical Writer)

        Returns:
            List of 8 agents with tier metadata
        """
        return [
            # ===== TIER 1: Planning & Coordination (2 agents) =====

            Agent(
                role="master-orchestrator",
                capabilities=[
                    # High-level planning
                    "plan", "planning", "orchestrate", "coordinate",
                    # Task decomposition
                    "decompose", "break down", "organize", "structure",
                    # Resource allocation
                    "delegate", "assign", "allocate", "distribute",
                    # Project management
                    "manage", "schedule", "prioritize", "roadmap",
                    "strategy", "overall", "high-level"
                ],
                tier=1,
                parent_agent=None,  # Top of hierarchy
                specialization=None  # Cross-domain
            ),

            Agent(
                role="qa-lead",
                capabilities=[
                    # Code review
                    "review", "code review", "inspect", "evaluate",
                    # Architecture validation
                    "architecture", "solid", "clean code", "clean architecture",
                    # Quality assurance
                    "quality", "qa", "quality assurance", "validate",
                    # Best practices
                    "best practices", "standards", "conventions",
                    "assess", "audit", "critique", "feedback"
                ],
                tier=1,
                parent_agent=None,  # Top of hierarchy
                specialization=None  # Cross-domain
            ),

            # ===== TIER 2: Domain Leads (3 agents) =====

            Agent(
                role="frontend-lead",
                capabilities=[
                    # Frontend domains
                    "frontend", "front-end", "client-side", "ui", "ux",
                    "user interface", "user experience",
                    # Frameworks
                    "react", "vue", "angular", "svelte",
                    # Web tech
                    "html", "css", "component", "responsive",
                    # Design
                    "dashboard", "navbar", "form", "modal", "layout",
                    "accessibility", "a11y", "state management"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="frontend"
            ),

            Agent(
                role="backend-lead",
                capabilities=[
                    # Backend domains
                    "backend", "back-end", "server-side", "server",
                    # API design
                    "api", "rest", "graphql", "endpoint", "microservice",
                    # Database
                    "database", "sql", "nosql", "query", "schema",
                    # Architecture
                    "architecture", "scalability", "distributed",
                    "authentication", "authorization", "middleware",
                    "cache", "caching", "performance"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="backend"
            ),

            Agent(
                role="devops-lead",
                capabilities=[
                    # DevOps domains
                    "devops", "deployment", "deploy", "infrastructure",
                    # CI/CD
                    "ci", "cd", "ci/cd", "pipeline", "continuous integration",
                    "continuous deployment", "automation",
                    # Containers
                    "docker", "dockerfile", "container", "kubernetes", "k8s",
                    # Monitoring
                    "monitoring", "observability", "logging", "metrics",
                    "prometheus", "grafana",
                    # Release
                    "release", "rollback", "production"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="devops"
            ),

            # ===== TIER 3: Specialized Executors (3 agents) =====

            Agent(
                role="python-specialist",
                capabilities=[
                    # Python-specific
                    "python", "py", "python3", "pythonic",
                    # Web frameworks
                    "django", "flask", "fastapi", "tornado",
                    # Async
                    "async", "asyncio", "await", "asynchronous",
                    # Package management
                    "pip", "venv", "virtualenv", "poetry",
                    # Testing
                    "pytest", "unittest", "mock",
                    # Type hints
                    "type hints", "typing", "pydantic", "dataclass",
                    # General coding (inherits from old "coder")
                    "code", "implement", "write", "create", "function", "class"
                ],
                tier=3,
                parent_agent="backend-lead",
                specialization="backend"  # Python primarily for backend
            ),

            Agent(
                role="unit-test-engineer",
                capabilities=[
                    # Unit testing
                    "unit test", "unittest", "unit testing",
                    # TDD
                    "tdd", "test-driven", "test driven development",
                    # Test frameworks
                    "pytest", "jest", "mocha", "junit",
                    # Test concepts
                    "test fixture", "mock", "stub", "spy", "fake",
                    "assertion", "test case", "test suite",
                    # Coverage
                    "coverage", "test coverage", "code coverage",
                    # General testing (inherits from old "tester")
                    "test", "testing", "validate", "verify", "check", "qa"
                ],
                tier=3,
                parent_agent="testing-lead",  # Will be added in Phase 2
                specialization="testing"
            ),

            Agent(
                role="technical-writer",
                capabilities=[
                    # Documentation
                    "documentation", "document", "docs", "readme",
                    # User guides
                    "user guide", "tutorial", "how-to", "getting started",
                    # API docs
                    "api docs", "api documentation", "reference",
                    # Release docs
                    "changelog", "release notes", "migration guide",
                    # Technical writing
                    "technical writing", "examples", "quickstart",
                    # General research (inherits from old "researcher")
                    "research", "investigate", "explore", "analyze", "study"
                ],
                tier=3,
                parent_agent="research-lead",  # Will be added in Phase 2
                specialization="documentation"
            )
        ]

    def create_scaled_agents(self) -> List[Agent]:
        """
        Create scaled agent team with full 3-tier hierarchy (12 agents for Phase 2).

        Week 11 Phase 2: Agent scaling expansion.

        Architecture:
            Tier 1 (2 agents): Orchestration & Quality Assurance
            Tier 2 (5 agents): Domain Leads (Frontend, Backend, Testing, Research, DevOps)
            Tier 3 (5 agents): Specialists (Python, JS/TS, Unit Test, Integration Test, Technical Writer)

        Returns:
            List of 12 agents with complete tier metadata
        """
        return [
            # ===== TIER 1: Planning & Coordination (2 agents) =====

            Agent(
                role="master-orchestrator",
                capabilities=[
                    # High-level planning
                    "plan", "planning", "orchestrate", "coordinate",
                    # Task decomposition
                    "decompose", "break down", "organize", "structure",
                    # Resource allocation
                    "delegate", "assign", "allocate", "distribute",
                    # Project management
                    "manage", "schedule", "prioritize", "roadmap",
                    "strategy", "overall", "high-level"
                ],
                tier=1,
                parent_agent=None,  # Top of hierarchy
                specialization=None  # Cross-domain
            ),

            Agent(
                role="qa-lead",
                capabilities=[
                    # Code review
                    "review", "code review", "inspect", "evaluate",
                    # Architecture validation
                    "architecture", "solid", "clean code", "clean architecture",
                    # Quality assurance
                    "quality", "qa", "quality assurance", "validate",
                    # Best practices
                    "best practices", "standards", "conventions",
                    "assess", "audit", "critique", "feedback"
                ],
                tier=1,
                parent_agent=None,  # Top of hierarchy
                specialization=None  # Cross-domain
            ),

            # ===== TIER 2: Domain Leads (5 agents) =====

            Agent(
                role="frontend-lead",
                capabilities=[
                    # Frontend domains
                    "frontend", "front-end", "client-side", "ui", "ux",
                    "user interface", "user experience",
                    # Frameworks
                    "react", "vue", "angular", "svelte",
                    # Web tech
                    "html", "css", "component", "responsive",
                    # Design
                    "dashboard", "navbar", "form", "modal", "layout",
                    "accessibility", "a11y", "state management"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="frontend"
            ),

            Agent(
                role="backend-lead",
                capabilities=[
                    # Backend domains
                    "backend", "back-end", "server-side", "server",
                    # API design
                    "api", "rest", "graphql", "endpoint", "microservice",
                    # Database
                    "database", "sql", "nosql", "query", "schema",
                    # Architecture
                    "architecture", "scalability", "distributed",
                    "authentication", "authorization", "middleware",
                    "cache", "caching", "performance"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="backend"
            ),

            Agent(
                role="testing-lead",
                capabilities=[
                    # Test strategy
                    "test strategy", "testing strategy", "qa strategy",
                    "test planning", "test architecture",
                    # Quality assurance
                    "quality", "qa", "quality assurance",
                    # Coverage & automation
                    "coverage", "test coverage", "test automation",
                    "ci testing", "continuous testing",
                    # Test types
                    "unit test", "integration test", "e2e", "end-to-end",
                    # General testing
                    "test", "testing", "validate", "verify"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="testing"
            ),

            Agent(
                role="research-lead",
                capabilities=[
                    # Research domains
                    "research", "investigate", "study", "explore",
                    "analyze", "analysis", "survey", "compare",
                    # Documentation strategy
                    "documentation strategy", "documentation architecture",
                    "knowledge management", "knowledge base",
                    # Technical writing leadership
                    "documentation", "technical writing",
                    "api documentation", "user documentation",
                    # Decision documents
                    "adr", "architecture decision", "rfc", "design doc"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="research"
            ),

            Agent(
                role="devops-lead",
                capabilities=[
                    # DevOps domains
                    "devops", "deployment", "deploy", "infrastructure",
                    # CI/CD
                    "ci", "cd", "ci/cd", "pipeline", "continuous integration",
                    "continuous deployment", "automation",
                    # Containers
                    "docker", "dockerfile", "container", "kubernetes", "k8s",
                    # Monitoring
                    "monitoring", "observability", "logging", "metrics",
                    "prometheus", "grafana",
                    # Release
                    "release", "rollback", "production"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="devops"
            ),

            # ===== TIER 3: Specialized Executors (5 agents) =====

            Agent(
                role="python-specialist",
                capabilities=[
                    # Python-specific
                    "python", "py", "python3", "pythonic",
                    # Web frameworks
                    "django", "flask", "fastapi", "tornado",
                    # Async
                    "async", "asyncio", "await", "asynchronous",
                    # Package management
                    "pip", "venv", "virtualenv", "poetry",
                    # Testing
                    "pytest", "unittest", "mock",
                    # Type hints
                    "type hints", "typing", "pydantic", "dataclass",
                    # General coding (inherits from old "coder")
                    "code", "implement", "write", "create", "function", "class"
                ],
                tier=3,
                parent_agent="backend-lead",
                specialization="backend"  # Python primarily for backend
            ),

            Agent(
                role="javascript-typescript-specialist",
                capabilities=[
                    # JavaScript
                    "javascript", "js", "ecmascript", "es6", "es2015",
                    # TypeScript
                    "typescript", "ts", "type safety", "interfaces",
                    # Node.js
                    "node", "nodejs", "npm", "yarn", "express",
                    # Frontend frameworks
                    "react code", "vue code", "angular code", "svelte code",
                    # Async patterns
                    "async await", "promises", "callbacks",
                    # Build tools
                    "webpack", "vite", "babel", "rollup",
                    # General coding
                    "code", "implement", "write", "create", "function"
                ],
                tier=3,
                parent_agent="frontend-lead",
                specialization="frontend"
            ),

            # Order matters: Unit (narrower) before Integration (broader) for proper routing
            Agent(
                role="unit-test-engineer",
                capabilities=[
                    # Unit testing (specific - NO generic "test"/"testing" to avoid overlap)
                    "unit test", "unittest", "unit testing", "unit",
                    # TDD
                    "tdd", "test-driven", "test driven development",
                    # Test frameworks
                    "pytest", "jest", "mocha", "junit",
                    # Test concepts
                    "fixture", "mock", "stub", "spy", "fake", "mocking",
                    "assertion", "assertions"
                ],
                tier=3,
                parent_agent="testing-lead",
                specialization="testing"
            ),

            Agent(
                role="integration-test-engineer",
                capabilities=[
                    # Integration testing (broader scope as fallback)
                    "integration", "api", "e2e", "end-to-end", "end to end",
                    "system", "workflow", "flow",
                    # E2E frameworks
                    "selenium", "cypress", "playwright", "puppeteer",
                    "postman", "rest-assured",
                    # Contract
                    "contract", "pact",
                    # Automation
                    "automation", "automated",
                    # Broad fallback terms (since unit-test-engineer is now narrow)
                    "test", "testing", "validate", "verify", "coverage"
                ],
                tier=3,
                parent_agent="testing-lead",
                specialization="testing"
            ),

            Agent(
                role="technical-writer",
                capabilities=[
                    # Documentation
                    "documentation", "document", "docs", "readme",
                    # User guides
                    "user guide", "tutorial", "how-to", "getting started",
                    # API docs
                    "api docs", "api documentation", "reference",
                    # Release docs
                    "changelog", "release notes", "migration guide",
                    # Technical writing
                    "technical writing", "examples", "quickstart",
                    # General research (inherits from old "researcher")
                    "research", "investigate", "explore", "analyze", "study"
                ],
                tier=3,
                parent_agent="research-lead",
                specialization="documentation"
            )
        ]

    def create_from_config(self, config: List[Dict[str, Any]]) -> List[Agent]:
        """
        Create agents from configuration.

        Args:
            config: List of agent configurations

        Returns:
            List of configured agents
        """
        agents = []
        for agent_config in config:
            agent = Agent(
                role=agent_config["role"],
                capabilities=agent_config["capabilities"]
            )
            agents.append(agent)
        return agents