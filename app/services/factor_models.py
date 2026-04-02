"""
Ernest Chan - Quantitative Trading: Factor Models Implementation

This module implements factor-based trading strategies as described in Ernest Chan's
"Quantitative Trading: How to Build Your Own Algorithmic Trading Business".

Key Concepts:
- Fama-French multi-factor models (Fama-French 3-factor, 5-factor)
- APT (Arbitrage Pricing Theory) implementation
- Factor exposure calculation and analysis
- Statistical arbitrage using factor models
- Risk management using factor-neutral portfolios

Author: Algorithmic Trading System
Date: 2026-01-28
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class FactorReturns:
    """Container for factor returns."""

    market_return: float
    smb_return: float  # Small Minus Big
    hml_return: float  # High Minus Low
    rmw_return: float  # Robust Minus Weak (5-factor)
    cma_return: float  # Conservative Minus Aggressive (5-factor)
    momentum_return: float  # Momentum factor (Carhart)


@dataclass
class FactorLoadings:
    """Container for asset factor loadings (betas)."""

    beta_market: float
    beta_smb: float
    beta_hml: float
    beta_rmw: float = 0.0
    beta_cma: float = 0.0
    beta_momentum: float = 0.0


@dataclass
class FactorModelResult:
    """Result of factor model regression."""

    asset_id: str
    factor_loadings: FactorLoadings
    r_squared: float
    p_values: dict[str, float]
    specific_return: float  # Idiosyncratic return
    expected_return: float
    factor_contribution: dict[str, float]


class FamaFrenchFactorModel:
    """
    Fama-French Factor Model Implementation.

    Implements the Fama-French multi-factor models:
    - 3-Factor Model: Market, SMB (Size), HML (Value)
    - 5-Factor Model: Adds RMW (Profitability), CMA (Investment)
    - Carhart 4-Factor: Adds Momentum

    Based on:
    - Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds.
    - Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model.
    - Carhart, M. M. (1997). On persistence in mutual fund performance.

    Usage:
        >>> model = FamaFrenchFactorModel()
        >>> result = model.fit(asset_returns, factor_returns)
        >>> print(result.factor_loadings)
    """

    def __init__(self, model_type: str = "three_factor"):
        """
        Initialize Fama-French factor model.

        Args:
            model_type: Type of factor model ('three_factor', 'five_factor', 'carhart')
        """
        self.model_type = model_type
        self.fitted = False
        self.last_result: FactorModelResult | None = None

        logger.info(f"FamaFrenchFactorModel initialized: model_type={model_type}")

    def fit(
        self,
        asset_returns: pd.Series,
        market_returns: pd.Series,
        smb_returns: pd.Series,
        hml_returns: pd.Series,
        rmw_returns: pd.Series | None = None,
        cma_returns: pd.Series | None = None,
        momentum_returns: pd.Series | None = None,
        risk_free_rate: float = 0.0,
    ) -> FactorModelResult:
        """
        Fit Fama-French factor model to asset returns.

        Args:
            asset_returns: Series of asset excess returns
            market_returns: Series of market excess returns (Rm - Rf)
            smb_returns: Series of Small Minus Big factor returns
            hml_returns: Series of High Minus Low factor returns
            rmw_returns: Series of Robust Minus Weak factor returns (5-factor)
            cma_returns: Series of Conservative Minus Aggressive returns (5-factor)
            momentum_returns: Series of momentum factor returns (Carhart)
            risk_free_rate: Risk-free rate (annualized)

        Returns:
            FactorModelResult with loadings and statistics
        """
        try:
            # Align data
            data = pd.DataFrame(
                {
                    "asset": asset_returns,
                    "market": market_returns,
                    "smb": smb_returns,
                    "hml": hml_returns,
                }
            )

            # Add optional factors based on model type
            if self.model_type == "five_factor":
                if rmw_returns is None or cma_returns is None:
                    raise ValueError("rmw_returns and cma_returns required for 5-factor model")
                data["rmw"] = rmw_returns
                data["cma"] = cma_returns

            elif self.model_type == "carhart":
                if momentum_returns is None:
                    raise ValueError("momentum_returns required for Carhart model")
                data["momentum"] = momentum_returns

            # Drop NaN values
            data = data.dropna()

            if len(data) < 30:  # Need at least 30 observations
                raise ValueError(f"Insufficient data: {len(data)} observations")

            # Prepare regression data
            y = data["asset"].values
            X = data[["market", "smb", "hml"]].values

            if self.model_type == "five_factor":
                X = data[["market", "smb", "hml", "rmw", "cma"]].values
            elif self.model_type == "carhart":
                X = data[["market", "smb", "hml", "momentum"]].values

            # Add constant
            X = np.column_stack([np.ones(len(X)), X])

            # OLS regression
            result = self._ols_regression(y, X)

            # Extract factor loadings
            factor_loadings = FactorLoadings(
                beta_market=float(result[1]),
                beta_smb=float(result[2]),
                beta_hml=float(result[3]),
                beta_rmw=float(result[4]) if self.model_type == "five_factor" else 0.0,
                beta_cma=float(result[5]) if self.model_type == "five_factor" else 0.0,
                beta_momentum=float(result[4]) if self.model_type == "carhart" else 0.0,
            )

            # Calculate R-squared
            y_pred = X @ result
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Calculate p-values
            p_values = self._calculate_p_values(y, X, result)

            # Calculate factor contributions
            factor_names = ["alpha", "market", "smb", "hml"]
            if self.model_type == "five_factor":
                factor_names.extend(["rmw", "cma"])
            elif self.model_type == "carhart":
                factor_names.append("momentum")

            factor_contribution = {}
            expected_return = result[0]  # Alpha

            for i, name in enumerate(factor_names[1:], start=1):
                contrib = result[i] * data[factor_names[i]].mean()
                factor_contribution[name] = float(contrib)
                expected_return += contrib

            # Create result
            model_result = FactorModelResult(
                asset_id="unknown",
                factor_loadings=factor_loadings,
                r_squared=float(r_squared),
                p_values=p_values,
                specific_return=float(result[0]),  # Alpha as specific return
                expected_return=float(expected_return),
                factor_contribution=factor_contribution,
            )

            self.last_result = model_result
            self.fitted = True

            logger.info(
                f"Fama-French model fitted: R²={r_squared:.4f}, "
                f"beta_market={factor_loadings.beta_market:.4f}"
            )

            return model_result

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error fitting Fama-French model: {e}")
            raise

    def _ols_regression(self, y: np.ndarray, X: np.ndarray) -> np.ndarray:
        """
        Perform OLS regression using normal equations.

        Args:
            y: Dependent variable
            X: Independent variables (with constant)

        Returns:
            Coefficient vector
        """
        # Normal equation: beta = (X'X)^(-1)X'y
        XtX = X.T @ X
        Xty = X.T @ y

        try:
            beta = np.linalg.solve(XtX, Xty)
            return beta
        except np.linalg.LinAlgError:
            # Use pseudo-inverse if singular
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            return beta

    def _calculate_p_values(
        self, y: np.ndarray, X: np.ndarray, beta: np.ndarray
    ) -> dict[str, float]:
        """
        Calculate p-values for regression coefficients.

        Args:
            y: Dependent variable
            X: Independent variables
            beta: Coefficients

        Returns:
            Dict of p-values
        """
        n, k = X.shape

        # Residuals
        residuals = y - X @ beta

        # Standard error of residuals
        sse = np.sum(residuals**2)
        sigma2 = sse / (n - k)

        # Standard errors of coefficients
        XtX_inv = np.linalg.inv(X.T @ X)
        se_beta = np.sqrt(np.diag(XtX_inv) * sigma2)

        # t-statistics
        t_stats = beta / se_beta

        # p-values (two-tailed)
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=n - k))

        factor_names = ["alpha", "market", "smb", "hml"]
        if self.model_type == "five_factor":
            factor_names.extend(["rmw", "cma"])
        elif self.model_type == "carhart":
            factor_names.append("momentum")

        return {name: float(p) for name, p in zip(factor_names, p_values)}

    def predict(
        self,
        factor_returns: FactorReturns,
    ) -> float:
        """
        Predict asset return using fitted factor model.

        Args:
            factor_returns: Factor returns for prediction period

        Returns:
            Predicted excess return
        """
        if not self.fitted or self.last_result is None:
            raise ValueError("Model must be fitted before prediction")

        loadings = self.last_result.factor_loadings

        predicted_return = (
            loadings.beta_market * factor_returns.market_return
            + loadings.beta_smb * factor_returns.smb_return
            + loadings.beta_hml * factor_returns.hml_return
            + loadings.beta_rmw * factor_returns.rmw_return
            + loadings.beta_cma * factor_returns.cma_return
            + loadings.beta_momentum * factor_returns.momentum_return
            + self.last_result.specific_return  # Add alpha
        )

        return predicted_return


class APTModel:
    """
    Arbitrage Pricing Theory (APT) Implementation.

    APT is a multi-factor model that assumes asset returns are driven by
    multiple macroeconomic factors. Unlike CAPM, APT does not specify
    the factors but assumes they exist.

    Based on:
    - Ross, S. A. (1976). The arbitrage theory of capital asset pricing.

    Implementation uses statistical factor extraction (PCA) to identify
    the most important factors driving returns.

    Usage:
        >>> apt = APTModel(n_factors=5)
        >>> apt.fit(returns_matrix)
        >>> loadings = apt.get_factor_loadings()
    """

    def __init__(self, n_factors: int = 5):
        """
        Initialize APT model.

        Args:
            n_factors: Number of statistical factors to extract
        """
        self.n_factors = n_factors
        self.fitted = False
        self.factor_loadings: np.ndarray | None = None
        self.factor_returns: np.ndarray | None = None
        self.eigenvalues: np.ndarray | None = None

        logger.info(f"APTModel initialized: n_factors={n_factors}")

    def fit(self, returns: pd.DataFrame) -> APTModel:
        """
        Fit APT model using PCA to extract statistical factors.

        Args:
            returns: DataFrame of asset returns (assets in columns, time in rows)

        Returns:
            Self for method chaining
        """
        try:
            # Handle missing values
            returns_clean = returns.dropna()

            if len(returns_clean) < self.n_factors + 10:
                raise ValueError(
                    f"Insufficient data: {len(returns_clean)} observations "
                    f"for {self.n_factors} factors"
                )

            # Standardize returns
            returns_standardized = (returns_clean - returns_clean.mean()) / returns_clean.std()

            # PCA to extract factors
            cov_matrix = returns_standardized.cov()
            eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

            # Sort by eigenvalue (descending)
            idx = np.argsort(eigenvalues)[::-1]
            self.eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]

            # Select top n_factors
            self.factor_loadings = eigenvectors[:, : self.n_factors]

            # Calculate factor returns (scores)
            self.factor_returns = returns_standardized.values @ self.factor_loadings

            self.fitted = True

            # Calculate explained variance
            explained_var = self.eigenvalues[: self.n_factors].sum() / self.eigenvalues.sum()

            logger.info(
                f"APT model fitted: {self.n_factors} factors explain "
                f"{explained_var:.2%} of variance"
            )

            return self

        except (ValueError, TypeError, np.linalg.LinAlgError) as e:
            logger.error(f"Error fitting APT model: {e}")
            raise

    def get_factor_loadings(self) -> pd.DataFrame:
        """
        Get factor loadings for all assets.

        Returns:
            DataFrame with factor loadings (assets x factors)
        """
        if not self.fitted or self.factor_loadings is None:
            raise ValueError("Model must be fitted first")

        return pd.DataFrame(
            self.factor_loadings,
            columns=[f"factor_{i + 1}" for i in range(self.n_factors)],
        )

    def get_factor_returns(self) -> pd.DataFrame:
        """
        Get historical factor returns.

        Returns:
            DataFrame with factor returns over time
        """
        if not self.fitted or self.factor_returns is None:
            raise ValueError("Model must be fitted first")

        return pd.DataFrame(
            self.factor_returns,
            columns=[f"factor_{i + 1}" for i in range(self.n_factors)],
        )

    def get_explained_variance_ratio(self) -> np.ndarray:
        """
        Get proportion of variance explained by each factor.

        Returns:
            Array of explained variance ratios
        """
        if self.eigenvalues is None:
            raise ValueError("Model must be fitted first")

        total_var = self.eigenvalues.sum()
        return self.eigenvalues[: self.n_factors] / total_var

    def predict_portfolio_risk(self, weights: np.ndarray) -> float:
        """
        Predict portfolio risk using APT factor model.

        Args:
            weights: Portfolio weights

        Returns:
            Predicted portfolio volatility (annualized)
        """
        if not self.fitted or self.factor_loadings is None:
            raise ValueError("Model must be fitted first")

        # Portfolio factor loadings
        portfolio_factor_loadings = weights @ self.factor_loadings

        # Factor covariance matrix
        factor_cov = (
            np.cov(self.factor_returns.T)
            if self.factor_returns is not None
            else np.eye(self.n_factors)
        )

        # Portfolio variance from factors
        portfolio_var = portfolio_factor_loadings @ factor_cov @ portfolio_factor_loadings.T

        return float(np.sqrt(portfolio_var))


class StatisticalArbitrage:
    """
    Statistical Arbitrage using Factor Models.

    Implements factor-neutral statistical arbitrage strategies as described
    by Ernest Chan. The strategy identifies mispriced securities based on
    their factor exposures and trades the convergence.

    Key Concepts:
    - Residual return (alpha) from factor model
    - Z-score of residual for entry/exit signals
    - Factor-neutral portfolio construction
    - Risk management using factor exposure limits

    Usage:
        >>> arb = StatisticalArbitrage(factor_model)
        >>> signals = arb.generate_signals(returns, factor_returns)
    """

    def __init__(
        self,
        factor_model: FamaFrenchFactorModel,
        z_score_threshold: float = 2.0,
        lookback_period: int = 20,
    ):
        """
        Initialize statistical arbitrage strategy.

        Args:
            factor_model: Fitted Fama-French factor model
            z_score_threshold: Z-score threshold for entry signals
            lookback_period: Lookback period for residual calculation
        """
        self.factor_model = factor_model
        self.z_score_threshold = z_score_threshold
        self.lookback_period = lookback_period

        logger.info(
            f"StatisticalArbitrage initialized: z_threshold={z_score_threshold}, "
            f"lookback={lookback_period}"
        )

    def calculate_residuals(
        self,
        asset_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> pd.Series:
        """
        Calculate residual returns (alpha) from factor model.

        Args:
            asset_returns: Asset returns
            factor_returns: DataFrame with factor returns columns

        Returns:
            Series of residual returns
        """
        if not self.factor_model.fitted:
            raise ValueError("Factor model must be fitted")

        # Calculate expected return from factors
        loadings = self.factor_model.last_result.factor_loadings

        expected_return = (
            loadings.beta_market * factor_returns.get("market", 0)
            + loadings.beta_smb * factor_returns.get("smb", 0)
            + loadings.beta_hml * factor_returns.get("hml", 0)
        )

        # Residual = actual - expected
        residual = asset_returns - expected_return

        return residual

    def generate_signals(
        self,
        asset_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> pd.Series:
        """
        Generate trading signals based on residual z-scores.

        Args:
            asset_returns: Asset returns
            factor_returns: DataFrame with factor returns

        Returns:
            Series of trading signals (+1 for long, -1 for short, 0 for neutral)
        """
        # Calculate residuals
        residuals = self.calculate_residuals(asset_returns, factor_returns)

        # Calculate rolling z-score
        rolling_mean = residuals.rolling(self.lookback_period).mean()
        rolling_std = residuals.rolling(self.lookback_period).std()
        z_scores = (residuals - rolling_mean) / rolling_std

        # Generate signals
        signals = pd.Series(0, index=z_scores.index)
        signals[z_scores > self.z_score_threshold] = -1  # Short when overvalued
        signals[z_scores < -self.z_score_threshold] = 1  # Long when undervalued

        return signals

    def construct_factor_neutral_portfolio(
        self,
        asset_returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
        signals: pd.DataFrame | None = None,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """
        Construct factor-neutral portfolio from multiple assets.

        Args:
            asset_returns: DataFrame of asset returns
            factor_returns: DataFrame of factor returns
            signals: Optional pre-computed signals

        Returns:
            Tuple of (portfolio_weights, portfolio_metrics)
        """
        n_assets = asset_returns.shape[1]

        if signals is None:
            signals = pd.DataFrame(0, index=asset_returns.index, columns=asset_returns.columns)

        # Fit factor model for each asset
        factor_loadings_list = []
        for asset in asset_returns.columns:
            self.factor_model.fit(
                asset_returns[asset],
                factor_returns.get("market", 0),
                factor_returns.get("smb", 0),
                factor_returns.get("hml", 0),
            )
            factor_loadings_list.append(
                [
                    self.factor_model.last_result.factor_loadings.beta_market,
                    self.factor_model.last_result.factor_loadings.beta_smb,
                    self.factor_model.last_result.factor_loadings.beta_hml,
                ]
            )

        factor_loadings_matrix = np.array(factor_loadings_list)

        # Solve for weights that neutralize factor exposure
        # Constraints: sum(w) = 1, factor_loadings.T @ w = 0
        n_factors = factor_loadings_matrix.shape[1]

        # Set up optimization
        from scipy.optimize import minimize

        def objective(weights):
            # Minimize portfolio variance
            portfolio_returns = asset_returns @ weights
            return portfolio_returns.var()

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},  # Fully invested
        ]

        # Factor neutral constraints
        for i in range(n_factors):
            constraints.append(
                {
                    "type": "eq",
                    "fun": lambda w, factor_idx=i: w @ factor_loadings_matrix[:, factor_idx],
                }
            )

        bounds = [(0.1, 0.5) for _ in range(n_assets)]  # Reasonable bounds

        initial_weights = np.ones(n_assets) / n_assets

        result = minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            logger.warning(f"Portfolio optimization failed: {result.message}")
            weights = initial_weights
        else:
            weights = result.x

        # Calculate portfolio metrics
        portfolio_return = (asset_returns * weights).sum(axis=1)
        metrics = {
            "expected_return": float(portfolio_return.mean() * 252),
            "volatility": float(portfolio_return.std() * np.sqrt(252)),
            "sharpe_ratio": float(portfolio_return.mean() / portfolio_return.std() * np.sqrt(252)),
            "factor_neutrality": float(np.max(np.abs(factor_loadings_matrix.T @ weights))),
        }

        return weights, metrics


def calculate_factor_exposure(
    asset_returns: pd.Series,
    factor_returns: pd.DataFrame,
) -> pd.Series:
    """
    Calculate factor exposure (betas) for an asset.

    Args:
        asset_returns: Asset returns
        factor_returns: Factor returns (each column is a factor)

    Returns:
        Series of factor betas
    """
    # Align data
    data = pd.concat([asset_returns, factor_returns], axis=1).dropna()

    y = data.iloc[:, 0].values
    X = data.iloc[:, 1:].values
    X = np.column_stack([np.ones(len(X)), X])  # Add constant

    # OLS regression
    beta = np.linalg.lstsq(X, y, rcond=None)[0]

    return pd.Series(beta[1:], index=factor_returns.columns)


def create_factor_portfolio(
    returns: pd.DataFrame,
    n_factors: int = 10,
    method: str = "pca",
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Create factor-mimicking portfolio from returns.

    Args:
        returns: Asset returns
        n_factors: Number of factors to extract
        method: Method for factor extraction ('pca' or 'ica')

    Returns:
        Tuple of (factor_returns, portfolio_weights)
    """
    from sklearn.decomposition import PCA, FastICA

    # Standardize
    returns_standardized = (returns - returns.mean()) / returns.std()

    # Extract factors
    if method == "pca":
        model = PCA(n_components=n_factors)
    elif method == "ica":
        model = FastICA(n_components=n_factors, random_state=42)
    else:
        raise ValueError(f"Unknown method: {method}")

    factor_returns = model.fit_transform(returns_standardized)
    portfolio_weights = model.components_.T

    return pd.DataFrame(factor_returns, index=returns.index), portfolio_weights


