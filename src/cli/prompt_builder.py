"""
Interactive Prompt Builder - P2.3 Implementation

Creates high-quality PromptStrategy objects through guided interactive workflow
with real-time validation and domain-specific suggestions.

Clean Architecture: Adapter layer (CLI interaction).
Week 14: Priority 2.3 - Interactive PromptStrategy Builder
"""

import json
import yaml
import click
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from src.entity.prompt_strategy import PromptStrategy
from src.adapters.prompt.strategy_validator import PromptStrategyValidator


class PromptBuilder:
    """
    Interactive CLI tool for building validated PromptStrategy objects.

    Workflow:
    1. Select domain (frontend, backend, testing, qa, research, devops, etc.)
    2. Enter persona (with domain-specific examples)
    3. Enter goal (prompt for measurable outcomes)
    4. Enter task (suggest file paths, tools, metrics)
    5. Enter context (suggest constraints, success criteria)
    6. Validate and review (show score, suggestions)
    7. Refine if needed
    8. Save to file (YAML, JSON, or Python)

    Attributes:
        validator: PromptStrategyValidator for quality validation
        min_score: Minimum acceptable quality score (default: 60.0)
    """

    # Available domains from domain_classifier.py
    DOMAINS = {
        "frontend": "UI/UX, React, Vue, Angular, CSS, HTML, component design",
        "backend": "API, REST, GraphQL, databases, servers, microservices",
        "testing": "Unit tests, integration tests, E2E, pytest, coverage (technical focus)",
        "qa": "Acceptance testing, BDD, Gherkin, exploratory, test planning (user/product focus)",
        "research": "Investigation, analysis, documentation, architecture decisions",
        "devops": "CI/CD, deployment, Docker, Kubernetes, infrastructure, monitoring",
        "security": "Authentication, encryption, vulnerabilities, OWASP, audits",
        "performance": "Optimization, profiling, benchmarking, latency, scalability",
        "documentation": "README, user guides, API docs, tutorials, changelogs",
        "dsl": "Parser, AST, interpreter, .ct files, workflow execution",
        "category-theory": "Mathematical foundations, formal verification, type theory",
        "general": "Cross-domain or unspecified tasks"
    }

    def __init__(self, min_score: float = 60.0):
        """
        Initialize prompt builder.

        Args:
            min_score: Minimum acceptable quality score (0-100)
        """
        self.validator = PromptStrategyValidator(min_score=min_score)
        self.min_score = min_score

    def build_interactive(self) -> Optional[PromptStrategy]:
        """
        Main interactive workflow for building a prompt.

        Returns:
            PromptStrategy object if successful, None if cancelled
        """
        click.echo("\n" + "=" * 70)
        click.echo("  Interactive Prompt Builder (P2.3)")
        click.echo("  Build high-quality prompts with real-time validation")
        click.echo("=" * 70 + "\n")

        # Step 1: Select domain
        domain = self.select_domain()
        if not domain:
            return None

        # Step 2: Enter persona
        persona = self.enter_persona(domain)
        if not persona:
            return None

        # Step 3: Enter goal
        goal = self.enter_goal(domain)
        if not goal:
            return None

        # Step 4: Enter task
        task = self.enter_task(domain)
        if not task:
            return None

        # Step 5: Enter context
        context = self.enter_context(domain)
        if not context:
            return None

        # Step 6: Create initial prompt strategy
        prompt_strategy = PromptStrategy(
            persona=persona,
            goal=goal,
            task=task,
            context=context,
            domain=domain,
            iteration=1
        )

        # Step 7: Validate and review
        validated_prompt = self.validate_and_review(prompt_strategy)
        if not validated_prompt:
            return None

        return validated_prompt

    def select_domain(self) -> Optional[str]:
        """
        Interactive domain selection with descriptions.

        Returns:
            Selected domain string, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 1: Select Domain")
        click.echo("-" * 70)
        click.echo("\nAvailable domains:\n")

        # Display domains with numbers
        domain_list = list(self.DOMAINS.keys())
        for i, (domain, description) in enumerate(self.DOMAINS.items(), 1):
            click.echo(f"  {i:2d}. {domain:15s} - {description}")

        # Get selection
        click.echo()
        choice = click.prompt(
            "Select domain (enter number or name)",
            type=str,
            default="general"
        )

        # Parse choice (number or name)
        try:
            # Try as number first
            choice_num = int(choice)
            if 1 <= choice_num <= len(domain_list):
                selected = domain_list[choice_num - 1]
            else:
                click.echo(f"Invalid choice: {choice}. Using 'general'.")
                selected = "general"
        except ValueError:
            # Try as domain name
            choice_lower = choice.lower()
            if choice_lower in self.DOMAINS:
                selected = choice_lower
            else:
                click.echo(f"Unknown domain: {choice}. Using 'general'.")
                selected = "general"

        click.echo(f"\n✓ Selected: {selected} - {self.DOMAINS[selected]}")
        return selected

    def enter_persona(self, domain: str) -> Optional[str]:
        """
        Interactive persona entry with domain-specific examples.

        Args:
            domain: Selected domain

        Returns:
            Persona string, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 2: Enter Persona (WHO)")
        click.echo("-" * 70)
        click.echo("\nDefine the agent's role, expertise level, and skills.\n")

        # Show domain-specific examples
        examples = self.get_persona_examples(domain)
        click.echo("Examples:")
        for example in examples:
            click.echo(f"  • {example}")

        click.echo("\nGuidelines:")
        click.echo("  • Specify expertise level (Junior, Senior, Lead, etc.)")
        click.echo("  • Mention relevant skills and experience")
        click.echo("  • Be specific about domain knowledge")

        click.echo()
        persona = click.prompt(
            "Enter persona",
            type=str,
            default=""
        )

        if not persona:
            click.echo("Persona cannot be empty. Cancelled.")
            return None

        click.echo(f"\n✓ Persona: {persona[:80]}...")
        return persona

    def enter_goal(self, domain: str) -> Optional[str]:
        """
        Interactive goal entry with measurable outcome prompts.

        Args:
            domain: Selected domain

        Returns:
            Goal string, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 3: Enter Goal (WHAT - Measurable Outcome)")
        click.echo("-" * 70)
        click.echo("\nDefine what success looks like with specific, measurable criteria.\n")

        # Show metric suggestions
        metrics = self.suggest_metrics(domain)
        if metrics:
            click.echo("Suggested metrics to include:")
            for metric in metrics:
                click.echo(f"  • {metric}")

        click.echo("\nGuidelines:")
        click.echo("  • Include numeric targets (>90% coverage, <50ms latency, etc.)")
        click.echo("  • Specify measurable outcomes")
        click.echo("  • State the expected improvement or result")

        click.echo()
        goal = click.prompt(
            "Enter goal",
            type=str,
            default=""
        )

        if not goal:
            click.echo("Goal cannot be empty. Cancelled.")
            return None

        click.echo(f"\n✓ Goal: {goal[:80]}...")
        return goal

    def enter_task(self, domain: str) -> Optional[str]:
        """
        Interactive task entry with file path and tool suggestions.

        Args:
            domain: Selected domain

        Returns:
            Task string, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 4: Enter Task (HOW - Concrete Actions)")
        click.echo("-" * 70)
        click.echo("\nDefine the specific actions to take.\n")

        # Show file path suggestions
        file_paths = self.suggest_file_paths(domain)
        if file_paths:
            click.echo("Common file paths for this domain:")
            for path in file_paths:
                click.echo(f"  • {path}")

        # Show tool suggestions
        tools = self.suggest_tools(domain)
        if tools:
            click.echo("\nRecommended tools:")
            for tool in tools:
                click.echo(f"  • {tool}")

        click.echo("\nGuidelines:")
        click.echo("  • Include specific file paths (not just directories)")
        click.echo("  • Mention concrete tools and commands")
        click.echo("  • Provide code examples if relevant")
        click.echo("  • Break down into clear steps")

        click.echo()
        task = click.prompt(
            "Enter task",
            type=str,
            default=""
        )

        if not task:
            click.echo("Task cannot be empty. Cancelled.")
            return None

        click.echo(f"\n✓ Task: {task[:80]}...")
        return task

    def enter_context(self, domain: str) -> Optional[str]:
        """
        Interactive context entry with constraint suggestions.

        Args:
            domain: Selected domain

        Returns:
            Context string, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 5: Enter Context (WHY/WHEN/WHERE)")
        click.echo("-" * 70)
        click.echo("\nProvide background, constraints, and success criteria.\n")

        # Show constraint suggestions
        constraints = self.suggest_constraints(domain)
        if constraints:
            click.echo("Common constraints:")
            for constraint in constraints:
                click.echo(f"  • {constraint}")

        click.echo("\nGuidelines:")
        click.echo("  • Agent tier level (Tier 1: Strategic, Tier 2: Lead, Tier 3: Specialist)")
        click.echo("  • Available tools and resources")
        click.echo("  • Constraints (backward compatibility, no breaking changes, etc.)")
        click.echo("  • Success criteria (all tests pass, coverage >90%, etc.)")
        click.echo("  • ULTRATHINK directive if deep analysis needed")

        click.echo()
        context = click.prompt(
            "Enter context",
            type=str,
            default=""
        )

        if not context:
            click.echo("Context cannot be empty. Cancelled.")
            return None

        click.echo(f"\n✓ Context: {context[:80]}...")
        return context

    def validate_and_review(self, prompt_strategy: PromptStrategy) -> Optional[PromptStrategy]:
        """
        Validate prompt and show results with refinement option.

        Args:
            prompt_strategy: PromptStrategy object to validate

        Returns:
            Validated and potentially refined PromptStrategy, or None if cancelled
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 6: Validation & Review")
        click.echo("-" * 70)

        # Convert to markdown for validation
        markdown_text = prompt_strategy.to_markdown()

        # Validate
        validation_result = self.validator.validate(markdown_text)

        # Update prompt strategy with validation results
        prompt_strategy.update_validation(
            score=validation_result.score,
            passed=validation_result.passed,
            suggestions=validation_result.suggestions
        )

        # Display results
        click.echo(f"\nQuality Score: {validation_result.score:.1f}/100")

        if validation_result.passed:
            click.echo(click.style("✓ PASSED", fg="green") + f" (threshold: {self.min_score})")
        else:
            click.echo(click.style("✗ FAILED", fg="red") + f" (threshold: {self.min_score})")

        # Show validation details
        click.echo(f"\nValidation Details:")
        click.echo(f"  Specificity:   {validation_result.checks.specificity:.1f}/100")
        click.echo(f"  Clarity:       {validation_result.checks.clarity:.1f}/100")
        click.echo(f"  Completeness:  {'✓' if validation_result.checks.completeness else '✗'}")
        click.echo(f"  4-Sentence:    {'✓' if validation_result.checks.four_sentence_present else '✗'}")

        # Show suggestions
        if validation_result.suggestions:
            click.echo("\nSuggestions for Improvement:")
            for i, suggestion in enumerate(validation_result.suggestions, 1):
                click.echo(f"  {i}. {suggestion}")

        # Ask for next action
        click.echo()
        if validation_result.passed:
            action = click.prompt(
                "Prompt passed validation. Save to file? (yes/no/refine)",
                type=str,
                default="yes"
            )
        else:
            action = click.prompt(
                "Prompt failed validation. Refine and retry? (yes/no)",
                type=str,
                default="yes"
            )

        if action.lower() in ["yes", "y"] and validation_result.passed:
            return prompt_strategy
        elif action.lower() == "refine":
            # Refine workflow (simplified for v1)
            click.echo("\nRefinement not yet implemented. Proceeding with current prompt.")
            return prompt_strategy
        elif action.lower() in ["yes", "y"] and not validation_result.passed:
            click.echo("\nRefinement workflow:")
            click.echo("  1. Review suggestions above")
            click.echo("  2. Re-run 'atado prompt create --interactive'")
            click.echo("  3. Incorporate suggestions in your answers")
            return None
        else:
            click.echo("Cancelled.")
            return None

    def save_prompt(self, prompt_strategy: PromptStrategy, output_format: str = "yaml") -> Optional[Path]:
        """
        Save prompt to file in specified format.

        Args:
            prompt_strategy: PromptStrategy to save
            output_format: Output format ('yaml', 'json', or 'python')

        Returns:
            Path to saved file, or None if failed
        """
        click.echo("\n" + "-" * 70)
        click.echo("STEP 7: Save Prompt")
        click.echo("-" * 70)

        # Get output directory
        default_dir = Path("prompts")
        output_dir = click.prompt(
            "Output directory",
            type=str,
            default=str(default_dir)
        )
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        domain = prompt_strategy.domain or "general"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_prompt_{timestamp}.{output_format}"
        file_path = output_path / filename

        # Confirm
        click.echo(f"\nFile: {file_path}")
        confirm = click.prompt("Save to this file? (yes/no)", type=str, default="yes")

        if confirm.lower() not in ["yes", "y"]:
            click.echo("Cancelled.")
            return None

        # Save based on format
        try:
            if output_format == "yaml":
                self._save_yaml(prompt_strategy, file_path)
            elif output_format == "json":
                self._save_json(prompt_strategy, file_path)
            elif output_format == "python":
                self._save_python(prompt_strategy, file_path)
            else:
                click.echo(f"Unsupported format: {output_format}")
                return None

            click.echo(click.style(f"\n✓ Saved to {file_path}", fg="green"))

            # Display ATADO command
            self._display_atado_command(file_path, output_format)

            return file_path
        except Exception as e:
            click.echo(click.style(f"\n✗ Error saving file: {e}", fg="red"))
            return None

    def _save_yaml(self, prompt_strategy: PromptStrategy, file_path: Path):
        """Save prompt as YAML file."""
        data = prompt_strategy.to_dict()
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def _save_json(self, prompt_strategy: PromptStrategy, file_path: Path):
        """Save prompt as JSON file."""
        data = prompt_strategy.to_dict()
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_python(self, prompt_strategy: PromptStrategy, file_path: Path):
        """Save prompt as Python dict file."""
        data = prompt_strategy.to_dict()
        with open(file_path, 'w') as f:
            f.write("\"\"\"Auto-generated prompt strategy.\"\"\"\n\n")
            f.write("PROMPT_STRATEGY = ")
            f.write(repr(data))
            f.write("\n")

    def _display_atado_command(self, file_path: Path, output_format: str):
        """Display ATADO command to execute the prompt."""
        click.echo("\n" + "-" * 70)
        click.echo("Execute with ATADO:")
        click.echo("-" * 70)
        click.echo("\n# Load and execute prompt:")
        click.echo(f"python3 -m src.main \\")
        click.echo(f"  --task \"$(cat {file_path})\" \\")
        click.echo(f"  --provider granite \\")
        click.echo(f"  --routing team \\")
        click.echo(f"  --agents scaled \\")
        click.echo(f"  --orchestrator simple \\")
        click.echo(f"  --collect-metrics \\")
        click.echo(f"  --timeout 120")
        click.echo()

    # ===== Suggestion Generators =====

    def get_persona_examples(self, domain: str) -> List[str]:
        """Get domain-specific persona examples."""
        examples = {
            "frontend": [
                "Senior Frontend Engineer with 5+ years React and TypeScript experience",
                "UI/UX Developer specializing in accessible, responsive component design",
                "Lead Frontend Architect with expertise in state management and performance"
            ],
            "backend": [
                "Senior Backend Engineer with expertise in Python, FastAPI, and PostgreSQL",
                "Database Specialist focusing on query optimization and schema design",
                "Lead Backend Architect with microservices and distributed systems experience"
            ],
            "testing": [
                "Senior Test Engineer with expertise in pytest, coverage analysis, and CI/CD",
                "Integration Test Specialist focusing on API and E2E testing with Selenium",
                "Lead QA Engineer with TDD/BDD experience and test automation"
            ],
            "qa": [
                "Senior QA Engineer with expertise in BDD, Gherkin, and acceptance testing",
                "Exploratory Test Specialist with usability and manual testing experience",
                "Lead QA Architect focusing on test planning and requirement validation"
            ],
            "research": [
                "Senior Software Architect with expertise in system design and ADRs",
                "Technical Researcher specializing in technology evaluation and documentation",
                "Lead Research Engineer with experience in technical writing and analysis"
            ],
            "devops": [
                "Senior DevOps Engineer with Kubernetes, Docker, and CI/CD expertise",
                "Infrastructure Specialist focusing on monitoring, logging, and observability",
                "Lead DevOps Architect with cloud infrastructure and automation experience"
            ]
        }
        return examples.get(domain, [
            "Experienced Software Engineer with relevant domain expertise",
            "Senior Developer with proven track record in similar projects",
            "Technical Lead with comprehensive understanding of best practices"
        ])

    def suggest_metrics(self, domain: str) -> List[str]:
        """Suggest domain-specific measurable metrics."""
        metrics = {
            "frontend": [
                "Lighthouse score >90 (performance, accessibility, best practices)",
                "First Contentful Paint <1.5s",
                "Component reusability >70%",
                "Browser compatibility: Chrome, Firefox, Safari, Edge"
            ],
            "backend": [
                "API response time p95 <100ms",
                "Database query time <50ms",
                "Error rate <0.1%",
                "Throughput >1000 requests/second"
            ],
            "testing": [
                "Test coverage >90%",
                "All tests passing (100% success rate)",
                "Test execution time <2 minutes",
                "No flaky tests (0% flakiness)"
            ],
            "qa": [
                "All acceptance criteria met (100%)",
                "User story validation complete",
                "Zero critical or high-priority bugs",
                "Usability score >80/100"
            ],
            "performance": [
                "Latency reduction from X ms to <Y ms",
                "Throughput improvement by >Z%",
                "Memory usage <X MB",
                "CPU usage <Y%"
            ]
        }
        return metrics.get(domain, [
            "Measurable success criteria defined",
            "Numeric targets specified",
            "Quantifiable improvement stated"
        ])

    def suggest_file_paths(self, domain: str) -> List[str]:
        """Suggest domain-specific file paths."""
        paths = {
            "frontend": [
                "src/components/*.tsx",
                "src/pages/*.tsx",
                "src/styles/*.css",
                "src/hooks/*.ts"
            ],
            "backend": [
                "src/adapters/agent/*.py",
                "src/use_cases/*.py",
                "src/entity/*.py",
                "src/interface/*.py"
            ],
            "testing": [
                "tests/unit/*.py",
                "tests/integration/*.py",
                "tests/conftest.py",
                "pytest.ini"
            ],
            "devops": [
                ".github/workflows/*.yml",
                "Dockerfile",
                "docker-compose.yml",
                "k8s/*.yaml"
            ],
            "dsl": [
                "src/dsl/adapters/*.py",
                "src/dsl/entities/*.py",
                "workflows/*.ct"
            ]
        }
        return paths.get(domain, ["src/**/*.py", "tests/**/*.py"])

    def suggest_tools(self, domain: str) -> List[str]:
        """Suggest domain-specific tools."""
        tools = {
            "frontend": ["React DevTools", "Lighthouse", "webpack-bundle-analyzer", "ESLint"],
            "backend": ["FastAPI", "SQLAlchemy", "Pydantic", "pytest"],
            "testing": ["pytest", "pytest-cov", "pytest-benchmark", "selenium", "locust"],
            "qa": ["Gherkin/Cucumber", "behave", "TestRail", "JIRA"],
            "performance": ["cProfile", "line_profiler", "pytest-benchmark", "Locust"],
            "devops": ["Docker", "Kubernetes", "GitHub Actions", "Prometheus", "Grafana"],
            "security": ["OWASP ZAP", "Bandit", "Safety", "pytest-security"]
        }
        return tools.get(domain, ["Generic tools appropriate for domain"])

    def suggest_constraints(self, domain: str) -> List[str]:
        """Suggest domain-specific constraints."""
        return [
            "Agent Tier: 2 (Lead) or 3 (Specialist)",
            "Previous interactions: 0 (or specify context)",
            "Backward compatibility required (no breaking changes)",
            "All existing tests must pass",
            "Code style: Follow PEP 8 / project conventions",
            "Documentation: Update relevant docs",
            "ULTRATHINK: Enabled (for complex tasks requiring deep analysis)"
        ]
