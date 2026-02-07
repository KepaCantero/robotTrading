"""
Data models for the Validation module (FASE 5.3).

This module defines all data structures for walk-forward validation,
overfitting detection, regime detection, and parameter stability analysis.

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "Advances in Financial Machine Learning" - Marcos López de Prado
    - "Expected Returns" - Antti Ilmanen
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

try:
    pass

    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback to standard library
    PYDANTIC_AVAILABLE = False

    from dataclasses import field


class OverfittingLevel(str, Enum):
    """Severity levels for overfitting detection."""

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class StabilityLevel(str, Enum):
    """Stability levels for parameter analysis."""

    STABLE = "stable"
    MODERATE = "moderate"
    UNSTABLE = "unstable"


class RegimeType(str, Enum):
    """Market regime types."""

    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class VolatilityRegime(str, Enum):
    """Volatility regime types."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TrendRegime(str, Enum):
    """Trend regime types."""

    TREND = "trend"
    RANGE = "range"
    TRANSITION = "transition"


@dataclass
class WalkForwardConfig:
    """
    Configuration for walk-forward validation.

    Attributes:
        train_period_months: Number of months for in-sample training period
        test_period_months: Number of months for out-of-sample testing period
        step_months: Number of months to roll forward for each window
        min_observations: Minimum number of observations required for training
        allow_overlap: Whether to allow overlap between windows
        rebalance_frequency: How often to rebalance during test period
        warmup_period: Number of days for warmup period
    """

    train_period_months: int = field(default=24)
    test_period_months: int = field(default=6)
    step_months: int = field(default=3)
    min_observations: int = field(default=252)
    allow_overlap: bool = field(default=True)
    rebalance_frequency: str = field(default="monthly")  # daily, weekly, monthly
    warmup_period: int = field(default=20)


@dataclass
class PeriodResult:
    """
    Results for a single IS/OS period.

    Attributes:
        period_id: Unique identifier for this period
        start_date: Start date of the period
        end_date: End date of the period
        is_in_sample: Whether this is in-sample or out-of-sample
        total_trades: Number of trades executed
        total_return: Total return percentage
        sharpe_ratio: Sharpe ratio
        max_drawdown: Maximum drawdown
        win_rate: Win rate percentage
        profit_factor: Profit factor
        parameters: Parameter values used for this period
        trades: List of trade records
        equity_curve: Daily equity values
    """

    period_id: UUID = field(default_factory=uuid4)
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    is_in_sample: bool = field(default=True)
    total_trades: int = field(default=0)
    total_return: Decimal = field(default=Decimal("0"))
    sharpe_ratio: Optional[Decimal] = field(default=None)
    max_drawdown: Decimal = field(default=Decimal("0"))
    win_rate: Decimal = field(default=Decimal("0"))
    profit_factor: Optional[Decimal] = field(default=None)
    parameters: Dict[str, Any] = field(default_factory=dict)
    trades: List[Any] = field(default_factory=list)
    equity_curve: List[Tuple[date, Decimal]] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """
    Complete walk-forward validation results.

    Attributes:
        is_results: List of in-sample period results
        os_results: List of out-of-sample period results
        is_performance: Aggregate in-sample performance metrics
        os_performance: Aggregate out-of-sample performance metrics
        is_os_ratio: OS/IS performance ratio (degradation metric)
        consistency_score: How consistent OS performance is across periods (0-100)
        num_periods: Number of IS/OS periods
        total_days: Total number of days tested
        recommendations: List of actionable recommendations
    """

    is_results: List[PeriodResult] = field(default_factory=list)
    os_results: List[PeriodResult] = field(default_factory=list)
    is_performance: Dict[str, Any] = field(default_factory=dict)
    os_performance: Dict[str, Any] = field(default_factory=dict)
    is_os_ratio: Decimal = field(default=Decimal("0"))
    consistency_score: Decimal = field(default=Decimal("0"))
    num_periods: int = field(default=0)
    total_days: int = field(default=0)
    recommendations: List[str] = field(default_factory=list)

    def get_degradation_summary(self) -> Dict[str, Any]:
        """Get summary of performance degradation from IS to OS."""
        if not self.is_performance or not self.os_performance:
            return {}

        is_sharpe = self.is_performance.get("sharpe_ratio", Decimal("0"))
        os_sharpe = self.os_performance.get("sharpe_ratio", Decimal("0"))
        is_return = self.is_performance.get("total_return", Decimal("0"))
        os_return = self.os_performance.get("total_return", Decimal("0"))

        sharpe_degradation = (os_sharpe / is_sharpe) if is_sharpe != 0 else Decimal("0")
        return_degradation = (os_return / is_return) if is_return != 0 else Decimal("0")

        return {
            "sharpe_degradation": sharpe_degradation,
            "return_degradation": return_degradation,
            "avg_degradation": (sharpe_degradation + return_degradation) / 2,
        }


