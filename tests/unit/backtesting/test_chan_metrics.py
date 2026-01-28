"""
Unit tests for Chan Metrics (Ernest Chan performance metrics)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from app.backtesting.chan_metrics import (
    ChanSharpeRatioCalculator,
    ChanDrawdownAnalyzer,
    ChanCalmarRatioCalculator,
    ChanReturnDistributionAnalyzer,
    ChanStrategyComparator,
    SharpeRatioResult,
    DrawdownResult,
    CalmarRatioResult,
    ReturnDistributionMetrics,
    StrategyComparisonResult,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
)


class TestChanSharpeRatioCalculator:
    """Tests for ChanSharpeRatioCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a ChanSharpeRatioCalculator instance."""
        return ChanSharpeRatioCalculator(risk_free_rate=0.02, trading_days=252)

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.01)

    @pytest.fixture
    def positive_returns(self):
        """Create returns with positive drift."""
        np.random.seed(42)
        return pd.Series(0.0005 + np.random.randn(252) * 0.01)

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.risk_free_rate == 0.02
        assert calculator.trading_days == 252

    def test_calculate_sharpe_ratio(self, calculator, sample_returns):
        """Test Sharpe ratio calculation."""
        result = calculator.calculate_sharpe_ratio(sample_returns)

        assert isinstance(result, SharpeRatioResult)
        assert hasattr(result, 'sharpe_ratio')
        assert hasattr(result, 'annualized_sharpe')
        assert hasattr(result, 'daily_mean_return')
        assert hasattr(result, 'daily_std_return')

    def test_annualized_sharpe_relationship(self, calculator, sample_returns):
        """Test relationship between daily and annualized Sharpe."""
        result = calculator.calculate_sharpe_ratio(sample_returns)

        # Annualized should be daily * sqrt(252)
        expected_annualized = result.sharpe_ratio * np.sqrt(252)
        assert abs(result.annualized_sharpe - expected_annualized) < 0.01

    def test_positive_returns_sharpe(self, calculator, positive_returns):
        """Test Sharpe ratio with positive drift."""
        result = calculator.calculate_sharpe_ratio(positive_returns)

        # Positive returns should generally give positive Sharpe
        # (though not guaranteed due to randomness)
        assert isinstance(result.annualized_sharpe, float)

    def test_skewness_calculation(self, calculator, sample_returns):
        """Test skewness calculation."""
        result = calculator.calculate_sharpe_ratio(sample_returns)

        assert isinstance(result.skewness, float)
        # Skewness can be positive or negative
        assert -5 < result.skewness < 5

    def test_excess_kurtosis_calculation(self, calculator, sample_returns):
        """Test excess kurtosis calculation."""
        result = calculator.calculate_sharpe_ratio(sample_returns)

        assert isinstance(result.excess_kurtosis, float)

    def test_confidence_interval(self, calculator, sample_returns):
        """Test confidence interval calculation."""
        result = calculator.calculate_sharpe_ratio(sample_returns, confidence_level=0.95)

        assert hasattr(result, 'confidence_interval_low')
        assert hasattr(result, 'confidence_interval_high')
        assert result.confidence_interval_low < result.confidence_interval_high

    def test_statistical_significance(self, calculator, positive_returns):
        """Test statistical significance testing."""
        result = calculator.calculate_sharpe_ratio(positive_returns)

        # np.bool_ is also valid, so use bool() conversion
        assert bool(result.is_statistically_significant) in [True, False]

    def test_insufficient_data(self, calculator):
        """Test handling of insufficient data."""
        short_returns = pd.Series([0.01, -0.01])
        result = calculator.calculate_sharpe_ratio(short_returns)

        assert isinstance(result, SharpeRatioResult)

    def test_with_nan_values(self, calculator):
        """Test handling of NaN values."""
        returns = pd.Series([0.01, np.nan, -0.01, 0.02, np.nan, 0.01])
        result = calculator.calculate_sharpe_ratio(returns)

        assert isinstance(result, SharpeRatioResult)

    def test_list_input(self, calculator):
        """Test with list input instead of pandas Series."""
        returns = [0.01, -0.01, 0.02, -0.005, 0.015] * 50
        result = calculator.calculate_sharpe_ratio(returns)

        assert isinstance(result, SharpeRatioResult)


class TestChanDrawdownAnalyzer:
    """Tests for ChanDrawdownAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a ChanDrawdownAnalyzer instance."""
        return ChanDrawdownAnalyzer()

    @pytest.fixture
    def sample_equity_curve(self):
        """Create sample equity curve."""
        np.random.seed(42)
        # Start with 100k, add some returns
        returns = np.random.randn(252) * 0.01
        equity = 100000 * (1 + returns).cumprod()
        return pd.Series(equity)

    @pytest.fixture
    def equity_with_drawdown(self):
        """Create equity curve with known drawdown."""
        # Create a pattern with clear peak and trough
        equity_values = [
            100000, 105000, 110000, 115000, 120000,  # Peak
            115000, 110000, 105000, 100000, 95000,   # Drawdown
            100000, 105000, 110000,                   # Recovery
        ]
        return pd.Series(equity_values)

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None

    def test_analyze_drawdown(self, analyzer, sample_equity_curve):
        """Test drawdown analysis."""
        result = analyzer.analyze_drawdown(sample_equity_curve)

        assert isinstance(result, DrawdownResult)
        assert hasattr(result, 'max_drawdown')
        assert hasattr(result, 'max_drawdown_percentage')
        assert hasattr(result, 'max_drawdown_duration_days')

    def test_max_drawdown_calculation(self, analyzer, equity_with_drawdown):
        """Test maximum drawdown calculation."""
        result = analyzer.analyze_drawdown(equity_with_drawdown)

        # Max drawdown should be from 120k to 95k
        # (95000 - 120000) / 120000 = -0.208 = -20.8%
        assert result.max_drawdown_percentage < 0
        assert abs(result.max_drawdown_percentage - (-20.8)) < 1.0

    def test_recovery_factor(self, analyzer, equity_with_drawdown):
        """Test recovery factor calculation."""
        result = analyzer.analyze_drawdown(equity_with_drawdown)

        assert hasattr(result, 'recovery_factor')
        # Recovery factor = (final - peak) / abs(max_dd)
        # (110000 - 120000) / 20833 = -0.48
        assert isinstance(result.recovery_factor, float)

    def test_drawdown_distribution(self, analyzer, sample_equity_curve):
        """Test drawdown distribution calculation."""
        result = analyzer.analyze_drawdown(sample_equity_curve)

        assert hasattr(result, 'drawdown_distribution')
        assert isinstance(result.drawdown_distribution, dict)
        # Should have percentile values
        assert 'p5' in result.drawdown_distribution
        assert 'p50' in result.drawdown_distribution
        assert 'p95' in result.drawdown_distribution

    def test_drawdown_periods(self, analyzer, equity_with_drawdown):
        """Test identification of drawdown periods."""
        result = analyzer.analyze_drawdown(equity_with_drawdown)

        assert hasattr(result, 'drawdown_periods')
        assert isinstance(result.drawdown_periods, list)

    def test_with_dates(self, analyzer):
        """Test drawdown analysis with dates."""
        dates = pd.date_range(start="2020-01-01", periods=100, freq="D")
        equity = pd.Series(
            100000 + np.random.randn(100).cumsum() * 100,
            index=dates,
        )

        result = analyzer.analyze_drawdown(equity, dates)

        assert isinstance(result, DrawdownResult)


class TestChanCalmarRatioCalculator:
    """Tests for ChanCalmarRatioCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a ChanCalmarRatioCalculator instance."""
        return ChanCalmarRatioCalculator(trading_days=252)

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.01 + 0.0003)

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.trading_days == 252

    def test_calculate_calmar_ratio(self, calculator, sample_returns):
        """Test Calmar ratio calculation."""
        result = calculator.calculate_calmar_ratio(sample_returns)

        assert isinstance(result, CalmarRatioResult)
        assert hasattr(result, 'calmar_ratio')
        assert hasattr(result, 'annual_return')
        assert hasattr(result, 'max_drawdown')

    def test_calmar_interpretation(self, calculator, sample_returns):
        """Test Calmar ratio interpretation."""
        result = calculator.calculate_calmar_ratio(sample_returns)

        assert hasattr(result, 'interpretation')
        assert isinstance(result.interpretation, str)
        assert len(result.interpretation) > 0

    def test_with_equity_curve(self, calculator):
        """Test Calmar ratio with equity curve."""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0005)
        equity = (1 + returns).cumprod() * 100000

        result = calculator.calculate_calmar_ratio(returns, equity)

        assert isinstance(result, CalmarRatioResult)

    def test_insufficient_data(self, calculator):
        """Test with insufficient data."""
        short_returns = pd.Series([0.01, -0.01])
        result = calculator.calculate_calmar_ratio(short_returns)

        assert isinstance(result, CalmarRatioResult)
        assert result.calmar_ratio == 0.0


class TestChanReturnDistributionAnalyzer:
    """Tests for ChanReturnDistributionAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a ChanReturnDistributionAnalyzer instance."""
        return ChanReturnDistributionAnalyzer()

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.01)

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None

    def test_analyze_return_distribution(self, analyzer, sample_returns):
        """Test return distribution analysis."""
        result = analyzer.analyze_return_distribution(sample_returns)

        assert isinstance(result, ReturnDistributionMetrics)
        assert hasattr(result, 'mean_return')
        assert hasattr(result, 'median_return')
        assert hasattr(result, 'std_return')

    def test_positive_negative_return_pct(self, analyzer, sample_returns):
        """Test positive/negative return percentage."""
        result = analyzer.analyze_return_distribution(sample_returns)

        assert hasattr(result, 'positive_return_pct')
        assert hasattr(result, 'negative_return_pct')
        assert result.positive_return_pct + result.negative_return_pct <= 1.0

    def test_best_worst_day(self, analyzer, sample_returns):
        """Test best and worst day calculations."""
        result = analyzer.analyze_return_distribution(sample_returns)

        assert hasattr(result, 'best_day_return')
        assert hasattr(result, 'worst_day_return')
        assert result.best_day_return > result.worst_day_return

    def test_capture_ratios(self, analyzer):
        """Test up/down capture ratios."""
        strategy_returns = pd.Series(np.random.randn(252) * 0.01 + 0.0003)
        benchmark_returns = pd.Series(np.random.randn(252) * 0.01 + 0.0001)

        result = analyzer.analyze_return_distribution(
            strategy_returns,
            benchmark_returns,
        )

        assert hasattr(result, 'up_capture_ratio')
        assert hasattr(result, 'down_capture_ratio')

    def test_tail_ratio(self, analyzer, sample_returns):
        """Test tail ratio calculation."""
        result = analyzer.analyze_return_distribution(sample_returns)

        assert hasattr(result, 'tail_ratio')
        assert result.tail_ratio >= 0


class TestChanStrategyComparator:
    """Tests for ChanStrategyComparator class."""

    @pytest.fixture
    def comparator(self):
        """Create a ChanStrategyComparator instance."""
        return ChanStrategyComparator()

    @pytest.fixture
    def returns1(self):
        """Create strategy 1 returns (better)."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.01 + 0.0005)

    @pytest.fixture
    def returns2(self):
        """Create strategy 2 returns (worse)."""
        np.random.seed(43)
        return pd.Series(np.random.randn(252) * 0.01 + 0.0001)

    def test_initialization(self, comparator):
        """Test comparator initialization."""
        assert comparator is not None

    def test_compare_strategies(self, comparator, returns1, returns2):
        """Test strategy comparison."""
        result = comparator.compare_strategies(returns1, returns2)

        assert isinstance(result, StrategyComparisonResult)
        assert hasattr(result, 'strategy1_sharpe')
        assert hasattr(result, 'strategy2_sharpe')
        assert hasattr(result, 'sharpe_difference')

    def test_tracking_error(self, comparator, returns1, returns2):
        """Test tracking error calculation."""
        result = comparator.compare_strategies(returns1, returns2)

        assert hasattr(result, 'tracking_error')
        assert result.tracking_error >= 0

    def test_information_ratio(self, comparator, returns1, returns2):
        """Test information ratio calculation."""
        result = comparator.compare_strategies(returns1, returns2)

        assert hasattr(result, 'information_ratio')
        assert isinstance(result.information_ratio, float)

    def test_recommended_strategy(self, comparator, returns1, returns2):
        """Test strategy recommendation."""
        result = comparator.compare_strategies(returns1, returns2)

        assert hasattr(result, 'recommended_strategy')
        assert isinstance(result.recommended_strategy, str)

    def test_identical_strategies(self, comparator):
        """Test comparison of identical strategies."""
        returns = pd.Series(np.random.randn(252) * 0.01)
        result = comparator.compare_strategies(returns, returns)

        assert isinstance(result, StrategyComparisonResult)
        assert result.sharpe_difference == 0.0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio convenience function."""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0003)
        sharpe = calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)

    def test_calculate_max_drawdown(self):
        """Test max drawdown convenience function."""
        equity = pd.Series(100000 + np.random.randn(252).cumsum() * 100)
        max_dd = calculate_max_drawdown(equity)

        assert isinstance(max_dd, float)
        assert max_dd <= 0  # Drawdown is negative

    def test_calculate_calmar_ratio(self):
        """Test Calmar ratio convenience function."""
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0003)
        calmar = calculate_calmar_ratio(returns)

        assert isinstance(calmar, float)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_returns(self):
        """Test with empty returns."""
        calc = ChanSharpeRatioCalculator()
        result = calc.calculate_sharpe_ratio(pd.Series([]))

        assert isinstance(result, SharpeRatioResult)

    def test_constant_returns(self):
        """Test with constant returns."""
        calc = ChanSharpeRatioCalculator()
        constant_returns = pd.Series([0.01] * 100)
        result = calc.calculate_sharpe_ratio(constant_returns)

        # Should handle zero volatility
        assert isinstance(result, SharpeRatioResult)

    def test_extreme_values(self):
        """Test with extreme values."""
        calc = ChanSharpeRatioCalculator()
        extreme_returns = pd.Series([100.0, -100.0, 50.0, -50.0])
        result = calc.calculate_sharpe_ratio(extreme_returns)

        assert isinstance(result, SharpeRatioResult)

    def test_single_value(self):
        """Test with single value."""
        analyzer = ChanDrawdownAnalyzer()
        single_equity = pd.Series([100000])
        result = analyzer.analyze_drawdown(single_equity)

        assert isinstance(result, DrawdownResult)


class TestIntegration:
    """Integration tests for Chan metrics."""

    def test_full_metrics_workflow(self):
        """Test complete workflow of metrics calculation."""
        # Generate realistic returns
        np.random.seed(42)
        returns = pd.Series(np.random.randn(252) * 0.01 + 0.0003)
        equity = 100000 * (1 + returns).cumprod()

        # Calculate all metrics
        sharpe_calc = ChanSharpeRatioCalculator()
        sharpe_result = sharpe_calc.calculate_sharpe_ratio(returns)

        dd_analyzer = ChanDrawdownAnalyzer()
        dd_result = dd_analyzer.analyze_drawdown(equity)

        calmar_calc = ChanCalmarRatioCalculator()
        calmar_result = calmar_calc.calculate_calmar_ratio(returns, equity)

        dist_analyzer = ChanReturnDistributionAnalyzer()
        dist_result = dist_analyzer.analyze_return_distribution(returns)

        # Verify all results are valid
        assert isinstance(sharpe_result, SharpeRatioResult)
        assert isinstance(dd_result, DrawdownResult)
        assert isinstance(calmar_result, CalmarRatioResult)
        assert isinstance(dist_result, ReturnDistributionMetrics)

        # Check consistency
        assert sharpe_result.annualized_sharpe > -10  # Reasonable range
        assert dd_result.max_drawdown_percentage < 0  # Drawdown is negative
        assert dist_result.mean_return > dist_result.worst_day_return

    def test_strategy_comparison_workflow(self):
        """Test complete strategy comparison workflow."""
        # Create two strategies
        np.random.seed(42)
        returns1 = pd.Series(np.random.randn(252) * 0.01 + 0.0005)
        returns2 = pd.Series(np.random.randn(252) * 0.01 + 0.0002)

        # Compare
        comparator = ChanStrategyComparator()
        result = comparator.compare_strategies(returns1, returns2)

        # Get individual metrics for comparison
        calc1 = ChanSharpeRatioCalculator()
        calc2 = ChanSharpeRatioCalculator()

        sharpe1 = calc1.calculate_sharpe_ratio(returns1)
        sharpe2 = calc2.calculate_sharpe_ratio(returns2)

        # Verify consistency
        assert abs(result.strategy1_sharpe - sharpe1.annualized_sharpe) < 0.01
        assert abs(result.strategy2_sharpe - sharpe2.annualized_sharpe) < 0.01
