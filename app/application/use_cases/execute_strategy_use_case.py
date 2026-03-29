"""
Execute Strategy Use Case - Execute a trading strategy
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from app.domain.models.signal import Signal, SignalType

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote
    from app.domain.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class ExecuteStrategyUseCase:
    """
    Use case for executing a trading strategy.

    This use case orchestrates strategy execution and order generation.
    """

    def __init__(self, strategy: BaseStrategy | None = None) -> None:
        """Initialize use case with optional strategy."""
        self._strategy = strategy
        self._correlation_id: str | None = None
        self._max_position_size: float = 1000000.0  # Default max position size

    def execute(
        self,
        market_data: Quote,
        strategy_type: str,
        parameters: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> list[Order]:
        """
        Execute the use case - run strategy and generate orders.

        Args:
            market_data: Market data quote for signal generation
            strategy_type: Type of strategy to execute
            parameters: Strategy parameters
            correlation_id: Optional correlation ID for tracing

        Returns:
            List of generated orders

        Raises:
            ValueError: If parameter application fails
        """
        self._correlation_id = correlation_id

        if not self._strategy:
            log_msg = "No strategy configured, returning empty orders"
            if self._correlation_id:
                logger.warning(f"{log_msg}", extra={"correlation_id": self._correlation_id})
            else:
                logger.warning(log_msg)
            return []

        # Apply parameters to strategy if provided
        if parameters:
            try:
                self._strategy.update_parameters(parameters)
                log_msg = f"Applied parameters to strategy: {parameters}"
                if self._correlation_id:
                    logger.debug(log_msg, extra={"correlation_id": self._correlation_id})
                else:
                    logger.debug(log_msg)
            except (TypeError, KeyError, ValueError) as e:
                log_msg = f"Failed to apply strategy parameters: {e}"
                if self._correlation_id:
                    logger.error(
                        log_msg, exc_info=True, extra={"correlation_id": self._correlation_id}
                    )
                else:
                    logger.error(log_msg, exc_info=True)
                raise ValueError(f"Invalid strategy parameters: {e}") from e

        # Execute strategy and generate signals with timeout protection
        try:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._strategy.generate_signals, market_data)
                try:
                    signals = future.result(timeout=30)  # 30 second timeout
                except concurrent.futures.TimeoutError:
                    log_msg = f"Strategy signal generation timed out for {market_data.symbol}"
                    if self._correlation_id:
                        logger.error(log_msg, extra={"correlation_id": self._correlation_id})
                    else:
                        logger.error(log_msg)
                    return []

            log_msg = f"Generated {len(signals)} signals for {market_data.symbol}"
            if self._correlation_id:
                logger.info(log_msg, extra={"correlation_id": self._correlation_id})
            else:
                logger.info(log_msg)
        except (AttributeError, ValueError, TypeError) as e:
            log_msg = f"Failed to generate signals for {market_data.symbol}: {e}"
            if self._correlation_id:
                logger.error(log_msg, exc_info=True, extra={"correlation_id": self._correlation_id})
            else:
                logger.error(log_msg, exc_info=True)
            return []

        # Convert signals to orders
        orders = self._convert_signals_to_orders(signals, strategy_type)
        log_msg = f"Generated {len(orders)} orders from {len(signals)} signals"
        if self._correlation_id:
            logger.info(log_msg, extra={"correlation_id": self._correlation_id})
        else:
            logger.info(log_msg)

        return orders

    def _convert_signals_to_orders(
        self,
        signals: list[Signal],
        strategy_type: str,
    ) -> list[Order]:
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
                    log_msg = f"Skipping HOLD signal {signal.signal_id}"
                    if self._correlation_id:
                        logger.debug(log_msg, extra={"correlation_id": self._correlation_id})
                    else:
                        logger.debug(log_msg)
                    continue

                # Skip signals that are not actionable (low confidence)
                if not signal.is_actionable:
                    log_msg = (
                        f"Skipping non-actionable signal {signal.signal_id} "
                        f"(confidence: {signal.confidence})"
                    )
                    if self._correlation_id:
                        logger.debug(log_msg, extra={"correlation_id": self._correlation_id})
                    else:
                        logger.debug(log_msg)
                    continue

                # Convert signal to order
                order = self._signal_to_order(signal, strategy_type)
                if order:
                    orders.append(order)
                    log_msg = (
                        f"Created order {order.order_id} for {signal.symbol} "
                        f"{signal.signal_type.value} @ {signal.price}"
                    )
                    if self._correlation_id:
                        logger.info(log_msg, extra={"correlation_id": self._correlation_id})
                    else:
                        logger.info(log_msg)

            except (ValueError, TypeError, AttributeError) as e:
                log_msg = f"Failed to convert signal {signal.signal_id} to order: {e}"
                if self._correlation_id:
                    logger.error(
                        log_msg, exc_info=True, extra={"correlation_id": self._correlation_id}
                    )
                else:
                    logger.error(log_msg, exc_info=True)
                continue

        return orders

    def _signal_to_order(
        self,
        signal: Signal,
        strategy_type: str,
    ) -> Order | None:
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

        # P0: Validate trading quantity before order creation
        if signal.volume is None:
            log_msg = f"Signal {signal.signal_id} has no volume, skipping order creation"
            if self._correlation_id:
                logger.warning(log_msg, extra={"correlation_id": self._correlation_id})
            else:
                logger.warning(log_msg)
            return None

        if signal.volume <= 0:
            log_msg = f"Signal {signal.signal_id} has invalid volume {signal.volume}, must be > 0"
            if self._correlation_id:
                logger.warning(log_msg, extra={"correlation_id": self._correlation_id})
            else:
                logger.warning(log_msg)
            return None

        # Calculate position value and check against max position size
        position_value = signal.volume * signal.price if signal.price else 0
        if position_value > self._max_position_size:
            log_msg = (
                f"Signal {signal.signal_id} position value {position_value} "
                f"exceeds max position size {self._max_position_size}, skipping order"
            )
            if self._correlation_id:
                logger.warning(log_msg, extra={"correlation_id": self._correlation_id})
            else:
                logger.warning(log_msg)
            return None

        # Create order ID with timezone-aware datetime (P1-2 fix)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
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
            created_at=datetime.now(timezone.utc),  # P1-2 fix: timezone-aware datetime
        )

        # Store signal metadata in event history for traceability
        order.event_history.append(
            {
                "event": "generated_from_signal",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),  # P1-2 fix: timezone-aware datetime
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type.value,
                "signal_confidence": signal.confidence,
                "signal_source": signal.source.value,
                "strategy_type": strategy_type,
            }
        )

        return order

    def validate_strategy_config(self, config: dict) -> bool:
        """
        Validate strategy configuration.

        Args:
            config: Strategy configuration dictionary (not used, strategy already has config)

        Returns:
            True if configuration is valid
        """
        if not self._strategy:
            return False

        return self._strategy.validate_config()
