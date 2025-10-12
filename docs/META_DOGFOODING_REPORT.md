# Meta-Dogfooding Report: External AI Agent Testing Project Builder

**Date:** 2025-10-11
**Test Conducted By:** Auggie (GPT-5) - External AI Agent
**Test Type:** Real-world usability validation of Project Builder by external AI agent
**Status:** ❌ **CRITICAL BUGS DISCOVERED - PROJECT BUILDER UNUSABLE**

---

## Executive Summary

**Mission**: Test whether external AI agents (like Auggie) can successfully use Project Builder to generate code from high-level goals.

**Goal Given to Auggie**: "Use Project Builder to generate automated CI/CD pipeline with git hooks and GitHub Actions"

**Result**: **COMPLETE FAILURE** - Project Builder failed to generate any artifacts across all three provider attempts (mock, tongyi-local, auto).

**Value Delivered**: Discovered CRITICAL bugs that prevent Project Builder from being usable by external AI agents. This is exactly the kind of validation that dogfooding provides.

**Impact**:
- ✅ **Positive**: Discovered real bugs before external users encountered them
- ❌ **Negative**: Project Builder cannot be used for its intended purpose in current state
- 🎯 **Action Required**: Fix bugs before any external deployment or demos

---

## Test Methodology

### Why This Test Matters

**Meta-Dogfooding Definition**: Using AI agents to test if other AI agents can use our product.

**Why We Did This**:
1. **Real-world validation**: Tests whether Project Builder's interface is usable by autonomous agents
2. **Bug discovery**: Finds issues that unit tests miss (integration, UX, documentation)
3. **Product validation**: Proves (or disproves) that the product works as intended
4. **Dogfooding**: Uses our own tools to improve themselves

### Test Setup

**External Agent**: Auggie (GPT-5) via MCP
**Execution Environment**: Docker container `project-builder`
**Command Used**: `docker exec -it project-builder python -m src.project_builder.cli.command`
**Task Specification**: Provided via `.auggie_task_meta_dogfooding.txt` to avoid shell quoting issues

**Task Requirements**:
- Use Project Builder CLI (not generate code directly)
- Document ALL issues encountered (errors, performance, UX problems)
- Try multiple providers if first fails
- Extract generated artifacts if successful

---

## Test Results: Three Provider Attempts

### Attempt 1: Mock Provider (Offline Testing)

**Command**:
```bash
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Automated CI/CD pipeline with git hooks and GitHub Actions workflows" \
  --project-id ci-cd-pipeline \
  --model mock \
  --parallel \
  --verbose
```

**Result**: ❌ **FAILED** - No artifacts generated

**Error**:
```
[GOAL_DECOMPOSER] Could not extract JSON from response:
Execute tasks in order: 1, 2, 3
```

**Root Cause**:
- `MockLLMProvider` returns plain text: `"Execute tasks in order: 1, 2, 3"`
- `GoalDecomposer` requires structured JSON response with tasks/subtasks
- No JSON mode or structured output in mock provider

**Severity**: **HIGH** - Blocks offline/local testing

**Code Location**: `src/adapters/llm/mock_provider.py`

**Impact**: Cannot dogfood Project Builder offline without external LLM credentials

---

### Attempt 2: tongyi-local Provider (Local LLM)

**Command**:
```bash
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Automated CI/CD pipeline with git hooks and GitHub Actions workflows" \
  --project-id ci-cd-pipeline-tongyi-local \
  --model tongyi-local \
  --parallel \
  --verbose
```

**Result**: ❌ **CRITICAL FAILURE** - Signature mismatch

**Error**:
```
TypeError: LocalTongyiAdapter.generate() missing 1 required positional argument: 'prompt'
```

**Root Cause**:
- `LocalTongyiAdapter.generate()` method signature doesn't match `ITextGenerator` interface
- Interface expects `generate(prompt: str, **kwargs)`
- Implementation is missing or has different parameters

**Severity**: **CRITICAL** - Complete adapter failure

**Code Location**: `src/adapters/llm/tongyi_local.py` (implied)

**Impact**: Local LLM path completely broken, cannot use Project Builder with local models

---

### Attempt 3: auto Provider (External LLM)

**Command**:
```bash
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Automated CI/CD pipeline with git hooks and GitHub Actions workflows" \
  --project-id ci-cd-pipeline-auto \
  --model auto \
  --parallel \
  --verbose
```

**Result**: ❌ **FAILED** - Requires external credentials

**Error**:
```
HF_TOKEN not found. Set HF_TOKEN environment variable or use huggingface-cli login
```

