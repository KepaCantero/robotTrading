"""
Validation module for financial backtesting.

This module implements advanced cross-validation techniques specifically
designed for financial time series to prevent look-ahead bias and
information leakage.

Key Components:
- PurgedKFold: K-Fold CV with purging and embargo
- PurgedTimeSeriesSplit: Time series split with purging and embargo
- Utility functions for purged cross-validation

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado
"""

from .purged_kfold import (
    PurgedKFold,
    PurgedKFoldConfig,
    PurgedSplit,
    PurgedTimeSeriesSplit,
    apply_embargo,
    cross_validate_with_purging,
    get_embargo_indices,
    get_purge_indices,
    purged_kfold_splits,
)

__all__ = [
    "PurgedKFold",
    "PurgedKFoldConfig",
    "PurgedSplit",
    "PurgedTimeSeriesSplit",
    "apply_embargo",
    "cross_validate_with_purging",
    "get_embargo_indices",
    "get_purge_indices",
    "purged_kfold_splits",
]
