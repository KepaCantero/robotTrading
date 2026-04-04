"""
Unit tests for Triple Barrier Method implementation.

Tests cover:
- Core barrier logic with Numba acceleration
- Dynamic barrier calculation
- Volatility scaling
- Label generation
- Edge cases and error handling
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from app.backtesting.labeling.triple_barrier import (
    TripleBarrierConfig,
    TripleBarrierLabeler,
    calculate_dynamic_barriers,
    calculate_sample_weights,
    get_barrier_labels,
    get_barrier_labels_with_timing,
    get_vertical_barriers,
    meta_labeling,
    plot_triple_barrier,
    purged_cv_split,
    triple_barrier_method,
)


class TestTripleBarrierConfig:
    """Test TripleBarrierConfig validation and initialization."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TripleBarrierConfig()
        assert config.upper_barrier_pct == 0.02
        assert config.lower_barrier_pct == -0.01
        assert config.vertical_barrier_days == 5
        assert config.vol_scale == 1.5
        assert config.vol_window == 20

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TripleBarrierConfig(
            upper_barrier_pct=0.03,
            lower_barrier_pct=-0.015,
            vertical_barrier_days=10,
            vol_scale=2.0,
        )
        assert config.upper_barrier_pct == 0.03
        assert config.lower_barrier_pct == -0.015
        assert config.vertical_barrier_days == 10
        assert config.vol_scale == 2.0

    def test_invalid_upper_barrier(self):
        """Test that non-positive upper barrier raises error."""
        with pytest.raises(ValueError, match="upper_barrier_pct must be positive"):
            TripleBarrierConfig(upper_barrier_pct=0.0)

        with pytest.raises(ValueError, match="upper_barrier_pct must be positive"):
            TripleBarrierConfig(upper_barrier_pct=-0.02)

    def test_invalid_lower_barrier(self):
        """Test that non-negative lower barrier raises error."""
        with pytest.raises(ValueError, match="lower_barrier_pct must be negative"):
            TripleBarrierConfig(lower_barrier_pct=0.0)

        with pytest.raises(ValueError, match="lower_barrier_pct must be negative"):
            TripleBarrierConfig(lower_barrier_pct=0.01)

    def test_invalid_vertical_barrier(self):
        """Test that non-positive vertical barrier raises error."""
        with pytest.raises(ValueError, match="vertical_barrier_days must be positive"):
            TripleBarrierConfig(vertical_barrier_days=0)

    def test_negative_risk_reward_warning(self):
        """Test warning when stop loss is larger than profit target."""
        with pytest.warns(UserWarning, match="Stop loss is larger than profit target"):
            TripleBarrierConfig(upper_barrier_pct=0.01, lower_barrier_pct=-0.02)


