"""
Advanced Visualizations - Comprehensive visualization suite for backtest analysis.

Provides:
- Correlation networks (networkx)
- Parallel coordinates plots (plotly)
- 3D scatter plots
- Underwater drawdown analysis
- Rolling metrics visualization
- Regime performance analysis
- Seasonality heatmaps
"""

import logging
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING, Tuple

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# Optional dependencies with graceful fallbacks
try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.dates import DateFormatter

    HAS_MATPLOTLIB = True
except (ImportError, Exception):
    # Matplotlib may fail due to numpy version incompatibility
    HAS_MATPLOTLIB = False
    plt = None
    sns = None
    DateFormatter = None

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    go = None
    make_subplots = None

logger = logging.getLogger(__name__)


class AdvancedVisualizer:
    """
    Advanced visualization suite for comprehensive backtest analysis.

    Supports both static (matplotlib) and interactive (plotly) visualizations.
    """

    def __init__(self, output_dir: str = "reports/meta_analyzer", dpi: int = 150):
        """
        Initialize AdvancedVisualizer.

        Args:
            output_dir: Directory for saving visualizations
            dpi: DPI for matplotlib figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi

        # Configure matplotlib style (only if available)
        if HAS_MATPLOTLIB and plt is not None:
            try:
                plt.style.use("seaborn-v0_8-darkgrid")
                if sns is not None:
                    sns.set_palette("husl")
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                logger.warning(f"Could not set matplotlib style: {e}")

        logger.info(f"AdvancedVisualizer initialized: output_dir={self.output_dir}, dpi={dpi}")

    def plot_correlation_network(
        self,
        data: pd.DataFrame,
        threshold: float = 0.3,
        figsize: Tuple[int, int] = (14, 10),
        output_file: Optional[str] = None,
    ) -> "Optional[Figure]":
        """
        Plot correlation network using networkx.

        Creates a graph where nodes are metrics and edges show strong correlations.

        Args:
            data: DataFrame with numeric columns
            threshold: Minimum correlation to draw edge (default: 0.3)
            figsize: Figure size
            output_file: Output filename (default: correlation_network.png)

        Returns:
            Figure object or None if plotting fails
        """
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping correlation network plot")
            return None
        if not HAS_NETWORKX or nx is None:
            logger.warning("networkx not available, skipping correlation network plot")
            return None

        try:
            # Select numeric columns
            numeric_data = data.select_dtypes(include=[np.number])
            if numeric_data.empty or len(numeric_data.columns) < 2:
                logger.warning("Not enough numeric columns for correlation network")
                return None

            # Calculate correlation matrix
            corr_matrix = numeric_data.corr()

            # Create graph
            G = nx.Graph()

            # Add nodes (metrics)
            for col in corr_matrix.columns:
                G.add_node(col)

            # Add edges for correlations above threshold
            for i, col1 in enumerate(corr_matrix.columns):
                for col2 in corr_matrix.columns[i + 1 :]:
                    corr_value = abs(corr_matrix.loc[col1, col2])
                    if corr_value >= threshold:
                        G.add_edge(col1, col2, weight=corr_value)

            # Create figure
            fig, ax = plt.subplots(figsize=figsize)

            # Layout
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

            # Draw network
            nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=1000, ax=ax, alpha=0.9)

            # Draw edges with varying width based on correlation strength
            edges = G.edges()
            weights = [G[u][v]["weight"] for u, v in edges]
            nx.draw_networkx_edges(
                G,
                pos,
                width=[w * 3 for w in weights],
                alpha=0.6,
                edge_color=weights,
                edge_cmap=plt.cm.coolwarm,
                ax=ax,
            )

            # Draw labels
            nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", ax=ax)

            ax.set_title("Correlation Network (threshold={})".format(threshold), fontsize=14)
            ax.axis("off")

            # Save figure
            output_path = self.output_dir / (output_file or "correlation_network.png")
            plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Correlation network saved: {output_path}")
            return fig

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error plotting correlation network: {e}", exc_info=True)
            return None

    def plot_parallel_coordinates(
        self,
        data: pd.DataFrame,
        color_col: Optional[str] = None,
        max_cols: int = 10,
        output_file: Optional[str] = None,
    ) -> Optional[str]:
        """
        Plot parallel coordinates using plotly (interactive).

        Args:
            data: DataFrame with numeric columns
            color_col: Column to use for coloring (default: first numeric column)
            max_cols: Maximum number of columns to include (default: 10)
            output_file: Output HTML filename

        Returns:
            Path to saved HTML file or None
        """
        # Check if required dependencies are available
        if not HAS_PLOTLY or go is None:
            logger.warning("plotly not available, skipping parallel coordinates plot")
            return None

        try:
            numeric_data = data.select_dtypes(include=[np.number]).copy()
            if numeric_data.empty:
                logger.warning("No numeric columns for parallel coordinates")
                return None

            # Limit columns
            if len(numeric_data.columns) > max_cols:
                numeric_data = numeric_data.iloc[:, :max_cols]

            # Determine color column
            if (color_col is None) or (color_col not in data.columns):
                color_col = numeric_data.columns[0]

            # Normalize data for better visualization
            normalized_data = (numeric_data - numeric_data.min()) / (
                numeric_data.max() - numeric_data.min() + 1e-8
            )

            # Create parallel coordinates figure
            fig = go.Figure(
                data=go.Parcoords(
                    dimensions=[
                        {"label": col, "values": normalized_data[col]}
                        for col in normalized_data.columns
                    ],
                    line={"color": data[color_col], "colorscale": "Viridis", "showscale": True},
                )
            )

            fig.update_layout(title="Parallel Coordinates Plot", height=600, width=1200)

            # Save HTML
            output_path = self.output_dir / (output_file or "parallel_coordinates.html")
            fig.write_html(str(output_path))

            logger.info(f"Parallel coordinates plot saved: {output_path}")
            return str(output_path)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error plotting parallel coordinates: {e}", exc_info=True)
            return None

    def plot_3d_scatter(
        self,
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        z_col: str,
        color_col: Optional[str] = None,
        size_col: Optional[str] = None,
        output_file: Optional[str] = None,
    ) -> Optional[str]:
        """
        Plot 3D scatter plot using plotly (interactive).

        Args:
            data: DataFrame with numeric columns
            x_col: Column for X axis
            y_col: Column for Y axis
            z_col: Column for Z axis
            color_col: Column for coloring
            size_col: Column for bubble size
            output_file: Output HTML filename

        Returns:
            Path to saved HTML file or None
        """
        # Check if required dependencies are available
        if not HAS_PLOTLY or go is None:
            logger.warning("plotly not available, skipping 3d scatter plot")
            return None

        try:
            # Validate columns
            if x_col not in data.columns or y_col not in data.columns or z_col not in data.columns:
                logger.warning(f"Missing required columns: {x_col}, {y_col}, {z_col}")
                return None

            # Create 3D scatter
            fig = go.Figure()

            if color_col and color_col in data.columns:
                fig.add_trace(
                    go.Scatter3d(
                        x=data[x_col],
                        y=data[y_col],
                        z=data[z_col],
                        mode="markers",
                        marker={
                            "size": (
                                4
                                if size_col is None
                                else (data[size_col] / data[size_col].max() * 10)
                            ),
                            "color": data[color_col],
                            "colorscale": "Viridis",
                            "showscale": True,
                            "colorbar": {"title": color_col},
                        },
                        text=data.index,
                        hovertemplate=f"<b>{x_col}:</b> %{{x}}<br>"
                        + f"<b>{y_col}:</b> %{{y}}<br>"
                        + f"<b>{z_col}:</b> %{{z}}<br>"
                        + "<extra></extra>",
                    )
                )
            else:
                fig.add_trace(
                    go.Scatter3d(
                        x=data[x_col],
                        y=data[y_col],
                        z=data[z_col],
                        mode="markers",
                        marker={"size": 4},
                    )
                )

            fig.update_layout(
                title=f"3D Scatter: {x_col} vs {y_col} vs {z_col}",
                scene={"xaxis_title": x_col, "yaxis_title": y_col, "zaxis_title": z_col},
                height=700,
                width=1000,
            )

            # Save HTML
            output_path = self.output_dir / (output_file or "3d_scatter.html")
            fig.write_html(str(output_path))

            logger.info(f"3D scatter plot saved: {output_path}")
            return str(output_path)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error plotting 3D scatter: {e}", exc_info=True)
            return None

    def plot_underwater_drawdown(
        self,
        equity_curve: pd.Series,
        figsize: Tuple[int, int] = (14, 6),
        output_file: Optional[str] = None,
    ) -> "Optional[Figure]":
        """
        Plot underwater (drawdown) chart.

        Shows the drawdown from peak at each point in time.

        Args:
            equity_curve: Series with equity values (index should be dates)
            figsize: Figure size
            output_file: Output filename

        Returns:
            Figure object or None
        """
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping underwater drawdown plot")
            return None

        try:
            # Calculate running maximum (peak)
            running_max = equity_curve.expanding().max()

            # Calculate drawdown
            drawdown = (equity_curve - running_max) / running_max * 100

            # Create figure
            fig, ax = plt.subplots(figsize=figsize)

            # Fill underwater area
            ax.fill_between(
                drawdown.index, drawdown.values, 0, color="red", alpha=0.3, label="Drawdown"
            )
            ax.plot(
                drawdown.index, drawdown.values, color="darkred", linewidth=1, label="Drawdown %"
            )

            # Formatting
            ax.set_title("Underwater (Drawdown) Chart", fontsize=14)
            ax.set_xlabel("Date")
            ax.set_ylabel("Drawdown (%)")
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

            # Format x-axis if datetime
            if isinstance(drawdown.index, pd.DatetimeIndex):
                ax.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
                plt.xticks(rotation=45)

            plt.tight_layout()

            # Save figure
            output_path = self.output_dir / (output_file or "underwater_drawdown.png")
            plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Underwater drawdown chart saved: {output_path}")
            return fig

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error plotting underwater drawdown: {e}", exc_info=True)
            return None

    def plot_rolling_metrics(
        self,
        equity_curve: pd.Series,
        window: int = 252,
        figsize: Tuple[int, int] = (14, 8),
        output_file: Optional[str] = None,
    ) -> "Optional[Figure]":
        """
        Plot rolling metrics (returns, sharpe, volatility).

        Args:
            equity_curve: Series with equity values
            window: Rolling window size (default: 252 days = 1 year)
            figsize: Figure size
            output_file: Output filename

        Returns:
            Figure object or None
        """
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping rolling metrics plot")
            return None

        try:
            # Calculate returns
            returns = equity_curve.pct_change().dropna()
            if len(returns) < window:
                logger.warning(f"Not enough data for {window}-day rolling window")
                return None

            # Calculate rolling metrics
            rolling_mean = returns.rolling(window).mean() * 252 * 100  # Annualized %
            rolling_std = returns.rolling(window).std() * np.sqrt(252) * 100  # Annualized %
            rolling_sharpe = rolling_mean / (rolling_std + 1e-8)

            # Create subplots
            fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)

            # Rolling return
            axes[0].plot(rolling_mean.index, rolling_mean.values, color="blue", linewidth=1.5)
            axes[0].fill_between(
                rolling_mean.index, rolling_mean.values, 0, alpha=0.3, color="blue"
            )
            axes[0].set_ylabel("Return (%)")
            axes[0].set_title(f"Rolling {window}-Day Metrics")
            axes[0].grid(True, alpha=0.3)

            # Rolling volatility
            axes[1].plot(rolling_std.index, rolling_std.values, color="orange", linewidth=1.5)
            axes[1].fill_between(
                rolling_std.index, rolling_std.values, 0, alpha=0.3, color="orange"
            )
            axes[1].set_ylabel("Volatility (%)")
            axes[1].grid(True, alpha=0.3)

            # Rolling Sharpe
            axes[2].plot(rolling_sharpe.index, rolling_sharpe.values, color="green", linewidth=1.5)
            axes[2].axhline(y=0, color="black", linestyle="-", linewidth=0.5)
            axes[2].fill_between(
                rolling_sharpe.index, rolling_sharpe.values, 0, alpha=0.3, color="green"
            )
            axes[2].set_ylabel("Sharpe Ratio")
            axes[2].set_xlabel("Date")
            axes[2].grid(True, alpha=0.3)

            # Format x-axis if datetime
            if isinstance(rolling_sharpe.index, pd.DatetimeIndex):
                axes[2].xaxis.set_major_formatter(DateFormatter("%Y-%m"))
                plt.xticks(rotation=45)

            plt.tight_layout()

            # Save figure
            output_path = self.output_dir / (output_file or "rolling_metrics.png")
            plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Rolling metrics chart saved: {output_path}")
            return fig

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error plotting rolling metrics: {e}", exc_info=True)
            return None

    def plot_regime_performance(
        self,
        returns: pd.Series,
        regime_labels: pd.Series,
        regime_names: Optional[Dict[int, str]] = None,
        figsize: Tuple[int, int] = (12, 6),
        output_file: Optional[str] = None,
    ) -> "Optional[Figure]":
        """
        Plot performance by regime.

        Args:
            returns: Series with returns
            regime_labels: Series with regime labels (same index as returns)
            regime_names: Dict mapping regime label to name
            figsize: Figure size
            output_file: Output filename

        Returns:
            Figure object or None
        """
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping regime performance plot")
            return None

        try:
            if len(returns) != len(regime_labels):
                logger.warning("returns and regime_labels must have same length")
                return None

            # Default regime names
            if regime_names is None:
                unique_regimes = sorted(regime_labels.unique())
                regime_names = {i: f"Regime {i}" for i in unique_regimes}

            # Create figure with subplots
            unique_regimes = sorted(regime_labels.unique())
            fig, axes = plt.subplots(2, 2, figsize=figsize)
            axes = axes.flatten()

            # Cumulative returns by regime
            ax = axes[0]
            for regime in unique_regimes:
                mask = regime_labels == regime
                regime_returns = returns[mask]
                cumulative = (1 + regime_returns).cumprod() - 1
                ax.plot(
                    cumulative.index,
                    cumulative.values,
                    label=regime_names.get(regime, f"Regime {regime}"),
                )

            ax.set_title("Cumulative Returns by Regime")
            ax.set_ylabel("Return")
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Return distribution by regime
            ax = axes[1]
            regime_returns_list = [returns[regime_labels == regime] for regime in unique_regimes]
            ax.boxplot(
                regime_returns_list,
                labels=[regime_names.get(r, f"Regime {r}") for r in unique_regimes],
            )
            ax.set_title("Return Distribution by Regime")
            ax.set_ylabel("Return")
            ax.grid(True, alpha=0.3)

            # Regime transition heatmap
            ax = axes[2]
            regime_counts = regime_labels.value_counts().sort_index()
            colors = plt.cm.viridis(np.linspace(0, 1, len(regime_counts)))
            ax.bar(
                [regime_names.get(r, f"Regime {r}") for r in regime_counts.index],
                regime_counts.values,
                color=colors,
            )
            ax.set_title("Time Spent in Each Regime")
            ax.set_ylabel("Number of Periods")
            ax.grid(True, alpha=0.3, axis="y")

            # Statistics by regime
            ax = axes[3]
            ax.axis("off")
            stats_text = "Regime Statistics:\n\n"
            for regime in unique_regimes:
                mask = regime_labels == regime
                regime_rets = returns[mask]
                stats_text += f"{regime_names.get(regime, f'Regime {regime}')}:\n"
                stats_text += f"  Mean Return: {regime_rets.mean():.4f}\n"
                stats_text += f"  Std Dev: {regime_rets.std():.4f}\n"
                stats_text += f"  Sharpe: {regime_rets.mean() / (regime_rets.std() + 1e-8):.4f}\n\n"

            ax.text(
                0.1,
                0.9,
                stats_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment="top",
                fontfamily="monospace",
                bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
            )

            plt.tight_layout()

            # Save figure
            output_path = self.output_dir / (output_file or "regime_performance.png")
            plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Regime performance chart saved: {output_path}")
            return fig

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error plotting regime performance: {e}", exc_info=True)
            return None

    def plot_seasonality_heatmap(
        self,
        returns: pd.Series,
        figsize: Tuple[int, int] = (14, 8),
        output_file: Optional[str] = None,
    ) -> "Optional[Figure]":
        """
        Plot seasonality heatmap (monthly returns by year).

        Args:
            returns: Series with returns (index should be dates)
            figsize: Figure size
            output_file: Output filename

        Returns:
            Figure object or None
        """
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping seasonality heatmap plot")
            return None

        try:
            # Ensure datetime index
            if not isinstance(returns.index, pd.DatetimeIndex):
                logger.warning("returns index must be DatetimeIndex")
                return None

            # Group by year and month
            monthly_returns = returns.resample("ME").sum()  # Month-end returns
            monthly_returns.index = monthly_returns.index.to_period("M")

            # Create pivot table (year x month)
            pivot_data = monthly_returns.groupby(
                [monthly_returns.index.year, monthly_returns.index.month]
            ).sum()
            pivot_table = pivot_data.unstack(fill_value=0)

            # Create heatmap
            fig, ax = plt.subplots(figsize=figsize)

            sns.heatmap(
                pivot_table,
                annot=True,
                fmt=".2%",
                cmap="RdYlGn",
                center=0,
                ax=ax,
                cbar_kws={"label": "Return"},
                vmin=-0.05,
                vmax=0.05,
            )

            ax.set_title("Monthly Returns Heatmap (Year x Month)")
            ax.set_xlabel("Month")
            ax.set_ylabel("Year")
            ax.set_xticklabels(
                [
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
                ],
                rotation=0,
            )

            plt.tight_layout()

            # Save figure
            output_path = self.output_dir / (output_file or "seasonality_heatmap.png")
            plt.savefig(output_path, dpi=self.dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Seasonality heatmap saved: {output_path}")
            return fig

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error plotting seasonality heatmap: {e}", exc_info=True)
            return None

    def generate_interactive_dashboard(
        self,
        data: pd.DataFrame,
        equity_curve: Optional[pd.Series] = None,
        output_file: str = "dashboard.html",
    ) -> Optional[str]:
        """
        Generate comprehensive interactive dashboard using plotly.

        Args:
            data: DataFrame with performance metrics
            equity_curve: Optional equity curve series
            output_file: Output HTML filename

        Returns:
            Path to saved HTML file or None
        """
        # Check if required dependencies are available
        if not HAS_PLOTLY or go is None:
            logger.warning("plotly not available, skipping interactive dashboard")
            return None

        try:
            # Create subplots
            numeric_cols = data.select_dtypes(include=[np.number]).columns[:6]
            fig = make_subplots(
                rows=3,
                cols=2,
                subplot_titles=[str(col) for col in numeric_cols],
                specs=[[{"type": "histogram"}, {"type": "box"}] for _ in range(3)],
            )

            # Add histograms and box plots
            for i, col in enumerate(numeric_cols):
                row = (i // 2) + 1
                col_idx = (i % 2) + 1

                # Histogram
                fig.add_trace(
                    go.Histogram(x=data[col], name=str(col), nbinsx=30),
                    row=row,
                    col=col_idx if col_idx == 1 else 2,
                )

                # Box plot
                if col_idx == 2 and i < len(numeric_cols) - 1:
                    next_col = numeric_cols[i + 1]
                    fig.add_trace(
                        go.Box(y=data[next_col], name=str(next_col)), row=row, col=col_idx
                    )

            fig.update_layout(height=1000, title="Performance Metrics Dashboard", showlegend=False)

            # Save HTML
            output_path = self.output_dir / output_file
            fig.write_html(str(output_path))

            logger.info(f"Interactive dashboard saved: {output_path}")
            return str(output_path)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error generating dashboard: {e}", exc_info=True)
            return None


# Export availability constants for tests
MATPLOTLIB_AVAILABLE = HAS_MATPLOTLIB
PLOTLY_AVAILABLE = HAS_PLOTLY
NETWORKX_AVAILABLE = HAS_NETWORKX
__all__ = ['AdvancedVisualizer', 'MATPLOTLIB_AVAILABLE', 'PLOTLY_AVAILABLE', 'NETWORKX_AVAILABLE']
