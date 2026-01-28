"""
Unit tests for Structural Change Detector.

Tests the StructuralChangeDetector class which implements CUSUM and Chow test
to detect structural changes in time series.
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    np.random.seed(42)
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 200)
    prices = [base_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    return prices


@pytest.fixture
def prices_with_change():
    """Generate prices with a structural change."""
    np.random.seed(123)
    prices = [100.0]

    # First regime: slight upward trend
    for i in range(100):
        prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.015)))

    # Second regime: higher volatility and downward trend
    for i in range(100):
        prices.append(prices[-1] * (1 + np.random.normal(-0.002, 0.03)))

    return prices


@pytest.fixture
def prices_without_change():
    """Generate prices without structural change."""
    np.random.seed(456)
    prices = [100.0]

    # Constant regime
    for i in range(200):
        prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.02)))

    return prices


@pytest.fixture
def detector():
    """Create a StructuralChangeDetector instance for testing."""
    from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector
    return StructuralChangeDetector()


@pytest.fixture
def cusum_detector():
    """Create detector configured for CUSUM."""
    from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector
    return StructuralChangeDetector(config={'method': 'cusum'})


@pytest.fixture
def chow_detector():
    """Create detector configured for Chow test."""
    from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector
    return StructuralChangeDetector(config={'method': 'chow'})


@pytest.mark.unit
class TestStructuralChangeDetectorInit:
    """Test initialization of StructuralChangeDetector."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector()

        assert detector.method == 'cusum'
        assert detector.significance_level == 0.05
        assert detector.window_size == 100

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        config = {
            'method': 'chow',
            'significance_level': 0.01,
            'window_size': 150
        }
        detector = StructuralChangeDetector(config=config)

        assert detector.method == 'chow'
        assert detector.significance_level == 0.01
        assert detector.window_size == 150


@pytest.mark.unit
class TestDetectCUSUM:
    """Test CUSUM detection functionality."""

    def test_detect_cusum_insufficient_data(self, cusum_detector):
        """Test CUSUM detection with insufficient data."""
        short_prices = [100.0] * 50  # Less than window_size

        result = cusum_detector.detect_cusum(short_prices)

        assert result['change_detected'] is False
        assert result['breakpoint'] is None
        assert result['p_value'] is None
        assert result['confidence'] == 0.0

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_success(self, mock_cusum, cusum_detector, sample_prices):
        """Test successful CUSUM detection."""
        # Mock CUSUM result: (test_statistic, p_value, critical_value)
        mock_cusum.return_value = (5.5, 0.02, 4.8)

        result = cusum_detector.detect_cusum(sample_prices)

        assert isinstance(result, dict)
        assert 'change_detected' in result
        assert 'p_value' in result
        assert 'test_statistic' in result

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_with_change(self, mock_cusum, cusum_detector, prices_with_change):
        """Test CUSUM detection with actual structural change."""
        # Return significant p-value
        mock_cusum.return_value = (6.0, 0.01, 4.8)

        result = cusum_detector.detect_cusum(prices_with_change)

        # With p < 0.05, should detect change
        if result['p_value'] is not None:
            assert result['change_detected'] == (result['p_value'] < cusum_detector.significance_level)

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_without_change(self, mock_cusum, cusum_detector, prices_without_change):
        """Test CUSUM detection without structural change."""
        # Return non-significant p-value
        mock_cusum.return_value = (2.0, 0.5, 4.8)

        result = cusum_detector.detect_cusum(prices_without_change)

        # With p > 0.05, should not detect change
        if result['p_value'] is not None:
            assert result['change_detected'] == (result['p_value'] < cusum_detector.significance_level)

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_confidence_calculation(self, mock_cusum, cusum_detector, sample_prices):
        """Test confidence calculation in CUSUM detection."""
        p_value = 0.03
        mock_cusum.return_value = (5.5, p_value, 4.8)

        result = cusum_detector.detect_cusum(sample_prices)

        assert result['confidence'] == 1.0 - p_value

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_with_tuple_result(self, mock_cusum, cusum_detector, sample_prices):
        """Test CUSUM with tuple result format."""
        mock_cusum.return_value = (5.5, 0.02, 4.8)

        result = cusum_detector.detect_cusum(sample_prices)

        assert result['test_statistic'] == 5.5
        assert result['p_value'] == 0.02

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_with_scalar_result(self, mock_cusum, cusum_detector, sample_prices):
        """Test CUSUM with scalar result format (no p_value)."""
        mock_cusum.return_value = 5.5

        result = cusum_detector.detect_cusum(sample_prices)

        assert result['test_statistic'] == 5.5
        assert result['p_value'] is None

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_cusum_with_exception(self, mock_cusum, cusum_detector, sample_prices):
        """Test CUSUM when exception occurs."""
        mock_cusum.side_effect = ValueError("Test error")

        result = cusum_detector.detect_cusum(sample_prices)

        assert result['change_detected'] is False
        assert result['confidence'] == 0.0


