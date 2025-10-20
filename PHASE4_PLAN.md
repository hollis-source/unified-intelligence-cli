# Phase 4: Agentic Integration Plan

**Date:** 2025-10-15  
**Status:** 📋 **PLANNING**

---

## Executive Summary

After successfully completing RAG integration (Phase 3), we now plan to:
1. **Validate** Granite's agentic capabilities (tool calling, planning, error recovery)
2. **Integrate** Granite + RAG with ATADO multi-agent orchestration framework
3. **Benchmark** performance vs existing LLM providers (OpenAI, Anthropic)

---

## Current State

**Completed Phases:**
- ✅ Phase 1: Hardware optimization (17.17 tok/s single instance)
- ✅ Phase 2: Multi-instance scaling (2×512K @ 31.34 tok/s)  
- ✅ Phase 3: RAG integration (p95 latency: 1.1ms)

**Assets:**
- IBM Granite 4.0-H (32B-A9B) with 512K context window
- SurrealDB vector database with semantic code search
- ATADO multi-agent framework (team-based routing, HTN planning)

---

## Strategic Analysis

### Key Assumptions to Challenge

1. **"Granite is suitable for agentic tasks"**
   - ❓ Granite is hybrid SSM+Attention optimized for long context, NOT specifically for agents
   - ❓ Unknown: Tool calling accuracy, planning quality, error recovery
   - **Validation:** Benchmark on agentic tasks first (Phase 4A)

2. **"ATADO integration is straightforward"**
   - ❓ ATADO has complex routing (team-based, hierarchical, HTN decomposition)
   - ❓ May require adapter refactoring for Granite's llama.cpp API
   - **Mitigation:** Start with simple ITextGenerator interface, extend later

3. **"RAG will improve agent performance"**
   - ❓ RAG adds 7ms latency + context tokens (may distract agents)
   - ❓ Retrieval relevance depends on query quality
   - **Validation:** A/B test RAG vs non-RAG on same ATADO workflows

4. **"512K context is necessary for agentic tasks"**
   - ❓ Most agent tasks don't need 512K (typical: 8K-64K)
   - **Trade-off:** Could use 4×128K for 2x throughput vs 2×512K

###Trade-offs Matrix

| Dimension | Granite 4.0-H Local | OpenAI/Anthropic API | Winner |
|-----------|---------------------|----------------------|--------|
| **Throughput** | 15.67 tok/s | 50-150 tok/s | API (3-10x faster) |
| **Context** | 512K tokens | 200K max | Granite (2.5x larger) |
| **Cost** | $0 (local) | $10-50/M tokens | Granite (infinite budget) |
| **Agentic Training** | Unknown | Excellent (RLHF) | API (proven) |
| **Privacy** | 100% local | Data sent to API | Granite (full control) |
| **Reliability** | Self-hosted | 99.9% SLA | API (managed) |
| **Latency** | ~6.5s/100tok | ~1-2s/100tok | API (3x faster) |

**Recommendation:**
- Use **Granite** for: Long-context tasks, privacy-sensitive workloads, cost optimization
- Use **API models** for: Fast iteration, complex agentic tasks, production reliability

---

## Phase 4A: Agentic Capability Validation (1 day)

### Goal
Understand Granite's strengths/weaknesses for agentic tasks before investing in full ATADO integration.

### Tests

**1. Tool Calling** (30 min)
- Test: Given file_read/bash_execute tools, ask to "check Python version"
- Success Criteria: Valid tool call syntax, correct tool selection
- Baseline: OpenAI/Anthropic achieve >95% accuracy

**2. Task Decomposition** (30 min)
- Test: "Implement user authentication" → subtasks
- Success Criteria: Logical decomposition (5-7 steps), correct dependencies
- Baseline: GPT-4 produces production-ready decompositions

**3. Multi-turn Reasoning** (30 min)
- Test: 5-turn conversation requiring context retention
- Success Criteria: No hallucinations, consistent with previous turns
- Baseline: Claude 3.5 excels at multi-turn tasks

**4. Error Recovery** (30 min)
- Test: Given failed test output, ask to identify root cause + fix
- Success Criteria: Correct diagnosis, valid fix
- Baseline: Most LLMs achieve 70-80% on debugging tasks

**5. Comparative Benchmark** (2 hours)
- Run same 10 tasks on Granite vs OpenAI vs Anthropic via ATADO
- Measure: Success rate, latency, quality (human evaluation)
- Document strengths/weaknesses

