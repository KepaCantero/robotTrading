"""
Meta-Labeling Position Sizing Example

Demonstrates the integration of López de Prado's meta-labeling framework
with the position sizing engine for ML-based bet sizing.

This example shows:
1. Training a meta-labeling model
2. Using meta-model probabilities for position sizing
3. Hybrid approach (meta-labeling + Kelly criterion)
4. Risk management integration

Based on:
- López de Prado, "Advances in Financial Machine Learning", Chapter 3 (Meta-Labeling)
- López de Prado, "Advances in Financial Machine Learning", Chapter 10 (Bet Sizing)
"""

import numpy as np
from decimal import Decimal

from app.services.position_sizing_engine import (
    MetaLabelingPositionSizer,
    PositionSizingEngineWithMetaLabeling,
)


def generate_sample_data(n_samples: int = 1000, n_features: int = 10, random_state: int = 42):
    """
    Generate synthetic trading data for demonstration.

    Args:
        n_samples: Number of samples
        n_features: Number of features
        random_state: Random seed

    Returns:
        Tuple of (X_train, y_train, X_test, y_test, expected_returns_test)
    """
    np.random.seed(random_state)

    # Generate features
    X = np.random.randn(n_samples, n_features)

    # Generate labels (-1, 0, 1) based on feature combinations
    # Simulate a weak signal
    signal_strength = X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2]
    y = np.zeros(n_samples)

    # Top 30% get signal 1 (buy)
    y[signal_strength > np.percentile(signal_strength, 70)] = 1

    # Bottom 30% get signal -1 (sell)
    y[signal_strength < np.percentile(signal_strength, 30)] = -1

    # Middle 40% get signal 0 (hold)

    # Generate expected returns (higher for correct predictions)
    expected_returns = np.random.randn(n_samples) * 0.02  # 2% std

    # Split into train/test
    split = int(0.8 * n_samples)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    expected_returns_test = expected_returns[split:]

    return X_train, y_train, X_test, y_test, expected_returns_test


