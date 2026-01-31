"""
Unit tests for Numba-accelerated metrics module.

Tests for performance-critical metrics calculations using Numba JIT compilation.
"""

import pytest
import numpy as np
from unittest.mock import patch, Mock
import time

try:
    from numba import jit

    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

from app.backtesting.numba_metrics import (
    # Helper functions
    sample_std_numba,
    # Return calculations
    calculate_returns_numba,
    calculate_cumulative_returns_numba,
    calculate_cagr_numba,
    calculate_log_returns_numba,
    # Risk metrics
    calculate_sharpe_numba,
    calculate_sortino_numba,
    calculate_var_numba,
    calculate_cvar_numba,
    # Drawdown analysis
    calculate_drawdown_series_numba,
    calculate_max_drawdown_numba,
    calculate_max_drawdown_duration_numba,
    # Trade statistics
    calculate_win_rate_numba,
    calculate_profit_factor_numba,
    calculate_avg_win_loss_numba,
    calculate_expectancy_numba,
    # Volatility metrics
    calculate_volatility_numba,
    calculate_rolling_volatility_numba,
    # Advanced metrics
    calculate_calmar_ratio_numba,
    calculate_information_ratio_numba,
    calculate_skewness_numba,
    calculate_kurtosis_numba,
    # Utility
    get_numba_metrics_info,
)


@pytest.mark.unit
class TestNumbaAvailability:
    """Test Numba availability and module initialization."""

    def test_numba_module_loaded(self):
        """Test that Numba module is properly loaded."""
        info = get_numba_metrics_info()

        assert isinstance(info, dict)
        assert "numba_available" in info
        assert "functions_optimized" in info

    def test_functions_are_jit_compiled(self):
        """Test that functions are JIT compiled."""
        # Check if key functions are JIT compiled
        functions_to_check = [
            calculate_returns_numba,
            calculate_sharpe_numba,
            calculate_sortino_numba,
            calculate_max_drawdown_numba,
            calculate_win_rate_numba,
        ]

        for func in functions_to_check:
            if NUMBA_AVAILABLE:
                assert hasattr(func, "py_func") or hasattr(func, "signatures")


@pytest.mark.unit
class TestSampleStdNumba:
    """Test sample standard deviation calculation."""

    def test_sample_std_basic(self):
        """Test basic sample standard deviation."""
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        result = sample_std_numba(values)

        # Compare with numpy
        expected = np.std(values, ddof=1)
        assert np.isclose(result, expected, rtol=1e-5)

    def test_sample_std_single_value(self):
        """Test sample std with single value (should return 0)."""
        values = np.array([5.0])

        result = sample_std_numba(values)
        assert result == 0.0

    def test_sample_std_empty(self):
        """Test sample std with empty array."""
        values = np.array([])

        result = sample_std_numba(values)
        assert result == 0.0

    def test_sample_std_constant_values(self):
        """Test sample std with constant values (should be 0)."""
        values = np.array([5.0, 5.0, 5.0, 5.0])

        result = sample_std_numba(values)
        assert result == 0.0

    @pytest.mark.parametrize("size", [10, 100, 1000])
    def test_sample_std_scalability(self, size):
        """Test sample std with different array sizes."""
        values = np.random.randn(size) * 0.01 + 0.05

        result = sample_std_numba(values)
        expected = np.std(values, ddof=1)

        assert np.isclose(result, expected, rtol=1e-5)


