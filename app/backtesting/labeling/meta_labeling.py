"""
Meta-Labeling Implementation for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 3.

Meta-labeling is a two-stage ML approach:
1. Primary Model: Predicts signal direction (buy/sell)
2. Meta Model: Predicts whether the primary model will be correct

This allows us to:
- Separate signal direction from position sizing
- Use meta-labels for bet sizing
- Improve risk-adjusted returns
- Reduce false positive rate

Key Concepts:
- Primary labels: Original trading signals (-1, 0, 1)
- Meta labels: Binary (1 if primary was correct, 0 otherwise)
- Bet sizing: Position size based on meta-model probability
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Custom exceptions for meta-labeling (CC-006: Specific exception types)
class MetaLabelingError(Exception):
    """Base exception for meta-labeling errors."""


class ModelNotFittedError(MetaLabelingError):
    """Raised when attempting to predict before fitting the model."""


class DataValidationError(MetaLabelingError):
    """Raised when input data validation fails."""


class BetSizingValidationError(MetaLabelingError):
    """Raised when bet sizing validation fails (TRD-001)."""


@dataclass
class MetaLabelingConfig:
    """Configuration for meta-labeling."""

    # Primary model settings
    primary_model_type: str = "rf"  # rf, xgb, lgb, logistic
    primary_threshold: float = 0.5  # Probability threshold for primary model

    # Meta model settings
    meta_model_type: str = "rf"  # rf, xgb, lgb, logistic
    meta_threshold: float = 0.5  # Probability threshold for meta model

    # Bet sizing settings
    bet_sizing_method: str = "kelly"  # kelly, probability, fixed
    max_bet_size: float = 1.0  # Maximum position size
    min_bet_size: float = 0.0  # Minimum position size

    # Cross-validation settings
    use_purged_cv: bool = True
    n_folds: int = 5
    purge_pct: float = 0.05
    embargo_pct: float = 0.02

    # Feature importance settings
    compute_importance: bool = True
    importance_method: str = "mdi"  # mdi, mda, sfi

    def __post_init__(self):
        """Validate configuration."""
        if self.primary_threshold < 0 or self.primary_threshold > 1:
            raise ValueError("primary_threshold must be between 0 and 1")

        if self.meta_threshold < 0 or self.meta_threshold > 1:
            raise ValueError("meta_threshold must be between 0 and 1")

        if self.max_bet_size < 0 or self.max_bet_size > 1:
            raise ValueError("max_bet_size must be between 0 and 1")

        if self.min_bet_size < 0 or self.min_bet_size > self.max_bet_size:
            raise ValueError("min_bet_size must be between 0 and max_bet_size")


@dataclass
class MetaLabelingResult:
    """Result of meta-labeling analysis."""

    # Predictions
    primary_predictions: np.ndarray
    primary_proba: np.ndarray
    meta_predictions: np.ndarray
    meta_proba: np.ndarray

    # Performance metrics
    primary_accuracy: float
    meta_accuracy: float
    combined_accuracy: float

    # Bet sizes
    bet_sizes: np.ndarray

    # Feature importance
    primary_importance: Dict[str, float] = field(default_factory=dict)
    meta_importance: Dict[str, float] = field(default_factory=dict)

    # Metadata
    n_samples: int = 0
    n_features: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_predictions": self.primary_predictions.tolist(),
            "primary_proba": self.primary_proba.tolist(),
            "meta_predictions": self.meta_predictions.tolist(),
            "meta_proba": self.meta_proba.tolist(),
            "primary_accuracy": float(self.primary_accuracy),
            "meta_accuracy": float(self.meta_accuracy),
            "combined_accuracy": float(self.combined_accuracy),
            "bet_sizes": self.bet_sizes.tolist(),
            "primary_importance": self.primary_importance,
            "meta_importance": self.meta_importance,
            "n_samples": self.n_samples,
            "n_features": self.n_features,
            "timestamp": self.timestamp.isoformat(),
        }


class MetaLabeling:
    """
    Meta-labeling implementation for financial ML.

    This class implements the complete meta-labeling pipeline:
    1. Train primary model on original features
    2. Generate meta-labels based on primary model correctness
    3. Train meta-model on features + primary predictions
    4. Use meta-model probabilities for bet sizing

    Example:
        >>> meta_labeling = MetaLabeling()
        >>> result = meta_labeling.fit_predict(X_train, y_train, X_test)
        >>> # Use result.bet_sizes for position sizing
    """

    def __init__(self, config: Optional[MetaLabelingConfig] = None):
        """
        Initialize meta-labeling pipeline.

        Args:
            config: Configuration for meta-labeling
        """
        self.config = config or MetaLabelingConfig()
        self.primary_model = None
        self.meta_model = None
        self._is_fitted = False

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        sample_weights: Optional[np.ndarray] = None,
    ) -> "MetaLabeling":
        """
        Fit both primary and meta models.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target labels (-1, 0, 1 for trading signals)
            sample_weights: Optional sample weights for training

        Returns:
            Self for method chaining

        Example:
            >>> meta_labeling = MetaLabeling()
            >>> meta_labeling.fit(X_train, y_train)
        """
        # Convert to numpy arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        # Validate inputs (CC-006: Specific exception types)
        if len(X) != len(y):
            raise DataValidationError(f"X and y must have same length: {len(X)} != {len(y)}")

        if len(X) == 0:
            raise DataValidationError("X and y must have at least one sample")

        # Step 1: Train primary model
        logger.info("Training primary model...")
        self.primary_model = self._create_model(self.config.primary_model_type)
        self.primary_model.fit(
            X,
            y,
            sample_weight=sample_weights,
        )

        # Step 2: Generate primary predictions and meta-labels
        primary_pred = self.primary_model.predict(X)
        primary_proba = self._get_proba(self.primary_model, X)

        # Create meta-labels: 1 if primary was correct, 0 otherwise
        meta_labels = (primary_pred == y).astype(int)

        logger.info(f"Primary accuracy: {np.mean(primary_pred == y):.4f}")
        logger.info(f"Meta-label distribution: {np.bincount(meta_labels)}")

        # Step 3: Prepare features for meta-model
        # Include original features + primary predictions + primary probabilities
        X_meta = np.column_stack([X, primary_pred, primary_proba])

        # Step 4: Train meta-model
        logger.info("Training meta model...")
        self.meta_model = self._create_model(self.config.meta_model_type)
        self.meta_model.fit(
            X_meta,
            meta_labels,
            sample_weight=sample_weights,
        )

        # Evaluate meta-model
        meta_pred = self.meta_model.predict(X_meta)
        self._get_proba(self.meta_model, X_meta)
        meta_accuracy = np.mean(meta_pred == meta_labels)

        logger.info(f"Meta-model accuracy: {meta_accuracy:.4f}")

        # Extract feature importance if requested
        if self.config.compute_importance:
            if hasattr(self.primary_model, "feature_importances_"):
                self.primary_importance_ = self.primary_model.feature_importances_
            if hasattr(self.meta_model, "feature_importances_"):
                # Meta-model has extra features (pred, proba)
                self.meta_importance_ = self.meta_model.feature_importances_

        self._is_fitted = True
        self.n_features_ = X.shape[1]

        return self

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> MetaLabelingResult:
        """
        Generate predictions and bet sizes.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            MetaLabelingResult with predictions and bet sizes

        Example:
            >>> result = meta_labeling.predict(X_test)
            >>> print(f"Bet sizes: {result.bet_sizes}")
        """
        if not self._is_fitted:
            raise ModelNotFittedError("Model must be fitted before prediction. Call fit() first.")

        # Convert to numpy array
        if isinstance(X, pd.DataFrame):
            X = X.values

        # Validate input
        if len(X) == 0:
            raise DataValidationError("X must have at least one sample")

        if X.shape[1] != self.n_features_:
            raise DataValidationError(
                f"X has {X.shape[1]} features but model expects {self.n_features_}"
            )

        # Primary model predictions
        primary_pred = self.primary_model.predict(X)
        primary_proba = self._get_proba(self.primary_model, X)

        # Prepare meta features
        X_meta = np.column_stack([X, primary_pred, primary_proba])

        # Meta model predictions
        meta_pred = self.meta_model.predict(X_meta)
        meta_proba = self._get_proba(self.meta_model, X_meta)

        # Calculate bet sizes from meta probabilities
        bet_sizes = self._calculate_bet_sizes(meta_proba)

        # TRD-001: Validate bet sizes
        self._validate_bet_sizes(bet_sizes)

        return MetaLabelingResult(
            primary_predictions=primary_pred,
            primary_proba=primary_proba,
            meta_predictions=meta_pred,
            meta_proba=meta_proba,
            primary_accuracy=0.0,  # Will be calculated if y is provided
            meta_accuracy=0.0,
            combined_accuracy=0.0,
            bet_sizes=bet_sizes,
            primary_importance=getattr(self, "primary_importance_", {}),
            meta_importance=getattr(self, "meta_importance_", {}),
            n_samples=len(X),
            n_features=self.n_features_,
        )

    def fit_predict(
        self,
        X_train: Union[pd.DataFrame, np.ndarray],
        y_train: Union[pd.Series, np.ndarray],
        X_test: Union[pd.DataFrame, np.ndarray],
        y_test: Optional[Union[pd.Series, np.ndarray]] = None,
        sample_weights: Optional[np.ndarray] = None,
    ) -> MetaLabelingResult:
        """
        Fit on training data and predict on test data.

        Args:
            X_train: Training features
            y_train: Training labels
            X_test: Test features
            y_test: Optional test labels for evaluation
            sample_weights: Optional sample weights

        Returns:
            MetaLabelingResult with predictions and metrics

        Example:
            >>> result = meta_labeling.fit_predict(X_train, y_train, X_test, y_test)
            >>> print(f"Combined accuracy: {result.combined_accuracy}")
        """
        # Fit models
        self.fit(X_train, y_train, sample_weights)

        # Predict on test set
        result = self.predict(X_test)

        # Calculate accuracies if y_test is provided
        if y_test is not None:
            if isinstance(y_test, pd.Series):
                y_test = y_test.values

            result.primary_accuracy = np.mean(result.primary_predictions == y_test)

            # Meta-labels for test set
            test_meta_labels = (result.primary_predictions == y_test).astype(int)
            result.meta_accuracy = np.mean(result.meta_predictions == test_meta_labels)

            # Combined accuracy: only count when meta-model says yes
            mask = result.meta_predictions == 1
            if mask.sum() > 0:
                result.combined_accuracy = np.mean(result.primary_predictions[mask] == y_test[mask])
            else:
                result.combined_accuracy = 0.0

            logger.info(f"Test primary accuracy: {result.primary_accuracy:.4f}")
            logger.info(f"Test meta accuracy: {result.meta_accuracy:.4f}")
            logger.info(f"Test combined accuracy: {result.combined_accuracy:.4f}")

        return result

    def _create_model(self, model_type: str) -> Any:
        """
        Create ML model based on type.

        Args:
            model_type: Type of model ('rf', 'xgb', 'lgb', 'logistic')

        Returns:
            Model instance
        """
        if model_type == "rf":
            from sklearn.ensemble import RandomForestClassifier

            return RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1,
            )
        elif model_type == "xgb":
            try:
                from xgboost import XGBClassifier

                return XGBClassifier(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1,
                    eval_metric="logloss",
                )
            except ImportError:
                # LOG-004: Add exc_info=True for stack traces
                logger.warning(
                    "XGBoost not available, falling back to RandomForest",
                    exc_info=True,
                )
                return self._create_model("rf")

        elif model_type == "lgb":
            try:
                from lightgbm import LGBMClassifier

                return LGBMClassifier(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.1,
                    random_state=42,
                    n_jobs=-1,
                    verbose=-1,
                )
            except ImportError:
                # LOG-004: Add exc_info=True for stack traces
                logger.warning(
                    "LightGBM not available, falling back to RandomForest",
                    exc_info=True,
                )
                return self._create_model("rf")

        elif model_type == "logistic":
            from sklearn.linear_model import LogisticRegression

            return LogisticRegression(
                random_state=42,
                max_iter=1000,
                n_jobs=-1,
            )

        else:
            raise DataValidationError(f"Unknown model type: {model_type}")

    def _get_proba(self, model: Any, X: np.ndarray) -> np.ndarray:
        """
        Get probability predictions from model.

        Args:
            model: Fitted model
            X: Feature matrix

        Returns:
            Probability array
        """
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)

            # Handle binary and multi-class
            if proba.shape[1] == 2:
                return proba[:, 1]  # Probability of positive class
            else:
                return proba.max(axis=1)  # Max probability for multi-class
        else:
            # Fallback to binary predictions
            return model.predict(X)

    def _calculate_bet_sizes(self, meta_proba: np.ndarray) -> np.ndarray:
        """
        Calculate bet sizes from meta-model probabilities.

        Args:
            meta_proba: Meta-model probabilities

        Returns:
            Bet sizes array
        """
        if self.config.bet_sizing_method == "kelly":
            # Kelly criterion: f = (bp - q) / b
            # where b = odds, p = probability of win, q = 1-p
            # Simplified: f = 2p - 1 (assuming even odds)
            bet_size = 2 * meta_proba - 1

        elif self.config.bet_sizing_method == "probability":
            # Direct probability sizing
            bet_size = meta_proba

        elif self.config.bet_sizing_method == "fixed":
            # Fixed size based on threshold
            bet_size = (meta_proba >= self.config.meta_threshold).astype(float)

        else:
            logger.error(f"Unknown bet sizing method: {self.config.bet_sizing_method}")
            raise DataValidationError(f"Unknown bet sizing method: {self.config.bet_sizing_method}")

        # Clip to [min_bet_size, max_bet_size]
        bet_size = np.clip(bet_size, self.config.min_bet_size, self.config.max_bet_size)

        # Only bet when meta-model says yes
        mask = meta_proba >= self.config.meta_threshold
        bet_size[~mask] = 0.0

        return bet_size

    def _validate_bet_sizes(self, bet_sizes: np.ndarray) -> None:
        """
        Validate bet sizes (TRD-001: Trading system validation).

        Args:
            bet_sizes: Array of bet sizes to validate

        Raises:
            BetSizingValidationError: If bet sizes are invalid
        """
        # Check for NaN or Inf
        if np.any(np.isnan(bet_sizes)):
            raise BetSizingValidationError("Bet sizes contain NaN values")

        if np.any(np.isinf(bet_sizes)):
            raise BetSizingValidationError("Bet sizes contain infinite values")

        # Check bounds
        if np.any(bet_sizes < self.config.min_bet_size):
            raise BetSizingValidationError(
                f"Bet sizes below minimum: {bet_sizes.min()} < {self.config.min_bet_size}"
            )

        if np.any(bet_sizes > self.config.max_bet_size):
            raise BetSizingValidationError(
                f"Bet sizes above maximum: {bet_sizes.max()} > {self.config.max_bet_size}"
            )

        # Check total exposure (TRD-001)
        total_exposure = np.abs(bet_sizes).sum()
        if total_exposure > 1.0:
            logger.warning(
                f"Total bet size exposure exceeds 1.0: {total_exposure:.4f}. "
                f"This may lead to over-leveraging.",
            )


def apply_meta_labeling(
    X_train: Union[pd.DataFrame, np.ndarray],
    y_train: Union[pd.Series, np.ndarray],
    X_test: Union[pd.DataFrame, np.ndarray],
    y_test: Optional[Union[pd.Series, np.ndarray]] = None,
    config: Optional[MetaLabelingConfig] = None,
) -> MetaLabelingResult:
    """
    Convenience function to apply meta-labeling.

    Args:
        X_train: Training features
        y_train: Training labels
        X_test: Test features
        y_test: Optional test labels
        config: Optional configuration

    Returns:
        MetaLabelingResult with predictions and bet sizes

    Example:
        >>> result = apply_meta_labeling(X_train, y_train, X_test, y_test)
        >>> print(f"Bet sizes: {result.bet_sizes}")
    """
    meta_labeling = MetaLabeling(config)
    return meta_labeling.fit_predict(X_train, y_train, X_test, y_test)


def calculate_meta_labels(
    primary_predictions: np.ndarray,
    actual_returns: np.ndarray,
    threshold: float = 0.0,
) -> np.ndarray:
    """
    Calculate meta-labels from primary predictions and actual returns.

    Meta-label is 1 if the primary prediction was correct (profitable),
    0 otherwise.

    Args:
        primary_predictions: Primary model predictions (-1, 0, 1)
        actual_returns: Actual returns for each prediction
        threshold: Minimum return to consider "correct"

    Returns:
        Binary meta-labels array

    Example:
        >>> meta_labels = calculate_meta_labels(predictions, returns, threshold=0.01)
        >>> print(f"Meta-label distribution: {np.bincount(meta_labels)}")
    """
    meta_labels = np.zeros(len(primary_predictions), dtype=int)

    for i, (pred, ret) in enumerate(zip(primary_predictions, actual_returns)):
        # Check if prediction was correct and profitable
        if (pred == 1 and ret > threshold) or (pred == -1 and ret < -threshold):
            meta_labels[i] = 1
        else:
            meta_labels[i] = 0

    return meta_labels


def snv_to_signal(
    side: np.ndarray,
    meta_labels: np.ndarray,
) -> np.ndarray:
    """
    Convert side and meta-labels to final trading signals.

    Only take trades where meta-label says yes (1).

    Args:
        side: Primary model side predictions (-1, 0, 1)
        meta_labels: Meta-labels (0 or 1)

    Returns:
        Final signals array

    Example:
        >>> final_signals = snv_to_signal(sides, meta_labels)
        >>> print(f"Number of trades: {(final_signals != 0).sum()}")
    """
    return side * meta_labels


def get_meta_labeling(config: Optional[MetaLabelingConfig] = None) -> MetaLabeling:
    """
    Get a MetaLabeling instance for López de Prado's meta-labeling approach.

    This is a convenience function for the compliance engine to check if
    López de Prado systems are available.

    Args:
        config: Optional configuration for meta-labeling

    Returns:
        MetaLabeling instance

    Example:
        >>> meta_labeling = get_meta_labeling()
        >>> result = meta_labeling.fit_predict(X_train, y_train, X_test, y_test)
    """
    return MetaLabeling(config=config)
