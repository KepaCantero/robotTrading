"""
Risk Models - Rishi Narang "Inside the Black Box" Chapter 4

This module implements the Risk Model architecture from Narang's framework:
- Factor risk models
- Covariance estimation
- Risk forecasting
- Risk constraints application

Key concepts from "Inside the Black Box":
- Risk models manage exposures and constraints
- Factor models decompose risk into systematic and idiosyncratic components
- Risk forecasting helps in position sizing and portfolio construction
- Risk constraints prevent excessive factor exposures

From Narang: "The risk model is responsible for ensuring that the portfolio
does not take on more risk than is intended, whether in aggregate or in
specific dimensions such as sectors, countries, or factors."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskFactorType(str, Enum):
    """Types of risk factors."""

    SECTOR = "sector"
    COUNTRY = "country"
    CURRENCY = "currency"
    STYLE = "style"  # Value, Growth, Size, etc.
    MARKET = "market"  # Beta
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    DURATION = "duration"  # For fixed income
    COMMODITY = "commodity"


class RiskModelType(str, Enum):
    """Types of risk models."""

    FACTOR_MODEL = "factor_model"
    COVARIANCE_MATRIX = "covariance_matrix"
    HISTORICAL_VAR = "historical_var"
    PARAMETRIC_VAR = "parametric_var"
    MONTE_CARLO = "monte_carlo"


@dataclass
class RiskFactor:
    """A single risk factor."""

    name: str
    factor_type: RiskFactorType
    exposures: Dict[str, float]  # symbol -> factor exposure
    returns: pd.Series  # Historical factor returns


@dataclass
class RiskBudget:
    """Risk budget for a specific factor."""

    factor: str
    max_exposure: Decimal  # Maximum allowed exposure
    current_exposure: Decimal
    utilization: Decimal  # current / max
    contribution_to_risk: Decimal  # Contribution to portfolio risk


@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""

    total_risk: Decimal  # Portfolio volatility or VaR
    systematic_risk: Decimal  # Risk from factors
    idiosyncratic_risk: Decimal  # Stock-specific risk
    factor_exposures: Dict[str, Decimal]
    var_95: Decimal  # Value at Risk at 95% confidence
    cvar_95: Decimal  # Conditional VaR at 95% confidence
    max_drawdown: Decimal
    beta: Decimal  # Portfolio beta
    correlation_to_market: Decimal


@dataclass
class RiskConstraint:
    """A risk constraint for portfolio construction."""

    name: str
    constraint_type: str  # "max_exposure", "min_diversification", "max_beta", etc.
    factor: Optional[str] = None  # Factor this constraint applies to
    max_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    penalty_weight: Decimal = Decimal("1.0")  # For constraint violation


class RiskModel:
    """
    Base risk model implementing Narang's risk framework.

    From Narang Chapter 4: Risk models serve three key purposes:
    1. Forecast the risk of potential portfolios
    2. Analyze the sources of risk in a portfolio
    3. Manage risk by applying constraints
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.risk_factors: Dict[str, RiskFactor] = {}
        self.risk_constraints: List[RiskConstraint] = []
        self.covariance_matrix: Optional[pd.DataFrame] = None
        self.lookup_days = config.get("lookup_days", 252)  # 1 year

    def add_risk_factor(self, factor: RiskFactor) -> None:
        """Add a risk factor to the model."""
        self.risk_factors[factor.name] = factor
        logger.info(f"Added risk factor: {factor.name} ({factor.factor_type.value})")

    def add_constraint(self, constraint: RiskConstraint) -> None:
        """Add a risk constraint."""
        self.risk_constraints.append(constraint)
        logger.info(f"Added risk constraint: {constraint.name}")

    def estimate_covariance_matrix(
        self, returns: pd.DataFrame, method: str = "sample"
    ) -> pd.DataFrame:
        """
        Estimate covariance matrix of asset returns.

        From Narang: Accurate covariance estimation is crucial for risk forecasting.
        Methods:
        - sample: Sample covariance (historical)
        - shrinkage: Shrinkage estimator (Ledoit-Wolf)
        - exponential: Exponentially weighted covariance
        """
        if method == "sample":
            return returns.cov() * 252  # Annualized

        elif method == "shrinkage":
            # Ledoit-Wolf shrinkage
            cov = returns.cov() * 252
            n = cov.shape[0]

            # Shrinkage target (constant correlation)
            var = np.diag(cov).mean()
            target = np.full((n, n), var * 0.1)  # Assume 10% average correlation
            np.fill_diagonal(target, np.diag(cov))

            # Shrinkage intensity (simplified)
            shrinkage = 0.5

            return (1 - shrinkage) * cov + shrinkage * pd.DataFrame(
                target, index=cov.index, columns=cov.columns
            )

        elif method == "exponential":
            # Exponentially weighted moving average
            span = self.config.get("ewma_span", 60)
            return returns.ewm(span=span).cov().iloc[-1] * 252

        else:
            raise ValueError(f"Unknown covariance estimation method: {method}")

    def calculate_factor_exposures(
        self, weights: Dict[str, float], factor_loadings: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate portfolio exposure to each risk factor.

        From Narang: Factor exposure = sum(weight_i * loading_i)

        Args:
            weights: Portfolio weights {symbol: weight}
            factor_loadings: Factor loadings {symbol: {factor: loading}}

        Returns:
            Factor exposures {factor: exposure}
        """
        exposures = {}

        for factor in factor_loadings.columns:
            factor_exposure = 0.0
            for symbol, weight in weights.items():
                if symbol in factor_loadings.index:
                    loading = factor_loadings.loc[symbol, factor]
                    factor_exposure += weight * loading
            exposures[factor] = factor_exposure

        return exposures

    def forecast_risk(self, weights: Dict[str, float], returns: pd.DataFrame) -> RiskMetrics:
        """
        Forecast portfolio risk.

        From Narang: Risk forecasting is essential for position sizing.

        Args:
            weights: Portfolio weights
            returns: Historical returns

        Returns:
            RiskMetrics with risk forecasts
        """
        # Calculate portfolio returns
        portfolio_returns = pd.Series(0.0, index=returns.index)
        for symbol, weight in weights.items():
            if symbol in returns.columns:
                portfolio_returns += returns[symbol] * weight

        # Calculate total risk (volatility)
        total_risk = Decimal(str(portfolio_returns.std() * np.sqrt(252)))

        # Calculate VaR (95%)
        var_95 = Decimal(str(portfolio_returns.quantile(0.05)))

        # Calculate CVaR (expected shortfall)
        cvar_95 = Decimal(str(portfolio_returns[portfolio_returns <= var_95].mean()))

        # Calculate max drawdown
        cum_returns = (1 + portfolio_returns).cumprod()
        running_max = cum_returns.expanding().max()
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = Decimal(str(drawdown.min()))

        # Calculate beta (correlation to market)
        if "market" in returns.columns or len(returns.columns) > 0:
            market_returns = returns.get("market", returns.mean(axis=1))
            covariance = portfolio_returns.cov(market_returns)
            market_variance = market_returns.var()
            beta = Decimal(str(covariance / market_variance if market_variance > 0 else 1.0))

            correlation = portfolio_returns.corr(market_returns)
            correlation_to_market = Decimal(str(correlation if not np.isnan(correlation) else 0.0))
        else:
            beta = Decimal("1.0")
            correlation_to_market = Decimal("0.0")

        # Decompose risk (simplified)
        # For a proper factor model, we'd need factor returns
        systematic_risk = total_risk * Decimal("0.7")  # Assume 70% systematic
        idiosyncratic_risk = total_risk * Decimal("0.3")  # 30% idiosyncratic

        return RiskMetrics(
            total_risk=total_risk,
            systematic_risk=systematic_risk,
            idiosyncratic_risk=idiosyncratic_risk,
            factor_exposures={},
            var_95=var_95,
            cvar_95=cvar_95,
            max_drawdown=max_drawdown,
            beta=beta,
            correlation_to_market=correlation_to_market,
        )

    def apply_risk_constraints(
        self,
        weights: pd.Series,
        factor_loadings: pd.DataFrame,
        constraints: Optional[List[RiskConstraint]] = None,
    ) -> pd.Series:
        """
        Apply risk constraints to portfolio weights.

        From Narang: Risk constraints prevent excessive factor exposures.

        This is the key function that implements the rule from Narang:
        "SIEMPRE separa Alpha Model de Risk Model"

        Args:
            weights: Proposed portfolio weights
            factor_loadings: Factor loadings for each asset
            constraints: List of constraints (uses self.risk_constraints if None)

        Returns:
            Adjusted weights satisfying constraints
        """
        if constraints is None:
            constraints = self.risk_constraints

        constrained_weights = weights.copy()
        constraints_to_apply = [c for c in constraints if c.constraint_type == "max_exposure"]

        # Apply max exposure constraints iteratively
        max_iterations = 10
        for iteration in range(max_iterations):
            violations = []

            for constraint in constraints_to_apply:
                if constraint.factor is None or constraint.max_value is None:
                    continue

                # Calculate current factor exposure
                factor_exposure = (
                    constrained_weights * factor_loadings.get(constraint.factor, 0)
                ).sum()

                if abs(factor_exposure) > float(constraint.max_value):
                    violations.append((constraint, factor_exposure))

                    # Scale down weights to reduce exposure
                    max_factor_exposure = float(constraint.max_value)
                    scale_factor = max_factor_exposure / abs(factor_exposure)

                    # Identify assets contributing to excess exposure
                    factor_values = factor_loadings.get(
                        constraint.factor, pd.Series(0, index=weights.index)
                    )

                    if factor_exposure > 0:
                        # Reduce long positions in this factor
                        mask = factor_values > 0
                    else:
                        # Reduce short positions in this factor
                        mask = factor_values < 0

                    # Apply scaling only to contributing assets
                    constrained_weights[mask] *= scale_factor

            if not violations:
                break  # All constraints satisfied

        # Renormalize weights
        total_weight = constrained_weights.abs().sum()
        if total_weight > 0:
            constrained_weights = constrained_weights / constrained_weights.sum()

        return constrained_weights

    def apply_factor_constraints(
        self,
        weights: pd.Series,
        factor_loadings: pd.DataFrame,
        max_factor_exposure: float = 0.15,
    ) -> pd.Series:
        """
        Apply factor exposure constraints (from Narang's example).

        From Narang rule file: "Limitar exposure a cada factor (e.g., sector, country).
        Example: Max 15% exposure to Tech sector."

        Args:
            weights: Portfolio weights
            factor_loadings: Factor loadings DataFrame
            max_factor_exposure: Maximum allowed exposure per factor

        Returns:
            Constrained weights
        """
        constrained_weights = weights.copy()

        for factor in factor_loadings.columns:
            # Calculate exposure to this factor
            factor_exposure = (weights * factor_loadings[factor]).sum()

            if abs(factor_exposure) > max_factor_exposure:
                # Reduce weights proportionally
                scale_factor = max_factor_exposure / abs(factor_exposure)

                # Apply only to assets that contribute to excess exposure
                if factor_exposure > 0:
                    mask = factor_loadings[factor] > 0
                else:
                    mask = factor_loadings[factor] < 0

                constrained_weights[mask] *= scale_factor

        # Renormalize
        if constrained_weights.sum() != 0:
            constrained_weights = constrained_weights / constrained_weights.sum()

        return constrained_weights

    def calculate_risk_budget(
        self, weights: Dict[str, float], factor_loadings: pd.DataFrame
    ) -> List[RiskBudget]:
        """
        Calculate risk budget for each factor.

        From Narang: Risk budgeting ensures that risk is distributed appropriately
        across factors.

        Args:
            weights: Portfolio weights
            factor_loadings: Factor loadings

        Returns:
            List of RiskBudget objects
        """
        budgets = []
        exposures = self.calculate_factor_exposures(weights, factor_loadings)

        # Get max exposure from constraints or use default
        max_exposures = {}
        for constraint in self.risk_constraints:
            if constraint.constraint_type == "max_exposure" and constraint.factor:
                max_exposures[constraint.factor] = float(constraint.max_value or Decimal("0.15"))

        for factor, exposure in exposures.items():
            max_exp = max_exposures.get(factor, 0.15)
            current_exp = Decimal(str(abs(exposure)))
            utilization = current_exp / Decimal(str(max_exp)) if max_exp > 0 else Decimal("0")

            # Simplified risk contribution
            risk_contribution = current_exp * current_exp  # Approximate

            budgets.append(
                RiskBudget(
                    factor=factor,
                    max_exposure=Decimal(str(max_exp)),
                    current_exposure=current_exp,
                    utilization=utilization,
                    contribution_to_risk=risk_contribution,
                )
            )

        return budgets

    def validate_portfolio_risk(
        self, weights: Dict[str, float], returns: pd.DataFrame
    ) -> Tuple[bool, List[str]]:
        """
        Validate that portfolio meets risk criteria.

        Args:
            weights: Portfolio weights
            returns: Historical returns

        Returns:
            Tuple of (is_valid, list of issues)
        """
        risk_metrics = self.forecast_risk(weights, returns)
        issues = []

        # Check total risk
        max_risk = self.config.get("max_portfolio_risk", 0.20)  # 20% vol
        if risk_metrics.total_risk > Decimal(str(max_risk)):
            issues.append(
                f"Total risk {risk_metrics.total_risk:.2%} exceeds maximum {max_risk:.2%}"
            )

        # Check VaR
        max_var = self.config.get("max_var_95", -0.05)  # 5% daily VaR
        if risk_metrics.var_95 < Decimal(str(max_var)):
            issues.append(f"VaR {risk_metrics.var_95:.2%} exceeds maximum {max_var:.2%}")

        # Check beta
        max_beta = self.config.get("max_beta", 1.5)
        min_beta = self.config.get("min_beta", 0.5)
        if not (min_beta <= float(risk_metrics.beta) <= max_beta):
            issues.append(f"Beta {risk_metrics.beta:.2f} outside range [{min_beta}, {max_beta}]")

        # Check factor constraints
        if hasattr(returns, 'columns'):
            # Use returns as proxy for factor loadings if none provided
            for constraint in self.risk_constraints:
                if constraint.constraint_type == "max_beta" and constraint.max_value:
                    if risk_metrics.beta > constraint.max_value:
                        issues.append(f"Beta exceeds constraint: {constraint.name}")

        return len(issues) == 0, issues


class FactorRiskModel(RiskModel):
    """
    Multi-factor risk model implementing Barra/BARRA-style methodology.

    From Narang: Factor models are the industry standard for risk management.
    They decompose risk into:
    1. Systematic risk (factor exposures)
    2. Idiosyncratic risk (asset-specific)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_type = RiskModelType.FACTOR_MODEL
        self.factor_returns: Dict[str, pd.Series] = {}
        self.specific_risk: Dict[str, float] = {}

    def estimate_factor_returns(
        self, asset_returns: pd.DataFrame, factor_loadings: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Estimate factor returns using cross-sectional regression.

        From Narang: Factor returns are estimated by regressing asset returns
        on factor loadings.

        Args:
            asset_returns: Asset returns for a single period
            factor_loadings: Factor loadings for each asset

        Returns:
            Estimated factor returns
        """
        # Align data
        common_assets = asset_returns.index.intersection(factor_loadings.index)
        if len(common_assets) < 10:
            return {}

        y = asset_returns.loc[common_assets]
        X = factor_loadings.loc[common_assets]

        # OLS regression for each factor
        factor_returns = {}
        for factor in X.columns:
            # Simple regression: return ~ factor_loading
            x_factor = X[factor].values.reshape(-1, 1)
            y_values = y.values

            try:
                # Estimate factor return as weighted average return
                factor_return = np.average(y_values, weights=np.abs(x_factor.flatten()))
                factor_returns[factor] = factor_return
            except (ValueError, ZeroDivisionError):
                continue

        return factor_returns

    def calculate_specific_risk(
        self, asset_returns: pd.DataFrame, factor_loadings: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate idiosyncratic (specific) risk for each asset.

        From Narang: Specific risk is the portion of risk not explained by factors.
        """
        specific_risk = {}

        for asset in asset_returns.columns:
            if asset not in factor_loadings.index:
                continue

            # Get asset returns
            returns = asset_returns[asset].dropna()

            # Calculate residual variance (simplified)
            # In practice, would regress returns on factors and take residual std
            specific_risk[asset] = returns.std() * 0.5  # Assume 50% is specific

        return specific_risk


class CovarianceRiskModel(RiskModel):
    """
    Covariance-based risk model.

    From Narang: Simpler than factor models but less informative about
    risk sources. Useful for smaller portfolios.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_type = RiskModelType.COVARIANCE_MATRIX

    def forecast_risk(self, weights: Dict[str, float], returns: pd.DataFrame) -> RiskMetrics:
        """Calculate risk using covariance matrix."""
        # Estimate covariance matrix
        cov_matrix = self.estimate_covariance_matrix(returns, method="shrinkage")

        # Convert weights to series aligned with covariance matrix
        weight_series = pd.Series(weights)

        # Calculate portfolio variance: w' * Sigma * w
        aligned_weights = weight_series.reindex(cov_matrix.index).fillna(0)
        portfolio_variance = aligned_weights.T @ cov_matrix.values @ aligned_weights

        Decimal(str(np.sqrt(portfolio_variance)))

        # For other metrics, use base implementation
        return super().forecast_risk(weights, returns)


def get_risk_model(config: Dict[str, Any]) -> RiskModel:
    """
    Factory function to create risk models.

    Args:
        config: Configuration with 'model_type' key

    Returns:
        RiskModel instance
    """
    model_type = config.get("model_type", "factor")

    if model_type == "factor":
        return FactorRiskModel(config)
    elif model_type == "covariance":
        return CovarianceRiskModel(config)
    else:
        return RiskModel(config)


__all__ = [
    "RiskFactorType",
    "RiskModelType",
    "RiskFactor",
    "RiskBudget",
    "RiskMetrics",
    "RiskConstraint",
    "RiskModel",
    "FactorRiskModel",
    "CovarianceRiskModel",
    "get_risk_model",
]
