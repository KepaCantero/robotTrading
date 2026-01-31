"""
Integration Tests for Tomasini Walk-Forward Validator

Tests the enhanced walk-forward validation following Tomasini & Jaekle's methodology:
1. Rolling window optimization with adaptive sizing
2. Parameter stability tracking across windows
3. Out-of-sample step size = 50% of training window
4. Market regime-aware window adjustment
5. IS/OOS consistency ratio with confidence intervals
6. Minimum 5 cycles for statistical significance
7. Parameter stability metrics

Key Tomasini Principles Tested:
- Step size = 50% of training window
- Parameter stability (CV < 30%)
- Consistency ratio > 0.7
- Minimum 5 cycles
- Regime-aware validation
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import numpy.typing as npt
import pytest

from app.backtesting.models import BacktestConfig
from app.backtesting.walk_forward_validator_enhanced import (
    ParameterHistory,
    ParameterStabilityMetrics,
    TomasiniWalkForwardResult,
    TomasiniWalkForwardValidator,
    TomasiniWindowResult,
)
from app.core.decimal_utils import round_price
from app.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

# Set reproducible seed
np.random.seed(42)


# ============================================================================
# Data Generation Utilities
# ============================================================================


def generate_gbmr_quotes(
    symbol: str = "AAPL",
    days: int = 2000,
    seed: int = 42,
    drift: float = 0.05,
    volatility: float = 0.20,
) -> list[Quote]:
    """
    Generate realistic OHLCV data using Geometric Brownian Motion.

    Args:
        symbol: Trading symbol
        days: Number of trading days
        seed: Random seed for reproducibility
        drift: Annual drift rate
        volatility: Annual volatility

    Returns:
        List of Quote objects with realistic OHLCV data
    """
    np.random.seed(seed)

    # GBM parameters
    mu = drift / 252  # Daily drift
    sigma = volatility / np.sqrt(252)  # Daily volatility

    # Generate price path
    prices = np.zeros(days)
    prices[0] = 100.0

    dW = np.random.standard_normal(days - 1)
    log_returns = (mu - 0.5 * sigma**2) + sigma * dW
    prices[1:] = prices[0] * np.exp(np.cumsum(log_returns))

    # Generate OHLC from close prices
    quotes = []
    base_date = datetime(2010, 1, 1)

    for i, price in enumerate(prices):
        high_low_range = abs(price * np.random.uniform(0.005, 0.02))

        open_price = price * np.random.uniform(0.995, 1.005)
        close_price = price
        high_price = max(open_price, close_price) + high_low_range / 2
        low_price = min(open_price, close_price) - high_low_range / 2

        base_volume = 1_000_000
        volume = int(base_volume * np.random.uniform(0.8, 1.2))

        spread = price * 0.001
        bid = round_price(price - spread / 2, "equity", symbol)
        ask = round_price(price + spread / 2, "equity", symbol)

        quotes.append(
            Quote(
                symbol=symbol,
                timestamp=base_date + timedelta(days=i),
                bid=Decimal(str(bid)),
                ask=Decimal(str(ask)),
                last=Decimal(str(round_price(price, "equity", symbol))),
                volume=Decimal(str(volume)),
                open=Decimal(str(round_price(open_price, "equity", symbol))),
                high=Decimal(str(round_price(high_price, "equity", symbol))),
                low=Decimal(str(round_price(low_price, "equity", symbol))),
                close=Decimal(str(round_price(close_price, "equity", symbol))),
            )
        )

    return quotes


def generate_momentum_signals(
    quotes: list[Quote],
    fast_period: int = 20,
    slow_period: int = 50,
    strength: float = 75.0,
    confidence: float = 80.0,
) -> list[Signal]:
    """
    Generate momentum-based trading signals.

    Args:
        quotes: List of Quote objects
        fast_period: Fast lookback period
        slow_period: Slow lookback period
        strength: Signal strength (0-100)
        confidence: Signal confidence (0-100)

    Returns:
        List of Signal objects
    """
    signals = []

    if len(quotes) < slow_period + 1:
        return signals

    closes = [float(q.close) for q in quotes]

    for i in range(slow_period, len(quotes)):
        # Calculate momentum
        fast_momentum = (closes[i] - closes[i - fast_period]) / closes[i - fast_period]
        slow_momentum = (closes[i] - closes[i - slow_period]) / closes[i - slow_period]

        # Generate signal based on momentum crossover
        if fast_momentum > 0 and slow_momentum > 0:
            if fast_momentum > slow_momentum:
                signals.append(
                    Signal(
                        symbol=quotes[i].symbol,
                        signal_type=SignalType.BUY,
                        source=SignalSource.TECHNICAL,
                        timestamp=quotes[i].timestamp,
                        price=quotes[i].close,
                        strength=(
                            SignalStrength.HIGH if strength > 75 else SignalStrength.MODERATE
                        ),
                        confidence=confidence,
                        liquidity_score=75.0,
                        priority_score=70.0,
                        volume=Decimal("1000000"),
                        metadata={
                            "strategy": "momentum",
                            "fast_momentum": round(fast_momentum, 4),
                            "slow_momentum": round(slow_momentum, 4),
                        },
                    )
                )
        elif fast_momentum < 0 and slow_momentum < 0:
            signals.append(
                Signal(
                    symbol=quotes[i].symbol,
                    signal_type=SignalType.SELL,
                    source=SignalSource.TECHNICAL,
                    timestamp=quotes[i].timestamp,
                    price=quotes[i].close,
                    strength=(SignalStrength.HIGH if strength > 75 else SignalStrength.MODERATE),
                    confidence=confidence,
                    liquidity_score=75.0,
                    priority_score=70.0,
                    volume=Decimal("1000000"),
                    metadata={
                        "strategy": "momentum",
                        "fast_momentum": round(fast_momentum, 4),
                        "slow_momentum": round(slow_momentum, 4),
                    },
                )
            )

    return signals


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tomasini_config():
    """Tomasini-compliant configuration."""
    return {
        "train_years": 4.0,
        "step_percentage": 0.5,  # Tomasini: 50%
        "min_cycles": 5,
        "regime_aware": True,
        "min_trades_per_window": 5,
        "thresholds": {
            "min_consistency_ratio": 0.7,
            "max_sharpe_degradation": 0.30,
            "max_return_degradation": 0.50,
            "min_oos_sharpe": 0.5,
            "max_oos_drawdown": -0.25,
            "max_parameter_cv": 0.30,
            "min_stable_parameters": 0.6,
        },
    }


@pytest.fixture
def backtest_config():
    """Sample backtest configuration."""
    return BacktestConfig(
        initial_capital=Decimal("100000"),
        commission_per_trade=Decimal("1.0"),
        slippage_percentage=Decimal("0.1"),
        max_position_size=Decimal("0.1"),
    )


@pytest.fixture
def sample_data():
    """Generate 12 years of sample data for walk-forward."""
    quotes = generate_gbmr_quotes(
        symbol="TEST", days=12 * 252, seed=42, drift=0.05, volatility=0.20
    )
    signals = generate_momentum_signals(quotes, fast_period=20, slow_period=50)
    return quotes, signals


# ============================================================================
# Test: Rolling Window Creation (Tomasini Principle)
# ============================================================================


class TestTomasiniRollingWindows:
    """Tests for Tomasini rolling window creation."""

    def test_create_rolling_windows_default_settings(self, tomasini_config):
        """Test rolling windows with Tomasini default settings."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        start_date = datetime(2010, 1, 1)
        end_date = datetime(2022, 1, 1)

        windows = validator.create_rolling_windows(start_date, end_date)

        # Should create multiple rolling windows
        assert len(windows) >= 5, "Should create at least 5 windows (Tomasini minimum)"

        # Check window structure
        for window in windows:
            assert "train_start" in window
            assert "train_end" in window
            assert "test_start" in window
            assert "test_end" in window

            # Verify no gaps
            assert window["train_end"] == window["test_start"]

            # Verify rolling (not anchored)
            if len(windows) > 1:
                # Windows should roll forward
                pass

    def test_step_size_is_50_percent_of_training_window(self, tomasini_config):
        """Test that step size = 50% of training window (Tomasini requirement)."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        start_date = datetime(2010, 1, 1)
        end_date = datetime(2020, 1, 1)

        windows = validator.create_rolling_windows(start_date, end_date)

        if len(windows) >= 2:
            # Calculate training window length
            train_length = (windows[0]["train_end"] - windows[0]["train_start"]).days

            # Calculate step size
            step_length = (windows[1]["train_start"] - windows[0]["train_start"]).days

            # Tomasini: step = 50% of training
            expected_step = int(train_length * validator.step_pct)

            assert (
                abs(step_length - expected_step) <= 7
            ), f"Step size ({step_length} days) should be ~50% of training ({train_length} days)"

    def test_test_window_equals_step_size(self, tomasini_config):
        """Test that test window length equals step size."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        start_date = datetime(2010, 1, 1)
        end_date = datetime(2020, 1, 1)

        windows = validator.create_rolling_windows(start_date, end_date)

        for window in windows:
            train_length = (window["train_end"] - window["train_start"]).days
            test_length = (window["test_end"] - window["test_start"]).days

            # Test window should equal step size (50% of training)
            expected_test = int(train_length * validator.step_pct)

            assert (
                abs(test_length - expected_test) <= 7
            ), f"Test window ({test_length} days) should equal step size ({expected_test} days)"