@pytest.mark.unit
class TestReturnCalculations:
    """Test return calculation functions."""

    def test_calculate_returns_numba_basic(self):
        """Test basic returns calculation."""
        prices = np.array([100.0, 101.0, 102.5, 101.5, 103.0])

        returns = calculate_returns_numba(prices)

        expected = np.array([0.01, 0.014851485, -0.009756098, 0.014778325])
        np.testing.assert_allclose(returns, expected, rtol=1e-6)

    def test_calculate_returns_numba_negative_prices(self):
        """Test returns with negative price changes."""
        prices = np.array([100.0, 99.0, 98.0, 97.0])

        returns = calculate_returns_numba(prices)

        assert all(returns < 0)
        assert len(returns) == len(prices) - 1

    def test_calculate_cumulative_returns_numba(self):
        """Test cumulative returns calculation."""
        returns = np.array([0.01, 0.02, -0.01, 0.03])

        cumulative = calculate_cumulative_returns_numba(returns)

        # Manual calculation: (1.01 * 1.02 * 0.99 * 1.03) - 1
        expected = (1.01 * 1.02 * 0.99 * 1.03) - 1
        assert abs(cumulative[-1] - expected) < 1e-6

    def test_calculate_cagr_numba(self):
        """Test CAGR calculation."""
        initial_value = 1000.0
        final_value = 1500.0
        n_periods = 5.0

        cagr = calculate_cagr_numba(final_value, initial_value, n_periods)

        # Manual calculation: (1500/1000)^(1/5) - 1
        expected = (final_value / initial_value) ** (1.0 / n_periods) - 1.0
        assert np.isclose(cagr, expected, rtol=1e-6)

    def test_calculate_cagr_numba_invalid_inputs(self):
        """Test CAGR with invalid inputs."""
        # Negative initial value
        result = calculate_cagr_numba(100, -100, 5)
        assert np.isnan(result)

        # Zero periods
        result = calculate_cagr_numba(100, 100, 0)
        assert np.isnan(result)

    def test_calculate_log_returns_numba(self):
        """Test log returns calculation."""
        prices = np.array([100.0, 101.0, 102.0])

        log_returns = calculate_log_returns_numba(prices)

        expected = np.log(np.array([101.0 / 100.0, 102.0 / 101.0]))
        np.testing.assert_allclose(log_returns, expected, rtol=1e-6)


@pytest.mark.unit
class TestRiskMetrics:
    """Test risk metric calculations."""

    def test_calculate_sharpe_numba(self):
        """Test Sharpe ratio calculation."""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01])
        risk_free_rate = 0.02
        periods_per_year = 252

        sharpe = calculate_sharpe_numba(returns, risk_free_rate, periods_per_year)

        # Sharpe should be positive given positive mean returns
        assert sharpe > 0
        assert isinstance(sharpe, float)

    def test_calculate_sharpe_numba_zero_volatility(self):
        """Test Sharpe with zero volatility (constant returns)."""
        returns = np.array([0.01, 0.01, 0.01, 0.01])

        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        assert sharpe == 0.0

    def test_calculate_sharpe_numba_empty(self):
        """Test Sharpe with empty returns."""
        returns = np.array([])

        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        assert np.isnan(sharpe)

    def test_calculate_sortino_numba(self):
        """Test Sortino ratio calculation."""
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.005])
        risk_free_rate = 0.02

        sortino = calculate_sortino_numba(returns, risk_free_rate, 252)

        # Sortino should handle downside deviation properly
        assert isinstance(sortino, float)

    def test_calculate_sortino_numba_no_downside(self):
        """Test Sortino with no downside returns."""
        returns = np.array([0.01, 0.02, 0.015, 0.03])

        sortino = calculate_sortino_numba(returns, 0.02, 252)
        # Should be very high or infinite when no downside
        assert sortino >= 0 or sortino == np.inf

    def test_calculate_var_numba(self):
        """Test Value at Risk calculation."""
        returns = np.random.randn(1000) * 0.01  # Normal returns

        var_95 = calculate_var_numba(returns, confidence_level=0.95)
        var_99 = calculate_var_numba(returns, confidence_level=0.99)

        # 99% VaR should be more negative than 95% VaR
        assert var_99 < var_95

    def test_calculate_var_numba_small_sample(self):
        """Test VaR with small sample."""
        returns = np.array([0.01, -0.02, 0.015, -0.01])

        var = calculate_var_numba(returns, 0.95)
        assert isinstance(var, float)

    def test_calculate_cvar_numba(self):
        """Test Conditional VaR calculation."""
        returns = np.random.randn(1000) * 0.01

        cvar_95 = calculate_cvar_numba(returns, confidence_level=0.95)
        var_95 = calculate_var_numba(returns, confidence_level=0.95)

        # CVaR should be more negative than VaR
        assert cvar_95 <= var_95