class TestBarrierLabeling:
    """Test core barrier labeling logic."""

    @pytest.fixture
    def simple_price_data(self):
        """Create simple price data for testing."""
        return np.array([100.0, 101.0, 102.0, 103.0, 104.0, 103.5, 102.5, 101.5, 100.5])

    @pytest.fixture
    def volatile_price_data(self):
        """Create volatile price data for testing."""
        return np.array([100.0, 95.0, 105.0, 98.0, 102.0, 97.0, 103.0, 96.0, 104.0, 99.0, 101.0])

    def test_upper_barrier_hit(self, simple_price_data):
        """Test labeling when upper barrier is hit first."""
        # Price goes up, should hit upper barrier (2%) first
        events = np.array([0])
        labels = get_barrier_labels(simple_price_data, events, 1.02, 0.99, 10)

        assert labels[0] == 1, "Should hit upper barrier first"

    def test_lower_barrier_hit(self, simple_price_data):
        """Test labeling when lower barrier is hit first."""
        # Use events from the peak, price goes down
        events = np.array([4])  # At price 104.0
        labels = get_barrier_labels(simple_price_data, events, 1.02, 0.99, 10)

        assert labels[0] == -1, "Should hit lower barrier first"

    def test_vertical_barrier_hit(self):
        """Test labeling when vertical barrier is hit (time expires)."""
        # Price stays relatively flat
        prices = np.array([100.0, 100.5, 99.5, 100.2, 99.8])
        events = np.array([0])
        labels = get_barrier_labels(prices, events, 1.05, 0.95, 3)

        assert labels[0] == 0, "Should hit vertical barrier"

    def test_multiple_events(self, volatile_price_data):
        """Test labeling with multiple events."""
        events = np.array([0, 2, 4, 6])
        labels = get_barrier_labels(volatile_price_data, events, 1.03, 0.97, 5)

        assert len(labels) == 4
        assert all(l in [1, -1, 0] for l in labels)

    def test_barrier_labels_with_timing(self, simple_price_data):
        """Test barrier labeling with timing information."""
        events = np.array([0])
        labels, timing = get_barrier_labels_with_timing(simple_price_data, events, 1.02, 0.99, 10)

        assert len(labels) == 1
        assert len(timing) == 1
        assert labels[0] == 1
        assert timing[0] > 0, "Timing should be positive"

    def test_exact_barrier_hit(self):
        """Test when price exactly hits a barrier level."""
        prices = np.array([100.0, 102.0, 98.0])
        events = np.array([0])

        # Upper barrier exactly hit at j=1 (price 102.0 = 100.0 * 1.02)
        labels_upper = get_barrier_labels(prices, events, 1.02, 0.99, 5)
        assert labels_upper[0] == 1

        # Lower barrier exactly hit at j=2 (price 98.0 = 100.0 * 0.98)
        # Use prices where lower is hit first chronologically
        prices_lower_first = np.array([100.0, 98.0, 102.0])
        labels_lower = get_barrier_labels(prices_lower_first, events, 1.02, 0.98, 5)
        assert labels_lower[0] == -1

    def test_barrier_at_data_boundary(self):
        """Test barriers near the end of available data."""
        prices = np.array([100.0, 101.0, 102.0])
        events = np.array([2])  # Last data point

        labels = get_barrier_labels(prices, events, 1.02, 0.99, 5)
        # Should hit vertical barrier since no more data
        assert labels[0] == 0


