"""
Unit tests for Correlation Regime Detector.

Tests the CorrelationRegimeDetector class which uses correlation analysis
to detect market regimes based on asset correlations.
"""

from typing import Dict, List

import numpy as np
import pytest


@pytest.fixture
def sample_price_data() -> Dict[str, List[float]]:
    """Generate sample multi-asset price data for testing."""
    np.random.seed(42)

    # Create correlated price data for 3 assets
    n_days = 100
    base_returns = np.random.normal(0.001, 0.02, n_days)

    price_data = {'AAPL': [100.0], 'MSFT': [100.0], 'GOOGL': [100.0]}

    for ret in base_returns:
        # Add some correlation with noise
        price_data['AAPL'].append(price_data['AAPL'][-1] * (1 + ret + np.random.normal(0, 0.005)))
        price_data['MSFT'].append(price_data['MSFT'][-1] * (1 + ret + np.random.normal(0, 0.006)))
        price_data['GOOGL'].append(price_data['GOOGL'][-1] * (1 + ret + np.random.normal(0, 0.007)))

    return price_data


@pytest.fixture
def high_correlation_data() -> Dict[str, List[float]]:
    """Generate high correlation price data."""
    np.random.seed(123)
    n_days = 100
    base_returns = np.random.normal(0.001, 0.01, n_days)

    price_data = {'SPY': [100.0], 'IVV': [100.0], 'VOO': [100.0]}

    for ret in base_returns:
        # Highly correlated (same returns + minimal noise)
        for symbol in price_data:
            price_data[symbol].append(
                price_data[symbol][-1] * (1 + ret + np.random.normal(0, 0.001))
            )

    return price_data


@pytest.fixture
def low_correlation_data() -> Dict[str, List[float]]:
    """Generate low correlation price data."""
    np.random.seed(456)
    n_days = 100

    price_data = {
        'AAPL': [100.0],
        'GLD': [100.0],  # Gold - low correlation with stocks
        'BTC': [100.0],  # Bitcoin - low correlation
    }

    for i in range(n_days):
        price_data['AAPL'].append(price_data['AAPL'][-1] * (1 + np.random.normal(0.001, 0.02)))
        price_data['GLD'].append(price_data['GLD'][-1] * (1 + np.random.normal(0.0005, 0.01)))
        price_data['BTC'].append(price_data['BTC'][-1] * (1 + np.random.normal(0.002, 0.05)))

    return price_data


@pytest.fixture
def detector():
    """Create a CorrelationRegimeDetector instance for testing."""
    from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
        CorrelationRegimeDetector,
    )

    return CorrelationRegimeDetector()


