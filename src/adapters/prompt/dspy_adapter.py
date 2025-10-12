"""
DSPy Prompt Adapter - Bridge between DSPy and unified-intelligence-cli LLM providers.

Sprint 1, US-1.2: Adapter to use DSPy prompt optimization with existing LLM providers.

Clean Architecture:
- DIP: Depends on ITextGenerator abstraction, not concrete providers
- SRP: Single responsibility - translate between DSPy and our providers
- OCP: Open for extension (add new task types), closed for modification
"""

import dspy
import logging
from typing import Optional
from src.entities import Task, ExecutionContext
from src.interfaces import ITextGenerator
from src.adapters.prompt.dspy_signatures import (
    ImplementationSignature,
    DesignSignature,
    TestingSignature,
    DocumentationSignature
)

logger = logging.getLogger(__name__)


class DSPyPromptAdapter:
    """
    Adapter to use DSPy prompt optimization with existing LLM providers.

    Wraps ITextGenerator implementations (Grok, Qwen3, etc.) with DSPy's
    auto-optimization capabilities.

    Architecture:
    - Accepts any ITextGenerator provider
    - Creates DSPy LM wrapper
    - Routes tasks to appropriate DSPy signature modules
    - Falls back to manual prompts for unsupported task types
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        use_chain_of_thought: bool = True
    ):
        """
        Initialize DSPy adapter with LLM provider.

        Args:
            llm_provider: Existing LLM provider (implements ITextGenerator)
            use_chain_of_thought: Whether to use ChainOfThought module (vs Predict)
        """
        self.llm_provider = llm_provider
        self.use_chain_of_thought = use_chain_of_thought

        # Configure DSPy to use our provider
        self.dspy_lm = self._wrap_provider(llm_provider)
        dspy.configure(lm=self.dspy_lm)

        # Initialize modules for each task type
        module_class = dspy.ChainOfThought if use_chain_of_thought else dspy.Predict

        self.implementation_module = module_class(ImplementationSignature)
        self.design_module = module_class(DesignSignature)
        self.testing_module = module_class(TestingSignature)
        self.documentation_module = module_class(DocumentationSignature)

        logger.info(f"DSPy adapter initialized with {llm_provider.__class__.__name__}")

    def _wrap_provider(self, provider: ITextGenerator) -> dspy.LM:
        """
        Wrap ITextGenerator provider for DSPy compatibility.

        Maps our provider format to DSPy's expected format.
        Uses OpenAI-compatible API which both HuggingFace and Grok support.

        Args:
            provider: Our LLM provider

        Returns:
            DSPy LM wrapper
        """
        # Extract provider details
        model_name = getattr(provider, 'model_id', None) or getattr(provider, 'model', 'unknown')
        api_base = getattr(provider, 'api_base', None)

        # HuggingFace adapters use 'token' instead of 'api_key'
        api_key = getattr(provider, 'api_key', None) or getattr(provider, 'token', None)

        # For HuggingFace providers without explicit api_base, use their OpenAI-compatible endpoint
        if api_key and not api_base and hasattr(provider, 'token'):
            # This is a HuggingFace provider
            api_base = "https://router.huggingface.co/nscale/v1"
            dspy_model = f"openai/{model_name}"
            logger.debug(f"Detected HuggingFace provider, using router endpoint")
        elif api_base and 'huggingface' in api_base.lower():
            # Explicit HuggingFace base URL
            dspy_model = f"openai/{model_name}"
        elif 'grok' in model_name.lower():
            # Grok uses OpenAI-compatible API
            dspy_model = f"openai/{model_name}"
        else:
            # Default to OpenAI format
            dspy_model = f"openai/{model_name}"

        logger.debug(f"Wrapping provider as DSPy LM: {dspy_model}, api_base={api_base}")

        return dspy.LM(
            model=dspy_model,
            api_base=api_base,
            api_key=api_key,
            cache=True  # Enable DSPy's built-in caching
        )

    def generate_for_task(
        self,
        task: Task,
        context: Optional[ExecutionContext] = None
    ) -> str:
        """
        Generate output for task using appropriate DSPy module.

        Routes to the correct signature based on task_type:
        - implementation/coding → ImplementationSignature
        - design → DesignSignature
        - testing → TestingSignature
        - documentation → DocumentationSignature
        - other → fallback to manual prompts

        Args:
            task: Task to execute
            context: Execution context with previous outputs

        Returns:
            Generated output (code, design, tests, etc.)
        """
        task_type = task.task_type if hasattr(task, 'task_type') else 'general'

        # Format context
        previous_outputs = self._format_context(context) if context else ""

        # Route to appropriate module
        try:
            if task_type in ['implementation', 'coding']:
                result = self.implementation_module(
                    task_description=task.description,
                    previous_outputs=previous_outputs
                )
                return result.code

            elif task_type == 'design':
                result = self.design_module(
                    task_description=task.description,
                    context=previous_outputs
                )
                return result.design_spec

            elif task_type == 'testing':
                # Extract code to test from context
                code_to_test = self._extract_code_from_context(context)
                result = self.testing_module(
                    task_description=task.description,
                    code_to_test=code_to_test
                )
                return result.test_code

            elif task_type == 'documentation':
                code_or_api = self._extract_code_from_context(context)
                result = self.documentation_module(
                    task_description=task.description,
                    code_or_api=code_or_api
                )
                return result.documentation

            else:
                # Fallback to manual prompts for unsupported task types
                logger.warning(
                    f"Task type '{task_type}' not yet supported by DSPy, "
                    f"falling back to manual prompts"
                )
                return self._fallback_manual_prompt(task, context)

        except Exception as e:
            logger.error(f"DSPy generation failed: {e}, falling back to manual")
            return self._fallback_manual_prompt(task, context)

    def _format_context(self, context: ExecutionContext) -> str:
        """
        Format execution context for DSPy input.

        Extracts llm_state and formats it as readable text for the LLM.

        Args:
            context: Execution context

        Returns:
            Formatted context string
        """
        if not context or not hasattr(context, 'llm_state'):
            return "No previous context available."

        llm_state = context.llm_state or {}
        formatted = []

        for key, value in llm_state.items():
            if isinstance(value, str) and len(value) > 500:
                # Truncate very long values
                formatted.append(f"{key}: {value[:500]}... (truncated)")
            else:
                formatted.append(f"{key}: {value}")

        return "\n".join(formatted) if formatted else "No previous context available."

    def _extract_code_from_context(self, context: Optional[ExecutionContext]) -> str:
        """
        Extract code artifacts from context for testing/documentation.

        Looks for keys ending with _code, _function, _implementation.

        Args:
            context: Execution context

        Returns:
            Extracted code or empty string
        """
        if not context or not hasattr(context, 'llm_state'):
            return ""

        llm_state = context.llm_state or {}

        # Look for keys containing code
        code_keys = [k for k in llm_state.keys() if any(
            suffix in k for suffix in ['_code', '_function', '_implementation']
        )]

        if code_keys:
            # Return most recent code (last key)
            return llm_state[code_keys[-1]]

        return ""

    def _fallback_manual_prompt(
        self,
        task: Task,
        context: Optional[ExecutionContext]
    ) -> str:
        """
        Fallback to manual prompts for unsupported task types.

        This provides graceful degradation when DSPy doesn't support
        a task type yet (e.g., deployment, research).

        Args:
            task: Task to execute
            context: Execution context

        Returns:
            Fallback response indicating manual prompt needed
        """
        return f"[FALLBACK] Manual prompt needed for task: {task.description}"
