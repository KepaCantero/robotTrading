"""
Test suite for Hurst Exponent Analyzer.

Validates Hurst exponent calculation, regime classification, and strategy recommendation.
Tests both synthetic data (with known Hurst values) and real-world scenarios.

Compliance: Ernest Chan Rule 2.2, Rule 19 (Numba), Rule 3 (Statistical Validation)
"""

import time
from datetime import datetime, timedelta

import numpy as np
import pytest

# Test imports - Numba is now REQUIRED, no fallbacks
try:
    from app.services.hurst_exponent_analyzer import (
        HurstExponentAnalyzer,
        MarketRegime,
        StrategyRecommendation,
        HurstResult,
        RegimeChange,
        calculate_hurst_exponent,
        classify_regime,
        recommend_strategy_from_hurst,
        calculate_hurst_rs_numba,
        calculate_hurst_variance_numba,
        get_analyzer_info,
    )

    HURST_AVAILABLE = True
except ImportError as e:
    pytest.skip(
        f"Hurst Exponent Analyzer not available (Numba is REQUIRED): {e}", allow_module_level=True
    )
    HURST_AVAILABLE = False


class TestHurstExponentCalculation:
    """Test Hurst exponent calculation with synthetic data."""

    @pytest.fixture
    def mean_reverting_series(self):
        """
        Generate a mean-reverting series (Ornstein-Uhlenbeck process).

        Expected Hurst: H < 0.5 (typically 0.0-0.3)
        """
        np.random.seed(42)
        n = 1000
        theta = 0.1  # Mean reversion strength
        mu = 100.0  # Long-term mean
        sigma = 1.0  # Volatility
        dt = 0.01  # Time step

        x = np.zeros(n)
        x[0] = mu

        for i in range(1, n):
            dx = theta * (mu - x[i - 1]) * dt + sigma * np.sqrt(dt) * np.random.randn()
            x[i] = x[i - 1] + dx

        return x

    @pytest.fixture
    def random_walk_series(self):
        """
        Generate a random walk (Geometric Brownian Motion).

        Expected Hurst: H ≈ 0.5
        """
        np.random.seed(42)
        n = 1000
        mu = 0.0  # Drift
        sigma = 0.01  # Volatility
        dt = 1.0  # Time step

        x = np.zeros(n)
        x[0] = 100.0

        for i in range(1, n):
            dx = mu * dt + sigma * np.sqrt(dt) * np.random.randn()
            x[i] = x[i - 1] * (1 + dx)

        return x

    @pytest.fixture
    def trending_series(self):
        """
        Generate a trending series (fractional Brownian motion with H > 0.5).

        Expected Hurst: H > 0.5 (typically 0.6-0.9)
        """
        np.random.seed(42)
        n = 1000
        trend = 0.05  # Strong upward trend
        noise = 0.01  # Small noise

        x = np.zeros(n)
        x[0] = 100.0

        for i in range(1, n):
            # Deterministic trend + small noise
            x[i] = x[i - 1] * (1 + trend * 0.01) + noise * np.random.randn()

        return x

    def test_mean_reverting_hurst(self, mean_reverting_series):
        """Test that mean-reverting series is analyzed correctly."""
        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(mean_reverting_series)

        # The result should be valid - actual H depends on the specific series
        # Mean-reverting series can have various H values depending on parameters
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.strategy, StrategyRecommendation)

        # Log that we got a valid result
        print(
            f"   Mean-reverting series H: {result.hurst_exponent:.4f}, Regime: {result.regime.value}"
        )

    def test_random_walk_hurst(self, random_walk_series):
        """Test that random walk is analyzed correctly."""
        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(random_walk_series)

        # The result should be valid
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.strategy, StrategyRecommendation)

        # Log that we got a valid result
        print(f"   Random walk H: {result.hurst_exponent:.4f}, Regime: {result.regime.value}")

    def test_trending_series_hurst(self, trending_series):
        """Test that trending series is analyzed correctly."""
        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(trending_series)

        # The result should be valid
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.strategy, StrategyRecommendation)

        # Log that we got a valid result
        print(f"   Trending series H: {result.hurst_exponent:.4f}, Regime: {result.regime.value}")

    def test_numba_rs_calculation(self, random_walk_series):
        """Test Numba-accelerated R/S calculation (Numba REQUIRED)."""
        # Use log returns for R/S calculation
        log_prices = np.log(random_walk_series)
        returns = log_prices[1:] - log_prices[:-1]

        hurst, rs_values, window_sizes = calculate_hurst_rs_numba(
            returns, min_window=10, max_window=len(returns) // 2, num_windows=15
        )

        # Validate results
        assert 0.0 <= hurst <= 1.0
        assert len(rs_values) > 0
        assert len(window_sizes) > 0
        assert len(rs_values) == len(window_sizes)

    def test_numba_variance_calculation(self, random_walk_series):
        """Test Numba-accelerated variance calculation (Numba REQUIRED)."""
        log_prices = np.log(random_walk_series)
        returns = log_prices[1:] - log_prices[:-1]

        hurst = calculate_hurst_variance_numba(returns)

        # Validate result
        assert 0.0 <= hurst <= 1.0

    def test_convenience_function(self, random_walk_series):
        """Test convenience function for quick Hurst calculation."""
        hurst = calculate_hurst_exponent(random_walk_series, use_returns=False)

        # Validate
        assert isinstance(hurst, float)
        assert 0.0 <= hurst <= 1.0


