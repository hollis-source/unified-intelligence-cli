"""Goal decomposer implementation using Premium Reasoning Model.

Converts natural language project goals into HTN task graphs using
Qwen3-Next-80B-A3B-Thinking model for strategic decomposition.
"""

import json
import re
from typing import Dict, Any

from src.interfaces import IGoalDecomposer, ITextGenerator, LLMConfig
from src.entities.htn.htn_node import HTNNode


class GoalDecomposer(IGoalDecomposer):
    """Decomposer for converting natural language goals to HTN graphs.

    Uses Premium Reasoning Model (Qwen3-Next-80B-Thinking) to strategically
    decompose project goals into hierarchical task networks with preconditions
    and effects.

    Attributes:
        thinking_model: Text generator for strategic reasoning
    """

    def __init__(self, thinking_model: ITextGenerator):
        """Initialize goal decomposer with thinking model.

        Args:
            thinking_model: Text generator implementing strategic reasoning
        """
        self.thinking_model = thinking_model

    async def decompose_goal(self, goal: str) -> HTNNode:
        """Decompose natural language goal into HTN task graph.

        Uses thinking model to:
        1. Identify core components and dependencies
        2. Determine critical path tasks
        3. Create hierarchical task structure
        4. Define preconditions and effects

        Args:
            goal: Natural language project goal

        Returns:
            HTN task graph representing the project

        Example:
            goal: "Create a REST API with user authentication"
            returns: HTNNode with design, implementation, and testing subtasks
        """
        # Generate HTN structure using thinking model
        prompt = self._build_decomposition_prompt(goal)

        config = LLMConfig(
            temperature=0.4,  # Lower for structured output
            max_tokens=8192   # Sufficient for HTN structure
        )

        response = await self.thinking_model.generate(
            messages=[{"role": "user", "content": prompt}],
            config=config
        )

        # Parse response into HTN structure
        htn_graph = self._parse_htn_from_response(response)

        # Validate HTN structure
        self._validate_htn(htn_graph)

        return htn_graph

    def _build_decomposition_prompt(self, goal: str) -> str:
        """Build prompt for HTN decomposition.

        Args:
            goal: Natural language project goal

        Returns:
            Structured prompt for thinking model
        """
        return f"""You are an expert project planner. Decompose the following project goal into a Hierarchical Task Network (HTN).

Project Goal: {goal}

Think step-by-step about:
1. What are the core components needed?
2. What are the critical dependencies between tasks?
3. What is the natural decomposition hierarchy?
4. What preconditions must be satisfied for each task?
5. What state changes (effects) does each task produce?

Generate a hierarchical task network in JSON format with this structure:

{{
  "task_id": "unique_task_identifier",
  "description": "Human-readable description",
  "subtasks": [
    {{
      "task_id": "subtask_1",
      "description": "Subtask description",
      "subtasks": [],
      "preconditions": {{"key": "value"}},
      "effects": {{"key": "value"}}
    }},
    ...
  ],
  "preconditions": {{}},
  "effects": {{}}
}}

Guidelines:
- Use snake_case for task_id (e.g., "design_api_schema")
- Keep hierarchy depth to 2-3 levels maximum
- Primitive tasks (leaves) have empty subtasks array
- Preconditions reference keys that must exist in world state
- Effects define what state changes the task produces
- For "{goal}", create 3-5 main tasks

Output ONLY the JSON structure, no additional text."""

    def _parse_htn_from_response(self, response: str) -> HTNNode:
        """Parse HTN structure from model response.

        Extracts JSON from response and recursively builds HTNNode structure.

        Args:
            response: Raw response from thinking model

        Returns:
            HTNNode root of task graph

        Raises:
            ValueError: If JSON parsing fails or structure is invalid
        """
        # Extract JSON from response
        # Model might include markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to extract JSON directly
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError(f"Could not extract JSON from response: {response[:200]}")

        try:
            htn_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")

        # Recursively build HTNNode from dictionary
        return self._dict_to_htn(htn_dict)

    def _dict_to_htn(self, data: Dict[str, Any]) -> HTNNode:
        """Recursively convert dictionary to HTNNode.

        Args:
            data: Dictionary representation of HTN node

        Returns:
            HTNNode instance

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if "task_id" not in data:
            raise ValueError("Missing required field: task_id")
        if "description" not in data:
            raise ValueError("Missing required field: description")

        # Create HTNNode
        node = HTNNode(
            task_id=data["task_id"],
            description=data["description"],
            subtasks=[],
            preconditions=data.get("preconditions", {}),
            effects=data.get("effects", {}),
            metadata=data.get("metadata", {})
        )

        # Recursively process subtasks
        for subtask_data in data.get("subtasks", []):
            subtask_node = self._dict_to_htn(subtask_data)
            node.add_subtask(subtask_node)

        return node

    def _validate_htn(self, htn_graph: HTNNode) -> None:
        """Validate HTN structure for correctness.

        Checks:
        - No circular dependencies
        - Valid preconditions/effects format
        - Reasonable depth (<= 5 levels)

        Args:
            htn_graph: HTN root node to validate

        Raises:
            ValueError: If validation fails
        """
        # Check depth
        depth = htn_graph.get_depth()
        if depth > 5:
            raise ValueError(f"HTN depth {depth} exceeds maximum of 5 levels")

        # Validate no circular references (simple check)
        visited_ids = set()
        self._check_circular_deps(htn_graph, visited_ids)

    def _check_circular_deps(self, node: HTNNode, visited: set) -> None:
        """Recursively check for circular task dependencies.

        Args:
            node: Current HTN node
            visited: Set of visited task IDs

        Raises:
            ValueError: If circular dependency detected
        """
        if node.task_id in visited:
            raise ValueError(f"Circular dependency detected: {node.task_id}")

        visited.add(node.task_id)

        for subtask in node.subtasks:
            self._check_circular_deps(subtask, visited.copy())
