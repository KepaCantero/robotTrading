"""
Triple Barrier Method Example - Financial ML Labeling

This example demonstrates how to use the Triple Barrier Method for generating
labels for machine learning in finance, following Marcos López de Prado's approach.

The Triple Barrier Method provides superior labels compared to fixed-time returns by:
1. Accounting for volatility (wider stops for volatile assets)
2. Incorporating risk-reward ratios
3. Reflecting realistic trading scenarios

Usage:
    python examples/triple_barrier_example.py
"""

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.backtesting.labeling.triple_barrier import (
    TripleBarrierConfig,
    TripleBarrierLabeler,
    plot_triple_barrier,
    triple_barrier_method,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_synthetic_data(
    n_days: int = 500,
    starting_price: float = 100.0,
    trend: float = 0.0005,
    volatility: float = 0.015,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic price data for demonstration.

    Args:
        n_days: Number of days of data
        starting_price: Initial price
        trend: Daily drift (trend)
        volatility: Daily volatility
        seed: Random seed for reproducibility

    Returns:
        DataFrame with date, close, and returns columns
    """
    np.random.seed(seed)

    # Generate price path using geometric Brownian motion
    dates = pd.date_range(start="2020-01-01", periods=n_days, freq="D")

    # Generate returns
    daily_returns = np.random.normal(trend, volatility, n_days)

    # Calculate prices
    prices = starting_price * np.exp(np.cumsum(daily_returns))

    # Create DataFrame
    df = pd.DataFrame({"date": dates, "close": prices})
    df.set_index("date", inplace=True)

    # Calculate returns
    df["returns"] = df["close"].pct_change()
    df["returns"].fillna(0, inplace=True)

    logger.info(f"Generated synthetic data: {len(df)} days from {df.index[0]} to {df.index[-1]}")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    return df


def generate_simple_signals(prices: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Generate simple momentum signals for demonstration.

    A signal is generated when price crosses above/below the moving average.

    Args:
        prices: Price series
        lookback: Lookback period for moving average

    Returns:
        Series of signal dates
    """
    # Calculate moving average
    ma = prices.rolling(window=lookback).mean()

    # Generate signals: price crosses above MA
    signals = []

    for i in range(lookback, len(prices) - 1):
        # Previous: price below MA, Current: price above MA
        if prices.iloc[i - 1] < ma.iloc[i - 1] and prices.iloc[i] >= ma.iloc[i]:
            signals.append(prices.index[i])

    return pd.Series(signals)


def example_basic_usage():
    """
    Example 1: Basic Triple Barrier Method usage.

    This demonstrates the simplest way to apply triple barrier labeling.
    """
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: Basic Triple Barrier Method")
    logger.info("=" * 80)

    # Generate synthetic data
    df = generate_synthetic_data(n_days=500, trend=0.0005, volatility=0.015)

    # Generate simple signals
    signals = generate_simple_signals(df["close"])

    logger.info(f"\nGenerated {len(signals)} trading signals")

    # Apply triple barrier labeling
    labels = triple_barrier_method(
        prices=df["close"],
        events=signals,
        upper_barrier_pct=0.02,  # 2% profit target
        lower_barrier_pct=-0.01,  # 1% stop loss
        vertical_barrier_days=5,  # 5-day maximum holding period
        vol_scaling=False,  # Use fixed barriers for simplicity
    )

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("LABEL DISTRIBUTION")
    logger.info("=" * 80)

    label_counts = labels["label"].value_counts().sort_index()
    label_names = {1: "Upper (Profit)", -1: "Lower (Stop)", 0: "Vertical (Time)"}

    for label, count in label_counts.items():
        name = label_names.get(label, f"Label {label}")
        pct = count / len(labels) * 100
        logger.info(f"{name:20s}: {count:4d} ({pct:5.1f}%)")

    # Display average holding periods
    logger.info("\n" + "=" * 80)
    logger.info("AVERAGE HOLDING PERIOD (bars)")
    logger.info("=" * 80)

    avg_holding = labels.groupby("label")["bars_to_barrier"].mean()

    for label, avg_bars in avg_holding.items():
        name = label_names.get(label, f"Label {label}")
        logger.info(f"{name:20s}: {avg_bars:.2f} bars")

    return df, signals, labels


def example_volatility_scaling():
    """
    Example 2: Volatility-adjusted barriers.

    This demonstrates dynamic barrier adjustment based on market volatility.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 2: Volatility-Adjusted Barriers")
    logger.info("=" * 80)

    # Generate data with changing volatility
    df = generate_synthetic_data(n_days=500, trend=0.0005, volatility=0.015)

    # Add volatility regime changes
    vol_regime = np.ones(len(df))
    vol_regime[:100] = 0.5  # Low vol
    vol_regime[100:250] = 2.0  # High vol
    vol_regime[250:] = 1.0  # Normal vol

    # Apply volatility scaling
    df["close"] = 100 + np.cumsum(np.random.randn(500) * 0.01 * vol_regime)

    # Generate signals
    signals = generate_simple_signals(df["close"])

    # Compare fixed vs dynamic barriers
    config = TripleBarrierConfig(
        upper_barrier_pct=0.02,
        lower_barrier_pct=-0.01,
        vertical_barrier_days=5,
        vol_window=20,
        vol_scale=1.5,
    )

    labeler = TripleBarrierLabeler(config)

    # Fixed barriers
    labels_fixed = labeler.fit_transform(df["close"], signals, vol_scaling=False)

    # Dynamic barriers (volatility-adjusted)
    labels_dynamic = labeler.fit_transform(df["close"], signals, vol_scaling=True)

    # Calculate average barrier widths
    logger.info("\nBarrier Width Comparison:")
    logger.info("-" * 80)

    avg_upper_fixed = labels_fixed["upper_barrier_pct"].mean()
    avg_lower_fixed = labels_fixed["lower_barrier_pct"].mean()
    logger.info(f"Fixed barriers - Upper: {avg_upper_fixed:+.2%}, Lower: {avg_lower_fixed:+.2%}")

    avg_upper_dynamic = labels_dynamic["upper_barrier_pct"].mean()
    avg_lower_dynamic = labels_dynamic["lower_barrier_pct"].mean()
    logger.info(
        f"Dynamic barriers - Upper: {avg_upper_dynamic:+.2%}, Lower: {avg_lower_dynamic:+.2%}"
    )

    logger.info(
        f"Vol scaling factor: Upper: {avg_upper_dynamic/avg_upper_fixed:.2f}x, "
        f"Lower: {avg_lower_dynamic/avg_lower_fixed:.2f}x"
    )

    return df, signals, labels_fixed, labels_dynamic


def example_custom_configuration():
    """
    Example 3: Custom configuration for different strategies.

    This demonstrates how to configure barriers for different trading styles.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 3: Custom Configuration for Different Strategies")
    logger.info("=" * 80)

    df = generate_synthetic_data(n_days=500, trend=0.0005, volatility=0.015)
    signals = generate_simple_signals(df["close"])

    # Define different strategy configurations
    strategies = {
        "Conservative": TripleBarrierConfig(
            upper_barrier_pct=0.01,  # 1% profit target
            lower_barrier_pct=-0.005,  # 0.5% stop loss (2:1 reward-risk)
            vertical_barrier_days=10,
        ),
        "Balanced": TripleBarrierConfig(
            upper_barrier_pct=0.02,  # 2% profit target
            lower_barrier_pct=-0.01,  # 1% stop loss (2:1 reward-risk)
            vertical_barrier_days=5,
        ),
        "Aggressive": TripleBarrierConfig(
            upper_barrier_pct=0.04,  # 4% profit target
            lower_barrier_pct=-0.02,  # 2% stop loss (2:1 reward-risk)
            vertical_barrier_days=3,
        ),
    }

    results = {}

    for strategy_name, config in strategies.items():
        labeler = TripleBarrierLabeler(config)
        labels = labeler.fit_transform(df["close"], signals)

        results[strategy_name] = {
            "config": config,
            "labels": labels,
            "win_rate": (labels["label"] == 1).sum() / len(labels),
            "avg_holding": labels["bars_to_barrier"].mean(),
        }

        logger.info(f"\n{strategy_name} Strategy:")
        logger.info(f"  Config: {config.upper_barrier_pct:+.1%} / {config.lower_barrier_pct:+.1%} / {config.vertical_barrier_days}d")
        logger.info(f"  Win Rate: {results[strategy_name]['win_rate']:.1%}")
        logger.info(f"  Avg Holding: {results[strategy_name]['avg_holding']:.2f} bars")

    return df, signals, results


def example_visualization(df: pd.DataFrame, signals: pd.Series, labels: pd.DataFrame):
    """
    Example 4: Visualizing triple barrier labels.

    This demonstrates how to visualize barrier hits for analysis.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 4: Visualization of Triple Barrier Labels")
    logger.info("=" * 80)

    # Select a few examples of each barrier type
    upper_examples = labels[labels["label"] == 1].head(2)
    lower_examples = labels[labels["label"] == -1].head(2)
    vertical_examples = labels[labels["label"] == 0].head(2)

    examples_to_plot = [
        ("Upper Barrier (Profit)", upper_examples),
        ("Lower Barrier (Stop)", lower_examples),
        ("Vertical Barrier (Time)", vertical_examples),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle("Triple Barrier Method Examples", fontsize=14, fontweight="bold")

    for row, (title, examples) in enumerate(examples_to_plot):
        for col, (event_time, row_data) in enumerate(examples.iterrows()):
            if col >= 2:
                break

            ax = axes[row, col]

            # Get event index
            event_idx = df.index.get_loc(event_time)

            # Get barrier levels
            entry_price = row_data["entry_price"]
            upper_barrier = entry_price * (1 + row_data["upper_barrier_pct"])
            lower_barrier = entry_price * (1 + row_data["lower_barrier_pct"])
            vertical_barrier = row_data["bars_to_barrier"]
            label = row_data["label"]

            # Plot
            plot_triple_barrier(
                df["close"],
                event_idx,
                upper_barrier,
                lower_barrier,
                vertical_barrier,
                label,
                ax=ax,
            )

            ax.set_title(f"{title} - {event_time.strftime('%Y-%m-%d')}")

    plt.tight_layout()
    plt.savefig("/tmp/triple_barrier_examples.png", dpi=100, bbox_inches="tight")
    logger.info("\nVisualization saved to: /tmp/triple_barrier_examples.png")

    return fig


def example_ml_integration(df: pd.DataFrame, signals: pd.Series, labels: pd.DataFrame):
    """
    Example 5: Integration with ML pipeline.

    This demonstrates how to use triple barrier labels in an ML context.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 5: Integration with ML Pipeline")
    logger.info("=" * 80)

    # Generate features (simple technical indicators)
    features = pd.DataFrame(index=signals)

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # Moving averages
    ma_short = df["close"].rolling(window=10).mean()
    ma_long = df["close"].rolling(window=30).mean()

    # Align features with signals
    for signal_time in signals:
        if signal_time in rsi.index:
            features.loc[signal_time, "rsi"] = rsi.loc[signal_time]
            features.loc[signal_time, "ma_ratio"] = ma_short.loc[signal_time] / ma_long.loc[signal_time]
            features.loc[signal_time, "momentum_5"] = (
                df["close"].pct_change(5).loc[signal_time]
                if signal_time in df["close"].index
                else 0
            )

    features = features.dropna()

    # Get labels aligned with features
    ml_labels = labels.loc[features.index]

    # Create binary labels for classification
    y_binary = (ml_labels["label"] == 1).astype(int)

    logger.info(f"\nML Dataset:")
    logger.info(f"  Samples: {len(features)}")
    logger.info(f"  Features: {features.shape[1]}")
    logger.info(f"  Positive class (profit): {y_binary.sum()} ({y_binary.mean():.1%})")
    logger.info(f"  Negative class (loss/time): {(1 - y_binary).sum()} ({(1 - y_binary).mean():.1%})")

    # Display feature statistics
    logger.info(f"\nFeature Statistics:")
    logger.info(features.describe())

    return features, y_binary


def example_performance_comparison():
    """
    Example 6: Compare triple barrier vs fixed-time labels.

    This demonstrates the advantages of triple barrier labeling.
    """
    logger.info("\n" + "=" * 80)
    logger.info("EXAMPLE 6: Triple Barrier vs Fixed-Time Labels")
    logger.info("=" * 80)

    df = generate_synthetic_data(n_days=500, trend=0.0005, volatility=0.015)
    signals = generate_simple_signals(df["close"])

    # Triple barrier labels
    tb_labels = triple_barrier_method(
        df["close"],
        signals,
        upper_barrier_pct=0.02,
        lower_barrier_pct=-0.01,
        vertical_barrier_days=5,
    )

    # Fixed-time labels (5-day return)
    fixed_labels = []
    for signal_time in signals:
        signal_idx = df.index.get_loc(signal_time)
        end_idx = min(signal_idx + 5, len(df) - 1)

        entry_price = df["close"].iloc[signal_idx]
        exit_price = df["close"].iloc[end_idx]

        ret = (exit_price - entry_price) / entry_price
        fixed_labels.append(1 if ret > 0 else -1)

    fixed_labels = pd.Series(fixed_labels, index=signals.index)

    # Compare distributions
    logger.info("\nLabel Distribution Comparison:")
    logger.info("-" * 80)

    tb_dist = tb_labels["label"].value_counts(normalize=True)
    fixed_dist = fixed_labels.value_counts(normalize=True)

    logger.info(f"Triple Barrier:")
    logger.info(f"  Upper (Profit):  {tb_dist.get(1, 0):.1%}")
    logger.info(f"  Lower (Stop):    {tb_dist.get(-1, 0):.1%}")
    logger.info(f"  Vertical (Time): {tb_dist.get(0, 0):.1%}")

    logger.info(f"\nFixed-Time (5-day):")
    logger.info(f"  Profit: {fixed_dist.get(1, 0):.1%}")
    logger.info(f"  Loss:   {fixed_dist.get(-1, 0):.1%}")

    return df, signals, tb_labels, fixed_labels


def main():
    """
    Run all examples.
    """
    logger.info("\n" + "=" * 80)
    logger.info("TRIPLE BARRIER METHOD - FINANCIAL ML LABELING EXAMPLES")
    logger.info("Based on Marcos López de Prado's 'Advances in Financial Machine Learning'")
    logger.info("=" * 80)

    # Example 1: Basic usage
    df, signals, labels = example_basic_usage()

    # Example 2: Volatility scaling
    df, signals, labels_fixed, labels_dynamic = example_volatility_scaling()

    # Example 3: Custom configurations
    df, signals, results = example_custom_configuration()

    # Example 4: Visualization
    example_visualization(df, signals, labels)

    # Example 5: ML integration
    features, y_binary = example_ml_integration(df, signals, labels)

    # Example 6: Performance comparison
    df, signals, tb_labels, fixed_labels = example_performance_comparison()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info("\nKey Takeaways:")
    logger.info("1. Triple Barrier Method provides dynamic, volatility-aware labels")
    logger.info("2. Labels reflect realistic trading outcomes (profit/stop/time)")
    logger.info("3. Can be customized for different trading strategies")
    logger.info("4. Integrates seamlessly with ML pipelines")
    logger.info("5. Superior to fixed-time labeling for most trading applications")
    logger.info("\nFor more information, see:")
    logger.info("- López de Prado, M. (2018). Advances in Financial Machine Learning")
    logger.info("- Chapter 3: Sample Weights and Triple Barrier Method")


if __name__ == "__main__":
    main()
