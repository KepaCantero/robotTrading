"""
Factor Models - Fama-French 5-Factor + Momentum Implementation

This module implements the Fama-French factor models:
1. Fama-French 3-Factor: Market, Size, Value
2. Fama-French 5-Factor: Market, Size, Value, Profitability, Investment
3. Carhart 4-Factor: FF3 + Momentum
4. FF5 + Momentum: Complete 6-factor model

Reference papers:
- Fama & French (1993): "Common risk factors in the returns on stocks and bonds"
- Fama & French (2015): "A five-factor asset pricing model"
- Carhart (1997): "On persistence in mutual fund performance"

SOLID Principles:
- Single Responsibility: Only factor model implementations
- Open/Closed: Extensible with new factor models
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .factor_calculator import FactorCalculator
from .models import FactorScores

logger = logging.getLogger(__name__)


@dataclass
class FactorModelResult:
    """Result from factor model regression."""

    # Factor coefficients (betas)
    beta_market: Optional[float] = None
    beta_size: Optional[float] = None
    beta_value: Optional[float] = None
    beta_profitability: Optional[float] = None
    beta_investment: Optional[float] = None
    beta_momentum: Optional[float] = None

    # Model statistics
    alpha: Optional[float] = None  # Intercept (abnormal return)
    r_squared: Optional[float] = None  # Goodness of fit
    p_value: Optional[float] = None  # Overall significance
    standard_error: Optional[float] = None  # Residual standard error

    # Diagnostics
    residuals_mean: Optional[float] = None
    residuals_std: Optional[float] = None

    # Model info
    model_name: str = ""
    estimation_period: str = ""
    observations: int = 0


class BaseFactorModel:
    """Base class for factor models."""

    def __init__(self, name: str):
        """Initialize factor model.

        Args:
            name: Model name
        """
        self.name = name
        self.calculator = FactorCalculator()

    def _ols_regression(self, y: np.ndarray, X: np.ndarray) -> SimpleOLSResult:
        """Perform OLS regression using SimpleOLSResult."""
        return SimpleOLSResult(X, y)

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """
        Fit factor model to return series.

        Args:
            returns: Asset returns (T periods)
            factor_returns: Dictionary of factor returns (each T periods)

        Returns:
            FactorModelResult with coefficients and statistics
        """
        raise NotImplementedError("Subclasses must implement fit()")

    def predict(
        self,
        factor_returns: dict[str, np.ndarray],
        coefficients: dict[str, float],
        alpha: float = 0,
    ) -> np.ndarray:
        """
        Predict returns using factor model.

        Args:
            factor_returns: Factor returns for each period
            coefficients: Factor coefficients
            alpha: Intercept term

        Returns:
            Predicted returns
        """
        prediction = np.full(len(next(iter(factor_returns.values()))), alpha)

        for factor, returns in factor_returns.items():
            if factor in coefficients:
                prediction += coefficients[factor] * returns

        return prediction


class CAPMModel(BaseFactorModel):
    """
    Capital Asset Pricing Model (single-factor).

    R_i - R_f = β_MKT * (R_M - R_f)
    """

    def __init__(self):
        super().__init__("CAPM")

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """Fit CAPM model."""
        if "market" not in factor_returns:
            raise ValueError("CAPM requires market factor returns")

        market_returns = factor_returns["market"]

        # OLS regression: returns ~ market
        X = sm_add_constant(market_returns)
        model = self._ols_regression(returns, X)

        result = FactorModelResult(
            model_name=self.name,
            beta_market=model.params[1],
            alpha=model.params[0],
            r_squared=model.rsquared,
            p_value=model.f_pvalue,
            standard_error=np.sqrt(model.mse_resid),
            residuals_mean=float(np.mean(model.resid)),
            residuals_std=float(np.std(model.resid)),
            observations=len(returns),
        )

        return result


class FF3FactorModel(BaseFactorModel):
    """
    Fama-French 3-Factor Model.

    R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML

    Factors:
    - MKT: Market risk premium
    - SMB: Small Minus Big (size)
    - HML: High Minus Low (value)
    """

    def __init__(self):
        super().__init__("Fama-French 3-Factor")

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """Fit FF3 model."""
        required_factors = ["market", "size", "value"]
        for factor in required_factors:
            if factor not in factor_returns:
                raise ValueError(f"FF3 requires {factor} factor returns")

        # Build design matrix
        X = np.column_stack(
            [
                factor_returns["market"],
                factor_returns["size"],
                factor_returns["value"],
            ]
        )
        X = sm_add_constant(X)

        model = self._ols_regression(returns, X)

        result = FactorModelResult(
            model_name=self.name,
            beta_market=model.params[1],
            beta_size=model.params[2],
            beta_value=model.params[3],
            alpha=model.params[0],
            r_squared=model.rsquared,
            p_value=model.f_pvalue,
            standard_error=np.sqrt(model.mse_resid),
            residuals_mean=float(np.mean(model.resid)),
            residuals_std=float(np.std(model.resid)),
            observations=len(returns),
        )

        return result


class FF5FactorModel(BaseFactorModel):
    """
    Fama-French 5-Factor Model.

    R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_RMW * RMW + β_CMA * CMA

    Factors:
    - MKT: Market risk premium
    - SMB: Small Minus Big (size)
    - HML: High Minus Low (value)
    - RMW: Robust Minus Weak (profitability)
    - CMA: Conservative Minus Aggressive (investment)
    """

    def __init__(self):
        super().__init__("Fama-French 5-Factor")

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """Fit FF5 model."""
        required_factors = ["market", "size", "value", "profitability", "investment"]
        for factor in required_factors:
            if factor not in factor_returns:
                raise ValueError(f"FF5 requires {factor} factor returns")

        # Build design matrix
        X = np.column_stack(
            [
                factor_returns["market"],
                factor_returns["size"],
                factor_returns["value"],
                factor_returns["profitability"],
                factor_returns["investment"],
            ]
        )
        X = sm_add_constant(X)

        model = self._ols_regression(returns, X)

        result = FactorModelResult(
            model_name=self.name,
            beta_market=model.params[1],
            beta_size=model.params[2],
            beta_value=model.params[3],
            beta_profitability=model.params[4],
            beta_investment=model.params[5],
            alpha=model.params[0],
            r_squared=model.rsquared,
            p_value=model.f_pvalue,
            standard_error=np.sqrt(model.mse_resid),
            residuals_mean=float(np.mean(model.resid)),
            residuals_std=float(np.std(model.resid)),
            observations=len(returns),
        )

        return result


class Carhart4FactorModel(BaseFactorModel):
    """
    Carhart 4-Factor Model (FF3 + Momentum).

    R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_WML * WML

    Adds momentum factor to FF3.
    """

    def __init__(self):
        super().__init__("Carhart 4-Factor")

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """Fit Carhart 4-factor model."""
        required_factors = ["market", "size", "value", "momentum"]
        for factor in required_factors:
            if factor not in factor_returns:
                raise ValueError(f"Carhart requires {factor} factor returns")

        # Build design matrix
        X = np.column_stack(
            [
                factor_returns["market"],
                factor_returns["size"],
                factor_returns["value"],
                factor_returns["momentum"],
            ]
        )
        X = sm_add_constant(X)

        model = self._ols_regression(returns, X)

        result = FactorModelResult(
            model_name=self.name,
            beta_market=model.params[1],
            beta_size=model.params[2],
            beta_value=model.params[3],
            beta_momentum=model.params[4],
            alpha=model.params[0],
            r_squared=model.rsquared,
            p_value=model.f_pvalue,
            standard_error=np.sqrt(model.mse_resid),
            residuals_mean=float(np.mean(model.resid)),
            residuals_std=float(np.std(model.resid)),
            observations=len(returns),
        )

        return result


class FF6FactorModel(BaseFactorModel):
    """
    Complete 6-Factor Model (FF5 + Momentum).

    R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_RMW * RMW + β_CMA * CMA + β_WML * WML

    This is the complete model used in the multi-factor strategy.
    """

    def __init__(self):
        super().__init__("FF5 + Momentum (6-Factor)")

    def fit(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """Fit 6-factor model."""
        required_factors = ["market", "size", "value", "profitability", "investment", "momentum"]
        for factor in required_factors:
            if factor not in factor_returns:
                raise ValueError(f"6-factor model requires {factor} factor returns")

        # Build design matrix
        X = np.column_stack(
            [
                factor_returns["market"],
                factor_returns["size"],
                factor_returns["value"],
                factor_returns["profitability"],
                factor_returns["investment"],
                factor_returns["momentum"],
            ]
        )
        X = sm_add_constant(X)

        model = self._ols_regression(returns, X)

        result = FactorModelResult(
            model_name=self.name,
            beta_market=model.params[1],
            beta_size=model.params[2],
            beta_value=model.params[3],
            beta_profitability=model.params[4],
            beta_investment=model.params[5],
            beta_momentum=model.params[6],
            alpha=model.params[0],
            r_squared=model.rsquared,
            p_value=model.f_pvalue,
            standard_error=np.sqrt(model.mse_resid),
            residuals_mean=float(np.mean(model.resid)),
            residuals_std=float(np.std(model.resid)),
            observations=len(returns),
        )

        return result


def sm_add_constant(x: np.ndarray) -> np.ndarray:
    """Add constant column to design matrix (simple implementation)."""
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    return np.column_stack([np.ones(len(x)), x])


class SimpleOLSResult:
    """Simple OLS regression result."""

    def __init__(self, X: np.ndarray, y: np.ndarray):
        """Fit OLS using normal equations."""
        # beta = (X'X)^(-1) X'y
        self.X = X
        self.y = y

        XtX = X.T @ X
        Xty = X.T @ y

        try:
            self.params = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            # Use pseudoinverse if singular
            self.params = np.linalg.pinv(XtX) @ Xty

        # Predicted values
        self.fitted_values = X @ self.params

        # Residuals
        self.resid = y - self.fitted_values

        # R-squared
        ss_res: float = float(np.sum(self.resid**2))
        ss_tot: float = float(np.sum((y - np.mean(y)) ** 2))
        self.rsquared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # MSE
        self.mse_resid = ss_res / (len(y) - len(self.params))

        # F-statistic p-value (simplified)
        n = len(y)
        k = len(self.params)
        f_stat = (ss_tot - ss_res) / (k - 1) / (ss_res / (n - k))
        from scipy.stats import f

        self.f_pvalue = 1 - f.cdf(f_stat, k - 1, n - k)


class FactorModelManager:
    """
    Manager for factor model operations.

    Provides unified interface for fitting different factor models
    and analyzing factor exposures.
    """

    def __init__(self):
        """Initialize factor model manager."""
        self.models = {
            "capm": CAPMModel(),
            "ff3": FF3FactorModel(),
            "ff5": FF5FactorModel(),
            "carhart": Carhart4FactorModel(),
            "ff6": FF6FactorModel(),
        }

    def fit_model(
        self,
        model_name: str,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> FactorModelResult:
        """
        Fit a specific factor model.

        Args:
            model_name: Name of model to fit
            returns: Asset returns
            factor_returns: Factor returns

        Returns:
            FactorModelResult
        """
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(self.models.keys())}")

        model = self.models[model_name]
        return model.fit(returns, factor_returns)

    def compare_models(
        self,
        returns: np.ndarray,
        factor_returns: dict[str, np.ndarray],
    ) -> dict[str, FactorModelResult]:
        """
        Compare all applicable factor models.

        Args:
            returns: Asset returns
            factor_returns: Factor returns

        Returns:
            Dictionary of model results
        """
        results = {}

        # Determine which models can be fit
        available_factors = set(factor_returns.keys())

        # Check which models have all required factors
        model_requirements = {
            "capm": {"market"},
            "ff3": {"market", "size", "value"},
            "carhart": {"market", "size", "value", "momentum"},
            "ff5": {"market", "size", "value", "profitability", "investment"},
            "ff6": {"market", "size", "value", "profitability", "investment", "momentum"},
        }

        for model_name, requirements in model_requirements.items():
            if requirements.issubset(available_factors):
                try:
                    result = self.fit_model(model_name, returns, factor_returns)
                    results[model_name] = result
                except Exception as e:
                    logger.warning(f"Failed to fit {model_name}: {e}")

        return results

    def get_best_model(
        self,
        results: dict[str, FactorModelResult],
        metric: str = "r_squared",
    ) -> tuple[str, FactorModelResult]:
        """
        Get best model based on specified metric.

        Args:
            results: Dictionary of model results
            metric: Metric to compare ("r_squared", "p_value", "standard_error")

        Returns:
            Tuple of (model_name, result)
        """
        if not results:
            raise ValueError("No model results to compare")

        # For R-squared and p-value: higher is better
        # For standard error: lower is better
        higher_is_better = metric in ["r_squared", "p_value"]

        best_model = max(
            results.items(),
            key=lambda x: getattr(x[1], metric) if higher_is_better else -getattr(x[1], metric),
        )

        return best_model

    def calculate_factor_exposures_from_scores(
        self,
        factor_scores: FactorScores,
        method: str = "z_score",
    ) -> dict[str, float]:
        """
        Calculate factor exposures from factor scores.

        Args:
            factor_scores: Factor scores
            method: Method for calculating exposures ("z_score", "rank")

        Returns:
            Dictionary of factor exposures
        """
        exposures = {}

        if method == "z_score":
            # Use z-scores directly as exposures
            exposures = {
                "value": float(factor_scores.value_score or 0),
                "size": float(factor_scores.size_score or 0),
                "profitability": float(factor_scores.profitability_score or 0),
                "investment": float(factor_scores.investment_score or 0),
                "momentum": float(factor_scores.momentum_score or 0),
            }

        elif method == "rank":
            # Convert scores to percentiles (0-1)
            # Assuming standard normal, use CDF
            from scipy.stats import norm

            exposures = {
                "value": norm.cdf(float(factor_scores.value_score or 0)),
                "size": norm.cdf(float(factor_scores.size_score or 0)),
                "profitability": norm.cdf(float(factor_scores.profitability_score or 0)),
                "investment": norm.cdf(float(factor_scores.investment_score or 0)),
                "momentum": norm.cdf(float(factor_scores.momentum_score or 0)),
            }

        return exposures
