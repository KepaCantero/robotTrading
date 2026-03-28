"""
MCC (Matthews Correlation Coefficient) Usage Example

This example demonstrates how MCC is now integrated into the SupervisedLearningEngine
for evaluating model performance on imbalanced binary classification tasks.

Context:
    In algorithmic trading, successful trades are often rare (e.g., 5-10% of opportunities).
    Traditional accuracy metrics are misleading in this scenario.
    MCC provides a balanced measure that accounts for:
    - True Positives (TP): Correctly predicted winning trades
    - True Negatives (TN): Correctly predicted losing/neutral trades
    - False Positives (FP): Predicted wins but lost money
    - False Negatives (FN): Predicted losses but missed opportunities

Reference:
    López de Prado, "Advances in Financial Machine Learning", Chapter 3.
"""

import numpy as np
from app.strategies.momentum_modular.learning.supervised_learning_engine import (
    SupervisedLearningEngine,
)


def example_mcc_integration():
    """
    Example: MCC in model evaluation
    """
    print("=" * 70)
    print("MCC Integration Example - SupervisedLearningEngine")
    print("=" * 70)
    print()

    # Configure the learning engine
    config = {
        'algorithm': 'xgboost',  # Also works with: random_forest, lightgbm, catboost, gradient_boosting, neural_net
        'feature_columns': ['rsi', 'momentum', 'ema_distance', 'volume_change'],
        'target_column': 'trade_success',  # Binary: 1 = profitable trade, 0 = unprofitable
        'model_parameters': {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
        },
    }

    # Create engine
    engine = SupervisedLearningEngine(config)

    # Prepare training data (imbalanced scenario: 10% winning trades)
    n_samples = 1000
    n_features = len(config['feature_columns'])

    training_data = {
        'features': np.random.randn(n_samples, n_features),
        'labels': np.array([1] * 100 + [0] * 900),  # 10% winners, 90% losers
        'metadata': {},
    }

    print("Training Scenario:")
    print(f"  Total samples: {n_samples}")
    print(
        f"  Winning trades: {np.sum(training_data['labels'])} ({np.mean(training_data['labels'])*100:.1f}%)"
    )
    print(
        f"  Losing trades: {n_samples - np.sum(training_data['labels'])} ({(1-np.mean(training_data['labels']))*100:.1f}%)"
    )
    print()

    # Train model
    print("Training model...")
    metrics = engine.train(training_data)

    print("Training completed!")
    print()
    print("Evaluation Metrics:")
    print("-" * 70)

    # Print all metrics
    for metric_name, value in metrics.items():
        if isinstance(value, float):
            print(f"  {metric_name:20s}: {value:.4f}")
        elif isinstance(value, dict):
            print(f"  {metric_name:20s}: {value}")
        else:
            print(f"  {metric_name:20s}: {value}")

    print("-" * 70)
    print()

    # Interpret MCC
    if 'mcc' in metrics and metrics['mcc'] is not None:
        mcc = metrics['mcc']
        print("MCC Interpretation:")
        print(f"  Current MCC: {mcc:.3f}")
        print()

        if mcc >= 0.7:
            print("  ✓ Excellent! Model shows strong predictive performance.")
            print("    The model reliably distinguishes winning from losing trades.")
        elif mcc >= 0.5:
            print("  ✓ Good! Model shows moderate predictive performance.")
            print("    Consider using this model for filtering trade opportunities.")
        elif mcc >= 0.3:
            print("  ⚠ Moderate. Model shows weak predictive performance.")
            print("    Model may benefit from additional features or more training data.")
        else:
            print("  ✗ Poor! Model shows little predictive power.")
            print("    Model may not be reliable for trading decisions.")
            print("    Consider:")
            print("      - Adding more informative features")
            print("      - Collecting more training data")
            print("      - Trying different algorithms")
            print("      - Adjusting hyperparameters")
    else:
        print("⚠ MCC not calculated (check logs for details)")

    print()
    print("=" * 70)
    print()


