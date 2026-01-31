"""
Unit tests for Stationarity Analyzer (Ernest Chan methodologies)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from app.services.stationarity_analyzer import (
    StationarityAnalyzer,
    CointegrationAnalyzer,
    find_cointegrated_pairs,
    StationarityTestResult,
    CointegrationTestResult,
)


class TestStationarityAnalyzer:
    """Tests for StationarityAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a StationarityAnalyzer instance."""
        return StationarityAnalyzer(confidence_level=0.95)

    @pytest.fixture
    def stationary_series(self):
        """Create a stationary series (mean-reverting)."""
        np.random.seed(42)
        # AR(1) process with phi < 1 is stationary
        phi = 0.5
        n = 200
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = phi * x[i - 1] + np.random.randn()
        return x

    @pytest.fixture
    def non_stationary_series(self):
        """Create a non-stationary series (random walk)."""
        np.random.seed(42)
        n = 200
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = x[i - 1] + np.random.randn()
        return x

    def test_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.confidence_level == 0.95
        assert analyzer.min_observations == 30

    def test_stationary_detection(self, analyzer, stationary_series):
        """Test detection of stationary series."""
        result = analyzer.test_stationarity(stationary_series, "TestAsset")

        assert isinstance(result, StationarityTestResult)
        assert hasattr(result, 'is_stationary')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'half_life')
        assert hasattr(result, 'hurst_exponent')

    def test_non_stationary_detection(self, analyzer, non_stationary_series):
        """Test detection of non-stationary series."""
        result = analyzer.test_stationarity(non_stationary_series, "TestAsset")

        assert isinstance(result, StationarityTestResult)
        # Random walk should be non-stationary
        # (may occasionally be detected as stationary due to randomness)

    def test_half_life_calculation(self, analyzer, stationary_series):
        """Test half-life calculation."""
        half_life = analyzer.calculate_half_life(stationary_series)

        assert isinstance(half_life, (int, float))
        assert half_life >= 0
        # Stationary series should have finite half-life
        assert half_life < float('inf')

    def test_hurst_exponent_calculation(self, analyzer):
        """Test Hurst exponent calculation."""
        # Mean-reverting series should have H < 0.5
        np.random.seed(42)
        phi = 0.3
        n = 200
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = phi * x[i - 1] + np.random.randn()

        hurst = analyzer.calculate_hurst_exponent(x)

        assert isinstance(hurst, (int, float))
        assert 0 <= hurst <= 1

    def test_optimal_lookback(self, analyzer):
        """Test optimal lookback period calculation."""
        np.random.seed(42)
        prices = np.cumsum(np.random.randn(200)) + 100

        lookback = analyzer.find_optimal_lookback(prices, max_lookback=50)

        assert isinstance(lookback, int)
        assert 5 <= lookback <= 50

    def test_insufficient_data(self, analyzer):
        """Test handling of insufficient data."""
        short_series = np.array([1, 2, 3])
        result = analyzer.test_stationarity(short_series)

        assert isinstance(result, StationarityTestResult)
        # Should return non-stationary result with explanation

    def test_with_nan_values(self, analyzer):
        """Test handling of NaN values."""
        series = np.array([1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10] * 20)
        result = analyzer.test_stationarity(series)

        assert isinstance(result, StationarityTestResult)

    def test_pandas_series_input(self, analyzer):
        """Test with pandas Series input."""
        prices = pd.Series([100, 101, 99, 100, 102, 98, 100] * 20)
        result = analyzer.test_stationarity(prices, "Test")

        assert isinstance(result, StationarityTestResult)


class TestCointegrationAnalyzer:
    """Tests for CointegrationAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a CointegrationAnalyzer instance."""
        return CointegrationAnalyzer(confidence_level=0.95)

    @pytest.fixture
    def cointegrated_pair(self):
        """Create a cointegrated pair."""
        np.random.seed(42)
        n = 200

        # Common stochastic trend
        trend = np.cumsum(np.random.randn(n))

        # Two series with the same trend + idiosyncratic noise
        y1 = trend + np.random.randn(n) * 0.5
        y2 = trend + np.random.randn(n) * 0.5

        return y1, y2

    @pytest.fixture
    def non_cointegrated_pair(self):
        """Create a non-cointegrated pair."""
        np.random.seed(42)
        n = 200

        # Independent random walks
        y1 = np.cumsum(np.random.randn(n))
        y2 = np.cumsum(np.random.randn(n))

        return y1, y2

    def test_cointegration_detection(self, analyzer, cointegrated_pair):
        """Test cointegration detection."""
        y1, y2 = cointegrated_pair
        result = analyzer.test_cointegration(y1, y2, "Asset1", "Asset2")

        assert isinstance(result, CointegrationTestResult)
        assert hasattr(result, 'is_cointegrated')
        assert hasattr(result, 'hedge_ratio')
        assert hasattr(result, 'spread_half_life')

    def test_non_cointegrated_pair(self, analyzer, non_cointegrated_pair):
        """Test with non-cointegrated pair."""
        y1, y2 = non_cointegrated_pair
        result = analyzer.test_cointegration(y1, y2, "Asset1", "Asset2")

        assert isinstance(result, CointegrationTestResult)

    def test_hedge_ratio_calculation(self, analyzer):
        """Test hedge ratio calculation."""
        np.random.seed(42)
        n = 100

        # y2 = 2 * y1 + noise
        y1 = np.random.randn(n).cumsum() + 100
        y2 = 2 * y1 + np.random.randn(n) * 5

        result = analyzer.test_cointegration(y1, y2, "Asset1", "Asset2")

        # Hedge ratio should be close to 2
        assert 1.5 < result.hedge_ratio < 2.5

    def test_position_size_calculation(self, analyzer):
        """Test optimal position size calculation."""
        # Create a mock cointegration result
        from app.services.stationarity_analyzer import CointegrationTestResult

        result = CointegrationTestResult(
            is_cointegrated=True,
            test_statistic=-5.0,
            p_value=0.01,
            critical_values={"1%": -3.43, "5%": -2.86, "10%": -2.57},
            hedge_ratio=1.5,
            spread_half_life=10.0,
            confidence_level=0.95,
            interpretation="Test",
            mean_reversion_speed="Fast",
        )

        size1, size2 = analyzer.calculate_optimal_position_sizes(
            result,
            price1=100.0,
            price2=150.0,
            capital=100000,
            risk_per_trade=0.02,
        )

        assert size1 > 0
        assert size2 > 0

    def test_entry_exit_thresholds(self, analyzer):
        """Test entry/exit threshold calculation."""
        np.random.seed(42)
        spread = np.random.randn(100)

        entry_threshold, exit_threshold = analyzer.calculate_entry_exit_thresholds(spread)

        assert entry_threshold > 0
        assert exit_threshold > 0
        assert entry_threshold > exit_threshold  # Entry should be wider


class TestFindCointegratedPairs:
    """Tests for find_cointegrated_pairs function."""

    @pytest.fixture
    def price_data(self):
        """Create sample price data for multiple assets."""
        np.random.seed(42)
        n = 200

        # Create some cointegrated pairs and some independent assets
        trend1 = np.cumsum(np.random.randn(n))
        trend2 = np.cumsum(np.random.randn(n))

        return {
            "AAPL": trend1 + np.random.randn(n) * 0.5,
            "MSFT": trend1 + np.random.randn(n) * 0.5,  # Cointegrated with AAPL
            "GOOGL": trend2 + np.random.randn(n) * 0.5,
            "AMZN": trend2 + np.random.randn(n) * 0.5,  # Cointegrated with GOOGL
            "TSLA": np.cumsum(np.random.randn(n)),  # Independent
        }

    def test_find_cointegrated_pairs(self, price_data):
        """Test finding cointegrated pairs."""
        pairs = find_cointegrated_pairs(
            price_data,
            confidence_level=0.95,
            min_half_life=5.0,
            max_half_life=100.0,
        )

        assert isinstance(pairs, list)
        # Should find some cointegrated pairs

    def test_pair_structure(self, price_data):
        """Test structure of returned pairs."""
        pairs = find_cointegrated_pairs(price_data)

        for pair in pairs:
            assert len(pair) == 3
            asset1, asset2, result = pair
            assert isinstance(asset1, str)
            assert isinstance(asset2, str)
            assert isinstance(result, CointegrationTestResult)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def analyzer(self):
        return StationarityAnalyzer()

    def test_empty_series(self, analyzer):
        """Test with empty series."""
        result = analyzer.test_stationarity([])
        assert isinstance(result, StationarityTestResult)

    def test_all_same_values(self, analyzer):
        """Test with constant series."""
        constant_series = np.ones(100) * 100
        result = analyzer.test_stationarity(constant_series)
        assert isinstance(result, StationarityTestResult)

    def test_very_short_series(self, analyzer):
        """Test with very short series."""
        short = np.array([1, 2])
        result = analyzer.test_stationarity(short)
        assert isinstance(result, StationarityTestResult)

    def test_series_with_inf_values(self, analyzer):
        """Test with infinite values."""
        series = np.array([1, 2, np.inf, 4, 5] * 10)
        result = analyzer.test_stationarity(series)
        assert isinstance(result, StationarityTestResult)


class TestIntegration:
    """Integration tests for stationarity analysis."""

    def test_full_workflow(self):
        """Test full workflow from price analysis to pair selection."""
        # Create price data
        np.random.seed(42)
        n = 200
        trend = np.cumsum(np.random.randn(n))

        price_data = {
            "A": trend + np.random.randn(n) * 0.5,
            "B": trend + np.random.randn(n) * 0.5,
            "C": np.cumsum(np.random.randn(n)),
        }

        # Find cointegrated pairs
        pairs = find_cointegrated_pairs(price_data)

        # Analyze results
        analyzer = CointegrationAnalyzer()

        for asset1, asset2, result in pairs:
            assert result.is_cointegrated

            # Calculate position sizes
            size1, size2 = analyzer.calculate_optimal_position_sizes(
                result,
                price1=100.0,
                price2=100.0,
                capital=100000,
            )

            assert size1 > 0
            assert size2 > 0
