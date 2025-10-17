# Agent Performance Metrics - Quick Start

**Goal**: Measure and improve 5 specialist agents from 20% baseline to 80%+ performance.

---

## 🚀 Get Started in 3 Steps

### 1. Run Baseline (First Time)
```bash
./measure_agents.sh baseline
```
⏱️ Takes ~10-15 minutes  
📊 Tests all 5 agents with 20 tasks each  
💾 Saves to `data/agent_performance/baseline.json`

---

### 2. View Dashboard
```bash
./measure_agents.sh dashboard
```
📈 Shows current performance  
🎯 Identifies optimization targets  
📉 Tracks week-over-week improvement

---

### 3. Iterate Weekly
```bash
# Make improvements (prompts, examples, code)
# Then re-test
./measure_agents.sh test

# Compare with baseline
./measure_agents.sh compare
```

---

## 📊 Key Metrics

| Metric | Target | Baseline | Description |
|--------|--------|----------|-------------|
| **Completion Rate** | 80%+ | 20% | % of tasks completed successfully |
| **Quality Score** | 8.0+/10 | 4-6 | Output quality (rubric-based) |
| **Specificity** | 80%+ | 30% | % with code references (file:line) |
| **Latency P95** | <30s | varies | 95th percentile execution time |
| **Cost per Task** | <$0.10 | varies | Estimated LLM API cost |

---

## 🎯 5 Specialist Agents

### 1. Python Engineer
**Focus**: Code quality, refactoring, SOLID principles  
**Example Task**: "Refactor src/adapters/agent/llm_executor.py to extract error handling"

### 2. Software Architect
**Focus**: System design, Clean Architecture, ADRs  
**Example Task**: "Design Clean Architecture layers for new RAG module"

### 3. Test Engineer
**Focus**: Unit, integration, E2E test generation  
**Example Task**: "Generate unit tests for src/entity/metrics.py MetricsCollector class"

### 4. DevOps Engineer
**Focus**: CI/CD, deployment, monitoring  
**Example Task**: "Design Docker Compose setup for local development"

### 5. Research Analyst
**Focus**: Documentation, investigation, planning  
**Example Task**: "Research best practices for Clean Architecture in Python"

---

## 📈 Expected Improvement Trajectory

```
Week 1 (Baseline):     20-40% completion, 4-6/10 quality
Week 2-4 (Optimize):   60-70% completion, 6-7/10 quality
Week 5+ (Refine):      80%+ completion, 8+/10 quality
```

---

## 🔧 Common Commands

```bash
# Initial baseline
./measure_agents.sh baseline

# Test single agent
./measure_agents.sh test python-engineer

# Test all agents
./measure_agents.sh test all

# View dashboard
./measure_agents.sh dashboard

# Compare with baseline
./measure_agents.sh compare

# Export HTML report
./measure_agents.sh export report.html

# Clean old results
./measure_agents.sh clean
```

---

## 🎯 Optimization Workflow

### Step 1: Identify Target
```bash
./measure_agents.sh dashboard
```
Look for "NEXT OPTIMIZATION TARGETS" section.  
Focus on highest Impact/Effort ratio.

### Step 2: Analyze Failures
```bash
# Check detailed results
cat data/agent_performance/results_*.json | jq '.detailed_results[] | select(.success == false)'
```

### Step 3: Improve
- **Low completion rate?** → Better error handling, clearer prompts
- **Low quality score?** → Add examples, improve rubric
- **Low specificity?** → Prompt for file:line references
- **High latency?** → Optimize prompts, use caching
- **High cost?** → Use cheaper models, reduce tokens

### Step 4: Re-test
```bash
./measure_agents.sh test [agent-name]
./measure_agents.sh compare
```

### Step 5: Verify No Regressions
**Critical**: Ensure other agents didn't degrade!

**Acceptance Criteria**:
- Completion rate: No decrease > 5%
- Quality score: No decrease > 0.5 points
- Latency P95: No increase > 20%

---

## 📁 File Structure

```
unified-intelligence-cli/
├── test_agent_performance.py      # Test harness (20 tasks × 5 agents)
├── agent_metrics_dashboard.py     # Metrics visualization
├── measure_agents.sh              # Quick start script
├── AGENT_METRICS.md               # Full documentation
├── AGENT_METRICS_QUICKSTART.md    # This file
└── data/
    └── agent_performance/
        ├── baseline.json          # Baseline metrics
        └── results_*.json         # Test results
```

---

## 🐛 Troubleshooting

### "No baseline found"
```bash
./measure_agents.sh baseline
```

### "No test results found"
```bash
./measure_agents.sh test
```

### "LLM provider error"
Check API keys:
```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

### "Import errors"
Install dependencies:
```bash
pip install -e .
```

---

## 📚 Learn More

- **Full Documentation**: `AGENT_METRICS.md`
- **Scoring Rubrics**: See "Output Quality Score" section in `AGENT_METRICS.md`
- **Task Definitions**: See `test_agent_performance.py` (lines 50-150)
- **Dashboard Code**: See `agent_metrics_dashboard.py`

---

## 🎉 Success Criteria

You're ready to ship when:

✅ All agents: 80%+ completion rate  
✅ All agents: 8.0+/10 quality score  
✅ All agents: 80%+ specificity  
✅ No regressions in re-tests  
✅ Human eval confirms automated scores (±1.0)

---

## 💡 Pro Tips

1. **Start with one agent** - Don't optimize all 5 at once
2. **Track weekly** - Consistent measurement reveals trends
3. **Save baselines** - Before major changes, save new baseline
4. **Human eval** - Sample 10% of tasks for manual review
5. **Celebrate wins** - When agents hit targets! 🎉

---

**Status**: ✅ Ready to use TODAY  
**Time to First Measurement**: ~15 minutes  
**Time to 80% Performance**: 4-6 weeks (with weekly iteration)

---

**Quick Start**:
```bash
./measure_agents.sh baseline
./measure_agents.sh dashboard
```

That's it! You're measuring agent performance. 🚀

