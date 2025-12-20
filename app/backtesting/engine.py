"""
Backtesting engine for AlgoTrading system.

This module provides the core backtesting functionality including
historical data simulation, trade execution, and performance metrics calculation.
"""

import logging
import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    TradeStatus,
)
from app.models.portfolio import AssetClass, Portfolio, Position
from app.models.signal import Signal, SignalType
from app.services.dynamic_capital_reallocation import DynamicCapitalReallocationEngine
from app.services.risk_envelope_validator import RiskEnvelopeValidator

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        config: BacktestConfig,
        diagnostic_logger=None,
        strategy=None,
        enable_risk_envelope: bool = True,
        risk_envelope_validator: Optional[RiskEnvelopeValidator] = None,
        strategy_name: str = "unknown",
        total_portfolio_capital: Optional[Decimal] = None,
        reallocation_engine: Optional[DynamicCapitalReallocationEngine] = None,
    ):
        """
        Initialize the backtesting engine.

        Args:
            config: Backtest configuration
            diagnostic_logger: Optional diagnostic logger
            strategy: Strategy instance for risk_check (optional but required for risk checking)
            enable_risk_envelope: Enable risk envelope validation (default True)
            risk_envelope_validator: Optional custom RiskEnvelopeValidator instance
            strategy_name: Name of strategy for risk envelope logging
            total_portfolio_capital: Total portfolio capital for multi-strategy scenarios (defaults to initial_capital)
            reallocation_engine: Optional DynamicCapitalReallocationEngine instance for performance tracking
        """
        self.config = config
        self.capital = config.initial_capital
        self.positions: Dict[str, Decimal] = {}  # symbol -> quantity
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, Decimal]] = []
        self.max_drawdown = Decimal("0")
        self.diagnostic_logger = diagnostic_logger
        self.peak_equity = config.initial_capital
        self.strategy = strategy  # Strategy instance for risk_check
        self.strategy_name = strategy_name
        self.total_portfolio_capital = total_portfolio_capital or config.initial_capital

        # Initialize Risk Envelope Validator
        self.enable_risk_envelope = enable_risk_envelope
        if enable_risk_envelope:
            self.risk_validator = risk_envelope_validator or RiskEnvelopeValidator()
            logger.info(f"✅ Risk Envelope Validator enabled for {strategy_name}")
        else:
            self.risk_validator = None

        # Initialize Dynamic Capital Reallocation Engine (optional, for performance tracking)
        self.reallocation_engine = reallocation_engine
        if reallocation_engine:
            logger.info(f"✅ Dynamic Capital Reallocation Engine linked for {strategy_name}")

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

        logger.info(
            f"📊 Backtest starting: {len(market_data)} market_data points, {len(signals)} signals"
        )
        if signals:
            logger.debug(f"Signal time range: {signals[0].timestamp} to {signals[-1].timestamp}")
            logger.debug(
                f"Market data time range: {market_data[0].timestamp} to {market_data[-1].timestamp}"
            )
            # Sample first few signals
            for i, sig in enumerate(signals[:5]):
                logger.debug(
                    f"Sample signal {i}: {sig.symbol} {sig.signal_type} at {sig.timestamp}, strategy={sig.metadata.get('strategy', 'N/A') if sig.metadata else 'N/A'}"
                )

        # Initialize backtest
        self._reset_backtest()

        # Process each market data point
        signal_index = 0
        signals_processed = 0
        signals_matched = 0
        signals_skipped = 0
        # Track matching stats by strategy
        strategy_stats = {}  # strategy_name -> {matched, skipped, symbol_mismatch, time_mismatch}

        for md in market_data:
            # Update equity curve
            self._update_equity_curve(md.timestamp)

            # NEW: Ejecutar reentrenamiento si es necesario (si strategy tiene learning_engine)
            if (
                self.strategy
                and hasattr(self.strategy, 'learning_engine')
                and self.strategy.learning_engine
            ):
                from app.strategies.momentum_modular.learning.learning_updater import (
                    LearningEngineUpdater,
                )

                if not hasattr(self.strategy, '_learning_updater'):
                    self.strategy._learning_updater = LearningEngineUpdater(
                        learning_engine=self.strategy.learning_engine, rebalance_frequency_days=7
                    )

                # Agregar market data al historial
                if hasattr(md, 'close') or hasattr(md, 'bid'):
                    price = float(get_price(md))
                    self.strategy._learning_updater.add_market_data(
                        market_data={
                            'price': price,
                            'volume': float(getattr(md, 'volume', 0)),
                            'symbol': md.symbol,
                        },
                        timestamp=md.timestamp,
                    )

                # Intentar reentrenar si es necesario
                self.strategy._learning_updater.retrain_if_needed(
                    current_date=md.timestamp,
                    quotes=market_data[: market_data.index(md) + 1] if md in market_data else None,
                )

            # Process signals for this timestamp
            # FIX: More flexible matching - allow signals within 1 day and exact symbol match
            while signal_index < len(signals):
                signal = signals[signal_index]
                strategy_name = (
                    signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
                )

                # Initialize strategy stats
                if strategy_name not in strategy_stats:
                    strategy_stats[strategy_name] = {
                        "matched": 0,
                        "skipped": 0,
                        "symbol_mismatch": 0,
                        "time_mismatch": 0,
                    }

                # Allow signals up to 1 day in the past (signals are generated on market data)
                time_diff = (md.timestamp - signal.timestamp).total_seconds()

                # Process signal if:
                # 1. Symbol matches exactly
                # 2. Signal timestamp is before or equal to market_data timestamp (within 1 day tolerance)
                signals_processed += 1

                # CRITICAL: Log all Momentum signals for debugging
                if strategy_name == "momentum":
                    logger.info(
                        f"🔍 MOMENTUM SIGNAL: {signal.symbol} {signal.signal_type} | "
                        f"MD: {md.symbol} | "
                        f"symbol_match={signal.symbol == md.symbol} | "
                        f"time_diff={time_diff:.0f}s | "
                        f"signal_time={signal.timestamp} | "
                        f"md_time={md.timestamp}"
                    )

                if signal.symbol == md.symbol and time_diff >= -86400 and time_diff <= 86400:
                    signals_matched += 1
                    strategy_stats[strategy_name]["matched"] += 1
                    if strategy_name == "momentum":
                        logger.info(
                            f"✅ MOMENTUM MATCHED: {signal.symbol} {signal.signal_type} at {md.timestamp}, time_diff={time_diff:.0f}s"
                        )
                    else:
                        logger.debug(
                            f"✅ MATCHED signal: {signal.symbol} {signal.signal_type} (strategy={strategy_name}) at {md.timestamp}, time_diff={time_diff:.0f}s"
                        )
                    self._process_signal(signal, md)
                    signal_index += 1
                elif signal.timestamp > md.timestamp:
                    # Signal is in the future, wait for next market data
                    if strategy_name == "momentum":
                        logger.debug(
                            f"⏳ MOMENTUM FUTURE: signal {signal.timestamp} > md {md.timestamp}, waiting..."
                        )
                    break
                else:
                    # Signal symbol doesn't match or too old, skip it
                    signals_skipped += 1
                    strategy_stats[strategy_name]["skipped"] += 1
                    if signal.symbol != md.symbol:
                        strategy_stats[strategy_name]["symbol_mismatch"] += 1
                        if (
                            signals_skipped <= 10 or strategy_name == "momentum"
                        ):  # Always log Momentum mismatches
                            logger.info(
                                f"❌ MOMENTUM SKIP: symbol mismatch {signal.symbol} != {md.symbol} (time_diff={time_diff:.0f}s)"
                            )
                    elif abs(time_diff) > 86400:
                        strategy_stats[strategy_name]["time_mismatch"] += 1
                        if (
                            signals_skipped <= 10 or strategy_name == "momentum"
                        ):  # Always log Momentum mismatches
                            logger.info(
                                f"❌ MOMENTUM SKIP: timestamp too far {time_diff:.0f}s (signal={signal.timestamp}, md={md.timestamp})"
                            )
                    signal_index += 1

            # Check for stop loss / take profit
            self._check_exit_conditions(md)

        # Close any remaining positions using the last price for each symbol
        # CRITICAL FIX: Build a price map from all market_data to get correct prices for each symbol
        price_map = {}
        for md in reversed(market_data):  # Start from most recent
            if md.symbol not in price_map:
                price_map[md.symbol] = get_price(md)

        self._close_all_positions(market_data[-1], price_map=price_map)

        logger.info(
            f"📊 Backtest matching stats: {signals_processed} processed, {signals_matched} matched, {signals_skipped} skipped, {len(self.trades)} trades executed"
        )

        # Log stats by strategy
        if strategy_stats:
            logger.info("📊 Matching stats by strategy:")
            for strategy_name, stats in sorted(strategy_stats.items()):
                logger.info(
                    f"  {strategy_name}: {stats['matched']} matched, {stats['skipped']} skipped "
                    f"(symbol_mismatch={stats['symbol_mismatch']}, time_mismatch={stats['time_mismatch']})"
                )

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

        # Update reallocation engine with strategy performance after backtest
        if self.reallocation_engine and performance:
            # Calculate winning and losing trades
            winning_trades = sum(1 for t in self.trades if t.pnl and t.pnl > 0)
            losing_trades = sum(1 for t in self.trades if t.pnl and t.pnl <= 0)
            total_trades = len(self.trades)

            # Update performance tracker
            self.reallocation_engine.update_strategy_performance(
                strategy_name=self.strategy_name,
                timestamp=market_data[-1].timestamp,  # Use end date as timestamp
                pnl=Decimal(str(performance.total_pnl)),
                returns=Decimal(str(total_return)),
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
            )
            logger.info(
                f"📊 Updated performance tracker for {self.strategy_name}: "
                f"PnL={performance.total_pnl:.2f}, "
                f"Return={total_return:.2f}%, "
                f"Trades={total_trades} (W:{winning_trades}, L:{losing_trades})"
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

    def _create_portfolio_from_state(self, current_price_func=None):
        """
        Create a Portfolio object from current backtesting state.

        Args:
            current_price_func: Optional function to get current price for a symbol

        Returns:
            Portfolio object
        """

        positions = []

        # Convert backtester positions to Portfolio Position objects
        for symbol, quantity in self.positions.items():
            if quantity == 0:
                continue

            # Get current price (use market price if available)
            if current_price_func:
                market_price = current_price_func(symbol)
            else:
                # Try to get price from most recent trade for this symbol
                market_price = Decimal("100")  # Default fallback
                for trade in reversed(self.trades):
                    if trade.symbol == symbol:
                        market_price = trade.entry_price
                        break

            # Get average entry price from open trades
            avg_price = market_price  # Default to market price
            buy_trades = [
                t
                for t in self.trades
                if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
            ]
            if buy_trades:
                total_qty = sum(t.quantity for t in buy_trades)
                total_cost = sum(t.quantity * t.entry_price for t in buy_trades)
                if total_qty > 0:
                    avg_price = total_cost / total_qty

            # Calculate unrealized PnL
            unrealized_pnl = (market_price - avg_price) * quantity

            position = Position(
                symbol=symbol,
                asset_class=AssetClass.EQUITY,
                quantity=quantity,
                avg_price=avg_price,
                market_price=market_price,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=Decimal("0"),
                currency="USD",
                broker="backtester",
            )
            positions.append(position)

        portfolio = Portfolio(
            portfolio_id="backtest_portfolio",
            cash=self.capital,
            positions=positions,
            timestamp=datetime.utcnow(),
            broker="backtester",
            currency="USD",
        )

        return portfolio

    def _process_signal(self, signal: Signal, market_data: Any):
        """Process a trading signal with risk_check if strategy is available."""
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # CRITICAL: Apply risk_check if strategy is available
        if self.strategy:
            try:
                # Create a Portfolio object from current state for risk_check
                # Use current_price from market_data for accurate portfolio valuation
                current_price = get_price(market_data)
                portfolio = self._create_portfolio_from_state(
                    current_price_func=lambda s: (
                        current_price if s == signal.symbol else Decimal("100")
                    )
                )

                # Apply risk_check
                # IMPORTANT: Capture the rejection reason from risk_check if possible
                risk_check_result = self.strategy.risk_check(signal, portfolio)
                if not risk_check_result:
                    # Try to extract specific rejection reason from the portfolio state
                    current_price = get_price(market_data)
                    rejection_reason = "Risk check failed"

                    # Add contextual information about why it might have failed
                    if signal.signal_type == SignalType.BUY:
                        position_size = self.strategy.get_position_size(signal, portfolio)
                        required_cash = (
                            signal.price * position_size if position_size > 0 else Decimal("0")
                        )
                        rejection_reason += f" (BUY: cash=${portfolio.cash:.2f}, required=${required_cash:.2f}, position_size={position_size:.6f})"
                    elif signal.signal_type == SignalType.SELL:
                        existing_pos = next(
                            (p for p in portfolio.positions if p.symbol == signal.symbol), None
                        )
                        if not existing_pos:
                            rejection_reason += " (SELL: no position exists)"
                        else:
                            rejection_reason += f" (SELL: position_qty={existing_pos.quantity:.6f})"

                    logger.info(
                        f"⚠️ REJECTED {signal.signal_type} {signal.symbol} (strategy={strategy_name}): {rejection_reason}"
                    )

                    # Log rejection to diagnostic logger with detailed reason
                    if self.diagnostic_logger:
                        signal_type_str = (
                            signal.signal_type.value
                            if hasattr(signal.signal_type, 'value')
                            else str(signal.signal_type)
                        )
                        self.diagnostic_logger.log_signal_rejected(
                            strategy_name,
                            signal.symbol,
                            rejection_reason,
                            failed_check="risk_check",
                            metadata=signal.metadata if hasattr(signal, 'metadata') else {},
                        )
                    return
                else:
                    logger.debug(
                        f"✅ PASSED risk_check: {signal.signal_type} {signal.symbol} (strategy={strategy_name})"
                    )
            except Exception as e:
                logger.error(
                    f"❌ ERROR in risk_check for {signal.symbol} (strategy={strategy_name}): {e}",
                    exc_info=True,
                )
                # On error, reject the signal for safety
                if self.diagnostic_logger:
                    signal_type_str = (
                        signal.signal_type.value
                        if hasattr(signal.signal_type, 'value')
                        else str(signal.signal_type)
                    )
                    self.diagnostic_logger.log_signal_rejected(
                        strategy_name,
                        signal.symbol,
                        signal_type_str,
                        f"Risk check error: {str(e)}",
                        signal.metadata if hasattr(signal, 'metadata') else {},
                    )
                return
        else:
            logger.warning(
                f"⚠️ No strategy provided, skipping risk_check for {signal.symbol} (strategy={strategy_name})"
            )

        # CRITICAL: Apply Risk Envelope validation if enabled
        if self.enable_risk_envelope and self.risk_validator:
            current_price = get_price(market_data)

            # Calculate current portfolio positions for validation
            current_portfolio_exposure = {}  # symbol -> position value
            strategy_positions = {}  # symbol -> position value for this strategy

            # Build exposure maps from current positions
            for symbol, quantity in self.positions.items():
                if quantity > 0:
                    # Get current price for this symbol (use signal price if same symbol, otherwise estimate)
                    pos_price = current_price if symbol == signal.symbol else Decimal("100")

                    # Try to get actual price from recent trades
                    for trade in reversed(self.trades):
                        if trade.symbol == symbol:
                            if trade.status == TradeStatus.OPEN:
                                pos_price = trade.entry_price
                            break

                    position_value = quantity * pos_price
                    current_portfolio_exposure[symbol] = position_value
                    strategy_positions[symbol] = position_value

            # Calculate trade value
            if signal.signal_type == SignalType.BUY:
                # Estimate trade value from position size
                portfolio = self._create_portfolio_from_state(
                    current_price_func=lambda s: (
                        current_price if s == signal.symbol else Decimal("100")
                    )
                )
                position_size = (
                    self.strategy.get_position_size(signal, portfolio)
                    if self.strategy
                    else Decimal("0.01")
                )
                trade_value = signal.price * position_size
            elif signal.signal_type == SignalType.SELL:
                # For sell, use current position value
                existing_pos = self.positions.get(signal.symbol, Decimal("0"))
                trade_value = existing_pos * current_price
            else:
                trade_value = Decimal("0")

            # Validate trade
            if trade_value > 0:
                is_valid, reason = self.risk_validator.validate_trade(
                    symbol=signal.symbol,
                    trade_value=trade_value,
                    strategy_name=self.strategy_name,
                    current_portfolio=current_portfolio_exposure,
                    strategy_positions=strategy_positions,
                    total_capital=self.total_portfolio_capital,
                    strategy_capital=self.config.initial_capital,
                )

                if not is_valid:
                    logger.warning(
                        f"❌ RISK ENVELOPE REJECTED {signal.signal_type} {signal.symbol} "
                        f"(strategy={strategy_name}): {reason}"
                    )
                    if self.diagnostic_logger:
                        signal_type_str = (
                            signal.signal_type.value
                            if hasattr(signal.signal_type, 'value')
                            else str(signal.signal_type)
                        )
                        self.diagnostic_logger.log_signal_rejected(
                            strategy_name,
                            signal.symbol,
                            signal_type_str,
                            f"Risk envelope: {reason}",
                            signal.metadata if hasattr(signal, 'metadata') else {},
                        )
                    return

        # Execute signal if risk_check passes
        if signal.signal_type == SignalType.BUY:
            logger.info(f"🔄 Processing BUY signal for {signal.symbol} (strategy={strategy_name})")
            self._execute_buy_signal(signal, market_data)
        elif signal.signal_type == SignalType.SELL:
            logger.info(f"🔄 Processing SELL signal for {signal.symbol} (strategy={strategy_name})")
            self._execute_sell_signal(signal, market_data)
        elif signal.signal_type == SignalType.HOLD:
            # Hold signals don't generate trades
            logger.debug(f"Processing HOLD signal for {signal.symbol} (skipped)")
            pass

    def _execute_buy_signal(self, signal: Signal, market_data: Any):
        """Execute a buy signal."""
        # CRITICAL FIX: Close existing position before opening new one
        # This prevents position accumulation and reduces drawdown
        current_position = self.positions.get(signal.symbol, Decimal("0"))
        if current_position > 0:
            # Close existing position first (with loss/profit)
            strategy_name = (
                signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
            )
            logger.info(
                f"🔄 BUY {signal.symbol} (strategy={strategy_name}): "
                f"Closing existing position ({current_position:.6f}) before opening new BUY"
            )
            self._close_position(
                signal.symbol, market_data.timestamp, "signal_reverse", get_price(market_data)
            )

        # Get price using helper function
        current_price = get_price(market_data)

        # Calculate position size based on signal confidence and available
        # capital
        position_size = self._calculate_position_size(signal, current_price)
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
        logger.info(
            f"💰 BUY {signal.symbol} (strategy={strategy_name}): position_size={position_size}, price={current_price}, capital={self.capital}"
        )

        if position_size <= 0:
            logger.warning(
                f"❌ BUY {signal.symbol} (strategy={strategy_name}): position_size <= 0, skipping"
            )
            return

        # Check if we have enough capital
        total_cost = position_size * current_price
        if total_cost > self.capital:
            logger.info(
                f"🔧 BUY {signal.symbol} (strategy={strategy_name}): total_cost ({total_cost}) > capital ({self.capital}), adjusting position_size"
            )
            position_size = self.capital / current_price

        if position_size <= 0:
            logger.warning(
                f"❌ BUY {signal.symbol} (strategy={strategy_name}): adjusted position_size <= 0, skipping"
            )
            return

        # NEW: Apply strategy-specific slippage and commission
        # Priority: signal metadata > strategy config > global config
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
        slippage_pct = self._get_strategy_slippage(signal, strategy_name)
        commission_pct = self._get_strategy_commission(signal, strategy_name)

        execution_price = self._apply_slippage(current_price, True, slippage_pct=slippage_pct)

        # Calculate costs: commission can be percentage or fixed amount
        trade_value = position_size * execution_price
        if commission_pct is not None:
            # Commission as percentage of trade value
            commission = trade_value * (commission_pct / Decimal("100"))
        else:
            # Fixed commission amount
            commission = self.config.commission_per_trade

        slippage_cost = abs(position_size * (execution_price - current_price))
        total_cost = position_size * execution_price + commission + slippage_cost

        logger.info(
            f"💰 BUY {signal.symbol} (strategy={strategy_name}): "
            f"execution_price={execution_price:.4f} (slippage={slippage_pct if slippage_pct else self.config.slippage_percentage:.2f}%), "
            f"commission=${commission:.2f} ({commission_pct if commission_pct else 'fixed'}), "
            f"slippage_cost=${slippage_cost:.2f}, total_cost=${total_cost:.2f}, capital=${self.capital:.2f}"
        )

        if total_cost > self.capital:
            logger.warning(
                f"❌ BUY {signal.symbol} (strategy={strategy_name}): total_cost ({total_cost}) > capital ({self.capital}) after slippage, skipping"
            )
            return

        logger.info(
            f"✅ EXECUTING BUY: {signal.symbol} qty={position_size} price={execution_price}"
        )

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

        # NEW: Registrar trade para learning engine (si está activo)
        if (
            self.strategy
            and hasattr(self.strategy, 'learning_engine')
            and self.strategy.learning_engine
        ):
            if hasattr(self.strategy, '_learning_updater'):
                self.strategy._learning_updater.add_trade_result(
                    trade={
                        'symbol': signal.symbol,
                        'entry_time': trade.entry_time,
                        'entry_price': float(trade.entry_price),
                        'quantity': float(trade.quantity),
                        'side': 'buy',
                    },
                    timestamp=market_data.timestamp,
                )

                # Si la estrategia tiene método add_trade_result, llamarlo también
                if hasattr(self.strategy, 'add_trade_result'):
                    self.strategy.add_trade_result(
                        {
                            'pnl': 0,  # P&L se actualizará al cerrar
                            'entry_time': trade.entry_time,
                            'symbol': signal.symbol,
                        }
                    )

        # Log execution to diagnostic logger
        if self.diagnostic_logger:
            strategy_name = (
                signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
            )
            self.diagnostic_logger.log_signal_executed(
                strategy_name=strategy_name,
                symbol=signal.symbol,
                metadata=signal.metadata if signal.metadata else {},
            )

    def _execute_sell_signal(self, signal: Signal, market_data: Any):
        """Execute a sell signal."""
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
        current_position = self.positions.get(signal.symbol, Decimal("0"))

        if current_position <= 0:
            logger.warning(
                f"❌ SELL {signal.symbol} (strategy={strategy_name}): No position to sell (position={current_position})"
            )
            return  # No position to sell

        # Get price using helper function
        current_price = get_price(market_data)

        # Calculate sell quantity (can be partial)
        calculated_sell_size = self._calculate_position_size(signal, current_price)
        sell_quantity = min(current_position, calculated_sell_size)
        logger.info(
            f"💰 SELL {signal.symbol} (strategy={strategy_name}): calculated_sell_size={calculated_sell_size}, sell_quantity={sell_quantity}, current_position={current_position}"
        )

        if sell_quantity <= 0:
            logger.warning(
                f"❌ SELL {signal.symbol} (strategy={strategy_name}): sell_quantity <= 0, skipping"
            )
            return

        logger.info(
            f"✅ EXECUTING SELL: {signal.symbol} (strategy={strategy_name}) qty={sell_quantity} price={current_price}"
        )

        # NEW: Apply strategy-specific slippage and commission
        # Priority: signal metadata > strategy config > global config
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
        slippage_pct = self._get_strategy_slippage(signal, strategy_name)
        commission_pct = self._get_strategy_commission(signal, strategy_name)

        execution_price = self._apply_slippage(current_price, False, slippage_pct=slippage_pct)

        # Calculate proceeds: commission can be percentage or fixed amount
        trade_value = sell_quantity * execution_price
        if commission_pct is not None:
            # Commission as percentage of trade value
            commission = trade_value * (commission_pct / Decimal("100"))
        else:
            # Fixed commission amount
            commission = self.config.commission_per_trade

        slippage_cost = abs(sell_quantity * (execution_price - current_price))
        proceeds = sell_quantity * execution_price - commission - slippage_cost

        logger.info(
            f"💰 SELL {signal.symbol} (strategy={strategy_name}): "
            f"execution_price={execution_price:.4f} (slippage={slippage_pct if slippage_pct else self.config.slippage_percentage:.2f}%), "
            f"commission=${commission:.2f} ({commission_pct if commission_pct else 'fixed'}), "
            f"slippage_cost=${slippage_cost:.2f}, proceeds=${proceeds:.2f}, "
            f"current_position={current_position:.6f}, capital=${self.capital:.2f}"
        )

        # Find the most recent buy trade for this symbol to calculate PnL
        buy_trades = [
            t
            for t in self.trades
            if t.symbol == signal.symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        logger.debug(f"SELL {signal.symbol}: found {len(buy_trades)} open buy trades")

        # Calculate PnL
        pnl = Decimal("0")
        if buy_trades:
            avg_buy_price = sum(t.entry_price * t.quantity for t in buy_trades) / sum(
                t.quantity for t in buy_trades
            )
            total_cost = avg_buy_price * sell_quantity + commission
            pnl = proceeds - total_cost
            logger.info(
                f"💰 PnL CALCULATION {signal.symbol} (strategy={strategy_name}): "
                f"avg_buy_price={avg_buy_price:.2f}, execution_price={execution_price:.2f}, "
                f"sell_quantity={sell_quantity:.6f}, proceeds={proceeds:.2f}, total_cost={total_cost:.2f}, pnl={pnl:.2f}"
            )
        else:
            logger.warning(
                f"⚠️ SELL {signal.symbol} (strategy={strategy_name}): NO buy_trades found! "
                f"Position exists ({current_position:.6f}) but no open buy trades. PnL will be 0."
            )

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

        # NEW: Registrar trade result para learning engine (con P&L)
        if (
            self.strategy
            and hasattr(self.strategy, 'learning_engine')
            and self.strategy.learning_engine
        ):
            if hasattr(self.strategy, '_learning_updater'):
                self.strategy._learning_updater.add_trade_result(
                    trade={
                        'symbol': signal.symbol,
                        'entry_time': (
                            buy_trades[-1].entry_time if buy_trades else market_data.timestamp
                        ),
                        'exit_time': market_data.timestamp,
                        'entry_price': float(avg_buy_price) if buy_trades else 0,
                        'exit_price': float(execution_price),
                        'quantity': float(sell_quantity),
                        'pnl': float(pnl),
                        'side': 'sell',
                    },
                    timestamp=market_data.timestamp,
                )

                # Actualizar en strategy también
                if hasattr(self.strategy, 'add_trade_result'):
                    self.strategy.add_trade_result(
                        {
                            'pnl': float(pnl),
                            'entry_time': (
                                buy_trades[-1].entry_time if buy_trades else market_data.timestamp
                            ),
                            'exit_time': market_data.timestamp,
                            'symbol': signal.symbol,
                        }
                    )

        # Log execution to diagnostic logger
        if self.diagnostic_logger:
            strategy_name = (
                signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"
            )
            self.diagnostic_logger.log_signal_executed(
                strategy_name=strategy_name,
                symbol=signal.symbol,
                metadata=signal.metadata if signal.metadata else {},
            )

    def _calculate_position_size(self, signal: Signal, price: Decimal) -> Decimal:
        """Calculate position size based on signal and risk management."""
        # Base position size on signal confidence and max position size
        # FIX: Ensure minimum position size to avoid zero trades
        confidence_factor = Decimal(
            str(max(signal.confidence / 100.0, 0.5))
        )  # Minimum 50% confidence factor
        max_position_value = self.capital * self.config.max_position_size

        position_value = max_position_value * confidence_factor

        # FIX: Ensure minimum position value to avoid rounding to zero
        min_position_value = self.capital * Decimal("0.01")  # At least 1% of capital
        position_value = max(position_value, min_position_value)

        position_size = position_value / price

        # FIX: Ensure minimum position size (at least 1 share)
        min_size = Decimal("1")
        position_size = max(position_size, min_size)

        return position_size.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _apply_slippage(
        self, price: Decimal, is_buy: bool, slippage_pct: Optional[Decimal] = None
    ) -> Decimal:
        """
        Apply slippage to execution price.

        Args:
            price: Base price
            is_buy: True for buy orders, False for sell
            slippage_pct: Optional slippage percentage (overrides config)

        Returns:
            Execution price with slippage applied
        """
        # Use provided slippage_pct or fall back to config
        if slippage_pct is not None:
            slippage_factor = slippage_pct / Decimal("100")
        else:
            slippage_factor = self.config.slippage_percentage / Decimal("100")

        if is_buy:
            # Buy orders execute at higher price (unfavorable)
            return price * (Decimal("1") + slippage_factor)
        else:
            # Sell orders execute at lower price (unfavorable)
            return price * (Decimal("1") - slippage_factor)

    def _get_strategy_slippage(self, signal: Signal, strategy_name: str) -> Optional[Decimal]:
        """
        Get slippage percentage for strategy.

        Priority: signal metadata > strategy config > global config > None

        Returns:
            Slippage percentage (as Decimal, e.g., 0.05 for 0.05%) or None to use config default
        """
        # 1. Check signal metadata first
        if signal.metadata and "slippage_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["slippage_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.debug(f"Invalid slippage value in metadata: {e}")
                pass

        # 2. Check strategy instance if available
        if self.strategy and hasattr(self.strategy, "slippage_per_trade_pct"):
            return self.strategy.slippage_per_trade_pct

        # 3. Return None to use global config default
        return None

    def _get_strategy_commission(self, signal: Signal, strategy_name: str) -> Optional[Decimal]:
        """
        Get commission percentage for strategy.

        Priority: signal metadata > strategy config > None (use fixed amount from config)

        Returns:
            Commission percentage (as Decimal, e.g., 0.05 for 0.05%) or None to use fixed amount
        """
        # 1. Check signal metadata first
        if signal.metadata and "commission_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["commission_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.debug(f"Invalid commission value in metadata: {e}")
                pass

        # 2. Check strategy instance if available
        if self.strategy and hasattr(self.strategy, "commission_per_trade_pct"):
            return self.strategy.commission_per_trade_pct

        # 3. Return None to use fixed commission from config
        return None

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

        # NEW: Apply slippage to exit price (for stop_loss/take_profit closes)
        # Use default slippage from config since we don't have signal context here
        exit_price_with_slippage = self._apply_slippage(exit_price, False)  # False = sell

        # Calculate P&L
        total_buy_cost = buy_cost
        # Use average commission per trade from recent trades if available
        avg_commission_per_buy = (
            sum(t.commission for t in recent_trades if t.commission) / len(recent_trades)
            if recent_trades and any(t.commission for t in recent_trades)
            else self.config.commission_per_trade
        )

        total_sell_proceeds = current_position * exit_price_with_slippage
        slippage_cost_exit = abs(current_position * (exit_price_with_slippage - exit_price))

        # Commission for sell: try to match strategy commission if available
        # For simplicity, use percentage if recent trades had percentage-based commission
        # Otherwise use fixed amount
        sell_trade_value = current_position * exit_price_with_slippage
        commission_sell = avg_commission_per_buy  # Default: same as buy

        # Check if we can infer commission type from recent trades
        # If buy trades had commission > fixed amount, assume percentage-based
        if recent_trades and any(
            t.commission > self.config.commission_per_trade * Decimal("1.5") for t in recent_trades
        ):
            # Likely percentage-based - estimate from trade value
            commission_rate = (
                avg_commission_per_buy / (recent_trades[0].quantity * recent_trades[0].entry_price)
                if recent_trades[0].quantity * recent_trades[0].entry_price > 0
                else Decimal("0")
            )
            commission_sell = sell_trade_value * commission_rate

        total_commission_cost = sum(t.commission for t in recent_trades) + commission_sell
        pnl = total_sell_proceeds - total_buy_cost - total_commission_cost - slippage_cost_exit
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
            commission=commission_sell,
            slippage=slippage_cost_exit,
        )

        # Add trade to results
        self.trades.append(trade)

        # Update capital
        self.capital += total_sell_proceeds - commission_sell
        self.positions[symbol] = Decimal("0")

    def _close_all_positions(
        self, final_market_data: Any, price_map: Optional[Dict[str, Decimal]] = None
    ):
        """
        Close all remaining positions at the end of backtest.

        Args:
            final_market_data: Last market data point (for timestamp)
            price_map: Optional dictionary mapping symbol -> price for accurate closing prices
        """
        for symbol in list(self.positions.keys()):
            if self.positions[symbol] > 0:
                # Use price from price_map if available, otherwise try to find it in recent trades
                closing_price = None
                if price_map and symbol in price_map:
                    closing_price = price_map[symbol]
                    logger.debug(f"Using price_map price for {symbol}: {closing_price:.2f}")
                else:
                    # Fallback: try to get price from most recent trade for this symbol
                    recent_trades_for_symbol = [
                        t for t in reversed(self.trades) if t.symbol == symbol
                    ]
                    if recent_trades_for_symbol:
                        closing_price = recent_trades_for_symbol[0].entry_price
                        logger.warning(
                            f"⚠️ No price_map entry for {symbol}, using last trade price: {closing_price:.2f}"
                        )
                    else:
                        # Last resort: use final_market_data price (may be wrong symbol)
                        closing_price = get_price(final_market_data)
                        logger.warning(
                            f"⚠️ Using final_market_data price for {symbol} (symbol may not match): {closing_price:.2f}"
                        )

                self._close_position(
                    symbol,
                    final_market_data.timestamp,
                    "end_of_backtest",
                    closing_price,
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

        # Calcular drawdown como valor negativo absoluto (no porcentaje)
        # max_drawdown debe ser <= 0 según validación Pydantic
        if self.peak_equity > 0:
            current_drawdown = portfolio_value - self.peak_equity  # Valor negativo o cero
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

        # Calculate win rate (asegurar que esté entre 0-100)
        if total_trades > 0:
            win_rate = Decimal(str((winning_count / total_trades) * 100))
            # Asegurar que no exceda 100 (por redondeos)
            win_rate = min(Decimal("100"), max(Decimal("0"), win_rate))
        else:
            win_rate = Decimal("0")

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
            max_drawdown=min(Decimal("0"), self.max_drawdown),  # Asegurar que sea <= 0
            max_drawdown_percentage=min(
                Decimal("0"),
                (
                    (self.max_drawdown / self.config.initial_capital * 100)
                    if self.config.initial_capital > 0
                    else Decimal("0")
                ),
            ),
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
