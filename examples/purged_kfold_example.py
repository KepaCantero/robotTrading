"""
Purged K-Fold with Embargo - Example Usage

Demonstrates how to use Purged K-Fold cross-validation for financial ML models.
This implements López de Prado's method to prevent look-ahead bias.

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado
    Chapter 3, Section 3.6: Cross-Validation in Finance
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score

from app.backtesting.validation.purged_kfold import (
    PurgedKFold,
    PurgedTimeSeriesSplit,
    cross_validate_with_purging,
    purged_kfold_splits,
)


def generate_synthetic_financial_data(n_samples=1000, n_features=10, random_state=42):
    """
    Generate synthetic financial time series data.

    Simulates realistic financial data with:
    - Autocorrelation (serial dependence)
    - Trend component
    - Volatility clustering
    - Noise

    Args:
        n_samples: Number of samples to generate
        n_features: Number of features
        random_state: Random seed for reproducibility

    Returns:
        X, y tuples where X is feature matrix and y is target
    """
    np.random.seed(random_state)

    # Generate time index
    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')

    # Generate features with realistic properties
    X = np.zeros((n_samples, n_features))

    for i in range(n_features):
        # Add trend
        trend = np.linspace(0, 1, n_samples)

        # Add autocorrelation
        ar_component = np.zeros(n_samples)
        ar_component[0] = np.random.randn()
        for j in range(1, n_samples):
            ar_component[j] = 0.7 * ar_component[j-1] + np.random.randn() * 0.3

        # Combine components
        X[:, i] = trend + ar_component + np.random.randn(n_samples) * 0.1

    # Generate binary target (classification)
    # Based on linear combination of features with threshold
    y_class = (X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2] + np.random.randn(n_samples) * 0.2 > 0).astype(int)

    # Generate continuous target (regression)
    y_reg = X[:, 0] + 0.5 * X[:, 1] - 0.3 * X[:, 2] + np.random.randn(n_samples) * 0.1

    return X, y_class, y_reg, dates


def example_1_basic_purged_kfold():
    """
    Example 1: Basic Purged K-Fold usage.

    Demonstrates the simplest way to use PurgedKFold for cross-validation.
    """
    print("=" * 80)
    print("Example 1: Basic Purged K-Fold Usage")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=1000)

    # Create PurgedKFold cross-validator
    purged_cv = PurgedKFold(
        n_splits=5,
        purge_pct=0.05,   # Purge 5% of data before test set
        embargo_pct=0.02,  # Embargo 2% of data after test set
    )

    # Generate splits
    splits = purged_cv.split(X, y_class)

    print(f"\nGenerated {len(splits)} purged splits")

    # Display split information
    summary = purged_cv.get_split_summary()
    print("\nSplit Summary:")
    print(summary.to_string(index=False))

    # Validate no leakage
    has_no_leakage = purged_cv.validate_no_leakage(X)
    print(f"\nNo information leakage detected: {has_no_leakage}")

    # Train a simple classifier on each fold
    print("\nTraining Random Forest on each fold:")
    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(splits):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y_class[train_idx], y_class[test_idx]

        clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        score = accuracy_score(y_test, y_pred)
        fold_scores.append(score)

        print(f"  Fold {fold + 1}: accuracy = {score:.4f} "
              f"(train={len(train_idx)}, test={len(test_idx)})")

    print(f"\nMean accuracy: {np.mean(fold_scores):.4f} (+/- {np.std(fold_scores):.4f})")


def example_2_convenience_function():
    """
    Example 2: Using the convenience function.

    Demonstrates the purged_kfold_splits() convenience function
    for quick cross-validation.
    """
    print("\n" + "=" * 80)
    print("Example 2: Convenience Function")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=500)

    # Use convenience function
    splits = purged_kfold_splits(
        X,
        n_splits=5,
        purge_pct=0.05,
        embargo_pct=0.02,
    )

    print(f"\nGenerated {len(splits)} purged splits using convenience function")

    # Train classifier
    scores = []
    for train_idx, test_idx in splits:
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y_class[train_idx], y_class[test_idx]

        clf = LogisticRegression(max_iter=1000, random_state=42)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        score = accuracy_score(y_test, y_pred)
        scores.append(score)

    print(f"\nLogistic Regression - Mean accuracy: {np.mean(scores):.4f}")


def example_3_cross_validate_with_purging():
    """
    Example 3: Using cross_validate_with_purging.

    Demonstrates the sklearn-like cross_validate interface
    with purged K-Fold.
    """
    print("\n" + "=" * 80)
    print("Example 3: Cross-Validate with Purging (sklearn-like API)")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, y_reg, dates = generate_synthetic_financial_data(n_samples=1000)

    # Example 3a: Classification
    print("\n3a. Classification Task:")
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)

    results_clf = cross_validate_with_purging(
        clf,
        X,
        y_class,
        n_splits=5,
        purge_pct=0.05,
        embargo_pct=0.02,
    )

    print(f"  Mean accuracy: {np.mean(results_clf['test_score']):.4f}")
    print(f"  Std accuracy:  {np.std(results_clf['test_score']):.4f}")

    # Example 3b: Regression
    print("\n3b. Regression Task:")
    reg = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)

    results_reg = cross_validate_with_purging(
        reg,
        X,
        y_reg,
        n_splits=5,
        purge_pct=0.05,
        embargo_pct=0.02,
    )

    print(f"  Mean R² score: {np.mean(results_reg['test_score']):.4f}")
    print(f"  Std R² score:  {np.std(results_reg['test_score']):.4f}")

    # Example 3c: Custom scoring
    print("\n3c. Custom Scoring (F1-score):")

    results_f1 = cross_validate_with_purging(
        clf,
        X,
        y_class,
        n_splits=5,
        purge_pct=0.05,
        embargo_pct=0.02,
        scoring=lambda y_true, y_pred: f1_score(y_true, y_pred, average='weighted')
    )

    print(f"  Mean F1-score: {np.mean(results_f1['test_score']):.4f}")


def example_4_time_series_split():
    """
    Example 4: PurgedTimeSeriesSplit.

    Demonstrates time series cross-validation with purging and embargo.
    """
    print("\n" + "=" * 80)
    print("Example 4: Purged Time Series Split")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=500)

    # Create PurgedTimeSeriesSplit
    tscv = PurgedTimeSeriesSplit(
        n_splits=5,
        purge_pct=0.05,
        embargo_pct=0.02,
        test_size=50,  # Fixed test size
    )

    # Generate splits
    splits = tscv.split(X, y_class)

    print(f"\nGenerated {len(splits)} time series splits")

    # Display split progression
    print("\nSplit Progression:")
    for fold, (train_idx, test_idx) in enumerate(splits):
        train_start = train_idx.min()
        train_end = train_idx.max()
        test_start = test_idx.min()
        test_end = test_idx.max()

        print(f"  Fold {fold + 1}: train=[{train_start}:{train_end}], "
              f"test=[{test_start}:{test_end}]")

    # Train classifier
    tscv = PurgedTimeSeriesSplit(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
    splits = tscv.split(X, y_class)

    scores = []
    for train_idx, test_idx in splits:
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y_class[train_idx], y_class[test_idx]

        clf = RandomForestClassifier(n_estimators=50, random_state=42)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        score = accuracy_score(y_test, y_pred)
        scores.append(score)

    print(f"\nMean accuracy: {np.mean(scores):.4f}")


def example_5_pandas_dataframe():
    """
    Example 5: Using with Pandas DataFrames.

    Demonstrates usage with pandas DataFrames and time index.
    """
    print("\n" + "=" * 80)
    print("Example 5: Using with Pandas DataFrames")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=1000)

    # Create DataFrame with time index
    X_df = pd.DataFrame(
        X,
        columns=[f'feature_{i}' for i in range(X.shape[1])],
        index=dates
    )

    y_series = pd.Series(y_class, index=dates, name='target')

    print(f"\nDataFrame shape: {X_df.shape}")
    print(f"Date range: {X_df.index.min()} to {X_df.index.max()}")

    # Use PurgedKFold with DataFrame
    purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
    splits = purged_cv.split(X_df, y_series)

    # Train classifier using DataFrame indices
    scores = []
    for train_idx, test_idx in splits:
        X_train = X_df.iloc[train_idx]
        X_test = X_df.iloc[test_idx]
        y_train = y_series.iloc[train_idx]
        y_test = y_series.iloc[test_idx]

        clf = RandomForestClassifier(n_estimators=50, random_state=42)
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)

        score = accuracy_score(y_test, y_pred)
        scores.append(score)

        print(f"  Fold {len(scores)}: accuracy = {score:.4f}")

    print(f"\nMean accuracy: {np.mean(scores):.4f}")


def example_6_comparing_purge_embargo_settings():
    """
    Example 6: Comparing different purge and embargo settings.

    Demonstrates the impact of different purge/embargo percentages
    on model performance.
    """
    print("\n" + "=" * 80)
    print("Example 6: Comparing Purge/Embargo Settings")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=1000)

    # Test different configurations
    configs = [
        {'purge_pct': 0.00, 'embargo_pct': 0.00, 'name': 'No Purge/Embargo'},
        {'purge_pct': 0.02, 'embargo_pct': 0.01, 'name': 'Light (2%/1%)'},
        {'purge_pct': 0.05, 'embargo_pct': 0.02, 'name': 'Medium (5%/2%)'},
        {'purge_pct': 0.10, 'embargo_pct': 0.05, 'name': 'Heavy (10%/5%)'},
    ]

    results = []

    for config in configs:
        purged_cv = PurgedKFold(
            n_splits=5,
            purge_pct=config['purge_pct'],
            embargo_pct=config['embargo_pct'],
        )

        splits = purged_cv.split(X, y_class)

        scores = []
        for train_idx, test_idx in splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y_class[train_idx], y_class[test_idx]

            clf = RandomForestClassifier(n_estimators=50, random_state=42)
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)

            score = accuracy_score(y_test, y_pred)
            scores.append(score)

        mean_score = np.mean(scores)
        std_score = np.std(scores)

        results.append({
            'config': config['name'],
            'purge_pct': config['purge_pct'],
            'embargo_pct': config['embargo_pct'],
            'mean_accuracy': mean_score,
            'std_accuracy': std_score,
            'n_splits': len(splits),
        })

        print(f"\n{config['name']}:")
        print(f"  Mean accuracy: {mean_score:.4f} (+/- {std_score:.4f})")
        print(f"  Splits generated: {len(splits)}")

    # Display comparison table
    print("\n" + "=" * 80)
    print("Configuration Comparison:")
    print("=" * 80)
    results_df = pd.DataFrame(results)
    print(results_df[['config', 'mean_accuracy', 'std_accuracy', 'n_splits']].to_string(index=False))


def example_7_leakage_detection():
    """
    Example 7: Information leakage detection.

    Demonstrates how to validate that splits have no information leakage.
    """
    print("\n" + "=" * 80)
    print("Example 7: Information Leakage Detection")
    print("=" * 80)

    # Generate synthetic data
    X, y_class, _, dates = generate_synthetic_financial_data(n_samples=1000)

    # Create PurgedKFold
    purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)

    # Generate splits
    splits = purged_cv.split(X, y_class)

    print(f"\nGenerated {len(splits)} purged splits")

    # Validate no leakage
    has_no_leakage = purged_cv.validate_no_leakage(X)
    print(f"\n✅ Validation passed: No information leakage detected" if has_no_leakage else "❌ Validation failed: Leakage detected")

    # Display split details
    print("\nSplit Details:")
    summary = purged_cv.get_split_summary()
    print(summary.to_string(index=False))

    # Check specific split
    print("\nDetailed Analysis of First Split:")
    if purged_cv.split_details:
        split = purged_cv.split_details[0]
        print(f"  Fold: {split.fold}")
        print(f"  Train size (before purge): {split.train_size_purged}")
        print(f"  Train size (after purge): {split.train_size_after_purge}")
        print(f"  Test size: {len(split.test_indices)}")
        print(f"  Purged samples: {len(split.purged_indices)}")
        print(f"  Embargo samples: {split.embargo_size}")
        print(f"  Actual purge %: {split.purge_pct_actual * 100:.2f}%")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Purged K-Fold with Embargo - Example Usage")
    print("Implementing López de Prado's Cross-Validation for Financial ML")
    print("=" * 80)

    # Run examples
    example_1_basic_purged_kfold()
    example_2_convenience_function()
    example_3_cross_validate_with_purging()
    example_4_time_series_split()
    example_5_pandas_dataframe()
    example_6_comparing_purge_embargo_settings()
    example_7_leakage_detection()

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)

    print("\nKey Takeaways:")
    print("1. Purged K-Fold prevents look-ahead bias in time series cross-validation")
    print("2. Purge removes training samples that overlap with test period")
    print("3. Embargo adds buffer after test set to prevent information leakage")
    print("4. Always validate that splits have no information leakage")
    print("5. Adjust purge_pct and embargo_pct based on your data characteristics")
    print("\nReference: 'Advances in Financial Machine Learning' by Marcos López de Prado")


if __name__ == '__main__':
    main()
