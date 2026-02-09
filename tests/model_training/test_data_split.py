"""
Test suite for app.backtesting.data_split

Addresses TST-005: Test coverage for data splitting utilities
"""

from datetime import datetime, timedelta
from typing import NamedTuple

import pytest

from app.backtesting.data_split import (
    DataSplit,
    MultipleTestingCorrector,
    TrainValTestSplitter,
    validate_out_of_sample_performance,
)


class MockBar(NamedTuple):
    """Mock market data bar for testing."""

    timestamp: datetime
    close: float = 100.0


class TestDataSplitImport:
    """Test module imports."""

    def test_import_data_split(self):
        """Test that DataSplit can be imported."""
        from app.backtesting.data_split import DataSplit

        assert DataSplit is not None

    def test_import_train_val_test_splitter(self):
        """Test that TrainValTestSplitter can be imported."""
        from app.backtesting.data_split import TrainValTestSplitter

        assert TrainValTestSplitter is not None

    def test_import_multiple_testing_corrector(self):
        """Test that MultipleTestingCorrector can be imported."""
        from app.backtesting.data_split import MultipleTestingCorrector

        assert MultipleTestingCorrector is not None

    def test_import_validate_oos_performance(self):
        """Test that validate_out_of_sample_performance can be imported."""
        from app.backtesting.data_split import validate_out_of_sample_performance

        assert validate_out_of_sample_performance is not None


class TestDataSplitInitialization:
    """Test DataSplit configuration."""

    def test_default_initialization(self):
        """Test DataSplit with default values."""
        split = DataSplit()
        assert split.train_pct == 0.70
        assert split.val_pct == 0.15
        assert split.test_pct == 0.15

    def test_custom_initialization(self):
        """Test DataSplit with custom values."""
        split = DataSplit(train_pct=0.60, val_pct=0.20, test_pct=0.20)
        assert split.train_pct == 0.60
        assert split.val_pct == 0.20
        assert split.test_pct == 0.20

    def test_invalid_percentages(self):
        """Test that invalid percentages raise ValueError."""
        with pytest.raises(ValueError):
            DataSplit(train_pct=0.5, val_pct=0.3, test_pct=0.3)  # Sum > 1.0


class TestTrainValTestSplitterInitialization:
    """Test TrainValTestSplitter initialization."""

    def test_default_initialization(self):
        """Test TrainValTestSplitter with default config."""
        splitter = TrainValTestSplitter()
        assert splitter.config.train_pct == 0.70

    def test_custom_config_initialization(self):
        """Test TrainValTestSplitter with custom config."""
        config = DataSplit(train_pct=0.60, val_pct=0.20, test_pct=0.20)
        splitter = TrainValTestSplitter(split_config=config)
        assert splitter.config.train_pct == 0.60


class TestBasicSplit:
    """Test basic train/val/test splitting."""

    def test_split_data(self):
        """Test basic data splitting."""
        splitter = TrainValTestSplitter()
        bars = self._generate_bars(1000)

        train, val, test = splitter.split_data(bars)

        assert len(train) == 700
        assert len(val) == 150
        assert len(test) == 150

    def test_split_preserves_temporal_order(self):
        """Test that splitting preserves temporal order."""
        splitter = TrainValTestSplitter()
        bars = self._generate_bars(100)

        train, val, test = splitter.split_data(bars)

        # Check that timestamps are in order
        assert train[0].timestamp < train[-1].timestamp
        assert val[0].timestamp < val[-1].timestamp
        assert test[0].timestamp < test[-1].timestamp

        # Check that train ends before val starts
        assert train[-1].timestamp < val[0].timestamp
        # Check that val ends before test starts
        assert val[-1].timestamp < test[0].timestamp

    def test_split_empty_data(self):
        """Test that empty data raises ValueError."""
        splitter = TrainValTestSplitter()
        with pytest.raises(ValueError):
            splitter.split_data([])

    def test_split_with_date_filter(self):
        """Test splitting with date filtering."""
        splitter = TrainValTestSplitter()
        bars = self._generate_bars(100)

        start_date = bars[10].timestamp
        end_date = bars[80].timestamp

        train, val, test = splitter.split_data(bars, start_date=start_date, end_date=end_date)

        # All data should be within date range
        for bar in train + val + test:
            assert start_date <= bar.timestamp <= end_date

    def _generate_bars(self, count: int) -> list:
        """Generate mock bars for testing."""
        start = datetime(2024, 1, 1)
        return [MockBar(timestamp=start + timedelta(days=i)) for i in range(count)]


