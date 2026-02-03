"""
Visualization utilities for Fractional Differentiation analysis.

This module provides plotting functions to visualize the effects of fractional
differentiation on time series data, including memory preservation and stationarity.
"""

import logging

import warnings
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .fractional_differentiation import FractionalDifferentiation

warnings.filterwarnings('ignore')

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10


def plot_frac_diff_comparison(
    series: pd.Series,
    d_values: List[float] = None,
    figsize: Tuple[int, int] = (14, 10),
    title: str = "Fractional Differentiation Comparison",
) -> plt.Figure:
    """
    Plot series at different differentiation levels.

    Args:
        series: Time series to analyze
        d_values: List of d values to plot (default: [0.0, 0.3, 0.5, 0.7, 1.0])
        figsize: Figure size
        title: Plot title

    Returns:
        matplotlib Figure object

    Example:
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> fig = plot_frac_diff_comparison(series, d_values=[0.0, 0.3, 0.5, 1.0])
        >>> plt.show()
    """
    if d_values is None:
        d_values = [0.0, 0.3, 0.5, 0.7, 1.0]

    fd = FractionalDifferentiation()
    n_plots = len(d_values)

    fig, axes = plt.subplots(n_plots, 1, figsize=figsize)
    if n_plots == 1:
        axes = [axes]

    for idx, d in enumerate(d_values):
        ax = axes[idx]

        if d == 0.0:
            diff_series = series
            label = 'Original (d=0.0)'
        else:
            diff_series = fd.fractional_diff(series, d=d)
            label = f'Fractionally Differentiated (d={d:.1f})'

        # Plot series
        ax.plot(diff_series.index, diff_series.values, linewidth=1, alpha=0.8)
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.set_ylabel('Value', fontsize=9)
        ax.grid(True, alpha=0.3)

        # Add statistics
        clean_series = diff_series.dropna()
        if len(clean_series) > 0:
            mean_val = clean_series.mean()
            std_val = clean_series.std()
            ax.axhline(mean_val, color='red', linestyle='--', linewidth=1, alpha=0.5)
            ax.text(
                0.02,
                0.95,
                f'μ={mean_val:.4f}, σ={std_val:.4f}',
                transform=ax.transAxes,
                fontsize=8,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
            )

    axes[-1].set_xlabel('Time', fontsize=10)
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()

    return fig


