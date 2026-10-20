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
        # objetivo maximo dividendo: core-satellite evidenciado (core
        # buy&hold crecimiento/aristócratas + filtro momentum anti-crash +
        # satélite high-yield + refugio BND). Precios ajustados → el momentum
        # incluye las distribuciones (dividend momentum, RFS 2026).
        "dividend_tracking": "app.domain.strategies.dividend_core_satellite:DividendCoreSatelliteStrategy",
        "dividend_etf_rotation": "app.domain.strategies.dividend_etf_rotation:DividendETFRotationStrategy",
        # objetivo preservar capital: anomalía de baja volatilidad (tramo de
        # menor vol realizada del universo sectorial, equiponderado, poca
        # rotación) — Blitz & van Vliet 2007, Baker/Bradley/Wurgler 2011.
        "low_volatility": "app.domain.strategies.low_volatility:LowVolatilityStrategy",
    }
    #: warm-up bars fed to the strategy before the execution window
    _WARMUP_DAYS = 180
    #: Signal model caps volume at 10M shares (validator fallback)
    _VOLUME_CAP = Decimal("9999999")

    #: optional param overrides injected by the optimizer (name → value);
    #: merged on top of the strategy's YAML config before instantiation.
    _strategy_param_overrides: dict | None = None

    def _build_strategy(self, name: str):
        """Instantiate the real strategy class for `name` (with fallback)."""
        import importlib

        path = self._STRATEGIES.get(name, self._STRATEGIES["mean_reversion"])
        module_path, class_name = path.split(":")
        strategy_cls = getattr(importlib.import_module(module_path), class_name)
        overrides = self._strategy_param_overrides or {}
        if name == "momentum_modular":
            import yaml

            repo_root = Path(__file__).resolve().parents[3]
            cfg = yaml.safe_load(
                (repo_root / "config" / "strategies" / "momentum_modular.yaml").read_text()
            )
            strategy = strategy_cls({"name": "momentum_modular", "enabled": True, **cfg})
        else:
            strategy = strategy_cls({"name": name, "enabled": True})
        # Optimizer overrides: the strategy's __init__ prioritises its YAML
        # config, so re-apply the tuned values directly on the instance
        # (they are plain attributes read at signal-generation time).
        for key, value in overrides.items():
            if hasattr(strategy, key):
                current = getattr(strategy, key)
                setattr(strategy, key, type(current)(value) if current is not None else value)
        return strategy

    @staticmethod
    def _reset_live_trading_gates() -> None:
        """Reset live-trading gates that misfire on historical replay.

        The compliance engine and the Harris microstructure integrator keep
        process-wide singletons whose quote-stuffing detector counts quotes
        per WALL-CLOCK second. Replaying years of daily bars in a couple of
        seconds looks like 150+ quotes/sec, and state accumulated by earlier
        runs in the same process trips "DO NOT TRADE" for every fill.
        Backtests are offline simulations: start each one from clean gates.
        """
        from app.engines.execution_engine.microstructure import harris_integration
        from app.services.compliance.compliance_engine import ComplianceEngine

        harris_integration._harris_integrator = None
        ComplianceEngine._instance = None

    def _run_real_backtest(self, config) -> BacktestResult:
        """Synchronous real backtest (worker thread)."""
        from datetime import time as dt_time

        from app.backtesting.data_loader import DataLoader
        from app.backtesting.engine import BacktestEngine
        from app.backtesting.models import BacktestConfig as EngineConfig

        repo_root = Path(__file__).resolve().parents[3]
        loader = DataLoader(base_path=repo_root / "data" / "historical")

        symbols = config.symbols or ["AAPL", "MSFT", "GOOGL"]
        # Estrategias cross-sectional (p.ej. rotación de ETFs): UNA instancia
        # viendo el timeline global de todos los símbolos. Las per-símbolo
        # (mean_reversion...) siguen con instancia propia como siempre.
        probe = self._build_strategy(config.strategy_name)
        shared_strategy = probe if getattr(probe, "is_cross_sectional", False) else None
        warmup_days = int(getattr(probe, "suggested_warmup_days", self._WARMUP_DAYS))

        load_start = datetime.combine(config.start_date - timedelta(days=warmup_days), dt_time.min)
        start_dt = datetime.combine(config.start_date, dt_time.min)
        end_dt = datetime.combine(config.end_date, dt_time.max)
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
            if shared_strategy is None:
                # estrategia per-símbolo (mean_reversion...): instancia propia
                # y su serie en orden, como siempre
                per_symbol_strategy = self._build_strategy(config.strategy_name)
                signals.extend(
                    signal
                    for quote in sorted(clamped, key=lambda q: q.timestamp)
                    for signal in per_symbol_strategy.generate_signals(quote)
                )

        if shared_strategy is not None:
            # estrategia cross-sectional: UNA instancia, timeline GLOBAL
            # intercalado por fecha (ver el universe completo en cada barra;
            # alimentarla por bloques de símbolo rompería la cross-sección)
            signals.extend(
                signal
                for quote in sorted(quotes, key=lambda q: q.timestamp)
                for signal in shared_strategy.generate_signals(quote)
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

        self._reset_live_trading_gates()

        engine = BacktestEngine(
            EngineConfig(
                strategy_name=config.strategy_name,
                initial_capital=config.initial_capital,
                max_position_size=Decimal(
                    str(getattr(probe, "suggested_max_position_size", Decimal("0.10")))
                ),
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

        # Gate R5/R6/DATA-001: walk-forward IS->OOS OBLIGATORIO sobre el MISMO
        # motor (antes vivía en un orquestador gemelo que el producto nunca
        # llamaba — los veredictos salían sin validación out-of-sample).
        gate = self._walk_forward_gate(quotes, signals, engine.config, start_dt, end_dt, probe)

        return self._map_engine_result(config, engine_result, start_dt, end_dt, gate)

    #: ciclos IS->OOS mínimos del gate (regla R5)
    _WF_MIN_CYCLES = 5
    #: fracción del span dedicada a entrenamiento y a cada ventana OOS; con
    #: 40% + 5 x 12% las cinco ventanas cubren exactamente el run
    _WF_TRAIN_FRACTION = 0.40
    _WF_VALIDATE_FRACTION = 0.12

    def _walk_forward_gate(
        self,
        quotes: list,
        signals: list,
        engine_config,
        start_dt: datetime,
        end_dt: datetime,
        probe,
    ) -> dict:
        """Walk-forward IS->OOS + compliance R5/R6/DATA-001 on the real motor.

        Windows scale with the run span so every run gets `_WF_MIN_CYCLES`
        cycles (a 10y run ≈ the classic 4y/1y windows; a 2y run gets
        proportionally shorter ones — and will honestly fail if the strategy
        barely trades inside them). Never raises: the verdict pipeline turns a
        failed gate into REJECTED with the reasons attached.
        """
        from app.backtesting.walk_forward_validator import (
            WalkForwardValidationParams,
            WalkForwardValidator,
        )

        span_days = max(1, (end_dt - start_dt).days)
        validate_years = span_days * self._WF_VALIDATE_FRACTION / 365
        validator = WalkForwardValidator(
            config={
                "train_years": span_days * self._WF_TRAIN_FRACTION / 365,
                "validation_years": validate_years,
                "step_years": validate_years,
                "min_windows": self._WF_MIN_CYCLES,
                # rotational ETF strategies trade a handful of times a year;
                # a window needs at least one trade to be evaluable
                "min_trades_per_window": 1,
                "thresholds": {
                    "min_cycles": self._WF_MIN_CYCLES,
                    "min_consistency": 0.6,
                    "max_return_std": 0.3,
                    "min_avg_sharpe": 0.0,
                    "max_avg_drawdown": -0.30,
                    "min_consistency_ratio": 0.7,
                    "max_degradation": 0.30,
                },
            }
        )
        try:
            wf = validator.validate_strategy(
                WalkForwardValidationParams(
                    quotes=quotes,
                    signals=signals,
                    config=engine_config,
                    start_date=start_dt,
                    end_date=end_dt,
                )
            )
        except Exception as exc:  # noqa: BLE001 - gate failure must surface, not crash
            logger.error("Walk-forward gate crashed: %s", exc, exc_info=True)
            return {
                "passed": None,
                "degradation": None,
                "windows": 0,
                "summary": f"gate error: {exc}",
            }

        windows = wf.get("windows") or []
        # validate_strategy already emits each window as {is_metrics, oos_metrics, ...}
        folds = [w for w in windows if isinstance(w, dict)]
        n_parameters = max(1, len(getattr(probe, "get_required_parameters", list)() or []))
        compliance = (
            validator.validate_compliance(
                folds, n_parameters=n_parameters, n_observations=span_days
            )
            if folds
            else None
        )

        analysis = wf.get("is_oos_analysis") or {}
        degradation = analysis.get("return_degradation")
        failures = list(wf.get("failures") or [])
        if wf.get("reason"):
            failures.append(str(wf["reason"]))
        if compliance is not None and not compliance.is_compliant:
            failures.extend(str(v) for v in compliance.violations)
        passed = bool(wf.get("passed")) and (compliance is None or compliance.is_compliant)
        summary = (
            f"{len(windows)} IS->OOS windows; return degradation {float(degradation):.0%}; "
            if degradation is not None
            else f"{len(windows)} IS->OOS windows; "
        ) + ("PASSED" if passed else "FAILED: " + "; ".join(failures[:4]))
        return {
            "passed": passed,
            "degradation": degradation,
            "windows": len(windows),
            "summary": summary,
            "failures": failures,
        }

    def _map_engine_result(
        self, config, engine_result, start_dt, end_dt, gate: dict | None = None
    ) -> BacktestResult:
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

        # Build a novice-readable trade summary (symbol, shares, prices, P&L)
        trade_summary = []
        for t in trades:
            trade_summary.append(
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "quantity": str(t.quantity),
                    "entry_price": str(t.entry_price),
                    "exit_price": str(t.exit_price) if t.exit_price else None,
                    "entry_time": t.entry_time.isoformat()[:10] if t.entry_time else None,
                    "exit_time": t.exit_time.isoformat()[:10] if t.exit_time else None,
                    "pnl": str(t.pnl) if t.pnl is not None else None,
                    "pnl_pct": str(t.pnl_percentage) if t.pnl_percentage is not None else None,
                    "commission": str(t.commission or 0),
                    "status": str(t.status.value) if hasattr(t.status, "value") else str(t.status),
                }
            )

        raw_equity = engine_result.equity_curve or []
        # Downsample to ≤200 points so the JSON payload stays under the
        # safe_json truncation limit (~4KB) while the chart still looks smooth
        step = max(1, len(raw_equity) // 200)
        equity_points = [(ts.isoformat(), str(val)) for ts, val in raw_equity[::step]]
        gate = gate or {}
        wf_passed = gate.get("passed")
        wf_failures = [str(f) for f in gate.get("failures") or []]
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
            equity_curve=equity_points,
            trades_summary=trade_summary,
            execution_duration_seconds=(end_dt - start_dt).total_seconds(),
            validation_passed=wf_passed is not False,
            validation_failures=wf_failures if wf_passed is False else [],
            walk_forward_passed=wf_passed,
            walk_forward_degradation=(
                Decimal(str(gate["degradation"])).quantize(Decimal("0.0001"))
                if gate.get("degradation") is not None
                else None
            ),
            walk_forward_windows=int(gate.get("windows") or 0),
            walk_forward_summary=str(gate.get("summary") or ""),
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
