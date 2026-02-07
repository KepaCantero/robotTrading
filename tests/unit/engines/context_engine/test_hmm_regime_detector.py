"""
Unit tests for HMM Regime Detector.

Tests the HMMRegimeDetector class which uses Hidden Markov Models
to detect market regimes (bull, bear, sideways).
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
def trending_prices() -> List[float]:
    """Generate trending price data (bull market)."""
    np.random.seed(123)
    base_price = 100.0
    returns = np.random.normal(0.005, 0.015, 200)  # Upward trend
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    return prices


@pytest.fixture
def bear_market_prices() -> List[float]:
    """Generate bear market price data."""
    np.random.seed(456)
    base_price = 100.0
    returns = np.random.normal(-0.003, 0.025, 200)  # Downward trend
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    return prices


@pytest.fixture
def detector():
    """Create an HMMRegimeDetector instance for testing."""
    from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMMRegimeDetector

    return HMMRegimeDetector(config={'n_regimes': 3})


@pytest.fixture
def two_regime_detector():
    """Create an HMMRegimeDetector with 2 regimes."""
    from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMMRegimeDetector

    return HMMRegimeDetector(config={'n_regimes': 2})


@pytest.mark.unit
class TestHMMRegimeDetectorInit:
    """Test initialization of HMMRegimeDetector."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector()

        assert detector.n_regimes == 3
        assert detector.n_features == 2
        assert detector.window_size == 100
        assert detector.min_samples == 50
        assert detector.model is None

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        config = {'n_regimes': 4, 'n_features': 3, 'window_size': 150, 'min_samples': 100}
        detector = HMMRegimeDetector(config=config)

        assert detector.n_regimes == 4
        assert detector.n_features == 3
        assert detector.window_size == 150
        assert detector.min_samples == 100

    def test_regime_labels_three_regimes(self):
        """Test regime labels for 3 regimes."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'n_regimes': 3})
        assert detector.regime_labels == ['bear', 'sideways', 'bull']

    def test_regime_labels_custom_regimes(self):
        """Test regime labels for custom number of regimes."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'n_regimes': 5})
        assert detector.regime_labels == [
            'regime_0',
            'regime_1',
            'regime_2',
            'regime_3',
            'regime_4',
        ]


@pytest.mark.unit
class TestCalculateRollingVolatility:
    """Test rolling volatility calculation."""

    def test_calculate_rolling_volatility_basic(self, detector, sample_prices):
        """Test basic rolling volatility calculation."""
        returns = np.diff(sample_prices) / sample_prices[:-1]
        volatility = detector._calculate_rolling_volatility(returns)

        assert len(volatility) == len(returns)
        assert isinstance(volatility, np.ndarray)
        assert np.all(volatility >= 0)  # Volatility should be non-negative

    def test_calculate_rolling_volatility_short_series(self, detector):
        """Test rolling volatility with short series (< window)."""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01])
        volatility = detector._calculate_rolling_volatility(returns)

        # Should fill with std of entire series
        expected_std = np.std(returns)
        assert np.allclose(volatility, expected_std, atol=1e-10)

    def test_calculate_rolling_volatility_constant_returns(self, detector):
        """Test rolling volatility with constant returns."""
        constant_returns = np.array([0.01] * 50)
        volatility = detector._calculate_rolling_volatility(constant_returns)

        # Should be zero
        assert np.allclose(volatility, 0.0, atol=1e-10)

    def test_calculate_rolling_volatility_window_edge_case(self, detector):
        """Test rolling volatility at window boundaries."""
        returns = np.random.normal(0, 0.02, 50)
        volatility = detector._calculate_rolling_volatility(returns, window=20)

        # First 20 values should be filled with first calculated value
        assert np.allclose(volatility[:20], volatility[20], atol=1e-10)


@pytest.mark.unit
class TestFit:
    """Test model fitting functionality."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_fit_success(self, mock_hmm, detector, sample_prices):
        """Test successful HMM fitting."""
        mock_model = MagicMock()
        mock_hmm.return_value = mock_model

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

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_fit_with_custom_parameters(self, mock_hmm, sample_prices):
        """Test fitting with custom HMM parameters."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'n_regimes': 4, 'window_size': 150})
        mock_model = MagicMock()
        mock_hmm.return_value = mock_model

        result = detector.fit(sample_prices)

        assert result is True

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_fit_uses_correct_observations_shape(self, mock_hmm, detector, sample_prices):
        """Test that fit creates observations with correct shape."""
        mock_model = MagicMock()
        mock_hmm.return_value = mock_model

        detector.fit(sample_prices)

        # Check that fit was called
        mock_model.fit.assert_called_once()

        # Get the call arguments
        call_args = mock_model.fit.call_args
        observations = call_args[0][0]

        # Should have shape (n_samples, n_features) = (100, 2)
        assert observations.shape[1] == 2  # n_features


