# AutoChecks Validation Results

**Generated**: 2025-10-17 10:19:56
**Agents Tested**: 2
**Total Tasks**: 40

---

## Results by Agent

❌ **Devops Agent** - FAIL
- Tasks: 20
- Passed: 2/20 (10.0%)
- Avg Quality: **3.72/10**
- Avg AutoScore: 6.20/10
- Avg Latency: 125.9s
- Avg Tokens: 2248
- Specificity: 15/20 (75.0%)
- Best: devops-18 (Q=6.0, A=10.0)
- Worst: devops-07 (Q=0.0, A=0.0)

✅ **Test Agent** - PASS
- Tasks: 20
- Passed: 14/20 (70.0%)
- Avg Quality: **6.58/10**
- Avg AutoScore: 6.58/10
- Avg Latency: 148.8s
- Avg Tokens: 2054
- Specificity: 14/20 (70.0%)
- Best: test-02 (Q=10.0, A=10.0)
- Worst: test-06 (Q=0.0, A=0.0)

---

## System-Wide Summary

- **Total Tasks**: 40
- **Total Passed**: 16/40 (40.0%)
- **System Avg Quality**: 5.15/10

### Final Verdict

⚠️ **MARGINAL**: System average quality (5.15) is below target (6.0) but shows improvement

Recommendation: Review scoring rules and template patterns for failing agents.

---

## Scoring System Notes

- **Quality Formula**: `quality = 0.6 * auto_score + 0.4 * human_score`
- **Human Score**: Currently null (defaults to 0)
- **Acceptance Threshold**: quality ≥ 6.0 for most agents
- **To Pass Without Human Scoring**: Requires auto_score ≥ 10.0

**Implication**: AutoChecks must achieve perfect 10/10 AutoScore to pass without human review.