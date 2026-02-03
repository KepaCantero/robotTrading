"""
Ensemble Methods for Statistical Learning.

This module implements comprehensive ensemble techniques following
Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning"
(ESL) Chapters 8, 10, 15, and 16.

Key Methods:
1. Bagging (Bootstrap Aggregating)
2. Boosting (AdaBoost, Gradient Boosting)
3. Stacking (Stacked Generalization)
4. Random Forests
5. Ensemble Pruning

Reference:
    "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    Chapter 8: Model Inference and Averaging
    Chapter 10: Boosting and Additive Trees
    Chapter 15: Random Forests
    Chapter 16: Ensemble Learning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.ensemble import (
    BaggingClassifier,
    BaggingRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
    StackingClassifier,
    StackingRegressor,
)
from sklearn.tree import DecisionTreeRegressor
from sklearn.utils.validation import check_is_fitted, check_X_y

logger = logging.getLogger(__name__)


class EnsembleMethod(Enum):
    """Ensemble method types."""

    BAGGING = "bagging"
    BOOSTING = "boosting"
    STACKING = "stacking"
    VOTING = "voting"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"


@dataclass
class EnsembleResult:
    """Result from ensemble method."""

    timestamp: datetime
    method: EnsembleMethod
    n_estimators: int
    train_score: float
    test_score: float

    # Individual estimator scores
    estimator_scores: List[float]

    # Ensemble performance
    ensemble_improvement: float  # Improvement over best single estimator
    diversity: float  # Diversity among estimators

    # Model info
    model_name: str

    # Additional info
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "method": self.method.value,
            "n_estimators": self.n_estimators,
            "train_score": self.train_score,
            "test_score": self.test_score,
            "estimator_scores": self.estimator_scores,
            "ensemble_improvement": self.ensemble_improvement,
            "diversity": self.diversity,
            "model_name": self.model_name,
            "details": self.details,
        }


@dataclass
class BaggingConfig:
    """Configuration for bagging."""

    n_estimators: int = 100
    max_samples: float = 1.0
    max_features: float = 1.0
    bootstrap: bool = True
    bootstrap_features: bool = False
    n_jobs: int = -1
    random_state: int = 42


@dataclass
class BoostingConfig:
    """Configuration for boosting."""

    n_estimators: int = 100
    learning_rate: float = 0.1
    max_depth: int = 3
    subsample: float = 1.0
    loss: str = "log_loss"  # for classification
    random_state: int = 42


@dataclass
class StackingConfig:
    """Configuration for stacking."""

    base_estimators: List[Tuple[str, BaseEstimator]]
    meta_estimator: BaseEstimator
    cv: int = 5
    n_jobs: int = -1


class BaggingEnsemble:
    """
    Bagging (Bootstrap Aggregating).

    Implements bagging as described in ESL Section 8.7.
    Bagging reduces variance by averaging predictions from multiple
    bootstrap samples.

    Key idea: Bootstrap aggregation reduces variance without increasing bias.
    Especially effective for high-variance, low-bias models (e.g., trees).

    Algorithm:
    1. Take B bootstrap samples from training data
    2. Fit model on each bootstrap sample
    3. Average predictions (regression) or majority vote (classification)

    Variance reduction: Var(f̄) ≈ ρσ² + (1-ρ)σ²/B

    Where:
    - ρ = correlation between predictions
    - σ² = variance of single predictor
    - B = number of bootstrap samples

    Reference: ESL Section 8.7
    """

    def __init__(
        self,
        estimator: Optional[BaseEstimator] = None,
        config: Optional[BaggingConfig] = None,
    ):
        """
        Initialize Bagging Ensemble.

        Args:
            estimator: Base estimator (default: Decision Tree)
            config: Bagging configuration
        """
        if config is None:
            config = BaggingConfig()

        self.config = config
        self.estimator = estimator or DecisionTreeRegressor()

        self.bagger_: Optional[Union[BaggingRegressor, BaggingClassifier]] = None

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> "BaggingEnsemble":
        """
        Fit bagging ensemble.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Self (fitted ensemble)
        """
        X_array, y_array = check_X_y(X, y)

        bagging_cls = self._get_bagging_class(y_array)
        self.bagger_ = self._create_bagger(bagging_cls)
        self.bagger_.fit(X_array, y_array)

        return self

    def _get_bagging_class(
        self, y: np.ndarray
    ) -> type[Union[BaggingClassifier, BaggingRegressor]]:
        """Determine bagging class based on target type."""
        if len(np.unique(y)) <= 15:
            return BaggingClassifier
        return BaggingRegressor

    def _create_bagger(
        self, bagging_cls: type[Union[BaggingClassifier, BaggingRegressor]]
    ) -> Union[BaggingClassifier, BaggingRegressor]:
        """Create bagging estimator with configuration."""
        return bagging_cls(
            estimator=self.estimator,
            n_estimators=self.config.n_estimators,
            max_samples=self.config.max_samples,
            max_features=self.config.max_features,
            bootstrap=self.config.bootstrap,
            bootstrap_features=self.config.bootstrap_features,
            n_jobs=self.config.n_jobs,
            random_state=self.config.random_state,
        )

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Predict using ensemble.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["bagger_"])
        return self.bagger_.predict(X)

    def score(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> float:
        """
        Return score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Score (R² for regression, accuracy for classification)
        """
        check_is_fitted(self, ["bagger_"])
        return self.bagger_.score(X, y)

    def get_estimator_scores(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> List[float]:
        """
        Get individual estimator scores.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            List of individual scores
        """
        check_is_fitted(self, ["bagger_"])
        return [estimator.score(X, y) for estimator in self.bagger_.estimators_]

    def get_oob_score(self) -> Optional[float]:
        """
        Get out-of-bag score.

        Returns:
            OOB score if available, None otherwise
        """
        check_is_fitted(self, ["bagger_"])
        return getattr(self.bagger_, 'oob_score_', None)


class BoostingEnsemble:
    """
    Boosting Ensemble.

    Implements boosting as described in ESL Chapter 10.
    Boosting builds models sequentially, each correcting the errors
    of previous models.

    Key idea: Combine weak learners (slightly better than random)
    to create a strong learner.

    Algorithm (AdaBoost):
    1. Initialize observation weights wᵢ = 1/n
    2. For m = 1 to M:
       a. Fit classifier fₘ(x) with weights wᵢ
       b. Compute weighted error errₘ
       c. Compute coefficient αₘ
       d. Update weights wᵢ
    3. Output: F(x) = sign(Σ αₘ fₘ(x))

    Algorithm (Gradient Boosting):
    1. Initialize F₀(x)
    2. For m = 1 to M:
       a. Compute pseudo-residuals
       b. Fit weak learner to residuals
       c. Compute multiplier ρₘ
       d. Update Fₘ(x) = Fₘ₋₁(x) + ρₘ fₘ(x)

    Reference: ESL Chapter 10
    """

    def __init__(
        self,
        config: Optional[BoostingConfig] = None,
        task_type: str = "auto",
    ):
        """
        Initialize Boosting Ensemble.

        Args:
            config: Boosting configuration
            task_type: 'classification', 'regression', or 'auto'
        """
        if config is None:
            config = BoostingConfig()

        self.config = config
        self.task_type = task_type

        self.booster_: Optional[Union[GradientBoostingClassifier, GradientBoostingRegressor]] = None

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> "BoostingEnsemble":
        """
        Fit boosting ensemble.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Self (fitted ensemble)
        """
        X_array, y_array = check_X_y(X, y)

        task = self._determine_task_type(y_array)
        self.booster_ = self._create_booster(task)
        self.booster_.fit(X_array, y_array)

        return self

    def _determine_task_type(self, y: np.ndarray) -> str:
        """Determine task type (classification or regression)."""
        if self.task_type == "auto":
            return "classification" if len(np.unique(y)) <= 15 else "regression"
        return self.task_type

    def _create_booster(
        self, task: str
    ) -> Union[GradientBoostingClassifier, GradientBoostingRegressor]:
        """Create gradient booster based on task type."""
        common_params = {
            "n_estimators": self.config.n_estimators,
            "learning_rate": self.config.learning_rate,
            "max_depth": self.config.max_depth,
            "subsample": self.config.subsample,
            "random_state": self.config.random_state,
        }

        if task == "classification":
            return GradientBoostingClassifier(**common_params)
        return GradientBoostingRegressor(**common_params)

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Predict using ensemble.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["booster_"])
        return self.booster_.predict(X)

    def staged_predict(self, X: Union[np.ndarray, pd.DataFrame]):
        """
        Get staged predictions.

        Args:
            X: Feature matrix

        Yields:
            Predictions at each stage
        """
        check_is_fitted(self, ["booster_"])
        return self.booster_.staged_predict(X)

    def score(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> float:
        """
        Return score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Score
        """
        check_is_fitted(self, ["booster_"])
        return self.booster_.score(X, y)

    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance.

        Returns:
            Feature importance array
        """
        check_is_fitted(self, ["booster_"])
        return self.booster_.feature_importances_