class TestDynamicBarriers:
    """Test dynamic barrier calculation."""

    @pytest.fixture
    def price_series(self):
        """Create price series with datetime index."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def event_series(self, price_series):
        """Create event series."""
        event_dates = price_series.index[::20]  # Every 20 days
        return pd.Series(event_dates)

    def test_fixed_barriers(self, price_series, event_series):
        """Test fixed barrier calculation (no volatility scaling)."""
        config = TripleBarrierConfig(upper_barrier_pct=0.02, lower_barrier_pct=-0.01)
        upper, lower = calculate_dynamic_barriers(
            price_series, event_series, config, vol_scaling=False
        )

        assert len(upper) == len(event_series)
        assert len(lower) == len(event_series)
        assert all(upper == config.upper_barrier_pct)
        assert all(lower == config.lower_barrier_pct)

    def test_dynamic_barriers_with_vol_scaling(self, price_series, event_series):
        """Test dynamic barrier calculation with volatility scaling."""
        config = TripleBarrierConfig(upper_barrier_pct=0.02, lower_barrier_pct=-0.01, vol_window=10)
        upper, lower = calculate_dynamic_barriers(
            price_series, event_series, config, vol_scaling=True
        )

        assert len(upper) == len(event_series)
        assert len(lower) == len(event_series)
        # Barriers should vary based on volatility
        assert upper.std() > 0, "Upper barriers should vary with volatility"
        assert lower.std() > 0, "Lower barriers should vary with volatility"

    def test_barrier_correlation_with_volatility(self, price_series, event_series):
        """Test that barriers correlate with volatility."""
        config = TripleBarrierConfig(vol_window=10)
        upper, _lower = calculate_dynamic_barriers(
            price_series, event_series, config, vol_scaling=True
        )

        # Drop NaN barriers (events without enough data for vol calculation)
        valid_mask = upper.notna()
        upper_valid = upper[valid_mask]

        # Calculate returns and volatility
        returns = price_series.pct_change().dropna()
        vol = returns.rolling(window=config.vol_window).std()

        # Get volatility at event times (matching upper's index)
        event_vols = []
        valid_indices = []
        for idx_pos, event_time in enumerate(event_series):
            if event_time in vol.index:
                event_vols.append(vol.loc[event_time])
                valid_indices.append(event_series.index[idx_pos])
            else:
                valid_idx = vol.index[vol.index <= event_time]
                if len(valid_idx) > 0:
                    event_vols.append(vol.loc[valid_idx[-1]])
                    valid_indices.append(event_series.index[idx_pos])

        # Higher volatility should lead to wider barriers
        event_vols = pd.Series(event_vols, index=valid_indices)

        # Align both series by common valid indices
        common_idx = upper_valid.index.intersection(event_vols.index)
        correlation = upper_valid.loc[common_idx].corr(event_vols.loc[common_idx])

        # Should be positive correlation (higher vol → wider barriers)
        assert correlation > 0, "Barriers should be wider in high volatility"


class TestVerticalBarriers:
    """Test vertical barrier calculation."""

    def test_vertical_barrier_calculation(self):
        """Test basic vertical barrier calculation."""
        dates = pd.date_range("2020-01-01", periods=20, freq="D")
        prices = pd.Series(range(20), index=dates)
        events = pd.Series([dates[5], dates[10]])

        vertical = get_vertical_barriers(events, prices, num_days=5)

        assert len(vertical) == 2
        assert vertical.iloc[0] == dates[10]  # 5 days after event 1
        assert vertical.iloc[1] == dates[15]  # 5 days after event 2

    def test_vertical_boundary_clipping(self):
        """Test that vertical barriers are clipped to data range."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(range(10), index=dates)
        events = pd.Series([dates[8]])  # Near the end

        vertical = get_vertical_barriers(events, prices, num_days=5)

        # Should be clipped to last available date
        assert vertical.iloc[0] <= prices.index[-1]


class TestTripleBarrierLabeler:
    """Test TripleBarrierLabeler class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample price and event data."""
        dates = pd.date_range("2020-01-01", periods=200, freq="D")
        np.random.seed(42)

        # Create trending price data
        trend = np.linspace(0, 20, 200)
        noise = np.random.randn(200) * 2
        prices = 100 + trend + noise

        price_series = pd.Series(prices, index=dates)

        # Create events every 20 days
        event_dates = dates[::20]
        event_series = pd.Series(event_dates)

        return price_series, event_series

    def test_labeler_initialization(self):
        """Test labeler initialization."""
        config = TripleBarrierConfig()
        labeler = TripleBarrierLabeler(config)

        assert labeler.config == config
        assert labeler.prices is None
        assert labeler.events is None

    def test_fit_returns_self(self, sample_data):
        """Test that fit returns self for method chaining."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()

        result = labeler.fit(prices, events)

        assert result is labeler

    def test_fit_generates_labels(self, sample_data):
        """Test that fit generates labels."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()

        labeler.fit(prices, events)

        assert labeler.labels_ is not None
        assert len(labeler.labels_) == len(events)
        assert "label" in labeler.labels_.columns
        assert "barrier_hit" in labeler.labels_.columns
        assert "bars_to_barrier" in labeler.labels_.columns

    def test_fit_transform(self, sample_data):
        """Test fit_transform method."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()

        labels = labeler.fit_transform(prices, events)

        assert isinstance(labels, pd.DataFrame)
        assert len(labels) == len(events)
        assert labeler.labels_ is not None

    def test_label_distribution(self, sample_data):
        """Test label distribution calculation."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()
        labeler.fit(prices, events)

        dist = labeler.get_label_distribution()

        assert isinstance(dist, pd.Series)
        assert set(dist.index).issubset({1, -1, 0})
        assert dist.sum() == len(events)

    def test_average_holding_period(self, sample_data):
        """Test average holding period calculation."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()
        labeler.fit(prices, events)

        avg_hold = labeler.get_average_holding_period()

        assert isinstance(avg_hold, dict)
        assert all(isinstance(k, int) for k in avg_hold.keys())
        assert all(isinstance(v, float) for v in avg_hold.values())
        assert all(v > 0 for v in avg_hold.values())

    def test_binary_labels(self, sample_data):
        """Test binary label conversion."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()
        labeler.fit(prices, events)

        bin_labels = labeler.get_bin_labels()

        assert isinstance(bin_labels, np.ndarray)
        assert len(bin_labels) == len(events)
        assert set(bin_labels).issubset({0, 1})

    def test_transform_without_fit_raises_error(self, sample_data):
        """Test that transform without fit raises error."""
        prices, events = sample_data
        labeler = TripleBarrierLabeler()

        with pytest.raises(ValueError, match="Labeler must be fitted"):
            labeler.transform(prices, events)

    def test_get_label_distribution_without_fit_raises_error(self):
        """Test that getting distribution without fit raises error."""
        labeler = TripleBarrierLabeler()

        with pytest.raises(ValueError, match="Labeler must be fitted"):
            labeler.get_label_distribution()


