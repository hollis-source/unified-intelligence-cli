"""
Model Selector - Intelligent model selection based on task requirements.

Clean Architecture: Strategy Pattern for model selection logic.
DIP: Returns provider names (abstraction), not concrete implementations.

Week 13: Multi-model orchestration with intelligent selection.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class SelectionCriteria(Enum):
    """Criteria for model selection."""
    SPEED = "speed"  # Prioritize low latency
    QUALITY = "quality"  # Prioritize success rate
    COST = "cost"  # Prioritize low cost
    PRIVACY = "privacy"  # Prioritize offline/local
    BALANCED = "balanced"  # Balance all factors


@dataclass
class ScoringWeights:
    """
    Configurable weights for balanced scoring.

    OCP Compliance: Allows customization without code modification.

    Weights should sum to 1.0 for proper normalization.
    Default: quality=0.4, speed=0.3, cost=0.3 (privacy excluded for online models).
    """
    quality_weight: float = 0.4
    speed_weight: float = 0.3
    cost_weight: float = 0.3
    privacy_weight: float = 0.0  # Usually 0 for balanced, can be > 0 if important

    def __post_init__(self):
        """Validate weights."""
        total = self.quality_weight + self.speed_weight + self.cost_weight + self.privacy_weight
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(
                f"Weights must sum to 1.0 (got {total}). "
                f"quality={self.quality_weight}, speed={self.speed_weight}, "
                f"cost={self.cost_weight}, privacy={self.privacy_weight}"
            )


@dataclass
class ModelCapabilities:
    """
    Model capabilities and performance metrics.

    Based on evaluation data from DEPLOYMENT_SUMMARY.md
    """
    name: str
    success_rate: float  # 0.0-1.0
    avg_latency: float  # seconds
    cost_per_month: float  # USD
    requires_internet: bool
    max_tokens: int
    supports_tools: bool = False

    def get_score(
        self,
        criteria: SelectionCriteria,
        weights: Optional[ScoringWeights] = None
    ) -> float:
        """
        Calculate selection score based on criteria.

        Higher score = better match for criteria.

        Args:
            criteria: Selection criteria
            weights: Optional custom weights for BALANCED scoring (OCP compliance)

        Returns:
            Score (0.0-100.0)
        """
        if criteria == SelectionCriteria.SPEED:
            # Lower latency = higher score
            # Normalize: 10s = 100, 30s = 33, 60s = 17
            return min(100, (10 / max(self.avg_latency, 1)) * 100)

        elif criteria == SelectionCriteria.QUALITY:
            # Higher success rate = higher score
            return self.success_rate * 100

        elif criteria == SelectionCriteria.COST:
            # Lower cost = higher score
            # Free = 100, $9/mo = 89, $32/mo = 68, $50/mo = 50
            return max(0, 100 - self.cost_per_month * 2)

        elif criteria == SelectionCriteria.PRIVACY:
            # Offline = 100, online = 0
            return 0 if self.requires_internet else 100

        elif criteria == SelectionCriteria.BALANCED:
            # Weighted average of all factors (configurable via weights parameter)
            if weights is None:
                weights = ScoringWeights()  # Use defaults

            speed_score = self.get_score(SelectionCriteria.SPEED)
            quality_score = self.get_score(SelectionCriteria.QUALITY)
            cost_score = self.get_score(SelectionCriteria.COST)
            privacy_score = self.get_score(SelectionCriteria.PRIVACY)

            return (
                (quality_score * weights.quality_weight) +
                (speed_score * weights.speed_weight) +
                (cost_score * weights.cost_weight) +
                (privacy_score * weights.privacy_weight)
            )

        return 0.0


class ModelSelector:
    """
    Intelligent model selector based on task requirements.

    Strategy Pattern: Different selection strategies based on criteria.
    SRP: Single responsibility - model selection logic only.
    OCP: Configurable scoring weights for balanced criteria.
    """

    def __init__(self, scoring_weights: Optional[ScoringWeights] = None):
        """
        Initialize model selector with capabilities registry.

        Args:
            scoring_weights: Optional custom weights for BALANCED scoring (OCP compliance)
        """
        self.models = self._initialize_capabilities()
        self.scoring_weights = scoring_weights  # None = use defaults

    def _initialize_capabilities(self) -> Dict[str, ModelCapabilities]:
        """
        Initialize model capabilities from evaluation data.

        Data sources:
        - DEPLOYMENT_SUMMARY.md: Qwen3 + Tongyi comparison
        - docs/PHASE_2_BASELINE_EVALUATION_COMPLETE.md: Tongyi baseline

        Returns:
            Dict mapping provider name to capabilities
        """
        return {
            "qwen3_zerogpu": ModelCapabilities(
                name="Qwen3-8B-ZeroGPU",
                success_rate=1.0,  # 100% (31/31 examples)
                avg_latency=13.8,  # 13.8s avg (eval endpoint)
                cost_per_month=9.0,  # HF Pro subscription
                requires_internet=True,
                max_tokens=2048,
                supports_tools=False
            ),
            "tongyi-local": ModelCapabilities(
                name="Tongyi-DeepResearch-30B-Local",
                success_rate=0.987,  # 98.7% (298/302 interactions)
                avg_latency=20.1,  # 20.1s avg, 10.9s median
                cost_per_month=31.67,  # $380/yr TCO (electricity + maintenance)
                requires_internet=False,
                max_tokens=4096,
                supports_tools=False
            ),
            "grok": ModelCapabilities(
                name="Grok-2-Latest",
                success_rate=0.95,  # Estimated (not benchmarked)
                avg_latency=5.0,  # API-based, typically fast
                cost_per_month=50.0,  # Estimated API costs
                requires_internet=True,
                max_tokens=8192,
                supports_tools=True
            )
        }

    def select_model(
        self,
        criteria: SelectionCriteria = SelectionCriteria.BALANCED,
        available_providers: Optional[List[str]] = None,
        task_description: Optional[str] = None
    ) -> str:
        """
        Select optimal model based on criteria.

        Args:
            criteria: Selection criteria (speed, quality, cost, privacy, balanced)
            available_providers: List of available provider names (None = all)
            task_description: Optional task description for analysis

        Returns:
            Provider name (e.g., "qwen3_zerogpu")
        """
        # Filter available models
        if available_providers:
            models = {
                name: caps
                for name, caps in self.models.items()
                if name in available_providers
            }
        else:
            models = self.models

        if not models:
            raise ValueError("No models available for selection")

        # Analyze task for special requirements
        if task_description:
            criteria = self._analyze_task_requirements(task_description, criteria)

        # Score each model (pass weights for BALANCED criteria)
        scores = {
            name: caps.get_score(criteria, weights=self.scoring_weights)
            for name, caps in models.items()
        }

        # Select highest scoring model
        best_model = max(scores.items(), key=lambda x: x[1])

        return best_model[0]

    def _analyze_task_requirements(
        self,
        task_description: str,
        default_criteria: SelectionCriteria
    ) -> SelectionCriteria:
        """
        Analyze task description to infer selection criteria.

        Keyword-based analysis for special requirements:
        - "offline", "local", "private" → PRIVACY
        - "fast", "quick", "urgent" → SPEED
        - "accurate", "quality", "critical" → QUALITY
        - "cheap", "cost-effective" → COST

        Args:
            task_description: Task description text
            default_criteria: Default criteria if no keywords match

        Returns:
            Inferred selection criteria
        """
        desc_lower = task_description.lower()

        # Privacy keywords
        if any(kw in desc_lower for kw in ["offline", "local", "private", "confidential"]):
            return SelectionCriteria.PRIVACY

        # Speed keywords
        if any(kw in desc_lower for kw in ["fast", "quick", "urgent", "real-time"]):
            return SelectionCriteria.SPEED

        # Quality keywords
        if any(kw in desc_lower for kw in ["accurate", "quality", "critical", "important"]):
            return SelectionCriteria.QUALITY

        # Cost keywords
        if any(kw in desc_lower for kw in ["cheap", "cost-effective", "budget"]):
            return SelectionCriteria.COST

        return default_criteria

    def get_fallback_chain(
        self,
        primary: str,
        criteria: SelectionCriteria = SelectionCriteria.BALANCED
    ) -> List[str]:
        """
        Get fallback chain for a primary model.

        Fallback strategy:
        1. Primary model (specified)
        2. Next best model by criteria
        3. Most reliable model (highest success rate)

        Args:
            primary: Primary model provider name
            criteria: Selection criteria for fallback

        Returns:
            List of provider names in fallback order
        """
        chain = [primary]

        # Get remaining models scored by criteria
        remaining = {
            name: caps.get_score(criteria)
            for name, caps in self.models.items()
            if name != primary
        }

        # Add best remaining model
        if remaining:
            next_best = max(remaining.items(), key=lambda x: x[1])[0]
            chain.append(next_best)

        # Add most reliable model (if not already in chain)
        most_reliable = max(
            self.models.items(),
            key=lambda x: x[1].success_rate
        )[0]

        if most_reliable not in chain:
            chain.append(most_reliable)

        return chain

    def get_model_info(self, provider_name: str) -> Optional[ModelCapabilities]:
        """
        Get capabilities info for a model.

        Args:
            provider_name: Provider name

        Returns:
            ModelCapabilities or None if not found
        """
        return self.models.get(provider_name)