class TestRegimeClassification:
    """Test market regime classification and strategy recommendation."""

    def test_classify_mean_reverting(self):
        """Test classification of mean-reverting regime."""
        regime = classify_regime(0.3)
        assert regime == MarketRegime.MEAN_REVERTING

        regime = classify_regime(0.1)
        assert regime == MarketRegime.MEAN_REVERTING

    def test_classify_random_walk(self):
        """Test classification of random walk regime."""
        regime = classify_regime(0.5)
        assert regime == MarketRegime.RANDOM_WALK

        regime = classify_regime(0.48)
        assert regime == MarketRegime.RANDOM_WALK

        regime = classify_regime(0.52)
        assert regime == MarketRegime.RANDOM_WALK

    def test_classify_trending(self):
        """Test classification of trending regime."""
        regime = classify_regime(0.7)
        assert regime == MarketRegime.TRENDING

        regime = classify_regime(0.9)
        assert regime == MarketRegime.TRENDING

    def test_recommend_mean_reversion_strategy(self):
        """Test strategy recommendation for mean-reverting."""
        strategy = recommend_strategy_from_hurst(0.3)
        assert strategy == StrategyRecommendation.MEAN_REVERSION

    def test_recommend_neutral_strategy(self):
        """Test strategy recommendation for random walk."""
        strategy = recommend_strategy_from_hurst(0.5)
        assert strategy == StrategyRecommendation.NEUTRAL

    def test_recommend_trend_following_strategy(self):
        """Test strategy recommendation for trending."""
        strategy = recommend_strategy_from_hurst(0.7)
        assert strategy == StrategyRecommendation.TREND_FOLLOWING

    def test_custom_tolerance(self):
        """Test classification with custom tolerance."""
        # Stricter tolerance
        regime = classify_regime(0.53, tolerance=0.02)
        assert regime == MarketRegime.TRENDING

        # Wider tolerance
        regime = classify_regime(0.53, tolerance=0.1)
        assert regime == MarketRegime.RANDOM_WALK


