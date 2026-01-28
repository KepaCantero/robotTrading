"""
Risk Parity Portfolio Optimization

Implements Risk Parity and related allocation methods that equalize
risk contribution across assets.

Reference: Rule 48-papers-markowitz (Related methods)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import minimize


@dataclass
class RiskParityResult:
    """Result of Risk Parity optimization."""

    weights: np.ndarray  # Risk parity weights
    risk_contributions: np.ndarray  # Risk contribution of each asset
    risk_budget: np.ndarray  # Target risk budget (usually equal)
    symbols: List[str]  # Asset symbols
    converged: bool  # Whether optimization converged

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}

    @property
    def risk_parity_error(self) -> float:
        """Get error in risk parity (std dev of risk contributions)."""
        return float(np.std(self.risk_contributions))


class RiskParityOptimizer:
    """
    Risk Parity portfolio optimizer.

    Risk Parity allocates weights such that each asset contributes
    equal risk to the portfolio:

    RC_i = w_i * (Σw)_i / σ_p = constant

    Methods:
    - Risk Parity (equal risk contribution)
    - Inverse Volatility
    - Equal Weight (benchmark)
    - Diversified Risk Parity

    Reference:
    - Qian, E., & Maas, K. (2010). "Risk Parity Portfolios"
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ):
        """
        Initialize Risk Parity optimizer.

        Args:
            risk_free_rate: Risk-free rate
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
        """
        self._risk_free_rate = risk_free_rate
        self._min_weight = min_weight
        self._max_weight = max_weight

    def optimize(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
        risk_budget: Optional[np.ndarray] = None,
    ) -> RiskParityResult:
        """
        Compute Risk Parity weights.

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols
            risk_budget: Target risk budget (None = equal risk)

        Returns:
            RiskParityResult with optimal weights
        """
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Default to equal risk budget
        if risk_budget is None:
            risk_budget = np.ones(n_assets) / n_assets

        # Initial guess (inverse volatility)
        inv_vol = 1.0 / np.sqrt(np.diag(cov_matrix))
        x0 = inv_vol / inv_vol.sum()

        # Objective: minimize sum of squared differences from risk budget
        def objective(weights: np.ndarray) -> float:
            # Calculate risk contributions
            portfolio_var = weights @ cov_matrix @ weights
            portfolio_std = np.sqrt(portfolio_var)

            if portfolio_std == 0:
                return 1e6

            marginal_contrib = cov_matrix @ weights
            contrib = weights * marginal_contrib / portfolio_std

            # Normalize to sum to 1
            contrib = contrib / contrib.sum()

            # Squared error from risk budget
            return float(np.sum((contrib - risk_budget) ** 2))

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9},
        )

        weights = result.x if result.success else x0

        # Calculate final risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=risk_budget,
            symbols=symbols,
            converged=result.success,
        )

    def inverse_volatility(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
    ) -> RiskParityResult:
        """
        Compute inverse volatility weights (simple risk parity).

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols

        Returns:
            RiskParityResult with inverse volatility weights
        """
        volatilities = np.sqrt(np.diag(cov_matrix))
        inv_vol = 1.0 / volatilities
        weights = inv_vol / inv_vol.sum()

        n_assets = len(volatilities)
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Calculate risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=np.ones(n_assets) / n_assets,
            symbols=symbols,
            converged=True,
        )

    def equal_weight(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
    ) -> RiskParityResult:
        """
        Compute equal weights (benchmark).

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols

        Returns:
            RiskParityResult with equal weights
        """
        n_assets = cov_matrix.shape[0]
        weights = np.ones(n_assets) / n_assets
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Calculate risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=np.ones(n_assets) / n_assets,
            symbols=symbols,
            converged=True,
        )

    def diversified_risk_parity(
        self,
        cov_matrix: np.ndarray,
        symbols: Optional[List[str]] = None,
        kappa: float = 1.0,
    ) -> RiskParityResult:
        """
        Compute Diversified Risk Parity weights.

        Adds diversification term to objective function.

        Args:
            cov_matrix: Covariance matrix
            symbols: Asset symbols
            kappa: Diversification parameter

        Returns:
            RiskParityResult with DRP weights
        """
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Risk budget (equal)
        risk_budget = np.ones(n_assets) / n_assets

        # Initial guess
        inv_vol = 1.0 / np.sqrt(np.diag(cov_matrix))
        x0 = inv_vol / inv_vol.sum()

        def objective(weights: np.ndarray) -> float:
            # Risk parity term
            portfolio_var = weights @ cov_matrix @ weights
            portfolio_std = np.sqrt(portfolio_var)
            marginal_contrib = cov_matrix @ weights
            contrib = weights * marginal_contrib / portfolio_std
            contrib = contrib / contrib.sum()

            rp_term = np.sum((contrib - risk_budget) ** 2)

            # Diversification term (negative entropy)
            div_term = -kappa * np.sum(weights * np.log(weights + 1e-10))

            return rp_term + div_term

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        # Bounds
        bounds = [(self._min_weight, self._max_weight) for _ in range(n_assets)]

        # Optimize
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        weights = result.x if result.success else x0

        # Calculate risk contributions
        portfolio_var = weights @ cov_matrix @ weights
        portfolio_std = np.sqrt(portfolio_var)
        marginal_contrib = cov_matrix @ weights
        risk_contributions = weights * marginal_contrib / portfolio_std

        return RiskParityResult(
            weights=weights,
            risk_contributions=risk_contributions,
            risk_budget=risk_budget,
            symbols=symbols,
            converged=result.success,
        )

    def get_diversification_ratio(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> float:
        """
        Calculate diversification ratio.

        DR = (Σ w_i σ_i) / σ_p

        Where DR > 1 indicates diversification benefit.

        Args:
            weights: Portfolio weights
            cov_matrix: Covariance matrix

        Returns:
            Diversification ratio
        """
        # Weighted average volatility
        volatilities = np.sqrt(np.diag(cov_matrix))
        avg_vol = float(weights @ volatilities)

        # Portfolio volatility
        portfolio_vol = float(np.sqrt(weights @ cov_matrix @ weights))

        if portfolio_vol == 0:
            return 1.0

        return avg_vol / portfolio_vol


def cluster_based_risk_parity(
    cov_matrix: np.ndarray,
    cluster_labels: np.ndarray,
    symbols: Optional[List[str]] = None,
) -> np.ndarray:
    """
    Compute Cluster-Based Risk Parity (CBRP) weights.

    Combines clustering with risk parity:
    1. Allocate to clusters using risk parity
    2. Allocate within clusters using risk parity

    Args:
        cov_matrix: Covariance matrix
        cluster_labels: Cluster assignment for each asset
        symbols: Asset symbols

    Returns:
        CBRP weights
    """
    n_assets = cov_matrix.shape[0]
    symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

    unique_clusters = np.unique(cluster_labels)
    n_clusters = len(unique_clusters)

    final_weights = np.zeros(n_assets)

    # Calculate cluster covariances and weights
    cluster_variances = {}

    for cluster_id in unique_clusters:
        indices = np.where(cluster_labels == cluster_id)[0]

        if len(indices) == 1:
            # Single asset cluster
            cluster_weights = np.array([1.0])
        else:
            # Inverse volatility within cluster
            cluster_cov = cov_matrix[np.ix_(indices, indices)]
            cluster_vols = np.sqrt(np.diag(cluster_cov))
            cluster_weights = 1.0 / cluster_vols
            cluster_weights = cluster_weights / cluster_weights.sum()

        # Calculate cluster variance
        cluster_cov = cov_matrix[np.ix_(indices, indices)]
        cluster_var = float(cluster_weights @ cluster_cov @ cluster_weights)
        cluster_variances[cluster_id] = cluster_var

        # Store intra-cluster weights
        final_weights[indices] = cluster_weights

    # Allocate across clusters (inverse variance)
    inv_var = np.array([1.0 / cluster_variances[c] for c in unique_clusters])
    cluster_allocation = inv_var / inv_var.sum()

    # Combine intra and inter cluster weights
    for i, cluster_id in enumerate(unique_clusters):
        indices = np.where(cluster_labels == cluster_id)[0]
        final_weights[indices] *= cluster_allocation[i]

    return final_weights
