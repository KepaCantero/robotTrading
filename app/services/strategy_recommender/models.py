"""
T6.1: StrategyRecommender - Models

Data models for strategy recommendation requests and results.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveWeights:
    """Weights for objective-driven scoring."""

    sharpe_weight: Decimal
    return_weight: Decimal
    drawdown_weight: Decimal
    sortino_weight: Decimal = Decimal("0")
    dividend_yield_weight: Decimal = Decimal("0")
    consistency_weight: Decimal = Decimal("0")


@dataclass
class StrategyScore:
    """Score for a single strategy metric."""

    metric_name: str
    metric_value: Decimal
    normalized_score: Decimal  # 0-100
    weight: Decimal  # Weight in overall score
    contribution: Decimal  # weighted_score = contribution to total


@dataclass
class RecommendationSuggestion:
    """Suggestion for strategy improvement."""

    suggestion_text: str
    priority: Literal["high", "medium", "low"]
    estimated_impact: str  # e.g., "+0.5 Sharpe ratio", "Reduce drawdown by 5%"


@dataclass
class StrategyRecommendationRequest:
    """Request for strategy recommendation."""

    profile_id: str
    input_id: str
    objective: str  # maximizar_capital, dividendos, preservation, growth, income
    backtest_result: Optional[Dict] = None
    sharpe_ratio: Optional[Decimal] = None
    annual_return_pct: Optional[Decimal] = None
    max_drawdown_pct: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    win_rate_pct: Optional[Decimal] = None
    dividend_yield_pct: Optional[Decimal] = None


@dataclass
class StrategyRecommendation:
    """Result of strategy recommendation."""

    success: bool
    profile_id: str
    recommendation_timestamp: datetime = field(default_factory=datetime.utcnow)

    # Recommendation details
    objective: str = ""
    overall_score: Decimal = Decimal("0")  # 0-100
    recommendation_status: str = "PENDING"  # STRONG_BUY, BUY, HOLD, REVIEW, NOT_RECOMMENDED
    confidence_level: str = "medium"  # high, medium, low

    # Component scores
    component_scores: Dict[str, StrategyScore] = field(default_factory=dict)

    # Recommendations
    suggestions: List[RecommendationSuggestion] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Detailed analysis
    objective_weights: Optional[ObjectiveWeights] = None
    error_message: Optional[str] = None


logger.debug(
    "StrategyRecommender models loaded",
    extra={
        "component": "strategy_recommender_models",
        "operation": "module_init",
        "models": [
            "ObjectiveWeights",
            "StrategyScore",
            "RecommendationSuggestion",
            "StrategyRecommendationRequest",
            "StrategyRecommendation",
        ],
    },
)
