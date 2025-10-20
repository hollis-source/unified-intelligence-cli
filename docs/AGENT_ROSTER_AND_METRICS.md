# Agent Roster and Metrics Framework

**Philosophy:** Continuous improvement - Each agent starts at 20% baseline, improves weekly to 80%+

**Date:** 2025-10-16
**Status:** Current agent lineup

---

## 5 Specialist Agents

### 1. Python Engineer
**Focus:** Code quality, refactoring, design patterns

**Capabilities:**
- Refactoring for Clean Code principles
- Design pattern implementation
- Type hints and static analysis
- Complexity reduction
- Code smell detection and remediation

**Metrics Targets:**
- Completion rate: 20% → 80%+
- Quality score: 5.0 → 8.0+
- Latency p95: ≤120s → ≤60s
- Cost per task: ≤10k → ≤6k tokens
- Specificity: ≥70% (with file:line references)

---

### 2. Software Architect
**Focus:** System design, Clean Architecture, ADRs

**Capabilities:**
- Clean Architecture restructuring
- C4 diagrams (Context, Container, Component, Code)
- Architecture Decision Records (ADRs)
- Boundary definition and anti-corruption layers
- Multi-tenancy, observability, scalability design

**Metrics Targets:**
- Completion rate: 20% → 80%+
- Quality score: 5.0 → 8.0+
- Latency p95: ≤120s → ≤60s
- Cost per task: ≤10k → ≤6k tokens
- Specificity: ≥70% (with architecture artifacts)

---

### 3. Test Engineer
**Focus:** Unit, integration, E2E test generation

**Capabilities:**
- Unit test generation with edge cases
- Integration test flows
- E2E test automation
- Property-based testing
- Contract testing
- Test coverage improvement
- Mutation testing

**Metrics Targets:**
- Completion rate: 20% → 80%+
- Quality score: 5.0 → 8.0+
- Latency p95: ≤120s → ≤60s
- Cost per task: ≤10k → ≤6k tokens
- Specificity: ≥70% (with test file references)

---

### 4. Database Specialist
**Focus:** Schema design, query optimization, migrations, data modeling

**Capabilities:**
- Database schema design (normalization, indexes)
- Query optimization and performance tuning
- Migration strategy and versioning
- Data modeling (ER diagrams, domain models)
- Database selection (SQL vs NoSQL)
- Connection pooling and transaction management
- Partitioning and sharding strategies
- Backup and recovery planning

**Metrics Targets:**
- Completion rate: 20% → 80%+
- Quality score: 5.0 → 8.0+
- Latency p95: ≤120s → ≤60s
- Cost per task: ≤10k → ≤6k tokens
- Specificity: ≥70% (with schema/query references)

**AutoChecks (0-10) Components:**
- Schema validity (SQLFluff, dbdiagram validation): 0-3
- Query performance (EXPLAIN ANALYZE analysis): 0-2
- Migration safety (up/down reversibility, no data loss): 0-2
- Normalization correctness (3NF+ compliance): 0-2
- Specificity (table/column/query references): 0-1

---

### 5. DevOps Engineer
**Focus:** CI/CD, deployment, monitoring, infrastructure

**Capabilities:**
- GitHub Actions / GitLab CI pipelines
- Docker containerization
- Kubernetes deployment
- Infrastructure as Code (Terraform, Helm)
- Monitoring and observability (logs, metrics, traces)
- Security scanning (SAST, SBOM, secrets)
- Deployment strategies (canary, blue/green)

**Metrics Targets:**
- Completion rate: 20% → 80%+
- Quality score: 5.0 → 8.0+
- Latency p95: ≤120s → ≤60s
- Cost per task: ≤10k → ≤6k tokens
- Specificity: ≥70% (with config file references)

---

## Common Metrics Framework

All agents tracked on 5 core metrics:

