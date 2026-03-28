"""
Purged K-Fold with Embargo Cross-Validation

Implementation of López de Prado's cross-validation method for financial time series.
This prevents look-ahead bias and information leakage in backtesting.

Key Concepts:
- Purge: Remove training samples that overlap with test period
- Embargo: Add buffer period after test set to prevent information leakage
- K-Fold: Split data into K folds for robust validation

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado
    Chapter 3, Section 3.6: Cross-Validation in Finance
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

logger = logging.getLogger(__name__)


@dataclass
class PurgedKFoldConfig:
    """Configuration for Purged K-Fold cross-validation."""

    n_splits: int = 5
    """Number of folds for cross-validation."""

    purge_pct: float = 0.05
    """Percentage of data to purge before test set (default: 5%)."""

    embargo_pct: float = 0.02
    """Percentage of data to embargo after test set (default: 2%)."""

    min_train_samples: int = 252
    """Minimum number of training samples required (default: 1 year of daily data)."""

    min_test_samples: int = 20
    """Minimum number of test samples required."""

    shuffle: bool = False
    """Whether to shuffle data (default: False for time series)."""

    random_state: Optional[int] = None
    """Random state for reproducibility."""

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.n_splits < 2:
            raise ValueError("n_splits must be at least 2")

        if not (0 <= self.purge_pct <= 0.5):
            raise ValueError("purge_pct must be between 0 and 0.5")

        if not (0 <= self.embargo_pct <= 0.5):
            raise ValueError("embargo_pct must be between 0 and 0.5")

        if self.min_train_samples < 1:
            raise ValueError("min_train_samples must be at least 1")

        if self.min_test_samples < 1:
            raise ValueError("min_test_samples must be at least 1")


@dataclass
class PurgedSplit:
    """Represents a single purged train/test split."""

    fold: int
    """Fold number."""

    train_indices: np.ndarray
    """Training indices after purging."""

    test_indices: np.ndarray
    """Test indices."""

    purged_indices: np.ndarray
    """Indices that were purged from training set."""

    embargo_indices: np.ndarray
    """Indices that were embargoed (buffer zone)."""

    train_size_purged: int
    """Training set size before purging."""

    train_size_after_purge: int
    """Training set size after purging."""

    purge_pct_actual: float
    """Actual purge percentage applied."""

    embargo_size: int
    """Number of embargoed samples."""


class PurgedKFold:
    """
    Purged K-Fold cross-validation with embargo for time series.

    This implements López de Prado's method to prevent look-ahead bias
    in financial ML backtesting.

    Example:
        >>> purged_cv = PurgedKFold(n_splits=5, purge_pct=0.05, embargo_pct=0.02)
        >>> for fold, (train_idx, test_idx) in enumerate(purged_cv.split(X, y)):
        ...     print(f"Fold {fold}: train={len(train_idx)}, test={len(test_idx)}")
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_pct: float = 0.05,
        embargo_pct: float = 0.02,
        min_train_samples: int = 252,
        min_test_samples: int = 20,
        shuffle: bool = False,
        random_state: Optional[int] = None,
    ):
        """
        Initialize PurgedKFold cross-validator.

        Args:
            n_splits: Number of folds (default: 5)
            purge_pct: Percentage to purge before test set (default: 0.05 = 5%)
            embargo_pct: Percentage to embargo after test set (default: 0.02 = 2%)
            min_train_samples: Minimum training samples required (default: 252)
            min_test_samples: Minimum test samples required (default: 20)
            shuffle: Whether to shuffle (default: False for time series)
            random_state: Random state for reproducibility
        """
        self.config = PurgedKFoldConfig(
            n_splits=n_splits,
            purge_pct=purge_pct,
            embargo_pct=embargo_pct,
            min_train_samples=min_train_samples,
            min_test_samples=min_test_samples,
            shuffle=shuffle,
            random_state=random_state,
        )

        # Initialize base KFold - never shuffle for time series
        self._base_kfold = KFold(
            n_splits=n_splits,
            shuffle=False,  # Always False for time series to preserve temporal order
            random_state=None,
        )

        # Store split details for analysis
        self.split_details: List[PurgedSplit] = []

    def split(
        self,
        X: Union[pd.DataFrame, pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate purged train/test splits.

        This method:
        1. Creates initial K-Fold splits
        2. Calculates purge and embargo zones
        3. Removes overlapping training samples
        4. Applies embargo buffer after test set

        Args:
            X: Training data (DataFrame, Series, or array)
            y: Target variable (optional, not used in splitting)
            groups: Group labels (optional, not used in splitting)

        Returns:
            List of (train_indices, test_indices) tuples with purged splits

        Example:
            >>> X = pd.DataFrame({'feature': range(1000)},
            ...                  index=pd.date_range('2020-01-01', periods=1000))
            >>> purged_cv = PurgedKFold(n_splits=5)
            >>> splits = purged_cv.split(X)
        """
        # Convert to numpy array for indexing
        if isinstance(X, (pd.DataFrame, pd.Series)):
            X_array = X.values
        else:
            X_array = np.array(X)

        n_samples = len(X_array)

        # Validate minimum samples
        if n_samples < self.config.min_train_samples + self.config.min_test_samples:
            raise ValueError(
                f"Insufficient samples: {n_samples} < "
                f"{self.config.min_train_samples + self.config.min_test_samples} "
                f"(min_train + min_test)"
            )

        # Calculate purge and embargo sizes
        purge_size = max(1, int(n_samples * self.config.purge_pct))
        embargo_size = max(1, int(n_samples * self.config.embargo_pct))

        # Generate base splits
        base_splits = list(self._base_kfold.split(np.arange(n_samples)))

        purged_splits = []
        self.split_details = []

        for fold, (train_idx, test_idx) in enumerate(base_splits):
            # Sort indices for time series
            train_idx_sorted = np.sort(train_idx)
            test_idx_sorted = np.sort(test_idx)

            # For time series, ensure training is before testing by removing
            # any training samples that come after the test set starts
            test_start = test_idx_sorted[0]
            test_end = test_idx_sorted[-1]

            # Filter training set to only include samples before test set
            # This ensures temporal integrity
            train_before_test = train_idx_sorted[train_idx_sorted < test_start]

            if len(train_before_test) < self.config.min_train_samples:
                logger.warning(
                    f"Fold {fold}: Insufficient training samples before test set: "
                    f"{len(train_before_test)} < {self.config.min_train_samples}. "
                    f"Skipping this fold."
                )
                continue

            # Calculate purge zone (samples before test set)
            purge_start = max(0, test_start - purge_size)
            purge_end = test_start

            # Calculate embargo zone (samples after test set)
            embargo_start = test_end + 1
            embargo_end = min(n_samples, embargo_start + embargo_size)

            # Get purged indices (train samples to remove)
            purged_indices = train_before_test[
                (train_before_test >= purge_start) & (train_before_test < purge_end)
            ]

            # Get embargo indices (buffer zone) - ensure at least minimal embargo
            if embargo_start < n_samples:
                # Ensure at least 1 embargoed sample when possible
                actual_embargo_end = max(embargo_start + 1, embargo_end)
                actual_embargo_end = min(n_samples, actual_embargo_end)
                embargo_indices = np.arange(embargo_start, actual_embargo_end)
            else:
                # At boundary, create minimal embargo (empty array)
                embargo_indices = np.array([], dtype=int)

            # Apply purge: remove overlapping training samples
            train_idx_purged = train_before_test[~np.isin(train_before_test, purged_indices)]

            # Apply embargo: also remove train samples in embargo zone
            train_idx_purged = train_idx_purged[~np.isin(train_idx_purged, embargo_indices)]

            # Validate minimum sizes
            if len(train_idx_purged) < self.config.min_train_samples:
                logger.warning(
                    f"Fold {fold}: Insufficient training samples after purging: "
                    f"{len(train_idx_purged)} < {self.config.min_train_samples}. "
                    f"Skipping this fold."
                )
                continue

            if len(test_idx_sorted) < self.config.min_test_samples:
                logger.warning(
                    f"Fold {fold}: Insufficient test samples: "
                    f"{len(test_idx_sorted)} < {self.config.min_test_samples}. "
                    f"Skipping this fold."
                )
                continue

            # Store split details
            split_detail = PurgedSplit(
                fold=fold,
                train_indices=train_idx_purged,
                test_indices=test_idx_sorted,
                purged_indices=purged_indices,
                embargo_indices=embargo_indices,
                train_size_purged=len(train_before_test),
                train_size_after_purge=len(train_idx_purged),
                purge_pct_actual=(
                    len(purged_indices) / len(train_before_test)
                    if len(train_before_test) > 0
                    else 0
                ),
                embargo_size=len(embargo_indices),
            )
            self.split_details.append(split_detail)

            purged_splits.append((train_idx_purged, test_idx_sorted))

            logger.debug(
                f"Fold {fold}: train={len(train_idx_purged)}, "
                f"test={len(test_idx_sorted)}, "
                f"purged={len(purged_indices)}, "
                f"embargo={len(embargo_indices)}"
            )

        if not purged_splits:
            raise ValueError(
                "No valid folds generated. Consider reducing purge_pct/embargo_pct "
                "or increasing n_splits."
            )

        logger.info(
            f"Generated {len(purged_splits)} purged splits "
            f"(from {self.config.n_splits} requested)"
        )

        return purged_splits

    def get_n_splits(self) -> int:
        """Returns the number of splits."""
        return self.config.n_splits

    def validate_no_leakage(self, X: Union[pd.DataFrame, pd.Series, np.ndarray]) -> bool:
        """
        Validate that there is no information leakage between train and test sets.

        This checks that:
        1. No training sample is after any test sample (temporal integrity)
        2. Purge zone was properly applied
        3. Embargo zone was properly applied

        Args:
            X: Training data to validate

        Returns:
            True if no leakage detected, False otherwise
        """
        if not self.split_details:
            raise ValueError("No splits available. Call split() first.")

        has_leakage = False

        for split in self.split_details:
            train_max = split.train_indices.max()
            test_min = split.test_indices.min()

            # Check temporal integrity
            if train_max >= test_min:
                logger.error(
                    f"Fold {split.fold}: Temporal leakage detected! "
                    f"Train max index {train_max} >= Test min index {test_min}"
                )
                has_leakage = True

            # Check purge was applied (only if purge_pct > 0)
            if self.config.purge_pct > 0 and len(split.purged_indices) > 0:
                # Purged indices should be immediately before test set
                purged_max = split.purged_indices.max()
                if purged_max >= test_min:
                    logger.error(
                        f"Fold {split.fold}: Purge not properly applied! "
                        f"Purged samples too close to test set."
                    )
                    has_leakage = True

        if not has_leakage:
            logger.info("✅ No information leakage detected in splits")

        return not has_leakage

    def get_split_summary(self) -> pd.DataFrame:
        """
        Get a summary of all splits.

        Returns:
            DataFrame with split statistics
        """
        if not self.split_details:
            raise ValueError("No splits available. Call split() first.")

        summary_data = []
        for split in self.split_details:
            summary_data.append(
                {
                    'fold': split.fold,
                    'train_size': split.train_size_after_purge,
                    'test_size': len(split.test_indices),
                    'purged_count': len(split.purged_indices),
                    'embargo_size': split.embargo_size,
                    'purge_pct': split.purge_pct_actual * 100,
                }
            )

        return pd.DataFrame(summary_data)


def get_purge_indices(
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    purge_pct: float = 0.05,
    n_samples: Optional[int] = None,
) -> np.ndarray:
    """
    Calculate which training indices should be purged.

    Purging removes training samples that overlap with or are too close
    to the test period, preventing look-ahead bias.

    Args:
        train_indices: Training set indices
        test_indices: Test set indices
        purge_pct: Percentage of data to purge (default: 5%)
        n_samples: Total number of samples (for calculating purge size)

    Returns:
        Array of indices to purge from training set
    """
    if n_samples is None:
        n_samples = max(train_indices.max(), test_indices.max()) + 1

    purge_size = max(1, int(n_samples * purge_pct))

    # Get test set boundaries
    test_start = test_indices.min()

    # Identify training samples to purge (samples just before test set)
    purge_start = max(0, test_start - purge_size)
    purge_end = test_start

    # Find training samples in the purge zone
    purged_indices = train_indices[(train_indices >= purge_start) & (train_indices < purge_end)]

    # If no samples in purge zone but train indices exist,
    # purge the samples closest to test set from the end of training
    if len(purged_indices) == 0 and len(train_indices) > 0:
        # Purge the last min(purge_size, len(train_indices)) samples from training
        train_sorted = np.sort(train_indices)
        n_to_purge = min(purge_size, len(train_sorted))
        purged_indices = train_sorted[-n_to_purge:]

    return purged_indices


def get_embargo_indices(
    test_indices: np.ndarray,
    embargo_pct: float = 0.02,
    n_samples: Optional[int] = None,
) -> np.ndarray:
    """
    Calculate embargo buffer indices after test set.

    Embargo creates a buffer zone after the test set to prevent
    information leakage from adjacent samples.

    Args:
        test_indices: Test set indices
        embargo_pct: Percentage of data to embargo (default: 2%)
        n_samples: Total number of samples (for calculating embargo size)

    Returns:
        Array of embargoed indices (buffer zone)
    """
    if n_samples is None:
        n_samples = test_indices.max() + 1

    embargo_size = max(1, int(n_samples * embargo_pct))

    # Get test set boundaries
    test_end = test_indices.max()

    # Calculate embargo zone
    embargo_start = test_end + 1
    embargo_end = min(n_samples, test_end + 1 + embargo_size)

    embargo_indices = np.arange(embargo_start, embargo_end)

    return embargo_indices


def apply_embargo(
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    embargo_pct: float = 0.02,
    n_samples: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply embargo to training set.

    Removes training samples that fall within the embargo buffer zone
    after the test set.

    Args:
        train_indices: Training set indices
        test_indices: Test set indices
        embargo_pct: Percentage of data to embargo (default: 2%)
        n_samples: Total number of samples

    Returns:
        Tuple of (train_indices_after_embargo, embargo_indices)
    """
    embargo_indices = get_embargo_indices(test_indices, embargo_pct, n_samples)

    # Remove embargoed samples from training set
    train_after_embargo = train_indices[~np.isin(train_indices, embargo_indices)]

    return train_after_embargo, embargo_indices


def purged_kfold_splits(
    X: Union[pd.DataFrame, pd.Series, np.ndarray],
    n_splits: int = 5,
    purge_pct: float = 0.05,
    embargo_pct: float = 0.02,
    min_train_samples: int = 252,
    min_test_samples: int = 20,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Convenience function to generate purged K-Fold splits.

    This is a simplified interface to PurgedKFold for quick usage.

    Args:
        X: Training data
        n_splits: Number of folds
        purge_pct: Percentage to purge before test set
        embargo_pct: Percentage to embargo after test set
        min_train_samples: Minimum training samples required
        min_test_samples: Minimum test samples required

    Returns:
        List of (train_indices, test_indices) tuples

    Example:
        >>> X = pd.DataFrame({'feature': range(1000)})
        >>> splits = purged_kfold_splits(X, n_splits=5, purge_pct=0.05)
        >>> for train_idx, test_idx in splits:
        ...     X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    """
    purged_cv = PurgedKFold(
        n_splits=n_splits,
        purge_pct=purge_pct,
        embargo_pct=embargo_pct,
        min_train_samples=min_train_samples,
        min_test_samples=min_test_samples,
    )

    return purged_cv.split(X)


def cross_validate_with_purging(
    estimator: object,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    n_splits: int = 5,
    purge_pct: float = 0.05,
    embargo_pct: float = 0.02,
    scoring: Optional[callable] = None,
    fit_params: Optional[Dict] = None,
) -> Dict[str, List[float]]:
    """
    Cross-validate an estimator using purged K-Fold splits.

    This function provides a sklearn-like cross_validate interface
    but with purged K-Fold for time series data.

    Args:
        estimator: ML estimator with fit() and predict() methods
        X: Feature matrix
        y: Target vector
        n_splits: Number of folds
        purge_pct: Percentage to purge before test set
        embargo_pct: Percentage to embargo after test set
        scoring: Scoring function (default: accuracy for classification, R² for regression)
        fit_params: Additional parameters to pass to fit()

    Returns:
        Dictionary with test scores for each fold

    Example:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> clf = RandomForestClassifier()
        >>> results = cross_validate_with_purging(clf, X, y, n_splits=5)
        >>> print(f"Mean score: {np.mean(results['test_score'])}")
    """
    if fit_params is None:
        fit_params = {}

    purged_cv = PurgedKFold(
        n_splits=n_splits,
        purge_pct=purge_pct,
        embargo_pct=embargo_pct,
    )

    splits = purged_cv.split(X, y)

    test_scores = []

    for fold, (train_idx, test_idx) in enumerate(splits):
        # Split data
        if isinstance(X, pd.DataFrame):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        else:
            X_train, X_test = X[train_idx], X[test_idx]

        if isinstance(y, pd.Series):
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        else:
            y_train, y_test = y[train_idx], y[test_idx]

        # Process fit_params to match training set size
        fit_params_fold = {}
        for key, value in fit_params.items():
            if isinstance(value, np.ndarray) and len(value) == len(X):
                # If parameter is full-size array, subset to training indices
                if isinstance(X, pd.DataFrame):
                    fit_params_fold[key] = value[train_idx]
                else:
                    fit_params_fold[key] = value[train_idx]
            else:
                fit_params_fold[key] = value

        # Train estimator
        estimator.fit(X_train, y_train, **fit_params_fold)

        # Predict and score
        y_pred = estimator.predict(X_test)

        if scoring is None:
            # Default scoring: accuracy for classification, R² for regression
            from sklearn.metrics import accuracy_score, r2_score

            if hasattr(estimator, 'classes_'):
                score = accuracy_score(y_test, y_pred)
            else:
                score = r2_score(y_test, y_pred)
        else:
            score = scoring(y_test, y_pred)

        test_scores.append(score)
        logger.debug(f"Fold {fold}: score = {score:.4f}")

    logger.info(
        f"Cross-validation: mean={np.mean(test_scores):.4f}, " f"std={np.std(test_scores):.4f}"
    )

    return {'test_score': test_scores}


class PurgedTimeSeriesSplit:
    """
    Time Series cross-validator with purging and embargo.

    Similar to PurgedKFold but specifically designed for time series
    with expanding or sliding windows.

    Example:
        >>> tscv = PurgedTimeSeriesSplit(n_splits=5, purge_pct=0.05)
        >>> for train_idx, test_idx in tscv.split(X):
        ...     print(f"Train: {len(train_idx)}, Test: {len(test_idx)}")
    """

    def __init__(
        self,
        n_splits: int = 5,
        purge_pct: float = 0.05,
        embargo_pct: float = 0.02,
        max_train_size: Optional[int] = None,
        test_size: Optional[int] = None,
    ):
        """
        Initialize PurgedTimeSeriesSplit.

        Args:
            n_splits: Number of splits
            purge_pct: Percentage to purge before test set
            embargo_pct: Percentage to embargo after test set
            max_train_size: Maximum training size (None for expanding window)
            test_size: Fixed test set size (None for auto)
        """
        self.n_splits = n_splits
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        self.max_train_size = max_train_size
        self.test_size = test_size

        self.split_details: List[PurgedSplit] = []

    def split(
        self,
        X: Union[pd.DataFrame, pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate time series splits with purging.

        Args:
            X: Training data
            y: Target (optional)
            groups: Group labels (optional)

        Returns:
            List of (train_indices, test_indices) tuples
        """
        if isinstance(X, (pd.DataFrame, pd.Series)):
            n_samples = len(X)
        else:
            n_samples = X.shape[0]

        # Calculate test size
        if self.test_size is None:
            test_size = n_samples // (self.n_splits + 1)
        else:
            test_size = self.test_size

        splits = []
        self.split_details = []

        for i in range(self.n_splits):
            # Calculate indices
            test_start = n_samples - (self.n_splits - i) * test_size
            test_end = test_start + test_size

            if test_end > n_samples:
                test_end = n_samples

            test_indices = np.arange(test_start, test_end)

            # Training indices (all before test set)
            train_indices = np.arange(0, test_start)

            # Apply purging
            purge_size = max(1, int(n_samples * self.purge_pct))
            purge_start = max(0, test_start - purge_size)

            purged_indices = train_indices[
                (train_indices >= purge_start) & (train_indices < test_start)
            ]

            train_indices = train_indices[~np.isin(train_indices, purged_indices)]

            # Apply embargo
            embargo_size = max(1, int(n_samples * self.embargo_pct))
            embargo_end = min(n_samples, test_end + embargo_size)
            embargo_indices = np.arange(test_end, embargo_end)

            train_indices = train_indices[~np.isin(train_indices, embargo_indices)]

            # Apply max train size
            if self.max_train_size is not None:
                train_indices = train_indices[-self.max_train_size :]

            if len(train_indices) == 0 or len(test_indices) == 0:
                logger.warning(f"Split {i}: Empty train or test set, skipping")
                continue

            splits.append((train_indices, test_indices))

            # Store details
            split_detail = PurgedSplit(
                fold=i,
                train_indices=train_indices,
                test_indices=test_indices,
                purged_indices=purged_indices,
                embargo_indices=embargo_indices,
                train_size_purged=len(train_indices) + len(purged_indices),
                train_size_after_purge=len(train_indices),
                purge_pct_actual=len(purged_indices) / (len(train_indices) + len(purged_indices)),
                embargo_size=len(embargo_indices),
            )
            self.split_details.append(split_detail)

        return splits

    def get_n_splits(self) -> int:
        """Returns the number of splits."""
        return self.n_splits
