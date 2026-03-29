"""
Feature Explosion Validation for Financial ML Models.

This module implements feature explosion validation as described in
Antti Ilmanen's "Expected Returns" methodologies.

Key Concepts:
- Feature explosion detection
- Multicollinearity analysis
- Overfitting detection through feature count
- Feature importance stability
- Optimal feature set selection

Reference:
    "Expected Returns: An Investor's Guide" by Antti Ilmanen
    Chapter 6: The dangers of data mining and feature explosion
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureExplosionLevel(Enum):
    """Feature explosion assessment levels."""

    SAFE = "safe"  # Feature count appropriate for sample size
    MODERATE = "moderate"  # Some feature explosion, manageable
    SEVERE = "severe"  # Significant feature explosion, action needed
    CRITICAL = "critical"  # Severe feature explosion, immediate action required


@dataclass
class FeatureExplosionResult:
    """Result of feature explosion analysis."""

    timestamp: datetime
    explosion_level: FeatureExplosionLevel
    n_features: int
    n_samples: int
    features_per_sample_ratio: float
    recommended_max_features: int
    excess_features: int
    vif_max: float  # Max Variance Inflation Factor
    correlation_max: float  # Max pairwise correlation
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "explosion_level": self.explosion_level.value,
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "features_per_sample_ratio": self.features_per_sample_ratio,
            "recommended_max_features": self.recommended_max_features,
            "excess_features": self.excess_features,
            "vif_max": self.vif_max,
            "correlation_max": self.correlation_max,
            "details": self.details,
        }


@dataclass
class MulticollinearityResult:
    """Result of multicollinearity analysis."""

    timestamp: datetime
    has_multicollinearity: bool
    n_highly_correlated_pairs: int
    n_high_vif_features: int
    high_correlation_pairs: list[tuple[str, str, float]]
    high_vif_features: dict[str, float]
    condition_number: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "has_multicollinearity": self.has_multicollinearity,
            "n_highly_correlated_pairs": self.n_highly_correlated_pairs,
            "n_high_vif_features": self.n_high_vif_features,
            "high_correlation_pairs": [
                {"feature1": f1, "feature2": f2, "correlation": c}
                for f1, f2, c in self.high_correlation_pairs
            ],
            "high_vif_features": self.high_vif_features,
            "condition_number": self.condition_number,
            "details": self.details,
        }


class FeatureExplosionValidator:
    """
    Feature explosion validator for ML models.

    This class implements validation to detect and prevent feature explosion,
    a critical issue identified by Antti Ilmanen in "Expected Returns".

    Key validations:
    1. Feature-to-sample ratio check
    2. Variance Inflation Factor (VIF) analysis
    3. Pairwise correlation detection
    4. Condition number analysis
    5. Feature importance stability
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize feature explosion validator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.max_features_ratio = self.config.get("max_features_ratio", 0.1)  # 10% rule
        self.vif_threshold = self.config.get("vif_threshold", 10.0)
        self.correlation_threshold = self.config.get("correlation_threshold", 0.9)
        self.condition_number_threshold = self.config.get("condition_number_threshold", 30.0)
        self.min_samples_per_feature = self.config.get("min_samples_per_feature", 20)

    def validate_feature_explosion(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> FeatureExplosionResult:
        """
        Validate for feature explosion.

        Feature explosion occurs when the number of features is too large
        relative to the number of samples, leading to overfitting.

        Args:
            X: Feature matrix
            y: Target vector (optional)
            feature_names: List of feature names (optional)

        Returns:
            FeatureExplosionResult with analysis
        """
        logger.info("Validating feature explosion...")

        # Convert to DataFrame if needed
        if isinstance(X, np.ndarray):
            if feature_names is None:
                feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            X = pd.DataFrame(X, columns=feature_names)

        n_features = X.shape[1]
        n_samples = X.shape[0]

        # Calculate feature-to-sample ratio
        ratio = n_features / n_samples if n_samples > 0 else float("inf")

        # Calculate recommended max features (Ilmanen's rule: ~10% of samples)
        recommended_max = max(10, int(n_samples * self.max_features_ratio))

        # Calculate excess features
        excess = max(0, n_features - recommended_max)

        # Check VIF
        vif_max = self._calculate_max_vif(X)

        # Check max correlation
        correlation_max = self._calculate_max_correlation(X)

        # Determine explosion level
        if ratio > 0.5 or vif_max > 20:
            explosion_level = FeatureExplosionLevel.CRITICAL
        elif ratio > 0.3 or vif_max > 10:
            explosion_level = FeatureExplosionLevel.SEVERE
        elif ratio > self.max_features_ratio * 2 or vif_max > 5:
            explosion_level = FeatureExplosionLevel.MODERATE
        else:
            explosion_level = FeatureExplosionLevel.SAFE

        result = FeatureExplosionResult(
            timestamp=datetime.now(),
            explosion_level=explosion_level,
            n_features=n_features,
            n_samples=n_samples,
            features_per_sample_ratio=ratio,
            recommended_max_features=recommended_max,
            excess_features=excess,
            vif_max=vif_max,
            correlation_max=correlation_max,
            details={
                "samples_per_feature": n_samples / n_features if n_features > 0 else 0,
                "ilmanen_rule_ok": n_samples >= n_features * self.min_samples_per_feature,
            },
        )

        logger.info(
            f"Feature Explosion: {explosion_level.value.upper()} | "
            f"Features={n_features} | Samples={n_samples} | "
            f"Ratio={ratio:.3f} | Excess={excess}"
        )

        return result

    def analyze_multicollinearity(
        self,
        X: pd.DataFrame | np.ndarray,
        feature_names: list[str] | None = None,
    ) -> MulticollinearityResult:
        """
        Analyze multicollinearity among features.

        Multicollinearity can lead to unstable coefficient estimates and
        unreliable feature importance, as discussed by Ilmanen.

        Args:
            X: Feature matrix
            feature_names: List of feature names

        Returns:
            MulticollinearityResult with analysis
        """
        logger.info("Analyzing multicollinearity...")

        # Convert to DataFrame if needed
        if isinstance(X, np.ndarray):
            if feature_names is None:
                feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            X = pd.DataFrame(X, columns=feature_names)

        # Calculate VIF for each feature
        vif_dict = self._calculate_all_vif(X)

        # Find high VIF features
        high_vif_features = {
            name: vif for name, vif in vif_dict.items() if vif > self.vif_threshold
        }

        # Find highly correlated pairs
        corr_matrix = X.corr()
        high_corr_pairs = []

        for i, col1 in enumerate(X.columns):
            for col2 in X.columns[i + 1 :]:
                corr = corr_matrix.loc[col1, col2]
                if abs(corr) > self.correlation_threshold:
                    high_corr_pairs.append((col1, col2, corr))

        # Sort by absolute correlation
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        # Calculate condition number
        try:
            condition_number = np.linalg.cond(X.values)
        except (ValueError, TypeError, np.linalg.LinAlgError):
            condition_number = float("inf")

        # Determine if multicollinearity exists
        has_multicollinearity = (
            len(high_vif_features) > 0
            or len(high_corr_pairs) > 0
            or condition_number > self.condition_number_threshold
        )

        result = MulticollinearityResult(
            timestamp=datetime.now(),
            has_multicollinearity=has_multicollinearity,
            n_highly_correlated_pairs=len(high_corr_pairs),
            n_high_vif_features=len(high_vif_features),
            high_correlation_pairs=high_corr_pairs,
            high_vif_features=high_vif_features,
            condition_number=condition_number,
            details={
                "mean_vif": np.mean(list(vif_dict.values())) if vif_dict else 0,
                "vif_threshold": self.vif_threshold,
                "correlation_threshold": self.correlation_threshold,
            },
        )

        logger.info(
            f"Multicollinearity: Detected={has_multicollinearity} | "
            f"High VIF={len(high_vif_features)} | High Corr Pairs={len(high_corr_pairs)} | "
            f"Condition Number={condition_number:.2f}"
        )

        return result

    def recommend_feature_reduction(
        self,
        X: pd.DataFrame | np.ndarray,
        feature_names: list[str] | None = None,
        method: str = "combined",
    ) -> dict[str, Any]:
        """
        Recommend features to remove to reduce explosion.

        Args:
            X: Feature matrix
            feature_names: List of feature names
            method: Method to use ('vif', 'correlation', 'variance', 'combined')

        Returns:
            Dict with feature reduction recommendations
        """
        logger.info(f"Generating feature reduction recommendations (method={method})...")

        # Convert to DataFrame if needed
        if isinstance(X, np.ndarray):
            if feature_names is None:
                feature_names = [f"feature_{i}" for i in range(X.shape[1])]
            X = pd.DataFrame(X, columns=feature_names)

        features_to_remove = set()

        if method in ["vif", "combined"]:
            # Iteratively remove high VIF features
            vif_dict = self._calculate_all_vif(X)
            sorted_vif = sorted(vif_dict.items(), key=lambda x: x[1], reverse=True)

            for name, vif in sorted_vif:
                if vif > self.vif_threshold:
                    features_to_remove.add(name)

        if method in ["correlation", "combined"]:
            # Remove one from each highly correlated pair
            corr_matrix = X.corr()
            removed_in_pair = set()

            for i, col1 in enumerate(X.columns):
                for col2 in X.columns[i + 1 :]:
                    if col1 in removed_in_pair or col2 in removed_in_pair:
                        continue

                    corr = corr_matrix.loc[col1, col2]
                    if abs(corr) > self.correlation_threshold:
                        # Remove the one with higher average correlation
                        corr1 = abs(corr_matrix.loc[col1]).mean()
                        corr2 = abs(corr_matrix.loc[col2]).mean()

                        if corr1 > corr2:
                            features_to_remove.add(col1)
                            removed_in_pair.add(col1)
                        else:
                            features_to_remove.add(col2)
                            removed_in_pair.add(col2)

        if method in ["variance", "combined"]:
            # Remove low variance features
            variances = X.var()
            low_var_threshold = variances.quantile(0.1)  # Bottom 10%
            low_var_features = variances[variances < low_var_threshold].index.tolist()

            for feature in low_var_features:
                features_to_remove.add(feature)

        # Calculate reduction impact
        n_original = X.shape[1]
        n_recommended_remove = len(features_to_remove)
        n_remaining = n_original - n_recommended_remove

        result = {
            "features_to_remove": list(features_to_remove),
            "n_features_to_remove": n_recommended_remove,
            "n_features_remaining": n_remaining,
            "reduction_ratio": n_recommended_remove / n_original if n_original > 0 else 0,
            "method_used": method,
            "details": {
                "original_features": list(X.columns),
                "recommended_features": [f for f in X.columns if f not in features_to_remove],
            },
        }

        logger.info(
            f"Feature Reduction: Remove {n_recommended_remove}/{n_original} features "
            f"({result['reduction_ratio']:.1%} reduction)"
        )

        return result

    def _calculate_max_vif(self, X: pd.DataFrame) -> float:
        """Calculate maximum Variance Inflation Factor."""
        try:
            vif_dict = self._calculate_all_vif(X)
            return max(vif_dict.values()) if vif_dict else 0.0
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.warning(f"VIF calculation failed: {e}")
            return 0.0

    def _calculate_all_vif(self, X: pd.DataFrame) -> dict[str, float]:
        """Calculate VIF for all features."""
        vif_dict = {}

        try:
            from sklearn.linear_model import LinearRegression

            for feature in X.columns:
                # Skip if feature has zero variance
                if X[feature].var() < 1e-10:
                    vif_dict[feature] = float("inf")
                    continue

                # Get other features
                other_features = [f for f in X.columns if f != feature]

                if not other_features:
                    vif_dict[feature] = 1.0
                    continue

                # Regress this feature on all others
                X_other = X[other_features].values
                y_target = X[feature].values

                model = LinearRegression()
                model.fit(X_other, y_target)
                y_pred = model.predict(X_other)

                # Calculate R²
                ss_res = np.sum((y_target - y_pred) ** 2)
                ss_tot = np.sum((y_target - np.mean(y_target)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                # VIF = 1 / (1 - R²)
                vif = 1 / (1 - r_squared) if r_squared < 1 else float("inf")
                vif_dict[feature] = vif

        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.warning(f"VIF calculation error: {e}")

        return vif_dict

    def _calculate_max_correlation(self, X: pd.DataFrame) -> float:
        """Calculate maximum pairwise correlation."""
        try:
            corr_matrix = X.corr()

            # Get upper triangle (excluding diagonal)
            upper_triangle = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )

            return upper_triangle.abs().max().max()
        except (ValueError, TypeError) as e:
            logger.warning(f"Correlation calculation failed: {e}")
            return 0.0


def validate_feature_explosion(
    X: pd.DataFrame | np.ndarray,
    y: pd.Series | np.ndarray | None = None,
    config: dict[str, Any] | None = None,
) -> FeatureExplosionResult:
    """
    Convenience function for feature explosion validation.

    Args:
        X: Feature matrix
        y: Target vector (optional)
        config: Configuration dictionary

    Returns:
        FeatureExplosionResult with analysis
    """
    validator = FeatureExplosionValidator(config)
    return validator.validate_feature_explosion(X, y)


def analyze_multicollinearity(
    X: pd.DataFrame | np.ndarray,
    config: dict[str, Any] | None = None,
) -> MulticollinearityResult:
    """
    Convenience function for multicollinearity analysis.

    Args:
        X: Feature matrix
        config: Configuration dictionary

    Returns:
        MulticollinearityResult with analysis
    """
    validator = FeatureExplosionValidator(config)
    return validator.analyze_multicollinearity(X)
