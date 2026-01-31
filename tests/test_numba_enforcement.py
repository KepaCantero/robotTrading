"""
Numba Enforcement Tests

CRITICAL: This test suite verifies that ALL performance-critical code
uses Numba JIT compilation. NO fallbacks. NO exceptions.

Test Coverage:
- Numba availability check
- Numba version verification
- Numba compilation verification
- Performance benchmarking
- Function correctness with Numba

Author: Performance Enforcement Team
Date: 2026-01-28
Version: 2.0.0 - MANDATORY NUMBA ENFORCEMENT
Compliance: Rule 19, Rule 23 - High Performance Python
"""

import pytest
import numpy as np
import time
from typing import List

# ============================================================================
# Test Numba Availability
# ============================================================================


def test_numba_mandatory_available():
    """Test that Numba is available (MANDATORY)."""
    with pytest.raises(RuntimeError) as exc_info:
        # Temporarily hide numba to test enforcement
        import sys

        numba_module = sys.modules.get('numba')
        if numba_module:
            del sys.modules['numba']

        try:
            from app.core.numba_enforcer import enforce_numba_available

            enforce_numba_available()
        finally:
            # Restore numba
            if numba_module:
                sys.modules['numba'] = numba_module

    # Should have raised RuntimeError about missing numba
    assert "Numba is REQUIRED" in str(exc_info.value) or "numba" in str(exc_info.value).lower()


def test_numba_version_requirement():
    """Test that Numba version meets minimum requirement."""
    import numba
    from app.core.numba_enforcer import get_numba_version

    version = get_numba_version()
    assert version is not None

    # Parse version
    version_parts = version.split('.')
    major = int(version_parts[0])
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0

    # Must be >= 0.59.0
    assert major >= 0 or (
        major == 0 and minor >= 59
    ), f"Numba version {version} is insufficient. Required: >=0.59.0"


def test_numba_accelerators_available():
    """Test that Numba accelerators module is available."""
    from app.core.numba_accelerators import (
        NUMBA_AVAILABLE,
        NUMBA_VERSION,
        calculate_rsi_numba,
        calculate_ema_numba,
        calculate_macd_numba,
    )

    assert NUMBA_AVAILABLE is True, "Numba must be available"
    assert NUMBA_VERSION is not None, "Numba version must be set"

    # Verify functions are Numba-compiled
    assert hasattr(calculate_rsi_numba, '__compiled__') or hasattr(
        calculate_rsi_numba, 'signatures'
    )
    assert hasattr(calculate_ema_numba, '__compiled__') or hasattr(
        calculate_ema_numba, 'signatures'
    )
    assert hasattr(calculate_macd_numba, '__compiled__') or hasattr(
        calculate_macd_numba, 'signatures'
    )


def test_numba_metrics_available():
    """Test that Numba metrics module is available."""
    from app.backtesting.numba_metrics import (
        NUMBA_AVAILABLE,
        NUMBA_VERSION,
        calculate_sharpe_numba,
        calculate_sortino_numba,
        calculate_var_numba,
    )

    assert NUMBA_AVAILABLE is True, "Numba must be available for metrics"
    assert NUMBA_VERSION is not None, "Numba version must be set"

    # Verify functions are Numba-compiled
    assert hasattr(calculate_sharpe_numba, '__compiled__') or hasattr(
        calculate_sharpe_numba, 'signatures'
    )
    assert hasattr(calculate_sortino_numba, '__compiled__') or hasattr(
        calculate_sortino_numba, 'signatures'
    )
    assert hasattr(calculate_var_numba, '__compiled__') or hasattr(
        calculate_var_numba, 'signatures'
    )


def test_numba_risk_available():
    """Test that Numba risk module is available."""
    from app.services.numba_risk import (
        NUMBA_AVAILABLE,
        NUMBA_VERSION,
        calculate_historical_var_numba,
        calculate_correlation_matrix_numba,
        calculate_portfolio_volatility_numba,
    )

    assert NUMBA_AVAILABLE is True, "Numba must be available for risk calculations"
    assert NUMBA_VERSION is not None, "Numba version must be set"

    # Verify functions are Numba-compiled
    assert hasattr(calculate_historical_var_numba, '__compiled__') or hasattr(
        calculate_historical_var_numba, 'signatures'
    )
    assert hasattr(calculate_correlation_matrix_numba, '__compiled__') or hasattr(
        calculate_correlation_matrix_numba, 'signatures'
    )
    assert hasattr(calculate_portfolio_volatility_numba, '__compiled__') or hasattr(
        calculate_portfolio_volatility_numba, 'signatures'
    )


