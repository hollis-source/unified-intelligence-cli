# Milestone 3: Autonomous Task Generation - Planning Document

**Timeline**: Weeks 7-10  
**Objective**: Enable system to generate its own improvement tasks from context analysis  
**Target Autonomy**: 75% (up from 60% at M2)

---

## Executive Summary

M3 represents a critical leap in ATADO's autonomy: the system will analyze its own context (codebase, metrics, test coverage) and autonomously generate improvement tasks. This closes the "human-in-the-loop" bottleneck where all improvement tasks currently require manual definition.

**Key Innovation**: Self-directed improvement through context-aware task generation.

---

## Objectives

### Primary Objectives
1. **Context Analysis Engine**: Analyze git history, test coverage, metrics trends, and codebase health
2. **Task Generation System**: LLM-driven generation of prioritized improvement tasks
3. **Self-Improvement Loop**: Analyze → Generate → Execute → Measure cycle
4. **Active Learning**: Identify weak domains and prioritize pattern collection

### Success Criteria
- System proposes 10+ valid improvement tasks per week
- 70%+ of proposed tasks accepted and executed
- Improvement velocity increases 2x (measured by success criteria progress)
- Autonomy increases from 60% to 75%

---

## Architecture

### M3.1: Context Analysis Engine

**Purpose**: Gather signals about system health and improvement opportunities

**Components**:

1. **Git History Analyzer** (`src/analysis/git_analyzer.py`)
   - Parse recent commits (last 30 days)
   - Identify patterns: bug fixes, features, refactors
   - Detect high-churn files (>10 commits/month)
   - Extract common issues from commit messages
   
   **Output**: `GitAnalysis` with high-churn files, commit patterns, issue themes

2. **Test Coverage Analyzer** (`src/analysis/coverage_analyzer.py`)
   - Parse coverage reports (pytest-cov, coverage.py)
   - Identify uncovered code paths
   - Detect low-coverage modules (<70%)
   - Prioritize critical paths without tests
   
   **Output**: `CoverageAnalysis` with uncovered files, low-coverage modules, priority list

3. **Metrics Trend Analyzer** (`src/analysis/metrics_analyzer.py`)
   - Load historical metrics (last 30 days)
   - Detect degrading trends (accuracy, latency, cost)
   - Identify anomalies (sudden spikes/drops)
   - Correlate metrics with code changes
   
   **Output**: `MetricsAnalysis` with degrading metrics, anomalies, correlations

4. **Codebase Health Scorer** (`src/analysis/health_scorer.py`)
   - Aggregate signals from all analyzers
   - Compute health score: 0-100
   - Factors: coverage (30%), complexity (20%), debt (20%), test pass rate (20%), metrics (10%)
   - Identify top improvement opportunities
   
   **Output**: `HealthScore` with overall score, factor breakdown, top opportunities

5. **Context Aggregator** (`src/analysis/context_aggregator.py`)
   - Combine all analyzer outputs
   - Rank improvement opportunities by impact
   - Generate unified context object
   
   **Output**: `SystemContext` with all analyses, ranked opportunities

**Data Flow**:
```
Git Repo → GitAnalyzer → GitAnalysis
Coverage Report → CoverageAnalyzer → CoverageAnalysis
Metrics DB → MetricsAnalyzer → MetricsAnalysis
                                    ↓
                            ContextAggregator → SystemContext
                                    ↓
                            TaskGenerator
```

---

### M3.2: Task Generation System

**Purpose**: Generate prioritized improvement tasks from context

**Components**:

1. **LLM-Driven Task Generator** (`src/generation/task_generator.py`)
   - Prompt LLM with SystemContext
   - Generate 10-20 improvement tasks per week
   - Structured output format (JSON schema)
   - Task types: bug fix, test addition, refactor, optimization, documentation
   
   **Prompt Template**:
   ```
   You are an autonomous software improvement agent. Analyze the following system context
   and generate 10-20 high-impact improvement tasks.
   
   Context:
   - Health Score: {health_score}/100
   - High-Churn Files: {high_churn_files}
   - Low-Coverage Modules: {low_coverage_modules}
   - Degrading Metrics: {degrading_metrics}
   
   Generate tasks in JSON format:
   [
     {
       "id": "task_001",
       "type": "test_addition",
       "priority": "high",
       "description": "Add unit tests for {module}",
       "rationale": "Module has 45% coverage, below 70% threshold",
       "estimated_effort_minutes": 60,
       "success_criteria": "Coverage >70%"
     },
     ...
   ]
   ```

