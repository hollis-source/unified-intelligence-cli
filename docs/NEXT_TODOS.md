# Next Todos

Date: 2025-10-11
Source: priorities.yaml (P1/P2 focus)

- [P1.1] Build production Docker image for Project Builder (health checks, JSON logs)
- [P1.1] Write deployment manifests (systemd/K8s), secrets, and env config
- [P1.1] Provision PostgreSQL (schema + connection settings) and readiness probes
- [P1.2] Implement endpoint health monitor daemon with auto-wake for scale-to-zero
- [P1.2] Add alerting rules and a minimal Grafana dashboard panel
- [P1.3] Add OpenTelemetry tracing to CLI and orchestrator paths
- [P1.3] Wire cost/usage metrics export and error/perf profiling hooks
- [P2] Enable pytest-cov, set coverage gate to 90% in CI
- [P2] Add DSL runtime integration tests (examples/workflows/*)
- [TYPE] Integrate HM type inference into DSL interpreter; add failing tests first
