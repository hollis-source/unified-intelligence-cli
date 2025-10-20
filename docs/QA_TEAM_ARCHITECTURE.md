# QA Team Architecture

**Date:** 2025-10-16
**Status:** Implemented - Separate QA Team for user acceptance and feature validation

---

## Executive Summary

Created a **separate QA Team** distinct from the **Testing Team** to better reflect real-world organizational structure and responsibilities.

**Key Change:**
- **Testing Team** → Technical testing (unit, integration, E2E, performance)
- **QA Team** → Product quality, user acceptance, feature validation

---

## Architecture Overview

### Tier 1: Strategic Leadership (2 agents)

**master-orchestrator**
- High-level planning and coordination
- Task decomposition and resource allocation
- Cross-domain orchestration

**architecture-lead** (renamed from "qa-lead")
- Code quality and architecture review
- SOLID principles, Clean Code enforcement
- Technical debt assessment
- **Clarification:** Focus on *code* quality, not *product* quality

### Tier 2: Domain Leads (6 agents)

1. **frontend-lead** - UI/UX, client-side development
2. **backend-lead** - Server-side, APIs, databases
3. **testing-lead** - Technical testing strategy
4. **qa-lead** - **Product quality** and user acceptance (NEW)
5. **research-lead** - Documentation and research
6. **devops-lead** - Infrastructure and deployment

### Tier 3: QA Specialists (under qa-lead)

#### 1. qa-engineer
**Focus:** Automated acceptance testing and BDD

**Capabilities:**
- User acceptance testing (UAT)
- Feature validation and verification
- Requirements validation
- BDD (Cucumber, Behave, Gherkin)
- Given/When/Then scenarios
- User journeys and flows
- Acceptance criteria validation

**Example Tasks:**
- "Write BDD scenarios for login feature"
- "Validate checkout flow meets acceptance criteria"
- "Create user journey tests for onboarding"

---

#### 2. exploratory-test-engineer
**Focus:** Manual exploratory testing and usability

**Capabilities:**
- Exploratory testing
- Ad hoc testing
- Manual verification
- Bug hunting
- Edge and corner case discovery
- Usability testing

**Example Tasks:**
- "Perform exploratory testing on new dashboard"
- "Find edge cases in payment processing"
- "Manual usability test for mobile app"

---

#### 3. test-case-designer
**Focus:** Test planning and scenario design

**Capabilities:**
- Test case design
- Test scenario creation
- Test planning and strategy
- Test coverage analysis
- Requirement coverage mapping
- Test data design

**Example Tasks:**
- "Design test cases for API rate limiting"
- "Create test plan for v2.0 release"
- "Map requirements to test coverage"

---

## QA Team vs Testing Team

### Clear Separation of Concerns

| Aspect | **Testing Team** | **QA Team** |
|--------|------------------|-------------|
| **Focus** | Technical correctness | User/product quality |
| **Perspective** | Developer/system | End-user/product |
| **Activities** | Code-level testing | Feature validation |
| **Automation** | 95% automated | Mix of automated/manual |
| **When** | During development | Before release |
| **Goal** | "Does it work correctly?" | "Does it meet expectations?" |

### Testing Team (testing-lead)

**Agents:**
- unit-test-engineer (pytest, jest, mocking)
- integration-test-engineer (E2E, API tests, Cypress)
- performance-testing-specialist
- security-testing-specialist
- load-testing-specialist

**Focus:**
- Unit tests for functions/classes
- Integration tests for system components
- Performance benchmarks
- Security scans
- Test automation infrastructure

**Example Tasks:**
- "Write unit tests for UserService class"
- "Create integration tests for payment API"
- "Run load tests for 10K concurrent users"

---

### QA Team (qa-lead)

**Agents:**
- qa-engineer (acceptance testing, BDD)
- exploratory-test-engineer (manual, exploratory)
- test-case-designer (test planning, scenarios)

**Focus:**
- Acceptance criteria verification
- Feature meets user expectations
- User journey validation
- Exploratory testing
- Test planning strategy

**Example Tasks:**
- "Validate login feature meets acceptance criteria"
- "Perform exploratory testing on checkout flow"
- "Design test scenarios for mobile onboarding"

---

## Routing Strategy

### QA Team Routing Keywords

Tasks containing these keywords route to **qa-lead**:

