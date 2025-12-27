"""
T9.1 PHASE 4: Tests for AdvancedVisualizationGenerator

Tests cover:
- Plotly chart generation for all 5 chart types
- Data transformation and validation
- Serialization methods (to_json, to_html_div)
- Edge cases (empty data, single point, extreme values)
- Error handling
"""

import json
from datetime import datetime
from decimal import Decimal

import numpy as np

from app.services.reporting_generator.visualization_generator import (
    AdvancedVisualizationGenerator,
    ChartMetadata,
    PlotlyChart,
    get_visualization_generator,
)


class TestPlotlyChart:
    """Tests for PlotlyChart dataclass."""

    def setup_method(self):
        """Setup test fixtures."""
        self.sample_chart = PlotlyChart(
            chart_id="test_chart",
            title="Test Chart",
            chart_type="line",
            data=[{"x": [1, 2, 3], "y": [10, 20, 30], "type": "scatter"}],
            layout={"title": "Test", "xaxis": {"title": "X"}},
            config={"responsive": True},
        )

    def test_plotly_chart_creation(self):
        """Test PlotlyChart creation with all fields."""
        assert self.sample_chart.chart_id == "test_chart"
        assert self.sample_chart.title == "Test Chart"
        assert self.sample_chart.chart_type == "line"
        assert len(self.sample_chart.data) == 1
        assert self.sample_chart.config["responsive"] is True

    def test_plotly_chart_to_json(self):
        """Test conversion to JSON string."""
        json_str = self.sample_chart.to_json()
        assert isinstance(json_str, str)

        # Should be valid JSON
        json_obj = json.loads(json_str)
        assert "data" in json_obj
        assert "layout" in json_obj
        assert "config" in json_obj

    def test_plotly_chart_to_html_div(self):
        """Test conversion to HTML div with embedded script."""
        html = self.sample_chart.to_html_div()
        assert isinstance(html, str)
        assert '<div id="test_chart"' in html
        assert "Plotly.newPlot" in html
        assert "var data_test_chart" in html
        assert "var layout_test_chart" in html
        assert "var config_test_chart" in html

    def test_plotly_chart_html_contains_json(self):
        """Test that HTML contains valid JSON data."""
        html = self.sample_chart.to_html_div()

        # Extract JSON strings from HTML
        assert '"x": [1, 2, 3]' in html
        assert '"y": [10, 20, 30]' in html

    def test_plotly_chart_with_complex_data(self):
        """Test PlotlyChart with multiple traces."""
        complex_chart = PlotlyChart(
            chart_id="multi_trace",
            title="Multi Trace",
            chart_type="line",
            data=[
                {"x": [1, 2, 3], "y": [10, 20, 30], "name": "Trace 1"},
                {"x": [1, 2, 3], "y": [15, 25, 35], "name": "Trace 2"},
            ],
            layout={"title": "Multi"},
            config={"responsive": True},
        )

        json_str = complex_chart.to_json()
        json_obj = json.loads(json_str)
        assert len(json_obj["data"]) == 2


class TestChartMetadata:
    """Tests for ChartMetadata dataclass."""

    def setup_method(self):
        """Setup test fixtures."""
        self.metadata = ChartMetadata(
            chart_id="test_chart",
            chart_type="line",
            title="Test Chart",
            description="A test chart",
            data_points=100,
            generation_time_ms=Decimal("125.5"),
        )

    def test_metadata_creation(self):
        """Test ChartMetadata creation."""
        assert self.metadata.chart_id == "test_chart"
        assert self.metadata.chart_type == "line"
        assert self.metadata.title == "Test Chart"
        assert self.metadata.data_points == 100
        assert self.metadata.generation_time_ms == Decimal("125.5")

    def test_metadata_generation_time_is_decimal(self):
        """Test that generation_time_ms is Decimal type."""
        assert isinstance(self.metadata.generation_time_ms, Decimal)


