# Task 2: Agent Performance Measurement System

**Model**: gpt5
**Duration**: 122s
**Timestamp**: 2025-10-16 03:36:56

---


## Agent Performance Measurement System

### Metrics Definition
| Metric | What it measures | How to compute (formula) | Collection source | Default target (Week 0 → Week 4+) |
|---|---|---|---|---|
| Task completion rate (%) | Percent of attempted tasks that meet acceptance criteria | completed_tasks / attempted_tasks * 100 | Automated tests + human acceptance | 20% → 80%+ |
| Output quality score (1–10) | Holistic quality based on rubric | 0.6*AutoChecks(0–10) + 0.4*Human(0–10) | Linters/tests/checkers + human rubric | 5.0 → 8.0+ |
| Latency p95 (s) | 95th percentile latency per agent | p95(latency_seconds across tasks) | Wall-clock timing | ≤120s → ≤60s |
| Cost per task (tokens) | Prompt + completion tokens | mean(tokens_prompt + tokens_completion) | Model usage metadata | ≤10k → ≤6k |
| Specificity (%) | Percent of responses with explicit code refs | count(outputs with file:line refs)/attempted * 100 | Regex on outputs | Python/Architect/Test/DevOps ≥70%; Research ≥40% |

Notes:
- completed_tasks: pass automated checks and (if required) human acceptance ≥ threshold.
- AutoChecks(0–10) is scaled per agent (see rubrics).
- p95: use numpy.percentile or custom quickselect percentile.
- file:line reference: e.g., src/app/foo.py:123 or path/to/file.ts:45.

### Scoring Rubrics
Anchor levels (used across all agents; map to 1, 4, 7, 9–10):
- 1: Wrong/missing, unsafe/broken, ignores instructions.
- 4: Partially correct, major gaps, low clarity, fails key checks.
- 7: Correct, complete, clear; passes checks; minor issues only.
- 9–10: Excellent, idiomatic, anticipates edge cases, high specificity, production-ready.

Agent-specific AutoChecks (0–10) components:
- Python Engineer
  - Lint/format pass (ruff/flake8/black): 0–2
  - Static typing (mypy/pyright) pass: 0–2
  - Tests pass on modified scope: 0–3
  - Complexity/duplication improvement: 0–2
  - Specificity (file:line, code excerpts): 0–1
- Software Architect
  - Clean Architecture alignment (layers/boundaries clear): 0–3
  - Artifacts present (C4: C, Ctx, Comp; ADRs): 0–2
  - Traceability (decisions ↔ requirements): 0–2
  - Feasibility (implementation-ready plan): 0–2
  - Specificity (repo/file anchors): 0–1
- Test Engineer
  - New/updated tests run green: 0–4
  - Coverage delta (+X% lines/branches): 0–3
  - Test quality (AAA, determinism, speed): 0–2
  - Specificity (targeted files, lines): 0–1
- DevOps Engineer
  - CI config validity (actionlint/yamllint): 0–3
  - Pipeline success on sample run/dry-run: 0–3
  - Idempotency/safety checks present: 0–2
  - Observability (logs/alerts): 0–1
  - Specificity (env/manifest refs): 0–1
- Research Analyst
  - Sources/citations quality (credible, diverse): 0–3
  - Synthesis/insight (not copy, actionable): 0–3
  - Structure (exec summary, plan, risks): 0–2
  - Verification (repro steps, data sanity): 0–1
  - Specificity (repo/code anchors where relevant): 0–1

Human evaluation (0–10) dimensions (2 points each):
- Correctness, Completeness, Clarity/Structure, Specificity/Actionability, Safety/Best Practices.

Acceptance threshold (counts as “completed”):
- Python/Test/DevOps: AutoChecks ≥6 and Human ≥6 (and required checks pass).
- Architect/Research: AutoChecks ≥5 and Human ≥7.

### Test Suite Design
Each agent has 20 concrete, real-world tasks. Keep tasks deterministic (pin versions, provide fixtures). Use a task YAML with:
- prompt
- inputs/artifacts (paths/fixtures)
- required checks (commands/regex expectations)
- human rubric dimensions to rate
- acceptance rules

