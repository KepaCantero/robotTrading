"""
Comprehensive tests for the Validation module (FASE 5.3).

Tests for:
- WalkForwardValidator
- OverfittingDetector
- RegimeDetector
- ParameterStabilityAnalyzer
"""

from __future__ import annotations

import datetime
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# Import validation module components
from app.backtesting.validation.models import (
    MarketRegime,
    OverfittingLevel,
    OverfittingMetrics,
    ParameterStabilityResult,
    PeriodResult,
    RegimeConfig,
    RegimeTransitionMatrix,
    RegimeType,
    StabilityLevel,
    TrendRegime,
    VolatilityRegime,
    WalkForwardConfig,
    WalkForwardResult,
)
from app.backtesting.validation.overfitting_detector import (
    OverfittingDetector,
    analyze_parameter_stability,
    calculate_overfitting_metrics,
    calculate_stability_score,
    classify_stability,
    detect_parameter_drift,
    generate_stability_recommendation,
)
from app.backtesting.validation.parameter_stability import (
    ParameterStabilityAnalyzer,
    calculate_parameter_stability,
    detect_parameter_drift_simple,
    filter_stable_parameters,
    rank_parameters_by_stability,
)
from app.backtesting.validation.regime_detector import (
    RegimeDetector,
    classify_market_state,
    detect_regime_from_data,
)
from app.backtesting.validation.walk_forward import (
    RollingWindowOptimizer,
    WalkForwardValidator,
    calculate_consistency_score,
    calculate_degradation,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """Create sample price data for testing."""
    np.random.seed(42)
    n_days = 1000

    # Generate realistic price path with trend and volatility
    returns = np.random.normal(0.0005, 0.02, n_days)
    prices = 100 * np.exp(np.cumsum(returns))

    dates = pd.date_range(start="2020-01-01", periods=n_days, freq="D")
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, n_days)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, n_days),
        },
        index=dates,
    )

    return df


@pytest.fixture
def sample_returns() -> pd.Series:
    """Create sample return series for testing."""
    np.random.seed(42)
    n = 500
    returns = pd.Series(
        np.random.normal(0.0005, 0.02, n),
        index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
    )
    return returns


@pytest.fixture
def walk_forward_config() -> WalkForwardConfig:
    """Create walk-forward configuration for testing."""
    return WalkForwardConfig(
        train_period_months=12,
        test_period_months=3,
        step_months=3,
        min_observations=100,
    )


@pytest.fixture
def regime_config() -> RegimeConfig:
    """Create regime detection configuration for testing."""
    return RegimeConfig(
        lookback_period=50,
        volatility_threshold=1.2,
        trend_threshold=0.01,
        sma_short=20,
        sma_long=50,
    )


@pytest.fixture
def sample_is_results() -> List[PeriodResult]:
    """Create sample in-sample results for testing."""
    results = []
    for i in range(5):
        result = PeriodResult(
            period_id=None,
            start_date=date(2020, 1, 1) + timedelta(days=90 * i),
            end_date=date(2020, 4, 1) + timedelta(days=90 * i),
            is_in_sample=True,
            total_trades=100 + i * 10,
            total_return=Decimal(str(10 + i * 2)),
            sharpe_ratio=Decimal(str(1.5 + i * 0.1)),
            max_drawdown=Decimal(str(-10 - i)),
            win_rate=Decimal(str(55 + i)),
            profit_factor=Decimal(str(1.8 + i * 0.1)),
            parameters={"window": 20 + i * 2, "threshold": 1.5},
        )
        results.append(result)
    return results


@pytest.fixture
def sample_os_results() -> List[PeriodResult]:
    """Create sample out-of-sample results for testing."""
    results = []
    for i in range(5):
        # Some degradation from IS
        result = PeriodResult(
            period_id=None,
            start_date=date(2020, 4, 1) + timedelta(days=90 * i),
            end_date=date(2020, 7, 1) + timedelta(days=90 * i),
            is_in_sample=False,
            total_trades=90 + i * 8,
            total_return=Decimal(str(8 + i * 1.5)),
            sharpe_ratio=Decimal(str(1.2 + i * 0.08)),
            max_drawdown=Decimal(str(-12 - i * 1.5)),
            win_rate=Decimal(str(52 + i)),
            profit_factor=Decimal(str(1.5 + i * 0.08)),
            parameters={"window": 20 + i * 2, "threshold": 1.5},
        )
        results.append(result)
    return results


