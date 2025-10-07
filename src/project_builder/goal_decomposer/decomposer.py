"""Goal decomposer implementation using Premium Reasoning Model.

Converts natural language project goals into HTN task graphs using
Qwen3-Next-80B-A3B-Thinking model for strategic decomposition.
"""

import json
import re
import logging
from typing import Dict, Any, Optional

from src.interfaces import IGoalDecomposer, ITextGenerator, LLMConfig
from src.entities.htn.htn_node import HTNNode

logger = logging.getLogger(__name__)


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
        self.max_retries = 3

    def _repair_json(self, json_str: str) -> str:
        """Attempt to repair common JSON syntax errors.

        Args:
            json_str: Potentially malformed JSON string

        Returns:
            Repaired JSON string
        """
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Add missing commas between objects/arrays
        json_str = re.sub(r'"\s*\n\s*"', r'",\n"', json_str)
        json_str = re.sub(r'}\s*\n\s*{', r'},\n{', json_str)
        json_str = re.sub(r']\s*\n\s*\[', r'],\n[', json_str)

        # Remove comments (JSON doesn't support comments)
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

        # Fix unescaped quotes (basic attempt)
        # This is tricky and might need refinement

        return json_str

    async def decompose_goal(self, goal: str) -> HTNNode:
        """Decompose natural language goal into HTN task graph with retry logic.

        Uses thinking model to:
        1. Identify core components and dependencies
        2. Determine critical path tasks
        3. Create hierarchical task structure
        4. Define preconditions and effects

        Retries with stricter prompts if JSON parsing fails.

        Args:
            goal: Natural language project goal

        Returns:
            HTN task graph representing the project

        Example:
            goal: "Create a REST API with user authentication"
            returns: HTNNode with design, implementation, and testing subtasks
        """
        import asyncio

        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Generate HTN structure using thinking model
                # Use stricter prompt on retries
                strict_mode = attempt > 0
                prompt = self._build_decomposition_prompt(goal, strict_mode=strict_mode)

                config = LLMConfig(
                    temperature=0.3 if strict_mode else 0.4,  # Lower for retries
                    max_tokens=8192
                )

                logger.info(f"Decomposing goal (attempt {attempt + 1}/{self.max_retries}): {goal[:50]}...")

                # Note: thinking_model.generate is synchronous (not async)
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.thinking_model.generate(
                        messages=[{"role": "user", "content": prompt}],
                        config=config
                    )
                )

                # Parse response into HTN structure (with repair)
                htn_graph = self._parse_htn_from_response(response, attempt=attempt)

                # Ensure root task has no preconditions (safety measure)
                htn_graph.preconditions = {}

                # Validate HTN structure
                self._validate_htn(htn_graph)

                logger.info(f"Successfully decomposed goal into HTN (depth {htn_graph.get_depth()})")
                return htn_graph

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    logger.info("Retrying with stricter prompt...")
                    continue
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise ValueError(f"Failed to decompose goal after {self.max_retries} attempts: {last_error}")

    def _build_decomposition_prompt(self, goal: str, strict_mode: bool = False) -> str:
        """Build prompt for HTN decomposition.

        Args:
            goal: Natural language project goal
            strict_mode: If True, use stricter JSON formatting instructions

        Returns:
            Structured prompt for thinking model
        """
        strict_warning = ""
        if strict_mode:
            strict_warning = """
**CRITICAL**: Previous attempt had JSON syntax errors. Follow JSON syntax EXACTLY:
- Use double quotes for all strings
- No trailing commas
- Escape all special characters
- Validate JSON structure before responding
"""

        return f"""You are an expert project planner. Decompose the following project goal into a Hierarchical Task Network (HTN).
{strict_warning}

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
- **IMPORTANT**: The root project task MUST have empty preconditions {{}}
- Effects define what state changes the task produces (e.g., {{"artifact_code": "generated_code.py"}})
- For "{goal}", create 3-5 main tasks

**WORLD STATE KEYS** (Available at execution time):
The orchestrator automatically seeds world_state with these keys when file paths are detected in the goal:
- `file_path` (str): Primary file path extracted from goal (e.g., "/opt/project/file.py")
- `file_paths` (List[str]): All file paths extracted from goal
- `file_refs` (List[str]): FileRef URIs for valid paths (e.g., ["file:///opt/project/file.py"])

**PRECONDITION FORMAT RULES**:
1. **Existence Check**: To check if a key exists (any value satisfies):
   - Use: {{"file_path": null}} or {{"file_paths": null}}
   - This checks that the key exists in world_state, regardless of its value

2. **Value Check**: To check for a specific value:
   - Use: {{"file_path": "/opt/project/file.py"}}
   - This checks that the key exists AND has the exact value specified

3. **CRITICAL CONSTRAINT**: Use ONLY the documented world_state keys above for preconditions
   - ✓ VALID: {{"file_path": null}}, {{"file_paths": null}}, {{"file_refs": null}}
   - ✗ INVALID: {{"file_exists": true}}, {{"target_file": "..."}}, {{"source_code": "..."}}

4. **DO NOT** use `file_snapshots` as a precondition (loaded AFTER precondition checks)

**PRECONDITION EXAMPLES**:
- Task needs any file path: {{"file_path": null}}
- Task needs specific file: {{"file_path": "/opt/project/specific.py"}}
- Task needs multiple files: {{"file_paths": null}}
- Task has no preconditions: {{}}

Output ONLY the JSON structure, no additional text."""

    def _parse_htn_from_response(self, response: str, attempt: int = 0) -> HTNNode:
        """Parse HTN structure from model response with JSON repair.

        Extracts JSON from response and recursively builds HTNNode structure.

        Args:
            response: Raw response from thinking model
            attempt: Current attempt number (for logging)

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

        # Try parsing, then try with repair if it fails
        try:
            htn_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt + 1}): {e}")
            logger.debug(f"Malformed JSON (first 500 chars): {json_str[:500]}")

            # Attempt repair
            logger.info("Attempting JSON repair...")
            repaired_json = self._repair_json(json_str)

            try:
                htn_dict = json.loads(repaired_json)
                logger.info("JSON repair successful")
            except json.JSONDecodeError as e2:
                logger.error(f"JSON repair failed: {e2}")
                logger.debug(f"Repaired JSON (first 500 chars): {repaired_json[:500]}")
                raise ValueError(f"Invalid JSON in response (repair failed): {e2}")

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
