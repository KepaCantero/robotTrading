"""
Trade Executor service for backtesting.

This service is responsible for executing buy and sell trades with all
necessary validations including liquidity, position sizing, and cost calculations.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Callable, Optional
from uuid import uuid4

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator
from app.backtesting.services.position_manager import PositionManager
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Executes trades with full validation and cost calculation.

    This service handles:
    - Buy order execution with all validations
    - Sell order execution with P&L calculation
    - Position size calculation based on risk
    - Commission and slippage application
    - Liquidity-aware execution

    Dependencies:
    - LiquidityValidator: Realistic order execution simulation
    - TradingValidator: Position size and stop-loss validation
    - PositionManager: Track and update positions
    - ProfitAndLossCalculator: Calculate trade profitability
    - config: Backtest configuration
    """

    def __init__(
        self,
        config: BacktestConfig,
        position_manager: PositionManager,
        pnl_calculator: ProfitAndLossCalculator,
        diagnostic_logger: Optional[Any] = None,
        strategy: Optional[Any] = None,
    ):
        """
        Initialize the TradeExecutor.

        Args:
            config: Backtest configuration
            position_manager: PositionManager instance
            pnl_calculator: ProfitAndLossCalculator instance
            diagnostic_logger: Optional diagnostic logger
            strategy: Optional strategy instance for custom parameters
        """
        from app.backtesting.liquidity_validator import LiquidityValidator
        from app.core.trading_validators import TradingValidator

        self.config = config
        self.position_manager = position_manager
        self.pnl_calculator = pnl_calculator
        self.diagnostic_logger = diagnostic_logger
        self.strategy = strategy

        # Initialize validators
        self.trading_validator = TradingValidator()
        self.liquidity_validator = LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),
        )

    def execute_buy_signal(
        self,
        signal: Signal,
        market_data: Any,
        capital: Decimal,
        close_position_func: Callable,
        validate_profitability_func: Callable,
    ) -> tuple[Optional[Trade], Decimal]:
        """
        Execute a buy signal with all validations.

        Args:
            signal: Buy signal to execute
            market_data: Current market data
            capital: Current available capital
            close_position_func: Function to close existing positions
            validate_profitability_func: Function to validate trade profitability

        Returns:
            Tuple of (executed_trade or None, updated_capital)
        """
        from app.backtesting.engine import get_price

        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # Skip BUY signal if already holding a position
        # CRITICAL FIX: Don't close and reopen - just skip to prevent commission losses
        current_position = self.position_manager.get_position(signal.symbol)
        if current_position > 0:
            logger.debug(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"Skipping - already holding position ({current_position:.6f})"
            )
            return None, capital

        current_price = get_price(market_data)

        # Validate trade profitability
        if not validate_profitability_func(signal, current_price):
            return None, capital

        # Calculate position size
        position_size = self._calculate_position_size(signal, current_price, capital)
        logger.info(
            f"BUY {signal.symbol} (strategy={strategy_name}): "
            f"position_size={position_size}, price={current_price}, capital={capital}"
        )

        if position_size <= 0:
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): " f"position_size <= 0, skipping"
            )
            return None, capital

        # Validate position size
        try:
            position_value = position_size * current_price
            self.trading_validator.validate_position_size(
                capital=capital,
                position_size=position_value,
                max_position_percent=self.config.max_position_size,
            )
        except ValueError as e:
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"Position size validation failed: {e}"
            )
            return None, capital

        # Validate stop-loss
        if self.config.stop_loss_percentage is not None:
            try:
                stop_loss_price = current_price * (
                    Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
                )
                self.trading_validator.validate_stop_loss(
                    entry_price=current_price, stop_loss=stop_loss_price, side="long"
                )
            except ValueError as e:
                logger.warning(
                    f"BUY {signal.symbol} (strategy={strategy_name}): "
                    f"Stop-loss validation failed: {e}"
                )
                return None, capital

        # Validate liquidity
        fill_result = self.liquidity_validator.simulate_fill(
            order_quantity=position_size,
            current_bar=market_data,
            order_side="buy",
            symbol=signal.symbol,
        )

        if fill_result.fill_status == "REJECTED":
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"Liquidity validation FAILED - {fill_result.rejection_reason}"
            )
            if self.diagnostic_logger:
                self.diagnostic_logger.log_signal_rejected(
                    strategy_name,
                    signal.symbol,
                    "liquidity_validation",
                    fill_result.rejection_reason,
                    signal.metadata if hasattr(signal, "metadata") else {},
                )
            return None, capital

        if fill_result.fill_status == "PARTIAL":
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"Partial fill - requested {position_size:.0f}, "
                f"filled {fill_result.filled_quantity:.0f} shares"
            )
            position_size = fill_result.filled_quantity

        execution_price = fill_result.fill_price

        if fill_result.market_impact and fill_result.market_impact > Decimal("0.005"):
            logger.info(f"BUY {signal.symbol}: Market impact = {fill_result.market_impact:.2%}")

        # Check capital availability
        total_cost = position_size * execution_price
        if total_cost > capital:
            logger.info(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"total_cost ({total_cost}) > capital ({capital}), adjusting position_size"
            )
            position_size = capital / execution_price

        if position_size <= 0:
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"adjusted position_size <= 0, skipping"
            )
            return None, capital

        # Calculate commission
        commission_pct = self._get_strategy_commission(signal, strategy_name)
        trade_value = position_size * execution_price
        if commission_pct is not None:
            commission = trade_value * (commission_pct / Decimal("100"))
        else:
            commission = self.config.commission_per_trade

        # Calculate costs
        slippage_cost = abs(position_size * (execution_price - current_price))
        total_cost = position_size * execution_price + commission

        logger.info(
            f"BUY {signal.symbol} (strategy={strategy_name}): "
            f"execution_price=${execution_price:.4f}, "
            f"commission=${commission:.2f}, "
            f"slippage_cost=${slippage_cost:.2f}, total_cost=${total_cost:.2f}"
        )

        if total_cost > capital:
            logger.warning(
                f"BUY {signal.symbol} (strategy={strategy_name}): "
                f"total_cost ({total_cost}) > capital ({capital}), skipping"
            )
            return None, capital

        # Create trade
        reason = self._build_trade_reason(signal, market_data)
        trade_id = str(uuid4())

        trade = Trade(
            trade_id=trade_id,
            symbol=signal.symbol,
            side="buy",
            quantity=position_size,
            entry_price=execution_price,
            entry_time=market_data.timestamp,
            status=TradeStatus.OPEN,
            commission=commission,
            slippage=slippage_cost,
            reason=reason,
        )

        logger.info(
            f"EXECUTING BUY: {signal.symbol} qty={position_size} price=${execution_price:.4f}"
        )

        # Update position
        self.position_manager.update_position(signal.symbol, position_size)

        # Log execution
        if self.diagnostic_logger:
            self.diagnostic_logger.log_signal_executed(
                strategy_name=strategy_name,
                symbol=signal.symbol,
                metadata=signal.metadata if signal.metadata else {},
            )

        return trade, capital - total_cost

    def execute_sell_signal(
        self,
        signal: Signal,
        market_data: Any,
        capital: Decimal,
        trades: list[Trade],
    ) -> tuple[Optional[Trade], Decimal]:
        """
        Execute a sell signal with P&L calculation.

        Args:
            signal: Sell signal to execute
            market_data: Current market data
            capital: Current available capital
            trades: List of existing trades

        Returns:
            Tuple of (executed_trade or None, updated_capital)
        """
        from app.backtesting.engine import get_price

        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        current_position = self.position_manager.get_position(signal.symbol)

        if current_position <= 0:
            logger.warning(
                f"SELL {signal.symbol} (strategy={strategy_name}): "
                f"No position to sell (position={current_position})"
            )
            return None, capital

        current_price = get_price(market_data)

        # Calculate sell quantity
        calculated_sell_size = self._calculate_position_size(signal, current_price, capital)
        sell_quantity = min(current_position, calculated_sell_size)

        logger.info(
            f"SELL {signal.symbol} (strategy={strategy_name}): "
            f"calculated_sell_size={calculated_sell_size}, "
            f"sell_quantity={sell_quantity}, current_position={current_position}"
        )

        if sell_quantity <= 0:
            logger.warning(
                f"SELL {signal.symbol} (strategy={strategy_name}): sell_quantity <= 0, skipping"
            )
            return None, capital

        # Validate liquidity
        fill_result = self.liquidity_validator.simulate_fill(
            order_quantity=sell_quantity,
            current_bar=market_data,
            order_side="sell",
            symbol=signal.symbol,
        )

        if fill_result.fill_status == "REJECTED":
            logger.warning(
                f"SELL {signal.symbol} (strategy={strategy_name}): "
                f"Liquidity validation FAILED - {fill_result.rejection_reason}"
            )
            if self.diagnostic_logger:
                self.diagnostic_logger.log_signal_rejected(
                    strategy_name,
                    signal.symbol,
                    "liquidity_validation",
                    fill_result.rejection_reason,
                    signal.metadata if hasattr(signal, "metadata") else {},
                )
            return None, capital

        if fill_result.fill_status == "PARTIAL":
            logger.warning(
                f"SELL {signal.symbol} (strategy={strategy_name}): "
                f"Partial fill - requested {sell_quantity:.0f}, "
                f"filled {fill_result.filled_quantity:.0f} shares"
            )
            sell_quantity = fill_result.filled_quantity

        execution_price = fill_result.fill_price

        if fill_result.market_impact and fill_result.market_impact > Decimal("0.005"):
            logger.info(f"SELL {signal.symbol}: Market impact = {fill_result.market_impact:.2%}")

        # Calculate commission
        commission_pct = self._get_strategy_commission(signal, strategy_name)
        trade_value = sell_quantity * execution_price
        if commission_pct is not None:
            commission = trade_value * (commission_pct / Decimal("100"))
        else:
            commission = self.config.commission_per_trade

        # Calculate proceeds
        slippage_cost = abs(sell_quantity * (execution_price - current_price))
        proceeds = sell_quantity * execution_price - commission

        logger.info(
            f"SELL {signal.symbol} (strategy={strategy_name}): "
            f"execution_price=${execution_price:.4f}, "
            f"commission=${commission:.2f}, "
            f"slippage_cost=${slippage_cost:.2f}, proceeds=${proceeds:.2f}"
        )

        # Calculate P&L using PnL calculator
        pnl_info = self.pnl_calculator.calculate_sell_pnl(
            trades=trades,
            symbol=signal.symbol,
            sell_quantity=sell_quantity,
            execution_price=execution_price,
            commission=commission,
        )

        # Create trade
        reason = self._build_trade_reason(signal, market_data)
        trade_id = str(uuid4())

        trade = Trade(
            trade_id=trade_id,
            symbol=signal.symbol,
            side="sell",
            quantity=sell_quantity,
            entry_price=pnl_info["avg_buy_price"] if pnl_info["buy_trades"] else execution_price,
            exit_price=execution_price,
            entry_time=pnl_info["entry_time"] if pnl_info["buy_trades"] else market_data.timestamp,
            exit_time=market_data.timestamp,
            status=TradeStatus.CLOSED,
            pnl=pnl_info["pnl"],
            pnl_percentage=pnl_info["pnl_percentage"],
            commission=commission,
            slippage=slippage_cost,
            reason=reason,
        )

        # Close matching buy trades
        for buy_trade in pnl_info["buy_trades"]:
            if sell_quantity > 0:
                closed_qty = min(buy_trade.quantity, sell_quantity)
                sell_quantity -= closed_qty
                if closed_qty >= buy_trade.quantity:
                    buy_trade.status = TradeStatus.CLOSED
                    buy_trade.exit_price = execution_price
                    buy_trade.exit_time = market_data.timestamp

        # Update position
        closed_quantity = sum(t.quantity for t in pnl_info["buy_trades"])
        self.position_manager.update_position(signal.symbol, -closed_quantity)

        logger.info(
            f"EXECUTING SELL: {signal.symbol} qty={closed_quantity} price=${execution_price:.4f}"
        )

        # Log execution
        if self.diagnostic_logger:
            self.diagnostic_logger.log_signal_executed(
                strategy_name=strategy_name,
                symbol=signal.symbol,
                metadata=signal.metadata if signal.metadata else {},
            )

        return trade, capital + proceeds

    def _calculate_position_size(self, signal: Signal, price: Decimal, capital: Decimal) -> Decimal:
        """Calculate position size based on signal and risk management."""
        from decimal import ROUND_HALF_UP

        confidence_factor = Decimal(str(max(signal.confidence / 100.0, 0.5)))
        max_position_value = capital * self.config.max_position_size

        position_value = max_position_value * confidence_factor

        # Adjust for commission ratio
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
        commission_pct = self._get_strategy_commission(signal, strategy_name)

        if commission_pct is None:
            commission = self.config.commission_per_trade
            if commission > 0:
                round_trip_commission = commission * 2
                current_commission_ratio = (
                    round_trip_commission / position_value if position_value > 0 else Decimal("1")
                )

                if current_commission_ratio > Decimal("0.01"):
                    min_position_value = round_trip_commission / Decimal("0.01")
                    position_value = max(position_value, min_position_value)
                    position_value = min(position_value, max_position_value)

                    logger.info(
                        f"Adjusted position value for {signal.symbol} from "
                        f"${max_position_value * confidence_factor:.2f} "
                        f"to ${position_value:.2f} to maintain commission ratio <= 1%"
                    )

        # Ensure minimum position value
        min_position_value = capital * Decimal("0.01")
        position_value = max(position_value, min_position_value)

        position_size = position_value / price
        min_size = Decimal("1")
        position_size = max(position_size, min_size)

        return position_size.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _get_strategy_commission(self, signal: Signal, strategy_name: str) -> Optional[Decimal]:
        """Get commission percentage for strategy."""
        from decimal import InvalidOperation

        if signal.metadata and "commission_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["commission_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation):
                pass

        if self.strategy and hasattr(self.strategy, "commission_per_trade_pct"):
            return self.strategy.commission_per_trade_pct

        return None

    def _get_strategy_slippage(self, signal: Signal) -> Optional[Decimal]:
        """Get slippage percentage for strategy."""
        from decimal import InvalidOperation

        if signal.metadata and "slippage_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["slippage_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation):
                pass

        if self.strategy and hasattr(self.strategy, "slippage_per_trade_pct"):
            return self.strategy.slippage_per_trade_pct

        return None

    def _apply_slippage(
        self, price: Decimal, is_buy: bool, slippage_pct: Optional[Decimal] = None
    ) -> Decimal:
        """Apply slippage to execution price."""
        if slippage_pct is not None:
            slippage_factor = slippage_pct / Decimal("100")
        else:
            slippage_factor = self.config.slippage_percentage / Decimal("100")

        if is_buy:
            return price * (Decimal("1") + slippage_factor)
        else:
            return price * (Decimal("1") - slippage_factor)

    def _build_trade_reason(self, signal: Signal, market_data: Any) -> str:
        """Build human-readable reason for the trade from signal metadata."""
        reason_parts = []

        signal_type_str = (
            signal.signal_type.value
            if hasattr(signal.signal_type, "value")
            else str(signal.signal_type)
        )
        reason_parts.append(signal_type_str.upper())

        source_str = signal.source.value if hasattr(signal.source, "value") else str(signal.source)
        if source_str:
            reason_parts.append(f"via {source_str}")

        if signal.metadata:
            metadata_strs = []
            for key, value in signal.metadata.items():
                if key in ["rsi", "ema_trend", "volume_ratio", "z_score", "spread"]:
                    metadata_strs.append(f"{key}={value}")
            if metadata_strs:
                reason_parts.append("(" + ", ".join(metadata_strs) + ")")

        reason_parts.append(f"conf={signal.confidence:.1f}%")

        return " ".join(reason_parts)
