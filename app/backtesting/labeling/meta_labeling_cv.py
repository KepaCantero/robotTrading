"""
Meta-Labeling Cross-Validation for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 4.

This module implements purged and embargoed cross-validation specifically designed
for meta-labeling applications in financial machine learning.

Key Concepts:
- Purged CV: Remove training samples that overlap with test period
- Embargo: Additional buffer after test period to prevent leakage
- Meta-labeling CV: Special handling for two-stage models
- Sequential Bootstrap: CV that respects time-series nature of data

Why Special CV is Needed for Meta-Labeling:
1. Labels overlap in time (trades have different durations)
2. Features may contain look-ahead bias if not careful
3. Meta-model depends on primary model predictions
4. Standard CV leads to unrealistic performance estimates

The Purged K-Fold CV:
- Removes training samples that overlap with test set
- Adds embargo period after each test fold
- Ensures test set is truly out-of-sample
- Prevents information leakage from overlapping labels

Example:
    >>> from sklearn.ensemble import RandomForestClassifier
    >>> primary_model = RandomForestClassifier()
    >>> meta_model = RandomForestClassifier()
    >>>
    >>> # Generate meta-labeling CV splits
    >>> cv = PurgedKFold(n_folds=5, embargo_pct=0.01)
    >>>
    >>> for train_idx, test_idx in cv.split(X, events, barriers):
    ...     # Train primary model
    ...     primary_model.fit(X[train_idx], y[train_idx])
    ...     primary_pred = primary_model.predict(X[train_idx])
    ...
    ...     # Generate meta-labels
    ...     meta_labels = (primary_pred == y[train_idx]).astype(int)
    ...
    ...     # Train meta-model
    ...     X_meta = np.column_stack([X[train_idx], primary_pred])
    ...     meta_model.fit(X_meta, meta_labels)
    ...
    ...     # Evaluate on test set
    ...     test_pred = meta_model.predict(X[test_idx])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CVConfig:
    """Configuration for cross-validation."""

    # Basic CV parameters
    n_folds: int = 5
    shuffle: bool = False  # Never shuffle time series!

    # Purging and embargo
    purge_pct: float = 0.05  # Percentage to purge from training
    embargo_pct: float = 0.01  # Percentage to embargo after test

    # Meta-labeling specific
    meta_labeling: bool = True
    primary_model_first: bool = True  # Train primary model before meta-model

    # Time-series specific
    is_timeseries: bool = True
    timeseries_gap: int = 1  # Minimum gap between train and test

    def __post_init__(self):
        """Validate configuration."""
        if self.n_folds <= 1:
            raise ValueError("n_folds must be greater than 1")

        if self.purge_pct < 0 or self.purge_pct >= 1:
            raise ValueError("purge_pct must be between 0 and 1")

        if self.embargo_pct < 0 or self.embargo_pct >= 1:
            raise ValueError("embargo_pct must be between 0 and 1")


@dataclass
class CVResult:
    """Result of cross-validation."""

    fold_scores: List[float]
    """Score for each fold"""

    mean_score: float
    """Mean score across folds"""

    std_score: float
    """Standard deviation of scores"""

    fold_predictions: List[np.ndarray]
    """Predictions for each fold"""

    fold_labels: List[np.ndarray]
    """True labels for each fold"""

    train_indices: List[np.ndarray]
    """Training indices for each fold"""

    test_indices: List[np.ndarray]
    """Test indices for each fold"""

    metadata: Dict[str, Union[str, int, float, bool, None]] = field(default_factory=dict)
    """Additional metadata"""

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Union[str, int, float, bool, list, None]]:
        """Convert to dictionary."""
        return {
            "fold_scores": self.fold_scores,
            "mean_score": float(self.mean_score),
            "std_score": float(self.std_score),
            "n_folds": len(self.fold_scores),
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class PurgedKFold:
    """
    Purged K-Fold cross-validation for financial ML.

    This class implements purged and embargoed CV that prevents
    data leakage from overlapping labels in financial time series.

    Example:
        >>> cv = PurgedKFold(n_folds=5, embargo_pct=0.01)
        >>> for train_idx, test_idx in cv.split(X, events):
        ...     model.fit(X[train_idx], y[train_idx])
        ...     score = model.score(X[test_idx], y[test_idx])
    """

    def __init__(
        self,
        n_folds: int = 5,
        purge_pct: float = 0.05,
        embargo_pct: float = 0.01,
        timeseries_gap: int = 1,
    ):
        """
        Initialize PurgedKFold.

        Args:
            n_folds: Number of folds for CV
            purge_pct: Percentage of data to purge before test set
            embargo_pct: Percentage of data to embargo after test set
            timeseries_gap: Minimum gap between train and test (in samples)
        """
        self.n_folds = n_folds
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        self.timeseries_gap = timeseries_gap

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        events: Optional[pd.Series] = None,
        labels: Optional[pd.DataFrame] = None,
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate purged train/test splits.

        Args:
            X: Feature matrix
            events: Event timestamps (for calculating overlaps)
            labels: DataFrame with label timing information
            y: Target variable

        Yields:
            Tuple of (train_indices, test_indices) for each fold

        Example:
            >>> for train_idx, test_idx in cv.split(X, events, labels):
            ...     X_train, X_test = X[train_idx], X[test_idx]
            ...     y_train, y_test = y[train_idx], y[test_idx]
        """
        n_samples = len(X)

        # Calculate purge and embargo sizes
        purge_size = int(n_samples * self.purge_pct)
        embargo_size = int(n_samples * self.embargo_pct)

        # Generate K-fold splits (sequential for time series)
        fold_size = n_samples // self.n_folds

        for fold in range(self.n_folds):
            # Calculate test fold boundaries
            test_start = fold * fold_size
            test_end = (fold + 1) * fold_size if fold < self.n_folds - 1 else n_samples

            # Purge period before test
            purge_start = max(0, test_start - purge_size)
            purge_end = test_start

            # Embargo period after test
            embargo_start = test_end
            embargo_end = min(n_samples, test_end + embargo_size)

            # Training set: exclude purge and embargo zones
            train_mask = np.ones(n_samples, dtype=bool)

            # Exclude test set
            train_mask[test_start:test_end] = False

            # Exclude purge period
            train_mask[purge_start:purge_end] = False

            # Exclude embargo period
            train_mask[embargo_start:embargo_end] = False

            # Additional purging based on label overlaps
            if events is not None and labels is not None:
                train_mask = self._apply_label_purge(
                    train_mask, test_start, test_end, events, labels
                )

            train_indices = np.where(train_mask)[0]
            test_indices = np.arange(test_start, test_end)

            # Skip if no training samples
            if len(train_indices) == 0:
                logger.warning(f"Fold {fold}: No training samples after purging")
                continue

            yield train_indices, test_indices

    def _apply_label_purge(
        self,
        train_mask: np.ndarray,
        test_start: int,
        test_end: int,
        events: pd.Series,
        labels: pd.DataFrame,
    ) -> np.ndarray:
        """
        Apply additional purging based on label overlaps.

        Removes training samples whose labels overlap with the test period.

        Args:
            train_mask: Current training mask
            test_start: Test set start index
            test_end: Test set end index
            events: Event timestamps
            labels: DataFrame with 'bars_to_barrier' column

        Returns:
            Updated train mask with overlapping samples removed
        """
        if "bars_to_barrier" not in labels.columns:
            return train_mask

        # Convert events to indices (ARCH-004: Extract to helper method)
        event_indices = self._get_event_indices(events)

        # For each training sample, check if its label overlaps with test set
        for i in np.where(train_mask)[0]:
            if i >= len(event_indices):
                continue

            if self._label_overlaps_test(i, event_indices, labels, test_start, test_end):
                train_mask[i] = False

        return train_mask

    def _get_event_indices(self, events: pd.Series) -> np.ndarray:
        """
        Get event indices from events series (ARCH-004: Extract helper method).

        Args:
            events: Event timestamps

        Returns:
            Array of event indices
        """
        # Convert events to indices if they're timestamps
        if isinstance(events.iloc[0], pd.Timestamp):
            # Events are already in the dataframe index
            return np.arange(len(events))
        else:
            return events.values

    def _label_overlaps_test(
        self,
        i: int,
        event_indices: np.ndarray,
        labels: pd.DataFrame,
        test_start: int,
        test_end: int,
    ) -> bool:
        """
        Check if a label overlaps with the test period (ARCH-004: Extract helper method).

        Args:
            i: Sample index
            event_indices: Array of event indices
            labels: DataFrame with 'bars_to_barrier' column
            test_start: Test set start index
            test_end: Test set end index

        Returns:
            True if label overlaps with test set
        """
        event_idx = event_indices[i]
        holding_period = labels["bars_to_barrier"].iloc[i]
        label_end = event_idx + int(holding_period)

        # Check if label overlaps with test set
        return label_end > test_start and event_idx < test_end