2. **Priority Ranking Algorithm** (`src/generation/priority_ranker.py`)
   - Rank tasks by: impact × urgency / effort
   - Impact: health score delta (estimated)
   - Urgency: metric trend severity
   - Effort: estimated minutes
   
   **Formula**: `priority_score = (impact * urgency) / log(effort + 1)`

3. **Task Validation and Filtering** (`src/generation/task_validator.py`)
   - Filter out invalid tasks (malformed, duplicate, dangerous)
   - Validate against safety governance rules
   - Ensure all tasks have clear success criteria
   - Check for dependencies and conflicts
   
   **Validation Rules**:
   - Must have description, type, priority, success criteria
   - Must pass safety governance checks
   - Must not duplicate existing tasks
   - Must have realistic effort estimate (<240 minutes)

4. **Template-Based Task Expansion** (`src/generation/task_expander.py`)
   - Expand high-level goals into concrete task sequences
   - Use task templates from `data/task_templates/`
   - Fill in placeholders with context-specific values
   
   **Example**: "Improve test coverage" → ["Add tests for module A", "Add tests for module B", ...]

5. **HTN Integration** (`src/generation/htn_integrator.py`)
   - Feed generated tasks into HTN decomposer
   - Create hierarchical task networks
   - Enable multi-step task execution
   
   **Output**: HTN-compatible task structures

**Data Flow**:
```
SystemContext → TaskGenerator → RawTasks
                                    ↓
                            TaskValidator → ValidTasks
                                    ↓
                            PriorityRanker → RankedTasks
                                    ↓
                            TaskExpander → ExpandedTasks
                                    ↓
                            HTNIntegrator → ExecutableTasks
```

---

### M3.3: Self-Improvement Loop

**Purpose**: Autonomous analyze → generate → execute → measure cycle

**Components**:

1. **Self-Improvement Orchestrator** (`src/orchestration/self_improvement.py`)
   - Run full cycle on schedule (daily or weekly)
   - Coordinate all components
   - Track cycle metrics
   
   **Cycle Steps**:
   1. Analyze context (M3.1)
   2. Generate tasks (M3.2)
   3. Execute top-N tasks (existing execution infrastructure)
   4. Measure outcomes (existing metrics)
   5. Update health score
   6. Repeat

2. **Automatic Task Scheduling** (`src/orchestration/task_scheduler.py`)
   - Schedule generated tasks based on priority
   - Respect resource limits (CPU, memory, cost)
   - Avoid conflicts with manual tasks
   - Rate limiting (max 10 tasks/day)
   
   **Scheduling Algorithm**:
   - Sort by priority score
   - Check resource availability
   - Schedule highest-priority tasks first
   - Defer low-priority tasks to next cycle

3. **Success/Failure Feedback Integration** (`src/orchestration/feedback_integrator.py`)
   - Feed execution results back to context analyzer
   - Update health scores based on outcomes
   - Adjust task generation based on success patterns
   - Learn which task types are most effective
   
   **Feedback Loop**:
   ```
   Task Execution → Success/Failure → Update Health Score
                                    ↓
                            Adjust Task Generation Weights
                                    ↓
                            Next Cycle Uses Updated Weights
   ```

4. **Improvement Velocity Tracking** (`src/monitoring/velocity_tracker.py`)
   - Track tasks/week, success rate, health score delta
   - Measure improvement velocity
   - Detect stagnation (no improvement for 2 weeks)
   - Alert on velocity drops
   
   **Metrics**:
   - Tasks proposed per week
   - Tasks executed per week
   - Success rate (%)
   - Health score delta per week
   - Velocity trend (increasing/decreasing/stable)

5. **Weekly Self-Improvement Reports** (`src/reporting/self_improvement_report.py`)
   - Auto-generate report of tasks proposed, executed, succeeded
   - Impact on metrics (accuracy, latency, cost)
   - Health score trend
   - Top improvements and failures
   
   **Report Format**: Markdown with charts, posted to Slack

---

### M3.4: Active Learning

**Purpose**: Identify weak domains and prioritize pattern collection

**Components**:

1. **Weak Domain Identifier** (`src/learning/weak_domain_identifier.py`)
   - Detect domains with <70% accuracy or <20 patterns
   - Rank by weakness score: `(100 - accuracy) * (1 / pattern_count)`
   - Flag for active collection
   
   **Output**: List of weak domains with weakness scores

