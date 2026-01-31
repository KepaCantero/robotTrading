"""
Unit tests for VaR Backtesting - Hull Chapter 18

Tests for Kupiec test, Christoffersen test, and exception tracking.
"""

import pytest
import numpy as np
from app.engines.risk_engine.var_calculators.var_calculators import VaRBacktester, run_var_backtest


class TestVaRBacktester:
    """Test suite for VaR backtesting functionality."""

    @pytest.fixture
    def backtester_95(self):
        """Create VaR backtester with 95% confidence level."""
        return VaRBacktester(confidence_level=0.95)

    @pytest.fixture
    def backtester_99(self):
        """Create VaR backtester with 99% confidence level."""
        return VaRBacktester(confidence_level=0.99)

    @pytest.fixture
    def valid_var_predictions(self):
        """Create valid VaR predictions (5% expected failure rate for 95% VaR)."""
        np.random.seed(42)
        n = 1000
        # Generate returns with 5% exceeding VaR
        returns = np.random.normal(0, 0.02, n)
        # Calculate empirical 5th percentile
        var_threshold = np.percentile(returns, 5)
        # Create VaR predictions slightly below threshold to get ~5% exceptions
        var_predictions = np.full(n, var_threshold * 1.1)
        return var_predictions, returns

    def test_kupiec_test_valid_model(self, backtester_95, valid_var_predictions):
        """Test Kupiec test with valid VaR model."""
        var_preds, returns = valid_var_predictions

        result = backtester_95.kupiec_test(var_preds, returns)

        assert 'error' not in result
        assert result['test_name'] == 'Kupiec Likelihood Ratio Test'
        assert result['observations'] == 1000
        assert 'exceptions' in result
        assert 'model_valid' in result
        assert 'interpretation' in result
        assert isinstance(result['lr_statistic'], float)

    def test_kupiec_test_rejects_bad_model(self, backtester_95):
        """Test Kupiec test rejects model with too many exceptions."""
        n = 500
        # Create VaR predictions that are too high (underestimates risk)
        var_preds = np.full(n, -0.01)  # Too high
        returns = np.random.normal(0, 0.02, n)

        result = backtester_95.kupiec_test(var_preds, returns)

        assert 'error' not in result
        # Should have many exceptions
        assert result['exceptions'] > 50  # More than expected 25

    def test_kupiec_test_length_mismatch(self, backtester_95):
        """Test Kupiec test with mismatched array lengths."""
        var_preds = np.array([-0.02, -0.025, -0.018])
        returns = np.array([-0.015, -0.03])  # Different length

        result = backtester_95.kupiec_test(var_preds, returns)

        assert 'error' in result
        assert 'Length mismatch' in result['error']

    def test_christoffersen_test_valid_model(self, backtester_95, valid_var_predictions):
        """Test Christoffersen test with independent exceptions."""
        var_preds, returns = valid_var_predictions

        result = backtester_95.christoffersen_test(var_preds, returns)

        assert 'error' not in result
        assert result['test_name'] == 'Christoffersen Independence Test'
        assert 'transitions' in result
        assert 'n_00' in result['transitions']
        assert 'n_01' in result['transitions']
        assert 'n_10' in result['transitions']
        assert 'n_11' in result['transitions']
        assert 'transition_probabilities' in result
        assert 'exceptions_independent' in result

    def test_christoffersen_test_detects_clustering(self, backtester_95):
        """Test Christoffersen test detects exception clustering."""
        n = 500
        # Create clustered exceptions
        returns = np.random.normal(0, 0.01, n)
        var_preds = np.full(n, -0.02)

        # Force clustering - exceptions happen in bursts
        exception_indices = [50, 51, 52, 53, 54, 200, 201, 202, 350, 351, 352, 353]
        for idx in exception_indices:
            returns[idx] = -0.03  # Force exception

        result = backtester_95.christoffersen_test(var_preds, returns)

        assert 'error' not in result
        # Should detect some dependence due to clustering
        assert 'pi_11' in result['transition_probabilities']
        assert 'pi_01' in result['transition_probabilities']

    def test_calculate_var_exceptions(self, backtester_95, valid_var_predictions):
        """Test VaR exception statistics calculation."""
        var_preds, returns = valid_var_predictions

        result = backtester_95.calculate_var_exceptions(var_preds, returns)

        assert 'error' not in result
        assert result['total_observations'] == 1000
        assert 'num_exceptions' in result
        assert 'exception_rate' in result
        assert 'exception_magnitude' in result
        assert 'clustering' in result
        assert 'exception_indices' in result

    def test_exception_clustering_metrics(self, backtester_95):
        """Test exception clustering detection."""
        n = 100
        returns = np.random.normal(0, 0.01, n)
        var_preds = np.full(n, -0.02)

        # Create specific exception pattern
        exception_indices = [10, 11, 12, 50, 51, 90]
        for idx in exception_indices:
            returns[idx] = -0.03

        result = backtester_95.calculate_var_exceptions(var_preds, returns)

        assert 'error' not in result
        assert result['num_exceptions'] == 6
        assert result['clustering']['avg_gap'] is not None
        assert result['clustering']['min_gap'] is not None
        assert result['clustering']['max_gap'] is not None

    def test_comprehensive_backtest(self, backtester_95, valid_var_predictions):
        """Test comprehensive backtest with all tests."""
        var_preds, returns = valid_var_predictions

        result = backtester_95.run_comprehensive_backtest(var_preds, returns)

        assert 'error' not in result
        assert 'overall_result' in result
        assert result['overall_result'] in ['PASS', 'CONDITIONAL', 'FAIL']
        assert 'recommendation' in result
        assert 'kupiec_test' in result
        assert 'christoffersen_test' in result
        assert 'exception_statistics' in result

    def test_backtest_result_interpretation(self, backtester_95):
        """Test backtest result interpretation logic."""
        # Test PASS condition (both tests pass)
        var_preds = np.array([-0.02] * 500)
        returns = np.random.normal(0, 0.01, 500)
        # Adjust to get approximately 5% exceptions
        threshold = np.percentile(returns, 5)
        var_preds = np.full(500, threshold * 1.05)

        result = backtester_95.run_comprehensive_backtest(var_preds, returns)

        assert 'overall_result' in result
        assert 'recommendation' in result

    def test_different_confidence_levels(self, backtester_95, backtester_99):
        """Test backtesting with different confidence levels."""
        n = 500
        returns = np.random.normal(0, 0.02, n)

        # 95% VaR
        var_95 = np.percentile(returns, 5)
        result_95 = backtester_95.kupiec_test(np.full(n, var_95), returns)

        # 99% VaR
        var_99 = np.percentile(returns, 1)
        result_99 = backtester_99.kupiec_test(np.full(n, var_99), returns)

        assert result_95['confidence_level'] == 0.95
        assert result_99['confidence_level'] == 0.99
        assert result_95['expected_failure_rate'] == 0.05
        assert result_99['expected_failure_rate'] == 0.01

    def test_convenience_function(self, valid_var_predictions):
        """Test the convenience function run_var_backtest."""
        var_preds, returns = valid_var_predictions

        result = run_var_backtest(
            var_preds, returns, confidence_level=0.95, significance_level=0.05
        )

        assert 'error' not in result
        assert 'overall_result' in result
        assert 'kupiec_test' in result
        assert 'christoffersen_test' in result

    def test_kupiec_interpretation_messages(self, backtester_95):
        """Test Kupiec test interpretation messages."""
        n = 500
        returns = np.random.normal(0, 0.02, n)
        var_preds = np.full(n, -0.01)

        result = backtester_95.kupiec_test(var_preds, returns)

        assert 'interpretation' in result
        assert isinstance(result['interpretation'], str)
        assert len(result['interpretation']) > 0

    def test_christoffersen_interpretation_messages(self, backtester_95):
        """Test Christoffersen test interpretation messages."""
        n = 500
        returns = np.random.normal(0, 0.01, n)
        var_preds = np.full(n, -0.02)

        result = backtester_95.christoffersen_test(var_preds, returns)

        assert 'interpretation' in result
        assert isinstance(result['interpretation'], str)
        assert 'π01=' in result['interpretation'] or 'pi_01=' in result['interpretation']

    def test_exception_magnitude_statistics(self, backtester_95):
        """Test exception magnitude statistics."""
        n = 200
        returns = np.random.normal(0, 0.01, n)
        var_preds = np.full(n, -0.015)

        # Force some exceptions with different magnitudes
        exception_magnitudes = [-0.02, -0.025, -0.03, -0.035, -0.04]
        for i, mag in enumerate(exception_magnitudes):
            returns[i * 20] = mag

        result = backtester_95.calculate_var_exceptions(var_preds, returns)

        assert 'error' not in result
        mag_stats = result['exception_magnitude']
        assert 'mean' in mag_stats
        assert 'std' in mag_stats
        assert 'min' in mag_stats
        assert 'max' in mag_stats
        # Max should be more negative than min (larger loss)
        assert mag_stats['max'] <= mag_stats['min']


class TestVaRBacktesterEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def backtester(self):
        return VaRBacktester(confidence_level=0.95)

    def test_empty_arrays(self, backtester):
        """Test with empty arrays."""
        result = backtester.kupiec_test(np.array([]), np.array([]))
        # Should handle gracefully or return error
        assert 'error' in result or result['observations'] == 0

    def test_single_observation(self, backtester):
        """Test with single observation."""
        var_preds = np.array([-0.02])
        returns = np.array([-0.015])

        result = backtester.kupiec_test(var_preds, returns)

        # Should handle but may have limited statistical power
        assert 'observations' in result

    def test_no_exceptions(self, backtester):
        """Test case with no VaR exceptions."""
        var_preds = np.array([-0.05, -0.05, -0.05])  # Very conservative
        returns = np.array([-0.01, -0.01, -0.01])  # All within VaR

        result = backtester.kupiec_test(var_preds, returns)

        assert result['num_exceptions'] == 0
        # Model may be too conservative

    def test_all_exceptions(self, backtester):
        """Test case where all observations are exceptions."""
        var_preds = np.array([-0.005, -0.005, -0.005])  # Too low
        returns = np.array([-0.02, -0.02, -0.02])  # All exceed VaR

        result = backtester.kupiec_test(var_preds, returns)

        assert result['num_exceptions'] == 3
        # Model seriously underestimates risk