@pytest.fixture
def sample_parameter_history() -> List[Dict[str, Any]]:
    """Create sample parameter history for testing."""
    return [
        {"window": 20, "threshold": 1.5, "stop_loss": 0.02},
        {"window": 22, "threshold": 1.6, "stop_loss": 0.025},
        {"window": 21, "threshold": 1.5, "stop_loss": 0.02},
        {"window": 23, "threshold": 1.7, "stop_loss": 0.022},
        {"window": 20, "threshold": 1.5, "stop_loss": 0.02},
    ]


# =============================================================================
# TESTS: MODELS
# =============================================================================


class TestValidationModels:
    """Tests for validation module data models."""

    def test_walk_forward_config_creation(self):
        """Test WalkForwardConfig creation."""
        config = WalkForwardConfig(
            train_period_months=24,
            test_period_months=6,
            step_months=3,
        )
        assert config.train_period_months == 24
        assert config.test_period_months == 6
        assert config.step_months == 3
        assert config.min_observations == 252
        assert config.allow_overlap is True

    def test_walk_forward_config_defaults(self):
        """Test WalkForwardConfig default values."""
        config = WalkForwardConfig()
        assert config.train_period_months == 24
        assert config.test_period_months == 6
        assert config.step_months == 3
        assert config.min_observations == 252

    def test_period_result_creation(self):
        """Test PeriodResult creation."""
        result = PeriodResult(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 4, 1),
            is_in_sample=True,
            total_trades=100,
            total_return=Decimal("10.5"),
        )
        assert result.is_in_sample is True
        assert result.total_trades == 100
        assert result.total_return == Decimal("10.5")

    def test_overfitting_level_enum(self):
        """Test OverfittingLevel enum."""
        assert OverfittingLevel.NONE == "none"
        assert OverfittingLevel.MILD == "mild"
        assert OverfittingLevel.MODERATE == "moderate"
        assert OverfittingLevel.SEVERE == "severe"

    def test_stability_level_enum(self):
        """Test StabilityLevel enum."""
        assert StabilityLevel.STABLE == "stable"
        assert StabilityLevel.MODERATE == "moderate"
        assert StabilityLevel.UNSTABLE == "unstable"

    def test_regime_type_enum(self):
        """Test RegimeType enum."""
        assert RegimeType.BULL == "bull"
        assert RegimeType.BEAR == "bear"
        assert RegimeType.NEUTRAL == "neutral"

    def test_volatility_regime_enum(self):
        """Test VolatilityRegime enum."""
        assert VolatilityRegime.LOW == "low"
        assert VolatilityRegime.NORMAL == "normal"
        assert VolatilityRegime.HIGH == "high"

    def test_trend_regime_enum(self):
        """Test TrendRegime enum."""
        assert TrendRegime.TREND == "trend"
        assert TrendRegime.RANGE == "range"
        assert TrendRegime.TRANSITION == "transition"

    def test_market_regime_creation(self, regime_config):
        """Test MarketRegime creation."""
        regime = MarketRegime(
            regime_type=RegimeType.BULL,
            volatility_regime=VolatilityRegime.NORMAL,
            trend_regime=TrendRegime.TREND,
            confidence=0.85,
            start_date=date(2024, 1, 1),
        )
        assert regime.regime_type == RegimeType.BULL
        assert regime.confidence == 0.85

    def test_market_regime_description(self):
        """Test MarketRegime description method."""
        regime = MarketRegime(
            regime_type=RegimeType.BULL,
            volatility_regime=VolatilityRegime.NORMAL,
            trend_regime=TrendRegime.TREND,
        )
        desc = regime.description()
        assert "Bullish" in desc
        assert "Normal volatility" in desc
        assert "Strong trending" in desc

    def test_market_regime_favorable_trend_following(self):
        """Test MarketRegime favorability for trend-following."""
        regime = MarketRegime(
            regime_type=RegimeType.BULL,
            trend_regime=TrendRegime.TREND,
        )
        assert regime.is_favorable_for_trend_following() is True

    def test_market_regime_favorable_mean_reversion(self):
        """Test MarketRegime favorability for mean-reversion."""
        regime = MarketRegime(
            volatility_regime=VolatilityRegime.HIGH,
            trend_regime=TrendRegime.RANGE,
        )
        assert regime.is_favorable_for_mean_reversion() is True

    def test_overfitting_metrics_creation(self):
        """Test OverfittingMetrics creation."""
        metrics = OverfittingMetrics(
            is_sharpe=Decimal("2.0"),
            os_sharpe=Decimal("1.5"),
            degradation_ratio=Decimal("0.75"),
            overfitting_level=OverfittingLevel.MILD,
        )
        assert metrics.is_sharpe == Decimal("2.0")
        assert metrics.os_sharpe == Decimal("1.5")
        assert metrics.degradation_ratio == Decimal("0.75")

    def test_overfitting_metrics_is_overfitted(self):
        """Test OverfittingMetrics.is_overfitted method."""
        # Severe overfitting
        metrics_severe = OverfittingMetrics(overfitting_level=OverfittingLevel.SEVERE)
        assert metrics_severe.is_overfitted() is True

        # No overfitting
        metrics_none = OverfittingMetrics(overfitting_level=OverfittingLevel.NONE)
        assert metrics_none.is_overfitted() is False

    def test_parameter_stability_result_creation(self):
        """Test ParameterStabilityResult creation."""
        result = ParameterStabilityResult(
            parameter_name="window",
            is_mean=Decimal("20"),
            is_std=Decimal("2"),
            stability_score=Decimal("90"),
            stability_level=StabilityLevel.STABLE,
        )
        assert result.parameter_name == "window"
        assert result.stability_level == StabilityLevel.STABLE

    def test_parameter_stability_result_is_stable(self):
        """Test ParameterStabilityResult.is_stable method."""
        # Stable
        result_stable = ParameterStabilityResult(
            parameter_name="window",
            stability_level=StabilityLevel.STABLE,
        )
        assert result_stable.is_stable() is True

        # Unstable
        result_unstable = ParameterStabilityResult(
            parameter_name="window",
            stability_level=StabilityLevel.UNSTABLE,
        )
        assert result_unstable.is_stable() is False

    def test_walk_forward_result_degradation_summary(self):
        """Test WalkForwardResult.get_degradation_summary method."""
        result = WalkForwardResult(
            is_performance={"sharpe_ratio": Decimal("2.0"), "total_return": Decimal("20")},
            os_performance={"sharpe_ratio": Decimal("1.5"), "total_return": Decimal("15")},
        )
        summary = result.get_degradation_summary()
        assert "sharpe_degradation" in summary
        assert "return_degradation" in summary
        assert summary["sharpe_degradation"] == Decimal("0.75")

    def test_regime_transition_matrix(self):
        """Test RegimeTransitionMatrix."""
        matrix = RegimeTransitionMatrix(
            matrix={
                "bull": {"bull": 0.8, "bear": 0.1, "neutral": 0.1},
                "bear": {"bull": 0.1, "bear": 0.8, "neutral": 0.1},
                "neutral": {"bull": 0.3, "bear": 0.2, "neutral": 0.5},
            },
            regimes=["bull", "bear", "neutral"],
            expected_durations={"bull": 126, "bear": 126, "neutral": 42},
        )

        # Test get_transition_probability
        assert matrix.get_transition_probability("bull", "bull") == 0.8
        assert matrix.get_transition_probability("bull", "bear") == 0.1

        # Test get_expected_duration
        assert matrix.get_expected_duration("bull") == 126


