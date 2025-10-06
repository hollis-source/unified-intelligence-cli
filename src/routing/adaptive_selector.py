"""
Adaptive Model Selector - Intelligent selection using learned performance data.

Clean Architecture: Application layer, implements IAdaptiveModelSelector.
LSP Compliance: Can substitute static ModelSelector.

Uses learned performance summaries to optimize cost, quality, and latency.
Based on Qwen3-Next-80B-Thinking architectural design.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.routing.adaptive_interfaces import (
    SelectionRequirements,
    SelectionStrategy,
    ModelSummary,
    IModelSummaryRepository
)
from src.routing.model_selector import ModelSelector, ModelCapabilities, SelectionCriteria


logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of model selection with rationale."""
    model_id: str
    score: float
    rationale: Dict[str, Any]


class AdaptiveModelSelector:
    """
    Adaptive model selector using learned performance data.

    LSP Compliance: Implements same interface as static ModelSelector.
    OCP Compliance: Extends selection logic without modifying core.
    DIP Compliance: Depends on IModelSummaryRepository abstraction.
    """

    def __init__(
        self,
        summary_repo: IModelSummaryRepository,
        fallback_selector: Optional[ModelSelector] = None
    ):
        """
        Initialize adaptive selector.

        Args:
            summary_repo: Repository for learned model summaries
            fallback_selector: Fallback to static selector if no learned data
        """
        self.summary_repo = summary_repo
        self.fallback_selector = fallback_selector or ModelSelector()

    def select_model(
        self,
        task_type: str,
        requirements: Optional[SelectionRequirements] = None,
        available_models: Optional[List[str]] = None
    ) -> str:
        """
        Select optimal model based on learned performance and requirements.

        Args:
            task_type: Type of task (e.g., "code_analysis", "translation")
            requirements: Selection requirements and constraints
            available_models: Optional list of available model IDs (None = all)

        Returns:
            Selected model ID

        Raises:
            ValueError: If no models meet requirements
        """
        if requirements is None:
            requirements = SelectionRequirements()

        # Get learned summaries for this task type
        summaries = self.summary_repo.get_summary_for_task_type(task_type)

        # Filter by available models if specified
        if available_models:
            summaries = [s for s in summaries if s.model_id in available_models]

        # If no learned data, fall back to static selector
        if not summaries:
            logger.info(
                f"AdaptiveSelector: No learned data for task_type='{task_type}', "
                f"falling back to static selector"
            )
            return self._fallback_select(task_type, requirements, available_models)

        # Filter summaries by hard constraints
        viable_summaries = self._filter_by_constraints(summaries, requirements)

        if not viable_summaries:
            logger.warning(
                f"AdaptiveSelector: No models meet requirements for task_type='{task_type}', "
                f"relaxing constraints and falling back"
            )
            return self._fallback_select(task_type, requirements, available_models)

        # Score and select best model
        result = self._select_best_model(viable_summaries, requirements)

        logger.info(
            f"AdaptiveSelector: Selected {result.model_id} for task_type='{task_type}' "
            f"(score={result.score:.2f}, strategy={requirements.strategy.value})"
        )
        logger.debug(f"AdaptiveSelector: Rationale: {result.rationale}")

        return result.model_id

    def _filter_by_constraints(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> List[ModelSummary]:
        """
        Filter summaries by hard constraints.

        Args:
            summaries: List of model summaries
            requirements: Selection requirements

        Returns:
            Filtered list of viable summaries
        """
        viable = []

        for summary in summaries:
            # Check latency constraint
            if requirements.max_latency_ms is not None:
                if summary.avg_latency_ms > requirements.max_latency_ms:
                    logger.debug(
                        f"AdaptiveSelector: Filtered out {summary.model_id} "
                        f"(latency {summary.avg_latency_ms:.1f}ms > {requirements.max_latency_ms}ms)"
                    )
                    continue

            # Check success rate constraint
            if requirements.min_success_rate is not None:
                if summary.success_rate < requirements.min_success_rate:
                    logger.debug(
                        f"AdaptiveSelector: Filtered out {summary.model_id} "
                        f"(success rate {summary.success_rate:.2%} < {requirements.min_success_rate:.2%})"
                    )
                    continue

            # Check cost constraint
            if requirements.max_cost_per_task is not None:
                if summary.avg_cost_per_task > requirements.max_cost_per_task:
                    logger.debug(
                        f"AdaptiveSelector: Filtered out {summary.model_id} "
                        f"(cost ${summary.avg_cost_per_task:.4f} > ${requirements.max_cost_per_task:.4f})"
                    )
                    continue

            viable.append(summary)

        return viable

    def _select_best_model(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> SelectionResult:
        """
        Select best model from viable summaries based on strategy.

        Args:
            summaries: List of viable model summaries
            requirements: Selection requirements

        Returns:
            Selection result with model ID and rationale
        """
        if requirements.strategy == SelectionStrategy.MINIMIZE_COST:
            return self._select_by_cost(summaries, requirements)
        elif requirements.strategy == SelectionStrategy.MINIMIZE_LATENCY:
            return self._select_by_latency(summaries, requirements)
        elif requirements.strategy == SelectionStrategy.MAXIMIZE_QUALITY:
            return self._select_by_quality(summaries, requirements)
        else:  # BALANCED
            return self._select_balanced(summaries, requirements)

    def _select_by_cost(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> SelectionResult:
        """
        Select model with minimum cost.

        Args:
            summaries: List of viable summaries
            requirements: Selection requirements

        Returns:
            Selection result
        """
        # Sort by cost (ascending), then by success rate (descending)
        sorted_summaries = sorted(
            summaries,
            key=lambda s: (s.avg_cost_per_task, -s.success_rate)
        )

        best = sorted_summaries[0]

        return SelectionResult(
            model_id=best.model_id,
            score=1.0 / (best.avg_cost_per_task + 0.001),  # Higher score = lower cost
            rationale={
                "strategy": "minimize_cost",
                "cost": best.avg_cost_per_task,
                "latency_ms": best.avg_latency_ms,
                "success_rate": best.success_rate,
                "sample_size": best.sample_size
            }
        )

    def _select_by_latency(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> SelectionResult:
        """
        Select model with minimum latency.

        Args:
            summaries: List of viable summaries
            requirements: Selection requirements

        Returns:
            Selection result
        """
        # Sort by latency (ascending), then by success rate (descending)
        sorted_summaries = sorted(
            summaries,
            key=lambda s: (s.avg_latency_ms, -s.success_rate)
        )

        best = sorted_summaries[0]

        return SelectionResult(
            model_id=best.model_id,
            score=1000.0 / (best.avg_latency_ms + 1.0),  # Higher score = lower latency
            rationale={
                "strategy": "minimize_latency",
                "latency_ms": best.avg_latency_ms,
                "cost": best.avg_cost_per_task,
                "success_rate": best.success_rate,
                "sample_size": best.sample_size
            }
        )

    def _select_by_quality(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> SelectionResult:
        """
        Select model with maximum success rate.

        Args:
            summaries: List of viable summaries
            requirements: Selection requirements

        Returns:
            Selection result
        """
        # Sort by success rate (descending), then by cost (ascending)
        sorted_summaries = sorted(
            summaries,
            key=lambda s: (-s.success_rate, s.avg_cost_per_task)
        )

        best = sorted_summaries[0]

        return SelectionResult(
            model_id=best.model_id,
            score=best.success_rate,
            rationale={
                "strategy": "maximize_quality",
                "success_rate": best.success_rate,
                "latency_ms": best.avg_latency_ms,
                "cost": best.avg_cost_per_task,
                "sample_size": best.sample_size
            }
        )

    def _select_balanced(
        self,
        summaries: List[ModelSummary],
        requirements: SelectionRequirements
    ) -> SelectionResult:
        """
        Select model using balanced scoring (weighted combination).

        Scoring weights (from 80B thinking model design):
        - Quality: 40% (success_rate)
        - Latency: 30% (inverse of latency_ms)
        - Cost: 30% (inverse of cost_per_task)

        Args:
            summaries: List of viable summaries
            requirements: Selection requirements

        Returns:
            Selection result
        """
        # Normalize metrics to 0-100 scale
        if not summaries:
            raise ValueError("No summaries to score")

        # Find min/max for normalization
        latencies = [s.avg_latency_ms for s in summaries]
        costs = [s.avg_cost_per_task for s in summaries]
        success_rates = [s.success_rate for s in summaries]

        min_latency, max_latency = min(latencies), max(latencies)
        min_cost, max_cost = min(costs), max(costs)

        scored_summaries = []

        for summary in summaries:
            # Quality score: success_rate * 100 (already 0-1 scale)
            quality_score = summary.success_rate * 100

            # Latency score: lower is better, normalize to 0-100
            if max_latency > min_latency:
                latency_score = 100 * (1 - (summary.avg_latency_ms - min_latency) / (max_latency - min_latency))
            else:
                latency_score = 100  # All same latency

            # Cost score: lower is better, normalize to 0-100
            if max_cost > min_cost:
                cost_score = 100 * (1 - (summary.avg_cost_per_task - min_cost) / (max_cost - min_cost))
            else:
                cost_score = 100  # All same cost

            # Weighted combination (40% quality, 30% latency, 30% cost)
            total_score = (
                quality_score * 0.4 +
                latency_score * 0.3 +
                cost_score * 0.3
            )

            scored_summaries.append((summary, total_score, quality_score, latency_score, cost_score))

        # Select highest scoring model
        scored_summaries.sort(key=lambda x: x[1], reverse=True)
        best_summary, best_score, q_score, l_score, c_score = scored_summaries[0]

        return SelectionResult(
            model_id=best_summary.model_id,
            score=best_score,
            rationale={
                "strategy": "balanced",
                "total_score": best_score,
                "quality_score": q_score,
                "latency_score": l_score,
                "cost_score": c_score,
                "success_rate": best_summary.success_rate,
                "latency_ms": best_summary.avg_latency_ms,
                "cost": best_summary.avg_cost_per_task,
                "sample_size": best_summary.sample_size
            }
        )

    def _fallback_select(
        self,
        task_type: str,
        requirements: SelectionRequirements,
        available_models: Optional[List[str]]
    ) -> str:
        """
        Fallback to static selector when no learned data available.

        Args:
            task_type: Task type
            requirements: Selection requirements
            available_models: Available models

        Returns:
            Selected model ID
        """
        # Map SelectionRequirements to static SelectionCriteria
        if requirements.strategy == SelectionStrategy.MINIMIZE_COST:
            criteria = SelectionCriteria.COST
        elif requirements.strategy == SelectionStrategy.MINIMIZE_LATENCY:
            criteria = SelectionCriteria.SPEED
        elif requirements.strategy == SelectionStrategy.MAXIMIZE_QUALITY:
            criteria = SelectionCriteria.QUALITY
        else:
            criteria = SelectionCriteria.BALANCED

        return self.fallback_selector.select_model(
            criteria=criteria,
            available_providers=available_models,
            task_description=task_type
        )

    def get_selection_rationale(
        self,
        model_id: str,
        task_type: str
    ) -> dict:
        """
        Get explanation for why a model would be selected.

        Args:
            model_id: Model ID to explain
            task_type: Task type

        Returns:
            Dict with selection rationale
        """
        summary = self.summary_repo.get_summary(model_id, task_type)

        if not summary:
            return {
                "model_id": model_id,
                "task_type": task_type,
                "explanation": "No learned data available",
                "data_source": "static_fallback"
            }

        # Get all summaries for comparison
        all_summaries = self.summary_repo.get_summary_for_task_type(task_type)

        # Rank this model
        by_cost = sorted(all_summaries, key=lambda s: s.avg_cost_per_task)
        by_latency = sorted(all_summaries, key=lambda s: s.avg_latency_ms)
        by_quality = sorted(all_summaries, key=lambda s: s.success_rate, reverse=True)

        cost_rank = next((i for i, s in enumerate(by_cost) if s.model_id == model_id), -1) + 1
        latency_rank = next((i for i, s in enumerate(by_latency) if s.model_id == model_id), -1) + 1
        quality_rank = next((i for i, s in enumerate(by_quality) if s.model_id == model_id), -1) + 1

        return {
            "model_id": model_id,
            "task_type": task_type,
            "metrics": {
                "avg_latency_ms": summary.avg_latency_ms,
                "success_rate": summary.success_rate,
                "avg_cost_per_task": summary.avg_cost_per_task,
                "sample_size": summary.sample_size
            },
            "rankings": {
                "cost_rank": f"{cost_rank}/{len(all_summaries)}",
                "latency_rank": f"{latency_rank}/{len(all_summaries)}",
                "quality_rank": f"{quality_rank}/{len(all_summaries)}"
            },
            "last_updated": summary.last_updated.isoformat(),
            "data_source": "learned_summaries"
        }
