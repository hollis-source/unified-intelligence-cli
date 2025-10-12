"""SurrealDB repository for tool execution history and audit trail.

Phase 2b: Tool-use history tracking with team-based metrics
Provides persistence for tool executions, agent executions, and team metrics.

Clean Architecture: Adapter layer (infrastructure concern)
SOLID: Single responsibility - tool history persistence

Schema:
    tool_executions table:
        - id: tool_executions:{uuid}
        - tool_name: str (e.g., "bash", "read_file")
        - team_name: str (e.g., "Testing", "Frontend")
        - agent_role: str (e.g., "testing-lead")
        - parameters: dict (tool input parameters)
        - result: str (tool execution result)
        - status: str ("success", "failure")
        - timestamp: datetime
        - duration_ms: int (execution time in milliseconds)
        - session_id: str (execution context session ID)
        - task_description: str (first 100 chars of task)

    agent_executions table:
        - id: agent_executions:{uuid}
        - agent_role: str
        - team_name: str
        - task_description: str
        - session_id: str
        - timestamp: datetime
        - tool_calls: list[str] (IDs of tool_executions)
        - status: str ("success", "failure")

Benefits:
    - Full audit trail of all tool accesses
    - Team-based metrics for optimization
    - Security: Track policy violations and access patterns
    - Performance: Identify slow tool executions
    - Debugging: Replay tool execution sequences
"""

import requests
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime


