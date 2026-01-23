"""
T9.1 PHASE 4: AdvancedVisualizationGenerator - Plotly-based interactive charts

Generates professional interactive visualizations for performance reports using Plotly.
Charts are optimized for HTML embedding and interactive exploration.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES FOR VISUALIZATION DATA
# ============================================================================


@dataclass
class PlotlyChart:
    """Plotly chart representation for HTML embedding."""

    chart_id: str
    title: str
    chart_type: str  # "line", "scatter", "bar", "heatmap", "waterfall"
    data: Dict[str, Any]  # Plotly data structure
    layout: Dict[str, Any]  # Plotly layout structure
    config: Dict[str, Any]  # Plotly config for interactivity

    def to_json(self) -> str:
        """Convert chart to JSON for HTML embedding."""
        return json.dumps(
            {
                "data": self.data,
                "layout": self.layout,
                "config": self.config,
            }
        )

    def to_html_div(self) -> str:
        """Generate HTML div with embedded Plotly chart."""
        html = f'<div id="{self.chart_id}" class="plotly-chart"></div>\n'
        html += '<script>\n'
        html += f'var data_{self.chart_id} = {json.dumps(self.data)};\n'
        html += f'var layout_{self.chart_id} = {json.dumps(self.layout)};\n'
        html += f'var config_{self.chart_id} = {json.dumps(self.config)};\n'
        html += f'Plotly.newPlot("{self.chart_id}", data_{self.chart_id}, layout_{self.chart_id}, config_{self.chart_id});\n'
        html += '</script>\n'
        return html


@dataclass
class ChartMetadata:
    """Metadata about a generated chart."""

    chart_id: str
    chart_type: str
    title: str
    description: str
    data_points: int
    generation_time_ms: Decimal


# ============================================================================
# VISUALIZATION GENERATOR
# ============================================================================


class AdvancedVisualizationGenerator:
    """
    Plotly-based visualization generator for interactive charts.

    Generates:
    - Cumulative returns line chart with drawdown overlay
    - Drawdown waterfall chart showing recovery patterns
    - Rolling metrics (Sharpe, volatility) time series
    - Monthly returns heatmap
    - Factor exposure bar chart
    """

    def __init__(self):
        """Initialize visualization generator."""
        self.charts_generated = 0
        self.default_colors = {
            "primary": "#1f77b4",
            "success": "#2ca02c",
            "danger": "#d62728",
            "warning": "#ff7f0e",
        }
        logger.info("AdvancedVisualizationGenerator initialized")

    # ========================================================================
    # CHART GENERATION METHODS
    # ========================================================================

    def generate_cumulative_returns_chart(
        self,
        returns: List[Decimal],
        title: str = "Cumulative Returns",
        benchmark_returns: Optional[List[Decimal]] = None,
    ) -> PlotlyChart:
        """
        Generate cumulative returns line chart.

        Args:
            returns: List of period returns (Decimal)
            title: Chart title
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            PlotlyChart with interactive line chart
        """
        try:
            returns_array = np.array([float(r) for r in returns])
            cumulative = np.cumprod(1 + returns_array) - 1
            cumulative_pct = cumulative * 100

            # Generate x-axis (periods)
            periods = list(range(len(cumulative)))

            # Data traces
            data = [
                {
                    "x": periods,
                    "y": cumulative_pct.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Strategy",
                    "line": {
                        "color": self.default_colors["primary"],
                        "width": 2,
                    },
                    "hovertemplate": "Period: %{x}<br>Return: %{y:.2f}%<extra></extra>",
                }
            ]

            # Add benchmark if provided
            if benchmark_returns:
                benchmark_array = np.array([float(r) for r in benchmark_returns])
                benchmark_cumulative = np.cumprod(1 + benchmark_array) - 1
                benchmark_pct = benchmark_cumulative * 100

                data.append(
                    {
                        "x": periods,
                        "y": benchmark_pct.tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "Benchmark",
                        "line": {
                            "color": self.default_colors["warning"],
                            "width": 2,
                            "dash": "dash",
                        },
                        "hovertemplate": "Period: %{x}<br>Return: %{y:.2f}%<extra></extra>",
                    }
                )

            layout = {
                "title": {"text": title, "x": 0.5, "xanchor": "center"},
                "xaxis": {"title": "Period", "showgrid": True},
                "yaxis": {"title": "Cumulative Return (%)", "showgrid": True},
                "hovermode": "x unified",
                "plot_bgcolor": "rgba(240,240,240,0.5)",
                "paper_bgcolor": "white",
                "margin": {"l": 60, "r": 20, "t": 60, "b": 40},
            }

            config = {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
                "toImageButtonOptions": {"format": "png", "filename": "returns_chart"},
            }

            chart = PlotlyChart(
                chart_id="cumulative_returns",
                title=title,
                chart_type="line",
                data=data,
                layout=layout,
                config=config,
            )

            self.charts_generated += 1
            return chart

        except Exception as e:
            logger.error(f"Cumulative returns chart generation failed: {e}")
            raise

    def generate_drawdown_waterfall(
        self,
        returns: List[Decimal],
        title: str = "Drawdown Analysis",
    ) -> PlotlyChart:
        """
        Generate drawdown waterfall chart showing peak-to-trough declines.

        Args:
            returns: List of period returns (Decimal)
            title: Chart title

        Returns:
            PlotlyChart with waterfall visualization
        """
        try:
            returns_array = np.array([float(r) for r in returns])
            cumulative = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max * 100

            periods = list(range(len(drawdown)))

            # Find significant drawdown periods (consecutive negative periods)
            significant_dd = []
            current_dd = 0
            start_idx = 0

            for i, dd in enumerate(drawdown):
                if dd < 0:
                    if current_dd == 0:
                        start_idx = i
                    current_dd += dd
                else:
                    if current_dd < 0:
                        significant_dd.append(
                            {
                                "start": start_idx,
                                "end": i - 1,
                                "depth": current_dd,
                            }
                        )
                    current_dd = 0

            # Data for waterfall
            x_labels = [
                f"Period {i}" for i in periods[:: max(1, len(periods) // 20)]
            ]  # Sample every nth
            y_values = drawdown[:: max(1, len(periods) // 20)].tolist()

            data = [
                {
                    "x": x_labels,
                    "y": y_values,
                    "type": "bar",
                    "marker": {
                        "color": [
                            (
                                self.default_colors["danger"]
                                if v < 0
                                else self.default_colors["success"]
                            )
                            for v in y_values
                        ],
                    },
                    "hovertemplate": "%{x}<br>Drawdown: %{y:.2f}%<extra></extra>",
                }
            ]

            layout = {
                "title": {"text": title, "x": 0.5, "xanchor": "center"},
                "xaxis": {"title": "Period"},
                "yaxis": {"title": "Drawdown (%)", "showgrid": True},
                "hovermode": "x",
                "plot_bgcolor": "rgba(240,240,240,0.5)",
                "paper_bgcolor": "white",
                "margin": {"l": 60, "r": 20, "t": 60, "b": 40},
            }

            config = {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
            }

            chart = PlotlyChart(
                chart_id="drawdown_waterfall",
                title=title,
                chart_type="bar",
                data=data,
                layout=layout,
                config=config,
            )

            self.charts_generated += 1
            return chart

        except Exception as e:
            logger.error(f"Drawdown waterfall generation failed: {e}")
            raise

    def generate_rolling_metrics_chart(
        self,
        returns: List[Decimal],
        window: int = 30,
        title: str = "Rolling Sharpe Ratio & Volatility",
    ) -> PlotlyChart:
        """
        Generate rolling metrics chart (Sharpe ratio and volatility).

        Args:
            returns: List of period returns (Decimal)
            window: Rolling window size (periods)
            title: Chart title

        Returns:
            PlotlyChart with dual-axis metrics
        """
        try:
            returns_array = np.array([float(r) for r in returns])

            # Calculate rolling metrics
            rolling_sharpe = []
            rolling_vol = []
            periods_list = []

            for i in range(window, len(returns_array)):
                window_returns = returns_array[i - window : i]
                mean_ret = np.mean(window_returns)
                std_ret = np.std(window_returns)
                sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
                vol = std_ret * np.sqrt(252) * 100

                rolling_sharpe.append(sharpe)
                rolling_vol.append(vol)
                periods_list.append(i)

            data = [
                {
                    "x": periods_list,
                    "y": rolling_sharpe,
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Sharpe Ratio",
                    "line": {"color": self.default_colors["primary"], "width": 2},
                    "yaxis": "y1",
                    "hovertemplate": "Period: %{x}<br>Sharpe: %{y:.2f}<extra></extra>",
                },
                {
                    "x": periods_list,
                    "y": rolling_vol,
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Volatility",
                    "line": {"color": self.default_colors["warning"], "width": 2},
                    "yaxis": "y2",
                    "hovertemplate": "Period: %{x}<br>Vol: %{y:.1f}%<extra></extra>",
                },
            ]

            layout = {
                "title": {"text": title, "x": 0.5, "xanchor": "center"},
                "xaxis": {"title": "Period"},
                "yaxis": {
                    "title": "Sharpe Ratio",
                    "titlefont": {"color": self.default_colors["primary"]},
                    "tickfont": {"color": self.default_colors["primary"]},
                },
                "yaxis2": {
                    "title": "Volatility (%)",
                    "titlefont": {"color": self.default_colors["warning"]},
                    "tickfont": {"color": self.default_colors["warning"]},
                    "overlaying": "y",
                    "side": "right",
                },
                "hovermode": "x unified",
                "plot_bgcolor": "rgba(240,240,240,0.5)",
                "paper_bgcolor": "white",
                "margin": {"l": 60, "r": 60, "t": 60, "b": 40},
                "legend": {"x": 0.5, "y": 1.1, "xanchor": "center", "yanchor": "top"},
            }

            config = {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
            }

            chart = PlotlyChart(
                chart_id="rolling_metrics",
                title=title,
                chart_type="line",
                data=data,
                layout=layout,
                config=config,
            )

            self.charts_generated += 1
            return chart

        except Exception as e:
            logger.error(f"Rolling metrics chart generation failed: {e}")
            raise

    def generate_heatmap_monthly_returns(
        self,
        returns: List[Decimal],
        title: str = "Monthly Returns Heatmap",
    ) -> PlotlyChart:
        """
        Generate heatmap of monthly returns.

        Args:
            returns: List of daily/period returns (Decimal)
            title: Chart title

        Returns:
            PlotlyChart with heatmap visualization
        """
        try:
            returns_array = np.array([float(r) for r in returns])

            # Assume 252 trading days, ~21 per month
            months = []
            years = []
            monthly_returns = []

            days_per_month = 21
            current_year = 2024
            current_month = 1

            for i in range(0, len(returns_array), days_per_month):
                month_ret = returns_array[i : i + days_per_month]
                if len(month_ret) > 0:
                    # Compound returns
                    monthly_ret = (np.prod(1 + month_ret) - 1) * 100
                    monthly_returns.append(monthly_ret)
                    months.append(current_month)
                    years.append(current_year)

                    current_month += 1
                    if current_month > 12:
                        current_month = 1
                        current_year += 1

            # Reshape into matrix (years x months)
            unique_years = sorted(set(years))
            year_idx = {year: i for i, year in enumerate(unique_years)}
            {m: i for i, m in enumerate(range(1, 13))}

            matrix = np.zeros((len(unique_years), 12))
            for y, m, ret in zip(years, months, monthly_returns):
                matrix[year_idx[y], m - 1] = ret

            month_names = [
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

            data = [
                {
                    "z": matrix.tolist(),
                    "x": month_names,
                    "y": unique_years,
                    "type": "heatmap",
                    "colorscale": "RdYlGn",
                    "zmid": 0,
                    "hovertemplate": "%{y} %{x}<br>Return: %{z:.2f}%<extra></extra>",
                }
            ]

            layout = {
                "title": {"text": title, "x": 0.5, "xanchor": "center"},
                "xaxis": {"title": "Month"},
                "yaxis": {"title": "Year"},
                "coloraxis": {"colorbar": {"title": "Return (%)"}},
                "margin": {"l": 60, "r": 100, "t": 60, "b": 40},
            }

            config = {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
            }

            chart = PlotlyChart(
                chart_id="monthly_returns_heatmap",
                title=title,
                chart_type="heatmap",
                data=data,
                layout=layout,
                config=config,
            )

            self.charts_generated += 1
            return chart

        except Exception as e:
            logger.error(f"Monthly returns heatmap generation failed: {e}")
            raise

    def generate_factor_exposures_chart(
        self,
        factor_data: Dict[str, Decimal],
        title: str = "Factor Exposures",
    ) -> PlotlyChart:
        """
        Generate bar chart of factor exposures/contributions.

        Args:
            factor_data: Dictionary of factor_name → exposure/coefficient
            title: Chart title

        Returns:
            PlotlyChart with factor bar chart
        """
        try:
            factor_names = list(factor_data.keys())
            factor_values = [float(factor_data[f]) for f in factor_names]

            # Color by positive/negative
            colors = [
                self.default_colors["success"] if v >= 0 else self.default_colors["danger"]
                for v in factor_values
            ]

            data = [
                {
                    "x": factor_names,
                    "y": factor_values,
                    "type": "bar",
                    "marker": {"color": colors},
                    "hovertemplate": "%{x}<br>Exposure: %{y:.3f}<extra></extra>",
                }
            ]

            layout = {
                "title": {"text": title, "x": 0.5, "xanchor": "center"},
                "xaxis": {"title": "Factor"},
                "yaxis": {"title": "Exposure / Coefficient", "showgrid": True},
                "hovermode": "x",
                "plot_bgcolor": "rgba(240,240,240,0.5)",
                "paper_bgcolor": "white",
                "margin": {"l": 60, "r": 20, "t": 60, "b": 40},
                "shapes": [
                    {
                        "type": "line",
                        "x0": -0.5,
                        "x1": len(factor_names) - 0.5,
                        "y0": 0,
                        "y1": 0,
                        "line": {"color": "black", "width": 1},
                    }
                ],
            }

            config = {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
            }

            chart = PlotlyChart(
                chart_id="factor_exposures",
                title=title,
                chart_type="bar",
                data=data,
                layout=layout,
                config=config,
            )

            self.charts_generated += 1
            return chart

        except Exception as e:
            logger.error(f"Factor exposures chart generation failed: {e}")
            raise

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_generator_status(self) -> Dict:
        """Get generator operational status."""
        return {
            "status": "operational",
            "charts_generated": self.charts_generated,
            "last_update": datetime.utcnow().isoformat(),
        }


# ============================================================================
# SINGLETON ACCESSOR
# ============================================================================


_viz_generator_instance: Optional[AdvancedVisualizationGenerator] = None


def get_visualization_generator() -> AdvancedVisualizationGenerator:
    """Get or create AdvancedVisualizationGenerator singleton."""
    global _viz_generator_instance
    if _viz_generator_instance is None:
        _viz_generator_instance = AdvancedVisualizationGenerator()

    return _viz_generator_instance