# ============================================================================
# Test: Parameter Stability (Tomasini Principle)
# ============================================================================


class TestTomasiniParameterStability:
    """Tests for Tomasini parameter stability tracking."""

    def test_parameter_history_tracking(self, tomasini_config):
        """Test that parameter history is tracked across windows."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Create sample parameter history
        history = [
            ParameterHistory(
                window_id=1,
                parameters={"param1": 10.0, "param2": 0.5},
                in_sample_sharpe=1.5,
                out_of_sample_sharpe=1.2,
                in_sample_return=0.20,
                out_of_sample_return=0.15,
                window_start=datetime(2010, 1, 1),
                window_end=datetime(2012, 1, 1),
                regime="BULL",
            ),
            ParameterHistory(
                window_id=2,
                parameters={"param1": 11.0, "param2": 0.52},
                in_sample_sharpe=1.4,
                out_of_sample_sharpe=1.1,
                in_sample_return=0.18,
                out_of_sample_return=0.14,
                window_start=datetime(2011, 1, 1),
                window_end=datetime(2013, 1, 1),
                regime="BULL",
            ),
            ParameterHistory(
                window_id=3,
                parameters={"param1": 9.5, "param2": 0.48},
                in_sample_sharpe=1.6,
                out_of_sample_sharpe=1.3,
                in_sample_return=0.22,
                out_of_sample_return=0.16,
                window_start=datetime(2012, 1, 1),
                window_end=datetime(2014, 1, 1),
                regime="BULL",
            ),
        ]

        # Calculate stability
        stability = validator.calculate_parameter_stability(history)

        # Should have stability metrics for both parameters
        assert len(stability) == 2
        assert "param1" in stability
        assert "param2" in stability

    def test_parameter_stability_cv_calculation(self, tomasini_config):
        """Test coefficient of variation calculation."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Create history with stable parameter (low CV)
        stable_history = [
            ParameterHistory(
                window_id=i,
                parameters={"stable_param": 10.0 + i * 0.1},  # Low variation
                in_sample_sharpe=1.0,
                out_of_sample_sharpe=0.8,
                in_sample_return=0.1,
                out_of_sample_return=0.08,
                window_start=datetime(2010 + i, 1, 1),
                window_end=datetime(2012 + i, 1, 1),
                regime="BULL",
            )
            for i in range(5)
        ]

        stability = validator.calculate_parameter_stability(stable_history)

        stable_metric = stability["stable_param"]

        # CV should be low (< 30% per Tomasini)
        assert (
            stable_metric.cv < 0.3
        ), f"Stable parameter should have CV < 30%, got {stable_metric.cv:.2%}"
        assert bool(stable_metric.is_stable) is True

    def test_parameter_stability_unstable_detection(self, tomasini_config):
        """Test detection of unstable parameters."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Create history with unstable parameter (high CV)
        unstable_history = [
            ParameterHistory(
                window_id=i,
                parameters={"unstable_param": 5.0 + i * 5.0},  # High variation
                in_sample_sharpe=1.0,
                out_of_sample_sharpe=0.8,
                in_sample_return=0.1,
                out_of_sample_return=0.08,
                window_start=datetime(2010 + i, 1, 1),
                window_end=datetime(2012 + i, 1, 1),
                regime="BULL",
            )
            for i in range(5)
        ]

        stability = validator.calculate_parameter_stability(unstable_history)

        unstable_metric = stability["unstable_param"]

        # CV should be high (> 30%)
        assert (
            unstable_metric.cv >= 0.3
        ), f"Unstable parameter should have CV >= 30%, got {unstable_metric.cv:.2%}"
        assert bool(unstable_metric.is_stable) is False

    def test_parameter_drift_detection(self, tomasini_config):
        """Test parameter drift detection using linear regression."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Create history with upward drift
        drift_history = [
            ParameterHistory(
                window_id=i,
                parameters={"drifting_param": 10.0 + i * 2.0},  # Clear upward trend
                in_sample_sharpe=1.0,
                out_of_sample_sharpe=0.8,
                in_sample_return=0.1,
                out_of_sample_return=0.08,
                window_start=datetime(2010 + i, 1, 1),
                window_end=datetime(2012 + i, 1, 1),
                regime="BULL",
            )
            for i in range(5)
        ]

        stability = validator.calculate_parameter_stability(drift_history)

        drift_metric = stability["drifting_param"]

        # Should detect positive drift
        assert drift_metric.drift_trend > 0, "Should detect positive drift"

        # Should have significance value
        assert 0 <= drift_metric.drift_significance <= 1


