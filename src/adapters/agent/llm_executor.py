"""
LLM-powered agent executor - Adapter layer implementation.

Week 1: Enhanced with error_details propagation for better debugging.
Week 9: Added passive data collection for model training pipeline.
SYD2 Fix: Added LLM response caching to reduce latency for expensive ULTRATHINK tasks.
Phase 2: Added prompt strategy integration with validation support.
"""

import time
import logging
from typing import Optional, Any, Union
from src.entity import Agent, Task, ExecutionResult, ExecutionStatus, ExecutionContext
from src.entity.prompt_strategy import PromptStrategy
from src.interface import IAgentExecutor, ITextGenerator, LLMConfig
from src.interface.async_text_generator import IAsyncTextGenerator
from src.interface.prompt_validator import IPromptValidator, ValidationResult
from src.exceptions import ToolExecutionError
from src.adapters.agent.llm_cache import LLMResponseCache, CacheConfig


class LLMAgentExecutor(IAgentExecutor):
    """
    Execute agents using LLM for task completion.
    DIP: Depends on ITextGenerator abstraction.
    Week 9: Optionally collects execution data for model training.
    """

    def __init__(
        self,
        llm_provider: Union[ITextGenerator, IAsyncTextGenerator],
        default_config: Optional[LLMConfig] = None,
        data_collector: Optional[Any] = None,
        provider_name: str = "unknown",
        orchestrator: str = "simple",
        cache_config: Optional[CacheConfig] = None,
        enable_cache: bool = True,
        enable_ultrathink: bool = True,
        prompt_validator: Optional[IPromptValidator] = None,
        validate_prompts: bool = False,
        use_prompt_strategy: bool = False,
        template_loader: Optional[Any] = None,
        template_merger: Optional[Any] = None,
        metrics_store: Optional["IPromptMetricsStore"] = None,
        output_validator: Optional[Any] = None,  # Week 14: P2.2 - OutputValidator for validation
        enable_output_validation: bool = False,  # Week 14: P2.2 - Enable output validation
        metrics_collector: Optional[Any] = None,  # Week 14: P2.2 - For recording validation metrics
    ):
        """
        Initialize with LLM provider.

        Args:
            llm_provider: LLM for agent intelligence (sync or async)
            default_config: Default LLM configuration
            data_collector: Optional DataCollector for training data (Week 9)
            provider_name: LLM provider name (mock, grok, tongyi) (Week 9)
            orchestrator: Orchestrator mode (simple, openai-agents) (Week 9)
            cache_config: Optional cache configuration (SYD2 fix)
            enable_cache: Enable response caching (SYD2 fix)
            enable_ultrathink: Enable ULTRATHINK prompts (Phase 4B: disable for Granite)
            prompt_validator: Optional prompt validator for quality validation (Phase 2)
            validate_prompts: Enable prompt validation before LLM calls (Phase 2)
            use_prompt_strategy: Use PromptStrategy entity for prompt building (Phase 2)
            template_loader: Optional TemplateLoader instance (Phase 3)
            template_merger: Optional PromptTemplateMerger instance (Phase 3)
            metrics_store: Optional IPromptMetricsStore to persist validation metrics (Phase 4)
            output_validator: Optional OutputValidator for post-execution validation (Week 14: P2.2)
            enable_output_validation: Enable output validation after LLM response (Week 14: P2.2)
            metrics_collector: Optional MetricsCollector for recording validation metrics (Week 14: P2.2)
        """
        self.llm_provider = llm_provider
        self.is_async_provider = isinstance(llm_provider, IAsyncTextGenerator)
        self.default_config = default_config or LLMConfig(
            temperature=0.7,
            max_tokens=1024  # Qwen3 HF Space limit (was 500, too restrictive)
        )
        self.data_collector = data_collector
        self.provider_name = provider_name
        self.orchestrator = orchestrator
        self.enable_ultrathink = enable_ultrathink

        # SYD2 FIX: Initialize response cache for expensive ULTRATHINK tasks
        if enable_cache:
            self.cache = LLMResponseCache(cache_config)
        else:
            self.cache = None

        # Phase 2: Prompt validation integration
        self.prompt_validator = prompt_validator
        self.validate_prompts = validate_prompts and prompt_validator is not None
        self.use_prompt_strategy = use_prompt_strategy
        # Phase 3: Template integration (optional)
        self.template_loader = template_loader
        self.template_merger = template_merger
        # Phase 4: Metrics store (optional)
        self.metrics_store = metrics_store

        # Week 14: P2.2 - Output validation integration
        self.output_validator = output_validator
        self.enable_output_validation = enable_output_validation and output_validator is not None
        self.metrics_collector = metrics_collector

    async def execute(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> ExecutionResult:
        """
        Execute task using agent's role and LLM.

        Clean Code: Clear async execution pattern.
        Week 9: Logs interaction data for model training if enabled.

        Args:
            agent: Agent to execute
            task: Task to complete
            context: Optional execution context

        Returns:
            ExecutionResult with LLM output
        """
        # Week 9: Track execution time for data collection
        start_time = time.time()

        # Build prompt based on agent role and task
        messages = self._build_messages(agent, task, context)

        # SYD2 FIX: Check cache before expensive LLM call
        cache_hit = False
        response_text = None
        usage = {}

        if self.cache:
            # Extract task description for cache keying
            task_desc = self._extract_task_description(task)
            response_text = self.cache.get(
                messages=messages,
                task_description=task_desc,
                model_name=self.provider_name
            )
            cache_hit = response_text is not None

            # Phase 2: Estimate usage for cache hits (no actual API call made)
            if cache_hit:
                estimated_tokens = len(response_text) // 4
                usage = {
                    "prompt_tokens": 0,  # Unknown for cache hit
                    "completion_tokens": estimated_tokens,
                    "total_tokens": estimated_tokens,
                    "cached": True  # Flag to indicate estimation
                }

        try:
            if not cache_hit:
                # Generate response using LLM (cache miss or disabled)
                # Support both sync and async providers
                if self.is_async_provider:
                    result = await self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )
                else:
                    result = self.llm_provider.generate(
                        messages=messages,
                        config=self.default_config
                    )

                # Extract content and usage from GenerationResult
                response_text = result.content
                usage = result.usage

                # Store in cache for future requests
                if self.cache:
                    task_desc = self._extract_task_description(task)
                    self.cache.set(
                        messages=messages,
                        response=response_text,
                        task_description=task_desc,
                        model_name=self.provider_name
                    )

            # Calculate execution duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Update context if provided
            if context:
                context.history.append({
                    "role": "assistant",
                    "content": response_text,
                    "agent": agent.role
                })

            # Week 9: Log successful interaction for training data
            if self.data_collector:
                self.data_collector.log_interaction(
                    task=task,
                    agent=agent,
                    messages=messages,
                    output=response_text,
                    status="success",
                    duration_ms=duration_ms,
                    llm_config=self.default_config,
                    provider=self.provider_name,
                    orchestrator=self.orchestrator,
                    context_history_length=len(context.history) if context else 0
                )

            # Week 14: P2.2 - Output validation (optional, non-blocking)
            validation_result = None
            if self.enable_output_validation and self.output_validator:
                try:
                    validation_result = self.output_validator.validate(response_text)

                    # Log validation results
                    if not validation_result.passed:
                        logging.warning(
                            f"Output validation failed for {agent.role}: {validation_result.error_message}"
                        )
                    elif validation_result.warnings:
                        logging.info(
                            f"Output validation passed with {len(validation_result.warnings)} warnings"
                        )

                    # Record validation metrics if collector available
                    if self.metrics_collector:
                        self.metrics_collector.record_output_validation(
                            task_description=task.description,
                            agent=agent.role,
                            validation_type=validation_result.validation_type.value,
                            passed=validation_result.passed,
                            error_message=validation_result.error_message,
                            error_line=validation_result.error_line,
                            error_column=validation_result.error_column,
                            warning_count=len(validation_result.warnings),
                            output_length=len(response_text)
                        )
                except Exception as e:
                    # Validation errors should never fail execution
                    logging.error(f"Output validation error (non-blocking): {e}")

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=response_text,
                errors=[],
                metadata={
                    "agent_role": agent.role,
                    "task_id": task.task_id,
                    "cache_hit": cache_hit,  # SYD2 FIX: Track cache performance
                    "duration_ms": duration_ms,
                    "usage": usage,  # Phase 2: Actual token usage from LLM
                    "validation_result": validation_result.to_dict() if validation_result else None  # Week 14: P2.2
                }
            )

        except Exception as e:
            # Calculate execution duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Week 1: Propagate tool errors with full context
            error_details = None

            # Check if it's a ToolExecutionError with structured details
            if isinstance(e, ToolExecutionError):
                error_details = e.to_error_details()
            else:
                # Generic exception - create basic error_details
                error_details = {
                    "error_type": "ExecutionError",
                    "component": "LLMAgentExecutor",
                    "input": {
                        "task_description": task.description,
                        "agent_role": agent.role
                    },
                    "root_cause": str(e),
                    "user_message": f"Task execution failed: {str(e)}",
                    "suggestion": "Check the error message and task description. Use --verbose for more details.",
                    "context": {
                        "exception_type": type(e).__name__,
                        "agent_role": agent.role,
                        "task_id": task.task_id
                    }
                }

            # Week 9: Log failed interaction for training data
            if self.data_collector:
                self.data_collector.log_interaction(
                    task=task,
                    agent=agent,
                    messages=messages,
                    output=None,
                    status="failure",
                    duration_ms=duration_ms,
                    llm_config=self.default_config,
                    provider=self.provider_name,
                    errors=[str(e)],
                    error_details=error_details,
                    orchestrator=self.orchestrator,
                    context_history_length=len(context.history) if context else 0
                )

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                output=None,
                errors=[str(e)],
                error_details=error_details,
                metadata={"agent_role": agent.role}
            )

    def _build_messages(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> list:
        """
        Build message list for LLM with optional ultrathink capability.

        SRP: Message construction logic.
        Week 13: Added chain-of-thought prompting for deeper analysis.
        Phase 4B: Made ULTRATHINK optional (disable for models with language issues).
        Phase 2: Added prompt strategy support with optional validation.
        """
        # Phase 2: Use PromptStrategy if enabled
        if self.use_prompt_strategy:
            # Build structured prompt strategy
            strategy = self._build_prompt_strategy(agent, task, context)

            # Validate if enabled
            if self.validate_prompts and self.prompt_validator:
                validation = self.prompt_validator.validate_strategy(strategy)

                if not validation.passed:
                    # Log validation failure
                    logging.warning(
                        f"Prompt validation failed (score: {validation.score:.1f}): "
                        f"{', '.join(validation.suggestions)}"
                    )

                # Phase 4: Persist metrics if store available (non-blocking)
                try:
                    if self.metrics_store:
                        from src.interface.prompt_metrics_store import PromptMetrics  # local import to avoid cycles
                        template_used = False
                        try:
                            domain = getattr(strategy, 'domain', self._infer_domain(agent.role))
                            loader = getattr(self, 'template_loader', None)
                            template_used = bool(loader and loader.has_template(domain))
                        except Exception:
                            template_used = False
                        metrics = PromptMetrics(
                            timestamp=PromptMetrics.now_iso(),
                            domain=getattr(strategy, 'domain', self._infer_domain(agent.role)),
                            agent_type=agent.role,
                            template_used=template_used,
                            validation_score=validation.score,
                            specificity=validation.specificity,
                            clarity=validation.clarity,
                            completeness=validation.completeness,
                            task_success=None,
                            metadata={
                                "suggestions": validation.suggestions[:5] if validation.suggestions else [],
                                "provider": self.provider_name,
                            },
                        )
                        self.metrics_store.log(metrics)
                except Exception as e:
                    logging.warning(f"Metrics logging failed (non-blocking): {e}")

            # Convert strategy to messages
            return self._strategy_to_messages(strategy, context)

        # Legacy path: Original message building (backward compatibility)
        messages = []

        if self.enable_ultrathink:
            # System message with ULTRATHINK instructions
            system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.

ULTRATHINK MODE: You MUST think step-by-step through problems before answering.
- Use <think></think> tags to show your reasoning process
- Break down complex problems into smaller steps
- Analyze multiple approaches before selecting the best one
- Verify your logic and check for errors
- Be thorough and rigorous in your analysis

IMPORTANT: When providing responses, include specific file:line references.
- Format: path/to/file.py:line_number - description
- Example: "src/adapters/llm/grok_adapter.py:42 - Update return type to GenerationResult"
- Example: "tests/unit/test_adapter.py:15 - Add test for token usage extraction"
- Reference actual code locations where changes should be made

Complete the given task using your expertise and deep analytical thinking."""

            task_prompt = f"""Task: {task.description}

IMPORTANT: Think through this problem step-by-step using <think></think> tags before providing your final answer. Consider:
1. What is being asked?
2. What information do I need?
3. What are the potential approaches?
4. What are the constraints and requirements?
5. What is the optimal solution?

MANDATORY: Your response MUST include at least 3 file:line references.
FORMAT: path/to/file.py:line_number - description

EXAMPLE OUTPUT:
"To implement this feature:

1. Update src/adapters/llm/grok_adapter.py:42 - Change return type to GenerationResult
2. Modify src/use_cases/task_planner.py:75 - Extract .content from result
3. Add tests/unit/test_adapter.py:18 - Verify usage extraction works

[Your detailed explanation here...]"

VALIDATION: Responses without 3+ file:line references will be marked incomplete.

AGENT-SPECIFIC GUIDANCE for {agent.role}:
{self._get_agent_specific_hints(agent.role)}

Think deeply, then provide your response. REMEMBER: Include 3+ file:line references."""
        else:
            # Simple system message (for models with ULTRATHINK compatibility issues)
            system_prompt = f"""You are a {agent.role} agent with capabilities: {', '.join(agent.capabilities)}.

MANDATORY: Include at least 3 file:line references in your response.
- Format: path/to/file.py:line_number - description
- Example: "src/main.py:85 - Add error handling"
- Example: "tests/test_main.py:42 - Verify error is raised"
- Example: "docs/API.md:120 - Document new error codes"

Your response will be validated for file:line references.

Complete the given task using your expertise and professional knowledge."""

            task_prompt = f"""Task: {task.description}

AGENT-SPECIFIC GUIDANCE for {agent.role}:
{self._get_agent_specific_hints(agent.role)}

Provide a clear, professional response based on your expertise."""

        messages.append({"role": "system", "content": system_prompt})

        # Add context history if available
        if context and context.history:
            messages.extend(context.history[-5:])  # Last 5 messages for context

        # Add task as user message
        messages.append({
            "role": "user",
            "content": task_prompt
        })

        return messages

    def _extract_task_description(self, task: Task) -> str:
        """
        Extract task description for cache keying.

        SYD2 FIX: Improves cache hit rate by using semantic task description.
        BUGFIX: Removed task_id to enable cache hits across similar tasks.

        Args:
            task: Task entity

        Returns:
            Task description string (semantic category, not unique ID)
        """
        desc = task.description.lower()

        # Normalize ULTRATHINK tasks for better cache hit rate
        if "ultrathink" in desc:
            # Extract key components: category only (removed task_id)
            # e.g., "ULTRATHINK: Plan refactoring for router" -> "ultrathink:refactoring"
            # This enables cache hits for all refactoring tasks
            if "refactoring" in desc or "refactor" in desc:
                category = "refactoring"
            elif "architecture" in desc:
                category = "architecture"
            elif "scalability" in desc:
                category = "scalability"
            elif "testing" in desc or "test" in desc:
                category = "testing"
            elif "performance" in desc:
                category = "performance"
            else:
                category = "analysis"

            # FIX: Removed task.task_id[:8] - was causing 0% hit rate
            return f"ultrathink:{category}"

        return desc[:100]  # Limit length for cache key

    def _get_agent_specific_hints(self, role: str) -> str:
        """
        Get agent-specific hints to guide output format.

        Phase C: Quality improvement - ensure consistent keyword appearance.
        Helps agents include patterns that AutoChecks looks for.
        """
        hints = {
            "python": """- Include function/class definitions (def, class keywords)
- Add type hints where applicable (: str, -> int, etc.)
- Include docstrings (triple quotes)
- Consider test cases if relevant (test_, assert)

EXAMPLE OUTPUT FORMAT:
"Here's the implementation:

```python
def process_data(items: List[str]) -> Dict[str, int]:
    \"\"\"Process items and return counts.\"\"\"
    return {item: len(item) for item in items}
```

File locations:
- src/utils/processor.py:45 - Add process_data function
- tests/test_processor.py:22 - Add unit test for process_data
- src/main.py:180 - Import and use processor"
""",

            "test": """- Use test function naming (test_* or def test)
- Include assertions (assert statements)
- Import test framework (import pytest or import unittest)
- Use fixtures/mocks where appropriate (@pytest.fixture, Mock)

EXAMPLE OUTPUT FORMAT:
"Test implementation:

```python
import pytest

def test_process_data():
    result = process_data(['a', 'bb'])
    assert result == {'a': 1, 'bb': 2}
```

File locations:
- tests/unit/test_processor.py:15 - Add test_process_data function
- tests/conftest.py:8 - Add fixture for test data
- tests/integration/test_workflow.py:42 - Add integration test"
""",

            "architect": """- Use keywords: "architecture", "diagram", "component", "layer", "service"
- Explain decisions and trade-offs (use "decision", "trade-off", "ADR")
- Reference design patterns (e.g., "factory pattern", "adapter", "SOLID principles")
- Structure your response with sections for: Architecture Overview, Components, Decisions, Trade-offs

EXAMPLE OUTPUT FORMAT:
"Architecture recommendation:

## Overview
The system should use a layered architecture with clear separation:
- Presentation Layer (API/UI)
- Business Logic Layer (Use Cases)
- Data Access Layer (Repositories)

## Key Decisions
1. Use Dependency Injection for loose coupling
2. Apply Repository pattern for data access
3. Implement CQRS for read/write separation

## Trade-offs
- Complexity: More layers = more files (acceptable for maintainability)
- Performance: Abstraction cost negligible vs flexibility gains

File locations:
- docs/architecture/SYSTEM_DESIGN.md:45 - Add layered architecture diagram
- src/use_cases/README.md:12 - Document business logic patterns
- docs/ADR/001-dependency-injection.md:1 - Create ADR for DI decision"
""",

            "database": """- Include SQL operations (CREATE, SELECT, INSERT, etc.)
- Consider indexing strategies (INDEX keyword)
- Add constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL)
- Think about transactions and performance (TRANSACTION, EXPLAIN)