**Root Cause**:
- Auto provider requires Hugging Face credentials
- No fallback to other providers
- Network dependency for external API calls

**Severity**: **HIGH** - Cannot use in secure/offline environments

**Impact**: Requires external credentials and network access, unsuitable for dogfooding in production environment

---

## Bugs Discovered

### Bug #1: MockLLMProvider Returns Non-JSON Text (HIGH)

**Category**: Provider Implementation
**Severity**: HIGH
**When**: Using --model mock
**Impact**: Cannot test Project Builder offline without external LLM access

**Details**:
- MockLLMProvider returns plain text strings
- GoalDecomposer expects JSON with structure: `{"tasks": [{"id": ..., "description": ...}]}`
- No structured output mode in mock provider

**Example**:
```python
# Current behavior (mock_provider.py)
if "plan" in last_msg.lower():
    return "Execute tasks in order: 1, 2, 3"  # Plain text!

# Expected behavior
if "plan" in last_msg.lower():
    return json.dumps({
        "tasks": [
            {"id": "task1", "description": "Setup git hooks", "subtasks": [...]},
            {"id": "task2", "description": "Create GitHub Actions", "subtasks": [...]}
        ]
    })
```

**Recommended Fix**:
1. Add JSON mode to MockLLMProvider
2. Provide pre-built responses for common goal types (CI/CD, REST API, etc.)
3. Parse goal description keywords to return appropriate mock structure

**Code Location**: `src/adapters/llm/mock_provider.py`

---

### Bug #2: LocalTongyiAdapter Signature Mismatch (CRITICAL)

**Category**: Adapter Implementation
**Severity**: CRITICAL
**When**: Using --model tongyi-local
**Impact**: Local LLM path completely broken

**Details**:
- `LocalTongyiAdapter.generate()` doesn't match `ITextGenerator` interface
- Missing required `prompt` parameter
- Complete adapter failure prevents any local LLM usage

**Error Message**:
```
TypeError: LocalTongyiAdapter.generate() missing 1 required positional argument: 'prompt'
```

**Recommended Fix**:
1. Update `LocalTongyiAdapter.generate()` signature to match `ITextGenerator`:
   ```python
   def generate(self, prompt: str, **kwargs) -> str:
       """Generate response from local Tongyi model."""
       # Implementation
   ```
2. Ensure all adapter implementations conform to interface contract
3. Add interface conformance tests to prevent regression

**Code Location**: `src/adapters/llm/tongyi_local.py` (inferred)

---

### Bug #3: Auto Provider Requires External Credentials (HIGH)

**Category**: Configuration / Orchestrator
**Severity**: HIGH
**When**: Using --model auto without HF_TOKEN
**Impact**: Cannot use in secure/offline environments

**Details**:
- Auto orchestrator attempts to use Hugging Face models
- Requires HF_TOKEN environment variable
- No fallback to local/mock providers
- Network dependency blocks dogfooding in production

**Error Message**:
```
HF_TOKEN not found. Set HF_TOKEN environment variable or use huggingface-cli login
```

**Recommended Fix**:
1. Implement provider fallback chain: external → local → mock
2. Add --offline flag to force local/mock providers
3. Better error messages guiding users to alternatives
4. Document credential requirements clearly

**Code Location**: Auto orchestrator provider selection logic

---

### Issue #4: Redis Cache Unavailable (LOW)

**Category**: Infrastructure
**Severity**: LOW
**When**: Project Builder container cannot reach Redis
**Impact**: Performance degradation (no caching), but not blocking

**Details**:
- Health check shows: `[Errno 111] Connection refused` for Redis
- Project Builder continues without caching
- Graceful degradation works correctly

**Warning**:
```
Health check failed: [Errno 111] Connection refused
```

**Recommended Fix**:
1. Ensure Redis is accessible from project-builder container network
2. Verify REDIS_HOST environment variable points to correct service
3. Consider this acceptable if caching is optional

**Code Location**: `src/observability/health_server.py:171` (recently fixed to use environment variables)

---

### Issue #5: Docker Exec Usage Not Documented (MEDIUM)

**Category**: Documentation
**Severity**: MEDIUM
**When**: External agents trying to use Project Builder in Docker
**Impact**: Confusion, trial-and-error required

**Details**:
- README doesn't document `docker exec` usage pattern
- No examples of running CLI inside container
- Auggie figured it out through Docker inspection, but shouldn't be necessary

**Recommended Fix**:
Add to README:
```markdown
## Using Project Builder in Docker

### Run CLI inside container
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Your goal here" \
  --project-id my-project \
  --model mock \
  --verbose

### Extract generated artifacts
docker cp project-builder:/app/projects/my-project ./local-projects/
```