@dataclass
class OverfittingMetrics:
    """
    Metrics for detecting overfitting.

    Attributes:
        is_sharpe: In-sample Sharpe ratio
        os_sharpe: Out-of-sample Sharpe ratio
        degradation_ratio: OS/IS Sharpe ratio
        is_return: In-sample total return
        os_return: Out-of-sample total return
        return_degradation: OS/IS return ratio
        overfitting_probability: Probability of overfitting (0-1)
        overfitting_level: Severity level of overfitting
        recommendations: List of recommendations to address overfitting
        whites_reality_pvalue: P-value from White's reality check
        mcs_pvalue: P-value from MCS test
        parameter_stability_score: Parameter stability score (0-100)
    """

    is_sharpe: Decimal = field(default=Decimal("0"))
    os_sharpe: Decimal = field(default=Decimal("0"))
    degradation_ratio: Decimal = field(default=Decimal("0"))
    is_return: Decimal = field(default=Decimal("0"))
    os_return: Decimal = field(default=Decimal("0"))
    return_degradation: Decimal = field(default=Decimal("0"))
    overfitting_probability: float = field(default=0.0)
    overfitting_level: OverfittingLevel = field(default=OverfittingLevel.NONE)
    recommendations: List[str] = field(default_factory=list)
    whites_reality_pvalue: Optional[float] = field(default=None)
    mcs_pvalue: Optional[float] = field(default=None)
    parameter_stability_score: Decimal = field(default=Decimal("100"))

    def is_overfitted(self) -> bool:
        """Check if strategy shows signs of overfitting."""
        return self.overfitting_level in [
            OverfittingLevel.MODERATE,
            OverfittingLevel.SEVERE,
        ]


@dataclass
class MarketRegime:
    """
    Detected market regime.

    Attributes:
        regime_type: Type of market regime (bull/bear/neutral)
        volatility_regime: Volatility regime (low/normal/high)
        trend_regime: Trend regime (trend/range/transition)
        confidence: Confidence level of regime detection (0-1)
        start_date: Start date of the regime
        end_date: End date of the regime (None if ongoing)
        expected_duration: Expected days until regime transition
        characteristics: Additional regime characteristics
    """

    regime_type: RegimeType = field(default=RegimeType.NEUTRAL)
    volatility_regime: VolatilityRegime = field(default=VolatilityRegime.NORMAL)
    trend_regime: TrendRegime = field(default=TrendRegime.TRANSITION)
    confidence: float = field(default=0.5)
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = field(default=None)
    expected_duration: Optional[int] = field(default=None)
    characteristics: Dict[str, Any] = field(default_factory=dict)

    def description(self) -> str:
        """Get human-readable regime description."""
        type_desc = {
            RegimeType.BULL: "Bullish market with upward price momentum",
            RegimeType.BEAR: "Bearish market with downward price momentum",
            RegimeType.NEUTRAL: "Sideways/neutral market",
        }

        vol_desc = {
            VolatilityRegime.LOW: "Low volatility environment",
            VolatilityRegime.NORMAL: "Normal volatility levels",
            VolatilityRegime.HIGH: "High volatility environment",
        }

        trend_desc = {
            TrendRegime.TREND: "Strong trending market",
            TrendRegime.RANGE: "Range-bound market",
            TrendRegime.TRANSITION: "Transitional market phase",
        }

        parts = [
            type_desc.get(self.regime_type, "Unknown regime"),
            vol_desc.get(self.volatility_regime, "Unknown volatility"),
            trend_desc.get(self.trend_regime, "Unknown trend"),
        ]

        return " | ".join(parts)

    def is_favorable_for_trend_following(self) -> bool:
        """Check if regime is favorable for trend-following strategies."""
        return self.regime_type == RegimeType.BULL and self.trend_regime == TrendRegime.TREND

    def is_favorable_for_mean_reversion(self) -> bool:
        """Check if regime is favorable for mean-reversion strategies."""
        return (
            self.volatility_regime == VolatilityRegime.HIGH
            and self.trend_regime == TrendRegime.RANGE
        )