EXAMPLE OUTPUT FORMAT:
"Database schema design:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
```

**Performance considerations:**
- Index on email for fast lookups
- SERIAL for auto-incrementing IDs
- TIMESTAMP for audit trail

**Constraints:**
- UNIQUE prevents duplicate emails
- NOT NULL ensures data integrity

File locations:
- db/migrations/001_create_users_table.sql:1 - Add users table migration
- db/schema.sql:45 - Update master schema
- docs/database/INDEXES.md:22 - Document indexing strategy"
""",

            "devops": """- Always include a CI/CD YAML config example in your response
- Use these exact keywords: "name:", "run:", "steps:", "jobs:"
- For Docker: use words "docker", "Dockerfile", "container", "image"
- Keep it simple and practical

EXAMPLE OUTPUT FORMAT:
"CI/CD pipeline setup:

```yaml
name: CI Pipeline
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t myapp:latest .
      - name: Run tests
        run: docker run myapp:latest pytest
```

**Key components:**
- Uses official GitHub Actions syntax
- Docker build for containerization
- Automated testing on every commit

File locations:
- .github/workflows/ci.yml:1 - Create GitHub Actions workflow
- Dockerfile:1 - Add container build instructions
- docs/DEPLOYMENT.md:55 - Document CI/CD pipeline"
""",

            "qa": """- Use BDD Gherkin syntax: "Feature:", "Scenario:", "Given", "When", "Then", "And"
- Include acceptance criteria validation
- Focus on user perspective and behavior
- Use keywords: "acceptance", "user journey", "feature validation", "scenario"
- Structure scenarios with clear Given/When/Then format

EXAMPLE OUTPUT FORMAT:
"BDD Scenarios for user login feature:

```gherkin
Feature: User Login
  As a registered user
  I want to log in with my credentials
  So that I can access my personalized dashboard