# =============================================================================
# TESTS: WALK-FORWARD VALIDATION
# =============================================================================


class TestWalkForwardValidator:
    """Tests for WalkForwardValidator."""

    def test_walk_forward_validator_initialization(self, walk_forward_config):
        """Test WalkForwardValidator initialization."""
        validator = WalkForwardValidator(config=walk_forward_config)
        assert validator.config == walk_forward_config
        assert validator.config.train_period_months == 12

    def test_walk_forward_validator_default_config(self):
        """Test WalkForwardValidator with default config."""
        validator = WalkForwardValidator()
        assert validator.config.train_period_months == 24
        assert validator.config.test_period_months == 6

    def test_calculate_degradation(self):
        """Test calculate_degradation function."""
        # Normal degradation
        degradation = calculate_degradation(2.0, 1.5)
        assert degradation == 0.75

        # No degradation
        degradation = calculate_degradation(1.0, 1.0)
        assert degradation == 1.0

        # Zero IS value
        degradation = calculate_degradation(0.0, 1.0)
        assert degradation == 0.0

    def test_calculate_consistency_score(self):
        """Test calculate_consistency_score function."""
        # Consistent values
        values = [10.0, 10.1, 9.9, 10.0, 10.1]
        score = calculate_consistency_score(values)
        assert score > 80  # High consistency

        # Inconsistent values
        values = [10.0, 20.0, 5.0, 15.0, 8.0]
        score = calculate_consistency_score(values)
        assert score < 50  # Low consistency

        # Empty list
        score = calculate_consistency_score([])
        assert score == 0.0

    def test_generate_rolling_windows(self, walk_forward_config, sample_price_data):
        """Test _generate_rolling_windows method."""
        validator = WalkForwardValidator(config=walk_forward_config)
        windows = validator._generate_rolling_windows(sample_price_data)

        assert len(windows) > 0

        for train_data, test_data in windows:
            assert len(train_data) > 0
            assert len(test_data) > 0
            assert len(train_data) >= walk_forward_config.min_observations