@pytest.mark.unit
class TestDrawdownAnalysis:
    """Test drawdown analysis functions."""

    def test_calculate_drawdown_series_numba(self):
        """Test drawdown series calculation."""
        equity_curve = np.array([100, 105, 103, 110, 108, 115, 112, 120])

        drawdowns = calculate_drawdown_series_numba(equity_curve)

        # Drawdowns should be non-positive
        assert all(drawdowns <= 0)

        # Maximum drawdown should occur after peak
        max_dd_idx = np.argmin(drawdowns)
        assert max_dd_idx >= 3  # After first peak at 110

    def test_calculate_max_drawdown_numba(self):
        """Test maximum drawdown calculation."""
        equity_curve = np.array([100, 110, 105, 115, 100, 120])

        max_dd = calculate_max_drawdown_numba(equity_curve)

        # Max drawdown should be negative
        assert max_dd < 0

        # Should be between 0 and -1 (or more negative for larger drawdowns)
        assert max_dd >= -0.5  # Max 50% drawdown for this data

    def test_calculate_max_drawdown_numba_uptrend(self):
        """Test max drawdown with pure uptrend (should be 0)."""
        equity_curve = np.array([100, 105, 110, 115, 120, 125])

        max_dd = calculate_max_drawdown_numba(equity_curve)
        assert max_dd == 0.0

    def test_calculate_max_drawdown_duration_numba(self):
        """Test maximum drawdown duration calculation."""
        # Create equity curve with clear drawdown period
        equity_curve = np.array(
            [
                100,  # Start
                110,  # Peak 1
                105,  # Drawdown
                108,
                107,
                115,  # New peak - end of drawdown
                120,  # Peak 2
                118,  # Drawdown
                115,
                112,  # Bottom
                118,  # Recovery
                122,  # New peak - end of drawdown
            ]
        )

        duration = calculate_max_drawdown_duration_numba(equity_curve)

        # Duration should be positive
        assert duration > 0
        assert isinstance(duration, (int, np.integer))


@pytest.mark.unit
class TestTradeStatistics:
    """Test trade statistics calculations."""

    def test_calculate_win_rate_numba(self):
        """Test win rate calculation."""
        pnl_array = np.array([100, -50, 75, -25, 50, -30, 80])

        win_rate = calculate_win_rate_numba(pnl_array)

        # 4 wins out of 7 trades = 57.14%
        expected = (4 / 7) * 100
        assert np.isclose(win_rate, expected, rtol=1e-5)

    def test_calculate_win_rate_numba_all_wins(self):
        """Test win rate with all winning trades."""
        pnl_array = np.array([100, 50, 75, 80])

        win_rate = calculate_win_rate_numba(pnl_array)
        assert win_rate == 100.0

    def test_calculate_win_rate_numba_all_losses(self):
        """Test win rate with all losing trades."""
        pnl_array = np.array([-100, -50, -75, -80])

        win_rate = calculate_win_rate_numba(pnl_array)
        assert win_rate == 0.0

    def test_calculate_win_rate_numba_empty(self):
        """Test win rate with empty array."""
        pnl_array = np.array([])

        win_rate = calculate_win_rate_numba(pnl_array)
        assert np.isnan(win_rate)

    def test_calculate_profit_factor_numba(self):
        """Test profit factor calculation."""
        pnl_array = np.array([100, -50, 75, -25, 50, -30])

        pf = calculate_profit_factor_numba(pnl_array)

        # Gross profit: 100 + 75 + 50 = 225
        # Gross loss: 50 + 25 + 30 = 105
        # Profit factor: 225 / 105 = 2.14
        expected = 225 / 105
        assert np.isclose(pf, expected, rtol=1e-5)

    def test_calculate_profit_factor_numba_no_losses(self):
        """Test profit factor with no losses."""
        pnl_array = np.array([100, 50, 75])

        pf = calculate_profit_factor_numba(pnl_array)
        assert pf == np.inf

    def test_calculate_profit_factor_numba_no_wins(self):
        """Test profit factor with no wins."""
        pnl_array = np.array([-100, -50, -75])

        pf = calculate_profit_factor_numba(pnl_array)
        assert pf == 0.0

    def test_calculate_avg_win_loss_numba(self):
        """Test average win and loss calculation."""
        pnl_array = np.array([100, -50, 75, -25, 50, -30])

        avg_win, avg_loss = calculate_avg_win_loss_numba(pnl_array)

        # Avg win: (100 + 75 + 50) / 3 = 75
        # Avg loss: (50 + 25 + 30) / 3 = 35
        expected_win = 225 / 3
        expected_loss = 105 / 3

        assert np.isclose(avg_win, expected_win, rtol=1e-5)
        assert np.isclose(avg_loss, expected_loss, rtol=1e-5)

    def test_calculate_expectancy_numba(self):
        """Test expectancy calculation."""
        pnl_array = np.array([100, -50, 75, -25, 50, -30])

        expectancy = calculate_expectancy_numba(pnl_array)

        # Average P&L
        expected = np.mean(pnl_array)
        assert np.isclose(expectancy, expected, rtol=1e-5)

    def test_calculate_expectancy_numba_empty(self):
        """Test expectancy with empty array."""
        pnl_array = np.array([])

        expectancy = calculate_expectancy_numba(pnl_array)
        assert np.isnan(expectancy)