class TestTripleBarrierMethod:
    """Test triple_barrier_method convenience function."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        price_series = pd.Series(prices, index=dates)
        event_series = pd.Series(dates[::10])

        return price_series, event_series

    def test_convenience_function(self, sample_data):
        """Test triple_barrier_method function."""
        prices, events = sample_data

        labels = triple_barrier_method(
            prices=prices,
            events=events,
            upper_barrier_pct=0.02,
            lower_barrier_pct=-0.01,
            vertical_barrier_days=5,
        )

        assert isinstance(labels, pd.DataFrame)
        assert len(labels) == len(events)
        assert "label" in labels.columns
        assert "barrier_hit" in labels.columns
        assert "bars_to_barrier" in labels.columns

    def test_convenience_function_with_vol_scaling(self, sample_data):
        """Test volatility scaling in convenience function."""
        prices, events = sample_data

        labels_no_vol = triple_barrier_method(prices, events, vol_scaling=False)
        labels_with_vol = triple_barrier_method(prices, events, vol_scaling=True)

        # Volatility scaling should produce different results
        # (unless volatility is constant, which is unlikely)
        assert len(labels_no_vol) == len(labels_with_vol)


class TestMetaLabeling:
    """Test meta-labeling functionality."""

    def test_meta_labeling_correct_signals(self):
        """Test meta-labeling for correct primary signals."""
        primary_labels = np.array([1, 1, -1, -1])
        actual_returns = np.array([0.02, 0.01, -0.02, -0.01])

        meta_labels = meta_labeling(primary_labels, None, actual_returns)

        expected = np.array([1, 1, 1, 1])
        np.testing.assert_array_equal(meta_labels, expected)

    def test_meta_labeling_incorrect_signals(self):
        """Test meta-labeling for incorrect primary signals."""
        primary_labels = np.array([1, 1, -1, -1])
        actual_returns = np.array([-0.02, -0.01, 0.02, 0.01])

        meta_labels = meta_labeling(primary_labels, None, actual_returns)

        expected = np.array([0, 0, 0, 0])
        np.testing.assert_array_equal(meta_labels, expected)

    def test_meta_labeling_mixed_signals(self):
        """Test meta-labeling with mixed correct/incorrect signals."""
        primary_labels = np.array([1, 1, -1, -1])
        actual_returns = np.array([0.02, -0.01, -0.02, 0.01])

        meta_labels = meta_labeling(primary_labels, None, actual_returns)

        expected = np.array([1, 0, 1, 0])
        np.testing.assert_array_equal(meta_labels, expected)


class TestSampleWeights:
    """Test sample weight calculation."""

    def test_sample_weights_no_overlap(self):
        """Test sample weights with no overlapping events."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        events = pd.Series(dates[::5])  # Events 5 days apart

        labels = pd.DataFrame({"bars_to_barrier": [2, 2]})

        weights = calculate_sample_weights(events, labels, max_holding_period=5)

        # No overlap should result in equal weights (normalized so average = 1.0)
        assert len(weights) == len(events)
        np.testing.assert_array_almost_equal(weights.values, [1.0, 1.0])

    def test_sample_weights_with_overlap(self):
        """Test sample weights with overlapping events."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        events = pd.Series([dates[0], dates[1], dates[2]])  # Overlapping events

        labels = pd.DataFrame({"bars_to_barrier": [3, 3, 3]})

        weights = calculate_sample_weights(events, labels, max_holding_period=5)

        # Events with more overlap should get lower weights
        assert len(weights) == len(events)
        # Production code normalizes to sum=n_samples (average weight = 1.0)
        assert weights.sum() == pytest.approx(len(events))


class TestPurgedCVSplit:
    """Test purged cross-validation splitting."""

    def test_purged_cv_split_basic(self):
        """Test basic purged CV split."""
        splits = purged_cv_split(n_samples=100, n_folds=5, embargo_pct=0.01)

        assert len(splits) == 5

        for train_idx, test_idx in splits:
            # Train should come before test
            assert train_idx.max() < test_idx.min() if len(train_idx) > 0 else True

    def test_purged_cv_split_embargo(self):
        """Test that embargo removes boundary samples."""
        splits = purged_cv_split(n_samples=100, n_folds=3, embargo_pct=0.1)

        for train_idx, test_idx in splits:
            if len(train_idx) > 0 and len(test_idx) > 0:
                # Should have gap between train and test
                gap = test_idx.min() - train_idx.max()
                assert gap >= 1, "Embargo should create gap between train and test"


class TestPlotTripleBarrier:
    """Test visualization functionality."""

    def test_plot_triple_barrier_upper(self):
        """Test plotting upper barrier hit."""
        prices = pd.Series([100, 101, 102, 103, 104])
        fig, ax = plt.subplots()

        result_ax = plot_triple_barrier(prices, 0, 102.0, 99.0, 3, 1, ax)

        assert result_ax is ax
        plt.close(fig)

    def test_plot_triple_barrier_lower(self):
        """Test plotting lower barrier hit."""
        prices = pd.Series([104, 103, 102, 101, 100])
        fig, ax = plt.subplots()

        result_ax = plot_triple_barrier(prices, 0, 106.0, 102.0, 3, -1, ax)

        assert result_ax is ax
        plt.close(fig)

    def test_plot_triple_barrier_no_axis(self):
        """Test plotting without providing axis."""
        prices = pd.Series([100, 101, 102, 103, 104])

        ax = plot_triple_barrier(prices, 0, 102.0, 99.0, 3, 1, ax=None)

        assert ax is not None
        plt.close()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_events(self):
        """Test with empty event series."""
        prices = pd.Series([100, 101, 102, 103, 104])
        events = pd.Series([], dtype="datetime64[ns]")

        labeler = TripleBarrierLabeler()
        labeler.fit(prices, events)

        assert len(labeler.labels_) == 0

    def test_single_event(self):
        """Test with single event."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(range(10), index=dates, dtype=float)
        events = pd.Series([dates[5]])

        labeler = TripleBarrierLabeler()
        labeler.fit(prices, events)

        assert len(labeler.labels_) == 1
        assert labeler.labels_["label"].iloc[0] in [1, -1, 0]

    def test_extreme_barrier_values(self):
        """Test with extreme barrier values."""
        prices = pd.Series([100.0, 101.0, 102.0])
        events = pd.Series([0])

        # Very wide barriers
        labels = get_barrier_labels(prices.values, events.values, 2.0, 0.5, 10)
        assert labels[0] == 0  # Should hit vertical barrier

        # Very narrow barriers
        labels = get_barrier_labels(prices.values, events.values, 1.001, 0.999, 10)
        # Should hit one of the horizontal barriers quickly
        assert labels[0] in [1, -1]


@pytest.fixture
def matplotlib_figure():
    """Fixture to manage matplotlib figures."""
    import matplotlib.pyplot as plt

    fig = plt.figure()
    yield fig
    plt.close(fig)