class TestRollingWindowOptimizer:
    """Tests for RollingWindowOptimizer."""

    def test_optimizer_initialization(self):
        """Test RollingWindowOptimizer initialization."""
        optimizer = RollingWindowOptimizer(
            optimization_metric="sharpe_ratio",
            maximize=True,
        )
        assert optimizer.optimization_metric == "sharpe_ratio"
        assert optimizer.maximize is True

    def test_generate_param_combinations(self):
        """Test _generate_param_combinations method."""
        optimizer = RollingWindowOptimizer()
        param_grid = {
            "window": [10, 20, 30],
            "threshold": [0.5, 1.0],
        }

        combinations = optimizer._generate_param_combinations(param_grid)

        assert len(combinations) == 6  # 3 * 2
        assert {"window": 10, "threshold": 0.5} in combinations
        assert {"window": 30, "threshold": 1.0} in combinations


# =============================================================================
# TESTS: OVERFITTING DETECTION
# =============================================================================


class TestOverfittingDetector:
    """Tests for OverfittingDetector."""

    def test_detector_initialization(self):
        """Test OverfittingDetector initialization."""
        detector = OverfittingDetector()
        assert detector.severe_threshold == 0.5
        assert detector.moderate_threshold == 0.7
        assert detector.mild_threshold == 0.85

    def test_detector_custom_thresholds(self):
        """Test OverfittingDetector with custom thresholds."""
        detector = OverfittingDetector(
            severe_threshold=0.4,
            moderate_threshold=0.6,
            mild_threshold=0.8,
        )
        assert detector.severe_threshold == 0.4
        assert detector.moderate_threshold == 0.6
        assert detector.mild_threshold == 0.8

    def test_detect_no_overfitting(self, sample_is_results, sample_os_results):
        """Test detect with minimal overfitting."""
        detector = OverfittingDetector()

        # Modify results to show minimal degradation
        for result in sample_os_results:
            result.sharpe_ratio = result.sharpe_ratio * Decimal("0.9")  # 90% retention

        metrics = detector.detect(
            is_results=sample_is_results,
            os_results=sample_os_results,
            n_params=3,
        )

        assert metrics.overfitting_level in [OverfittingLevel.NONE, OverfittingLevel.MILD]

    def test_detect_severe_overfitting(self, sample_is_results):
        """Test detect with severe overfitting."""
        detector = OverfittingDetector()

        # Create degraded OS results
        os_results = []
        for result in sample_is_results:
            degraded = PeriodResult(
                start_date=result.start_date,
                end_date=result.end_date,
                is_in_sample=False,
                sharpe_ratio=result.sharpe_ratio * Decimal("0.4"),  # 60% degradation
                total_return=result.total_return * Decimal("0.3"),
            )
            os_results.append(degraded)

        metrics = detector.detect(
            is_results=sample_is_results,
            os_results=os_results,
            n_params=10,
        )

        assert metrics.overfitting_level == OverfittingLevel.SEVERE
        assert metrics.overfitting_probability > 0.5

    def test_calculate_degradation(self):
        """Test calculate_degradation method."""
        detector = OverfittingDetector()

        # Normal case
        degradation = detector.calculate_degradation(2.0, 1.5)
        assert degradation == 0.75

        # Zero IS value
        degradation = detector.calculate_degradation(0.0, 1.0)
        assert degradation == 0.0

    def test_classify_overfitting(self):
        """Test _classify_overfitting method."""
        detector = OverfittingDetector()

        # None
        assert detector._classify_overfitting(0.9) == OverfittingLevel.NONE
        assert detector._classify_overfitting(0.85) == OverfittingLevel.NONE

        # Mild
        assert detector._classify_overfitting(0.8) == OverfittingLevel.MILD
        assert detector._classify_overfitting(0.7) == OverfittingLevel.MILD

        # Moderate
        assert detector._classify_overfitting(0.65) == OverfittingLevel.MODERATE
        assert detector._classify_overfitting(0.5) == OverfittingLevel.MODERATE

        # Severe
        assert detector._classify_overfitting(0.4) == OverfittingLevel.SEVERE
        assert detector._classify_overfitting(0.2) == OverfittingLevel.SEVERE

    def test_whites_reality_check(self):
        """Test whites_reality_check method."""
        detector = OverfittingDetector()

        # Create returns
        np.random.seed(42)
        strategy_returns = pd.Series(np.random.normal(0.001, 0.02, 500))
        null_returns = pd.Series(np.random.normal(0.0005, 0.02, 500))

        p_value, is_significant = detector.whites_reality_check(
            returns=strategy_returns,
            null_returns=null_returns,
            n_bootstrap=100,
        )

        assert 0 <= p_value <= 1
        assert isinstance(is_significant, bool)

    def test_mcs_test(self):
        """Test mcs_test method."""
        detector = OverfittingDetector()

        # Create strategy returns
        np.random.seed(42)
        strategies_returns = [
            pd.Series(np.random.normal(0.001, 0.02, 500)),
            pd.Series(np.random.normal(0.0008, 0.02, 500)),
        ]

        p_value, is_in_mcs = detector.mcs_test(
            strategies_returns=strategies_returns,
            alpha=0.05,
        )

        assert 0 <= p_value <= 1
        assert isinstance(is_in_mcs, bool)