2. **Pattern Collection Prioritizer** (`src/learning/collection_prioritizer.py`)
   - Prioritize pattern collection for weak domains
   - Generate collection tasks (e.g., "Collect 20 backend patterns")
   - Schedule collection jobs
   
   **Priority Formula**: `priority = weakness_score * business_impact`

3. **Auto-Trigger Collection Jobs** (`src/learning/collection_trigger.py`)
   - Automatically run `build_rag_patterns.py` for weak domains
   - Schedule weekly collection jobs
   - Monitor collection progress
   
   **Trigger Conditions**:
   - Domain accuracy <70%
   - Pattern count <20
   - No collection in last 7 days

4. **Pattern Distribution Balancer** (`src/learning/distribution_balancer.py`)
   - Ensure all domains have >=20 patterns and >=70% accuracy
   - Balance pattern distribution (within 20% of mean)
   - Prevent over-collection in strong domains
   
   **Balancing Algorithm**:
   - Compute mean pattern count across domains
   - Identify domains <80% of mean
   - Prioritize collection for under-represented domains

---

## Implementation Plan

### Week 7: Context Analysis Engine
- **Day 1-2**: Git analyzer, coverage analyzer
- **Day 3-4**: Metrics analyzer, health scorer
- **Day 5**: Context aggregator, integration tests

### Week 8: Task Generation System
- **Day 1-2**: LLM-driven task generator, prompt engineering
- **Day 3**: Priority ranker, task validator
- **Day 4**: Template expander, HTN integrator
- **Day 5**: Integration tests, validation

### Week 9: Self-Improvement Loop
- **Day 1-2**: Self-improvement orchestrator, task scheduler
- **Day 3**: Feedback integrator, velocity tracker
- **Day 4**: Weekly reporting
- **Day 5**: End-to-end testing

### Week 10: Active Learning & Validation
- **Day 1-2**: Weak domain identifier, collection prioritizer
- **Day 3**: Auto-trigger collection, distribution balancer
- **Day 4**: Integration testing
- **Day 5**: M3 validation, documentation

---

## Success Metrics

| Metric | Baseline (M2) | Target (M3) | Measurement |
|--------|---------------|-------------|-------------|
| Tasks proposed/week | 0 | 10+ | Task generator output |
| Task acceptance rate | N/A | 70%+ | Manual review + auto-execution |
| Improvement velocity | Low | 2x | Health score delta/week |
| Autonomy rate | 60% | 75% | Human intervention % |
| Weak domain coverage | Unknown | 100% | All domains >=20 patterns |

---

## Risks & Mitigations

### Risks
1. **LLM generates invalid/dangerous tasks**
   - Mitigation: Task validator + safety governance (M2)
   
2. **Task generation too aggressive (resource exhaustion)**
   - Mitigation: Rate limiting (max 10 tasks/day), resource quotas
   
3. **Generated tasks don't improve metrics**
   - Mitigation: Feedback loop, adjust generation weights based on outcomes
   
4. **Context analysis too slow**
   - Mitigation: Incremental analysis, caching, async processing

### Mitigations Implemented
- Safety governance from M2 (blocks dangerous tasks)
- Resource limits (CPU, memory, cost)
- Feedback loop (learn from failures)
- Graceful degradation (fallback to manual tasks)

---

## Dependencies

### Internal
- M2 safety governance (task validation)
- M2 pattern quality (active learning)
- Existing execution infrastructure (task execution)
- Existing metrics (feedback loop)

### External
- Git repository access
- Coverage reports (pytest-cov)
- LLM API (task generation)
- SurrealDB (pattern storage)

---

## Next Steps

1. **Week 7 Kickoff**: Implement context analysis engine
2. **Prototype**: Build minimal task generator for validation
3. **Feedback**: Review generated tasks with stakeholders
4. **Iterate**: Refine prompts and validation rules
5. **Deploy**: Enable self-improvement loop in production

---

## Conclusion

M3 will transform ATADO from a reactive system (human-driven tasks) to a proactive system (self-directed improvement). By analyzing its own context and generating improvement tasks, ATADO will achieve 75% autonomy and 2x improvement velocity.

**Critical Success Factor**: High-quality task generation with robust validation and safety guardrails.

**Next Milestone**: M4 (Production Readiness) - Scale to 1000+ tasks/hour with SLO enforcement.