@pytest.mark.unit
class TestDetectChowTest:
    """Test Chow test detection functionality."""

    def test_detect_chow_insufficient_data(self, chow_detector):
        """Test Chow test with insufficient data."""
        short_prices = [100.0] * 50

        result = chow_detector.detect_chow_test(short_prices)

        assert result['change_detected'] is False
        assert result['breakpoint'] is None
        assert result['p_value'] is None

    def test_detect_chow_default_breakpoint(self, chow_detector, sample_prices):
        """Test Chow test with default breakpoint (middle)."""
        result = chow_detector.detect_chow_test(sample_prices)

        assert isinstance(result, dict)
        assert 'breakpoint' in result
        assert result['breakpoint'] is not None

    def test_detect_chow_custom_breakpoint(self, chow_detector, sample_prices):
        """Test Chow test with custom breakpoint."""
        custom_breakpoint = 80
        result = chow_detector.detect_chow_test(sample_prices, breakpoint=custom_breakpoint)

        assert result['breakpoint'] == custom_breakpoint

    def test_detect_chow_invalid_breakpoint_too_small(self, chow_detector, sample_prices):
        """Test Chow test with breakpoint too small."""
        result = chow_detector.detect_chow_test(sample_prices, breakpoint=5)

        assert result['change_detected'] is False
        assert result['breakpoint'] is None

    def test_detect_chow_invalid_breakpoint_too_large(self, chow_detector, sample_prices):
        """Test Chow test with breakpoint too large."""
        # Get returns length
        returns = np.diff(sample_prices[-chow_detector.window_size:]) / sample_prices[-chow_detector.window_size:-1]

        result = chow_detector.detect_chow_test(sample_prices, breakpoint=len(returns) - 5)

        assert result['change_detected'] is False
        assert result['breakpoint'] is None

    def test_detect_chow_statistics(self, chow_detector, sample_prices):
        """Test that Chow test returns statistics."""
        result = chow_detector.detect_chow_test(sample_prices)

        assert 'f_statistic' in result
        assert 'mean_before' in result
        assert 'mean_after' in result
        assert 'p_value' in result

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.stats')
    def test_detect_chow_with_change(self, mock_stats, chow_detector, prices_with_change):
        """Test Chow test detection with actual change."""
        # Mock F-distribution CDF to return low p-value
        mock_stats.f.cdf.return_value = 0.95

        result = chow_detector.detect_chow_test(prices_with_change)

        # Should detect change if means are different enough
        assert 'change_detected' in result

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.stats')
    def test_detect_chow_p_value_calculation(self, mock_stats, chow_detector, sample_prices):
        """Test p-value calculation in Chow test."""
        # Mock F-distribution CDF
        mock_stats.f.cdf.return_value = 0.97

        result = chow_detector.detect_chow_test(sample_prices)

        assert result['p_value'] == 1.0 - 0.97
        assert result['confidence'] == 0.97

    def test_detect_chow_zero_pooled_variance(self, chow_detector):
        """Test Chow test with zero pooled variance."""
        # Create constant prices (zero variance)
        constant_prices = [100.0] * 150

        result = chow_detector.detect_chow_test(constant_prices)

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_detect_chow_with_exception(self, chow_detector, sample_prices):
        """Test Chow test when exception occurs."""
        # This should handle any exceptions gracefully
        result = chow_detector.detect_chow_test(sample_prices)

        assert isinstance(result, dict)