class MetaLabelingCV:
    """
    Cross-validation specifically for meta-labeling models.

    This class implements the complete CV pipeline for meta-labeling:
    1. Split data using purged CV
    2. Train primary model on training set
    3. Generate meta-labels
    4. Train meta-model
    5. Evaluate on test set

    Example:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> primary_model = RandomForestClassifier()
        >>> meta_model = RandomForestClassifier()
        >>>
        >>> cv = MetaLabelingCV(n_folds=5)
        >>> results = cv.cross_validate(
        ...     primary_model, meta_model, X, y, events, labels
        ... )
        >>> print(f"Mean accuracy: {results.mean_score:.4f}")
    """

    def __init__(
        self,
        n_folds: int = 5,
        purge_pct: float = 0.05,
        embargo_pct: float = 0.01,
        scoring: str = "accuracy",
    ):
        """
        Initialize MetaLabelingCV.

        Args:
            n_folds: Number of CV folds
            purge_pct: Percentage to purge from training
            embargo_pct: Percentage to embargo after test
            scoring: Scoring metric ('accuracy', 'f1', 'roc_auc')
        """
        self.n_folds = n_folds
        self.purge_pct = purge_pct
        self.embargo_pct = embargo_pct
        self.scoring = scoring

        self.purged_kfold = PurgedKFold(
            n_folds=n_folds,
            purge_pct=purge_pct,
            embargo_pct=embargo_pct,
        )

    def cross_validate(
        self,
        primary_model: object,
        meta_model: object,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        events: Optional[pd.Series] = None,
        labels: Optional[pd.DataFrame] = None,
        sample_weights: Optional[np.ndarray] = None,
    ) -> CVResult:
        """
        Perform cross-validation for meta-labeling.

        Args:
            primary_model: Primary model for direction prediction
            meta_model: Meta-model for bet sizing
            X: Feature matrix
            y: Target labels (-1, 0, 1)
            events: Event timestamps
            labels: DataFrame with label timing info
            sample_weights: Optional sample weights

        Returns:
            CVResult with scores and predictions

        Example:
            >>> from sklearn.ensemble import RandomForestClassifier
            >>> primary = RandomForestClassifier()
            >>> meta = RandomForestClassifier()
            >>> results = cv.cross_validate(primary, meta, X, y, events, labels)
        """
        # Convert to numpy arrays
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        fold_scores = []
        fold_predictions = []
        fold_labels = []
        train_indices_list = []
        test_indices_list = []

        # Perform CV
        for fold_idx, (train_idx, test_idx) in enumerate(
            self.purged_kfold.split(X, events, labels)
        ):
            logger.info(f"Processing fold {fold_idx + 1}/{self.n_folds}")

            # Split data
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            weights = None
            if sample_weights is not None:
                weights = sample_weights[train_idx]

            # Step 1: Train primary model
            primary_model.fit(X_train, y_train, sample_weight=weights)

            # Step 2: Generate primary predictions and meta-labels
            primary_pred_train = primary_model.predict(X_train)
            meta_labels_train = (primary_pred_train == y_train).astype(int)

            # Step 3: Prepare meta features
            X_meta_train = np.column_stack([X_train, primary_pred_train])

            # Step 4: Train meta-model
            meta_model.fit(X_meta_train, meta_labels_train, sample_weight=weights)

            # Step 5: Evaluate on test set
            primary_pred_test = primary_model.predict(X_test)
            X_meta_test = np.column_stack([X_test, primary_pred_test])
            meta_pred_test = meta_model.predict(X_meta_test)

            # Calculate score
            score = self._calculate_score(y_test, primary_pred_test, meta_pred_test)
            fold_scores.append(score)

            # Store predictions
            fold_predictions.append(meta_pred_test)
            fold_labels.append(y_test)
            train_indices_list.append(train_idx)
            test_indices_list.append(test_idx)

            logger.info(f"Fold {fold_idx + 1} score: {score:.4f}")

        # Calculate aggregate statistics
        mean_score = np.mean(fold_scores)
        std_score = np.std(fold_scores)

        return CVResult(
            fold_scores=fold_scores,
            mean_score=mean_score,
            std_score=std_score,
            fold_predictions=fold_predictions,
            fold_labels=fold_labels,
            train_indices=train_indices_list,
            test_indices=test_indices_list,
            metadata={
                "n_folds": self.n_folds,
                "scoring": self.scoring,
                "purge_pct": self.purge_pct,
                "embargo_pct": self.embargo_pct,
            },
        )

    def _calculate_score(
        self,
        y_true: np.ndarray,
        primary_pred: np.ndarray,
        meta_pred: np.ndarray,
    ) -> float:
        """
        Calculate score for a fold.

        Args:
            y_true: True labels
            primary_pred: Primary model predictions
            meta_pred: Meta-model predictions

        Returns:
            Score value
        """
        if self.scoring == "accuracy":
            # Combined accuracy: only count when meta-model says yes
            mask = meta_pred == 1
            if mask.sum() > 0:
                return np.mean(primary_pred[mask] == y_true[mask])
            else:
                return 0.0

        elif self.scoring == "f1":
            from sklearn.metrics import f1_score

            # F1 score of meta-labels
            meta_labels_true = (primary_pred == y_true).astype(int)
            return f1_score(meta_labels_true, meta_pred)

        elif self.scoring == "roc_auc":
            from sklearn.metrics import roc_auc_score

            # ROC AUC for meta-model
            meta_labels_true = (primary_pred == y_true).astype(int)

            # Need probabilities for ROC AUC
            # For now, use binary predictions
            try:
                return roc_auc_score(meta_labels_true, meta_pred)
            except ValueError:
                # If only one class present
                return 0.5

        else:
            return np.mean(primary_pred == y_true)


