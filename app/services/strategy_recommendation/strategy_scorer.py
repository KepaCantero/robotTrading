"""
T19.1.1: StrategyScorer - Scores strategies based on performance metrics and objectives

Calculates composite scores using objective-weighted metrics.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""

    strategy_name: str
    total_return: Decimal  # 10% = 0.10
    annual_return: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal  # Negative number
    win_rate: Decimal  # 0-1
    profit_factor: Decimal
    num_trades: int
    backtest_period_days: int


@dataclass
class StrategyScore:
    """Composite score for a strategy."""

    strategy_name: str
    overall_score: Decimal  # 0-100
    return_score: Decimal  # 0-100
    risk_score: Decimal  # 0-100
    stability_score: Decimal  # 0-100
    consistency_score: Decimal  # 0-100
    objective: str
    confidence: str  # high, medium, low


class StrategyScorer:
    """
    Scores strategies based on performance metrics and user objectives.

    Features:
    - Objective-driven scoring (growth, income, preservation, balanced)
    - Multi-dimensional evaluation (return, risk, stability, consistency)
    - Confidence assessment
    - Customizable weighting
    """

    def __init__(self):
        """Initialize strategy scorer."""
        self.score_history: Dict[str, StrategyScore] = {}
        logger.info("✅ StrategyScorer initialized")

    async def score_strategy(
        self,
        metrics: StrategyMetrics,
        objective: str = "balanced",
    ) -> StrategyScore:
        """
        Score a strategy based on metrics and objective.

        Args:
            metrics: StrategyMetrics for the strategy
            objective: Investment objective (growth, income, preservation, balanced)

        Returns:
            StrategyScore with composite score
        """
        # Calculate individual scores
        return_score = await self._calculate_return_score(metrics)
        risk_score = await self._calculate_risk_score(metrics)
        stability_score = await self._calculate_stability_score(metrics)
        consistency_score = await self._calculate_consistency_score(metrics)

        # Get objective-specific weights
        weights = self._get_objective_weights(objective)

        # Calculate weighted overall score
        overall_score = (
            return_score * weights["return"]
            + risk_score * weights["risk"]
            + stability_score * weights["stability"]
            + consistency_score * weights["consistency"]
        )

        # Assess confidence
        confidence = await self._assess_confidence(metrics)

        score = StrategyScore(
            strategy_name=metrics.strategy_name,
            overall_score=overall_score,
            return_score=return_score,
            risk_score=risk_score,
            stability_score=stability_score,
            consistency_score=consistency_score,
            objective=objective,
            confidence=confidence,
        )

        self.score_history[metrics.strategy_name] = score
        logger.info(f"✅ Scored {metrics.strategy_name}: {overall_score:.1f}/100 ({objective})")
        return score

    async def _calculate_return_score(self, metrics: StrategyMetrics) -> Decimal:
        """Calculate return performance score (0-100)."""
        # Normalize annual return: 0% = 0, 20% = 100
        return_pct = metrics.annual_return * Decimal("100")
        score = min(return_pct * Decimal("5"), Decimal("100"))  # 20% = 100
        return max(Decimal("0"), score)

    async def _calculate_risk_score(self, metrics: StrategyMetrics) -> Decimal:
        """Calculate risk score (0-100, higher is better = lower risk)."""
        # Invert max_drawdown: -10% = 90, -50% = 50
        # Treat as positive internally
        drawdown_abs = abs(metrics.max_drawdown)

        # 0% drawdown = 100, 50% drawdown = 50
        if drawdown_abs == 0:
            return Decimal("100")
        if drawdown_abs >= Decimal("1"):
            return Decimal("0")

        score = Decimal("100") * (Decimal("1") - drawdown_abs)
        return max(Decimal("0"), min(Decimal("100"), score))

    async def _calculate_stability_score(self, metrics: StrategyMetrics) -> Decimal:
        """Calculate strategy stability score based on Sharpe ratio (0-100)."""
        # Sharpe ratio of 1.0 = 50, 2.0 = 100, 0 = 0
        sharpe_normalized = metrics.sharpe_ratio * Decimal("50")
        score = min(sharpe_normalized, Decimal("100"))
        return max(Decimal("0"), score)

    async def _calculate_consistency_score(self, metrics: StrategyMetrics) -> Decimal:
        """Calculate consistency score based on win rate and profit factor (0-100)."""
        # Win rate component (50% = 50, 60% = 60, 70% = 70)
        win_rate_score = metrics.win_rate * Decimal("100")

        # Profit factor component (1.5 = 50, 3.0 = 100)
        pf_score = min(metrics.profit_factor * Decimal("50"), Decimal("100"))

        # Average both components
        consistency = (win_rate_score + pf_score) / Decimal("2")
        return max(Decimal("0"), min(Decimal("100"), consistency))

    def _get_objective_weights(self, objective: str) -> Dict[str, Decimal]:
        """Get metric weights based on objective."""
        weights_map = {
            "growth": {
                "return": Decimal("0.40"),
                "risk": Decimal("0.30"),
                "stability": Decimal("0.20"),
                "consistency": Decimal("0.10"),
            },
            "income": {
                "return": Decimal("0.20"),
                "risk": Decimal("0.40"),
                "stability": Decimal("0.20"),
                "consistency": Decimal("0.20"),
            },
            "preservation": {
                "return": Decimal("0.10"),
                "risk": Decimal("0.50"),
                "stability": Decimal("0.25"),
                "consistency": Decimal("0.15"),
            },
            "balanced": {
                "return": Decimal("0.25"),
                "risk": Decimal("0.25"),
                "stability": Decimal("0.25"),
                "consistency": Decimal("0.25"),
            },
        }
        return weights_map.get(objective, weights_map["balanced"])

    async def _assess_confidence(self, metrics: StrategyMetrics) -> str:
        """Assess confidence level in the score."""
        # High confidence: many trades, long backtest, good metrics
        if metrics.num_trades >= 50 and metrics.backtest_period_days >= 252:
            if metrics.sharpe_ratio >= Decimal("1.0"):
                return "high"
            elif metrics.sharpe_ratio >= Decimal("0.5"):
                return "medium"
            else:
                return "low"
        elif metrics.num_trades >= 20 and metrics.backtest_period_days >= 126:
            return "medium"
        else:
            return "low"

    def get_scorer_status(self) -> Dict:
        """Get scorer status."""
        return {
            "strategies_scored": len(self.score_history),
        }


# Singleton
_scorer: Optional[StrategyScorer] = None


def get_strategy_scorer() -> StrategyScorer:
    """Get or create singleton StrategyScorer."""
    global _scorer
    if _scorer is None:
        _scorer = StrategyScorer()

    return _scorer