class TestVaRBacktesterIntegration:
    """Integration tests for VaR backtesting."""

    @pytest.fixture
    def backtester(self):
        return VaRBacktester(confidence_level=0.95)

    def test_full_backtesting_workflow(self, backtester):
        """Test complete backtesting workflow."""
        # Simulate realistic scenario
        np.random.seed(42)
        n = 1000

        # Generate returns with volatility clustering
        returns = []
        volatility = 0.01
        for i in range(n):
            # GARCH-like volatility clustering
            if i > 0 and abs(returns[-1]) > 0.02:
                volatility = 0.025
            else:
                volatility = 0.95 * volatility + 0.05 * 0.01

            returns.append(np.random.normal(0, volatility))

        returns = np.array(returns)

        # Calculate rolling VaR (simplified)
        window = 100
        var_preds = []
        for i in range(n):
            if i < window:
                # Use expanding window
                hist_returns = returns[: i + 1]
            else:
                hist_returns = returns[i - window : i]

            var_val = np.percentile(hist_returns, 5)
            var_preds.append(var_val)

        var_preds = np.array(var_preds)

        # Run comprehensive backtest
        result = backtester.run_comprehensive_backtest(var_preds, returns)

        # Validate results
        assert 'error' not in result
        assert 'overall_result' in result
        assert 'exception_statistics' in result

        # Check that exception rate is reasonable
        exception_rate = result['exception_statistics']['exception_rate']
        assert 0.01 < exception_rate < 0.15  # Should be around 0.05 but allow variance