---

### Issue #6: No Offline Deterministic Path for Common Tasks (HIGH)

**Category**: Design
**Severity**: HIGH
**When**: Trying to use Project Builder for common infra tasks
**Impact**: Requires LLM even for standard, repeatable patterns

**Details**:
- Tasks like "CI/CD pipeline" are common and well-defined
- Should have deterministic templates/recipes
- Shouldn't require LLM inference for standard patterns
- Wastes compute and adds failure points

**Recommended Fix**:
Implement "starter pack" system:
```bash
# List available recipes
docker exec project-builder python -m src.project_builder.cli.command --list-recipes

# Use recipe directly (no LLM needed)
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id my-ci-cd

# Recipes include:
# - ci-cd-standard: GitHub Actions + pre-commit hooks
# - rest-api-python: FastAPI REST API with CRUD
# - docker-compose-stack: Multi-service Docker setup
# - monitoring-grafana: Prometheus + Grafana monitoring
```

**Benefits**:
- Fast (no LLM inference)
- Deterministic (same output every time)
- Offline-capable
- Perfect for dogfooding common patterns

---

## Impact Analysis

### On Project Builder Product

| Aspect | Status | Impact |
|--------|--------|--------|
| **Usability by AI Agents** | ❌ BLOCKED | External agents cannot use PB successfully |
| **Offline Testing** | ❌ BLOCKED | Mock provider doesn't work |
| **Local LLM Path** | ❌ BROKEN | Critical adapter bug |
| **External LLM Path** | ⚠️ LIMITED | Requires credentials + network |
| **CLI Interface** | ✅ GOOD | Clear, discoverable, well-designed |
| **Documentation** | ⚠️ INCOMPLETE | Missing Docker usage patterns |
| **Dogfooding Capability** | ❌ BLOCKED | Cannot use PB to improve itself |

### On CI/CD Automation Goal

**Original Goal**: "Use Auggie to research, plan, and implement automated CI/CD through git"

**Status**: **BLOCKED** - Cannot proceed until Project Builder bugs are fixed

**Alternative Path**:
1. Fix PB bugs first (estimated 4-8 hours)
2. Re-run meta-dogfooding test
3. If successful, extract CI/CD artifacts
4. If still failing, generate CI/CD directly (not via PB)

---

## Value Delivered by Meta-Dogfooding

### What We Learned

✅ **CRITICAL bugs discovered before external deployment**
✅ **Real-world validation that PB doesn't work for external agents yet**
✅ **Clear action items with severity ratings**
✅ **Proof that dogfooding methodology works**
✅ **CLI interface validated as good (only thing that worked)**
✅ **Documentation gaps identified**
✅ **Design issues surfaced (no deterministic recipes)**

### What Would Have Happened Without This Test

❌ External users would hit same bugs
❌ Frustration and loss of trust
❌ Wasted time debugging in production
❌ No systematic bug tracking
❌ Product demos would fail
❌ False confidence in PB readiness

### Dogfooding ROI

