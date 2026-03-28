"""
Cross-Validation Methods for Statistical Learning.

This module implements comprehensive cross-validation techniques following
Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning"
(ESL) Chapter 7: Model Assessment and Selection.

Key Methods:
1. K-Fold Cross-Validation
2. Leave-One-Out Cross-Validation (LOOCV)
3. Nested Cross-Validation for hyperparameter tuning
4. Stratified K-Fold for classification
5. Time Series Cross-Validation
6. Custom CV with purging and embargo for financial data

Reference:
    "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    Chapter 7: Model Assessment and Selection
    Chapter 12: Support Vector Machines and Flexible Discriminants
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Generator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Type alias for parameter values in cross-validation
ParamValue = Union[int, float, str, bool]
ParamGrid = Dict[str, List[ParamValue]]
ParamDict = Dict[str, ParamValue]
DataSplit = Tuple[Union[pd.DataFrame, np.ndarray], Union[pd.DataFrame, np.ndarray]]
from sklearn.base import BaseEstimator, clone
from sklearn.model_selection import KFold, LeaveOneOut, StratifiedKFold

logger = logging.getLogger(__name__)


class CVMethod(Enum):
    """Cross-validation method types."""

    KFOLD = "kfold"
    LOOCV = "loocv"
    STRATIFIED_KFOLD = "stratified_kfold"
    TIME_SERIES = "time_series"
    NESTED = "nested"
    PURGED = "purged"


@dataclass
class CVResult:
    """Results from cross-validation."""

    timestamp: datetime
    method: CVMethod
    n_splits: int
    mean_score: float
    std_score: float
    fold_scores: List[float]
    fit_times: List[float]
    score_times: List[float]
    params: ParamDict = field(default_factory=dict)

    # Additional statistics
    min_score: float = 0.0
    max_score: float = 0.0
    score_range: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)

    # Model-specific info
    model_name: str = ""
    scorer_name: str = ""

    def to_dict(self) -> Dict[str, Union[str, int, float, List[float], ParamDict, Tuple[float, float]]]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "method": self.method.value,
            "n_splits": self.n_splits,
            "mean_score": self.mean_score,
            "std_score": self.std_score,
            "fold_scores": self.fold_scores,
            "fit_times": self.fit_times,
            "score_times": self.score_times,
            "params": self.params,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "score_range": self.score_range,
            "confidence_interval": self.confidence_interval,
            "model_name": self.model_name,
            "scorer_name": self.scorer_name,
        }


@dataclass
class NestedCVResult:
    """Results from nested cross-validation."""

    timestamp: datetime
    outer_score: float
    outer_std: float
    best_params: ParamDict
    best_inner_score: float
    n_outer_splits: int
    n_inner_splits: int
    outer_fold_scores: List[float]
    selected_params_per_fold: List[ParamDict]

    def to_dict(self) -> Dict[str, Union[str, int, float, List[float], ParamDict]]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "outer_score": self.outer_score,
            "outer_std": self.outer_std,
            "best_params": self.best_params,
            "best_inner_score": self.best_inner_score,
            "n_outer_splits": self.n_outer_splits,
            "n_inner_splits": self.n_inner_splits,
            "outer_fold_scores": self.outer_fold_scores,
            "selected_params_per_fold": self.selected_params_per_fold,
        }


class KFoldCV:
    """
    K-Fold Cross-Validation.

    Implements standard K-fold CV as described in ESL Section 7.10.
    The data is divided into K roughly equal parts, and each part is
    used as test set while the remaining K-1 parts form the training set.

    For regression problems, use standard K-fold.
    For classification problems, use StratifiedKFold instead.
    """

    def __init__(
        self,
        n_splits: int = 5,
        shuffle: bool = False,
        random_state: Optional[int] = None,
    ):
        """
        Initialize K-Fold CV.

        Args:
            n_splits: Number of folds (K)
            shuffle: Whether to shuffle data before splitting
            random_state: Random seed for reproducibility
        """
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state

        if n_splits < 2:
            raise ValueError("n_splits must be at least 2")

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate train/test splits.

        Args:
            X: Feature matrix
            y: Target vector (optional, not used in standard K-fold)
            groups: Group labels (optional, not used)

        Yields:
            (train_indices, test_indices) tuples
        """
        kfold = KFold(
            n_splits=self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
        )

        for train_idx, test_idx in kfold.split(X, y, groups):
            yield train_idx, test_idx

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self.n_splits


