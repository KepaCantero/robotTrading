from __future__ import annotations

"""Data models for Hurst Exponent analysis.

This module contains all data classes and enums used throughout
the hurst_analysis module. All models are immutable value objects
following the Single Responsibility Principle.
"""


import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """
    Market regime classification based on Hurst Exponent.


    According to Ernest Chan (Algorithmic Trading, Rule 2.2):
    - MEAN_REVERTING: H < 0.5 (anti-persistent behavior)
    - RANDOM_WALK: H approx 0.5 (efficient market, no predictability)
    - TRENDING: H > 0.5 (persistent behavior)

    Attributes:
        MEAN_REVERTING: Market exhibits mean-reversion
        RANDOM_WALK: Market follows random walk
        TRENDING: Market exhibits trending behavior
    """

    MEAN_REVERTING = "mean_reverting"
    RANDOM_WALK = "random_walk"
    TRENDING = "trending"


class StrategyRecommendation(Enum):
    """
    Trading strategy recommendations based on Hurst Exponent.

    Attributes:
        MEAN_REVERSION: Use mean reversion strategies (pairs trading, stat arb)
        NEUTRAL: Use market-neutral strategies (market making, arbitrage)
        TREND_FOLLOWING: Use trend following strategies (momentum, breakout)
    """

    MEAN_REVERSION = "mean_reversion"
    NEUTRAL = "neutral"
    TREND_FOLLOWING = "trend_following"


@dataclass(frozen=True)
class HurstResult:
    """
    Immutable result object from Hurst Exponent analysis.

    This value object contains all analysis results and cannot be mutated
    after creation, ensuring data integrity throughout the system.

    Attributes:
        hurst_exponent: Calculated Hurst Exponent (H), range [0, 1]
        regime: Market regime classification
        strategy: Recommended trading strategy
        confidence: Statistical confidence level [0, 1]
        method: Calculation method used (e.g., "rs", "variance", "agg_var")
        std_error: Standard error of the estimate (optional)
        p_value: Statistical significance p-value (optional)
        rs_values: R/S values used for regression (optional)
        window_sizes: Window sizes used in analysis (optional)
    """

    hurst_exponent: float
    regime: MarketRegime
    strategy: StrategyRecommendation
    confidence: float
    method: str
    std_error: float | None = None
    p_value: float | None = None
    rs_values: list[float] | None = None
    window_sizes: list[int] | None = None


@dataclass(frozen=True)
class RegimeChange:
    """
    Immutable detection of regime change over time.

    This value object represents a detected change in market regime
    with full provenance information.

    Attributes:
        timestamp: When the change was detected
        old_regime: Previous market regime
        new_regime: Current market regime
        old_hurst: Previous Hurst exponent value
        new_hurst: Current Hurst exponent value
        confidence: Confidence in the change detection [0, 1]
    """

    timestamp: datetime
    old_regime: MarketRegime
    new_regime: MarketRegime
    old_hurst: float
    new_hurst: float
    confidence: float


logger.debug(
    "HurstAnalysis models loaded",
    extra={
        "component": "hurst_analysis_models",
        "operation": "module_init",
        "models": [
            "MarketRegime",
            "StrategyRecommendation",
            "HurstResult",
            "RegimeChange",
        ],
    },
)