@pytest.mark.unit
class TestDetect:
    """Test regime detection functionality."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_basic(self, mock_hmm, detector, sample_prices):
        """Test basic regime detection."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0, 1, 2, 1, 1])  # Various states
        mock_model.score_samples.return_value = (
            np.array([-1.0, -2.0, -3.0]),
            np.array([[0.1, 0.2, 0.7]]),
        )
        mock_hmm.return_value = mock_model

        result = detector.detect(sample_prices)

        assert isinstance(result, dict)
        assert 'regime' in result
        assert 'probability' in result
        assert 'regime_probabilities' in result
        assert 'confidence' in result
        assert 'state' in result

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_returns_valid_regime(self, mock_hmm, detector, sample_prices):
        """Test that detect returns a valid regime label."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])  # Bull regime
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.1, 0.2, 0.7]]))
        mock_hmm.return_value = mock_model

        result = detector.detect(sample_prices)

        assert result['regime'] in ['bear', 'sideways', 'bull']

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_probability_range(self, mock_hmm, detector, sample_prices):
        """Test that probability is in valid range."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.2, 0.6, 0.2]]))
        mock_hmm.return_value = mock_model

        result = detector.detect(sample_prices)

        assert 0.0 <= result['probability'] <= 1.0

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_regime_probabilities(self, mock_hmm, detector, sample_prices):
        """Test that all regime probabilities are included."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.1, 0.7, 0.2]]))
        mock_hmm.return_value = mock_model

        result = detector.detect(sample_prices)

        assert len(result['regime_probabilities']) == 3
        assert 'bear' in result['regime_probabilities']
        assert 'sideways' in result['regime_probabilities']
        assert 'bull' in result['regime_probabilities']

    def test_detect_without_fit(self, detector):
        """Test detection without prior fitting (should auto-fit)."""
        with patch.object(detector, 'fit', return_value=False):
            result = detector.detect(sample_prices)

            assert result['regime'] == 'unknown'
            assert result['probability'] == 0.0
            assert result['confidence'] == 0.0

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_confidence_calculation(self, mock_hmm, detector, sample_prices):
        """Test confidence calculation in detection."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.05, 0.15, 0.8]]))
        mock_hmm.return_value = mock_model

        result = detector.detect(sample_prices)

        # Confidence should be max probability
        assert result['confidence'] == 0.8


@pytest.mark.unit
class TestGetTransitionMatrix:
    """Test transition matrix retrieval."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_get_transition_matrix_with_model(self, mock_hmm, detector, sample_prices):
        """Test getting transition matrix when model is trained."""
        mock_model = MagicMock()
        expected_matrix = np.array([[0.9, 0.05, 0.05], [0.1, 0.8, 0.1], [0.05, 0.05, 0.9]])
        mock_model.transmat_ = expected_matrix
        mock_hmm.return_value = mock_model

        detector.fit(sample_prices)
        result = detector.get_transition_matrix()

        assert result is not None
        assert np.array_equal(result, expected_matrix)

    def test_get_transition_matrix_without_model(self, detector):
        """Test getting transition matrix without trained model."""
        result = detector.get_transition_matrix()

        assert result is None

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_transition_matrix_properties(self, mock_hmm, detector, sample_prices):
        """Test that transition matrix has valid properties."""
        mock_model = MagicMock()
        mock_model.transmat_ = np.array([[0.8, 0.1, 0.1], [0.2, 0.6, 0.2], [0.1, 0.1, 0.8]])
        mock_hmm.return_value = mock_model

        detector.fit(sample_prices)
        transmat = detector.get_transition_matrix()

        # Each row should sum to 1
        for row in transmat:
            assert np.isclose(row.sum(), 1.0, atol=1e-10)

        # All values should be non-negative
        assert np.all(transmat >= 0)


@pytest.mark.unit
class TestGetRegimeMeans:
    """Test regime means retrieval."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_get_regime_means_with_model(self, mock_hmm, detector, sample_prices):
        """Test getting regime means when model is trained."""
        mock_model = MagicMock()
        expected_means = np.array([[-0.005, 0.02], [0.001, 0.015], [0.005, 0.025]])
        mock_model.means_ = expected_means
        mock_hmm.return_value = mock_model

        detector.fit(sample_prices)
        result = detector.get_regime_means()

        assert result is not None
        assert np.array_equal(result, expected_means)

    def test_get_regime_means_without_model(self, detector):
        """Test getting regime means without trained model."""
        result = detector.get_regime_means()

        assert result is None

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_regime_means_shape(self, mock_hmm, detector, sample_prices):
        """Test that regime means has correct shape."""
        mock_model = MagicMock()
        mock_model.means_ = np.array([[0.0, 0.0]] * 3)
        mock_hmm.return_value = mock_model

        detector.fit(sample_prices)
        means = detector.get_regime_means()

        # Should have shape (n_regimes, n_features)
        assert means.shape == (3, 2)


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_price_list(self, detector):
        """Test with empty price list."""
        result = detector.detect([])

        assert result['regime'] == 'unknown'

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
        """Test with negative prices."""
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

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_constant_prices(self, mock_hmm, detector):
        """Test with constant prices."""
        constant_prices = [100.0] * 200

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.1, 0.8, 0.1]]))
        mock_hmm.return_value = mock_model

        result = detector.detect(constant_prices)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for HMM detector."""

    @pytest.mark.parametrize("n_regimes", [2, 3, 4, 5])
    def test_different_n_regimes(self, n_regimes, sample_prices):
        """Test with different numbers of regimes."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'n_regimes': n_regimes})

        assert len(detector.regime_labels) == n_regimes

    @pytest.mark.parametrize("window_size", [50, 100, 150, 200])
    def test_different_window_sizes(self, window_size, sample_prices):
        """Test with different window sizes."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'window_size': window_size, 'min_samples': 30})

        assert detector.window_size == window_size

    @pytest.mark.parametrize("min_samples", [30, 50, 100, 150])
    def test_different_min_samples(self, min_samples, sample_prices):
        """Test with different min_samples values."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        detector = HMMRegimeDetector(config={'min_samples': min_samples})

        assert detector.min_samples == min_samples


