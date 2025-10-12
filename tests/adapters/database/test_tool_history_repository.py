"""
Unit tests for ToolHistoryRepository - Phase 2b.

Tests tool execution history tracking, audit trail, and metrics collection.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.adapters.database.tool_history_repository import ToolHistoryRepository


@pytest.fixture
def mock_session():
    """Mock requests.Session for testing."""
    session = Mock()
    session.auth = None
    session.headers = {}
    return session


@pytest.fixture
def mock_requests(mock_session):
    """Mock requests module."""
    with patch('src.adapters.database.tool_history_repository.requests') as mock_requests:
        mock_requests.Session.return_value = mock_session

        # Mock health check
        health_response = Mock()
        health_response.status_code = 200
        mock_session.get.return_value = health_response

        yield mock_requests, mock_session


def test_tool_history_repository_initialization(mock_requests):
    """Test ToolHistoryRepository initializes correctly."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository(
        host="localhost",
        port=8000,
        namespace="project_builder",
        database="production"
    )

    assert repo.host == "localhost"
    assert repo.port == 8000
    assert repo.namespace == "project_builder"
    assert repo.database == "production"
    assert repo.base_url == "http://localhost:8000"

    # Verify health check was called
    mock_sess.get.assert_called_once_with("http://localhost:8000/health")


def test_tool_history_repository_connection_failure():
    """Test ToolHistoryRepository raises ConnectionError on health check failure."""
    with patch('src.adapters.database.tool_history_repository.requests.Session') as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock failed health check
        health_response = Mock()
        health_response.status_code = 500
        mock_session.get.return_value = health_response

        with pytest.raises(ConnectionError, match="SurrealDB health check failed: 500"):
            ToolHistoryRepository()


def test_record_tool_execution(mock_requests):
    """Test recording a tool execution."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock successful POST response
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK", "result": {"id": "tool_executions:abc123"}}
    ]
    mock_sess.post.return_value = post_response

    # Record execution
    execution_id = repo.record_tool_execution(
        tool_name="bash",
        team_name="Testing",
        agent_role="testing-lead",
        parameters={"command": "pytest tests/"},
        result="5 passed",
        status="success",
        duration_ms=1234,
        session_id="session-123",
        task_description="Run test suite"
    )

    # Verify execution ID is a UUID string
    assert isinstance(execution_id, str)
    assert len(execution_id) == 36  # UUID length with hyphens

    # Verify POST was called
    mock_sess.post.assert_called_once()
    call_args = mock_sess.post.call_args
    assert call_args[0][0] == "http://localhost:8000/sql"

    # Verify query contains expected data
    query_data = call_args[1]["data"]
    assert "tool_executions:" in query_data
    assert "bash" in query_data
    assert "Testing" in query_data
    assert "testing-lead" in query_data


def test_record_tool_execution_truncates_result(mock_requests):
    """Test that large results are truncated to 1000 chars."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock successful POST response
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK", "result": {"id": "tool_executions:abc123"}}
    ]
    mock_sess.post.return_value = post_response

    # Create large result (2000 chars)
    large_result = "x" * 2000

    repo.record_tool_execution(
        tool_name="bash",
        team_name="Testing",
        agent_role="testing-lead",
        parameters={},
        result=large_result,
        status="success",
        duration_ms=100,
        session_id="session-123",
        task_description="Test"
    )

    # Verify query contains truncated result (1000 chars)
    call_args = mock_sess.post.call_args
    query_data = call_args[1]["data"]

    # Result should be truncated to 1000 chars
    assert large_result[:1000] in query_data
    assert large_result[1001:] not in query_data


def test_get_tool_history(mock_requests):
    """Test retrieving tool execution history."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock POST response with history data
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK"},  # USE NS
        {"status": "OK"},  # USE DB
        {
            "status": "OK",
            "result": [
                {
                    "tool_name": "bash",
                    "team_name": "Testing",
                    "status": "success",
                    "duration_ms": 1234
                },
                {
                    "tool_name": "read_file",
                    "team_name": "Testing",
                    "status": "success",
                    "duration_ms": 50
                }
            ]
        }
    ]
    mock_sess.post.return_value = post_response

    # Get history
    history = repo.get_tool_history(team_name="Testing", limit=100)

    assert len(history) == 2
    assert history[0]["tool_name"] == "bash"
    assert history[1]["tool_name"] == "read_file"

    # Verify query contains team filter
    call_args = mock_sess.post.call_args
    query_data = call_args[1]["data"]
    assert "team_name = 'Testing'" in query_data


def test_get_team_metrics(mock_requests):
    """Test retrieving team metrics."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock multiple POST responses for different queries
    responses = [
        # Total executions
        [{"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": [{"total": 100}]}],
        # Success count
        [{"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": [{"success_count": 90}]}],
        # Avg duration
        [{"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": [{"avg_duration": 1234.5}]}],
        # Tool distribution
        [{"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": [
            {"tool_name": "bash", "count": 60},
            {"tool_name": "read_file", "count": 40}
        ]}],
        # Recent failures
        [{"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": []}]
    ]

    mock_sess.post.side_effect = [
        Mock(status_code=200, json=lambda: resp) for resp in responses
    ]

    # Get metrics
    metrics = repo.get_team_metrics("Testing")

    assert metrics["team_name"] == "Testing"
    assert metrics["total_executions"] == 100
    assert metrics["success_rate"] == 0.9  # 90/100
    assert metrics["avg_duration_ms"] == 1234.5
    assert metrics["tool_distribution"] == {"bash": 60, "read_file": 40}
    assert metrics["most_used_tool"] == "bash"
    assert metrics["recent_failures"] == []


