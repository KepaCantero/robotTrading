"""
Fama-French Factor Models Domain Service

Implements Fama-French 3-factor and Carhart 4-factor models
for analyzing returns and constructing factor portfolios.

Reference: Rule 43-papers-fama-french-carhart-factors.md
Papers:
- Fama, E.F., & French, K.R. (1993). "Common risk factors in stock returns"
- Carhart, M.M. (1997). "On persistence in mutual fund performance"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
from scipy import stats

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class FactorReturns:
    """Returns for a single factor model period."""

    market_return: float  # Rm - Rf (Market excess return)
    smb_return: float  # Small Minus Big
    hml_return: float  # High Minus Low
    umd_return: float = 0.0  # Up Minus Down (momentum, for 4-factor)
    risk_free_rate: float = 0.0  # Risk-free rate

    @property
    def three_factor(self) -> np.ndarray:
        """Get 3-factor returns as array."""
        return np.array(
            [
                self.market_return,
                self.smb_return,
                self.hml_return,
            ]
        )

    @property
    def four_factor(self) -> np.ndarray:
        """Get 4-factor returns as array."""
        return np.array(
            [
                self.market_return,
                self.smb_return,
                self.hml_return,
                self.umd_return,
            ]
        )


@dataclass
class FactorLoadings:
    """Factor loadings (sensitivities) for an asset or portfolio."""

    market_beta: float  # Market beta
    smb_beta: float  # Size beta
    hml_beta: float  # Value beta
    umd_beta: float = 0.0  # Momentum beta (4-factor)
    alpha: float = 0.0  # Alpha (excess return not explained by factors)

    def predict_return(self, factor_returns: FactorReturns) -> float:
        """
        Predict return using factor loadings.

        R = α + β_mkt * R_mkt + β_smb * SMB + β_hml * HML + β_umd * UMD

        Args:
            factor_returns: Factor returns for prediction period

        Returns:
            Predicted excess return
        """
        predicted = (
            self.alpha
            + self.market_beta * factor_returns.market_return
            + self.smb_beta * factor_returns.smb_return
            + self.hml_beta * factor_returns.hml_return
            + self.umd_beta * factor_returns.umd_return
        )
        return predicted


@dataclass
class FactorModelResult:
    """Result of factor model regression."""

    loadings: FactorLoadings  # Factor betas
    r_squared: float  # R-squared (fit quality)
    p_values: Dict[str, float]  # Statistical significance
    t_stats: Dict[str, float]  # T-statistics
    standard_errors: Dict[str, float]  # Standard errors
    n_obs: int  # Number of observations
    p_value_significance_threshold: float = 0.1  # Configured threshold for alpha significance

    @property
    def is_market_beta_significant(self) -> bool:
        """Check if market beta is statistically significant (p < 0.05)."""
        try:
            config = get_config()
            significance_threshold = float(
                getattr(config.trading, 'p_value_significance_threshold', 0.05)
            )
        except Exception:
            significance_threshold = 0.05
        return self.p_values.get("market", 1.0) < significance_threshold

    @property
    def has_positive_alpha(self) -> bool:
        """Check if alpha is positive and significant."""
        return (
            self.loadings.alpha > 0
            and self.p_values.get("alpha", 1.0) < self.p_value_significance_threshold
        )


class FamaFrenchModel:
    """
    Fama-French factor model calculator.

    Implements 3-factor and 4-factor models:
    - 3-Factor: Market (Rm-Rf), Size (SMB), Value (HML)
    - 4-Factor: + Momentum (UMD)

    This is a pure domain service that can be used with any data source.

    Reference: Fama & French (1993), Carhart (1997)
    """

    def __init__(
        self,
        model_type: str = "3factor",  # 3factor or 4factor
        risk_free_rate: float | None = None,
    ):
        """
        Initialize Fama-French model.

        Args:
            model_type: Factor model type
            risk_free_rate: Annual risk-free rate
        """
        self._model_type = model_type

        # Get risk-free rate from config if not provided
        if risk_free_rate is None:
            try:
                config = get_config()
                risk_free_rate = float(getattr(config.trading, 'risk_free_rate', 0.02))
            except Exception:
                risk_free_rate = 0.02
        self._risk_free_rate = risk_free_rate

        # Load trading thresholds from config
        trading_config = get_config()
        self._tt = trading_config.trading_thresholds

    def estimate_loadings(
        self,
        asset_returns: np.ndarray,  # Excess returns (R - Rf)
        factor_returns: FactorReturns,
    ) -> FactorModelResult:
        """
        Estimate factor loadings via OLS regression.

        R_i - R_f = α + β_mkt * (R_m - R_f) + β_smb * SMB + β_hml * HML + ε

        Args:
            asset_returns: Asset excess returns (T periods)
            factor_returns: Factor returns for each period

        Returns:
            FactorModelResult with estimated loadings
        """
        # Input validation - check array length
        if len(asset_returns) < 2:
            logger.warning(
                "Insufficient observations for factor model estimation (need at least 2)"
            )
            # Return default result
            n_params = 4 if self._model_type == "3factor" else 5
            factor_names = ["alpha", "market", "smb", "hml"] + (
                ["umd"] if self._model_type == "4factor" else []
            )
            return FactorModelResult(
                loadings=FactorLoadings(
                    market_beta=1.0,
                    smb_beta=0.0,
                    hml_beta=0.0,
                    umd_beta=0.0,
                    alpha=0.0,
                ),
                r_squared=0.0,
                p_values=dict.fromkeys(factor_names, 1.0),
                t_stats=dict.fromkeys(factor_names, 0.0),
                standard_errors=dict.fromkeys(factor_names, 1.0),
                n_obs=len(asset_returns),
                p_value_significance_threshold=self._tt.p_value_significance,
            )

        # Handle NaN values in asset returns
        valid_mask = ~np.isnan(asset_returns) & ~np.isinf(asset_returns)
        asset_returns_clean = asset_returns[valid_mask]

        if len(asset_returns_clean) < 2:
            logger.warning("Insufficient valid observations after filtering NaN/inf")
            n_params = 4 if self._model_type == "3factor" else 5
            factor_names = ["alpha", "market", "smb", "hml"] + (
                ["umd"] if self._model_type == "4factor" else []
            )
            return FactorModelResult(
                loadings=FactorLoadings(
                    market_beta=1.0,
                    smb_beta=0.0,
                    hml_beta=0.0,
                    umd_beta=0.0,
                    alpha=0.0,
                ),
                r_squared=0.0,
                p_values=dict.fromkeys(factor_names, 1.0),
                t_stats=dict.fromkeys(factor_names, 0.0),
                standard_errors=dict.fromkeys(factor_names, 1.0),
                n_obs=len(asset_returns_clean),
                p_value_significance_threshold=self._tt.p_value_significance,
            )

        # Log if we filtered values
        if len(asset_returns_clean) < len(asset_returns):
            n_filtered = len(asset_returns) - len(asset_returns_clean)
            logger.warning(f"Filtered out {n_filtered} NaN/inf values from asset_returns")

        # Validate factor returns
        if not all(
            np.isfinite(
                [
                    factor_returns.market_return,
                    factor_returns.smb_return,
                    factor_returns.hml_return,
                    factor_returns.umd_return,
                ]
            )
        ):
            logger.warning("Factor returns contain NaN or inf values")
            # Replace with zeros
            factor_returns = FactorReturns(
                market_return=np.nan_to_num(factor_returns.market_return),
                smb_return=np.nan_to_num(factor_returns.smb_return),
                hml_return=np.nan_to_num(factor_returns.hml_return),
                umd_return=np.nan_to_num(factor_returns.umd_return),
                risk_free_rate=np.nan_to_num(factor_returns.risk_free_rate),
            )

        # Build factor matrix
        if self._model_type == "4factor":
            X = np.column_stack(
                [
                    np.ones(len(asset_returns_clean)),  # Intercept (alpha)
                    factor_returns.market_return,
                    factor_returns.smb_return,
                    factor_returns.hml_return,
                    factor_returns.umd_return,
                ]
            )
            factor_names = ["alpha", "market", "smb", "hml", "umd"]
        else:  # 3factor
            X = np.column_stack(
                [
                    np.ones(len(asset_returns_clean)),
                    factor_returns.market_return,
                    factor_returns.smb_return,
                    factor_returns.hml_return,
                ]
            )
            factor_names = ["alpha", "market", "smb", "hml"]

        # Add constant to factor returns for intercept
        y = asset_returns_clean

        # OLS regression
        # Note: scipy linregress doesn't support multiple regression directly
        # Use numpy's lstsq for proper multivariate regression

        # Proper multivariate regression
        betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)

        # Calculate residuals
        residuals = y - X @ betas
        n_obs = len(y)
        n_params = len(betas)

        # R-squared
        ss_tot: float = float(np.sum((y - np.mean(y)) ** 2))
        ss_res: float = float(np.sum(residuals**2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0

        # Standard errors (simplified)
        mse = ss_res / (n_obs - n_params) if n_obs > n_params else 0
        if n_obs > n_params:
            try:
                var_covar = mse * np.linalg.inv(X.T @ X)
                std_errors = np.sqrt(np.diag(var_covar))
            except np.linalg.LinAlgError:
                logger.warning("Singular matrix in variance-covariance calculation")
                std_errors = np.ones(n_params)
        else:
            std_errors = np.ones(n_params)

        # T-statistics (handle division by zero)
        t_stats = np.divide(betas, std_errors, out=np.zeros_like(betas), where=std_errors != 0)

        # P-values (two-tailed)
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n_obs - n_params))

        # Build result dictionaries
        p_dict = dict(zip(factor_names, p_values))
        t_dict = dict(zip(factor_names, t_stats))
        se_dict = dict(zip(factor_names, std_errors))

        # Create loadings
        if self._model_type == "4factor":
            loadings = FactorLoadings(
                market_beta=float(betas[1]),
                smb_beta=float(betas[2]),
                hml_beta=float(betas[3]),
                umd_beta=float(betas[4]),
                alpha=float(betas[0]),
            )
        else:
            loadings = FactorLoadings(
                market_beta=float(betas[1]),
                smb_beta=float(betas[2]),
                hml_beta=float(betas[3]),
                umd_beta=0.0,
                alpha=float(betas[0]),
            )

        return FactorModelResult(
            loadings=loadings,
            r_squared=float(r_squared),
            p_values=p_dict,
            t_stats=t_dict,
            standard_errors=se_dict,
            n_obs=n_obs,
            p_value_significance_threshold=self._tt.p_value_significance,
        )

    def construct_factor_portfolio(
        self,
        factor_returns: pd.DataFrame,  # Columns: Rm-Rf, SMB, HML, UMD
        target_factor: str = "hml",  # Factor to target
        long_leg: bool = True,  # Long or short the factor
    ) -> Dict[str, float]:
        """
        Construct a pure factor portfolio.

        Creates a portfolio that loads primarily on a single factor.

        Args:
            factor_returns: Historical factor returns
            target_factor: Factor to target (smb, hml, umd)
            long_leg: Whether to go long (True) or short (False) the factor

        Returns:
            Dictionary of asset -> weight
        """
        # This is a simplified implementation
        # In practice, you'd regress asset returns on factors and select
        # assets with high loadings on the target factor

        # Placeholder: equal weight to top quintile of factor exposure
        n_assets = 50  # Assuming 50 assets
        weights: Dict[str, float] = {}

        if long_leg:
            # Long top 20% of assets by factor loading
            n_selected = max(1, n_assets // 5)
            1.0 / n_selected
            # In practice, select assets based on actual factor loadings
        else:
            # Short top 20% (or long bottom 20%)
            n_selected = max(1, n_assets // 5)
            -1.0 / n_selected

        return weights

    def calculate_expected_return(
        self,
        loadings: FactorLoadings,
        factor_returns: FactorReturns,
    ) -> float:
        """
        Calculate expected return using factor model.

        Args:
            loadings: Factor loadings
            factor_returns: Expected factor returns

        Returns:
            Expected excess return
        """
        return loadings.predict_return(factor_returns)


@dataclass
class FactorTiming:
    """Factor timing signals based on macro indicators."""

    market_timing_score: float  # -1 to 1 (bearish to bullish)
    size_timing_score: float  # -1 to 1 (large cap to small cap)
    value_timing_score: float  # -1 to 1 (growth to value)

    @property
    def recommend_momentum(self) -> bool:
        """Check if momentum factors are favored."""
        return self.market_timing_score > 0.3

    @property
    def recommend_value(self) -> bool:
        """Check if value factors are favored."""
        return self.value_timing_score > 0.3

    @property
    def recommend_small_cap(self) -> bool:
        """Check if small cap is favored."""
        return self.size_timing_score > 0.3
