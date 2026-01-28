"""
Feature Importance Methods for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 8.

This module implements three key feature importance methods:

1. MDI (Mean Decrease Impurity):
   - Built-in feature importance from tree-based models
   - Measures total reduction in impurity from each feature
   - Fast but biased towards high-cardinality features

2. MDA (Mean Decrease Accuracy):
   - Permutation importance
   - Measures decrease in accuracy when feature is shuffled
   - More reliable but computationally expensive
   - Model-agnostic

3. SFI (Single Feature Importance):
   - Trains separate model for each feature
   - Measures accuracy of single-feature models
   - Most robust but very computationally expensive

Key Concepts:
- MDI is fast but biased
- MDA is unbiased but slower
- SFI is most robust but slowest
- Use multiple methods for robust feature selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureImportanceConfig:
    """Configuration for feature importance calculation."""

    # Methods to compute
    compute_mdi: bool = True
    compute_mda: bool = True
    compute_sfi: bool = False  # Disabled by default (slow)

    # MDI settings
    mdi_normalize: bool = True
    mdi_min_samples: int = 10

    # MDA settings
    mda_n_repeats: int = 10
    mda_scoring: str = "accuracy"  # accuracy, f1, roc_auc, neg_mse
    mda_n_jobs: int = -1
    mda_random_state: int = 42

    # SFI settings
    sfi_n_splits: int = 5
    sfi_scoring: str = "accuracy"

    # General settings
    max_samples: int = 10000  # Subsample for large datasets
    feature_names: Optional[List[str]] = None

    def __post_init__(self):
        """Validate configuration."""
        valid_scoring = ["accuracy", "f1", "roc_auc", "neg_mse", "r2"]
        if self.mda_scoring not in valid_scoring:
            raise ValueError(f"mda_scoring must be one of {valid_scoring}")


@dataclass
class ImportanceResult:
    """Result of feature importance calculation."""

    feature_names: List[str]
    mdi_importance: Dict[str, float] = field(default_factory=dict)
    mda_importance: Dict[str, float] = field(default_factory=dict)
    sfi_importance: Dict[str, float] = field(default_factory=dict)

    # Rankings
    mdi_rank: Dict[str, int] = field(default_factory=dict)
    mda_rank: Dict[str, int] = field(default_factory=dict)
    sfi_rank: Dict[str, int] = field(default_factory=dict)

    # Combined
    combined_importance: Dict[str, float] = field(default_factory=dict)
    combined_rank: Dict[str, int] = field(default_factory=dict)

    # Metadata
    n_features: int = 0
    n_samples: int = 0
    methods_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "feature_names": self.feature_names,
            "mdi_importance": self.mdi_importance,
            "mda_importance": self.mda_importance,
            "sfi_importance": self.sfi_importance,
            "mdi_rank": self.mdi_rank,
            "mda_rank": self.mda_rank,
            "sfi_rank": self.sfi_rank,
            "combined_importance": self.combined_importance,
            "combined_rank": self.combined_rank,
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "methods_used": self.methods_used,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_top_features(self, method: str = "combined", n: int = 10) -> List[str]:
        """Get top N features by importance method."""
        if method == "mdi":
            importance = self.mdi_importance
        elif method == "mda":
            importance = self.mda_importance
        elif method == "sfi":
            importance = self.sfi_importance
        else:
            importance = self.combined_importance

        ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        return [f[0] for f in ranked[:n]]

    def get_low_importance_features(
        self, method: str = "combined", threshold: float = 0.01
    ) -> List[str]:
        """Get features below importance threshold."""
        if method == "mdi":
            importance = self.mdi_importance
        elif method == "mda":
            importance = self.mda_importance
        elif method == "sfi":
            importance = self.sfi_importance
        else:
            importance = self.combined_importance

        return [f for f, imp in importance.items() if imp < threshold]


class FeatureImportanceMDI:
    """
    Mean Decrease Impurity (MDI) feature importance.

    MDI is the default feature importance for tree-based models.
    It measures the total reduction in impurity (Gini or entropy)
    attributed to each feature.

    Pros:
    - Fast to compute
    - Available during training
    - Works with any tree-based model

    Cons:
    - Biased towards high-cardinality features
    - Not robust to correlated features
    - Can be misleading for continuous features
    """

    def __init__(self, config: FeatureImportanceConfig):
        """Initialize MDI calculator."""
        self.config = config

    def calculate(
        self,
        model: Any,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Calculate MDI importance from trained model.

        Args:
            model: Trained tree-based model
            feature_names: Optional feature names

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not hasattr(model, "feature_importances_"):
            logger.warning("Model does not have feature_importances_ attribute")
            return {}

        importances = model.feature_importances_

        # Normalize if requested
        if self.config.mdi_normalize:
            importances = importances / importances.sum()

        # Get feature names
        if feature_names is None:
            if hasattr(model, "feature_names_in_"):
                feature_names = list(model.feature_names_in_)
            else:
                feature_names = [f"feature_{i}" for i in range(len(importances))]

        # Create dictionary
        importance_dict = {name: float(imp) for name, imp in zip(feature_names, importances)}

        # Sort by importance
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        return importance_dict


class FeatureImportanceMDA:
    """
    Mean Decrease Accuracy (MDA) feature importance.

    MDA measures the decrease in model performance when a feature's
    values are randomly shuffled. This breaks the relationship between
    that feature and the target, revealing its true importance.

    Pros:
    - Unbiased estimate of feature importance
    - Works with any model type
    - Robust to feature correlations
    - Reflects real predictive value

    Cons:
    - Computationally expensive (requires multiple predictions)
    - Can be slow on large datasets
    - Results can vary with different random seeds
    """

    def __init__(self, config: FeatureImportanceConfig):
        """Initialize MDA calculator."""
        self.config = config

    def calculate(
        self,
        model: Any,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Calculate MDA importance via permutation.

        Args:
            model: Trained model with predict method
            X: Feature matrix
            y: Target vector
            feature_names: Optional feature names

        Returns:
            Dictionary mapping feature names to importance scores
        """
        # Convert to numpy arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        # Subsample if dataset is large
        if len(X) > self.config.max_samples:
            rng = np.random.default_rng(self.config.mda_random_state)
            indices = rng.choice(len(X), self.config.max_samples, replace=False)
            X = X[indices]
            y = y[indices]

        # Get feature names
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        # Calculate baseline score
        baseline_score = self._score_model(model, X, y)

        # Calculate importance for each feature
        importances = {}
        rng = np.random.default_rng(self.config.mda_random_state)

        for i, feature_name in enumerate(feature_names):
            score_decreases = []

            for _ in range(self.config.mda_n_repeats):
                # Shuffle feature
                X_permuted = X.copy()
                rng.shuffle(X_permuted[:, i])

                # Calculate score with permuted feature
                permuted_score = self._score_model(model, X_permuted, y)

                # Score decrease = baseline - permuted
                score_decrease = baseline_score - permuted_score
                score_decreases.append(score_decrease)

            # Average score decrease across repeats
            importances[feature_name] = float(np.mean(score_decreases))

        # Normalize to sum to 1
        total_importance = sum(importances.values())
        if total_importance > 0:
            importances = {k: v / total_importance for k, v in importances.items()}

        # Sort by importance
        importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

        return importances

    def _score_model(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
    ) -> float:
        """Calculate model score based on configured metric."""
        predictions = model.predict(X)

        if self.config.mda_scoring == "accuracy":
            return np.mean(predictions == y)
        elif self.config.mda_scoring == "f1":
            from sklearn.metrics import f1_score

            return f1_score(y, predictions, average="weighted")
        elif self.config.mda_scoring == "roc_auc":
            from sklearn.metrics import roc_auc_score

            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)
                if proba.shape[1] == 2:
                    return roc_auc_score(y, proba[:, 1])
                else:
                    return roc_auc_score(y, proba, multi_class="ovr")
            else:
                logger.warning("Model does not have predict_proba, using accuracy")
                return np.mean(predictions == y)
        elif self.config.mda_scoring == "neg_mse":
            return -np.mean((y - predictions) ** 2)
        elif self.config.mda_scoring == "r2":
            from sklearn.metrics import r2_score

            return r2_score(y, predictions)
        else:
            return np.mean(predictions == y)


