"""
Black-Litterman Portfolio Optimization

Implements the Black-Litterman model for combining investor views
with market equilibrium returns.

Reference: Rule 48-papers-markowitz (Related methods)
Paper: Black, F., & Litterman, R. (1992). "Global Portfolio Optimization"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from app.domain.services.portfolio_optimization.mean_variance_optimizer import (
    MeanVarianceOptimizer,
    OptimizationResult,
)


@dataclass
class View:
    """Investor view on asset returns."""

    symbols: List[str]  # Assets involved in view
    pick: np.ndarray  # View weights (sums to 0 for relative views)
    confidence: float  # View confidence (0-1)
    expected_return: float  # Expected return of view


@dataclass
class BlackLittermanResult:
    """Result of Black-Litterman optimization."""

    equilibrium_returns: np.ndarray  # Implied equilibrium returns
    blended_returns: np.ndarray  # BL blended returns
    weights: np.ndarray  # Optimal weights
    symbols: List[str]  # Asset symbols
    view_adjustment: np.ndarray  # Adjustment from views

    # Optimization metrics
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    converged: bool

    @property
    def weights_dict(self) -> Dict[str, float]:
        """Get weights as dictionary."""
        return {symbol: float(w) for symbol, w in zip(self.symbols, self.weights)}


class BlackLittermanOptimizer:
    """
    Black-Litterman portfolio optimizer.

    The Black-Litterman model:
    1. Computes implied equilibrium returns from market cap weights
    2. Combines with investor views using Bayes' rule
    3. Optimizes using blended returns

    This addresses two key issues with MVO:
    - Estimation error in expected returns
    - Concentration of weights

    Reference: Black, F., & Litterman, R. (1992)
    """

    def __init__(
        self,
        risk_aversion: float = 3.0,
        risk_free_rate: float = 0.02,
        tau: float = 0.05,  # Uncertainty scaling parameter
    ):
        """
        Initialize Black-Litterman optimizer.

        Args:
            risk_aversion: Risk aversion parameter
            risk_free_rate: Risk-free rate
            tau: Scaling parameter for uncertainty in prior
        """
        self._risk_aversion = risk_aversion
        self._risk_free_rate = risk_free_rate
        self._tau = tau

    def optimize(
        self,
        cov_matrix: np.ndarray,
        market_cap_weights: Optional[np.ndarray] = None,
        views: Optional[List[View]] = None,
        symbols: Optional[List[str]] = None,
    ) -> BlackLittermanResult:
        """
        Compute Black-Litterman optimal portfolio.

        Args:
            cov_matrix: Covariance matrix
            market_cap_weights: Market capitalization weights (None = equal weight)
            views: List of investor views (None = no views)
            symbols: Asset symbols

        Returns:
            BlackLittermanResult with optimal weights
        """
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Default market weights (equal weight if not provided)
        if market_cap_weights is None:
            market_cap_weights = np.ones(n_assets) / n_assets

        # Step 1: Calculate implied equilibrium returns
        implied_returns = self._calculate_implied_returns(
            cov_matrix,
            market_cap_weights,
        )

        # Step 2: Combine with views
        if views is None or len(views) == 0:
            # No views - use equilibrium returns
            bl_returns = implied_returns
            view_adjustment = np.zeros(n_assets)
        else:
            bl_returns, view_adjustment = self._combine_with_views(
                cov_matrix,
                implied_returns,
                views,
                symbols,
            )

        # Step 3: Optimize with blended returns
        result = self._optimize_with_returns(
            cov_matrix,
            bl_returns,
            symbols,
        )

        return BlackLittermanResult(
            equilibrium_returns=implied_returns,
            blended_returns=bl_returns,
            weights=result.weights,
            symbols=symbols,
            view_adjustment=view_adjustment,
            expected_return=result.expected_return,
            expected_risk=result.expected_risk,
            sharpe_ratio=result.sharpe_ratio,
            converged=result.converged,
        )

    def _calculate_implied_returns(
        self,
        cov_matrix: np.ndarray,
        market_weights: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate implied equilibrium returns from market weights.

        π = λ * Σ * w_market

        Where λ = (E[R_p] - R_f) / σ_p²
        For simplicity, we assume market is efficient: π = δ * Σ * w

        Args:
            cov_matrix: Covariance matrix
            market_weights: Market capitalization weights

        Returns:
            Implied equilibrium returns (daily)
        """
        # Excess equilibrium returns
        implied_returns = self._risk_aversion * (cov_matrix @ market_weights)

        return implied_returns

    def _combine_with_views(
        self,
        cov_matrix: np.ndarray,
        implied_returns: np.ndarray,
        views: List[View],
        symbols: List[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Combine equilibrium returns with investor views.

        Uses Black-Litterman formula:
        μ_BL = [(τΣ)^(-1) + P'Ω(-1)P](-1) * [(τΣ)^(-1)π + P'Ω(-1)Q]

        Where:
        - P: Pick matrix (maps views to assets)
        - Q: View returns
        - Ω: View uncertainty matrix

        Args:
            cov_matrix: Covariance matrix
            implied_returns: Implied equilibrium returns
            views: List of investor views
            symbols: Asset symbols

        Returns:
            Tuple of (blended_returns, view_adjustment)
        """
        n_assets = len(symbols)
        n_views = len(views)

        # Build pick matrix P
        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        omega = np.zeros((n_views, n_views))

        for i, view in enumerate(views):
            # Get indices for symbols in view
            indices = [symbols.index(s) for s in view.symbols if s in symbols]

            # Set pick matrix
            for idx, symbol_idx in enumerate(indices):
                P[i, symbol_idx] = view.pick[idx]

            # Expected return of view
            Q[i] = view.expected_return / 252  # Convert annual to daily

            # View uncertainty (inverse of confidence squared)
            # Higher confidence = lower uncertainty
            omega[i, i] = (1.0 - view.confidence) / view.confidence if view.confidence > 0 else 1.0

        # Scale covariance matrix
        tau_sigma = self._tau * cov_matrix

        # Black-Litterman formula components
        M1 = np.linalg.inv(tau_sigma)
        M2 = P.T @ np.linalg.inv(omega) @ P

        # Combined precision matrix
        M_combined = M1 + M2

        # Combined expected returns
        R1 = M1 @ implied_returns
        R2 = P.T @ np.linalg.inv(omega) @ Q
        R_combined = R1 + R2

        # Solve for blended returns
        bl_returns = np.linalg.inv(M_combined) @ R_combined

        # Calculate view adjustment
        view_adjustment = bl_returns - implied_returns

        return bl_returns, view_adjustment

    def _optimize_with_returns(
        self,
        cov_matrix: np.ndarray,
        expected_returns: np.ndarray,
        symbols: List[str],
    ) -> OptimizationResult:
        """
        Optimize using expected returns.

        Args:
            cov_matrix: Covariance matrix
            expected_returns: Expected returns (daily)
            symbols: Asset symbols

        Returns:
            OptimizationResult
        """
        n_assets = len(symbols)

        # Use MVO to maximize Sharpe
        mvo = MeanVarianceOptimizer(
            risk_free_rate=self._risk_free_rate,
            min_weight=0.0,
            max_weight=1.0,
            allow_short=False,
        )

        # Convert daily returns to annual for MVO
        annual_returns = expected_returns * 252

        # Create covariance result (dummy means for now)
        from app.domain.services.portfolio_optimization.covariance_calculator import (
            CovarianceResult,
        )
        from app.domain.services.portfolio_optimization.mean_variance_optimizer import (
            OptimizationResult as MvoResult,
        )

        # Direct optimization
        def objective(weights: np.ndarray) -> float:
            portfolio_return = float(weights @ annual_returns)
            portfolio_var = float(weights @ cov_matrix @ weights)
            portfolio_std = np.sqrt(portfolio_var)

            # Annualize
            annual_return = portfolio_return * 252
            annual_std = portfolio_std * np.sqrt(252)

            sharpe = (annual_return - self._risk_free_rate) / annual_std
            return -sharpe

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]
        bounds = [(0.0, 1.0) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        weights = result.x if result.success else x0
        expected_return = float(weights @ annual_returns)
        expected_var = float(weights @ cov_matrix @ weights)
        expected_risk = np.sqrt(expected_var) * np.sqrt(252)
        sharpe = (expected_return - self._risk_free_rate) / expected_risk

        return MvoResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe,
            symbols=symbols,
            converged=result.success,
            message=result.message,
        )


def create_relative_view(
    symbols: List[str],
    outperform: str,
    underperform: str,
    confidence: float,
    expected_alpha: float,
) -> View:
    """
    Create a relative outperformance view.

    Args:
        symbols: All symbols in universe
        outperform: Symbol expected to outperform
        underperform: Symbol expected to underperform
        confidence: View confidence (0-1)
        expected_alpha: Expected excess return (annual)

    Returns:
        View object
    """
    pick = np.zeros(len(symbols))
    pick[symbols.index(outperform)] = 1.0
    pick[symbols.index(underperform)] = -1.0

    return View(
        symbols=[outperform, underperform],
        pick=pick[[symbols.index(outperform), symbols.index(underperform)]],
        confidence=confidence,
        expected_return=expected_alpha,
    )
