"""
Feature Engineering Module for AlgoTrading System.

This module provides advanced feature engineering techniques for financial time series,
following Marcos López de Prado's "Advances in Financial Machine Learning".

Main Components:
- FractionalDifferentiation: Stationary features with memory preservation
- FeatureImportance: MDI, MDA, and SFI importance methods
- Visualization utilities for analysis and debugging

Example:
    >>> from app.backtesting.feature_engineering import FractionalDifferentiation
    >>> fd = FractionalDifferentiation()
    >>> optimal_d, p_value, _ = fd.find_optimal_d(price_series)
    >>> frac_diff_series = fd.fractional_diff(price_series, d=optimal_d)
"""

from .feature_importance import (
    FeatureImportanceConfig,
    FeatureImportanceMDA,
    FeatureImportanceMDI,
    FeatureImportanceSFI,
    FinancialMLFeatureImportance,
    ImportanceResult,
    calculate_feature_importance,
)

# NEW: Feature Importance with Uniqueness (95% compliance)
from .feature_importance_uniqueness import (
    FeatureClusterer,
    FinancialMLFeatureImportanceWithUniqueness,
    MDAWithUniqueness,
    MDIWithUniqueness,
    UniquenessCalculator,
    UniquenessConfig,
    UniquenessResult,
    calculate_feature_importance_with_uniqueness,
)
from .fractional_differentiation import (
    FractionalDifferentiation,
    FractionalDiffTransformer,
    apply_frac_diff_to_dataframe,
    find_optimal_d,
    fractional_diff,
    get_weights,
)

__all__ = [
    # Fractional Differentiation
    "FractionalDifferentiation",
    "FractionalDiffTransformer",
    "get_weights",
    "fractional_diff",
    "find_optimal_d",
    "apply_frac_diff_to_dataframe",
    # Feature Importance (López de Prado)
    "FinancialMLFeatureImportance",
    "FeatureImportanceMDI",
    "FeatureImportanceMDA",
    "FeatureImportanceSFI",
    "FeatureImportanceConfig",
    "ImportanceResult",
    "calculate_feature_importance",
    # NEW: Feature Importance with Uniqueness (95% compliance)
    "UniquenessCalculator",
    "MDIWithUniqueness",
    "MDAWithUniqueness",
    "FeatureClusterer",
    "FinancialMLFeatureImportanceWithUniqueness",
    "calculate_feature_importance_with_uniqueness",
    "UniquenessConfig",
    "UniquenessResult",
]

# Version info
__version__ = "1.0.0"
__author__ = "Advanced Financial Machine Learning Implementation"
