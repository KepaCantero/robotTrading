"""
Tests for data splitting and multiple testing correction functionality.
"""

import pytest
from datetime import datetime, timedelta

from app.backtesting.data_split import (
    DataSplit,
    MultipleTestingCorrector,
    TrainValTestSplitter,
    validate_out_of_sample_performance,
)


class MockQuote:
    """Mock quote for testing."""

    def __init__(self, timestamp, close=100.0):
        self.timestamp = timestamp
        self.close = close
        self.symbol = "TEST"


class TestDataSplit:
    """Test data splitting functionality."""

    def test_default_split_config(self):
        """Test default data split configuration."""
        split = DataSplit()
        assert split.train_pct == 0.70
        assert split.val_pct == 0.15
        assert split.test_pct == 0.15
        assert split.min_train_days == 252

    def test_custom_split_config(self):
        """Test custom data split configuration."""
        split = DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2)
        assert split.train_pct == 0.6
        assert split.val_pct == 0.2
        assert split.test_pct == 0.2

    def test_invalid_split_config(self):
        """Test that invalid split configuration raises error."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            DataSplit(train_pct=0.5, val_pct=0.3, test_pct=0.3)  # Sum = 1.1


class TestTrainValTestSplitter:
    """Test train/validation/test splitter."""

    def test_split_data_basic(self):
        """Test basic data splitting."""
        splitter = TrainValTestSplitter()

        # Create 100 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(100)
        ]

        train, val, test = splitter.split_data(quotes)

        # Check split ratios
        assert len(train) == 70  # 70%
        assert len(val) == 15  # 15%
        assert len(test) == 15  # 15%

    def test_split_data_with_date_filter(self):
        """Test data splitting with date filtering."""
        splitter = TrainValTestSplitter()

        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(100)
        ]

        # Filter to only include first 50 days
        train, val, test = splitter.split_data(
            quotes,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 10)  # ~40 days
        )

        # Should have fewer quotes
        total_filtered = len(train) + len(val) + len(test)
        assert total_filtered <= 50

    def test_split_data_empty(self):
        """Test that empty data raises error."""
        splitter = TrainValTestSplitter()

        with pytest.raises(ValueError, match="Market data is empty"):
            splitter.split_data([])

    def test_split_preserves_temporal_order(self):
        """Test that split preserves temporal order."""
        splitter = TrainValTestSplitter()

        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(100)
        ]

        train, val, test = splitter.split_data(quotes)

        # Check that all timestamps in train are before val
        if train and val:
            assert train[-1].timestamp <= val[0].timestamp

        # Check that all timestamps in val are before test
        if val and test:
            assert val[-1].timestamp <= test[0].timestamp


class TestMultipleTestingCorrector:
    """Test multiple testing correction."""

    def test_bonferroni_correction_basic(self):
        """Test basic Bonferroni correction."""
        corrector = MultipleTestingCorrector(num_tests=10, base_confidence=0.95)
        adjusted = corrector.bonferroni_correction()

        # Bonferroni: alpha / n
        # 0.95 / 10 = 0.095
        expected = 0.095
        assert abs(adjusted - expected) < 0.001

    def test_bonferroni_correction_single_test(self):
        """Test Bonferroni correction with single test."""
        corrector = MultipleTestingCorrector(num_tests=1, base_confidence=0.95)
        adjusted = corrector.bonferroni_correction()

        # Should be unchanged with single test
        assert adjusted == 0.95

    def test_bonferroni_correction_many_tests(self):
        """Test Bonferroni correction with many tests."""
        corrector = MultipleTestingCorrector(num_tests=100, base_confidence=0.95)
        adjusted = corrector.bonferroni_correction()

        # 0.95 / 100 = 0.0095
        expected = 0.0095
        assert abs(adjusted - expected) < 0.0001

    def test_benjamini_hochberg_correction(self):
        """Test Benjamini-Hochberg correction."""
        corrector = MultipleTestingCorrector(num_tests=5, base_confidence=0.95)

        # Mock p-values
        p_values = [0.01, 0.03, 0.05, 0.10, 0.20]

        significant = corrector.benjamini_hochberg_correction(p_values)

        # Should identify which tests are significant
        assert isinstance(significant, list)
        assert len(significant) == 5
        assert all(isinstance(s, bool) for s in significant)

        # First few should be significant
        assert significant[0]  # p=0.01 is significant

    def test_holm_bonferroni_correction(self):
        """Test Holm-Bonferroni correction."""
        corrector = MultipleTestingCorrector(num_tests=5, base_confidence=0.95)

        p_values = [0.01, 0.03, 0.05, 0.10, 0.20]

        significant = corrector.holm_bonferroni_correction(p_values)

        assert isinstance(significant, list)
        assert len(significant) == 5
        assert all(isinstance(s, bool) for s in significant)

    def test_correction_empty_p_values(self):
        """Test correction with empty p-values."""
        corrector = MultipleTestingCorrector(num_tests=5, base_confidence=0.95)

        significant = corrector.benjamini_hochberg_correction([])
        assert significant == []

        significant = corrector.holm_bonferroni_correction([])
        assert significant == []


class TestWalkForwardSplit:
    """Test walk-forward splitting functionality."""

    def test_walk_forward_split_basic(self):
        """Test basic walk-forward split."""
        splitter = TrainValTestSplitter()

        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        # Use smaller window for testing
        splits = splitter.walk_forward_split(quotes, window_size=100, step_size=50)

        # Should create multiple splits
        assert len(splits) > 0

        # Each split should have train, val, test
        for train, val, test in splits:
            assert len(train) > 0
            assert len(val) > 0
            assert len(test) > 0
            assert len(train) + len(val) + len(test) == 100

    def test_walk_forward_split_multiple_windows(self):
        """Test that walk-forward creates multiple rolling windows."""
        splitter = TrainValTestSplitter()

        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        # Use default window_size=252, step_size=63
        splits = splitter.walk_forward_split(quotes)

        # Should create at least 2 windows
        assert len(splits) >= 2

    def test_walk_forward_split_insufficient_data(self):
        """Test walk-forward with insufficient data returns empty list."""
        splitter = TrainValTestSplitter()

        # Create only 500 bars (less than 3 * 252 = 756 minimum)
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(500)
        ]

        splits = splitter.walk_forward_split(quotes)

        # Should return empty list due to insufficient data
        assert len(splits) == 0

    def test_walk_forward_split_temporal_order(self):
        """Test that walk-forward windows maintain temporal order."""
        splitter = TrainValTestSplitter()

        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i), close=i)
            for i in range(1000)
        ]

        splits = splitter.walk_forward_split(quotes, window_size=100, step_size=100)

        # Check that windows are sequential
        for i in range(len(splits) - 1):
            current_window_test_end = splits[i][2][-1].close
            next_window_train_start = splits[i + 1][0][0].close

            # Windows should be sequential
            assert next_window_train_start > current_window_test_end


class TestValidateOutOfSamplePerformance:
    """Test out-of-sample performance validation."""

    def test_validation_pass(self):
        """Test validation passes with good performance."""
        result = validate_out_of_sample_performance(
            train_sharpe=2.0,
            val_sharpe=1.8,
            test_sharpe=1.6,
            min_performance_ratio=0.7,
        )

        assert result

    def test_validation_fail_degradation(self):
        """Test validation fails with severe degradation."""
        result = validate_out_of_sample_performance(
            train_sharpe=2.0,
            val_sharpe=1.8,
            test_sharpe=0.9,  # 50% of val (below 0.7 threshold)
            min_performance_ratio=0.7,
        )

        assert not result

    def test_validation_fail_sign_flip(self):
        """Test validation fails with sign flip."""
        result = validate_out_of_sample_performance(
            train_sharpe=2.0,
            val_sharpe=1.8,
            test_sharpe=-0.5,  # Negative when val is positive
            min_performance_ratio=0.7,
        )

        assert not result

    def test_validation_edge_case(self):
        """Test validation at threshold boundary."""
        result = validate_out_of_sample_performance(
            train_sharpe=2.0,
            val_sharpe=1.0,
            test_sharpe=0.7,  # Exactly at threshold
            min_performance_ratio=0.7,
        )

        assert result

    def test_validation_with_zero_val_sharpe(self):
        """Test validation when val Sharpe is zero."""
        result = validate_out_of_sample_performance(
            train_sharpe=1.0,
            val_sharpe=0.0,
            test_sharpe=0.0,
            min_performance_ratio=0.7,
        )

        # Should pass (0 >= 0 * 0.7)
        assert result

    def test_validation_negative_all_sharpes(self):
        """Test validation when all Sharpe ratios are negative."""
        result = validate_out_of_sample_performance(
            train_sharpe=-1.0,
            val_sharpe=-0.8,
            test_sharpe=-0.6,
            min_performance_ratio=0.7,
        )

        # Test (-0.6) >= val (-0.8) * 0.7 = -0.56
        # -0.6 < -0.56, so fails degradation check
        assert not result

    def test_validation_custom_ratio(self):
        """Test validation with custom performance ratio."""
        result = validate_out_of_sample_performance(
            train_sharpe=2.0,
            val_sharpe=2.0,
            test_sharpe=0.8,  # 40% of val
            min_performance_ratio=0.5,
        )

        # 0.8 < 2.0 * 0.5 = 1.0, so should fail
        assert not result


class TestIntegrationScenarios:
    """Integration tests combining multiple components."""

    def test_full_workflow_split_and_validate(self):
        """Test complete workflow: split data and validate performance."""
        splitter = TrainValTestSplitter()

        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        # Split data
        train, val, test = splitter.split_data(quotes)

        # Simulate Sharpe ratios
        train_sharpe = 1.5
        val_sharpe = 1.3
        test_sharpe = 1.1

        # Validate OOS performance
        result = validate_out_of_sample_performance(
            train_sharpe, val_sharpe, test_sharpe
        )

        assert result is True
        assert len(train) == 700
        assert len(val) == 150
        assert len(test) == 150

    def test_overfitting_detection_scenario(self):
        """Test scenario that should detect overfitting."""
        splitter = TrainValTestSplitter()

        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        train, val, test = splitter.split_data(quotes)

        # Simulate overfitting: high train/val, poor test
        train_sharpe = 3.0
        val_sharpe = 2.5
        test_sharpe = 0.5  # Much worse than val

        # Should detect overfitting
        result = validate_out_of_sample_performance(
            train_sharpe, val_sharpe, test_sharpe, min_performance_ratio=0.7
        )

        assert result is False  # Overfitting detected

    def test_walk_forward_with_multiple_testing_correction(self):
        """Test walk-forward validation with multiple testing correction."""
        splitter = TrainValTestSplitter()

        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        # Perform walk-forward split
        splits = splitter.walk_forward_split(quotes, window_size=200, step_size=100)

        # Apply multiple testing correction for all splits
        corrector = MultipleTestingCorrector(num_tests=len(splits))
        adjusted_confidence = corrector.bonferroni_correction()

        # Should have at least 2 splits
        assert len(splits) >= 2
        # Adjusted confidence should be lower than original
        assert adjusted_confidence < 0.95

    def test_different_split_ratios(self):
        """Test that different split ratios all work correctly."""
        # Create 1000 mock quotes
        base_time = datetime(2024, 1, 1)
        quotes = [
            MockQuote(timestamp=base_time + timedelta(days=i))
            for i in range(1000)
        ]

        # Test various split configurations
        configs = [
            DataSplit(0.6, 0.2, 0.2),
            DataSplit(0.7, 0.15, 0.15),
            DataSplit(0.8, 0.1, 0.1),
        ]

        for config in configs:
            splitter = TrainValTestSplitter(split_config=config)
            train, val, test = splitter.split_data(quotes)

            total = len(train) + len(val) + len(test)
            assert total == 1000

            # Check approximate ratios (within 1% tolerance)
            assert abs(len(train) / total - config.train_pct) < 0.01
            assert abs(len(val) / total - config.val_pct) < 0.01
            assert abs(len(test) / total - config.test_pct) < 0.01
