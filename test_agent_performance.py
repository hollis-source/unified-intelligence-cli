#!/usr/bin/env python3
"""
Agent Performance Test Harness

Tests 5 specialist agents with 20 real tasks each:
1. Python Engineer - Code quality, refactoring, patterns
2. Software Architect - System design, Clean Architecture
3. Test Engineer - Unit, integration, E2E test generation
4. DevOps Engineer - CI/CD, deployment, monitoring
5. Research Analyst - Documentation, investigation, planning

Philosophy: Continuous improvement. Baseline 20% → Target 80%+.

Usage:
    python test_agent_performance.py --agent python-engineer
    python test_agent_performance.py --agent all --save-baseline
    python test_agent_performance.py --compare baseline.json current.json
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.entity import Agent, Task, ExecutionStatus
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.factories.provider_factory import ProviderFactory
from src.interface import LLMConfig


@dataclass
class TaskResult:
    """Single task execution result"""
    task_id: str
    description: str
    agent_role: str
    success: bool
    duration_seconds: float
    quality_score: float  # 1-10
    specificity_score: float  # 0-100% (code references)
    token_count: int
    cost_estimate: float
    error: Optional[str] = None
    output_preview: str = ""


@dataclass
class AgentPerformanceMetrics:
    """Aggregate metrics for an agent"""
    agent_role: str
    total_tasks: int
    completion_rate: float  # %
    avg_quality_score: float  # 1-10
    avg_latency_p50: float  # seconds
    avg_latency_p95: float  # seconds
    avg_specificity: float  # %
    total_cost: float
    cost_per_task: float
    timestamp: str


# ============================================================================
# TEST TASK DEFINITIONS (20 per agent)
# ============================================================================

PYTHON_ENGINEER_TASKS = [
    "Refactor src/adapters/agent/llm_executor.py to extract error handling into separate ErrorHandler class",
    "Apply SOLID principles to src/routing/team_router.py - identify SRP violations",
    "Add type hints to all functions in src/use_cases/task_coordinator.py",
    "Extract magic numbers from src/priority_queue/priority_calculator.py into named constants",
    "Refactor nested conditionals in src/adapters/llm/hybrid_executor.py using guard clauses",
    "Implement builder pattern for Agent creation in src/factories/agent_factory.py",
    "Add docstrings (Google style) to all public methods in src/entity/metrics.py",
    "Identify and fix code duplication in src/routing/hierarchical_router.py",
    "Apply DRY principle to src/adapters/orchestration/hybrid_orchestrator.py",
    "Refactor src/dsl/adapters/htn_compiler.py to use strategy pattern for compilation",
    "Add input validation to src/entity/agent_team.py constructor",
    "Extract configuration logic from src/composition.py into ConfigLoader class",
    "Implement factory method pattern for creating LLM providers in src/factories/provider_factory.py",
    "Refactor src/use_cases/task_planner.py to separate planning logic from execution",
    "Add error recovery mechanism to src/adapters/llm/auggie_executor.py",
    "Apply interface segregation to src/interface/agent_executor.py",
    "Refactor src/routing/model_selector.py to use polymorphism instead of conditionals",
    "Extract database logic from src/priority_queue/redis_adapter.py into repository pattern",
    "Add logging to all exception handlers in src/adapters/agent/capability_selector.py",
    "Refactor src/entity/htn/htn_node.py to use composite pattern for task hierarchy",
]

SOFTWARE_ARCHITECT_TASKS = [
    "Design Clean Architecture layers for new RAG module (entities, use cases, adapters)",
    "Create architecture decision record (ADR) for choosing Redis over in-memory queue",
    "Design hexagonal architecture ports for external LLM providers",
    "Propose dependency injection strategy for src/composition.py",
    "Design event-driven architecture for agent communication",
    "Create component diagram showing relationships between routing, orchestration, and execution",
    "Design scalability strategy for handling 1000+ concurrent tasks",
    "Propose caching architecture for LLM responses (src/adapters/agent/llm_cache.py)",
    "Design monitoring architecture using Prometheus and Grafana",
    "Create sequence diagram for task execution flow through HTN compiler",
    "Design plugin architecture for adding new agent types",
    "Propose microservices decomposition strategy for monolithic codebase",
    "Design API gateway pattern for multi-model LLM routing",
    "Create architecture for distributed task queue with fault tolerance",
    "Design observability strategy (logging, metrics, tracing)",
    "Propose database schema for storing agent performance metrics",
    "Design authentication and authorization architecture for multi-tenant system",
    "Create disaster recovery plan for production deployment",
    "Design CI/CD pipeline architecture with automated testing gates",
    "Propose refactoring roadmap to eliminate circular dependencies",
]

TEST_ENGINEER_TASKS = [
    "Generate unit tests for src/entity/metrics.py MetricsCollector class",
    "Create integration tests for src/routing/team_router.py with mock agents",
    "Write E2E test for complete task execution flow from CLI to result",
    "Generate pytest fixtures for common test data in tests/conftest.py",
    "Create property-based tests for src/dsl/adapters/htn_compiler.py using Hypothesis",
    "Write performance tests for src/adapters/llm/hybrid_executor.py (latency benchmarks)",
    "Generate mocks for ITextGenerator interface in tests/unit/interface/",
    "Create test suite for error handling in src/use_cases/task_coordinator.py",
    "Write contract tests for LLM provider adapters (OpenAI, Anthropic, Grok)",
    "Generate load tests for priority queue with 10,000 concurrent tasks",
    "Create regression test suite for routing accuracy (90%+ target)",
    "Write security tests for input validation in src/entity/agent.py",
    "Generate mutation tests to verify test suite quality",
    "Create smoke tests for production deployment validation",
    "Write chaos engineering tests for fault injection",
    "Generate visual regression tests for CLI output formatting",
    "Create test data generators for realistic task distributions",
    "Write tests for concurrent access to src/entity/metrics.py (thread safety)",
    "Generate code coverage report and identify untested branches",
    "Create test documentation with examples for each test category",
]

DEVOPS_ENGINEER_TASKS = [
    "Design Docker Compose setup for local development with Redis and SurrealDB",
    "Create Kubernetes deployment manifests for production (k8s/ directory)",
    "Set up Prometheus metrics collection for agent performance monitoring",
    "Design CI/CD pipeline using GitHub Actions with automated testing",
    "Create health check endpoints for all services",
    "Design log aggregation strategy using ELK stack or Loki",
    "Set up automated backup strategy for Redis priority queue",
    "Create infrastructure as code using Terraform for AWS deployment",
    "Design auto-scaling strategy based on queue depth metrics",
    "Set up alerting rules for critical failures (PagerDuty/Slack)",
    "Create deployment rollback strategy with blue-green deployment",
    "Design secrets management using Vault or AWS Secrets Manager",
    "Set up distributed tracing using Jaeger or OpenTelemetry",
    "Create performance monitoring dashboard in Grafana",
    "Design disaster recovery runbook with RTO/RPO targets",
    "Set up automated security scanning (Snyk, Trivy) in CI pipeline",
    "Create resource quotas and limits for Kubernetes pods",
    "Design network policies for service-to-service communication",
    "Set up automated certificate rotation for TLS",
    "Create cost optimization strategy for cloud infrastructure",
]

RESEARCH_ANALYST_TASKS = [
    "Research best practices for Clean Architecture in Python projects",
    "Investigate optimal LoRA rank values for 7B parameter models with evidence",
    "Compare LangGraph vs custom HTN orchestration for multi-agent systems",
    "Research GPU pricing for inference workloads (A100, H100, L40S)",
    "Investigate category theory applications in workflow composition",
    "Research best practices for prompt engineering in code generation",
    "Compare vector databases for RAG (Pinecone, Weaviate, Qdrant, ChromaDB)",
    "Investigate model quantization techniques (GGUF, GPTQ, AWQ)",
    "Research distributed computing frameworks for multi-agent systems",
    "Investigate best practices for LLM response caching strategies",
    "Research evaluation metrics for code generation quality",
    "Compare agentic frameworks (AutoGen, CrewAI, LangGraph, custom)",
    "Investigate optimal batch sizes for parallel LLM inference",
    "Research security best practices for LLM API key management",
    "Investigate cost optimization strategies for LLM API usage",
    "Research best practices for testing AI systems",
    "Compare deployment strategies for local LLM inference (llama.cpp, vLLM, TGI)",
    "Investigate monitoring best practices for production AI systems",
    "Research data collection strategies for model fine-tuning",
    "Investigate ethical considerations for autonomous AI agents",
]


# ============================================================================
# SCORING RUBRICS
# ============================================================================

def score_quality(output: str, task_description: str, agent_role: str) -> float:
    """
    Score output quality (1-10) based on agent-specific rubric.
    
    Rubric:
    - 9-10: Exceptional - Exceeds requirements, production-ready
    - 7-8: Good - Meets requirements, minor improvements needed
    - 5-6: Acceptable - Partial completion, significant gaps
    - 3-4: Poor - Minimal effort, major issues
    - 1-2: Failure - Incorrect or unusable
    
    Args:
        output: Agent output text
        task_description: Original task
        agent_role: Agent type for context
        
    Returns:
        Quality score 1.0-10.0
    """
    score = 5.0  # Baseline
    
    # Length check (too short = incomplete)
    if len(output) < 100:
        score -= 2.0
    elif len(output) > 500:
        score += 1.0
        
    # Structure check (markdown formatting)
    if "```" in output:  # Code blocks
        score += 1.0
    if "#" in output:  # Headers
        score += 0.5
    if "- " in output or "* " in output:  # Lists
        score += 0.5
        
    # Specificity check (file paths, line numbers)
    if "src/" in output or "tests/" in output:
        score += 1.0
    if ".py" in output:
        score += 0.5
        
    # Agent-specific criteria
    if agent_role == "python-engineer":
        if any(kw in output.lower() for kw in ["solid", "dry", "refactor", "pattern"]):
            score += 1.0
        if "class " in output or "def " in output:
            score += 0.5
            
    elif agent_role == "software-architect":
        if any(kw in output.lower() for kw in ["architecture", "design", "layer", "component"]):
            score += 1.0
        if "diagram" in output.lower() or "adr" in output.lower():
            score += 0.5
            
    elif agent_role == "test-engineer":
        if "test" in output.lower() and ("pytest" in output.lower() or "assert" in output.lower()):
            score += 1.0
        if "@pytest" in output or "def test_" in output:
            score += 1.0
            
    elif agent_role == "devops-engineer":
        if any(kw in output.lower() for kw in ["docker", "kubernetes", "ci/cd", "deploy"]):
            score += 1.0
        if "yaml" in output.lower() or "dockerfile" in output.lower():
            score += 0.5
            
    elif agent_role == "research-analyst":
        if any(kw in output.lower() for kw in ["research", "compare", "analysis", "evidence"]):
            score += 1.0
        if "source:" in output.lower() or "reference:" in output.lower():
            score += 0.5
    
    return min(10.0, max(1.0, score))


def score_specificity(output: str) -> float:
    """
    Score specificity (0-100%) based on code references.
    
    Specificity = % of output with concrete references:
    - File paths (src/module/file.py)
    - Line numbers (line 42)
    - Function/class names (MyClass.method())
    - Specific values (threshold=0.9)
    
    Args:
        output: Agent output text
        
    Returns:
        Specificity percentage 0.0-100.0
    """
    if not output:
        return 0.0
        
    specificity_indicators = [
        r"src/[\w/]+\.py",  # File paths
        r"line \d+",  # Line numbers
        r":\d+",  # Line references
        r"def \w+",  # Function definitions
        r"class \w+",  # Class definitions
        r"\w+\(\)",  # Function calls
        r"=\s*[\d.]+",  # Numeric values
        r"threshold|limit|max|min",  # Specific parameters
    ]
    
    import re
    matches = 0
    for pattern in specificity_indicators:
        matches += len(re.findall(pattern, output))
    
    # Normalize by output length (words)
    words = len(output.split())
    if words == 0:
        return 0.0
        
    specificity = min(100.0, (matches / words) * 100 * 5)  # Scale factor
    return specificity


def estimate_cost(token_count: int, model: str = "gpt-4") -> float:
    """
    Estimate cost based on token count.
    
    Pricing (approximate):
    - GPT-4: $0.03/1K input, $0.06/1K output
    - GPT-3.5: $0.001/1K input, $0.002/1K output
    - Claude Sonnet: $0.003/1K input, $0.015/1K output
    
    Args:
        token_count: Total tokens (input + output)
        model: Model name
        
    Returns:
        Cost in USD
    """
    # Assume 50/50 input/output split
    input_tokens = token_count // 2
    output_tokens = token_count // 2
    
    if "gpt-4" in model.lower():
        return (input_tokens * 0.03 + output_tokens * 0.06) / 1000
    elif "gpt-3.5" in model.lower():
        return (input_tokens * 0.001 + output_tokens * 0.002) / 1000
    elif "claude" in model.lower():
        return (input_tokens * 0.003 + output_tokens * 0.015) / 1000
    else:
        return (input_tokens * 0.01 + output_tokens * 0.02) / 1000  # Default


# ============================================================================
# TEST EXECUTION
# ============================================================================

def run_agent_test(
    agent: Agent,
    task_description: str,
    task_id: str,
    executor: LLMAgentExecutor
) -> TaskResult:
    """Execute single task and collect metrics"""
    print(f"  [{task_id}] {task_description[:60]}...")
    
    task = Task(description=task_description, task_id=task_id)
    
    start_time = time.time()
    try:
        result = executor.execute(agent, task)
        duration = time.time() - start_time
        
        output = result.output if result.status == ExecutionStatus.SUCCESS else ""
        success = result.status == ExecutionStatus.SUCCESS
        
        # Score output
        quality = score_quality(output, task_description, agent.role)
        specificity = score_specificity(output)
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        token_count = (len(task_description) + len(output)) // 4
        cost = estimate_cost(token_count)
        
        return TaskResult(
            task_id=task_id,
            description=task_description,
            agent_role=agent.role,
            success=success,
            duration_seconds=duration,
            quality_score=quality,
            specificity_score=specificity,
            token_count=token_count,
            cost_estimate=cost,
            error=result.error_details if not success else None,
            output_preview=output[:200]
        )

    except Exception as e:
        duration = time.time() - start_time
        return TaskResult(
            task_id=task_id,
            description=task_description,
            agent_role=agent.role,
            success=False,
            duration_seconds=duration,
            quality_score=1.0,
            specificity_score=0.0,
            token_count=0,
            cost_estimate=0.0,
            error=str(e),
            output_preview=""
        )


def calculate_percentile(values: List[float], percentile: int) -> float:
    """Calculate percentile from list of values"""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    # Use proper percentile calculation (0-based indexing)
    if percentile == 0:
        return sorted_values[0]
    if percentile == 100:
        return sorted_values[-1]
    index = int((len(sorted_values) - 1) * percentile / 100)
    return sorted_values[index]


def aggregate_metrics(results: List[TaskResult]) -> AgentPerformanceMetrics:
    """Aggregate task results into performance metrics"""
    if not results:
        return AgentPerformanceMetrics(
            agent_role="unknown",
            total_tasks=0,
            completion_rate=0.0,
            avg_quality_score=0.0,
            avg_latency_p50=0.0,
            avg_latency_p95=0.0,
            avg_specificity=0.0,
            total_cost=0.0,
            cost_per_task=0.0,
            timestamp=datetime.now().isoformat()
        )

    agent_role = results[0].agent_role
    total_tasks = len(results)
    successful = [r for r in results if r.success]
    completion_rate = (len(successful) / total_tasks) * 100

    # Quality metrics
    quality_scores = [r.quality_score for r in successful] if successful else [0.0]
    avg_quality = sum(quality_scores) / len(quality_scores)

    # Latency metrics
    latencies = [r.duration_seconds for r in results]
    p50 = calculate_percentile(latencies, 50)
    p95 = calculate_percentile(latencies, 95)

    # Specificity
    specificity_scores = [r.specificity_score for r in successful] if successful else [0.0]
    avg_specificity = sum(specificity_scores) / len(specificity_scores)

    # Cost
    total_cost = sum(r.cost_estimate for r in results)
    cost_per_task = total_cost / total_tasks if total_tasks > 0 else 0.0

    return AgentPerformanceMetrics(
        agent_role=agent_role,
        total_tasks=total_tasks,
        completion_rate=completion_rate,
        avg_quality_score=avg_quality,
        avg_latency_p50=p50,
        avg_latency_p95=p95,
        avg_specificity=avg_specificity,
        total_cost=total_cost,
        cost_per_task=cost_per_task,
        timestamp=datetime.now().isoformat()
    )


def run_agent_suite(agent_role: str, provider: str = "auto") -> Tuple[AgentPerformanceMetrics, List[TaskResult]]:
    """Run full test suite for one agent"""
    print(f"\n{'='*80}")
    print(f"Testing Agent: {agent_role.upper()}")
    print(f"{'='*80}\n")

    # Get tasks for agent
    task_map = {
        "python-engineer": PYTHON_ENGINEER_TASKS,
        "software-architect": SOFTWARE_ARCHITECT_TASKS,
        "test-engineer": TEST_ENGINEER_TASKS,
        "devops-engineer": DEVOPS_ENGINEER_TASKS,
        "research-analyst": RESEARCH_ANALYST_TASKS,
    }

    tasks = task_map.get(agent_role, [])
    if not tasks:
        print(f"❌ Unknown agent role: {agent_role}")
        return None, []

    # Create agent
    capabilities = [agent_role.replace("-", " ")]
    agent = Agent(role=agent_role, capabilities=capabilities)

    # Create executor
    llm_provider = ProviderFactory.create_provider(provider)
    config = LLMConfig(temperature=0.7, max_tokens=2000)
    executor = LLMAgentExecutor(llm_provider, config)

    # Run tasks
    results = []
    for i, task_desc in enumerate(tasks, 1):
        task_id = f"{agent_role}-{i:02d}"
        result = run_agent_test(agent, task_desc, task_id, executor)
        results.append(result)

        # Progress indicator
        status = "✓" if result.success else "✗"
        print(f"    {status} Quality: {result.quality_score:.1f}/10, "
              f"Specificity: {result.specificity_score:.0f}%, "
              f"Time: {result.duration_seconds:.1f}s")

    # Aggregate metrics
    metrics = aggregate_metrics(results)

    # Print summary
    print(f"\n{'─'*80}")
    print(f"SUMMARY: {agent_role}")
    print(f"{'─'*80}")
    print(f"Completion Rate:    {metrics.completion_rate:.1f}%")
    print(f"Avg Quality Score:  {metrics.avg_quality_score:.1f}/10")
    print(f"Avg Specificity:    {metrics.avg_specificity:.1f}%")
    print(f"Latency P50:        {metrics.avg_latency_p50:.2f}s")
    print(f"Latency P95:        {metrics.avg_latency_p95:.2f}s")
    print(f"Total Cost:         ${metrics.total_cost:.4f}")
    print(f"Cost per Task:      ${metrics.cost_per_task:.4f}")
    print(f"{'─'*80}\n")

    return metrics, results


def save_results(metrics: List[AgentPerformanceMetrics], results: List[TaskResult], filename: str):
    """Save results to JSON file"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "metrics": [asdict(m) for m in metrics],
        "detailed_results": [asdict(r) for r in results]
    }

    output_path = Path("data/agent_performance") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Results saved to {output_path}")