class ToolHistoryRepository:
    """SurrealDB-based repository for tool execution history.

    Tracks all tool executions with team context, enabling audit trails,
    metrics collection, and security analysis.

    Attributes:
        host: SurrealDB host (e.g., 'localhost' or 'surrealdb')
        port: SurrealDB port (default: 8000)
        namespace: SurrealDB namespace (e.g., 'project_builder')
        database: SurrealDB database (e.g., 'production')
        username: Authentication username
        password: Authentication password
        base_url: Constructed base URL for HTTP API
        session: Requests session for persistent connections
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        namespace: str = "project_builder",
        database: str = "production",
        username: str = "root",
        password: str = "changeme"
    ):
        """Initialize tool history repository.

        Args:
            host: SurrealDB host
            port: SurrealDB port
            namespace: SurrealDB namespace
            database: SurrealDB database
            username: Authentication username
            password: Authentication password
        """
        self.host = host
        self.port = port
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}"

        # Create persistent session with authentication
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            "Accept": "application/json",
        })

        # Test connection
        self._test_connection()

    def _test_connection(self) -> None:
        """Test SurrealDB connection.

        Raises:
            ConnectionError: If unable to connect to SurrealDB
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code != 200:
                raise ConnectionError(f"SurrealDB health check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Unable to connect to SurrealDB at {self.base_url}: {e}")

    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Any:
        """Execute SurrealQL query via HTTP API.

        Args:
            query: SurrealQL query string
            variables: Query variables (for parameterized queries)

        Returns:
            Query result (parsed JSON)

        Raises:
            RuntimeError: If query execution fails
        """
        full_query = f"USE NS {self.namespace}; USE DB {self.database}; {query}"

        headers = {
            "Surreal-NS": self.namespace,
            "Surreal-DB": self.database,
            "Accept": "application/json",
        }

        if variables:
            # Replace $key with JSON-serialized value in query
            import json
            for key, value in variables.items():
                json_value = json.dumps(value)
                full_query = full_query.replace(f"${key}", json_value)

        try:
            response = self.session.post(
                f"{self.base_url}/sql",
                data=full_query,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()

            # SurrealDB returns array of results (one per statement)
            if isinstance(result, list):
                for item in result:
                    if item.get("status") == "ERR":
                        raise RuntimeError(f"SurrealDB query error: {item.get('result')}")
                # Return result of last statement
                return result[-1].get("result") if result else None
            else:
                return result

        except requests.exceptions.RequestException as e:
            error_body = getattr(e.response, 'text', 'No response body') if hasattr(e, 'response') else 'No response'
            raise RuntimeError(f"SurrealDB query execution failed: {e}\nResponse: {error_body}\nQuery: {full_query[:500]}")

    def record_tool_execution(
        self,
        tool_name: str,
        team_name: str,
        agent_role: str,
        parameters: Dict[str, Any],
        result: str,
        status: str,
        duration_ms: int,
        session_id: str,
        task_description: str = ""
    ) -> str:
        """Record a single tool execution to SurrealDB.

        Args:
            tool_name: Name of tool executed (e.g., "bash", "read_file")
            team_name: Team that executed tool (e.g., "Testing", "Frontend")
            agent_role: Role of agent that executed tool (e.g., "testing-lead")
            parameters: Tool input parameters (dict)
            result: Tool execution result (string, truncated if > 1000 chars)
            status: Execution status ("success" or "failure")
            duration_ms: Execution time in milliseconds
            session_id: Execution context session ID
            task_description: First 100 chars of task (for context)

        Returns:
            ID of created tool_executions record

        Example:
            ```python
            repo.record_tool_execution(
                tool_name="bash",
                team_name="Testing",
                agent_role="testing-lead",
                parameters={"command": "pytest tests/"},
                result="5 passed",
                status="success",
                duration_ms=1234,
                session_id="abc-123",
                task_description="Run test suite"
            )
            ```
        """
        # Generate unique ID
        execution_id = str(uuid.uuid4())
        record_id = f"tool_executions:{execution_id}"

        # Truncate result if too large (SurrealDB can handle large strings, but keep reasonable)
        result_truncated = result[:1000] if len(result) > 1000 else result

        # Truncate task description
        task_desc_truncated = task_description[:100] if len(task_description) > 100 else task_description

        # Create record
        data = {
            "tool_name": tool_name,
            "team_name": team_name,
            "agent_role": agent_role,
            "parameters": parameters,
            "result": result_truncated,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "session_id": session_id,
            "task_description": task_desc_truncated
        }

        query = f"""
        CREATE {record_id} CONTENT $data RETURN AFTER;
        """

        self._execute_query(query, variables={"data": data})

        return execution_id

    def record_agent_execution(
        self,
        agent_role: str,
        team_name: str,
        task_description: str,
        session_id: str,
        tool_call_ids: List[str],
        status: str
    ) -> str:
        """Record an agent execution (aggregates multiple tool calls).

        Args:
            agent_role: Role of agent (e.g., "testing-lead")
            team_name: Team name (e.g., "Testing")
            task_description: Full task description
            session_id: Execution context session ID
            tool_call_ids: List of tool_executions IDs associated with this agent execution
            status: Execution status ("success" or "failure")

        Returns:
            ID of created agent_executions record
        """
        execution_id = str(uuid.uuid4())
        record_id = f"agent_executions:{execution_id}"

        data = {
            "agent_role": agent_role,
            "team_name": team_name,
            "task_description": task_description,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tool_calls": tool_call_ids,
            "status": status
        }

        query = f"""
        CREATE {record_id} CONTENT $data RETURN AFTER;
        """

        self._execute_query(query, variables={"data": data})

        return execution_id

    def get_tool_history(
        self,
        team_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tool execution history with optional filters.

        Args:
            team_name: Filter by team (optional)
            tool_name: Filter by tool name (optional)
            limit: Maximum number of records to return

        Returns:
            List of tool execution records

        Example:
            ```python
            # Get all bash executions by Testing team
            history = repo.get_tool_history(team_name="Testing", tool_name="bash")
            ```
        """
        # Build query with optional filters
        conditions = []
        if team_name:
            conditions.append(f"team_name = '{team_name}'")
        if tool_name:
            conditions.append(f"tool_name = '{tool_name}'")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT * FROM tool_executions
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit};
        """

        result = self._execute_query(query)

        return result if result else []

    def get_team_metrics(self, team_name: str) -> Dict[str, Any]:
        """Get comprehensive metrics for a team's tool usage.

        Args:
            team_name: Team name (e.g., "Testing", "Frontend")

        Returns:
            Dictionary with team metrics:
                - total_executions: int
                - success_rate: float (0.0 to 1.0)
                - avg_duration_ms: float
                - tool_distribution: dict[tool_name -> count]
                - most_used_tool: str
                - recent_failures: list[dict] (last 10 failures)

        Example:
            ```python
            metrics = repo.get_team_metrics("Testing")
            print(f"Success rate: {metrics['success_rate'] * 100}%")
            print(f"Most used tool: {metrics['most_used_tool']}")
            ```
        """
        # Total executions
        total_query = """
        SELECT count() as total FROM tool_executions
        WHERE team_name = $team_name
        GROUP ALL;
        """
        total_result = self._execute_query(total_query, variables={"team_name": team_name})
        total_executions = total_result[0].get("total", 0) if total_result else 0

        # Success rate
        success_query = """
        SELECT count() as success_count FROM tool_executions
        WHERE team_name = $team_name AND status = 'success'
        GROUP ALL;
        """
        success_result = self._execute_query(success_query, variables={"team_name": team_name})
        success_count = success_result[0].get("success_count", 0) if success_result else 0
        success_rate = (success_count / total_executions) if total_executions > 0 else 0.0

        # Average duration
        avg_duration_query = """
        SELECT math::mean(duration_ms) as avg_duration FROM tool_executions
        WHERE team_name = $team_name
        GROUP ALL;
        """
        avg_result = self._execute_query(avg_duration_query, variables={"team_name": team_name})
        avg_duration = avg_result[0].get("avg_duration", 0.0) if avg_result else 0.0

        # Tool distribution
        tool_dist_query = """
        SELECT tool_name, count() as count FROM tool_executions
        WHERE team_name = $team_name
        GROUP BY tool_name
        ORDER BY count DESC;
        """
        tool_dist_result = self._execute_query(tool_dist_query, variables={"team_name": team_name})
        tool_distribution = {
            item["tool_name"]: item["count"]
            for item in (tool_dist_result if tool_dist_result else [])
        }

        # Most used tool
        most_used_tool = max(tool_distribution.items(), key=lambda x: x[1])[0] if tool_distribution else "N/A"

        # Recent failures
        failures_query = """
        SELECT tool_name, task_description, result, timestamp FROM tool_executions
        WHERE team_name = $team_name AND status = 'failure'
        ORDER BY timestamp DESC
        LIMIT 10;
        """
        failures_result = self._execute_query(failures_query, variables={"team_name": team_name})
        recent_failures = failures_result if failures_result else []

        return {
            "team_name": team_name,
            "total_executions": total_executions,
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": round(avg_duration, 2),
            "tool_distribution": tool_distribution,
            "most_used_tool": most_used_tool,
            "recent_failures": recent_failures
        }

    def get_policy_violations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent policy violations (tool access attempts that failed).

        Policy violations are identified by status="failure" in tool_executions.
        In Phase 2a, TeamAwareToolRegistry blocks disallowed tools, which would
        result in tool execution failures.

        Args:
            limit: Maximum number of violations to return

        Returns:
            List of policy violation records

        Note: This requires Phase 2a logging integration where blocked tool
        attempts are recorded with status="failure" and a specific error message.
        """
        query = f"""
        SELECT * FROM tool_executions
        WHERE status = 'failure'
        ORDER BY timestamp DESC
        LIMIT {limit};
        """

        result = self._execute_query(query)

        return result if result else []

    def clear_history(self, team_name: Optional[str] = None) -> int:
        """Clear tool execution history (for testing/maintenance).

        Args:
            team_name: Clear only for specific team (None = clear all)

        Returns:
            Number of records deleted

        Warning: This is destructive. Use with caution.
        """
        if team_name:
            query = """
            DELETE FROM tool_executions WHERE team_name = $team_name;
            """
            result = self._execute_query(query, variables={"team_name": team_name})
        else:
            query = """
            DELETE FROM tool_executions;
            """
            result = self._execute_query(query)

        # SurrealDB DELETE returns deleted records
        return len(result) if result else 0