class TestParameterStabilityFunctions:
    """Tests for parameter stability utility functions."""

    def test_calculate_stability_score(self):
        """Test calculate_stability_score function."""
        # Stable parameter
        score = calculate_stability_score(Decimal("2"), Decimal("20"))
        assert score == Decimal("90")  # (1 - 2/20) * 100

        # Unstable parameter
        score = calculate_stability_score(Decimal("10"), Decimal("20"))
        assert score == Decimal("50")  # (1 - 10/20) * 100

        # Zero mean
        score = calculate_stability_score(Decimal("2"), Decimal("0"))
        assert score == Decimal("0")

    def test_classify_stability(self):
        """Test classify_stability function."""
        # Stable
        assert classify_stability(Decimal("80")) == StabilityLevel.STABLE
        assert classify_stability(Decimal("70")) == StabilityLevel.STABLE

        # Moderate
        assert classify_stability(Decimal("60")) == StabilityLevel.MODERATE
        assert classify_stability(Decimal("40")) == StabilityLevel.MODERATE

        # Unstable
        assert classify_stability(Decimal("30")) == StabilityLevel.UNSTABLE
        assert classify_stability(Decimal("10")) == StabilityLevel.UNSTABLE

    def test_detect_parameter_drift(self):
        """Test detect_parameter_drift function."""
        # No drift (stable values)
        values = [20, 21, 20, 19, 20, 21, 20]
        assert detect_parameter_drift(values) is False

        # Drift (increasing trend)
        values = [20, 22, 24, 26, 28, 30, 32]
        assert detect_parameter_drift(values) is True

        # Too few values
        values = [20, 21]
        assert detect_parameter_drift(values) is False

    def test_generate_stability_recommendation(self):
        """Test generate_stability_recommendation function."""
        # Drift detected
        rec = generate_stability_recommendation("window", StabilityLevel.STABLE, True)
        assert "drift" in rec.lower()
        assert "window" in rec

        # Stable
        rec = generate_stability_recommendation("threshold", StabilityLevel.STABLE, False)
        assert "stable" in rec.lower()
        assert "good candidate" in rec.lower()

    def test_analyze_parameter_stability(self, sample_parameter_history):
        """Test analyze_parameter_stability function."""
        results = analyze_parameter_stability(
            is_params=sample_parameter_history,
            os_params=sample_parameter_history,
        )

        assert len(results) > 0

        for result in results:
            assert isinstance(result, ParameterStabilityResult)
            assert result.parameter_name
            assert 0 <= result.stability_score <= 100


# =============================================================================
# TESTS: REGIME DETECTION
# =============================================================================


