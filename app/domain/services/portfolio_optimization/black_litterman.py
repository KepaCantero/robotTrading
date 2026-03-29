"""
Black-Litterman Portfolio Optimization

Implements the Black-Litterman model for combining investor views
with market equilibrium returns.

Reference: Rule 48-papers-markowitz (Related methods)
Paper: Black, F., & Litterman, R. (1992). "Global Portfolio Optimization"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from app.domain.services.portfolio_optimization._validation import (
    TRADING_DAYS,
    log_optimization_failure,
    validate_covariance_matrix,
)
from app.domain.services.portfolio_optimization.mean_variance_optimizer import OptimizationResult

logger = logging.getLogger(__name__)


# Black-Litterman default parameters
DEFAULT_RISK_AVERSION = 3.0  # Typical institutional risk aversion (delta)
DEFAULT_TAU = 0.05  # Uncertainty scaling parameter for prior
# Default risk-free rate - can be overridden via config
DEFAULT_RISK_FREE_RATE = 0.02  # Annual risk-free rate


@dataclass
class View:
    """Investor view on asset returns."""

    symbols: list[str]  # Assets involved in view
    pick: np.ndarray  # View weights (sums to 0 for relative views)
    confidence: float  # View confidence (0-1)
    expected_return: float  # Expected return of view (annualized)

    def __post_init__(self):
        """Validate view parameters."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"View confidence must be in [0, 1], got {self.confidence}")

        if len(self.pick) != len(self.symbols):
            raise ValueError(
                f"Pick vector length {len(self.pick)} must match symbols length {len(self.symbols)}"
            )


