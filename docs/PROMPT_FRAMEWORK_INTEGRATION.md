# Agentic Prompt Strategy Framework Integration

**Status:** Phase 1 Complete (Core Integration)  
**Date:** 2025-10-19  
**Integration Version:** 1.0

---

## Overview

This document describes the integration of the `agentic-prompt-strategy-framework` into ATADO for systematic prompt quality validation and improvement.

---

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Layer                       │
│  - IPromptValidator (contract)                          │
│  - ValidationResult, ValidationChecks (DTOs)            │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ depends on
                           │
┌─────────────────────────────────────────────────────────┐
│                     Entity Layer                         │
│  - PromptStrategy (domain model)                        │
│  - to_system_prompt(), to_markdown(), etc.              │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ implements
                           │
┌─────────────────────────────────────────────────────────┐
│                    Adapter Layer                         │
│  - PromptStrategyValidator (framework wrapper)          │
│  - Integrates with agentic-prompt-strategy-framework    │
└─────────────────────────────────────────────────────────┘
```

---

## Framework Path Configuration

### Directory Structure

```
/home/ui-cli_jake/
├── agentic-prompt-strategy-framework/    # Framework (sibling)
│   ├── scripts/
│   │   └── validate_prompt.py           # Validation logic
│   ├── prompts/
│   │   └── templates/                   # Domain templates
│   └── src/
│       ├── entities/
│       ├── use_cases/
│       └── adapters/
│
└── unified-intelligence-cli/             # ATADO (this project)
    └── src/
        ├── entity/
        │   └── prompt_strategy.py       # NEW: PromptStrategy entity
        ├── interface/
        │   └── prompt_validator.py      # NEW: IPromptValidator interface
        └── adapters/
            └── prompt/
                ├── __init__.py
                └── strategy_validator.py # NEW: Validator adapter
```

### Python Path Resolution

The `PromptStrategyValidator` adapter automatically adds the framework to `sys.path`:

```python
# In src/adapters/prompt/strategy_validator.py
framework_path = Path(__file__).parent.parent.parent.parent.parent / "agentic-prompt-strategy-framework"
sys.path.insert(0, str(framework_path))
```

**Resolved Path:** `/home/ui-cli_jake/agentic-prompt-strategy-framework`

### Fallback Mode

If the framework is not available, the validator operates in **fallback mode**:
- Uses simple heuristics for validation
- Logs warning message
- Returns basic ValidationResult
- No errors or crashes

---

## Components

### 1. PromptStrategy Entity

**File:** `src/entity/prompt_strategy.py`

**Purpose:** Core domain model for structured prompts

**Key Methods:**
- `to_system_prompt()` - Convert to LLM system prompt
- `to_user_prompt()` - Convert to LLM user prompt
- `to_markdown()` - Convert to markdown for validation
- `update_validation()` - Update validation results
- `to_dict()` / `from_dict()` - Serialization

**Frameworks Supported:**
- 4-Sentence Framework (Persona, Goal, Task, Context)
- ROLE Model (Role, Objective, Logistics, Expectations)

---

### 2. IPromptValidator Interface

**File:** `src/interface/prompt_validator.py`

**Purpose:** Contract for prompt validation (DIP)

**Key Types:**
- `ValidationChecks` - Detailed check results
- `ValidationResult` - Overall validation result
- `IPromptValidator` - Validator interface
- `IPromptEnhancer` - Optional enhancer interface

**Validation Criteria:**
- Framework compliance (4-Sentence OR ROLE)
- Specificity ≥50% (file paths, code, numbers)
- Clarity ≥70% (no ambiguous words)
- Completeness (≥50 words, headers, structure)

---

### 3. PromptStrategyValidator Adapter

**File:** `src/adapters/prompt/strategy_validator.py`

**Purpose:** Wrap framework validation logic

**Features:**
- Automatic framework path resolution
- Fallback mode if framework unavailable
- Configurable minimum score threshold
- Detailed suggestions for improvement

**Usage:**
```python
from src.adapters.prompt import PromptStrategyValidator
from src.entity.prompt_strategy import PromptStrategy

# Create validator
validator = PromptStrategyValidator(min_score=60.0)

# Create strategy
strategy = PromptStrategy(
    persona="Senior Python Developer",
    goal="Refactor code to improve maintainability",
    task="Extract duplicate logic into reusable functions",
    context="Legacy codebase with 30% code duplication"
)

# Validate
result = validator.validate_strategy(strategy)

