# Agent Performance Measurement System

**Philosophy**: Continuous improvement. Each agent starts at 20% baseline, improves weekly to 80%+.

**Status**: ✅ Ready to measure TODAY

---

## Overview

This system measures performance for 5 specialist agents:

1. **Python Engineer** - Code quality, refactoring, SOLID principles
2. **Software Architect** - System design, Clean Architecture, ADRs
3. **Test Engineer** - Unit, integration, E2E test generation
4. **DevOps Engineer** - CI/CD, deployment, monitoring
5. **Research Analyst** - Documentation, investigation, planning

---

## Metrics Tracked

### 1. Task Completion Rate (%)
**Definition**: Percentage of tasks completed successfully without errors.

**Target**: 80%+

**Measurement**: 
- Success = ExecutionStatus.SUCCESS
- Failure = ExecutionStatus.FAILED or exception raised

**Baseline**: 20% (untrained agent)

---

### 2. Output Quality Score (1-10)
**Definition**: Subjective quality of agent output based on rubric.

**Target**: 8.0+/10

**Scoring Rubric**:

| Score | Rating | Description |
|-------|--------|-------------|
| 9-10 | Exceptional | Exceeds requirements, production-ready, comprehensive |
| 7-8 | Good | Meets requirements, minor improvements needed |
| 5-6 | Acceptable | Partial completion, significant gaps |
| 3-4 | Poor | Minimal effort, major issues |
| 1-2 | Failure | Incorrect or unusable |

**Scoring Criteria** (automated):

**Base Score**: 5.0

**Length**:
- < 100 chars: -2.0 (too short)
- > 500 chars: +1.0 (comprehensive)