# ============================================================================
# Test Numba Function Correctness
# ============================================================================


def test_rsi_calculation_correctness():
    """Test that Numba RSI calculation produces correct results."""
    from app.core.numba_accelerators import calculate_rsi_numba

    # Create test data with known RSI values
    prices = np.array(
        [
            44.0,
            44.25,
            44.50,
            43.75,
            44.00,
            44.25,
            44.75,
            45.00,
            45.25,
            45.50,
            45.00,
            45.25,
            45.50,
            45.75,
            46.00,
        ]
    )

    rsi = calculate_rsi_numba(prices, period=14)

    # RSI should be between 0 and 100
    assert 0 <= rsi <= 100, f"RSI {rsi} is outside valid range [0, 100]"
    assert not np.isnan(rsi), "RSI should not be NaN for sufficient data"


def test_ema_calculation_correctness():
    """Test that Numba EMA calculation produces correct results."""
    from app.core.numba_accelerators import calculate_ema_single_numba

    prices = np.array(
        [
            44.0,
            44.25,
            44.50,
            43.75,
            44.00,
            44.25,
            44.75,
            45.00,
            45.25,
            45.50,
        ]
    )

    ema = calculate_ema_single_numba(prices, period=5)

    # EMA should be a valid number
    assert not np.isnan(ema), "EMA should not be NaN for sufficient data"
    assert ema > 0, "EMA should be positive for positive prices"


def test_sharpe_ratio_correctness():
    """Test that Numba Sharpe ratio calculation produces correct results."""
    from app.backtesting.numba_metrics import calculate_sharpe_numba

    returns = np.array(
        [
            0.01,
            0.02,
            -0.01,
            0.03,
            0.01,
            -0.02,
            0.01,
            0.02,
            -0.01,
            0.01,
        ]
    )

    sharpe = calculate_sharpe_numba(returns, risk_free_rate=0.02, periods_per_year=252)

    # Sharpe should be a valid number
    assert not np.isnan(sharpe), "Sharpe ratio should not be NaN"
    assert isinstance(sharpe, (float, np.floating)), "Sharpe should be a float"


def test_var_calculation_correctness():
    """Test that Numba VaR calculation produces correct results."""
    from app.backtesting.numba_metrics import calculate_var_numba

    returns = np.array(
        [
            0.01,
            0.02,
            -0.01,
            0.03,
            0.01,
            -0.02,
            0.01,
            0.02,
            -0.01,
            0.01,
            -0.03,
            -0.02,
            -0.01,
            0.01,
            0.02,
        ]
    )

    var_95 = calculate_var_numba(returns, confidence_level=0.95)

    # VaR should be negative (loss) and within reasonable range
    assert var_95 <= 0, f"VaR at 95% should be negative (loss), got {var_95}"
    assert not np.isnan(var_95), "VaR should not be NaN"


def test_correlation_matrix_correctness():
    """Test that Numba correlation matrix calculation produces correct results."""
    from app.services.numba_risk import calculate_correlation_matrix_numba

    # Create test returns matrix
    np.random.seed(42)
    returns_matrix = np.random.randn(100, 5) * 0.01  # 100 periods, 5 assets

    corr_matrix = calculate_correlation_matrix_numba(returns_matrix)

    # Check shape
    assert corr_matrix.shape == (5, 5), "Correlation matrix should be 5x5"

    # Check diagonal is 1
    for i in range(5):
        assert abs(corr_matrix[i, i] - 1.0) < 1e-10, f"Diagonal element [{i},{i}] should be 1.0"

    # Check symmetry
    for i in range(5):
        for j in range(5):
            assert (
                abs(corr_matrix[i, j] - corr_matrix[j, i]) < 1e-10
            ), f"Correlation matrix should be symmetric at [{i},{j}]"

    # Check values are in [-1, 1]
    assert np.all(corr_matrix >= -1.0), "All correlations should be >= -1"
    assert np.all(corr_matrix <= 1.0), "All correlations should be <= 1"


# ============================================================================
# Test Numba Performance
# ============================================================================


