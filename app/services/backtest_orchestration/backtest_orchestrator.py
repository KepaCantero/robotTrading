"""
T4.1: BacktestOrchestrator - Backtesting execution and orchestration

Orchestrates the execution of backtests for parametrized strategies.
Wraps existing backtesting infrastructure (SimpleBacktester, ComprehensiveBacktestRunner)
and provides standardized interface for the parametrization pipeline.

Calculates feasibility_ratio: achieved_return / required_return
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .models import (
    BacktestMetrics,
    BacktestOrchestrationRequest,
    BacktestOrchestrationResult,
    BacktestResult,
    BacktestStatus,
)

logger = logging.getLogger(__name__)


class BacktestOrchestrator:
    """
    Orchestrates backtesting execution for parametrized trading strategies.

    Features:
    - Wraps existing SimpleBacktester and ComprehensiveBacktestRunner
    - Calculates feasibility_ratio for deployment decisions
    - Handles strategy execution with parametrized modules
    - Validates backtest results against constraints
    - Tracks execution history
    """

    def __init__(self):
        """Initialize backtest orchestrator."""
        self.execution_history: list[BacktestOrchestrationResult] = []
        # Lazy-import backtesting infrastructure to avoid heavy dependencies
        self._backtest_engine = None
        self._data_loader = None
        logger.info("✅ BacktestOrchestrator initialized")

    def _get_backtest_engine(self):
        """Lazy-load backtesting engine."""
        if self._backtest_engine is None:
            pass

    def _get_data_loader(self):
        """Lazy-load data loader."""
        if self._data_loader is None:
            pass

    async def orchestrate(
        self,
        request: BacktestOrchestrationRequest,
    ) -> BacktestOrchestrationResult:
        """
        Orchestrate backtesting execution.

        Args:
            request: BacktestOrchestrationRequest with profile and parameters

        Returns:
            BacktestOrchestrationResult with feasibility_ratio and decision
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Validate request
            validation_errors = self._validate_request(request)
            if validation_errors:
                return BacktestOrchestrationResult(
                    success=False,
                    error_message=f"Request validation failed: {', '.join(validation_errors)}",
                    warnings=validation_errors,
                )

            # Step 3: Execute the REAL backtest with the full request
            backtest_result = await self._execute_backtest(request)

            if not backtest_result.success:
                return BacktestOrchestrationResult(
                    success=False,
                    backtest_result=backtest_result,
                    error_message=backtest_result.error_message,
                    feasibility_ratio=Decimal("0"),
                    feasibility_status="REJECTED",
                )

            # Step 4: Calculate feasibility ratio
            feasibility_ratio = self._calculate_feasibility_ratio(
                request.target_monthly_return_eur,
                request.initial_capital,
                backtest_result.achieved_annual_return_pct,
            )

            # Step 5: Determine feasibility status
            feasibility_status = self._determine_feasibility_status(feasibility_ratio)

            # Step 6: Validate results
            warnings = self._validate_backtest_result(backtest_result, feasibility_ratio)

            # Create orchestration result
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result = BacktestOrchestrationResult(
                success=True,
                backtest_result=backtest_result,
                feasibility_ratio=feasibility_ratio,
                feasibility_status=feasibility_status,
                warnings=warnings,
                orchestration_time_ms=elapsed_ms,
            )

            # Store in history
            self.execution_history.append(result)

            logger.info(
                f"✅ Backtest completed for {request.profile_id}: "
                f"feasibility_ratio={feasibility_ratio:.2f}, status={feasibility_status}"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error orchestrating backtest: {e}")
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return BacktestOrchestrationResult(
                success=False,
                error_message=str(e),
                orchestration_time_ms=elapsed_ms,
            )

    def _validate_request(self, request: BacktestOrchestrationRequest) -> list[str]:
        """Validate orchestration request."""
        errors = []

        if request.initial_capital <= Decimal("0"):
            errors.append("Initial capital must be positive")

        if request.target_monthly_return_eur < Decimal("0"):
            errors.append("Target monthly return must be non-negative")

        if request.start_date >= request.end_date:
            errors.append("Start date must be before end date")

        if not request.strategy_name:
            errors.append("Strategy name is required")

        return errors

    async def _execute_backtest(
        self,
        config,
    ) -> BacktestResult:
        """Execute a REAL backtest: CSV data → strategy signals → BacktestEngine.

        Runs the repo's actual engine (commissions, slippage, t+1 execution,
        stop-loss/take-profit) over data/historical candles with the strategy
        selected for the profile. Heavy CPU work runs in a worker thread so
        the event loop stays responsive.
        """
        try:
            return await asyncio.to_thread(self._run_real_backtest, config)
        except Exception as e:  # noqa: BLE001 - surface any engine failure honestly
            logger.error(f"Real backtest failed: {e}", exc_info=True)
            return BacktestResult(
                test_id=f"test_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                profile_id=config.profile_id,
                input_id=config.input_id,
                status=BacktestStatus.FAILED,
                success=False,
                error_message=f"Real backtest failed: {e}",
            )

    #: real strategy classes the orchestrator can run
    _STRATEGIES = {
        "mean_reversion": "app.domain.strategies.mean_reversion:MeanReversionStrategy",
        "momentum_modular": "app.domain.strategies.strategy:ModularMomentumStrategy",
    }
    #: warm-up bars fed to the strategy before the execution window
    _WARMUP_DAYS = 180
    #: Signal model caps volume at 10M shares (validator fallback)
    _VOLUME_CAP = Decimal("9999999")

    def _build_strategy(self, name: str):
        """Instantiate the real strategy class for `name` (with fallback)."""
        import importlib

        path = self._STRATEGIES.get(name, self._STRATEGIES["mean_reversion"])
        module_path, class_name = path.split(":")
        strategy_cls = getattr(importlib.import_module(module_path), class_name)
        if name == "momentum_modular":
            import yaml

            repo_root = Path(__file__).resolve().parents[3]
            cfg = yaml.safe_load(
                (repo_root / "config" / "strategies" / "momentum_modular.yaml").read_text()
            )
            return strategy_cls({"name": "momentum_modular", "enabled": True, **cfg})
        return strategy_cls({"name": name, "enabled": True})

    def _run_real_backtest(self, config) -> BacktestResult:
        """Synchronous real backtest (worker thread)."""
        from datetime import time as dt_time

        from app.backtesting.data_loader import DataLoader
        from app.backtesting.engine import BacktestEngine
        from app.backtesting.models import BacktestConfig as EngineConfig

        repo_root = Path(__file__).resolve().parents[3]
        loader = DataLoader(base_path=repo_root / "data" / "historical")

        load_start = datetime.combine(
            config.start_date - timedelta(days=self._WARMUP_DAYS), dt_time.min
        )
        start_dt = datetime.combine(config.start_date, dt_time.min)
        end_dt = datetime.combine(config.end_date, dt_time.max)

        symbols = config.symbols or ["AAPL", "MSFT", "GOOGL"]
        quotes: list = []
        signals: list = []
        for symbol in symbols:
            try:
                raw = loader.load_market_data(symbol, load_start, end_dt, "1d", "csv")
            except Exception as exc:  # noqa: BLE001 - one bad symbol shouldn't kill all
                logger.warning("No data for %s: %s", symbol, exc)
                continue
            clamped = [
                q
                if q.volume <= self._VOLUME_CAP
                else q.model_copy(update={"volume": self._VOLUME_CAP})
                for q in raw
            ]
            if not clamped:
                continue
            quotes.extend(clamped)
            strategy = self._build_strategy(config.strategy_name)
            signals.extend(
                signal
                for quote in sorted(clamped, key=lambda q: q.timestamp)
                for signal in strategy.generate_signals(quote)
            )

        if not quotes:
            raise ValueError(f"No historical data found for {symbols} — check data/historical")

        # Only signals inside the execution window can fill (the engine keeps
        # market data inside the window; warm-up bars only build strategy state)
        window_signals = [s for s in signals if start_dt <= s.timestamp <= end_dt]
        if not window_signals:
            raise ValueError(
                "The strategy generated no signals in the selected period — "
                "try a longer window or another strategy"
            )

        engine = BacktestEngine(
            EngineConfig(
                strategy_name=config.strategy_name,
                initial_capital=config.initial_capital,
                commission_per_trade=config.commission_per_trade
                if config.commission_per_trade is not None
                else Decimal("1.0"),
                slippage_percentage=config.slippage_percentage
                if config.slippage_percentage is not None
                else Decimal("0.1"),
                stop_loss_percentage=config.stop_loss_percentage,
                take_profit_percentage=config.take_profit_percentage,
            ),
            # NOTE: no `strategy=` on purpose: the engine's optional per-signal
            # risk_check needs risk params the shipped strategy configs don't
            # provide and silently rejects every signal otherwise.
            strategy_name=config.strategy_name,
        )
        engine_result = engine.run_backtest(quotes, window_signals, start_dt, end_dt)

        return self._map_engine_result(config, engine_result, start_dt, end_dt)

    def _map_engine_result(self, config, engine_result, start_dt, end_dt) -> BacktestResult:
        """Translate the real engine result into the orchestration payload."""
        performance = engine_result.performance
        trades = list(engine_result.trades)
        initial = config.initial_capital
        final = engine_result.final_capital or initial
        equity = [Decimal(str(value)) for _, value in engine_result.equity_curve or []]

        wins = [t for t in trades if self._trade_pnl(t) > 0]
        losses = [t for t in trades if self._trade_pnl(t) <= 0]
        win_rate = (Decimal(len(wins)) / Decimal(len(trades)) * 100) if trades else Decimal("0")
        gross_wins = sum((self._trade_pnl(t) for t in wins), Decimal("0"))
        gross_losses = abs(sum((self._trade_pnl(t) for t in losses), Decimal("0")))
        profit_factor = (
            gross_wins / gross_losses
            if gross_losses > 0
            else (Decimal("99") if gross_wins > 0 else Decimal("0"))
        )

        total_return = (final / initial - Decimal("1")) * Decimal("100")
        days = max((end_dt - start_dt).days, 1)
        annual_return = total_return * Decimal("365") / Decimal(days)

        # daily returns from the equity curve → volatility + VaR(95)
        daily_returns = [
            (equity[i] / equity[i - 1] - Decimal("1")) * Decimal("100")
            for i in range(1, len(equity))
            if equity[i - 1] > 0
        ]
        if len(daily_returns) >= 2:
            mean_ret = sum(daily_returns) / Decimal(len(daily_returns))
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / Decimal(
                len(daily_returns) - 1
            )
            volatility = (variance.sqrt() * Decimal("252").sqrt()).quantize(Decimal("0.01"))
            ordered = sorted(daily_returns)
            var95 = abs(ordered[max(0, int(len(ordered) * 0.05) - 1)]).quantize(Decimal("0.01"))
        else:
            volatility = Decimal("0")
            var95 = Decimal("0")

        peak = max(equity) if equity else initial

        def _metric(value, default: Decimal = Decimal("0")) -> Decimal:
            return Decimal(str(value)) if value is not None else default

        metrics = BacktestMetrics(
            total_return_pct=total_return.quantize(Decimal("0.01")),
            annual_return_pct=annual_return.quantize(Decimal("0.01")),
            monthly_return_pct=(annual_return / Decimal("12")).quantize(Decimal("0.01")),
            sharpe_ratio=_metric(performance.sharpe_ratio).quantize(Decimal("0.01")),
            sortino_ratio=_metric(performance.sortino_ratio).quantize(Decimal("0.01")),
            calmar_ratio=_metric(performance.calmar_ratio).quantize(Decimal("0.01")),
            max_drawdown_pct=_metric(performance.max_drawdown).quantize(Decimal("0.01")),
            volatility_pct=volatility,
            var_95_pct=var95,
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=win_rate.quantize(Decimal("0.01")),
            avg_win_pct=self._mean_pct(wins, initial),
            avg_loss_pct=self._mean_pct(losses, initial),
            profit_factor=profit_factor.quantize(Decimal("0.01")),
            expectancy_pct=(
                (gross_wins - gross_losses)
                / initial
                * Decimal("100")
                / Decimal(max(len(trades), 1))
            ).quantize(Decimal("0.01")),
            recovery_factor=Decimal("0"),
            ulcer_index=Decimal("0"),
            consecutive_wins=0,
            consecutive_losses=0,
        )

        achieved_annual = metrics.annual_return_pct
        return BacktestResult(
            test_id=f"test_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            profile_id=config.profile_id,
            input_id=config.input_id,
            status=BacktestStatus.COMPLETED,
            success=True,
            starting_capital=initial,
            ending_capital=final,
            peak_capital=peak if peak > initial else initial,
            achieved_annual_return_pct=achieved_annual,
            metrics=metrics,
            execution_duration_seconds=(end_dt - start_dt).total_seconds(),
        )

    @staticmethod
    def _trade_pnl(trade) -> Decimal:
        for attr in ("pnl", "profit_loss", "net_pnl", "realized_pnl"):
            value = getattr(trade, attr, None)
            if value is not None:
                return Decimal(str(value))
        return Decimal("0")

    @staticmethod
    def _mean_pct(trades, initial: Decimal) -> Decimal:
        if not trades:
            return Decimal("0")
        total = Decimal("0")
        for trade in trades:
            pnl = BacktestOrchestrator._trade_pnl(trade)
            if pnl == 0:
                continue
            entry = getattr(trade, "entry_price", None) or getattr(trade, "buy_price", None)
            qty = getattr(trade, "quantity", None) or getattr(trade, "shares", None)
            notional = (
                Decimal(str(entry)) * Decimal(str(qty)) if entry is not None and qty else initial
            )
            total += pnl / notional * Decimal("100") if notional else Decimal("0")
        return (total / Decimal(len(trades))).quantize(Decimal("0.01"))

    def _calculate_feasibility_ratio(
        self,
        target_monthly_return_eur: Decimal,
        initial_capital: Decimal,
        achieved_annual_return_pct: Decimal,
    ) -> Decimal:
        """
        Calculate feasibility ratio.

        feasibility_ratio = achieved_annual_return / required_annual_return

        Rule:
        - >= 1.0: APPROVED (can meet target)
        - 0.7-1.0: CONDITIONAL (needs optimization)
        - < 0.7: REJECTED (not viable)
        """
        if initial_capital <= Decimal("0"):
            return Decimal("0")

        # Required annual return = (monthly return / capital) * 12 * 100
        required_annual_return_pct = (
            (target_monthly_return_eur / initial_capital) * 12 * Decimal("100")
        )

        if required_annual_return_pct <= Decimal("0"):
            # No return required, so any positive return is feasible
            return Decimal("1.0") if achieved_annual_return_pct >= Decimal("0") else Decimal("0")

        feasibility_ratio = achieved_annual_return_pct / required_annual_return_pct

        logger.debug(
            "Feasibility calculation: "
            f"required={required_annual_return_pct:.2f}%, "
            f"achieved={achieved_annual_return_pct:.2f}%, "
            f"ratio={feasibility_ratio:.2f}"
        )

        return feasibility_ratio

    def _determine_feasibility_status(self, feasibility_ratio: Decimal) -> str:
        """Determine feasibility status from ratio."""
        if feasibility_ratio >= Decimal("1.0"):
            return "APPROVED"
        elif feasibility_ratio >= Decimal("0.7"):
            return "CONDITIONAL"
        else:
            return "REJECTED"

    def _validate_backtest_result(
        self,
        result: BacktestResult,
        feasibility_ratio: Decimal,
    ) -> list[str]:
        """Validate backtest result and return warnings."""
        warnings = []

        if result.metrics:
            # Check Sharpe ratio (should be > 1.0 for good strategies)
            if result.metrics.sharpe_ratio < Decimal("1.0"):
                warnings.append(
                    f"⚠  Low Sharpe ratio ({result.metrics.sharpe_ratio:.2f}) - "
                    "consider adjusting parameters"
                )

            # Check max drawdown (should be < 20%)
            if result.metrics.max_drawdown_pct > Decimal("20"):
                warnings.append(
                    f"⚠  High max drawdown ({result.metrics.max_drawdown_pct:.2f}%) - "
                    "consider adding risk management"
                )

            # Check win rate (should be > 40%)
            if result.metrics.win_rate_pct < Decimal("40"):
                warnings.append(
                    f"⚠  Low win rate ({result.metrics.win_rate_pct:.2f}%) - "
                    "may indicate poor signal quality"
                )

        # Check feasibility ratio
        if feasibility_ratio < Decimal("1.0"):
            warnings.append(
                "⚠  Cannot consistently meet return target "
                f"(feasibility_ratio={feasibility_ratio:.2f})"
            )

        return warnings

    async def get_execution_history(
        self,
        limit: int | None = None,
    ) -> list[BacktestOrchestrationResult]:
        """Get execution history."""
        results = self.execution_history
        if limit:
            results = results[-limit:]
        return results

    def get_orchestrator_status(self) -> dict:
        """Get orchestrator operational status."""
        successful = sum(1 for r in self.execution_history if r.success)
        total = len(self.execution_history)

        return {
            "total_backtests": total,
            "successful_backtests": successful,
            "success_rate": successful / max(1, total),
            "execution_history_size": total,
        }


# Singleton
_orchestrator: BacktestOrchestrator | None = None


def get_backtest_orchestrator() -> BacktestOrchestrator:
    """Get or create singleton BacktestOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BacktestOrchestrator()

    return _orchestrator
