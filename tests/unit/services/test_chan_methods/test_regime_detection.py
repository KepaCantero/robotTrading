"""
Tests for Ernest Chan Regime Detection Implementation
"""

import numpy as np
import pandas as pd
import pytest

from app.services.regime_detection_chan import (
    MarketRegimeDetector,
    RegimeType,
    VolatilityRegimeDetector,
    detect_market_regimes,
    get_regime_statistics,
)


class TestMarketRegimeDetector:
    """Test Market Regime Detector."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 500

        returns = pd.Series(
            np.random.normal(0.0005, 0.02, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        return returns

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        np.random.seed(42)
        n = 500

        # Geometric random walk
        returns = np.random.normal(0.0005, 0.02, n)
        prices = 100 * np.exp(np.cumsum(returns))

        prices = pd.Series(prices, index=pd.date_range('2023-01-01', periods=n, freq='D'))

        return prices

    def test_initialization(self):
        """Test detector initialization."""
        detector = MarketRegimeDetector(n_regimes=3, method='hmm')

        assert detector.n_regimes == 3
        assert detector.method == 'hmm'
        assert detector.model is None

    def test_detect_hmm_regimes(self, sample_returns, sample_prices):
        """Test HMM regime detection."""
        detector = MarketRegimeDetector(n_regimes=3, method='hmm')

        regimes = detector.detect_regimes(sample_returns, sample_prices)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)
        assert all(regime in ['bull', 'bear', 'neutral'] for regime in regimes.values)

    def test_detect_kmeans_regimes(self, sample_returns, sample_prices):
        """Test K-Means regime detection."""
        detector = MarketRegimeDetector(n_regimes=3, method='kmeans')

        regimes = detector.detect_regimes(sample_returns, sample_prices)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)

    def test_detect_threshold_regimes(self, sample_returns, sample_prices):
        """Test threshold-based regime detection."""
        detector = MarketRegimeDetector(n_regimes=3, method='threshold')

        regimes = detector.detect_regimes(sample_returns, sample_prices)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)

    def test_detect_momentum_regimes(self, sample_returns):
        """Test momentum-based regime detection."""
        detector = MarketRegimeDetector(n_regimes=3, method='momentum')

        regimes = detector.detect_regimes(sample_returns)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)

    def test_insufficient_data(self):
        """Test with insufficient data."""
        detector = MarketRegimeDetector(lookback_window=100)

        short_returns = pd.Series([0.01, 0.02, -0.01])

        regimes = detector.detect_regimes(short_returns)

        # Should return neutral regime for insufficient data
        assert all(regime == 'neutral' for regime in regimes.values)

    def test_get_current_regime(self, sample_returns, sample_prices):
        """Test getting current regime."""
        detector = MarketRegimeDetector(n_regimes=3, method='hmm')

        current_regime = detector.get_current_regime(sample_returns, sample_prices)

        assert current_regime.regime_type in RegimeType
        assert current_regime.probability > 0
        assert current_regime.duration_days > 0

    def test_invalid_method(self, sample_returns):
        """Test with invalid detection method."""
        detector = MarketRegimeDetector(method='invalid_method')

        with pytest.raises(ValueError):
            detector.detect_regimes(sample_returns)


class TestVolatilityRegimeDetector:
    """Test Volatility Regime Detector."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns with varying volatility."""
        np.random.seed(42)
        n = 500

        # Simulate changing volatility regimes
        returns = []
        for i in range(n):
            if i < 200:
                vol = 0.01  # Low volatility
            elif i < 350:
                vol = 0.02  # Medium volatility
            else:
                vol = 0.04  # High volatility

            returns.append(np.random.normal(0.0005, vol))

        returns = pd.Series(returns, index=pd.date_range('2023-01-01', periods=n, freq='D'))

        return returns

    def test_initialization(self):
        """Test detector initialization."""
        detector = VolatilityRegimeDetector(n_regimes=2)

        assert detector.n_regimes == 2

    def test_detect_hmm_volatility(self, sample_returns):
        """Test HMM volatility detection."""
        detector = VolatilityRegimeDetector(method='hmm')

        regimes = detector.detect_volatility_regimes(sample_returns)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)
        assert all(regime in ['low', 'high', 'medium'] for regime in regimes.values)

    def test_detect_threshold_volatility(self, sample_returns):
        """Test threshold-based volatility detection."""
        detector = VolatilityRegimeDetector(method='threshold')

        regimes = detector.detect_volatility_regimes(sample_returns)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)

    def test_three_volatility_regimes(self, sample_returns):
        """Test with 3 volatility regimes."""
        detector = VolatilityRegimeDetector(n_regimes=3, method='hmm')

        regimes = detector.detect_volatility_regimes(sample_returns)

        unique_regimes = set(regimes.values)
        assert len(unique_regimes) <= 3


class TestHighLevelFunctions:
    """Test high-level regime detection functions."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 500

        returns = pd.Series(
            np.random.normal(0.0005, 0.02, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        return returns

    def test_detect_market_regimes(self, sample_returns):
        """Test high-level regime detection function."""
        regimes = detect_market_regimes(sample_returns, method='hmm', n_regimes=3)

        assert isinstance(regimes, pd.Series)
        assert len(regimes) == len(sample_returns)

    def test_detect_market_regimes_different_methods(self, sample_returns):
        """Test with different detection methods."""
        methods = ['hmm', 'kmeans', 'threshold']

        for method in methods:
            regimes = detect_market_regimes(sample_returns, method=method, n_regimes=3)

            assert isinstance(regimes, pd.Series)
            assert len(regimes) == len(sample_returns)

    def test_get_regime_statistics(self, sample_returns):
        """Test getting regime statistics."""
        regimes = detect_market_regimes(sample_returns, method='hmm', n_regimes=3)

        stats = get_regime_statistics(sample_returns, regimes)

        assert isinstance(stats, pd.DataFrame)
        assert len(stats) <= 3  # At most 3 regimes
        assert 'regime' in stats.columns
        assert 'periods' in stats.columns
        assert 'mean_return' in stats.columns
        assert 'volatility' in stats.columns
        assert 'sharpe' in stats.columns


class TestRegimeAwareStrategy:
    """Test regime-aware strategy backtesting."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for regime-aware strategy testing."""
        np.random.seed(42)
        n = 500

        returns = pd.Series(
            np.random.normal(0.0005, 0.02, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        regimes = pd.Series(
            np.random.choice(['bull', 'bear', 'neutral'], n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        # Strategy returns for each regime
        bull_returns = pd.Series(
            np.random.normal(0.001, 0.015, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        bear_returns = pd.Series(
            np.random.normal(0.0003, 0.01, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        neutral_returns = pd.Series(
            np.random.normal(0.0005, 0.012, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
        )

        return {
            'returns': returns,
            'regimes': regimes,
            'bull_returns': bull_returns,
            'bear_returns': bear_returns,
            'neutral_returns': neutral_returns,
        }

    def test_backtest_regime_aware_strategy(self, sample_data):
        """Test regime-aware strategy backtesting."""
        detector = MarketRegimeDetector(n_regimes=3, method='hmm')

        combined_returns = detector.backtest_regime_aware_strategy(
            returns=sample_data['returns'],
            regime_signals=sample_data['regimes'],
            bull_strategy_returns=sample_data['bull_returns'],
            bear_strategy_returns=sample_data['bear_returns'],
            neutral_strategy_returns=sample_data['neutral_returns'],
        )

        assert isinstance(combined_returns, pd.Series)
        assert len(combined_returns) == len(sample_data['returns'])