def plot_weights(
    d: float = 0.5, threshold: float = 1e-5, figsize: Tuple[int, int] = (12, 6)
) -> plt.Figure:
    """
    Plot fractional differentiation weights.

    Args:
        d: Differentiation order
        threshold: Weight cutoff threshold
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> fig = plot_weights(d=0.5)
        >>> plt.show()
    """
    fd = FractionalDifferentiation(threshold=threshold)
    weights = fd.get_weights(d, threshold)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Plot weights
    axes[0].bar(range(len(weights)), weights, width=0.8, alpha=0.7)
    axes[0].axhline(0, color='black', linestyle='-', linewidth=0.5)
    axes[0].set_title(f'Fractional Differentiation Weights (d={d})', fontweight='bold')
    axes[0].set_xlabel('Lag', fontsize=10)
    axes[0].set_ylabel('Weight', fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # Plot log absolute weights
    axes[1].semilogy(
        range(len(weights)), np.abs(weights), marker='o', markersize=3, linewidth=1.5, alpha=0.7
    )
    axes[1].axhline(
        threshold, color='red', linestyle='--', linewidth=1.5, label=f'Threshold={threshold}'
    )
    axes[1].set_title(f'Weight Decay (d={d})', fontweight='bold')
    axes[1].set_xlabel('Lag', fontsize=10)
    axes[1].set_ylabel('|Weight| (log scale)', fontsize=10)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_memory_preservation(
    series: pd.Series,
    d_values: List[float] = None,
    max_lag: int = 20,
    figsize: Tuple[int, int] = (12, 8),
) -> plt.Figure:
    """
    Plot autocorrelation function to visualize memory preservation.

    Args:
        series: Time series to analyze
        d_values: List of d values to compare
        max_lag: Maximum lag for ACF
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> fig = plot_memory_preservation(series, d_values=[0.0, 0.3, 0.5, 1.0])
        >>> plt.show()
    """
    if d_values is None:
        d_values = [0.0, 0.3, 0.5, 0.7, 1.0]

    fd = FractionalDifferentiation()

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Plot ACF for each d value
    for d in d_values:
        if d == 0.0:
            diff_series = series
        else:
            diff_series = fd.fractional_diff(series, d=d)

        clean_series = diff_series.dropna()
        if len(clean_series) < max_lag + 10:
            continue

        # Calculate ACF
        acf_values = [
            clean_series.autocorr(lag=lag) if lag < len(clean_series) else 0
            for lag in range(max_lag + 1)
        ]

        # Plot ACF
        axes[0].plot(
            range(max_lag + 1),
            acf_values,
            marker='o',
            markersize=4,
            linewidth=2,
            alpha=0.7,
            label=f'd={d:.1f}',
        )

    axes[0].axhline(0, color='black', linestyle='-', linewidth=0.5)
    axes[0].axhline(
        1.96 / np.sqrt(len(series.dropna())),
        color='red',
        linestyle='--',
        linewidth=1,
        alpha=0.5,
        label='95% CI',
    )
    axes[0].axhline(
        -1.96 / np.sqrt(len(series.dropna())), color='red', linestyle='--', linewidth=1, alpha=0.5
    )
    axes[0].set_title('Autocorrelation Function', fontweight='bold')
    axes[0].set_xlabel('Lag', fontsize=10)
    axes[0].set_ylabel('Correlation', fontsize=10)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot memory preservation vs d
    d_tested = []
    memory_preserved = []

    for d in np.linspace(0, 1, 21):
        if d == 0.0:
            diff_series = series
        else:
            diff_series = fd.fractional_diff(series, d=d)

        memory_metrics = fd.calculate_memory_loss(series, diff_series)
        d_tested.append(d)
        memory_preserved.append(memory_metrics['memory_preservation_ratio'])

    axes[1].plot(d_tested, memory_preserved, linewidth=2, marker='o', markersize=5)
    axes[1].fill_between(d_tested, memory_preserved, alpha=0.3)
    axes[1].set_title('Memory Preservation vs Differentiation Order', fontweight='bold')
    axes[1].set_xlabel('Differentiation Order (d)', fontsize=10)
    axes[1].set_ylabel('Memory Preservation Ratio', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(0, 1.05)

    plt.tight_layout()
    return fig


def plot_stationarity_test(
    series: pd.Series,
    d_range: Tuple[float, float] = (0.0, 1.0),
    n_points: int = 21,
    figsize: Tuple[int, int] = (12, 6),
) -> plt.Figure:
    """
    Plot ADF test p-values across different d values.

    Args:
        series: Time series to analyze
        d_range: Range of d values to test (min, max)
        n_points: Number of d values to test
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> fig = plot_stationarity_test(series)
        >>> plt.show()
    """
    fd = FractionalDifferentiation()

    d_values = np.linspace(d_range[0], d_range[1], n_points)
    p_values = []
    adf_stats = []

    for d in d_values:
        if d == 0.0:
            diff_series = series
        else:
            diff_series = fd.fractional_diff(series, d=d)

        clean_series = diff_series.dropna()

        if len(clean_series) < 50:
            p_values.append(1.0)
            adf_stats.append(0)
            continue

        try:
            from app.core.statsmodels_fallback import adfuller

            adf_result = adfuller(clean_series, maxlag=1)
            p_values.append(adf_result[1])
            adf_stats.append(adf_result[0])
        except:
            p_values.append(1.0)
            adf_stats.append(0)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Plot p-values
    axes[0].plot(d_values, p_values, linewidth=2, marker='o', markersize=5, color='blue')
    axes[0].axhline(
        fd.adfuller_alpha,
        color='red',
        linestyle='--',
        linewidth=2,
        label=f'Significance level (α={fd.adfuller_alpha})',
    )
    axes[0].fill_between(
        d_values,
        0,
        p_values,
        where=[p < fd.adfuller_alpha for p in p_values],
        alpha=0.3,
        color='green',
        label='Stationary region',
    )
    axes[0].set_title('ADF Test P-Value vs Differentiation Order', fontweight='bold')
    axes[0].set_xlabel('Differentiation Order (d)', fontsize=10)
    axes[0].set_ylabel('P-Value', fontsize=10)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-0.05, 1.05)

    # Plot ADF statistics
    axes[1].plot(d_values, adf_stats, linewidth=2, marker='o', markersize=5, color='green')
    axes[1].axhline(0, color='black', linestyle='-', linewidth=0.5)
    axes[1].set_title('ADF Test Statistic vs Differentiation Order', fontweight='bold')
    axes[1].set_xlabel('Differentiation Order (d)', fontsize=10)
    axes[1].set_ylabel('ADF Statistic', fontsize=10)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_optimal_d_search(
    series: pd.Series, min_d: float = 0.0, max_d: float = 1.0, figsize: Tuple[int, int] = (14, 8)
) -> plt.Figure:
    """
    Visualize the optimal d search process.

    Args:
        series: Time series to analyze
        min_d: Minimum d to search
        max_d: Maximum d to search
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> fig = plot_optimal_d_search(series)
        >>> plt.show()
    """
    fd = FractionalDifferentiation()
    optimal_d, p_value, metadata = fd.find_optimal_d(
        series, min_d=min_d, max_d=max_d, method='grid'
    )

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Original series
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(series.index, series.values, linewidth=1, alpha=0.8)
    ax1.set_title('Original Series', fontweight='bold')
    ax1.set_ylabel('Value', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Optimally fractionally differenced series
    ax2 = fig.add_subplot(gs[1, :])
    diff_series = fd.fractional_diff(series, d=optimal_d)
    ax2.plot(diff_series.index, diff_series.values, linewidth=1, alpha=0.8, color='green')
    ax2.set_title(
        f'Fractionally Differentiated (d={optimal_d:.3f}, p={p_value:.4f})', fontweight='bold'
    )
    ax2.set_ylabel('Value', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # Plot 3: P-value vs d
    ax3 = fig.add_subplot(gs[2, 0])
    d_values = [entry['d'] for entry in metadata['test_history']]
    p_values = [entry['p_value'] for entry in metadata['test_history']]
    [entry['stationary'] for entry in metadata['test_history']]

    ax3.plot(d_values, p_values, linewidth=2, marker='o', markersize=5)
    ax3.axhline(
        fd.adfuller_alpha, color='red', linestyle='--', linewidth=2, label=f'α={fd.adfuller_alpha}'
    )
    ax3.scatter(
        [optimal_d], [p_value], color='green', s=200, zorder=5, label=f'Optimal d={optimal_d:.3f}'
    )
    ax3.set_title('Stationarity Search', fontweight='bold')
    ax3.set_xlabel('d', fontsize=9)
    ax3.set_ylabel('P-Value', fontsize=9)
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Plot 4: Memory preservation
    ax4 = fig.add_subplot(gs[2, 1])
    d_tested = []
    memory_ratios = []

    for d in np.linspace(0, 1, 21):
        if d == 0.0:
            test_diff = series
        else:
            test_diff = fd.fractional_diff(series, d=d)

        memory_metrics = fd.calculate_memory_loss(series, test_diff)
        d_tested.append(d)
        memory_ratios.append(memory_metrics['memory_preservation_ratio'])

    ax4.plot(d_tested, memory_ratios, linewidth=2, marker='o', markersize=5, color='orange')
    ax4.axvline(
        optimal_d, color='green', linestyle='--', linewidth=2, label=f'Optimal d={optimal_d:.3f}'
    )
    ax4.set_title('Memory Preservation', fontweight='bold')
    ax4.set_xlabel('d', fontsize=9)
    ax4.set_ylabel('Memory Ratio', fontsize=9)
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 1.05)

    fig.suptitle('Optimal Fractional Differentiation Search', fontsize=14, fontweight='bold')

    return fig


def plot_multi_feature_analysis(
    df: pd.DataFrame,
    features: List[str] = None,
    d: float = 0.5,
    figsize: Tuple[int, int] = (14, 10),
) -> plt.Figure:
    """
    Analyze fractional differentiation across multiple features.

    Args:
        df: DataFrame with features
        features: List of feature names (None = all numeric)
        d: Differentiation order
        figsize: Figure size

    Returns:
        matplotlib Figure object

    Example:
        >>> df = pd.DataFrame({
        ...     'price': np.random.randn(1000).cumsum(),
        ...     'volume': np.random.randint(100, 1000, 1000),
        ...     'returns': np.random.randn(1000) * 0.02
        ... })
        >>> fig = plot_multi_feature_analysis(df, d=0.3)
        >>> plt.show()
    """
    if features is None:
        features = df.select_dtypes(include=[np.number]).columns.tolist()[:5]

    fd = FractionalDifferentiation()

    n_features = len(features)
    fig, axes = plt.subplots(n_features, 2, figsize=figsize)

    if n_features == 1:
        axes = axes.reshape(1, -1)

    for idx, feature in enumerate(features):
        if feature not in df.columns:
            continue

        series = df[feature].dropna()

        # Original series
        axes[idx, 0].plot(series.index, series.values, linewidth=1, alpha=0.8)
        axes[idx, 0].set_title(f'{feature} - Original', fontweight='bold')
        axes[idx, 0].set_ylabel('Value', fontsize=9)
        axes[idx, 0].grid(True, alpha=0.3)

        # Fractionally differenced series
        diff_series = fd.fractional_diff(series, d=d)
        axes[idx, 1].plot(
            diff_series.index, diff_series.values, linewidth=1, alpha=0.8, color='green'
        )
        axes[idx, 1].set_title(f'{feature} - Fractionally Diff (d={d})', fontweight='bold')
        axes[idx, 1].set_ylabel('Value', fontsize=9)
        axes[idx, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def create_summary_report(
    series: pd.Series, d_values: List[float] = None, save_path: Optional[str] = None
) -> plt.Figure:
    """
    Create a comprehensive summary report for fractional differentiation analysis.

    Args:
        series: Time series to analyze
        d_values: List of d values to analyze
        save_path: Path to save the figure (optional)

    Returns:
        matplotlib Figure object

    Example:
        >>> series = pd.Series(np.random.randn(1000).cumsum())
        >>> fig = create_summary_report(series, save_path='fracdiff_report.png')
    """
    if d_values is None:
        d_values = [0.0, 0.3, 0.5, 0.7, 1.0]

    fd = FractionalDifferentiation()

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # 1. Original series
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(series.index, series.values, linewidth=1, alpha=0.8)
    ax1.set_title('Original Time Series', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Value', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # 2. Comparison of different d values
    ax2 = fig.add_subplot(gs[1, 0])
    for d in [0.0, 0.5, 1.0]:
        if d == 0.0:
            plot_series = series
            label = 'Original'
        else:
            plot_series = fd.fractional_diff(series, d=d)
            label = f'd={d:.1f}'

        clean_series = plot_series.dropna()
        ax2.plot(clean_series.index, clean_series.values, linewidth=1, alpha=0.7, label=label)

    ax2.set_title('Differentiation Comparison', fontweight='bold', fontsize=11)
    ax2.set_ylabel('Value', fontsize=10)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # 3. Weights visualization
    ax3 = fig.add_subplot(gs[1, 1])
    weights = fd.get_weights(d=0.5)
    ax3.bar(range(len(weights)), weights, width=0.8, alpha=0.7)
    ax3.set_title(f'Weights (d=0.5, n={len(weights)})', fontweight='bold', fontsize=11)
    ax3.set_xlabel('Lag', fontsize=10)
    ax3.set_ylabel('Weight', fontsize=10)
    ax3.grid(True, alpha=0.3)

    # 4. Stationarity test results
    ax4 = fig.add_subplot(gs[2, 0])
    comparison = fd.compare_d_values(series, d_values=d_values)

    colors = ['green' if s else 'red' for s in comparison['is_stationary']]
    ax4.bar(comparison['d'], comparison['p_value'], width=0.08, color=colors, alpha=0.7)
    ax4.axhline(
        fd.adfuller_alpha, color='red', linestyle='--', linewidth=2, label=f'α={fd.adfuller_alpha}'
    )
    ax4.set_title('Stationarity Test Results', fontweight='bold', fontsize=11)
    ax4.set_xlabel('d', fontsize=10)
    ax4.set_ylabel('P-Value', fontsize=10)
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')

    # 5. Memory preservation
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(
        comparison['d'],
        comparison['memory_preservation'],
        linewidth=2,
        marker='o',
        markersize=6,
        color='orange',
    )
    ax5.fill_between(comparison['d'], comparison['memory_preservation'], alpha=0.3)
    ax5.set_title('Memory Preservation', fontweight='bold', fontsize=11)
    ax5.set_xlabel('d', fontsize=10)
    ax5.set_ylabel('Memory Ratio', fontsize=10)
    ax5.grid(True, alpha=0.3)
    ax5.set_ylim(0, 1.05)

    # 6. Summary statistics table
    ax6 = fig.add_subplot(gs[3, :])
    ax6.axis('off')

    # Create summary table
    summary_data = []
    # Use itertuples instead of iterrows for better performance
    for row in comparison.itertuples():
        summary_data.append(
            [
                f"d={row.d:.1f}",
                f"{row.p_value:.4f}",
                "Yes" if row.is_stationary else "No",
                f"{row.memory_preservation:.3f}",
                f"{row.memory_loss_pct:.1f}%",
            ]
        )

    table = ax6.table(
        cellText=summary_data,
        colLabels=['d', 'P-Value', 'Stationary', 'Memory Ratio', 'Memory Loss'],
        cellLoc='center',
        loc='center',
        colWidths=[0.15, 0.2, 0.15, 0.25, 0.25],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Style header row
    for i in range(5):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')

    ax6.set_title('Summary Statistics', fontweight='bold', fontsize=11, y=0.9)

    fig.suptitle(
        'Fractional Differentiation Analysis Report', fontsize=16, fontweight='bold', y=0.995
    )

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.debug(f"Report saved to {save_path}")

    return fig