@dataclass
class BlackLittermanResult:
    """Result of Black-Litterman optimization."""

    equilibrium_returns: np.ndarray  # Implied equilibrium returns (daily)
    blended_returns: np.ndarray  # BL blended returns (daily)
    weights: np.ndarray  # Optimal weights
    symbols: list[str]  # Asset symbols
    view_adjustment: np.ndarray  # Adjustment from views (daily)

    # Optimization metrics (annualized)
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    converged: bool

    @property
    def weights_dict(self) -> dict[str, float]:
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
        risk_aversion: float = DEFAULT_RISK_AVERSION,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        tau: float = DEFAULT_TAU,
    ):
        """
        Initialize Black-Litterman optimizer.

        Args:
            risk_aversion: Risk aversion parameter (delta)
            risk_free_rate: Annual risk-free rate
            tau: Scaling parameter for uncertainty in prior
        """
        if risk_aversion <= 0:
            raise ValueError(f"Risk aversion must be positive, got {risk_aversion}")
        if tau <= 0:
            raise ValueError(f"Tau must be positive, got {tau}")
        if risk_free_rate < 0:
            raise ValueError(f"Risk-free rate cannot be negative, got {risk_free_rate}")

        self._risk_aversion = risk_aversion
        self._risk_free_rate = risk_free_rate
        self._tau = tau

    def optimize(
        self,
        cov_matrix: np.ndarray,
        market_cap_weights: np.ndarray | None = None,
        views: list[View] | None = None,
        symbols: list[str] | None = None,
    ) -> BlackLittermanResult:
        """
        Compute Black-Litterman optimal portfolio.

        Args:
            cov_matrix: Covariance matrix (daily)
            market_cap_weights: Market capitalization weights (None = equal weight)
            views: List of investor views (None = no views)
            symbols: Asset symbols

        Returns:
            BlackLittermanResult with optimal weights

        Raises:
            ValueError: If covariance matrix validation fails
        """
        # Validate covariance matrix
        is_valid, validated_cov, error_msg = validate_covariance_matrix(
            cov_matrix,
            check_psd=True,
            check_symmetry=True,
            enforce_psd=True,
        )

        if not is_valid:
            raise ValueError(f"Invalid covariance matrix: {error_msg}")

        cov_matrix = validated_cov
        n_assets = cov_matrix.shape[0]
        symbols = symbols or [f"Asset_{i}" for i in range(n_assets)]

        # Validate and normalize market weights
        if market_cap_weights is None:
            market_cap_weights = np.ones(n_assets) / n_assets
        else:
            market_cap_weights = np.asarray(market_cap_weights)
            if len(market_cap_weights) != n_assets:
                raise ValueError(
                    f"Market weights length {len(market_cap_weights)} "
                    f"must match n_assets {n_assets}"
                )
            # Normalize to sum to 1
            market_cap_weights = market_cap_weights / market_cap_weights.sum()

        # Step 1: Calculate implied equilibrium returns
        try:
            implied_returns = self._calculate_implied_returns(
                cov_matrix,
                market_cap_weights,
            )
        except np.linalg.LinAlgError as e:
            log_optimization_failure(
                "_calculate_implied_returns",
                e,
                {"n_assets": n_assets, "method": "BL equilibrium returns"},
            )
            raise ValueError(f"Failed to calculate implied returns: {e}") from e

        # Step 2: Combine with views
        if views is None or len(views) == 0:
            # No views - use equilibrium returns
            bl_returns = implied_returns
            view_adjustment = np.zeros(n_assets)
        else:
            try:
                bl_returns, view_adjustment = self._combine_with_views(
                    cov_matrix,
                    implied_returns,
                    views,
                    symbols,
                )
            except (ValueError, np.linalg.LinAlgError) as e:
                log_optimization_failure(
                    "_combine_with_views",
                    e,
                    {"n_views": len(views), "symbols": symbols},
                )
                # Fall back to equilibrium returns
                logger.warning(
                    "Falling back to equilibrium returns due to view combination failure"
                )
                bl_returns = implied_returns
                view_adjustment = np.zeros(n_assets)

        # Step 3: Optimize with blended returns
        try:
            result = self._optimize_with_returns(
                cov_matrix,
                bl_returns,
                symbols,
            )
        except Exception as e:
            log_optimization_failure(
                "_optimize_with_returns",
                e,
                {"symbols": symbols[:5] if symbols else None},  # Log first 5 symbols
            )
            raise

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

        π = δ * Σ * w_market

        Where:
        - π = implied excess returns (daily)
        - δ = risk aversion
        - Σ = covariance matrix (daily)
        - w = market capitalization weights

        Args:
            cov_matrix: Covariance matrix (must be PSD)
            market_weights: Market capitalization weights

        Returns:
            Implied equilibrium returns (daily)

        Raises:
            np.linalg.LinAlgError: If covariance matrix is singular
        """
        # Excess equilibrium returns (daily)
        # π = δ * Σ * w
        implied_returns = self._risk_aversion * (cov_matrix @ market_weights)

        return implied_returns

    def _combine_with_views(
        self,
        cov_matrix: np.ndarray,
        implied_returns: np.ndarray,
        views: list[View],
        symbols: list[str],
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Combine equilibrium returns with investor views.

        Uses Black-Litterman formula:
        μ_BL = [(τΣ)^(-1) + P'Ω(-1)P]^(-1) * [(τΣ)^(-1)π + P'Ω^(-1)Q]

        Where:
        - P: Pick matrix (maps views to assets)
        - Q: View returns
        - Ω: View uncertainty matrix (diagonal)

        Args:
            cov_matrix: Covariance matrix
            implied_returns: Implied equilibrium returns
            views: List of investor views
            symbols: Asset symbols

        Returns:
            Tuple of (blended_returns, view_adjustment)

        Raises:
            ValueError: If view symbols not found in symbols list
            np.linalg.LinAlgError: If matrix inversions fail
        """
        n_assets = len(symbols)
        n_views = len(views)

        # Build pick matrix P
        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        omega = np.zeros((n_views, n_views))

        for i, view in enumerate(views):
            # Validate view symbols
            valid_symbols = [s for s in view.symbols if s in symbols]

            if len(valid_symbols) != len(view.symbols):
                missing = set(view.symbols) - set(symbols)
                raise ValueError(f"View symbols not found in universe: {missing}")

            # Get indices for symbols in view
            indices = [symbols.index(s) for s in view.symbols]

            # Set pick matrix
            for idx, symbol_idx in enumerate(indices):
                P[i, symbol_idx] = view.pick[idx]

            # Expected return of view (convert annual to daily)
            Q[i] = view.expected_return / TRADING_DAYS

            # View uncertainty (inverse of confidence)
            # Ω[i,i] = (1-c)/c for confidence c
            # Higher confidence = lower uncertainty
            if view.confidence > 0:
                omega[i, i] = (1.0 - view.confidence) / view.confidence
            else:
                # Zero confidence = maximum uncertainty
                omega[i, i] = 1.0

        # Scale covariance matrix by tau
        tau_sigma = self._tau * cov_matrix

        try:
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

        except np.linalg.LinAlgError as e:
            logger.error(f"Matrix inversion failed in BL view combination: {e}")
            raise

        # Calculate view adjustment
        view_adjustment = bl_returns - implied_returns

        return bl_returns, view_adjustment

    def _optimize_with_returns(
        self,
        cov_matrix: np.ndarray,
        expected_returns: np.ndarray,
        symbols: list[str],
    ) -> OptimizationResult:
        """
        Optimize using expected returns.

        Uses MVO to maximize Sharpe ratio with BL returns.

        Args:
            cov_matrix: Covariance matrix
            expected_returns: Expected returns (daily)
            symbols: Asset symbols

        Returns:
            OptimizationResult
        """
        n_assets = len(symbols)

        # Convert daily returns to annual for MVO
        annual_returns = expected_returns * TRADING_DAYS

        # Direct optimization
        def objective(weights: np.ndarray) -> float:
            portfolio_return = float(weights @ annual_returns)
            portfolio_var = float(weights @ cov_matrix @ weights)
            portfolio_std = np.sqrt(portfolio_var)

            # Annualize (returns are already annual, std needs scaling)
            annual_std = portfolio_std * np.sqrt(TRADING_DAYS)

            sharpe = (portfolio_return - self._risk_free_rate) / annual_std
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
        expected_risk = np.sqrt(expected_var) * np.sqrt(TRADING_DAYS)
        sharpe = (expected_return - self._risk_free_rate) / expected_risk

        return OptimizationResult(
            weights=weights,
            expected_return=expected_return,
            expected_risk=expected_risk,
            sharpe_ratio=sharpe,
            symbols=symbols,
            converged=result.success,
            message=result.message,
        )


def create_relative_view(
    symbols: list[str],
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

    Raises:
        ValueError: If symbols not found in universe
    """
    # Validate symbols exist
    if outperform not in symbols:
        raise ValueError(f"Outperform symbol '{outperform}' not in symbols list")
    if underperform not in symbols:
        raise ValueError(f"Underperform symbol '{underperform}' not in symbols list")

    # Validate confidence
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be in [0, 1], got {confidence}")

    # Create pick vector for relative view
    # +1 for outperformer, -1 for underperformer
    pick = np.zeros(len(symbols))
    pick[symbols.index(outperform)] = 1.0
    pick[symbols.index(underperform)] = -1.0

    return View(
        symbols=[outperform, underperform],
        pick=pick[[symbols.index(outperform), symbols.index(underperform)]],
        confidence=confidence,
        expected_return=expected_alpha,
    )