def cv_score_meta_labeling(
    primary_model: object,
    meta_model: object,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    events: Optional[pd.Series] = None,
    labels: Optional[pd.DataFrame] = None,
    n_folds: int = 5,
    purge_pct: float = 0.05,
    embargo_pct: float = 0.01,
    scoring: str = "accuracy",
) -> Dict[str, float]:
    """
    Calculate cross-validation score for meta-labeling.

    Convenience function for quick CV evaluation.

    Args:
        primary_model: Primary model instance
        meta_model: Meta-model instance
        X: Feature matrix
        y: Target labels
        events: Event timestamps
        labels: DataFrame with label timing
        n_folds: Number of CV folds
        purge_pct: Purge percentage
        embargo_pct: Embargo percentage
        scoring: Scoring metric

    Returns:
        Dictionary with mean and std scores

    Example:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> scores = cv_score_meta_labeling(
        ...     RandomForestClassifier(),
        ...     RandomForestClassifier(),
        ...     X, y, events, labels
        ... )
        >>> print(f"Mean accuracy: {scores['mean']:.4f} ± {scores['std']:.4f}")
    """
    cv = MetaLabelingCV(
        n_folds=n_folds,
        purge_pct=purge_pct,
        embargo_pct=embargo_pct,
        scoring=scoring,
    )

    results = cv.cross_validate(primary_model, meta_model, X, y, events, labels)

    return {
        "mean": results.mean_score,
        "std": results.std_score,
        "scores": results.fold_scores,
    }