Scenario: Successful login with valid credentials
  Given a registered user with email "test@example.com" and password "pass123"
  And the user is on the login page
  When the user enters their email and password
  And clicks the "Login" button
  Then the user should be redirected to the dashboard
  And a success message "Welcome back!" should be displayed
  And the session cookie should be set

Scenario: Failed login with invalid password
  Given a registered user with email "test@example.com"
  And the user is on the login page
  When the user enters their email and incorrect password
  And clicks the "Login" button
  Then an error message "Invalid credentials" should be displayed
  And the user should remain on the login page
  And no session cookie should be set
```

**Acceptance Criteria Validation:**
✓ User can log in with valid credentials
✓ Failed login shows appropriate error message
✓ Successful login redirects to dashboard
✓ Login sets session cookie correctly

File locations:
- tests/acceptance/features/login.feature:1 - Create Gherkin scenarios
- src/components/LoginForm.tsx:42 - Reference login UI component
- src/api/auth.py:18 - Reference authentication API endpoint
- tests/fixtures/users.py:8 - Add test user data"
""",

            "qa-lead": """- Use BDD Gherkin syntax: "Feature:", "Scenario:", "Given", "When", "Then", "And"
- Include acceptance criteria validation
- Focus on user perspective and behavior
- Use keywords: "acceptance", "user journey", "feature validation", "scenario"
- Structure scenarios with clear Given/When/Then format

EXAMPLE OUTPUT FORMAT:
"BDD Scenarios for user login feature:

```gherkin
Feature: User Login
  As a registered user
  I want to log in with my credentials
  So that I can access my personalized dashboard

