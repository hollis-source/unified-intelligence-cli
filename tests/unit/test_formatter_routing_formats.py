import json
from src.adapters.cli.result_formatter import ResultFormatter
from src.adapters.cli.claude_settings import ClaudeOutputSettings
from src.entity import ExecutionResult, ExecutionStatus


def make_res(output: str, metadata=None):
    return ExecutionResult(status=ExecutionStatus.SUCCESS, output=output, errors=[], metadata=metadata or {})


ROUTING = {"routing_path": {"domain": "backend", "team": "Backend", "agent": "py", "scores": [("backend", 3.0), ("qa", 1.0)]}}


def test_routing_human_only(capsys):
    s = ClaudeOutputSettings(verbosity='verbose', include_routing_trace=True)  # type: ignore
    s = ClaudeOutputSettings(verbosity='verbose', include_routing_trace=True, show_top3_domain_scores=True, routing_trace_format='human')  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("ok", metadata=ROUTING)
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "Route: backend" in out
    assert not any(line.strip().startswith('{') for line in out.splitlines())


def test_routing_json_only(capsys):
    s = ClaudeOutputSettings(verbosity='verbose', include_routing_trace=True, routing_trace_format='json')  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("ok", metadata=ROUTING)
    fmt.format_results([res])
    out = capsys.readouterr().out
    json_lines = [ln for ln in out.splitlines() if ln.strip().startswith('{')]
    assert len(json_lines) == 1
    obj = json.loads(json_lines[0])
    assert obj["routing_path"]["team"] == "Backend"


def test_routing_both(capsys):
    s = ClaudeOutputSettings(verbosity='verbose', include_routing_trace=True, routing_trace_format='both')  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("ok", metadata=ROUTING)
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "Route: backend" in out
    json_lines = [ln for ln in out.splitlines() if ln.strip().startswith('{')]
    assert len(json_lines) == 1