### Deliverables
- `test_granite_agentic.py` - Automated benchmark script ✅
- `GRANITE_AGENTIC_BENCHMARK.md` - Results + analysis
- `granite_benchmark.json` - Machine-readable results

### Success Metrics
| Metric | Target | Rationale |
|--------|--------|-----------|
| Tool calling accuracy | >80% | Minimum for production agents |
| Task decomposition quality | 3.5/5 | Human eval scale |
| Error recovery rate | >70% | Industry baseline |
| Overall agentic score | >75% | Aggregate across all tests |

### Decision Point
- **If >75%:** Proceed to Phase 4B (ATADO integration)
- **If 50-75%:** Use Granite for long-context only, API for complex tasks
- **If <50%:** Recommend API models for all agentic workflows

---

## Phase 4B: ATADO Integration (2-3 days)

### Goal
Integrate Granite + RAG as ATADO LLM provider, validate on real workflows.

### Implementation Steps

**1. Create GraniteAdapter** (4 hours)

```python
# src/adapters/llm/granite_adapter.py

class GraniteAdapter(ITextGenerator):
    """
    IBM Granite 4.0-H adapter with RAG support.
    
    Features:
    - Load balancing across 2 instances (8080, 8081)
    - RAG context injection (optional)
    - Streaming support
    - Prompt caching
    """
    
    def __init__(self, instances=None, enable_rag=True):
        self.instances = instances or ["http://localhost:8080", "http://localhost:8081"]
        self.enable_rag = enable_rag
        self.current_instance = 0  # Round-robin
        
        if enable_rag:
            self.rag = CodebaseRAG(db=..., embedder=...)
    
    def generate(self, messages, config=None):
        # Extract user query from messages
        query = messages[-1]["content"]
        
        # Retrieve RAG context (if enabled)
        if self.enable_rag:
            context = self._retrieve_context(query)
            messages = self._inject_context(messages, context)
        
        # Load balance across instances
        instance = self._get_next_instance()
        
        # Call llama.cpp
        response = requests.post(
            f"{instance}/completion",
            json={"prompt": self._format_prompt(messages), ...}
        )
        
        return response.json()["content"]
```

**2. RAG-Enhanced TaskCoordinator** (4 hours)

Extend existing `RAGTaskCoordinator` to support Granite adapter.

```python
# src/use_cases/rag_task_coordinator.py

class RAGTaskCoordinator(TaskCoordinatorUseCase):
    """
    Task coordinator with Granite + RAG.
    
    Flow:
    1. Task → Retrieve relevant code via RAG
    2. Inject context into agent prompts
    3. Execute with Granite
    4. Log execution patterns back to SurrealDB
    """
    
    async def coordinate(self, tasks, agents, context):
        for task in tasks:
            # Retrieve codebase context
            rag_context = await self.rag.retrieve(task.description)
            
            # Inject into agent executor
            task.metadata["rag_context"] = rag_context
            
            # Execute with Granite
            result = await self.agent_executor.execute(task, agents)
            
            # Log for future learning
            await self._log_execution(task, result, rag_context)
        
        return results
```

**3. Integration Testing** (8 hours)

Test on progressively complex ATADO workflows:

**Test A: Single Agent Task** (Simple)
- Task: "Explain the HTN task decomposition algorithm"
- Agent: Research specialist
- Expected: Granite retrieves HTN code via RAG, generates explanation
- Metrics: Accuracy (human eval), latency, RAG context relevance

**Test B: Multi-Agent Task** (Medium)
- Task: "Review pull request #123 for code quality and test coverage"
- Agents: Code reviewer, Test engineer
- Expected: Team-based routing, parallel execution, RAG retrieval
- Metrics: Review quality, task success rate, coordination overhead

**Test C: Complex Orchestration** (Hard)
- Task: "Research optimal caching strategies for distributed systems"
- Agents: 6 research agents (parallel execution)
- Expected: HTN decomposition, distributed research, synthesis
- Metrics: Research depth, synthesis quality, execution time

**Test D: A/B Comparison** (Validation)
- Run Tests A-C with Granite+RAG vs OpenAI (no RAG)
- Measure: Success rate, latency, quality (human eval), cost

**4. Performance Optimization** (4 hours)

