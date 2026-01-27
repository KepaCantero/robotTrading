"""
Example: Train/Validation/Test Split for Backtesting

This example demonstrates how to use the data split functionality to prevent
overfitting and data snooping in backtesting.
"""

from datetime import datetime, timedelta
from app.backtesting.data_split import (
    DataSplit,
    TrainValTestSplitter,
    MultipleTestingCorrector,
    validate_out_of_sample_performance,
)


class MockBar:
    """Mock market data bar for demonstration."""

    def __init__(self, timestamp, close=100.0):
        self.timestamp = timestamp
        self.close = close


def example_basic_split():
    """Example 1: Basic train/validation/test split."""
    print("=" * 60)
    print("Example 1: Basic Train/Validation/Test Split")
    print("=" * 60)

    # Generate sample market data (1000 days)
    bars = [
        MockBar(datetime(2020, 1, 1) + timedelta(days=i), close=100 + i)
        for i in range(1000)
    ]

    # Create splitter with default configuration (70/15/15)
    splitter = TrainValTestSplitter()

    # Split the data
    train, val, test = splitter.split_data(bars)

    print(f"\nTotal bars: {len(bars)}")
    print(f"Training set: {len(train)} bars ({len(train)/len(bars):.1%})")
    print(f"Validation set: {len(val)} bars ({len(val)/len(bars):.1%})")
    print(f"Test set: {len(test)} bars ({len(test)/len(bars):.1%})")

    print(f"\nTime ranges:")
    print(f"  Train: {train[0].timestamp.date()} to {train[-1].timestamp.date()}")
    print(f"  Val: {val[0].timestamp.date()} to {val[-1].timestamp.date()}")
    print(f"  Test: {test[0].timestamp.date()} to {test[-1].timestamp.date()}")


def example_custom_split():
    """Example 2: Custom split configuration."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Split Configuration (60/20/20)")
    print("=" * 60)

    bars = [
        MockBar(datetime(2020, 1, 1) + timedelta(days=i), close=100 + i)
        for i in range(1000)
    ]

    # Create custom split configuration
    config = DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2)
    splitter = TrainValTestSplitter(split_config=config)

    train, val, test = splitter.split_data(bars)

    print(f"\nTotal bars: {len(bars)}")
    print(f"Training set: {len(train)} bars ({len(train)/len(bars):.1%})")
    print(f"Validation set: {len(val)} bars ({len(val)/len(bars):.1%})")
    print(f"Test set: {len(test)} bars ({len(test)/len(bars):.1%})")


def example_date_filtered_split():
    """Example 3: Split with date filtering."""
    print("\n" + "=" * 60)
    print("Example 3: Split with Date Filtering")
    print("=" * 60)

    bars = [
        MockBar(datetime(2020, 1, 1) + timedelta(days=i), close=100 + i)
        for i in range(1000)
    ]

    splitter = TrainValTestSplitter()

    # Split only data from 2021
    train, val, test = splitter.split_data(
        bars,
        start_date=datetime(2021, 1, 1),
        end_date=datetime(2021, 12, 31)
    )

    total = len(train) + len(val) + len(test)
    print(f"\nTotal bars in 2021: {total}")
    print(f"Training set: {len(train)} bars ({len(train)/total:.1%})")
    print(f"Validation set: {len(val)} bars ({len(val)/total:.1%})")
    print(f"Test set: {len(test)} bars ({len(test)/total:.1%})")


def example_walk_forward_split():
    """Example 4: Walk-forward validation."""
    print("\n" + "=" * 60)
    print("Example 4: Walk-Forward Validation")
    print("=" * 60)

    bars = [
        MockBar(datetime(2020, 1, 1) + timedelta(days=i), close=100 + i)
        for i in range(1000)
    ]

    splitter = TrainValTestSplitter()

    # Create walk-forward windows
    splits = splitter.walk_forward_split(
        bars,
        window_size=252,  # 1 year
        step_size=63      # 3 months
    )

    print(f"\nCreated {len(splits)} walk-forward windows")
    print("\nFirst 3 windows:")
    for i, (train, val, test) in enumerate(splits[:3], 1):
        print(f"  Window {i}: Train={len(train)}, Val={len(val)}, Test={len(test)}")


def example_multiple_testing_correction():
    """Example 5: Multiple testing correction."""
    print("\n" + "=" * 60)
    print("Example 5: Multiple Testing Correction")
    print("=" * 60)

    # Scenario: Testing 20 different strategy configurations
    num_tests = 20
    corrector = MultipleTestingCorrector(num_tests=num_tests, base_confidence=0.95)

    print(f"\nTesting {num_tests} strategy configurations")
    print(f"Base confidence: 95%")

    # Bonferroni correction (conservative)
    adjusted = corrector.bonferroni_correction()
    print(f"\nBonferroni adjusted confidence: {adjusted:.4%} ({adjusted:.2%})")
    print(f"  → Much stricter! Need stronger evidence.")

    # Benjamini-Hochberg (less conservative)
    p_values = [0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.15, 0.20, 0.25, 0.30,
                0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.90]

    significant = corrector.benjamini_hochberg_correction(p_values)
    num_significant = sum(significant)

    print(f"\nBenjamini-Hochberg (FDR 5%):")
    print(f"  Significant tests: {num_significant}/{num_tests}")
    print(f"  → Less conservative than Bonferroni")


def example_oos_validation():
    """Example 6: Out-of-sample performance validation."""
    print("\n" + "=" * 60)
    print("Example 6: Out-of-Sample Performance Validation")
    print("=" * 60)

    # Scenario 1: Good performance (no overfitting)
    print("\nScenario 1: Good performance")
    train_sharpe = 2.0
    val_sharpe = 1.8
    test_sharpe = 1.6

    result = validate_out_of_sample_performance(
        train_sharpe, val_sharpe, test_sharpe, min_performance_ratio=0.7
    )

    print(f"  Train Sharpe: {train_sharpe:.2f}")
    print(f"  Val Sharpe: {val_sharpe:.2f}")
    print(f"  Test Sharpe: {test_sharpe:.2f}")
    print(f"  OOS Validation: {'✅ PASSED' if result else '❌ FAILED'}")

    # Scenario 2: Overfitting detected
    print("\nScenario 2: Overfitting detected")
    train_sharpe = 3.0
    val_sharpe = 2.5
    test_sharpe = 0.5  # Much worse!

    result = validate_out_of_sample_performance(
        train_sharpe, val_sharpe, test_sharpe, min_performance_ratio=0.7
    )

    print(f"  Train Sharpe: {train_sharpe:.2f}")
    print(f"  Val Sharpe: {val_sharpe:.2f}")
    print(f"  Test Sharpe: {test_sharpe:.2f}")
    print(f"  OOS Validation: {'✅ PASSED' if result else '❌ FAILED - Overfitting!'}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("TRAIN/VALIDATION/TEST SPLIT EXAMPLES")
    print("Preventing Overfitting and Data Snooping in Backtesting")
    print("=" * 60)

    example_basic_split()
    example_custom_split()
    example_date_filtered_split()
    example_walk_forward_split()
    example_multiple_testing_correction()
    example_oos_validation()

    print("\n" + "=" * 60)
    print("KEY TAKEAWAYS")
    print("=" * 60)
    print("""
1. Always split data BEFORE backtesting to prevent data snooping
2. Use training set for parameter optimization
3. Use validation set for model selection
4. Use test set ONLY for final evaluation
5. Apply multiple testing corrections when testing many configurations
6. Validate out-of-sample performance to detect overfitting
7. Consider walk-forward validation for time-series data
    """)


if __name__ == "__main__":
    main()
