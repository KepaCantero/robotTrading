"""
Unit tests for Clustering Regime Detector.

Tests the ClusteringRegimeDetector class which uses KMeans and DBSCAN
to identify market regimes based on market features.
"""

from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def sample_prices() -> List[float]:
    """Generate sample price data for testing."""
    np.random.seed(42)
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 200)  # 200 days of returns
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    return prices


@pytest.fixture
def detector():
    """Create a ClusteringRegimeDetector instance for testing."""
    from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
        ClusteringRegimeDetector,
    )

    return ClusteringRegimeDetector(config={'n_clusters': 3, 'method': 'kmeans'})


@pytest.fixture
def dbscan_detector():
    """Create a ClusteringRegimeDetector with DBSCAN for testing."""
    from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
        ClusteringRegimeDetector,
    )

    return ClusteringRegimeDetector(config={'method': 'dbscan', 'min_samples': 10})


@pytest.mark.unit
class TestClusteringRegimeDetectorInit:
    """Test initialization of ClusteringRegimeDetector."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector()

        assert detector.method == 'kmeans'
        assert detector.n_clusters == 3
        assert detector.window_size == 100
        assert detector.min_samples == 50
        assert detector.use_pca is False
        assert detector.model is None

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        config = {
            'method': 'dbscan',
            'n_clusters': 5,
            'window_size': 50,
            'min_samples': 20,
            'use_pca': True,
            'n_components_pca': 3,
        }
        detector = ClusteringRegimeDetector(config=config)

        assert detector.method == 'dbscan'
        assert detector.n_clusters == 5
        assert detector.window_size == 50
        assert detector.min_samples == 20
        assert detector.use_pca is True
        assert detector.n_components_pca == 3

    def test_regime_labels_three_clusters(self):
        """Test regime labels for 3 clusters."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector(config={'n_clusters': 3})
        assert detector.regime_labels == ['bear', 'sideways', 'bull']

    def test_regime_labels_custom_clusters(self):
        """Test regime labels for custom number of clusters."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector(config={'n_clusters': 5})
        assert detector.regime_labels == [
            'regime_0',
            'regime_1',
            'regime_2',
            'regime_3',
            'regime_4',
        ]


@pytest.mark.unit
class TestExtractFeatures:
    """Test feature extraction functionality."""

    def test_extract_features_basic(self, detector, sample_prices):
        """Test basic feature extraction."""
        features = detector._extract_features(sample_prices)

        assert len(features) > 0
        assert isinstance(features, np.ndarray)

        # Should have features for: returns (4 periods), volatility, momentum, RSI-like
        assert len(features) == 7  # 4 returns + 1 volatility + 1 momentum + 1 RSI

    def test_extract_features_insufficient_data(self, detector):
        """Test feature extraction with insufficient data."""
        short_prices = [100.0, 101.0, 102.0]
        features = detector._extract_features(short_prices)

        assert len(features) == 0

    def test_extract_features_exactly_20_prices(self, detector):
        """Test feature extraction with exactly 20 prices (minimum)."""
        prices_20 = [100.0 + i for i in range(20)]
        features = detector._extract_features(prices_20)

        assert len(features) == 7

    def test_extract_features_constant_prices(self, detector):
        """Test feature extraction with constant prices."""
        constant_prices = [100.0] * 100
        features = detector._extract_features(constant_prices)

        assert len(features) == 7
        # Returns should be zero
        assert features[0] == 0.0  # 1-period return

    def test_extract_features_trending_prices(self, detector):
        """Test feature extraction with trending prices."""
        trending_prices = [100.0 * (1 + 0.01 * i) for i in range(100)]
        features = detector._extract_features(trending_prices)

        assert len(features) == 7
        # Momentum should be positive
        assert features[5] > 0  # Momentum feature


@pytest.mark.unit
class TestFit:
    """Test model fitting functionality."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_fit_kmeans_success(self, mock_kmeans, detector, sample_prices):
        """Test successful KMeans fitting."""
        mock_model = MagicMock()
        mock_kmeans.return_value = mock_model

        result = detector.fit(sample_prices)

        assert result is True
        assert detector.model is not None
        mock_model.fit.assert_called_once()

    def test_fit_insufficient_data(self, detector):
        """Test fitting with insufficient data."""
        short_prices = [100.0] * 10  # Less than min_samples

        result = detector.fit(short_prices)

        assert result is False
        assert detector.model is None

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.DBSCAN')
    def test_fit_dbscan_success(self, mock_dbscan, dbscan_detector, sample_prices):
        """Test successful DBSCAN fitting."""
        mock_model = MagicMock()
        mock_dbscan.return_value = mock_model

        result = dbscan_detector.fit(sample_prices)

        assert result is True
        assert dbscan_detector.model is not None
        mock_model.fit.assert_called_once()

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_fit_with_pca(self, mock_kmeans, sample_prices):
        """Test fitting with PCA enabled."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector(config={'use_pca': True, 'n_components_pca': 2})
        mock_model = MagicMock()
        mock_kmeans.return_value = mock_model

        result = detector.fit(sample_prices)

        assert result is True
        assert detector.pca is not None

    def test_fit_unknown_method(self, sample_prices):
        """Test fitting with unknown method."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        detector = ClusteringRegimeDetector(config={'method': 'unknown_method'})

        result = detector.fit(sample_prices)

        assert result is False