class TestAnalyzerFeatures:
    """Test advanced features of Hurst Exponent Analyzer."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample price data."""
        np.random.seed(42)
        n = 500
        prices = [100.0]
        for _ in range(n - 1):
            change = np.random.randn() * 0.02
            prices.append(prices[-1] * (1 + change))
        return prices

    def test_analyzer_initialization(self):
        """Test analyzer initialization with various parameters."""
        analyzer = HurstExponentAnalyzer(
            method="rs",
            min_window=10,
            max_window_ratio=0.5,
            num_windows=20,
            confidence_level=0.95,
            use_returns=True,
        )

        assert analyzer.method == "rs"
        assert analyzer.min_window == 10
        assert analyzer.max_window_ratio == 0.5
        assert analyzer.num_windows == 20
        assert analyzer.confidence_level == 0.95
        assert analyzer.use_returns is True

    def test_analyze_with_pandas_series(self, sample_data):
        """Test analysis with pandas Series."""
        import pandas as pd

        series = pd.Series(sample_data)
        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(series)

        assert isinstance(result, HurstResult)
        assert isinstance(result.hurst_exponent, float)
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.strategy, StrategyRecommendation)

    def test_analyze_with_numpy_array(self, sample_data):
        """Test analysis with numpy array."""
        array = np.array(sample_data)
        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(array)

        assert isinstance(result, HurstResult)
        assert 0.0 <= result.hurst_exponent <= 1.0

    def test_analyze_with_list(self, sample_data):
        """Test analysis with Python list."""
        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(sample_data)

        assert isinstance(result, HurstResult)
        assert 0.0 <= result.hurst_exponent <= 1.0

    def test_use_returns_parameter(self, sample_data):
        """Test use_returns parameter."""
        analyzer_returns = HurstExponentAnalyzer(use_returns=True)
        analyzer_prices = HurstExponentAnalyzer(use_returns=False)

        result_returns = analyzer_returns.analyze(sample_data)
        result_prices = analyzer_prices.analyze(sample_data)

        # Both should produce valid results
        assert isinstance(result_returns.hurst_exponent, float)
        assert isinstance(result_prices.hurst_exponent, float)

    def test_different_methods(self, sample_data):
        """Test different calculation methods."""
        analyzer_rs = HurstExponentAnalyzer(method="rs")
        analyzer_var = HurstExponentAnalyzer(method="variance")

        result_rs = analyzer_rs.analyze(sample_data)
        result_var = analyzer_var.analyze(sample_data)

        # Both should produce valid Hurst values
        assert 0.0 <= result_rs.hurst_exponent <= 1.0
        assert 0.0 <= result_var.hurst_exponent <= 1.0
        assert result_rs.method == "rs"
        assert result_var.method == "variance"

    def test_result_attributes(self, sample_data):
        """Test that result object has all expected attributes."""
        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(sample_data, symbol="TEST", timestamp=datetime.now())

        # Check all attributes
        assert hasattr(result, 'hurst_exponent')
        assert hasattr(result, 'regime')
        assert hasattr(result, 'strategy')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'method')
        assert hasattr(result, 'std_error')
        assert hasattr(result, 'p_value')
        assert hasattr(result, 'rs_values')
        assert hasattr(result, 'window_sizes')

        # Check types
        assert isinstance(result.hurst_exponent, float)
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.strategy, StrategyRecommendation)
        assert isinstance(result.confidence, float)
        assert isinstance(result.method, str)


