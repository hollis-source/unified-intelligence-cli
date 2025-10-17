import json
from src.adapters.cli.result_formatter import ResultFormatter
from src.adapters.cli.claude_settings import ClaudeOutputSettings
from src.entity import ExecutionResult, ExecutionStatus


def make_res(output: str, metadata=None):
    return ExecutionResult(status=ExecutionStatus.SUCCESS, output=output, errors=[], metadata=metadata or {})


def test_quiet_mode_shows_status_only(capsys):
    s = ClaudeOutputSettings(verbosity='quiet')  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("Hello world", metadata={"routing_path": {"domain": "d", "team": "t", "agent": "a"}})
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "Hello world" not in out
    assert "Route:" not in out
    assert "Status:" in out


def test_normal_mode_hides_routing(capsys):
    s = ClaudeOutputSettings(verbosity='normal', include_routing_trace=True)  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("Hello world", metadata={"routing_path": {"domain": "d", "team": "t", "agent": "a"}})
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "Hello world" in out
    assert "Route:" not in out


def test_verbose_mode_shows_routing_with_scores(capsys):
    s = ClaudeOutputSettings(verbosity='verbose', include_routing_trace=True, show_top3_domain_scores=True)  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("ok", metadata={"routing_path": {"domain": "d", "team": "t", "agent": "a", "scores": [("d", 1.0)]}})
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "Route:" in out
    assert "top3=[('d', 1.0)]" in out


def test_truncation_respects_code_block_boundaries(capsys):
    body = "```python\nprint('x')\n```\nAFTER"
    s = ClaudeOutputSettings(verbosity='normal', max_chars=10, wrap_code_blocks='augment_code_snippet')  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res(body)
    fmt.format_results([res])
    out = capsys.readouterr().out
    # Must not cut inside augment block; should include closing tag then ellipsis
    assert "<augment_code_snippet" in out
    assert "</augment_code_snippet>" in out
    assert out.strip().endswith("…")


def test_inline_code_suppression(capsys):
    s = ClaudeOutputSettings(inline_code_allowed=False)  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("Inline: `code` snippet")
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "`code`" not in out
    assert "code" in out


def test_cache_annotation_footer(capsys):
    s = ClaudeOutputSettings(show_cache_annotations=True)  # type: ignore
    fmt = ResultFormatter(settings=s)
    res = make_res("ok", metadata={"cache_hit": True, "ttl": 5})
    fmt.format_results([res])
    out = capsys.readouterr().out
    assert "(cache: hit; ttl: 5s)" in out