def test_get_team_metrics_no_executions(mock_requests):
    """Test team metrics with no executions returns zeros."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock empty responses
    empty_response = [
        {"status": "OK"}, {"status": "OK"}, {"status": "OK", "result": []}
    ]

    mock_sess.post.side_effect = [
        Mock(status_code=200, json=lambda: empty_response) for _ in range(5)
    ]

    metrics = repo.get_team_metrics("EmptyTeam")

    assert metrics["total_executions"] == 0
    assert metrics["success_rate"] == 0.0
    assert metrics["avg_duration_ms"] == 0.0
    assert metrics["tool_distribution"] == {}
    assert metrics["most_used_tool"] == "N/A"


def test_clear_history(mock_requests):
    """Test clearing tool execution history."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock DELETE response
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK"},
        {"status": "OK"},
        {"status": "OK", "result": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}  # 3 deleted records
    ]
    mock_sess.post.return_value = post_response

    # Clear history for specific team
    deleted_count = repo.clear_history(team_name="Testing")

    assert deleted_count == 3

    # Verify DELETE query
    call_args = mock_sess.post.call_args
    query_data = call_args[1]["data"]
    assert "DELETE FROM tool_executions" in query_data
    assert "team_name" in query_data


def test_execute_query_error_handling(mock_requests):
    """Test _execute_query handles SurrealDB errors."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock error response
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK"},
        {"status": "ERR", "result": "Query syntax error"}
    ]
    mock_sess.post.return_value = post_response

    # Execute query should raise RuntimeError
    with pytest.raises(RuntimeError, match="SurrealDB query error: Query syntax error"):
        repo._execute_query("SELECT * FROM invalid_table;")


def test_record_agent_execution(mock_requests):
    """Test recording an agent execution."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock successful POST response
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK", "result": {"id": "agent_executions:xyz789"}}
    ]
    mock_sess.post.return_value = post_response

    # Record agent execution
    execution_id = repo.record_agent_execution(
        agent_role="testing-lead",
        team_name="Testing",
        task_description="Run integration tests",
        session_id="session-123",
        tool_call_ids=["tool-1", "tool-2", "tool-3"],
        status="success"
    )

    # Verify execution ID is a UUID string
    assert isinstance(execution_id, str)
    assert len(execution_id) == 36

    # Verify POST was called
    mock_sess.post.assert_called_once()
    call_args = mock_sess.post.call_args
    query_data = call_args[1]["data"]

    # Verify query contains expected data
    assert "agent_executions:" in query_data
    assert "testing-lead" in query_data
    assert "Testing" in query_data
    assert "Run integration tests" in query_data


def test_get_policy_violations(mock_requests):
    """Test retrieving policy violations."""
    mock_req, mock_sess = mock_requests

    repo = ToolHistoryRepository()

    # Mock POST response with violations
    post_response = Mock()
    post_response.status_code = 200
    post_response.json.return_value = [
        {"status": "OK"},
        {"status": "OK"},
        {
            "status": "OK",
            "result": [
                {
                    "tool_name": "bash",
                    "team_name": "Frontend",
                    "status": "failure",
                    "result": "Error: tool 'bash' not allowed for team",
                    "timestamp": "2025-01-15T10:30:00Z"
                }
            ]
        }
    ]
    mock_sess.post.return_value = post_response

    # Get violations
    violations = repo.get_policy_violations(limit=50)

    assert len(violations) == 1
    assert violations[0]["tool_name"] == "bash"
    assert violations[0]["team_name"] == "Frontend"
    assert violations[0]["status"] == "failure"

    # Verify query filters by status="failure"
    call_args = mock_sess.post.call_args
    query_data = call_args[1]["data"]
    assert "status = 'failure'" in query_data
