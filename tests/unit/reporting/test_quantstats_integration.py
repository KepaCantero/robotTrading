"""
Tests for QuantStatsIntegration (T9.1.2)

Tests advanced metrics calculation from returns series.
"""

import numpy as np
import pandas as pd
import pytest

from app.services.reporting.quantstats_integration import (
    QUANTSTATS_AVAILABLE,
    QuantStatsIntegration,
    get_quantstats_integration,
)


class TestQuantStatsIntegration:
    """Test suite for QuantStatsIntegration."""

    @pytest.fixture
    def integration(self):
        """Create integration instance."""
        return QuantStatsIntegration()

    @pytest.fixture
    def good_returns(self):
        """Create good performance returns."""
        np.random.seed(42)
        return pd.Series(
            np.random.normal(0.001, 0.01, 252),  # Daily positive returns
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

    @pytest.fixture
    def poor_returns(self):
        """Create poor performance returns."""
        np.random.seed(42)
        return pd.Series(
            np.random.normal(-0.0005, 0.015, 252),  # Daily negative returns
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

    @pytest.fixture
    def benchmark_returns(self):
        """Create benchmark returns."""
        np.random.seed(43)
        return pd.Series(
            np.random.normal(0.0003, 0.009, 252),
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

    # =========================================================================
    # TEST: Metrics Calculation
    # =========================================================================

    def test_calculates_total_return(self, integration, good_returns):
        """Test total return calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "total_return" in metrics
        assert isinstance(metrics["total_return"], float)
        assert metrics["total_return"] > 0, "Good returns should have positive total return"

    def test_calculates_volatility(self, integration, good_returns):
        """Test volatility calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "volatility" in metrics
        assert metrics["volatility"] > 0, "Volatility should be positive"

    def test_calculates_sharpe_ratio(self, integration, good_returns):
        """Test Sharpe ratio calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "sharpe_ratio" in metrics
        assert isinstance(metrics["sharpe_ratio"], float)

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_calculates_sortino_ratio(self, integration, good_returns):
        """Test Sortino ratio calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "sortino_ratio" in metrics

    def test_calculates_max_drawdown(self, integration, good_returns):
        """Test maximum drawdown calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "max_drawdown" in metrics
        assert metrics["max_drawdown"] <= 0, "Drawdown should be non-positive"

    def test_calculates_win_rate(self, integration, good_returns):
        """Test win rate calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "win_rate" in metrics
        assert 0 <= metrics["win_rate"] <= 1, "Win rate should be 0-1"

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_calculates_profit_factor(self, integration, good_returns):
        """Test profit factor calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "profit_factor" in metrics
        assert metrics["profit_factor"] >= 0

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_calculates_recovery_factor(self, integration, good_returns):
        """Test recovery factor calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "recovery_factor" in metrics
        assert metrics["recovery_factor"] >= 0

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_calculates_consecutive_wins(self, integration, good_returns):
        """Test consecutive wins calculation."""
        metrics = integration.calculate_advanced_metrics(good_returns)

        assert "max_consecutive_wins" in metrics
        assert metrics["max_consecutive_wins"] > 0

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_calculates_consecutive_losses(self, integration, poor_returns):
        """Test consecutive losses calculation."""
        metrics = integration.calculate_advanced_metrics(poor_returns)

        assert "max_consecutive_losses" in metrics

    def test_good_returns_better_than_poor(self, integration, good_returns, poor_returns):
        """Test good returns produce better metrics than poor returns."""
        good_metrics = integration.calculate_advanced_metrics(good_returns)
        poor_metrics = integration.calculate_advanced_metrics(poor_returns)

        # Good returns should have higher Sharpe
        assert good_metrics.get("sharpe_ratio", 0) >= poor_metrics.get("sharpe_ratio", 0)
        # Good returns should have higher total return
        assert good_metrics.get("total_return", 0) >= poor_metrics.get("total_return", 0)

    # =========================================================================
    # TEST: Benchmark Comparison
    # =========================================================================

    @pytest.mark.skipif(not QUANTSTATS_AVAILABLE, reason="QuantStats not installed")
    def test_information_ratio_with_benchmark(self, integration, good_returns, benchmark_returns):
        """Test information ratio calculation with benchmark."""
        metrics = integration.calculate_advanced_metrics(good_returns, benchmark_returns)

        assert "information_ratio" in metrics

    def test_handles_mismatched_benchmark_length(self, integration, good_returns):
        """Test handling of mismatched benchmark length."""
        bad_benchmark = pd.Series([0.001, 0.002])  # Only 2 periods vs 252

        metrics = integration.calculate_advanced_metrics(good_returns, bad_benchmark)

        # Should handle gracefully without information_ratio
        assert "information_ratio" not in metrics
        assert "sharpe_ratio" in metrics

    # =========================================================================
    # TEST: Edge Cases
    # =========================================================================

    def test_empty_returns(self, integration):
        """Test empty returns series."""
        empty = pd.Series([])

        metrics = integration.calculate_advanced_metrics(empty)

        assert isinstance(metrics, dict)
        # Should return empty or minimal metrics

    def test_single_return(self, integration):
        """Test single return value."""
        single = pd.Series([0.01])

        metrics = integration.calculate_advanced_metrics(single)

        assert isinstance(metrics, dict)

    def test_zero_returns(self, integration):
        """Test all zero returns."""
        zeros = pd.Series([0.0] * 252)

        metrics = integration.calculate_advanced_metrics(zeros)

        assert "total_return" in metrics
        assert metrics["total_return"] == 0.0
        # Volatility should be 0 (allow for floating-point precision)
        assert abs(metrics.get("volatility", 0)) < 1e-10

    def test_constant_returns(self, integration):
        """Test constant returns."""
        constants = pd.Series([0.001] * 252)

        metrics = integration.calculate_advanced_metrics(constants)

        assert "total_return" in metrics
        assert metrics["total_return"] > 0
        # Volatility should be ~0 (allow for floating-point precision)
        assert abs(metrics.get("volatility", 0)) < 1e-10

    # =========================================================================
    # TEST: Fallback Metrics
    # =========================================================================

    def test_fallback_metrics_available(self, integration, good_returns):
        """Test fallback metrics are available."""
        metrics = integration._fallback_metrics(good_returns)

        assert "total_return" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics

    def test_fallback_handles_short_series(self, integration):
        """Test fallback with very short series."""
        short = pd.Series([0.01])

        metrics = integration._fallback_metrics(short)

        # Should return empty dict for too-short series
        assert isinstance(metrics, dict)

    # =========================================================================
    # TEST: Metrics Summary
    # =========================================================================

    def test_metrics_summary(self, integration, good_returns):
        """Test metrics summary generation."""
        summary = integration.get_metrics_summary(good_returns)

        assert "metrics" in summary
        assert "source" in summary
        assert "count" in summary
        assert "is_available" in summary
        assert summary["count"] > 0

    def test_metrics_summary_with_benchmark(self, integration, good_returns, benchmark_returns):
        """Test metrics summary with benchmark."""
        summary = integration.get_metrics_summary(good_returns, benchmark_returns)

        assert "metrics" in summary
        assert len(summary["metrics"]) > 0

    # =========================================================================
    # TEST: Data Type Handling
    # =========================================================================

    def test_accepts_list_input(self, integration):
        """Test accepts list input and converts to Series."""
        returns_list = [0.01, 0.02, -0.01, 0.015] * 63  # 252 periods

        metrics = integration.calculate_advanced_metrics(returns_list)

        assert isinstance(metrics, dict)
        assert len(metrics) > 0

    def test_singleton_pattern(self):
        """Test get_quantstats_integration returns singleton."""
        int1 = get_quantstats_integration()
        int2 = get_quantstats_integration()

        assert int1 is int2, "Should return same instance"
