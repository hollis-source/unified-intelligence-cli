import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.interfaces import ITextGenerator, LLMConfig


class MockLLMProvider(ITextGenerator):
    """Mock LLM provider that returns deterministic JSON for offline tests.

    Accepts an optional default_response used when no template match is found
    and the on-disk mock_responses.json does not define a 'default' template.

    Args:
        default_response: Default response to return
        latency_ms: Simulated latency in milliseconds (for parallel testing)
    """

    def __init__(self, default_response: Any | None = None, latency_ms: float = 0):
        self.responses = self._load_responses()
        self.default_response = default_response
        self.latency_ms = latency_ms

    def _load_responses(self) -> Dict[str, Any]:
        """Load mock responses from JSON file."""
        responses_path = Path(__file__).parent / 'mock_responses.json'
        if responses_path.exists():
            with open(responses_path, 'r') as f:
                return json.load(f)
        return {}

    def _match_goal_to_template(self, goal: str) -> str:
        """Match goal description to appropriate template key."""
        goal_lower = (goal or "").lower()
        # CI/CD keywords
        if any(kw in goal_lower for kw in ['ci/cd', 'ci cd', 'github actions', 'pipeline', 'git hooks', 'ci', 'cd']):
            return 'ci_cd_pipeline'
        # REST API keywords
        if any(kw in goal_lower for kw in ['rest api', 'api', 'fastapi', 'flask']):
            return 'rest_api'
        return 'default'

    def generate(self, messages: List[Dict[str, Any]] | str, config: Optional[LLMConfig] = None) -> str:
        """Generate mock response.

        - If default_response is set and messages is a standard list, return it.
        - Otherwise, parse goal from input (string or messages) and return JSON
          with a top-level 'tasks' list built from on-disk templates.
        - Simulates latency if latency_ms is set (for parallel execution testing)
        """
        # Simulate network latency if configured
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)

        # Interface-compliant fast path for integration tests
        if self.default_response is not None and isinstance(messages, list):
            return self.default_response

        # Normalize to a single prompt string
        prompt = ""
        if isinstance(messages, str):
            prompt = messages
        elif isinstance(messages, list):
            parts: List[str] = []
            for m in messages:
                if isinstance(m, dict):
                    c = m.get('content')
                    if isinstance(c, str):
                        parts.append(c)
                    elif isinstance(c, list):
                        for ch in c:
                            if isinstance(ch, dict):
                                t = ch.get('text') or ch.get('content')
                                if isinstance(t, str):
                                    parts.append(t)
            prompt = "\n".join(parts).strip()

        # Extract goal from prompt heuristically
        goal = ""
        for line in prompt.split("\n"):
            if 'goal:' in line.lower():
                goal = line.split(':', 1)[1].strip()
                break
        if not goal:
            goal = prompt.strip()

        # Choose template and build 'tasks' view
        key = self._match_goal_to_template(goal)
        template = self.responses.get(key) or self.responses.get('default') or {
            "task_id": "root_default",
            "description": "Default decomposition for generic goals",
            "subtasks": [
                {"task_id": "analyze_requirements", "description": "Analyze project requirements"}
            ]
        }
        tasks = []
        for t in template.get('subtasks', []):
            tasks.append({
                "task_id": t.get("task_id"),
                "description": t.get("description", "")
            })
        if not tasks:
            tasks = [{
                "task_id": template.get("task_id", "task1"),
                "description": template.get("description", "Task")
            }]

        return json.dumps({"tasks": tasks}, indent=2)

