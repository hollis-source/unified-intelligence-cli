"""Agent factory - Creates agents from configuration."""

from typing import List, Dict, Any
from src.entity import Agent
from src.interface import IAgentFactory


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
                role="architecture-lead",
                capabilities=[
                    # Code review
                    "review", "code review", "inspect", "evaluate",
                    # Architecture validation
                    "architecture", "solid", "clean code", "clean architecture",
                    # Code quality (not product QA)
                    "code quality", "technical debt", "refactoring",
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
        Create scaled agent team with full 3-tier hierarchy (130 agents - Phase 2 Aggressive Scaling).

        Week 11 Phase 2: Agent scaling expansion (12 agents).
        Week 13: Added Category Theory & DSL specialization (4 agents).
        Phase 2 (Aggressive): Scaled to 130 agents for massive parallelism on 96-core EPYC + ZeroGPU H200.

        Architecture:
            Tier 1 (2 agents): Orchestration & Quality Assurance
            Tier 2 (7 agents): Domain Leads (Frontend, Backend, Testing, Research, DevOps, Category Theory, DSL)
            Tier 3 (121 agents): Specialized Executors across all domains
                - Frontend: 19 specialists (React, Vue, Angular, Svelte, CSS, Tailwind, etc.)
                - Backend: 21 specialists (Django, Flask, FastAPI, PostgreSQL, Redis, etc.)
                - Testing: 20 specialists (Unit, Integration, Performance, Security, etc.)
                - Research: 16 specialists (Documentation, Tutorials, Analysis, etc.)
                - DevOps: 16 specialists (Docker, Kubernetes, AWS, GCP, Azure, etc.)
                - Category Theory: 16 specialists (Functors, Monads, Adjunctions, etc.)
                - DSL: 18 specialists (Parser, Compiler, Optimizer, LSP, etc.)

        Performance Target:
            - Workflow execution: 10-20s (vs 85s baseline with 16 agents)
            - Speedup: 4x-8x via massive concurrent execution
            - Hardware: 96 CPU cores + 1TB RAM + ZeroGPU H200 80GB VRAM

        Returns:
            List of 130 agents with complete tier metadata
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
                role="architecture-lead",
                capabilities=[
                    # Code review
                    "review", "code review", "inspect", "evaluate",
                    # Architecture validation
                    "architecture", "solid", "clean code", "clean architecture",
                    # Code quality (not product QA)
                    "code quality", "technical debt", "refactoring",
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

            Agent(
                role="qa-lead",
                capabilities=[
                    # Product quality (not code quality - that's architecture-lead)
                    "quality assurance", "qa", "product quality",
                    # Acceptance testing strategy
                    "acceptance", "acceptance testing", "uat", "user acceptance",
                    # Requirements & validation
                    "requirements validation", "feature validation",
                    "acceptance criteria", "story validation",
                    # Test planning
                    "test strategy", "test planning", "test case design",
                    "test scenarios", "test plan",
                    # User perspective
                    "user journey", "user flow", "user testing",
                    # Exploratory & manual testing
                    "exploratory testing", "manual testing"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="qa"
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
                role="qa-engineer",
                capabilities=[
                    # User acceptance testing
                    "acceptance", "acceptance test", "acceptance testing", "uat",
                    "user acceptance", "user acceptance testing",
                    # Feature validation
                    "feature validation", "feature testing", "feature verification",
                    "requirements validation", "requirements testing",
                    # BDD (Behavior-Driven Development)
                    "bdd", "behavior driven", "gherkin", "cucumber", "behave",
                    "given when then", "scenario", "feature file",
                    # User perspective testing
                    "user journey", "user flow", "user scenario", "user story testing",
                    "acceptance criteria", "story validation",
                    # QA activities
                    "qa", "quality assurance", "exploratory testing",
                    "manual testing", "test case", "test plan"
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
            ),

            # ===== TIER 2: Category Theory & DSL Domain Leads (2 agents) =====
            # Week 13: Specialized teams for DSL and Category Theory expertise

            Agent(
                role="category-theory-expert",
                capabilities=[
                    # Category theory foundations
                    "category", "category-theory", "category theory",
                    "functor", "morphism", "natural transformation",
                    # Algebraic structures
                    "monad", "monoid", "algebra", "algebraic", "composition",
                    # DSL theory
                    "dsl", "domain-specific language", "composability",
                    # Mathematical analysis
                    "mathematical", "theory", "proof", "law", "validation",
                    # Composition
                    "compose", "composition", "pipeline", "∘", "morphism composition"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="category-theory"
            ),

            Agent(
                role="dsl-deployment-specialist",
                capabilities=[
                    # Deployment & orchestration
                    "deploy", "deployment", "orchestration", "execute",
                    # DSL execution
                    "dsl", "workflow", "pipeline", "task execution",
                    # Integration
                    "integration", "production", "ci/cd",
                    # Strategy
                    "strategy", "planning", "coordination",
                    # Workflow management
                    "task management", "scheduling", "resource allocation"
                ],
                tier=2,
                parent_agent="master-orchestrator",
                specialization="dsl-deployment"
            ),

            # ===== TIER 3: Category Theory & DSL Specialists (2 agents) =====

            Agent(
                role="dsl-architect",
                capabilities=[
                    # DSL design
                    "dsl", "dsl-design", "domain-specific language",
                    "language design", "syntax", "grammar",
                    # Parser & interpreter
                    "parser", "ast", "abstract syntax tree",
                    "interpreter", "lexer", "tokenizer",
                    # Implementation
                    "implement", "design", "architecture",
                    # Language features
                    "operator", "expression", "statement",
                    # Practical DSL
                    "pipeline-design", "workflow-design", ".ct", "ct-file"
                ],
                tier=3,
                parent_agent="category-theory-expert",
                specialization="dsl-architecture"
            ),

            Agent(
                role="dsl-task-engineer",
                capabilities=[
                    # Task implementation
                    "task", "task implementation", "write task",
                    "create task", "implement task",
                    # Workflow creation
                    "workflow", "pipeline", ".ct file", "ct-file",
                    # DSL coding
                    "dsl-task", "workflow-design", "pipeline-design",
                    # Concrete implementations
                    "implement", "create", "write", "build",
                    # Testing
                    "test", "validate", "verify", "debug"
                ],
                tier=3,
                parent_agent="dsl-deployment-specialist",
                specialization="dsl-tasks"
            ),

            # ===== TIER 3: FRONTEND SPECIALISTS (17 additional) =====

            Agent(
                role="react-specialist",
                capabilities=["react", "jsx", "hooks", "context", "redux", "next.js", "component lifecycle", "react testing library"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="vue-specialist",
                capabilities=["vue", "vuex", "composition api", "nuxt", "pinia", "vue router", "vue components"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="angular-specialist",
                capabilities=["angular", "rxjs", "ngrx", "angular cli", "dependency injection", "angular modules"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="svelte-specialist",
                capabilities=["svelte", "sveltekit", "svelte stores", "reactive", "compiler", "transitions"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="css-specialist",
                capabilities=["css", "css3", "sass", "scss", "less", "flexbox", "grid", "animations", "responsive"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="tailwind-specialist",
                capabilities=["tailwind", "tailwindcss", "utility-first", "postcss", "jit", "responsive design"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="state-management-specialist",
                capabilities=["state management", "redux", "mobx", "zustand", "recoil", "global state", "context api"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="routing-specialist",
                capabilities=["routing", "router", "navigation", "react router", "vue router", "spa routing", "history api"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="forms-specialist",
                capabilities=["forms", "form validation", "formik", "react hook form", "input validation", "form state"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="accessibility-specialist",
                capabilities=["accessibility", "a11y", "wcag", "aria", "screen reader", "keyboard navigation", "semantic html"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="frontend-performance-specialist",
                capabilities=["performance", "optimization", "lazy loading", "code splitting", "web vitals", "lighthouse"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="seo-specialist",
                capabilities=["seo", "meta tags", "open graph", "schema markup", "sitemap", "search optimization"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="pwa-specialist",
                capabilities=["pwa", "service worker", "manifest", "offline", "push notifications", "installable"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="frontend-testing-specialist",
                capabilities=["frontend testing", "jest", "vitest", "testing library", "e2e frontend", "component testing"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="component-library-specialist",
                capabilities=["component library", "design system", "storybook", "material ui", "chakra ui", "ant design"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="build-tools-specialist",
                capabilities=["webpack", "vite", "rollup", "parcel", "esbuild", "bundler", "build optimization"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="typescript-frontend-specialist",
                capabilities=["typescript frontend", "type definitions", "generics", "interfaces frontend", "type safety ui"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),
            Agent(
                role="design-systems-specialist",
                capabilities=["design system", "design tokens", "component api", "theming", "brand consistency"],
                tier=3, parent_agent="frontend-lead", specialization="frontend"
            ),

            # ===== TIER 3: BACKEND SPECIALISTS (19 additional) =====

            Agent(
                role="django-specialist",
                capabilities=["django", "django orm", "django rest framework", "models", "migrations", "admin", "middleware"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="flask-specialist",
                capabilities=["flask", "blueprints", "flask extensions", "jinja2", "werkzeug", "microframework"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="fastapi-specialist",
                capabilities=["fastapi", "pydantic", "async api", "openapi", "swagger", "type hints api"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="express-specialist",
                capabilities=["express", "express.js", "middleware", "routing express", "node server"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="nestjs-specialist",
                capabilities=["nestjs", "decorators", "dependency injection nest", "modules nest", "typescript backend"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="api-design-specialist",
                capabilities=["api design", "rest api", "api versioning", "api documentation", "swagger", "openapi spec"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="graphql-specialist",
                capabilities=["graphql", "schema", "resolvers", "apollo", "relay", "graph api", "subscriptions"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="rest-specialist",
                capabilities=["rest", "restful", "http methods", "status codes", "hateoas", "rest best practices"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="database-design-specialist",
                capabilities=["database design", "schema design", "normalization", "indexes", "relationships", "er diagrams"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="postgresql-specialist",
                capabilities=["postgresql", "postgres", "psql", "pgadmin", "jsonb", "full text search", "views"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="mongodb-specialist",
                capabilities=["mongodb", "nosql", "documents", "collections", "aggregation", "mongoose", "atlas"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="redis-specialist",
                capabilities=["redis", "cache", "key-value", "pub/sub", "redis streams", "in-memory database"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="caching-specialist",
                capabilities=["caching strategy", "cache invalidation", "cdn", "edge caching", "memoization"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="auth-specialist",
                capabilities=["authentication", "authorization", "jwt", "oauth", "session", "passport", "auth0"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="webhooks-specialist",
                capabilities=["webhooks", "callbacks", "event driven", "webhook security", "retry logic"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="message-queue-specialist",
                capabilities=["message queue", "rabbitmq", "kafka", "celery", "background jobs", "async tasks"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="microservices-specialist",
                capabilities=["microservices", "service mesh", "api gateway", "service discovery", "distributed systems"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="websockets-specialist",
                capabilities=["websockets", "socket.io", "realtime", "bidirectional", "push updates"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="background-jobs-specialist",
                capabilities=["background jobs", "task queue", "job scheduling", "cron", "worker processes"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),
            Agent(
                role="rate-limiting-specialist",
                capabilities=["rate limiting", "throttling", "api limits", "quota", "circuit breaker"],
                tier=3, parent_agent="backend-lead", specialization="backend"
            ),

            # ===== TIER 3: TESTING SPECIALISTS (17 additional) =====

            Agent(
                role="performance-testing-specialist",
                capabilities=["performance testing", "load testing", "stress testing", "benchmarking", "response time"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="load-testing-specialist",
                capabilities=["load testing", "jmeter", "k6", "gatling", "artillery", "concurrent users", "throughput"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="security-testing-specialist",
                capabilities=["security testing", "penetration testing", "vulnerability", "owasp", "security scan"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="accessibility-testing-specialist",
                capabilities=["accessibility testing", "a11y testing", "axe", "wcag compliance", "screen reader testing"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="visual-regression-specialist",
                capabilities=["visual regression", "screenshot testing", "percy", "chromatic", "visual diff"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="test-data-specialist",
                capabilities=["test data", "fixtures", "factories", "seed data", "data generation", "faker"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="mocking-specialist",
                capabilities=["mocking", "test doubles", "stubs", "spies", "sinon", "mock server", "msw"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="snapshot-testing-specialist",
                capabilities=["snapshot testing", "snapshot", "visual snapshots", "regression detection"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="contract-testing-specialist",
                capabilities=["contract testing", "pact", "consumer driven", "api contracts", "schema validation"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="chaos-engineering-specialist",
                capabilities=["chaos engineering", "fault injection", "resilience testing", "chaos monkey", "failure simulation"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="fuzz-testing-specialist",
                capabilities=["fuzz testing", "fuzzing", "random input", "edge cases", "input validation testing"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="property-testing-specialist",
                capabilities=["property based testing", "hypothesis", "quickcheck", "generative testing", "property tests"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="mutation-testing-specialist",
                capabilities=["mutation testing", "test quality", "mutation score", "stryker", "pit"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="coverage-analysis-specialist",
                capabilities=["coverage analysis", "code coverage", "branch coverage", "line coverage", "istanbul", "coverage report"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="cicd-testing-specialist",
                capabilities=["ci/cd testing", "pipeline testing", "test automation ci", "github actions tests", "test orchestration"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="smoke-testing-specialist",
                capabilities=["smoke testing", "sanity testing", "build verification", "deployment verification"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),
            Agent(
                role="regression-testing-specialist",
                capabilities=["regression testing", "regression suite", "regression automation", "change validation"],
                tier=3, parent_agent="testing-lead", specialization="testing"
            ),

            # ===== TIER 3: RESEARCH SPECIALISTS (14 additional) =====

            Agent(
                role="api-documentation-specialist",
                capabilities=["api documentation", "swagger docs", "openapi docs", "api reference", "endpoint docs"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),
            Agent(
                role="tutorial-specialist",
                capabilities=["tutorial", "getting started", "quickstart", "walkthrough", "step by step", "how to guide"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),
            Agent(
                role="code-examples-specialist",
                capabilities=["code examples", "sample code", "code snippets", "usage examples", "cookbook"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),
            Agent(
                role="migration-guide-specialist",
                capabilities=["migration guide", "upgrade guide", "breaking changes", "version migration", "compatibility"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),
            Agent(
                role="changelog-specialist",
                capabilities=["changelog", "release notes", "version history", "what's new", "updates"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),
            Agent(
                role="architecture-decisions-specialist",
                capabilities=["architecture decision", "adr", "design decisions", "technical decisions", "rfc"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="knowledge-base-specialist",
                capabilities=["knowledge base", "wiki", "documentation hub", "internal docs", "knowledge management"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="data-analysis-specialist",
                capabilities=["data analysis", "analytics", "metrics analysis", "statistics", "insights"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="benchmarking-specialist",
                capabilities=["benchmarking", "performance benchmarks", "comparison", "metrics", "baseline"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="competitive-analysis-specialist",
                capabilities=["competitive analysis", "market research", "competitor analysis", "landscape", "alternatives"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="user-research-specialist",
                capabilities=["user research", "ux research", "user interviews", "surveys", "usability"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="academic-research-specialist",
                capabilities=["academic research", "papers", "research papers", "scholarly", "citations"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="literature-review-specialist",
                capabilities=["literature review", "survey", "state of art", "related work", "prior art"],
                tier=3, parent_agent="research-lead", specialization="research"
            ),
            Agent(
                role="troubleshooting-specialist",
                capabilities=["troubleshooting", "debugging guide", "common issues", "faq", "problem solving"],
                tier=3, parent_agent="research-lead", specialization="documentation"
            ),

            # ===== TIER 3: DEVOPS SPECIALISTS (15 additional) =====

            Agent(
                role="docker-specialist",
                capabilities=["docker", "dockerfile", "containers", "docker compose", "images", "volumes"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="kubernetes-specialist",
                capabilities=["kubernetes", "k8s", "pods", "deployments", "services", "ingress", "helm"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="terraform-specialist",
                capabilities=["terraform", "infrastructure as code", "terraform modules", "state management", "provisioning"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="cicd-specialist",
                capabilities=["ci/cd", "continuous integration", "continuous deployment", "pipeline", "automation"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="github-actions-specialist",
                capabilities=["github actions", "workflows", "actions", "runners", "github ci"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="gitlab-ci-specialist",
                capabilities=["gitlab ci", "gitlab pipelines", ".gitlab-ci.yml", "gitlab runners"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="jenkins-specialist",
                capabilities=["jenkins", "jenkinsfile", "jenkins pipeline", "jenkins jobs", "jenkins plugins"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="aws-specialist",
                capabilities=["aws", "ec2", "s3", "lambda", "cloudformation", "ecs", "rds"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="gcp-specialist",
                capabilities=["gcp", "google cloud", "gke", "cloud run", "cloud functions", "bigquery"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="azure-specialist",
                capabilities=["azure", "azure devops", "aks", "azure functions", "cosmos db"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="monitoring-specialist",
                capabilities=["monitoring", "metrics", "alerting", "observability", "dashboards"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="logging-specialist",
                capabilities=["logging", "log aggregation", "elk", "splunk", "log analysis"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="alerting-specialist",
                capabilities=["alerting", "alerts", "notifications", "incident response", "pagerduty"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="security-scanning-specialist",
                capabilities=["security scanning", "vulnerability scanning", "sast", "dast", "dependency scanning"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),
            Agent(
                role="container-orchestration-specialist",
                capabilities=["container orchestration", "swarm", "nomad", "orchestration", "cluster management"],
                tier=3, parent_agent="devops-lead", specialization="devops"
            ),

            # ===== TIER 3: CATEGORY THEORY SPECIALISTS (15 additional) =====

            Agent(
                role="functors-specialist",
                capabilities=["functor", "functors", "map", "fmap", "functor laws", "functor composition"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="monads-specialist",
                capabilities=["monad", "monads", "bind", "return", "monad laws", "do notation", "kleisli"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="applicatives-specialist",
                capabilities=["applicative", "applicatives", "applicative functor", "pure", "apply"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="adjunctions-specialist",
                capabilities=["adjunction", "adjunctions", "adjoint functors", "unit", "counit"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="natural-transformations-specialist",
                capabilities=["natural transformation", "naturality", "component", "natural isomorphism"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="limits-colimits-specialist",
                capabilities=["limits", "colimits", "product", "coproduct", "pullback", "pushout"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="category-laws-specialist",
                capabilities=["category laws", "associativity", "identity", "composition laws", "categorical axioms"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="yoneda-specialist",
                capabilities=["yoneda", "yoneda lemma", "presheaf", "representable", "hom functor"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="f-algebras-specialist",
                capabilities=["f-algebra", "coalgebra", "catamorphism", "anamorphism", "recursion schemes"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="free-monads-specialist",
                capabilities=["free monad", "free structures", "free algebra", "interpreter pattern"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="kleisli-specialist",
                capabilities=["kleisli", "kleisli category", "kleisli arrow", "monadic composition"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="product-coproduct-specialist",
                capabilities=["product category", "coproduct", "sum type", "product type", "categorical product"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="exponentials-specialist",
                capabilities=["exponential object", "cartesian closed", "curry", "uncurry", "lambda"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="topoi-specialist",
                capabilities=["topos", "topoi", "subobject classifier", "elementary topos", "categorical logic"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),
            Agent(
                role="type-theory-specialist",
                capabilities=["type theory", "dependent types", "curry-howard", "propositions as types"],
                tier=3, parent_agent="category-theory-expert", specialization="category-theory"
            ),

            # ===== TIER 3: DSL SPECIALISTS (15 additional) =====

            Agent(
                role="dsl-parser-specialist",
                capabilities=["parser", "parsing", "lark", "antlr", "parser combinator", "recursive descent"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-lexer-specialist",
                capabilities=["lexer", "tokenizer", "lexical analysis", "tokens", "scanner"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="ast-specialist",
                capabilities=["ast", "abstract syntax tree", "tree traversal", "visitor pattern", "ast nodes"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="type-checker-specialist",
                capabilities=["type checking", "type inference", "type system", "type errors", "static analysis"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-optimizer-specialist",
                capabilities=["optimizer", "optimization", "constant folding", "dead code elimination", "peephole"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="code-generator-specialist",
                capabilities=["code generation", "codegen", "target language", "emit code", "transpiler"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-interpreter-specialist",
                capabilities=["interpreter", "evaluation", "runtime", "execute ast", "visitor"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-compiler-specialist",
                capabilities=["compiler", "compilation", "compile time", "bytecode", "ir"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="syntax-design-specialist",
                capabilities=["syntax design", "grammar design", "language syntax", "concrete syntax", "bnf"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="semantic-analysis-specialist",
                capabilities=["semantic analysis", "semantics", "scope", "symbol table", "name resolution"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="error-reporting-specialist",
                capabilities=["error reporting", "error messages", "diagnostics", "error recovery", "syntax error"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="ide-integration-specialist",
                capabilities=["ide integration", "editor support", "syntax highlighting", "autocomplete", "linting"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="language-server-specialist",
                capabilities=["language server", "lsp", "language server protocol", "hover", "go to definition"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-debugging-specialist",
                capabilities=["debugging dsl", "breakpoints", "step through", "watch", "debug info"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
            ),
            Agent(
                role="dsl-profiling-specialist",
                capabilities=["profiling", "performance analysis", "bottlenecks", "profiler", "execution time"],
                tier=3, parent_agent="dsl-deployment-specialist", specialization="dsl-architecture"
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