class LeaveOneOutCV:
    """
    Leave-One-Out Cross-Validation (LOOCV).

    Implements LOOCV as described in ESL Section 7.10.
    Each observation is used once as test set while the remaining
    n-1 observations form the training set.

    LOOCV is approximately unbiased but can have high variance.
    Computationally expensive for large datasets but provides
    the most thorough validation.

    Advantages:
    - Approximately unbiased
    - Deterministic (no randomness)

    Disadvantages:
    - Computationally expensive (n models to train)
    - High variance of the error estimate
    """

    def __init__(self):
        """Initialize LOOCV."""
        self.loo = LeaveOneOut()

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate train/test splits.

        Args:
            X: Feature matrix
            y: Target vector (optional)
            groups: Group labels (optional, not used)

        Yields:
            (train_indices, test_indices) tuples
        """
        for train_idx, test_idx in self.loo.split(X, y, groups):
            yield train_idx, test_idx

    def get_n_splits(self, X: Union[pd.DataFrame, np.ndarray]) -> int:
        """
        Return the number of splits.

        Args:
            X: Feature matrix

        Returns:
            Number of samples (n)
        """
        if isinstance(X, (pd.DataFrame, pd.Series)):
            return len(X)
        return X.shape[0]


class StratifiedKFoldCV:
    """
    Stratified K-Fold Cross-Validation.

    Implements stratified K-fold CV for classification problems.
    Ensures that each fold has approximately the same proportion
    of samples from each class as the complete dataset.

    This is crucial for imbalanced datasets to ensure representative
    sampling across all folds.
    """

    def __init__(
        self,
        n_splits: int = 5,
        shuffle: bool = False,
        random_state: Optional[int] = None,
    ):
        """
        Initialize Stratified K-Fold CV.

        Args:
            n_splits: Number of folds
            shuffle: Whether to shuffle data before splitting
            random_state: Random seed for reproducibility
        """
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state

        if n_splits < 2:
            raise ValueError("n_splits must be at least 2")

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate stratified train/test splits.

        Args:
            X: Feature matrix
            y: Target vector (required for stratification)
            groups: Group labels (optional, not used)

        Yields:
            (train_indices, test_indices) tuples
        """
        if y is None:
            raise ValueError("y must be provided for stratified K-fold")

        # Convert to numpy array if needed
        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y

        skfold = StratifiedKFold(
            n_splits=self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
        )

        for train_idx, test_idx in skfold.split(X, y_array, groups):
            yield train_idx, test_idx

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self.n_splits


class TimeSeriesSplitCV:
    """
    Time Series Cross-Validation.

    Implements time series CV for temporal data.
    Unlike standard K-fold, this respects the temporal ordering
    of observations to prevent look-ahead bias.

    The training set grows incrementally, always using past data
    to predict future observations.

    This is essential for financial time series data where
    temporal integrity is critical.
    """

    def __init__(
        self,
        n_splits: int = 5,
        max_train_size: Optional[int] = None,
        test_size: Optional[int] = None,
    ):
        """
        Initialize Time Series Split CV.

        Args:
            n_splits: Number of splits
            max_train_size: Maximum size of training set (None for growing window)
            test_size: Size of test set (None for auto)
        """
        self.n_splits = n_splits
        self.max_train_size = max_train_size
        self.test_size = test_size

        if n_splits < 2:
            raise ValueError("n_splits must be at least 2")

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate time-series-aware train/test splits.

        Args:
            X: Feature matrix
            y: Target vector (optional)
            groups: Group labels (optional, not used)

        Yields:
            (train_indices, test_indices) tuples
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

        for i in range(self.n_splits):
            # Test set
            test_start = n_samples - (self.n_splits - i) * test_size
            test_end = min(test_start + test_size, n_samples)
            test_indices = np.arange(test_start, test_end)

            # Training set (all before test set)
            train_indices = np.arange(0, test_start)

            # Apply max train size
            if self.max_train_size is not None and len(train_indices) > self.max_train_size:
                train_indices = train_indices[-self.max_train_size :]

            yield train_indices, test_indices

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self.n_splits