Scenario: Successful login with valid credentials
  Given a registered user with email "test@example.com" and password "pass123"
  And the user is on the login page
  When the user enters their email and password
  And clicks the "Login" button
  Then the user should be redirected to the dashboard
  And a success message "Welcome back!" should be displayed
  And the session cookie should be set
```

File locations:
- tests/acceptance/features/login.feature:1 - Create Gherkin scenarios
- src/components/LoginForm.tsx:42 - Reference login UI component
- src/api/auth.py:18 - Reference authentication API endpoint
- tests/fixtures/users.py:8 - Add test user data"
""",

            "qa-engineer": """- Use BDD Gherkin syntax: "Feature:", "Scenario:", "Given", "When", "Then", "And"
- Include acceptance criteria validation
- Focus on user perspective and behavior
- Use keywords: "acceptance", "user journey", "feature validation", "scenario"
- Structure scenarios with clear Given/When/Then format

EXAMPLE OUTPUT FORMAT:
"BDD Scenarios for user login feature:

```gherkin
Feature: User Login
  As a registered user
  I want to log in with my credentials
  So that I can access my personalized dashboard

Scenario: Successful login with valid credentials
  Given a registered user with email "test@example.com" and password "pass123"
  And the user is on the login page
  When the user enters their email and password
  And clicks the "Login" button
  Then the user should be redirected to the dashboard
  And a success message "Welcome back!" should be displayed
  And the session cookie should be set