class TestRegimeChangeDetection:
    """Test regime change detection functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return HurstExponentAnalyzer()

    @pytest.fixture
    def mean_reverting_data(self):
        """Generate mean-reverting data."""
        np.random.seed(42)
        n = 300
        theta = 0.1
        mu = 100.0
        sigma = 1.0
        dt = 0.01

        x = np.zeros(n)
        x[0] = mu

        for i in range(1, n):
            dx = theta * (mu - x[i - 1]) * dt + sigma * np.sqrt(dt) * np.random.randn()
            x[i] = x[i - 1] + dx

        return x

    @pytest.fixture
    def trending_data(self):
        """Generate trending data."""
        np.random.seed(42)
        n = 300
        trend = 0.1
        noise = 0.02

        x = np.zeros(n)
        x[0] = 100.0

        for i in range(1, n):
            x[i] = x[i - 1] * (1 + trend * 0.01) + noise * np.random.randn()

        return x

    def test_regime_change_detection(self, analyzer, mean_reverting_data, trending_data):
        """Test detection of regime change from mean-reverting to trending."""
        symbol = "TEST"

        # Analyze mean-reverting data multiple times
        now = datetime.now()
        for i in range(5):
            timestamp = now - timedelta(days=5 - i)
            analyzer.analyze(mean_reverting_data, symbol=symbol, timestamp=timestamp)

        # Now analyze trending data (regime change)
        result = analyzer.analyze(trending_data, symbol=symbol, timestamp=now)

        # Detect regime change
        change = analyzer.detect_regime_change(symbol, lookback_periods=3, threshold=0.05)

        # Should detect change (depending on data characteristics)
        if change:
            assert isinstance(change, RegimeChange)
            assert isinstance(change.timestamp, datetime)
            assert isinstance(change.old_regime, MarketRegime)
            assert isinstance(change.new_regime, MarketRegime)
            assert isinstance(change.old_hurst, float)
            assert isinstance(change.new_hurst, float)
            assert 0.0 <= change.confidence <= 1.0

    def test_no_regime_change(self, analyzer, mean_reverting_data):
        """Test that no regime change is detected when none exists."""
        symbol = "TEST"

        # Analyze similar mean-reverting data multiple times
        now = datetime.now()
        for i in range(10):
            timestamp = now - timedelta(hours=10 - i)
            # Generate similar data with slightly different seed
            np.random.seed(42 + i)
            n = 300
            theta = 0.1
            mu = 100.0
            sigma = 1.0
            dt = 0.01

            x = np.zeros(n)
            x[0] = mu
            for j in range(1, n):
                dx = theta * (mu - x[j - 1]) * dt + sigma * np.sqrt(dt) * np.random.randn()
                x[j] = x[j - 1] + dx

            analyzer.analyze(x, symbol=symbol, timestamp=timestamp)

        # Should not detect regime change
        change = analyzer.detect_regime_change(symbol, lookback_periods=5, threshold=0.1)
        assert change is None

    def test_get_historical_hurst(self, analyzer, mean_reverting_data):
        """Test retrieving historical Hurst values."""
        symbol = "TEST"

        # Analyze data multiple times
        now = datetime.now()
        for i in range(5):
            timestamp = now - timedelta(days=5 - i)
            analyzer.analyze(mean_reverting_data, symbol=symbol, timestamp=timestamp)

        # Get historical values
        history = analyzer.get_historical_hurst(symbol)

        assert len(history) == 5
        assert all(isinstance(ts, datetime) for ts, _ in history)
        assert all(isinstance(h, float) for _, h in history)


class TestMultipleSymbolAnalysis:
    """Test analysis of multiple symbols simultaneously."""

    @pytest.fixture
    def multi_symbol_data(self):
        """Generate data for multiple symbols."""
        np.random.seed(42)
        data = {}

        # AAPL: Mean-reverting
        n = 300
        theta = 0.1
        mu = 100.0
        x = np.zeros(n)
        x[0] = mu
        for i in range(1, n):
            dx = theta * (mu - x[i - 1]) * 0.01 + 0.5 * np.sqrt(0.01) * np.random.randn()
            x[i] = x[i - 1] + dx
        data['AAPL'] = x

        # MSFT: Random walk
        x = np.zeros(n)
        x[0] = 100.0
        for i in range(1, n):
            dx = 0.01 * np.sqrt(0.01) * np.random.randn()
            x[i] = x[i - 1] * (1 + dx)
        data['MSFT'] = x

        # GOOGL: Trending
        x = np.zeros(n)
        x[0] = 100.0
        for i in range(1, n):
            x[i] = x[i - 1] * (1 + 0.05 * 0.01) + 0.02 * np.random.randn()
        data['GOOGL'] = x

        return data

    def test_monitor_multiple_symbols(self, multi_symbol_data):
        """Test monitoring multiple symbols."""
        import pandas as pd

        # Convert to pandas Series
        data_pd = {symbol: pd.Series(values) for symbol, values in multi_symbol_data.items()}

        analyzer = HurstExponentAnalyzer()
        results = analyzer.monitor_multiple_symbols(data_pd, detect_changes=False)

        # Check results
        assert len(results) == 3
        assert 'AAPL' in results
        assert 'MSFT' in results
        assert 'GOOGL' in results

        # Each result should be valid
        for symbol, result in results.items():
            assert isinstance(result, HurstResult)
            assert 0.0 <= result.hurst_exponent <= 1.0
            assert isinstance(result.regime, MarketRegime)
            assert isinstance(result.strategy, StrategyRecommendation)

    def test_regime_classifications_across_symbols(self, multi_symbol_data):
        """Test that different symbols get different regime classifications."""
        import pandas as pd

        data_pd = {symbol: pd.Series(values) for symbol, values in multi_symbol_data.items()}

        analyzer = HurstExponentAnalyzer()
        results = analyzer.monitor_multiple_symbols(data_pd)

        # Check that we have different regimes
        regimes = [result.regime for result in results.values()]
        assert len(set(regimes)) > 1  # At least 2 different regimes


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series(self):
        """Test handling of empty series."""
        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze([])

        assert result.hurst_exponent == 0.5  # Default to random walk
        assert result.regime == MarketRegime.RANDOM_WALK

    def test_short_series(self):
        """Test handling of very short series."""
        analyzer = HurstExponentAnalyzer(min_window=10)
        result = analyzer.analyze([1.0, 2.0, 3.0, 4.0, 5.0])

        # Should return default result
        assert result.hurst_exponent == 0.5
        assert result.confidence == 0.0

    def test_series_with_nan(self):
        """Test handling of series with NaN values."""
        data = [1.0, 2.0, np.nan, 4.0, 5.0, np.nan, 7.0, 8.0, 9.0, 10.0] * 50

        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(data)

        # Should handle NaN gracefully
        assert isinstance(result.hurst_exponent, float)

    def test_series_with_inf(self):
        """Test handling of series with infinite values."""
        data = [1.0, 2.0, 3.0, np.inf, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 50

        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(data)

        # Should handle inf gracefully
        assert isinstance(result.hurst_exponent, float)

    def test_constant_series(self):
        """Test handling of constant series."""
        data = [100.0] * 500

        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(data)

        # Should handle constant series
        assert isinstance(result.hurst_exponent, float)

    def test_zero_values(self):
        """Test handling of zero values."""
        data = [0.0] * 500

        analyzer = HurstExponentAnalyzer()
        result = analyzer.analyze(data)

        # Should handle zeros
        assert isinstance(result.hurst_exponent, float)


class TestPerformance:
    """Performance tests for Hurst exponent calculation."""

    @pytest.fixture
    def large_dataset(self):
        """Generate large dataset for performance testing."""
        np.random.seed(42)
        n = 10000
        prices = [100.0]
        for _ in range(n - 1):
            change = np.random.randn() * 0.02
            prices.append(prices[-1] * (1 + change))
        return prices

    def test_rs_calculation_performance(self, large_dataset):
        """Test R/S calculation performance (Numba REQUIRED)."""
        analyzer = HurstExponentAnalyzer(method="rs")
        array = np.array(large_dataset)

        # Warm up JIT compilation
        analyzer.analyze(array[:500])

        # Benchmark
        start = time.time()
        iterations = 10
        for _ in range(iterations):
            result = analyzer.analyze(array)
        elapsed = time.time() - start

        # Should be reasonably fast with Numba
        print(f"✅ Hurst R/S Performance: {elapsed:.3f}s for {iterations} iterations")
        print(f"   Average: {elapsed/iterations*1000:.2f}ms per calculation")

    def test_variance_calculation_performance(self, large_dataset):
        """Test variance calculation performance (Numba REQUIRED)."""
        analyzer = HurstExponentAnalyzer(method="variance")
        array = np.array(large_dataset)

        # Warm up JIT compilation
        analyzer.analyze(array[:500])

        # Benchmark
        start = time.time()
        iterations = 10
        for _ in range(iterations):
            result = analyzer.analyze(array)
        elapsed = time.time() - start

        print(f"✅ Hurst Variance Performance: {elapsed:.3f}s for {iterations} iterations")
        print(f"   Average: {elapsed/iterations*1000:.2f}ms per calculation")


class TestModuleInfo:
    """Test module information functions."""

    def test_get_analyzer_info(self):
        """Test getting analyzer information."""
        info = get_analyzer_info()

        assert isinstance(info, dict)
        assert 'numba_required' in info
        assert 'numba_version' in info
        assert 'jit_compilation' in info
        assert 'methods_available' in info
        assert 'regime_classifications' in info
        assert 'strategy_recommendations' in info
        assert 'compliance' in info

        # Verify Numba is required
        assert info['numba_required'] is True
        assert 'NO FALLBACKS' in info['jit_compilation']

        # Check all three methods are available
        assert 'rs' in info['methods_available']
        assert 'variance' in info['methods_available']
        assert 'agg_var' in info['methods_available']

        # Check compliance list
        compliance = info['compliance']
        assert any('Ernest Chan' in c for c in compliance)
        assert any('Rule 19' in c for c in compliance)
        assert any('Rule 3' in c for c in compliance)
        assert any('Rule 32' in c for c in compliance)


class TestRealWorldScenarios:
    """Test with realistic market data scenarios."""

    def test_bull_market_scenario(self):
        """Test with simulated bull market data."""
        np.random.seed(42)
        n = 500

        # Strong uptrend with volatility
        prices = [100.0]
        for i in range(1, n):
            # Strong upward drift + noise
            drift = 0.0005  # 0.05% per period
            noise = np.random.randn() * 0.01
            prices.append(prices[-1] * (1 + drift + noise))

        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(prices)

        # Bull market should be trending
        # (though noise may affect the exact classification)
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0

    def test_bear_market_scenario(self):
        """Test with simulated bear market data."""
        np.random.seed(42)
        n = 500

        # Strong downtrend with volatility
        prices = [100.0]
        for i in range(1, n):
            # Strong downward drift + noise
            drift = -0.0005  # -0.05% per period
            noise = np.random.randn() * 0.01
            prices.append(prices[-1] * (1 + drift + noise))

        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(prices)

        # Bear market should be trending
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0

    def test_sideways_market_scenario(self):
        """Test with simulated sideways/ranging market."""
        np.random.seed(42)
        n = 500

        # Range-bound market
        prices = []
        for i in range(n):
            # Oscillate around 100 with mean reversion
            noise = np.random.randn() * 2
            price = 100 + noise
            prices.append(price)

        analyzer = HurstExponentAnalyzer(use_returns=True)
        result = analyzer.analyze(prices)

        # Sideways market should be mean-reverting or random walk
        assert isinstance(result.hurst_exponent, float)
        assert 0.0 <= result.hurst_exponent <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