@pytest.mark.unit
class TestIntegration:
    """Integration tests for HMM detector."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_full_workflow(self, mock_hmm, sample_prices):
        """Test complete workflow: initialize, fit, detect, get properties."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1, 1, 2])
        mock_model.score_samples.return_value = (
            np.array([-1.0, -2.0, -3.0]),
            np.array([[0.1, 0.7, 0.2]]),
        )
        mock_model.transmat_ = np.eye(3)
        mock_model.means_ = np.zeros((3, 2))
        mock_hmm.return_value = mock_model

        # Initialize
        detector = HMMRegimeDetector(config={'n_regimes': 3})

        # Fit
        fit_result = detector.fit(sample_prices)
        assert fit_result is True

        # Detect
        detection_result = detector.detect(sample_prices)
        assert detection_result['regime'] in ['bear', 'sideways', 'bull']

        # Get transition matrix
        transmat = detector.get_transition_matrix()
        assert transmat is not None

        # Get regime means
        means = detector.get_regime_means()
        assert means is not None

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_different_market_conditions(self, mock_hmm, trending_prices, bear_market_prices):
        """Test detection under different market conditions."""
        from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
            HMMRegimeDetector,
        )

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2])  # Bull for trending
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.1, 0.1, 0.8]]))
        mock_hmm.return_value = mock_model

        detector = HMMRegimeDetector()

        # Bull market
        result_bull = detector.detect(trending_prices)
        assert result_bull['regime'] == 'bull'

        # Bear market
        mock_model.predict.return_value = np.array([0])  # Bear
        mock_model.score_samples.return_value = (np.array([-1.0]), np.array([[0.8, 0.1, 0.1]]))
        result_bear = detector.detect(bear_market_prices)
        assert result_bear['regime'] == 'bear'


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_large_dataset(self, mock_hmm, detector):
        """Test with large dataset."""
        np.random.seed(42)
        large_prices = np.random.lognormal(4.6, 0.02, 5000).tolist()

        mock_model = MagicMock()
        mock_hmm.return_value = mock_model

        # Should complete without timing out
        result = detector.fit(large_prices)
        assert isinstance(result, bool)

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_high_volatility_prices(self, mock_hmm, detector):
        """Test with high volatility price data."""
        np.random.seed(42)
        base_price = 100.0
        high_vol_returns = np.random.normal(0, 0.1, 200)  # 10% daily volatility
        prices = [base_price]
        for ret in high_vol_returns:
            prices.append(prices[-1] * (1 + ret))

        mock_model = MagicMock()
        mock_hmm.return_value = mock_model

        # Should handle high volatility data
        result = detector.detect(prices)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in HMM detector."""

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_fit_with_exception(self, mock_hmm, detector, sample_prices):
        """Test fit when HMM raises an exception."""
        mock_hmm.side_effect = ValueError("Test error")

        result = detector.fit(sample_prices)

        assert result is False

    @patch('app.engines.context_engine.regime_detectors.hmm_regime_detector.hmm.GaussianHMM')
    def test_detect_with_exception(self, mock_hmm, detector):
        """Test detect when model operations raise exception."""
        mock_model = MagicMock()
        mock_model.predict.side_effect = ValueError("Test error")
        mock_hmm.return_value = mock_model

        prices = [100.0] * 100

        result = detector.detect(prices)

        assert result['regime'] == 'unknown'
        assert result['confidence'] == 0.0