def get_factor_model(model_type: str = "fama_french", **kwargs):
    """
    Factory function to get factor model instance.

    This function provides a convenient way to instantiate factor models
    without directly importing and calling the class constructors.

    Args:
        model_type: Type of factor model to create. Options:
            - "fama_french" or "ff": FamaFrenchFactorModel
            - "apt": APTModel
        **kwargs: Additional arguments passed to the model constructor

    Returns:
        Instance of the requested factor model

    Raises:
        ValueError: If model_type is unknown

    Examples:
        >>> # Get Fama-French 3-factor model (default)
        >>> model = get_factor_model("fama_french", ff_model_type="three_factor")
        >>> result = model.fit(asset_returns, market_returns, smb_returns, hml_returns)

        >>> # Get Fama-French 5-factor model
        >>> model = get_factor_model("fama_french", ff_model_type="five_factor")

        >>> # Get APT model with 5 factors
        >>> apt = get_factor_model("apt", n_factors=5)
        >>> apt.fit(returns_matrix)

    """
    model_type_lower = model_type.lower().replace("-", "_")

    if model_type_lower in ("fama_french", "ff", "fama-french"):
        # Extract ff_model_type parameter if provided for FamaFrenchFactorModel
        ff_model_type = kwargs.pop("ff_model_type", "three_factor")
        return FamaFrenchFactorModel(model_type=ff_model_type, **kwargs)

    elif model_type_lower == "apt":
        # Extract n_factors parameter if provided for APTModel
        n_factors = kwargs.pop("n_factors", 5)
        return APTModel(n_factors=n_factors, **kwargs)

    else:
        available_models = ["fama_french", "apt"]
        raise ValueError(
            f"Unknown model type: '{model_type}'. Available models: {available_models}"
        )
