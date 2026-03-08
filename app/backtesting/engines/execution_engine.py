"""
Pessimistic Execution Backtest Engine.

This engine implements realistic order execution that eliminates Look-Ahead Bias:
- Signal generated at close t, executed at open t+1
- Pessimistic Execution: SL executes before TP in same bar
- Slippage applied to execution prices

This is a refactored version of app/backtesting/execution_engine.py that
extends BaseBacktestEngine for consistency across the codebase.

SINGLE SOURCE OF TRUTH: All values from CentralizedConfig.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from app.backtesting.base_engine import (
    BaseBacktestEngine,
    EngineType,
    ExecutionResult,
    ExecutionType,
    Position,
)
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.services.transaction_cost_model import BrokerType, TransactionCostModel
from app.domain.models.market_data import Quote

logger = logging.getLogger(__name__)


class ExecutionBacktestEngine(BaseBacktestEngine[BacktestConfig, BacktestResult]):
    """
    Pessimistic Execution Backtest Engine (Req #10 - CRITICAL).

    Implements:
    1. Signal at close t, execution at open t+1 (prevents Look-Ahead Bias)
    2. Pessimistic Execution: SL before TP in same bar (worst-case)
    3. Realistic slippage on execution

    This provides more conservative backtesting results by assuming
    the worst-case execution within each bar.

    Usage:
        ```python
        config = BacktestConfig(initial_capital=Decimal("100000"))
        engine = ExecutionBacktestEngine(
            config=config,
            execution_type=ExecutionType.PESSIMISTIC,
        )
        result = engine.run_backtest(market_data, signals)
        ```
    """

    def __init__(
        self,
        config: BacktestConfig,
        execution_type: ExecutionType = ExecutionType.PESSIMISTIC,
        base_slippage_bps: Optional[Decimal] = None,
        transaction_cost_model: Optional[TransactionCostModel] = None,
        enable_next_day_execution: Optional[bool] = None,
        strategy_name: str = "execution_engine",
    ):
        """
        Initialize the pessimistic execution engine.

        SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.

        Args:
            config: Backtest configuration
            execution_type: Type of execution simulation
            base_slippage_bps: Base slippage in basis points (default: from CentralizedConfig)
            transaction_cost_model: Optional transaction cost model
            enable_next_day_execution: If True, execute at next bar open
            strategy_name: Name of the strategy
        """
        super().__init__(
            config=config,
            strategy_name=strategy_name,
        )

        self.execution_type = execution_type
        self.base_slippage_bps = (
            base_slippage_bps if base_slippage_bps is not None else self._base_slippage_bps
        )
        self.transaction_cost_model = transaction_cost_model or TransactionCostModel(
            broker=BrokerType.INTERACTIVE_BROKERS,
            conservative=True,
        )
        self.enable_next_day_execution = (
            enable_next_day_execution
            if enable_next_day_execution is not None
            else self._bt_config.enable_next_day_execution
        )

        # Track open positions for intra-bar execution
        self._open_positions: List[Position] = []

        logger.info(
            f"ExecutionBacktestEngine initialized with execution_type={execution_type.value}, "
            f"base_slippage_bps={self.base_slippage_bps}"
        )

    # =========================================================================
    # IMPLEMENTATION OF ABSTRACT METHODS
    # =========================================================================

    def get_engine_type(self) -> EngineType:
        """Return the engine type identifier."""
        return EngineType.EXECUTION

    def run_backtest(
        self,
        market_data: Union[List[Any], List[Quote]],
        signals: Optional[List[Any]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
    ) -> BacktestResult:
        """
        Run a complete backtest with pessimistic execution.

        This implementation processes signals with next-day execution
        and pessimistic intra-bar stop handling.

        Args:
            market_data: Historical market data
            signals: Optional pre-generated trading signals
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            BacktestResult with pessimistic execution results
        """
        self._validate_market_data(market_data)

        # Filter by date range
        market_data, signals = self._sort_data_by_timestamp(market_data, signals)
        market_data = self._filter_by_date_range(market_data, start_date, end_date)
        signals = self._filter_by_date_range(signals, start_date, end_date)

        # Reset state
        self._reset_backtest()
        self._open_positions.clear()

        # Process market data with pessimistic execution
        execution_results: List[ExecutionResult] = []

        for i, md in enumerate(market_data):
            # Update last known price
            current_price = self._get_price(md)
            self.state.last_known_prices[md.symbol] = current_price

            # Process any signals for this timestamp
            if signals:
                signal_results = self._process_signals_with_delay(signals, market_data, i)
                execution_results.extend(signal_results)

            # Check intra-bar execution for open positions
            if hasattr(md, "open") and hasattr(md, "high") and hasattr(md, "low"):
                intra_bar_results = self._check_intra_bar_execution(md)
                execution_results.extend(intra_bar_results)

            # Update equity curve
            self.state.equity_curve.append((md.timestamp, self.state.capital))

        # Close remaining positions
        self._close_all_positions_at_end(market_data[-1])

        # Calculate metrics
        return self._create_result_from_executions(
            execution_results, market_data[0].timestamp, market_data[-1].timestamp
        )

    def _create_result(
        self,
        **kwargs,
    ) -> BacktestResult:
        """Create BacktestResult from calculated metrics."""
        return BacktestResult(
            config=self.config,
            trades=self.state.trades,
            performance=kwargs.get("performance"),
            equity_curve=self.state.equity_curve,
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            final_capital=self.state.capital,
            total_return=kwargs.get("total_return", Decimal("0")),
            annualized_return=kwargs.get("annualized_return"),
        )

    # =========================================================================
    # EXECUTION ENGINE SPECIFIC METHODS
    # =========================================================================

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
        if side.lower() == "buy":
            execution_price = next_open_price * (Decimal("1") + slippage_bps / Decimal("10000"))
        else:
            execution_price = next_open_price * (Decimal("1") - slippage_bps / Decimal("10000"))

        # Calculate commission
        cost_result = self.transaction_cost_model.calculate_costs(
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            price=execution_price,
        )
        commission = cost_result.commission

        # Update capital
        if side.lower() == "buy":
            self.state.capital -= execution_price * quantity + commission
            self.state.positions[symbol] = self.state.positions.get(symbol, Decimal("0")) + quantity
        else:
            self.state.capital += execution_price * quantity - commission

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
            return None, position

        sl_hit = False
        tp_hit = False
        execution_price = None

        if position.side.lower() == "long":
            if position.stop_loss_price and bar_low <= position.stop_loss_price:
                sl_hit = True
            if position.take_profit_price and bar_high >= position.take_profit_price:
                tp_hit = True

            # Pessimistic: SL before TP
            if sl_hit and tp_hit:
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

            if sl_hit and tp_hit:
                execution_price = position.stop_loss_price
                logger.debug(f"Pessimistic execution: SL hit before TP for {position.symbol}")
            elif sl_hit:
                execution_price = position.stop_loss_price
            elif tp_hit:
                execution_price = position.take_profit_price

        if execution_price is None:
            return None, position

        # Calculate slippage on stop execution
        slippage_bps = self.base_slippage_bps * self._stop_slippage_multiplier

        # Apply slippage (worse for position holder)
        if position.side.lower() == "long":
            exit_price = execution_price * (Decimal("1") - slippage_bps / Decimal("10000"))
        else:
            exit_price = execution_price * (Decimal("1") + slippage_bps / Decimal("10000"))

        # Calculate commission
        exit_side = "sell" if position.side.lower() == "long" else "buy"
        cost_result = self.transaction_cost_model.calculate_costs(
            symbol=position.symbol,
            side=exit_side.upper(),
            quantity=position.quantity,
            price=exit_price,
        )

        # Update capital
        self.state.capital += position.quantity * exit_price - cost_result.commission
        self.state.positions[position.symbol] = Decimal("0")

        result = ExecutionResult(
            symbol=position.symbol,
            side=exit_side,
            quantity=position.quantity,
            signal_time=position.entry_time,
            execution_time=bar_time,
            signal_price=position.entry_price,
            execution_price=exit_price.quantize(Decimal("0.01")),
            slippage_bps=slippage_bps,
            commission=cost_result.commission,
            executed=True,
            stop_loss_hit=sl_hit,
            take_profit_hit=tp_hit,
            stop_execution_price=execution_price,
        )

        return result, None

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

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _calculate_slippage(self, side: str, volatility: Optional[Decimal]) -> Decimal:
        """Calculate slippage based on volatility."""
        slippage = self.base_slippage_bps

        if volatility:
            vol_multiplier = Decimal("1") + (volatility * self._volatility_multiplier)
            slippage = slippage * vol_multiplier

        return slippage

    def _process_signals_with_delay(
        self,
        signals: List[Any],
        market_data: List[Any],
        current_index: int,
    ) -> List[ExecutionResult]:
        """Process signals with next-day execution delay."""
        results = []

        if current_index >= len(market_data) - 1:
            return results

        current_md = market_data[current_index]
        next_md = market_data[current_index + 1]

        for signal in signals:
            if not hasattr(signal, "timestamp"):
                continue

            if signal.timestamp != current_md.timestamp:
                continue

            if not hasattr(signal, "symbol") or signal.symbol != current_md.symbol:
                continue

            # Execute at next bar open
            if self.enable_next_day_execution:
                signal_price = self._get_price(current_md)
                next_open = getattr(next_md, "open", None) or getattr(
                    next_md, "open_price", signal_price
                )

                result = self.execute_entry_order(
                    symbol=signal.symbol,
                    side=signal.signal_type.value.lower()
                    if hasattr(signal.signal_type, "value")
                    else str(signal.signal_type).lower(),
                    quantity=Decimal("100"),  # Default quantity
                    signal_time=signal.timestamp,
                    signal_price=signal_price,
                    next_open_price=next_open,
                    next_bar_time=next_md.timestamp,
                )
                results.append(result)

        return results

    def _check_intra_bar_execution(self, md: Any) -> List[ExecutionResult]:
        """Check for intra-bar stop executions."""
        results = []

        positions_to_remove = []
        for position in self._open_positions:
            if position.symbol != md.symbol:
                continue

            result, remaining = self.process_intra_bar_execution(
                position=position,
                bar_open=getattr(md, "open", md.close) or getattr(md, "open_price", md.close),
                bar_high=getattr(md, "high", md.close) or getattr(md, "high_price", md.close),
                bar_low=getattr(md, "low", md.close) or getattr(md, "low_price", md.close),
                bar_close=self._get_price(md),
                bar_time=md.timestamp,
            )

            if result:
                results.append(result)

            if remaining is None:
                positions_to_remove.append(position)

        for pos in positions_to_remove:
            self._open_positions.remove(pos)

        return results

    def _close_all_positions_at_end(self, final_md: Any) -> None:
        """Close all remaining positions at end of backtest."""
        for symbol, quantity in list(self.state.positions.items()):
            if quantity > 0:
                exit_price = self._get_price(final_md)
                exit_price_with_slippage = self._apply_slippage(exit_price, is_buy=False)

                cost_result = self.transaction_cost_model.calculate_costs(
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    price=exit_price_with_slippage,
                )

                self.state.capital += quantity * exit_price_with_slippage - cost_result.commission
                self.state.positions[symbol] = Decimal("0")

    def _create_result_from_executions(
        self,
        execution_results: List[ExecutionResult],
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Create BacktestResult from execution results."""
        total_return = (
            (self.state.capital - self.config.initial_capital) / self.config.initial_capital
        ) * 100

        days = (end_date - start_date).days
        years = Decimal(str(days / 365.25)) if days > 0 else Decimal("0")
        annualized_return = (
            (
                (self.state.capital / self.config.initial_capital) ** (Decimal("1") / years)
                - Decimal("1")
            )
            * Decimal("100")
            if years > 0
            else Decimal("0")
        )

        # Create simplified performance metrics
        from app.backtesting.models import PerformanceMetrics

        performance = PerformanceMetrics(
            total_trades=len(execution_results),
            winning_trades=sum(1 for r in execution_results if r.execution_price > r.signal_price),
            losing_trades=sum(1 for r in execution_results if r.execution_price <= r.signal_price),
            win_rate=Decimal(
                str(
                    sum(1 for r in execution_results if r.execution_price > r.signal_price)
                    / len(execution_results)
                    * 100
                )
            )
            if execution_results
            else Decimal("0"),
            total_pnl=self.state.capital - self.config.initial_capital,
            total_pnl_percentage=total_return,
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_profit=self.state.capital - self.config.initial_capital,
            max_drawdown=Decimal("0"),
            max_drawdown_percentage=Decimal("0"),
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            largest_win=Decimal("0"),
            largest_loss=Decimal("0"),
            total_days=days,
            avg_trade_duration=Decimal("0"),
        )

        return self._create_result(
            performance=performance,
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annualized_return=annualized_return,
        )


# Helper function for creating positions with stops
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


# Backward compatibility alias
PessimisticExecutionEngine = ExecutionBacktestEngine
