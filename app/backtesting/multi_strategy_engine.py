"""
Multi-Strategy Backtesting Engine.

TASK-PA-1, PA-2: Implements multi-strategy backtesting with capital allocation.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.signal_diagnostic_logger import SignalDiagnosticLogger
from app.models.market_data import Quote
from app.services.multi_strategy_allocation import MultiStrategyAllocationManager
from app.services.portfolio_config_manager import (
    PortfolioConfigManager,
    get_portfolio_config_manager,
)
from app.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class MultiStrategyBacktester:
    """
    Multi-strategy backtesting engine with capital allocation.
    
    Manages multiple strategy backtests simultaneously with allocated capital per strategy.
    """

    def __init__(
        self,
        allocation_manager: MultiStrategyAllocationManager,
        strategies: Dict[str, BaseStrategy],
        config_params: Dict,
        portfolio_config_manager: Optional[PortfolioConfigManager] = None,
        enable_diagnostics: bool = True,
        early_abort_loss_pct: Optional[Decimal] = None,  # Abort if loss > X% in first 2 years
    ):
        """
        Initialize multi-strategy backtester.
        
        Args:
            allocation_manager: Capital allocation manager
            strategies: Dictionary of strategy instances {name: strategy}
            config_params: Common backtest parameters (commission, slippage, etc.)
            portfolio_config_manager: Optional portfolio config manager for sector filtering
        """
        self.allocation_manager = allocation_manager
        self.strategies = strategies
        self.config_params = config_params
        self.total_capital = allocation_manager.total_capital
        self.portfolio_config = portfolio_config_manager or get_portfolio_config_manager()
        self.enable_diagnostics = enable_diagnostics
        self.early_abort_loss_pct = early_abort_loss_pct or Decimal("0.20")  # Default 20%
        
        # Initialize diagnostic logger if enabled
        self.diagnostic_logger = SignalDiagnosticLogger() if enable_diagnostics else None

    def run_multi_strategy_backtest(
        self, quotes: List[Quote], start_date: datetime, end_date: datetime
    ) -> Dict[str, Dict]:
        """
        Run backtest across multiple strategies with allocated capital.
        
        Args:
            quotes: Historical market data
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dictionary with consolidated results per strategy and combined metrics
        """
        logger.info(f"Starting multi-strategy backtest with ${self.total_capital:,.2f} total capital")

        # Allocate capital to each strategy
        capital_allocations = self.allocation_manager.allocate_capital()
        
        results_by_strategy: Dict[str, BacktestResult] = {}
        signals_by_strategy: Dict[str, List] = {}

        # Run backtest for each strategy with its allocated capital
        for strategy_name, allocated_capital in capital_allocations.items():
            strategy = self.strategies.get(strategy_name)
            
            if not strategy:
                logger.warning(f"Strategy '{strategy_name}' not found in strategies dict")
                continue

            logger.info(f"Backtesting {strategy_name} with ${allocated_capital:,.2f} capital")

            # Filter quotes by sector if configured
            filtered_quotes = self._filter_quotes_by_strategy(quotes, strategy_name)
            
            if len(filtered_quotes) < len(quotes):
                logger.info(
                    f"{strategy_name}: Filtered {len(quotes)} quotes to {len(filtered_quotes)} "
                    f"based on sector configuration"
                )

            # Generate signals for this strategy
            signals = []
            for quote in filtered_quotes:
                try:
                    # Double-check sector filtering at signal generation
                    if self.portfolio_config.should_filter_symbol(quote.symbol, strategy_name):
                        candidate_signals = strategy.generate_signals(quote)
                        
                        # Log signal candidates for diagnostics
                        if self.diagnostic_logger:
                            for sig in candidate_signals:
                                self.diagnostic_logger.log_signal_candidate(
                                    strategy_name,
                                    quote.symbol,
                                    sig.signal_type.value if hasattr(sig.signal_type, 'value') else str(sig.signal_type),
                                    sig.metadata if hasattr(sig, 'metadata') else {},
                                )
                        
                        signals.extend(candidate_signals)
                except Exception as e:
                    logger.debug(f"Signal error for {strategy_name}: {e}")

            signals_by_strategy[strategy_name] = signals

            if not signals:
                logger.warning(f"No signals generated for {strategy_name}")
                # Create empty result
                results_by_strategy[strategy_name] = self._create_empty_result(
                    strategy_name, allocated_capital, start_date, end_date
                )
                continue

            # Create config with allocated capital
            config = BacktestConfig(
                strategy_name=f"{strategy_name}_backtest",
                initial_capital=allocated_capital,
                commission_per_trade=self.config_params.get("commission", Decimal("1.0")),
                slippage_percentage=self.config_params.get("slippage", Decimal("0.05")),
                stop_loss_percentage=self.config_params.get("stop_loss"),
                take_profit_percentage=self.config_params.get("take_profit"),
                max_position_size=self.config_params.get("max_position_size", Decimal("0.1")),
            )

            # Run backtest with allocated capital
            backtester = SimpleBacktester(config)
            result = backtester.run_backtest(quotes, signals, start_date, end_date)
            results_by_strategy[strategy_name] = result
            
            # Early-abort check: if loss > threshold in first 2 years
            if self.early_abort_loss_pct:
                two_years_later = datetime(
                    start_date.year + 2, start_date.month, start_date.day
                )
                if end_date > two_years_later:
                    # Check performance in first 2 years
                    # This is simplified - in production would need intermediate equity curve
                    total_return = result.total_return
                    if total_return < -float(self.early_abort_loss_pct) * 100:
                        logger.warning(
                            f"{strategy_name}: Early abort - loss {total_return:.2f}% "
                            f"exceeds threshold {self.early_abort_loss_pct * 100:.0f}%"
                        )
        
        # Save diagnostic report if enabled
        if self.diagnostic_logger:
            self.diagnostic_logger.save_diagnostic_report()
            self.diagnostic_logger.print_summary()

        # Consolidate results
        consolidated = self._consolidate_results(results_by_strategy, capital_allocations)
        
        logger.info(
            f"Multi-strategy backtest completed: "
            f"{consolidated['combined']['total_initial_capital']:,.2f} initial -> "
            f"{consolidated['combined']['total_final_capital']:,.2f} final "
            f"({consolidated['combined']['total_return']:.2f}% return)"
        )

        return consolidated

    def _create_empty_result(
        self,
        strategy_name: str,
        initial_capital: Decimal,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Create empty backtest result when no signals generated."""
        from app.backtesting.models import PerformanceMetrics

        total_days = (end_date - start_date).days or 1
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            final_capital=initial_capital,
            total_return=Decimal("0"),
            trades=[],
            equity_curve=[(start_date, initial_capital), (end_date, initial_capital)],
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
        results_by_strategy: Dict[str, BacktestResult],
        capital_allocations: Dict[str, Decimal],
    ) -> Dict:
        """
        Consolidate results from multiple strategies.
        
        Returns:
            Dictionary with:
            - per_strategy: individual results
            - combined: aggregated metrics
            - allocation: capital allocation details
        """
        # Calculate combined metrics
        total_initial = sum(capital_allocations.values())
        total_final = sum(r.final_capital for r in results_by_strategy.values())
        total_return = ((total_final - total_initial) / total_initial * 100) if total_initial > 0 else Decimal("0")

        # Aggregate trades (Trade objects don't have mutable metadata, so we just track them)
        all_trades = []
        for strategy_name, result in results_by_strategy.items():
            for trade in result.trades:
                # Just add the trade - metadata is not mutable in Trade model
                all_trades.append(trade)

        # Calculate weighted metrics
        weighted_sharpe = self._calculate_weighted_sharpe(results_by_strategy, capital_allocations)
        weighted_max_dd = self._calculate_weighted_max_dd(results_by_strategy, capital_allocations)

        # Per-strategy metrics
        per_strategy = {}
        for strategy_name, result in results_by_strategy.items():
            per_strategy[strategy_name] = {
                "initial_capital": float(capital_allocations[strategy_name]),
                "final_capital": float(result.final_capital),
                "total_trades": result.performance.total_trades,
                "win_rate": float(result.performance.win_rate),
                "total_return": float(result.total_return),
                "sharpe_ratio": float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else None,
                "max_drawdown": float(result.performance.max_drawdown) if result.performance.max_drawdown else 0,
            }

        return {
            "per_strategy": per_strategy,
            "combined": {
                "total_initial_capital": float(total_initial),
                "total_final_capital": float(total_final),
                "total_return": float(total_return),
                "total_trades": sum(r.performance.total_trades for r in results_by_strategy.values()),
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
            "results": results_by_strategy,  # Full BacktestResult objects
        }

    def _calculate_weighted_sharpe(
        self,
        results_by_strategy: Dict[str, BacktestResult],
        capital_allocations: Dict[str, Decimal],
    ) -> float:
        """Calculate weighted average Sharpe ratio."""
        total_sharpe = 0.0
        total_weight = 0.0

        for strategy_name, result in results_by_strategy.items():
            weight = float(capital_allocations[strategy_name])
            total_weight += weight
            if result.performance.sharpe_ratio:
                total_sharpe += float(result.performance.sharpe_ratio) * weight

        return (total_sharpe / total_weight) if total_weight > 0 else 0.0

    def _calculate_weighted_max_dd(
        self,
        results_by_strategy: Dict[str, BacktestResult],
        capital_allocations: Dict[str, Decimal],
    ) -> float:
        """Calculate weighted average max drawdown."""
        total_dd = 0.0
        total_weight = 0.0

        for strategy_name, result in results_by_strategy.items():
            weight = float(capital_allocations[strategy_name])
            total_weight += weight
            max_dd = float(result.performance.max_drawdown or 0)
            total_dd += max_dd * weight

        return (total_dd / total_weight) if total_weight > 0 else 0.0

    def get_allocation_summary(self) -> Dict[str, Any]:
        """
        Get current allocation summary.
        
        Returns:
            Dictionary with allocation details
        """
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

    def _filter_quotes_by_strategy(
        self, quotes: List[Quote], strategy_name: str
    ) -> List[Quote]:
        """
        Filter quotes by strategy sector configuration.
        
        Args:
            quotes: List of quotes to filter
            strategy_name: Name of the strategy
            
        Returns:
            Filtered list of quotes
        """
        allowed_symbols = self.portfolio_config.get_strategy_symbols(strategy_name)
        
        # If no sectors configured, return all quotes
        if not allowed_symbols:
            return quotes
        
        # Filter quotes by allowed symbols
        filtered = [q for q in quotes if q.symbol in allowed_symbols]
        
        return filtered

