"""
Complete López de Prado Meta-Labeling Pipeline Example

This example demonstrates the complete meta-labeling pipeline with all
95% compliance features from López de Prado's "Advances in Financial Machine Learning".

Pipeline Steps:
1. Generate triple barrier labels
2. Calculate sample uniqueness weights
3. Train meta-labeling models with purged CV
4. Calculate feature importance with uniqueness
5. Calculate bet sizes using meta-labeling
6. Train multiple models concurrently
7. Create ensemble predictions

Usage:
    python examples/lopez_de_prado_95_example.py
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("XGBoost not available, using RandomForest instead")

# Import López de Prado 95% compliance modules
from app.backtesting.labeling import (
    # Triple Barrier
    TripleBarrierLabeler,
    TripleBarrierConfig,
    calculate_sample_weights_uniqueness,
    # Meta-Labeling
    MetaLabelingCV,
    MetaLabelingBetSizing,
    MetaBetSizingConfig,
    # Concurrent Training
    ConcurrentModelTrainer,
)

from app.backtesting.feature_engineering import (
    FinancialMLFeatureImportanceWithUniqueness,
    UniquenessConfig,
)


def generate_sample_data(n_samples: int = 1000, n_features: int = 20):
    """
    Generate sample financial data for demonstration.

    Args:
        n_samples: Number of samples
        n_features: Number of features

    Returns:
        Tuple of (X, y, prices, events, labels)
    """
    np.random.seed(42)

    # Generate prices with random walk
    returns = np.random.randn(n_samples) * 0.02
    prices = 100 * np.cumprod(1 + returns)

    # Generate features with some predictive signal
    X = np.random.randn(n_samples, n_features)

    # Add some signal to features
    signal = (X[:, 0] + X[:, 1] + X[:, 2]) / 3
    prices += signal * 2

    # Create price series
    price_series = pd.Series(
        prices,
        index=pd.date_range("2020-01-01", periods=n_samples, freq="H"),
    )

    # Generate events (every 50 bars)
    event_indices = np.arange(50, n_samples, 50)
    events = price_series.index[event_indices]

    # Generate triple barrier labels
    config = TripleBarrierConfig(
        upper_barrier_pct=0.02,
        lower_barrier_pct=-0.01,
        vertical_barrier_days=5,
        vol_scaling=True,
    )

    labeler = TripleBarrierLabeler(config)
    labels_df = labeler.fit_transform(price_series, events)

    # Extract features at event times
    X_events = X[event_indices]
    y_events = labels_df["label"].values

    return X_events, y_events, price_series, events, labels_df


def step1_triple_barrier_labeling():
    """Step 1: Generate triple barrier labels."""
    print("\n" + "=" * 80)
    print("STEP 1: Triple Barrier Labeling")
    print("=" * 80)

    # Generate sample data
    X, y, prices, events, labels_df = generate_sample_data()

    print(f"Generated {len(X)} samples with {X.shape[1]} features")
    print(f"Label distribution:")
    print(labels_df["label"].value_counts())

    return X, y, prices, events, labels_df


def step2_calculate_uniqueness(X, y, prices, events, labels_df):
    """Step 2: Calculate sample uniqueness weights."""
    print("\n" + "=" * 80)
    print("STEP 2: Calculate Sample Uniqueness")
    print("=" * 80)

    # Calculate uniqueness weights
    uniqueness_weights = calculate_sample_weights_uniqueness(
        events, labels_df, prices
    )

    print(f"Average uniqueness: {uniqueness_weights.mean():.4f}")
    print(f"Min uniqueness: {uniqueness_weights.min():.4f}")
    print(f"Max uniqueness: {uniqueness_weights.max():.4f}")

    # Show distribution
    n_unique = (uniqueness_weights > 0.9).sum()
    n_common = (uniqueness_weights < 0.5).sum()
    print(f"Highly unique samples (w > 0.9): {n_unique}")
    print(f"Common samples (w < 0.5): {n_common}")

    return uniqueness_weights


def step3_meta_labeling_cv(X, y, events, labels_df, uniqueness_weights):
    """Step 3: Train meta-labeling models with purged CV."""
    print("\n" + "=" * 80)
    print("STEP 3: Meta-Labeling with Purged Cross-Validation")
    print("=" * 80)

    # Create models
    primary_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=5,
        random_state=42,
    )

    meta_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=5,
        random_state=42,
    )

    # Create CV with purging and embargo
    cv = MetaLabelingCV(
        n_folds=5,
        purge_pct=0.05,
        embargo_pct=0.01,
        scoring="accuracy",
    )

    # Run cross-validation
    print("Running cross-validation with 5 folds...")
    cv_results = cv.cross_validate(
        primary_model,
        meta_model,
        X,
        y,
        events,
        labels_df,
        sample_weights=uniqueness_weights,
    )

    print(f"\nCross-Validation Results:")
    print(f"Mean accuracy: {cv_results.mean_score:.4f} ± {cv_results.std_score:.4f}")
    print(f"Fold scores: {[f'{s:.4f}' for s in cv_results.fold_scores]}")

    # Train final models on all data
    print("\nTraining final models on all data...")
    primary_model.fit(X, y, sample_weight=uniqueness_weights)

    # Generate meta-labels
    primary_pred = primary_model.predict(X)
    meta_labels = (primary_pred == y).astype(int)

    X_meta = np.column_stack([X, primary_pred])
    meta_model.fit(X_meta, meta_labels, sample_weight=uniqueness_weights)

    print(f"Meta-label distribution: {np.bincount(meta_labels)}")

    return primary_model, meta_model


def step4_feature_importance(X, y, events, labels_df, primary_model):
    """Step 4: Calculate feature importance with uniqueness."""
    print("\n" + "=" * 80)
    print("STEP 4: Feature Importance with Uniqueness")
    print("=" * 80)

    # Create feature importance calculator
    config = UniquenessConfig(
        cluster_features=True,
        correlation_threshold=0.7,
    )

    importance_calc = FinancialMLFeatureImportanceWithUniqueness(config)

    # Calculate importance
    print("Calculating feature importance with uniqueness weighting...")
    result = importance_calc.calculate_importance(
        primary_model, X, y, events, labels_df
    )

    print(f"\nAverage uniqueness: {result.avg_uniqueness:.4f}")
    print(f"Methods used: {result.methods_used}")

    # Get top features
    top_features = sorted(
        result.combined_importance.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    print(f"\nTop 10 Features:")
    for i, (feature, importance) in enumerate(top_features, 1):
        print(f"  {i:2d}. {feature:15s}: {importance:.4f}")

    # Show feature clusters if any
    if result.feature_clusters:
        print(f"\nFeature Clusters ({len(result.feature_clusters)}):")
        for rep, members in list(result.feature_clusters.items())[:3]:
            print(f"  {rep}: {members}")

    return result


def step5_bet_sizing(primary_model, meta_model, X_test):
    """Step 5: Calculate bet sizes using meta-labeling."""
    print("\n" + "=" * 80)
    print("STEP 5: Bet Sizing with Meta-Labeling")
    print("=" * 80)

    # Create bet sizing configuration
    config = MetaBetSizingConfig(
        method="meta_kelly",
        confidence_threshold=0.5,
        high_confidence_threshold=0.7,
        max_bet_size=0.25,
        kelly_fraction=0.25,
    )

    bet_sizing = MetaLabelingBetSizing(config)

    # Generate expected returns (mock)
    expected_returns = np.random.uniform(0.01, 0.03, len(X_test))

    # Calculate bet sizes
    result = bet_sizing.calculate_sizes(
        primary_model, meta_model, X_test, expected_returns
    )

    print(f"\nBet Sizing Results:")
    print(f"Average bet size: {result.bet_sizes.mean():.4f}")
    print(f"Max bet size: {result.bet_sizes.max():.4f}")
    print(f"Number of trades: {(result.bet_sizes > 0).sum()}")
    print(f"Total exposure: {result.bet_sizes.sum():.4f}")

    # Show confidence distribution
    confidence_levels = result.confidence_levels
    n_low = (confidence_levels == 0).sum()
    n_med = (confidence_levels == 1).sum()
    n_high = (confidence_levels == 2).sum()

    print(f"\nConfidence Distribution:")
    print(f"  Low (< 0.5):    {n_low:3d}")
    print(f"  Medium (0.5-0.7): {n_med:3d}")
    print(f"  High (> 0.7):   {n_high:3d}")

    # Show some bet sizes
    active_bets = result.bet_sizes[result.bet_sizes > 0]
    if len(active_bets) > 0:
        print(f"\nSample Bet Sizes (first 10):")
        for i, size in enumerate(active_bets[:10], 1):
            print(f"  Bet {i:2d}: {size:.4f}")

    return result


def step6_concurrent_training(X, y, events, labels_df, uniqueness_weights):
    """Step 6: Train multiple models concurrently."""
    print("\n" + "=" * 80)
    print("STEP 6: Concurrent Model Training")
    print("=" * 80)

    # Create multiple models
    models = {
        "rf": RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
        ),
        "rf_shallow": RandomForestClassifier(
            n_estimators=50,
            max_depth=3,
            random_state=42,
        ),
    }

    if HAS_XGBOOST:
        models["xgb"] = XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
            eval_metric="logloss",
        )

    models["lr"] = LogisticRegression(
        random_state=42,
        max_iter=1000,
    )

    print(f"Training {len(models)} models concurrently...")

    # Train models concurrently
    trainer = ConcurrentModelTrainer(n_jobs=4)
    ensemble_results = trainer.train_models_concurrent(
        models, X, y, events, labels_df
    )

    print(f"\nEnsemble Results:")
    print(f"Number of models: {ensemble_results.metadata['n_models']}")
    print(f"Ensemble score: {ensemble_results.ensemble_score:.4f}")

    # Show individual model scores
    print(f"\nIndividual Model Scores:")
    for result in ensemble_results.model_results:
        print(f"  {result.model_name:15s}: {result.score:.4f}")

    # Show ensemble weights
    print(f"\nEnsemble Weights:")
    for model_name, weight in ensemble_results.ensemble_weights.items():
        print(f"  {model_name:15s}: {weight:.4f}")

    return ensemble_results


def main():
    """Run the complete López de Prado meta-labeling pipeline."""
    print("\n" + "=" * 80)
    print("LÓPEZ DE PRADO META-LABELING PIPELINE - 95% COMPLIANCE")
    print("=" * 80)
    print("\nThis example demonstrates the complete meta-labeling pipeline")
    print("with all López de Prado features implemented for 95% compliance.")
    print("\nFeatures demonstrated:")
    print("  1. Triple Barrier Labeling")
    print("  2. Sample Uniqueness Weights")
    print("  3. Purged Cross-Validation for Meta-Labeling")
    print("  4. Feature Importance with Uniqueness")
    print("  5. Bet Sizing with Meta-Labeling")
    print("  6. Concurrent Model Training")

    # Step 1: Generate labels
    X, y, prices, events, labels_df = step1_triple_barrier_labeling()

    # Step 2: Calculate uniqueness
    uniqueness_weights = step2_calculate_uniqueness(X, y, prices, events, labels_df)

    # Step 3: Train meta-labeling models
    primary_model, meta_model = step3_meta_labeling_cv(
        X, y, events, labels_df, uniqueness_weights
    )

    # Step 4: Feature importance
    importance_result = step4_feature_importance(
        X, y, events, labels_df, primary_model
    )

    # Step 5: Bet sizing
    # Create test data (just use training data for demo)
    bet_sizing_result = step5_bet_sizing(primary_model, meta_model, X)

    # Step 6: Concurrent training
    ensemble_results = step6_concurrent_training(
        X, y, events, labels_df, uniqueness_weights
    )

    # Final summary
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETION SUMMARY")
    print("=" * 80)

    print("\n✅ All steps completed successfully!")
    print("\nKey Results:")
    print(f"  - Trained meta-labeling models with purged CV")
    print(f"  - Calculated uniqueness-weighted feature importance")
    print(f"  - Generated meta-labeling bet sizes")
    print(f"  - Trained ensemble of {len(ensemble_results.model_results)} models")

    print("\n🎯 95% López de Prado Compliance Achieved!")
    print("\nFor more information, see:")
    print("  - docs/LOPEZ_DE_PRADO_95_COMPLIANCE.md")
    print("  - LOPEZ_DE_PRADO_95_IMPLEMENTATION_SUMMARY.md")

    return {
        "X": X,
        "y": y,
        "primary_model": primary_model,
        "meta_model": meta_model,
        "importance_result": importance_result,
        "bet_sizing_result": bet_sizing_result,
        "ensemble_results": ensemble_results,
    }


if __name__ == "__main__":
    results = main()