@pytest.mark.unit
class TestDetect:
    """Test regime detection functionality."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_detect_basic(self, mock_kmeans, detector, sample_prices):
        """Test basic regime detection."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])  # Predict cluster 1 (sideways)
        mock_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_model

        result = detector.detect(sample_prices)

        assert isinstance(result, dict)
        assert 'regime' in result
        assert 'cluster' in result
        assert 'confidence' in result
        assert result['regime'] == 'sideways'
        assert result['cluster'] == 1

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detectors.DBSCAN')
    def test_detect_outlier(self, mock_dbscan, dbscan_detector, sample_prices):
        """Test detection of outliers with DBSCAN."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([-1])  # Outlier
        mock_dbscan.return_value = mock_model

        result = dbscan_detector.detect(sample_prices)

        assert result['regime'] == 'outlier'
        assert result['cluster'] == -1
        assert result['confidence'] == 0.0

    def test_detect_without_fit(self, detector, sample_prices):
        """Test detection without prior fitting (should auto-fit)."""
        with patch.object(detector, 'fit', return_value=False):
            result = detector.detect(sample_prices)

            assert result['regime'] == 'unknown'
            assert result['cluster'] == -1
            assert result['confidence'] == 0.0

    def test_detect_insufficient_features(self, detector):
        """Test detection with insufficient features."""
        short_prices = [100.0, 101.0]

        result = detector.detect(short_prices)

        assert result['regime'] == 'unknown'
        assert result['cluster'] == -1

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_detect_confidence_calculation(self, mock_kmeans, detector, sample_prices):
        """Test confidence calculation in detection."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0])
        mock_model.cluster_centers_ = np.array([[0, 0], [10, 10], [20, 20]])
        mock_kmeans.return_value = mock_model

        result = detector.detect(sample_prices)

        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_price_list(self, detector):
        """Test with empty price list."""
        result = detector.detect([])

        assert result['regime'] == 'unknown'
        assert result['cluster'] == -1

    def test_single_price(self, detector):
        """Test with single price."""
        result = detector.detect([100.0])

        assert result['regime'] == 'unknown'

    def test_nan_in_prices(self, detector):
        """Test with NaN values in prices."""
        prices_with_nan = [100.0, 101.0, float('nan'), 103.0, 104.0]

        # Should handle gracefully without crashing
        result = detector.detect(prices_with_nan)
        assert isinstance(result, dict)

    def test_inf_in_prices(self, detector):
        """Test with infinite values in prices."""
        prices_with_inf = [100.0, 101.0, float('inf'), 103.0, 104.0]

        # Should handle gracefully without crashing
        result = detector.detect(prices_with_inf)
        assert isinstance(result, dict)

    def test_negative_prices(self, detector):
        """Test with negative prices (invalid but should handle)."""
        negative_prices = [-100.0, -101.0, -102.0]

        # Should handle without crashing
        result = detector.detect(negative_prices)
        assert isinstance(result, dict)

    def test_zero_prices(self, detector):
        """Test with zero prices."""
        zero_prices = [100.0, 0.0, 100.0]

        # Should handle without crashing
        result = detector.detect(zero_prices)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for clustering detector."""

    @pytest.mark.parametrize("n_clusters", [2, 3, 4, 5, 10])
    def test_different_n_clusters(self, n_clusters, sample_prices):
        """Test with different numbers of clusters."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        config = {'n_clusters': n_clusters, 'method': 'kmeans'}
        detector = ClusteringRegimeDetector(config=config)

        assert len(detector.regime_labels) == n_clusters

    @pytest.mark.parametrize("window_size", [20, 50, 100, 200])
    def test_different_window_sizes(self, window_size, sample_prices):
        """Test with different window sizes."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        config = {'window_size': window_size, 'min_samples': 10}
        detector = ClusteringRegimeDetector(config=config)

        assert detector.window_size == window_size

    @pytest.mark.parametrize("method", ['kmeans', 'dbscan'])
    def test_different_methods(self, method, sample_prices):
        """Test with different clustering methods."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        config = {'method': method, 'min_samples': 10}
        detector = ClusteringRegimeDetector(config=config)

        assert detector.method == method


@pytest.mark.unit
class TestIntegration:
    """Integration tests for clustering detector."""

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    def test_full_workflow(self, mock_kmeans, sample_prices):
        """Test complete workflow: initialize, fit, detect."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])  # Bull regime
        mock_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_model

        # Initialize
        detector = ClusteringRegimeDetector(config={'n_clusters': 3})

        # Fit
        fit_result = detector.fit(sample_prices)
        assert fit_result is True

        # Detect
        detection_result = detector.detect(sample_prices)
        assert detection_result['regime'] == 'bull'
        assert detection_result['cluster'] == 2

    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.KMeans')
    @patch('app.engines.context_engine.regime_detectors.clustering_regime_detector.StandardScaler')
    def test_scaler_integration(self, mock_scaler, mock_kmeans, sample_prices):
        """Test that scaler is properly integrated."""
        from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
            ClusteringRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.cluster_centers_ = np.array([[0, 0], [1, 1], [2, 2]])
        mock_kmeans.return_value = mock_model

        detector = ClusteringRegimeDetector()
        result = detector.detect(sample_prices)

        assert isinstance(result, dict)


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    def test_large_dataset(self, detector):
        """Test with large dataset."""
        np.random.seed(42)
        large_prices = np.random.lognormal(4.6, 0.02, 10000).tolist()

        # Should complete without timing out
        result = detector.fit(large_prices)
        assert isinstance(result, bool)

    def test_high_volatility_prices(self, detector):
        """Test with high volatility price data."""
        np.random.seed(42)
        base_price = 100.0
        high_vol_returns = np.random.normal(0, 0.1, 200)  # 10% daily volatility
        prices = [base_price]
        for ret in high_vol_returns:
            prices.append(prices[-1] * (1 + ret))

        # Should handle high volatility data
        result = detector.detect(prices)
        assert isinstance(result, dict)