class FeatureImportanceSFI:
    """
    Single Feature Importance (SFI) for financial ML.

    SFI trains a separate model for each feature and measures
    its predictive power in isolation. This is the most robust
    method but also the most computationally expensive.

    Pros:
    - Most robust to feature correlations
    - Measures individual predictive power
    - Model-agnostic
    - Useful for feature selection

    Cons:
    - Very computationally expensive
    - Ignores feature interactions
    - May underestimate importance of correlated features
    """

    def __init__(self, config: FeatureImportanceConfig):
        """Initialize SFI calculator."""
        self.config = config

    def calculate(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
        model_type: Any = None,
    ) -> Dict[str, float]:
        """
        Calculate SFI importance for each feature.

        Args:
            X: Feature matrix
            y: Target vector
            feature_names: Optional feature names
            model_type: Model class to use (default: RandomForest)

        Returns:
            Dictionary mapping feature names to importance scores
        """
        # Convert to numpy arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
            feature_names = feature_names or X.columns.tolist()
        if isinstance(y, pd.Series):
            y = y.values

        # Get feature names
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        # Import model
        if model_type is None:
            from sklearn.ensemble import RandomForestClassifier

            # Determine if classification or regression
            unique_values = len(np.unique(y))
            if unique_values <= 10:
                model_type = RandomForestClassifier
            else:
                from sklearn.ensemble import RandomForestRegressor

                model_type = RandomForestRegressor

        # Calculate importance for each feature
        importances = {}

        for i, feature_name in enumerate(feature_names):
            # Extract single feature
            X_single = X[:, i : i + 1]

            # Train model on single feature
            try:
                model = model_type(
                    n_estimators=50,
                    max_depth=3,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1,
                )
                model.fit(X_single, y)

                # Calculate score
                score = model.score(X_single, y)
                importances[feature_name] = float(score)

            except Exception as e:
                logger.warning(f"Error calculating SFI for {feature_name}: {e}")
                importances[feature_name] = 0.0

        # Normalize to sum to 1
        total_importance = sum(importances.values())
        if total_importance > 0:
            importances = {k: v / total_importance for k, v in importances.items()}

        # Sort by importance
        importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

        return importances