class TestRegimeDetector:
    """Tests for RegimeDetector."""

    def test_detector_initialization(self, regime_config):
        """Test RegimeDetector initialization."""
        detector = RegimeDetector(config=regime_config)
        assert detector.config == regime_config

    def test_detector_default_config(self):
        """Test RegimeDetector with default config."""
        detector = RegimeDetector()
        assert detector.config.lookback_period == 50
        assert detector.config.volatility_threshold == 1.2

    def test_detect_regime(self, regime_config, sample_price_data, sample_returns):
        """Test detect_regime method."""
        detector = RegimeDetector(config=regime_config)

        regime = detector.detect_regime(
            prices=sample_price_data["close"],
            returns=sample_returns,
            as_of_date=date(2022, 1, 1),
        )

        assert isinstance(regime, MarketRegime)
        assert regime.regime_type in RegimeType
        assert regime.volatility_regime in VolatilityRegime
        assert regime.trend_regime in TrendRegime
        assert 0 <= regime.confidence <= 1

    def test_detect_regime_description(self, regime_config, sample_price_data, sample_returns):
        """Test regime description."""
        detector = RegimeDetector(config=regime_config)

        regime = detector.detect_regime(
            prices=sample_price_data["close"],
            returns=sample_returns,
            as_of_date=date(2022, 1, 1),
        )

        desc = regime.description()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_detect_regime_bull_market(self):
        """Test regime detection with bull market data."""
        detector = RegimeDetector()

        # Create trending up prices
        n = 300
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(0.001, 0.01, n))))
        returns = prices.pct_change().dropna()

        regime = detector.detect_regime(
            prices=prices,
            returns=returns,
            as_of_date=date(2022, 1, 1),
        )

        # Should detect bull or neutral (not bear)
        assert regime.regime_type in [RegimeType.BULL, RegimeType.NEUTRAL]

    def test_detect_regime_bear_market(self):
        """Test regime detection with bear market data."""
        detector = RegimeDetector()

        # Create trending down prices
        n = 300
        prices = pd.Series(100 * np.exp(np.cumsum(np.random.normal(-0.001, 0.01, n))))
        returns = prices.pct_change().dropna()

        regime = detector.detect_regime(
            prices=prices,
            returns=returns,
            as_of_date=date(2022, 1, 1),
        )

        # Should detect bear or neutral (not bull)
        assert regime.regime_type in [RegimeType.BEAR, RegimeType.NEUTRAL]

    def test_detect_volatility_regime(self):
        """Test _detect_volatility_regime method."""
        detector = RegimeDetector()

        # Low volatility
        low_vol_returns = pd.Series(np.random.normal(0, 0.005, 300))
        regime = detector._detect_volatility_regime(low_vol_returns)
        assert regime in VolatilityRegime

        # High volatility
        high_vol_returns = pd.Series(np.random.normal(0, 0.05, 300))
        regime = detector._detect_volatility_regime(high_vol_returns)
        assert regime in VolatilityRegime

    def test_calculate_transition_matrix(self, regime_config, sample_price_data, sample_returns):
        """Test calculate_transition_matrix method."""
        detector = RegimeDetector(config=regime_config)

        # Get regime history
        history = detector.detect_regime_history(
            prices=sample_price_data["close"],
            returns=sample_returns,
        )

        if len(history) > 2:
            matrix = detector.calculate_transition_matrix(history)

            assert isinstance(matrix, RegimeTransitionMatrix)
            assert len(matrix.regimes) > 0
            assert len(matrix.expected_durations) > 0

    def test_get_regime_aware_recommendation(self, regime_config):
        """Test get_regime_aware_recommendation method."""
        detector = RegimeDetector(config=regime_config)

        # Bull market regime
        bull_regime = MarketRegime(
            regime_type=RegimeType.BULL,
            trend_regime=TrendRegime.TREND,
            volatility_regime=VolatilityRegime.NORMAL,
        )

        recommendations = detector.get_regime_aware_recommendation(bull_regime)
        assert len(recommendations) > 0
        assert any("bull" in rec.lower() for rec in recommendations)

        # Bear market regime
        bear_regime = MarketRegime(
            regime_type=RegimeType.BEAR,
            trend_regime=TrendRegime.TREND,
            volatility_regime=VolatilityRegime.HIGH,
        )

        recommendations = detector.get_regime_aware_recommendation(bear_regime)
        assert len(recommendations) > 0
        assert any("bear" in rec.lower() for rec in recommendations)


class TestRegimeUtilityFunctions:
    """Tests for regime detection utility functions."""

    def test_detect_regime_from_data(self, sample_price_data):
        """Test detect_regime_from_data function."""
        regime = detect_regime_from_data(sample_price_data["close"])

        assert isinstance(regime, MarketRegime)
        assert regime.regime_type in RegimeType

    def test_classify_market_state(self, sample_price_data):
        """Test classify_market_state function."""
        state = classify_market_state(sample_price_data["close"])

        assert isinstance(state, str)
        assert "_" in state  # Should be format like "bull_normal_vol"


# =============================================================================
# TESTS: PARAMETER STABILITY
# =============================================================================


