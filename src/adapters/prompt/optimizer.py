"""DSPy Prompt Optimizer using MIPROv2.

Sprint 2, US-2.2: Automatic prompt optimization from training examples.

This module wraps DSPy's MIPROv2 optimizer to automatically improve
prompts based on quality metrics and training data.

Clean Architecture:
- Wraps DSPy MIPROv2 with domain-specific interface
- Stores/loads optimized prompts for reproducibility
- Calculates improvement metrics for reporting
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional

import dspy

from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """
    Optimizer for DSPy prompts using MIPROv2.

    Accepts training examples and a quality metric, then uses
    DSPy's MIPROv2 to find optimal prompt variations.

    Attributes:
        training_examples: List of training example dicts
        metric: Quality metric function (example, prediction) -> float
        num_trials: Number of optimization trials (default: 20)
        dspy_examples: Training examples in DSPy format
    """

    def __init__(
        self,
        training_examples: List[Dict[str, str]],
        metric: Optional[Callable] = None,
        num_trials: int = 20
    ):
        """
        Initialize prompt optimizer.

        Args:
            training_examples: List of dicts with 'task_description' and 'expected_output'
            metric: Quality metric function (if None, uses default)
            num_trials: Number of MIPROv2 optimization trials
        """
        self.training_examples = training_examples
        self.metric = metric or self._default_metric
        self.num_trials = num_trials

        # Convert training examples to DSPy format
        self.dspy_examples = self._convert_to_dspy_examples(training_examples)

        logger.info(f"PromptOptimizer initialized with {len(training_examples)} examples, {num_trials} trials")

    def _convert_to_dspy_examples(self, examples: List[Dict[str, str]]) -> List[dspy.Example]:
        """
        Convert dict training examples to DSPy Example format.

        Args:
            examples: List of dicts with task_description and expected_output

        Returns:
            List of dspy.Example instances
        """
        dspy_examples = []

        for ex in examples:
            if not isinstance(ex, dict):
                logger.warning(f"Skipping non-dict example: {ex}")
                continue

            if "task_description" not in ex or "expected_output" not in ex:
                logger.warning(f"Skipping example missing required fields: {ex}")
                continue

            # Create DSPy Example with inputs and outputs marked
            dspy_ex = dspy.Example(
                task_description=ex["task_description"],
                expected_output=ex["expected_output"]
            ).with_inputs("task_description")

            dspy_examples.append(dspy_ex)

        return dspy_examples

    def optimize(
        self,
        adapter: DSPyPromptAdapter,
        task_type: str = "implementation",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run MIPROv2 optimization on DSPy adapter.

        Args:
            adapter: DSPy adapter to optimize
            task_type: Task type to optimize (implementation, design, testing, docs)
            output_path: Optional path to save optimized prompts

        Returns:
            Optimization results with baseline_score, optimized_score, improvement
        """
        logger.info(f"Starting optimization for task_type={task_type}, num_trials={self.num_trials}")

        # Select module to optimize based on task type
        module_to_optimize = self._get_module_for_task_type(adapter, task_type)

        if not self.dspy_examples:
            logger.warning("No training examples available for optimization")
            return {
                "task_type": task_type,
                "baseline_score": 0.0,
                "optimized_score": 0.0,
                "improvement": 0.0,
                "error": "No training examples"
            }

        # Calculate baseline score (before optimization)
        baseline_score = self._calculate_baseline_score(module_to_optimize, self.dspy_examples)
        logger.info(f"Baseline score: {baseline_score:.3f}")

        # Create MIPROv2 optimizer
        # Note: Setting auto=None to allow manual num_candidates and num_trials
        # num_candidates: number of prompt variations to generate
        # num_trials: number of optimization iterations
        optimizer = dspy.MIPROv2(
            metric=self.metric,
            num_candidates=self.num_trials,
            num_trials=max(self.num_trials, 10),  # At least 10 trials recommended
            init_temperature=1.0,
            auto=None  # Disable auto-tuning to use manual configuration
        )

        # Run optimization
        logger.info(f"Running MIPROv2 optimization with {self.num_trials} trials...")
        try:
            optimized_module = optimizer.compile(
                module_to_optimize,
                trainset=self.dspy_examples
            )

            # Calculate optimized score
            optimized_score = self._calculate_baseline_score(optimized_module, self.dspy_examples)
            logger.info(f"Optimized score: {optimized_score:.3f}")

            improvement = optimized_score - baseline_score
            logger.info(f"Improvement: {improvement:+.3f} ({improvement/baseline_score*100:+.1f}%)")

            # Build results
            results = {
                "task_type": task_type,
                "optimized_at": datetime.now().isoformat(),
                "num_trials": self.num_trials,
                "baseline_score": baseline_score,
                "optimized_score": optimized_score,
                "improvement": improvement,
                "improvement_pct": (improvement / baseline_score * 100) if baseline_score > 0 else 0
            }

            # Save if output path provided
            if output_path:
                self._save_optimized_prompts(results, output_path)

            return results

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {
                "task_type": task_type,
                "baseline_score": baseline_score,
                "optimized_score": baseline_score,
                "improvement": 0.0,
                "error": str(e)
            }

    def _get_module_for_task_type(self, adapter: DSPyPromptAdapter, task_type: str) -> dspy.Module:
        """
        Get DSPy module for task type.

        Args:
            adapter: DSPy adapter
            task_type: Task type string

        Returns:
            DSPy module to optimize
        """
        module_map = {
            "implementation": adapter.implementation_module,
            "coding": adapter.implementation_module,
            "design": adapter.design_module,
            "testing": adapter.testing_module,
            "documentation": adapter.documentation_module,
            "docs": adapter.documentation_module
        }

        module = module_map.get(task_type)
        if not module:
            logger.warning(f"Unknown task type '{task_type}', defaulting to implementation")
            module = adapter.implementation_module

        return module

    def _calculate_baseline_score(
        self,
        module: dspy.Module,
        examples: List[dspy.Example]
    ) -> float:
        """
        Calculate average score across examples.

        Args:
            module: DSPy module to evaluate
            examples: Test examples

        Returns:
            Average metric score
        """
        if not examples:
            return 0.0

        total_score = 0.0

        for example in examples:
            try:
                # Run module prediction
                # Provide empty previous_outputs if module expects it
                try:
                    prediction = module(
                        task_description=example.task_description,
                        previous_outputs=""
                    )
                except TypeError:
                    # Module doesn't expect previous_outputs
                    prediction = module(task_description=example.task_description)

                # Calculate metric
                score = self.metric(example, prediction)
                total_score += score

            except Exception as e:
                logger.warning(f"Error evaluating example: {e}")
                # Score 0 for failed examples
                total_score += 0.0

        return total_score / len(examples)

    def _save_optimized_prompts(self, results: Dict[str, Any], output_path: str):
        """
        Save optimized prompts to disk.

        Args:
            results: Optimization results
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved optimized prompts to {output_path}")

    def load_optimized_prompts(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Load previously optimized prompts.

        Args:
            path: Path to optimized prompts JSON file

        Returns:
            Optimization results dict, or None if file doesn't exist
        """
        file_path = Path(path)

        if not file_path.exists():
            logger.warning(f"Optimized prompts file not found: {path}")
            return None

        with open(file_path) as f:
            data = json.load(f)

        logger.info(f"Loaded optimized prompts from {path}")
        return data

    def _default_metric(self, example: dspy.Example, prediction: dspy.Prediction) -> float:
        """
        Default metric if none provided.

        Simple exact match metric for testing.

        Args:
            example: DSPy example
            prediction: DSPy prediction

        Returns:
            1.0 if exact match, 0.0 otherwise
        """
        expected = example.expected_output
        predicted = getattr(prediction, 'code', getattr(prediction, 'output', ''))

        return 1.0 if expected == predicted else 0.0
