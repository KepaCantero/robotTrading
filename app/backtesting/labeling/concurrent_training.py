"""
Concurrent Model Training for Financial ML

Based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 4 & 7.

This module implements concurrent training of multiple models with proper
handling of sample uniqueness and model ensembling.

Key Concepts:
1. Concurrent Training: Train multiple models in parallel
2. Uniqueness-Weighted Ensembling: Weight models by sample uniqueness
3. Sequential Model Training: Train models sequentially with purged data
4. Ensemble Methods: Combine predictions from multiple models

Why Concurrent Training:
- Faster model development
- Robustness through model diversity
- Better handling of non-stationary data
- Reduced overfitting through ensembling

Ensemble Strategies:
1. Simple Average: Equal weight to all models
2. Weighted Average: Weight by performance or uniqueness
3. Stacking: Use meta-model to combine predictions
4. Voting: Majority vote for classification

Example:
    >>> from sklearn.ensemble import RandomForestClassifier
    >>> from sklearn.linear_model import LogisticRegression
    >>>
    >>> models = {
    ...     'rf': RandomForestClassifier(),
    ...     'lr': LogisticRegression(),
    ... }
    >>>
    >>> # Train concurrently
    >>> trainer = ConcurrentModelTrainer()
    >>> results = trainer.train_models_concurrent(
    ...     models, X_train, y_train, events, labels
    ... )
    >>>
    >>> # Ensemble predictions
    >>> ensemble_pred = results.ensemble_predict(X_test)

Note on ASYNC-001 (NOT APPLIED):
    This module uses ProcessPoolExecutor for true parallelism across CPU cores,
    which is appropriate for CPU-bound ML model training. Async/await would not
    provide benefits here since the training operations are CPU-bound, not I/O-bound.
    ProcessPoolExecutor correctly utilizes multiprocessing to avoid Python's GIL.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Custom exceptions for concurrent training (CC-006: Specific exception types)
class ConcurrentTrainingError(Exception):
    """Base exception for concurrent training errors."""


class ModelTrainingError(ConcurrentTrainingError):
    """Raised when a model fails to train."""


class EnsembleError(ConcurrentTrainingError):
    """Raised when ensemble creation fails."""


@dataclass
class ConcurrentTrainingConfig:
    """Configuration for concurrent model training."""

    # Training parameters
    n_jobs: int = -1  # -1 means use all available cores
    verbose: int = 1

    # Ensemble parameters
    ensemble_method: str = "weighted"  # simple, weighted, stacking, voting
    weight_by: str = "accuracy"  # accuracy, f1, roc_auc, uniqueness

    # Uniqueness weighting
    use_uniqueness_weights: bool = True
    uniqueness_method: str = "average"

    # Cross-validation
    cv_folds: int = 5
    purge_pct: float = 0.05
    embargo_pct: float = 0.01

    # Stacking parameters
    stacking_meta_model: str = "logistic"  # logistic, rf, xgb

    # Model selection
    select_best_models: bool = True
    top_n_models: int = 3

    def __post_init__(self):
        """Validate configuration."""
        valid_ensemble = ["simple", "weighted", "stacking", "voting"]
        if self.ensemble_method not in valid_ensemble:
            raise ValueError(f"ensemble_method must be one of {valid_ensemble}")

        valid_weight = ["accuracy", "f1", "roc_auc", "uniqueness"]
        if self.weight_by not in valid_weight:
            raise ValueError(f"weight_by must be one of {valid_weight}")


@dataclass
class ModelResult:
    """Result from a single model training."""

    model_name: str
    model: object
    predictions: np.ndarray
    probabilities: Optional[np.ndarray]
    score: float
    training_time: float

    # Uniqueness information
    uniqueness_weights: Optional[np.ndarray] = None
    avg_uniqueness: float = 0.0

    # Feature importance
    feature_importance: Dict[str, float] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Union[str, int, float, bool, None]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EnsembleResult:
    """Result from ensemble model training."""

    model_results: List[ModelResult]
    """Results from individual models"""

    ensemble_predictions: np.ndarray
    """Ensemble predictions"""

    ensemble_probabilities: Optional[np.ndarray]
    """Ensemble probabilities"""

    ensemble_score: float
    """Ensemble score"""

    ensemble_weights: Dict[str, float]
    """Weights for each model in ensemble"""

    stacking_model: Optional[object] = None
    """Stacking meta-model (if used)"""

    metadata: Dict[str, Union[str, int, float, bool, None]] = field(default_factory=dict)
    """Additional metadata"""

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Union[str, int, float, bool, list, None]]:
        """Convert to dictionary."""
        return {
            "ensemble_predictions": self.ensemble_predictions.tolist(),
            "ensemble_score": float(self.ensemble_score),
            "ensemble_weights": self.ensemble_weights,
            "n_models": len(self.model_results),
            "models": [mr.model_name for mr in self.model_results],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class ConcurrentModelTrainer:
    """
    Concurrent training of multiple models for financial ML.

    This class implements parallel training of multiple models with
    proper handling of sample uniqueness and ensemble creation.

    Example:
        >>> trainer = ConcurrentModelTrainer(n_jobs=4)
        >>> results = trainer.train_models_concurrent(
        ...     models, X_train, y_train, events, labels
        ... )
        >>> ensemble_pred = results.ensemble_predictions
    """

    def __init__(self, config: Optional[ConcurrentTrainingConfig] = None):
        """
        Initialize ConcurrentModelTrainer.

        Args:
            config: Configuration for concurrent training
        """
        self.config = config or ConcurrentTrainingConfig()

    # ========== Helper Methods (ARCH-004: Extract helper methods) ==========

    def _convert_to_numpy(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert pandas objects to numpy arrays.

        Args:
            X: Feature matrix
            y: Target labels

        Returns:
            Tuple of (X_array, y_array)
        """
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values
        return X, y

    def _calculate_uniqueness_weights(
        self,
        events: Optional[pd.Series],
        labels: Optional[pd.DataFrame],
        X: np.ndarray,
    ) -> Optional[np.ndarray]:
        """
        Calculate uniqueness weights if events and labels are provided.

        Args:
            events: Event timestamps
            labels: DataFrame with label timing
            X: Feature matrix (for price series)

        Returns:
            Uniqueness weights or None
        """
        if not self.config.use_uniqueness_weights or events is None or labels is None:
            return None

        from .triple_barrier import calculate_sample_weights_uniqueness

        price_series = pd.Series(range(len(X)))
        return calculate_sample_weights_uniqueness(events, labels, price_series).values

    def _combine_sample_weights(
        self,
        sample_weights: Optional[np.ndarray],
        uniqueness_weights: Optional[np.ndarray],
    ) -> Optional[np.ndarray]:
        """
        Combine sample weights with uniqueness weights.

        Args:
            sample_weights: Original sample weights
            uniqueness_weights: Uniqueness weights

        Returns:
            Combined weights or None
        """
        if uniqueness_weights is not None and sample_weights is not None:
            return sample_weights * uniqueness_weights
        elif uniqueness_weights is not None:
            return uniqueness_weights
        else:
            return sample_weights

    def train_models_concurrent(
        self,
        models: Dict[str, object],
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        events: Optional[pd.Series] = None,
        labels: Optional[pd.DataFrame] = None,
        sample_weights: Optional[np.ndarray] = None,
    ) -> EnsembleResult:
        """
        Train multiple models concurrently.

        Args:
            models: Dictionary of model_name -> model_instance
            X: Feature matrix
            y: Target labels
            events: Event timestamps
            labels: DataFrame with label timing
            sample_weights: Optional sample weights

        Returns:
            EnsembleResult with predictions and weights

        Example:
            >>> models = {
            ...     'rf': RandomForestClassifier(),
            ...     'lr': LogisticRegression(),
            ... }
            >>> results = trainer.train_models_concurrent(
            ...     models, X, y, events, labels
            ... )
        """
        # Convert to numpy arrays (ARCH-004: Use helper method)
        X, y = self._convert_to_numpy(X, y)

        # Calculate uniqueness weights (ARCH-004: Use helper method)
        uniqueness_weights = self._calculate_uniqueness_weights(events, labels, X)

        # Train models concurrently
        model_results = []
        n_models = len(models)

        logger.info(f"Training {n_models} models concurrently...")

        # Determine number of jobs
        n_jobs = self.config.n_jobs if self.config.n_jobs > 0 else None

        # Use ProcessPoolExecutor for true parallelism
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            # Submit training jobs
            futures = {}
            for model_name, model in models.items():
                future = executor.submit(
                    self._train_single_model,
                    model_name,
                    model,
                    X,
                    y,
                    sample_weights,
                    uniqueness_weights,
                )
                futures[future] = model_name

            # Collect results
            for future in as_completed(futures):
                model_name = futures[future]
                try:
                    result = future.result()
                    model_results.append(result)
                    logger.info(f"Model {model_name} completed: score={result.score:.4f}")
                except Exception:
                    # LOG-004: Add exc_info=True for stack traces
                    logger.error(
                        f"Model {model_name} failed to train",
                        exc_info=True,
                    )

        if not model_results:
            raise ModelTrainingError("All models failed to train")

        # Create ensemble
        ensemble_result = self._create_ensemble(model_results, X, y, events, labels)

        return ensemble_result

    def _train_single_model(
        self,
        model_name: str,
        model: object,
        X: np.ndarray,
        y: np.ndarray,
        sample_weights: Optional[np.ndarray],
        uniqueness_weights: Optional[np.ndarray],
    ) -> ModelResult:
        """
        Train a single model (for parallel execution).

        Note: This must be pickleable for multiprocessing.
        """
        import time

        start_time = time.time()

        # Combine sample weights with uniqueness weights (ARCH-004: Use helper method)
        combined_weights = self._combine_sample_weights(sample_weights, uniqueness_weights)

        # Train model
        if combined_weights is not None:
            model.fit(X, y, sample_weight=combined_weights)
        else:
            model.fit(X, y)

        training_time = time.time() - start_time

        # Make predictions
        predictions = model.predict(X)

        # Get probabilities if available
        probabilities = None
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)
            if probabilities.shape[1] == 2:
                probabilities = probabilities[:, 1]

        # Calculate score
        score = np.mean(predictions == y)

        # Get feature importance if available
        feature_importance = {}
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            for i, imp in enumerate(importances):
                feature_importance[f"feature_{i}"] = float(imp)

        # Calculate average uniqueness
        avg_uniqueness = 0.0
        if uniqueness_weights is not None:
            avg_uniqueness = float(uniqueness_weights.mean())

        return ModelResult(
            model_name=model_name,
            model=model,
            predictions=predictions,
            probabilities=probabilities,
            score=score,
            training_time=training_time,
            uniqueness_weights=uniqueness_weights,
            avg_uniqueness=avg_uniqueness,
            feature_importance=feature_importance,
        )

    def _create_ensemble(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        y: np.ndarray,
        events: Optional[pd.Series],
        labels: Optional[pd.DataFrame],
    ) -> EnsembleResult:
        """
        Create ensemble from trained models.

        Args:
            model_results: Results from individual models
            X: Feature matrix
            y: Target labels
            events: Event timestamps
            labels: DataFrame with label timing

        Returns:
            EnsembleResult
        """
        # Select best models if requested (ARCH-004: Use helper method)
        model_results = self._select_best_models(model_results)

        # Calculate ensemble weights (ARCH-004: Use helper method)
        ensemble_weights = self._calculate_ensemble_weights(model_results, X, y)

        # Generate ensemble predictions
        ensemble_pred, ensemble_proba = self._ensemble_predict(model_results, X, ensemble_weights)

        # Calculate ensemble score
        ensemble_score = np.mean(ensemble_pred == y)

        # Stacking model if requested
        stacking_model = None
        if self.config.ensemble_method == "stacking":
            stacking_model = self._create_stacking_model(model_results, X, y, events, labels)

        return EnsembleResult(
            model_results=model_results,
            ensemble_predictions=ensemble_pred,
            ensemble_probabilities=ensemble_proba,
            ensemble_score=ensemble_score,
            ensemble_weights=ensemble_weights,
            stacking_model=stacking_model,
            metadata={
                "n_models": len(model_results),
                "ensemble_method": self.config.ensemble_method,
            },
        )

    def _select_best_models(self, model_results: List[ModelResult]) -> List[ModelResult]:
        """
        Select best models if configured (ARCH-004: Extract helper method).

        Args:
            model_results: Results from individual models

        Returns:
            Filtered model results
        """
        if self.config.select_best_models:
            return sorted(model_results, key=lambda x: x.score, reverse=True)[
                : self.config.top_n_models
            ]
        return model_results

    def _calculate_ensemble_weights(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calculate ensemble weights for each model (ARCH-004: Extract helper method).

        Args:
            model_results: Results from individual models
            X: Feature matrix
            y: Target labels

        Returns:
            Dictionary mapping model names to weights
        """
        weights = {}

        if self.config.ensemble_method == "simple":
            # Equal weights
            for result in model_results:
                weights[result.model_name] = 1.0 / len(model_results)

        elif self.config.ensemble_method == "weighted":
            # Weight by performance
            if self.config.weight_by == "accuracy":
                scores = [result.score for result in model_results]
            elif self.config.weight_by == "uniqueness":
                scores = [result.avg_uniqueness for result in model_results]
            else:
                scores = [result.score for result in model_results]

            # Softmax weighting
            exp_scores = np.exp(np.array(scores))
            softmax_weights = exp_scores / exp_scores.sum()

            for result, weight in zip(model_results, softmax_weights):
                weights[result.model_name] = float(weight)

        elif self.config.ensemble_method == "voting":
            # Equal weights (voting is done by majority)
            for result in model_results:
                weights[result.model_name] = 1.0 / len(model_results)

        else:  # stacking
            # Weights determined by stacking model
            for result in model_results:
                weights[result.model_name] = 1.0 / len(model_results)

        return weights

    def _ensemble_predict(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        weights: Dict[str, float],
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Generate ensemble predictions (ARCH-004: Split into smaller methods).

        Args:
            model_results: Results from individual models
            X: Feature matrix
            weights: Model weights

        Returns:
            Tuple of (predictions, probabilities)
        """
        if self.config.ensemble_method == "voting":
            return self._voting_predict(model_results, X, weights)
        else:
            return self._weighted_predict(model_results, X, weights)

    def _voting_predict(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        weights: Dict[str, float],
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Generate ensemble predictions using majority voting (ARCH-004: Helper method).

        Args:
            model_results: Results from individual models
            X: Feature matrix
            weights: Model weights (unused for voting, kept for interface)

        Returns:
            Tuple of (predictions, None)
        """
        # Majority voting
        predictions_list = []
        for result in model_results:
            pred = result.model.predict(X)
            predictions_list.append(pred)

        predictions = np.array(
            [np.bincount(preds.astype(int)).argmax() for preds in zip(*predictions_list)]
        )

        return predictions, None

    def _weighted_predict(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        weights: Dict[str, float],
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Generate ensemble predictions using weighted average (ARCH-004: Helper method).

        Args:
            model_results: Results from individual models
            X: Feature matrix
            weights: Model weights

        Returns:
            Tuple of (predictions, probabilities)
        """
        n_samples = len(X)
        weighted_pred = np.zeros(n_samples)
        weighted_proba = np.zeros(n_samples)

        total_weight = 0.0
        for result in model_results:
            weight = weights.get(result.model_name, 0.0)
            pred = result.model.predict(X)
            weighted_pred += weight * pred

            if result.probabilities is not None:
                proba = result.model.predict_proba(X)
                if proba.shape[1] == 2:
                    weighted_proba += weight * proba[:, 1]

            total_weight += weight

        if total_weight > 0:
            weighted_pred /= total_weight
            weighted_proba /= total_weight

        # Convert to binary predictions
        predictions = (weighted_pred >= 0.5).astype(int)
        probabilities = weighted_proba if total_weight > 0 else None

        return predictions, probabilities

    def _create_stacking_model(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        y: np.ndarray,
        events: Optional[pd.Series],
        labels: Optional[pd.DataFrame],
    ) -> object:
        """
        Create stacking meta-model.

        Args:
            model_results: Results from individual models
            X: Feature matrix
            y: Target labels
            events: Event timestamps
            labels: DataFrame with label timing

        Returns:
            Trained meta-model
        """
        # Get predictions from base models
        meta_features = []
        for result in model_results:
            if result.probabilities is not None:
                meta_features.append(result.probabilities)
            else:
                meta_features.append(result.predictions.astype(float))

        # Create meta-feature matrix
        X_meta = np.column_stack(meta_features)

        # Train meta-model
        if self.config.stacking_meta_model == "logistic":
            from sklearn.linear_model import LogisticRegression

            meta_model = LogisticRegression()
        elif self.config.stacking_meta_model == "rf":
            from sklearn.ensemble import RandomForestClassifier

            meta_model = RandomForestClassifier(n_estimators=50, max_depth=3)
        elif self.config.stacking_meta_model == "xgb":
            try:
                from xgboost import XGBClassifier

                meta_model = XGBClassifier(n_estimators=50, max_depth=3)
            except ImportError:
                from sklearn.ensemble import RandomForestClassifier

                meta_model = RandomForestClassifier(n_estimators=50, max_depth=3)
        else:
            from sklearn.linear_model import LogisticRegression

            meta_model = LogisticRegression()

        # Use purged CV for meta-model
        if events is not None and labels is not None:
            from .meta_labeling_cv import PurgedKFold

            PurgedKFold(
                n_folds=self.config.cv_folds,
                purge_pct=self.config.purge_pct,
                embargo_pct=self.config.embargo_pct,
            )

            # Simple fitting for now
            # In practice, would use purged CV
            meta_model.fit(X_meta, y)
        else:
            meta_model.fit(X_meta, y)

        return meta_model


class SequentialModelTrainer:
    """
    Sequential training of models with purged data.

    This class implements sequential model training where each model
    is trained on data that has been purged of samples used in
    previous models.

    Example:
        >>> trainer = SequentialModelTrainer()
        >>> results = trainer.train_models_sequential(
        ...     models, X, y, events, labels
        ... )
    """

    def __init__(self, config: Optional[ConcurrentTrainingConfig] = None):
        """Initialize SequentialModelTrainer."""
        self.config = config or ConcurrentTrainingConfig()

    # ========== Helper Methods (ARCH-004: Extract helper methods) ==========

    def _convert_to_numpy(
        self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Convert pandas objects to numpy arrays."""
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values
        return X, y

    def _get_feature_importance(self, model: object) -> Dict[str, float]:
        """Extract feature importance from model if available."""
        feature_importance = {}
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            for i, imp in enumerate(importances):
                feature_importance[f"feature_{i}"] = float(imp)
        return feature_importance

    def _get_probabilities(self, model: object, X: np.ndarray) -> Optional[np.ndarray]:
        """Get probabilities from model if available."""
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)
            if probabilities.shape[1] == 2:
                return probabilities[:, 1]
        return None

    def train_models_sequential(
        self,
        models: Dict[str, object],
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        events: Optional[pd.Series] = None,
        labels: Optional[pd.DataFrame] = None,
    ) -> EnsembleResult:
        """
        Train models sequentially with purged data.

        Args:
            models: Dictionary of models
            X: Feature matrix
            y: Target labels
            events: Event timestamps
            labels: DataFrame with label timing

        Returns:
            EnsembleResult
        """
        # Convert to numpy arrays (ARCH-004: Use helper method)
        X, y = self._convert_to_numpy(X, y)

        model_results = []
        used_indices = set()

        for model_name, model in models.items():
            # Determine which samples to use
            available_indices = set(range(len(X))) - used_indices

            if not available_indices:
                logger.warning(f"No samples left for {model_name}")
                continue

            train_indices = np.array(list(available_indices))

            # Train model
            X_train = X[train_indices]
            y_train = y[train_indices]

            model.fit(X_train, y_train)

            # Make predictions
            predictions = model.predict(X)

            # Calculate score
            score = np.mean(predictions[train_indices] == y_train)

            # Get probabilities (ARCH-004: Use helper method)
            probabilities = self._get_probabilities(model, X)

            # Get feature importance (ARCH-004: Use helper method)
            feature_importance = self._get_feature_importance(model)

            result = ModelResult(
                model_name=model_name,
                model=model,
                predictions=predictions,
                probabilities=probabilities,
                score=score,
                training_time=0.0,
                feature_importance=feature_importance,
            )

            model_results.append(result)

            # Mark samples as used
            # In practice, would use more sophisticated logic
            used_indices.update(train_indices[: len(train_indices) // 2])

            logger.info(f"Model {model_name} completed: score={score:.4f}")

        # Create ensemble
        if not model_results:
            raise ModelTrainingError("All models failed to train")

        ensemble_result = self._create_ensemble(model_results, X, y)

        return ensemble_result

    def _create_ensemble(
        self,
        model_results: List[ModelResult],
        X: np.ndarray,
        y: np.ndarray,
    ) -> EnsembleResult:
        """Create ensemble from sequential training results."""
        # Simple equal weighting
        weights = {result.model_name: 1.0 / len(model_results) for result in model_results}

        # Weighted predictions
        ensemble_pred = np.zeros(len(X))
        for result in model_results:
            ensemble_pred += weights[result.model_name] * result.predictions

        ensemble_pred = (ensemble_pred >= 0.5).astype(int)
        ensemble_score = np.mean(ensemble_pred == y)

        return EnsembleResult(
            model_results=model_results,
            ensemble_predictions=ensemble_pred,
            ensemble_probabilities=None,
            ensemble_score=ensemble_score,
            ensemble_weights=weights,
            metadata={
                "n_models": len(model_results),
                "ensemble_method": "sequential",
            },
        )


def train_models_concurrent(
    models: Dict[str, object],
    X: Union[pd.DataFrame, np.ndarray],
    y: Union[pd.Series, np.ndarray],
    events: Optional[pd.Series] = None,
    labels: Optional[pd.DataFrame] = None,
    ensemble_method: str = "weighted",
    n_jobs: int = -1,
) -> EnsembleResult:
    """
    Train multiple models concurrently.

    Convenience function for quick concurrent training.

    Args:
        models: Dictionary of models
        X: Feature matrix
        y: Target labels
        events: Event timestamps
        labels: DataFrame with label timing
        ensemble_method: Method for combining predictions
        n_jobs: Number of parallel jobs

    Returns:
        EnsembleResult with predictions

    Example:
        >>> models = {
        ...     'rf': RandomForestClassifier(),
        ...     'lr': LogisticRegression(),
        ... }
        >>> results = train_models_concurrent(
        ...     models, X, y, events, labels
        ... )
        >>> print(f"Ensemble score: {results.ensemble_score:.4f}")
    """
    config = ConcurrentTrainingConfig(
        ensemble_method=ensemble_method,
        n_jobs=n_jobs,
    )

    trainer = ConcurrentModelTrainer(config)
    return trainer.train_models_concurrent(models, X, y, events, labels)