class FinancialMLFeatureImportance:
    """
    Complete feature importance implementation for financial ML.

    This class integrates MDI, MDA, and SFI methods following
    López de Prado's methodology.

    Example:
        >>> importance = FinancialMLFeatureImportance()
        >>> result = importance.calculate_importance(model, X_train, y_train)
        >>> print(result.get_top_features(n=10))
    """

    def __init__(self, config: Optional[FeatureImportanceConfig] = None):
        """
        Initialize feature importance calculator.

        Args:
            config: Configuration for importance calculation
        """
        self.config = config or FeatureImportanceConfig()

        # Initialize calculators
        self.mdi_calculator = FeatureImportanceMDI(self.config)
        self.mda_calculator = FeatureImportanceMDA(self.config)
        self.sfi_calculator = FeatureImportanceSFI(self.config)

    def calculate_importance(
        self,
        model: Any,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> ImportanceResult:
        """
        Calculate feature importance using multiple methods.

        Args:
            model: Trained model
            X: Feature matrix
            y: Target vector
            feature_names: Optional feature names

        Returns:
            ImportanceResult with all importance scores

        Example:
            >>> result = importance.calculate_importance(model, X, y)
            >>> print(f"Top features: {result.get_top_features()}")
        """
        # Convert to numpy arrays if needed
        if isinstance(X, pd.DataFrame):
            feature_names = feature_names or X.columns.tolist()
            X_array = X.values
        else:
            X_array = X
            feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]

        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y

        n_features = X_array.shape[1]
        n_samples = X_array.shape[0]

        # Calculate MDI importance
        mdi_importance = {}
        if self.config.compute_mdi:
            logger.info("Calculating MDI importance...")
            mdi_importance = self.mdi_calculator.calculate(model, feature_names)

        # Calculate MDA importance
        mda_importance = {}
        if self.config.compute_mda:
            logger.info("Calculating MDA importance...")
            mda_importance = self.mda_calculator.calculate(model, X_array, y_array, feature_names)

        # Calculate SFI importance
        sfi_importance = {}
        if self.config.compute_sfi:
            logger.info("Calculating SFI importance...")
            sfi_importance = self.sfi_calculator.calculate(X_array, y_array, feature_names)

        # Create rankings
        mdi_rank = self._create_ranking(mdi_importance)
        mda_rank = self._create_ranking(mda_importance)
        sfi_rank = self._create_ranking(sfi_importance)

        # Combine importances (average of available methods)
        combined_importance = self._combine_importances(
            mdi_importance, mda_importance, sfi_importance
        )
        combined_rank = self._create_ranking(combined_importance)

        # Track methods used
        methods_used = []
        if self.config.compute_mdi and mdi_importance:
            methods_used.append("mdi")
        if self.config.compute_mda and mda_importance:
            methods_used.append("mda")
        if self.config.compute_sfi and sfi_importance:
            methods_used.append("sfi")

        return ImportanceResult(
            feature_names=feature_names,
            mdi_importance=mdi_importance,
            mda_importance=mda_importance,
            sfi_importance=sfi_importance,
            mdi_rank=mdi_rank,
            mda_rank=mda_rank,
            sfi_rank=sfi_rank,
            combined_importance=combined_importance,
            combined_rank=combined_rank,
            n_features=n_features,
            n_samples=n_samples,
            methods_used=methods_used,
        )

    def _create_ranking(self, importance: Dict[str, float]) -> Dict[str, int]:
        """Create feature ranking from importance scores."""
        if not importance:
            return {}

        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        return {feature: rank + 1 for rank, (feature, _) in enumerate(sorted_features)}

    def _combine_importances(
        self,
        mdi: Dict[str, float],
        mda: Dict[str, float],
        sfi: Dict[str, float],
    ) -> Dict[str, float]:
        """Combine importance scores from multiple methods."""
        # Collect all importances
        all_importances = {}

        for feature, value in mdi.items():
            if feature not in all_importances:
                all_importances[feature] = []
            all_importances[feature].append(value)

        for feature, value in mda.items():
            if feature not in all_importances:
                all_importances[feature] = []
            all_importances[feature].append(value)

        for feature, value in sfi.items():
            if feature not in all_importances:
                all_importances[feature] = []
            all_importances[feature].append(value)

        # Average across methods
        combined = {}
        for feature, values in all_importances.items():
            combined[feature] = float(np.mean(values))

        # Normalize to sum to 1
        total = sum(combined.values())
        if total > 0:
            combined = {k: v / total for k, v in combined.items()}

        return combined


def calculate_feature_importance(
    model: Any,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    method: str = "combined",
    **kwargs,
) -> Dict[str, float]:
    """
    Convenience function to calculate feature importance.

    Args:
        model: Trained model
        X: Feature matrix
        y: Target vector
        method: Importance method ('mdi', 'mda', 'sfi', 'combined')
        **kwargs: Additional arguments

    Returns:
        Dictionary mapping feature names to importance scores

    Example:
        >>> importance = calculate_feature_importance(model, X, y, method="mda")
        >>> top_features = sorted(importance, key=importance.get, reverse=True)[:5]
    """
    # Update config based on method
    config = FeatureImportanceConfig(**kwargs)

    if method == "mdi":
        config.compute_mda = False
        config.compute_sfi = False
    elif method == "mda":
        config.compute_mdi = False
        config.compute_sfi = False
    elif method == "sfi":
        config.compute_mdi = False
        config.compute_mda = False

    # Calculate importance
    calculator = FinancialMLFeatureImportance(config)
    result = calculator.calculate_importance(model, X, y)

    # Return requested method
    if method == "mdi":
        return result.mdi_importance
    elif method == "mda":
        return result.mda_importance
    elif method == "sfi":
        return result.sfi_importance
    else:
        return result.combined_importance
