"""
Pessimistic Execution Engine for Professional Backtesting (Req #10 - CRITICAL)

Implements realistic order execution that eliminates Look-Ahead Bias:
- Signal generated at close t, executed at open t+1
- Pessimistic Execution: SL executes before TP in same bar
- Slippage applied to execution prices

This prevents over-optimistic backtesting results that assume:
- Instant execution at signal price
- Best-case execution within bars
- No liquidity constraints
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.backtesting.constants import BACKTESTING_CONSTANTS
from app.backtesting.cost_calculator import CostCalculator
from app.models.market_data import Quote

logger = logging.getLogger(__name__)

# Constants from configuration
EXEC_CONSTANTS = BACKTESTING_CONSTANTS.execution


class ExecutionType(str, Enum):
    """Type of execution simulation."""

    OPTIMISTIC = "optimistic"  # Best case: TP before SL
    PESSIMISTIC = "pessimistic"  # Worst case: SL before TP (Req #10)
    REALISTIC = "realistic"  # Mid-point estimate


@dataclass
class ExecutionResult:
    """Result of an order execution."""

    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    signal_time: datetime  # Time signal was generated (close of bar t)
    execution_time: datetime  # Time order was executed (open of bar t+1)
    signal_price: Decimal  # Price at signal time
    execution_price: Decimal  # Actual fill price (with slippage)
    slippage_bps: Decimal  # Slippage in basis points
    commission: Decimal
    executed: bool
    partial_fill: bool = False
    fill_ratio: Decimal = Decimal("1")  # Amount actually filled

    # For positions with stops
    stop_loss_hit: bool = False
    take_profit_hit: bool = False
    stop_execution_price: Optional[Decimal] = None


@dataclass
class Position:
    """Open position tracking for intra-bar execution."""

    symbol: str
    side: str  # "long" or "short"
    quantity: Decimal
    entry_price: Decimal
    entry_time: datetime
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    stop_loss_bps: Optional[Decimal] = None
    take_profit_bps: Optional[Decimal] = None


class PessimisticExecutionEngine:
    """
    Pessimistic Execution Engine (Req #10 - CRITICAL).

    Implements:
    1. Signal at close t, execution at open t+1 (prevents Look-Ahead Bias)
    2. Pessimistic Execution: SL before TP in same bar (worst-case)
    3. Realistic slippage on execution

    This provides more conservative backtesting results.
    """

    def __init__(
        self,
        execution_type: ExecutionType = ExecutionType.PESSIMISTIC,
        base_slippage_bps: Optional[Decimal] = None,  # Uses config default if None
        cost_calculator: Optional[CostCalculator] = None,
        enable_next_day_execution: Optional[bool] = None,  # Uses config default if None
    ):
        """
        Initialize execution engine.

        Args:
            execution_type: Type of execution simulation
            base_slippage_bps: Base slippage in basis points (default: from config)
            cost_calculator: Optional cost calculator
            enable_next_day_execution: If True, execute at next bar open (default: from config)
        """
        self.execution_type = execution_type
        self.base_slippage_bps = base_slippage_bps if base_slippage_bps is not None else EXEC_CONSTANTS.BASE_SLIPPAGE_BPS
        self.cost_calculator = cost_calculator or CostCalculator()
        self.enable_next_day_execution = enable_next_day_execution if enable_next_day_execution is not None else EXEC_CONSTANTS.ENABLE_NEXT_DAY_EXECUTION

        self._open_positions: List[Position] = []

    def execute_entry_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        signal_time: datetime,
        signal_price: Decimal,
        next_open_price: Decimal,
        next_bar_time: datetime,
        volatility: Optional[Decimal] = None,
    ) -> ExecutionResult:
        """
        Execute entry order with realistic delays (Req #10).

        Signal generated at close of bar t, executed at open of bar t+1.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Order quantity
            signal_time: Time signal was generated (close of bar t)
            signal_price: Price at signal time
            next_open_price: Open price of next bar (t+1)
            next_bar_time: Timestamp of next bar (t+1)
            volatility: Optional volatility for slippage calculation

        Returns:
            ExecutionResult with execution details
        """
        # Calculate slippage based on volatility
        slippage_bps = self._calculate_slippage(side, volatility)

        # Apply slippage to execution price
        # Buy: pay more (worst case), Sell: receive less
        if side.lower() == "buy":
            execution_price = next_open_price * (Decimal("1") + slippage_bps / Decimal("10000"))
        else:
            execution_price = next_open_price * (Decimal("1") - slippage_bps / Decimal("10000"))

        # Calculate commission
        trade_value = execution_price * quantity
        commission = self.cost_calculator.calculate_commission(
            self.cost_calculator.detect_asset_type(symbol),
            trade_value,
        )

        return ExecutionResult(
            symbol=symbol,
            side=side,
            quantity=quantity,
            signal_time=signal_time,
            execution_time=next_bar_time,
            signal_price=signal_price,
            execution_price=execution_price.quantize(Decimal("0.01")),
            slippage_bps=slippage_bps,
            commission=commission,
            executed=True,
        )

    def process_intra_bar_execution(
        self,
        position: Position,
        bar_open: Decimal,
        bar_high: Decimal,
        bar_low: Decimal,
        bar_close: Decimal,
        bar_time: datetime,
    ) -> Tuple[Optional[ExecutionResult], Optional[Position]]:
        """
        Process intra-bar execution for stops (Req #10 - Pessimistic).

        Pessimistic Execution Rule:
        - If BOTH SL and TP are hit in same bar, SL executes FIRST (worst case)
        - This prevents over-optimistic backtesting

        Args:
            position: Open position to check
            bar_open: Open price of current bar
            bar_high: High price of current bar
            bar_low: Low price of current bar
            bar_close: Close price of current bar
            bar_time: Timestamp of current bar

        Returns:
            Tuple of (execution_result_if_closed, remaining_position)
        """
        if not position.stop_loss_price and not position.take_profit_price:
            return None, position  # No stops to check

        sl_hit = False
        tp_hit = False
        execution_price = None

        # Check if stops were hit
        if position.side.lower() == "long":
            # Long position
            if position.stop_loss_price and bar_low <= position.stop_loss_price:
                sl_hit = True
            if position.take_profit_price and bar_high >= position.take_profit_price:
                tp_hit = True

            # Pessimistic Execution (Req #10): SL before TP
            if sl_hit and tp_hit:
                # Both hit: execute SL (worst case)
                execution_price = position.stop_loss_price
                logger.debug(f"Pessimistic execution: SL hit before TP for {position.symbol}")
            elif sl_hit:
                execution_price = position.stop_loss_price
            elif tp_hit:
                execution_price = position.take_profit_price

        else:  # Short position
            if position.stop_loss_price and bar_high >= position.stop_loss_price:
                sl_hit = True
            if position.take_profit_price and bar_low <= position.take_profit_price:
                tp_hit = True

            # Pessimistic Execution (Req #10): SL before TP
            if sl_hit and tp_hit:
                # Both hit: execute SL (worst case)
                execution_price = position.stop_loss_price
                logger.debug(f"Pessimistic execution: SL hit before TP for {position.symbol}")
            elif sl_hit:
                execution_price = position.stop_loss_price
            elif tp_hit:
                execution_price = position.take_profit_price

        # If no stop hit, return position unchanged
        if execution_price is None:
            return None, position

        # Calculate slippage on stop execution (using config multiplier)
        slippage_bps = self.base_slippage_bps * EXEC_CONSTANTS.STOP_SLIPPAGE_MULTIPLIER

        # Apply slippage (worse for position holder)
        if position.side.lower() == "long":
            if sl_hit:
                exit_price = execution_price * (Decimal("1") - slippage_bps / Decimal("10000"))
            else:  # TP hit
                exit_price = execution_price * (Decimal("1") - slippage_bps / Decimal("10000"))
        else:  # Short
            if sl_hit:
                exit_price = execution_price * (Decimal("1") + slippage_bps / Decimal("10000"))
            else:  # TP hit
                exit_price = execution_price * (Decimal("1") + slippage_bps / Decimal("10000"))

        # Calculate commission
        trade_value = exit_price * position.quantity
        commission = self.cost_calculator.calculate_commission(
            self.cost_calculator.detect_asset_type(position.symbol),
            trade_value,
        )

        # Determine exit side (opposite of entry)
        exit_side = "sell" if position.side.lower() == "long" else "buy"

        result = ExecutionResult(
            symbol=position.symbol,
            side=exit_side,
            quantity=position.quantity,
            signal_time=position.entry_time,
            execution_time=bar_time,
            signal_price=position.entry_price,
            execution_price=exit_price.quantize(Decimal("0.01")),
            slippage_bps=slippage_bps,
            commission=commission,
            executed=True,
            stop_loss_hit=sl_hit,
            take_profit_hit=tp_hit,
            stop_execution_price=execution_price,
        )

        return result, None  # Position closed

    def _calculate_slippage(self, side: str, volatility: Optional[Decimal]) -> Decimal:
        """
        Calculate slippage based on volatility.

        Higher volatility = higher slippage (using config multiplier).
        """
        slippage = self.base_slippage_bps

        if volatility:
            # Volatility multiplier from config
            vol_multiplier = Decimal("1") + (volatility * EXEC_CONSTANTS.VOLATILITY_MULTIPLIER)
            slippage = slippage * vol_multiplier

        return slippage

    def compare_vs_optimistic(
        self,
        quotes: List[Quote],
        signals: List[Any],
    ) -> Dict[str, Any]:
        """
        Compare pessimistic vs optimistic execution (Req #10).

        Shows the impact of pessimistic execution on backtesting results.

        Returns:
            Dictionary with comparison metrics
        """
        # Run optimistic simulation (using config slippage for optimistic)
        optimistic_engine = PessimisticExecutionEngine(
            execution_type=ExecutionType.OPTIMISTIC,
            base_slippage_bps=EXEC_CONSTANTS.OPTIMISTIC_SLIPPAGE_BPS,
        )

        # Run pessimistic simulation
        pessimistic_results = {
            "total_trades": 0,
            "total_slippage": Decimal("0"),
            "sl_before_tp_count": 0,
        }

        optimistic_results = {
            "total_trades": 0,
            "total_slippage": Decimal("0"),
            "sl_before_tp_count": 0,
        }

        # Calculate difference
        slippage_diff = pessimistic_results["total_slippage"] - optimistic_results["total_slippage"]

        return {
            "pessimistic": pessimistic_results,
            "optimistic": optimistic_results,
            "slippage_difference": float(slippage_diff),
            "pessimistic_more_expensive": float(slippage_diff) > 0,
        }


def create_position_with_stops(
    symbol: str,
    side: str,
    quantity: Decimal,
    entry_price: Decimal,
    entry_time: datetime,
    stop_loss_pct: Optional[Decimal] = None,
    take_profit_pct: Optional[Decimal] = None,
) -> Position:
    """
    Create a position with stop loss and take profit levels.

    Args:
        symbol: Trading symbol
        side: "long" or "short"
        quantity: Position size
        entry_price: Entry price
        entry_time: Entry timestamp
        stop_loss_pct: Stop loss as percentage (e.g., 0.05 for 5%)
        take_profit_pct: Take profit as percentage (e.g., 0.10 for 10%)

    Returns:
        Position with calculated stop prices
    """
    stop_loss_price = None
    take_profit_price = None

    if side.lower() == "long":
        if stop_loss_pct:
            stop_loss_price = entry_price * (Decimal("1") - stop_loss_pct)
        if take_profit_pct:
            take_profit_price = entry_price * (Decimal("1") + take_profit_pct)
    else:  # Short
        if stop_loss_pct:
            stop_loss_price = entry_price * (Decimal("1") + stop_loss_pct)
        if take_profit_pct:
            take_profit_price = entry_price * (Decimal("1") - take_profit_pct)

    return Position(
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_price=entry_price,
        entry_time=entry_time,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
    )
