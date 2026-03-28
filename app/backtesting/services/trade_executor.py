"""
Trade Executor service for backtesting.

This service is responsible for executing buy and sell trades with all
necessary validations including liquidity, position sizing, and cost calculations.

BUG #3 FIX: Now uses TransactionCostModel for realistic costs instead of
simple percentage-based commission.

SINGLE SOURCE OF TRUTH: Uses shared utilities for slippage and trade reason.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable, Optional
from uuid import uuid4

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator
from app.backtesting.services.position_manager import PositionManager
from app.backtesting.services.transaction_cost_model import (
    BrokerType,
    OrderType,
    TransactionCostModel,
    TransactionCostResult,
)

# SHARED UTILITIES: Centralized slippage and trade utilities
from app.backtesting.shared.slippage_utils import apply_slippage as shared_apply_slippage
from app.backtesting.shared.trade_utils import build_trade_reason as shared_build_trade_reason
from app.domain.models.signal import Signal

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Executes trades with full validation and cost calculation.

    This service handles:
    - Buy order execution with all validations
    - Sell order execution with P&L calculation
    - Position size calculation based on risk
    - Commission and slippage application using TransactionCostModel
    - Liquidity-aware execution

    Dependencies:
    - LiquidityValidator: Realistic order execution simulation
    - TradingValidator: Position size and stop-loss validation
    - PositionManager: Track and update positions
    - ProfitAndLossCalculator: Calculate trade profitability
    - TransactionCostModel: Realistic transaction cost calculation
    - config: Backtest configuration
    """

    def __init__(
        self,
        config: BacktestConfig,
        position_manager: PositionManager,
        pnl_calculator: ProfitAndLossCalculator,
        diagnostic_logger: Optional[object] = None,
        strategy: Optional[object] = None,
        use_realistic_costs: bool = True,
        broker_type: BrokerType = BrokerType.INTERACTIVE_BROKERS,
    ):
        """
        Initialize the TradeExecutor.

        Args:
            config: Backtest configuration
            position_manager: PositionManager instance
            pnl_calculator: ProfitAndLossCalculator instance
            diagnostic_logger: Optional diagnostic logger
            strategy: Optional strategy instance for custom parameters
            use_realistic_costs: Use TransactionCostModel for realistic costs (default True)
            broker_type: Broker type for cost modeling (default IBKR)
        """
        from app.backtesting.liquidity_validator import LiquidityValidator
        from app.domain.services.trading_validators import TradingValidator

        self.config = config
        self.position_manager = position_manager
        self.pnl_calculator = pnl_calculator
        self.diagnostic_logger = diagnostic_logger
        self.strategy = strategy

        # BUG #3 FIX: Initialize TransactionCostModel for realistic costs
        self.use_realistic_costs = use_realistic_costs
        self.transaction_cost_model = TransactionCostModel(
            broker=broker_type,
            conservative=True,  # Use conservative estimates for backtesting
        )

        # Initialize validators
        self.trading_validator = TradingValidator()

        # Get liquidity configuration from CentralizedConfig
        from app.shared.config.centralized_config import get_config

        backtest_config = get_config().backtesting
        self.liquidity_validator = LiquidityValidator(
            enable_partial_fills=backtest_config.liquidity_enable_partial_fills,
            max_order_pct_of_volume=backtest_config.liquidity_max_order_pct_of_volume,
            warning_order_pct_of_volume=backtest_config.liquidity_warning_order_pct_of_volume,
            partial_fill_pct=backtest_config.liquidity_partial_fill_pct,
        )

    def execute_buy_signal(
        self,
        signal: Signal,
        market_data: object,
        capital: Decimal,
        close_position_func: Callable,
        validate_profitability_func: Callable,
        position_size: Optional[Decimal] = None,  # Pass from ComplianceEngine to avoid duplication
    ) -> tuple[Optional[Trade], Decimal]:
        """
        Execute a buy signal with all validations.

        Args:
            signal: Buy signal to execute
            market_data: Current market data
            capital: Current available capital
            close_position_func: Function to close existing positions
            validate_profitability_func: Function to validate trade profitability
            position_size: Pre-calculated position size from ComplianceEngine (avoids duplication)

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

        # Position size MUST come from ComplianceEngine - no fallback allowed
        if position_size is None:
            raise ValueError(
                "position_size is required. "
                "Pass position_size from ComplianceEngine.calculate_position_size() "
                "to ensure consistent position sizing across the system."
            )
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

        # BUG #3 FIX: Calculate transaction costs using realistic model
        cost_result = self._calculate_transaction_costs(
            symbol=signal.symbol,
            side="BUY",
            quantity=position_size,
            price=execution_price,
            signal=signal,
            market_data=market_data,
        )

        # Extract individual costs for logging and trade record
        commission = cost_result.commission
        slippage_cost = cost_result.slippage_cost + cost_result.market_impact_cost
        total_cost = position_size * execution_price + cost_result.total_cost

        logger.info(
            f"BUY {signal.symbol} (strategy={strategy_name}): "
            f"execution_price=${execution_price:.4f}, "
            f"commission=${commission:.2f}, "
            f"spread=${cost_result.spread_cost:.2f}, "
            f"slippage=${slippage_cost:.2f}, "
            f"total_cost=${total_cost:.2f} ({cost_result.total_cost_bps:.1f} bps)"
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
        market_data: object,
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
            logger.debug(
                f"SELL {signal.symbol} (strategy={strategy_name}): "
                f"No position to sell (position={current_position})"
            )
            return None, capital

        get_price(market_data)

        # Sell the entire current position (no need to calculate position size for sells)
        sell_quantity = current_position

        logger.info(
            f"SELL {signal.symbol} (strategy={strategy_name}): "
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

        # BUG #3 FIX: Calculate transaction costs using realistic model
        cost_result = self._calculate_transaction_costs(
            symbol=signal.symbol,
            side="SELL",
            quantity=sell_quantity,
            price=execution_price,
            signal=signal,
            market_data=market_data,
        )

        # Extract individual costs for logging and trade record
        commission = cost_result.commission
        slippage_cost = cost_result.slippage_cost + cost_result.market_impact_cost
        total_costs = cost_result.total_cost  # Includes SEC/TAF fees on sells

        # Calculate proceeds (sell value minus all costs)
        proceeds = sell_quantity * execution_price - total_costs

        logger.info(
            f"SELL {signal.symbol} (strategy={strategy_name}): "
            f"execution_price=${execution_price:.4f}, "
            f"commission=${commission:.2f}, "
            f"spread=${cost_result.spread_cost:.2f}, "
            f"sec/taf=${cost_result.sec_fee + cost_result.taf_fee:.2f}, "
            f"slippage=${slippage_cost:.2f}, "
            f"proceeds=${proceeds:.2f} (total costs: {cost_result.total_cost_bps:.1f} bps)"
        )

        # Calculate P&L using PnL calculator
        pnl_info = self.pnl_calculator.calculate_sell_pnl(
            trades=trades,
            symbol=signal.symbol,
            sell_quantity=sell_quantity,
            execution_price=execution_price,
            commission=total_costs,  # Use total costs, not just commission
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

    def _get_strategy_commission(self, signal: Signal, strategy_name: str) -> Optional[Decimal]:
        """Get commission percentage for strategy."""
        from decimal import InvalidOperation

        if signal.metadata and "commission_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["commission_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation):
                # Invalid commission value in metadata - will fall back to strategy or default
                logger.debug(
                    f"Invalid commission_per_trade_pct in signal metadata: "
                    f"{signal.metadata.get('commission_per_trade_pct')}"
                )

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
                # Invalid slippage value in metadata - will fall back to strategy or default
                logger.debug(
                    f"Invalid slippage_per_trade_pct in signal metadata: "
                    f"{signal.metadata.get('slippage_per_trade_pct')}"
                )

        if self.strategy and hasattr(self.strategy, "slippage_per_trade_pct"):
            return self.strategy.slippage_per_trade_pct

        return None

    def _apply_slippage(
        self, price: Decimal, is_buy: bool, slippage_pct: Optional[Decimal] = None
    ) -> Decimal:
        """
        Apply slippage to execution price.

        DELEGATES TO: app.backtesting.shared.slippage_utils.apply_slippage
        SINGLE SOURCE OF TRUTH: All slippage calculations go through shared utility.
        """
        return shared_apply_slippage(
            price=price,
            is_buy=is_buy,
            slippage_pct=slippage_pct,
            is_stop=False,
            is_volatile=False,
        )

    def _build_trade_reason(self, signal: Signal, market_data: object) -> str:
        """
        Build human-readable reason for the trade from signal metadata.

        DELEGATES TO: app.backtesting.shared.trade_utils.build_trade_reason
        SINGLE SOURCE OF TRUTH: All trade reason building goes through shared utility.
        """
        return shared_build_trade_reason(signal=signal, market_data=market_data)

    def _calculate_transaction_costs(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        signal: Optional[Signal] = None,
        market_data: Optional[object] = None,
    ) -> TransactionCostResult:
        """
        Calculate transaction costs using TransactionCostModel.

        BUG #3 FIX: Uses realistic cost model instead of simple percentage.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Number of shares
            price: Execution price
            signal: Optional signal for metadata
            market_data: Optional market data for volume/volatility

        Returns:
            TransactionCostResult with all cost components
        """
        strategy_name = "unknown"
        if signal and signal.metadata:
            strategy_name = signal.metadata.get("strategy", "unknown")

        # Check if strategy overrides commission percentage
        commission_pct = self._get_strategy_commission(signal, strategy_name) if signal else None

        if commission_pct is not None:
            # Strategy has custom commission percentage - use simple calculation
            trade_value = quantity * price
            commission = trade_value * (commission_pct / Decimal("100"))

            return TransactionCostResult(
                gross_value=trade_value,
                commission=commission,
                total_cost=commission,
                total_cost_bps=(commission / trade_value * Decimal("10000"))
                if trade_value > 0
                else Decimal("0"),
            )

        # Use realistic TransactionCostModel
        # Get volume from market data if available
        average_volume = None
        if market_data and hasattr(market_data, "volume"):
            try:
                average_volume = Decimal(str(market_data.volume))
            except (ValueError, TypeError):
                # Invalid or missing volume data - TransactionCostModel will handle gracefully
                logger.debug(
                    f"Could not extract volume from market_data for {symbol}: "
                    f"volume={getattr(market_data, 'volume', None)}"
                )

        return self.transaction_cost_model.calculate_costs(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=OrderType.MARKET,  # Backtesting assumes market orders
            average_volume=average_volume,
        )
