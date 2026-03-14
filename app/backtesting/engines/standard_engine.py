"""
Standard Backtest Engine.

This engine provides standard single-strategy backtesting with:
- Comprehensive compliance integration
- Service-based architecture (PositionManager, TradeExecutor, etc.)
- Risk envelope validation
- Learning engine support

This is a refactored version of app/backtesting/engine.py that
extends BaseBacktestEngine for consistency across the codebase.

SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import pandas as pd

from app.backtesting.base_engine import BaseBacktestEngine, EngineType
from app.backtesting.liquidity_validator import LiquidityValidator
from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    TradeStatus,
)

# Services
from app.backtesting.services.equity_tracker import EquityCurveTracker
from app.backtesting.services.exit_monitor import ExitConditionMonitor
from app.backtesting.services.performance_calculator import PerformanceMetricsCalculator
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator
from app.backtesting.services.position_manager import PositionManager
from app.backtesting.services.signal_processor import SignalProcessor
from app.backtesting.services.trade_executor import TradeExecutor

# Domain imports
from app.domain.models.portfolio import AssetClass, Portfolio, Position
from app.domain.models.signal import Signal
from app.domain.services.compliance.compliance_engine import ComplianceEngine
from app.domain.services.trading_validators import TradingValidator

logger = logging.getLogger(__name__)


class StandardBacktestEngine(BaseBacktestEngine[BacktestConfig, BacktestResult]):
    """
    Standard backtest engine for single-strategy backtesting.

    This engine orchestrates trade execution with configurable slippage,
    commission, and risk management parameters using specialized service classes.

    Features:
    - Compliance engine integration
    - Service-based architecture for maintainability
    - Risk envelope validation
    - Learning engine support
    - Pickle support for multiprocessing
    """

    def __init__(
        self,
        config: BacktestConfig,
        diagnostic_logger=None,
        strategy=None,
        enable_risk_envelope: bool = True,
        compliance_engine: Optional[ComplianceEngine] = None,
        strategy_name: str = "unknown",
        total_portfolio_capital: Optional[Decimal] = None,
        reallocation_engine: Optional[Any] = None,
    ):
        """
        Initialize the standard backtest engine.

        Args:
            config: Backtest configuration
            diagnostic_logger: Optional diagnostic logger
            strategy: Strategy instance for risk_check
            enable_risk_envelope: Enable risk envelope validation (default True)
            compliance_engine: Optional ComplianceEngine instance
            strategy_name: Name of strategy for logging
            total_portfolio_capital: Total portfolio capital for multi-strategy
            reallocation_engine: Optional DynamicCapitalReallocationEngine
        """
        super().__init__(
            config=config,
            strategy=strategy,
            diagnostic_logger=diagnostic_logger,
            strategy_name=strategy_name,
            enable_risk_envelope=enable_risk_envelope,
        )

        self.total_portfolio_capital = total_portfolio_capital or config.initial_capital
        self.reallocation_engine = reallocation_engine

        # Store market_data for compliance engine price_history
        self._market_data_list: List = []

        # Initialize service classes
        self._initialize_services(compliance_engine)

        # Initialize validators
        self.trading_validator = TradingValidator()
        self.liquidity_validator = LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),
        )

        logger.info(
            f"StandardBacktestEngine initialized for {strategy_name} with COMPLIANCE ENGINE"
        )

    def _initialize_services(self, compliance_engine: Optional[ComplianceEngine]) -> None:
        """Initialize all service classes."""
        # PositionManager - pure state holder for positions
        self.position_manager = PositionManager()

        # EquityCurveTracker - tracks portfolio value over time
        self.equity_tracker = EquityCurveTracker(
            position_manager=self.position_manager,
            initial_capital=self.config.initial_capital,
        )

        # ProfitAndLossCalculator - calculates trade profitability
        self.pnl_calculator = ProfitAndLossCalculator(self.config)

        # SignalProcessor - validates and processes trading signals
        self.signal_processor = SignalProcessor(
            config=self.config,
            strategy=self.strategy,
            compliance_engine=compliance_engine,
            enable_risk_envelope=self.enable_risk_envelope,
            diagnostic_logger=self.diagnostic_logger,
            total_portfolio_capital=self.total_portfolio_capital,
            strategy_name=self.strategy_name,
        )

        # TradeExecutor - executes buy and sell trades
        self.trade_executor = TradeExecutor(
            config=self.config,
            position_manager=self.position_manager,
            pnl_calculator=self.pnl_calculator,
            diagnostic_logger=self.diagnostic_logger,
            strategy=self.strategy,
        )

        # ExitConditionMonitor - monitors stop-loss and take-profit
        self.exit_monitor = ExitConditionMonitor(
            config=self.config,
            position_manager=self.position_manager,
            apply_slippage_func=self._apply_slippage,
        )

        # PerformanceMetricsCalculator - calculates performance metrics
        self.performance_calculator = PerformanceMetricsCalculator(self.config)

        # COMPLIANCE: Initialize compliance_engine
        self.compliance_engine = compliance_engine or ComplianceEngine(enable_logging=False)
        self.compliance_engine.set_starting_capital(float(self.config.initial_capital))

    # =========================================================================
    # IMPLEMENTATION OF ABSTRACT METHODS
    # =========================================================================

    def get_engine_type(self) -> EngineType:
        """Return the engine type identifier."""
        return EngineType.STANDARD

    def run_backtest(  # pylint: disable=signature-differs
        self,
        market_data: List,
        signals: List[Signal],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
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

        self._validate_market_data(market_data)

        # Sort data by timestamp
        market_data, signals = self._sort_data_by_timestamp(market_data, signals)

        logger.info(
            f"Backtest starting: {len(market_data)} market_data points, {len(signals)} signals"
        )

        # Initialize backtest
        self._reset_backtest()

        # Store market_data for compliance engine price_history
        self._market_data_list = market_data

        # Process each market data point
        signal_index = 0
        signals_processed = 0
        signals_matched = 0
        signals_skipped = 0
        strategy_stats: Dict[str, Dict[str, int]] = {}

        for md in market_data:
            # Track the current price for this symbol BEFORE updating equity curve
            current_md_price = self._get_price(md)
            self.state.last_known_prices[md.symbol] = current_md_price

            # Update equity curve
            self.equity_tracker.update_equity_curve(
                md.timestamp, self.state.capital, self.state.last_known_prices
            )

            # Execute learning engine retraining if needed
            self._execute_learning_retraining(md, market_data)

            # Process signals for this timestamp
            (
                signal_index,
                signals_processed,
                signals_matched,
                signals_skipped,
                strategy_stats,
            ) = self._process_signals_at_timestamp(
                md,
                signals,
                signal_index,
                signals_processed,
                signals_matched,
                signals_skipped,
                strategy_stats,
            )

            # Check for stop loss / take profit
            self.exit_monitor.check_exit_conditions(
                market_data=md,
                trades=self.state.trades,
                close_position_func=self._close_position,
            )

        # Close any remaining positions using the last price for each symbol
        price_map = self._build_price_map(market_data)
        self._close_all_positions(market_data[-1], price_map=price_map)

        logger.info(
            f"Backtest matching stats: {signals_processed} processed, "
            f"{signals_matched} matched, {signals_skipped} skipped, "
            f"{len(self.state.trades)} trades executed"
        )

        # Calculate final metrics
        performance = self.performance_calculator.calculate_performance_metrics(
            trades=self.state.trades,
            max_drawdown=self.equity_tracker.get_max_drawdown(),
            initial_capital=self.config.initial_capital,
        )

        # Calculate returns
        total_return = (
            (self.state.capital - self.config.initial_capital) / self.config.initial_capital
        ) * 100

        # Calculate annualized return
        days = (market_data[-1].timestamp - market_data[0].timestamp).days
        years = Decimal(str(days / 365.25))
        annualized_return = (
            (
                (self.state.capital / self.config.initial_capital) ** (Decimal("1") / years)
                - Decimal("1")
            )
            * Decimal("100")
            if years > 0
            else Decimal("0")
        )

        # Update reallocation engine with strategy performance after backtest
        self._update_reallocation_engine(performance, total_return, market_data)

        return self._create_result(
            performance=performance,
            trades=self.state.trades,
            equity_curve=self.equity_tracker.get_equity_curve(),
            start_date=market_data[0].timestamp,
            end_date=market_data[-1].timestamp,
            final_capital=self.state.capital,
            total_return=total_return,
            annualized_return=annualized_return,
        )

    def _create_result(  # pylint: disable=arguments-differ
        self,
        performance: PerformanceMetrics,
        trades: List[Trade],
        equity_curve: List[Tuple[datetime, Decimal]],
        start_date: datetime,
        end_date: datetime,
        final_capital: Decimal,
        total_return: Decimal,
        annualized_return: Decimal,
        **kwargs,
    ) -> BacktestResult:
        """Create BacktestResult from calculated metrics."""
        return BacktestResult(
            config=self.config,
            trades=trades,
            performance=performance,
            equity_curve=equity_curve,
            start_date=start_date,
            end_date=end_date,
            final_capital=final_capital,
            total_return=total_return,
            annualized_return=annualized_return,
        )

    # =========================================================================
    # STANDARD ENGINE SPECIFIC METHODS
    # =========================================================================

    def _reset_backtest(self) -> None:
        """Reset backtest state."""
        super()._reset_backtest()
        self.state.trades.clear()
        self.position_manager.clear_all_positions()
        self.equity_tracker.reset()

    def _process_signals_at_timestamp(
        self,
        market_data: Any,
        signals: List[Signal],
        signal_index: int,
        signals_processed: int,
        signals_matched: int,
        signals_skipped: int,
        strategy_stats: Dict[str, Dict[str, int]],
    ) -> Tuple[int, int, int, int, Dict[str, Dict[str, int]]]:
        """Process all signals at the current timestamp."""
        while signal_index < len(signals):
            signal = signals[signal_index]

            # CRITICAL: Check if signal matches current market_data symbol FIRST
            if signal.symbol != market_data.symbol:
                break

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

            time_diff = (market_data.timestamp - signal.timestamp).total_seconds()
            signals_processed += 1

            if signal.symbol == market_data.symbol and time_diff >= -86400 and time_diff <= 86400:
                signals_matched += 1
                strategy_stats[strategy_name]["matched"] += 1
                self._process_signal(signal, market_data)
                signal_index += 1
            elif signal.timestamp > market_data.timestamp:
                break
            else:
                signals_skipped += 1
                strategy_stats[strategy_name]["skipped"] += 1
                signal_index += 1

        return signal_index, signals_processed, signals_matched, signals_skipped, strategy_stats

    def _process_signal(self, signal: Signal, market_data: Any) -> None:
        """Process a trading signal with compliance checks."""
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # COMPLIANCE: Check kill switch FIRST
        if self.compliance_engine.check_kill_switch():
            self._log_signal_rejected(
                signal.symbol,
                "kill_switch_active",
                "Kill switch triggered - trading halted",
            )
            return

        # Use SignalProcessor to validate and determine action
        action = self.signal_processor.process_signal(
            signal=signal,
            market_data=market_data,
            positions=self.position_manager.get_all_positions(),
            capital=self.state.capital,
            last_known_prices=self.state.last_known_prices,
            create_portfolio_func=self._create_portfolio_from_state,
            validate_profitability_func=self._validate_trade_profitability,
        )

        if action == "BUY":
            self._execute_buy_with_compliance(signal, market_data, strategy_name)
        elif action == "SELL":
            self._execute_sell_with_compliance(signal, market_data, strategy_name)

    def _execute_buy_with_compliance(
        self, signal: Signal, market_data: Any, strategy_name: str
    ) -> None:
        """Execute buy trade with compliance validation."""
        current_price = self._get_price(market_data)

        # Ask ComplianceEngine for position size
        estimated_quantity = self.compliance_engine.calculate_position_size(
            symbol=signal.symbol,
            price=current_price,
            capital=self.state.capital,
            confidence=signal.confidence if hasattr(signal, "confidence") else 100.0,
        )

        # Build price history for compliance engine validation
        price_history = self._build_price_history(
            symbol=signal.symbol,
            current_timestamp=market_data.timestamp,
        )

        # COMPLIANCE: Pre-trade analysis
        pre_trade_analysis = self.compliance_engine.analyze_pre_trade(
            symbol=signal.symbol,
            side="BUY",
            quantity=estimated_quantity,
            price=current_price,
            price_history=price_history,
            urgency=0.5,
            signal_time=signal.timestamp,
        )

        if not pre_trade_analysis.can_execute:
            self._log_signal_rejected(
                signal.symbol,
                "pre_trade_compliance",
                f"Pre-trade analysis rejected: {pre_trade_analysis.reasons}",
            )
            return

        # Execute buy trade
        trade, new_capital = self.trade_executor.execute_buy_signal(
            signal=signal,
            market_data=market_data,
            capital=self.state.capital,
            close_position_func=self._close_position,
            validate_profitability_func=self._validate_trade_profitability,
            position_size=estimated_quantity,
        )

        if trade:
            self.state.trades.append(trade)
            self.state.capital = new_capital

            # COMPLIANCE: Post-trade analysis
            self.compliance_engine.analyze_post_trade(
                order_id=trade.trade_id,
                symbol=trade.symbol,
                side="buy",
                quantity=trade.quantity,
                execution_price=trade.entry_price,
                signal_price=current_price,
                signal_time=signal.timestamp,
                submission_time=trade.entry_time,
                execution_time=trade.entry_time,
                nbbo=None,
            )

            self._register_buy_trade_for_learning(trade, signal, market_data)

    def _execute_sell_with_compliance(
        self, signal: Signal, market_data: Any, strategy_name: str
    ) -> None:
        """Execute sell trade with compliance validation."""
        current_price = self._get_price(market_data)
        current_position_qty = self.position_manager.get_position(signal.symbol)

        price_history = self._build_price_history(
            symbol=signal.symbol,
            current_timestamp=market_data.timestamp,
        )

        # COMPLIANCE: Pre-trade analysis
        pre_trade_analysis = self.compliance_engine.analyze_pre_trade(
            symbol=signal.symbol,
            side="SELL",
            quantity=Decimal(str(current_position_qty)),
            price=current_price,
            price_history=price_history,
            urgency=0.5,
            signal_time=signal.timestamp,
        )

        if not pre_trade_analysis.can_execute:
            self._log_signal_rejected(
                signal.symbol,
                "pre_trade_compliance",
                f"Pre-trade analysis rejected: {pre_trade_analysis.reasons}",
            )
            return

        # Execute sell trade
        trade, new_capital = self.trade_executor.execute_sell_signal(
            signal=signal,
            market_data=market_data,
            capital=self.state.capital,
            trades=self.state.trades,
        )

        if trade:
            self.state.trades.append(trade)
            self.state.capital = new_capital

            # COMPLIANCE: Post-trade analysis
            self.compliance_engine.analyze_post_trade(
                order_id=trade.trade_id,
                symbol=trade.symbol,
                side="sell",
                quantity=trade.quantity,
                execution_price=trade.exit_price or current_price,
                signal_price=current_price,
                signal_time=signal.timestamp,
                submission_time=trade.exit_time if trade.exit_time else trade.entry_time,
                execution_time=trade.exit_time if trade.exit_time else trade.entry_time,
                nbbo=None,
            )

            # Track daily P&L for kill switch monitoring
            if trade.exit_price and trade.entry_price:
                realized_pnl = float(
                    (trade.exit_price - trade.entry_price) * trade.quantity
                ) - float(trade.commission)
                self.compliance_engine.track_daily_pnl(
                    symbol=trade.symbol,
                    side="SELL",
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    realized_pnl=realized_pnl,
                )

            self._register_sell_trade_for_learning(trade, signal, market_data)

    def _validate_trade_profitability(self, signal: Signal, price: Decimal) -> bool:
        """Validate if a trade can be profitable after commission costs."""
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        commission_pct = self._get_strategy_commission(signal, strategy_name)
        if commission_pct is not None:
            return True

        commission = self.config.commission_per_trade
        if commission <= 0:
            return True

        take_profit_pct = self.config.take_profit_percentage
        if take_profit_pct is None:
            return True

        max_position_value = self.state.capital * self.config.max_position_size
        round_trip_commission = commission * 2

        commission_ratio = (
            round_trip_commission / max_position_value if max_position_value > 0 else Decimal("1")
        )

        if commission_ratio > Decimal("0.01"):
            min_position_value_needed = round_trip_commission / Decimal("0.01")
            if min_position_value_needed > self.state.capital:
                logger.warning(
                    f"TRADE REJECTED {signal.symbol} (strategy={strategy_name}): "
                    f"Commission ratio {commission_ratio:.2%} exceeds 1%"
                )
                return False

        expected_profit = max_position_value * take_profit_pct
        min_required_profit = round_trip_commission * 5

        if expected_profit <= min_required_profit:
            logger.warning(
                f"TRADE REJECTED {signal.symbol} (strategy={strategy_name}): "
                f"Expected profit ${expected_profit:.2f} < 5x commission ${min_required_profit:.2f}"
            )
            return False

        return True

    def _get_strategy_commission(self, signal: Signal, strategy_name: str) -> Optional[Decimal]:
        """Get commission percentage for strategy."""
        if signal.metadata and "commission_per_trade_pct" in signal.metadata:
            try:
                return Decimal(str(signal.metadata["commission_per_trade_pct"]))
            except (ValueError, TypeError, InvalidOperation):
                pass

        if self.strategy and hasattr(self.strategy, "commission_per_trade_pct"):
            return self.strategy.commission_per_trade_pct

        return None

    def _build_price_history(
        self, symbol: str, current_timestamp: datetime, lookback_days: int = 252
    ) -> Optional[pd.DataFrame]:
        """Build a price history DataFrame for compliance engine validation."""
        if not self._market_data_list:
            return None

        lookback_timestamp = current_timestamp - timedelta(days=lookback_days)
        historical_data = []

        for md in self._market_data_list:
            if md.symbol == symbol and lookback_timestamp <= md.timestamp <= current_timestamp:
                row = {
                    "timestamp": md.timestamp,
                    "open": getattr(md, "open", None) or getattr(md, "open_price", None),
                    "high": getattr(md, "high", None) or getattr(md, "high_price", None),
                    "low": getattr(md, "low", None) or getattr(md, "low_price", None),
                    "close": self._get_price(md),
                    "volume": getattr(md, "volume", 0),
                }
                historical_data.append(row)

        if not historical_data:
            return None

        df = pd.DataFrame(historical_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: float(x) if hasattr(x, "__float__") else x)

        return df

    def _create_portfolio_from_state(self, current_price_func=None) -> Portfolio:
        """Create a Portfolio object from current backtesting state."""
        positions = []

        for symbol, quantity in self.position_manager.get_all_positions().items():
            if quantity == 0:
                continue

            if current_price_func:
                market_price = current_price_func(symbol)
            elif symbol in self.state.last_known_prices:
                market_price = self.state.last_known_prices[symbol]
            else:
                market_price = None
                for trade in reversed(self.state.trades):
                    if trade.symbol == symbol:
                        market_price = trade.entry_price
                        break
                if not market_price:
                    market_price = Decimal("0")

            avg_price = market_price
            buy_trades = [
                t
                for t in self.state.trades
                if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
            ]
            if buy_trades:
                total_qty = sum(t.quantity for t in buy_trades)
                total_cost = sum(t.quantity * t.entry_price for t in buy_trades)
                if total_qty > 0:
                    avg_price = total_cost / total_qty

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

        return Portfolio(
            portfolio_id="backtest_portfolio",
            cash=self.state.capital,
            positions=positions,
            timestamp=datetime.utcnow(),
            broker="backtester",
            currency="USD",
        )

    def _close_position(
        self, symbol: str, timestamp: datetime, reason: str, current_price: Decimal = None
    ) -> None:
        """Close a position completely."""
        current_position = self.position_manager.get_position(symbol)

        if current_position <= 0:
            return

        recent_trades = [t for t in self.state.trades if t.symbol == symbol and t.side == "buy"]

        if not recent_trades:
            return

        pnl_info = self.pnl_calculator.calculate_close_position_pnl(
            symbol=symbol,
            quantity=current_position,
            exit_price=current_price or recent_trades[-1].entry_price,
            trades=self.state.trades,
        )

        exit_price_with_slippage = self._apply_slippage(
            current_price or recent_trades[-1].entry_price, False
        )

        trade = Trade(
            trade_id=str(uuid4()),
            symbol=symbol,
            side="sell",
            quantity=current_position,
            entry_price=pnl_info["avg_entry_price"],
            exit_price=current_price or recent_trades[-1].entry_price,
            entry_time=pnl_info["entry_time"] or timestamp,
            exit_time=timestamp,
            status=TradeStatus.CLOSED,
            pnl=pnl_info["pnl"],
            pnl_percentage=pnl_info["pnl_percentage"],
            commission=pnl_info["total_commission"],
            slippage=abs(
                current_position
                * (exit_price_with_slippage - (current_price or recent_trades[-1].entry_price))
            ),
            reason=reason,
        )

        for buy_trade in recent_trades:
            if buy_trade.status == TradeStatus.OPEN:
                buy_trade.status = TradeStatus.CLOSED
                buy_trade.exit_price = current_price or recent_trades[-1].entry_price
                buy_trade.exit_time = timestamp

        self.state.trades.append(trade)
        self.state.capital += (
            current_position * exit_price_with_slippage - pnl_info["total_commission"]
        )
        self.position_manager.close_position(symbol)

    def _close_all_positions(
        self, final_market_data: Any, price_map: Optional[Dict[str, Decimal]] = None
    ) -> None:
        """Close all remaining positions at the end of backtest."""
        for symbol in self.position_manager.get_symbols_with_positions():
            closing_price = None
            if price_map and symbol in price_map:
                closing_price = price_map[symbol]
            else:
                recent_trades_for_symbol = [
                    t for t in reversed(self.state.trades) if t.symbol == symbol
                ]
                if recent_trades_for_symbol:
                    closing_price = recent_trades_for_symbol[0].entry_price
                else:
                    closing_price = self._get_price(final_market_data)

            self._close_position(
                symbol, final_market_data.timestamp, "end_of_backtest", closing_price
            )

    def _execute_learning_retraining(self, market_data: Any, all_market_data: List) -> None:
        """Execute learning engine retraining if necessary."""
        if not (
            self.strategy
            and hasattr(self.strategy, "learning_engine")
            and self.strategy.learning_engine
        ):
            return

        from app.domain.strategies.learning.learning_updater import LearningEngineUpdater

        if not hasattr(self.strategy, "_learning_updater"):
            self.strategy._learning_updater = LearningEngineUpdater(
                learning_engine=self.strategy.learning_engine, rebalance_frequency_days=7
            )

        if hasattr(market_data, "close") or hasattr(market_data, "bid"):
            price = float(self._get_price(market_data))
            self.strategy._learning_updater.add_market_data(
                market_data={
                    "price": price,
                    "volume": float(getattr(market_data, "volume", 0)),
                    "symbol": market_data.symbol,
                },
                timestamp=market_data.timestamp,
            )

        try:
            market_data_index = all_market_data.index(market_data)
        except ValueError:
            market_data_index = -1

        self.strategy._learning_updater.retrain_if_needed(
            current_date=market_data.timestamp,
            quotes=all_market_data[: market_data_index + 1] if market_data_index >= 0 else None,
        )

    def _register_buy_trade_for_learning(
        self, trade: Trade, signal: Signal, market_data: Any
    ) -> None:
        """Register a buy trade for the learning engine."""
        if not (
            self.strategy
            and hasattr(self.strategy, "learning_engine")
            and self.strategy.learning_engine
        ):
            return

        if hasattr(self.strategy, "_learning_updater"):
            self.strategy._learning_updater.add_trade_result(
                trade={
                    "symbol": signal.symbol,
                    "entry_time": trade.entry_time,
                    "entry_price": float(trade.entry_price),
                    "quantity": float(trade.quantity),
                    "side": "buy",
                },
                timestamp=market_data.timestamp,
            )

    def _register_sell_trade_for_learning(
        self, trade: Trade, signal: Signal, market_data: Any
    ) -> None:
        """Register a sell trade result for the learning engine."""
        if not (
            self.strategy
            and hasattr(self.strategy, "learning_engine")
            and self.strategy.learning_engine
        ):
            return

        if hasattr(self.strategy, "_learning_updater"):
            self.strategy._learning_updater.add_trade_result(
                trade={
                    "symbol": signal.symbol,
                    "entry_time": trade.entry_time,
                    "exit_time": trade.exit_time,
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price),
                    "quantity": float(trade.quantity),
                    "pnl": float(trade.pnl) if trade.pnl else 0,
                    "side": "sell",
                },
                timestamp=market_data.timestamp,
            )

    def _update_reallocation_engine(
        self, performance: PerformanceMetrics, total_return: Decimal, market_data: List
    ) -> None:
        """Update reallocation engine with strategy performance after backtest."""
        if not (self.reallocation_engine and performance):
            return

        winning_trades = sum(1 for t in self.state.trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in self.state.trades if t.pnl and t.pnl <= 0)
        total_trades = len(self.state.trades)

        self.reallocation_engine.update_strategy_performance(
            strategy_name=self.strategy_name,
            timestamp=market_data[-1].timestamp,
            pnl=Decimal(str(performance.total_pnl)),
            returns=Decimal(str(total_return)),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

    # =========================================================================
    # PICKLE SUPPORT
    # =========================================================================

    def __getstate__(self) -> Dict[str, Any]:
        """Get state for pickling."""
        state = super().__getstate__()
        state.update(
            {
                "total_portfolio_capital": float(self.total_portfolio_capital),
            }
        )
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Restore state from pickling."""
        super().__setstate__(state)
        self.total_portfolio_capital = Decimal(str(state.get("total_portfolio_capital", "100000")))
        self._initialize_services(None)


# Backward compatibility alias
SimpleBacktester = StandardBacktestEngine
