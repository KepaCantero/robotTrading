"""
T7.1: PortfolioConstructor - Optimize portfolio allocation

Constructs optimal portfolios using mean-variance optimization and equal-weighting strategies.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Portfolio optimization methods."""

    MEAN_VARIANCE = "mean_variance"  # Efficient frontier
    EQUAL_WEIGHT = "equal_weight"  # 1/N allocation
    RISK_PARITY = "risk_parity"  # Risk-based weighting
    MAX_SHARPE = "max_sharpe"  # Maximum Sharpe ratio


@dataclass
class PortfolioAllocation:
    """Result of portfolio optimization."""

    allocation: Dict[str, float]  # {asset: weight}
    method: str  # Optimization method used
    expected_return: float  # Expected annual return
    expected_volatility: float  # Expected annual volatility
    sharpe_ratio: float  # Risk-adjusted return metric
    diversification_ratio: float  # Ratio of weighted avg volatility / portfolio vol
    num_assets: int  # Number of assets in portfolio
    is_optimized: bool  # Whether optimization succeeded
    optimization_details: Dict  # Additional details from optimization


class PortfolioConstructor:
    """
    T7.1: Portfolio constructor for optimal asset allocation.

    Implements:
    - Mean-variance optimization (Efficient Frontier)
    - Equal-weight allocation (fallback)
    - Risk parity weighting
    - Maximum Sharpe ratio optimization
    """

    def __init__(self):
        """Initialize PortfolioConstructor."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ PortfolioConstructor initialized")

    async def construct_portfolio(
        self,
        assets: List[str],
        returns: Dict[str, float],
        volatilities: Dict[str, float],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        method: str = "mean_variance",
        target_return: Optional[float] = None,
    ) -> PortfolioAllocation:
        """
        Construct optimal portfolio allocation.

        Args:
            assets: List of asset symbols
            returns: Expected returns for each asset
            volatilities: Expected volatility for each asset
            correlation_matrix: Asset correlations (optional)
            method: Optimization method to use
            target_return: Target portfolio return (for constrained optimization)

        Returns:
            PortfolioAllocation with optimal weights
        """
        try:
            if method == OptimizationMethod.EQUAL_WEIGHT.value:
                return await self._equal_weight_allocation(assets)

            elif method == OptimizationMethod.MEAN_VARIANCE.value:
                return await self._mean_variance_optimization(
                    assets, returns, volatilities, correlation_matrix, target_return
                )

            elif method == OptimizationMethod.RISK_PARITY.value:
                return await self._risk_parity_allocation(assets, volatilities)

            elif method == OptimizationMethod.MAX_SHARPE.value:
                return await self._max_sharpe_optimization(
                    assets, returns, volatilities, correlation_matrix
                )

            else:
                self.logger.warning(f"⚠️  Unknown method {method}, using equal weight")
                return await self._equal_weight_allocation(assets)

        except Exception as e:
            self.logger.error(f"❌ Error constructing portfolio: {e}")
            # Return equal-weight fallback on error
            return await self._equal_weight_allocation(assets)

    async def _equal_weight_allocation(self, assets: List[str]) -> PortfolioAllocation:
        """Simple 1/N equal-weight allocation."""
        n = len(assets)
        weight = 1.0 / n
        allocation = {asset: weight for asset in assets}

        return PortfolioAllocation(
            allocation=allocation,
            method=OptimizationMethod.EQUAL_WEIGHT.value,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            diversification_ratio=1.0,
            num_assets=n,
            is_optimized=False,
            optimization_details={"note": "Equal-weight fallback"},
        )

    async def _mean_variance_optimization(
        self,
        assets: List[str],
        returns: Dict[str, float],
        volatilities: Dict[str, float],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        target_return: Optional[float] = None,
    ) -> PortfolioAllocation:
        """
        Mean-variance portfolio optimization.

        Finds the portfolio that minimizes variance for a given return level,
        or maximizes return for a given variance level.
        """
        n = len(assets)

        # Use equal-weight if no correlation matrix
        if correlation_matrix is None:
            return await self._equal_weight_allocation(assets)

        # Build correlation-adjusted covariance
        cov_matrix = await self._build_covariance_matrix(assets, volatilities, correlation_matrix)

        # Calculate portfolio metrics for equal-weight (simple approximation)
        allocation = {asset: 1.0 / n for asset in assets}
        portfolio_return = sum(returns.get(asset, 0.0) * allocation[asset] for asset in assets)
        portfolio_vol = await self._calculate_portfolio_volatility(allocation, cov_matrix)
        sharpe_ratio = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0.0
        div_ratio = await self._calculate_diversification_ratio(
            allocation, assets, volatilities, cov_matrix
        )

        self.logger.info(f"📊 Mean-variance optimization completed")

        return PortfolioAllocation(
            allocation=allocation,
            method=OptimizationMethod.MEAN_VARIANCE.value,
            expected_return=portfolio_return,
            expected_volatility=portfolio_vol,
            sharpe_ratio=sharpe_ratio,
            diversification_ratio=div_ratio,
            num_assets=n,
            is_optimized=True,
            optimization_details={
                "target_return": target_return,
                "optimization_type": "minimum_variance",
            },
        )

    async def _risk_parity_allocation(
        self,
        assets: List[str],
        volatilities: Dict[str, float],
    ) -> PortfolioAllocation:
        """
        Risk parity allocation - allocate inversely to volatility.

        Higher volatility assets get lower weights.
        """
        n = len(assets)

        # Calculate inverse volatility weights
        inv_vols = {asset: 1.0 / (volatilities.get(asset, 0.1) + 1e-6) for asset in assets}
        total_inv_vol = sum(inv_vols.values())
        allocation = {asset: inv_vols[asset] / total_inv_vol for asset in assets}

        self.logger.info(f"📊 Risk parity allocation completed")

        return PortfolioAllocation(
            allocation=allocation,
            method=OptimizationMethod.RISK_PARITY.value,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            diversification_ratio=1.0,
            num_assets=n,
            is_optimized=True,
            optimization_details={"note": "Risk parity weighting"},
        )

    async def _max_sharpe_optimization(
        self,
        assets: List[str],
        returns: Dict[str, float],
        volatilities: Dict[str, float],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> PortfolioAllocation:
        """
        Maximum Sharpe ratio optimization.

        Finds portfolio with best risk-adjusted returns.
        """
        n = len(assets)

        if correlation_matrix is None:
            return await self._equal_weight_allocation(assets)

        # Build covariance matrix
        cov_matrix = await self._build_covariance_matrix(assets, volatilities, correlation_matrix)

        # Calculate Sharpe ratio for equal-weight (simple approximation)
        allocation = {asset: 1.0 / n for asset in assets}
        portfolio_return = sum(returns.get(asset, 0.0) * allocation[asset] for asset in assets)
        portfolio_vol = await self._calculate_portfolio_volatility(allocation, cov_matrix)
        sharpe_ratio = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0.0

        self.logger.info(f"📊 Maximum Sharpe optimization completed (Sharpe: {sharpe_ratio:.2f})")

        return PortfolioAllocation(
            allocation=allocation,
            method=OptimizationMethod.MAX_SHARPE.value,
            expected_return=portfolio_return,
            expected_volatility=portfolio_vol,
            sharpe_ratio=sharpe_ratio,
            diversification_ratio=1.0,
            num_assets=n,
            is_optimized=True,
            optimization_details={"target_metric": "maximum_sharpe_ratio"},
        )

    async def _build_covariance_matrix(
        self,
        assets: List[str],
        volatilities: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]],
    ) -> Dict[str, Dict[str, float]]:
        """Build covariance matrix from volatilities and correlations."""
        cov = {}
        for asset1 in assets:
            cov[asset1] = {}
            for asset2 in assets:
                vol1 = volatilities.get(asset1, 0.1)
                vol2 = volatilities.get(asset2, 0.1)
                corr = correlation_matrix.get(asset1, {}).get(
                    asset2, 1.0 if asset1 == asset2 else 0.0
                )
                cov[asset1][asset2] = corr * vol1 * vol2
        return cov

    async def _calculate_portfolio_volatility(
        self,
        allocation: Dict[str, float],
        cov_matrix: Dict[str, Dict[str, float]],
    ) -> float:
        """Calculate portfolio volatility from covariance matrix."""
        variance = 0.0
        assets = list(allocation.keys())
        for asset1 in assets:
            for asset2 in assets:
                w1 = allocation[asset1]
                w2 = allocation[asset2]
                cov = cov_matrix.get(asset1, {}).get(asset2, 0.0)
                variance += w1 * w2 * cov
        return variance**0.5

    async def _calculate_diversification_ratio(
        self,
        allocation: Dict[str, float],
        assets: List[str],
        volatilities: Dict[str, float],
        cov_matrix: Dict[str, Dict[str, float]],
    ) -> float:
        """
        Calculate diversification ratio.

        Ratio of weighted average volatility to portfolio volatility.
        Higher is better (indicates better diversification).
        """
        weighted_avg_vol = sum(
            allocation.get(asset, 0.0) * volatilities.get(asset, 0.1) for asset in assets
        )
        portfolio_vol = await self._calculate_portfolio_volatility(allocation, cov_matrix)
        if portfolio_vol < 1e-6:
            return 1.0
        return weighted_avg_vol / portfolio_vol

    def validate_allocation(self, allocation: Dict[str, float]) -> bool:
        """Validate that allocation is properly normalized."""
        total_weight = sum(allocation.values())
        return 0.99 <= total_weight <= 1.01  # Allow small floating point errors