class TestParameterStabilityAnalyzer:
    """Tests for ParameterStabilityAnalyzer."""

    def test_analyzer_initialization(self):
        """Test ParameterStabilityAnalyzer initialization."""
        analyzer = ParameterStabilityAnalyzer()
        assert analyzer.stable_threshold == 70.0
        assert analyzer.moderate_threshold == 40.0

    def test_analyze(self, sample_parameter_history):
        """Test analyze method."""
        analyzer = ParameterStabilityAnalyzer()

        results = analyzer.analyze(
            is_params=sample_parameter_history,
            os_params=sample_parameter_history,
        )

        assert len(results) > 0

        for result in results:
            assert isinstance(result, ParameterStabilityResult)
            assert result.parameter_name
            assert 0 <= result.stability_score <= 100
            assert result.stability_level in StabilityLevel

    def test_analyze_stable_parameters(self):
        """Test analyze with stable parameters."""
        analyzer = ParameterStabilityAnalyzer()

        # Create stable parameter history
        stable_params = [
            {"window": 20, "threshold": 1.5},
            {"window": 20, "threshold": 1.5},
            {"window": 20, "threshold": 1.5},
            {"window": 20, "threshold": 1.5},
        ]

        results = analyzer.analyze(stable_params, stable_params)

        for result in results:
            assert result.stability_score >= 70  # Should be stable

    def test_analyze_unstable_parameters(self):
        """Test analyze with unstable parameters."""
        analyzer = ParameterStabilityAnalyzer()

        # Create unstable parameter history
        unstable_params = [
            {"window": 10, "threshold": 0.5},
            {"window": 30, "threshold": 2.5},
            {"window": 15, "threshold": 1.0},
            {"window": 40, "threshold": 3.0},
        ]

        results = analyzer.analyze(unstable_params, unstable_params)

        for result in results:
            # At least some should be unstable
            if result.parameter_name == "window":
                assert result.stability_level in [StabilityLevel.UNSTABLE, StabilityLevel.MODERATE]

    def test_calculate_stability_score(self):
        """Test calculate_stability_score method."""
        analyzer = ParameterStabilityAnalyzer()

        # Stable
        score = analyzer.calculate_stability_score(Decimal("2"), Decimal("20"))
        assert score >= 70

        # Unstable
        score = analyzer.calculate_stability_score(Decimal("15"), Decimal("20"))
        assert score < 30

    def test_detect_drift(self):
        """Test detect_drift method."""
        analyzer = ParameterStabilityAnalyzer()

        # No drift
        stable_values = [20, 20, 20, 20, 20]
        assert analyzer.detect_drift(stable_values) is False

        # Drift
        trending_values = [10, 15, 20, 25, 30, 35, 40]
        assert analyzer.detect_drift(trending_values) is True

        # Too few values
        short_values = [20, 21]
        assert analyzer.detect_drift(short_values) is False

    def test_compare_parameter_distributions(self, sample_parameter_history):
        """Test compare_parameter_distributions method."""
        analyzer = ParameterStabilityAnalyzer()

        results = analyzer.compare_parameter_distributions(
            is_params=sample_parameter_history,
            os_params=sample_parameter_history,
        )

        # Should have results for each parameter
        assert len(results) > 0

        for param_name, stats in results.items():
            assert "ks_statistic" in stats
            assert "p_value" in stats
            assert "same_distribution" in stats

    def test_calculate_parameter_correlation(self, sample_parameter_history):
        """Test calculate_parameter_correlation method."""
        analyzer = ParameterStabilityAnalyzer()

        corr_df = analyzer.calculate_parameter_correlation(sample_parameter_history)

        assert isinstance(corr_df, pd.DataFrame)
        if not corr_df.empty:
            assert corr_df.shape[0] > 0
            assert corr_df.shape[1] > 0

    def test_find_redundant_parameters(self, sample_parameter_history):
        """Test find_redundant_parameters method."""
        analyzer = ParameterStabilityAnalyzer()

        # Create parameters with high correlation
        correlated_params = [
            {"window": 20, "double_window": 40},
            {"window": 22, "double_window": 44},
            {"window": 21, "double_window": 42},
            {"window": 23, "double_window": 46},
        ]

        redundant = analyzer.find_redundant_parameters(correlated_params, threshold=0.9)

        # Should detect the correlation
        if redundant:
            assert len(redundant) > 0