class SequentialBootstrap:
    """
        Sequential Bootstrap for time series cross-validation.

        This implements the sequential bootstrap method from López de Prado,
        which builds the training set sequentially while maintaining the
        time-series property of the data.

        Key Features:
    - Sequential sampling respects time ordering
    - Bootstrap samples are built incrementally
    - Maintains temporal dependencies

        Example:
            >>> sb = SequentialBootstrap(n_splits=5, test_size=0.2)
            >>> for train_idx, test_idx in sb.split(X):
            ...     model.fit(X[train_idx], y[train_idx])
            ...     score = model.score(X[test_idx], y[test_idx])
    """

    def __init__(
        self,
        n_splits: int = 5,
        test_size: float = 0.2,
        gap: int = 1,
    ):
        """
        Initialize SequentialBootstrap.

        Args:
            n_splits: Number of splits
            test_size: Size of test set (as fraction)
            gap: Gap between train and test (in samples)
        """
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate sequential train/test splits.

        Args:
            X: Feature matrix
            y: Target (optional, not used)

        Yields:
            Tuple of (train_indices, test_indices)
        """
        n_samples = len(X)
        test_n_samples = int(n_samples * self.test_size)

        # Generate sequential splits
        for i in range(self.n_splits):
            # Calculate test set start
            test_start = int((i / self.n_splits) * (n_samples - test_n_samples))
            test_end = test_start + test_n_samples

            # Ensure we don't go out of bounds
            test_end = min(test_end, n_samples)

            # Training set: all data before test set (with gap)
            train_end = test_start - self.gap
            train_indices = np.arange(max(0, train_end))
            test_indices = np.arange(test_start, test_end)

            if len(train_indices) == 0 or len(test_indices) == 0:
                continue

            yield train_indices, test_indices


def calculate_purge_embargo_sizes(
    n_samples: int,
    n_folds: int = 5,
    purge_pct: float = 0.05,
    embargo_pct: float = 0.01,
) -> Dict[str, int]:
    """
    Calculate purge and embargo sizes for CV.

    Args:
        n_samples: Total number of samples
        n_folds: Number of CV folds
        purge_pct: Purge percentage
        embargo_pct: Embargo percentage

    Returns:
        Dictionary with calculated sizes

    Example:
        >>> sizes = calculate_purge_embargo_sizes(1000, n_folds=5)
        >>> print(f"Purge size: {sizes['purge_size']}")
        >>> print(f"Embargo size: {sizes['embargo_size']}")
    """
    fold_size = n_samples // n_folds
    purge_size = int(n_samples * purge_pct)
    embargo_size = int(n_samples * embargo_pct)

    return {
        "fold_size": fold_size,
        "purge_size": purge_size,
        "embargo_size": embargo_size,
        "train_size_per_fold": fold_size * (n_folds - 1) - purge_size - embargo_size,
    }