@pytest.mark.unit
class TestCorrelationRegimeDetectorInit:
    """Test initialization of CorrelationRegimeDetector."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector()

        assert detector.window_size == 60
        assert detector.correlation_threshold == 0.7
        assert detector.use_pca is True
        assert detector.n_components_pca == 3
        assert detector.baseline_correlation is None

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        config = {
            'window_size': 30,
            'correlation_threshold': 0.5,
            'use_pca': False,
            'n_components_pca': 5,
        }
        detector = CorrelationRegimeDetector(config=config)

        assert detector.window_size == 30
        assert detector.correlation_threshold == 0.5
        assert detector.use_pca is False
        assert detector.n_components_pca == 5


@pytest.mark.unit
class TestCalculateCorrelationMatrix:
    """Test correlation matrix calculation."""

    def test_calculate_correlation_matrix_basic(self, detector, sample_price_data):
        """Test basic correlation matrix calculation."""
        # Convert price data to returns matrix
        symbols = list(sample_price_data.keys())
        min_length = min(len(prices) for prices in sample_price_data.values())

        returns_dict = {}
        for symbol, prices in sample_price_data.items():
            returns = np.diff(prices[-min_length:]) / prices[-min_length:-1]
            returns_dict[symbol] = returns[-detector.window_size :]

        returns_matrix = np.array([returns_dict[symbol] for symbol in symbols]).T

        corr_matrix = detector._calculate_correlation_matrix(returns_matrix)

        assert isinstance(corr_matrix, np.ndarray)
        assert corr_matrix.shape == (3, 3)  # 3 assets
        assert np.allclose(np.diag(corr_matrix), 1.0, atol=1e-10)  # Diagonal should be 1.0

    def test_calculate_correlation_matrix_single_asset(self, detector):
        """Test correlation matrix with single asset."""
        returns_matrix = np.array([[0.01, 0.02, 0.03]]).T

        corr_matrix = detector._calculate_correlation_matrix(returns_matrix)

        assert corr_matrix.shape == (1, 1)
        assert corr_matrix[0, 0] == 1.0

    def test_correlation_matrix_symmetry(self, detector, sample_price_data):
        """Test that correlation matrix is symmetric."""
        symbols = list(sample_price_data.keys())
        min_length = min(len(prices) for prices in sample_price_data.values())

        returns_dict = {}
        for symbol, prices in sample_price_data.items():
            returns = np.diff(prices[-min_length:]) / prices[-min_length:-1]
            returns_dict[symbol] = returns[-detector.window_size :]

        returns_matrix = np.array([returns_dict[symbol] for symbol in symbols]).T

        corr_matrix = detector._calculate_correlation_matrix(returns_matrix)

        assert np.allclose(corr_matrix, corr_matrix.T, atol=1e-10)


@pytest.mark.unit
class TestCalculatePCAVariance:
    """Test PCA variance calculation."""

    def test_calculate_pca_variance_with_pca(self, detector, sample_price_data):
        """Test PCA variance calculation with PCA enabled."""
        symbols = list(sample_price_data.keys())
        min_length = min(len(prices) for prices in sample_price_data.values())

        returns_dict = {}
        for symbol, prices in sample_price_data.items():
            returns = np.diff(prices[-min_length:]) / prices[-min_length:-1]
            returns_dict[symbol] = returns[-detector.window_size :]

        returns_matrix = np.array([returns_dict[symbol] for symbol in symbols]).T

        pca_variance = detector._calculate_pca_variance(returns_matrix)

        assert isinstance(pca_variance, float)
        assert 0.0 <= pca_variance <= 1.0

    def test_calculate_pca_variance_without_pca(self, sample_price_data):
        """Test PCA variance calculation with PCA disabled."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'use_pca': False})

        symbols = list(sample_price_data.keys())
        min_length = min(len(prices) for prices in sample_price_data.values())

        returns_dict = {}
        for symbol, prices in sample_price_data.items():
            returns = np.diff(prices[-min_length:]) / prices[-min_length:-1]
            returns_dict[symbol] = returns[-detector.window_size :]

        returns_matrix = np.array([returns_dict[symbol] for symbol in symbols]).T

        pca_variance = detector._calculate_pca_variance(returns_matrix)

        assert pca_variance == 0.0

    def test_calculate_pca_variance_single_asset(self, detector):
        """Test PCA variance with single asset."""
        returns_matrix = np.array([[0.01, 0.02, 0.03]]).T

        pca_variance = detector._calculate_pca_variance(returns_matrix)

        assert pca_variance == 0.0


@pytest.mark.unit
class TestDetect:
    """Test regime detection functionality."""

    def test_detect_basic(self, detector, sample_price_data):
        """Test basic regime detection."""
        result = detector.detect(sample_price_data)

        assert isinstance(result, dict)
        assert 'regime' in result
        assert 'correlation_regime' in result
        assert 'average_correlation' in result
        assert 'pca_variance' in result
        assert 'confidence' in result

    def test_detect_high_correlation(self, detector, high_correlation_data):
        """Test detection with high correlation data."""
        result = detector.detect(high_correlation_data)

        assert result['correlation_regime'] in [
            'high_correlation',
            'normal_correlation',
            'low_correlation',
        ]
        assert result['average_correlation'] > 0.5  # Should be relatively high

    def test_detect_low_correlation(self, detector, low_correlation_data):
        """Test detection with low correlation data."""
        result = detector.detect(low_correlation_data)

        assert result['correlation_regime'] in [
            'high_correlation',
            'normal_correlation',
            'low_correlation',
        ]
        assert result['average_correlation'] < 0.7  # Should be relatively low

    def test_detect_insufficient_assets(self, detector):
        """Test detection with insufficient assets (less than 2)."""
        single_asset_data = {'AAPL': [100.0, 101.0, 102.0]}

        result = detector.detect(single_asset_data)

        assert result['regime'] == 'unknown'
        assert result['correlation_regime'] == 'unknown'
        assert result['confidence'] == 0.0

    def test_detect_insufficient_data_length(self, detector):
        """Test detection with insufficient data length."""
        short_data = {'AAPL': [100.0, 101.0], 'MSFT': [100.0, 101.0]}

        result = detector.detect(short_data)

        assert result['regime'] == 'unknown'
        assert result['confidence'] == 0.0

    def test_detect_correlation_matrix_in_result(self, detector, sample_price_data):
        """Test that correlation matrix is included in result."""
        result = detector.detect(sample_price_data)

        assert 'correlation_matrix' in result
        assert isinstance(result['correlation_matrix'], list)
        assert len(result['correlation_matrix']) == 3  # 3 assets


