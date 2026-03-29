"""
Model Selection Criteria for Statistical Learning.

This module implements comprehensive model selection criteria following
Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning"
(ESL) Chapter 7: Model Assessment and Selection.

Key Criteria:
1. AIC (Akaike Information Criterion)
2. BIC (Bayesian Information Criterion)
3. Adjusted R-squared
4. Mallow's Cp
5. Cross-Validation estimates
6. Generalized Cross-Validation (GCV)

Reference:
    "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    Chapter 7: Model Assessment and Selection
    Chapter 9: Generalized Linear Models and Regression Splines
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score
from sklearn.utils.validation import check_array, check_is_fitted

logger = logging.getLogger(__name__)


class CriterionType(Enum):
    """Model selection criterion types."""

    AIC = "aic"  # Akaike Information Criterion
    BIC = "bic"  # Bayesian Information Criterion
    ADJUSTED_R2 = "adjusted_r2"
    MALLOW_CP = "mallow_cp"
    GCV = "gcv"  # Generalized Cross-Validation
    CV_SCORE = "cv_score"


@dataclass
class ModelCriterionResult:
    """Result of model selection criterion calculation."""

    timestamp: datetime
    model_name: str
    criterion_type: CriterionType
    criterion_value: float
    n_params: int
    n_samples: int

    # Performance metrics
    mse: float
    rmse: float
    r2: float
    adjusted_r2: float

    # Additional statistics
    log_likelihood: float = 0.0
    aic: float = 0.0
    bic: float = 0.0

    # Ranking (lower is better for AIC, BIC, Cp)
    rank: int | None = None

    # Additional info
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "criterion_type": self.criterion_type.value,
            "criterion_value": self.criterion_value,
            "n_params": self.n_params,
            "n_samples": self.n_samples,
            "mse": self.mse,
            "rmse": self.rmse,
            "r2": self.r2,
            "adjusted_r2": self.adjusted_r2,
            "log_likelihood": self.log_likelihood,
            "aic": self.aic,
            "bic": self.bic,
            "rank": self.rank,
            "details": self.details,
        }


@dataclass
class ModelComparisonResult:
    """Result of comparing multiple models."""

    timestamp: datetime
    models: list[ModelCriterionResult]
    best_model_by_aic: str
    best_model_by_bic: str
    best_model_by_adjusted_r2: str
    best_model_by_cv: str | None

    # Summary statistics
    comparison_table: pd.DataFrame

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "models": [m.to_dict() for m in self.models],
            "best_model_by_aic": self.best_model_by_aic,
            "best_model_by_bic": self.best_model_by_bic,
            "best_model_by_adjusted_r2": self.best_model_by_adjusted_r2,
            "best_model_by_cv": self.best_model_by_cv,
            "comparison_table": self.comparison_table.to_dict(),
        }


class AICCalculator:
    """
    Akaike Information Criterion (AIC).

    AIC estimates the relative quality of statistical models.
    It balances goodness of fit against model complexity.

    AIC = 2k - 2ln(L)

    Where:
    - k = number of parameters
    - L = maximized value of likelihood function

    Lower AIC indicates better model (penalizes complexity).

    Interpretation:
    - ΔAIC < 2: Substantial evidence
    - 4 ≤ ΔAIC < 7: considerably less evidence
    - ΔAIC ≥ 10: essentially none

    Reference: ESL Section 7.5
    """

    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_params: int,
        estimate_sigma: bool = True,
    ) -> float:
        """
        Calculate AIC.

        For linear regression with normally distributed errors:

        AIC = n * ln(RSS/n) + 2k

        Where:
        - n = sample size
        - RSS = residual sum of squares
        - k = number of parameters (including σ² if estimated)

        Args:
            y_true: True values
            y_pred: Predicted values
            n_params: Number of parameters (excluding σ²)
            estimate_sigma: Whether σ² was estimated (adds 1 to k)

        Returns:
            AIC value
        """
        n = len(y_true)
        residuals = y_true - y_pred
        rss = np.sum(residuals**2)

        # Number of parameters
        k = n_params
        if estimate_sigma:
            k += 1

        # AIC formula (constant term omitted for comparison)
        aic = n * np.log(rss / n) + 2 * k

        return aic

    @staticmethod
    def calculate_with_likelihood(
        log_likelihood: float,
        n_params: int,
    ) -> float:
        """
        Calculate AIC from log-likelihood.

        AIC = 2k - 2ln(L)

        Args:
            log_likelihood: Log-likelihood value
            n_params: Number of parameters

        Returns:
            AIC value
        """
        return 2 * n_params - 2 * log_likelihood


class BICCalculator:
    """
    Bayesian Information Criterion (BIC).

    BIC is a criterion for model selection among a finite set of models.
    It has a stronger penalty for complexity than AIC.

    BIC = k * ln(n) - 2ln(L)

    Where:
    - k = number of parameters
    - n = sample size
    - L = maximized value of likelihood function

    Lower BIC indicates better model.

    Interpretation:
    - BIC approximates Bayes factor
    - Stronger penalty for complexity than AIC
    - Consistent model selection (selects true model as n → ∞)

    Reference: ESL Section 7.7
    """

    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_params: int,
        estimate_sigma: bool = True,
    ) -> float:
        """
        Calculate BIC.

        For linear regression:

        BIC = n * ln(RSS/n) + k * ln(n)

        Args:
            y_true: True values
            y_pred: Predicted values
            n_params: Number of parameters (excluding σ²)
            estimate_sigma: Whether σ² was estimated (adds 1 to k)

        Returns:
            BIC value
        """
        n = len(y_true)
        residuals = y_true - y_pred
        rss = np.sum(residuals**2)

        # Number of parameters
        k = n_params
        if estimate_sigma:
            k += 1

        # BIC formula
        bic = n * np.log(rss / n) + k * np.log(n)

        return bic

    @staticmethod
    def calculate_with_likelihood(
        log_likelihood: float,
        n_params: int,
        n_samples: int,
    ) -> float:
        """
        Calculate BIC from log-likelihood.

        BIC = k * ln(n) - 2ln(L)

        Args:
            log_likelihood: Log-likelihood value
            n_params: Number of parameters
            n_samples: Sample size

        Returns:
            BIC value
        """
        return n_params * np.log(n_samples) - 2 * log_likelihood


class AdjustedR2Calculator:
    """
    Adjusted R-squared.

    R² increases with number of predictors, even if they don't improve model.
    Adjusted R² penalizes model complexity.

    Adjusted R² = 1 - (1 - R²) * (n - 1) / (n - p - 1)

    Where:
    - n = sample size
    - p = number of predictors

    Adjusted R² can be negative if model fit is very poor.
    Higher is better.

    Reference: ESL Section 3.2
    """

    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_params: int,
    ) -> float:
        """
        Calculate adjusted R².

        Args:
            y_true: True values
            y_pred: Predicted values
            n_params: Number of parameters (excluding intercept)

        Returns:
            Adjusted R² value
        """
        n = len(y_true)

        # Calculate R²
        r2 = r2_score(y_true, y_pred)

        # Adjusted R²
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - n_params - 1)

        return adj_r2


class MallowCpCalculator:
    """
    Mallow's Cp.

    Mallow's Cp is used for model selection in regression.
    It compares the precision of a subset model to a full model.

    Cp = (RSS_p / σ²) - n + 2p

    Where:
    - RSS_p = residual sum of squares for subset model
    - σ² = estimate of variance from full model
    - n = sample size
    - p = number of parameters in subset model

    Good models have Cp ≈ p.

    Reference: ESL Section 3.3
    """

    @staticmethod
    def calculate(
        rss_subset: float,
        rss_full: float,
        n_params_subset: int,
        n_params_full: int,
        n_samples: int,
    ) -> tuple[float, float]:
        """
        Calculate Mallow's Cp.

        Args:
            rss_subset: RSS of subset model
            rss_full: RSS of full model
            n_params_subset: Number of parameters in subset model
            n_params_full: Number of parameters in full model
            n_samples: Sample size

        Returns:
            (Cp value, p value for comparison)
        """
        # Estimate σ² from full model
        sigma_squared = rss_full / (n_samples - n_params_full)

        # Calculate Cp
        cp = (rss_subset / sigma_squared) - n_samples + 2 * n_params_subset

        return cp, float(n_params_subset)


class GCVCalculator:
    """
    Generalized Cross-Validation.

    GCV is a rotation-invariant version of cross-validation.
    It's computationally efficient for smoothing splines.

    GCV = (1/n) * Σ(y_i - f̂_i)² / (1 - tr(S)/n)²

    Where:
    - S = smoothing matrix (hat matrix)
    - tr(S) = effective degrees of freedom

    For linear models: GCV ≈ (n * RSS) / (n - p)²

    Reference: ESL Section 5.4
    """

    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_params: int,
    ) -> float:
        """
        Calculate GCV.

        Args:
            y_true: True values
            y_pred: Predicted values
            n_params: Number of parameters

        Returns:
            GCV value
        """
        n = len(y_true)

        # Calculate RSS
        residuals = y_true - y_pred
        rss = np.sum(residuals**2)

        # GCV approximation for linear models
        gcv = (n * rss) / ((n - n_params) ** 2)

        return gcv


class ModelSelector:
    """
    Comprehensive model selection using multiple criteria.

    This class implements ESL-recommended model selection procedures,
    comparing models based on:
    1. AIC
    2. BIC
    3. Adjusted R²
    4. Cross-validation score
    5. Mallow's Cp
    6. GCV
    """

    def __init__(
        self,
        cv_folds: int = 5,
        random_state: int = 42,
    ):
        """
        Initialize model selector.

        Args:
            cv_folds: Number of CV folds
            random_state: Random seed
        """
        self.cv_folds = cv_folds
        self.random_state = random_state

    def evaluate_model(
        self,
        model: BaseEstimator,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        model_name: str,
    ) -> ModelCriterionResult:
        """
        Evaluate model using all criteria.

        Args:
            model: Fitted or unfitted model
            X: Feature matrix
            y: Target vector
            model_name: Name of the model

        Returns:
            ModelCriterionResult with all criteria
        """
        X_array = check_array(X)
        y_array = check_array(y, ensure_2d=False)

        n_samples, n_features = X_array.shape

        # Fit model if not already fitted
        try:
            check_is_fitted(model)
            model_fitted = model
        except Exception:
            model_fitted = clone(model)
            model_fitted.fit(X_array, y_array)

        # Predictions
        y_pred = model_fitted.predict(X_array)

        # Calculate metrics
        mse = mean_squared_error(y_array, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_array, y_pred)

        # Number of parameters (including intercept)
        # For most sklearn models: n_features + intercept
        if hasattr(model_fitted, "coef_"):
            n_params = np.sum(model_fitted.coef_ != 0) + 1  # non-zero coef + intercept
        else:
            n_params = n_features + 1

        # Adjusted R²
        adj_r2 = AdjustedR2Calculator.calculate(y_array, y_pred, n_params)

        # AIC
        aic = AICCalculator.calculate(y_array, y_pred, n_params)

        # BIC
        bic = BICCalculator.calculate(y_array, y_pred, n_params)

        # GCV
        gcv = GCVCalculator.calculate(y_array, y_pred, n_params)

        # CV score
        try:
            cv_scores = cross_val_score(
                model_fitted,
                X_array,
                y_array,
                cv=self.cv_folds,
                scoring="neg_mean_squared_error",
            )
            cv_rmse = np.sqrt(-np.mean(cv_scores))
        except Exception as e:
            logger.warning(f"CV failed for {model_name}: {e}")
            cv_rmse = None

        # Estimate log-likelihood (assuming normal errors)
        residuals = y_array - y_pred
        sigma_squared = np.sum(residuals**2) / n_samples
        log_likelihood = -0.5 * n_samples * (np.log(2 * np.pi * sigma_squared) + 1)

        result = ModelCriterionResult(
            timestamp=datetime.now(),
            model_name=model_name,
            criterion_type=CriterionType.BIC,  # Default
            criterion_value=bic,
            n_params=n_params,
            n_samples=n_samples,
            mse=mse,
            rmse=rmse,
            r2=r2,
            adjusted_r2=adj_r2,
            log_likelihood=log_likelihood,
            aic=aic,
            bic=bic,
            details={
                "gcv": gcv,
                "cv_rmse": cv_rmse,
            },
        )

        logger.info(
            f"Model {model_name}: AIC={aic:.2f}, BIC={bic:.2f}, AdjR²={adj_r2:.4f}, RMSE={rmse:.4f}"
        )

        return result

    def compare_models(
        self,
        models: dict[str, BaseEstimator],
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
    ) -> ModelComparisonResult:
        """
        Compare multiple models using all criteria.

        Args:
            models: Dictionary mapping model names to model objects
            X: Feature matrix
            y: Target vector

        Returns:
            ModelComparisonResult with comparison
        """
        results = []

        for model_name, model in models.items():
            try:
                result = self.evaluate_model(model, X, y, model_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate {model_name}: {e}")
                continue

        if not results:
            raise ValueError("No models could be evaluated")

        # Rank models by each criterion
        # Lower is better for AIC, BIC; higher is better for AdjR²
        results.sort(key=lambda r: r.aic)
        for i, r in enumerate(results):
            if r.details.get("rank_aic") is None:
                r.details["rank_aic"] = i + 1

        results.sort(key=lambda r: r.bic)
        for i, r in enumerate(results):
            r.details["rank_bic"] = i + 1

        results.sort(key=lambda r: r.adjusted_r2, reverse=True)
        for i, r in enumerate(results):
            r.details["rank_adj_r2"] = i + 1

        # Find best models
        best_aic = min(results, key=lambda r: r.aic)
        best_bic = min(results, key=lambda r: r.bic)
        best_adj_r2 = max(results, key=lambda r: r.adjusted_r2)

        best_model_by_aic = best_aic.model_name
        best_model_by_bic = best_bic.model_name
        best_model_by_adjusted_r2 = best_adj_r2.model_name

        # CV best (if available)
        cv_results = [r for r in results if r.details.get("cv_rmse") is not None]
        if cv_results:
            best_cv = min(cv_results, key=lambda r: r.details["cv_rmse"])
            best_model_by_cv = best_cv.model_name
        else:
            best_model_by_cv = None

        # Create comparison table
        comparison_data = {
            "Model": [r.model_name for r in results],
            "Params": [r.n_params for r in results],
            "R²": [r.r2 for r in results],
            "Adj_R²": [r.adjusted_r2 for r in results],
            "RMSE": [r.rmse for r in results],
            "AIC": [r.aic for r in results],
            "BIC": [r.bic for r in results],
            "Rank_AIC": [r.details.get("rank_aic", 0) for r in results],
            "Rank_BIC": [r.details.get("rank_bic", 0) for r in results],
            "Rank_AdjR²": [r.details.get("rank_adj_r2", 0) for r in results],
        }

        comparison_table = pd.DataFrame(comparison_data)

        return ModelComparisonResult(
            timestamp=datetime.now(),
            models=results,
            best_model_by_aic=best_model_by_aic,
            best_model_by_bic=best_model_by_bic,
            best_model_by_adjusted_r2=best_model_by_adjusted_r2,
            best_model_by_cv=best_model_by_cv,
            comparison_table=comparison_table,
        )

    def select_best_model(
        self,
        models: dict[str, BaseEstimator],
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        criterion: str = "bic",
    ) -> tuple[str, BaseEstimator, ModelCriterionResult]:
        """
        Select best model by criterion.

        Args:
            models: Dictionary mapping model names to model objects
            X: Feature matrix
            y: Target vector
            criterion: Selection criterion ('aic', 'bic', 'adjusted_r2')

        Returns:
            (best_model_name, best_model, result)
        """
        comparison = self.compare_models(models, X, y)

        if criterion == "aic":
            best_name = comparison.best_model_by_aic
        elif criterion == "bic":
            best_name = comparison.best_model_by_bic
        elif criterion == "adjusted_r2":
            best_name = comparison.best_model_by_adjusted_r2
        else:
            raise ValueError(f"Unknown criterion: {criterion}")

        best_result = next(r for r in comparison.models if r.model_name == best_name)
        best_model = clone(models[best_name])
        best_model.fit(X, y)

        logger.info(f"Best model by {criterion}: {best_name}")

        return best_name, best_model, best_result

    def compute_information_criteria(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_params: int,
    ) -> dict[str, float]:
        """
        Compute all information criteria.

        Args:
            y_true: True values
            y_pred: Predicted values
            n_params: Number of parameters

        Returns:
            Dictionary with all criteria
        """
        return {
            "aic": AICCalculator.calculate(y_true, y_pred, n_params),
            "bic": BICCalculator.calculate(y_true, y_pred, n_params),
            "adjusted_r2": AdjustedR2Calculator.calculate(y_true, y_pred, n_params),
            "gcv": GCVCalculator.calculate(y_true, y_pred, n_params),
            "r2": r2_score(y_true, y_pred),
            "mse": mean_squared_error(y_true, y_pred),
        }


def select_model_by_aic(
    models: dict[str, BaseEstimator],
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
) -> tuple[str, BaseEstimator, ModelCriterionResult]:
    """
    Select model by AIC.

    Args:
        models: Dictionary mapping model names to model objects
        X: Feature matrix
        y: Target vector

    Returns:
        (best_model_name, best_model, result)
    """
    selector = ModelSelector()
    return selector.select_best_model(models, X, y, criterion="aic")


def select_model_by_bic(
    models: dict[str, BaseEstimator],
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
) -> tuple[str, BaseEstimator, ModelCriterionResult]:
    """
    Select model by BIC.

    Args:
        models: Dictionary mapping model names to model objects
        X: Feature matrix
        y: Target vector

    Returns:
        (best_model_name, best_model, result)
    """
    selector = ModelSelector()
    return selector.select_best_model(models, X, y, criterion="bic")


def compute_criteria(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_params: int,
) -> dict[str, float]:
    """
    Compute all model selection criteria.

    Args:
        y_true: True values
        y_pred: Predicted values
        n_params: Number of parameters

    Returns:
        Dictionary with all criteria

    Example:
        >>> y_pred = model.predict(X_test)
        >>> criteria = compute_criteria(y_test, y_pred, n_params=5)
        >>> print(f"AIC: {criteria['aic']:.2f}")
        >>> print(f"BIC: {criteria['bic']:.2f}")
    """
    selector = ModelSelector()
    return selector.compute_information_criteria(y_true, y_pred, n_params)
