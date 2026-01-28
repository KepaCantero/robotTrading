"""
Purged Cross-Validation Example (López de Prado Chapter 4).

This example demonstrates how to use purged K-Fold cross-validation
to prevent look-ahead bias when training ML models on financial time series.

Key Concepts:
- Purge: Remove training samples that overlap with test period
- Embargo: Add buffer period after test set using t1 (exit times)
- Event-aware: Uses actual event lifetimes from triple barrier labeling

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado
    Chapter 4, Section 4.4-4.5
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report

from app.backtesting.validation.cross_validation import (
    PurgedKFold,
    PurgedTimeSeriesSplit,
    cv_score,
)
from app.backtesting.labeling.triple_barrier import (
    TripleBarrierConfig,
    TripleBarrierLabeler,
    triple_barrier_method,
)


def generate_sample_data(n_samples=1000, n_features=10):
    """
    Generate synthetic financial data for demonstration.

    In practice, you would use real market data here.
    """
    np.random.seed(42)

    # Create features (e.g., technical indicators)
    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)],
        index=dates
    )

    # Simulate prices
    prices = pd.Series(
        100 + np.cumsum(np.random.randn(n_samples) * 0.01),
        index=dates,
        name='close'
    )

    # Generate trading signals (events)
    # In practice, these would come from your strategy
    signal_dates = dates[::20]  # Every 20 days

    return X, prices, signal_dates


def example_1_basic_purged_cv():
    """Example 1: Basic purged K-Fold cross-validation."""
    print("\n" + "="*80)
    print("Example 1: Basic Purged K-Fold CV")
    print("="*80)

    # Generate sample data
    X, prices, signal_dates = generate_sample_data(n_samples=1000, n_features=10)

    # Create labels (simplified - use triple barrier in practice)
    y = pd.Series(
        np.random.randint(0, 2, len(X)),
        index=X.index
    )

    # Create events with t1 (exit times)
    # In practice, t1 comes from triple barrier labeling
    events = pd.DataFrame({
        't1': X.index + pd.Timedelta(days=np.random.randint(1, 10, len(X)))
    }, index=X.index)

    print(f"\nDataset shape: {X.shape}")
    print(f"Label distribution:\n{y.value_counts()}")

    # Create purged CV splitter
    purged_cv = PurgedKFold(
        n_splits=5,
        embargo_pct=0.01,  # 1% embargo after test set
        purge_pct=0.05,    # 5% purge before test set
    )

    # Perform cross-validation
    print("\nPerforming purged cross-validation...")
    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(purged_cv.split(X, y, events=events)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        score = accuracy_score(y_test, y_pred)
        fold_scores.append(score)

        print(f"  Fold {fold}: train={len(train_idx):4d}, test={len(test_idx):4d}, accuracy={score:.4f}")

    print(f"\nMean CV Score: {np.mean(fold_scores):.4f} (+/- {np.std(fold_scores):.4f})")

    # Get split summary
    summary = purged_cv.get_split_summary()
    print("\nSplit Summary:")
    print(summary.to_string(index=False))

    # Validate no leakage
    is_valid = purged_cv.validate_no_leakage(X)
    print(f"\nNo information leakage: {'✓ Yes' if is_valid else '✗ No'}")


def example_2_event_based_embargo():
    """Example 2: Event-based embargo using triple barrier t1."""
    print("\n" + "="*80)
    print("Example 2: Event-Based Embargo with Triple Barrier")
    print("="*80)

    # Generate sample data
    X, prices, signal_dates = generate_sample_data(n_samples=1000, n_features=10)

    # Apply triple barrier labeling
    config = TripleBarrierConfig(
        upper_barrier_pct=0.02,
        lower_barrier_pct=-0.01,
        vertical_barrier_days=5
    )

    labeler = TripleBarrierLabeler(config)
    labels_df = labeler.fit_transform(prices, pd.Series(signal_dates))

    print(f"\nGenerated {len(labels_df)} triple barrier labels")
    print(f"Label distribution:\n{labels_df['label'].value_counts()}")

    # Create events DataFrame with t1 (exit times)
    # Calculate t1 from triple barrier results
    events = pd.DataFrame({
        't1': signal_dates + pd.to_timedelta(labels_df['bars_to_barrier'].values, unit='D')
    }, index=signal_dates)

    # Create binary labels
    y = (labels_df['label'] == 1).astype(int)  # 1 if upper barrier hit
    y.index = signal_dates

    # Align features with events
    X_aligned = X.loc[signal_dates]

    print(f"\nAligned dataset shape: {X_aligned.shape}")

    # Use purged CV with event-based embargo
    purged_cv = PurgedKFold(
        n_splits=5,
        embargo_pct=0.01,
        purge_pct=0.05,
    )

    print("\nPerforming purged CV with event-based embargo...")
    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(purged_cv.split(X_aligned, y, events=events)):
        X_train, X_test = X_aligned.iloc[train_idx], X_aligned.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Train model
        model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate
        score = model.score(X_test, y_test)
        fold_scores.append(score)

        print(f"  Fold {fold}: train={len(train_idx):3d}, test={len(test_idx):3d}, accuracy={score:.4f}")

    print(f"\nMean CV Score: {np.mean(fold_scores):.4f} (+/- {np.std(fold_scores):.4f})")


def example_3_time_series_split():
    """Example 3: Purged time series split with expanding window."""
    print("\n" + "="*80)
    print("Example 3: Purged Time Series Split")
    print("="*80)

    # Generate sample data
    X, prices, signal_dates = generate_sample_data(n_samples=1000, n_features=10)

    y = pd.Series(
        np.random.randint(0, 2, len(X)),
        index=X.index
    )

    events = pd.DataFrame({
        't1': X.index + pd.Timedelta(days=5)
    }, index=X.index)

    # Use time series split
    tscv = PurgedTimeSeriesSplit(
        n_splits=5,
        embargo_pct=0.01,
        purge_pct=0.05,
        max_train_size=500,  # Sliding window of 500 samples
    )

    print("\nPerforming purged time series cross-validation...")
    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X, y, events=events)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        print(f"  Fold {fold}: train={len(train_idx):4d}, test={len(test_idx):4d}")

        # Train model
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate
        score = model.score(X_test, y_test)
        fold_scores.append(score)
        print(f"         accuracy={score:.4f}")

    print(f"\nMean CV Score: {np.mean(fold_scores):.4f} (+/- {np.std(fold_scores):.4f})")


def example_4_cv_score_function():
    """Example 4: Using the cv_score convenience function."""
    print("\n" + "="*80)
    print("Example 4: Using cv_score() Function")
    print("="*80)

    # Generate sample data
    X, prices, signal_dates = generate_sample_data(n_samples=1000, n_features=10)

    y = pd.Series(
        np.random.randint(0, 2, len(X)),
        index=X.index
    )

    events = pd.DataFrame({
        't1': X.index + pd.Timedelta(days=5)
    }, index=X.index)

    # Use cv_score function
    model = RandomForestClassifier(n_estimators=100, random_state=42)

    results = cv_score(
        estimator=model,
        X=X.values,
        y=y.values,
        events=events,
        n_splits=5,
        embargo_pct=0.01,
        purge_pct=0.05,
    )

    print(f"\nCross-Validation Results:")
    print(f"  Mean Score: {results['mean_score']:.4f}")
    print(f"  Std Score:  {results['std_score']:.4f}")
    print(f"  Fold Scores: {[f'{s:.4f}' for s in results['fold_scores']]}")


def example_5_comparison_standard_vs_purged():
    """Example 5: Compare standard K-Fold vs Purged K-Fold."""
    print("\n" + "="*80)
    print("Example 5: Standard K-Fold vs Purged K-Fold")
    print("="*80)

    from sklearn.model_selection import KFold

    # Generate sample data with temporal structure
    X, prices, signal_dates = generate_sample_data(n_samples=1000, n_features=10)

    y = pd.Series(
        np.random.randint(0, 2, len(X)),
        index=X.index
    )

    events = pd.DataFrame({
        't1': X.index + pd.Timedelta(days=5)
    }, index=X.index)

    # Standard K-Fold (with leakage!)
    print("\n1. Standard K-Fold (HAS LOOK-AHEAD BIAS):")
    standard_kfold = KFold(n_splits=5, shuffle=False)
    standard_scores = []

    for train_idx, test_idx in standard_kfold.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        standard_scores.append(score)

    print(f"   Mean Score: {np.mean(standard_scores):.4f} (+/- {np.std(standard_scores):.4f})")

    # Check for leakage
    has_leakage = False
    for train_idx, test_idx in standard_kfold.split(X):
        if train_idx.max() > test_idx.min():
            has_leakage = True
            break
    print(f"   Has Look-Ahead Leakage: {'✗ Yes (BAD!)' if has_leakage else '✓ No'}")

    # Purged K-Fold (no leakage)
    print("\n2. Purged K-Fold (NO LOOK-AHEAD BIAS):")
    purged_cv = PurgedKFold(n_splits=5, embargo_pct=0.01, purge_pct=0.05)
    purged_scores = []

    for train_idx, test_idx in purged_cv.split(X, y, events=events):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
        purged_scores.append(score)

    print(f"   Mean Score: {np.mean(purged_scores):.4f} (+/- {np.std(purged_scores):.4f})")
    print(f"   Has Look-Ahead Leakage: {'✗ Yes' if not purged_cv.validate_no_leakage(X) else '✓ No (GOOD!)'}")

    # Compare
    print("\nComparison:")
    print(f"  Standard K-Fold:    {np.mean(standard_scores):.4f} (may be inflated due to leakage)")
    print(f"  Purged K-Fold:      {np.mean(purged_scores):.4f} (realistic estimate)")
    print(f"  Difference:         {np.mean(standard_scores) - np.mean(purged_scores):.4f}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PURGED CROSS-VALIDATION EXAMPLES")
    print("López de Prado, Chapter 4")
    print("="*80)

    # Run examples
    example_1_basic_purged_cv()
    example_2_event_based_embargo()
    example_3_time_series_split()
    example_4_cv_score_function()
    example_5_comparison_standard_vs_purged()

    print("\n" + "="*80)
    print("Examples completed successfully!")
    print("="*80 + "\n")