**Structure**:
- Code blocks (```): +1.0
- Headers (#): +0.5
- Lists (- or *): +0.5

**Specificity**:
- File paths (src/): +1.0
- File extensions (.py): +0.5

**Agent-Specific**:

*Python Engineer*:
- Keywords (solid, dry, refactor, pattern): +1.0
- Code (class, def): +0.5

*Software Architect*:
- Keywords (architecture, design, layer, component): +1.0
- Artifacts (diagram, adr): +0.5

*Test Engineer*:
- Keywords (test, pytest, assert): +1.0
- Test code (@pytest, def test_): +1.0

*DevOps Engineer*:
- Keywords (docker, kubernetes, ci/cd, deploy): +1.0
- Config files (yaml, dockerfile): +0.5

*Research Analyst*:
- Keywords (research, compare, analysis, evidence): +1.0
- Citations (source:, reference:): +0.5

**Final Score**: min(10.0, max(1.0, calculated_score))

---

### 3. Latency P95 (seconds)
**Definition**: 95th percentile task execution time.

**Target**: < 30s for research, < 60s for implementation

**Measurement**: 
- Start: Before executor.execute()
- End: After result returned
- P95: 95th percentile of all task latencies

**Baseline**: Varies by task complexity

---

### 4. Cost per Task (USD)
**Definition**: Estimated cost based on token usage.

**Target**: < $0.10 per task (research), < $0.50 (implementation)

**Pricing** (approximate):
- GPT-4: $0.03/1K input, $0.06/1K output
- GPT-3.5: $0.001/1K input, $0.002/1K output
- Claude Sonnet: $0.003/1K input, $0.015/1K output

**Token Estimation**: 
- 1 token ≈ 4 characters
- Assume 50/50 input/output split

**Calculation**:
```python
input_tokens = (len(task_description) + len(output)) // 8
output_tokens = (len(task_description) + len(output)) // 8
cost = (input_tokens * input_price + output_tokens * output_price) / 1000
```

---

### 5. Specificity (%)
**Definition**: Percentage of output with concrete code references.

**Target**: 80%+

**Indicators**:
- File paths: `src/module/file.py`
- Line numbers: `line 42`, `:123`
- Function/class names: `MyClass.method()`
- Specific values: `threshold=0.9`

**Calculation**:
```python
matches = count_regex_matches(output, specificity_patterns)
words = len(output.split())
specificity = min(100.0, (matches / words) * 100 * 5)
```

**Patterns**:
- `src/[\w/]+\.py` - File paths
- `line \d+` - Line numbers
- `:\d+` - Line references
- `def \w+` - Function definitions
- `class \w+` - Class definitions
- `\w+\(\)` - Function calls
- `=\s*[\d.]+` - Numeric values
- `threshold|limit|max|min` - Specific parameters

---

## Test Tasks (20 per Agent)

### Python Engineer Tasks
Focus: Code quality, refactoring, SOLID principles

**Examples**:
1. Refactor src/adapters/agent/llm_executor.py to extract error handling into separate ErrorHandler class
2. Apply SOLID principles to src/routing/team_router.py - identify SRP violations
3. Add type hints to all functions in src/use_cases/task_coordinator.py
4. Extract magic numbers from src/priority_queue/priority_calculator.py into named constants
5. Refactor nested conditionals in src/adapters/llm/hybrid_executor.py using guard clauses

*(See test_agent_performance.py for all 20 tasks)*

---

### Software Architect Tasks
Focus: System design, Clean Architecture, ADRs

**Examples**:
1. Design Clean Architecture layers for new RAG module (entities, use cases, adapters)
2. Create architecture decision record (ADR) for choosing Redis over in-memory queue
3. Design hexagonal architecture ports for external LLM providers
4. Propose dependency injection strategy for src/composition.py
5. Design event-driven architecture for agent communication

*(See test_agent_performance.py for all 20 tasks)*

---

### Test Engineer Tasks
Focus: Unit, integration, E2E test generation

**Examples**:
1. Generate unit tests for src/entity/metrics.py MetricsCollector class
2. Create integration tests for src/routing/team_router.py with mock agents
3. Write E2E test for complete task execution flow from CLI to result
4. Generate pytest fixtures for common test data in tests/conftest.py
5. Create property-based tests for src/dsl/adapters/htn_compiler.py using Hypothesis

*(See test_agent_performance.py for all 20 tasks)*

---

### DevOps Engineer Tasks
Focus: CI/CD, deployment, monitoring

**Examples**:
1. Design Docker Compose setup for local development with Redis and SurrealDB
2. Create Kubernetes deployment manifests for production (k8s/ directory)
3. Set up Prometheus metrics collection for agent performance monitoring
4. Design CI/CD pipeline using GitHub Actions with automated testing
5. Create health check endpoints for all services

*(See test_agent_performance.py for all 20 tasks)*

---

### Research Analyst Tasks
Focus: Documentation, investigation, planning

**Examples**:
1. Research best practices for Clean Architecture in Python projects
2. Investigate optimal LoRA rank values for 7B parameter models with evidence
3. Compare LangGraph vs custom HTN orchestration for multi-agent systems
4. Research GPU pricing for inference workloads (A100, H100, L40S)
5. Investigate category theory applications in workflow composition

*(See test_agent_performance.py for all 20 tasks)*

---

## Usage

### 1. Run Baseline Measurement

```bash
# Test all agents and save as baseline
python test_agent_performance.py --agent all --save-baseline

# Test single agent
python test_agent_performance.py --agent python-engineer
```

**Output**:
```
================================================================================
Testing Agent: PYTHON-ENGINEER
================================================================================

  [python-engineer-01] Refactor src/adapters/agent/llm_executor.py to extract...
    ✓ Quality: 7.5/10, Specificity: 65%, Time: 12.3s
  [python-engineer-02] Apply SOLID principles to src/routing/team_router.py...
    ✓ Quality: 8.0/10, Specificity: 72%, Time: 15.1s
  ...

────────────────────────────────────────────────────────────────────────────────
SUMMARY: python-engineer
────────────────────────────────────────────────────────────────────────────────
Completion Rate:    85.0%
Avg Quality Score:  7.2/10
Avg Specificity:    68.5%
Latency P50:        14.23s
Latency P95:        28.45s
Total Cost:         $0.8234
Cost per Task:      $0.0412
────────────────────────────────────────────────────────────────────────────────

✅ Results saved to data/agent_performance/baseline.json
```

---

### 2. View Dashboard

```bash
# View all agents
python agent_metrics_dashboard.py

# View specific agent
python agent_metrics_dashboard.py --agent python-engineer

# Export to HTML
python agent_metrics_dashboard.py --export report.html
```

**Output**:
```
====================================================================================================
AGENT PERFORMANCE DASHBOARD
====================================================================================================

📊 CURRENT STATE
────────────────────────────────────────────────────────────────────────────────────────────────────

PYTHON-ENGINEER
  Completion Rate:    85.0%  ✅
  Quality Score:       7.2/10 ⚠️
  Specificity:        68.5%  ⚠️
  Latency P95:        28.45s
  Cost per Task:      $0.0412

...

📈 IMPROVEMENT TRAJECTORY (Week-over-Week)
────────────────────────────────────────────────────────────────────────────────────────────────────

PYTHON-ENGINEER (1.2 weeks)
  Completion Rate:  ✅ +15.0% ↑
  Quality Score:    ✅ +1.8 ↑
  Specificity:      ✅ +22.5% ↑
  Latency P95:      ✅ -5.2s ↓
  Cost per Task:    ✅ -0.0123 ↓

...

🎯 NEXT OPTIMIZATION TARGETS (Highest Impact/Lowest Effort)
────────────────────────────────────────────────────────────────────────────────────────────────────

1. TEST-ENGINEER
   Impact/Effort Ratio: 2.45
   Recommendation: Improve task completion rate (+25% needed) | Enhance output quality (+2.3 points needed)

2. RESEARCH-ANALYST
   Impact/Effort Ratio: 2.12
   Recommendation: Add more code references (+35% needed)

...
```

---

### 3. Compare Results

```bash
# Compare baseline vs current
python test_agent_performance.py --compare data/agent_performance/baseline.json data/agent_performance/results_20251016_143022.json
```

**Output**:
```
================================================================================
PERFORMANCE COMPARISON
================================================================================
Baseline: data/agent_performance/baseline.json
Current:  data/agent_performance/results_20251016_143022.json

PYTHON-ENGINEER
────────────────────────────────────────────────────────────────────────────────
  Completion Rate:  85.0% (+15.0% ↑)
  Quality Score:    7.2/10 (+1.8 ↑)
  Specificity:      68.5% (+22.5% ↑)
  Latency P95:      28.45s (-5.2s ↓)
```

---

## Continuous Improvement Process

### Week 1: Baseline
1. Run `python test_agent_performance.py --agent all --save-baseline`
2. Review dashboard: `python agent_metrics_dashboard.py`
3. Identify lowest-performing agent
4. Document baseline metrics

**Expected**: 20-40% completion, 4-6/10 quality

---

### Week 2-4: Optimization
1. Focus on top optimization target (highest impact/effort ratio)
2. Implement improvements:
   - Better prompts
   - Few-shot examples
   - Tool integration
   - Error handling
3. Re-run tests weekly
4. Track improvement trajectory

**Target**: 60-70% completion, 6-7/10 quality

---

### Week 5+: Refinement
1. Address remaining gaps
2. Optimize for specificity (code references)
3. Reduce latency (caching, batching)
4. Minimize cost (model selection)

**Target**: 80%+ completion, 8+/10 quality

---

## Regression Testing

**Critical**: Don't break what works!

### Process
1. Save baseline: `--save-baseline`
2. Make changes (prompts, code, config)
3. Re-run tests: `python test_agent_performance.py --agent all`
4. Compare: `--compare baseline.json current.json`
5. **Verify no regressions** (completion rate, quality)

### Acceptance Criteria
- Completion rate: No decrease > 5%
- Quality score: No decrease > 0.5 points
- Latency P95: No increase > 20%

---

## Human Evaluation Protocol

**When**: Quality score < 7.0 or specificity < 60%

### Process
1. Sample 10% of tasks (2 per agent)
2. Manual review by domain expert
3. Score 1-10 based on:
   - Correctness
   - Completeness
   - Actionability
   - Code quality (if applicable)
4. Compare human score vs automated score
5. Adjust scoring rubric if needed

### Calibration
- Run human eval every 2 weeks
- Target: Human score within ±1.0 of automated score
- Adjust weights if systematic bias detected

---

## Next Steps

1. **TODAY**: Run baseline measurement
   ```bash
   python test_agent_performance.py --agent all --save-baseline
   ```

2. **Review**: Check dashboard
   ```bash
   python agent_metrics_dashboard.py
   ```

3. **Optimize**: Focus on top target from dashboard

4. **Iterate**: Re-run weekly, track improvement

5. **Celebrate**: When agents hit 80%+ targets! 🎉

---

## Files

- `test_agent_performance.py` - Test harness (20 tasks × 5 agents)
- `agent_metrics_dashboard.py` - Metrics visualization
- `AGENT_METRICS.md` - This documentation
- `data/agent_performance/` - Results storage

---

## FAQ

**Q: Why 20 tasks per agent?**
A: Statistically significant (p95 reliable), but fast enough to run daily (~10 min total).

**Q: Can I add custom tasks?**
A: Yes! Edit task lists in `test_agent_performance.py`.

**Q: How do I change scoring rubric?**
A: Modify `score_quality()` function. Re-run baseline after changes.

**Q: What if completion rate is < 50%?**
A: Check error logs, improve prompts, add examples, verify LLM provider.

**Q: How do I track multiple models?**
A: Run tests with different `--provider` flags, save separate baselines.

---

**Status**: ✅ Ready to use
**Last Updated**: 2025-10-16
**Maintainer**: unified-intelligence-cli team