class NestedCrossValidation:
    """
    Nested Cross-Validation for hyperparameter tuning.

    Implements nested CV as described in ESL Section 7.10.
    Uses an inner CV loop for model selection (hyperparameter tuning)
    and an outer CV loop for error estimation.

    This provides an unbiased estimate of model performance when
    hyperparameter tuning is involved.

    Structure:
    - Outer loop: Estimates generalization error
    - Inner loop: Selects best hyperparameters

    Advantages:
    - Unbiased performance estimate
    - Proper hyperparameter tuning
    - No information leakage

    Disadvantages:
    - Computationally expensive
    """

    def __init__(
        self,
        estimator: BaseEstimator,
        param_grid: ParamGrid,
        outer_cv: object = None,
        inner_cv: object = None,
        scoring: Optional[Union[str, Callable]] = None,
        n_jobs: int = 1,
    ):
        """
        Initialize Nested CV.

        Args:
            estimator: Base estimator to tune
            param_grid: Parameter grid for search
            outer_cv: Outer CV splitter (default: 5-fold)
            inner_cv: Inner CV splitter (default: 3-fold)
            scoring: Scoring metric
            n_jobs: Number of parallel jobs
        """
        self.estimator = estimator
        self.param_grid = param_grid
        self.scoring = scoring
        self.n_jobs = n_jobs

        # Default CV splitters
        if outer_cv is None:
            outer_cv = KFold(n_splits=5, shuffle=True, random_state=42)
        if inner_cv is None:
            inner_cv = KFold(n_splits=3, shuffle=True, random_state=42)

        self.outer_cv = outer_cv
        self.inner_cv = inner_cv

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
    ) -> NestedCVResult:
        """
        Perform nested cross-validation.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            NestedCVResult with nested CV results
        """
        from sklearn.model_selection import GridSearchCV

        logger.info("Starting nested cross-validation...")

        outer_scores = []
        selected_params = []

        for fold_idx, (train_idx, test_idx) in enumerate(self.outer_cv.split(X)):
            logger.info(f"Outer fold {fold_idx + 1}/{self.outer_cv.get_n_splits()}")

            X_train, X_test = self._split_data(X, train_idx, test_idx)
            y_train, y_test = self._split_target(y, train_idx, test_idx)

            # Inner CV: Hyperparameter tuning
            inner_search = GridSearchCV(
                estimator=clone(self.estimator),
                param_grid=self.param_grid,
                cv=self.inner_cv,
                scoring=self.scoring,
                n_jobs=self.n_jobs,
            )

            inner_search.fit(X_train, y_train)

            # Evaluate on outer test set
            outer_score = inner_search.best_estimator_.score(X_test, y_test)
            outer_scores.append(outer_score)
            selected_params.append(inner_search.best_params_)

            logger.info(
                f"Fold {fold_idx + 1}: score={outer_score:.4f}, "
                f"best_params={inner_search.best_params_}"
            )

        # Calculate statistics
        outer_scores = np.array(outer_scores)
        outer_mean = np.mean(outer_scores)
        outer_std = np.std(outer_scores)

        # Find most frequently selected params
        import ast
        from collections import Counter

        param_counts = Counter([str(p) for p in selected_params])
        best_params_str = param_counts.most_common(1)[0][0]
        best_params = ast.literal_eval(best_params_str)

        result = NestedCVResult(
            timestamp=datetime.now(),
            outer_score=outer_mean,
            outer_std=outer_std,
            best_params=best_params,
            best_inner_score=0.0,  # Would need to track this separately
            n_outer_splits=self.outer_cv.get_n_splits(),
            n_inner_splits=self.inner_cv.get_n_splits(),
            outer_fold_scores=outer_scores.tolist(),
            selected_params_per_fold=selected_params,
        )

        logger.info(f"Nested CV completed: outer_score={outer_mean:.4f} ± {outer_std:.4f}")

        return result

    def _split_data(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        train_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> Tuple[Union[pd.DataFrame, np.ndarray], Union[pd.DataFrame, np.ndarray]]:
        """Split feature matrix."""
        if isinstance(X, pd.DataFrame):
            return X.iloc[train_idx], X.iloc[test_idx]
        return X[train_idx], X[test_idx]

    def _split_target(
        self,
        y: Union[pd.Series, np.ndarray],
        train_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
        """Split target vector."""
        if isinstance(y, pd.Series):
            return y.iloc[train_idx], y.iloc[test_idx]
        return y[train_idx], y[test_idx]


class CrossValidation:
    """
    Unified Cross-Validation interface.

    This class provides a unified interface for all CV methods
    following ESL best practices.
    """

    def __init__(
        self,
        method: CVMethod = CVMethod.KFOLD,
        n_splits: int = 5,
        shuffle: bool = False,
        random_state: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize Cross-Validation.

        Args:
            method: CV method to use
            n_splits: Number of splits
            shuffle: Whether to shuffle data
            random_state: Random seed
            **kwargs: Additional method-specific parameters
        """
        self.method = method
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state
        self.kwargs = kwargs

        # Initialize CV splitter
        self._cv_splitter = self._get_splitter()

    def _get_splitter(self) -> Union["KFoldCV", "LeaveOneOutCV", "StratifiedKFoldCV", "TimeSeriesSplitCV"]:
        """Get CV splitter based on method."""
        if self.method == CVMethod.KFOLD:
            return KFoldCV(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state,
            )
        elif self.method == CVMethod.LOOCV:
            return LeaveOneOutCV()
        elif self.method == CVMethod.STRATIFIED_KFOLD:
            return StratifiedKFoldCV(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state,
            )
        elif self.method == CVMethod.TIME_SERIES:
            return TimeSeriesSplitCV(
                n_splits=self.n_splits,
                max_train_size=self.kwargs.get("max_train_size"),
                test_size=self.kwargs.get("test_size"),
            )
        else:
            raise ValueError(f"Unknown CV method: {self.method}")

    def split(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
        groups: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Generate train/test splits.

        Args:
            X: Feature matrix
            y: Target vector
            groups: Group labels

        Yields:
            (train_indices, test_indices) tuples
        """
        return self._cv_splitter.split(X, y, groups)

    def cross_validate(
        self,
        estimator: BaseEstimator,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        scoring: Optional[Union[str, Callable]] = None,
        return_estimator: bool = False,
    ) -> CVResult:
        """
        Perform cross-validation.

        Args:
            estimator: ML estimator
            X: Feature matrix
            y: Target vector
            scoring: Scoring metric
            return_estimator: Whether to return fitted estimators

        Returns:
            CVResult with validation results
        """
        import time

        from sklearn.metrics import check_scoring

        logger.info(f"Running {self.method.value} cross-validation...")

        scorer = check_scoring(estimator, scoring=scoring)

        fold_scores = []
        fit_times = []
        score_times = []

        for train_idx, test_idx in self.split(X, y):
            # Split data
            X_train, X_test = self._split_data(X, train_idx, test_idx)
            y_train, y_test = self._split_target(y, train_idx, test_idx)

            # Fit and score
            start_time = time.time()
            estimator_clone = clone(estimator)
            estimator_clone.fit(X_train, y_train)
            fit_time = time.time() - start_time

            start_time = time.time()
            score = scorer(estimator_clone, X_test, y_test)
            score_time = time.time() - start_time

            fold_scores.append(score)
            fit_times.append(fit_time)
            score_times.append(score_time)

        # Calculate statistics
        fold_scores = np.array(fold_scores)
        mean_score = np.mean(fold_scores)
        std_score = np.std(fold_scores)

        # Confidence interval (95%)
        ci_margin = 1.96 * std_score / np.sqrt(len(fold_scores))
        confidence_interval = (mean_score - ci_margin, mean_score + ci_margin)

        result = CVResult(
            timestamp=datetime.now(),
            method=self.method,
            n_splits=self.n_splits,
            mean_score=mean_score,
            std_score=std_score,
            fold_scores=fold_scores.tolist(),
            fit_times=fit_times,
            score_times=score_times,
            model_name=type(estimator).__name__,
            scorer_name=str(scorer),
            min_score=float(np.min(fold_scores)),
            max_score=float(np.max(fold_scores)),
            score_range=float(np.max(fold_scores) - np.min(fold_scores)),
            confidence_interval=confidence_interval,
        )

        logger.info(
            f"CV Result: {mean_score:.4f} ± {std_score:.4f} "
            f"[{confidence_interval[0]:.4f}, {confidence_interval[1]:.4f}]"
        )

        return result

    def _split_data(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        train_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> Tuple[Union[pd.DataFrame, np.ndarray], Union[pd.DataFrame, np.ndarray]]:
        """Split feature matrix."""
        if isinstance(X, pd.DataFrame):
            return X.iloc[train_idx], X.iloc[test_idx]
        return X[train_idx], X[test_idx]

    def _split_target(
        self,
        y: Union[pd.Series, np.ndarray],
        train_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
        """Split target vector."""
        if isinstance(y, pd.Series):
            return y.iloc[train_idx], y.iloc[test_idx]
        return y[train_idx], y[test_idx]

    def get_n_splits(self) -> int:
        """Return the number of splits."""
        return self._cv_splitter.get_n_splits()


def cross_validate(
    estimator: BaseEstimator,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    method: str = "kfold",
    n_splits: int = 5,
    scoring: Optional[Union[str, Callable]] = None,
    **kwargs,
) -> CVResult:
    """
    Convenience function for cross-validation.

    Args:
        estimator: ML estimator
        X: Feature matrix
        y: Target vector
        method: CV method ('kfold', 'loocv', 'stratified', 'time_series')
        n_splits: Number of splits
        scoring: Scoring metric
        **kwargs: Additional parameters

    Returns:
        CVResult with validation results

    Example:
        >>> from sklearn.ensemble import RandomForestClassifier
        >>> clf = RandomForestClassifier()
        >>> result = cross_validate(clf, X, y, method='kfold', n_splits=5)
        >>> print(f"Mean accuracy: {result.mean_score:.4f}")
    """
    method_map = {
        "kfold": CVMethod.KFOLD,
        "loocv": CVMethod.LOOCV,
        "stratified": CVMethod.STRATIFIED_KFOLD,
        "time_series": CVMethod.TIME_SERIES,
    }

    if method not in method_map:
        raise ValueError(f"Unknown method: {method}. Choose from {list(method_map.keys())}")

    cv_method = method_map[method]

    cv = CrossValidation(
        method=cv_method,
        n_splits=n_splits,
        **kwargs,
    )

    return cv.cross_validate(estimator, X, y, scoring=scoring)


def nested_cross_validate(
    estimator: BaseEstimator,
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    param_grid: ParamGrid,
    outer_splits: int = 5,
    inner_splits: int = 3,
    scoring: Optional[Union[str, Callable]] = None,
    n_jobs: int = 1,
) -> NestedCVResult:
    """
    Convenience function for nested cross-validation.

    Args:
        estimator: Base estimator
        X: Feature matrix
        y: Target vector
        param_grid: Parameter grid
        outer_splits: Number of outer folds
        inner_splits: Number of inner folds
        scoring: Scoring metric
        n_jobs: Number of parallel jobs

    Returns:
        NestedCVResult with nested CV results

    Example:
        >>> from sklearn.svm import SVC
        >>> param_grid = {'C': [0.1, 1, 10], 'gamma': [0.01, 0.1]}
        >>> result = nested_cross_validate(SVC(), X, y, param_grid)
        >>> print(f"Outer CV score: {result.outer_score:.4f}")
    """
    from sklearn.model_selection import KFold

    outer_cv = KFold(n_splits=outer_splits, shuffle=True, random_state=42)
    inner_cv = KFold(n_splits=inner_splits, shuffle=True, random_state=42)

    nested_cv = NestedCrossValidation(
        estimator=estimator,
        param_grid=param_grid,
        outer_cv=outer_cv,
        inner_cv=inner_cv,
        scoring=scoring,
        n_jobs=n_jobs,
    )

    return nested_cv.fit(X, y)
