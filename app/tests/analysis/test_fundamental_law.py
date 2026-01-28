"""
Comprehensive tests for the Fundamental Law of Active Management module.

This test suite covers all functionality of the fundamental law analysis:
- FundamentalLawCalculator: IR decomposition and strategy analysis
- ICCalculator: Information Coefficient calculation and testing
- BreadthCalculator: Breadth calculation and independence factor

Target: 50+ tests

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.analysis.fundamental_law import (
    BreadthCalculator,
    BreadthMetrics,
    FundamentalLawCalculator,
    FundamentalLawComponents,
    ICCalculator,
    ICMetrics,
    StrategyAnalysis,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_forecasts():
    """Create sample forecast data."""
    np.random.seed(42)
    n = 100
    return pd.Series(
        np.random.randn(n) * 0.02,
        index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
    )


@pytest.fixture
def sample_returns():
    """Create sample return data correlated with forecasts."""
    np.random.seed(42)
    n = 100
    forecasts = np.random.randn(n) * 0.02
    # Returns are correlated with forecasts plus noise
    returns = 0.7 * forecasts + np.random.randn(n) * 0.01
    return pd.Series(
        returns,
        index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
    )


@pytest.fixture
def sample_benchmark_returns():
    """Create sample benchmark return data."""
    np.random.seed(123)
    n = 100
    return pd.Series(
        np.random.randn(n) * 0.01,
        index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
    )


@pytest.fixture
def sample_portfolio_returns():
    """Create sample portfolio returns."""
    np.random.seed(42)
    n = 100
    return pd.Series(
        np.random.randn(n) * 0.015 + 0.0005,  # Slight positive drift
        index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
    )


@pytest.fixture
def sample_correlation_matrix():
    """Create sample correlation matrix."""
    np.random.seed(42)
    n = 5
    # Create a correlation matrix with moderate correlation
    corr = np.random.uniform(0.2, 0.5, (n, n))
    corr = (corr + corr.T) / 2  # Make symmetric
    np.fill_diagonal(corr, 1.0)  # Unit diagonal
    return pd.DataFrame(
        corr,
        index=[f"asset_{i}" for i in range(n)],
        columns=[f"asset_{i}" for i in range(n)],
    )


@pytest.fixture
def perfect_forecasts_and_returns():
    """Create perfectly correlated forecasts and returns."""
    np.random.seed(42)
    n = 50
    values = np.random.randn(n) * 0.02
    return (
        pd.Series(values, index=pd.date_range(start="2020-01-01", periods=n, freq="D")),
        pd.Series(values, index=pd.date_range(start="2020-01-01", periods=n, freq="D")),
    )


@pytest.fixture
def uncorrelated_forecasts_and_returns():
    """Create uncorrelated forecasts and returns."""
    np.random.seed(42)
    n = 50
    return (
        pd.Series(
            np.random.randn(n) * 0.02,
            index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
        ),
        pd.Series(
            np.random.randn(n) * 0.02,
            index=pd.date_range(start="2020-01-01", periods=n, freq="D"),
        ),
    )


# ============================================================================
# MODELS TESTS
# ============================================================================


class TestFundamentalLawComponents:
    """Tests for FundamentalLawComponents model."""

    def test_creation_valid(self):
        """Test creating valid components."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("1.0"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        assert components.information_ratio == Decimal("1.0")
        assert components.information_coefficient == Decimal("0.05")

    def test_validate_perfect_law(self):
        """Test validation with perfect Fundamental Law relationship."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("1.0"),  # 0.05 × 20 × 1.0 = 1.0
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        assert components.validate()

    def test_validate_with_tolerance(self):
        """Test validation with tolerance for small deviations."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("0.99"),  # Small deviation
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        assert components.validate(tolerance=Decimal("0.02"))

    def test_validate_negative_ir_raises(self):
        """Test that negative IR raises ValueError."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("-0.5"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        with pytest.raises(ValueError, match="Information Ratio cannot be negative"):
            components.validate()

    def test_validate_negative_ic_raises(self):
        """Test that negative IC raises ValueError."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("1.0"),
            information_coefficient=Decimal("-0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        with pytest.raises(ValueError, match="Information Coefficient cannot be negative"):
            components.validate()

    def test_get_theoretical_ir(self):
        """Test calculation of theoretical IR."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("1.0"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        theoretical = components.get_theoretical_ir()
        assert theoretical == Decimal("1.000")

    def test_get_efficiency_gap(self):
        """Test calculation of efficiency gap."""
        components = FundamentalLawComponents(
            information_ratio=Decimal("0.8"),  # Below theoretical
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )
        gap = components.get_efficiency_gap()
        assert gap == Decimal("0.200")


class TestICMetrics:
    """Tests for ICMetrics model."""

    def test_creation(self):
        """Test creating IC metrics."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[Decimal("0.05"), Decimal("0.03"), Decimal("0.02")],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.ic == Decimal("0.05")

    def test_is_significant_true(self):
        """Test is_significant returns True when p < 0.05."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.is_significant()

    def test_is_significant_false(self):
        """Test is_significant returns False when p >= 0.05."""
        metrics = ICMetrics(
            ic=Decimal("0.02"),
            ic_rank=Decimal("0.01"),
            ic_decay=[],
            statistical_significance=0.10,
            confidence_interval=(Decimal("0.00"), Decimal("0.04")),
        )
        assert not metrics.is_significant()

    def test_is_significant_custom_alpha(self):
        """Test is_significant with custom alpha."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[],
            statistical_significance=0.0005,  # More significant
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.is_significant(alpha=0.001)
        assert not metrics.is_significant(alpha=0.0001)

    def test_get_skill_level_excellent(self):
        """Test skill level categorization - excellent."""
        metrics = ICMetrics(
            ic=Decimal("0.06"),
            ic_rank=Decimal("0.05"),
            ic_decay=[],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.04"), Decimal("0.08")),
        )
        assert metrics.get_skill_level() == "excellent"

    def test_get_skill_level_good(self):
        """Test skill level categorization - good."""
        metrics = ICMetrics(
            ic=Decimal("0.04"),
            ic_rank=Decimal("0.03"),
            ic_decay=[],
            statistical_significance=0.01,
            confidence_interval=(Decimal("0.02"), Decimal("0.06")),
        )
        assert metrics.get_skill_level() == "good"

    def test_get_skill_level_fair(self):
        """Test skill level categorization - fair."""
        metrics = ICMetrics(
            ic=Decimal("0.02"),
            ic_rank=Decimal("0.01"),
            ic_decay=[],
            statistical_significance=0.05,
            confidence_interval=(Decimal("0.00"), Decimal("0.04")),
        )
        assert metrics.get_skill_level() == "fair"

    def test_get_skill_level_poor(self):
        """Test skill level categorization - poor."""
        metrics = ICMetrics(
            ic=Decimal("0.005"),
            ic_rank=Decimal("0.00"),
            ic_decay=[],
            statistical_significance=0.5,
            confidence_interval=(Decimal("-0.01"), Decimal("0.02")),
        )
        assert metrics.get_skill_level() == "poor"

    def test_get_signal_persistence_long(self):
        """Test signal persistence - long."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[Decimal("0.05"), Decimal("0.045"), Decimal("0.04")],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.get_signal_persistence() == "long"

    def test_get_signal_persistence_short(self):
        """Test signal persistence - short."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[Decimal("0.05"), Decimal("0.02"), Decimal("0.01")],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.get_signal_persistence() == "short"

    def test_get_signal_persistence_empty(self):
        """Test signal persistence with no decay data."""
        metrics = ICMetrics(
            ic=Decimal("0.05"),
            ic_rank=Decimal("0.04"),
            ic_decay=[],
            statistical_significance=0.001,
            confidence_interval=(Decimal("0.03"), Decimal("0.07")),
        )
        assert metrics.get_signal_persistence() == "unknown"


class TestBreadthMetrics:
    """Tests for BreadthMetrics model."""

    def test_creation(self):
        """Test creating breadth metrics."""
        metrics = BreadthMetrics(
            annual_breadth=Decimal("5200"),
            independence_factor=Decimal("0.5"),
            effective_breadth=Decimal("2600"),
            notes="Weekly rebalancing, 100 stocks",
        )
        assert metrics.annual_breadth == Decimal("5200")

    def test_get_breadth_category_high(self):
        """Test breadth categorization - high."""
        metrics = BreadthMetrics(
            annual_breadth=Decimal("2000"),
            independence_factor=Decimal("1.0"),
            effective_breadth=Decimal("2000"),
        )
        assert metrics.get_breadth_category() == "high"

    def test_get_breadth_category_medium(self):
        """Test breadth categorization - medium."""
        metrics = BreadthMetrics(
            annual_breadth=Decimal("500"),
            independence_factor=Decimal("1.0"),
            effective_breadth=Decimal("500"),
        )
        assert metrics.get_breadth_category() == "medium"

    def test_get_breadth_category_low(self):
        """Test breadth categorization - low."""
        metrics = BreadthMetrics(
            annual_breadth=Decimal("50"),
            independence_factor=Decimal("1.0"),
            effective_breadth=Decimal("50"),
        )
        assert metrics.get_breadth_category() == "low"

    def test_get_breadth_sqrt(self):
        """Test calculation of breadth square root."""
        metrics = BreadthMetrics(
            annual_breadth=Decimal("400"),
            independence_factor=Decimal("1.0"),
            effective_breadth=Decimal("400"),
        )
        sqrt_val = metrics.get_breadth_sqrt()
        assert abs(sqrt_val - Decimal("20.00")) < Decimal("0.01")


class TestStrategyAnalysis:
    """Tests for StrategyAnalysis model."""

    @pytest.fixture
    def sample_components(self):
        """Sample components for testing."""
        return FundamentalLawComponents(
            information_ratio=Decimal("0.8"),
            information_coefficient=Decimal("0.04"),
            breadth=Decimal("400"),
            breadth_sqrt=Decimal("20.0"),
            transfer_coefficient=Decimal("1.0"),
        )

    def test_creation(self, sample_components):
        """Test creating strategy analysis."""
        analysis = StrategyAnalysis(
            strategy_name="Test Strategy",
            components=sample_components,
            skill_level="good",
            breadth_assessment="medium",
        )
        assert analysis.strategy_name == "Test Strategy"
        assert analysis.skill_level == "good"

    def test_get_summary(self, sample_components):
        """Test summary generation."""
        analysis = StrategyAnalysis(
            strategy_name="Momentum Strategy",
            components=sample_components,
            skill_level="good",
            breadth_assessment="medium",
        )
        summary = analysis.get_summary()
        assert "Momentum Strategy" in summary
        assert "IR: 0.80" in summary
        assert "IC: 0.040" in summary
        assert "Skill: good" in summary

    def test_get_improvement_plan_with_suggestions(self, sample_components):
        """Test improvement plan with specific suggestions."""
        analysis = StrategyAnalysis(
            strategy_name="Test Strategy",
            components=sample_components,
            skill_level="good",
            breadth_assessment="medium",
            improvement_suggestions=["Improve alpha model", "Reduce constraints"],
        )
        plan = analysis.get_improvement_plan()
        assert "Improve alpha model" in plan
        assert "Reduce constraints" in plan

    def test_get_improvement_plan_without_suggestions(self, sample_components):
        """Test improvement plan generates general suggestions."""
        analysis = StrategyAnalysis(
            strategy_name="Test Strategy",
            components=sample_components,
            skill_level="good",
            breadth_assessment="medium",
        )
        plan = analysis.get_improvement_plan()
        assert "Improvement Plan" in plan
        assert len(plan) > 0

    def test_get_ir_decomposition(self, sample_components):
        """Test IR decomposition dictionary."""
        analysis = StrategyAnalysis(
            strategy_name="Test",
            components=sample_components,
            skill_level="good",
            breadth_assessment="medium",
        )
        decomp = analysis.get_ir_decomposition()
        assert "information_ratio" in decomp
        assert "ic_contribution" in decomp
        assert "breadth_contribution" in decomp
        assert decomp["information_ratio"] == 0.8


# ============================================================================
# IC CALCULATOR TESTS
# ============================================================================


class TestICCalculator:
    """Tests for ICCalculator."""

    def test_initialization(self):
        """Test calculator initialization."""
        calculator = ICCalculator(min_observations=30)
        assert calculator.min_observations == 30

    def test_calculate_ic_valid(self, sample_forecasts, sample_returns):
        """Test IC calculation with valid data."""
        calculator = ICCalculator()
        metrics = calculator.calculate_ic(sample_forecasts, sample_returns)
        assert isinstance(metrics, ICMetrics)
        assert isinstance(metrics.ic, Decimal)

    def test_calculate_ic_perfect_correlation(self, perfect_forecasts_and_returns):
        """Test IC with perfectly correlated data."""
        forecasts, returns = perfect_forecasts_and_returns
        calculator = ICCalculator()
        metrics = calculator.calculate_ic(forecasts, returns)
        # Should be very high (close to 1.0)
        assert metrics.ic > Decimal("0.9")

    def test_calculate_ic_uncorrelated(self, uncorrelated_forecasts_and_returns):
        """Test IC with uncorrelated data."""
        forecasts, returns = uncorrelated_forecasts_and_returns
        calculator = ICCalculator()
        metrics = calculator.calculate_ic(forecasts, returns)
        # Should be close to 0
        assert abs(metrics.ic) < Decimal("0.3")

    def test_calculate_ic_different_lengths_raises(self, sample_forecasts):
        """Test that different lengths raise ValueError."""
        calculator = ICCalculator()
        returns = pd.Series([0.01, 0.02])  # Different length
        with pytest.raises(ValueError, match="must have same length"):
            calculator.calculate_ic(sample_forecasts, returns)

    def test_calculate_ic_insufficient_data_raises(self):
        """Test that insufficient data raises ValueError."""
        calculator = ICCalculator(min_observations=50)
        forecasts = pd.Series([0.01, 0.02, 0.03])
        returns = pd.Series([0.01, 0.02, 0.03])
        with pytest.raises(ValueError, match="Insufficient observations"):
            calculator.calculate_ic(forecasts, returns)

    def test_calculate_ic_spearman(self, sample_forecasts, sample_returns):
        """Test IC calculation with Spearman correlation."""
        calculator = ICCalculator()
        metrics = calculator.calculate_ic(sample_forecasts, sample_returns, method="spearman")
        assert isinstance(metrics.ic_rank, Decimal)

    def test_calculate_ic_invalid_method_raises(self, sample_forecasts, sample_returns):
        """Test that invalid method raises ValueError."""
        calculator = ICCalculator()
        with pytest.raises(ValueError, match="Invalid correlation method"):
            calculator.calculate_ic(sample_forecasts, sample_returns, method="invalid")

    def test_calculate_ic_with_nans(self, sample_forecasts, sample_returns):
        """Test IC calculation handles NaN values."""
        forecasts_with_nan = sample_forecasts.copy()
        forecasts_with_nan.iloc[10:15] = np.nan

        returns_with_nan = sample_returns.copy()
        returns_with_nan.iloc[20:25] = np.nan

        calculator = ICCalculator(min_observations=50)
        metrics = calculator.calculate_ic(forecasts_with_nan, returns_with_nan)
        # Should successfully calculate with remaining valid data
        assert isinstance(metrics, ICMetrics)

    def test_calculate_ic_decay(self, sample_forecasts, sample_returns):
        """Test IC decay calculation."""
        calculator = ICCalculator(min_observations=20)
        decay = calculator.calculate_ic_decay(sample_forecasts, sample_returns, periods=[1, 2, 3])
        assert len(decay) == 3
        assert all(isinstance(d, Decimal) for d in decay)

    def test_test_significance(self):
        """Test IC significance testing."""
        calculator = ICCalculator()
        # IC=0.25 with n=100 should be significant
        p_value, is_sig = calculator.test_significance(ic=0.25, n_observations=100)
        assert 0 <= p_value <= 1
        assert is_sig  # IC=0.25 with n=100 should be significant

    def test_test_significance_low_ic(self):
        """Test significance testing with low IC."""
        calculator = ICCalculator()
        # IC=0.05 with n=100 is NOT significant
        p_value, is_sig = calculator.test_significance(ic=0.05, n_observations=100)
        # Should NOT be significant (p > 0.05)
        assert isinstance(is_sig, bool)
        assert not is_sig  # Low IC should not be significant

    def test_calculate_confidence_interval(self):
        """Test confidence interval calculation."""
        calculator = ICCalculator()
        ci = calculator.calculate_confidence_interval(ic=0.05, n=100)
        assert len(ci) == 2
        assert ci[0] < 0.05 < ci[1]  # CI should contain the IC

    def test_calculate_confidence_interval_invalid_ic_raises(self):
        """Test that invalid IC raises ValueError."""
        calculator = ICCalculator()
        with pytest.raises(ValueError, match="IC must be in \\[-1, 1\\]"):
            calculator.calculate_confidence_interval(ic=1.5, n=100)

    def test_calculate_rolling_ic(self, sample_forecasts, sample_returns):
        """Test rolling IC calculation."""
        calculator = ICCalculator(min_observations=20)
        rolling_ic = calculator.calculate_rolling_ic(sample_forecasts, sample_returns, window=30)
        assert isinstance(rolling_ic, pd.Series)
        assert len(rolling_ic) > 0

    def test_calculate_rolling_ic_insufficient_data_raises(self):
        """Test rolling IC with insufficient data."""
        calculator = ICCalculator()
        short_series = pd.Series([0.01, 0.02, 0.03])
        with pytest.raises(ValueError, match="Insufficient data"):
            calculator.calculate_rolling_ic(short_series, short_series, window=20)


# ============================================================================
# BREADTH CALCULATOR TESTS
# ============================================================================


class TestBreadthCalculator:
    """Tests for BreadthCalculator."""

    def test_calculate_breadth_weekly(self):
        """Test breadth calculation with weekly rebalancing."""
        calculator = BreadthCalculator()
        metrics = calculator.calculate_breadth(n_assets=100, rebalance_frequency="weekly")
        assert metrics.annual_breadth == Decimal("5200")  # 52 × 100
        assert metrics.independence_factor == Decimal("0.5")  # Default

    def test_calculate_breadth_daily(self):
        """Test breadth calculation with daily rebalancing."""
        calculator = BreadthCalculator()
        metrics = calculator.calculate_breadth(n_assets=50, rebalance_frequency="daily")
        assert metrics.annual_breadth == Decimal("12600")  # 252 × 50

    def test_calculate_breadth_monthly(self):
        """Test breadth calculation with monthly rebalancing."""
        calculator = BreadthCalculator()
        metrics = calculator.calculate_breadth(n_assets=200, rebalance_frequency="monthly")
        assert metrics.annual_breadth == Decimal("2400")  # 12 × 200

    def test_calculate_breadth_invalid_frequency_raises(self):
        """Test that invalid frequency raises ValueError."""
        calculator = BreadthCalculator()
        with pytest.raises(ValueError, match="Invalid rebalance_frequency"):
            calculator.calculate_breadth(n_assets=100, rebalance_frequency="hourly")

    def test_calculate_breadth_negative_assets_raises(self):
        """Test that negative assets raises ValueError."""
        calculator = BreadthCalculator()
        with pytest.raises(ValueError, match="n_assets must be positive"):
            calculator.calculate_breadth(n_assets=-10, rebalance_frequency="weekly")

    def test_calculate_independence_factor_uncorrelated(self):
        """Test independence factor with uncorrelated assets."""
        calculator = BreadthCalculator()
        # Identity matrix = uncorrelated assets
        corr_matrix = pd.DataFrame(np.eye(5))
        factor = calculator.calculate_independence_factor(corr_matrix)
        # Should be close to 1.0
        assert factor >= Decimal("0.9")

    def test_calculate_independence_factor_correlated(self):
        """Test independence factor with correlated assets."""
        calculator = BreadthCalculator()
        # All assets perfectly correlated
        corr_array = np.ones((5, 5))
        np.fill_diagonal(corr_array, 1.0)
        corr_matrix = pd.DataFrame(corr_array)
        factor = calculator.calculate_independence_factor(corr_matrix)
        # Should be low (1/n = 0.2)
        assert factor <= Decimal("0.3")

    def test_calculate_independence_factor_sample_matrix(self, sample_correlation_matrix):
        """Test independence factor with sample correlation matrix."""
        calculator = BreadthCalculator()
        factor = calculator.calculate_independence_factor(sample_correlation_matrix)
        assert Decimal("0") <= factor <= Decimal("1")

    def test_calculate_from_returns(self):
        """Test breadth calculation from returns data."""
        calculator = BreadthCalculator()
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns = pd.DataFrame(
            np.random.randn(252, 10) * 0.01,
            index=dates,
            columns=[f"asset_{i}" for i in range(10)],
        )
        metrics = calculator.calculate_from_returns(returns)
        assert metrics.effective_breadth > 0
        assert metrics.independence_factor > 0

    def test_estimate_required_breadth(self):
        """Test estimating required breadth for target IR."""
        calculator = BreadthCalculator()
        # IR = 1.0, IC = 0.05 => BR = (1.0 / 0.05)^2 = 400
        br = calculator.estimate_required_breadth(
            target_ir=Decimal("1.0"),
            information_coefficient=Decimal("0.05"),
        )
        assert abs(br - Decimal("400")) < Decimal("10")

    def test_estimate_required_breadth_with_tc(self):
        """Test estimating required breadth with TC."""
        calculator = BreadthCalculator()
        # IR = 1.0, IC = 0.05, TC = 0.5
        # => BR = (1.0 / (0.05 × 0.5))^2 = (1.0 / 0.025)^2 = 1600
        br = calculator.estimate_required_breadth(
            target_ir=Decimal("1.0"),
            information_coefficient=Decimal("0.05"),
            transfer_coefficient=Decimal("0.5"),
        )
        assert abs(br - Decimal("1600")) < Decimal("50")

    def test_estimate_required_breadth_zero_ic_raises(self):
        """Test that zero IC raises ValueError."""
        calculator = BreadthCalculator()
        with pytest.raises(ValueError, match="Information Coefficient must be positive"):
            calculator.estimate_required_breadth(
                target_ir=Decimal("1.0"),
                information_coefficient=Decimal("0"),
            )

    def test_decompose_breadth(self):
        """Test breadth decomposition."""
        calculator = BreadthCalculator()
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        returns = pd.DataFrame(
            np.random.randn(100, 5) * 0.01,
            index=dates,
            columns=[f"A{i}" for i in range(5)],
        )
        decomp = calculator.decompose_breadth(returns)
        assert "n_assets" in decomp
        assert "periods_per_year" in decomp
        assert "independence_factor" in decomp
        assert "effective_breadth" in decomp
        assert decomp["n_assets"] == 5


# ============================================================================
# FUNDAMENTAL LAW CALCULATOR TESTS
# ============================================================================


class TestFundamentalLawCalculator:
    """Tests for FundamentalLawCalculator."""

    def test_initialization(self):
        """Test calculator initialization."""
        calculator = FundamentalLawCalculator()
        assert isinstance(calculator.ic_calculator, ICCalculator)
        assert isinstance(calculator.breadth_calculator, BreadthCalculator)

    def test_calculate_fundamental_law(self):
        """Test calculation of fundamental law components."""
        calculator = FundamentalLawCalculator()
        components = calculator.calculate_fundamental_law(
            information_ratio=Decimal("1.0"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("400"),
        )
        assert components.information_ratio == Decimal("1.0")
        assert components.breadth_sqrt == calculator._calculate_breadth_sqrt(Decimal("400"))

    def test_calculate_fundamental_law_with_tc(self):
        """Test calculation with transfer coefficient."""
        calculator = FundamentalLawCalculator()
        components = calculator.calculate_fundamental_law(
            information_ratio=Decimal("0.5"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("100"),
            transfer_coefficient=Decimal("0.5"),
        )
        assert components.transfer_coefficient == Decimal("0.5")

    def test_calculate_fundamental_law_negative_ir_raises(self):
        """Test that negative IR raises ValueError."""
        calculator = FundamentalLawCalculator()
        with pytest.raises(ValueError, match="Information Ratio cannot be negative"):
            calculator.calculate_fundamental_law(
                information_ratio=Decimal("-0.5"),
                information_coefficient=Decimal("0.05"),
                breadth=Decimal("400"),
            )

    def test_calculate_fundamental_law_invalid_ic_raises(self):
        """Test that invalid IC raises ValueError."""
        calculator = FundamentalLawCalculator()
        with pytest.raises(ValueError, match="Information Coefficient must be in \\[-1, 1\\]"):
            calculator.calculate_fundamental_law(
                information_ratio=Decimal("1.0"),
                information_coefficient=Decimal("1.5"),
                breadth=Decimal("400"),
            )

    def test_decompose_ir(self, sample_forecasts, sample_returns, sample_benchmark_returns):
        """Test IR decomposition from returns."""
        calculator = FundamentalLawCalculator()
        components = calculator.decompose_ir(
            returns=sample_returns,
            forecasts=sample_forecasts,
            benchmark_returns=sample_benchmark_returns,
        )
        # IR should be clamped to non-negative by the function
        assert components.information_ratio >= 0
        assert isinstance(components.information_coefficient, Decimal)

    def test_decompose_ir_different_lengths_raises(self, sample_forecasts, sample_returns):
        """Test that different lengths raise ValueError."""
        calculator = FundamentalLawCalculator()
        short_benchmark = pd.Series([0.01] * 50)
        with pytest.raises(ValueError, match="must have same length"):
            calculator.decompose_ir(
                returns=sample_returns,
                forecasts=sample_forecasts,
                benchmark_returns=short_benchmark,
            )

    def test_analyze_strategy(self):
        """Test strategy analysis."""
        calculator = FundamentalLawCalculator()
        components = calculator.calculate_fundamental_law(
            information_ratio=Decimal("0.6"),
            information_coefficient=Decimal("0.03"),
            breadth=Decimal("400"),
        )
        analysis = calculator.analyze_strategy(components, "Test Strategy")
        assert analysis.strategy_name == "Test Strategy"
        assert analysis.skill_level in ["excellent", "good", "fair", "poor"]
        assert analysis.breadth_assessment in ["high", "medium", "low"]

    def test_compare_strategies(self):
        """Test comparing multiple strategies."""
        calculator = FundamentalLawCalculator()
        strategies = {
            "Momentum": calculator.calculate_fundamental_law(
                Decimal("0.8"), Decimal("0.04"), Decimal("400")
            ),
            "Value": calculator.calculate_fundamental_law(
                Decimal("0.6"), Decimal("0.03"), Decimal("300")
            ),
        }
        comparison = calculator.compare_strategies(strategies)
        assert len(comparison) == 2
        assert "IR" in comparison.columns
        assert "IC" in comparison.columns

    def test_calculate_required_ic_for_target_ir(self):
        """Test calculating required IC for target IR."""
        calculator = FundamentalLawCalculator()
        # IR = 1.0, BR = 400, TC = 1.0
        # IC = 1.0 / (20 × 1.0) = 0.05
        ic = calculator.calculate_required_ic_for_target_ir(
            target_ir=Decimal("1.0"),
            breadth=Decimal("400"),
        )
        assert abs(ic - Decimal("0.05")) < Decimal("0.01")

    def test_calculate_breadth_sqrt(self):
        """Test breadth square root calculation."""
        calculator = FundamentalLawCalculator()
        sqrt_val = calculator._calculate_breadth_sqrt(Decimal("400"))
        assert abs(sqrt_val - Decimal("20.0")) < Decimal("0.01")

    def test_assess_skill_level(self):
        """Test skill level assessment."""
        calculator = FundamentalLawCalculator()
        assert calculator._assess_skill_level(Decimal("0.06")) == "excellent"
        assert calculator._assess_skill_level(Decimal("0.04")) == "good"
        assert calculator._assess_skill_level(Decimal("0.02")) == "fair"
        assert calculator._assess_skill_level(Decimal("0.005")) == "poor"

    def test_assess_breadth(self):
        """Test breadth assessment."""
        calculator = FundamentalLawCalculator()
        assert calculator._assess_breadth(Decimal("1500")) == "high"
        assert calculator._assess_breadth(Decimal("500")) == "medium"
        assert calculator._assess_breadth(Decimal("50")) == "low"

    def test_assess_ir(self):
        """Test IR assessment."""
        calculator = FundamentalLawCalculator()
        assert calculator._assess_ir(Decimal("1.5")) == "excellent"
        assert calculator._assess_ir(Decimal("0.7")) == "good"
        assert calculator._assess_ir(Decimal("0.3")) == "fair"
        assert calculator._assess_ir(Decimal("0.1")) == "poor"

    def test_assess_tc(self):
        """Test TC assessment."""
        calculator = FundamentalLawCalculator()
        assert calculator._assess_tc(Decimal("0.9")) == "excellent"
        assert calculator._assess_tc(Decimal("0.7")) == "good"
        assert calculator._assess_tc(Decimal("0.5")) == "fair"
        assert calculator._assess_tc(Decimal("0.3")) == "poor"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestFundamentalLawIntegration:
    """Integration tests for the complete Fundamental Law workflow."""

    def test_full_workflow_analysis(self):
        """Test complete workflow from data to strategy analysis."""
        # Create sample data with positive correlation
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2020-01-01", periods=n, freq="D")

        # Create forecasts and make returns beat benchmark
        forecasts = pd.Series(np.random.randn(n) * 0.01, index=dates)
        # Returns should outperform benchmark
        returns = forecasts + pd.Series(np.random.randn(n) * 0.005, index=dates)
        # Benchmark is random with lower returns
        benchmark = pd.Series(np.random.randn(n) * 0.005, index=dates)

        # Calculate components
        calculator = FundamentalLawCalculator()
        components = calculator.decompose_ir(returns, forecasts, benchmark)

        # Analyze strategy
        analysis = calculator.analyze_strategy(components, "Integration Test Strategy")

        # Verify results
        assert isinstance(analysis, StrategyAnalysis)
        assert analysis.strategy_name == "Integration Test Strategy"
        # Components should be valid (IR is non-negative after clamping)
        assert components.validate(tolerance=Decimal("1.0"))  # Allow larger tolerance

    def test_ic_and_breadth_integration(self):
        """Test integration of IC and breadth calculations."""
        # Create returns data for breadth calculation
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns_df = pd.DataFrame(
            np.random.randn(252, 10) * 0.01,
            index=dates,
            columns=[f"asset_{i}" for i in range(10)],
        )

        # Calculate breadth
        br_calculator = BreadthCalculator()
        br_metrics = br_calculator.calculate_from_returns(returns_df)

        # Calculate IC for each asset
        ic_calculator = ICCalculator(min_observations=50)
        ics = []
        for asset in returns_df.columns:
            # Use past returns as forecast for current returns
            forecasts = returns_df[asset].shift(1).dropna()
            asset_returns = returns_df[asset].iloc[1:].loc[forecasts.index]
            if len(forecasts) >= 20:
                metrics = ic_calculator.calculate_ic(forecasts, asset_returns)
                ics.append(float(metrics.ic))

        # Verify we got some IC values
        assert len(ics) > 0
        assert br_metrics.effective_breadth > 0

    def test_strategy_comparison_workflow(self):
        """Test workflow for comparing multiple strategies."""
        calculator = FundamentalLawCalculator()

        # Define multiple strategies with different characteristics
        strategies = {
            "High Skill, Low Breadth": calculator.calculate_fundamental_law(
                information_ratio=Decimal("0.7"),
                information_coefficient=Decimal("0.07"),
                breadth=Decimal("100"),
            ),
            "Low Skill, High Breadth": calculator.calculate_fundamental_law(
                information_ratio=Decimal("0.7"),
                information_coefficient=Decimal("0.02"),
                breadth=Decimal("1225"),
            ),
            "Balanced": calculator.calculate_fundamental_law(
                information_ratio=Decimal("0.8"),
                information_coefficient=Decimal("0.04"),
                breadth=Decimal("400"),
            ),
        }

        # Compare strategies
        comparison = calculator.compare_strategies(strategies)

        # Analyze each strategy
        analyses = {}
        for name, components in strategies.items():
            analyses[name] = calculator.analyze_strategy(components, name)

        # Verify results
        assert len(comparison) == 3
        assert all(name in analyses for name in strategies.keys())

        # All should achieve similar IR but with different profiles
        ir_values = comparison["IR"].values
        assert all(abs(ir - 0.7) < 0.2 for ir in ir_values)


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_breadth(self):
        """Test handling of zero breadth."""
        calculator = FundamentalLawCalculator()
        # Zero breadth is valid (sqrt(0) = 0)
        # The result should be IR = 0 regardless of IC
        components = calculator.calculate_fundamental_law(
            information_ratio=Decimal("0"),
            information_coefficient=Decimal("0.05"),
            breadth=Decimal("0"),
        )
        assert components.breadth == Decimal("0")
        assert components.breadth_sqrt == Decimal("0")

    def test_perfect_correlation_ic(self, perfect_forecasts_and_returns):
        """Test IC with perfect correlation."""
        forecasts, returns = perfect_forecasts_and_returns
        calculator = ICCalculator()
        metrics = calculator.calculate_ic(forecasts, returns)
        # Handle edge case of perfect correlation
        assert metrics.ic <= Decimal("1.0")

    def test_constant_series_ic(self):
        """Test IC with constant series."""
        calculator = ICCalculator(min_observations=5)
        constant_series = pd.Series([0.01] * 50)
        returns = pd.Series([0.01] * 50)
        metrics = calculator.calculate_ic(constant_series, returns)
        # Should return zero IC for constant series
        assert metrics.ic == Decimal("0")

    def test_single_asset_breadth(self):
        """Test breadth with single asset."""
        calculator = BreadthCalculator()
        metrics = calculator.calculate_breadth(n_assets=1, rebalance_frequency="weekly")
        assert metrics.annual_breadth == Decimal("52")

    def test_very_large_breadth(self):
        """Test breadth with very large number of assets."""
        calculator = BreadthCalculator()
        metrics = calculator.calculate_breadth(n_assets=5000, rebalance_frequency="daily")
        assert metrics.annual_breadth == Decimal("1260000")  # 252 × 5000

    def test_negative_correlation_matrix(self):
        """Test independence factor with negative correlations."""
        calculator = BreadthCalculator()
        # Create matrix with some negative correlations
        n = 3
        corr = np.array([[1.0, -0.3, 0.2], [-0.3, 1.0, 0.1], [0.2, 0.1, 1.0]])
        corr_df = pd.DataFrame(corr)
        factor = calculator.calculate_independence_factor(corr_df)
        # Should still return a valid factor
        assert Decimal("0") <= factor <= Decimal("1")
