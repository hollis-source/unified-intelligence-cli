# Auggie to Qwen-Agent Transition Plan

**Document Version:** 1.0
**Date:** October 14, 2025
**Status:** Draft - Awaiting Approval
**Owner:** Autonomous Orchestrator Team

---

## Executive Summary

**Objective:** Transition the autonomous orchestrator from auggie (Node.js CLI for Claude/GPT APIs) to Qwen-Agent (Python framework for local Qwen3-8B models).

**Benefits:**
- **Cost Savings:** $400-700/month by replacing 60% of cloud API calls with local inference
- **Performance:** 30-40% faster response times (10-15s vs 15-25s)
- **Reliability:** No API rate limits or network dependencies
- **Privacy:** Sensitive code stays local, no cloud transmission

**Risks:**
- **Quality Degradation:** Qwen3-8B may underperform vs Claude Sonnet 4.5 on complex tasks
- **Integration Complexity:** Qwen-Agent framework requires significant adapter code
- **Maintenance Burden:** Local models require updates, quantization, GPU management

**Timeline:** 8-10 weeks (6 phases)

**Success Criteria:** ≥95% success rate, ≤20s latency, ≥20% code complexity reduction

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Target State Architecture](#target-state-architecture)
3. [Transition Strategy](#transition-strategy)
4. [Phase-by-Phase Plan](#phase-by-phase-plan)
5. [Risk Mitigation](#risk-mitigation)
6. [Success Metrics](#success-metrics)
7. [Rollback Procedures](#rollback-procedures)
8. [Resource Requirements](#resource-requirements)
9. [Decision Gates](#decision-gates)
10. [References](#references)

---

## 1. Current State Analysis

### 1.1 Auggie Integration Points

**Primary Integration:** `LocalWorkerPool` (src/claude_orchestrator/adapters/local_worker_pool.py:306-349)

```python
# Current implementation (lines 306-339)
auggie_cmd = [
    "auggie",
    "--instruction-file", str(instruction_path),
    "--model", model,  # sonnet4 or sonnet4.5
    "--quiet",
]

process = subprocess.Popen(
    auggie_cmd,
    cwd=working_dir,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,
    start_new_session=True,
    env=env,
)
```

**Key Characteristics:**
- **CLI-based:** Auggie is a Node.js executable invoked via subprocess
- **Model Selection:** Supports sonnet4, sonnet4.5, gpt5 via `--model` flag
- **Async Execution:** Fire-and-forget with PID tracking
- **Output Handling:** Streams to log files, parsed post-execution
- **Error Handling:** Exit codes and log parsing

**Other Integration Points:**
1. `SingleWorkerPool` (SSH-based, similar pattern)
2. `AuggiePRReviewer` (specialized PR review adapter)
3. Configuration files (model names, timeouts)

### 1.2 Auggie Capabilities Used

| Capability | Usage | Qwen-Agent Equivalent |
|------------|-------|----------------------|
| Instruction file input | All tasks | `qwen_agent.Agent.run(prompt=file_content)` |
| Multi-model support | sonnet4/4.5, gpt5 | Qwen3-8B (local), fallback to API |
| Streaming output | Log files | `qwen_agent.Agent.run_stream()` |
| Quiet mode | `--quiet` flag | N/A (Python integration) |
| Working directory | `cwd=` param | Python `os.chdir()` or path config |

### 1.3 Dependencies

**Runtime Dependencies:**
- Node.js v22+ (for auggie)
- auggie npm package
- Anthropic API key (ANTHROPIC_API_KEY)
- OpenAI API key (for GPT-5, optional)

**File System:**
- `/tmp/orchestrator-task-*.txt` (instruction files)
- `/tmp/orchestrator-task-*.log` (output logs)
- `/tmp/orchestrator-task-*.status` (status files)
- `/tmp/orchestrator-task-*.pid` (process IDs)

---

## 2. Target State Architecture

### 2.1 Qwen-Agent Architecture

**New Component:** `QwenAgentWorkerPool` (implements `IWorkerPool`)

```python
"""QwenAgentWorkerPool Adapter.

Local Qwen3-8B-based worker pool using Qwen-Agent framework.
Drop-in replacement for auggie-based LocalWorkerPool.

Clean Architecture: Adapter layer (implements IWorkerPool interface)
SOLID: LSP - substitutable for IWorkerPool
"""

from qwen_agent import Agent
from qwen_agent.llm import ModelService

class QwenAgentWorkerPool(IWorkerPool):
    """
    Worker pool using local Qwen3-8B via Qwen-Agent framework.

    Key Features:
    - Local inference (no API calls)
    - Function calling support (built-in)
    - Streaming output
    - Dual-mode thinking (/think vs /no_think)

    Fallback Strategy:
    - Complex tasks (>100 lines, architecture): Fallback to Claude Sonnet 4.5
    - Simple tasks (<50 lines, CRUD): Use Qwen3-8B
    - Error recovery: Retry with Claude if Qwen fails
    """

    def __init__(self, config: WorkerPoolConfig):
        # Initialize Qwen3-8B model
        self.qwen_agent = Agent(
            function_list=[],  # Add tools later
            llm={
                'model': 'Qwen3-8B',
                'model_server': 'local',  # vs 'dashscope' for API
                'generate_cfg': {
                    'top_p': 0.8,
                    'temperature': 0.7,
                }
            }
        )

        # Fallback to Claude for complex tasks
        self.fallback_enabled = config.fallback_to_auggie
        self.auggie_pool = LocalWorkerPool(config) if self.fallback_enabled else None

    def assign_task(self, task: GeneratedTask) -> Worker:
        # Complexity analysis
        if self._is_complex_task(task):
            logger.info(f"Task {task.id} is complex, using auggie fallback")
            return self.auggie_pool.assign_task(task)

        # Execute with Qwen-Agent
        return self._execute_with_qwen(task)
```

### 2.2 Integration with Existing Architecture

**Clean Architecture Preservation:**
```
┌─────────────────────────────────────────┐
│   Orchestrator (Use Case Layer)        │
│   - AutonomousOrchestrator              │
└────────────┬────────────────────────────┘
             │ depends on IWorkerPool (interface)
             ▼
┌─────────────────────────────────────────┐
│   IWorkerPool Interface (Port)          │
│   - assign_task(task) -> Worker         │
│   - wait_for_completion(worker_id)      │
│   - get_worker_status(worker_id)        │
└─────┬───────────────────┬───────────────┘
      │                   │
      ▼                   ▼
┌─────────────┐    ┌──────────────────┐
│LocalWorker  │    │QwenAgentWorker   │  ← NEW
│Pool         │    │Pool              │
│(auggie)     │    │(Qwen-Agent)      │
└─────────────┘    └──────────────────┘
```

**Key Principle:** Orchestrator never knows which implementation it's using (Dependency Inversion Principle).

### 2.3 Hybrid Approach (Transition State)

**Strategy:** Run both adapters in parallel with intelligent routing.

```python
class HybridWorkerPool(IWorkerPool):
    """
    Hybrid pool that routes tasks to Qwen-Agent or auggie based on complexity.

    Routing Logic:
    - Complex tasks (architecture, refactoring): auggie (Claude Sonnet 4.5)
    - Simple tasks (CRUD, tests, docs): Qwen-Agent (Qwen3-8B)
    - Error recovery: Retry failed Qwen tasks with auggie
    """

    def __init__(self, config: WorkerPoolConfig):
        self.qwen_pool = QwenAgentWorkerPool(config)
        self.auggie_pool = LocalWorkerPool(config)

        # Metrics tracking
        self.qwen_success_rate = 0.0
        self.auggie_success_rate = 0.0
        self.qwen_latency_avg = 0.0
        self.auggie_latency_avg = 0.0

    def assign_task(self, task: GeneratedTask) -> Worker:
        # Route based on complexity
        if self._should_use_qwen(task):
            try:
                return self.qwen_pool.assign_task(task)
            except Exception as e:
                logger.warning(f"Qwen failed for {task.id}, falling back to auggie: {e}")
                return self.auggie_pool.assign_task(task)
        else:
            return self.auggie_pool.assign_task(task)

    def _should_use_qwen(self, task: GeneratedTask) -> bool:
        """
        Determine if task is suitable for Qwen-Agent.

        Criteria:
        - Estimated time < 30 minutes
        - Not flagged as "complex" or "architecture"
        - No multi-file refactoring
        - Success rate > 90% for similar tasks
        """
        # Complexity heuristics
        is_simple = (
            task.estimated_minutes < 30 and
            "architecture" not in task.instruction.lower() and
            "refactor" not in task.instruction.lower() and
            self.qwen_success_rate > 0.9
        )

        return is_simple
```

---

## 3. Transition Strategy

### 3.1 Core Principles

1. **Gradual Rollout:** Never big-bang migration. Phase-by-phase with validation.
2. **Backward Compatibility:** Maintain auggie support for 6+ months post-transition.
3. **Data-Driven Decisions:** Use A/B testing and metrics to validate each phase.
4. **Fallback Always Available:** Qwen failures automatically retry with auggie.
5. **No Orchestrator Changes:** Only adapter layer changes (Clean Architecture).

### 3.2 Rollout Strategy

**Phase 0: Foundation (Week 1-2)**
- Set up Qwen-Agent development environment
- Create proof-of-concept QwenAgentWorkerPool
- Validate Qwen3-8B model works locally
- Benchmark baseline performance

**Phase 1: Adapter Implementation (Week 3-4)**
- Implement QwenAgentWorkerPool (full IWorkerPool interface)
- Add HybridWorkerPool for dual-mode operation
- Create complexity classifier
- Unit tests (100% coverage)

**Phase 2: Limited Beta (Week 5-6)**
- Route 10% of simple tasks to Qwen-Agent
- Monitor success rate, latency, quality
- Collect failure logs for analysis
- A/B test results

**Phase 3: Expanded Rollout (Week 7-8)**
- Route 50% of simple tasks to Qwen-Agent (if Phase 2 success rate ≥95%)
- Add function calling support (Qwen-Agent tools)
- Implement auto-retry logic (Qwen → auggie fallback)

**Phase 4: Full Deployment (Week 9-10)**
- Route 90% of tasks to Qwen-Agent (keep 10% on auggie for comparison)
- Deprecate auggie for simple tasks
- Update documentation

**Phase 5: Auggie Sunset (Month 3-6)**
- Monitor Qwen-Agent stability for 3 months
- Remove auggie dependency (optional - keep for complex tasks)

### 3.3 Validation at Each Phase

**Gate Criteria (must pass to proceed):**
1. **Success Rate:** ≥95% task completion (vs baseline 98%)
2. **Latency:** ≤20s average (vs baseline 15s)
3. **Quality:** Code review scores ≥85/100 (manual review of 20 samples)
4. **Cost:** ≥30% API cost reduction
5. **Stability:** Zero critical bugs, <5% rollback rate

**Failure Triggers (rollback to previous phase):**
- Success rate < 90%
- Critical bug discovered
- User complaints > 10 per week
- Manual quality review fails (score < 80/100)

---

## 4. Phase-by-Phase Plan

### Phase 0: Foundation (Week 1-2)

**Objective:** Set up infrastructure and validate Qwen3-8B works locally.

**Tasks:**
1. **Environment Setup (2 hours)**
   - Install Qwen-Agent: `pip install qwen-agent`
   - Install llama.cpp (if not using HuggingFace)
   - Verify Qwen3-8B model: `/data/ai-models/Qwen3-8B/` (16.4GB)
   - Test quantized version: Qwen3-8B-Q4_K_M.gguf (4.5GB)

2. **Proof-of-Concept (8 hours)**
   - Create minimal QwenAgentWorkerPool
   - Execute 1 simple task (e.g., "Create hello_world.py")
   - Measure latency, success rate
   - Compare output quality with auggie (Claude Sonnet 4.5)

3. **Benchmarking (4 hours)**
   - Run 50 simple tasks with both adapters
   - Measure: success rate, latency, quality scores
   - Document baseline metrics

**Deliverables:**
- POC code: `src/claude_orchestrator/adapters/qwen_agent_worker_pool.py` (minimal)
- Benchmark report: `docs/QWEN_AGENT_POC_RESULTS.md`
- Decision: GO/NO-GO for Phase 1

**Success Criteria:**
- Qwen3-8B executes tasks successfully (≥80% success rate in POC)
- Latency ≤25s (acceptable for POC)
- No critical issues (crashes, data corruption)

---

### Phase 1: Full Adapter Implementation (Week 3-4)

**Objective:** Implement production-ready QwenAgentWorkerPool and HybridWorkerPool.

**Tasks:**
1. **QwenAgentWorkerPool Implementation (16 hours)**
   - Implement all IWorkerPool methods:
     - `assign_task(task)` → execute with Qwen-Agent
     - `wait_for_completion(worker_id)` → stream output, parse results
     - `get_worker_status(worker_id)` → track Qwen-Agent execution
     - `cancel_task(worker_id)` → interrupt Qwen-Agent
     - `shutdown()` → cleanup resources
   - Handle instruction file → prompt conversion
   - Stream output to log files (match auggie format)
   - Error handling and logging

2. **HybridWorkerPool Implementation (12 hours)**
   - Implement complexity classifier (`_should_use_qwen()`)
   - Add fallback logic (Qwen failure → retry with auggie)
   - Metrics tracking (success rate, latency per adapter)
   - A/B testing infrastructure (route X% to Qwen, Y% to auggie)

3. **Testing (12 hours)**
   - Unit tests: 100% coverage for QwenAgentWorkerPool
   - Integration tests: Execute 100 tasks with HybridWorkerPool
   - Edge cases: timeouts, cancellations, malformed instructions
   - Load testing: 10 concurrent tasks

4. **Configuration (4 hours)**
   - Add config options:
     ```yaml
     worker_pool:
       type: hybrid  # or qwen_agent, local (auggie)
       qwen_model: Qwen3-8B-Q4_K_M  # quantized for speed
       fallback_enabled: true
       complexity_threshold: 30  # minutes
       qwen_traffic_percent: 10  # start with 10%
     ```

**Deliverables:**
- `src/claude_orchestrator/adapters/qwen_agent_worker_pool.py` (full implementation)
- `src/claude_orchestrator/adapters/hybrid_worker_pool.py`
- `tests/unit/claude_orchestrator/test_qwen_agent_worker_pool.py`
- `tests/integration/claude_orchestrator/test_hybrid_worker_pool.py`
- Updated configuration schema

**Success Criteria:**
- All tests pass (100% unit, 100% integration)
- HybridWorkerPool routes correctly (10% to Qwen in beta)
- Fallback works (Qwen failure → auggie retry)

---

### Phase 2: Limited Beta (Week 5-6)

**Objective:** Deploy HybridWorkerPool in production, route 10% traffic to Qwen-Agent.

**Tasks:**
1. **Deployment (4 hours)**
   - Update `autonomous_dev_tool.py` to use HybridWorkerPool
   - Set `qwen_traffic_percent: 10`
   - Deploy to production
   - Monitor logs for 24 hours

2. **Monitoring (ongoing, 2 weeks)**
   - Track metrics:
     - Success rate: Qwen vs auggie
     - Latency: P50, P95, P99
     - Error rate: Qwen failures, fallback triggers
     - Cost: API calls saved
   - Alert on:
     - Success rate < 90%
     - Latency > 30s (P95)
     - Error rate > 10%

3. **Quality Review (8 hours/week)**
   - Sample 20 Qwen-generated outputs per week
   - Manual code review (correctness, style, completeness)
   - Score each output: 0-100
   - Compare with auggie baseline

4. **Analysis (4 hours)**
   - Aggregate metrics after 2 weeks
   - Identify failure patterns (which tasks Qwen fails on)
   - Tune complexity classifier
   - Decision: GO/NO-GO for Phase 3

**Deliverables:**
- Production deployment
- Metrics dashboard (Grafana or similar)
- Quality review report: `docs/PHASE2_QUALITY_REVIEW.md`
- Decision report: `docs/PHASE2_DECISION_REPORT.md`

**Success Criteria (Gate to Phase 3):**
- Success rate ≥95% (vs baseline 98%)
- Latency P95 ≤25s (vs baseline 15s)
- Quality score ≥85/100 (manual review)
- Zero critical bugs
- <5% fallback rate (Qwen failures)

**Rollback Triggers:**
- Success rate < 90%
- Quality score < 80/100
- >3 critical bugs
- User complaints > 5

---

### Phase 3: Expanded Rollout (Week 7-8)

**Objective:** Increase Qwen traffic to 50%, add function calling support.

**Tasks:**
1. **Traffic Increase (2 hours)**
   - Update config: `qwen_traffic_percent: 50`
   - Deploy and monitor

2. **Function Calling (16 hours)**
   - Implement Qwen-Agent tools:
     - File operations (read, write, glob)
     - Git operations (commit, push, branch)
     - Test execution (pytest, coverage)
   - Map to Qwen-Agent `function_list`
   - Test tool usage in complex tasks

3. **Auto-Retry Logic (8 hours)**
   - Detect Qwen failures (timeout, syntax error, low confidence)
   - Automatically retry with auggie (Claude Sonnet 4.5)
   - Log retry reasons for analysis

4. **Monitoring & Analysis (ongoing)**
   - Same as Phase 2, but higher traffic volume
   - Identify new failure patterns at scale

**Deliverables:**
- Updated config: 50% Qwen traffic
- Function calling implementation
- Auto-retry logic
- Phase 3 quality review: `docs/PHASE3_QUALITY_REVIEW.md`

**Success Criteria (Gate to Phase 4):**
- Success rate ≥95% (50% traffic)
- Latency P95 ≤20s
- Quality score ≥85/100
- ≥30% API cost reduction
- Function calling works (≥90% tool success rate)

---

### Phase 4: Full Deployment (Week 9-10)

**Objective:** Route 90% traffic to Qwen-Agent, deprecate auggie for simple tasks.

**Tasks:**
1. **Traffic Increase (2 hours)**
   - Update config: `qwen_traffic_percent: 90`
   - Keep 10% on auggie for comparison (A/B testing)

2. **Performance Tuning (8 hours)**
   - Optimize Qwen3-8B quantization (Q4 vs Q5 vs FP16)
   - Tune temperature, top_p, max_tokens
   - Batch processing (if applicable)
   - Profile and fix bottlenecks

3. **Documentation (8 hours)**
   - Update CLAUDE.md: Dogfooding section
   - Update autonomous orchestrator docs
   - Migration guide for users
   - Troubleshooting guide

4. **Stability Monitoring (2 weeks)**
   - Monitor 90% traffic for 2 weeks
   - Track long-term success rate, latency trends
   - Identify any regressions

**Deliverables:**
- 90% Qwen traffic in production
- Performance tuning report
- Updated documentation
- Phase 4 final report: `docs/PHASE4_FINAL_REPORT.md`

**Success Criteria (Transition Complete):**
- Success rate ≥95% sustained for 2 weeks
- Latency P95 ≤20s sustained
- Quality score ≥85/100 sustained
- ≥50% API cost reduction
- Zero critical bugs for 2 weeks

---

### Phase 5: Auggie Sunset (Month 3-6)

**Objective:** Remove auggie dependency (optional - may keep for complex tasks).

**Tasks:**
1. **Monitoring Period (3 months)**
   - Track Qwen-Agent stability long-term
   - Collect user feedback
   - Identify edge cases

2. **Decision: Full Replacement vs Hybrid Long-Term**
   - **Option A:** Remove auggie entirely (100% Qwen-Agent)
     - Only if: Success rate ≥98%, quality perfect
   - **Option B:** Keep hybrid (90% Qwen, 10% auggie for complex tasks)
     - Recommended: Best of both worlds

3. **Cleanup (if Option A chosen)**
   - Remove auggie npm package
   - Remove LocalWorkerPool adapter
   - Update all configs
   - Archive migration documentation

**Deliverables:**
- Final decision report
- Cleanup (if applicable)
- Post-mortem: `docs/AUGGIE_TO_QWEN_POSTMORTEM.md`

---

## 5. Risk Mitigation

### 5.1 Quality Degradation Risk

**Risk:** Qwen3-8B underperforms vs Claude Sonnet 4.5 on complex tasks.

**Likelihood:** High (80%)
**Impact:** High (user dissatisfaction, bugs)

**Mitigation:**
1. **Hybrid Approach:** Keep auggie for complex tasks (architecture, refactoring)
2. **Fallback Always Enabled:** Auto-retry Qwen failures with auggie
3. **Quality Gates:** Manual review at each phase, rollback if quality < 85/100
4. **Fine-Tuning:** Continue training Qwen3-8B on codebase-specific data

**Contingency:**
- If quality never reaches 85/100, keep hybrid long-term (90% Qwen, 10% auggie)

---

### 5.2 Integration Complexity Risk

**Risk:** Qwen-Agent framework requires significant refactoring, delays timeline.

**Likelihood:** Medium (50%)
**Impact:** Medium (2-4 week delay)

**Mitigation:**
1. **POC First:** Validate integration works before committing (Phase 0)
2. **Incremental Approach:** Implement adapter methods one at a time
3. **Clean Architecture:** Minimal changes to orchestrator (only adapter layer)
4. **Fallback:** Keep auggie working throughout transition

**Contingency:**
- If integration blockers discovered, extend Phase 1 by 2 weeks
- If Qwen-Agent unusable, abort transition (GO/NO-GO gate at Phase 0 end)

---

### 5.3 Maintenance Burden Risk

**Risk:** Local models require updates, quantization, GPU management.

**Likelihood:** Medium (50%)
**Impact:** Low (2-4 hours/month)

**Mitigation:**
1. **Quantized Models:** Use Q4_K_M (4.5GB) for speed, low maintenance
2. **CPU Inference:** llama.cpp supports CPU (no GPU dependencies)
3. **Automated Updates:** Script to download new Qwen models
4. **Monitoring:** Alert if model performance degrades

**Contingency:**
- If maintenance > 8 hours/month, re-evaluate hybrid vs full Qwen approach

---

### 5.4 Cost Savings Not Realized Risk

**Risk:** Qwen-Agent doesn't reduce costs as expected.

**Likelihood:** Low (20%)
**Impact:** Low (transition still valuable for speed/privacy)

**Mitigation:**
1. **Track API Calls:** Monitor Anthropic API usage before/after
2. **Cost Modeling:** Project savings based on Phase 2 data
3. **Decision Gate:** If Phase 3 doesn't show ≥30% savings, re-evaluate

**Contingency:**
- If savings < 20%, still proceed if quality/speed benefits justify effort

---

## 6. Success Metrics

### 6.1 Primary Metrics (Gates)

| Metric | Baseline (auggie) | Target (Qwen) | Phase 2 | Phase 3 | Phase 4 |
|--------|-------------------|---------------|---------|---------|---------|
| **Success Rate** | 98% | ≥95% | ≥95% | ≥95% | ≥95% |
| **Latency (P95)** | 15s | ≤20s | ≤25s | ≤20s | ≤20s |
| **Quality Score** | 90/100 | ≥85/100 | ≥85 | ≥85 | ≥85 |
| **API Cost Reduction** | $0 | ≥50% | ≥10% | ≥30% | ≥50% |
| **Fallback Rate** | N/A | <5% | <10% | <5% | <5% |

### 6.2 Secondary Metrics (Monitoring)

- **Error Rate:** <2% (Qwen syntax errors, crashes)
- **Retry Rate:** <10% (Qwen → auggie fallback)
- **Tool Success Rate:** ≥90% (function calling)
- **Model Load Time:** <3s (Qwen3-8B initialization)
- **Memory Usage:** <2GB (Qwen3-8B Q4_K_M)
- **User Complaints:** <5/week

### 6.3 Quality Review Criteria (Manual)

**Scoring Rubric (0-100):**
- **Correctness (40 points):** Code runs without errors, meets requirements
- **Style (20 points):** PEP 8, clean code principles, proper naming
- **Completeness (20 points):** All tasks completed, no missing features
- **Documentation (10 points):** Docstrings, comments, README updates
- **Test Coverage (10 points):** Unit tests provided (if applicable)

**Sample Size:**
- Phase 2: 20 samples/week (2 weeks = 40 total)
- Phase 3: 20 samples/week (2 weeks = 40 total)
- Phase 4: 20 samples/week (2 weeks = 40 total)

**Reviewers:**
- 2 senior engineers (blind review, no knowledge of Qwen vs auggie)

---

## 7. Rollback Procedures

### 7.1 Rollback Triggers

**Immediate Rollback (within 1 hour):**
- Critical bug (data corruption, security issue)
- Success rate < 85%
- Production outage caused by Qwen-Agent

**Planned Rollback (within 1 day):**
- Success rate 85-90% (below gate)
- Quality score < 80/100
- User complaints > 10/week

**Phase Rollback (return to previous phase):**
- Success rate 90-95% but unstable
- Cost savings < expected but non-critical

### 7.2 Rollback Steps

**Step 1: Reduce Traffic (5 minutes)**
```bash
# Update config
vim config/worker_pool.yaml
# Change: qwen_traffic_percent: 50 → 10

# Restart orchestrator
systemctl restart autonomous-orchestrator
```

**Step 2: Investigate (1-4 hours)**
- Review logs: `/tmp/orchestrator-task-*.log`
- Identify failure patterns
- Reproduce bugs locally

**Step 3: Fix or Abort (varies)**
- **Option A:** Fix issue, redeploy (if quick fix available)
- **Option B:** Rollback to previous phase (if systematic issue)
- **Option C:** Abort transition (if fundamental Qwen-Agent issue)

**Step 4: Post-Mortem (1 day)**
- Document what went wrong
- Update risk mitigation strategies
- Decide: retry phase or abort transition

### 7.3 Rollback Testing

**Pre-Deployment:**
- Test rollback procedure in staging
- Ensure auggie still works after Qwen-Agent deployed
- Verify config changes take effect instantly

**During Each Phase:**
- Practice rollback drills (every 2 weeks)
- Ensure team knows how to execute rollback

---

## 8. Resource Requirements

### 8.1 Human Resources

| Role | Time Commitment | Phases |
|------|----------------|---------|
| **Senior Engineer** | 50% (4 hours/day) | 0-4 (10 weeks) |
| **Code Reviewer** | 10% (4 hours/week) | 2-4 (6 weeks) |
| **DevOps Engineer** | 20% (1 hour/day) | 1-4 (8 weeks) |
| **Project Manager** | 10% (2 hours/week) | 0-5 (6 months) |

**Total Effort:** ~200 hours (5 weeks FTE)

### 8.2 Infrastructure

| Resource | Requirements | Cost |
|----------|--------------|------|
| **Qwen3-8B Model** | 16.4GB disk (or 4.5GB quantized) | $0 |
| **CPU/GPU** | 48-core CPU or 1x GPU (24GB VRAM) | Existing |
| **RAM** | +2GB for Qwen-Agent | Existing |
| **Disk** | +20GB for models, logs | Existing |
| **API Credits** | Anthropic (reduced by 50% after Phase 4) | -$400/month |

**Net Cost:** -$400/month after Phase 4 (savings)

### 8.3 Software

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| qwen-agent | ≥0.0.4 | Apache 2.0 | Qwen-Agent framework |
| transformers | ≥4.56.2 | Apache 2.0 | HuggingFace models |
| llama-cpp-python | ≥0.2.0 | MIT | GGUF inference (optional) |
| torch | ≥2.0 | BSD | PyTorch for models |

---

## 9. Decision Gates

### 9.1 Gate 0: GO/NO-GO for Phase 1 (End of Week 2)

**Criteria:**
- [ ] Qwen3-8B executes POC tasks (≥80% success rate)
- [ ] Latency ≤30s in POC
- [ ] No critical issues (crashes, data corruption)
- [ ] Team confident in Qwen-Agent integration

**Decision Makers:** Senior Engineer, Project Manager

**Outcomes:**
- **GO:** Proceed to Phase 1 (Adapter Implementation)
- **NO-GO:** Abort transition, stick with auggie

---

### 9.2 Gate 1: GO/NO-GO for Phase 2 (End of Week 4)

**Criteria:**
- [ ] QwenAgentWorkerPool fully implemented
- [ ] All tests pass (100% unit, 100% integration)
- [ ] HybridWorkerPool routes correctly
- [ ] Fallback logic works

**Decision Makers:** Senior Engineer, Code Reviewer

**Outcomes:**
- **GO:** Proceed to Phase 2 (Limited Beta)
- **NO-GO:** Fix issues, retry Gate 1 next week

---

### 9.3 Gate 2: GO/NO-GO for Phase 3 (End of Week 6)

**Criteria:**
- [ ] Success rate ≥95% (10% traffic)
- [ ] Latency P95 ≤25s
- [ ] Quality score ≥85/100
- [ ] <5% fallback rate
- [ ] Zero critical bugs

**Decision Makers:** Senior Engineer, Code Reviewer, Project Manager

**Outcomes:**
- **GO:** Proceed to Phase 3 (Expand to 50%)
- **ROLLBACK:** Reduce traffic, investigate issues
- **ABORT:** Fundamental quality issues, stick with auggie

---

### 9.4 Gate 3: GO/NO-GO for Phase 4 (End of Week 8)

**Criteria:**
- [ ] Success rate ≥95% (50% traffic)
- [ ] Latency P95 ≤20s
- [ ] Quality score ≥85/100
- [ ] ≥30% API cost reduction
- [ ] Function calling works

**Decision Makers:** Senior Engineer, Project Manager

**Outcomes:**
- **GO:** Proceed to Phase 4 (90% traffic)
- **ROLLBACK:** Return to Phase 2 (10% traffic)

---

### 9.5 Gate 4: Transition Complete (End of Week 10)

**Criteria:**
- [ ] Success rate ≥95% (90% traffic, sustained 2 weeks)
- [ ] Latency P95 ≤20s (sustained)
- [ ] Quality score ≥85/100 (sustained)
- [ ] ≥50% API cost reduction
- [ ] Zero critical bugs for 2 weeks

**Decision Makers:** Senior Engineer, Project Manager, CTO

**Outcomes:**
- **COMPLETE:** Transition successful, begin Phase 5 (optional auggie sunset)
- **HYBRID LONG-TERM:** Keep 90/10 split indefinitely

---

## 10. References

### 10.1 Related Documents

- [QWEN3_QWEN_AGENT_ANALYSIS.md](./QWEN3_QWEN_AGENT_ANALYSIS.md) - Qwen3 research and analysis
- [CLAUDE.md](../CLAUDE.md) - Dogfooding guidelines
- [IWorkerPool Interface](../src/claude_orchestrator/interfaces/worker_pool.py) - Abstract interface
- [LocalWorkerPool](../src/claude_orchestrator/adapters/local_worker_pool.py) - Current auggie implementation

### 10.2 External References

- [Qwen-Agent GitHub](https://github.com/QwenLM/Qwen-Agent) - Official Qwen-Agent framework
- [Qwen3 Model Card](https://huggingface.co/Qwen/Qwen3-8B) - Qwen3-8B on HuggingFace
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - GGUF inference engine
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Architectural principles

### 10.3 Benchmarking Data

*To be added after Phase 0 completion*

---

## Appendix A: Complexity Classifier Heuristics

```python
def classify_task_complexity(task: GeneratedTask) -> str:
    """
    Classify task as simple, medium, or complex.

    Returns:
        "simple" -> Use Qwen-Agent
        "medium" -> Use Qwen-Agent with fallback
        "complex" -> Use auggie (Claude Sonnet 4.5)
    """
    instruction = task.instruction.lower()

    # Complex keywords
    complex_keywords = [
        "architecture", "design", "refactor", "migrate",
        "multi-file", "breaking change", "legacy code",
    ]

    # Simple keywords
    simple_keywords = [
        "create", "add", "test", "doc", "fix typo",
        "update readme", "format", "lint",
    ]

    # Check keywords
    if any(kw in instruction for kw in complex_keywords):
        return "complex"

    if any(kw in instruction for kw in simple_keywords):
        return "simple"

    # Check estimated time
    if task.estimated_minutes > 60:
        return "complex"
    elif task.estimated_minutes < 15:
        return "simple"
    else:
        return "medium"
```

---

## Appendix B: Qwen-Agent Configuration Examples

```python
# Example 1: Local Qwen3-8B with llama.cpp
config = {
    'model': 'Qwen3-8B-Q4_K_M',
    'model_server': 'local',
    'model_path': '/data/ai-models/Qwen3-8B-Q4_K_M.gguf',
    'generate_cfg': {
        'top_p': 0.8,
        'temperature': 0.7,
        'max_tokens': 8192,
    },
}

# Example 2: HuggingFace Transformers
config = {
    'model': 'Qwen/Qwen3-8B',
    'model_server': 'huggingface',
    'device': 'cuda',  # or 'cpu'
    'generate_cfg': {
        'top_p': 0.8,
        'temperature': 0.7,
        'max_new_tokens': 8192,
    },
}

# Example 3: Hybrid with fallback
config = {
    'primary_model': {
        'model': 'Qwen3-8B',
        'model_server': 'local',
    },
    'fallback_model': {
        'model': 'claude-sonnet-4.5',
        'model_server': 'anthropic',
        'api_key': os.getenv('ANTHROPIC_API_KEY'),
    },
    'fallback_triggers': [
        'timeout',
        'syntax_error',
        'low_confidence',
    ],
}
```

---

**END OF TRANSITION PLAN**

*Last Updated: October 14, 2025*
*Version: 1.0 - Draft*
*Status: Awaiting Approval*