@dataclass
class RegimeConfig:
    """
    Configuration for regime detection.

    Attributes:
        lookback_period: Number of days to look back for regime analysis
        volatility_threshold: Multiplier for volatility threshold
        trend_threshold: Minimum slope for trend detection
        sma_short: Short SMA period
        sma_long: Long SMA period
        volatility_window: Window for volatility calculation
        use_hmm: Whether to use Hidden Markov Models
    """

    lookback_period: int = field(default=50)
    volatility_threshold: float = field(default=1.2)
    trend_threshold: float = field(default=0.01)
    sma_short: int = field(default=50)
    sma_long: int = field(default=200)
    volatility_window: int = field(default=20)
    use_hmm: bool = field(default=False)


@dataclass
class ParameterStabilityResult:
    """
    Results for parameter stability analysis.

    Attributes:
        parameter_name: Name of the parameter
        is_mean: Mean value in in-sample periods
        is_std: Standard deviation in in-sample periods
        os_mean: Mean value in out-of-sample periods
        os_std: Standard deviation in out-of-sample periods
        stability_score: Stability score (0-100)
        stability_level: Stability level classification
        drift_detected: Whether parameter drift was detected
        recommendation: Recommendation for this parameter
        coefficient_of_variation: CV (std/mean)
    """

    parameter_name: str = field(default="")
    is_mean: Decimal = field(default=Decimal("0"))
    is_std: Decimal = field(default=Decimal("0"))
    os_mean: Decimal = field(default=Decimal("0"))
    os_std: Decimal = field(default=Decimal("0"))
    stability_score: Decimal = field(default=Decimal("0"))
    stability_level: StabilityLevel = field(default=StabilityLevel.STABLE)
    drift_detected: bool = field(default=False)
    recommendation: str = field(default="")
    coefficient_of_variation: Decimal = field(default=Decimal("0"))

    def is_stable(self) -> bool:
        """Check if parameter is stable."""
        return self.stability_level == StabilityLevel.STABLE


@dataclass
class RegimeTransitionMatrix:
    """
    Transition probability matrix for market regimes.

    Attributes:
        matrix: 3x3 transition probability matrix
        regimes: List of regime names
        expected_durations: Expected duration for each regime
        last_update: When the matrix was last updated
    """

    matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    regimes: List[str] = field(default_factory=list)
    expected_durations: Dict[str, float] = field(default_factory=dict)
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_transition_probability(self, from_regime: str, to_regime: str) -> float:
        """Get transition probability between regimes."""
        if from_regime in self.matrix and to_regime in self.matrix[from_regime]:
            return self.matrix[from_regime][to_regime]
        return 0.0

    def get_expected_duration(self, regime: str) -> Optional[float]:
        """Get expected duration for a regime in days."""
        return self.expected_durations.get(regime)