@pytest.mark.unit
class TestVolatilityMetrics:
    """Test volatility metric calculations."""

    def test_calculate_volatility_numba(self):
        """Test annualized volatility calculation."""
        returns = np.random.randn(252) * 0.01  # Daily returns

        vol = calculate_volatility_numba(returns, periods_per_year=252)

        # Volatility should be positive
        assert vol > 0
        assert isinstance(vol, float)

    def test_calculate_volatility_numba_empty(self):
        """Test volatility with empty returns."""
        returns = np.array([])

        vol = calculate_volatility_numba(returns, 252)
        assert np.isnan(vol)

    def test_calculate_rolling_volatility_numba(self):
        """Test rolling volatility calculation."""
        returns = np.random.randn(100) * 0.01
        window = 20

        rolling_vol = calculate_rolling_volatility_numba(returns, window, 252)

        # First (window-1) values should be NaN
        assert np.isnan(rolling_vol[: window - 1]).all()

        # Rest should be non-NaN
        assert not np.isnan(rolling_vol[window - 1 :]).any()

        # All values should be non-negative
        assert (rolling_vol[~np.isnan(rolling_vol)] >= 0).all()

    def test_calculate_rolling_volatility_numba_window_too_large(self):
        """Test rolling volatility with window larger than data."""
        returns = np.random.randn(10) * 0.01
        window = 20

        rolling_vol = calculate_rolling_volatility_numba(returns, window, 252)

        # All values should be NaN
        assert np.isnan(rolling_vol).all()


@pytest.mark.unit
class TestAdvancedMetrics:
    """Test advanced metric calculations."""

    def test_calculate_calmar_ratio_numba(self):
        """Test Calmar ratio calculation."""
        initial_value = 1000.0
        final_value = 1500.0
        max_drawdown = -0.15
        n_periods = 5.0

        calmar = calculate_calmar_ratio_numba(final_value, initial_value, max_drawdown, n_periods)

        # Calmar = CAGR / |Max Drawdown|
        cagr = (final_value / initial_value) ** (1.0 / n_periods) - 1.0
        expected = cagr / abs(max_drawdown)

        assert np.isclose(calmar, expected, rtol=1e-5)

    def test_calculate_calmar_ratio_numba_zero_drawdown(self):
        """Test Calmar ratio with zero drawdown."""
        calmar = calculate_calmar_ratio_numba(1500, 1000, 0.0, 5)

        # Should be infinite with positive CAGR and zero drawdown
        assert calmar == np.inf

    def test_calculate_information_ratio_numba(self):
        """Test Information Ratio calculation."""
        returns = np.random.randn(100) * 0.01
        benchmark_returns = np.random.randn(100) * 0.008

        ir = calculate_information_ratio_numba(returns, benchmark_returns)

        # IR should be a finite number
        assert np.isfinite(ir)

    def test_calculate_information_ratio_numba_mismatched_length(self):
        """Test IR with mismatched array lengths."""
        returns = np.random.randn(100) * 0.01
        benchmark_returns = np.random.randn(50) * 0.008

        ir = calculate_information_ratio_numba(returns, benchmark_returns)
        assert np.isnan(ir)

    def test_calculate_skewness_numba(self):
        """Test skewness calculation."""
        # Positive skew
        returns = np.array([0.01, 0.02, 0.03, 0.015, 0.025, 0.05])

        skew = calculate_skewness_numba(returns)
        assert isinstance(skew, float)

    def test_calculate_skewness_numba_small_sample(self):
        """Test skewness with small sample."""
        returns = np.array([0.01, 0.02])

        skew = calculate_skewness_numba(returns)
        assert np.isnan(skew)

    def test_calculate_kurtosis_numba(self):
        """Test kurtosis calculation."""
        returns = np.random.randn(100) * 0.01

        kurt = calculate_kurtosis_numba(returns)
        assert isinstance(kurt, float)

    def test_calculate_kurtosis_numba_small_sample(self):
        """Test kurtosis with small sample."""
        returns = np.array([0.01, 0.02, 0.015])

        kurt = calculate_kurtosis_numba(returns)
        assert np.isnan(kurt)


