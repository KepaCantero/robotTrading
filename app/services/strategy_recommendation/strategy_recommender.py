"""
T19.1.3: StrategyRecommender - Generates personalized strategy recommendations

Integrates scoring and ranking to provide comprehensive strategy recommendations.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyRecommendation:
    """Personalized strategy recommendation."""
    recommended_strategy: str
    confidence_level: str  # high, medium, low
    overall_score: Decimal  # 0-100
    reasoning: str  # Why this strategy is recommended
    alternatives: List[str]  # Alternative strategies to consider
    risk_assessment: str  # low, medium, high
    estimated_annual_return: Decimal
    max_expected_drawdown: Decimal
    suitability_score: Decimal  # How well it matches user profile


class StrategyRecommender:
    """
    Generates personalized strategy recommendations.

    Features:
    - Objective-aware recommendations
    - Risk profile matching
    - Alternative suggestions
    - Detailed explanations
    - Recommendation tracking
    """

    def __init__(self):
        """Initialize strategy recommender."""
        self.recommendation_history: List[StrategyRecommendation] = []
        logger.info("✅ StrategyRecommender initialized")

    async def recommend_strategy(
        self,
        ranked_strategies: List,
        objective: str = "balanced",
        risk_profile: str = "moderate",
    ) -> StrategyRecommendation:
        """
        Generate strategy recommendation based on ranking and profile.

        Args:
            ranked_strategies: List of RankedStrategy from ranker
            objective: Investment objective
            risk_profile: Risk tolerance

        Returns:
            StrategyRecommendation
        """
        if not ranked_strategies:
            return StrategyRecommendation(
                recommended_strategy="NONE",
                confidence_level="low",
                overall_score=Decimal("0"),
                reasoning="No strategies available for recommendation",
                alternatives=[],
                risk_assessment="unknown",
                estimated_annual_return=Decimal("0"),
                max_expected_drawdown=Decimal("0"),
                suitability_score=Decimal("0"),
            )

        # Get best strategy and alternatives
        best = ranked_strategies[0]
        alternatives = [s.strategy_name for s in ranked_strategies[1:min(4, len(ranked_strategies))]]

        # Assess suitability based on profile
        suitability = await self._assess_suitability(best, objective, risk_profile)

        # Determine confidence
        confidence = await self._determine_confidence(best, suitability)

        # Generate reasoning
        reasoning = await self._generate_reasoning(best, objective, risk_profile)

        # Estimate returns and risk
        estimated_return = await self._estimate_annual_return(best, objective)
        max_drawdown = await self._estimate_max_drawdown(best, risk_profile)

        recommendation = StrategyRecommendation(
            recommended_strategy=best.strategy_name,
            confidence_level=confidence,
            overall_score=best.overall_score,
            reasoning=reasoning,
            alternatives=alternatives,
            risk_assessment=await self._assess_risk_level(best),
            estimated_annual_return=estimated_return,
            max_expected_drawdown=max_drawdown,
            suitability_score=suitability,
        )

        self.recommendation_history.append(recommendation)
        logger.info(
            f"✅ Recommended {best.strategy_name} for {objective} objective "
            f"({confidence} confidence)"
        )
        return recommendation

    async def _assess_suitability(
        self,
        strategy,
        objective: str,
        risk_profile: str,
    ) -> Decimal:
        """Assess how well strategy suits the user profile."""
        suitability = Decimal("50")  # Base score

        # Objective match scoring
        if objective == "growth" and strategy.return_score > Decimal("70"):
            suitability += Decimal("20")
        elif objective == "income" and strategy.consistency_score > Decimal("70"):
            suitability += Decimal("20")
        elif objective == "preservation" and strategy.risk_score > Decimal("70"):
            suitability += Decimal("20")
        elif objective == "balanced":
            suitability += Decimal("15")

        # Risk profile match
        if risk_profile == "conservative" and strategy.risk_score > Decimal("70"):
            suitability += Decimal("20")
        elif risk_profile == "moderate" and Decimal("60") <= strategy.risk_score <= Decimal("80"):
            suitability += Decimal("20")
        elif risk_profile == "aggressive" and strategy.return_score > Decimal("70"):
            suitability += Decimal("20")

        return min(Decimal("100"), suitability)

    async def _determine_confidence(
        self,
        strategy,
        suitability: Decimal,
    ) -> str:
        """Determine confidence level."""
        combined_score = (strategy.overall_score + suitability) / Decimal("2")

        if combined_score >= Decimal("75"):
            return "high"
        elif combined_score >= Decimal("60"):
            return "medium"
        else:
            return "low"

    async def _generate_reasoning(
        self,
        strategy,
        objective: str,
        risk_profile: str,
    ) -> str:
        """Generate reasoning for recommendation."""
        reasons = []

        strongest_metric = max(
            ("return", strategy.return_score),
            ("stability", strategy.stability_score),
            ("consistency", strategy.consistency_score),
            ("risk management", strategy.risk_score),
            key=lambda x: x[1],
        )

        reasons.append(
            f"This strategy excels in {strongest_metric[0]} "
            f"(score: {strongest_metric[1]:.0f}/100)"
        )

        if objective == "growth":
            reasons.append("Strong focus on capital appreciation")
        elif objective == "income":
            reasons.append("Emphasis on consistent returns and stability")
        elif objective == "preservation":
            reasons.append("Excellent downside protection")
        else:
            reasons.append("Balanced approach across all metrics")

        if risk_profile == "conservative":
            reasons.append("Appropriate risk level for conservative investors")
        elif risk_profile == "aggressive":
            reasons.append("Suitable for aggressive growth-oriented portfolios")
        else:
            reasons.append("Well-suited for moderate risk tolerance")

        return ". ".join(reasons)

    async def _estimate_annual_return(
        self,
        strategy,
        objective: str,
    ) -> Decimal:
        """Estimate annual return based on strategy score."""
        base_return = strategy.return_score / Decimal("10") * Decimal("0.015")

        if objective == "growth":
            return min(base_return * Decimal("1.2"), Decimal("0.20"))
        elif objective == "income":
            return min(base_return * Decimal("0.8"), Decimal("0.10"))
        elif objective == "preservation":
            return min(base_return * Decimal("0.5"), Decimal("0.05"))
        else:
            return base_return

    async def _estimate_max_drawdown(
        self,
        strategy,
        risk_profile: str,
    ) -> Decimal:
        """Estimate maximum expected drawdown."""
        drawdown_estimate = (Decimal("100") - strategy.risk_score) / Decimal("100") * Decimal("0.40")

        if risk_profile == "conservative":
            return -drawdown_estimate * Decimal("1.2")
        else:
            return -drawdown_estimate

    async def _assess_risk_level(self, strategy) -> str:
        """Assess risk level of strategy."""
        if strategy.risk_score >= Decimal("75"):
            return "low"
        elif strategy.risk_score >= Decimal("50"):
            return "medium"
        else:
            return "high"

    async def get_all_recommendations(
        self,
        limit: Optional[int] = None,
    ) -> List[StrategyRecommendation]:
        """
        Get recommendation history.

        Args:
            limit: Maximum recommendations to return

        Returns:
            Recommendation history
        """
        if limit is None:
            return self.recommendation_history
        return self.recommendation_history[-limit:]

    def get_recommender_status(self) -> Dict:
        """Get recommender status."""
        return {
            "total_recommendations": len(self.recommendation_history),
            "high_confidence": sum(
                1 for r in self.recommendation_history if r.confidence_level == "high"
            ),
            "medium_confidence": sum(
                1 for r in self.recommendation_history if r.confidence_level == "medium"
            ),
            "low_confidence": sum(
                1 for r in self.recommendation_history if r.confidence_level == "low"
            ),
        }


# Singleton
_recommender: Optional[StrategyRecommender] = None


def get_strategy_recommender() -> StrategyRecommender:
    """Get or create singleton StrategyRecommender."""
    global _recommender
    if _recommender is None:
        _recommender = StrategyRecommender()
    return _recommender