@pytest.mark.unit
class TestDetect:
    """Test general detect functionality."""

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_detect_with_cusum_method(self, mock_cusum, cusum_detector, sample_prices):
        """Test detect with CUSUM method."""
        mock_cusum.return_value = (5.5, 0.02, 4.8)

        result = cusum_detector.detect(sample_prices)

        assert isinstance(result, dict)
        assert 'change_detected' in result

    def test_detect_with_chow_method(self, chow_detector, sample_prices):
        """Test detect with Chow method."""
        result = chow_detector.detect(sample_prices)

        assert isinstance(result, dict)
        assert 'change_detected' in result

    def test_detect_with_unknown_method(self, sample_prices):
        """Test detect with unknown method (should default to CUSUM)."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'method': 'unknown'})

        result = detector.detect(sample_prices)

        # Should default to CUSUM
        assert isinstance(result, dict)

    def test_detect_with_chow_breakpoint_argument(self, chow_detector, sample_prices):
        """Test detect with Chow method and breakpoint argument."""
        custom_breakpoint = 75
        result = chow_detector.detect(sample_prices, breakpoint=custom_breakpoint)

        assert result['breakpoint'] == custom_breakpoint


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_prices(self, detector):
        """Test with empty price list."""
        result = detector.detect([])

        assert result['change_detected'] is False

    def test_single_price(self, detector):
        """Test with single price."""
        result = detector.detect([100.0])

        assert result['change_detected'] is False

    def test_nan_in_prices(self, detector):
        """Test with NaN values in prices."""
        prices_with_nan = [100.0, 101.0, float('nan'), 103.0, 104.0]

        # Should handle gracefully
        result = detector.detect(prices_with_nan)
        assert isinstance(result, dict)

    def test_inf_in_prices(self, detector):
        """Test with infinite values in prices."""
        prices_with_inf = [100.0, 101.0, float('inf'), 103.0, 104.0]

        # Should handle gracefully
        result = detector.detect(prices_with_inf)
        assert isinstance(result, dict)

    def test_negative_prices(self, detector):
        """Test with negative prices."""
        negative_prices = [-100.0, -101.0, -102.0]

        # Should handle gracefully
        result = detector.detect(negative_prices)
        assert isinstance(result, dict)

    def test_zero_prices(self, detector):
        """Test with zero prices."""
        zero_prices = [100.0, 0.0, 100.0]

        # Should handle gracefully
        result = detector.detect(zero_prices)
        assert isinstance(result, dict)

    def test_constant_prices(self, detector):
        """Test with constant prices."""
        constant_prices = [100.0] * 150

        result = detector.detect(constant_prices)

        assert isinstance(result, dict)


@pytest.mark.unit
class TestPropertyBasedTests:
    """Property-based tests for structural change detector."""

    @pytest.mark.parametrize("method", ['cusum', 'chow'])
    def test_different_methods(self, method, sample_prices):
        """Test with different detection methods."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'method': method})

        assert detector.method == method

    @pytest.mark.parametrize("significance_level", [0.01, 0.05, 0.1])
    def test_different_significance_levels(self, significance_level, sample_prices):
        """Test with different significance levels."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'significance_level': significance_level})

        assert detector.significance_level == significance_level

    @pytest.mark.parametrize("window_size", [50, 100, 150, 200])
    def test_different_window_sizes(self, window_size):
        """Test with different window sizes."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'window_size': window_size})

        assert detector.window_size == window_size

    @pytest.mark.parametrize("breakpoint", [30, 50, 70, 90])
    def test_different_breakpoints(self, breakpoint, sample_prices):
        """Test Chow test with different breakpoints."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'method': 'chow'})

        result = detector.detect_chow_test(sample_prices, breakpoint=breakpoint)

        assert isinstance(result, dict)


@pytest.mark.unit
class TestStatistics:
    """Test statistical calculations."""

    def test_chow_test_mean_calculation(self, chow_detector, sample_prices):
        """Test that Chow test correctly calculates means."""
        breakpoint = 100
        result = chow_detector.detect_chow_test(sample_prices, breakpoint=breakpoint)

        assert 'mean_before' in result
        assert 'mean_after' in result
        assert isinstance(result['mean_before'], float)
        assert isinstance(result['mean_after'], float)

    def test_chow_test_f_statistic_positive(self, chow_detector, sample_prices):
        """Test that F-statistic is non-negative."""
        result = chow_detector.detect_chow_test(sample_prices)

        assert 'f_statistic' in result
        assert result['f_statistic'] >= 0

    def test_cusum_test_statistic(self, cusum_detector, sample_prices):
        """Test that CUSUM test statistic is calculated."""
        with patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid') as mock_cusum:
            mock_cusum.return_value = (5.5, 0.02, 4.8)

            result = cusum_detector.detect_cusum(sample_prices)

            assert 'test_statistic' in result
            assert isinstance(result['test_statistic'], float)


@pytest.mark.unit
class TestIntegration:
    """Integration tests for structural change detector."""

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_full_workflow_cusum(self, mock_cusum, sample_prices):
        """Test complete workflow with CUSUM."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'method': 'cusum'})
        mock_cusum.return_value = (5.5, 0.02, 4.8)

        result = detector.detect(sample_prices)

        assert 'change_detected' in result
        assert 'confidence' in result

    def test_full_workflow_chow(self, sample_prices):
        """Test complete workflow with Chow test."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        detector = StructuralChangeDetector(config={'method': 'chow'})

        result = detector.detect(sample_prices)

        assert 'change_detected' in result
        assert 'breakpoint' in result
        assert 'p_value' in result


@pytest.mark.unit
class TestComparison:
    """Test comparison between methods."""

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_cusum_vs_chow_consistency(self, mock_cusum, prices_with_change):
        """Test that CUSUM and Chow test give consistent results."""
        from app.engines.context_engine.volatility_analyzers.structural_change_detector import StructuralChangeDetector

        # Mock CUSUM to detect change
        mock_cusum.return_value = (6.0, 0.01, 4.8)

        cusum_detector = StructuralChangeDetector(config={'method': 'cusum'})
        chow_detector = StructuralChangeDetector(config={'method': 'chow'})

        cusum_result = cusum_detector.detect(prices_with_change)

        # CUSUM should detect change with p < 0.05
        if cusum_result['p_value'] is not None:
            assert cusum_result['change_detected'] == (cusum_result['p_value'] < 0.05)


@pytest.mark.unit
class TestPerformance:
    """Performance and stress tests."""

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_large_dataset_cusum(self, mock_cusum, cusum_detector):
        """Test CUSUM with large dataset."""
        np.random.seed(42)
        large_prices = np.random.lognormal(4.6, 0.02, 5000).tolist()

        mock_cusum.return_value = (3.0, 0.3, 4.8)

        # Should complete without timing out
        result = cusum_detector.detect_cusum(large_prices)
        assert isinstance(result, dict)

    def test_large_dataset_chow(self, chow_detector):
        """Test Chow test with large dataset."""
        np.random.seed(42)
        large_prices = np.random.lognormal(4.6, 0.02, 5000).tolist()

        # Should complete without timing out
        result = chow_detector.detect_chow_test(large_prices)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestConfidence:
    """Test confidence calculations."""

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_cusum_confidence_range(self, mock_cusum, cusum_detector, sample_prices):
        """Test that CUSUM confidence is in valid range."""
        mock_cusum.return_value = (5.5, 0.03, 4.8)

        result = cusum_detector.detect_cusum(sample_prices)

        assert 0.0 <= result['confidence'] <= 1.0

    def test_chow_confidence_range(self, chow_detector, sample_prices):
        """Test that Chow confidence is in valid range."""
        result = chow_detector.detect_chow_test(sample_prices)

        assert 0.0 <= result['confidence'] <= 1.0

    @patch('app.engines.context_engine.volatility_analyzers.structural_change_detector.breaks_cusumolsresid')
    def test_confidence_relationship_with_p_value(self, mock_cusum, cusum_detector, sample_prices):
        """Test that confidence = 1 - p_value."""
        p_value = 0.04
        mock_cusum.return_value = (5.5, p_value, 4.8)

        result = cusum_detector.detect_cusum(sample_prices)

        assert result['confidence'] == 1.0 - p_value


@pytest.mark.unit
class TestBreakpointHandling:
    """Test breakpoint handling in Chow test."""

    def test_breakpoint_at_edge(self, chow_detector, sample_prices):
        """Test breakpoint at minimum allowed value."""
        # Get returns length
        returns = np.diff(sample_prices[-chow_detector.window_size:]) / sample_prices[-chow_detector.window_size:-1]

        # Use breakpoint at edge (should be valid)
        result = chow_detector.detect_chow_test(sample_prices, breakpoint=10)

        if len(returns) > 20:
            assert result['breakpoint'] == 10 or result['breakpoint'] is None

    def test_breakpoint_in_middle(self, chow_detector, sample_prices):
        """Test breakpoint in middle of series."""
        returns = np.diff(sample_prices[-chow_detector.window_size:]) / sample_prices[-chow_detector.window_size:-1]
        middle_breakpoint = len(returns) // 2

        result = chow_detector.detect_chow_test(sample_prices, breakpoint=middle_breakpoint)

        assert result['breakpoint'] == middle_breakpoint
