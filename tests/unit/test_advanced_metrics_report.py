from scripts.advanced_metrics_report import (
    RoutingDecision, ExecLog, summarize, _role_to_domain_heuristic,
)


def test_role_to_domain_heuristic():
    assert _role_to_domain_heuristic("backend-specialist-A") == "backend"
    assert _role_to_domain_heuristic("QA-Engineer") == "qa"
    assert _role_to_domain_heuristic("Researcher") == "research"
    assert _role_to_domain_heuristic("unknown") is None


def test_summarize_basic_drift_and_xfer():
    # Build synthetic decisions: first window all success, second half all fail (drift -1.0)
    decisions = [
        RoutingDecision(task_domain="backend", routing_strategy="baseline", success=True, metadata={})
        for _ in range(5)
    ] + [
        RoutingDecision(task_domain="backend", routing_strategy="rag", success=False, metadata={"rag_used": True, "top_patterns": [{"agent": "frontend-specialist"}]})
        for _ in range(5)
    ]

    execs = [
        ExecLog(task_domain="backend", agent_role="backend-specialist-A", success=True, latency_seconds=1.0),
        ExecLog(task_domain="backend", agent_role="backend-specialist-A", success=False, latency_seconds=2.0),
    ]
    agent_perf_rows = [
        {"agent_role": "backend-specialist-A", "success_rate": 0.75, "avg_latency_ms": 1200, "total_tasks": 12}
    ]

    report = summarize(decisions, execs, agent_perf_rows)

    # Drift should show a negative diff for backend
    drift = report["drift"]
    assert "backend" in drift["diffs"]
    assert drift["diffs"]["backend"] < 0

    # Cross-domain transfer picks up mismatch: task backend vs top pattern frontend
    xfer = report["cross_domain_transfer"]
    assert xfer["sample"] >= 1
    assert xfer["cross_rate"] > 0