Python Engineer (20)
1. Refactor utils/date.py to remove timezone bugs; add pytz-free approach.
2. Replace inheritance with composition in services/payment/processor.py.
3. Extract repository pattern from dao/*.py into repositories/.
4. Reduce cyclomatic complexity of handlers/order_handler.py <10.
5. Introduce dataclasses in models/customer.py; keep serialization stable.
6. Optimize JSON parsing in loaders/bulk_import.py (streaming).
7. Remove global state in config/settings.py; inject via factory.
8. Replace manual retries with tenacity in clients/http_client.py.
9. Convert synchronous I/O to asyncio in io/file_sync.py with tests.
10. Add type hints to api/v1/* and enforce mypy strict.
11. Replace custom logger with structlog; keep format compatibility.
12. Eliminate dead code in feature flags; add coverage to 90% in module.
13. Implement Strategy pattern for discount rules.
14. Introduce pydantic models for request validation.
15. Break monolithic function process_all() into cohesive units.
16. Memoize expensive pure function compute_score().
17. Replace regex parser with state machine for edge cases; keep API.
18. Enforce immutability where possible (frozen dataclasses).
19. Add context managers to manage resource lifecycles.
20. Fix flaky time-based tests with freezegun; isolate time source.

Software Architect (20)
1. Propose Clean Architecture restructuring for src/ with domain/app/infra.
2. C4 Context and Container diagrams for current system.
3. ADR: Choose Postgres over MySQL with constraints.
4. ADR: Async messaging vs synchronous REST for orders.
5. Boundaries for payments vs billing; anti-corruption layer plan.
6. Multi-tenancy strategy (schema vs row-level) with trade-offs.
7. Modular monolith plan before microservices; strangler pattern path.
8. Observability architecture (logs/metrics/traces) with SLIs/SLOs.
9. API gateway vs service mesh choice and rollout plan.
10. Identity/Access design (OIDC flows, roles, least privilege).
11. Data retention and GDPR delete strategy.
12. Feature flag governance and migration plan.
13. Caching layers (read-through/write-through) and invalidation.
14. Schema evolution and backward compatibility policy.
15. Tenant isolation threat model + mitigations.
16. Blue/green vs rolling deployments decision record.
17. Multi-region DR strategy with RPO/RTO targets.
18. Event versioning and schema registry.
19. Clean code ownership and boundaries for teams.
20. Tech roadmap Q1–Q2 with milestones linked to architecture changes.

Test Engineer (20)
1. Generate unit tests for utils/math.py with edge cases.
2. Add integration tests for order creation flow across services.
3. E2E test login → checkout happy path (headless).
4. Snapshot tests for templating in emails/*.j2.
5. Contract tests for payments client against mock server.
6. Add property-based tests for parser/tokenizer.
7. Test flaky retry logic with fake clock and backoff.
8. Coverage to 85% for module analytics/pipeline.py.
9. Mutant-kill tests using mutmut on core/validators.py.
10. Idempotency tests for task re-run.
11. Performance test for search endpoint p95<200ms locally.
12. Test DB migrations up/down on ephemeral DB.
13. Parameterized tests for locales in formatting.
14. Test concurrency issues with threaded runner.
15. Golden-file tests for CLI output stability.
16. Security tests for input validation on API.
17. Fixtures refactor to factory-boy for clarity.
18. E2E: password reset including email interception.
19. Smoke tests for health/metrics endpoints.
20. Test schema validation with jsonschema.

DevOps Engineer (20)
1. Create GitHub Actions CI with lint/test/cache.
2. Add actionlint and yamllint checks.
3. Build and push Docker image with proper tags.
4. Multi-stage Dockerfile for slim runtime.
5. Add Python cache and dependabot config.
6. Terraform plan for dev VPC (dry-run only).
7. Helm chart template lint for service.
8. Add OTel collector sidecar and traces exporting.
9. Canary deploy strategy manifest (no-op).
10. Rollback step documented and automated.
11. GitHub Environments with protection rules.
12. Slack notifications on failures.
13. Pre-commit hooks config for repo.
14. Versioning with SemVer release workflow.
15. SBOM generation via syft/cyclonedx.
16. SAST scan step (bandit, trivy).
17. Secrets scanning and prevention.
18. Matrix build for py versions.
19. Workload identity for CI → cloud.
20. Post-deploy smoke job gating promote.

Research Analyst (20)
1. Investigate library X: pros/cons, performance, licenses, pick.
2. Summarize RFC-xxxx and implications for our API.
3. Competitor analysis table and gaps.
4. Plan to migrate to Clean Architecture: phases, risks, owners.
5. Experiment design for caching strategy validation.
6. Literature review on test flakiness mitigation.
7. Monitoring tools comparison; recommend stack.
8. Doc: How to run repo locally (fresh laptop).
9. Onboarding guide for new devs (first week).
10. Risk register for Q1 projects with mitigations.
11. Data model glossary and shared language doc.
12. Retrospective analysis on incident INC-123.
13. Benchmark methodology for parser speed.
14. Migration plan from Travis → GitHub Actions.
15. Dataset curation protocol and QA steps.
16. Threat modeling for auth flows; STRIDE.
17. ADR: choose pre-commit hook set.
18. Proposal: reduce token cost per task by prompting.
19. Documentation IA overhaul outline.
20. Research plan for AI-assisted code reviews.

### Implementation Guide

Quick start (run today):
- Put your 100 tasks into tasks/<agent>/<id>.yaml (example format below).
- Run the harness to execute tasks, time them, and record metrics into metrics.jsonl.
- Optionally add human scores via a CSV, then aggregate and view p95/means.

Task YAML example (minimal):
````yaml mode=EXCERPT
id: py-01
agent: python
prompt: "Refactor utils/date.py to remove timezone bugs."
checks:
  - type: cmd; run: "pytest -q tests/utils/test_date.py"
  - type: lint; run: "ruff ."
accept: "all_checks_green AND human>=6"
````

Run a task via CLI (adapt template to your unified-intelligence-cli):
````python mode=EXCERPT
import os,subprocess,time,json,uuid
def run_task(agent,prompt):
  t0=time.time()
  p=subprocess.run([os.getenv("UICLI","uicli"),"run","--agent",agent],input=prompt,text=True,capture_output=True)
  lat=time.time()-t0; out=p.stdout; meta=json.loads(p.stderr or "{}")
  return {"ok":p.returncode==0,"lat":lat,"out":out,"usage":meta.get("usage",{})}
````

Compute p95 and token cost:
````python mode=EXCERPT
import numpy as np
def p95(xs): return float(np.percentile(xs,95)) if xs else 0.0
def tokens(u): return int(u.get("prompt_tokens",0)+u.get("completion_tokens",0))
def mean(xs): return sum(xs)/len(xs) if xs else 0.0
````

Detect specificity (file:line references):
````python mode=EXCERPT
import re
FILELINE=re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,6}:\d+")
def is_specific(txt): return bool(FILELINE.search(txt or ""))
````

Execute checks and aggregate per-task metrics:
````python mode=EXCERPT
import json,subprocess,datetime as dt
def run_check(cmd): return subprocess.run(cmd,shell=True).returncode==0
def record(res,agent,tid,prompt):
  rec={"ts":dt.datetime.utcnow().isoformat(),"agent":agent,"task":tid,**res}
  rec["specific"]=is_specific(res["out"]); rec["tokens"]=tokens(res["usage"])
  return rec
````

Write JSONL and weekly rollup:
````python mode=EXCERPT
import json,collections,statistics as st
def to_jsonl(path,recs): open(path,"a").write("\n".join(map(json.dumps,recs))+"\n")
def rollup(recs):
  by=collections.defaultdict(list)
  [by[(r["agent"])].append(r) for r in recs]
  return {a:{"rate":100*sum(x["ok"] for x in rs)/len(rs),
             "p95":p95([x["lat"] for x in rs]),
             "cost":mean([x["tokens"] for x in rs]),
             "spec":100*mean([x["specific"] for x in rs])} for a,rs in by.items()}
````

Human ratings CSV merge (columns: agent,task,human_score 0–10):
````python mode=EXCERPT
import csv
def merge_human(recs,csv_path):
  h={(r["agent"],r["task"]):float(r["human_score"]) for r in csv.DictReader(open(csv_path))}
  for r in recs: r["human"]=h.get((r["agent"],r["task"]),None)
  return recs
````

Compute quality score and completion decision:
````python mode=EXCERPT
def quality(res,auto,hum):
  auto10=min(max(auto,0),10); hum10=(hum if hum is not None else 0)
  return 0.6*auto10+0.4*hum10
def completed(agent,q,checks_ok):
  th={"python":(6,6),"test":(6,6),"devops":(6,6),"architect":(5,7),"research":(5,7)}
  at,ht=th.get(agent,(6,6))
  return checks_ok and q>=max(at,ht)
````

AutoChecks stubs (replace with your check runners):
````python mode=EXCERPT
def auto_checks(agent,task_dir="."):
  # Return 0–10 based on per-agent checks (lint/tests/etc.)
  # Example: ruff/mypy/pytest/actionlint/coverage deltas…
  return 7.0
````

Minimal CLI entry (batch run):
````python mode=EXCERPT
def run_suite(items):
  recs=[]
  for it in items:
    r=run_task(it["agent"],it["prompt"]); a=it["agent"]; tid=it["id"]
    checks_ok=all(run_check(c["run"]) for c in it.get("checks",[]))
    aq=auto_checks(a); rec=record(r,a,tid,it["prompt"]); rec["auto"]=aq
    rec["quality"]=quality(r,aq,rec.get("human"))
    rec["completed"]=completed(a,rec["quality"],checks_ok); recs.append(rec)
  return recs
````

JSONL record example (one line):
````json mode=EXCERPT
{"ts":"2025-10-16T12:00:00Z","agent":"python","task":"py-01","ok":true,"lat":42.1,"tokens":5632,"specific":true,"quality":7.8,"completed":true}
````

Regression testing (goldens via regex expectations):
````yaml mode=EXCERPT
task: py-15
expect:
  - "def process_part_\\w+\\("
  - "src/core/process.py:\\d+"
tolerance: "structure-only"
````

Next optimization target heuristic (impact/effort):
````python mode=EXCERPT
def next_target(roll):
  goals={"rate":80,"p95":60,"cost":6000,"spec":70}
  effort={"rate":3,"p95":2,"cost":2,"spec":1}
  gaps={k:max(0,goals[k]-v) if k!="p95" else max(0,v-goals[k]) for k,v in roll.items()}
  roi={k:(gaps[k]/max(effort[k],1)) for k in goals}
  return max(roi,key=roi.get)
````

### Dashboard Concept
Lightweight options you can use today:
- CSV/JSONL → Google Sheets/Data Studio for quick charts (completion rate, quality, p95).
- Streamlit/Panel for a minimal local dashboard.

Streamlit stub:
````python mode=EXCERPT
import streamlit as st,json
recs=[json.loads(l) for l in open("metrics.jsonl")]
st.metric("Completion %", f'{sum(r["completed"] for r in recs)/len(recs)*100:.1f}')
st.metric("p95 Latency (s)", f'{p95([r["lat"] for r in recs]):.1f}')
````

Week-over-week trend idea:
- Store dated files like runs/2025-10-16/metrics.jsonl.
- Weekly job aggregates by agent: completion %, mean quality, p95 latency, mean tokens, specificity %.
- Plot weekly line charts; annotate changes when prompts/templates/checks changed.

### Human Evaluation Protocol (fast, consistent)
- Sampling: Take 5 tasks per agent per week (stratified by difficulty).
- Blinded evaluation: Hide agent identity; show task, output, and acceptance criteria.
- 5 dimensions × 0–2 points each (see rubric); score independently; disagreements resolved by median.
- SLA: ≤48h turnaround; calibrate weekly with 3 shared examples.

### Automated Scoring Where Possible
- Python/Test: ruff, mypy/pyright, pytest, coverage.py delta, mutmut optional.
- DevOps: actionlint, yamllint, trivy/bandit (no network), dockerfilelint.
- Architect/Research: artifact presence (ADRs, diagrams in docs/), structure checks (headings), link validator; regex-based presence checks.

### Regression Testing (don’t break what works)
- Freeze tasks and their goldens/expectations.
- On agent/template updates, rerun the suite; fail build if:
  - Completion rate drops >5 pts, or
  - Any previously completed task fails acceptance.
- Allow guarded exceptions with ADR noting rationale.

### Metrics Tracking Approach
- Storage: Append-only metrics.jsonl per run; include agent, task id, timestamps, usage, checks, quality, completed.
- Aggregation: Daily/weekly rollups persisted to runs/YYYY-WW/rollup.json.
- Improvement trajectory: Display week-over-week deltas with sparkline or simple arrows.
- Next optimization target: Use next_target() to pick metric focus per agent; log rationale.

### Putting It In Motion Today
1. Create 100 YAML task files from the lists above (start with 10 per agent if time-limited).
2. Configure UICLI command template via env UICLI (e.g., uicli or unified-intelligence-cli).
3. Run the suite with run_suite(), write metrics.jsonl, merge human CSV if available.
4. Compute rollups and pick next_target per agent; share dashboard screenshot.

If you want me to, I can convert these into ready-to-run repo scripts (harness.py, tasks/, dashboard.py) and a minimal GitHub Action to run nightly.

