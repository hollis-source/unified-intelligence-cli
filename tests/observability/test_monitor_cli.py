import re
from click.testing import CliRunner

from src.observability.monitor_cli import monitor


def test_monitor_cli_runs_and_stops_quickly():
    runner = CliRunner()
    result = runner.invoke(monitor, ["--duration", "0.1"])  # short run
    assert result.exit_code == 0
    # should print start and stop logs
    assert "Health server started" in result.output
    assert "Health server stopped" in result.output


def test_monitor_cli_accepts_ephemeral_port():
    runner = CliRunner()
    result = runner.invoke(monitor, ["--host", "127.0.0.1", "--port", "0", "--duration", "0.1"])
    assert result.exit_code == 0
    # should include an URL with discovered port
    assert "http://127.0.0.1:" in result.output
    # ensure a numeric port was printed
    ports = re.findall(r"http://127.0.0.1:(\d+)", result.output)
    assert any(int(p) > 0 for p in ports)