def example_1_basic_meta_labeling_sizing():
    """
    Example 1: Basic meta-labeling position sizing.

    Shows how to use meta-model probabilities to size positions.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Meta-Labeling Position Sizing")
    print("=" * 80)

    # Generate sample data
    X_train, y_train, X_test, y_test, expected_returns = generate_sample_data()

    # Initialize meta-labeling position sizer
    sizer = MetaLabelingPositionSizer(
        config={
            "bet_sizing_method": "meta_kelly",  # Use Kelly criterion with meta-probabilities
            "confidence_threshold": 0.5,  # Only trade when meta-model is confident
            "max_bet_size": 0.25,  # Maximum 25% position size
            "min_bet_size": 0.01,  # Minimum 1% position size
        }
    )

    # Fit meta-model
    print("\nTraining meta-labeling model...")
    result = sizer.fit_meta_model(X_train, y_train, X_test, y_test)

    print(f"\nMeta-Model Performance:")
    print(f"  Primary Model Accuracy: {result['metrics']['primary_accuracy']:.2%}")
    print(f"  Meta-Model Accuracy: {result['metrics']['meta_accuracy']:.2%}")
    print(f"  Combined Accuracy: {result['metrics']['combined_accuracy']:.2%}")

    # Calculate position sizes using meta-labeling
    print("\nCalculating position sizes using meta-labeling...")
    position_sizes = sizer.calculate_position_size(
        signals=y_test,
        meta_proba=result["meta_proba"],
        expected_returns=expected_returns,
        capital=Decimal("10000"),
    )

    # Analyze results
    n_trades = (position_sizes != 0).sum()
    avg_long_size = (
        position_sizes[position_sizes > 0].mean() if (position_sizes > 0).sum() > 0 else 0
    )
    avg_short_size = (
        position_sizes[position_sizes < 0].mean() if (position_sizes < 0).sum() > 0 else 0
    )
    total_exposure = np.abs(position_sizes).sum()

    print(f"\nPosition Sizing Results:")
    print(f"  Total signals: {len(y_test)}")
    print(f"  Trades taken: {n_trades} ({n_trades / len(y_test) * 100:.1f}%)")
    print(f"  Average long position: {avg_long_size:.2%}")
    print(f"  Average short position: {avg_short_size:.2%}")
    print(f"  Total exposure: {total_exposure:.2%}")

    # Show sample positions
    print(f"\nSample Positions (first 10):")
    print("  Signal | Meta-Proba | Position Size | Expected Return")
    print("  -------|------------|---------------|----------------")
    for i in range(min(10, len(y_test))):
        print(
            f"  {y_test[i]:6d} | {result['meta_proba'][i]:10.2%} | "
            f"{position_sizes[i]:13.2%} | {expected_returns[i]:14.2%}"
        )


def example_2_hybrid_meta_kelly():
    """
    Example 2: Hybrid meta-labeling + Kelly criterion.

    Combines meta-labeling filtering with Kelly criterion sizing.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Hybrid Meta-Labeling + Kelly Criterion")
    print("=" * 80)

    # Generate sample data
    X_train, y_train, X_test, y_test, expected_returns = generate_sample_data()

    # Initialize extended position sizing engine
    engine = PositionSizingEngineWithMetaLabeling()

    # Simulate historical performance for Kelly calculation
    win_rate = 0.55  # 55% win rate
    avg_win = 100.0  # Average win: $100
    avg_loss = 75.0  # Average loss: $75
    capital = Decimal("10000")  # $10,000 capital

    print(f"\nHistorical Performance:")
    print(f"  Win Rate: {win_rate:.2%}")
    print(f"  Average Win: ${avg_win:.2f}")
    print(f"  Average Loss: ${avg_loss:.2f}")
    print(f"  Capital: ${capital}")

    # Calculate Kelly fraction
    kelly_result = engine.calculate_kelly_position_size(
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        capital=capital,
    )

    print(f"\nKelly Criterion Results:")
    print(f"  Raw Kelly: {kelly_result['kelly_fraction']:.4f}")
    print(f"  Half-Kelly (capped): {kelly_result['half_kelly_fraction']:.4f}")
    print(f"  Position Value: ${kelly_result['position_value']:.2f}")
    print(f"  Recommendation: {kelly_result['recommendation']}")

    # Fit meta-model
    print("\nTraining meta-labeling model...")
    result = engine.meta_sizer.fit_meta_model(X_train, y_train, X_test, y_test)

    # Calculate hybrid position sizes
    print("\nCalculating hybrid position sizes...")
    hybrid_result = engine.calculate_hybrid_sizes(
        signals=y_test,
        meta_proba=result["meta_proba"],
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        capital=capital,
        expected_returns=expected_returns,
    )

    # Analyze results
    position_sizes = hybrid_result["position_sizes"]
    filter_mask = hybrid_result["filter_mask"]
    kelly_fraction = hybrid_result["kelly_fraction"]

    n_filtered = filter_mask.sum()
    n_trades = (position_sizes != 0).sum()
    avg_size = np.abs(position_sizes[position_sizes != 0]).mean() if n_trades > 0 else 0

    print(f"\nHybrid Position Sizing Results:")
    print(f"  Kelly Cap: {kelly_fraction:.2%}")
    print(f"  Signals passing meta-filter: {n_filtered} ({n_filtered / len(y_test) * 100:.1f}%)")
    print(f"  Final trades taken: {n_trades} ({n_trades / len(y_test) * 100:.1f}%)")
    print(f"  Average position size: {avg_size:.2%}")

    # Show sample positions
    print(f"\nSample Positions (first 10):")
    print("  Signal | Meta-Proba | Filter | Meta-Size | Kelly-Cap | Final Size")
    print("  -------|------------|--------|-----------|-----------|-----------")
    for i in range(min(10, len(y_test))):
        print(
            f"  {y_test[i]:6d} | {result['meta_proba'][i]:10.2%} | "
            f"{'Yes' if filter_mask[i] else 'No ':6} | "
            f"{hybrid_result['meta_sizes'][i]:9.2%} | "
            f"{kelly_fraction:9.2%} | {position_sizes[i]:10.2%}"
        )


