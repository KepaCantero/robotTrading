"""
Execute Strategy Use Case - Execute a trading strategy
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from app.domain.entities.order import Order, OrderSide, OrderType, OrderStatus
from app.models.signal import Signal, SignalType
from app.strategies.base import BaseStrategy


logger = logging.getLogger(__name__)


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
            logger.warning("No strategy configured, returning empty orders")
            return []

        # Apply parameters to strategy if provided
        if parameters:
            try:
                self._strategy.update_parameters(parameters)
                logger.debug(f"Applied parameters to strategy: {parameters}")
            except Exception as e:
                logger.error(f"Failed to apply strategy parameters: {e}")

        # Execute strategy and generate signals
        try:
            signals = self._strategy.generate_signals(symbol)
            logger.info(f"Generated {len(signals)} signals for {symbol}")
        except Exception as e:
            logger.error(f"Failed to generate signals for {symbol}: {e}")
            return []

        # Convert signals to orders
        orders = self._convert_signals_to_orders(signals, strategy_type)
        logger.info(f"Generated {len(orders)} orders from {len(signals)} signals")

        return orders

    def _convert_signals_to_orders(
        self,
        signals: List[Signal],
        strategy_type: str,
    ) -> List[Order]:
        """
        Convert trading signals to orders.

        Args:
            signals: List of trading signals
            strategy_type: Type of strategy that generated the signals

        Returns:
            List of orders generated from signals
        """
        orders = []

        for signal in signals:
            try:
                # Skip HOLD signals - they don't generate orders
                if signal.signal_type == SignalType.HOLD:
                    logger.debug(f"Skipping HOLD signal {signal.signal_id}")
                    continue

                # Skip signals that are not actionable (low confidence)
                if not signal.is_actionable:
                    logger.debug(
                        f"Skipping non-actionable signal {signal.signal_id} "
                        f"(confidence: {signal.confidence})"
                    )
                    continue

                # Convert signal to order
                order = self._signal_to_order(signal, strategy_type)
                if order:
                    orders.append(order)
                    logger.info(
                        f"Created order {order.order_id} for {signal.symbol} "
                        f"{signal.signal_type.value} @ {signal.price}"
                    )

            except Exception as e:
                logger.error(f"Failed to convert signal {signal.signal_id} to order: {e}")
                continue

        return orders

    def _signal_to_order(
        self,
        signal: Signal,
        strategy_type: str,
    ) -> Optional[Order]:
        """
        Convert a single signal to an order.

        Args:
            signal: Trading signal
            strategy_type: Type of strategy

        Returns:
            Order object or None if conversion fails
        """
        # Determine order side from signal type
        if signal.signal_type == SignalType.BUY:
            order_side = OrderSide.BUY
        elif signal.signal_type == SignalType.SELL:
            order_side = OrderSide.SELL
        else:
            return None  # HOLD signals don't generate orders

        # Create order ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        order_id = f"order_{strategy_type}_{signal.symbol}_{timestamp}"

        # Create the order
        order = Order(
            order_id=order_id,
            symbol=signal.symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=signal.volume,
            price=signal.price,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        # Store signal metadata in event history for traceability
        order.event_history.append(
            {
                "event": "generated_from_signal",
                "timestamp": datetime.utcnow().isoformat(),
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.value,
                "signal_confidence": signal.confidence,
                "signal_source": signal.source.value,
                "strategy_type": strategy_type,
            }
        )

        return order

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