class TestParameterStabilityUtilityFunctions:
    """Tests for parameter stability utility functions."""

    def test_calculate_parameter_stability(self):
        """Test calculate_parameter_stability function."""
        # Stable parameter
        metrics = calculate_parameter_stability([20, 20, 20, 20, 20])
        assert metrics["stability_score"] == 100.0
        assert metrics["stability_level"] == "stable"

        # Unstable parameter
        metrics = calculate_parameter_stability([10, 30, 15, 25, 20])
        assert metrics["stability_score"] < 70

        # Empty list
        metrics = calculate_parameter_stability([])
        assert metrics["stability_score"] == 0.0

    def test_detect_parameter_drift_simple(self):
        """Test detect_parameter_drift_simple function."""
        # No drift
        assert detect_parameter_drift_simple([20, 20, 20, 20]) is False

        # Drift
        assert detect_parameter_drift_simple([20, 25, 30, 35, 40]) is True

        # Too short
        assert detect_parameter_drift_simple([20, 21]) is False

    def test_rank_parameters_by_stability(self, sample_parameter_history):
        """Test rank_parameters_by_stability function."""
        analyzer = ParameterStabilityAnalyzer()
        results = analyzer.analyze(sample_parameter_history, sample_parameter_history)

        ranked = rank_parameters_by_stability(results)

        assert len(ranked) == len(results)

        # Check descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].stability_score >= ranked[i + 1].stability_score

    def test_filter_stable_parameters(self, sample_parameter_history):
        """Test filter_stable_parameters function."""
        analyzer = ParameterStabilityAnalyzer()
        results = analyzer.analyze(sample_parameter_history, sample_parameter_history)

        stable_params = filter_stable_parameters(results, min_score=70.0)

        # All returned parameters should be stable
        for param_name in stable_params:
            result = next(r for r in results if r.parameter_name == param_name)
            assert result.stability_score >= 70.0
            assert result.stability_level == StabilityLevel.STABLE


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestValidationIntegration:
    """Integration tests for validation module."""

    def test_full_walk_forward_validation_workflow(self, sample_price_data):
        """Test complete walk-forward validation workflow."""
        config = WalkForwardConfig(
            train_period_months=6,
            test_period_months=2,
            step_months=2,
            min_observations=50,
        )

        validator = WalkForwardValidator(config=config)

        # Generate windows
        windows = validator._generate_rolling_windows(sample_price_data)

        assert len(windows) > 0

    def test_overfitting_detection_workflow(self, sample_is_results, sample_os_results):
        """Test complete overfitting detection workflow."""
        detector = OverfittingDetector()

        metrics = detector.detect(
            is_results=sample_is_results,
            os_results=sample_os_results,
            n_params=5,
            parameter_history=[
                {"window": 20, "threshold": 1.5},
                {"window": 22, "threshold": 1.6},
                {"window": 21, "threshold": 1.5},
            ],
        )

        assert metrics.overfitting_level in OverfittingLevel
        assert len(metrics.recommendations) > 0

    def test_regime_detection_workflow(self, sample_price_data, sample_returns):
        """Test complete regime detection workflow."""
        detector = RegimeDetector()

        # Detect current regime
        current_regime = detector.detect_regime(
            prices=sample_price_data["close"],
            returns=sample_returns,
            as_of_date=date(2022, 1, 1),
        )

        # Get recommendations
        recommendations = detector.get_regime_aware_recommendation(current_regime)

        assert isinstance(current_regime, MarketRegime)
        assert len(recommendations) > 0

    def test_parameter_stability_workflow(self, sample_parameter_history):
        """Test complete parameter stability workflow."""
        analyzer = ParameterStabilityAnalyzer()

        # Analyze stability
        results = analyzer.analyze(sample_parameter_history, sample_parameter_history)

        # Rank parameters
        ranked = rank_parameters_by_stability(results)

        # Filter stable parameters
        stable = filter_stable_parameters(results)

        assert len(ranked) > 0
        assert isinstance(stable, list)


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestValidationEdgeCases:
    """Tests for edge cases and error handling."""

    def test_walk_forward_with_insufficient_data(self):
        """Test walk-forward validation with insufficient data."""
        validator = WalkForwardValidator()

        # Very small dataset
        small_data = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104],
            }
        )

        with pytest.raises(ValueError):
            validator._generate_rolling_windows(small_data)

    def test_overfitting_detector_with_empty_results(self):
        """Test overfitting detector with empty results."""
        detector = OverfittingDetector()

        metrics = detector.detect([], [], n_params=0)

        assert metrics.is_sharpe == Decimal("0")
        assert metrics.os_sharpe == Decimal("0")

    def test_regime_detector_with_short_series(self):
        """Test regime detector with very short series."""
        detector = RegimeDetector()

        short_prices = pd.Series([100, 101, 102, 103, 104])
        short_returns = short_prices.pct_change().dropna()

        regime = detector.detect_regime(
            prices=short_prices,
            returns=short_returns,
            as_of_date=date(2022, 1, 1),
        )

        # Should still return a regime, even with low confidence
        assert isinstance(regime, MarketRegime)

    def test_parameter_stability_with_empty_history(self):
        """Test parameter stability with empty history."""
        analyzer = ParameterStabilityAnalyzer()

        results = analyzer.analyze([], [])

        assert len(results) == 0

    def test_calculate_degradation_edge_cases(self):
        """Test calculate_degradation with edge cases."""
        # Negative values
        degradation = calculate_degradation(-2.0, -1.5)
        assert degradation == 0.75

        # Very small values
        degradation = calculate_degradation(0.0001, 0.00008)
        assert degradation == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
