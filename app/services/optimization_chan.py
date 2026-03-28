from __future__ import annotations

"""
Ernest Chan - Quantitative Trading: Portfolio Optimization Implementation

This module implements portfolio optimization methods as described in Ernest Chan's
"Quantitative Trading: How to Build Your Own Algorithmic Trading Business".

Key Concepts:
- Mean-Variance Optimization (Markowitz)
- Risk Parity Implementation (Equal Risk Contribution)
- Hierarchical Risk Parity (HRP)
- Maximum Diversification Portfolio
- Minimum Variance Portfolio
- Target Volatility Portfolio
- CVaR (Conditional Value at Risk) Optimization

Based on:
- Markowitz, H. (1952). Portfolio Selection.
- Maillard, S., Roncalli, T., & Teiletche, J. (2010). The properties of equally weighted risk contributions.
- Lopez de Prado, M. (2016). Building diversified portfolios that outperform out of sample.

Author: Algorithmic Trading System
Date: 2026-01-28
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

# Optional cvxpy dependency
try:
    import cvxpy as cp

    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    cp = None

logger = logging.getLogger(__name__)


def _check_cvxpy_available() -> None:
    """Check if cvxpy is available, raise ImportError if not."""
    if not CVXPY_AVAILABLE:
        raise ImportError(
            "cvxpy is required for portfolio optimization. Install it with: pip install cvxpy"
        )


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    weights: np.ndarray
    expected_return: float
    volatility: float
    sharpe_ratio: float
    method: str
    risk_contributions: Optional[np.ndarray] = None
    diversification_ratio: Optional[float] = None
    turnover: Optional[float] = None
    metadata: Optional[Dict] = None


class MeanVarianceOptimizer:
    """
    Mean-Variance Optimization (Markowitz Portfolio Theory).

    Implements classical mean-variance optimization with various objectives:
    - Maximize Sharpe ratio
    - Minimize variance (minimum variance portfolio)
    - Maximize return for given risk
    - Maximize diversification

    Usage:
        >>> optimizer = MeanVarianceOptimizer()
        >>> result = getattr(config.trading, 'max_risk_per_trade', 0.02)
    """

    def __init__(self):
        """Initialize Mean-Variance Optimizer."""
        self.last_result: Optional[OptimizationResult] = None
        logger.info("MeanVarianceOptimizer initialized")

    def optimize(
        self,
        returns: pd.DataFrame,
        objective: str = "max_sharpe",
        risk_free_rate: float = 0.0,
        weight_constraints: Optional[Dict[str, float]] = None,
        sector_constraints: Optional[Dict[str, Tuple[List[int], float]]] = None,
    ) -> OptimizationResult:
        """
        Optimize portfolio weights using mean-variance framework.

        Args:
            returns: DataFrame of asset returns (assets in columns)
            objective: Optimization objective ('max_sharpe', 'min_variance', 'max_diversification')
            risk_free_rate: Risk-free rate for Sharpe calculation
            weight_constraints: Dict with 'min_weight', 'max_weight', 'max_positions'
            sector_constraints: Dict mapping sector name to (asset_indices, max_weight)

        Returns:
            OptimizationResult with optimized weights and metrics
        """
        _check_cvxpy_available()

        try:
            # Calculate inputs
            mu = returns.mean().values * 252  # Annualized returns
            sigma = returns.cov().values * 252  # Annualized covariance

            n_assets = len(mu)

            # Set default constraints
            constraints = weight_constraints or {}
            min_weight = constraints.get('min_weight', 0.0)
            max_weight = constraints.get('max_weight', 1.0)
            max_positions = constraints.get('max_positions', n_assets)

            # Define optimization variables
            w = cp.Variable(n_assets)

            # Portfolio statistics
            portfolio_return = mu.T @ w
            portfolio_var = cp.quad_form(w, sigma)
            portfolio_vol = cp.sqrt(portfolio_var)

            # Build constraints list
            constraint_list = [
                cp.sum(w) == 1,  # Fully invested
                w >= min_weight,  # Minimum weight
                w <= max_weight,  # Maximum weight
            ]

            # Add sector constraints if provided
            if sector_constraints:
                for _sector_name, (asset_indices, sector_max_weight) in sector_constraints.items():
                    sector_weights = w[asset_indices]
                    constraint_list.append(cp.sum(sector_weights) <= sector_max_weight)

            # Limit number of positions (cardinality constraint approximation)
            if max_positions < n_assets:
                # Use L1 norm as proxy for sparsity
                # This is a convex relaxation of the cardinality constraint
                constraint_list.append(cp.norm1(w) <= max_positions * max_weight * 0.8)

            # Set objective based on specification
            if objective == "max_sharpe":
                # Maximize Sharpe ratio: (mu - rf) / sigma
                # Equivalent to: maximize (mu - rf)'w / sqrt(w'Sigma*w)
                # We can solve this as: minimize (w'Sigma*w) / ((mu - rf)'w)
                risk_adjusted_returns = mu - risk_free_rate
                objective = cp.Minimize(portfolio_var / (risk_adjusted_returns.T @ w))

            elif objective == "min_variance":
                # Minimize portfolio variance
                objective = cp.Minimize(portfolio_var)

            elif objective == "max_diversification":
                # Maximize diversification ratio
                # DR = (w' * sigma_diag) / sqrt(w' * Sigma * w)
                vol_weights = np.sqrt(np.diag(sigma))
                weighted_avg_vol = vol_weights.T @ w
                objective = cp.Maximize(weighted_avg_vol / portfolio_vol)

            elif objective == "max_return":
                # Maximize return with risk constraint
                max_vol = constraints.get('max_volatility', 0.2)
                constraint_list.append(portfolio_vol <= max_vol)
                objective = cp.Maximize(portfolio_return)

            else:
                raise ValueError(f"Unknown objective: {objective}")

            # Solve optimization
            problem = cp.Problem(objective, constraint_list)
            problem.solve(solver=cp.ECOS, verbose=False)

            if problem.status != "optimal":
                # Try SCS solver if ECOS fails
                problem.solve(solver=cp.SCS, verbose=False)

            if problem.status != "optimal":
                raise ValueError(f"Optimization failed: {problem.status}")

            # Extract weights
            weights = w.value
            weights = np.maximum(weights, 0)  # Ensure non-negative
            weights = weights / weights.sum()  # Normalize

            # Calculate portfolio metrics
            expected_return = float(mu @ weights)
            volatility = float(np.sqrt(weights @ sigma @ weights))
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Calculate risk contributions
            marginal_contrib = (sigma @ weights) / volatility
            risk_contrib = weights * marginal_contrib

            # Calculate diversification ratio
            weighted_avg_vol = float(np.sum(np.sqrt(np.diag(sigma)) * weights))
            div_ratio = weighted_avg_vol / volatility if volatility > 0 else 1.0

            result = OptimizationResult(
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                method=f"mean_variance_{objective}",
                risk_contributions=risk_contrib,
                diversification_ratio=div_ratio,
                metadata={'solver_status': problem.status},
            )

            self.last_result = result

            logger.info(
                f"Mean-Variance optimization complete: "
                f"return={expected_return:.4f}, vol={volatility:.4f}, sharpe={sharpe_ratio:.4f}"
            )

            return result

        except (ValueError, TypeError, cp.SolverError) as e:
            logger.error(f"Mean-variance optimization failed: {e}")
            # Return equal weight fallback
            n = returns.shape[1]
            equal_weights = np.ones(n) / n
            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="equal_weight_fallback",
            )


class RiskParityOptimizer:
    """
    Risk Parity Optimization (Equal Risk Contribution).

    Risk parity allocates capital so that each asset contributes equally
    to portfolio risk. This is different from equal weight allocation.

    Based on:
    - Maillard, S., Roncalli, T., & Teiletche, J. (2010).
      The properties of equally weighted risk contributions.

    Usage:
        >>> optimizer = RiskParityOptimizer()
        >>> result = optimizer.optimize(returns)
    """

    def __init__(self):
        """Initialize Risk Parity Optimizer."""
        self.last_result: Optional[OptimizationResult] = None
        logger.info("RiskParityOptimizer initialized")

    def optimize(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.0,
        weight_constraints: Optional[Dict[str, float]] = None,
        tolerance: float = 1e-8,
        max_iterations: int = 1000,
    ) -> OptimizationResult:
        """
        Optimize portfolio weights for equal risk contribution.

        Args:
            returns: DataFrame of asset returns
            risk_free_rate: Risk-free rate for Sharpe calculation
            weight_constraints: Weight bounds constraints
            tolerance: Convergence tolerance
            max_iterations: Maximum optimization iterations

        Returns:
            OptimizationResult with risk parity weights
        """
        try:
            # Calculate inputs
            mu = returns.mean().values * 252
            sigma = returns.cov().values * 252

            n_assets = len(mu)

            # Set constraints
            constraints = weight_constraints or {}
            min_weight = constraints.get('min_weight', 0.0)
            max_weight = constraints.get('max_weight', 1.0)

            # Initial guess: inverse volatility weights
            inv_vol = 1.0 / np.sqrt(np.diag(sigma))
            inv_vol = inv_vol / inv_vol.sum()
            x0 = inv_vol

            # Target risk contribution (equal)
            target_risk = 1.0 / n_assets

            def _risk_parity_objective(weights: np.ndarray) -> float:
                """Objective: minimize sum of squared deviations from equal risk."""
                portfolio_var = weights @ sigma @ weights
                if portfolio_var <= 0:
                    return 1e10

                # Risk contributions: RC_i = w_i * (Sigma @ w)_i / sigma_p^2
                marginal_contrib = sigma @ weights
                risk_contrib = weights * marginal_contrib / portfolio_var

                # Sum of squared deviations from target
                return float(np.sum((risk_contrib - target_risk) ** 2))

            def _risk_parity_gradient(weights: np.ndarray) -> np.ndarray:
                """Analytical gradient for faster convergence."""
                portfolio_var = weights @ sigma @ weights
                if portfolio_var <= 0:
                    return np.zeros(n_assets)

                sigma_w = sigma @ weights
                rc = weights * sigma_w / portfolio_var
                diff = rc - target_risk

                # Gradient
                grad = np.zeros(n_assets)
                for i in range(n_assets):
                    for j in range(n_assets):
                        if i == j:
                            drc_dw = (sigma_w[i] + weights[i] * sigma[i, i]) / portfolio_var
                            drc_dw -= rc[i] * 2 * sigma_w[j] / portfolio_var
                        else:
                            drc_dw = weights[i] * sigma[i, j] / portfolio_var
                            drc_dw -= rc[i] * 2 * sigma_w[j] / portfolio_var
                        grad[j] += 2 * diff[i] * drc_dw

                return grad

            # Constraints: fully invested, bounds
            bounds = [(min_weight, max_weight) for _ in range(n_assets)]
            constraints_dict = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}

            # Optimize
            result = minimize(
                _risk_parity_objective,
                x0,
                method='SLSQP',
                jac=_risk_parity_gradient,
                bounds=bounds,
                constraints=constraints_dict,
                options={'ftol': tolerance, 'maxiter': max_iterations},
            )

            if not result.success:
                logger.warning(f"Risk parity optimization warning: {result.message}")

            weights = result.x
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()

            # Calculate metrics
            expected_return = float(mu @ weights)
            volatility = float(np.sqrt(weights @ sigma @ weights))
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Risk contributions
            portfolio_vol = volatility
            marginal_contrib = (sigma @ weights) / portfolio_vol
            risk_contrib = weights * marginal_contrib

            # Verify equal risk contribution
            risk_parity_score = float(np.std(risk_contrib))

            opt_result = OptimizationResult(
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                method="risk_parity",
                risk_contributions=risk_contrib,
                metadata={'risk_parity_score': risk_parity_score},
            )

            self.last_result = opt_result

            logger.info(
                f"Risk parity optimization complete: "
                f"vol={volatility:.4f}, risk_parity_score={risk_parity_score:.6f}"
            )

            return opt_result

        except (ValueError, TypeError) as e:
            logger.error(f"Risk parity optimization failed: {e}")
            n = returns.shape[1]
            equal_weights = np.ones(n) / n
            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="equal_weight_fallback",
            )


class HierarchicalRiskParityOptimizer:
    """
    Hierarchical Risk Parity (HRP) Optimization.

    HRP uses hierarchical clustering to group assets and allocates risk
    based on the cluster structure. This approach is more robust than
    traditional optimization and doesn't require invertibility of the
    covariance matrix.

    Based on:
    - Lopez de Prado, M. (2016). Building diversified portfolios that outperform out of sample.
    - Lopez de Prado, M. (2016). Hierarchical Risk Parity.

    Usage:
        >>> optimizer = HierarchicalRiskParityOptimizer()
        >>> result = optimizer.optimize(returns, method='ward')
    """

    def __init__(self):
        """Initialize HRP Optimizer."""
        self.last_result: Optional[OptimizationResult] = None
        self.linkage_matrix: Optional[np.ndarray] = None
        logger.info("HierarchicalRiskParityOptimizer initialized")

    def optimize(
        self,
        returns: pd.DataFrame,
        method: str = "ward",
        metric: str = "euclidean",
        risk_free_rate: float = 0.0,
    ) -> OptimizationResult:
        """
        Optimize portfolio weights using Hierarchical Risk Parity.

        Args:
            returns: DataFrame of asset returns
            method: Linkage method ('single', 'complete', 'average', 'ward')
            metric: Distance metric
            risk_free_rate: Risk-free rate for Sharpe calculation

        Returns:
            OptimizationResult with HRP weights
        """
        try:
            # Calculate covariance matrix
            sigma = returns.cov().values * 252
            mu = returns.mean().values * 252

            # Calculate correlation matrix
            corr = returns.corr().values

            # Distance matrix: d(i,j) = sqrt(0.5 * (1 - corr(i,j)))
            distance_matrix = np.sqrt(0.5 * (1 - corr))

            # Hierarchical clustering
            self.linkage_matrix = linkage(
                squareform(distance_matrix),
                method=method,
                metric=metric,
            )

            # Get cluster order
            n_assets = len(mu)
            order = self._get_cluster_order(self.linkage_matrix, n_assets)

            # Recursive bisection to allocate weights
            weights = self._hrp_allocation(sigma, order)

            # Calculate metrics
            expected_return = float(mu @ weights)
            volatility = float(np.sqrt(weights @ sigma @ weights))
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Risk contributions
            marginal_contrib = (sigma @ weights) / volatility
            risk_contrib = weights * marginal_contrib

            # Diversification ratio
            weighted_avg_vol = float(np.sum(np.sqrt(np.diag(sigma)) * weights))
            div_ratio = weighted_avg_vol / volatility if volatility > 0 else 1.0

            result = OptimizationResult(
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                method="hierarchical_risk_parity",
                risk_contributions=risk_contrib,
                diversification_ratio=div_ratio,
                metadata={
                    'linkage_method': method,
                    'distance_metric': metric,
                },
            )

            self.last_result = result

            logger.info(
                f"HRP optimization complete: "
                f"return={expected_return:.4f}, vol={volatility:.4f}, div_ratio={div_ratio:.4f}"
            )

            return result

        except (ValueError, TypeError) as e:
            logger.error(f"HRP optimization failed: {e}")
            n = returns.shape[1]
            equal_weights = np.ones(n) / n
            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="equal_weight_fallback",
            )

    def _get_cluster_order(self, linkage_matrix: np.ndarray, n_items: int) -> List[int]:
        """
        Get ordered list of items from hierarchical clustering.

        Args:
            linkage_matrix: Linkage matrix from scipy.cluster.hierarchy.linkage
            n_items: Number of items

        Returns:
            Ordered list of indices
        """
        # This is a simplified version - full implementation would use
        # scipy.cluster.hierarchy.dendrogram and extract the order

        dendro = dendrogram(linkage_matrix, no_plot=True)
        return dendro['leaves']

    def _hrp_allocation(
        self,
        sigma: np.ndarray,
        order: List[int],
    ) -> np.ndarray:
        """
        Recursive bisection for HRP weight allocation.

        Args:
            sigma: Covariance matrix
            order: Ordered list of asset indices

        Returns:
            HRP weights
        """
        n = len(order)
        weights = np.ones(n) / n

        # Recursive bisection
        def _bisect_allocation(items: List[int], weights_slice: np.ndarray) -> None:
            """Recursively bisect and allocate weights."""
            if len(items) <= 1:
                return

            # Split point
            mid = len(items) // 2
            left_items = items[:mid]
            right_items = items[mid:]

            # Calculate variances
            left_var = self._get_cluster_variance(sigma, left_items, weights_slice[:mid])
            right_var = self._get_cluster_variance(sigma, right_items, weights_slice[mid:])

            # Allocate weights inversely proportional to variance
            total_var = left_var + right_var
            if total_var > 0:
                left_weight = right_var / total_var
                right_weight = left_var / total_var

                # Update weights
                weights_slice[:mid] *= left_weight
                weights_slice[mid:] *= right_weight

            # Recurse
            _bisect_allocation(left_items, weights_slice[:mid])
            _bisect_allocation(right_items, weights_slice[mid:])

        # Initial call
        _bisect_allocation(order, weights)

        # Reorder weights to original asset order
        ordered_weights = np.zeros(n)
        ordered_weights[order] = weights

        return ordered_weights

    def _get_cluster_variance(
        self,
        sigma: np.ndarray,
        items: List[int],
        weights: np.ndarray,
    ) -> float:
        """Calculate cluster variance."""
        if len(items) == 0:
            return 0.0

        # Normalize weights
        weights_norm = weights / weights.sum()

        # Cluster variance
        cluster_sigma = sigma[np.ix_(items, items)]
        cluster_var = weights_norm @ cluster_sigma @ weights_norm

        return float(cluster_var)


class MaximumDiversificationOptimizer:
    """
    Maximum Diversification Portfolio Optimization.

    Maximizes the diversification ratio, which measures the ratio of
    the weighted average volatility to the portfolio volatility.

    DR = (sum(w_i * sigma_i)) / sqrt(w' * Sigma * w)

    Based on:
    - Choueifaty, Y., & Coignard, Y. (2008). Toward maximum diversification.

    Usage:
        >>> optimizer = MaximumDiversificationOptimizer()
        >>> result = optimizer.optimize(returns)
    """

    def __init__(self):
        """Initialize Maximum Diversification Optimizer."""
        self.last_result: Optional[OptimizationResult] = None
        logger.info("MaximumDiversificationOptimizer initialized")

    def optimize(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.0,
        weight_constraints: Optional[Dict[str, float]] = None,
    ) -> OptimizationResult:
        """
        Optimize for maximum diversification ratio.

        Args:
            returns: DataFrame of asset returns
            risk_free_rate: Risk-free rate
            weight_constraints: Weight bounds

        Returns:
            OptimizationResult
        """
        _check_cvxpy_available()

        try:
            mu = returns.mean().values * 252
            sigma = returns.cov().values * 252

            n_assets = len(mu)

            constraints = weight_constraints or {}
            min_weight = constraints.get('min_weight', 0.0)
            max_weight = constraints.get('max_weight', 1.0)

            # CVXPY optimization
            w = cp.Variable(n_assets)

            portfolio_var = cp.quad_form(w, sigma)
            portfolio_vol = cp.sqrt(portfolio_var)

            # Weighted average volatility (diagonal)
            vol_weights = np.sqrt(np.diag(sigma))
            weighted_avg_vol = vol_weights.T @ w

            # Maximize diversification ratio
            objective = cp.Maximize(weighted_avg_vol / portfolio_vol)

            constraint_list = [
                cp.sum(w) == 1,
                w >= min_weight,
                w <= max_weight,
            ]

            problem = cp.Problem(objective, constraint_list)
            problem.solve(solver=cp.ECOS)

            if problem.status != "optimal":
                problem.solve(solver=cp.SCS)

            weights = w.value
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()

            expected_return = float(mu @ weights)
            volatility = float(np.sqrt(weights @ sigma @ weights))
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Risk contributions
            marginal_contrib = (sigma @ weights) / volatility
            risk_contrib = weights * marginal_contrib

            # Diversification ratio
            div_ratio = float(np.sum(vol_weights * weights) / volatility)

            result = OptimizationResult(
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                method="maximum_diversification",
                risk_contributions=risk_contrib,
                diversification_ratio=div_ratio,
            )

            self.last_result = result

            logger.info(
                f"Maximum diversification complete: "
                f"div_ratio={div_ratio:.4f}, vol={volatility:.4f}"
            )

            return result

        except (ValueError, TypeError, cp.SolverError) as e:
            logger.error(f"Maximum diversification optimization failed: {e}")
            n = returns.shape[1]
            equal_weights = np.ones(n) / n
            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="equal_weight_fallback",
            )


class CVaROptimizer:
    """
    Conditional Value at Risk (CVaR) Optimization.

    CVaR (also known as Expected Shortfall) is a coherent risk measure
    that calculates the expected loss beyond VaR. This is useful for
    risk-averse optimization.

    Based on:
    - Rockafellar, R. T., & Uryasev, S. (2000). Optimization of conditional value-at-risk.

    Usage:
        >>> optimizer = CVaROptimizer(confidence_level=0.95)
        >>> result = optimizer.optimize(returns)
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize CVaR Optimizer.

        Args:
            confidence_level: Confidence level for CVaR (e.g., 0.95 for 95%)
        """
        self.confidence_level = confidence_level
        self.last_result: Optional[OptimizationResult] = None
        logger.info(f"CVaROptimizer initialized: confidence={confidence_level}")

    def optimize(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.0,
        weight_constraints: Optional[Dict[str, float]] = None,
    ) -> OptimizationResult:
        """
        Optimize portfolio for CVaR minimization.

        Args:
            returns: DataFrame of asset returns
            risk_free_rate: Risk-free rate
            weight_constraints: Weight bounds

        Returns:
            OptimizationResult
        """
        _check_cvxpy_available()

        try:
            # Convert returns to numpy (scenarios x assets)
            R = returns.values

            n_scenarios, n_assets = R.shape

            constraints = weight_constraints or {}
            min_weight = constraints.get('min_weight', 0.0)
            max_weight = constraints.get('max_weight', 1.0)

            # CVXPY optimization
            w = cp.Variable(n_assets)
            gamma = cp.Variable()  # VaR

            # Auxiliary variables for CVaR calculation
            # z_i = max(0, -R_i'w - gamma)
            z = cp.Variable(n_scenarios, nonneg=True)

            # Portfolio returns for each scenario
            portfolio_returns = R @ w

            # CVaR calculation: CVaR = gamma + (1 / ((1-alpha) * S)) * sum(z_i)
            alpha = self.confidence_level
            cvar = gamma + cp.sum(z) / ((1 - alpha) * n_scenarios)

            # Constraints: z_i >= -portfolio_return_i - gamma
            constraints_list = [
                cp.sum(w) == 1,
                w >= min_weight,
                w <= max_weight,
                z >= -portfolio_returns - gamma,
            ]

            # Minimize CVaR
            objective = cp.Minimize(cvar)

            problem = cp.Problem(objective, constraints_list)
            problem.solve(solver=cp.ECOS)

            if problem.status != "optimal":
                problem.solve(solver=cp.SCS)

            weights = w.value
            weights = np.maximum(weights, 0)
            weights = weights / weights.sum()

            # Calculate metrics
            mu = returns.mean().values * 252
            sigma = returns.cov().values * 252

            expected_return = float(mu @ weights)
            volatility = float(np.sqrt(weights @ sigma @ weights))
            sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Calculate actual CVaR and VaR from historical returns
            portfolio_returns_hist = returns @ weights
            var = np.percentile(portfolio_returns_hist, (1 - self.confidence_level) * 100)
            cvar_actual = portfolio_returns_hist[portfolio_returns_hist <= var].mean()

            result = OptimizationResult(
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                method="cvar_optimization",
                metadata={
                    'cvar': float(cvar_actual),
                    'var': float(var),
                    'confidence_level': self.confidence_level,
                },
            )

            self.last_result = result

            logger.info(
                f"CVaR optimization complete: " f"CVaR(95%)={cvar_actual:.4f}, vol={volatility:.4f}"
            )

            return result

        except (ValueError, TypeError, cp.SolverError) as e:
            logger.error(f"CVaR optimization failed: {e}")
            n = returns.shape[1]
            equal_weights = np.ones(n) / n
            return OptimizationResult(
                weights=equal_weights,
                expected_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                method="equal_weight_fallback",
            )


def optimize_portfolio(
    returns: pd.DataFrame,
    method: str = "mean_variance",
    **kwargs,
) -> OptimizationResult:
    """
    High-level portfolio optimization function.

    Args:
        returns: DataFrame of asset returns
        method: Optimization method ('mean_variance', 'risk_parity', 'hrp', 'max_div', 'cvar')
        **kwargs: Additional arguments for specific optimizers

    Returns:
        OptimizationResult

    Example:
        >>> result = optimize_portfolio(returns, method='hrp')
        >>> print(result.weights)
    """
    if method == "mean_variance":
        optimizer = MeanVarianceOptimizer()
    elif method == "risk_parity":
        optimizer = RiskParityOptimizer()
    elif method == "hrp":
        optimizer = HierarchicalRiskParityOptimizer()
    elif method == "max_div":
        optimizer = MaximumDiversificationOptimizer()
    elif method == "cvar":
        optimizer = CVaROptimizer(**kwargs)
    else:
        raise ValueError(f"Unknown optimization method: {method}")

    return optimizer.optimize(returns, **kwargs)
