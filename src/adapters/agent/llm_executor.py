import json
import logging
from typing import Any, Dict, List, Optional

from src.validation import OutputValidator, ValidationResult, ValidationType


logger = logging.getLogger(__name__)


class LLMExecutor:
    """
    Executes a language model agent to completion.

    Week 14: Priority 2.2 - Added output validation support.
    """

    def __init__(
        self,
        agent: Any,
        tool_executor: Any,
        output_validator: Optional[OutputValidator] = None,
        enable_validation: bool = False
    ) -> None:
        """
        Initialize with the agent and tool executor.

        Args:
            agent: Agent to execute
            tool_executor: Tool executor for agent tools
            output_validator: Optional output validator (creates default if None and enable_validation=True)
            enable_validation: Enable output validation (default: False for backward compatibility)
        """
        self.agent = agent
        self.tool_executor = tool_executor
        self.enable_validation = enable_validation

        # Initialize validator if enabled
        if self.enable_validation and output_validator is None:
            self.output_validator = OutputValidator()
        else:
            self.output_validator = output_validator

    def run_agent(self, prompt: str, max_steps: int = 10) -> Dict[str, Any]:
        """
        Run the agent with the given prompt and return the result.

        Week 14: Priority 2.2 - Added output validation.

        Returns:
            Dict with 'steps', 'final_observation', and optionally 'validation_result'
        """
        try:
            steps = []
            for _ in range(max_steps):
                step = self._run_agent_step(prompt, steps)
                steps.append(step)
                if step['done']:
                    break
                prompt = step['observation']

            final_output = step['observation']
            result = {
                'steps': steps,
                'final_observation': final_output
            }

            # Week 14: Validate output if enabled
            if self.enable_validation and self.output_validator:
                validation_result = self._validate_output(final_output)
                result['validation_result'] = validation_result.to_dict()

                # Log validation results
                if not validation_result.passed:
                    logger.warning(
                        f"Output validation failed: {validation_result.error_message}"
                    )
                elif validation_result.warnings:
                    logger.info(
                        f"Output validation passed with {len(validation_result.warnings)} warnings"
                    )
                else:
                    logger.debug("Output validation passed")

            return result
        except Exception as e:
            raise RuntimeError(f"Error executing agent: {e}") from e

    def _run_agent_step(self, prompt: str, previous_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a single step of the agent."""
        observation, done = self.agent.act(prompt, previous_steps)
        return {
            'observation': observation,
            'done': done
        }

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with the given name and arguments."""
        try:
            return self.tool_executor.execute(tool_name, args)
        except Exception as e:
            raise RuntimeError(f"Error executing tool {tool_name}: {e}") from e

    def _parse_tool_response(self, response: str) -> Dict[str, Any]:
        """Parse the raw response from a tool into a structured dict."""
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from tool: {response}") from e

    def _format_tool_args(self, args: Dict[str, Any]) -> str:
        """Format tool arguments into a string for the tool executor."""
        return json.dumps(args)

    def _validate_output(
        self,
        output: str,
        validation_type: Optional[ValidationType] = None
    ) -> ValidationResult:
        """
        Validate agent output (Week 14: Priority 2.2).

        Args:
            output: Agent output to validate
            validation_type: Optional type hint (auto-detect if None)

        Returns:
            ValidationResult with pass/fail and error details

        Strategy:
            1. Delegate to OutputValidator
            2. Log validation results
            3. Return structured result (never raise exception)
        """
        try:
            return self.output_validator.validate(output, validation_type)
        except Exception as e:
            # Validation should never fail the execution
            logger.error(f"Output validation error: {e}")
            return ValidationResult(
                passed=False,
                validation_type=ValidationType.GENERIC,
                error_message=f"Validation error: {str(e)}"
            )