**Time Invested**: ~2 hours (Auggie's test + documentation)
**Bugs Found**: 6 issues (3 CRITICAL/HIGH, 3 MEDIUM/LOW)
**Value**: Prevented product launch with broken core functionality
**ROI**: **EXTREMELY HIGH** - Would have caused significant damage if discovered by users

---

## Recommendations

### Immediate (Critical Path - Before Any Use)

1. **Fix Bug #2: LocalTongyiAdapter Signature** (CRITICAL)
   - Estimated time: 2 hours
   - Unblocks local LLM path
   - Priority: P0

2. **Fix Bug #1: MockLLMProvider JSON Mode** (HIGH)
   - Estimated time: 3 hours
   - Unblocks offline testing
   - Priority: P0

3. **Add Common Task Recipes** (HIGH)
   - Estimated time: 4-6 hours
   - Provides deterministic path for CI/CD and other common patterns
   - Priority: P1

### Short-term (Before External Demo)

4. **Improve Documentation** (MEDIUM)
   - Add Docker exec usage examples
   - Document all provider options and requirements
   - Estimated time: 1 hour
   - Priority: P1

5. **Implement Provider Fallback Chain** (HIGH)
   - Auto → local → mock fallback
   - Add --offline flag
   - Estimated time: 2 hours
   - Priority: P1

### Long-term (Quality Improvements)

6. **Add Interface Conformance Tests** (MEDIUM)
   - Prevent adapter signature mismatches
   - Automated testing for all providers
   - Estimated time: 3 hours
   - Priority: P2

7. **Improve Redis Connectivity** (LOW)
   - Document network configuration
   - Add retry logic to Redis connections
   - Estimated time: 1 hour
   - Priority: P3

---

## Re-test Plan

### After Critical Bugs Fixed

**Objective**: Validate that external AI agents can successfully use Project Builder

**Test Steps**:
1. Fix Bug #1 (MockLLMProvider JSON mode)
2. Fix Bug #2 (LocalTongyiAdapter signature)
3. Re-run Auggie test with --model mock
4. Verify artifacts generated successfully
5. Extract and integrate CI/CD workflows
6. Document success

**Success Criteria**:
- ✅ Mock provider generates valid JSON
- ✅ GoalDecomposer parses response successfully
- ✅ HTN planning completes without errors
- ✅ Artifacts generated in `/app/projects/ci-cd-pipeline/`
- ✅ Generated files are valid and usable
- ✅ Auggie can complete task without manual intervention

### After Recipe System Implemented

**Objective**: Validate deterministic CI/CD generation

**Test Steps**:
1. Implement CI/CD recipe
2. Test: `docker exec project-builder python -m src.project_builder.cli.command --recipe ci-cd-standard --project-id test-ci-cd`
3. Verify output includes:
   - `.github/workflows/ci.yml`
   - `.github/workflows/cd.yml`
   - `.git/hooks/pre-commit`
   - `.git/hooks/post-commit`
   - Documentation

**Success Criteria**:
- ✅ Completes in <5 seconds (no LLM inference)
- ✅ Deterministic output (same every time)
- ✅ All files generated correctly
- ✅ Works offline (no network required)
- ✅ Auggie can use recipe successfully

---

## Conclusion

**Status**: Meta-dogfooding test **SUCCEEDED** in its primary objective: validating whether Project Builder works for external AI agents.

**Answer**: **NO** - Project Builder does NOT currently work for external AI agents due to CRITICAL bugs.

**Value**: This test was **INVALUABLE** - discovered showstopper bugs before external deployment.

**Next Steps**:
1. Fix CRITICAL bugs (#1, #2)
2. Implement recipe system for common tasks (#6)
3. Re-run meta-dogfooding test
4. If successful, extract and integrate CI/CD artifacts
5. Document success and lessons learned

**Lesson Learned**: Dogfooding reveals bugs that unit tests miss. External agent testing is essential for validating autonomous system usability.

---

## Appendix: Auggie's Full Test Execution

### Auggie's Approach

1. **Research Phase**: Examined Project Builder CLI via `docker exec project-builder python -m src.project_builder.cli.command --help`
2. **First Attempt**: Used --model mock for offline testing
3. **Issue Tracking**: Documented JSON parsing error
4. **Second Attempt**: Tried --model tongyi-local
5. **Issue Tracking**: Documented signature mismatch
6. **Third Attempt**: Tried --model auto
7. **Issue Tracking**: Documented credential requirements
8. **Analysis**: Concluded that all paths failed, compiled comprehensive bug report
9. **Recommendations**: Provided prioritized fix list

### Auggie's Observations

> "The Project Builder CLI interface is clear and well-designed. The --help output was comprehensive, and I could easily understand how to invoke it. However, all three provider attempts failed with different errors."

> "The mock provider should be the easiest path for dogfooding, but it returns plain text instead of JSON. This is a critical gap for offline testing."

> "The tongyi-local adapter has a fundamental signature mismatch - this suggests it may have never been tested or the interface changed without updating implementations."

> "For common infrastructure tasks like CI/CD, Project Builder should provide deterministic recipes that don't require LLM inference. This would make dogfooding much more reliable."

### Empty Project Directories Created

```
/app/projects/ci-cd-pipeline/               # Mock provider attempt
/app/projects/ci-cd-pipeline-tongyi-local/  # tongyi-local attempt
/app/projects/ci-cd-pipeline-auto/          # auto provider attempt
```

All directories empty - no artifacts generated in any attempt.

---

**Report Generated**: 2025-10-11
**Test Conducted By**: Auggie (GPT-5 via Auggie MCP)
**Report Author**: Claude (Sonnet 4.5)
**Repository**: unified-intelligence-cli
**Project Builder Version**: Current (as of 2025-10-11)

**Related Documentation**:
- Task Specification: `.auggie_task_meta_dogfooding.txt`
- Autocommit System: `docs/AUTOCOMMIT_*.md`
- Dogfooding Success: `docs/DOGFOODING_SUCCESS.md` (health check fix)
- Redis Security: `docs/REDIS_SECURITY_INCIDENT.md`