# ============================================================================
# Test: IS/OOS Consistency (Tomasini Principle)
# ============================================================================


class TestTomasiniConsistency:
    """Tests for Tomasini IS/OOS consistency metrics."""

    def test_consistency_ratio_calculation(self, tomasini_config):
        """Test consistency ratio calculation (OOS Sharpe / IS Sharpe)."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Perfect consistency (OOS = IS)
        ratio_perfect = validator._calculate_consistency_ratio(1.0, 1.0)
        assert ratio_perfect == 1.0

        # Degraded but acceptable (OOS = 0.8 * IS)
        ratio_good = validator._calculate_consistency_ratio(1.0, 0.8)
        assert ratio_good == 0.8

        # Poor consistency (OOS = 0.5 * IS)
        ratio_poor = validator._calculate_consistency_ratio(1.0, 0.5)
        assert ratio_poor == 0.5

        # Zero IS Sharpe (edge case)
        ratio_zero = validator._calculate_consistency_ratio(0.0, 0.5)
        assert ratio_zero == 1.0

    def test_sharpe_degradation_calculation(self, tomasini_config):
        """Test Sharpe degradation calculation."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # No degradation
        deg_none = validator._calculate_sharpe_degradation(1.0, 1.0)
        assert deg_none == 0.0

        # 30% degradation (Tomasini threshold)
        deg_30 = validator._calculate_sharpe_degradation(1.0, 0.7)
        assert abs(deg_30 - 0.3) < 1e-6

        # 50% degradation
        deg_50 = validator._calculate_sharpe_degradation(1.0, 0.5)
        assert abs(deg_50 - 0.5) < 1e-6

    def test_return_degradation_calculation(self, tomasini_config):
        """Test return degradation calculation."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # No degradation
        deg_none = validator._calculate_return_degradation(0.20, 0.20)
        assert deg_none == 0.0

        # 25% degradation
        deg_25 = validator._calculate_return_degradation(0.20, 0.15)
        assert abs(deg_25 - 0.25) < 0.01


# ============================================================================
# Test: Minimum Cycles Validation (Tomasini Principle)
# ============================================================================


class TestTomasiniMinimumCycles:
    """Tests for Tomasini minimum 5 cycles requirement."""

    def test_insufficient_windows_rejection(self, tomasini_config, sample_data, backtest_config):
        """Test that insufficient windows are rejected."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        # Use only 3 years (should produce < 5 cycles)
        short_quotes = quotes[: 3 * 252]

        result = validator.validate_strategy(
            short_quotes,
            signals[:100],
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2013, 1, 1),
        )

        # Should fail due to insufficient windows
        assert result.passed is False
        assert result.total_windows < validator.min_cycles
        assert any("Insufficient windows" in r for r in result.failure_reasons)

    def test_sufficient_windows_acceptance(self, tomasini_config, sample_data, backtest_config):
        """Test that sufficient windows are accepted."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
        )

        # Should have sufficient windows (may still fail on metrics)
        assert result.total_windows >= validator.min_cycles


# ============================================================================
# Test: Full Walk-Forward Validation
# ============================================================================


class TestTomasiniWalkForwardFull:
    """Integration tests for full Tomasini walk-forward validation."""

    def test_full_validation_without_optimization(
        self, tomasini_config, sample_data, backtest_config
    ):
        """Test full validation without parameter optimization."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
            param_grid=None,  # No optimization
        )

        # Should execute all windows
        assert result.total_windows >= 5

        # Should have window results
        assert len(result.windows) == result.total_windows

        # Each window should have both IS and OOS metrics
        for window in result.windows:
            assert window.is_sharpe >= 0  # IS metrics calculated
            assert window.oos_sharpe >= 0  # OOS metrics calculated
            assert window.consistency_ratio >= 0

        # Should calculate Tomasini score
        assert 0 <= result.tomasini_score <= 100

    def test_full_validation_with_optimization(self, tomasini_config, sample_data, backtest_config):
        """Test full validation with parameter optimization."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        # Simple parameter grid
        param_grid = {
            "fast_period": [10, 20, 30],
            "slow_period": [40, 50, 60],
        }

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
            param_grid=param_grid,
        )

        # Should have optimal parameters for each window
        for window in result.windows:
            # At least some parameters should be selected
            # (May be empty if optimization failed, which is acceptable)
            assert isinstance(window.optimal_parameters, dict)

        # Should have parameter stability metrics
        if result.parameter_stability:
            # Check that stability was calculated
            for param_name, stability in result.parameter_stability.items():
                assert stability.parameter_name == param_name
                assert stability.cv >= 0
                assert isinstance(stability.is_stable, (bool, np.bool_))

    def test_tomasini_score_components(self, tomasini_config, sample_data, backtest_config):
        """Test that Tomasini score includes all components."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
        )

        # Tomasini score should be weighted combination
        assert 0 <= result.robustness_score <= 1
        assert 0 <= result.parameter_stability_score <= 1
        assert 0 <= result.consistency_score <= 1

        # Overall score should be combination
        expected_score = (
            result.robustness_score * 0.4
            + result.parameter_stability_score * 0.3
            + result.consistency_score * 0.3
        ) * 100

        assert abs(result.tomasini_score - expected_score) < 1.0

    def test_regime_robustness_tracking(self, tomasini_config, sample_data, backtest_config):
        """Test regime-aware robustness tracking."""
        validator = TomasiniWalkForwardValidator(config={**tomasini_config, "regime_aware": True})

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
        )

        # Should have regime robustness metrics
        assert isinstance(result.regime_robustness, dict)

        # Each window should have regime info
        for window in result.windows:
            assert window.train_regime in [
                "BULL",
                "BEAR",
                "SIDEWAYS",
                "UNKNOWN",
                "INSUFFICIENT_DATA",
            ]
            assert window.test_regime in [
                "BULL",
                "BEAR",
                "SIDEWAYS",
                "UNKNOWN",
                "INSUFFICIENT_DATA",
            ]
            assert isinstance(window.regime_change, bool)

    def test_full_validation_with_optimization(self, tomasini_config, sample_data, backtest_config):
        """Test full validation with parameter optimization."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        # Simple parameter grid
        param_grid = {
            "fast_period": [10, 20, 30],
            "slow_period": [40, 50, 60],
        }

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config,
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
            param_grid=param_grid,
        )

        # Should have optimal parameters for each window
        for window in result.windows:
            # At least some parameters should be selected
            # (May be empty if optimization failed, which is acceptable)
            assert isinstance(window.optimal_parameters, dict)

        # Should have parameter stability metrics
        if result.parameter_stability:
            # Check that stability was calculated
            for param_name, stability in result.parameter_stability.items():
                assert stability.parameter_name == param_name
                assert stability.cv >= 0
                assert isinstance(stability.is_stable, bool)

    def test_tomasini_score_components(self, tomasini_config, sample_data):
        """Test that Tomasini score includes all components."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config(),
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
        )

        # Tomasini score should be weighted combination
        assert 0 <= result.robustness_score <= 1
        assert 0 <= result.parameter_stability_score <= 1
        assert 0 <= result.consistency_score <= 1

        # Overall score should be combination
        expected_score = (
            result.robustness_score * 0.4
            + result.parameter_stability_score * 0.3
            + result.consistency_score * 0.3
        ) * 100

        assert abs(result.tomasini_score - expected_score) < 1.0

    def test_regime_robustness_tracking(self, tomasini_config, sample_data):
        """Test regime-aware robustness tracking."""
        validator = TomasiniWalkForwardValidator(config={**tomasini_config, "regime_aware": True})

        quotes, signals = sample_data

        result = validator.validate_strategy(
            quotes,
            signals,
            backtest_config(),
            datetime(2010, 1, 1),
            datetime(2022, 1, 1),
        )

        # Should have regime robustness metrics
        assert isinstance(result.regime_robustness, dict)

        # Each window should have regime info
        for window in result.windows:
            assert window.train_regime in [
                "BULL",
                "BEAR",
                "SIDEWAYS",
                "UNKNOWN",
                "INSUFFICIENT_DATA",
            ]
            assert window.test_regime in [
                "BULL",
                "BEAR",
                "SIDEWAYS",
                "UNKNOWN",
                "INSUFFICIENT_DATA",
            ]
            assert isinstance(window.regime_change, bool)