| Metric | Formula | Collection | Target (Week 0 → Week 4+) |
|--------|---------|------------|---------------------------|
| **Task Completion Rate (%)** | (completed_tasks / attempted_tasks) × 100 | Automated tests + human acceptance | 20% → 80%+ |
| **Output Quality Score (1-10)** | 0.6 × AutoChecks + 0.4 × Human | Linters/tests + rubric | 5.0 → 8.0+ |
| **Latency P95 (seconds)** | 95th percentile of response times | Wall-clock timing | ≤120s → ≤60s |
| **Cost per Task (tokens)** | mean(prompt_tokens + completion_tokens) | Model usage API | ≤10k → ≤6k |
| **Specificity (%)** | (responses with file:line refs / total) × 100 | Regex pattern matching | ≥70% (code), ≥40% (research) |

---

## Test Suite Design (100 Tasks)

Each agent has 20 concrete, deterministic tasks.

### Python Engineer (20 tasks)

1. Refactor utils/date.py to remove timezone bugs; add pytz-free approach
2. Replace inheritance with composition in services/payment/processor.py
3. Extract repository pattern from dao/*.py into repositories/
4. Reduce cyclomatic complexity of handlers/order_handler.py to <10
5. Introduce dataclasses in models/customer.py; keep serialization stable
6. Optimize JSON parsing in loaders/bulk_import.py (streaming)
7. Remove global state in config/settings.py; inject via factory
8. Replace manual retries with tenacity in clients/http_client.py
9. Convert synchronous I/O to asyncio in io/file_sync.py with tests
10. Add type hints to api/v1/* and enforce mypy strict
11. Replace custom logger with structlog; keep format compatibility
12. Eliminate dead code in feature flags; add coverage to 90% in module
13. Implement Strategy pattern for discount rules
14. Introduce pydantic models for request validation
15. Break monolithic function process_all() into cohesive units
16. Memoize expensive pure function compute_score()
17. Replace regex parser with state machine for edge cases; keep API
18. Enforce immutability where possible (frozen dataclasses)
19. Add context managers to manage resource lifecycles
20. Fix flaky time-based tests with freezegun; isolate time source

### Software Architect (20 tasks)

1. Propose Clean Architecture restructuring for src/ with domain/app/infra
2. C4 Context and Container diagrams for current system
3. ADR: Choose Postgres over MySQL with constraints
4. ADR: Async messaging vs synchronous REST for orders
5. Boundaries for payments vs billing; anti-corruption layer plan
6. Multi-tenancy strategy (schema vs row-level) with trade-offs
7. Modular monolith plan before microservices; strangler pattern path
8. Observability architecture (logs/metrics/traces) with SLIs/SLOs
9. API gateway vs service mesh choice and rollout plan
10. Identity/Access design (OIDC flows, roles, least privilege)
11. Data retention and GDPR delete strategy
12. Feature flag governance and migration plan
13. Caching layers (read-through/write-through) and invalidation
14. Schema evolution and backward compatibility policy
15. Tenant isolation threat model + mitigations
16. Blue/green vs rolling deployments decision record
17. Multi-region DR strategy with RPO/RTO targets
18. Event versioning and schema registry
19. Clean code ownership and boundaries for teams
20. Tech roadmap Q1-Q2 with milestones linked to architecture changes

### Test Engineer (20 tasks)

1. Generate unit tests for utils/math.py with edge cases
2. Add integration tests for order creation flow across services
3. E2E test login → checkout happy path (headless)
4. Snapshot tests for templating in emails/*.j2
5. Contract tests for payments client against mock server
6. Add property-based tests for parser/tokenizer
7. Test flaky retry logic with fake clock and backoff
8. Coverage to 85% for module analytics/pipeline.py
9. Mutant-kill tests using mutmut on core/validators.py
10. Idempotency tests for task re-run
11. Performance test for search endpoint p95<200ms locally
12. Test DB migrations up/down on ephemeral DB
13. Parameterized tests for locales in formatting
14. Test concurrency issues with threaded runner
15. Golden-file tests for CLI output stability
16. Security tests for input validation on API
17. Fixtures refactor to factory-boy for clarity
18. E2E: password reset including email interception
19. Smoke tests for health/metrics endpoints
20. Test schema validation with jsonschema

### Database Specialist (20 tasks)

**Traditional Database (PostgreSQL) - Tasks 1-10:**
1. Design normalized schema for multi-tenant SaaS with tenant isolation
2. Optimize slow query on orders table (EXPLAIN ANALYZE → index strategy)
3. Create migration to add soft-delete without downtime (dual-write pattern)
4. Design partition strategy for time-series events table (1B+ rows)
5. Model many-to-many relationship between users and roles with audit trail
6. Choose database for analytics workload (Postgres vs Clickhouse vs BigQuery)
7. Design connection pooling strategy for Django app (pgbouncer configuration)
8. Optimize JOIN query to reduce from 5s to <100ms (composite indexes)
9. Schema migration for adding NOT NULL constraint safely (backfill strategy)
10. Design sharding key for horizontal scaling (consistent hashing analysis)

**RAG/SurrealDB/Vector Embeddings - Tasks 11-20:**
11. Design SurrealDB schema for RAG codebase indexing (entities, embeddings, relationships)
12. Optimize vector similarity search query performance (800ms → <100ms target)
13. Fix SurrealDB result unwrapping bug causing 57% RAG failure rate (ACTUAL BUG!)
14. Design embedding storage strategy for multi-model RAG (768, 1536, 3072 dims)
15. Implement hybrid search combining vector similarity and metadata filtering
16. Design SurrealDB connection pooling for async RAG (fix WebSocket timeout issue)
17. Analyze and optimize embedding dimensionality (storage vs accuracy trade-offs)
18. Optimize RAG context window retrieval (dynamic k selection, MMR re-ranking)
19. Implement incremental RAG index updates without full re-indexing
20. Design SurrealDB monitoring and observability for RAG system (Prometheus/Grafana)

### DevOps Engineer (20 tasks)

1. Create GitHub Actions CI with lint/test/cache
2. Add actionlint and yamllint checks
3. Build and push Docker image with proper tags
4. Multi-stage Dockerfile for slim runtime
5. Add Python cache and dependabot config
6. Terraform plan for dev VPC (dry-run only)
7. Helm chart template lint for service
8. Add OTel collector sidecar and traces exporting
9. Canary deploy strategy manifest (no-op)
10. Rollback step documented and automated
11. GitHub Environments with protection rules
12. Slack notifications on failures
13. Pre-commit hooks config for repo
14. Versioning with SemVer release workflow
15. SBOM generation via syft/cyclonedx
16. SAST scan step (bandit, trivy)
17. Secrets scanning and prevention
18. Matrix build for Python versions
19. Workload identity for CI → cloud
20. Post-deploy smoke job gating promote

---

## Scoring Rubrics

### Common Anchor Levels (1, 4, 7, 9-10)

- **1:** Wrong/missing, unsafe/broken, ignores instructions
- **4:** Partially correct, major gaps, low clarity, fails key checks
- **7:** Correct, complete, clear; passes checks; minor issues only
- **9-10:** Excellent, idiomatic, anticipates edge cases, high specificity

### Agent-Specific AutoChecks (0-10)

**Python Engineer:**
- Lint/format pass (ruff/flake8/black): 0-2
- Static typing (mypy/pyright) pass: 0-2
- Tests pass on modified scope: 0-3
- Complexity/duplication improvement: 0-2
- Specificity (file:line, code excerpts): 0-1

**Software Architect:**
- Clean Architecture alignment (layers/boundaries): 0-3
- Artifacts present (C4/ADRs): 0-2
- Traceability (decisions ↔ requirements): 0-2
- Feasibility (implementation-ready): 0-2
- Specificity (repo/file anchors): 0-1

**Test Engineer:**
- New/updated tests run green: 0-4
- Coverage delta (+X% lines/branches): 0-3
- Test quality (AAA, determinism, speed): 0-2
- Specificity (targeted files, lines): 0-1

**Database Specialist:**
- Schema validity (SQLFluff, dbdiagram): 0-3
- Query performance (EXPLAIN ANALYZE): 0-2
- Migration safety (reversible, no data loss): 0-2
- Normalization (3NF+ compliance): 0-2
- Specificity (table/column/query refs): 0-1

**DevOps Engineer:**
- CI config validity (actionlint/yamllint): 0-3
- Pipeline success (sample run/dry-run): 0-3
- Idempotency/safety checks: 0-2
- Observability (logs/alerts): 0-1
- Specificity (env/manifest refs): 0-1

### Human Evaluation (0-10)

5 dimensions × 2 points each:
1. **Correctness** - Factually accurate, solves the problem
2. **Completeness** - Addresses all requirements, no gaps
3. **Clarity/Structure** - Well-organized, easy to understand
4. **Specificity/Actionability** - Concrete, with file:line references
5. **Safety/Best Practices** - Follows conventions, avoids anti-patterns

### Acceptance Thresholds

**Counts as "completed" task:**
- **Python/Test/DevOps/Database:** AutoChecks ≥6 AND Human ≥6 (and required checks pass)
- **Architect:** AutoChecks ≥5 AND Human ≥7

---

## Implementation Roadmap

### Week 1: Baseline (20% functionality)

**Goal:** Get all 5 agents responding to tasks with 20% completion rate

**Tasks:**
1. Create 10 tasks per agent (50 total) in YAML format
2. Implement basic agent prompts (simple, no complex orchestration)
3. Run first metrics collection
4. Establish baseline: completion rate, quality, latency, cost, specificity

**Success Criteria:**
- All 5 agents can execute tasks
- Metrics harness running
- Baseline data collected

### Week 2: First Iteration (40% functionality)

**Goal:** Improve based on Week 1 data

**Tasks:**
1. Identify lowest-performing agents (by completion rate)
2. Improve prompts based on failure modes
3. Add 10 more tasks per agent (100 total)
4. Re-measure and compare week-over-week

**Success Criteria:**
- ≥1 agent reaches 40% completion rate
- Quality scores improve by +1.0 on average
- Clear improvement trajectory visible

### Week 3: Measure and Evaluate (60% functionality)

**Goal:** Data-driven decision on adding complexity

**Tasks:**
1. Run full 100-task suite
2. Analyze where agents struggle (need RAG? need persistence?)
3. Document findings
4. Decide: Add LangGraph? Add RAG? Keep iterating simple approach?

**Decision Point:**
- IF workflows take >2 hours: Consider LangGraph adapter (persistence)
- IF specificity <70%: Consider RAG (codebase context)
- OTHERWISE: Keep iterating to 80%+

---

## Next Optimization Target Heuristic

```python
def next_target(rollup):
    goals = {"rate": 80, "p95": 60, "cost": 6000, "spec": 70}
    effort = {"rate": 3, "p95": 2, "cost": 2, "spec": 1}

    gaps = {
        k: max(0, goals[k] - v) if k != "p95" else max(0, v - goals[k])
        for k, v in rollup.items()
    }

    roi = {k: (gaps[k] / max(effort[k], 1)) for k in goals}

    return max(roi, key=roi.get)
```

**ROI Formula:** (Gap to goal) / (Effort to improve)

**Example:**
- Completion rate: 30% (gap: 50, effort: 3, ROI: 16.7)
- Quality: 6.0 (gap: 2.0, effort: 3, ROI: 0.67)
- Latency p95: 90s (gap: 30, effort: 2, ROI: 15.0)
- Cost: 8000 tokens (gap: 2000, effort: 2, ROI: 1000)
- Specificity: 50% (gap: 20, effort: 1, ROI: 20.0)

**Next target:** Specificity (highest ROI: 20.0)

---

## Current Status

| Agent | Current | Target (Week 4) | Status |
|-------|---------|-----------------|--------|
| Python Engineer | 0% | 40% | Not yet implemented |
| Software Architect | 0% | 40% | Not yet implemented |
| Test Engineer | 0% | 40% | Not yet implemented |
| Database Specialist | 0% | 40% | Not yet implemented |
| DevOps Engineer | 0% | 40% | Not yet implemented |

**Next immediate action:** Implement metrics harness and create first 50 tasks