def compare_results(baseline_file: str, current_file: str):
    """Compare two result files and show improvement"""
    baseline = json.load(open(baseline_file))
    current = json.load(open(current_file))

    print(f"\n{'='*80}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*80}\n")
    print(f"Baseline: {baseline_file}")
    print(f"Current:  {current_file}\n")

    baseline_metrics = {m["agent_role"]: m for m in baseline["metrics"]}
    current_metrics = {m["agent_role"]: m for m in current["metrics"]}

    for agent_role in baseline_metrics:
        if agent_role not in current_metrics:
            continue

        b = baseline_metrics[agent_role]
        c = current_metrics[agent_role]

        print(f"{agent_role.upper()}")
        print(f"{'─'*80}")

        # Calculate deltas
        completion_delta = c["completion_rate"] - b["completion_rate"]
        quality_delta = c["avg_quality_score"] - b["avg_quality_score"]
        specificity_delta = c["avg_specificity"] - b["avg_specificity"]
        latency_delta = c["avg_latency_p95"] - b["avg_latency_p95"]

        # Format with arrows
        def format_delta(delta, suffix="", reverse=False):
            arrow = "↑" if (delta > 0) != reverse else "↓"
            color = "+" if (delta > 0) != reverse else ""
            return f"{color}{delta:+.1f}{suffix} {arrow}"

        print(f"  Completion Rate:  {c['completion_rate']:.1f}% ({format_delta(completion_delta, '%')})")
        print(f"  Quality Score:    {c['avg_quality_score']:.1f}/10 ({format_delta(quality_delta)})")
        print(f"  Specificity:      {c['avg_specificity']:.1f}% ({format_delta(specificity_delta, '%')})")
        print(f"  Latency P95:      {c['avg_latency_p95']:.2f}s ({format_delta(latency_delta, 's', reverse=True)})")
        print()