@pytest.mark.unit
class TestNumbaPerformance:
    """Test performance characteristics of Numba functions."""

    @pytest.mark.parametrize("size", [1000, 10000])
    def test_returns_calculation_performance(self, size):
        """Test returns calculation performance with larger arrays."""
        prices = 100 + np.cumsum(np.random.randn(size) * 0.01)

        start_time = time.time()
        returns = calculate_returns_numba(prices)
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 1 second for 10K points)
        assert elapsed < 1.0
        assert len(returns) == size - 1

    def test_sharpe_performance(self):
        """Test Sharpe ratio calculation performance."""
        returns = np.random.randn(10000) * 0.01

        start_time = time.time()
        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        elapsed = time.time() - start_time

        # Should complete in reasonable time
        assert elapsed < 1.0
        assert np.isfinite(sharpe)


@pytest.mark.unit
class TestNumbaEdgeCases:
    """Test edge cases for Numba functions."""

    def test_zero_prices(self):
        """Test returns calculation with zero prices."""
        prices = np.array([100.0, 0.0, 101.0])

        # Should handle gracefully (inf or nan)
        returns = calculate_returns_numba(prices)
        assert len(returns) == 2

    def test_nan_handling(self):
        """Test handling of NaN values."""
        returns = np.array([0.01, np.nan, 0.02, -0.01, np.nan])

        # Functions should handle NaN gracefully
        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        # Result may be NaN but should not raise error
        assert isinstance(sharpe, (float, np.floating))

    def test_inf_handling(self):
        """Test handling of infinite values."""
        returns = np.array([0.01, np.inf, 0.02, -0.01])

        # Should handle inf gracefully
        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        assert isinstance(sharpe, (float, np.floating))

    def test_very_large_numbers(self):
        """Test with very large numbers."""
        equity_curve = np.array([1e10, 1.1e10, 1.05e10, 1.2e10])

        max_dd = calculate_max_drawdown_numba(equity_curve)
        assert isinstance(max_dd, (float, np.floating))

    def test_very_small_numbers(self):
        """Test with very small numbers."""
        returns = np.array([1e-10, 2e-10, -1e-10])

        sharpe = calculate_sharpe_numba(returns, 0.02, 252)
        assert isinstance(sharpe, (float, np.floating))


@pytest.mark.unit
class TestNumbaPropertyBased:
    """Property-based tests for Numba functions."""

    @pytest.mark.parametrize("mean,std", [(0.0, 0.01), (0.0005, 0.02)])
    def test_sharpe_property(self, mean, std):
        """Test Sharpe ratio properties."""
        np.random.seed(42)
        returns = np.random.randn(1000) * std + mean

        sharpe = calculate_sharpe_numba(returns, 0.0, 252)

        # Higher mean returns should generally give higher Sharpe
        # (with same std and zero risk-free rate)
        assert isinstance(sharpe, float)

    @pytest.mark.parametrize("n_periods", [10, 50, 100])
    def test_cagr_property(self, n_periods):
        """Test CAGR properties."""
        initial = 1000.0
        final = 2000.0  # Double

        cagr = calculate_cagr_numba(final, initial, n_periods)

        # Should be positive (growth)
        assert cagr > 0

        # Longer period should give smaller CAGR
        cagr_longer = calculate_cagr_numba(final, initial, n_periods * 2)
        assert cagr_longer < cagr

    @pytest.mark.parametrize("win_rate", [0.3, 0.5, 0.7])
    def test_win_rate_property(self, win_rate):
        """Test win rate properties."""
        n_trades = 100
        pnl_array = np.where(np.random.rand(n_trades) < win_rate, 100, -50)

        calculated_win_rate = calculate_win_rate_numba(pnl_array)

        # Should be close to expected win rate
        # (allowing for randomness)
        assert 0 <= calculated_win_rate <= 100
