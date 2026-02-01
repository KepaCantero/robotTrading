"""
Rebalance Portfolio Use Case - Rebalance an existing portfolio
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd

from app.domain.entities.portfolio import Portfolio


class BasePortfolioOptimizer(Protocol):
    """
    Protocol for portfolio optimizers.

    This protocol defines the interface for portfolio optimization
    implementations that can be injected into the use case.
    """

    def optimize(self, returns: pd.DataFrame, **kwargs: Any) -> Dict[str, float]:
        """
        Optimize portfolio weights based on returns.

        Args:
            returns: DataFrame of asset returns
            **kwargs: Additional optimization parameters

        Returns:
            Dictionary mapping asset names to optimal weights
        """
        ...


class RebalancePortfolioUseCase:
    """
    Use case for rebalancing a portfolio.

    This use case orchestrates portfolio rebalancing using
    portfolio optimization algorithms.
    """

    def __init__(
        self,
        optimizer: Optional[BasePortfolioOptimizer] = None,
    ):
        """Initialize use case with optional optimizer."""
        self._optimizer = optimizer

    def execute(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, Decimal],
        rebalance_threshold: Decimal = Decimal("0.05"),
    ) -> List[str]:
        """
        Execute the use case - rebalance portfolio.

        Args:
            portfolio: Portfolio to rebalance
            target_weights: Target weights for each asset
            rebalance_threshold: Threshold for triggering rebalance

        Returns:
            List of rebalancing actions taken
        """
        if not self._optimizer:
            return ["No optimizer configured"]

        # Calculate current weights
        current_weights = self._get_current_weights(portfolio)

        # Check if rebalance is needed
        if not self._needs_rebalance(current_weights, target_weights, rebalance_threshold):
            return ["No rebalance needed"]

        # Generate rebalancing orders
        return self._generate_rebalance_orders(current_weights, target_weights)

    def _get_current_weights(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """
        Get current portfolio weights.

        Calculates the weight of each position as a percentage of total
        portfolio value (positions + cash).

        Args:
            portfolio: Portfolio to calculate weights for

        Returns:
            Dictionary mapping symbols to their current weights (as Decimals)
        """
        weights: Dict[str, Decimal] = {}

        # Get total portfolio value (cash + positions)
        total_value = portfolio.get_total_value().amount

        # Avoid division by zero
        if total_value == 0:
            return weights

        # Calculate weight for each position
        for symbol, position in portfolio.positions.items():
            position_value = position.get_value().amount
            weight = position_value / total_value
            weights[symbol] = weight

        return weights

    def _needs_rebalance(
        self,
        current: Dict[str, Decimal],
        target: Dict[str, Decimal],
        threshold: Decimal,
    ) -> bool:
        """
        Check if rebalancing is needed.

        Compares current weights against target weights and returns True
        if any asset deviates beyond the threshold.

        Args:
            current: Current portfolio weights by symbol
            target: Target weights by symbol
            threshold: Rebalance threshold (e.g., 0.05 for 5%)

        Returns:
            True if rebalancing is needed, False otherwise
        """
        # Get all unique symbols from both current and target
        all_symbols = set(current.keys()) | set(target.keys())

        for symbol in all_symbols:
            current_weight = current.get(symbol, Decimal("0"))
            target_weight = target.get(symbol, Decimal("0"))

            # Calculate absolute difference
            diff = abs(current_weight - target_weight)

            # Rebalance if difference exceeds threshold
            if diff > threshold:
                return True

        return False

    def _generate_rebalance_orders(
        self,
        current: Dict[str, Decimal],
        target: Dict[str, Decimal],
    ) -> List[str]:
        """
        Generate rebalancing orders.

        Creates a list of buy/sell orders to adjust current weights
        to target weights. Orders are returned as descriptive strings.

        Args:
            current: Current portfolio weights by symbol
            target: Target weights by symbol

        Returns:
            List of rebalancing actions as descriptive strings
        """
        orders: List[str] = []

        # Get all unique symbols from both current and target
        all_symbols = set(current.keys()) | set(target.keys())

        for symbol in all_symbols:
            current_weight = current.get(symbol, Decimal("0"))
            target_weight = target.get(symbol, Decimal("0"))

            # Calculate weight difference
            diff = target_weight - current_weight

            # Generate order if there's a meaningful difference
            # Using small epsilon to avoid noise
            epsilon = Decimal("0.0001")
            if abs(diff) > epsilon:
                if diff > 0:
                    # Need to buy/increase position
                    action = f"BUY {symbol}: increase weight by {diff:.4f} to reach target {target_weight:.4f}"
                else:
                    # Need to sell/decrease position
                    action = f"SELL {symbol}: decrease weight by {abs(diff):.4f} to reach target {target_weight:.4f}"
                orders.append(action)

        return orders
