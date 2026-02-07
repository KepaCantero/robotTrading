"""
Financial ML Integration Module

Comprehensive integration of all López de Prado Financial ML methods
for the AlgoTrading system.

This module provides a unified interface to:
1. Fractional Differentiation for stationary features
2. Triple Barrier Method for dynamic labeling
3. Purged K-Fold CV for robust validation
4. Meta-labeling for position sizing
5. Bet sizing from meta-labels
6. Feature Importance (MDI, MDA, SFI)

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado

Example:
    >>> from app.backtesting.financial_ml import FinancialMLPipeline
    >>> pipeline = FinancialMLPipeline()
    >>> result = pipeline.fit_predict(X, y, prices)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Import López de Prado components
from .feature_engineering import (
    FeatureImportanceConfig,
    FinancialMLFeatureImportance,
    FractionalDifferentiation,
    ImportanceResult,
)
from .labeling import (
    BetSizing,
    BetSizingConfig,
    MetaLabeling,
    MetaLabelingConfig,
    TripleBarrierConfig,
    TripleBarrierLabeler,
)
from .validation import purged_kfold_splits

logger = logging.getLogger(__name__)


@dataclass
class FinancialMLConfig:
    """Unified configuration for Financial ML pipeline."""

    # Fractional Differentiation
    fracdiff_threshold: float = 1e-5
    fracdiff_adfuller_alpha: float = 0.05
    apply_fracdiff: bool = True

    # Triple Barrier
    upper_barrier_pct: float = 0.02
    lower_barrier_pct: float = -0.01
    vertical_barrier_days: int = 5
    vol_scaling: bool = True

    # Purged K-Fold CV
    use_purged_cv: bool = True
    n_folds: int = 5
    purge_pct: float = 0.05
    embargo_pct: float = 0.02

    # Meta-labeling
    use_meta_labeling: bool = True
    primary_model_type: str = "rf"
    meta_model_type: str = "rf"

    # Bet Sizing
    bet_sizing_method: str = "kelly"
    kelly_fraction: float = 0.25
    max_bet_size: float = 1.0

    # Feature Importance
    compute_importance: bool = True
    importance_method: str = "combined"  # mdi, mda, sfi, combined

    # General
    random_state: int = 42
    n_jobs: int = -1


@dataclass
class FinancialMLResult:
    """Comprehensive result from Financial ML pipeline."""

    # Features
    X_original: np.ndarray
    X_transformed: np.ndarray
    feature_names: List[str]

    # Labels
    y_original: np.ndarray
    y_triple_barrier: np.ndarray
    y_meta: Optional[np.ndarray] = None

    # Predictions
    primary_predictions: Optional[np.ndarray] = None
    meta_predictions: Optional[np.ndarray] = None
    bet_sizes: Optional[np.ndarray] = None

    # Feature Importance
    importance: Optional[ImportanceResult] = None

    # Cross-validation scores
    cv_scores: Dict[str, List[float]] = field(default_factory=dict)

    # Metrics
    primary_accuracy: float = 0.0
    meta_accuracy: float = 0.0
    combined_accuracy: float = 0.0

    # Metadata
    n_samples: int = 0
    n_features: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "n_samples": self.n_samples,
            "n_features": self.n_features,
            "primary_accuracy": float(self.primary_accuracy),
            "meta_accuracy": float(self.meta_accuracy),
            "combined_accuracy": float(self.combined_accuracy),
            "cv_scores": self.cv_scores,
            "timestamp": self.timestamp.isoformat(),
        }


class FinancialMLPipeline:
    """
    Complete Financial ML pipeline integrating all López de Prado methods.

    This class provides a unified interface for:
    1. Feature engineering with fractional differentiation
    2. Labeling with triple barrier method
    3. Validation with purged K-fold CV
    4. Meta-labeling for position sizing
    5. Bet sizing from meta-labels
    6. Feature importance analysis

    Example:
        >>> pipeline = FinancialMLPipeline()
        >>> result = pipeline.fit_predict(X, prices)
        >>> print(f"Primary accuracy: {result.primary_accuracy:.2%}")
        >>> print(f"Meta accuracy: {result.meta_accuracy:.2%}")
    """

    def __init__(self, config: Optional[FinancialMLConfig] = None):
        """
        Initialize Financial ML pipeline.

        Args:
            config: Configuration for the pipeline
        """
        self.config = config or FinancialMLConfig()

        # Initialize components
        self.fracdiff = FractionalDifferentiation(
            threshold=self.config.fracdiff_threshold,
            adfuller_alpha=self.config.fracdiff_adfuller_alpha,
        )

        self.triple_barrier = TripleBarrierLabeler(
            config=TripleBarrierConfig(
                upper_barrier_pct=self.config.upper_barrier_pct,
                lower_barrier_pct=self.config.lower_barrier_pct,
                vertical_barrier_days=self.config.vertical_barrier_days,
            )
        )

        self.meta_labeling = MetaLabeling(
            config=MetaLabelingConfig(
                primary_model_type=self.config.primary_model_type,
                meta_model_type=self.config.meta_model_type,
            )
        )

        self.bet_sizing = BetSizing(
            config=BetSizingConfig(
                method=self.config.bet_sizing_method,
                kelly_fraction=self.config.kelly_fraction,
                max_position_size=self.config.max_bet_size,
            )
        )

        # State
        self._is_fitted = False
        self.feature_importance_ = None

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        prices: Union[pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> "FinancialMLPipeline":
        """
        Fit the Financial ML pipeline.

        Args:
            X: Feature matrix (n_samples, n_features)
            prices: Price series for triple barrier labeling
            y: Optional target labels (if None, generates from triple barrier)

        Returns:
            Self for method chaining

        Example:
            >>> pipeline.fit(X_train, prices_train)
        """
        # Convert to arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
            self.feature_names_ = X.columns.tolist()
        else:
            self.feature_names_ = [f"feature_{i}" for i in range(X.shape[1])]

        if isinstance(prices, pd.Series):
            prices = prices.values
            self.price_index_ = prices.index.tolist()
        else:
            self.price_index_ = list(range(len(prices)))

        # Store original features
        self.X_original_ = X

        # Step 1: Apply fractional differentiation if requested
        if self.config.apply_fracdiff:
            logger.info("Applying fractional differentiation...")
            X_transformed = self._apply_fracdiff_to_features(X, prices)
        else:
            X_transformed = X

        self.X_transformed_ = X_transformed

        # Step 2: Generate triple barrier labels if not provided
        if y is None:
            logger.info("Generating triple barrier labels...")
            events = pd.Series(self.price_index_)
            prices_series = pd.Series(prices, index=self.price_index_)

            labels_df = self.triple_barrier.fit_transform(prices_series, events)
            y_triple_barrier = labels_df["label"].values
        else:
            if isinstance(y, pd.Series):
                y_triple_barrier = y.values
            else:
                y_triple_barrier = y

        self.y_triple_barrier_ = y_triple_barrier

        # Step 3: Train meta-labeling model if requested
        if self.config.use_meta_labeling:
            logger.info("Training meta-labeling model...")
            # Use purged CV for training
            if self.config.use_purged_cv:
                splits = purged_kfold_splits(
                    X_transformed,
                    n_splits=self.config.n_folds,
                    purge_pct=self.config.purge_pct,
                    embargo_pct=self.config.embargo_pct,
                )
                # Train on first split for simplicity
                train_idx, _ = splits[0]
                X_train_cv = X_transformed[train_idx]
                y_train_cv = y_triple_barrier[train_idx]
            else:
                X_train_cv = X_transformed
                y_train_cv = y_triple_barrier

            self.meta_labeling.fit(X_train_cv, y_train_cv)

        # Step 4: Calculate feature importance if requested
        if self.config.compute_importance:
            logger.info("Calculating feature importance...")
            importance_config = FeatureImportanceConfig(
                compute_mdi=self.config.importance_method in ["mdi", "combined"],
                compute_mda=self.config.importance_method in ["mda", "combined"],
                compute_sfi=self.config.importance_method in ["sfi", "combined"],
            )

            importance_calculator = FinancialMLFeatureImportance(importance_config)

            # Train a simple model for importance calculation
            from sklearn.ensemble import RandomForestClassifier

            model = RandomForestClassifier(
                n_estimators=100, random_state=self.config.random_state, n_jobs=self.config.n_jobs
            )
            model.fit(X_transformed, y_triple_barrier)

            self.feature_importance_ = importance_calculator.calculate_importance(
                model, X_transformed, y_triple_barrier, self.feature_names_
            )

        self._is_fitted = True
        self.n_features_ = X.shape[1]

        return self

    def predict(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        prices: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> FinancialMLResult:
        """
        Generate predictions with bet sizes.

        Args:
            X: Feature matrix
            prices: Optional price series for triple barrier

        Returns:
            FinancialMLResult with predictions and bet sizes

        Example:
            >>> result = pipeline.predict(X_test, prices_test)
            >>> print(f"Bets: {result.bet_sizes}")
        """
        if not self._is_fitted:
            raise ValueError("Pipeline must be fitted before prediction")

        # Convert to arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(prices, pd.Series):
            prices = prices.values

        # Apply fractional differentiation if used in training
        if self.config.apply_fracdiff:
            X_transformed = self._apply_fracdiff_to_features(X, prices)
        else:
            X_transformed = X

        # Generate predictions
        if self.config.use_meta_labeling:
            meta_result = self.meta_labeling.predict(X_transformed)
            primary_predictions = meta_result.primary_predictions
            meta_proba = meta_result.meta_proba

            # Calculate bet sizes
            bet_result = self.bet_sizing.calculate_sizes(
                predictions=primary_predictions,
                probabilities=meta_proba,
            )
            bet_sizes = bet_result.bet_sizes

            meta_predictions = meta_result.meta_predictions
        else:
            # Simple predictions without meta-labeling
            primary_predictions = self.meta_labeling.primary_model.predict(X_transformed)
            meta_predictions = None
            bet_sizes = None

        return FinancialMLResult(
            X_original=X,
            X_transformed=X_transformed,
            feature_names=self.feature_names_,
            y_original=np.zeros(len(X)),  # Will be filled if y provided
            y_triple_barrier=np.zeros(len(X)),
            primary_predictions=primary_predictions,
            meta_predictions=meta_predictions,
            bet_sizes=bet_sizes,
            importance=self.feature_importance_,
            n_samples=len(X),
            n_features=self.n_features_,
        )

    def fit_predict(
        self,
        X_train: Union[pd.DataFrame, np.ndarray],
        prices_train: Union[pd.Series, np.ndarray],
        X_test: Union[pd.DataFrame, np.ndarray],
        prices_test: Optional[Union[pd.Series, np.ndarray]] = None,
        y_test: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> FinancialMLResult:
        """
        Fit on training data and predict on test data.

        Args:
            X_train: Training features
            prices_train: Training prices
            X_test: Test features
            prices_test: Optional test prices
            y_test: Optional test labels for evaluation

        Returns:
            FinancialMLResult with predictions and metrics

        Example:
            >>> result = pipeline.fit_predict(X_train, prices_train, X_test, prices_test, y_test)
            >>> print(f"Combined accuracy: {result.combined_accuracy:.2%}")
        """
        # Fit pipeline
        self.fit(X_train, prices_train)

        # Predict on test set
        result = self.predict(X_test, prices_test)

        # Evaluate if y_test is provided
        if y_test is not None:
            if isinstance(y_test, pd.Series):
                y_test = y_test.values

            # Generate triple barrier labels for test set
            if prices_test is not None:
                if isinstance(prices_test, pd.Series):
                    prices_test_series = prices_test
                else:
                    prices_test_series = pd.Series(prices_test)

                events = pd.Series(range(len(prices_test)))
                labels_df = self.triple_barrier.fit_transform(prices_test_series, events)
                y_test_tb = labels_df["label"].values
            else:
                y_test_tb = y_test

            result.y_triple_barrier = y_test_tb
            result.y_original = y_test

            # Calculate accuracies
            if result.primary_predictions is not None:
                result.primary_accuracy = np.mean(result.primary_predictions == y_test_tb)

            if result.meta_predictions is not None:
                # Meta-labels: correct if primary prediction was right
                meta_labels = (result.primary_predictions == y_test_tb).astype(int)
                result.meta_accuracy = np.mean(result.meta_predictions == meta_labels)

                # Combined accuracy
                mask = result.meta_predictions == 1
                if mask.sum() > 0:
                    result.combined_accuracy = np.mean(
                        result.primary_predictions[mask] == y_test_tb[mask]
                    )

        return result

    def cross_validate(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        prices: Union[pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Dict[str, List[float]]:
        """
        Perform purged K-fold cross-validation.

        Args:
            X: Feature matrix
            prices: Price series
            y: Optional target labels

        Returns:
            Dictionary with CV scores for each fold

        Example:
            >>> cv_scores = pipeline.cross_validate(X, prices, y)
            >>> print(f"Mean accuracy: {np.mean(cv_scores['primary_accuracy']):.2%}")
        """
        # Convert to arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(prices, pd.Series):
            prices = prices.values

        # Generate labels if not provided
        if y is None:
            events = pd.Series(range(len(prices)))
            prices_series = pd.Series(prices)
            labels_df = self.triple_barrier.fit_transform(prices_series, events)
            y = labels_df["label"].values

        # Apply fractional differentiation if requested
        if self.config.apply_fracdiff:
            X_transformed = self._apply_fracdiff_to_features(X, prices)
        else:
            X_transformed = X

        # Generate purged splits
        splits = purged_kfold_splits(
            X_transformed,
            n_splits=self.config.n_folds,
            purge_pct=self.config.purge_pct,
            embargo_pct=self.config.embargo_pct,
        )

        cv_scores = {
            "primary_accuracy": [],
            "meta_accuracy": [],
            "combined_accuracy": [],
        }

        # Perform CV
        for fold, (train_idx, test_idx) in enumerate(splits):
            logger.info(f"Running fold {fold + 1}/{self.config.n_folds}")

            X_train_fold, X_test_fold = X_transformed[train_idx], X_transformed[test_idx]
            y_train_fold, y_test_fold = y[train_idx], y[test_idx]

            # Train meta-labeling
            if self.config.use_meta_labeling:
                self.meta_labeling.fit(X_train_fold, y_train_fold)

                # Predict
                meta_result = self.meta_labeling.predict(X_test_fold)
                primary_pred = meta_result.primary_predictions
                meta_pred = meta_result.meta_predictions
            else:
                primary_pred = self.meta_labeling.primary_model.predict(X_test_fold)
                meta_pred = None

            # Calculate metrics
            primary_acc = np.mean(primary_pred == y_test_fold)
            cv_scores["primary_accuracy"].append(primary_acc)

            if meta_pred is not None:
                meta_labels = (primary_pred == y_test_fold).astype(int)
                meta_acc = np.mean(meta_pred == meta_labels)
                cv_scores["meta_accuracy"].append(meta_acc)

                mask = meta_pred == 1
                if mask.sum() > 0:
                    combined_acc = np.mean(primary_pred[mask] == y_test_fold[mask])
                    cv_scores["combined_accuracy"].append(combined_acc)
                else:
                    cv_scores["combined_accuracy"].append(0.0)

        return cv_scores

    def _apply_fracdiff_to_features(self, X: np.ndarray, prices: np.ndarray) -> np.ndarray:
        """Apply fractional differentiation to features."""
        X_transformed = np.zeros_like(X)

        for i in range(X.shape[1]):
            # Try to find optimal d for first column
            if i == 0:
                feature_series = pd.Series(X[:, i])
                try:
                    optimal_d, _, _ = self.fracdiff.find_optimal_d(feature_series)
                    logger.info(f"Feature {i}: optimal d = {optimal_d:.3f}")
                except (ValueError, TypeError, RuntimeError):
                    optimal_d = 0.5  # Default
                    logger.warning(f"Could not find optimal d for feature {i}, using {optimal_d}")
            else:
                optimal_d = 0.5  # Use default for other features

            # Apply fractional differentiation
            try:
                frac_diff = self.fracdiff.fractional_diff(pd.Series(X[:, i]), d=optimal_d)
                X_transformed[:, i] = frac_diff.fillna(0).values
            except (ValueError, TypeError, RuntimeError):
                X_transformed[:, i] = X[:, i]  # Fallback to original

        return X_transformed


# Convenience functions
def apply_financial_ml(
    X_train: Union[pd.DataFrame, np.ndarray],
    prices_train: Union[pd.Series, np.ndarray],
    X_test: Union[pd.DataFrame, np.ndarray],
    prices_test: Union[pd.Series, np.ndarray],
    y_test: Optional[Union[pd.Series, np.ndarray]] = None,
    config: Optional[FinancialMLConfig] = None,
) -> FinancialMLResult:
    """
    Convenience function to apply complete Financial ML pipeline.

    Args:
        X_train: Training features
        prices_train: Training prices
        X_test: Test features
        prices_test: Test prices
        y_test: Optional test labels
        config: Optional configuration

    Returns:
        FinancialMLResult with predictions and metrics

    Example:
        >>> result = apply_financial_ml(X_train, prices_train, X_test, prices_test, y_test)
        >>> print(f"Combined accuracy: {result.combined_accuracy:.2%}")
        >>> print(f"Top features: {result.importance.get_top_features()}")
    """
    pipeline = FinancialMLPipeline(config)
    return pipeline.fit_predict(X_train, prices_train, X_test, prices_test, y_test)


def calculate_lopez_de_prado_features(
    prices: pd.Series,
    features: Optional[pd.DataFrame] = None,
    config: Optional[FinancialMLConfig] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Calculate López de Prado features and labels.

    Args:
        prices: Price series
        features: Optional existing features
        config: Optional configuration

    Returns:
        Tuple of (features DataFrame, labels Series)

    Example:
        >>> X, y = calculate_lopez_de_prado_features(prices)
        >>> print(f"Features shape: {X.shape}, Labels shape: {y.shape}")
    """
    config = config or FinancialMLConfig()

    # Generate features if not provided
    if features is None:
        # Basic features: returns, volatility, etc.
        features = pd.DataFrame(index=prices.index)

        # Returns
        features["returns"] = prices.pct_change()

        # Log returns
        features["log_returns"] = np.log(prices / prices.shift(1))

        # Volatility
        features["volatility_20"] = features["returns"].rolling(20).std()

        # Momentum
        for period in [5, 10, 20]:
            features[f"momentum_{period}"] = prices.pct_change(period)

        # RSI
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features["rsi"] = 100 - (100 / (1 + rs))

        # Drop NaN
        features = features.dropna()

    # Apply fractional differentiation
    if config.apply_fracdiff:
        fracdiff = FractionalDifferentiation(threshold=config.fracdiff_threshold)

        fracdiff_features = pd.DataFrame(index=features.index)
        for col in features.columns:
            try:
                optimal_d, _, _ = fracdiff.find_optimal_d(features[col].dropna())
                fracdiff_series = fracdiff.fractional_diff(features[col], d=optimal_d)
                fracdiff_features[f"{col}_fracdiff"] = fracdiff_series
            except (ValueError, TypeError, RuntimeError):
                fracdiff_features[col] = features[col]

        X = fracdiff_features.dropna()
    else:
        X = features

    # Generate triple barrier labels
    triple_barrier = TripleBarrierLabeler(
        config=TripleBarrierConfig(
            upper_barrier_pct=config.upper_barrier_pct,
            lower_barrier_pct=config.lower_barrier_pct,
            vertical_barrier_days=config.vertical_barrier_days,
        )
    )

    # Align indices
    common_index = X.index.intersection(prices.index)
    X_aligned = X.loc[common_index]
    prices_aligned = prices.loc[common_index]

    events = pd.Series(range(len(prices_aligned)))
    labels_df = triple_barrier.fit_transform(prices_aligned, events)

    y = labels_df["label"]

    return X_aligned, y