**Primary (high confidence):**
- "acceptance", "acceptance testing", "uat"
- "user acceptance", "feature validation"
- "acceptance criteria", "story validation"
- "bdd", "gherkin", "cucumber", "behave"
- "given when then", "scenario", "feature file"

**Secondary (moderate confidence):**
- "exploratory testing", "manual testing"
- "user journey", "user flow", "user scenario"
- "test plan", "test case design"
- "requirements validation", "requirements testing"

**Tertiary (low confidence):**
- "qa", "quality assurance" (may conflict with architecture-lead)
- "feature testing", "feature verification"

### Testing Team Routing Keywords

Tasks containing these keywords route to **testing-lead**:

**Primary:**
- "unit test", "unittest", "unit testing"
- "integration test", "e2e", "end-to-end"
- "performance test", "load test", "stress test"
- "security test", "penetration test"
- "pytest", "jest", "mocha", "cypress", "selenium"

**Fallback:**
- Generic "test", "testing", "validate", "verify" (routes to integration-test-engineer)

---

## Team Internal Routing Logic

### QA Team Internal Routing

**qa-lead delegates to:**

1. **qa-engineer** if task mentions:
   - "acceptance", "uat", "acceptance criteria"
   - "bdd", "gherkin", "cucumber", "scenario"
   - "user journey", "user flow"
   - "feature validation"

2. **exploratory-test-engineer** if task mentions:
   - "exploratory", "manual testing"
   - "usability", "user experience testing"
   - "bug hunting", "edge cases"

3. **test-case-designer** if task mentions:
   - "test case", "test plan", "test strategy"
   - "test coverage", "scenario design"
   - "test data"

**Default:** qa-engineer (most common use case)

---

## Benefits of Separate QA Team

### 1. Clear Responsibility Boundaries

**Before:**
- "Quality" was ambiguous (code quality vs product quality)
- Testing Team handled both technical and acceptance testing
- No clear owner for user-perspective validation

**After:**
- architecture-lead owns code quality
- qa-lead owns product quality
- Clear escalation path for user-facing issues

---

### 2. Mirrors Real Organizations

Most software companies have separate teams:

```
Engineering Organization
├── Development Team (backend-lead, frontend-lead)
├── Testing Team (automation, unit, integration)
├── QA Team (acceptance, manual, exploratory)
└── DevOps Team (infrastructure, deployment)
```

Our agent architecture now reflects this structure.

---

### 3. Enables Role Specialization

**Testing Engineers:**
- Deep technical testing expertise
- Test automation frameworks
- Performance and security tools
- CI/CD integration

**QA Engineers:**
- User perspective and empathy
- Business requirement understanding
- Exploratory testing skills
- Manual verification techniques

Different skill sets, different career paths.

---

### 4. Better Task Routing

**Before:**
```
"Write acceptance tests for login feature"
  → Ambiguous: testing-lead or qa-lead?
  → Both had "testing" in capabilities
```

**After:**
```
"Write acceptance tests for login feature"
  → Clear: qa-lead (has "acceptance testing" capability)
  → qa-lead routes to qa-engineer (BDD specialist)
```

---

### 5. Scalability

As organization grows:

**Testing Team can add:**
- chaos-engineering-specialist
- mutation-testing-specialist
- contract-testing-specialist

**QA Team can add:**
- regression-test-engineer
- smoke-test-engineer
- beta-test-coordinator

Independent growth without overlap.

---

## Implementation Details

### Files Modified

**src/factories/agent_factory.py**
- Line 124-139: Renamed "qa-lead" → "architecture-lead" (Tier 1)
- Line 440-461: Added new "qa-lead" (Tier 2)
- Line 551-606: Updated qa-engineer, added exploratory-test-engineer, test-case-designer (Tier 3)

### Agent Count

**Before:** 11 agents (5 at Tier 3)
**After:** 14 agents (8 at Tier 3)

**New Tier 2 lead:** qa-lead
**New Tier 3 agents:** exploratory-test-engineer, test-case-designer

---

## Example Task Routing

### Scenario 1: Acceptance Testing

**Task:** "Write BDD scenarios for user registration feature"

**Routing:**
1. Domain classifier detects "bdd scenarios" → qa domain
2. Routes to **qa-lead**
3. qa-lead sees "bdd" keyword → routes to **qa-engineer**
4. qa-engineer generates Cucumber/Gherkin scenarios

---

### Scenario 2: Exploratory Testing

**Task:** "Perform exploratory testing on new dashboard to find edge cases"

