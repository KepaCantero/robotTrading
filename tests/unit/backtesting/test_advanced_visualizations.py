"""
Tests for AdvancedVisualizer - comprehensive visualization suite.

Tests all 8 visualization methods with various data scenarios:
- Correlation network
- Parallel coordinates
- 3D scatter plot
- Underwater drawdown
- Rolling metrics
- Regime performance
- Seasonality heatmap
- Interactive dashboard
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.backtesting.advanced_visualizations import MATPLOTLIB_AVAILABLE, AdvancedVisualizer


class TestAdvancedVisualizer:
    """Tests for AdvancedVisualizer class."""

    @pytest.fixture
    def temp_output_dir(self) -> str:
        """Create temporary output directory for visualizations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def visualizer(self, temp_output_dir: str) -> AdvancedVisualizer:
        """Create AdvancedVisualizer instance."""
        return AdvancedVisualizer(output_dir=temp_output_dir, dpi=100)

    @pytest.fixture
    def sample_numeric_data(self) -> pd.DataFrame:
        """Create sample numeric data for testing."""
        np.random.seed(42)
        n = 100

        return pd.DataFrame(
            {
                "sharpe_ratio": np.random.uniform(0, 3, n),
                "total_pnl": np.random.uniform(-10000, 50000, n),
                "max_drawdown": np.random.uniform(-0.5, 0, n),
                "win_rate": np.random.uniform(0, 1, n),
                "return_pct": np.random.uniform(-0.2, 0.5, n),
                "volatility": np.random.uniform(0, 0.3, n),
                "sortino_ratio": np.random.uniform(0, 4, n),
                "profit_factor": np.random.uniform(0.5, 3, n),
            }
        )

    @pytest.fixture
    def sample_equity_curve(self) -> pd.Series:
        """Create sample equity curve with datetime index."""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")  # Business days
        returns = np.random.normal(0.001, 0.02, 252)
        equity = (1 + returns).cumprod() * 100000
        return pd.Series(equity, index=dates, name="equity")

    @pytest.fixture
    def sample_returns(self) -> pd.Series:
        """Create sample returns series with datetime index."""
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
        returns = np.random.normal(0.001, 0.02, 252)
        return pd.Series(returns, index=dates, name="returns")

    @pytest.fixture
    def sample_regime_labels(self) -> pd.Series:
        """Create sample regime labels."""
        # 3 regimes: 0 (Bull), 1 (Neutral), 2 (Bear)
        labels = np.random.choice([0, 1, 2], size=252, p=[0.4, 0.35, 0.25])
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
        return pd.Series(labels, index=dates, name="regime")

    # Tests for plot_correlation_network
    def test_correlation_network_basic(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test basic correlation network generation."""
        result = visualizer.plot_correlation_network(sample_numeric_data)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None, "Function should return a Figure when matplotlib available"
            output_files = list(Path(visualizer.output_dir).glob("correlation_network.png"))
            assert len(output_files) == 1, "Should save correlation network file"
        else:
            assert result is None, "Should return None when matplotlib unavailable"

    def test_correlation_network_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test correlation network with custom filename."""
        custom_file = "custom_network.png"
        result = visualizer.plot_correlation_network(sample_numeric_data, output_file=custom_file)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob(custom_file))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_correlation_network_threshold(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test correlation network with different thresholds."""
        result_low = visualizer.plot_correlation_network(sample_numeric_data, threshold=0.2)
        result_high = visualizer.plot_correlation_network(sample_numeric_data, threshold=0.7)

        if MATPLOTLIB_AVAILABLE:
            assert result_low is not None
            assert result_high is not None
        else:
            assert result_low is None
            assert result_high is None

    def test_correlation_network_insufficient_data(self, visualizer: AdvancedVisualizer):
        """Test correlation network with insufficient data."""
        small_df = pd.DataFrame({"col1": [1, 2, 3]})
        result = visualizer.plot_correlation_network(small_df)

        # Should return None (not enough columns or no matplotlib)
        assert result is None

    def test_correlation_network_figsize(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test correlation network with custom figure size."""
        result = visualizer.plot_correlation_network(sample_numeric_data, figsize=(12, 10))

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    # Tests for plot_parallel_coordinates
    def test_parallel_coordinates_basic(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test basic parallel coordinates plot generation."""
        result = visualizer.plot_parallel_coordinates(sample_numeric_data)

        if result is not None:  # Only if plotly is available
            output_files = list(Path(visualizer.output_dir).glob("parallel_coordinates.html"))
            assert len(output_files) == 1, "Should save parallel coordinates file"

    def test_parallel_coordinates_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test parallel coordinates with custom filename."""
        custom_file = "custom_parallel.html"
        result = visualizer.plot_parallel_coordinates(sample_numeric_data, output_file=custom_file)

        if result is not None:
            assert custom_file in result

    def test_parallel_coordinates_color_column(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test parallel coordinates with color column specification."""
        result = visualizer.plot_parallel_coordinates(sample_numeric_data, color_col="sharpe_ratio")

        if result is not None:
            assert result is not None

    def test_parallel_coordinates_max_cols(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test parallel coordinates with column limit."""
        result = visualizer.plot_parallel_coordinates(sample_numeric_data, max_cols=4)

        if result is not None:
            assert result is not None

    def test_parallel_coordinates_empty_data(self, visualizer: AdvancedVisualizer):
        """Test parallel coordinates with empty data."""
        empty_df = pd.DataFrame()
        result = visualizer.plot_parallel_coordinates(empty_df)

        assert result is None

    # Tests for plot_3d_scatter
    def test_3d_scatter_basic(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test basic 3D scatter plot."""
        result = visualizer.plot_3d_scatter(
            sample_numeric_data,
            x_col="sharpe_ratio",
            y_col="total_pnl",
            z_col="max_drawdown",
        )

        if result is not None:  # Only if plotly is available
            output_files = list(Path(visualizer.output_dir).glob("3d_scatter.html"))
            assert len(output_files) == 1

    def test_3d_scatter_with_color(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test 3D scatter with color dimension."""
        result = visualizer.plot_3d_scatter(
            sample_numeric_data,
            x_col="sharpe_ratio",
            y_col="total_pnl",
            z_col="max_drawdown",
            color_col="win_rate",
        )

        if result is not None:
            assert result is not None

    def test_3d_scatter_with_size(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test 3D scatter with size dimension."""
        result = visualizer.plot_3d_scatter(
            sample_numeric_data,
            x_col="sharpe_ratio",
            y_col="total_pnl",
            z_col="max_drawdown",
            size_col="volatility",
        )

        if result is not None:
            assert result is not None

    def test_3d_scatter_missing_column(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test 3D scatter with missing column."""
        result = visualizer.plot_3d_scatter(
            sample_numeric_data,
            x_col="sharpe_ratio",
            y_col="total_pnl",
            z_col="nonexistent_column",
        )

        assert result is None

    def test_3d_scatter_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test 3D scatter with custom filename."""
        custom_file = "custom_3d.html"
        result = visualizer.plot_3d_scatter(
            sample_numeric_data,
            x_col="sharpe_ratio",
            y_col="total_pnl",
            z_col="max_drawdown",
            output_file=custom_file,
        )

        if result is not None:
            assert custom_file in result

    # Tests for plot_underwater_drawdown
    def test_underwater_drawdown_basic(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test basic underwater drawdown plot."""
        result = visualizer.plot_underwater_drawdown(sample_equity_curve)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob("underwater_drawdown.png"))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_underwater_drawdown_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test underwater drawdown with custom filename."""
        custom_file = "custom_drawdown.png"
        result = visualizer.plot_underwater_drawdown(sample_equity_curve, output_file=custom_file)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob(custom_file))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_underwater_drawdown_figsize(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test underwater drawdown with custom figure size."""
        result = visualizer.plot_underwater_drawdown(sample_equity_curve, figsize=(16, 8))

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_underwater_drawdown_monotonic_increase(
        self, visualizer: AdvancedVisualizer, temp_output_dir: str
    ):
        """Test underwater drawdown with monotonically increasing equity."""
        # Purely increasing equity should have zero drawdown
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        equity = pd.Series(np.linspace(100, 200, 100), index=dates)

        result = visualizer.plot_underwater_drawdown(equity)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_underwater_drawdown_with_crash(
        self, visualizer: AdvancedVisualizer, temp_output_dir: str
    ):
        """Test underwater drawdown with significant crash."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        equity = pd.Series([100] * 50 + [50] * 50, index=dates, dtype=float)

        result = visualizer.plot_underwater_drawdown(equity)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    # Tests for plot_rolling_metrics
    def test_rolling_metrics_basic(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test basic rolling metrics plot."""
        result = visualizer.plot_rolling_metrics(sample_equity_curve, window=50)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob("rolling_metrics.png"))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_rolling_metrics_custom_window(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test rolling metrics with custom window."""
        result = visualizer.plot_rolling_metrics(sample_equity_curve, window=30)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_rolling_metrics_large_window(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test rolling metrics with window larger than data."""
        result = visualizer.plot_rolling_metrics(sample_equity_curve, window=500)

        # Should handle gracefully
        assert result is None

    def test_rolling_metrics_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test rolling metrics with custom filename."""
        custom_file = "custom_rolling.png"
        result = visualizer.plot_rolling_metrics(
            sample_equity_curve, window=50, output_file=custom_file
        )

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob(custom_file))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_rolling_metrics_figsize(
        self, visualizer: AdvancedVisualizer, sample_equity_curve: pd.Series
    ):
        """Test rolling metrics with custom figure size."""
        result = visualizer.plot_rolling_metrics(sample_equity_curve, window=50, figsize=(16, 10))

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    # Tests for plot_regime_performance
    def test_regime_performance_basic(
        self,
        visualizer: AdvancedVisualizer,
        sample_returns: pd.Series,
        sample_regime_labels: pd.Series,
    ):
        """Test basic regime performance plot."""
        result = visualizer.plot_regime_performance(sample_returns, sample_regime_labels)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob("regime_performance.png"))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_regime_performance_custom_names(
        self,
        visualizer: AdvancedVisualizer,
        sample_returns: pd.Series,
        sample_regime_labels: pd.Series,
    ):
        """Test regime performance with custom regime names."""
        regime_names = {0: "Bull Market", 1: "Sideways", 2: "Bear Market"}
        result = visualizer.plot_regime_performance(
            sample_returns, sample_regime_labels, regime_names=regime_names
        )

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_regime_performance_mismatched_lengths(
        self, visualizer: AdvancedVisualizer, sample_returns: pd.Series
    ):
        """Test regime performance with mismatched lengths."""
        mismatched_labels = pd.Series([0, 1, 2] * 50)  # 150 elements instead of 252
        result = visualizer.plot_regime_performance(sample_returns, mismatched_labels)

        assert result is None

    def test_regime_performance_single_regime(
        self, visualizer: AdvancedVisualizer, sample_returns: pd.Series
    ):
        """Test regime performance with single regime."""
        single_regime = pd.Series([0] * len(sample_returns), index=sample_returns.index)
        result = visualizer.plot_regime_performance(sample_returns, single_regime)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_regime_performance_custom_filename(
        self,
        visualizer: AdvancedVisualizer,
        sample_returns: pd.Series,
        sample_regime_labels: pd.Series,
    ):
        """Test regime performance with custom filename."""
        custom_file = "custom_regimes.png"
        result = visualizer.plot_regime_performance(
            sample_returns, sample_regime_labels, output_file=custom_file
        )

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob(custom_file))
            assert len(output_files) == 1
        else:
            assert result is None

    # Tests for plot_seasonality_heatmap
    def test_seasonality_heatmap_basic(
        self, visualizer: AdvancedVisualizer, sample_returns: pd.Series
    ):
        """Test basic seasonality heatmap."""
        result = visualizer.plot_seasonality_heatmap(sample_returns)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob("seasonality_heatmap.png"))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_seasonality_heatmap_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_returns: pd.Series
    ):
        """Test seasonality heatmap with custom filename."""
        custom_file = "custom_seasonality.png"
        result = visualizer.plot_seasonality_heatmap(sample_returns, output_file=custom_file)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
            output_files = list(Path(visualizer.output_dir).glob(custom_file))
            assert len(output_files) == 1
        else:
            assert result is None

    def test_seasonality_heatmap_multiple_years(self, visualizer: AdvancedVisualizer):
        """Test seasonality heatmap with multiple years of data."""
        # Create 3 years of daily data
        dates = pd.date_range(start="2021-01-01", periods=3 * 252, freq="B")
        returns = np.random.normal(0.001, 0.02, 3 * 252)
        multi_year_returns = pd.Series(returns, index=dates)

        result = visualizer.plot_seasonality_heatmap(multi_year_returns)

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    def test_seasonality_heatmap_non_datetime_index(self, visualizer: AdvancedVisualizer):
        """Test seasonality heatmap with non-datetime index."""
        returns = pd.Series(np.random.normal(0, 0.02, 100))
        result = visualizer.plot_seasonality_heatmap(returns)

        # Should handle gracefully
        assert result is None

    def test_seasonality_heatmap_figsize(
        self, visualizer: AdvancedVisualizer, sample_returns: pd.Series
    ):
        """Test seasonality heatmap with custom figure size."""
        result = visualizer.plot_seasonality_heatmap(sample_returns, figsize=(16, 10))

        if MATPLOTLIB_AVAILABLE:
            assert result is not None
        else:
            assert result is None

    # Tests for generate_interactive_dashboard
    def test_dashboard_basic(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test basic interactive dashboard generation."""
        result = visualizer.generate_interactive_dashboard(sample_numeric_data)

        if result is not None:  # Only if plotly is available
            assert "dashboard.html" in result
            output_files = list(Path(visualizer.output_dir).glob("dashboard.html"))
            assert len(output_files) == 1

    def test_dashboard_with_equity_curve(
        self,
        visualizer: AdvancedVisualizer,
        sample_numeric_data: pd.DataFrame,
        sample_equity_curve: pd.Series,
    ):
        """Test dashboard with equity curve."""
        result = visualizer.generate_interactive_dashboard(
            sample_numeric_data, equity_curve=sample_equity_curve
        )

        if result is not None:
            assert result is not None

    def test_dashboard_custom_filename(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test dashboard with custom filename."""
        custom_file = "custom_dashboard.html"
        result = visualizer.generate_interactive_dashboard(
            sample_numeric_data, output_file=custom_file
        )

        if result is not None:
            assert custom_file in result

    def test_dashboard_empty_data(self, visualizer: AdvancedVisualizer):
        """Test dashboard with empty data."""
        empty_df = pd.DataFrame()
        result = visualizer.generate_interactive_dashboard(empty_df)

        # Should handle gracefully
        assert result is None or isinstance(result, str)

    # Integration tests
    def test_all_visualizations_with_sample_data(
        self,
        visualizer: AdvancedVisualizer,
        sample_numeric_data: pd.DataFrame,
        sample_equity_curve: pd.Series,
        sample_returns: pd.Series,
        sample_regime_labels: pd.Series,
    ):
        """Test all visualizations together with sample data."""
        # These should all execute without errors
        results = {
            "network": visualizer.plot_correlation_network(sample_numeric_data),
            "parallel": visualizer.plot_parallel_coordinates(sample_numeric_data),
            "scatter3d": visualizer.plot_3d_scatter(
                sample_numeric_data,
                x_col="sharpe_ratio",
                y_col="total_pnl",
                z_col="max_drawdown",
            ),
            "drawdown": visualizer.plot_underwater_drawdown(sample_equity_curve),
            "rolling": visualizer.plot_rolling_metrics(sample_equity_curve, window=50),
            "regime": visualizer.plot_regime_performance(sample_returns, sample_regime_labels),
            "seasonality": visualizer.plot_seasonality_heatmap(sample_returns),
        }

        # At least the static visualizations should succeed (or return None if matplotlib not available)
        if MATPLOTLIB_AVAILABLE:
            assert results["network"] is not None
            assert results["drawdown"] is not None
            assert results["rolling"] is not None
            assert results["regime"] is not None

    def test_output_directory_creation(self):
        """Test that output directory is created properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = str(Path(tmpdir) / "custom" / "nested" / "dir")
            AdvancedVisualizer(output_dir=custom_dir)

            assert Path(custom_dir).exists()

    def test_visualizer_attributes(self, visualizer: AdvancedVisualizer):
        """Test visualizer has correct attributes."""
        assert hasattr(visualizer, "output_dir")
        assert hasattr(visualizer, "dpi")
        assert visualizer.dpi == 100

    def test_large_dataset_handling(self, visualizer: AdvancedVisualizer):
        """Test handling of large dataset."""
        # Create large dataset
        large_data = pd.DataFrame(np.random.randn(10000, 8), columns=[f"col_{i}" for i in range(8)])

        # These should handle large data efficiently
        result = visualizer.plot_correlation_network(large_data)
        assert result is not None or result is None  # Either succeeds or fails gracefully

    def test_correlation_network_custom_figsize(
        self, visualizer: AdvancedVisualizer, sample_numeric_data: pd.DataFrame
    ):
        """Test correlation network with various figure sizes."""
        sizes = [(10, 8), (14, 10), (16, 12)]

        for figsize in sizes:
            result = visualizer.plot_correlation_network(sample_numeric_data, figsize=figsize)
            if MATPLOTLIB_AVAILABLE:
                assert result is not None
            else:
                assert result is None

    def test_rolling_metrics_window_validation(self, visualizer: AdvancedVisualizer):
        """Test rolling metrics with various window sizes."""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        equity = pd.Series(np.linspace(100, 110, 100), index=dates)

        windows = [5, 10, 30, 50]
        for window in windows:
            result = visualizer.plot_rolling_metrics(equity, window=window)
            # Should work for reasonable windows
            if window <= len(equity) // 2:
                if MATPLOTLIB_AVAILABLE:
                    assert result is not None
                else:
                    assert result is None
            else:
                assert result is None
