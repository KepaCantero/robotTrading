"""
T6.1: StrategyRecommender - Strategy recommendation engine

Scores and recommends strategies based on:
1. Backtest performance metrics (Sharpe, return, drawdown)
2. Investment objective alignment
3. Risk-adjusted returns
4. Improvement opportunities

Uses objective-driven weighting:
- maximizar_capital: 60% Sharpe + 30% return + 10% Sortino
- maximizar_dividendos: 50% dividend + 30% Sharpe + 20% preservation
- capital_preservation: 50% drawdown_inverse + 40% Sharpe + 10% return
- balanced_growth: 40% Sharpe + 30% return + 30% drawdown_inverse
- income_generation: 50% dividend + 30% consistency + 20% Sharpe
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    ObjectiveWeights,
    RecommendationSuggestion,
    StrategyRecommendation,
    StrategyRecommendationRequest,
    StrategyScore,
)

logger = logging.getLogger(__name__)


class StrategyRecommender:
    """
    Recommends strategies based on objective-driven scoring.

    Applies weights specific to investment objectives and provides
    actionable recommendations for improvement.
    """

    # Objective-specific weights
    OBJECTIVE_WEIGHTS = {
        "maximizar_capital": ObjectiveWeights(
            sharpe_weight=Decimal("0.60"),
            return_weight=Decimal("0.30"),
            drawdown_weight=Decimal("0"),
            sortino_weight=Decimal("0.10"),
        ),
        "maximizar_dividendos": ObjectiveWeights(
            sharpe_weight=Decimal("0.30"),
            return_weight=Decimal("0.20"),
            drawdown_weight=Decimal("0.20"),
            dividend_yield_weight=Decimal("0.50"),
        ),
        "capital_preservation": ObjectiveWeights(
            sharpe_weight=Decimal("0.40"),
            return_weight=Decimal("0.10"),
            drawdown_weight=Decimal("0.50"),
        ),
        "balanced_growth": ObjectiveWeights(
            sharpe_weight=Decimal("0.40"),
            return_weight=Decimal("0.30"),
            drawdown_weight=Decimal("0.30"),
        ),
        "income_generation": ObjectiveWeights(
            sharpe_weight=Decimal("0.20"),
            return_weight=Decimal("0.30"),
            drawdown_weight=Decimal("0.20"),
            dividend_yield_weight=Decimal("0.50"),
            consistency_weight=Decimal("0.30"),
        ),
    }

    # Score thresholds for recommendation status
    SCORE_THRESHOLDS = {
        "STRONG_BUY": Decimal("85"),
        "BUY": Decimal("70"),
        "HOLD": Decimal("50"),
        "REVIEW": Decimal("30"),
        "NOT_RECOMMENDED": Decimal("0"),
    }

    def __init__(self):
        """Initialize strategy recommender."""
        self.recommendation_history: List[StrategyRecommendation] = []
        logger.info("✅ StrategyRecommender initialized")

    async def recommend(
        self,
        request: StrategyRecommendationRequest,
    ) -> StrategyRecommendation:
        """
        Generate strategy recommendation based on backtest results and objective.

        Args:
            request: StrategyRecommendationRequest with metrics and objective

        Returns:
            StrategyRecommendation with score, status, and suggestions
        """
        start_time = datetime.utcnow()

        try:
            # Initialize recommendation
            recommendation = StrategyRecommendation(
                success=True,
                profile_id=request.profile_id,
                objective=request.objective,
            )

            # Get objective weights
            weights = self._get_objective_weights(request.objective)
            recommendation.objective_weights = weights

            # Calculate component scores
            component_scores = self._calculate_component_scores(request, weights)
            recommendation.component_scores = component_scores

            # Calculate overall score
            overall_score = self._calculate_overall_score(component_scores)
            recommendation.overall_score = overall_score

            # Determine recommendation status
            status, confidence = self._determine_recommendation_status(overall_score)
            recommendation.recommendation_status = status
            recommendation.confidence_level = confidence

            # Generate suggestions
            suggestions = self._generate_suggestions(request, component_scores, weights)
            recommendation.suggestions = suggestions

            # Identify strengths and weaknesses
            strengths, weaknesses = self._identify_characteristics(component_scores, weights)
            recommendation.strengths = strengths
            recommendation.weaknesses = weaknesses

            # Store in history
            self.recommendation_history.append(recommendation)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ Recommendation generated for {request.profile_id}: "
                f"score={overall_score:.0f}/100, status={status}, "
                f"elapsed={elapsed_ms:.0f}ms"
            )
            return recommendation

        except Exception as e:
            logger.error(f"❌ Error generating recommendation: {e}")
            return StrategyRecommendation(
                success=False,
                profile_id=request.profile_id,
                objective=request.objective,
                error_message=str(e),
            )

    def _get_objective_weights(self, objective: str) -> ObjectiveWeights:
        """Get weights for objective (default to balanced if not found)."""
        return self.OBJECTIVE_WEIGHTS.get(
            objective,
            self.OBJECTIVE_WEIGHTS["balanced_growth"],
        )

    def _calculate_component_scores(
        self,
        request: StrategyRecommendationRequest,
        weights: ObjectiveWeights,
    ) -> Dict[str, StrategyScore]:
        """Calculate normalized scores for each component."""
        scores = {}

        # Sharpe ratio component (target: 1.5+)
        if weights.sharpe_weight > Decimal("0"):
            sharpe = request.sharpe_ratio or Decimal("0")
            normalized = min(sharpe / Decimal("1.5") * Decimal("100"), Decimal("100"))
            scores["sharpe_ratio"] = StrategyScore(
                metric_name="Sharpe Ratio",
                metric_value=sharpe,
                normalized_score=normalized,
                weight=weights.sharpe_weight,
                contribution=normalized * weights.sharpe_weight,
            )

        # Return component (target: 15%+ annually)
        if weights.return_weight > Decimal("0"):
            ret = request.annual_return_pct or Decimal("0")
            normalized = min(ret / Decimal("15") * Decimal("100"), Decimal("100"))
            scores["annual_return"] = StrategyScore(
                metric_name="Annual Return %",
                metric_value=ret,
                normalized_score=normalized,
                weight=weights.return_weight,
                contribution=normalized * weights.return_weight,
            )

        # Max drawdown component (target: <10%, inverse scoring)
        if weights.drawdown_weight > Decimal("0"):
            drawdown = request.max_drawdown_pct or Decimal("0")
            # Inverse scoring: lower drawdown = higher score
            normalized = max(Decimal("100") - (drawdown * Decimal("2")), Decimal("0"))
            scores["max_drawdown"] = StrategyScore(
                metric_name="Max Drawdown %",
                metric_value=drawdown,
                normalized_score=normalized,
                weight=weights.drawdown_weight,
                contribution=normalized * weights.drawdown_weight,
            )

        # Sortino ratio component (target: 2.0+)
        if weights.sortino_weight > Decimal("0"):
            sortino = request.sortino_ratio or Decimal("0")
            normalized = min(sortino / Decimal("2.0") * Decimal("100"), Decimal("100"))
            scores["sortino_ratio"] = StrategyScore(
                metric_name="Sortino Ratio",
                metric_value=sortino,
                normalized_score=normalized,
                weight=weights.sortino_weight,
                contribution=normalized * weights.sortino_weight,
            )

        # Dividend yield component (target: 4%+)
        if weights.dividend_yield_weight > Decimal("0"):
            dividend = request.dividend_yield_pct or Decimal("0")
            normalized = min(dividend / Decimal("4") * Decimal("100"), Decimal("100"))
            scores["dividend_yield"] = StrategyScore(
                metric_name="Dividend Yield %",
                metric_value=dividend,
                normalized_score=normalized,
                weight=weights.dividend_yield_weight,
                contribution=normalized * weights.dividend_yield_weight,
            )

        # Win rate component (consistency proxy, target: 55%+)
        if weights.consistency_weight > Decimal("0"):
            win_rate = request.win_rate_pct or Decimal("0")
            normalized = min(win_rate / Decimal("55") * Decimal("100"), Decimal("100"))
            scores["win_rate"] = StrategyScore(
                metric_name="Win Rate %",
                metric_value=win_rate,
                normalized_score=normalized,
                weight=weights.consistency_weight,
                contribution=normalized * weights.consistency_weight,
            )

        return scores

    def _calculate_overall_score(
        self,
        component_scores: Dict[str, StrategyScore],
    ) -> Decimal:
        """Calculate weighted overall score (0-100)."""
        if not component_scores:
            return Decimal("0")

        total_contribution = sum(score.contribution for score in component_scores.values())

        # Normalize by sum of weights
        total_weight = sum(score.weight for score in component_scores.values())
        if total_weight > Decimal("0"):
            return total_contribution / total_weight
        return Decimal("0")

    def _determine_recommendation_status(
        self,
        overall_score: Decimal,
    ) -> Tuple[str, str]:
        """Determine recommendation status and confidence based on score."""
        if overall_score >= self.SCORE_THRESHOLDS["STRONG_BUY"]:
            return "STRONG_BUY", "high"
        elif overall_score >= self.SCORE_THRESHOLDS["BUY"]:
            return "BUY", "high"
        elif overall_score >= self.SCORE_THRESHOLDS["HOLD"]:
            return "HOLD", "medium"
        elif overall_score >= self.SCORE_THRESHOLDS["REVIEW"]:
            return "REVIEW", "medium"
        else:
            return "NOT_RECOMMENDED", "low"

    def _generate_suggestions(
        self,
        request: StrategyRecommendationRequest,
        component_scores: Dict[str, StrategyScore],
        weights: ObjectiveWeights,
    ) -> List[RecommendationSuggestion]:
        """Generate improvement suggestions based on weak components."""
        suggestions = []

        # Check Sharpe ratio
        if "sharpe_ratio" in component_scores:
            sharpe_score = component_scores["sharpe_ratio"]
            if sharpe_score.normalized_score < Decimal("70"):
                suggestions.append(
                    RecommendationSuggestion(
                        suggestion_text=(
                            f"Improve risk-adjusted returns: Sharpe ratio is "
                            f"{sharpe_score.metric_value:.2f}, target is 1.5+"
                        ),
                        priority="high" if sharpe_score.weight > Decimal("0.30") else "medium",
                        estimated_impact="+0.3 Sharpe ratio with parameter tuning",
                    )
                )

        # Check returns
        if "annual_return" in component_scores:
            return_score = component_scores["annual_return"]
            if return_score.normalized_score < Decimal("70"):
                suggestions.append(
                    RecommendationSuggestion(
                        suggestion_text=(
                            f"Increase returns: {return_score.metric_value:.1f}% annual, "
                            f"target is 15%+"
                        ),
                        priority="high" if return_score.weight > Decimal("0.30") else "medium",
                        estimated_impact="+5% annual return with optimization",
                    )
                )

        # Check drawdown
        if "max_drawdown" in component_scores:
            drawdown_score = component_scores["max_drawdown"]
            if drawdown_score.normalized_score < Decimal("70"):
                suggestions.append(
                    RecommendationSuggestion(
                        suggestion_text=(
                            f"Reduce downside risk: Max drawdown is "
                            f"{drawdown_score.metric_value:.1f}%, target is <10%"
                        ),
                        priority="high" if drawdown_score.weight > Decimal("0.30") else "medium",
                        estimated_impact="Reduce drawdown by 5% with risk limits",
                    )
                )

        # Check Sortino ratio
        if "sortino_ratio" in component_scores:
            sortino_score = component_scores["sortino_ratio"]
            if sortino_score.normalized_score < Decimal("70"):
                suggestions.append(
                    RecommendationSuggestion(
                        suggestion_text=(
                            f"Improve downside-risk-adjusted returns: Sortino ratio is "
                            f"{sortino_score.metric_value:.2f}, target is 2.0+"
                        ),
                        priority="medium",
                        estimated_impact="+0.5 Sortino ratio with downside protection",
                    )
                )

        # Check dividend yield
        if "dividend_yield" in component_scores:
            dividend_score = component_scores["dividend_yield"]
            if dividend_score.normalized_score < Decimal("50"):
                suggestions.append(
                    RecommendationSuggestion(
                        suggestion_text=(
                            f"Increase dividend income: Current yield is "
                            f"{dividend_score.metric_value:.1f}%, target is 4%+"
                        ),
                        priority="high" if dividend_score.weight > Decimal("0.30") else "low",
                        estimated_impact="+2% dividend yield with sector focus",
                    )
                )

        return suggestions[:3]  # Limit to top 3 suggestions

    def _identify_characteristics(
        self,
        component_scores: Dict[str, StrategyScore],
        weights: ObjectiveWeights,
    ) -> Tuple[List[str], List[str]]:
        """Identify strategy strengths and weaknesses."""
        strengths = []
        weaknesses = []

        for metric_name, score in component_scores.items():
            if score.normalized_score >= Decimal("80"):
                metric_readable = score.metric_name
                strengths.append(f"Strong {metric_readable} performance ({score.metric_value:.2f})")
            elif score.normalized_score < Decimal("40"):
                metric_readable = score.metric_name
                weaknesses.append(
                    f"Weak {metric_readable} ({score.metric_value:.2f}) - needs improvement"
                )

        return strengths, weaknesses

    async def get_recommendation_history(
        self,
        limit: Optional[int] = None,
    ) -> List[StrategyRecommendation]:
        """Get recommendation history."""
        results = self.recommendation_history
        if limit:
            results = results[-limit:]
        return results

    def get_recommender_status(self) -> Dict:
        """Get recommender operational status."""
        successful = sum(1 for r in self.recommendation_history if r.success)
        total = len(self.recommendation_history)

        # Calculate average score
        avg_score = Decimal("0")
        if successful > 0:
            scores = [
                r.overall_score
                for r in self.recommendation_history
                if r.success and r.overall_score > Decimal("0")
            ]
            if scores:
                avg_score = sum(scores) / len(scores)

        return {
            "total_recommendations": total,
            "successful_recommendations": successful,
            "success_rate": successful / max(1, total),
            "average_score": float(avg_score),
            "history_size": total,
        }


# Singleton
_recommender: Optional[StrategyRecommender] = None


def get_strategy_recommender() -> StrategyRecommender:
    """Get or create singleton StrategyRecommender."""
    global _recommender
    if _recommender is None:
        _recommender = StrategyRecommender()
    return _recommender