print(f"Score: {result.score}")
print(f"Passed: {result.passed}")
print(f"Suggestions: {result.suggestions}")
```

---

## Integration Points

### Current (Phase 1)

✅ **Entity Layer**
- `PromptStrategy` entity created
- Serialization methods implemented

✅ **Interface Layer**
- `IPromptValidator` interface defined
- `ValidationResult` and `ValidationChecks` DTOs created

✅ **Adapter Layer**
- `PromptStrategyValidator` adapter implemented
- Framework integration with fallback mode

### Upcoming (Phase 2-6)

⏳ **Phase 2:** LLMAgentExecutor Enhancement
- Integrate validator into prompt generation
- Optional validation before LLM calls
- Metrics collection

⏳ **Phase 3:** Template Library Integration
- Load domain-specific templates
- Merge templates with task-specific info

⏳ **Phase 4:** SurrealDB Metrics Integration
- Store prompt quality metrics
- Track improvement over time

⏳ **Phase 5:** CLI Integration
- Add `--validate-prompts` flag
- Add `--use-prompt-templates` flag
- Add `--collect-prompt-metrics` flag

⏳ **Phase 6:** Testing & Documentation
- Comprehensive test suite
- Performance benchmarking
- User documentation

---

## Testing

### Unit Tests (Phase 1)

**Files:**
- `tests/unit/test_prompt_strategy.py`
- `tests/unit/test_prompt_validator.py`
- `tests/unit/test_strategy_validator.py`

**Coverage:**
- PromptStrategy creation and methods
- Validation interface contracts
- Validator adapter with/without framework

### Integration Tests (Future)

**Files:**
- `tests/integration/test_llm_executor_with_validation.py`
- `tests/integration/test_prompt_template_integration.py`

---

## Configuration

### Environment Variables

None required for Phase 1. Future phases may add:

```bash
# Optional: Override framework path
export ATADO_PROMPT_FRAMEWORK_PATH="/custom/path/to/framework"

# Optional: Disable validation (performance)
export ATADO_VALIDATE_PROMPTS=false

# Optional: Set minimum score threshold
export ATADO_PROMPT_MIN_SCORE=70.0
```

### CLI Flags (Phase 5)

```bash
# Enable prompt validation
python -m src.main --task "..." --validate-prompts

# Use domain templates
python -m src.main --task "..." --use-prompt-templates

# Collect metrics
python -m src.main --task "..." --collect-prompt-metrics

# Set minimum score
python -m src.main --task "..." --validate-prompts --prompt-min-score 70.0
```

---

## Backward Compatibility

### Guarantees

✅ **No Breaking Changes**
- All new features are opt-in
- Existing code works without modifications
- Default behavior unchanged

✅ **Graceful Degradation**
- Framework unavailable → fallback mode
- Validation disabled → no overhead
- Templates missing → dynamic generation

✅ **Optional Dependencies**
- Framework is optional (fallback mode available)
- No new external packages required

---

## Performance Considerations

### Validation Overhead

**Without Validation (Default):**
- No overhead
- Existing performance maintained

**With Validation (Opt-In):**
- ~10-50ms per prompt validation
- Negligible compared to LLM latency (1-10s)
- Can be disabled for production if needed

### Optimization Strategies

1. **Cache validation results** for identical prompts
2. **Async validation** (validate while LLM processes)
3. **Batch validation** for multiple prompts
4. **Sampling** (validate 10% of prompts in production)

---

## Troubleshooting

### Framework Not Found

**Symptom:** Warning message about fallback mode

**Solution:**
```bash
# Verify framework exists
ls -la /home/ui-cli_jake/agentic-prompt-strategy-framework

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Test import
cd unified-intelligence-cli
python -c "from src.adapters.prompt import PromptStrategyValidator; print('OK')"
```

### Import Errors

**Symptom:** `ImportError` or `ModuleNotFoundError`

**Solution:**
```bash
# Ensure framework dependencies installed
cd /home/ui-cli_jake/agentic-prompt-strategy-framework
pip install -r requirements.txt  # if exists

# Or install in unified-intelligence-cli venv
cd /home/ui-cli_jake/unified-intelligence-cli
source venv/bin/activate
pip install -e ../agentic-prompt-strategy-framework  # if setup.py exists
```

### Low Validation Scores

**Symptom:** Prompts consistently score <60

**Solution:**
1. Review suggestions in `ValidationResult.suggestions`
2. Add file paths, code examples, numeric constraints
3. Remove ambiguous words (maybe, perhaps, etc.)
4. Ensure framework sections present (Persona, Goal, Task, Context)
5. Use templates from `agentic-prompt-strategy-framework/prompts/templates/`

---

## References

### Documentation

- [ATADO Integration Strategy](./ATADO_INTEGRATION_STRATEGY.md)
- [ATADO Philosophy](./ATADO_PHILOSOPHY_AND_PRINCIPLES.md)
- [Framework README](../../agentic-prompt-strategy-framework/README.md)
- [Framework CLAUDE.md](../../agentic-prompt-strategy-framework/CLAUDE.md)

### Code

- Entity: `src/entity/prompt_strategy.py`
- Interface: `src/interface/prompt_validator.py`
- Adapter: `src/adapters/prompt/strategy_validator.py`
- Tests: `tests/unit/test_prompt_*.py`

---

**Last Updated:** 2025-10-19  
**Next Review:** Phase 2 completion (Week 2-3)