class StackingEnsemble:
    """
    Stacking (Stacked Generalization).

    Implements stacking as described in ESL Section 8.8.
    Stacking combines predictions from multiple base models using
    a meta-model that learns how to best combine them.

    Architecture:
    Level 0 (Base models): Diverse set of models
    Level 1 (Meta model): Learns to combine base predictions

    Key insight: Different models capture different aspects of data.
    The meta-model learns optimal weighting scheme.

    Algorithm:
    1. Train K base models on training data
    2. Use CV to generate meta-features (out-of-fold predictions)
    3. Train meta-model on meta-features
    4. For prediction: base models predict → meta-model combines

    Reference: ESL Section 8.8
    """

    def __init__(
        self,
        base_estimators: List[Tuple[str, BaseEstimator]],
        meta_estimator: Optional[BaseEstimator] = None,
        cv: int = 5,
    ):
        """
        Initialize Stacking Ensemble.

        Args:
            base_estimators: List of (name, estimator) tuples
            meta_estimator: Meta-learner (default: Ridge regression / Logistic regression)
            cv: Number of CV folds for meta-features
        """
        self.base_estimators = base_estimators
        self.meta_estimator = meta_estimator
        self.cv = cv

        self.stacker_: Optional[Union[StackingClassifier, StackingRegressor]] = None

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> "StackingEnsemble":
        """
        Fit stacking ensemble.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Self (fitted ensemble)
        """
        X_array, y_array = check_X_y(X, y)

        self._ensure_meta_estimator(y_array)
        stacking_cls = self._get_stacking_class(y_array)
        self.stacker_ = self._create_stacker(stacking_cls)
        self.stacker_.fit(X_array, y_array)

        return self

    def _ensure_meta_estimator(self, y: np.ndarray) -> None:
        """Ensure meta estimator is set based on task type."""
        if self.meta_estimator is not None:
            return

        if len(np.unique(y)) <= 15:
            from sklearn.linear_model import LogisticRegression
            self.meta_estimator = LogisticRegression()
        else:
            from sklearn.linear_model import Ridge
            self.meta_estimator = Ridge()

    def _get_stacking_class(
        self, y: np.ndarray
    ) -> type[Union[StackingClassifier, StackingRegressor]]:
        """Get stacking class based on target type."""
        return StackingClassifier if len(np.unique(y)) <= 15 else StackingRegressor

    def _create_stacker(
        self, stacking_cls: type[Union[StackingClassifier, StackingRegressor]]
    ) -> Union[StackingClassifier, StackingRegressor]:
        """Create stacking estimator."""
        return stacking_cls(
            estimators=self.base_estimators,
            final_estimator=self.meta_estimator,
            cv=self.cv,
        )

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Predict using ensemble.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["stacker_"])
        return self.stacker_.predict(X)

    def score(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> float:
        """
        Return score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Score
        """
        check_is_fitted(self, ["stacker_"])
        return self.stacker_.score(X, y)

    def get_base_model_scores(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> Dict[str, float]:
        """
        Get individual base model scores.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Dictionary mapping model names to scores
        """
        check_is_fitted(self, ["stacker_"])
        return {name: estimator.score(X, y) for name, estimator in self.stacker_.estimators_}


class RandomForestEnsemble:
    """
    Random Forest Ensemble.

    Implements Random Forest as described in ESL Chapter 15.
    Random Forest is a special case of bagging with:
    1. Decision trees as base learners
    2. Random feature selection at each split

    Key improvements over bagging:
    - Decorrelation of trees through random feature selection
    - Better variance reduction

    Algorithm:
    1. For b = 1 to B:
       a. Draw bootstrap sample
       b. Grow tree to unpruned tree
       c. At each split, randomly select m features
       d. Choose best split from m features

    Parameter m:
    - Classification: m = √p
    - Regression: m = p/3

    Out-of-bag error: Internal CV estimate using samples not in bootstrap.

    Reference: ESL Chapter 15
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = None,
        min_samples_split: int = 2,
        max_features: str = "sqrt",
        bootstrap: bool = True,
        oob_score: bool = True,
        random_state: int = 42,
    ):
        """
        Initialize Random Forest.

        Args:
            n_estimators: Number of trees
            max_depth: Maximum tree depth
            min_samples_split: Min samples to split
            max_features: Max features to consider ('sqrt', 'log2', None)
            bootstrap: Whether to use bootstrap
            oob_score: Whether to compute OOB score
            random_state: Random seed
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.bootstrap = bootstrap
        self.oob_score = oob_score
        self.random_state = random_state
        self.rf_: Optional[Union[RandomForestClassifier, RandomForestRegressor]] = None

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> "RandomForestEnsemble":
        """
        Fit Random Forest.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Self (fitted ensemble)
        """
        X_array, y_array = check_X_y(X, y)

        rf_cls = self._get_rf_class(y_array)
        self.rf_ = self._create_random_forest(rf_cls)
        self.rf_.fit(X_array, y_array)

        return self

    def _get_rf_class(
        self, y: np.ndarray
    ) -> type[Union[RandomForestClassifier, RandomForestRegressor]]:
        """Determine Random Forest class based on target type."""
        return RandomForestClassifier if len(np.unique(y)) <= 15 else RandomForestRegressor

    def _create_random_forest(
        self, rf_cls: type[Union[RandomForestClassifier, RandomForestRegressor]]
    ) -> Union[RandomForestClassifier, RandomForestRegressor]:
        """Create Random Forest estimator."""
        return rf_cls(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            max_features=self.max_features,
            bootstrap=self.bootstrap,
            oob_score=self.oob_score,
            random_state=self.random_state,
        )

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Predict using ensemble.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["rf_"])
        return self.rf_.predict(X)

    def score(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
    ) -> float:
        """
        Return score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Score
        """
        check_is_fitted(self, ["rf_"])
        return self.rf_.score(X, y)

    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance (MDI).

        Returns:
            Feature importance array
        """
        check_is_fitted(self, ["rf_"])
        return self.rf_.feature_importances_

    def get_oob_score(self) -> Optional[float]:
        """
        Get out-of-bag score.

        Returns:
            OOB score if computed, None otherwise
        """
        check_is_fitted(self, ["rf_"])
        return getattr(self.rf_, 'oob_score_', None)


class EnsembleAnalyzer:
    """
    Comprehensive ensemble analysis.

    This class provides tools for analyzing and comparing different
    ensemble methods following ESL best practices.
    """

    def __init__(self, test_size: float = 0.2, random_state: int = 42):
        """
        Initialize analyzer.

        Args:
            test_size: Test set size
            random_state: Random seed
        """
        self.test_size = test_size
        self.random_state = random_state

    def analyze_bagging(
        self,
        estimator: BaseEstimator,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        n_estimators: int = 100,
    ) -> EnsembleResult:
        """
        Analyze bagging ensemble.

        Args:
            estimator: Base estimator
            X: Feature matrix
            y: Target vector
            n_estimators: Number of estimators

        Returns:
            EnsembleResult with analysis
        """
        X_train, X_test, y_train, y_test = self._split_data(X, y)

        bagging = self._train_bagging(estimator, X_train, y_train, n_estimators)
        scores = self._compute_bagging_scores(bagging, X_train, X_test, y_train, y_test)

        result = self._create_bagging_result(bagging, estimator, n_estimators, scores, X_test)
        self._log_bagging_result(n_estimators, scores["test"], result.ensemble_improvement)

        return result

    def _split_data(
        self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]
    ) -> Tuple:
        """Split data into train and test sets."""
        from sklearn.model_selection import train_test_split
        return train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

    def _compute_bagging_scores(
        self, bagging: BaggingEnsemble, X_train: Union[np.ndarray, pd.DataFrame],
        X_test: Union[np.ndarray, pd.DataFrame], y_train: Union[np.ndarray, pd.Series],
        y_test: Union[np.ndarray, pd.Series]
    ) -> Dict[str, Any]:
        """Compute bagging scores."""
        return {
            "train": bagging.score(X_train, y_train),
            "test": bagging.score(X_test, y_test),
            "estimator_scores": bagging.get_estimator_scores(X_test, y_test),
        }

    def _create_bagging_result(
        self, bagging: BaggingEnsemble, estimator: BaseEstimator, n_estimators: int,
        scores: Dict[str, Any], X_test: Union[np.ndarray, pd.DataFrame]
    ) -> EnsembleResult:
        """Create ensemble result for bagging."""
        result = self._create_ensemble_result(
            method=EnsembleMethod.BAGGING,
            n_estimators=n_estimators,
            train_score=scores["train"],
            test_score=scores["test"],
            estimator_scores=scores["estimator_scores"],
            model_name=type(estimator).__name__,
            details={"oob_score": bagging.get_oob_score()},
        )
        result.diversity = self._compute_diversity(bagging, X_test)
        return result

    def _train_bagging(
        self, estimator: BaseEstimator, X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series], n_estimators: int
    ) -> BaggingEnsemble:
        """Train bagging ensemble with given estimator."""
        config = BaggingConfig(n_estimators=n_estimators)
        bagging = BaggingEnsemble(estimator=estimator, config=config)
        bagging.fit(X, y)
        return bagging

    def _log_bagging_result(self, n_estimators: int, test_score: float, improvement: float) -> None:
        """Log bagging analysis results."""
        logger.info(
            f"Bagging: n={n_estimators}, test_score={test_score:.4f}, "
            f"improvement={improvement:.4f}"
        )

    def analyze_boosting(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        n_estimators: int = 100,
        learning_rate: float = 0.1,
        max_depth: int = 3,
    ) -> EnsembleResult:
        """
        Analyze boosting ensemble.

        Args:
            X: Feature matrix
            y: Target vector
            n_estimators: Number of estimators
            learning_rate: Learning rate
            max_depth: Max tree depth

        Returns:
            EnsembleResult with analysis
        """
        X_train, X_test, y_train, y_test = self._split_data(X, y)

        boosting = self._train_boosting(X_train, y_train, n_estimators, learning_rate, max_depth)
        train_score = boosting.score(X_train, y_train)
        test_score = boosting.score(X_test, y_test)
        staged_scores = list(boosting.staged_predict(X_test))
        importance = boosting.get_feature_importance()

        result = EnsembleResult(
            timestamp=datetime.now(),
            method=EnsembleMethod.GRADIENT_BOOSTING,
            n_estimators=n_estimators,
            train_score=train_score,
            test_score=test_score,
            estimator_scores=[test_score] * len(staged_scores),
            ensemble_improvement=0.0,
            diversity=0.0,
            model_name="GradientBoosting",
            details={
                "learning_rate": learning_rate,
                "max_depth": max_depth,
                "feature_importance": importance.tolist(),
            },
        )

        logger.info(f"Boosting: n={n_estimators}, test_score={test_score:.4f}")

        return result

    def _train_boosting(
        self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series],
        n_estimators: int, learning_rate: float, max_depth: int
    ) -> BoostingEnsemble:
        """Train boosting ensemble with given parameters."""
        config = BoostingConfig(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
        )
        boosting = BoostingEnsemble(config=config)
        boosting.fit(X, y)
        return boosting

    def analyze_stacking(
        self,
        base_estimators: List[Tuple[str, BaseEstimator]],
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        meta_estimator: Optional[BaseEstimator] = None,
    ) -> EnsembleResult:
        """
        Analyze stacking ensemble.

        Args:
            base_estimators: List of (name, estimator) tuples
            X: Feature matrix
            y: Target vector
            meta_estimator: Meta-learner

        Returns:
            EnsembleResult with analysis
        """
        X_train, X_test, y_train, y_test = self._split_data(X, y)

        stacking = self._train_stacking(base_estimators, X_train, y_train, meta_estimator)
        train_score = stacking.score(X_train, y_train)
        test_score = stacking.score(X_test, y_test)
        base_scores_dict = stacking.get_base_model_scores(X_test, y_test)
        base_scores = list(base_scores_dict.values())

        result = EnsembleResult(
            timestamp=datetime.now(),
            method=EnsembleMethod.STACKING,
            n_estimators=len(base_estimators),
            train_score=train_score,
            test_score=test_score,
            estimator_scores=base_scores,
            ensemble_improvement=test_score - max(base_scores),
            diversity=0.0,
            model_name="Stacking",
            details={"base_scores": base_scores_dict},
        )

        self._log_stacking_result(len(base_estimators), test_score, result.ensemble_improvement)

        return result

    def _train_stacking(
        self, base_estimators: List[Tuple[str, BaseEstimator]],
        X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series],
        meta_estimator: Optional[BaseEstimator]
    ) -> StackingEnsemble:
        """Train stacking ensemble with given base estimators."""
        stacking = StackingEnsemble(
            base_estimators=base_estimators,
            meta_estimator=meta_estimator,
        )
        stacking.fit(X, y)
        return stacking

    def _log_stacking_result(self, n_estimators: int, test_score: float, improvement: float) -> None:
        """Log stacking analysis results."""
        logger.info(
            f"Stacking: n={n_estimators}, test_score={test_score:.4f}, "
            f"improvement={improvement:.4f}"
        )

    def _compute_diversity(
        self,
        ensemble: Union[BaggingEnsemble, RandomForestEnsemble],
        X: Union[np.ndarray, pd.DataFrame],
    ) -> float:
        """
        Compute diversity among ensemble members.

        Diversity measured as 1 - average correlation between predictions.

        Args:
            ensemble: Fitted ensemble
            X: Feature matrix

        Returns:
            Diversity score (0 = identical, 1 = completely different)
        """
        check_is_fitted(ensemble, ["bagger_", "rf_"])

        estimators = self._get_ensemble_estimators(ensemble)
        predictions = self._get_estimator_predictions(estimators, X)
        correlations = self._compute_pairwise_correlations(predictions)

        if not correlations:
            return 0.0

        return 1 - np.mean(correlations)

    def _get_ensemble_estimators(
        self, ensemble: Union[BaggingEnsemble, RandomForestEnsemble]
    ) -> List[BaseEstimator]:
        """Get estimators from fitted ensemble."""
        if hasattr(ensemble, "bagger_"):
            return ensemble.bagger_.estimators_
        return ensemble.rf_.estimators_

    def _get_estimator_predictions(
        self, estimators: List[BaseEstimator], X: Union[np.ndarray, pd.DataFrame]
    ) -> np.ndarray:
        """Get predictions from all estimators."""
        return np.array([estimator.predict(X) for estimator in estimators])

    def _compute_pairwise_correlations(self, predictions: np.ndarray) -> List[float]:
        """Compute pairwise correlations between predictions."""
        n_estimators = len(predictions)
        correlations = []

        for i in range(n_estimators):
            for j in range(i + 1, n_estimators):
                corr = np.corrcoef(predictions[i], predictions[j])[0, 1]
                if not np.isnan(corr):
                    correlations.append(corr)

        return correlations

    def _create_ensemble_result(
        self,
        method: EnsembleMethod,
        n_estimators: int,
        train_score: float,
        test_score: float,
        estimator_scores: List[float],
        model_name: str,
        details: Dict[str, Any],
    ) -> EnsembleResult:
        """Create ensemble result with computed metrics."""
        best_single = max(estimator_scores) if estimator_scores else test_score
        improvement = test_score - best_single

        return EnsembleResult(
            timestamp=datetime.now(),
            method=method,
            n_estimators=n_estimators,
            train_score=train_score,
            test_score=test_score,
            estimator_scores=estimator_scores,
            ensemble_improvement=improvement,
            diversity=0.0,
            model_name=model_name,
            details=details,
        )

    def compare_ensembles(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        base_estimator: Optional[BaseEstimator] = None,
        base_estimators: Optional[List[Tuple[str, BaseEstimator]]] = None,
        n_estimators: int = 100,
    ) -> Dict[str, EnsembleResult]:
        """
        Compare different ensemble methods.

        Args:
            X: Feature matrix
            y: Target vector
            base_estimator: Base estimator for bagging/RF
            base_estimators: Base estimators for stacking
            n_estimators: Number of estimators

        Returns:
            Dictionary mapping method names to results
        """
        base_estimator = base_estimator or DecisionTreeRegressor()
        base_estimators = base_estimators or self._get_default_base_estimators()

        results = {}

        results["bagging"] = self._safe_analyze_bagging(base_estimator, X, y, n_estimators)
        results["random_forest"] = self._safe_analyze_random_forest(X, y, n_estimators)
        results["boosting"] = self._safe_analyze_boosting(X, y, n_estimators)
        results["stacking"] = self._safe_analyze_stacking(base_estimators, X, y)

        return results

    def _get_default_base_estimators(self) -> List[Tuple[str, BaseEstimator]]:
        """Get default base estimators for stacking."""
        return [
            ("dt", DecisionTreeRegressor()),
            ("rf", RandomForestRegressor(n_estimators=50)),
        ]

    def _safe_analyze_bagging(
        self, estimator: BaseEstimator, X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series], n_estimators: int
    ) -> Optional[EnsembleResult]:
        """Safely analyze bagging ensemble with error handling."""
        try:
            return self.analyze_bagging(estimator, X, y, n_estimators=n_estimators)
        except Exception as e:
            logger.error(f"Bagging failed: {e}")
            return None

    def _safe_analyze_random_forest(
        self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series],
        n_estimators: int
    ) -> Optional[EnsembleResult]:
        """Safely analyze random forest with error handling."""
        try:
            rf = RandomForestEnsemble(n_estimators=n_estimators)
            rf.fit(X, y)
            score = rf.score(X, y)
            return EnsembleResult(
                timestamp=datetime.now(),
                method=EnsembleMethod.RANDOM_FOREST,
                n_estimators=n_estimators,
                train_score=score,
                test_score=score,
                estimator_scores=[],
                ensemble_improvement=0.0,
                diversity=0.0,
                model_name="RandomForest",
            )
        except Exception as e:
            logger.error(f"Random Forest failed: {e}")
            return None

    def _safe_analyze_boosting(
        self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series],
        n_estimators: int
    ) -> Optional[EnsembleResult]:
        """Safely analyze boosting ensemble with error handling."""
        try:
            return self.analyze_boosting(X, y, n_estimators=n_estimators)
        except Exception as e:
            logger.error(f"Boosting failed: {e}")
            return None

    def _safe_analyze_stacking(
        self, base_estimators: List[Tuple[str, BaseEstimator]],
        X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]
    ) -> Optional[EnsembleResult]:
        """Safely analyze stacking ensemble with error handling."""
        try:
            return self.analyze_stacking(base_estimators, X, y)
        except Exception as e:
            logger.error(f"Stacking failed: {e}")
            return None


def bagging_ensemble(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    n_estimators: int = 100,
) -> Tuple[BaggingEnsemble, EnsembleResult]:
    """
    Convenience function for bagging.

    Args:
        X: Feature matrix
        y: Target vector
        n_estimators: Number of estimators

    Returns:
        (fitted_ensemble, result)

    Example:
        >>> ensemble, result = bagging_ensemble(X, y, n_estimators=100)
        >>> print(f"Test score: {result.test_score:.4f}")
    """
    analyzer = EnsembleAnalyzer()
    estimator = DecisionTreeRegressor()
    result = analyzer.analyze_bagging(estimator, X, y, n_estimators=n_estimators)

    ensemble = BaggingEnsemble(estimator=estimator)
    ensemble.fit(X, y)

    return ensemble, result


def stacking_ensemble(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    base_estimators: List[Tuple[str, BaseEstimator]],
) -> Tuple[StackingEnsemble, EnsembleResult]:
    """
    Convenience function for stacking.

    Args:
        X: Feature matrix
        y: Target vector
        base_estimators: List of (name, estimator) tuples

    Returns:
        (fitted_ensemble, result)

    Example:
        >>> base_models = [("lr", LinearRegression()), ("rf", RandomForestRegressor())]
        >>> ensemble, result = stacking_ensemble(X, y, base_models)
        >>> print(f"Test score: {result.test_score:.4f}")
    """
    analyzer = EnsembleAnalyzer()
    result = analyzer.analyze_stacking(base_estimators, X, y)

    ensemble = StackingEnsemble(base_estimators=base_estimators)
    ensemble.fit(X, y)

    return ensemble, result