Scenario: Failed login with invalid password
  Given a registered user with email "test@example.com"
  And the user is on the login page
  When the user enters their email and incorrect password
  And clicks the "Login" button
  Then an error message "Invalid credentials" should be displayed
  And the user should remain on the login page
  And no session cookie should be set
```

**Acceptance Criteria Validation:**
✓ User can log in with valid credentials
✓ Failed login shows appropriate error message
✓ Successful login redirects to dashboard
✓ Login sets session cookie correctly

File locations:
- tests/acceptance/features/login.feature:1 - Create Gherkin scenarios
- src/components/LoginForm.tsx:42 - Reference login UI component
- src/api/auth.py:18 - Reference authentication API endpoint
- tests/fixtures/users.py:8 - Add test user data"
""",

            "exploratory-test-engineer": """- Design exploratory test charters with clear objectives
- Identify risk areas and edge cases
- Use keywords: "exploratory", "test charter", "risk area", "edge case", "usability"
- Focus on discovering unexpected behaviors
- Include bug reporting template

EXAMPLE OUTPUT FORMAT:
"Exploratory Testing Charter for Checkout Flow:

## Test Charter #1: Payment Method Validation (45 min)
**Objective:** Explore payment method selection and validation behavior

**Areas to Explore:**
1. Credit card input validation (format, expiry, CVV)
2. PayPal integration flow and error handling
3. Cryptocurrency payment gateway behavior
4. Payment method switching mid-checkout

**Risk Areas:**
- Payment processing failures without user feedback
- Race conditions when switching payment methods
- Timeout handling during payment gateway calls
- Edge cases: expired cards, insufficient funds, invalid CVV

**Expected Behaviors:**
- Invalid card shows inline error immediately
- Gateway timeouts show user-friendly message
- Payment switching preserves other checkout data
- All payment errors are logged for debugging

**Bug Report Template:**
If found: Document steps, expected vs actual behavior, severity, screenshots

## Test Charter #2: Shipping Address Edge Cases (30 min)
**Objective:** Test address validation with unusual inputs

**Areas to Explore:**
1. PO Box addresses
2. International addresses (non-US)
3. Special characters in address fields
4. Very long address strings
5. Copy-paste behavior

File locations:
- tests/qa/exploratory/checkout_charters.md:1 - Document test charters
- src/pages/CheckoutPage.tsx:95 - Reference checkout UI
- src/components/PaymentForm.tsx:42 - Reference payment component
- tests/qa/bugs/checkout_bugs.md:1 - Track discovered issues"
""",

            "test-case-designer": """- Design comprehensive test plans with clear structure
- Map test scenarios to requirements
- Use keywords: "test plan", "test scenario", "test case", "coverage", "pass/fail criteria"
- Include test data requirements and execution estimates
- Create traceability matrix linking tests to requirements

EXAMPLE OUTPUT FORMAT:
"Test Plan for User Profile Feature:

## 1. Test Objectives
Validate user profile management meets all acceptance criteria including data persistence, validation, email verification, and audit logging.

## 2. Scope
**In Scope:**
- Profile data viewing and editing
- Email change with verification flow
- Password change with current password validation
- Avatar upload with format/size validation
- Audit log for profile changes

**Out of Scope:**
- Account deletion
- Two-factor authentication

## 3. Test Scenarios

### Scenario 1: Profile Data Update
**Requirement:** AC-1 - Profile data persists correctly to database
**Prerequisites:** User logged in with existing profile
**Test Data:** User ID: 12345, Name: "John Doe", Bio: "Software Engineer"
**Steps:**
1. Navigate to profile page
2. Update name to "Jane Smith"
3. Update bio to "Senior Engineer"
4. Click "Save Changes"
**Expected Result:** Changes saved, success message shown, data persists after refresh
**Pass Criteria:** Profile shows updated name and bio immediately and after page reload
**Fail Criteria:** Any field doesn't persist or shows old data after refresh
**Estimated Time:** 3 min

### Scenario 2: Email Change Verification Flow
**Requirement:** AC-2 - Email change requires verification
**Prerequisites:** User logged in, access to test email account
**Test Data:** Current email: old@example.com, New email: new@example.com
**Steps:**
1. Change email in profile settings
2. Check for verification email at new address
3. Click verification link in email
4. Confirm email change in app
**Expected Result:** Verification email sent, link works, email updated after verification
**Pass Criteria:** Email changes only after verification link clicked
**Fail Criteria:** Email changes without verification OR verification link doesn't work
**Estimated Time:** 5 min

## 4. Requirements Traceability Matrix

| Requirement | Test Scenario | Priority | Status |
|-------------|---------------|----------|--------|
| AC-1: Data persistence | Scenario 1 | High | Pending |
| AC-2: Email verification | Scenario 2 | High | Pending |
| AC-3: Password validation | Scenario 3 | High | Pending |
| AC-4: Audit logging | Scenario 4 | Medium | Pending |
| AC-5: Avatar validation | Scenario 5 | Medium | Pending |

## 5. Test Execution Summary
**Total Scenarios:** 5
**Estimated Time:** 22 minutes
**Required Test Data:** 3 user accounts, 5 test images (various formats/sizes)

File locations:
- tests/qa/test_plans/user_profile_test_plan.md:1 - Complete test plan document
- src/models/user_profile.py:15 - Reference profile data model
- src/components/ProfileForm.tsx:68 - Reference profile UI
- tests/fixtures/profile_data.py:1 - Define test data fixtures"
"""
        }

        return hints.get(role, "- Provide clear, specific technical guidance")

    def _build_prompt_strategy(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> PromptStrategy:
        """
        Build PromptStrategy from agent and task.

        Phase 2: Structured prompt building using PromptStrategy entity.
        Phase 3: Prefer template-based strategy when available.

        Args:
            agent: Agent to execute
            task: Task to complete
            context: Optional execution context

        Returns:
            PromptStrategy entity
        """
        domain = self._infer_domain(agent.role)

        # Phase 3: Try template-based strategy first
        try:
            loader = getattr(self, "template_loader", None)
            if loader is None:
                # Lazy import to avoid hard dependency
                try:
                    from src.adapters.prompt.template_loader import TemplateLoader  # type: ignore
                    loader = TemplateLoader()
                    self.template_loader = loader
                except Exception as _e:
                    loader = None
            template = loader.load_template(domain) if loader else None
            if template is not None:
                # Build context text and merge
                context_text = self._build_context_text(agent, task, context)
                merger = getattr(self, "template_merger", None)
                if merger is None:
                    try:
                        from src.use_cases.prompt_template_merger import PromptTemplateMerger  # type: ignore
                        merger = PromptTemplateMerger()
                        self.template_merger = merger
                    except Exception:
                        merger = None
                if merger is not None:
                    strategy = merger.merge(template, agent, task, context_text)
                    return strategy
        except Exception as e:
            logging.warning(f"Template-based prompt strategy failed; falling back. Reason: {e}")

        # Fallback: Persona: Agent role + capabilities
        persona = f"{agent.role} agent with capabilities: {', '.join(agent.capabilities)}"
        if agent.tier:
            persona += f" (Tier {agent.tier})"

        # Goal: Extract from task or use default
        goal = self._extract_goal(task)

        # Task: Task description
        task_text = task.description

        # Context: Build from execution context
        context_text = self._build_context_text(agent, task, context)

        return PromptStrategy(
            persona=persona,
            goal=goal,
            task=task_text,
            context=context_text,
            agent_type=agent.role,
            domain=domain,
        )

    def _extract_goal(self, task: Task) -> str:
        """
        Extract measurable goal from task.

        Phase 2: Simple heuristic to identify goals in task descriptions.

        Args:
            task: Task entity

        Returns:
            Goal statement
        """
        desc = task.description.lower()

        # Look for goal keywords
        goal_keywords = [
            "reduce", "improve", "optimize", "increase", "decrease",
            "achieve", "implement", "create", "build", "design",
            "refactor", "fix", "resolve", "enhance", "upgrade"
        ]

        # If task contains goal keywords, use it as-is
        if any(keyword in desc for keyword in goal_keywords):
            return task.description

        # Otherwise, wrap in goal statement
        return f"Successfully complete: {task.description}"

    def _build_context_text(
        self,
        agent: Agent,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> str:
        """
        Build context section from execution context.

        Phase 2: Gather relevant context information.

        Args:
            agent: Agent entity
            task: Task entity
            context: Optional execution context

        Returns:
            Context text
        """
        parts = []

        # Add agent tier information
        if agent.tier:
            parts.append(f"Agent Tier: {agent.tier}")

        # Add context history if available
        if context and context.history:
            parts.append(f"Previous interactions: {len(context.history)}")

        # Add ULTRATHINK mode info
        if self.enable_ultrathink:
            parts.append("Mode: ULTRATHINK (step-by-step reasoning required)")

        # Add task priority if high
        if hasattr(task, 'priority') and task.priority and task.priority <= 2:
            parts.append(f"Priority: {task.priority} (High)")

        return "\n".join(parts) if parts else "Standard execution context"

    def _infer_domain(self, role: str) -> str:
        """
        Infer domain from agent role.

        Phase 2: Map agent roles to domains for template selection.

        Args:
            role: Agent role string

        Returns:
            Domain classification
        """
        role_lower = role.lower()

        # Domain mapping based on role keywords
        domain_map = {
            "frontend": "frontend",
            "backend": "backend",
            "database": "database",
            "test": "testing",
            "qa": "qa",
            "devops": "devops",
            "architect": "architecture",
            "research": "research",
            "python": "python",
            "data": "data"
        }

        # Find matching domain
        for key, domain in domain_map.items():
            if key in role_lower:
                return domain

        return "general"

    def _strategy_to_messages(
        self,
        strategy: PromptStrategy,
        context: Optional[ExecutionContext]
    ) -> list:
        """
        Convert PromptStrategy to LLM message format.

        Phase 2: Transform structured strategy into messages.

        Args:
            strategy: PromptStrategy entity
            context: Optional execution context

        Returns:
            List of message dictionaries
        """
        messages = []

        # System message from strategy
        system_prompt = strategy.to_system_prompt(include_ultrathink=self.enable_ultrathink)
        messages.append({"role": "system", "content": system_prompt})

        # Add context history if available
        if context and context.history:
            messages.extend(context.history[-5:])  # Last 5 messages for context

        # User message from strategy
        user_prompt = strategy.to_user_prompt()
        messages.append({"role": "user", "content": user_prompt})

        return messages
