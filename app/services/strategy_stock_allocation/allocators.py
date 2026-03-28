"""
Capital allocation modules.

Provides ERC (Equal Risk Contribution) / Risk Parity capital allocation
following Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize

if TYPE_CHECKING:
    from app.shared.config.params.strategy_config import StockAllocationSettings

logger = logging.getLogger(__name__)


class ERCCapitalAllocator:
    """
    Allocates capital using ERC (Equal Risk Contribution) / Risk Parity.

    Minimizes inequality of marginal risk contribution across assets.
    """

    def __init__(
        self,
        config: StockAllocationSettings,
    ) -> None:
        """
        Initialize ERC capital allocator.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def allocate(
        self,
        scores: dict[str, dict[str, float]],
        total_capital: float,
        filtered_stocks: dict[str, np.ndarray],
        strategy_allocations: dict[str, float],
    ) -> dict[str, float]:
        """
        Allocate capital using ERC (Equal Risk Contribution) / Risk Parity.

        Minimizes inequality of marginal risk contribution.

        Args:
            scores: Dictionary mapping ticker to strategy scores
            total_capital: Total capital to allocate
            filtered_stocks: Dictionary mapping ticker to price data for covariance
            strategy_allocations: Dictionary mapping strategy to capital allocation

        Returns:
            Dictionary mapping ticker to allocated capital
        """
        logger.info(f"Allocating capital using ERC (total: ${total_capital:,.2f})")

        try:
            tickers = list(scores.keys())
            if len(tickers) == 0:
                return {}

            # Calculate returns for covariance matrix
            returns_dict = self._calculate_returns(filtered_stocks, tickers)

            if len(returns_dict) == 0:
                logger.warning("No returns data available for ERC - using equal weights")
                return self._equal_weight_allocation(tickers, total_capital)

            # Build covariance matrix
            cov_matrix = self._build_covariance_matrix(returns_dict)

            # Optimize ERC weights
            optimal_weights = self._optimize_erc_weights(cov_matrix, tickers)

            # Allocate capital
            allocations = self._apply_weights_to_capital(tickers, optimal_weights, total_capital)

            logger.info(
                f"ERC optimization successful: {len(allocations)} allocations, "
                f"total=${sum(allocations.values()):,.2f}"
            )
            return allocations

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error in ERC allocation: {e}", exc_info=True)
            tickers = list(scores.keys())
            return self._equal_weight_allocation(tickers, total_capital)

    def _calculate_returns(
        self, filtered_stocks: dict[str, np.ndarray], tickers: list[str]
    ) -> dict[str, np.ndarray]:
        """Calculate returns for covariance matrix."""
        returns_dict = {}

        for ticker in tickers:
            if ticker in filtered_stocks:
                prices = filtered_stocks[ticker]
                if isinstance(prices, np.ndarray):
                    returns = np.diff(prices) / prices[:-1]
                    returns_dict[ticker] = returns

        return returns_dict

    def _build_covariance_matrix(self, returns_dict: dict[str, np.ndarray]) -> np.ndarray:
        """Build covariance matrix from returns."""
        min_len = min(len(r) for r in returns_dict.values())
        returns_matrix = np.array([r[:min_len] for r in returns_dict.values()])
        return np.cov(returns_matrix)

    def _optimize_erc_weights(self, cov_matrix: np.ndarray, tickers: list[str]) -> np.ndarray:
        """Optimize weights for ERC allocation."""
        n = len(tickers)
        initial_weights = np.ones(n) / n

        # Objective function: minimize variance of risk contributions
        def objective(weights):
            weights = np.maximum(weights, 0)
            weights = weights / np.sum(weights)

            port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

            if port_vol < 1e-10:
                return 1e10

            marginal_contrib = np.dot(cov_matrix, weights) / port_vol
            risk_contrib = weights * marginal_contrib
            variance_risk_contrib = np.var(risk_contrib)

            return variance_risk_contrib

        # Constraints: weights sum to 1
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        # Bounds
        max_weight = self.config.MAX_STRATEGY_EXPOSURE
        bounds = [(0, max_weight) for _ in range(n)]

        # Optimize
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={
                'maxiter': self.config.ERC_MAX_ITERATIONS,
                'ftol': self.config.ERC_OPTIMIZATION_TOLERANCE,
            },
        )

        if result.success:
            optimal_weights = result.x
            optimal_weights = np.maximum(optimal_weights, 0)
            weight_sum = np.sum(optimal_weights)

            if weight_sum > 1e-10:
                optimal_weights = optimal_weights / weight_sum
            else:
                optimal_weights = np.ones(n) / n

            return optimal_weights
        else:
            logger.warning(f"ERC optimization failed: {result.message}, using equal weights")
            return np.ones(n) / n

    def _apply_weights_to_capital(
        self, tickers: list[str], weights: np.ndarray, total_capital: float
    ) -> dict[str, float]:
        """Apply optimized weights to capital allocation."""
        allocations = {ticker: float(total_capital * w) for ticker, w in zip(tickers, weights)}

        # Ensure allocations sum to exactly total_capital
        allocated_sum = sum(allocations.values())
        if abs(allocated_sum - total_capital) > 0.01:
            diff = total_capital - allocated_sum
            max_ticker = max(allocations.keys(), key=lambda k: allocations[k])
            allocations[max_ticker] += diff

        return allocations

    def _equal_weight_allocation(
        self, tickers: list[str], total_capital: float
    ) -> dict[str, float]:
        """Fallback to equal weight allocation."""
        if len(tickers) == 0:
            return {}

        equal_weight = min(1.0 / len(tickers), self.config.MAX_STRATEGY_EXPOSURE)
        allocations = dict.fromkeys(tickers, total_capital * equal_weight)

        # Normalize if needed
        total_allocated = sum(allocations.values())
        if total_allocated < total_capital - 0.01:
            remaining = total_capital - total_allocated
            per_ticker = remaining / len(tickers)

            for ticker in allocations:
                new_weight = (allocations[ticker] + per_ticker) / total_capital
                if new_weight <= self.config.MAX_STRATEGY_EXPOSURE:
                    allocations[ticker] += per_ticker
                else:
                    allocations[ticker] = total_capital * self.config.MAX_STRATEGY_EXPOSURE

        # Final adjustment
        allocated_sum = sum(allocations.values())
        if abs(allocated_sum - total_capital) > 0.01:
            diff = total_capital - allocated_sum
            max_ticker = max(allocations.keys(), key=lambda k: allocations[k])
            allocations[max_ticker] += diff

        return allocations