class TestWalkForwardSplit:
    """Test walk-forward splitting."""

    def test_walk_forward_split(self):
        """Test walk-forward splitting."""
        splitter = TrainValTestSplitter()
        bars = self._generate_bars(1000)

        splits = splitter.walk_forward_split(bars, window_size=252, step_size=63)

        assert len(splits) > 0
        for train, val, test in splits:
            assert len(train) > 0
            assert len(val) > 0
            assert len(test) > 0

    def test_walk_forward_insufficient_data(self):
        """Test walk-forward with insufficient data."""
        splitter = TrainValTestSplitter()
        bars = self._generate_bars(100)  # Less than 3 * window_size

        splits = splitter.walk_forward_split(bars, window_size=252, step_size=63)

        # Should return empty list or very few splits
        assert isinstance(splits, list)


class TestMultipleTestingCorrector:
    """Test multiple testing correction."""

    def test_bonferroni_correction(self):
        """Test Bonferroni correction."""
        corrector = MultipleTestingCorrector(num_tests=10, base_confidence=0.95)
        adjusted = corrector.bonferroni_correction()
        assert adjusted == pytest.approx(0.095)

    def test_benjamini_hochberg_correction(self):
        """Test Benjamini-Hochberg correction."""
        corrector = MultipleTestingCorrector(num_tests=5, base_confidence=0.95)
        p_values = [0.01, 0.03, 0.05, 0.10, 0.20]

        significant = corrector.benjamini_hochberg_correction(p_values)

        assert isinstance(significant, list)
        assert len(significant) == 5
        assert all(isinstance(s, bool) for s in significant)

    def test_holm_bonferroni_correction(self):
        """Test Holm-Bonferroni correction."""
        corrector = MultipleTestingCorrector(num_tests=5, base_confidence=0.95)
        p_values = [0.01, 0.03, 0.05, 0.10, 0.20]

        significant = corrector.holm_bonferroni_correction(p_values)

        assert isinstance(significant, list)
        assert len(significant) == 5
        assert all(isinstance(s, bool) for s in significant)


class TestOutOfSampleValidation:
    """Test out-of-sample performance validation."""

    def test_validate_oos_performance_pass(self):
        """Test OOS validation passes when test is acceptable."""
        result = validate_out_of_sample_performance(
            train_sharpe=1.5, val_sharpe=1.2, test_sharpe=1.0, min_performance_ratio=0.7
        )
        assert result is True

    def test_validate_oos_performance_fail_degradation(self):
        """Test OOS validation fails with degradation."""
        result = validate_out_of_sample_performance(
            train_sharpe=1.5,
            val_sharpe=1.2,
            test_sharpe=0.5,  # Less than 0.7 * 1.2 = 0.84
            min_performance_ratio=0.7,
        )
        assert result is False

    def test_validate_oos_performance_fail_sign_flip(self):
        """Test OOS validation fails with sign flip."""
        result = validate_out_of_sample_performance(
            train_sharpe=1.5,
            val_sharpe=1.2,
            test_sharpe=-0.5,  # Negative while val is positive
            min_performance_ratio=0.7,
        )
        assert result is False

    def _generate_bars(self, count: int) -> list:
        """Generate mock bars for testing."""
        start = datetime(2024, 1, 1)
        return [MockBar(timestamp=start + timedelta(days=i)) for i in range(count)]
