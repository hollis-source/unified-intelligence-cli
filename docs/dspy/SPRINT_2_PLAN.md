# Sprint 2: Optimization Pipeline

**Goal**: Implement DSPy's MIPROv2 optimizer to automatically improve prompts from metrics
**Duration**: 1 week
**Story Points**: 16

## Sprint Overview
Sprint 1 delivered "prompting with structure" using DSPy signatures. Sprint 2 adds the critical optimization layer that makes DSPy powerful: auto-improving prompts based on quality metrics.

## User Stories

### US-2.1: Create Metric Evaluator (5 story points)
**As a** developer
**I want** automated quality metrics for LLM outputs
**So that** DSPy can optimize prompts toward measurable goals

**Acceptance Criteria**:
- [ ] Create `QualityMetricEvaluator` class
- [ ] Implement syntax correctness metric (AST parsing)
- [ ] Implement completeness metric (no TODOs/placeholders)
- [ ] Implement conciseness metric (no thinking verbosity)
- [ ] Calculate weighted quality score (40% syntax, 40% complete, 20% concise)
- [ ] Return DSPy-compatible metric function (float 0.0-1.0)
- [ ] TDD: 8+ tests covering all metrics

**Files**:
- `src/adapters/prompt/quality_metrics.py`
- `tests/adapters/prompt/test_quality_metrics.py`

---

### US-2.2: Implement MIPROv2 Optimizer (8 story points)
**As a** developer
**I want** DSPy's MIPROv2 optimizer integrated
**So that** prompts automatically improve from training examples

**Acceptance Criteria**:
- [ ] Create `PromptOptimizer` class wrapping `dspy.MIPROv2`
- [ ] Accept training examples (task, expected output pairs)
- [ ] Accept metric function from `QualityMetricEvaluator`
- [ ] Run optimization with configurable trials (default: 20)
- [ ] Save optimized prompts to disk (for reproducibility)
- [ ] Load previously optimized prompts
- [ ] Support per-task-type optimization (implementation, design, testing, docs)
- [ ] TDD: 6+ tests covering optimization flow

**Files**:
- `src/adapters/prompt/optimizer.py`
- `tests/adapters/prompt/test_optimizer.py`
- `data/optimized_prompts/` (storage directory)

**MIPROv2 Configuration**:
```python
optimizer = dspy.MIPROv2(
    metric=quality_metric,
    num_candidates=20,  # Generate 20 prompt variations
    init_temperature=1.0
)
```

---

### US-2.3: Create Optimization Workflow (3 story points)
**As a** developer
**I want** a CLI script to run prompt optimization
**So that** I can easily optimize prompts on training data

**Acceptance Criteria**:
- [ ] Create `scripts/optimize_prompts.py` CLI tool
- [ ] Accept training data file (JSONL format)
- [ ] Accept task type (implementation, design, testing, docs)
- [ ] Run MIPROv2 optimization with progress display
- [ ] Save optimized prompts with metadata (date, score, trials)
- [ ] Display before/after quality comparison
- [ ] Support resume from checkpoint

**CLI Usage**:
```bash
./venv/bin/python scripts/optimize_prompts.py \
  --task-type implementation \
  --training-data data/training/implementation_examples.jsonl \
  --num-trials 20 \
  --output data/optimized_prompts/implementation.json
```

**Files**:
- `scripts/optimize_prompts.py`
- `data/training/implementation_examples.jsonl` (training examples)

---

### Sprint Demo: Multiply Function Optimization
**Goal**: Demonstrate prompt optimization improving quality score

**Steps**:
1. Create training examples from Sprint 1 baseline artifacts
2. Run optimization on implementation task type:
   ```bash
   ./venv/bin/python scripts/optimize_prompts.py \
     --task-type implementation \
     --training-data data/training/implementation_examples.jsonl \
     --num-trials 20
   ```
3. Compare quality scores:
   - Baseline (manual prompts): 68.9%
   - Sprint 1 (DSPy signatures): 100.0%
   - Sprint 2 (optimized): Target ≥100% (maintain or improve)
4. Document optimization improvements

**Success Criteria**: Optimized prompts maintain ≥100% quality score

---

## Technical Design

### Quality Metric Function
DSPy optimizers require a metric function with signature:
```python
def quality_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Return score 0.0-1.0 for prediction quality."""
    # Analyze prediction output
    # Return weighted score
```

### Training Example Format
```jsonl
{"task_description": "Write multiply function", "expected_output": "def multiply(a, b):\n    return a * b"}
{"task_description": "Write add function", "expected_output": "def add(a, b):\n    return a + b"}
```

### Optimization Flow
```
Training Examples → MIPROv2 Optimizer → Optimized Prompts
                         ↑
                   Quality Metric
```

### Storage Format
```json
{
  "task_type": "implementation",
  "optimized_at": "2025-10-07T05:00:00",
  "num_trials": 20,
  "baseline_score": 0.689,
  "optimized_score": 1.0,
  "improvement": 0.311,
  "prompts": {
    "system_prompt": "...",
    "task_prompt_template": "..."
  }
}
```

---

## Definition of Done
- [ ] All 3 user stories completed
- [ ] 14+ tests passing (8 + 6 + 0 for script)
- [ ] Demo shows optimization maintaining ≥100% quality
- [ ] Documentation updated
- [ ] Code reviewed (Clean Architecture principles)

---

## Dependencies
- DSPy 3.0.3 (already installed)
- Training data from Sprint 1 baseline
- Quality metrics from `scripts/measure_baseline.py`

---

## Risks & Mitigations
1. **Risk**: Optimization may not improve beyond 100% (already perfect)
   - **Mitigation**: Use more complex tasks, demonstrate stability

2. **Risk**: MIPROv2 requires many LLM calls (expensive)
   - **Mitigation**: Start with small num_trials (5-10), cache aggressively

3. **Risk**: Optimized prompts may overfit to training examples
   - **Mitigation**: Use diverse training set, validate on held-out data

---

## Velocity Estimate
- US-2.1: 5 points × 25 min/point = 2 hours
- US-2.2: 8 points × 25 min/point = 3.5 hours
- US-2.3: 3 points × 25 min/point = 1.5 hours
- **Total**: 16 points = ~7 hours work

---

**Sprint Start**: 2025-10-07
**Sprint End**: Target 2025-10-14 (or earlier with autonomous execution)
