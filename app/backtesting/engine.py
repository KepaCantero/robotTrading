"""
Backtesting engine for AlgoTrading system.

This module provides the core backtesting functionality including
historical data simulation, trade execution, and performance metrics calculation.
"""

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    TradeStatus,
)
from app.models.signal import Signal, SignalType


def get_price(md) -> Decimal:
    """Get closing price from MarketData or Quote object."""
    # Try Quote first (has 'close' attribute)
    if hasattr(md, 'close'):
        return md.close
    # Try MarketData (has 'close_price' attribute)
    elif hasattr(md, 'close_price'):
        return md.close_price
    else:
        raise AttributeError(
            f"MarketData object has no 'close' or 'close_price' attribute: {type(md)}"
        )


class SimpleBacktester:
    """
    Simple backtesting engine for trading strategies.

    This engine simulates trading execution with configurable slippage,
    commission, and risk management parameters.
    """

    def __init__(self, config: BacktestConfig):
        """Initialize the backtesting engine."""
        self.config = config
        self.capital = config.initial_capital
        self.positions: Dict[str, Decimal] = {}  # symbol -> quantity
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
        self.max_drawdown = Decimal("0")
        self.peak_equity = config.initial_capital

    def run_backtest(
        self,
        market_data: List,
        signals: List[Signal],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> BacktestResult:
        """
        Run a complete backtest simulation.

        Args:
            market_data: Historical market data
            signals: Trading signals to execute
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            BacktestResult with complete backtest analysis
        """
        # Filter data by date range
        if start_date:
            market_data = [md for md in market_data if md.timestamp >= start_date]
        if end_date:
            market_data = [md for md in market_data if md.timestamp <= end_date]

        if not market_data:
            raise ValueError("No market data available for the specified date range")

        # Sort data by timestamp
        market_data.sort(key=lambda x: x.timestamp)
        signals.sort(key=lambda x: x.timestamp)

        # Initialize backtest
        self._reset_backtest()

        # Process each market data point
        signal_index = 0
        for md in market_data:
            # Update equity curve
            self._update_equity_curve(md.timestamp)

            # Process signals for this timestamp
            # FIX: More flexible matching - allow signals within 1 day and exact symbol match
            while signal_index < len(signals):
                signal = signals[signal_index]
                
                # Allow signals up to 1 day in the past (signals are generated on market data)
                time_diff = (md.timestamp - signal.timestamp).total_seconds()
                
                # Process signal if:
                # 1. Symbol matches exactly
                # 2. Signal timestamp is before or equal to market_data timestamp (within 1 day tolerance)
                if signal.symbol == md.symbol and time_diff >= -86400 and time_diff <= 86400:
                    self._process_signal(signal, md)
                    signal_index += 1
                elif signal.timestamp > md.timestamp:
                    # Signal is in the future, wait for next market data
                    break
                else:
                    # Signal symbol doesn't match or too old, skip it
                    signal_index += 1

            # Check for stop loss / take profit
            self._check_exit_conditions(md)

        # Close any remaining positions
        self._close_all_positions(market_data[-1])

        # Calculate final metrics
        performance = self._calculate_performance_metrics()

        # Calculate returns
        total_return = (
            (self.capital - self.config.initial_capital) / self.config.initial_capital
        ) * 100

        # Calculate annualized return
        days = (market_data[-1].timestamp - market_data[0].timestamp).days
        years = Decimal(str(days / 365.25))
        annualized_return = (
            ((self.capital / self.config.initial_capital) ** (Decimal("1") / years) - Decimal("1"))
            * Decimal("100")
            if years > 0
            else Decimal("0")
        )

        return BacktestResult(
            config=self.config,
            trades=self.trades,
            performance=performance,
            equity_curve=self.equity_curve,
            start_date=market_data[0].timestamp,
            end_date=market_data[-1].timestamp,
            final_capital=self.capital,
            total_return=total_return,
            annualized_return=annualized_return,
        )

    def _reset_backtest(self):
        """Reset backtest state."""
        self.capital = self.config.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()
        self.max_drawdown = Decimal("0")
        self.peak_equity = self.config.initial_capital

    def _process_signal(self, signal: Signal, market_data: Any):
        """Process a trading signal."""
        if signal.signal_type == SignalType.BUY:
            self._execute_buy_signal(signal, market_data)
        elif signal.signal_type == SignalType.SELL:
            self._execute_sell_signal(signal, market_data)
        elif signal.signal_type == SignalType.HOLD:
            # Hold signals don't generate trades
            pass

    def _execute_buy_signal(self, signal: Signal, market_data: Any):
        """Execute a buy signal."""
        # CRITICAL FIX: Close existing position before opening new one
        # This prevents position accumulation and reduces drawdown
        current_position = self.positions.get(signal.symbol, Decimal("0"))
        if current_position > 0:
            # Close existing position first (with loss/profit)
            self._close_position(
                signal.symbol, market_data.timestamp, "signal_reverse", get_price(market_data)
            )

        # Get price using helper function
        current_price = get_price(market_data)

        # Calculate position size based on signal confidence and available
        # capital
        position_size = self._calculate_position_size(signal, current_price)

        if position_size <= 0:
            return

        # Check if we have enough capital
        total_cost = position_size * current_price
        if total_cost > self.capital:
            position_size = self.capital / current_price

        if position_size <= 0:
            return

        # Apply slippage
        execution_price = self._apply_slippage(current_price, True)

        # Calculate costs
        commission = self.config.commission_per_trade
        slippage_cost = abs(position_size * (execution_price - current_price))
        total_cost = position_size * execution_price + commission + slippage_cost

        if total_cost > self.capital:
            return

        # Build reason from signal metadata
        reason = self._build_trade_reason(signal, market_data)

        # Execute trade
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

        self.trades.append(trade)
        self.positions[signal.symbol] = (
            self.positions.get(signal.symbol, Decimal("0")) + position_size
        )
        self.capital -= total_cost

    def _execute_sell_signal(self, signal: Signal, market_data: Any):
        """Execute a sell signal."""
        current_position = self.positions.get(signal.symbol, Decimal("0"))

        if current_position <= 0:
            return  # No position to sell

        # Get price using helper function
        current_price = get_price(market_data)

        # Calculate sell quantity (can be partial)
        sell_quantity = min(
            current_position,
            self._calculate_position_size(signal, current_price),
        )

        if sell_quantity <= 0:
            return

        # Apply slippage
        execution_price = self._apply_slippage(current_price, False)

        # Calculate proceeds
        commission = self.config.commission_per_trade
        slippage_cost = abs(sell_quantity * (execution_price - current_price))
        proceeds = sell_quantity * execution_price - commission - slippage_cost

        # Find the most recent buy trade for this symbol to calculate PnL
        buy_trades = [
            t
            for t in self.trades
            if t.symbol == signal.symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        # Calculate PnL
        pnl = Decimal("0")
        if buy_trades:
            avg_buy_price = sum(t.entry_price * t.quantity for t in buy_trades) / sum(
                t.quantity for t in buy_trades
            )
            total_cost = avg_buy_price * sell_quantity + commission
            pnl = proceeds - total_cost

        # Build reason from signal metadata
        reason = self._build_trade_reason(signal, market_data)

        # Execute trade
        trade_id = str(uuid4())
        trade = Trade(
            trade_id=trade_id,
            symbol=signal.symbol,
            side="sell",
            quantity=sell_quantity,
            entry_price=execution_price if not buy_trades else buy_trades[-1].entry_price,
            exit_price=execution_price,
            entry_time=buy_trades[-1].entry_time if buy_trades else market_data.timestamp,
            exit_time=market_data.timestamp,
            status=TradeStatus.CLOSED,
            pnl=pnl,
            pnl_percentage=(
                (pnl / (avg_buy_price * sell_quantity) * 100) if buy_trades else Decimal("0")
            ),
            commission=commission,
            slippage=slippage_cost,
            reason=reason,
        )

        # Close the matching buy trades
        for buy_trade in buy_trades:
            if sell_quantity > 0:
                closed_qty = min(buy_trade.quantity, sell_quantity)
                sell_quantity -= closed_qty
                if closed_qty >= buy_trade.quantity:
                    buy_trade.status = TradeStatus.CLOSED
                    buy_trade.exit_price = execution_price
                    buy_trade.exit_time = market_data.timestamp
                else:
                    # Partial fill - not handling for now
                    buy_trade.status = TradeStatus.CLOSED
                    buy_trade.exit_price = execution_price
                    buy_trade.exit_time = market_data.timestamp

        self.trades.append(trade)
        self.positions[signal.symbol] = current_position - sum(
            t.quantity for t in buy_trades if t.status == TradeStatus.CLOSED
        )
        self.capital += proceeds

    def _calculate_position_size(self, signal: Signal, price: Decimal) -> Decimal:
        """Calculate position size based on signal and risk management."""
        # Base position size on signal confidence and max position size
        confidence_factor = Decimal(str(signal.confidence / 100.0))
        max_position_value = self.capital * self.config.max_position_size

        position_value = max_position_value * confidence_factor
        position_size = position_value / price

        return position_size.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _apply_slippage(self, price: Decimal, is_buy: bool) -> Decimal:
        """Apply slippage to execution price."""
        slippage_factor = self.config.slippage_percentage / Decimal("100")

        if is_buy:
            # Buy orders execute at higher price (unfavorable)
            return price * (Decimal("1") + slippage_factor)
        else:
            # Sell orders execute at lower price (unfavorable)
            return price * (Decimal("1") - slippage_factor)

    def _build_trade_reason(self, signal: Signal, market_data: Any) -> str:
        """Build human-readable reason for the trade from signal metadata."""
        reason_parts = []

        # Add signal type and strength
        # Handle both SignalType enum and string
        signal_type_str = (
            signal.signal_type.value
            if hasattr(signal.signal_type, 'value')
            else str(signal.signal_type)
        )
        reason_parts.append(signal_type_str.upper())

        # Add source information
        source_str = signal.source.value if hasattr(signal.source, 'value') else str(signal.source)
        if source_str:
            reason_parts.append(f"via {source_str}")

        # Extract and format metadata
        if signal.metadata:
            metadata_strs = []
            for key, value in signal.metadata.items():
                if key in ["rsi", "ema_trend", "volume_ratio", "z_score", "spread"]:
                    # Technical indicators
                    metadata_strs.append(f"{key}={value}")
            if metadata_strs:
                reason_parts.append("(" + ", ".join(metadata_strs) + ")")

        # Add confidence
        reason_parts.append(f"conf={signal.confidence:.1f}%")

        return " ".join(reason_parts)

    def _check_exit_conditions(self, market_data: Any):
        """Check for stop loss and take profit conditions."""
        if market_data.symbol not in self.positions:
            return

        current_position = self.positions[market_data.symbol]
        if current_position <= 0:
            return

        # Find the most recent buy trade for this symbol
        recent_trades = [
            t
            for t in self.trades
            if t.symbol == market_data.symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        if not recent_trades:
            return

        # Use the most recent trade's entry price
        entry_price = recent_trades[-1].entry_price
        current_price = get_price(market_data)

        # Check stop loss
        if self.config.stop_loss_percentage:
            stop_loss_price = entry_price * (
                Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
            )
            if current_price <= stop_loss_price:
                self._close_position(
                    market_data.symbol, market_data.timestamp, "stop_loss", current_price
                )
                return

        # Check take profit
        if self.config.take_profit_percentage:
            take_profit_price = entry_price * (
                Decimal("1") + self.config.take_profit_percentage / Decimal("100")
            )
            if current_price >= take_profit_price:
                self._close_position(
                    market_data.symbol, market_data.timestamp, "take_profit", current_price
                )
                return

    def _close_position(
        self, symbol: str, timestamp: datetime, reason: str, current_price: Decimal = None
    ):
        """Close a position completely."""
        current_position = self.positions.get(symbol, Decimal("0"))

        if current_position <= 0:
            return

        # Find the most recent buy trade for this symbol
        recent_trades = [t for t in self.trades if t.symbol == symbol and t.side == "buy"]

        if not recent_trades:
            return

        # Use the average entry price from all buy trades for this symbol
        buy_quantity = sum(t.quantity for t in recent_trades if t.status == TradeStatus.OPEN)
        buy_cost = sum(
            t.quantity * t.entry_price for t in recent_trades if t.status == TradeStatus.OPEN
        )
        avg_entry_price = (
            buy_cost / buy_quantity if buy_quantity > 0 else recent_trades[-1].entry_price
        )

        # Use provided current price or fallback
        exit_price = current_price if current_price else avg_entry_price

        # Calculate P&L
        total_buy_cost = buy_cost
        total_sell_proceeds = current_position * exit_price
        commission_cost = self.config.commission_per_trade * (
            Decimal(len(recent_trades)) + Decimal("1")
        )  # Commission for buy + sell
        pnl = total_sell_proceeds - total_buy_cost - commission_cost
        pnl_percentage = (pnl / total_buy_cost * 100) if total_buy_cost > 0 else Decimal("0")

        # Close all matching buy trades
        for buy_trade in recent_trades:
            if buy_trade.status == TradeStatus.OPEN:
                buy_trade.status = TradeStatus.CLOSED
                buy_trade.exit_price = exit_price
                buy_trade.exit_time = timestamp

        # Create summary sell trade
        trade_id = str(uuid4())
        trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            side="sell",
            quantity=current_position,
            entry_price=avg_entry_price,
            exit_price=exit_price,
            entry_time=recent_trades[0].entry_time,
            exit_time=timestamp,
            status=TradeStatus.CLOSED,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            commission=self.config.commission_per_trade,
            slippage=Decimal("0"),
        )

        # Add trade to results
        self.trades.append(trade)

        # Update capital
        self.capital += total_sell_proceeds - self.config.commission_per_trade
        self.positions[symbol] = Decimal("0")

    def _close_all_positions(self, final_market_data: Any):
        """Close all remaining positions at the end of backtest."""
        for symbol in list(self.positions.keys()):
            if self.positions[symbol] > 0:
                self._close_position(
                    symbol,
                    final_market_data.timestamp,
                    "end_of_backtest",
                    get_price(final_market_data),
                )

    def _update_equity_curve(self, timestamp: datetime):
        """Update equity curve with current portfolio value."""
        # Calculate current portfolio value
        portfolio_value = self.capital

        # Add unrealized P&L from open positions
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                # For simplicity, we'll use the last known price
                # In a real implementation, you'd need to track current prices
                portfolio_value += quantity * Decimal("100")  # Placeholder price

        self.equity_curve.append((timestamp, portfolio_value))

        # Update drawdown
        if portfolio_value > self.peak_equity:
            self.peak_equity = portfolio_value

        current_drawdown = (portfolio_value - self.peak_equity) / self.peak_equity * 100
        if current_drawdown < self.max_drawdown:
            self.max_drawdown = current_drawdown

    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return self._create_empty_metrics()

        # Separate winning and losing trades
        winning_trades = []
        losing_trades = []

        for trade in self.trades:
            if trade.status == TradeStatus.CLOSED and trade.pnl is not None:
                if trade.pnl > 0:
                    winning_trades.append(trade)
                else:
                    losing_trades.append(trade)

        total_trades = len(winning_trades) + len(losing_trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        # Calculate win rate
        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else Decimal("0")

        # Calculate P&L metrics
        total_pnl = sum(trade.pnl for trade in winning_trades + losing_trades)
        gross_profit = (
            sum(trade.pnl for trade in winning_trades) if winning_trades else Decimal("0")
        )
        gross_loss = sum(trade.pnl for trade in losing_trades) if losing_trades else Decimal("0")
        net_profit = gross_profit + gross_loss

        # Calculate trade statistics
        avg_win = gross_profit / winning_count if winning_count > 0 else Decimal("0")
        avg_loss = gross_loss / losing_count if losing_count > 0 else Decimal("0")
        largest_win = max(trade.pnl for trade in winning_trades) if winning_trades else Decimal("0")
        largest_loss = min(trade.pnl for trade in losing_trades) if losing_trades else Decimal("0")

        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio()

        # Calculate time metrics
        if self.trades:
            first_trade = min(self.trades, key=lambda t: t.entry_time)
            last_trade = max(self.trades, key=lambda t: t.exit_time or t.entry_time)
            last_time = last_trade.exit_time or last_trade.entry_time
            total_days = (last_time - first_trade.entry_time).days
            avg_trade_duration = total_days / total_trades if total_trades > 0 else Decimal("0")
        else:
            total_days = 0
            avg_trade_duration = Decimal("0")

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percentage=(total_pnl / self.config.initial_capital * 100),
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            max_drawdown=self.max_drawdown,
            max_drawdown_percentage=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=None,  # Not implemented yet
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_days=total_days,
            avg_trade_duration=avg_trade_duration,
        )

    def _calculate_sharpe_ratio(self) -> Optional[Decimal]:
        """Calculate Sharpe ratio (simplified implementation)."""
        if len(self.equity_curve) < 2:
            return None

        # Calculate daily returns
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1][1]
            curr_equity = self.equity_curve[i][1]
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)

        if not returns:
            return None

        # Calculate mean and standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = Decimal(str(math.sqrt(float(variance))))

        # Annualize returns
        annual_mean = mean_return * Decimal("365.25")
        annual_std = std_dev * Decimal(str(math.sqrt(365.25)))

        # Calculate Sharpe ratio
        excess_return = annual_mean - self.config.risk_free_rate
        if annual_std > 0:
            return excess_return / annual_std

        return None

    def _create_empty_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics."""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=Decimal("0"),
            total_pnl=Decimal("0"),
            total_pnl_percentage=Decimal("0"),
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_profit=Decimal("0"),
            max_drawdown=Decimal("0"),
            max_drawdown_percentage=Decimal("0"),
            sharpe_ratio=None,
            sortino_ratio=None,
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            largest_win=Decimal("0"),
            largest_loss=Decimal("0"),
            total_days=0,
            avg_trade_duration=Decimal("0"),
        )