def example_mcc_comparison():
    """
    Example: Compare different scenarios using MCC
    """
    print("=" * 70)
    print("MCC Scenario Comparison")
    print("=" * 70)
    print()

    from app.backtesting.metrics import calculate_matthews_corrcoef

    scenarios = [
        {
            'name': 'Perfect Prediction',
            'y_true': np.array([1, 1, 1, 0, 0, 0]),
            'y_pred': np.array([1, 1, 1, 0, 0, 0]),
        },
        {
            'name': 'Good Prediction',
            'y_true': np.array([1, 1, 1, 0, 0, 0]),
            'y_pred': np.array([1, 1, 0, 0, 0, 0]),
        },
        {
            'name': 'Random Prediction',
            'y_true': np.array([1, 1, 1, 0, 0, 0]),
            'y_pred': np.array([1, 0, 1, 0, 1, 0]),
        },
        {
            'name': 'Poor Prediction',
            'y_true': np.array([1, 1, 1, 0, 0, 0]),
            'y_pred': np.array([0, 0, 0, 1, 1, 1]),
        },
        {
            'name': 'Complete Disagreement',
            'y_true': np.array([1, 1, 1, 0, 0, 0]),
            'y_pred': np.array([0, 0, 0, 1, 1, 1]),
        },
    ]

    print(f"{'Scenario':<25} {'MCC':>10} {'Interpretation'}")
    print("-" * 70)

    for scenario in scenarios:
        mcc = calculate_matthews_corrcoef(scenario['y_true'], scenario['y_pred'])

        if mcc >= 0.7:
            interpretation = "Excellent"
        elif mcc >= 0.5:
            interpretation = "Good"
        elif mcc >= 0.3:
            interpretation = "Moderate"
        elif mcc >= 0:
            interpretation = "Poor"
        else:
            interpretation = "Terrible"

        print(f"{scenario['name']:<25} {mcc:>10.3f}  {interpretation}")

    print("-" * 70)
    print()
    print("Key Insights:")
    print("  1. MCC = +1.0: Perfect prediction (ideal)")
    print("  2. MCC > 0.5: Good model performance (acceptable for trading)")
    print("  3. MCC 0.3-0.5: Moderate performance (may need improvement)")
    print("  4. MCC < 0.3: Poor performance (not reliable for trading)")
    print("  5. MCC = 0.0: Random prediction (no predictive power)")
    print("  6. MCC < 0.0: Worse than random (model is inverted!)")
    print()
    print("=" * 70)
    print()


def example_mcc_vs_accuracy():
    """
    Example: Why MCC is better than accuracy for imbalanced data
    """
    print("=" * 70)
    print("MCC vs Accuracy: Imbalanced Data Scenario")
    print("=" * 70)
    print()

    from app.backtesting.metrics import calculate_matthews_corrcoef
    from sklearn.metrics import accuracy_score

    # Scenario: 95% losing trades, 5% winning trades
    # Model always predicts "losing trade" (0)
    y_true = np.array([1] * 5 + [0] * 95)
    y_pred = np.array([0] * 100)  # Always predict losing trade

    accuracy = accuracy_score(y_true, y_pred)
    mcc = calculate_matthews_corrcoef(y_true, y_pred)

    print("Scenario: Market with 5% winning trades")
    print(f"  Total opportunities: 100")
    print(f"  Winning trades: 5 (5%)")
    print(f"  Losing trades: 95 (95%)")
    print()

    print("Model: Always predicts 'losing trade' (never takes a trade)")
    print()

    print("Metrics:")
    print(f"  Accuracy:  {accuracy:.2%}")
    print(f"  MCC:       {mcc:.3f}")
    print()

    print("Interpretation:")
    print(f"  Accuracy says: {accuracy:.1%}% accuracy - EXCELLENT? ✗")
    print("    But model never finds winning trades! Useless for trading.")
    print()
    print(f"  MCC says: {mcc:.3f} - POOR ✓")
    print("    Model has no predictive power. Correctly identifies problem.")
    print()

    print("Conclusion:")
    print("  Accuracy is misleading with imbalanced data.")
    print("  MCC correctly identifies that the model has no predictive power.")
    print("  For trading (imbalanced by nature), always use MCC!")
    print()
    print("=" * 70)
    print()


if __name__ == '__main__':
    # Run all examples
    example_mcc_integration()
    example_mcc_comparison()
    example_mcc_vs_accuracy()

    print("\nAll examples completed successfully!")
    print("\nFor more information, see:")
    print("  - app/backtesting/metrics.py: calculate_matthews_corrcoef()")
    print("  - app/strategies/momentum_modular/learning/supervised_learning_engine.py")
    print("  - MCC_IMPLEMENTATION_REPORT.md")
