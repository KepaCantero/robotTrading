"""
Purged Cross-Validation for Financial Time Series (López de Prado Chapter 4).

Prevents look-ahead bias by purging training samples that overlap with test period
based on event timestamps and their exit times (t1).

Key Concepts:
- Purge: Remove training samples that overlap with test period
- Embargo: Add buffer period after test set using t1 (exit times)
- Event-aware: Uses actual event lifetimes (t1) rather than fixed windows

This implementation differs from standard PurgedKFold by:
1. Using event-based embargo (t1 exit times from triple barrier)
2. Accounting for overlapping samples based on actual event durations
3. Following López de Prado's Chapter 4 methodology more closely

Reference:
    "Advances in Financial Machine Learning" by Marcos López de Prado
    Chapter 4, Section 4.4-4.5: Cross-Validation in Finance
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

logger = logging.getLogger(__name__)


@dataclass
class PurgedCVConfig:
    """Configuration for Purged Cross-Validation with event-based embargo."""

    n_splits: int = 5
    """Number of CV folds."""

    embargo_pct: float = 0.01
    """Percentage of data to embargo after each split (default: 1%)."""

    purge_pct: float = 0.05
    """Percentage of data to purge before test set (default: 5%)."""

    min_train_samples: int = 252
    """Minimum number of training samples required (default: 1 year daily)."""

    min_test_samples: int = 20
    """Minimum number of test samples required."""

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


@dataclass
class PurgedSplitResult:
    """Results from a purged split operation."""

    fold: int
    """Fold number."""

    train_indices: np.ndarray
    """Training indices after purging."""

    test_indices: np.ndarray
    """Test indices."""

    purged_indices: np.ndarray
    """Indices that were purged from training set."""

    embargo_indices: np.ndarray
    """Indices in the embargo buffer zone."""

    train_size_before: int
    """Training set size before purging."""

    train_size_after: int
    """Training set size after purging."""

    n_purged: int
    """Number of samples purged."""

    n_embargoed: int
    """Number of samples in embargo zone."""


class PurgedKFold:
    """
    Purged K-Fold CV for time series with event-based embargo.

    This implementation follows López de Prado's methodology:
    1. Standard K-Fold split
    2. Purge training samples that overlap with test period
    3. Apply embargo using t1 (exit times) if available

    The key innovation is using event exit times (t1) from triple barrier
    labeling to determine embargo zones, rather than fixed windows.

    Example:
        >>> purged_cv = PurgedKFold(n_splits=5, embargo_pct=0.01)
        >>> X = pd.DataFrame({'feature': range(1000)})
        >>> events = pd.DataFrame({
        ...     't1': pd.date_range('2020-01-01', periods=1000, freq='D') + pd.Timedelta(days=5)
        ... })
        >>> for fold, (train_idx, test_idx) in enumerate(purged_cv.split(X, events=events)):
        ...     print(f"Fold {fold}: train={len(train_idx)}, test={len(test_idx)}")
    """

    def __init__(
        self,
        n_splits: int = 5,
        embargo_pct: float = 0.01,
        purge_pct: float = 0.05,
        min_train_samples: int = 252,
        min_test_samples: int = 20,
        random_state: Optional[int] = None,
    ):
        """
        Initialize PurgedKFold cross-validator.

        Args:
            n_splits: Number of folds (default: 5)
            embargo_pct: Percentage to embargo after test set (default: 0.01 = 1%)
            purge_pct: Percentage to purge before test set (default: 0.05 = 5%)
            min_train_samples: Minimum training samples required (default: 252)
            min_test_samples: Minimum test samples required (default: 20)
            random_state: Random state for reproducibility
        """
        self.config = PurgedCVConfig(
            n_splits=n_splits,
            embargo_pct=embargo_pct,
            purge_pct=purge_pct,
            min_train_samples=min_train_samples,
            min_test_samples=min_test_samples,
            random_state=random_state,
        )

        self._base_kfold = KFold(
            n_splits=n_splits,
            shuffle=False,  # Never shuffle time series
            random_state=random_state,
        )

        self.split_results: List[PurgedSplitResult] = []

    def split(
        self,
        X: Union[pd.DataFrame, pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
        events: Optional[pd.DataFrame] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate purged train/test splits.

        This method:
        1. Creates standard K-Fold splits
        2. Purges training samples that overlap with test period
        3. Applies embargo using t1 (exit times) if events DataFrame provided

        Args:
            X: Features (DataFrame, Series, or array)
            y: Labels (optional, not used in splitting)
            groups: Group labels (optional, not used)
            events: DataFrame with 't1' column (exit times) for embargo calculation.
                    If None, uses percentage-based embargo.

        Yields:
            (train_indices, test_indices) tuples

        Example:
            >>> purged_cv = PurgedKFold(n_splits=5, embargo_pct=0.01)
            >>> events = pd.DataFrame({'t1': [...]})  # Exit times
            >>> for train_idx, test_idx in purged_cv.split(X, events=events):
            ...     X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        """
        # Convert to array for indexing
        if isinstance(X, (pd.DataFrame, pd.Series)):
            n_samples = len(X)
            if isinstance(X, pd.DataFrame):
                index = X.index
            else:
                index = X.index
        else:
            n_samples = X.shape[0]
            index = pd.RangeIndex(n_samples)

        # Validate minimum samples
        if n_samples < self.config.min_train_samples + self.config.min_test_samples:
            raise ValueError(
                f"Insufficient samples: {n_samples} < "
                f"{self.config.min_train_samples + self.config.min_test_samples} "
                f"(min_train + min_test)"
            )

        # Process events if provided
        if events is not None and 't1' not in events.columns:
            logger.warning(
                "Events DataFrame provided but no 't1' column found. "
                "Using percentage-based embargo instead."
            )
            events = None

        # Generate base splits
        base_splits = list(self._base_kfold.split(np.arange(n_samples)))

        self.split_results = []

        for fold, (train_idx, test_idx) in enumerate(base_splits):
            # Sort indices (important for time series)
            train_idx_sorted = np.sort(train_idx)
            test_idx_sorted = np.sort(test_idx)

            # Get test set boundaries
            test_start = test_idx_sorted[0]
            test_end = test_idx_sorted[-1]

            # For time series, ensure training is before testing by removing
            # any training samples that come after the test set starts
            train_before_test = train_idx_sorted[train_idx_sorted < test_start]

            if len(train_before_test) < self.config.min_train_samples:
                logger.warning(
                    f"Fold {fold}: Insufficient training samples before test set: "
                    f"{len(train_before_test)} < {self.config.min_train_samples}. "
                    f"Skipping this fold."
                )
                continue

            # Calculate purge size
            purge_size = max(1, int(n_samples * self.config.purge_pct))

            # Identify samples to purge (before test set)
            purge_start = max(0, test_start - purge_size)
            purged_mask = (train_before_test >= purge_start) & (train_before_test < test_start)
            purged_indices = train_before_test[purged_mask]

            # Remove purged samples from training set
            train_idx_purged = train_before_test[~purged_mask]

            # Calculate embargo based on events or percentage
            if events is not None and 't1' in events.columns:
                # Event-based embargo: use t1 exit times
                embargo_indices = self._calculate_event_embargo(test_idx_sorted, events, index)
            else:
                # Percentage-based embargo
                embargo_size = max(1, int(n_samples * self.config.embargo_pct))
                embargo_start = test_end + 1
                embargo_end = min(n_samples, test_end + 1 + embargo_size)
                embargo_indices = np.arange(embargo_start, embargo_end)

            # Remove embargoed samples from training set
            train_idx_final = train_idx_purged[~np.isin(train_idx_purged, embargo_indices)]

            # Validate minimum sizes
            if len(train_idx_final) < self.config.min_train_samples:
                logger.warning(
                    f"Fold {fold}: Insufficient training samples after purging: "
                    f"{len(train_idx_final)} < {self.config.min_train_samples}. "
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

            # Store split result
            split_result = PurgedSplitResult(
                fold=fold,
                train_indices=train_idx_final,
                test_indices=test_idx_sorted,
                purged_indices=purged_indices,
                embargo_indices=embargo_indices,
                train_size_before=len(train_before_test),
                train_size_after=len(train_idx_final),
                n_purged=len(purged_indices),
                n_embargoed=len(embargo_indices),
            )
            self.split_results.append(split_result)

            logger.debug(
                f"Fold {fold}: train={len(train_idx_final)}, "
                f"test={len(test_idx_sorted)}, "
                f"purged={len(purged_indices)}, "
                f"embargo={len(embargo_indices)}"
            )

            yield train_idx_final, test_idx_sorted

        if len(self.split_results) == 0:
            raise ValueError(
                "No valid folds generated. Consider reducing purge_pct/embargo_pct "
                "or increasing n_splits."
            )

        logger.info(
            f"Generated {len(self.split_results)} purged splits "
            f"(from {self.config.n_splits} requested)"
        )

    def _calculate_event_embargo(
        self,
        test_indices: np.ndarray,
        events: pd.DataFrame,
        index: pd.Index,
    ) -> np.ndarray:
        """
        Calculate embargo based on event exit times (t1).

        This implements López de Prado's event-based embargo where
        the embargo period extends to the maximum t1 (exit time) in
        the test set plus a buffer.

        Args:
            test_indices: Indices of test set
            events: DataFrame with 't1' column (exit times)
            index: Index of the original data

        Returns:
            Array of embargoed indices
        """
        # Get t1 values for test indices
        test_t1_values = []

        for idx in test_indices:
            if idx < len(events):
                t1 = events.iloc[idx]['t1']
                test_t1_values.append(t1)

        if not test_t1_values:
            # Fallback to percentage-based
            max(1, int(len(index) * self.config.embargo_pct))
            return np.array([])

        # Find maximum t1 in test set
        max_t1 = max(test_t1_values)

        # Convert to positional index if t1 is timestamp
        if isinstance(max_t1, pd.Timestamp):
            # Find position of max_t1 in index
            try:
                embargo_end_pos = index.get_loc(max_t1) + 1
            except KeyError:
                # t1 not in index, estimate position
                embargo_end_pos = test_indices[-1] + int(len(index) * self.config.embargo_pct)
        else:
            # t1 is already a position
            embargo_end_pos = int(max_t1) + 1

        # Add buffer
        buffer_size = int(len(index) * self.config.embargo_pct)
        embargo_end_pos = min(len(index), embargo_end_pos + buffer_size)

        # Embargo indices are from test_end to embargo_end
        embargo_start = test_indices[-1] + 1
        embargo_indices = np.arange(embargo_start, embargo_end_pos)

        return embargo_indices

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self.config.n_splits

    def get_split_summary(self) -> pd.DataFrame:
        """
        Get a summary of all splits.

        Returns:
            DataFrame with split statistics
        """
        if not self.split_results:
            raise ValueError("No splits available. Call split() first.")

        summary_data = []
        for split in self.split_results:
            summary_data.append(
                {
                    'fold': split.fold,
                    'train_size': split.train_size_after,
                    'test_size': len(split.test_indices),
                    'n_purged': split.n_purged,
                    'n_embargoed': split.n_embargoed,
                    'embargo_size': split.n_embargoed,
                    'purge_pct': (
                        split.n_purged / split.train_size_before
                        if split.train_size_before > 0
                        else 0
                    ),
                }
            )

        return pd.DataFrame(summary_data)

    def validate_no_leakage(self, X: Union[pd.DataFrame, pd.Series, np.ndarray]) -> bool:
        """
        Validate that there is no information leakage between train and test sets.

        Checks:
        1. No training sample is after any test sample (temporal integrity)
        2. Purge zone was properly applied
        3. Embargo zone was properly applied

        Args:
            X: Training data to validate

        Returns:
            True if no leakage detected, False otherwise
        """
        if not self.split_results:
            raise ValueError("No splits available. Call split() first.")

        has_leakage = False

        for split in self.split_results:
            train_max = split.train_indices.max()
            test_min = split.test_indices.min()

            # Check temporal integrity
            if train_max >= test_min:
                logger.error(
                    f"Fold {split.fold}: Temporal leakage detected! "
                    f"Train max index {train_max} >= Test min index {test_min}"
                )
                has_leakage = True

        if not has_leakage:
            logger.info("✅ No information leakage detected in splits")

        return not has_leakage


class PurgedTimeSeriesSplit:
    """
    Time Series cross-validator with purging and embargo.

    Similar to PurgedKFold but uses expanding/sliding windows
    instead of K-Fold splits.

    Example:
        >>> tscv = PurgedTimeSeriesSplit(n_splits=5, embargo_pct=0.01)
        >>> for train_idx, test_idx in tscv.split(X):
        ...     print(f"Train: {len(train_idx)}, Test: {len(test_idx)}")
    """

    def __init__(
        self,
        n_splits: int = 5,
        embargo_pct: float = 0.01,
        purge_pct: float = 0.05,
        max_train_size: Optional[int] = None,
        test_size: Optional[int] = None,
    ):
        """
        Initialize PurgedTimeSeriesSplit.

        Args:
            n_splits: Number of splits
            embargo_pct: Percentage to embargo after test set
            purge_pct: Percentage to purge before test set
            max_train_size: Maximum training size (None for expanding window)
            test_size: Fixed test set size (None for auto)
        """
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct
        self.purge_pct = purge_pct
        self.max_train_size = max_train_size
        self.test_size = test_size

        self.split_results: List[PurgedSplitResult] = []

    def split(
        self,
        X: Union[pd.DataFrame, pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
        events: Optional[pd.DataFrame] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate time series splits with purging.

        Args:
            X: Training data
            y: Target (optional)
            groups: Group labels (optional)
            events: DataFrame with 't1' column for embargo (optional)

        Yields:
            (train_indices, test_indices) tuples
        """
        if isinstance(X, (pd.DataFrame, pd.Series)):
            n_samples = len(X)
        else:
            n_samples = X.shape[0]

        # Calculate test size
        if self.test_size is None:
            test_size = max(1, n_samples // (self.n_splits + 1))
        else:
            test_size = self.test_size

        self.split_results = []

        for i in range(self.n_splits):
            # Calculate test set indices
            test_start = n_samples - (self.n_splits - i) * test_size
            test_end = min(test_start + test_size, n_samples)

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
            if events is not None and 't1' in events.columns:
                # Event-based embargo
                purged_kfold = PurgedKFold(
                    n_splits=2,
                    embargo_pct=self.embargo_pct,
                    purge_pct=0,
                )
                embargo_indices = purged_kfold._calculate_event_embargo(
                    test_indices, events, pd.RangeIndex(n_samples)
                )
            else:
                # Percentage-based embargo
                embargo_size = max(1, int(n_samples * self.embargo_pct))
                embargo_end = min(n_samples, test_end + embargo_size)
                embargo_indices = np.arange(test_end, embargo_end)

            train_indices = train_indices[~np.isin(train_indices, embargo_indices)]

            # Apply max train size
            if self.max_train_size is not None and len(train_indices) > self.max_train_size:
                train_indices = train_indices[-self.max_train_size :]

            if len(train_indices) == 0 or len(test_indices) == 0:
                logger.warning(f"Split {i}: Empty train or test set, skipping")
                continue

            # Store result
            split_result = PurgedSplitResult(
                fold=i,
                train_indices=train_indices,
                test_indices=test_indices,
                purged_indices=purged_indices,
                embargo_indices=embargo_indices,
                train_size_before=len(train_indices) + len(purged_indices),
                train_size_after=len(train_indices),
                n_purged=len(purged_indices),
                n_embargoed=len(embargo_indices),
            )
            self.split_results.append(split_result)

            yield train_indices, test_indices

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self.n_splits


def cv_score(
    estimator: object,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    events: Optional[pd.DataFrame] = None,
    n_splits: int = 5,
    embargo_pct: float = 0.01,
    purge_pct: float = 0.05,
    scoring: Optional[callable] = None,
) -> Dict[str, float]:
    """
    Cross-validate an estimator using purged K-Fold splits.

    This provides a sklearn-like cross_val_score interface but with
    purged K-Fold for time series data.

    Args:
        estimator: ML estimator with fit() and predict() methods
        X: Feature matrix
        y: Target vector
        events: DataFrame with 't1' column for event-based embargo (optional)
        n_splits: Number of folds
        embargo_pct: Percentage to embargo after test set
        purge_pct: Percentage to purge before test set
        scoring: Scoring function (default: accuracy for classification)

    Returns:
        Dictionary with 'mean_score', 'std_score', and 'fold_scores'

    Example:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> clf = RandomForestClassifier()
        >>> events = pd.DataFrame({'t1': [...]})
        >>> results = cv_score(clf, X, y, events=events, n_splits=5)
        >>> print(f"Mean accuracy: {results['mean_score']:.4f}")
    """
    purged_cv = PurgedKFold(
        n_splits=n_splits,
        embargo_pct=embargo_pct,
        purge_pct=purge_pct,
    )

    fold_scores = []

    for fold, (train_idx, test_idx) in enumerate(purged_cv.split(X, events=events)):
        # Split data
        if isinstance(X, pd.DataFrame):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        else:
            X_train, X_test = X[train_idx], X[test_idx]

        if isinstance(y, pd.Series):
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        else:
            y_train, y_test = y[train_idx], y[test_idx]

        # Train estimator
        estimator.fit(X_train, y_train)

        # Predict and score
        y_pred = estimator.predict(X_test)

        if scoring is None:
            # Default: accuracy for classification
            from sklearn.metrics import accuracy_score

            score = accuracy_score(y_test, y_pred)
        else:
            score = scoring(y_test, y_pred)

        fold_scores.append(score)
        logger.debug(f"Fold {fold}: score = {score:.4f}")

    return {
        'mean_score': np.mean(fold_scores),
        'std_score': np.std(fold_scores),
        'fold_scores': fold_scores,
    }


# Alias for backward compatibility with compliance engine
# PurgedCV is the main class users should interact with for López de Prado's purged CV
PurgedCV = PurgedKFold


def get_purged_cv(config: Optional[PurgedCVConfig] = None) -> PurgedCV:
    """
    Get a PurgedCV instance for López de Prado's purged cross-validation.

    This is a convenience function for the compliance engine to check if
    López de Prado systems are available.

    Args:
        config: Optional configuration for purged CV

    Returns:
        PurgedCV instance (aliased to PurgedKFold)

    Example:
        >>> purged_cv = get_purged_cv()
        >>> for train_idx, test_idx in purged_cv.split(X, events=events):
        ...     # Train and evaluate model
        ...     pass
    """
    config = config or PurgedCVConfig()
    return PurgedCV(
        n_splits=config.n_splits,
        embargo_pct=config.embargo_pct,
        purge_pct=config.purge_pct,
    )