def example_3_different_bet_sizing_methods():
    """
    Example 3: Comparing different bet sizing methods.

    Compares meta_kelly, meta_probability, and meta_expected_value methods.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Comparing Bet Sizing Methods")
    print("=" * 80)

    # Generate sample data
    X_train, y_train, X_test, y_test, expected_returns = generate_sample_data()

    # Fit meta-model once
    sizer = MetaLabelingPositionSizer()
    result = sizer.fit_meta_model(X_train, y_train, X_test, y_test)

    methods = ["meta_kelly", "meta_probability", "meta_expected_value"]

    print(f"\nComparing bet sizing methods:")
    print(f"  Meta-Model Accuracy: {result['metrics']['meta_accuracy']:.2%}")
    print()

    for method in methods:
        # Update sizer configuration
        sizer.bet_sizing_method = method

        # Calculate position sizes
        position_sizes = sizer.calculate_position_size(
            signals=y_test,
            meta_proba=result["meta_proba"],
            expected_returns=expected_returns,
        )

        # Analyze
        n_trades = (position_sizes != 0).sum()
        avg_size = np.abs(position_sizes[position_sizes != 0]).mean() if n_trades > 0 else 0
        total_exposure = np.abs(position_sizes).sum()

        print(
            f"{method:20} | Trades: {n_trades:3} | Avg Size: {avg_size:6.2%} | Exposure: {total_exposure:5.2%}"
        )


def example_4_confidence_threshold_impact():
    """
    Example 4: Impact of confidence threshold on position sizing.

    Shows how different confidence thresholds affect trading behavior.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Confidence Threshold Impact")
    print("=" * 80)

    # Generate sample data
    X_train, y_train, X_test, y_test, expected_returns = generate_sample_data()

    # Fit meta-model once
    sizer = MetaLabelingPositionSizer()
    result = sizer.fit_meta_model(X_train, y_train, X_test, y_test)

    thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]

    print(f"\nImpact of confidence threshold on trading:")
    print()

    for threshold in thresholds:
        # Update sizer configuration
        sizer.confidence_threshold = threshold

        # Calculate position sizes
        position_sizes = sizer.calculate_position_size(
            signals=y_test,
            meta_proba=result["meta_proba"],
            expected_returns=expected_returns,
        )

        # Analyze
        n_trades = (position_sizes != 0).sum()
        avg_size = np.abs(position_sizes[position_sizes != 0]).mean() if n_trades > 0 else 0
        total_exposure = np.abs(position_sizes).sum()
        avg_confidence = result["meta_proba"][position_sizes != 0].mean() if n_trades > 0 else 0

        print(
            f"Threshold {threshold:.1f} | Trades: {n_trades:3} ({n_trades / len(y_test) * 100:5.1f}%) | "
            f"Avg Size: {avg_size:5.2%} | Exposure: {total_exposure:5.2%} | "
            f"Avg Confidence: {avg_confidence:.2%}"
        )


def example_5_risk_management_integration():
    """
    Example 5: Risk management integration with meta-labeling.

    Shows how to combine meta-labeling with traditional risk management.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Risk Management Integration")
    print("=" * 80)

    # Generate sample data
    X_train, y_train, X_test, y_test, expected_returns = generate_sample_data()

    # Initialize extended engine
    engine = PositionSizingEngineWithMetaLabeling()

    # Configure meta-labeling sizer with risk limits
    engine.meta_sizer.config = {
        "bet_sizing_method": "meta_kelly",
        "confidence_threshold": 0.5,
        "max_bet_size": 0.10,  # Maximum 10% per position
        "min_bet_size": 0.01,
    }

    # Fit meta-model
    result = engine.meta_sizer.fit_meta_model(X_train, y_train, X_test, y_test)

    # Calculate position sizes with meta-labeling
    position_sizes = engine.calculate_meta_labeling_sizes(
        signals=y_test,
        meta_proba=result["meta_proba"],
        expected_returns=expected_returns,
        capital=Decimal("10000"),
    )

    # Apply position limits
    max_position_limit = 0.15  # 15% max per position
    max_portfolio_exposure = 0.80  # 80% max total exposure

    print(f"\nRisk Management Parameters:")
    print(f"  Max Position Limit: {max_position_limit:.2%}")
    print(f"  Max Portfolio Exposure: {max_portfolio_exposure:.2%}")

    # Apply position limit
    position_sizes_capped = np.clip(position_sizes, -max_position_limit, max_position_limit)

    # Apply portfolio exposure limit
    total_exposure = np.abs(position_sizes_capped).sum()
    if total_exposure > max_portfolio_exposure:
        scale_factor = max_portfolio_exposure / total_exposure
        position_sizes_final = position_sizes_capped * scale_factor
        print(f"  Applied exposure scaling: {scale_factor:.4f}")
    else:
        position_sizes_final = position_sizes_capped
        print(f"  No exposure scaling needed")

    # Analyze final results
    n_trades = (position_sizes_final != 0).sum()
    avg_long_size = (
        position_sizes_final[position_sizes_final > 0].mean()
        if (position_sizes_final > 0).sum() > 0
        else 0
    )
    avg_short_size = (
        position_sizes_final[position_sizes_final < 0].mean()
        if (position_sizes_final < 0).sum() > 0
        else 0
    )
    total_exposure_final = np.abs(position_sizes_final).sum()

    print(f"\nFinal Position Sizing Results:")
    print(f"  Trades taken: {n_trades}")
    print(f"  Average long position: {avg_long_size:.2%}")
    print(f"  Average short position: {avg_short_size:.2%}")
    print(f"  Total exposure: {total_exposure_final:.2%}")
    print(f"  Remaining capital: {1 - total_exposure_final:.2%}")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("META-LABELING POSITION SIZING EXAMPLES")
    print("López de Prado Financial ML Integration")
    print("=" * 80)

    try:
        example_1_basic_meta_labeling_sizing()
        example_2_hybrid_meta_kelly()
        example_3_different_bet_sizing_methods()
        example_4_confidence_threshold_impact()
        example_5_risk_management_integration()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
