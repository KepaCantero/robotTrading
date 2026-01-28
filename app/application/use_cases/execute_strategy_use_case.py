"""
Execute Strategy Use Case - Execute a trading strategy
"""

from typing import Dict, List, Optional

from app.domain.entities.order import Order
from app.strategies.base import BaseStrategy


class ExecuteStrategyUseCase:
    """
    Use case for executing a trading strategy.

    This use case orchestrates strategy execution and order generation.
    """

    def __init__(self, strategy: Optional[BaseStrategy] = None):
        """Initialize use case with optional strategy."""
        self._strategy = strategy

    def execute(
        self,
        symbol: str,
        strategy_type: str,
        parameters: Optional[Dict] = None,
    ) -> List[Order]:
        """
        Execute the use case - run strategy and generate orders.

        Args:
            symbol: Trading symbol
            strategy_type: Type of strategy to execute
            parameters: Strategy parameters

        Returns:
            List of generated orders
        """
        if not self._strategy:
            # Return empty orders if no strategy configured
            return []

        # Execute strategy and generate signals
        signals = self._strategy.generate_signals(symbol)

        # Convert signals to orders (simplified)
        # In real implementation, this would be more complex
        return []

    def validate_strategy_config(self, config: Dict) -> bool:
        """
        Validate strategy configuration.

        Args:
            config: Strategy configuration dictionary

        Returns:
            True if configuration is valid
        """
        if not self._strategy:
            return False

        return self._strategy.validate_config(config)
