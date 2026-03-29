"""
Multi-Strategy Backtest Engine.

This engine provides multi-strategy backtesting with:
- Capital allocation per strategy
- StrategyStockAllocator for intelligent stock assignment
- Dynamic capital reallocation
- BacktestingCompliance integration (R5, R6, R7, DATA-001)

This is a refactored version of app/backtesting/multi_strategy_engine.py that
extends BaseBacktestEngine for consistency across the codebase.

SINGLE SOURCE OF TRUTH: All defaults from CentralizedConfig.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

from app.backtesting.backtesting_compliance import (
    BacktestingComplianceResult,
    create_backtesting_compliance,
)
from app.backtesting.base_engine import BaseBacktestEngine, EngineType
from app.backtesting.models import BacktestConfig, BacktestResult, PerformanceMetrics
from app.backtesting.signal_diagnostic_logger import SignalDiagnosticLogger
from app.services.dynamic_capital_reallocation import DynamicCapitalReallocationEngine
from app.services.portfolio_config_manager import (
    PortfolioConfigManager,
    get_portfolio_config_manager,
)
from app.services.strategy_stock_allocator import StrategyStockAllocator

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig
from app.shared.config.params.strategy_config import StockAllocationSettings

if TYPE_CHECKING:
    from app.domain.models.market_data import Quote
    from app.domain.strategies.base import BaseStrategy
    from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

logger = logging.getLogger(__name__)


# Configuration for multi-strategy engine
class MultiStrategyConfig(BacktestConfig):
    """Configuration for multi-strategy backtesting."""

    strategies: ClassVar[dict[str, Decimal]] = {}  # strategy_name -> weight
    enable_dynamic_reallocation: bool = True
    reallocation_frequency_days: int = 30
    early_abort_loss_pct: Decimal = Decimal("0.20")


class MultiStrategyResult:
    """Result from multi-strategy backtest."""

    def __init__(
        self,
        per_strategy: dict[str, dict],
        combined: dict,
        allocation: dict,
        results_by_strategy: dict[str, BacktestResult],
        stock_allocation: dict | None = None,
    ):
        self.per_strategy = per_strategy
        self.combined = combined
        self.allocation = allocation
        self.results_by_strategy = results_by_strategy
        self.stock_allocation = stock_allocation


class MultiStrategyBacktestEngine(BaseBacktestEngine[MultiStrategyConfig, MultiStrategyResult]):
    """
    Multi-strategy backtesting engine with capital allocation.

    TASK-PA-1, PA-2: Implements multi-strategy backtesting with capital allocation.

    COMPLIANCE: Integrado con BacktestingCompliance para validar:
    - R5: Walk-Forward Analysis
    - R6: Overfitting Prevention
    - R7: Monte Carlo para riesgo
    - DATA-001: Purged Cross-Validation

    Features:
    - StrategyStockAllocator for intelligent stock assignment
    - Dynamic capital reallocation between strategies
    - Comprehensive compliance integration
    """

    def __init__(
        self,
        allocation_manager: MultiStrategyAllocationManager,
        strategies: dict[str, BaseStrategy],
        config_params: dict[str, Any],
        portfolio_config_manager: PortfolioConfigManager | None = None,
        enable_diagnostics: bool = True,
        early_abort_loss_pct: Decimal | None = None,
        enable_dynamic_reallocation: bool = True,
        reallocation_frequency_days: int = 30,
    ):
        """
        Initialize multi-strategy backtester.

        Args:
            allocation_manager: Capital allocation manager
            strategies: Dictionary of strategy instances {name: strategy}
            config_params: Common backtest parameters (commission, slippage, etc.)
            portfolio_config_manager: Optional portfolio config manager
            enable_diagnostics: Enable diagnostic logging
            early_abort_loss_pct: Abort if loss > X% in first 2 years
            enable_dynamic_reallocation: Enable dynamic capital reallocation
            reallocation_frequency_days: Days between reallocations
        """
        # Create config from parameters
        config = MultiStrategyConfig(
            strategy_name="multi_strategy",
            initial_capital=allocation_manager.total_capital,
            commission_per_trade=config_params.get("commission", Decimal("1.0")),
            slippage_percentage=config_params.get("slippage", Decimal("0.1")),
        )

        super().__init__(
            config=config,
            strategy_name="multi_strategy",
        )

        self.allocation_manager = allocation_manager
        self.strategies = strategies
        self.config_params = config_params
        self.total_capital = allocation_manager.total_capital
        self.portfolio_config = portfolio_config_manager or get_portfolio_config_manager()
        self.enable_diagnostics = enable_diagnostics
        self.early_abort_loss_pct = early_abort_loss_pct or Decimal("0.20")

        # Initialize diagnostic logger
        self.diagnostic_logger = SignalDiagnosticLogger() if enable_diagnostics else None

        # Initialize Strategy Stock Allocator
        allocation_config = StockAllocationSettings()
        self.stock_allocator = StrategyStockAllocator(config=allocation_config)
        self.allocation_result = None

        # Initialize Dynamic Capital Reallocation Engine
        self.enable_dynamic_reallocation = enable_dynamic_reallocation
        if enable_dynamic_reallocation:
            self.reallocation_engine = DynamicCapitalReallocationEngine(
                rebalance_frequency_days=reallocation_frequency_days,
                rolling_window_days=30,
            )
            logger.info(
                f"Dynamic Capital Reallocation Engine enabled (frequency: {reallocation_frequency_days} days)"
            )
        else:
            self.reallocation_engine = None

        # COMPLIANCE: Initialize BacktestingCompliance
        self.backtesting_compliance = create_backtesting_compliance()
        self.compliance_results: list[BacktestingComplianceResult] = []

        logger.info("MultiStrategyBacktestEngine: BacktestingCompliance initialized")

    # =========================================================================
    # IMPLEMENTATION OF ABSTRACT METHODS
    # =========================================================================

    def get_engine_type(self) -> EngineType:
        """Return the engine type identifier."""
        return EngineType.MULTI_STRATEGY

    def run_backtest(
        self,
        market_data: list[Quote] | list[Any],
        signals: list[Any] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        **kwargs,
    ) -> MultiStrategyResult:
        """
        Run backtest across multiple strategies with allocated capital.

        Uses StrategyStockAllocator to intelligently select and assign stocks
        to strategies based on statistical classification.

        Args:
            market_data: Historical market data (quotes)
            signals: Ignored for multi-strategy (generated per strategy)
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            MultiStrategyResult with consolidated results per strategy
        """
        quotes = market_data  # Alias for clarity

        logger.info(
            f"Starting multi-strategy backtest with ${self.total_capital:,.2f} total capital"
        )

        # STEP 1: Convert quotes to historical_data format for allocator
        historical_data = self._convert_quotes_to_dataframe_dict(quotes)

        # STEP 2: Use StrategyStockAllocator to select and assign stocks
        logger.info("Using StrategyStockAllocator to select and assign stocks to strategies")

        # Get strategy-level capital allocations
        capital_allocations = self.allocation_manager.allocate_capital()
        strategy_allocations_dict = {
            strategy: float(capital) for strategy, capital in capital_allocations.items()
        }

        # Run allocation
        use_allocator = self._run_allocation(historical_data, strategy_allocations_dict)

        # STEP 3: Run backtest for each strategy
        results_by_strategy: dict[str, BacktestResult] = {}
        signals_by_strategy: dict[str, list] = {}

        for strategy_name, allocated_capital in capital_allocations.items():
            strategy = self.strategies.get(strategy_name)

            if not strategy:
                logger.warning(f"Strategy '{strategy_name}' not found in strategies dict")
                continue

            logger.info(f"Backtesting {strategy_name} with ${allocated_capital:,.2f} capital")

            # Filter quotes based on allocator result or fallback
            if use_allocator:
                filtered_quotes = self._filter_quotes_by_allocator(quotes, strategy_name)
            else:
                filtered_quotes = self._filter_quotes_by_strategy(quotes, strategy_name)

            # Generate signals for this strategy
            signals = self._generate_signals_for_strategy(strategy, strategy_name, filtered_quotes)
            signals_by_strategy[strategy_name] = signals

            if not signals:
                logger.warning(f"No signals generated for {strategy_name}")
                results_by_strategy[strategy_name] = self._create_empty_result(
                    strategy_name, allocated_capital, start_date, end_date
                )
                continue

            # Create config with allocated capital
            bt_config = self._bt_config
            config = BacktestConfig(
                strategy_name=f"{strategy_name}_backtest",
                initial_capital=allocated_capital,
                commission_per_trade=self.config_params.get("commission", bt_config.min_commission),
                slippage_percentage=self.config_params.get(
                    "slippage", bt_config.base_slippage_bps / Decimal("100")
                ),
                stop_loss_percentage=self.config_params.get(
                    "stop_loss", bt_config.default_stop_loss_pct * Decimal("100")
                ),
                take_profit_percentage=self.config_params.get(
                    "take_profit", bt_config.default_take_profit_pct * Decimal("100")
                ),
                max_position_size=self.config_params.get(
                    "max_position_size", bt_config.default_max_position_size
                ),
            )

            # Run backtest using StandardBacktestEngine
            from app.backtesting.engines.standard_engine import StandardBacktestEngine

            backtester = StandardBacktestEngine(
                config,
                diagnostic_logger=self.diagnostic_logger,
                strategy=strategy,
                enable_risk_envelope=True,
                strategy_name=strategy_name,
                total_portfolio_capital=self.total_capital,
                reallocation_engine=self.reallocation_engine,
            )
            result = backtester.run_backtest(filtered_quotes, signals, start_date, end_date)
            results_by_strategy[strategy_name] = result

            # Early-abort check
            if self.early_abort_loss_pct:
                self._check_early_abort(strategy_name, result, start_date, end_date)

        # Save diagnostic report if enabled
        if self.diagnostic_logger:
            self.diagnostic_logger.save_diagnostic_report()
            self.diagnostic_logger.print_summary()

        # Consolidate results
        consolidated = self._consolidate_results(results_by_strategy, capital_allocations)

        # Add allocation information
        if self.allocation_result:
            consolidated["stock_allocation"] = {
                "validation_passed": self.allocation_result.validation_passed,
                "allocated_stocks": len(self.allocation_result.allocations),
                "residual_capital": float(self.allocation_result.residual_capital),
                "validation_errors": self.allocation_result.validation_errors,
                "allocation_method": "StrategyStockAllocator",
                "decision_logs": (
                    self.allocation_result.decision_logs[-10:]
                    if self.allocation_result.decision_logs
                    else []
                ),
            }

        logger.info(
            f"Multi-strategy backtest completed: "
            f"{consolidated['combined']['total_initial_capital']:,.2f} initial -> "
            f"{consolidated['combined']['total_final_capital']:,.2f} final "
            f"({consolidated['combined']['total_return']:.2f}% return)"
        )

        return MultiStrategyResult(
            per_strategy=consolidated["per_strategy"],
            combined=consolidated["combined"],
            allocation=consolidated["allocation"],
            results_by_strategy=results_by_strategy,
            stock_allocation=consolidated.get("stock_allocation"),
        )

    def _create_result(self, **kwargs) -> MultiStrategyResult:
        """Create MultiStrategyResult (delegated to run_backtest)."""
        return MultiStrategyResult(
            per_strategy=kwargs.get("per_strategy", {}),
            combined=kwargs.get("combined", {}),
            allocation=kwargs.get("allocation", {}),
            results_by_strategy=kwargs.get("results_by_strategy", {}),
            stock_allocation=kwargs.get("stock_allocation"),
        )

    # =========================================================================
    # MULTI-STRATEGY SPECIFIC METHODS
    # =========================================================================

    def _run_allocation(
        self,
        historical_data: dict[str, pd.DataFrame],
        strategy_allocations_dict: dict[str, float],
    ) -> bool:
        """Run stock allocation and return True if successful."""
        try:
            logger.info("Executing StrategyStockAllocator.allocate()...")
            self.allocation_result = self.stock_allocator.allocate(
                historical_data=historical_data,
                total_capital=float(self.total_capital),
                strategy_allocations=strategy_allocations_dict,
            )
            logger.info(
                f"Allocation completed. Validation: {self.allocation_result.validation_passed}, "
                f"Allocations: {len(self.allocation_result.allocations)}"
            )
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"StrategyStockAllocator.allocate() failed: {e}", exc_info=True)
            self.allocation_result = None
            return False

        if not self.allocation_result or not self.allocation_result.validation_passed:
            logger.warning(
                f"Stock allocation {'validation failed' if self.allocation_result else 'failed'}: "
                f"{self.allocation_result.validation_errors if self.allocation_result else 'Exception'}. "
                "Falling back to portfolio config filtering."
            )
            return False

        logger.info(
            f"Stock allocation successful: {len(self.allocation_result.allocations)} stocks assigned, "
            f"${self.allocation_result.residual_capital:,.2f} residual capital"
        )
        return True

    def _generate_signals_for_strategy(
        self,
        strategy: BaseStrategy,
        strategy_name: str,
        filtered_quotes: list[Quote],
    ) -> list[Any]:
        """Generate signals for a strategy from filtered quotes."""
        signals = []
        errors_count = 0

        for quote in filtered_quotes:
            try:
                candidate_signals = strategy.generate_signals(quote)

                if candidate_signals:
                    for sig in candidate_signals:
                        signals.append(sig)

                        if self.diagnostic_logger:
                            self.diagnostic_logger.log_signal_candidate(
                                strategy_name,
                                quote.symbol,
                                (
                                    sig.signal_type.value
                                    if hasattr(sig.signal_type, "value")
                                    else str(sig.signal_type)
                                ),
                                sig.metadata if hasattr(sig, "metadata") else {},
                            )
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                errors_count += 1
                logger.error(f"{strategy_name} ERROR generating signals for {quote.symbol}: {e}")

        logger.info(
            f"{strategy_name}: Generated {len(signals)} signals from {len(filtered_quotes)} quotes, "
            f"errors={errors_count}"
        )

        return signals

    def _filter_quotes_by_strategy(self, quotes: list[Quote], strategy_name: str) -> list[Quote]:
        """Filter quotes by strategy sector configuration."""
        allowed_symbols = self.portfolio_config.get_strategy_symbols(strategy_name)

        if not allowed_symbols:
            return quotes

        return [q for q in quotes if q.symbol in allowed_symbols]

    def _filter_quotes_by_allocator(self, quotes: list[Quote], strategy_name: str) -> list[Quote]:
        """Filter quotes based on StrategyStockAllocator assignment results."""
        if not self.allocation_result:
            return self._filter_quotes_by_strategy(quotes, strategy_name)

        # Get symbols assigned to this strategy
        assigned_symbols = set()
        for ticker, metrics in self.allocation_result.allocations.items():
            if metrics.strategy == strategy_name:
                assigned_symbols.add(ticker)

        # Include pairs if this is pairs_trading
        if strategy_name == "pairs_trading":
            for pair in self.allocation_result.pairs:
                assigned_symbols.add(pair.ticker1)
                assigned_symbols.add(pair.ticker2)

        if not assigned_symbols:
            return self._filter_quotes_by_strategy(quotes, strategy_name)

        return [q for q in quotes if q.symbol in assigned_symbols]

    def _convert_quotes_to_dataframe_dict(self, quotes: list[Quote]) -> dict[str, pd.DataFrame]:
        """Convert List[Quote] to Dict[str, pd.DataFrame] for allocator."""
        quotes_by_symbol = defaultdict(list)
        for quote in quotes:
            quotes_by_symbol[quote.symbol].append(quote)

        historical_data = {}

        for symbol, symbol_quotes in quotes_by_symbol.items():
            symbol_quotes.sort(key=lambda q: q.timestamp)

            data = {
                "open": [float(q.open) for q in symbol_quotes],
                "high": [float(q.high) for q in symbol_quotes],
                "low": [float(q.low) for q in symbol_quotes],
                "close": [float(q.close) for q in symbol_quotes],
                "volume": [float(q.volume) for q in symbol_quotes],
            }

            timestamps = [q.timestamp for q in symbol_quotes]
            df = pd.DataFrame(data, index=pd.DatetimeIndex(timestamps))
            historical_data[symbol] = df

        return historical_data

    def _create_empty_result(
        self,
        strategy_name: str,
        initial_capital: Decimal,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BacktestResult:
        """Create empty backtest result when no signals generated."""
        total_days = (end_date - start_date).days if start_date and end_date else 1

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date or datetime.now(),
            end_date=end_date or datetime.now(),
            final_capital=initial_capital,
            total_return=Decimal("0"),
            trades=[],
            equity_curve=(
                [(start_date, initial_capital), (end_date, initial_capital)]
                if start_date and end_date
                else []
            ),
            performance=PerformanceMetrics(
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
                total_days=total_days,
                avg_trade_duration=Decimal("0"),
            ),
        )

    def _consolidate_results(
        self,
        results_by_strategy: dict[str, BacktestResult],
        capital_allocations: dict[str, Decimal],
    ) -> dict:
        """Consolidate results from multiple strategies."""
        total_initial = sum(capital_allocations.values())
        total_final = sum(r.final_capital for r in results_by_strategy.values())
        total_return = (
            ((total_final - total_initial) / total_initial * 100)
            if total_initial > 0
            else Decimal("0")
        )

        all_trades = []
        for _strategy_name, result in results_by_strategy.items():
            all_trades.extend(result.trades)

        weighted_sharpe = self._calculate_weighted_sharpe(results_by_strategy, capital_allocations)
        weighted_max_dd = self._calculate_weighted_max_dd(results_by_strategy, capital_allocations)

        per_strategy = {}
        for strategy_name, result in results_by_strategy.items():
            per_strategy[strategy_name] = {
                "initial_capital": float(capital_allocations[strategy_name]),
                "final_capital": float(result.final_capital),
                "total_trades": result.performance.total_trades if result.performance else 0,
                "win_rate": float(result.performance.win_rate) if result.performance else 0.0,
                "total_return": float(result.total_return),
                "sharpe_ratio": (
                    float(result.performance.sharpe_ratio)
                    if result.performance and result.performance.sharpe_ratio
                    else None
                ),
                "max_drawdown": (
                    float(result.performance.max_drawdown)
                    if result.performance and result.performance.max_drawdown
                    else 0
                ),
            }

        return {
            "per_strategy": per_strategy,
            "combined": {
                "total_initial_capital": float(total_initial),
                "total_final_capital": float(total_final),
                "total_return": float(total_return),
                "total_trades": sum(
                    r.performance.total_trades
                    for r in results_by_strategy.values()
                    if r.performance
                ),
                "weighted_sharpe": weighted_sharpe,
                "weighted_max_dd": weighted_max_dd,
                "all_trades": all_trades,
            },
            "allocation": {
                name: {
                    "capital": float(capital),
                    "weight": float(capital / total_initial) if total_initial > 0 else 0.0,
                }
                for name, capital in capital_allocations.items()
            },
            "results": results_by_strategy,
        }

    def _calculate_weighted_sharpe(
        self,
        results_by_strategy: dict[str, BacktestResult],
        capital_allocations: dict[str, Decimal],
    ) -> float:
        """Calculate weighted average Sharpe ratio."""
        total_sharpe = 0.0
        total_weight = 0.0

        for strategy_name, result in results_by_strategy.items():
            weight = float(capital_allocations[strategy_name])
            total_weight += weight
            if result.performance and result.performance.sharpe_ratio:
                total_sharpe += float(result.performance.sharpe_ratio) * weight

        return (total_sharpe / total_weight) if total_weight > 0 else 0.0

    def _calculate_weighted_max_dd(
        self,
        results_by_strategy: dict[str, BacktestResult],
        capital_allocations: dict[str, Decimal],
    ) -> float:
        """Calculate weighted average max drawdown."""
        total_dd = 0.0
        total_weight = 0.0

        for strategy_name, result in results_by_strategy.items():
            weight = float(capital_allocations[strategy_name])
            total_weight += weight
            if result.performance:
                max_dd = float(result.performance.max_drawdown or 0)
                total_dd += max_dd * weight

        return (total_dd / total_weight) if total_weight > 0 else 0.0

    def _check_early_abort(
        self,
        strategy_name: str,
        result: BacktestResult,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> None:
        """Check if backtest should be aborted due to early losses."""
        if not start_date or not end_date:
            return

        two_years_later = datetime(start_date.year + 2, start_date.month, start_date.day)
        if end_date > two_years_later:
            total_return = result.total_return
            if total_return < -float(self.early_abort_loss_pct) * 100:
                logger.warning(
                    f"{strategy_name}: Early abort - loss {total_return:.2f}% "
                    f"exceeds threshold {self.early_abort_loss_pct * 100:.0f}%"
                )

    def get_allocation_summary(self) -> dict[str, Any]:
        """Get current allocation summary."""
        capital_allocations = self.allocation_manager.allocate_capital()
        total = self.allocation_manager.total_capital

        summary = {}
        for name, capital in capital_allocations.items():
            weight = float(capital / total) if total > 0 else 0.0
            allocation = self.allocation_manager.strategy_allocations.get(name)

            summary[name] = {
                "allocated_capital": float(capital),
                "weight": weight,
                "target_weight": float(allocation.target_weight) if allocation else 0.0,
                "min_weight": float(allocation.min_weight) if allocation else 0.0,
                "max_weight": float(allocation.max_weight) if allocation else 0.0,
            }

        return summary


# Backward compatibility alias
MultiStrategyBacktester = MultiStrategyBacktestEngine