@pytest.mark.unit
class TestSetBaseline:
    """Test baseline functionality."""

    def test_set_baseline(self, detector, sample_price_data):
        """Test setting baseline correlation."""
        detector.set_baseline(sample_price_data)

        assert detector.baseline_correlation is not None
        assert isinstance(detector.baseline_correlation, float)

    def test_baseline_comparison(self, detector, sample_price_data):
        """Test baseline comparison in detection."""
        # Set baseline
        detector.set_baseline(sample_price_data)
        detector.baseline_correlation

        # Detect with baseline set
        result = detector.detect(sample_price_data)

        assert 'baseline_comparison' in result
        assert result['baseline_comparison'] is not None
        assert 'baseline_correlation' in result['baseline_comparison']
        assert 'correlation_change' in result['baseline_comparison']
        assert 'regime_changed' in result['baseline_comparison']

    def test_baseline_without_setting(self, detector, sample_price_data):
        """Test detection without baseline set."""
        result = detector.detect(sample_price_data)

        assert 'baseline_comparison' in result
        assert result['baseline_comparison'] is None


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_price_data(self, detector):
        """Test with empty price data."""
        result = detector.detect({})

        assert result['regime'] == 'unknown'

    def test_nan_in_prices(self, detector):
        """Test with NaN values in prices."""
        data_with_nan = {
            'AAPL': [100.0, 101.0, float('nan'), 103.0],
            'MSFT': [100.0, 101.0, 102.0, 103.0],
        }

        # Should handle gracefully
        result = detector.detect(data_with_nan)
        assert isinstance(result, dict)

    def test_inf_in_prices(self, detector):
        """Test with infinite values in prices."""
        data_with_inf = {
            'AAPL': [100.0, 101.0, float('inf'), 103.0],
            'MSFT': [100.0, 101.0, 102.0, 103.0],
        }

        # Should handle gracefully
        result = detector.detect(data_with_inf)
        assert isinstance(result, dict)

    def test_zero_prices(self, detector):
        """Test with zero prices."""
        data_with_zero = {'AAPL': [100.0, 0.0, 100.0], 'MSFT': [100.0, 100.0, 100.0]}

        # Should handle gracefully
        result = detector.detect(data_with_zero)
        assert isinstance(result, dict)

    def test_negative_prices(self, detector):
        """Test with negative prices."""
        data_with_negative = {'AAPL': [-100.0, -101.0, -102.0], 'MSFT': [-100.0, -101.0, -102.0]}

        # Should handle gracefully
        result = detector.detect(data_with_negative)
        assert isinstance(result, dict)

    def test_different_length_price_series(self, detector):
        """Test with different length price series."""
        uneven_data = {'AAPL': [100.0] * 100, 'MSFT': [100.0] * 80, 'GOOGL': [100.0] * 60}

        # Should handle by using minimum length
        result = detector.detect(uneven_data)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestCorrelationThresholds:
    """Test correlation threshold classification."""

    def test_high_correlation_classification(self, high_correlation_data):
        """Test classification of high correlation regime."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'correlation_threshold': 0.6})
        result = detector.detect(high_correlation_data)

        # With high correlation data, should detect high or normal correlation
        assert result['correlation_regime'] in ['high_correlation', 'normal_correlation']

    def test_normal_correlation_classification(self, sample_price_data):
        """Test classification of normal correlation regime."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'correlation_threshold': 0.8})
        result = detector.detect(sample_price_data)

        # With moderate threshold, should detect normal or low correlation
        assert result['correlation_regime'] in ['normal_correlation', 'low_correlation']

    def test_low_correlation_classification(self, low_correlation_data):
        """Test classification of low correlation regime."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'correlation_threshold': 0.5})
        result = detector.detect(low_correlation_data)

        # With low correlation data
        assert result['correlation_regime'] == 'low_correlation'


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for correlation detector."""

    @pytest.mark.parametrize("window_size", [20, 40, 60, 100])
    def test_different_window_sizes(self, window_size, sample_price_data):
        """Test with different window sizes."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(config={'window_size': window_size})

        assert detector.window_size == window_size

    @pytest.mark.parametrize("correlation_threshold", [0.3, 0.5, 0.7, 0.9])
    def test_different_correlation_thresholds(self, correlation_threshold, sample_price_data):
        """Test with different correlation thresholds."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector(
            config={'correlation_threshold': correlation_threshold}
        )

        assert detector.correlation_threshold == correlation_threshold

    @pytest.mark.parametrize("n_assets", [2, 3, 5, 10])
    def test_different_numbers_of_assets(self, n_assets):
        """Test with different numbers of assets."""
        from app.engines.context_engine.regime_detectors.correlation_regime_detector import (
            CorrelationRegimeDetector,
        )

        detector = CorrelationRegimeDetector()

        # Generate price data for n_assets
        np.random.seed(42)
        price_data = {f'Asset_{i}': [100.0] * 100 for i in range(n_assets)}

        result = detector.detect(price_data)

        assert isinstance(result, dict)
        if n_assets >= 2:
            assert len(result['correlation_matrix']) == n_assets


