"""
Strategy Combiner for Portfolio Weight Allocation.

This module implements various methods for combining trading strategies
into a portfolio with optimal weight allocations.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.ensemble.models import (
    AllocationMethod,
    CombinedPortfolio,
    StrategyAllocation,
)
from app.models.portfolio import MarketRegime

logger = logging.getLogger(__name__)


class StrategyCombiner:
    """Combine multiple trading strategies with optimal weight allocation.

    This class provides various methods for allocating capital across
    multiple strategies based on different optimization criteria:
    - Mean-variance optimization (Markowitz)
    - Risk parity allocation
    - Equal weight allocation
    - Regime-dependent allocation
    - Hierarchical risk parity

    Example:
        >>> combiner = StrategyCombiner(
        ...     strategies=['momentum', 'mean_reversion', 'trend'],
        ...     method=AllocationMethod.RISK_PARITY
        ... )
        >>> allocation = combiner.calculate_allocation(returns_data)
    """

    def __init__(
        self,
        strategies: List[str],
        method: AllocationMethod = AllocationMethod.RISK_PARITY,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        rebalance_threshold: float = 0.05,
    ):
        """Initialize strategy combiner.

        Args:
            strategies: List of strategy names
            method: Allocation method to use
            min_weight: Minimum weight for any strategy
            max_weight: Maximum weight for any strategy
            rebalance_threshold: Drift threshold for rebalancing

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            if not strategies or len(strategies) < 2:
                raise ValueError("At least 2 strategies required")

            if not (0 <= min_weight <= max_weight <= 1):
                raise ValueError(f"Invalid weight bounds: min={min_weight}, max={max_weight}")

            if not (0 < rebalance_threshold <= 1):
                raise ValueError(f"Invalid rebalance threshold: {rebalance_threshold}")

            self.strategies = strategies
            self.method = method
            self.min_weight = min_weight
            self.max_weight = max_weight
            self.rebalance_threshold = rebalance_threshold

            # Track current allocation
            self.current_allocation: Dict[str, Decimal] = self._initialize_allocation()

            # Track historical returns for regime detection
            self.returns_history: Dict[str, List[float]] = {s: [] for s in strategies}

        except (TypeError, AttributeError) as e:
            logger.error("StrategyCombiner initialization failed", exc_info=True)
            raise ValueError(f"Invalid parameters: {e}") from e

    def calculate_allocation(
        self,
        returns_data: Dict[str, np.ndarray],
        regime: Optional[MarketRegime] = None,
    ) -> List[StrategyAllocation]:
        """Calculate optimal strategy allocation.

        Args:
            returns_data: Historical returns for each strategy
            regime: Optional market regime for regime-dependent allocation

        Returns:
            List of strategy allocations

        Raises:
            ValueError: If data is invalid
        """
        try:
            # Validate input
            self._validate_returns_data(returns_data)

            # Calculate weights based on method
            if self.method == AllocationMethod.EQUAL_WEIGHT:
                weights = self._equal_weight_allocation()
            elif self.method == AllocationMethod.MEAN_VARIANCE:
                weights = self._mean_variance_allocation(returns_data)
            elif self.method == AllocationMethod.RISK_PARITY:
                weights = self._risk_parity_allocation(returns_data)
            elif self.method == AllocationMethod.REGIME_DEPENDENT:
                weights = self._regime_dependent_allocation(returns_data, regime)
            elif self.method == AllocationMethod.HIERARCHICAL_RISK_PARITY:
                weights = self._hierarchical_risk_parity_allocation(returns_data)
            elif self.method == AllocationMethod.BLACK_LITTERMAN:
                weights = self._black_litterman_allocation(returns_data)
            else:
                raise ValueError(f"Unsupported allocation method: {self.method}")

            # Apply weight constraints
            weights = self._apply_weight_constraints(weights)

            # Create allocation objects
            allocations = []
            for strategy in self.strategies:
                weight = Decimal(str(weights[strategy]))
                current_weight = self.current_allocation.get(strategy, Decimal("0"))

                allocation = StrategyAllocation(
                    strategy=strategy,
                    weight=weight,
                    target_weight=weight,
                    actual_weight=current_weight,
                )

                allocations.append(allocation)

            # Update current allocation
            self.current_allocation = {s: Decimal(str(weights[s])) for s in self.strategies}

            return allocations

        except Exception as e:
            logger.error("Allocation calculation failed", exc_info=True)
            raise RuntimeError(f"Allocation calculation failed: {e}") from e

    def _initialize_allocation(self) -> Dict[str, Decimal]:
        """Initialize equal allocation."""
        weight = Decimal(str(1.0 / len(self.strategies)))
        return {strategy: weight for strategy in self.strategies}

    def _validate_returns_data(self, returns_data: Dict[str, np.ndarray]) -> None:
        """Validate returns data.

        Args:
            returns_data: Returns data to validate

        Raises:
            ValueError: If data is invalid
        """
        if not returns_data:
            raise ValueError("Returns data cannot be empty")

        for strategy in self.strategies:
            if strategy not in returns_data:
                raise ValueError(f"Missing returns data for strategy: {strategy}")

            if not isinstance(returns_data[strategy], np.ndarray):
                raise ValueError(f"Returns for {strategy} must be numpy array")

            if len(returns_data[strategy]) < 2:
                raise ValueError(f"Insufficient data for {strategy}")

    def _equal_weight_allocation(self) -> Dict[str, float]:
        """Calculate equal weight allocation.

        Returns:
            Dictionary of equal weights for each strategy
        """
        weight = 1.0 / len(self.strategies)
        return {strategy: weight for strategy in self.strategies}

    def _mean_variance_allocation(self, returns_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate mean-variance optimal allocation (Markowitz).

        Maximizes: w'μ - λ * w'Σw
        where w = weights, μ = expected returns, Σ = covariance matrix

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Dictionary of optimal weights
        """
        try:
            n = len(self.strategies)

            # Calculate expected returns (mean)
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            expected_returns = np.mean(returns_matrix, axis=0)

            # Calculate covariance matrix
            cov_matrix = np.cov(returns_matrix, rowvar=False)

            # Add small regularization to ensure positive semi-definite
            cov_matrix = cov_matrix + np.eye(n) * 1e-8

            # Solve quadratic optimization
            # For simplicity, use tangency portfolio (max Sharpe)
            try:
                # Inverse covariance
                inv_cov = np.linalg.inv(cov_matrix)

                # Equal risk aversion (λ = 1)
                weights = inv_cov @ expected_returns

                # Normalize weights
                weights = np.maximum(weights, 0)  # Long only
                weights = weights / np.sum(weights)

            except np.linalg.LinAlgError:
                # Fallback to equal weights if singular matrix
                return self._equal_weight_allocation()

            # Convert to dictionary
            return {strategy: float(weights[i]) for i, strategy in enumerate(self.strategies)}

        except Exception:
            logger.error("Mean-variance allocation failed", exc_info=True)
            return self._equal_weight_allocation()

    def _risk_parity_allocation(self, returns_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate risk parity allocation.

        Risk parity allocates weights such that each strategy contributes
        equal risk to the portfolio.

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Dictionary of risk parity weights
        """
        try:
            n = len(self.strategies)

            # Calculate covariance matrix
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            cov_matrix = np.cov(returns_matrix, rowvar=False)

            # Add small regularization
            cov_matrix = cov_matrix + np.eye(n) * 1e-8

            # Risk parity weights are proportional to 1/sqrt(diagonal(cov))
            # This is a simple approximation
            volatilities = np.sqrt(np.diag(cov_matrix))
            inv_vols = 1.0 / volatilities
            weights = inv_vols / np.sum(inv_vols)

            # Convert to dictionary
            return {strategy: float(weights[i]) for i, strategy in enumerate(self.strategies)}

        except Exception:
            logger.error("Risk parity allocation failed", exc_info=True)
            return self._equal_weight_allocation()

    def _regime_dependent_allocation(
        self,
        returns_data: Dict[str, np.ndarray],
        regime: Optional[MarketRegime] = None,
    ) -> Dict[str, float]:
        """Calculate regime-dependent allocation.

        Adjusts strategy allocation based on market regime.

        Args:
            returns_data: Historical returns for each strategy
            regime: Current market regime

        Returns:
            Dictionary of regime-adjusted weights
        """
        try:
            # Start with risk parity base
            base_weights = self._risk_parity_allocation(returns_data)

            if regime is None:
                return base_weights

            # Adjust weights based on regime
            adjustments = self._get_regime_adjustments(regime)

            # Apply adjustments
            adjusted_weights = {}
            for strategy, weight in base_weights.items():
                adjustment = adjustments.get(strategy, 1.0)
                adjusted_weights[strategy] = weight * adjustment

            # Normalize
            total = sum(adjusted_weights.values())
            if total > 0:
                adjusted_weights = {k: v / total for k, v in adjusted_weights.items()}

            return adjusted_weights

        except Exception:
            logger.error("Regime-dependent allocation failed", exc_info=True)
            return self._equal_weight_allocation()

    def _get_regime_adjustments(self, regime: MarketRegime) -> Dict[str, float]:
        """Get weight adjustments for a given regime.

        Args:
            regime: Market regime

        Returns:
            Dictionary of adjustment factors
        """
        # Define regime-based adjustments
        # These are heuristic and should be calibrated
        adjustments = {}

        if regime == MarketRegime.TRENDING_UP:
            # Favor trend-following strategies
            adjustments = {
                "trend_following": 1.5,
                "momentum": 1.3,
                "mean_reversion": 0.7,
                "arbitrage": 0.8,
            }
        elif regime == MarketRegime.TRENDING_DOWN:
            # Favor defensive strategies
            adjustments = {
                "trend_following": 0.6,
                "momentum": 0.7,
                "mean_reversion": 1.2,
                "arbitrage": 1.0,
            }
        elif regime == MarketRegime.RANGING:
            # Favor mean reversion
            adjustments = {
                "trend_following": 0.7,
                "momentum": 0.9,
                "mean_reversion": 1.4,
                "arbitrage": 1.1,
            }
        elif regime == MarketRegime.VOLATILE:
            # Favor low-volatility strategies
            adjustments = {
                "trend_following": 0.8,
                "momentum": 0.9,
                "mean_reversion": 1.1,
                "arbitrage": 1.2,
            }
        else:  # UNKNOWN
            # Use equal weights
            adjustments = {s: 1.0 for s in self.strategies}

        # Fill in missing strategies
        for strategy in self.strategies:
            if strategy not in adjustments:
                adjustments[strategy] = 1.0

        return adjustments

    def _hierarchical_risk_parity_allocation(
        self, returns_data: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """Calculate hierarchical risk parity (HRP) allocation.

        HRP uses hierarchical clustering to allocate capital based on
        correlation structure, providing better out-of-sample performance.

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Dictionary of HRP weights
        """
        try:
            # Calculate correlation matrix
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            corr_matrix = np.corrcoef(returns_matrix, rowvar=False)

            # Simple HRP implementation using inverse distance weighting
            # Convert correlation to distance
            distance_matrix = np.sqrt(2 * (1 - corr_matrix))

            # Calculate weights as inverse of average distance
            avg_distances = np.mean(distance_matrix, axis=1)
            inv_distances = 1.0 / (avg_distances + 1e-8)
            weights = inv_distances / np.sum(inv_distances)

            # Convert to dictionary
            return {strategy: float(weights[i]) for i, strategy in enumerate(self.strategies)}

        except Exception:
            logger.error("HRP allocation failed", exc_info=True)
            return self._equal_weight_allocation()

    def _black_litterman_allocation(self, returns_data: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate Black-Litterman allocation.

        Combines market equilibrium with investor views to produce
        more stable portfolio allocations.

        Args:
            returns_data: Historical returns for each strategy

        Returns:
            Dictionary of Black-Litterman weights
        """
        try:
            n = len(self.strategies)

            # Calculate market parameters
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            cov_matrix = np.cov(returns_matrix, rowvar=False)
            cov_matrix = cov_matrix + np.eye(n) * 1e-8

            # Market equilibrium returns (simplified as historical means)
            pi = np.mean(returns_matrix, axis=0)

            # No investor views (use equilibrium)
            mu = pi

            # Calculate optimal weights
            inv_cov = np.linalg.inv(cov_matrix)
            weights = inv_cov @ mu

            # Normalize and enforce long-only
            weights = np.maximum(weights, 0)
            weights = weights / np.sum(weights)

            # Convert to dictionary
            return {strategy: float(weights[i]) for i, strategy in enumerate(self.strategies)}

        except Exception:
            logger.error("Black-Litterman allocation failed", exc_info=True)
            return self._equal_weight_allocation()

    def _apply_weight_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply min/max weight constraints.

        Args:
            weights: Raw weights

        Returns:
            Constrained weights
        """
        # Apply min/max bounds
        constrained = {k: max(self.min_weight, min(self.max_weight, v)) for k, v in weights.items()}

        # Normalize to sum to 1
        total = sum(constrained.values())

        if total > 0:
            constrained = {k: v / total for k, v in constrained.items()}

        return constrained

    def calculate_portfolio_metrics(
        self,
        allocation: List[StrategyAllocation],
        returns_data: Dict[str, np.ndarray],
    ) -> CombinedPortfolio:
        """Calculate combined portfolio metrics.

        Args:
            allocation: Strategy allocation
            returns_data: Historical returns data

        Returns:
            Combined portfolio metrics
        """
        try:
            # Get weights
            weights = np.array([float(a.weight) for a in allocation])

            # Calculate weighted returns
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            portfolio_returns = returns_matrix @ weights

            # Calculate metrics
            total_return = Decimal(str(np.mean(portfolio_returns) * 252))
            volatility = Decimal(str(np.std(portfolio_returns) * np.sqrt(252)))

            # Sharpe ratio (assuming risk-free rate = 0)
            sharpe = total_return / volatility if volatility > 0 else Decimal("0")

            # Sortino ratio
            negative_returns = portfolio_returns[portfolio_returns < 0]
            downside_risk = (
                np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0
            )
            sortino = (
                total_return / Decimal(str(downside_risk)) if downside_risk > 0 else Decimal("0")
            )

            # Max drawdown (negative value)
            cumulative = np.cumprod(1 + portfolio_returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = Decimal(str(np.min(drawdown)))  # Already negative

            # Diversification ratio
            div_ratio = self._calculate_diversification_ratio(allocation, returns_data)

            # Effective number of strategies
            effective_n = self._calculate_effective_number_strategies(weights)

            # Mean correlation
            mean_corr = self._calculate_mean_correlation(returns_data, weights)

            return CombinedPortfolio(
                total_return=total_return,
                volatility=volatility,
                sharpe_ratio=sharpe,
                sortino_ratio=sortino,
                max_drawdown=max_drawdown,
                diversification_ratio=div_ratio,
                effective_n_strategies=effective_n,
                correlation_mean=mean_corr,
                allocation=allocation,
            )

        except Exception as e:
            logger.error("Portfolio metrics calculation failed", exc_info=True)
            raise RuntimeError(f"Portfolio metrics calculation failed: {e}") from e

    def _calculate_diversification_ratio(
        self,
        allocation: List[StrategyAllocation],
        returns_data: Dict[str, np.ndarray],
    ) -> Decimal:
        """Calculate diversification ratio.

        The diversification ratio is the weighted average volatility divided
        by portfolio volatility. Values > 1 indicate diversification benefits.

        Args:
            allocation: Strategy allocation
            returns_data: Returns data

        Returns:
            Diversification ratio
        """
        try:
            weights = np.array([float(a.weight) for a in allocation])

            # Calculate individual volatilities
            vols = []
            for strategy in self.strategies:
                vol = np.std(returns_data[strategy]) * np.sqrt(252)
                vols.append(vol)

            # Weighted average volatility
            weighted_avg_vol = np.dot(weights, vols)

            # Portfolio volatility
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            portfolio_returns = returns_matrix @ weights
            portfolio_vol = np.std(portfolio_returns) * np.sqrt(252)

            if portfolio_vol == 0:
                return Decimal("1.0")

            return Decimal(str(weighted_avg_vol / portfolio_vol))

        except Exception:
            logger.error("Diversification ratio calculation failed", exc_info=True)
            return Decimal("1.0")

    def _calculate_effective_number_strategies(self, weights: np.ndarray) -> float:
        """Calculate effective number of strategies.

        Effective N = exp(-sum(w * log(w)))
        Measures diversification across strategies.

        Args:
            weights: Strategy weights

        Returns:
            Effective number of strategies
        """
        try:
            # Filter out zero weights
            non_zero = weights[weights > 0]

            if len(non_zero) == 0:
                return 1.0

            # Calculate entropy-based measure
            effective_n = np.exp(-np.sum(non_zero * np.log(non_zero)))

            return float(effective_n)

        except Exception:
            logger.error("Effective number of strategies calculation failed", exc_info=True)
            return 1.0

    def _calculate_mean_correlation(
        self,
        returns_data: Dict[str, np.ndarray],
        weights: np.ndarray,
    ) -> Decimal:
        """Calculate weighted mean correlation.

        Args:
            returns_data: Returns data
            weights: Strategy weights

        Returns:
            Weighted mean correlation
        """
        try:
            # Calculate correlation matrix
            returns_matrix = np.column_stack([returns_data[s] for s in self.strategies])
            corr_matrix = np.corrcoef(returns_matrix, rowvar=False)

            # Calculate weighted mean correlation
            n = len(self.strategies)
            total_weight = 0.0
            weighted_corr_sum = 0.0

            for i in range(n):
                for j in range(i + 1, n):
                    weight = weights[i] * weights[j]
                    weighted_corr_sum += weight * corr_matrix[i, j]
                    total_weight += weight

            if total_weight == 0:
                return Decimal("0")

            mean_corr = weighted_corr_sum / total_weight

            return Decimal(str(mean_corr))

        except Exception:
            logger.error("Mean correlation calculation failed", exc_info=True)
            return Decimal("0")

    def needs_rebalancing(self, allocation: List[StrategyAllocation]) -> bool:
        """Check if portfolio needs rebalancing.

        Args:
            allocation: Current allocation

        Returns:
            True if rebalancing is needed
        """
        for alloc in allocation:
            if alloc.needs_rebalance:
                return True
        return False

    def rebalance(
        self,
        current_allocation: List[StrategyAllocation],
        target_allocation: List[StrategyAllocation],
    ) -> Dict[str, Decimal]:
        """Calculate rebalancing trades.

        Args:
            current_allocation: Current allocation
            target_allocation: Target allocation

        Returns:
            Dictionary of trades (positive = buy, negative = sell)
        """
        trades = {}

        current_dict = {a.strategy: a.actual_weight for a in current_allocation}
        target_dict = {a.strategy: a.target_weight for a in target_allocation}

        for strategy in self.strategies:
            current = current_dict.get(strategy, Decimal("0"))
            target = target_dict.get(strategy, Decimal("0"))
            trades[strategy] = target - current

        return trades

    def get_allocation_summary(self, allocation: List[StrategyAllocation]) -> Dict[str, Any]:
        """Get summary of allocation.

        Args:
            allocation: Strategy allocation

        Returns:
            Summary dictionary
        """
        try:
            return {
                "num_strategies": len(allocation),
                "max_weight": float(max(a.weight for a in allocation)),
                "min_weight": float(min(a.weight for a in allocation)),
                "weight_concentration": float(
                    max(a.weight for a in allocation) - min(a.weight for a in allocation)
                ),
                "needs_rebalance": self.needs_rebalancing(allocation),
                "strategies": [a.strategy for a in allocation],
                "weights": {a.strategy: float(a.weight) for a in allocation},
            }

        except Exception:
            logger.error("Allocation summary calculation failed", exc_info=True)
            return {}