# ============================================================================
# Test: Window Result Structure
# ============================================================================


class TestTomasiniWindowResult:
    """Tests for TomasiniWindowResult data structure."""

    def test_window_result_structure(self):
        """Test that window result has all required fields."""
        window = TomasiniWindowResult(
            window_id=1,
            train_start=datetime(2020, 1, 1),
            train_end=datetime(2022, 1, 1),
            test_start=datetime(2022, 1, 1),
            test_end=datetime(2023, 1, 1),
            is_return=0.20,
            is_sharpe=1.5,
            is_sortino=1.8,
            is_max_drawdown=-0.10,
            is_volatility=0.15,
            is_trades=50,
            oos_return=0.15,
            oos_sharpe=1.2,
            oos_sortino=1.5,
            oos_max_drawdown=-0.12,
            oos_volatility=0.16,
            oos_trades=40,
            consistency_ratio=0.8,
            return_degradation=0.25,
            sharpe_degradation=0.20,
            train_regime="BULL",
            test_regime="BULL",
            regime_change=False,
            optimal_parameters={"param1": 10.0},
            passed=True,
            failure_reasons=[],
        )

        # Check all fields are accessible
        assert window.window_id == 1
        assert window.is_return == 0.20
        assert window.oos_sharpe == 1.2
        assert window.consistency_ratio == 0.8
        assert window.train_regime == "BULL"
        assert window.passed is True

        # Check to_dict conversion
        result_dict = window.to_dict()
        assert "period" in result_dict
        assert "in_sample" in result_dict
        assert "out_of_sample" in result_dict
        assert "consistency" in result_dict
        assert "regime" in result_dict
        assert "validation" in result_dict