- Profile RAG retrieval overhead (target: <10ms end-to-end)
- Optimize context injection (relevance filtering, token budget)
- Tune retrieval top-k for different task types (3-5 for simple, 10-15 for complex)
- Implement prompt caching for repeated queries

### Deliverables
- `src/adapters/llm/granite_adapter.py` - GraniteAdapter implementation
- `src/use_cases/rag_task_coordinator.py` - Extended coordinator
- `tests/integration/test_granite_atado.py` - Integration tests
- `ATADO_INTEGRATION_RESULTS.md` - Performance analysis

### Success Metrics
| Metric | Target | Baseline (OpenAI) |
|--------|--------|-------------------|
| Task success rate | >70% | 85% |
| Tool calling accuracy | >80% | 95% |
| End-to-end latency | <60s | <30s |
| RAG context relevance | >0.6 similarity | N/A |
| Cost per 1000 tasks | $0 | $50-100 |

---

## Risk Assessment

### High Risks
1. **Granite may not perform well on agentic tasks** (70% probability)
   - Mitigation: Phase 4A benchmarking validates before full integration
   - Fallback: Use Granite for long-context only, API for complex tasks

2. **RAG may add more noise than signal** (40% probability)
   - Mitigation: A/B test RAG vs non-RAG, measure relevance
   - Fallback: Make RAG optional, disabled by default

### Medium Risks
3. **ATADO adapter integration complexity** (50% probability)
   - Mitigation: Start with simple ITextGenerator, extend incrementally
   - Fallback: Use existing OpenAI adapter as template

4. **Performance regression vs API models** (60% probability)
   - Mitigation: Accept 2-3x latency for cost/privacy benefits
   - Fallback: Hybrid approach (Granite for some tasks, API for others)

### Low Risks
5. **llama.cpp stability issues** (20% probability)
   - Mitigation: Instances have been running stably for Phase 2-3
   - Fallback: Restart instances, add health checks

---

## Timeline

### Week 1
**Day 1:** Phase 4A - Agentic benchmarking
- Morning: Run automated tests (tool calling, decomposition, error recovery)
- Afternoon: Comparative benchmark vs OpenAI/Anthropic
- Evening: Analyze results, document findings

**Day 2:** Phase 4B Start - GraniteAdapter
- Morning: Implement GraniteAdapter with load balancing
- Afternoon: Add RAG integration
- Evening: Unit tests for adapter

**Day 3:** Phase 4B - TaskCoordinator integration
- Morning: Extend RAGTaskCoordinator for Granite
- Afternoon: Integration test A (single agent)
- Evening: Fix issues, optimize

### Week 2  
**Day 4:** Phase 4B - Complex testing
- Morning: Integration test B (multi-agent)
- Afternoon: Integration test C (complex orchestration)
- Evening: A/B comparison analysis

**Day 5:** Optimization + Documentation
- Morning: Performance optimization (caching, profiling)
- Afternoon: Write ATADO_INTEGRATION_RESULTS.md
- Evening: Update production deployment docs

---

## Success Criteria

**Phase 4A (Benchmarking):**
- ✅ Automated benchmark suite runs without errors
- ✅ Results documented with strengths/weaknesses
- ✅ Decision made: Proceed with integration OR use API models

**Phase 4B (Integration):**
- ✅ GraniteAdapter implements ITextGenerator interface
- ✅ Integration tests pass on single + multi-agent workflows
- ✅ A/B comparison shows <30% performance gap vs API models
- ✅ Production deployment guide updated

**Overall Phase 4:**
- ✅ System can execute ATADO workflows with Granite + RAG
- ✅ Performance acceptable for non-latency-critical tasks
- ✅ Cost savings validated (vs API model baseline)
- ✅ Privacy benefits realized (100% local execution)

---

## Next Phase Preview

### Phase 5: Production Deployment (If Phase 4 succeeds)
1. Load balancer setup (nginx/haproxy for 2 Granite instances)
2. Monitoring stack (Prometheus + Grafana)
3. Automated failover (health checks, instance restart)
4. Incremental codebase indexing (watch for file changes)
5. Advanced RAG features (hybrid search, re-ranking)

---

**Status:** 📋 Ready to execute Phase 4A (Agentic Benchmarking)  
**Estimated Duration:** 3-5 days (depending on results)  
**Confidence:** 75% (validated approach, manageable risks)
