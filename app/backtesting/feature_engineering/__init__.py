"""
Feature Engineering Module for AlgoTrading System.

This module provides advanced feature engineering techniques for financial time series,
with a focus on fractional differentiation for creating stationary features while
preserving memory - a critical concept from López de Prado's work.

Main Components:
- FractionalDifferentiation: Core fractional differentiation implementation
- FractionalDiffTransformer: Scikit-learn compatible transformer
- Visualization utilities for analysis and debugging

Example:
    >>> from app.backtesting.feature_engineering import FractionalDifferentiation
    >>> fd = FractionalDifferentiation()
    >>> optimal_d, p_value, _ = fd.find_optimal_d(price_series)
    >>> frac_diff_series = fd.fractional_diff(price_series, d=optimal_d)
"""

from .fractional_differentiation import (
    FractionalDifferentiation,
    FractionalDiffTransformer,
    get_weights,
    fractional_diff,
    find_optimal_d,
    apply_frac_diff_to_dataframe,
)

__all__ = [
    "FractionalDifferentiation",
    "FractionalDiffTransformer",
    "get_weights",
    "fractional_diff",
    "find_optimal_d",
    "apply_frac_diff_to_dataframe",
]

# Version info
__version__ = "1.0.0"
__author__ = "Advanced Financial Machine Learning Implementation"