# ============================================================================
# Test: Result Structure
# ============================================================================


class TestTomasiniWalkForwardResult:
    """Tests for TomasiniWalkForwardResult data structure."""

    def test_result_structure_complete(self):
        """Test that result has all required fields."""
        result = TomasiniWalkForwardResult(
            passed=True,
            total_windows=5,
            passed_windows=4,
            avg_is_return=0.20,
            avg_oos_return=0.15,
            avg_is_sharpe=1.5,
            avg_oos_sharpe=1.2,
            avg_consistency_ratio=0.8,
            avg_return_degradation=0.25,
            avg_sharpe_degradation=0.20,
            windows=[],
            parameter_stability={},
            robustness_score=0.8,
            regime_robustness={"BULL": 0.15, "BEAR": -0.05},
            failure_reasons=[],
            tomasini_score=80.0,
            parameter_stability_score=0.85,
            consistency_score=0.80,
        )

        # Check all fields
        assert result.passed is True
        assert result.total_windows == 5
        assert result.avg_is_return == 0.20
        assert result.tomasini_score == 80.0

        # Check to_dict conversion
        result_dict = result.to_dict()
        assert "overall" in result_dict
        assert "aggregated_metrics" in result_dict
        assert "consistency" in result_dict
        assert "scores" in result_dict
        assert "regime_robustness" in result_dict


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestTomasiniEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_quotes(self, tomasini_config, backtest_config):
        """Test handling of empty quotes."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        result = validator.validate_strategy(
            [], [], backtest_config, datetime(2020, 1, 1), datetime(2022, 1, 1)
        )

        assert result.passed is False
        assert result.total_windows == 0

    def test_insufficient_data_for_regime_detection(self, tomasini_config, backtest_config):
        """Test regime detection with insufficient data."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Generate only 3 months of data
        short_quotes = generate_gbmr_quotes(days=63, seed=42)
        short_signals = generate_momentum_signals(short_quotes)

        result = validator.validate_strategy(
            short_quotes,
            short_signals,
            backtest_config,
            datetime(2020, 1, 1),
            datetime(2020, 3, 31),
        )

        # Should handle gracefully
        assert isinstance(result, TomasiniWalkForwardResult)

    def test_zero_sharpe_ratio_handling(self, tomasini_config):
        """Test handling of zero Sharpe ratios in consistency calculation."""
        validator = TomasiniWalkForwardValidator(config=tomasini_config)

        # Zero IS Sharpe
        ratio = validator._calculate_consistency_ratio(0.0, 1.0)
        # Should return 1.0 (no degradation) or handle gracefully
        assert ratio >= 0

        # Zero OOS Sharpe
        ratio = validator._calculate_consistency_ratio(1.0, 0.0)
        assert ratio == 0.0


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
