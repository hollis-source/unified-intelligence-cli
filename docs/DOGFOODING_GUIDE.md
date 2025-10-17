# Dogfooding Guide  Using Our Tools to Build The System

This guide shows how to use the project's own capabilities (Auggie MCP, Autonomous Orchestrator, Project Builder, DSL) to implement features faster and with higher quality. All examples are grounded in the current repository.

---

## Philosophy

Use our own tools to design, implement, test, and validate themselves. This:
- Reduces time-to-value with parallel strategy+tactics
- Surfaces real-world issues early (coverage bottlenecks, CI edges)
- Increases quality via multi-model review and rigorous validation

---

## Tooling Overview

- Auggie MCP (multi-model collaboration)
  - Pragmatic implementation: GPT-5
  - Rigorous review: Claude 4.5
- Autonomous Orchestrator (continuous loop)
  - `src/claude_orchestrator/orchestrators/autonomous_orchestrator.py`
  - CLI: `autonomous_dev_tool.py`
- Project Builder (HTN-based codegen)
  - `docs/AGENTIC_PROJECT_BUILDER_BLUEPRINT.md`
- Category Theory DSL (workflow composition)
  - `docs/DSL_USER_GUIDE.md`, `src/dsl/*`
- Team Routing / Multi-Agent Orchestration
  - See `README.md` and `tests/integration/test_multiagent_orchestration.py`

---

## Integration Patterns

1) Parallel Strategy + Tactics
- You design architecture and key decisions
- Auggie generates implementation/tests in parallel

2) Multi-tool Composition
- Use Project Builder to scaffold modules
- Use DSL to define workflows
- Use Auggie to implement and Claude 4.5 to review

3) Self-Improvement (Dogfooding)
- Run autonomous loops to improve the repository itself
- Log metrics and iterate based on success rate

4) Second Opinion / Validation
- Use GPT-5 for first pass, Claude 4.5 for rigorous code review

---

## Real Examples

### Example 1: Building the Autonomous Dev Tool

The CLI located at `autonomous_dev_tool.py` (426 lines) was assembled by dogfooding with Auggie. It composes existing orchestrator components and persists metrics.

Key constructs used (real code):
```python
from src.claude_orchestrator.use_cases.analyze_context_use_case import AnalyzeContextUseCase
from src.claude_orchestrator.use_cases.generate_next_task_use_case import GenerateNextTaskUseCase
from src.claude_orchestrator.adapters.single_worker_pool import SingleWorkerPool
from src.claude_orchestrator.entities.worker import WorkerPoolConfig
```
Run it:
```bash
python autonomous_dev_tool.py run --continuous --mode fast
python autonomous_dev_tool.py status
```

### Example 2: Multi-Model AI Code Review

The Auggie PR reviewer adapter uses both GPT-5 and Claude 4.5 and requires consensus for approval.

Adapter: `src/claude_orchestrator/adapters/auggie_pr_reviewer.py`
```python
review_gpt5 = self._review_with_model(instruction, "gpt5", "GPT-5")
review_claude = self._review_with_model(instruction, "claude", "Claude 4.5")
result = self._combine_reviews(pr, [review_gpt5, review_claude], start_time)
```
Use patterns (shell):
```bash
# Pragmatic implementation
python - <<'PY'
from mcp__auggie import auggie_with_gpt5
auggie_with_gpt5(instruction='Create REST API with users endpoint')
PY

# Rigorous code review
python - <<'PY'
from mcp__auggie import auggie_with_claude
auggie_with_claude(instruction='Review REST API implementation')
PY
```

### Example 3: Fixing Coverage Bottlenecks

Through dogfooding we validated that full coverage analysis can be slow at scale. The orchestrator and dev tool default to `run_coverage=False` for fast mode.

```python
# autonomous_dev_tool.py
mode_cfg = resolve_mode("fast")  # tests=False, coverage=False
success, meta, durs = runner.run_once(mode_cfg)
```

---

## When to Dogfood vs. When Not To

Use dogfooding for:
- Complex features and multi-step tasks
- Code generation, scaffolding, and test creation
- Validation (tests, coverage, PR review)

Avoid dogfooding for:
- Trivial tasks (<5 minutes)
- Tight debug loops needing instant feedback
- Pure exploration without clear outputs

---

## Success Metrics

Track improvements quantitatively:
- Development time reduction (expected vs. actual)
- Bugs discovered during real usage
- Quality improvements from multi-model review (scores, issues caught)
- Autonomous success rate across iterations

Metrics are persisted here:
- `~/.ui-cli/autonomous_metrics.json`
- Aggregates include `success_rate`, `avg_duration_by_mode`, `tasks_by_goal`, `tasks_by_priority`

---

## Quickstart Recipes

- Run 5 autonomous iterations locally:
```bash
python autonomous_dev_tool.py run --iterations 5 --mode fast
```

- Continuous improvement loop on remote SSH worker (defaults from code):
```bash
AUTONOMOUS_SSH_HOST=root@208.87.135.78 \
AUTONOMOUS_WORKING_DIR=/root \
AUTONOMOUS_MODEL=sonnet4 \
python autonomous_dev_tool.py run --continuous --mode thorough
```

- Status / Reset:
```bash
python autonomous_dev_tool.py status
python autonomous_dev_tool.py reset
```

---

## References
- Orchestrator loop: `src/claude_orchestrator/orchestrators/autonomous_orchestrator.py`
- Use cases: `src/claude_orchestrator/use_cases/*`
- Adapters: `src/claude_orchestrator/adapters/*`
- Entities/Interfaces: `src/claude_orchestrator/entities/*`, `src/claude_orchestrator/interfaces/*`
- Priorities: `priorities.yaml`
- DSL: `docs/DSL_USER_GUIDE.md`, `src/dsl/*`