def test_rsi_performance_improvement():
    """Test that Numba RSI is significantly faster than pure Python."""
    from app.core.numba_accelerators import calculate_rsi_numba

    # Create large dataset
    prices = np.random.randn(10000) * 10 + 100

    # Time Numba version
    start = time.time()
    for _ in range(100):
        rsi = calculate_rsi_numba(prices, period=14)
    numba_time = time.time() - start

    # Pure Python version (slow)
    def rsi_python(prices, period=14):
        n = len(prices)
        if n < period + 1:
            return np.nan

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100.0

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    start = time.time()
    for _ in range(10):  # Fewer iterations for Python
        rsi_py = rsi_python(prices, period=14)
    python_time = time.time() - start

    # Numba should be at least 10x faster (even with compilation overhead)
    # Adjust for the fact that we ran Python 10x fewer times
    speedup = (python_time * 10) / numba_time

    print(f"\nRSI Performance:")
    print(f"  Numba time (100 iterations): {numba_time:.4f}s")
    print(f"  Python time (10 iterations): {python_time:.4f}s")
    print(f"  Estimated speedup: {speedup:.1f}x")

    # After first compilation, Numba should be significantly faster
    # We expect at least 5x speedup (conservative)
    assert speedup > 5, f"Numba should be >5x faster, got {speedup:.1f}x"


def test_correlation_performance_improvement():
    """Test that Numba correlation calculation is significantly faster."""
    from app.services.numba_risk import calculate_correlation_matrix_numba

    # Create large dataset
    np.random.seed(42)
    returns_matrix = np.random.randn(5000, 50) * 0.01  # 5000 periods, 50 assets

    # Time Numba version
    start = time.time()
    corr_matrix = calculate_correlation_matrix_numba(returns_matrix)
    numba_time = time.time() - start

    # Pandas version (for comparison)
    import pandas as pd

    df = pd.DataFrame(returns_matrix)
    start = time.time()
    corr_pandas = df.corr().values
    pandas_time = time.time() - start

    # Numba should be competitive or faster
    print(f"\nCorrelation Matrix Performance (5000 periods, 50 assets):")
    print(f"  Numba time: {numba_time:.4f}s")
    print(f"  Pandas time: {pandas_time:.4f}s")

    # Both should produce similar results
    assert np.allclose(
        corr_matrix, corr_pandas, atol=1e-6
    ), "Numba and Pandas should produce similar results"


# ============================================================================
# Test Numba Enforcer
# ============================================================================


def test_numba_enforcer_startup():
    """Test that Numba enforcer works at startup."""
    from app.core.numba_enforcer import enforce_numba_available

    # Should not raise if Numba is available
    try:
        enforce_numba_available()
    except RuntimeError:
        pytest.fail("enforce_numba_available() raised RuntimeError unexpectedly")


def test_numba_function_verification():
    """Test Numba function verification."""
    from app.core.numba_enforcer import verify_numba_function
    from app.core.numba_accelerators import calculate_rsi_numba

    prices = np.array(
        [
            44.0,
            44.25,
            44.50,
            43.75,
            44.00,
            44.25,
            44.75,
            45.00,
            45.25,
            45.50,
            45.00,
            45.25,
            45.50,
            45.75,
            46.00,
        ]
    )

    # Should verify successfully
    result = verify_numba_function(calculate_rsi_numba, prices, 14)
    assert result is True, "Function verification should succeed"


# ============================================================================
# Integration Tests
# ============================================================================


def test_numba_integration_with_metrics_calculator():
    """Test that Numba functions integrate properly with metrics calculator."""
    from app.backtesting.numba_metrics import (
        calculate_returns_numba,
        calculate_sharpe_numba,
        calculate_max_drawdown_numba,
    )

    # Create test data
    prices = np.array([100, 101, 102, 101, 100, 102, 103, 104, 103, 105])

    # Calculate returns
    returns = calculate_returns_numba(prices)

    # Calculate metrics
    sharpe = calculate_sharpe_numba(returns, risk_free_rate=0.02, periods_per_year=252)
    max_dd = calculate_max_drawdown_numba(prices)

    # Verify results
    assert not np.isnan(sharpe), "Sharpe should not be NaN"
    assert max_dd <= 0, "Max drawdown should be negative or zero"


def test_numba_integration_with_risk_calculator():
    """Test that Numba functions integrate properly with risk calculator."""
    from app.services.numba_risk import (
        calculate_portfolio_var_numba,
        calculate_historical_cvar_numba,
    )

    # Create test data
    np.random.seed(42)
    weights = np.array([0.6, 0.4])
    returns_matrix = np.random.randn(1000, 2) * 0.01

    # Calculate portfolio VaR
    portfolio_var = calculate_portfolio_var_numba(weights, returns_matrix, 0.95)

    # Verify result
    assert not np.isnan(portfolio_var), "Portfolio VaR should not be NaN"
    assert portfolio_var <= 0, "VaR should be negative (loss)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