def main():
    parser = argparse.ArgumentParser(description="Agent Performance Test Harness")
    parser.add_argument(
        "--agent",
        choices=["python-engineer", "software-architect", "test-engineer",
                 "devops-engineer", "research-analyst", "all"],
        default="all",
        help="Agent to test (default: all)"
    )
    parser.add_argument("--provider", default="auto", help="LLM provider (default: auto)")
    parser.add_argument("--save-baseline", action="store_true", help="Save as baseline.json")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "CURRENT"),
                       help="Compare two result files")

    args = parser.parse_args()

    if args.compare:
        compare_results(args.compare[0], args.compare[1])
        return

    # Run tests
    agents_to_test = [
        "python-engineer", "software-architect", "test-engineer",
        "devops-engineer", "research-analyst"
    ] if args.agent == "all" else [args.agent]

    all_metrics = []
    all_results = []

    for agent_role in agents_to_test:
        metrics, results = run_agent_suite(agent_role, args.provider)
        if metrics:
            all_metrics.append(metrics)
            all_results.extend(results)

    # Save results
    filename = "baseline.json" if args.save_baseline else f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_results(all_metrics, all_results, filename)

    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    print(f"Total Agents Tested: {len(all_metrics)}")
    print(f"Total Tasks:         {sum(m.total_tasks for m in all_metrics)}")
    print(f"Avg Completion:      {sum(m.completion_rate for m in all_metrics) / len(all_metrics):.1f}%")
    print(f"Avg Quality:         {sum(m.avg_quality_score for m in all_metrics) / len(all_metrics):.1f}/10")
    print(f"Total Cost:          ${sum(m.total_cost for m in all_metrics):.4f}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()


