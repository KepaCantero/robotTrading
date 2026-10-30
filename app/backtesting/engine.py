"""
Backtesting engine for AlgoTrading system.

This module provides the core backtesting functionality including
historical data simulation, trade execution, and performance metrics calculation.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.backtesting.base_engine import SlippageParams
    from app.domain.models.market_data import Quote
    from app.domain.models.signal import Signal
    from app.services.dynamic_capital_reallocation import DynamicCapitalReallocationEngine

from uuid import uuid4

from app.backtesting.liquidity_validator import LiquidityValidator
from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    TradeStatus,
)
from app.backtesting.services.equity_tracker import EquityCurveTracker
from app.backtesting.services.exit_monitor import ExitConditionMonitor
from app.backtesting.services.performance_calculator import PerformanceMetricsCalculator
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator
from app.backtesting.services.position_manager import PositionManager
from app.backtesting.services.signal_processor import SignalProcessor
from app.backtesting.services.trade_executor import TradeExecutor

# SHARED UTILITIES: Centralized slippage and trade utilities
from app.backtesting.shared.slippage_utils import apply_slippage as shared_apply_slippage
from app.backtesting.shared.trade_utils import build_trade_reason as shared_build_trade_reason
from app.domain.models.portfolio import AssetClass, Portfolio, Position

# COMPLIANCE: Import compliance_engine - "THE ONLY ENGINE" that must be used
from app.domain.services.compliance.compliance_engine import ComplianceEngine
from app.domain.services.trading_validators import TradingValidator
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# Get centralized backtesting configuration
_config = get_config()
_backtest_config = _config.backtesting


def get_price(md) -> Decimal:
    """Get closing price from MarketData or Quote object."""
    # Try Quote first (has 'close' attribute)
    if hasattr(md, "close"):
        return md.close
    # Try MarketData (has 'close_price' attribute)
    elif hasattr(md, "close_price"):
        return md.close_price
    else:
        raise AttributeError(
            f"MarketData object has no 'close' or 'close_price' attribute: {type(md)}"
        )


def reset_live_trading_gates() -> None:
    """Reset live-trading gates that misfire on historical replay.

    The compliance engine and the Harris microstructure integrator keep
    process-wide singletons: the kill switch tracks P&L across everything
    the process ever simulated, and the quote-stuffing detector counts quotes
    per wall-clock second (years of daily bars replayed in seconds look like
    150+ quotes/sec). Backtests are offline simulations — each one starts
    from clean gates.
    """
    from app.engines.execution_engine.microstructure import harris_integration

    harris_integration._harris_integrator = None  # noqa: SLF001 - singleton reset
    ComplianceEngine._instance = None  # noqa: SLF001 - singleton reset


class BacktestEngine:
    """
    Backtesting engine for trading strategies.

    This engine orchestrates trade execution with configurable slippage,
    commission, and risk management parameters using specialized service classes.
    """

    def __init__(
        self,
        config: BacktestConfig,
        diagnostic_logger=None,
        strategy=None,
        enable_risk_envelope: bool = True,
        compliance_engine: ComplianceEngine | None = None,
        strategy_name: str = "unknown",
        total_portfolio_capital: Decimal | None = None,
        reallocation_engine: DynamicCapitalReallocationEngine | None = None,
    ):
        """
        Initialize the backtesting engine.

        Args:
            config: Backtest configuration
            diagnostic_logger: Optional diagnostic logger
            strategy: Strategy instance for risk_check (optional but required for risk checking)
            enable_risk_envelope: Enable risk envelope validation (default True)
            compliance_engine: Optional ComplianceEngine instance (uses singleton if not provided)
            strategy_name: Name of strategy for risk envelope logging
            total_portfolio_capital: Total portfolio capital for multi-strategy scenarios (defaults to initial_capital)
            reallocation_engine: Optional DynamicCapitalReallocationEngine instance for performance tracking
        """
        self.config = config
        self.capital = config.initial_capital
        self.diagnostic_logger = diagnostic_logger
        self.strategy = strategy  # Strategy instance for risk_check
        self.strategy_name = strategy_name
        self.total_portfolio_capital = total_portfolio_capital or config.initial_capital
        self.reallocation_engine = reallocation_engine

        # Every backtest is an isolated simulation: start it from clean
        # live-trading gates. ComplianceEngine is a process singleton whose
        # kill switch / quote-stuffing state would otherwise leak from the
        # previous backtest (walk-forward windows, optimizer trials, dashboard
        # runs) and silently reject every later trade.
        if compliance_engine is None:
            reset_live_trading_gates()

        # Track last known price for each symbol for accurate equity curve calculation
        self.last_known_prices: dict[str, Decimal] = {}

        # Signals matched on bar t awaiting execution at the open of the next
        # bar for their symbol (next_day_execution=True)
        self._pending_signals: dict[str, list[Signal]] = {}

        # Store market_data for building price_history for compliance engine
        self._market_data_list: list[Quote] = []

        # Initialize service classes
        # PositionManager - pure state holder for positions
        self.position_manager = PositionManager()

        # EquityCurveTracker - tracks portfolio value over time
        self.equity_tracker = EquityCurveTracker(
            position_manager=self.position_manager,
            initial_capital=config.initial_capital,
        )

        # ProfitAndLossCalculator - calculates trade profitability
        self.pnl_calculator = ProfitAndLossCalculator(config)

        # SignalProcessor - validates and processes trading signals
        self.signal_processor = SignalProcessor(
            config=config,
            strategy=strategy,
            compliance_engine=compliance_engine,
            enable_risk_envelope=enable_risk_envelope,
            diagnostic_logger=diagnostic_logger,
            total_portfolio_capital=self.total_portfolio_capital,
            strategy_name=strategy_name,
        )

        # TradeExecutor - executes buy and sell trades
        self.trade_executor = TradeExecutor(
            config=config,
            position_manager=self.position_manager,
            pnl_calculator=self.pnl_calculator,
            diagnostic_logger=diagnostic_logger,
            strategy=strategy,
        )

        # ExitConditionMonitor - monitors stop-loss and take-profit
        self.exit_monitor = ExitConditionMonitor(
            config=config,
            position_manager=self.position_manager,
            apply_slippage_func=self._apply_slippage,
        )

        # PerformanceMetricsCalculator - calculates performance metrics
        self.performance_calculator = PerformanceMetricsCalculator(config)

        # Keep trade list for P&L calculations
        self.trades: list[Trade] = []

        # Initialize validators (keep for backward compatibility)
        self.trading_validator = TradingValidator()
        self.liquidity_validator = LiquidityValidator(
            enable_partial_fills=_backtest_config.liquidity_enable_partial_fills,
            max_order_pct_of_volume=_backtest_config.liquidity_max_order_pct_of_volume,
            warning_order_pct_of_volume=_backtest_config.liquidity_warning_order_pct_of_volume,
            partial_fill_pct=_backtest_config.liquidity_partial_fill_pct,
        )

        # COMPLIANCE: Initialize compliance_engine - "THE ONLY ENGINE" per documentation
        # This engine integrates ALL 17 systems (8 main + 12 compliance rules)
        # All trades MUST be validated through analyze_pre_trade() and analyze_post_trade()
        self.compliance_engine = ComplianceEngine(
            enable_logging=_backtest_config.compliance_enable_logging,
        )
        # Set starting capital for kill switch calculations (Hull Rule 13.1)
        self.compliance_engine.set_starting_capital(float(config.initial_capital))

        #: sizing base shared by all BUYs of one trading day (see run loop)
        self._sizing_capital: Decimal | None = None
        self._sizing_day = None

        #: D05: live strategy receiving fill feedback during the run
        self._live_strategy: Any = None

        logger.info(f"BacktestEngine initialized for {strategy_name} with COMPLIANCE ENGINE")

    def _notify_live(
        self,
        symbol: str,
        side: str,
        status: str,
        requested: Decimal,
        filled: Decimal,
    ) -> None:
        """D05: execution feedback to the live strategy (never throws)."""
        hook = getattr(self._live_strategy, "on_fill", None)
        if hook is None:
            return
        try:
            hook(
                symbol=symbol,
                side=side,
                status=status,
                requested_qty=requested,
                filled_qty=filled,
            )
        except Exception:  # noqa: BLE001 - feedback must never break the run
            logger.exception("on_fill feedback failed for %s (%s)", symbol, status)

    # ==========================================================================
    # CONVENIENCE WRAPPERS (for testing / backward compatibility)
    # ==========================================================================

    @property
    def positions(self) -> dict[str, Decimal]:
        """Convenience accessor for position_manager.positions (backward compatibility)."""
        return self.position_manager.positions

    def _execute_buy_signal(self, signal: Signal, market_data: Quote) -> None:
        """
        Convenience wrapper to execute a buy signal for testing.

        Calculates position size internally and delegates to the trade_executor.

        Args:
            signal: Buy signal to execute
            market_data: Current market data (quote)
        """
        current_price = get_price(market_data)

        # Calculate position size: use max_position_size fraction of capital
        position_value = self.capital * self.config.max_position_size
        position_size = position_value / current_price

        trade, new_capital = self.trade_executor.execute_buy_signal(
            signal=signal,
            market_data=market_data,
            capital=self.capital,
            close_position_func=self._close_position,
            validate_profitability_func=self._validate_trade_profitability,
            position_size=position_size,
        )
        if trade:
            self.trades.append(trade)
            self.capital = new_capital

    def _check_exit_conditions(self, market_data: Quote) -> bool:
        """
        Convenience wrapper to check exit conditions for testing.

        Delegates to exit_monitor.check_exit_conditions.

        Args:
            market_data: Current market data (quote)

        Returns:
            True if a position was closed
        """
        return self.exit_monitor.check_exit_conditions(
            market_data=market_data,
            trades=self.trades,
            close_position_func=self._close_position,
        )

    # ==========================================================================
    # PICKLE SUPPORT (for multiprocessing)
    # ==========================================================================

    def __getstate__(self) -> dict[str, object]:
        """
        Get state for pickling (excludes unpicklable objects).

        The BacktestEngine contains unpicklable objects (thread locks in
        compliance_engine, diagnostic_logger, strategy). For multiprocessing,
        we extract the essential configuration and let each worker create
        a fresh engine instance.
        """
        state: dict[str, object] = {
            "config": self.config,
            "strategy_name": self.strategy_name,
            "total_portfolio_capital": self.total_portfolio_capital,
            # Reset runtime state for worker processes
            "capital": self.config.initial_capital,
            "last_known_prices": {},
            "trades": [],
            "_pending_signals": {},
        }
        return state

    def __setstate__(self, state: dict[str, object]) -> None:
        """
        Restore state from pickling (reinitializes engine in worker process).

        Creates a fresh BacktestEngine instance in the worker process with
        the same configuration but independent state.
        """
        self.__dict__.update(state)
        # Recreate all service objects
        self.position_manager = PositionManager()
        self.equity_tracker = EquityCurveTracker(
            position_manager=self.position_manager,
            initial_capital=self.config.initial_capital,
        )
        self.pnl_calculator = ProfitAndLossCalculator(self.config)
        self.signal_processor = SignalProcessor(
            config=self.config,
            strategy=None,  # Strategy is not picklable, set to None
            compliance_engine=None,
            enable_risk_envelope=False,
            diagnostic_logger=None,
            total_portfolio_capital=self.total_portfolio_capital,
            strategy_name=self.strategy_name,
        )
        self.trade_executor = TradeExecutor(
            config=self.config,
            position_manager=self.position_manager,
            pnl_calculator=self.pnl_calculator,
            diagnostic_logger=None,
            strategy=None,
        )
        self.exit_monitor = ExitConditionMonitor(
            config=self.config,
            position_manager=self.position_manager,
            apply_slippage_func=self._apply_slippage,
        )
        self.performance_calculator = PerformanceMetricsCalculator(self.config)
        self.trading_validator = TradingValidator()
        self.liquidity_validator = LiquidityValidator(
            enable_partial_fills=_backtest_config.liquidity_enable_partial_fills,
            max_order_pct_of_volume=_backtest_config.liquidity_max_order_pct_of_volume,
            warning_order_pct_of_volume=_backtest_config.liquidity_warning_order_pct_of_volume,
            partial_fill_pct=_backtest_config.liquidity_partial_fill_pct,
        )
        # Recreate compliance engine (it has its own pickle support)
        self.compliance_engine = ComplianceEngine(enable_logging=False)
        self.compliance_engine.set_starting_capital(float(self.config.initial_capital))
        self.diagnostic_logger = None
        self.strategy = None
        self.reallocation_engine = None

    def run_backtest(
        self,
        market_data: list[Quote],
        signals: list[Signal],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        live_strategy: Any = None,
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

        # D05: live mode — the strategy generates per bar DURING the run
        # (instead of a precomputed list) and receives fill feedback
        # (rejections, partial fills, stop closes) BEFORE its next decision.
        self._live_strategy = live_strategy
        if live_strategy is not None:
            logger.info(
                "Live strategy mode: %s generates per bar with on_fill feedback",
                type(live_strategy).__name__,
            )

        logger.info(
            f"Backtest starting: {len(market_data)} market_data points, {len(signals)} signals"
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

        # Store market_data for compliance engine price_history
        self._market_data_list = market_data

        # Process each market data point
        signal_index = 0
        signals_processed = 0
        signals_matched = 0
        signals_skipped = 0
        # Track matching stats by strategy
        strategy_stats: dict[str, dict[str, int]] = {}

        last_md = None
        for md in market_data:
            # Sizing base per trading day: simultaneous buys (rebalance day of
            # a cross-sectional strategy) must each size the SAME portfolio —
            # sizing on post-fill capital deployed only 1-(1-r)^n of intended
            day = md.timestamp.date()
            if day != self._sizing_day:
                # Cierre del día PREVIO: marcar la cartera UNA VEZ por día,
                # cuando todos los símbolos ya tienen su último precio. La
                # marca por cotización mezclaba precios de días distintos
                # dentro del mismo punto (el primer símbolo del crash en su
                # mínimo, el resto aún al cierre previo) y suavizaba los
                # drawdowns ~7pp (COVID: -29% engine vs -36% cierre diario).
                if last_md is not None:
                    self.equity_tracker.update_equity_curve(
                        last_md.timestamp, self.capital, self.last_known_prices
                    )
                self._sizing_day = day
                self._sizing_capital = None
                # Kill switch is DAILY (Hull Rule 13.1): a new simulated day
                # must clear the previous day's tally, otherwise the breaker
                # latches forever once its own rejection stops new trades from
                # ever rolling the day over.
                self.compliance_engine.reset_daily_tracking()

            # Execute signals matched on a previous bar of this symbol at the
            # OPEN of the current bar (t+1 execution, prevents look-ahead bias)
            self._execute_pending_signals(md)

            # Track the current price for this symbol
            current_md_price = get_price(md)
            self.last_known_prices[md.symbol] = current_md_price

            # Execute learning engine retraining if needed
            self._execute_learning_retraining(md, market_data)

            # Process signals for this timestamp — in live mode (D05) the
            # strategy generates THIS bar's signals right here, after the
            # t+1 fills above notified their outcomes: decisions always
            # follow the freshest execution state.
            if self._live_strategy is not None:
                bar_signals = self._live_strategy.generate_signals(md)
                # A cross-sectional rebalance emits orders for the WHOLE
                # target book on the triggering bar. The static-list path
                # relies on each symbol's signal being matched at its own
                # bar later; a live batch must be queued IN FULL here —
                # the pending queue fills each at its own symbol's next
                # bar open (t+1), so pricing stays per-symbol.
                for live_signal in bar_signals:
                    signals_processed += 1
                    signals_matched += 1
                    strategy_name = (
                        live_signal.metadata.get("strategy", "live")
                        if live_signal.metadata
                        else "live"
                    )
                    strategy_stats.setdefault(
                        strategy_name,
                        {"matched": 0, "skipped": 0, "symbol_mismatch": 0, "time_mismatch": 0},
                    )
                    strategy_stats[strategy_name]["matched"] += 1
                    self._pending_signals.setdefault(live_signal.symbol, []).append(live_signal)
            else:
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
                trades=self.trades,
                close_position_func=self._close_position,
            )
            last_md = md

        # Último día: cierre marcado con los precios finales antes de cerrar
        # posiciones (el cierre forzado ya no debe mover la curva)
        if last_md is not None:
            self.equity_tracker.update_equity_curve(
                last_md.timestamp, self.capital, self.last_known_prices
            )

        # Close any remaining positions using the last price for each symbol
        price_map = self._build_price_map(market_data)
        self._close_all_positions(market_data[-1], price_map=price_map)

        # Signals still pending had no subsequent bar for their symbol to fill at
        if self._pending_signals:
            dropped = sum(len(v) for v in self._pending_signals.values())
            logger.info(f"Dropped {dropped} pending signal(s) with no subsequent bar to fill at")
            self._pending_signals.clear()

        logger.info(
            f"Backtest matching stats: {signals_processed} processed, {signals_matched} matched, {signals_skipped} skipped, {len(self.trades)} trades executed"
        )

        # Log stats by strategy
        if strategy_stats:
            logger.info("Matching stats by strategy:")
            for strategy_name, stats in sorted(strategy_stats.items()):
                logger.info(
                    f"  {strategy_name}: {stats['matched']} matched, {stats['skipped']} skipped "
                    f"(symbol_mismatch={stats['symbol_mismatch']}, time_mismatch={stats['time_mismatch']})"
                )

        # Calculate final metrics
        performance = self.performance_calculator.calculate_performance_metrics(
            trades=self.trades,
            # Decimal fraction from peak equity (contract: PerformanceMetrics.max_drawdown)
            max_drawdown=self.equity_tracker.get_max_drawdown_percentage() / Decimal("100"),
            initial_capital=self.config.initial_capital,
            equity_returns=self.equity_tracker.calculate_returns(),
        )

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
        self._update_reallocation_engine(performance, total_return, market_data)

        return BacktestResult(
            config=self.config,
            trades=self.trades,
            performance=performance,
            equity_curve=self.equity_tracker.get_equity_curve(),
            start_date=market_data[0].timestamp,
            end_date=market_data[-1].timestamp,
            final_capital=self.capital,
            total_return=total_return,
            annualized_return=annualized_return,
        )

    def _build_price_history(
        self, symbol: str, current_timestamp: datetime, lookback_days: int = 252
    ):
        """
        Build a price history DataFrame for compliance engine validation.

        Args:
            symbol: Symbol to build history for
            current_timestamp: Current timestamp (get data up to this point)
            lookback_days: Number of days to look back (default 252 trading days)

        Returns:
            pandas DataFrame with OHLCV data and DatetimeIndex, or None if no data
        """
        from datetime import timedelta

        import pandas as pd

        if not self._market_data_list:
            return None

        # Calculate lookback timestamp
        lookback_timestamp = current_timestamp - timedelta(days=lookback_days)

        # Filter market data for this symbol up to current timestamp
        historical_data = []
        for md in self._market_data_list:
            if md.symbol == symbol and lookback_timestamp <= md.timestamp <= current_timestamp:
                # Extract OHLCV data
                row = {
                    "timestamp": md.timestamp,
                    "open": getattr(md, "open", None) or getattr(md, "open_price", None),
                    "high": getattr(md, "high", None) or getattr(md, "high_price", None),
                    "low": getattr(md, "low", None) or getattr(md, "low_price", None),
                    "close": get_price(md),
                    "volume": getattr(md, "volume", 0),
                }
                historical_data.append(row)

        if not historical_data:
            return None

        # Build DataFrame with DatetimeIndex
        df = pd.DataFrame(historical_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        # Convert Decimal to float for pandas compatibility
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: float(x) if hasattr(x, "__float__") else x)

        return df

    def _reset_backtest(self) -> None:
        """Reset backtest state."""
        self.capital = self.config.initial_capital
        self.trades.clear()
        self.position_manager.clear_all_positions()
        self.equity_tracker.reset()
        self.last_known_prices.clear()
        self._pending_signals.clear()
        self._sizing_capital = None
        self._sizing_day = None

    def _execute_learning_retraining(
        self, market_data: Quote, all_market_data: list[Quote]
    ) -> None:
        """
        Execute learning engine retraining if necessary.

        Args:
            market_data: Current market data point
            all_market_data: All market data for learning context
        """
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

        # Add market data to history
        if hasattr(market_data, "close") or hasattr(market_data, "bid"):
            price = float(get_price(market_data))
            self.strategy._learning_updater.add_market_data(
                market_data={
                    "price": price,
                    "volume": float(getattr(market_data, "volume", 0)),
                    "symbol": market_data.symbol,
                },
                timestamp=market_data.timestamp,
            )

        # Try to retrain if needed
        try:
            market_data_index = all_market_data.index(market_data)
        except ValueError:
            market_data_index = -1

        self.strategy._learning_updater.retrain_if_needed(
            current_date=market_data.timestamp,
            quotes=all_market_data[: market_data_index + 1] if market_data_index >= 0 else None,
        )

    def _execute_pending_signals(self, market_data: Quote) -> None:
        """
        Execute signals queued on previous bars at the current bar's open.

        Only called when config.next_day_execution is True. Queued signals
        whose symbol never reappears in the data are dropped (no fill on a
        bar that does not exist).

        Args:
            market_data: Current bar (fill happens at its open)
        """
        pending = self._pending_signals.get(market_data.symbol)
        if not pending:
            return

        del self._pending_signals[market_data.symbol]
        open_view = self._open_price_view(market_data)
        for signal in pending:
            logger.debug(
                f"T+1 EXECUTION: {signal.symbol} {signal.signal_type} "
                f"(strategy={signal.metadata.get('strategy', 'unknown') if signal.metadata else 'unknown'}) "
                f"signal={signal.timestamp} filled at open of {market_data.timestamp}"
            )
            self._process_signal(signal, open_view)

    @staticmethod
    def _open_price_view(md: Quote) -> Quote:
        """
        Return a copy of the bar priced at its open for t+1 open execution.

        The fill chain derives base prices from close/last/ask/bid, so those
        fields are replaced with the open. High/low/volume stay real (they
        are only used for exit checks and liquidity on later bars).
        """
        open_price = getattr(md, "open", None)
        if open_price is None:
            return md
        update: dict[str, Decimal] = {"close": open_price, "last": open_price}
        if getattr(md, "ask", None) is not None:
            update["ask"] = open_price
        if getattr(md, "bid", None) is not None:
            update["bid"] = open_price
        return md.model_copy(update=update)

    def _process_signals_at_timestamp(
        self,
        market_data: Quote,
        signals: list[Signal],
        signal_index: int,
        signals_processed: int,
        signals_matched: int,
        signals_skipped: int,
        strategy_stats: dict[str, dict[str, int]],
    ) -> tuple[int, int, int, int, dict[str, dict[str, int]]]:
        """
        Process all signals at the current timestamp.

        CRITICAL: Only process signals that match the current market_data symbol.
        Signals from other symbols are skipped (but signal_index is NOT advanced,
        so they can be processed when their corresponding market_data is encountered).

        Returns:
            Tuple of (signal_index, signals_processed, signals_matched, signals_skipped, strategy_stats)
        """
        while signal_index < len(signals):
            signal = signals[signal_index]

            # CRITICAL: Check if signal matches current market_data symbol FIRST
            # If signal.symbol != market_data.symbol, we need to skip this signal
            # for NOW (do NOT advance signal_index) - it will be processed when
            # we encounter market_data for that symbol.
            if signal.symbol != market_data.symbol:
                # Signal is for a different symbol, stop processing current market_data
                # The signal will be processed when we reach its corresponding market_data
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

            # Allow signals up to 1 day in the past (signals are generated on market data)
            time_diff = (market_data.timestamp - signal.timestamp).total_seconds()

            signals_processed += 1

            # CRITICAL: Log all Momentum signals for debugging
            if strategy_name == "momentum":
                logger.info(
                    f"MOMENTUM SIGNAL: {signal.symbol} {signal.signal_type} | "
                    f"MD: {market_data.symbol} | "
                    f"symbol_match={signal.symbol == market_data.symbol} | "
                    f"time_diff={time_diff:.0f}s | "
                    f"signal_time={signal.timestamp} | "
                    f"md_time={market_data.timestamp}"
                )

            # A signal may only execute on a bar at or after its timestamp:
            # time_diff >= 0 (signals from the future are never executed) and
            # at most 1 day old (older signals are stale and skipped).
            if signal.symbol == market_data.symbol and 0 <= time_diff <= 86400:
                signals_matched += 1
                strategy_stats[strategy_name]["matched"] += 1
                if strategy_name == "momentum":
                    logger.info(
                        f"MOMENTUM MATCHED: {signal.symbol} {signal.signal_type} at {market_data.timestamp}, time_diff={time_diff:.0f}s"
                    )
                else:
                    logger.debug(
                        f"MATCHED signal: {signal.symbol} {signal.signal_type} (strategy={strategy_name}) at {market_data.timestamp}, time_diff={time_diff:.0f}s"
                    )
                if self.config.next_day_execution:
                    # Queue for execution at the open of this symbol's next bar
                    self._pending_signals.setdefault(signal.symbol, []).append(signal)
                else:
                    self._process_signal(signal, market_data)
                signal_index += 1
            elif signal.timestamp > market_data.timestamp:
                # Signal is in the future, wait for next market data
                if strategy_name == "momentum":
                    logger.debug(
                        f"MOMENTUM FUTURE: signal {signal.timestamp} > md {market_data.timestamp}, waiting..."
                    )
                break
            else:
                # Signal symbol doesn't match or too old, skip it
                signals_skipped += 1
                strategy_stats[strategy_name]["skipped"] += 1
                if signal.symbol != market_data.symbol:
                    strategy_stats[strategy_name]["symbol_mismatch"] += 1
                    if signals_skipped <= 10 or strategy_name == "momentum":
                        logger.info(
                            f"MOMENTUM SKIP: symbol mismatch {signal.symbol} != {market_data.symbol} (time_diff={time_diff:.0f}s)"
                        )
                elif abs(time_diff) > 86400:
                    strategy_stats[strategy_name]["time_mismatch"] += 1
                    if signals_skipped <= 10 or strategy_name == "momentum":
                        logger.info(
                            f"MOMENTUM SKIP: timestamp too far {time_diff:.0f}s (signal={signal.timestamp}, md={market_data.timestamp})"
                        )
                signal_index += 1

        return signal_index, signals_processed, signals_matched, signals_skipped, strategy_stats

    def _process_signal(self, signal: Signal, market_data: Quote) -> None:
        """
        Process a trading signal using the SignalProcessor and TradeExecutor services.

        COMPLIANCE: All trades MUST be validated through compliance_engine:
        - analyze_pre_trade() before executing any trade
        - analyze_post_trade() after executing any trade
        - check_kill_switch() checked before processing

        Args:
            signal: Trading signal to process
            market_data: Current market data
        """
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # COMPLIANCE: Check kill switch FIRST (Hull Rule 13.1)
        # If kill switch is active, block new ENTRIES; exits stay allowed so
        # the strategy can still de-risk on the very day the breaker trips.
        if self.compliance_engine.check_kill_switch() and signal.signal_type != "SELL":
            logger.warning(
                f"COMPLIANCE BLOCK: {signal.symbol} {signal.signal_type} (strategy={strategy_name}): "
                f"Kill switch active - trade rejected"
            )
            if self.diagnostic_logger:
                self.diagnostic_logger.log_signal_rejected(
                    strategy_name,
                    signal.symbol,
                    "kill_switch_active",
                    "Kill switch triggered - trading halted",
                    signal.metadata if hasattr(signal, "metadata") else {},
                )
            self._notify_live(
                signal.symbol,
                str(signal.signal_type).lower().replace("signaltype.", ""),
                "rejected",
                Decimal("0"),  # Signal carries no quantity (sizing is by
                Decimal("0"),  # position_weight) — caught by the B5 run
            )
            return  # Do NOT process this signal

        # Use SignalProcessor to validate and determine action
        action = self.signal_processor.process_signal(
            signal=signal,
            market_data=market_data,
            positions=self.position_manager.get_all_positions(),
            capital=self.capital,
            last_known_prices=self.last_known_prices,
            create_portfolio_func=self._create_portfolio_from_state,
            validate_profitability_func=self._validate_trade_profitability,
        )

        if action == "BUY":
            # COMPLIANCE: Calculate position size FIRST (backtesting is "stupid", asks compliance engine)
            current_price = get_price(market_data)

            # Ask ComplianceEngine for position size. The engine's own
            # max_position_size must govern: without it the sizer falls back
            # to the compliance singleton default (10%), silently capping
            # every strategy at ~8% per position and leaving most capital idle.
            # Base: the FIRST buy of the trading day snapshots the portfolio
            # (after same-day sells, if any); the rest of the day's buys size
            # that same portfolio instead of the post-fill remains.
            if self._sizing_capital is None:
                # Base de sizing = PATRIMONIO marcado (caja + posiciones al
                # último cierre), NO la caja restante: un símbolo que entra
                # meses después (VYMI tras acumular historia) se dimensionaba
                # contra el cash sobrante (31k en vez del equity 93k) y el
                # libro quedaba crónicamente infra-desplegado (~76%).
                self._sizing_capital = self.equity_tracker.get_current_portfolio_value(
                    self.capital, self.last_known_prices
                )
            # Peso declarado por la estrategia para ESTA señal (mangas con
            # pesos distintos: core vs satélite). El clamp solo limita POR
            # ARRIBA (25%, el techo real del validador): el viejo suelo del
            # 5% inflaba el 0.19% de una cartera exhaustiva de 500 nombres
            # a un 5% — orden de $5.000 contra un cap de $1.000, y TODAS
            # las compras rechazadas en bucle (cacería 30-10).
            sizing_ratio = float(self.config.max_position_size)
            declared = (signal.metadata or {}).get("position_weight")
            if declared is not None:
                try:
                    declared_ratio = float(declared)
                except (TypeError, ValueError):
                    logger.warning(
                        "Invalid position_weight %r on %s signal; using config default",
                        declared,
                        signal.symbol,
                    )
                else:
                    if declared_ratio > 0:
                        sizing_ratio = min(0.25, declared_ratio)
            estimated_quantity = self.compliance_engine.calculate_position_size(
                symbol=signal.symbol,
                price=current_price,
                capital=self._sizing_capital,
                confidence=signal.confidence if hasattr(signal, "confidence") else 100.0,
                max_position_ratio=sizing_ratio,
            )

            # Build price history for compliance engine validation
            price_history = self._build_price_history(
                symbol=signal.symbol,
                current_timestamp=market_data.timestamp,
            )

            # COMPLIANCE: Pre-trade analysis with estimated quantity
            pre_trade_analysis = self.compliance_engine.analyze_pre_trade(
                symbol=signal.symbol,
                side="BUY",
                quantity=estimated_quantity,  # Now using estimated quantity, not Decimal("0")!
                price=current_price,
                price_history=price_history,
                urgency=0.5,
                signal_time=signal.timestamp,
            )

            # COMPLIANCE: Check if trade is approved by compliance engine
            if not pre_trade_analysis.can_execute:
                logger.warning(
                    f"COMPLIANCE BLOCK: {signal.symbol} BUY (strategy={strategy_name}): "
                    f"Pre-trade analysis rejected - {pre_trade_analysis.reasons}"
                )
                if self.diagnostic_logger:
                    self.diagnostic_logger.log_signal_rejected(
                        strategy_name,
                        signal.symbol,
                        "pre_trade_compliance",
                        f"Pre-trade analysis rejected: {pre_trade_analysis.reasons}",
                        signal.metadata if hasattr(signal, "metadata") else {},
                    )
                self._notify_live(
                    signal.symbol, "buy", "rejected", estimated_quantity, Decimal("0")
                )
                return  # Do NOT execute this trade

            # Execute buy trade - pass position_size from ComplianceEngine to avoid duplication
            trade, new_capital = self.trade_executor.execute_buy_signal(
                signal=signal,
                market_data=market_data,
                capital=self.capital,
                close_position_func=self._close_position,
                validate_profitability_func=self._validate_trade_profitability,
                position_size=estimated_quantity,  # Use quantity from ComplianceEngine
                # the max-position-% check must use the day's portfolio (the
                # sizing base), not post-fill cash — see _sizing_capital
                validation_capital=self._sizing_capital,
            )
            if trade:
                self.trades.append(trade)
                self.capital = new_capital
                self._notify_live(
                    signal.symbol, "buy", "filled", estimated_quantity, trade.quantity
                )

                # COMPLIANCE: Post-trade analysis - validate execution quality
                post_trade_analysis = self.compliance_engine.analyze_post_trade(
                    order_id=trade.trade_id,
                    symbol=trade.symbol,
                    side="buy",
                    quantity=trade.quantity,
                    execution_price=trade.entry_price,
                    signal_price=current_price,
                    signal_time=signal.timestamp,
                    submission_time=trade.entry_time,
                    execution_time=trade.entry_time,
                    nbbo=None,  # NBBO not available in backtesting
                )

                # Log post-trade analysis if SLO not met
                if not post_trade_analysis.slo_met:
                    logger.warning(
                        f"COMPLIANCE WARNING: {signal.symbol} BUY (strategy={strategy_name}): "
                        f"SLO not met - latency={post_trade_analysis.latency_ms:.2f}ms"
                    )

                # Register trade for learning engine
                self._register_buy_trade_for_learning(trade, signal, market_data)
            else:
                # executor refused (e.g. profitability validation): the live
                # strategy must learn the buy never happened (D05)
                self._notify_live(
                    signal.symbol, "buy", "rejected", estimated_quantity, Decimal("0")
                )

        elif action == "SELL":
            # COMPLIANCE: Pre-trade analysis - validate sell trade before execution
            current_price = get_price(market_data)

            # Get current position quantity for SELL (from position_manager)
            current_position_qty = self.position_manager.get_position(signal.symbol)

            # Build price history for compliance engine validation
            price_history = self._build_price_history(
                symbol=signal.symbol,
                current_timestamp=market_data.timestamp,
            )

            # COMPLIANCE: Pre-trade analysis with actual position quantity
            pre_trade_analysis = self.compliance_engine.analyze_pre_trade(
                symbol=signal.symbol,
                side="SELL",
                quantity=Decimal(
                    str(current_position_qty)
                ),  # Actual position quantity, not Decimal("0")!
                price=current_price,
                price_history=price_history,
                urgency=0.5,
                signal_time=signal.timestamp,
            )

            # COMPLIANCE: Check if trade is approved by compliance engine
            if not pre_trade_analysis.can_execute:
                logger.warning(
                    f"COMPLIANCE BLOCK: {signal.symbol} SELL (strategy={strategy_name}): "
                    f"Pre-trade analysis rejected - {pre_trade_analysis.reasons}"
                )
                if self.diagnostic_logger:
                    self.diagnostic_logger.log_signal_rejected(
                        strategy_name,
                        signal.symbol,
                        "pre_trade_compliance",
                        f"Pre-trade analysis rejected: {pre_trade_analysis.reasons}",
                        signal.metadata if hasattr(signal, "metadata") else {},
                    )
                self._notify_live(
                    signal.symbol,
                    "sell",
                    "rejected",
                    Decimal(str(current_position_qty)),
                    Decimal("0"),
                )
                return  # Do NOT execute this trade

            # Execute sell trade
            trade, new_capital = self.trade_executor.execute_sell_signal(
                signal=signal,
                market_data=market_data,
                capital=self.capital,
                trades=self.trades,
            )
            if trade:
                self.trades.append(trade)
                self.capital = new_capital
                self._notify_live(
                    signal.symbol,
                    "sell",
                    "filled",
                    Decimal(str(current_position_qty)),
                    trade.quantity,
                )

                # COMPLIANCE: Post-trade analysis - validate execution quality
                post_trade_analysis = self.compliance_engine.analyze_post_trade(
                    order_id=trade.trade_id,
                    symbol=trade.symbol,
                    side="sell",
                    quantity=trade.quantity,
                    execution_price=trade.exit_price or current_price,
                    signal_price=current_price,
                    signal_time=signal.timestamp,
                    submission_time=trade.exit_time if trade.exit_time else trade.entry_time,
                    execution_time=trade.exit_time if trade.exit_time else trade.entry_time,
                    nbbo=None,  # NBBO not available in backtesting
                )

                # Log post-trade analysis if SLO not met
                if not post_trade_analysis.slo_met:
                    logger.warning(
                        f"COMPLIANCE WARNING: {signal.symbol} SELL (strategy={strategy_name}): "
                        f"SLO not met - latency={post_trade_analysis.latency_ms:.2f}ms"
                    )

                # COMPLIANCE: Track daily P&L for kill switch monitoring (Hull Rule 13.1)
                # Calculate realized P&L from the trade
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
                        trade_time=market_data.timestamp,
                    )

                # Register trade result for learning engine
                self._register_sell_trade_for_learning(trade, signal, market_data)

    def _validate_trade_profitability(self, signal: Signal, price: Decimal) -> bool:
        """
        Validate if a trade can be profitable after commission costs.

        Args:
            signal: Trading signal
            price: Current price

        Returns:
            True if trade is profitable, False otherwise
        """
        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # Get commission (fixed or percentage-based)
        commission_pct = self._get_strategy_commission(signal, strategy_name)

        if commission_pct is not None:
            # Percentage-based commission - skip validation (will be calculated on trade value)
            return True

        # Fixed commission
        commission = self.config.commission_per_trade

        # If commission is $0, always allow trade
        if commission <= 0:
            return True

        # Calculate expected profit from take profit
        take_profit_pct = self.config.take_profit_percentage
        if take_profit_pct is None:
            # No take profit configured, allow trade
            return True

        # Calculate maximum position value
        max_position_value = self.capital * self.config.max_position_size

        # Position sizing validation
        round_trip_commission = commission * 2  # Buy + sell

        # Check if commission ratio exceeds 1% of position value
        commission_ratio = (
            round_trip_commission / max_position_value if max_position_value > 0 else Decimal("1")
        )

        if commission_ratio > Decimal("0.01"):
            # Commission is too high relative to position size
            min_position_value_needed = round_trip_commission / Decimal("0.01")

            if min_position_value_needed > self.capital:
                logger.warning(
                    f"TRADE REJECTED {signal.symbol} (strategy={strategy_name}): "
                    f"Commission ratio {commission_ratio:.2%} exceeds 1%. "
                    f"Round-trip commission: ${round_trip_commission:.2f}"
                )

                if self.diagnostic_logger:
                    self.diagnostic_logger.log_signal_rejected(
                        strategy_name,
                        signal.symbol,
                        "commission_ratio_exceeded",
                        f"Commission ratio {commission_ratio:.2%} > 1%",
                        signal.metadata if hasattr(signal, "metadata") else {},
                    )
                return False

        # Calculate expected profit at take profit
        # take_profit_pct is stored as decimal (0.12 = 12%), so use directly
        expected_profit = max_position_value * take_profit_pct

        # Validate: expected profit must be GREATER THAN 5x round-trip commission
        min_required_profit = round_trip_commission * 5

        if expected_profit <= min_required_profit:
            logger.warning(
                f"TRADE REJECTED {signal.symbol} (strategy={strategy_name}): "
                f"Expected profit ${expected_profit:.2f} is less than 5x commission ${min_required_profit:.2f}"
            )

            if self.diagnostic_logger:
                self.diagnostic_logger.log_signal_rejected(
                    strategy_name,
                    signal.symbol,
                    "profitability_check_failed",
                    f"Expected profit ${expected_profit:.2f} < 5x commission ${min_required_profit:.2f}",
                    signal.metadata if hasattr(signal, "metadata") else {},
                )
            return False

        logger.debug(
            f"Trade profitability check PASSED for {signal.symbol}: "
            f"Expected profit ${expected_profit:.2f} >= 5x commission ${min_required_profit:.2f}"
        )
        return True

    def _get_strategy_commission(self, signal: Signal, strategy_name: str) -> Decimal | None:
        """
        Get commission percentage for strategy.

        Priority: signal metadata > strategy config > None (use fixed amount from config)

        Returns:
            Commission percentage (as Decimal, e.g., 0.05 for 0.05%) or None to use fixed amount
        """
        # 1. Check signal metadata first
        if signal.metadata and "commission_per_trade_pct" in signal.metadata:
            with contextlib.suppress(ValueError, TypeError, InvalidOperation):
                return Decimal(str(signal.metadata["commission_per_trade_pct"]))

        # 2. Check strategy instance if available
        if self.strategy and hasattr(self.strategy, "commission_per_trade_pct"):
            return self.strategy.commission_per_trade_pct

        # 3. Return None to use fixed commission from config
        return None

    def _get_strategy_slippage(self, signal: Signal) -> Decimal | None:
        """
        Get slippage percentage for strategy.

        Priority: signal metadata > strategy config > global config > None

        Returns:
            Slippage percentage (as Decimal, e.g., 0.05 for 0.05%) or None to use config default
        """
        # 1. Check signal metadata first
        if signal.metadata and "slippage_per_trade_pct" in signal.metadata:
            with contextlib.suppress(ValueError, TypeError, InvalidOperation):
                return Decimal(str(signal.metadata["slippage_per_trade_pct"]))

        # 2. Check strategy instance if available
        if self.strategy and hasattr(self.strategy, "slippage_per_trade_pct"):
            return self.strategy.slippage_per_trade_pct

        # 3. Return None to use global config default
        return None

    def _apply_slippage(self, params: SlippageParams) -> Decimal:
        """
        Apply slippage to execution price.

        DELEGATES TO: app.backtesting.shared.slippage_utils.apply_slippage
        SINGLE SOURCE OF TRUTH: All slippage calculations go through shared utility.

        Args:
            params: SlippageParams containing all parameters

        Returns:
            Execution price with slippage applied
        """

        # Use shared utility for centralized slippage calculation
        return shared_apply_slippage(
            price=params.price,
            is_buy=params.is_buy,
            slippage_pct=params.slippage_pct,
            is_stop=params.is_stop,
            is_volatile=params.is_volatile,
        )

    def _build_trade_reason(self, signal: Signal, market_data: Quote) -> str:
        """
        Build human-readable reason for the trade from signal metadata.

        DELEGATES TO: app.backtesting.shared.trade_utils.build_trade_reason
        SINGLE SOURCE OF TRUTH: All trade reason building goes through shared utility.

        Args:
            signal: Trading signal
            market_data: Current market data

        Returns:
            Human-readable trade reason string
        """
        # Use shared utility for centralized trade reason building
        return shared_build_trade_reason(signal=signal, market_data=market_data)

    def _create_portfolio_from_state(self, current_price_func=None) -> Portfolio:
        """
        Create a Portfolio object from current backtesting state.

        Args:
            current_price_func: Optional function to get current price for a symbol

        Returns:
            Portfolio object
        """
        positions = []

        # Convert positions to Portfolio Position objects
        for symbol, quantity in self.position_manager.get_all_positions().items():
            if quantity == 0:
                continue

            # Get current price
            if current_price_func:
                market_price = current_price_func(symbol)
            elif symbol in self.last_known_prices:
                market_price = self.last_known_prices[symbol]
            else:
                # Fallback: try to get price from most recent trade
                market_price = None
                for trade in reversed(self.trades):
                    if trade.symbol == symbol:
                        market_price = trade.entry_price
                        break
                if not market_price:
                    logger.warning(f"No price available for {symbol} in portfolio creation")
                    market_price = Decimal("0")

            # Get average entry price from open trades
            avg_price = market_price
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

    def _close_position(
        self, symbol: str, timestamp: datetime, reason: str, current_price: Decimal | None = None
    ) -> None:
        """
        Close a position completely.

        Args:
            symbol: Trading symbol
            timestamp: Close timestamp
            reason: Reason for closing position
            current_price: Current price (optional)
        """
        current_position = self.position_manager.get_position(symbol)

        if current_position <= 0:
            return

        # Find the most recent buy trade for this symbol
        recent_trades = [t for t in self.trades if t.symbol == symbol and t.side == "buy"]

        if not recent_trades:
            return

        # Apply slippage to exit price FIRST: the capital update books the
        # slippage-adjusted proceeds, so the P&L must use the same price to
        # stay reconcilable with capital.
        from app.backtesting.base_engine import SlippageParams

        reference_price = current_price or recent_trades[-1].entry_price
        slippage_params = SlippageParams(
            price=reference_price,
            is_buy=False,
        )
        exit_price_with_slippage = self._apply_slippage(slippage_params)

        # Calculate P&L using PnL calculator (at the slippage-adjusted price)
        pnl_info = self.pnl_calculator.calculate_close_position_pnl(
            symbol=symbol,
            quantity=current_position,
            exit_price=exit_price_with_slippage,
            trades=self.trades,
        )

        # Create summary sell trade
        trade_id = str(uuid4())
        trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            side="sell",
            quantity=current_position,
            entry_price=pnl_info["avg_entry_price"],
            exit_price=reference_price,
            entry_time=pnl_info["entry_time"] or timestamp,
            exit_time=timestamp,
            status=TradeStatus.CLOSED,
            pnl=pnl_info["pnl"],
            pnl_percentage=pnl_info["pnl_percentage"],
            commission=pnl_info["total_commission"],
            slippage=abs(current_position * (exit_price_with_slippage - reference_price)),
            all_in_cost=pnl_info["total_commission"]
            + abs(current_position * (exit_price_with_slippage - reference_price)),
            reason=reason,  # FIX: Set the reason for the trade
        )

        # Close all matching buy trades
        for buy_trade in recent_trades:
            if buy_trade.status == TradeStatus.OPEN:
                buy_trade.status = TradeStatus.CLOSED
                buy_trade.exit_price = current_price or recent_trades[-1].entry_price
                buy_trade.exit_time = timestamp

        # Add trade to results
        self.trades.append(trade)

        # Update capital and position
        self.capital += current_position * exit_price_with_slippage - pnl_info["total_commission"]
        self.position_manager.close_position(symbol)
        # D05: stop/TP close (or forced end-of-run close) — the live
        # strategy must learn the position is GONE before its next decision.
        self._notify_live(symbol, "sell", "closed", current_position, current_position)

    def _close_all_positions(
        self, final_market_data: Quote, price_map: dict[str, Decimal] | None = None
    ) -> None:
        """
        Close all remaining positions at the end of backtest.

        Args:
            final_market_data: Last market data point (for timestamp)
            price_map: Optional dictionary mapping symbol -> price for accurate closing prices
        """
        for symbol in self.position_manager.get_symbols_with_positions():
            closing_price = None
            if price_map and symbol in price_map:
                closing_price = price_map[symbol]
                logger.debug(f"Using price_map price for {symbol}: {closing_price:.2f}")
            else:
                # Fallback: try to get price from most recent trade
                recent_trades_for_symbol = [t for t in reversed(self.trades) if t.symbol == symbol]
                if recent_trades_for_symbol:
                    closing_price = recent_trades_for_symbol[0].entry_price
                    logger.warning(
                        f"No price_map entry for {symbol}, using last trade price: {closing_price:.2f}"
                    )
                else:
                    closing_price = get_price(final_market_data)
                    logger.warning(
                        f"Using final_market_data price for {symbol}: {closing_price:.2f}"
                    )

            self._close_position(
                symbol, final_market_data.timestamp, "end_of_backtest", closing_price
            )

    def _build_price_map(self, market_data: list[Quote]) -> dict[str, Decimal]:
        """
        Build a price map from market data for accurate position closing.

        Args:
            market_data: List of market data points

        Returns:
            Dictionary mapping symbol to most recent price
        """
        price_map = {}
        for md in reversed(market_data):  # Start from most recent
            if md.symbol not in price_map:
                price_map[md.symbol] = get_price(md)
        return price_map

    def _register_buy_trade_for_learning(
        self, trade: Trade, signal: Signal, market_data: Quote
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

            if hasattr(self.strategy, "add_trade_result"):
                self.strategy.add_trade_result(
                    {
                        "pnl": 0,
                        "entry_time": trade.entry_time,
                        "symbol": signal.symbol,
                    }
                )

    def _register_sell_trade_for_learning(
        self, trade: Trade, signal: Signal, market_data: Quote
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

            if hasattr(self.strategy, "add_trade_result"):
                self.strategy.add_trade_result(
                    {
                        "pnl": float(trade.pnl) if trade.pnl else 0,
                        "entry_time": trade.entry_time,
                        "exit_time": trade.exit_time,
                        "symbol": signal.symbol,
                    }
                )

    def _update_reallocation_engine(
        self, performance: PerformanceMetrics, total_return: Decimal, market_data: list[Quote]
    ) -> None:
        """Update reallocation engine with strategy performance after backtest."""
        if not (self.reallocation_engine and performance):
            return

        winning_trades = sum(1 for t in self.trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl and t.pnl <= 0)
        total_trades = len(self.trades)

        self.reallocation_engine.update_strategy_performance(
            strategy_name=self.strategy_name,
            timestamp=market_data[-1].timestamp,
            pnl=Decimal(str(performance.total_pnl)),
            returns=Decimal(str(total_return)),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )
        logger.info(
            f"Updated performance tracker for {self.strategy_name}: "
            f"PnL={performance.total_pnl:.2f}, "
            f"Return={total_return:.2f}%, "
            f"Trades={total_trades} (W:{winning_trades}, L:{losing_trades})"
        )


# Keep backward compatibility alias
SimpleBacktester = BacktestEngine