class TestAdvancedVisualizationGenerator:
    """Tests for AdvancedVisualizationGenerator class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = AdvancedVisualizationGenerator()
        self.sample_returns = [
            Decimal("0.01"),
            Decimal("0.02"),
            Decimal("-0.01"),
            Decimal("0.015"),
            Decimal("0.005"),
        ]
        self.extended_returns = [Decimal(str(0.001 * i)) for i in range(1, 101)]

    def test_generator_initialization(self):
        """Test AdvancedVisualizationGenerator initialization."""
        assert self.generator.charts_generated == 0
        assert "primary" in self.generator.default_colors
        assert "success" in self.generator.default_colors
        assert "danger" in self.generator.default_colors
        assert "warning" in self.generator.default_colors

    def test_default_colors_hex_format(self):
        """Test that default colors are valid hex codes."""
        for color_key, color_val in self.generator.default_colors.items():
            assert color_val.startswith("#")
            assert len(color_val) == 7  # #RRGGBB

    # ========================================================================
    # CUMULATIVE RETURNS CHART TESTS
    # ========================================================================

    def test_generate_cumulative_returns_chart(self):
        """Test basic cumulative returns chart generation."""
        chart = self.generator.generate_cumulative_returns_chart(self.sample_returns)

        assert isinstance(chart, PlotlyChart)
        assert chart.chart_id == "cumulative_returns"
        assert chart.chart_type == "line"
        assert chart.title == "Cumulative Returns"
        assert len(chart.data) == 1
        assert self.generator.charts_generated == 1

    def test_cumulative_returns_chart_with_custom_title(self):
        """Test cumulative returns chart with custom title."""
        custom_title = "My Custom Returns"
        chart = self.generator.generate_cumulative_returns_chart(
            self.sample_returns, title=custom_title
        )

        assert chart.title == custom_title
        assert custom_title in chart.layout["title"]["text"]

    def test_cumulative_returns_chart_with_benchmark(self):
        """Test cumulative returns chart with benchmark returns."""
        benchmark = [
            Decimal("0.008"),
            Decimal("0.009"),
            Decimal("-0.005"),
            Decimal("0.010"),
            Decimal("0.003"),
        ]

        chart = self.generator.generate_cumulative_returns_chart(
            self.sample_returns, benchmark_returns=benchmark
        )

        # Should have 2 traces: strategy + benchmark
        assert len(chart.data) == 2
        assert chart.data[0]["name"] == "Strategy"
        assert chart.data[1]["name"] == "Benchmark"
        assert chart.data[1]["line"]["dash"] == "dash"

    def test_cumulative_returns_chart_data_structure(self):
        """Test cumulative returns chart data structure."""
        chart = self.generator.generate_cumulative_returns_chart(self.extended_returns)

        trace = chart.data[0]
        assert "x" in trace
        assert "y" in trace
        assert trace["type"] == "scatter"
        assert trace["mode"] == "lines"
        assert len(trace["x"]) == len(self.extended_returns)
        assert len(trace["y"]) == len(self.extended_returns)

    def test_cumulative_returns_chart_layout(self):
        """Test cumulative returns chart layout properties."""
        chart = self.generator.generate_cumulative_returns_chart(self.sample_returns)

        layout = chart.layout
        assert "title" in layout
        assert "xaxis" in layout
        assert "yaxis" in layout
        assert layout["xaxis"]["title"] == "Period"
        assert layout["yaxis"]["title"] == "Cumulative Return (%)"
        assert layout["hovermode"] == "x unified"

    def test_cumulative_returns_chart_config(self):
        """Test cumulative returns chart config for interactivity."""
        chart = self.generator.generate_cumulative_returns_chart(self.sample_returns)

        config = chart.config
        assert config["responsive"] is True
        assert config["displayModeBar"] is True
        assert config["displaylogo"] is False
        assert "toImageButtonOptions" in config

    def test_cumulative_returns_single_return(self):
        """Test cumulative returns with single return value."""
        single_return = [Decimal("0.05")]
        chart = self.generator.generate_cumulative_returns_chart(single_return)

        assert len(chart.data[0]["x"]) == 1
        assert len(chart.data[0]["y"]) == 1

    def test_cumulative_returns_negative_returns(self):
        """Test cumulative returns with negative returns."""
        negative_returns = [Decimal("-0.01"), Decimal("-0.02"), Decimal("-0.015")]
        chart = self.generator.generate_cumulative_returns_chart(negative_returns)

        # Cumulative return should be negative
        assert all(y <= 0 for y in chart.data[0]["y"])

    # ========================================================================
    # DRAWDOWN WATERFALL CHART TESTS
    # ========================================================================

    def test_generate_drawdown_waterfall(self):
        """Test drawdown waterfall chart generation."""
        chart = self.generator.generate_drawdown_waterfall(self.sample_returns)

        assert isinstance(chart, PlotlyChart)
        assert chart.chart_id == "drawdown_waterfall"
        assert chart.chart_type == "bar"
        assert chart.title == "Drawdown Analysis"
        assert self.generator.charts_generated == 1

    def test_drawdown_waterfall_with_custom_title(self):
        """Test drawdown waterfall with custom title."""
        custom_title = "My Drawdown Analysis"
        chart = self.generator.generate_drawdown_waterfall(self.sample_returns, title=custom_title)

        assert chart.title == custom_title

    def test_drawdown_waterfall_data_structure(self):
        """Test drawdown waterfall chart data structure."""
        chart = self.generator.generate_drawdown_waterfall(self.extended_returns)

        trace = chart.data[0]
        assert "x" in trace
        assert "y" in trace
        assert trace["type"] == "bar"
        assert "marker" in trace
        assert "color" in trace["marker"]

    def test_drawdown_waterfall_coloring(self):
        """Test that drawdown waterfall uses correct colors."""
        chart = self.generator.generate_drawdown_waterfall(self.extended_returns)

        trace = chart.data[0]
        colors = trace["marker"]["color"]
        assert isinstance(colors, list)
        # Colors should be danger (red) for negative, success (green) for positive
        for i, color in enumerate(colors):
            assert color in [
                self.generator.default_colors["danger"],
                self.generator.default_colors["success"],
            ]

    def test_drawdown_waterfall_with_no_drawdown(self):
        """Test drawdown waterfall with only positive returns."""
        positive_returns = [Decimal("0.01"), Decimal("0.02"), Decimal("0.015"), Decimal("0.020")]
        chart = self.generator.generate_drawdown_waterfall(positive_returns)

        # Chart should still be generated
        assert len(chart.data) == 1
        # All y values should be <= 0 or near 0
        assert all(y <= 0.01 for y in chart.data[0]["y"])  # Allow small floating point errors

    def test_drawdown_waterfall_sampling(self):
        """Test that long series are sampled."""
        long_returns = [Decimal(str(0.001)) for _ in range(500)]
        chart = self.generator.generate_drawdown_waterfall(long_returns)

        # Should have fewer data points than input (sampled)
        assert len(chart.data[0]["x"]) < len(long_returns)

    # ========================================================================
    # ROLLING METRICS CHART TESTS
    # ========================================================================

    def test_generate_rolling_metrics_chart(self):
        """Test rolling metrics chart generation."""
        chart = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=10)

        assert isinstance(chart, PlotlyChart)
        assert chart.chart_id == "rolling_metrics"
        assert chart.chart_type == "line"
        assert chart.title == "Rolling Sharpe Ratio & Volatility"
        assert len(chart.data) == 2  # Sharpe + Volatility
        assert self.generator.charts_generated == 1

    def test_rolling_metrics_dual_axis(self):
        """Test rolling metrics chart uses dual axis."""
        chart = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=10)

        traces = chart.data
        assert traces[0]["yaxis"] == "y1"
        assert traces[1]["yaxis"] == "y2"

        layout = chart.layout
        assert "yaxis" in layout
        assert "yaxis2" in layout
        assert layout["yaxis2"]["overlaying"] == "y"
        assert layout["yaxis2"]["side"] == "right"

    def test_rolling_metrics_window_parameter(self):
        """Test rolling metrics with different window sizes."""
        chart_w5 = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=5)
        chart_w20 = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=20)

        # Larger window should have fewer data points
        assert len(chart_w5.data[0]["x"]) > len(chart_w20.data[0]["x"])

    def test_rolling_metrics_custom_title(self):
        """Test rolling metrics with custom title."""
        custom_title = "My Rolling Metrics"
        chart = self.generator.generate_rolling_metrics_chart(
            self.extended_returns, window=10, title=custom_title
        )

        assert chart.title == custom_title

    def test_rolling_metrics_names(self):
        """Test that rolling metrics traces have correct names."""
        chart = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=10)

        assert chart.data[0]["name"] == "Sharpe Ratio"
        assert chart.data[1]["name"] == "Volatility"

    def test_rolling_metrics_axis_titles(self):
        """Test rolling metrics axis titles."""
        chart = self.generator.generate_rolling_metrics_chart(self.extended_returns, window=10)

        assert chart.layout["yaxis"]["title"] == "Sharpe Ratio"
        assert chart.layout["yaxis2"]["title"] == "Volatility (%)"

    def test_rolling_metrics_small_dataset(self):
        """Test rolling metrics with dataset smaller than window."""
        small_returns = [Decimal("0.01"), Decimal("0.02"), Decimal("0.015")]
        chart = self.generator.generate_rolling_metrics_chart(small_returns, window=10)

        # Should produce empty or minimal data
        assert isinstance(chart, PlotlyChart)
        if len(chart.data[0]["x"]) == 0:
            assert len(chart.data[0]["y"]) == 0

    # ========================================================================
    # MONTHLY RETURNS HEATMAP TESTS
    # ========================================================================

    def test_generate_heatmap_monthly_returns(self):
        """Test monthly returns heatmap generation."""
        chart = self.generator.generate_heatmap_monthly_returns(self.extended_returns)

        assert isinstance(chart, PlotlyChart)
        assert chart.chart_id == "monthly_returns_heatmap"
        assert chart.chart_type == "heatmap"
        assert chart.title == "Monthly Returns Heatmap"
        assert self.generator.charts_generated == 1

    def test_heatmap_monthly_returns_data_structure(self):
        """Test heatmap data structure."""
        chart = self.generator.generate_heatmap_monthly_returns(self.extended_returns)

        trace = chart.data[0]
        assert "z" in trace  # Heatmap values
        assert "x" in trace  # Months
        assert "y" in trace  # Years
        assert trace["type"] == "heatmap"
        assert trace["colorscale"] == "RdYlGn"
        assert trace["zmid"] == 0  # Center at 0 for return data

    def test_heatmap_month_names(self):
        """Test heatmap uses correct month names."""
        chart = self.generator.generate_heatmap_monthly_returns(self.extended_returns)

        months = chart.data[0]["x"]
        expected_months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        assert months == expected_months

    def test_heatmap_custom_title(self):
        """Test heatmap with custom title."""
        custom_title = "My Monthly Returns"
        chart = self.generator.generate_heatmap_monthly_returns(
            self.extended_returns, title=custom_title
        )

        assert chart.title == custom_title

    def test_heatmap_colorbar(self):
        """Test heatmap colorbar configuration."""
        chart = self.generator.generate_heatmap_monthly_returns(self.extended_returns)

        layout = chart.layout
        assert "coloraxis" in layout
        assert layout["coloraxis"]["colorbar"]["title"] == "Return (%)"

    def test_heatmap_long_series(self):
        """Test heatmap with long series spanning multiple years."""
        # 504 days = ~24 months
        long_returns = [Decimal(str(0.0005)) for _ in range(504)]
        chart = self.generator.generate_heatmap_monthly_returns(long_returns)

        chart.data[0]["z"]
        years = chart.data[0]["y"]
        # Should span at least 2 years
        assert len(years) >= 2

    # ========================================================================
    # FACTOR EXPOSURES CHART TESTS
    # ========================================================================

    def test_generate_factor_exposures_chart(self):
        """Test factor exposures chart generation."""
        factors = {
            "Market": Decimal("0.85"),
            "Size": Decimal("-0.10"),
            "Value": Decimal("0.25"),
            "Momentum": Decimal("0.15"),
        }

        chart = self.generator.generate_factor_exposures_chart(factors)

        assert isinstance(chart, PlotlyChart)
        assert chart.chart_id == "factor_exposures"
        assert chart.chart_type == "bar"
        assert chart.title == "Factor Exposures"
        assert self.generator.charts_generated == 1

    def test_factor_exposures_data_structure(self):
        """Test factor exposures chart data structure."""
        factors = {
            "Market": Decimal("0.85"),
            "Size": Decimal("-0.10"),
        }

        chart = self.generator.generate_factor_exposures_chart(factors)

        trace = chart.data[0]
        assert "x" in trace  # Factor names
        assert "y" in trace  # Exposures
        assert trace["type"] == "bar"
        assert len(trace["x"]) == 2
        assert len(trace["y"]) == 2

    def test_factor_exposures_coloring(self):
        """Test factor exposures use correct colors."""
        factors = {
            "Positive": Decimal("0.50"),
            "Negative": Decimal("-0.30"),
        }

        chart = self.generator.generate_factor_exposures_chart(factors)

        colors = chart.data[0]["marker"]["color"]
        assert colors[0] == self.generator.default_colors["success"]  # Positive → green
        assert colors[1] == self.generator.default_colors["danger"]  # Negative → red

    def test_factor_exposures_zero_line(self):
        """Test factor exposures includes zero line."""
        factors = {"Factor1": Decimal("0.5")}
        chart = self.generator.generate_factor_exposures_chart(factors)

        layout = chart.layout
        assert "shapes" in layout
        assert len(layout["shapes"]) >= 1
        # Check for horizontal line at y=0
        assert any(shape.get("y0") == 0 and shape.get("y1") == 0 for shape in layout["shapes"])

    def test_factor_exposures_custom_title(self):
        """Test factor exposures with custom title."""
        custom_title = "My Factors"
        factors = {"Factor1": Decimal("0.5")}
        chart = self.generator.generate_factor_exposures_chart(factors, title=custom_title)

        assert chart.title == custom_title

    def test_factor_exposures_single_factor(self):
        """Test factor exposures with single factor."""
        factors = {"Market": Decimal("0.75")}
        chart = self.generator.generate_factor_exposures_chart(factors)

        assert len(chart.data[0]["x"]) == 1
        assert len(chart.data[0]["y"]) == 1

    def test_factor_exposures_many_factors(self):
        """Test factor exposures with many factors."""
        factors = {f"Factor{i}": Decimal(str(i * 0.1)) for i in range(10)}
        chart = self.generator.generate_factor_exposures_chart(factors)

        assert len(chart.data[0]["x"]) == 10
        assert len(chart.data[0]["y"]) == 10

    # ========================================================================
    # UTILITY METHODS TESTS
    # ========================================================================

    def test_get_generator_status(self):
        """Test generator status reporting."""
        # Generate a few charts
        self.generator.generate_cumulative_returns_chart(self.sample_returns)
        self.generator.generate_drawdown_waterfall(self.sample_returns)

        status = self.generator.get_generator_status()

        assert status["status"] == "operational"
        assert status["charts_generated"] == 2
        assert "last_update" in status

    def test_get_generator_status_format(self):
        """Test generator status has correct format."""
        status = self.generator.get_generator_status()

        assert isinstance(status, dict)
        assert isinstance(status["charts_generated"], int)
        assert isinstance(status["last_update"], str)
        # last_update should be ISO format datetime
        datetime.fromisoformat(status["last_update"])

    def test_charts_generated_counter(self):
        """Test that charts_generated counter increments correctly."""
        assert self.generator.charts_generated == 0

        self.generator.generate_cumulative_returns_chart(self.sample_returns)
        assert self.generator.charts_generated == 1

        self.generator.generate_drawdown_waterfall(self.sample_returns)
        assert self.generator.charts_generated == 2

        self.generator.generate_rolling_metrics_chart(self.extended_returns)
        assert self.generator.charts_generated == 3

    # ========================================================================
    # EDGE CASES AND ERROR HANDLING
    # ========================================================================

    def test_cumulative_returns_empty_list(self):
        """Test cumulative returns with empty list."""
        empty_returns = []

        # Should raise an exception when trying to compute with empty data
        try:
            chart = self.generator.generate_cumulative_returns_chart(empty_returns)
            # If no exception, chart should still be created but with no data
            assert isinstance(chart, PlotlyChart)
        except (ValueError, IndexError, TypeError):
            # Expected behavior
            pass

    def test_cumulative_returns_all_zeros(self):
        """Test cumulative returns with all zeros."""
        zero_returns = [Decimal("0") for _ in range(10)]
        chart = self.generator.generate_cumulative_returns_chart(zero_returns)

        # All cumulative returns should be 0
        assert all(abs(y) < 0.01 for y in chart.data[0]["y"])

    def test_cumulative_returns_large_values(self):
        """Test cumulative returns with large return values."""
        large_returns = [Decimal("1.0"), Decimal("2.0"), Decimal("0.5")]
        chart = self.generator.generate_cumulative_returns_chart(large_returns)

        assert isinstance(chart, PlotlyChart)
        assert len(chart.data[0]["y"]) == 3

    def test_factor_exposures_empty_dict(self):
        """Test factor exposures with empty dictionary."""
        empty_factors = {}

        chart = self.generator.generate_factor_exposures_chart(empty_factors)

        # Should handle gracefully
        assert isinstance(chart, PlotlyChart)
        assert len(chart.data[0]["x"]) == 0

    def test_factor_exposures_mixed_signs(self):
        """Test factor exposures with mixed positive and negative values."""
        factors = {
            "Pos1": Decimal("0.5"),
            "Neg1": Decimal("-0.3"),
            "Pos2": Decimal("0.2"),
            "Neg2": Decimal("-0.1"),
        }

        chart = self.generator.generate_factor_exposures_chart(factors)

        colors = chart.data[0]["marker"]["color"]
        # Check mix of colors
        has_success = any(c == self.generator.default_colors["success"] for c in colors)
        has_danger = any(c == self.generator.default_colors["danger"] for c in colors)
        assert has_success and has_danger

    def test_rolling_metrics_high_volatility(self):
        """Test rolling metrics with high volatility."""
        volatile_returns = [Decimal(str(np.sin(i * 0.1))) for i in range(100)]
        chart = self.generator.generate_rolling_metrics_chart(volatile_returns, window=20)

        assert isinstance(chart, PlotlyChart)
        assert len(chart.data) == 2

    # ========================================================================
    # SERIALIZATION TESTS
    # ========================================================================

    def test_chart_json_serialization(self):
        """Test that all generated charts can be serialized to JSON."""
        chart = self.generator.generate_cumulative_returns_chart(self.sample_returns)

        json_str = chart.to_json()
        json_obj = json.loads(json_str)

        assert "data" in json_obj
        assert "layout" in json_obj
        assert "config" in json_obj

    def test_chart_html_generation(self):
        """Test that all generated charts can be converted to HTML."""
        chart = self.generator.generate_cumulative_returns_chart(self.sample_returns)

        html = chart.to_html_div()

        assert isinstance(html, str)
        assert len(html) > 0
        assert "plotly-chart" in html
        assert "Plotly.newPlot" in html

    def test_all_chart_types_serializable(self):
        """Test that all chart types can be serialized."""
        factors = {"Factor1": Decimal("0.5"), "Factor2": Decimal("-0.2")}

        charts = [
            self.generator.generate_cumulative_returns_chart(self.sample_returns),
            self.generator.generate_drawdown_waterfall(self.sample_returns),
            self.generator.generate_rolling_metrics_chart(self.extended_returns),
            self.generator.generate_heatmap_monthly_returns(self.extended_returns),
            self.generator.generate_factor_exposures_chart(factors),
        ]

        for chart in charts:
            # Should not raise exception
            json_str = chart.to_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0

            html = chart.to_html_div()
            assert isinstance(html, str)
            assert len(html) > 0

    # ========================================================================
    # SINGLETON TESTS
    # ========================================================================

    def test_get_visualization_generator_singleton(self):
        """Test that get_visualization_generator returns singleton."""
        gen1 = get_visualization_generator()
        gen2 = get_visualization_generator()

        assert gen1 is gen2

    def test_singleton_persistence(self):
        """Test that singleton state persists across calls."""
        gen1 = get_visualization_generator()
        initial_count = gen1.charts_generated

        gen1.generate_cumulative_returns_chart(self.sample_returns)
        assert gen1.charts_generated == initial_count + 1

        gen2 = get_visualization_generator()
        assert gen2.charts_generated == gen1.charts_generated


class TestIntegrationVisualizationComponents:
    """Integration tests for visualization components."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = AdvancedVisualizationGenerator()
        self.returns = [Decimal(str(0.001 * i)) for i in range(1, 101)]

    def test_generate_full_report_visualizations(self):
        """Test generating a complete set of visualizations for a report."""
        factors = {
            "Market": Decimal("0.75"),
            "Size": Decimal("-0.15"),
            "Value": Decimal("0.20"),
        }

        # Generate all chart types
        returns_chart = self.generator.generate_cumulative_returns_chart(self.returns)
        drawdown_chart = self.generator.generate_drawdown_waterfall(self.returns)
        metrics_chart = self.generator.generate_rolling_metrics_chart(self.returns)
        heatmap_chart = self.generator.generate_heatmap_monthly_returns(self.returns)
        factor_chart = self.generator.generate_factor_exposures_chart(factors)

        # Verify all charts are valid
        charts = [returns_chart, drawdown_chart, metrics_chart, heatmap_chart, factor_chart]
        for chart in charts:
            assert isinstance(chart, PlotlyChart)
            json_str = chart.to_json()
            json_obj = json.loads(json_str)
            assert "data" in json_obj

    def test_visualizations_with_benchmark_comparison(self):
        """Test visualizations with benchmark comparison."""
        benchmark = [Decimal(str(0.0008 * i)) for i in range(1, 101)]

        returns_chart = self.generator.generate_cumulative_returns_chart(
            self.returns, benchmark_returns=benchmark
        )

        # Should have 2 traces
        assert len(returns_chart.data) == 2
        assert returns_chart.data[0]["name"] == "Strategy"
        assert returns_chart.data[1]["name"] == "Benchmark"

    def test_multiple_generators_independent(self):
        """Test that multiple generator instances are independent."""
        gen1 = AdvancedVisualizationGenerator()
        gen2 = AdvancedVisualizationGenerator()

        gen1.generate_cumulative_returns_chart(self.returns)
        gen2.generate_drawdown_waterfall(self.returns)

        assert gen1.charts_generated == 1
        assert gen2.charts_generated == 1
