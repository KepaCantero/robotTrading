"""
T6.1: StrategyRecommender - Recommend best strategy based on objective-driven weighting

Scores backtest results using objective-specific metrics and confidence levels.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ObjectiveType(str, Enum):
    """Investment objectives for weighting strategy."""
    MAXIMIZAR_CAPITAL = "maximizar_capital"
    MAXIMIZAR_DIVIDENDOS = "maximizar_dividendos"
    CAPITAL_PRESERVATION = "capital_preservation"
    BALANCED_GROWTH = "balanced_growth"
    INCOME_GENERATION = "income_generation"


class ConfidenceLevel(str, Enum):
    """Confidence levels for recommendations."""
    VERY_HIGH = "VERY_HIGH"  # 90-100
    HIGH = "HIGH"  # 75-89
    MODERATE = "MODERATE"  # 60-74
    LOW = "LOW"  # 40-59
    VERY_LOW = "VERY_LOW"  # <40


@dataclass
class RecommendationDetails:
    """Details of recommendation rationale and suggestions."""
    strengths: List[str]  # What the strategy does well
    weaknesses: List[str]  # Areas for improvement
    suggestions: List[str]  # Actionable improvements
    risk_assessment: str  # Risk level analysis
    fit_analysis: str  # How well strategy fits objective


@dataclass
class StrategyRecommendation:
    """Recommendation for a strategy based on backtest results."""
    recommendation: str  # "APPROVED", "CONDITIONAL", "REVIEW", "REJECTED"
    score: float  # 0-100 recommendation score
    confidence_level: str  # ConfidenceLevel enum
    objective_weights: Dict[str, float]  # Weights used for scoring
    metric_scores: Dict[str, float]  # Individual metric scores
    details: RecommendationDetails
    summary: str  # Human-readable summary


class StrategyRecommender:
    """
    T6.1: Recommender for strategies based on objective-driven weighting.

    Weights different performance metrics based on investment objective:
    - maximizar_capital: 60% Sharpe + 30% total_return + 10% Sortino
    - maximizar_dividendos: 50% dividend_yield + 30% Sharpe + 20% capital_preservation
    - capital_preservation: 50% max_drawdown_inverse + 40% Sharpe + 10% return
    - balanced_growth: 40% Sharpe + 30% return + 30% drawdown_inverse
    - income_generation: 50% dividend_yield + 30% consistency + 20% Sharpe
    """

    # Objective-driven weighting schemas
    WEIGHTING_SCHEMAS = {
        ObjectiveType.MAXIMIZAR_CAPITAL: {
            "sharpe_ratio": 0.60,
            "total_return": 0.30,
            "sortino_ratio": 0.10,
        },
        ObjectiveType.MAXIMIZAR_DIVIDENDOS: {
            "dividend_yield": 0.50,
            "sharpe_ratio": 0.30,
            "capital_preservation": 0.20,
        },
        ObjectiveType.CAPITAL_PRESERVATION: {
            "max_drawdown_inverse": 0.50,
            "sharpe_ratio": 0.40,
            "total_return": 0.10,
        },
        ObjectiveType.BALANCED_GROWTH: {
            "sharpe_ratio": 0.40,
            "total_return": 0.30,
            "max_drawdown_inverse": 0.30,
        },
        ObjectiveType.INCOME_GENERATION: {
            "dividend_yield": 0.50,
            "consistency": 0.30,
            "sharpe_ratio": 0.20,
        },
    }

    # Thresholds for recommendations
    SCORE_THRESHOLDS = {
        "approved": 75.0,  # Score >= 75
        "conditional": 60.0,  # Score 60-74
        "review": 40.0,  # Score 40-59
        "rejected": 0.0,  # Score < 40
    }

    def __init__(self):
        """Initialize StrategyRecommender."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ StrategyRecommender initialized")

    async def recommend(
        self,
        strategy_name: str,
        backtest_result: Dict,
        investment_profile,
    ) -> StrategyRecommendation:
        """
        Generate recommendation for a strategy.

        Args:
            strategy_name: Name of the strategy being evaluated
            backtest_result: Dict with backtest metrics (Sharpe, return, drawdown, etc.)
            investment_profile: InvestmentProfile with objetivo_inversion

        Returns:
            StrategyRecommendation with score, confidence, and details
        """
        try:
            # Get objective type
            objective = investment_profile.objetivo_inversion
            if isinstance(objective, str):
                objective = ObjectiveType(objective)

            # Get weighting schema for objective
            weights = self.WEIGHTING_SCHEMAS.get(objective)
            if not weights:
                self.logger.warning(f"⚠️  Unknown objective: {objective}, using default balanced")
                weights = self.WEIGHTING_SCHEMAS[ObjectiveType.BALANCED_GROWTH]

            # Calculate metric scores
            metric_scores = await self._calculate_metric_scores(backtest_result)

            # Calculate weighted recommendation score
            recommendation_score = await self._calculate_score(metric_scores, weights)

            # Determine recommendation and confidence
            recommendation, confidence = self._determine_recommendation(recommendation_score)

            # Generate details
            details = await self._generate_details(
                metric_scores,
                recommendation_score,
                objective,
                backtest_result
            )

            # Generate summary
            summary = self._generate_summary(
                recommendation_score,
                confidence,
                objective,
                backtest_result
            )

            result = StrategyRecommendation(
                recommendation=recommendation,
                score=recommendation_score,
                confidence_level=confidence,
                objective_weights=weights,
                metric_scores=metric_scores,
                details=details,
                summary=summary
            )

            self.logger.info(
                f"📊 Recommendation for {strategy_name}: {recommendation} "
                f"(score: {recommendation_score:.1f}, confidence: {confidence})"
            )
            return result

        except Exception as e:
            self.logger.error(f"❌ Error generating recommendation: {e}")
            raise

    async def _calculate_metric_scores(self, backtest_result: Dict) -> Dict[str, float]:
        """
        Calculate normalized metric scores (0-100) from backtest results.

        Handles different metric types:
        - Sharpe ratio: Higher is better
        - Returns: Higher is better
        - Drawdown: Lower is better (inverted)
        - Dividend yield: Higher is better
        - Consistency: Higher is better
        """
        scores = {}

        # Sharpe ratio normalization (assume -1 to 3 range)
        sharpe = self._safe_float(backtest_result.get("sharpe_ratio", 0.0))
        scores["sharpe_ratio"] = min(100, max(0, (sharpe + 1) / 4 * 100))

        # Total return normalization (0% to 50% annual range)
        total_return = self._safe_float(backtest_result.get("total_return", 0.0))
        scores["total_return"] = min(100, max(0, total_return / 0.50 * 100))

        # Sortino ratio (similar to Sharpe but downside-focused)
        sortino = self._safe_float(backtest_result.get("sortino_ratio", 0.0))
        scores["sortino_ratio"] = min(100, max(0, (sortino + 1) / 4 * 100))

        # Max drawdown (lower is better, so invert)
        max_drawdown = self._safe_float(backtest_result.get("max_drawdown", -0.1))
        scores["max_drawdown_inverse"] = min(100, max(0, (1 + max_drawdown) * 100))

        # Dividend yield (0% to 10% range)
        dividend_yield = self._safe_float(backtest_result.get("dividend_yield", 0.0))
        scores["dividend_yield"] = min(100, max(0, dividend_yield / 0.10 * 100))

        # Win rate (consistency)
        win_rate = self._safe_float(backtest_result.get("win_rate", 0.5))
        scores["consistency"] = win_rate * 100  # Already 0-100 scale

        # Capital preservation (inverse of drawdown)
        scores["capital_preservation"] = scores["max_drawdown_inverse"]

        return scores

    async def _calculate_score(
        self,
        metric_scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate weighted recommendation score.

        Args:
            metric_scores: Individual metric scores (0-100)
            weights: Weights for each metric (sum to 1.0)

        Returns:
            Weighted score (0-100)
        """
        total_score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            metric_score = metric_scores.get(metric, 0.0)
            total_score += metric_score * weight
            total_weight += weight

        # Normalize if weights don't sum to 1.0
        if total_weight > 0:
            return total_score / total_weight
        return 0.0

    def _determine_recommendation(self, score: float) -> tuple:
        """
        Determine recommendation status and confidence level based on score.

        Args:
            score: Recommendation score (0-100)

        Returns:
            Tuple of (recommendation, confidence_level)
        """
        if score >= self.SCORE_THRESHOLDS["approved"]:
            recommendation = "APPROVED"
            if score >= 90:
                confidence = ConfidenceLevel.VERY_HIGH.value
            else:
                confidence = ConfidenceLevel.HIGH.value

        elif score >= self.SCORE_THRESHOLDS["conditional"]:
            recommendation = "CONDITIONAL"
            confidence = ConfidenceLevel.MODERATE.value

        elif score >= self.SCORE_THRESHOLDS["review"]:
            recommendation = "REVIEW"
            confidence = ConfidenceLevel.LOW.value

        else:
            recommendation = "REJECTED"
            confidence = ConfidenceLevel.VERY_LOW.value

        return recommendation, confidence

    async def _generate_details(
        self,
        metric_scores: Dict[str, float],
        score: float,
        objective,
        backtest_result: Dict
    ) -> RecommendationDetails:
        """Generate detailed analysis of recommendation."""
        strengths = []
        weaknesses = []
        suggestions = []

        # Analyze metric strengths and weaknesses
        if metric_scores.get("sharpe_ratio", 0) > 70:
            strengths.append("Strong risk-adjusted returns (high Sharpe ratio)")
        else:
            weaknesses.append("Low risk-adjusted returns")
            suggestions.append("Consider risk management improvements")

        if metric_scores.get("total_return", 0) > 70:
            strengths.append("Excellent absolute returns")
        elif metric_scores.get("total_return", 0) < 40:
            weaknesses.append("Below-average returns")
            suggestions.append("Optimize entry/exit logic for higher returns")

        if metric_scores.get("max_drawdown_inverse", 0) > 80:
            strengths.append("Excellent capital preservation")
        elif metric_scores.get("max_drawdown_inverse", 0) < 40:
            weaknesses.append("High drawdown risk")
            suggestions.append("Implement stronger stop-loss or position sizing")

        # Objective-specific analysis
        if objective == ObjectiveType.MAXIMIZAR_CAPITAL:
            if metric_scores.get("sharpe_ratio", 0) < 50:
                suggestions.append("Improve Sharpe ratio for capital maximization")
        elif objective == ObjectiveType.CAPITAL_PRESERVATION:
            if metric_scores.get("max_drawdown_inverse", 0) < 70:
                suggestions.append("Strengthen capital preservation (reduce drawdowns)")

        # Risk assessment
        if score >= 75:
            risk_assessment = "Low to moderate risk - strategy is robust"
        elif score >= 60:
            risk_assessment = "Moderate risk - improvements needed"
        else:
            risk_assessment = "High risk - significant improvements required"

        # Fit analysis
        fit_scores = {
            ObjectiveType.MAXIMIZAR_CAPITAL: metric_scores.get("sharpe_ratio", 0),
            ObjectiveType.CAPITAL_PRESERVATION: metric_scores.get("max_drawdown_inverse", 0),
            ObjectiveType.INCOME_GENERATION: metric_scores.get("dividend_yield", 0),
            ObjectiveType.BALANCED_GROWTH: (
                metric_scores.get("sharpe_ratio", 0) +
                metric_scores.get("total_return", 0) +
                metric_scores.get("max_drawdown_inverse", 0)
            ) / 3,
            ObjectiveType.MAXIMIZAR_DIVIDENDOS: metric_scores.get("dividend_yield", 0),
        }

        fit_score = fit_scores.get(objective, score)
        if fit_score >= 75:
            fit_analysis = "Excellent fit for the selected objective"
        elif fit_score >= 60:
            fit_analysis = "Good fit for the selected objective"
        else:
            fit_analysis = "Moderate to poor fit - consider alternative strategies"

        return RecommendationDetails(
            strengths=strengths or ["Strategy shows promise"],
            weaknesses=weaknesses or ["No critical weaknesses identified"],
            suggestions=suggestions or ["Continue monitoring performance"],
            risk_assessment=risk_assessment,
            fit_analysis=fit_analysis
        )

    def _generate_summary(
        self,
        score: float,
        confidence: str,
        objective,
        backtest_result: Dict
    ) -> str:
        """Generate human-readable recommendation summary."""
        return (
            f"Strategy achieves {score:.1f}/100 for {objective.value.replace('_', ' ')} "
            f"with {confidence} confidence. "
            f"Annual return: {self._safe_float(backtest_result.get('total_return', 0))*100:.1f}%, "
            f"Sharpe: {self._safe_float(backtest_result.get('sharpe_ratio', 0)):.2f}."
        )

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        return 0.0