@pytest.mark.unit
class TestIntegration:
    """Integration tests for correlation detector."""

    def test_full_workflow_with_baseline(self, detector, sample_price_data):
        """Test complete workflow: set baseline, detect, compare."""
        # Set baseline
        detector.set_baseline(sample_price_data)

        # Detect
        result = detector.detect(sample_price_data)

        # Verify baseline comparison
        assert result['baseline_comparison'] is not None
        assert 'baseline_correlation' in result['baseline_comparison']

    def test_regime_change_detection(self, detector, sample_price_data, high_correlation_data):
        """Test regime change detection."""
        # Set baseline with normal correlation
        detector.set_baseline(sample_price_data)

        # Detect with high correlation
        result = detector.detect(high_correlation_data)

        # Should detect change if correlation difference is significant
        if result['baseline_comparison']:
            assert 'regime_changed' in result['baseline_comparison']

    def test_confidence_calculation(self, detector, sample_price_data):
        """Test confidence calculation based on number of correlations."""
        result = detector.detect(sample_price_data)

        # With 3 assets, we have 3 unique correlations (3 choose 2)
        # Confidence should be min(1.0, 3/10) = 0.3
        assert 0.0 <= result['confidence'] <= 1.0


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    def test_large_dataset(self, detector):
        """Test with large dataset."""
        np.random.seed(42)
        n_assets = 50
        n_days = 500

        large_data = {}
        for i in range(n_assets):
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [100.0]
            for ret in returns:
                prices.append(prices[-1] * (1 + ret))
            large_data[f'Asset_{i}'] = prices

        # Should complete without timing out
        result = detector.detect(large_data)
        assert isinstance(result, dict)

    def test_high_frequency_correlation_calculation(self, detector):
        """Test repeated correlation calculations."""
        np.random.seed(42)
        price_data = {'AAPL': [100.0] * 200, 'MSFT': [100.0] * 200, 'GOOGL': [100.0] * 200}

        # Should handle multiple calculations efficiently
        for _ in range(10):
            result = detector.detect(price_data)
            assert isinstance(result, dict)
