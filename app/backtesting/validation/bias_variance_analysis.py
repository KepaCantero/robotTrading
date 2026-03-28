"""
Bias-Variance Decomposition and Analysis for Financial ML Models.

This module implements bias-variance tradeoff analysis as described in
Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning".

Key Concepts:
- Bias-variance decomposition
- Learning curve analysis
- Model stability tests
- Irreducible error estimation
- Optimal model complexity selection

Reference:
    "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    Chapter 7: Model Assessment and Selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ModelComplexityLevel(Enum):
    """Model complexity assessment levels."""

    UNDERFIT = "underfit"  # High bias, low variance
    OPTIMAL = "optimal"  # Balanced bias and variance
    OVERFIT = "overfit"  # Low bias, high variance


@dataclass
class BiasVarianceResult:
    """Result of bias-variance decomposition."""

    timestamp: datetime
    model_name: str
    bias_squared: float
    variance: float
    irreducible_error: float
    total_error: float
    complexity_level: ModelComplexityLevel
    bias_contribution: float  # % of total error from bias
    variance_contribution: float  # % of total error from variance
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "bias_squared": self.bias_squared,
            "variance": self.variance,
            "irreducible_error": self.irreducible_error,
            "total_error": self.total_error,
            "complexity_level": self.complexity_level.value,
            "bias_contribution": self.bias_contribution,
            "variance_contribution": self.variance_contribution,
            "details": self.details,
        }


@dataclass
class LearningCurvePoint:
    """Single point on learning curve."""

    train_size: int
    train_score: float
    test_score: float
    fit_time: float
    train_std: float = 0.0
    test_std: float = 0.0


@dataclass
class LearningCurveResult:
    """Result of learning curve analysis."""

    timestamp: datetime
    model_name: str
    curve_points: List[LearningCurvePoint]
    is_converged: bool
    convergence_gap: float  # Gap between train and test at max size
    potential_improvement: float  # Estimated improvement with more data
    suffers_high_bias: bool
    suffers_high_variance: bool
    recommended_action: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "curve_points": [
                {
                    "train_size": p.train_size,
                    "train_score": p.train_score,
                    "test_score": p.test_score,
                    "fit_time": p.fit_time,
                    "train_std": p.train_std,
                    "test_std": p.test_std,
                }
                for p in self.curve_points
            ],
            "is_converged": self.is_converged,
            "convergence_gap": self.convergence_gap,
            "potential_improvement": self.potential_improvement,
            "suffers_high_bias": self.suffers_high_bias,
            "suffers_high_variance": self.suffers_high_variance,
            "recommended_action": self.recommended_action,
            "details": self.details,
        }


@dataclass
class StabilityTestResult:
    """Result of model stability test."""

    timestamp: datetime
    model_name: str
    test_type: str
    is_stable: bool
    stability_score: float
    performance_variance: float
    coefficient_of_variation: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "test_type": self.test_type,
            "is_stable": self.is_stable,
            "stability_score": self.stability_score,
            "performance_variance": self.performance_variance,
            "coefficient_of_variation": self.coefficient_of_variation,
            "details": self.details,
        }


class BiasVarianceAnalyzer:
    """
    Bias-Variance analyzer for ML models.

    This class implements comprehensive bias-variance analysis as described
    in "The Elements of Statistical Learning" by Hastie et al.

    Key analyses:
    1. Bias-variance decomposition
    2. Learning curve analysis
    3. Temporal stability tests
    4. Cross-validation stability
    5. Bootstrap stability
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize bias-variance analyzer.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.n_bootstrap_samples = self.config.get("n_bootstrap_samples", 100)
        self.train_sizes = self.config.get("train_sizes", np.linspace(0.1, 1.0, 10))
        self.cv_folds = self.config.get("cv_folds", 5)
        self.random_state = self.config.get("random_state", 42)
        self.bias_threshold = self.config.get("bias_threshold", 0.3)
        self.variance_threshold = self.config.get("variance_threshold", 0.2)

        np.random.seed(self.random_state)

    def decompose_bias_variance(
        self,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        n_bootstrap: Optional[int] = None,
    ) -> BiasVarianceResult:
        """
        Perform bias-variance decomposition using bootstrap.

        Uses the bootstrap method to estimate bias and variance components
        of the prediction error, following ESL methodology.

        Args:
            model: ML model with fit() and predict() methods
            X: Feature matrix
            y: Target vector
            n_bootstrap: Number of bootstrap samples

        Returns:
            BiasVarianceResult with decomposition
        """
        n_bootstrap = n_bootstrap or self.n_bootstrap_samples

        logger.info(
            f"Performing bias-variance decomposition with {n_bootstrap} bootstrap samples..."
        )

        n_samples = X.shape[0]
        n_test = min(1000, n_samples // 5)  # Use 20% for testing

        # Split data
        indices = np.arange(n_samples)
        np.random.shuffle(indices)

        test_indices = indices[:n_test]
        train_indices = indices[n_test:]

        X_test, y_test = X[test_indices], y[test_indices]
        X_train, y_train = X[train_indices], y[train_indices]

        # Bootstrap predictions
        predictions = []

        for i in range(n_bootstrap):
            # Bootstrap sample
            boot_indices = np.random.choice(len(X_train), size=len(X_train), replace=True)
            X_boot = X_train[boot_indices]
            y_boot = y_train[boot_indices]

            try:
                # Clone and fit model
                from sklearn.base import clone

                model_clone = clone(model)
                model_clone.fit(X_boot, y_boot)
                y_pred = model_clone.predict(X_test)
                predictions.append(y_pred)
            except Exception as e:
                logger.warning(f"Bootstrap iteration {i} failed: {e}")
                continue

        if not predictions:
            return BiasVarianceResult(
                timestamp=datetime.now(),
                model_name=type(model).__name__,
                bias_squared=0.0,
                variance=0.0,
                irreducible_error=1.0,
                total_error=1.0,
                complexity_level=ModelComplexityLevel.OPTIMAL,
                bias_contribution=0.0,
                variance_contribution=0.0,
                details={"error": "All bootstrap iterations failed"},
            )

        predictions = np.array(predictions)  # Shape: (n_bootstrap, n_test)

        # Calculate average prediction
        y_pred_avg = np.mean(predictions, axis=0)

        # Decompose error
        # Bias^2: (E[f(x)] - y)^2
        bias_squared = np.mean((y_pred_avg - y_test) ** 2)

        # Variance: E[(f(x) - E[f(x)])^2]
        variance = np.mean(np.var(predictions, axis=0))

        # Irreducible error: σ²
        # Estimated as residual error after accounting for bias and variance
        total_mse = np.mean((predictions - y_test) ** 2)
        irreducible_error = total_mse - bias_squared - variance
        irreducible_error = max(0, irreducible_error)  # Ensure non-negative

        total_error = bias_squared + variance + irreducible_error

        # Calculate contributions
        bias_contribution = (bias_squared / total_error * 100) if total_error > 0 else 0
        variance_contribution = (variance / total_error * 100) if total_error > 0 else 0

        # Determine complexity level
        if bias_contribution > 70:
            complexity = ModelComplexityLevel.UNDERFIT
        elif variance_contribution > 50:
            complexity = ModelComplexityLevel.OVERFIT
        else:
            complexity = ModelComplexityLevel.OPTIMAL

        result = BiasVarianceResult(
            timestamp=datetime.now(),
            model_name=type(model).__name__,
            bias_squared=bias_squared,
            variance=variance,
            irreducible_error=irreducible_error,
            total_error=total_error,
            complexity_level=complexity,
            bias_contribution=bias_contribution,
            variance_contribution=variance_contribution,
            details={
                "n_bootstrap": n_bootstrap,
                "n_test_samples": n_test,
                "rmse": np.sqrt(total_error),
            },
        )

        logger.info(
            f"Bias-Variance: Bias²={bias_squared:.4f} | Var={variance:.4f} | "
            f"Complexity={complexity.value}"
        )

        return result

    def analyze_learning_curve(
        self,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        train_sizes: Optional[np.ndarray] = None,
        cv: Optional[int] = None,
        scoring: Optional[Callable] = None,
    ) -> LearningCurveResult:
        """
        Analyze learning curve to diagnose bias/variance problems.

        Following ESL methodology, this analyzes how model performance
        changes with training set size.

        Args:
            model: ML model with fit() and predict() methods
            X: Feature matrix
            y: Target vector
            train_sizes: Fractions of data to use for training
            cv: Number of CV folds
            scoring: Scoring function (higher is better)

        Returns:
            LearningCurveResult with analysis
        """
        if train_sizes is None:
            train_sizes = self.train_sizes
        if cv is None:
            cv = self.cv_folds

        logger.info("Analyzing learning curve...")

        n_samples = len(X)
        curve_points = []

        for train_frac in train_sizes:
            train_size = int(n_samples * train_frac)

            if train_size < 10:
                continue

            train_scores = []
            test_scores = []
            fit_times = []

            for fold in range(cv):
                # Create train/test split for this fold
                indices = np.arange(n_samples)
                np.random.shuffle(indices)

                test_size = n_samples // cv
                test_start = fold * test_size
                test_end = test_start + test_size

                test_indices = indices[test_start:test_end]
                train_indices = np.concatenate([indices[:test_start], indices[test_end:]])

                # Subsample training data
                if len(train_indices) > train_size:
                    train_indices = np.random.choice(train_indices, size=train_size, replace=False)

                X_train, y_train = X[train_indices], y[train_indices]
                X_test, y_test = X[test_indices], y[test_indices]

                try:
                    import time

                    from sklearn.base import clone

                    start_time = time.time()
                    model_clone = clone(model)
                    model_clone.fit(X_train, y_train)
                    fit_time = time.time() - start_time

                    # Calculate scores
                    if scoring is None:
                        # Default: R² for regression, accuracy for classification
                        train_score = model_clone.score(X_train, y_train)
                        test_score = model_clone.score(X_test, y_test)
                    else:
                        train_score = scoring(y_train, model_clone.predict(X_train))
                        test_score = scoring(y_test, model_clone.predict(X_test))

                    train_scores.append(train_score)
                    test_scores.append(test_score)
                    fit_times.append(fit_time)

                except Exception as e:
                    logger.warning(f"Learning curve point failed: {e}")
                    continue

            if train_scores and test_scores:
                curve_points.append(
                    LearningCurvePoint(
                        train_size=train_size,
                        train_score=np.mean(train_scores),
                        test_score=np.mean(test_scores),
                        fit_time=np.mean(fit_times),
                        train_std=np.std(train_scores),
                        test_std=np.std(test_scores),
                    )
                )

        # Analyze curve
        if not curve_points:
            return LearningCurveResult(
                timestamp=datetime.now(),
                model_name=type(model).__name__,
                curve_points=[],
                is_converged=False,
                convergence_gap=0.0,
                potential_improvement=0.0,
                suffers_high_bias=False,
                suffers_high_variance=False,
                recommended_action="Unable to analyze - no valid data points",
                details={"error": "No valid curve points generated"},
            )

        final_point = curve_points[-1]
        first_point = curve_points[0]

        # Check for convergence
        convergence_gap = final_point.train_score - final_point.test_score
        is_converged = convergence_gap < 0.1

        # Estimate potential improvement with more data
        if len(curve_points) >= 3:
            recent_scores = [p.test_score for p in curve_points[-3:]]
            improvement_trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            potential_improvement = improvement_trend * 5  # Project 5 more points
        else:
            potential_improvement = 0.0

        # Diagnose bias/variance problems
        suffers_high_bias = final_point.train_score < 0.8  # Underfitting
        suffers_high_variance = convergence_gap > 0.2  # Overfitting

        # Generate recommendation
        if suffers_high_bias and not suffers_high_variance:
            recommended_action = (
                "Model has high bias. Consider: "
                "1. Adding more features, "
                "2. Using a more complex model, "
                "3. Reducing regularization"
            )
        elif suffers_high_variance and not suffers_high_bias:
            recommended_action = (
                "Model has high variance. Consider: "
                "1. Getting more training data, "
                "2. Using a simpler model, "
                "3. Increasing regularization, "
                "4. Feature selection"
            )
        elif suffers_high_bias and suffers_high_variance:
            recommended_action = (
                "Model has both high bias and variance. "
                "This suggests data quality issues or "
                "inappropriate model for the problem."
            )
        else:
            recommended_action = (
                "Model appears well-balanced. "
                "Consider tuning hyperparameters for marginal improvements."
            )

        result = LearningCurveResult(
            timestamp=datetime.now(),
            model_name=type(model).__name__,
            curve_points=curve_points,
            is_converged=is_converged,
            convergence_gap=convergence_gap,
            potential_improvement=potential_improvement,
            suffers_high_bias=suffers_high_bias,
            suffers_high_variance=suffers_high_variance,
            recommended_action=recommended_action,
            details={
                "final_train_score": final_point.train_score,
                "final_test_score": final_point.test_score,
                "first_test_score": first_point.test_score,
                "improvement": final_point.test_score - first_point.test_score,
            },
        )

        logger.info(
            f"Learning Curve: Converged={is_converged} | "
            f"Gap={convergence_gap:.3f} | "
            f"High Bias={suffers_high_bias} | High Variance={suffers_high_variance}"
        )

        return result

    def test_temporal_stability(
        self,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        timestamps: np.ndarray,
        n_windows: int = 5,
    ) -> StabilityTestResult:
        """
        Test model stability across time periods.

        This validates that model performance is stable over time,
        a critical requirement for trading systems.

        Args:
            model: ML model with fit() and predict() methods
            X: Feature matrix
            y: Target vector
            timestamps: Timestamp array for samples
            n_windows: Number of time windows to test

        Returns:
            StabilityTestResult with temporal stability analysis
        """
        logger.info(f"Testing temporal stability with {n_windows} windows...")

        n_samples = len(X)
        window_size = n_samples // n_windows

        scores = []

        for i in range(n_windows):
            start_idx = i * window_size
            end_idx = (i + 1) * window_size if i < n_windows - 1 else n_samples

            X_window = X[start_idx:end_idx]
            y_window = y[start_idx:end_idx]

            if len(X_window) < 10:
                continue

            try:
                from sklearn.base import clone
                from sklearn.model_selection import cross_val_score

                model_clone = clone(model)
                cv_scores = cross_val_score(model_clone, X_window, y_window, cv=3)
                scores.extend(cv_scores)
            except Exception as e:
                logger.warning(f"Temporal window {i} failed: {e}")
                continue

        if not scores:
            return StabilityTestResult(
                timestamp=datetime.now(),
                model_name=type(model).__name__,
                test_type="temporal_stability",
                is_stable=False,
                stability_score=0.0,
                performance_variance=0.0,
                coefficient_of_variation=1.0,
                details={"error": "No valid scores computed"},
            )

        scores = np.array(scores)

        # Calculate stability metrics
        mean_score = np.mean(scores)
        score_variance = np.var(scores)
        cv = np.std(scores) / (abs(mean_score) + 1e-8)

        # Stability criterion: CV < 0.2
        is_stable = cv < 0.2
        stability_score = max(0, 1 - cv)

        result = StabilityTestResult(
            timestamp=datetime.now(),
            model_name=type(model).__name__,
            test_type="temporal_stability",
            is_stable=is_stable,
            stability_score=stability_score,
            performance_variance=score_variance,
            coefficient_of_variation=cv,
            details={
                "n_windows": n_windows,
                "mean_score": mean_score,
                "std_score": np.std(scores),
                "min_score": np.min(scores),
                "max_score": np.max(scores),
                "score_range": np.max(scores) - np.min(scores),
            },
        )

        logger.info(
            f"Temporal Stability: Stable={is_stable} | "
            f"CV={cv:.3f} | Score={stability_score:.3f}"
        )

        return result

    def test_bootstrap_stability(
        self,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        n_bootstrap: Optional[int] = None,
    ) -> StabilityTestResult:
        """
        Test model stability using bootstrap resampling.

        This tests how sensitive the model is to variations in training data,
        which is important for understanding overfitting.

        Args:
            model: ML model with fit() and predict() methods
            X: Feature matrix
            y: Target vector
            n_bootstrap: Number of bootstrap samples

        Returns:
            StabilityTestResult with bootstrap stability analysis
        """
        n_bootstrap = n_bootstrap or self.n_bootstrap_samples

        logger.info(f"Testing bootstrap stability with {n_bootstrap} samples...")

        n_samples = len(X)
        n_test = min(500, n_samples // 10)

        # Split data
        indices = np.arange(n_samples)
        np.random.shuffle(indices)

        test_indices = indices[:n_test]
        train_indices = indices[n_test:]

        X_test, y_test = X[test_indices], y[test_indices]
        X_train, y_train = X[train_indices], y[train_indices]

        scores = []

        for i in range(n_bootstrap):
            # Bootstrap sample
            boot_indices = np.random.choice(len(X_train), size=len(X_train), replace=True)
            X_boot = X_train[boot_indices]
            y_boot = y_train[boot_indices]

            try:
                from sklearn.base import clone

                model_clone = clone(model)
                model_clone.fit(X_boot, y_boot)
                score = model_clone.score(X_test, y_test)
                scores.append(score)
            except Exception as e:
                logger.warning(f"Bootstrap iteration {i} failed: {e}")
                continue

        if not scores:
            return StabilityTestResult(
                timestamp=datetime.now(),
                model_name=type(model).__name__,
                test_type="bootstrap_stability",
                is_stable=False,
                stability_score=0.0,
                performance_variance=0.0,
                coefficient_of_variation=1.0,
                details={"error": "No valid bootstrap samples"},
            )

        scores = np.array(scores)

        # Calculate stability metrics
        mean_score = np.mean(scores)
        score_variance = np.var(scores)
        cv = np.std(scores) / (abs(mean_score) + 1e-8)

        # Stability criterion: CV < 0.15 for bootstrap
        is_stable = cv < 0.15
        stability_score = max(0, 1 - cv / 0.15)

        result = StabilityTestResult(
            timestamp=datetime.now(),
            model_name=type(model).__name__,
            test_type="bootstrap_stability",
            is_stable=is_stable,
            stability_score=stability_score,
            performance_variance=score_variance,
            coefficient_of_variation=cv,
            details={
                "n_bootstrap": n_bootstrap,
                "mean_score": mean_score,
                "std_score": np.std(scores),
                "min_score": np.min(scores),
                "max_score": np.max(scores),
                "percentile_5": np.percentile(scores, 5),
                "percentile_95": np.percentile(scores, 95),
            },
        )

        logger.info(
            f"Bootstrap Stability: Stable={is_stable} | "
            f"CV={cv:.3f} | Score={stability_score:.3f}"
        )

        return result

    def comprehensive_analysis(
        self,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive bias-variance and stability analysis.

        Args:
            model: ML model to analyze
            X: Feature matrix
            y: Target vector
            timestamps: Optional timestamps for temporal stability

        Returns:
            Dict with all analysis results
        """
        results = {
            "bias_variance": None,
            "learning_curve": None,
            "temporal_stability": None,
            "bootstrap_stability": None,
        }

        # Bias-variance decomposition
        try:
            results["bias_variance"] = self.decompose_bias_variance(model, X, y)
        except Exception as e:
            logger.error(f"Bias-variance decomposition failed: {e}")

        # Learning curve analysis
        try:
            results["learning_curve"] = self.analyze_learning_curve(model, X, y)
        except Exception as e:
            logger.error(f"Learning curve analysis failed: {e}")

        # Bootstrap stability
        try:
            results["bootstrap_stability"] = self.test_bootstrap_stability(model, X, y)
        except Exception as e:
            logger.error(f"Bootstrap stability test failed: {e}")

        # Temporal stability (if timestamps provided)
        if timestamps is not None:
            try:
                results["temporal_stability"] = self.test_temporal_stability(
                    model, X, y, timestamps
                )
            except Exception as e:
                logger.error(f"Temporal stability test failed: {e}")

        return results


def analyze_bias_variance(
    model: object,
    X: np.ndarray,
    y: np.ndarray,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function for bias-variance analysis.

    Args:
        model: ML model to analyze
        X: Feature matrix
        y: Target vector
        config: Configuration dictionary

    Returns:
        Dict with analysis results
    """
    analyzer = BiasVarianceAnalyzer(config)
    return analyzer.comprehensive_analysis(model, X, y)