**Routing:**
1. Domain classifier detects "exploratory testing" → qa domain
2. Routes to **qa-lead**
3. qa-lead sees "exploratory" keyword → routes to **exploratory-test-engineer**
4. exploratory-test-engineer performs manual testing and documents findings

---

### Scenario 3: Test Planning

**Task:** "Create comprehensive test plan for v2.0 release"

**Routing:**
1. Domain classifier detects "test plan" → qa domain
2. Routes to **qa-lead**
3. qa-lead sees "test plan" keyword → routes to **test-case-designer**
4. test-case-designer creates test strategy document with coverage matrix

---

### Scenario 4: Unit Testing (NOT QA)

**Task:** "Write unit tests for PaymentService class"

**Routing:**
1. Domain classifier detects "unit tests" → testing domain
2. Routes to **testing-lead**
3. testing-lead sees "unit" keyword → routes to **unit-test-engineer**
4. unit-test-engineer writes pytest tests

**Note:** Does NOT route to QA Team because "unit testing" is technical, not user-facing.

---

## Next Steps

### Phase 1: Routing Implementation (Current)
- ✅ Add QA Team to agent factory
- ⬜ Update domain classifier with "qa" domain
- ⬜ Update team router to recognize qa-lead
- ⬜ Test routing with sample tasks

### Phase 2: Prompt Engineering
- ⬜ Create qa-engineer prompts (BDD focus, file:line enforcement)
- ⬜ Create exploratory-test-engineer prompts (bug reporting format)
- ⬜ Create test-case-designer prompts (test plan templates)

### Phase 3: Validation
- ⬜ Create 10 QA test tasks (acceptance, exploratory, planning)
- ⬜ Run validation to measure specificity and quality
- ⬜ Compare QA team vs Testing team routing accuracy

### Phase 4: Integration
- ⬜ Add QA tasks to existing task library (tasks/qa/)
- ⬜ Update metrics harness to track QA team performance
- ⬜ Document QA team workflows in CLAUDE.md

---

## Critique

### What Works ✅

1. **Clear separation:** Testing (technical) vs QA (user/product)
2. **Matches industry structure:** Most companies have separate testing and QA
3. **Enables specialization:** Different skills, different agents
4. **Better routing:** Keywords like "acceptance" clearly map to QA

### What Needs Validation ⚠️

1. **Keyword overlap:** "qa" and "quality assurance" appear in both architecture-lead and qa-lead
   - **Risk:** Misrouting tasks
   - **Mitigation:** Use weight-based routing (architecture-lead for "code quality", qa-lead for "acceptance")

2. **Team size imbalance:** QA Team (3 agents) vs Testing Team (2 agents)
   - **Risk:** QA may be underutilized if most tasks are technical tests
   - **Mitigation:** Monitor routing metrics, add/remove agents as needed

3. **Manual testing challenges:** exploratory-test-engineer does manual testing, but we're in automated CLI
   - **Risk:** Can't actually perform manual clicks, only generate test plans
   - **Mitigation:** Frame as "design exploratory test scenarios" rather than "perform manual tests"

### Assumptions 🤔

1. **Assumption:** User tasks will include acceptance testing requests
   - **Reality:** Need to validate with actual user requests
   - **Test:** Run 20-task validation with QA-focused tasks

2. **Assumption:** BDD scenarios are high-value outputs
   - **Reality:** Depends on whether user uses BDD frameworks
   - **Test:** Survey user workflows (Cucumber? Behave? pytest-bdd?)

3. **Assumption:** Separate QA lead is necessary
   - **Reality:** Could qa-engineer report to testing-lead instead
   - **Trade-off:** Separate lead enables independence but adds complexity

---

## Recommendations

### Short-Term (Immediate)
1. Update domain classifier to recognize "qa" domain
2. Test routing with 5-10 sample tasks
3. Verify no regressions in existing testing-team routing

### Medium-Term (Next Week)
1. Create QA agent prompts with file:line enforcement
2. Run 20-task validation comparing QA vs Testing routing
3. Measure QA team specificity (target: 75%+)

### Long-Term (Next Month)
1. Add more QA specialists if demand is high (smoke-test, regression-test)
2. Consider merging QA and Testing under single "Quality" lead if overlap is too high
3. Collect user feedback on acceptance testing outputs

---

**Architecture Status:** Implemented ✅
**Routing Status:** Pending ⬜
**Validation Status:** Pending ⬜

**Next Action:** Update domain classifier and team router to recognize QA Team
