"""
T4.1: BacktestOrchestrator - Backtesting execution and orchestration

Orchestrates the execution of backtests for parametrized strategies on the
single BacktestEngine and provides the standardized interface for the
parametrization pipeline (walk-forward gate, benchmark, feasibility).

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

    def _build_strategy(self, name: str, symbols: list[str] | None = None):
        """Instantiate the real strategy class for `name` (with fallback).

        Cross-sectional strategies trade the RUN's universe: without it they
        fall back to their default symbols, which may not even be in the
        loaded data (e.g. Automatic universe + dividend layers → zero quotes
        tracked → "no signals" failure).
        """
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
        elif name == "dividend_tracking" and symbols:
            strategy = strategy_cls({"name": name, "enabled": True, "symbols": symbols})
        elif name == "low_volatility" and symbols:
            strategy = strategy_cls({"name": name, "enabled": True, "universe": symbols})
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
        """Start the run from clean live-trading gates (single source: the engine)."""
        from app.backtesting.engine import reset_live_trading_gates

        reset_live_trading_gates()

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
        probe = self._build_strategy(config.strategy_name, symbols)
        shared_strategy = probe if getattr(probe, "is_cross_sectional", False) else None
        if shared_strategy is not None:
            # warm-up builds indicator history only; the first position
            # decision happens INSIDE the execution window
            shared_strategy.signals_valid_from = datetime.combine(config.start_date, dt_time.min)
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
                per_symbol_strategy = self._build_strategy(config.strategy_name, symbols)
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

        # Gate R5/R6/DATA-001: estabilidad walk-forward OBLIGATORIA sobre el
        # MISMO motor (antes vivía en un orquestador gemelo que el producto
        # nunca llamaba — los veredictos salían sin validación out-of-sample).
        gate = self._walk_forward_gate(engine_result, engine.config, probe)
        benchmark = self._load_benchmark(config, loader, start_dt, end_dt)

        return self._map_engine_result(config, engine_result, start_dt, end_dt, gate, benchmark)

    #: same-index substitutes tried when the requested benchmark does not
    #: cover the window (local SPY history starts in 2016; IVV in 2000)
    _BENCHMARK_FALLBACKS: dict[str, tuple[str, ...]] = {"SPY": ("IVV",)}
    #: a benchmark "covers" the window if its first quote falls within this
    #: fraction of the span from the requested start
    _BENCHMARK_COVERAGE_TOLERANCE = 0.05

    def _load_benchmark(self, config, loader, start_dt, end_dt) -> dict | None:
        """Buy&hold reference over the same window (default SPY).

        Normalised to the run's initial capital so the curve can be overlaid
        on the equity chart; honest context for market conditions ("did the
        strategy beat just holding the market?"). Returns None when disabled
        or unavailable — the verdict never depends on it.

        A benchmark that only covers the tail of a long window would silently
        compare 20 years of strategy against 10 years of market, so same-index
        substitutes with deeper history are tried and the best-covering series
        wins.
        """
        symbol = (config.benchmark_symbol or "").strip().upper()
        if not symbol:
            return None
        span_days = max(1, (end_dt - start_dt).days)
        tolerance = timedelta(days=span_days * self._BENCHMARK_COVERAGE_TOLERANCE)
        best: tuple[str, list[tuple[datetime, float]]] | None = None
        for candidate in (symbol, *self._BENCHMARK_FALLBACKS.get(symbol, ())):
            try:
                raw = loader.load_market_data(candidate, start_dt, end_dt, "1d", "csv")
            except Exception as exc:  # noqa: BLE001 - benchmark is context, not a gate
                logger.warning("Benchmark %s unavailable: %s", candidate, exc)
                continue
            closes = sorted((q.timestamp, float(q.close if q.close else q.last)) for q in raw)
            if len(closes) < 2 or closes[0][1] <= 0:
                continue
            if best is None or closes[0][0] < best[1][0][0]:
                best = (candidate, closes)
            if closes[0][0] <= start_dt + tolerance:
                break
        if best is None:
            return None
        symbol, closes = best
        base = closes[0][1]
        curve = [(ts.isoformat(), value / base) for ts, value in closes]
        total = Decimal(str(curve[-1][1] - 1.0)) * Decimal("100")
        step = max(1, len(curve) // 200)
        return {
            "symbol": symbol,
            "return_pct": total.quantize(Decimal("0.01")),
            "curve": [(ts, f"{v:.6f}") for ts, v in curve[::step]],
        }

    #: ventanas secuenciales del gate de estabilidad (regla R5)
    _WF_MIN_CYCLES = 5
    #: volatilidad anual mínima (mismo floor que PerformanceMetricsCalculator)
    _WF_VOL_FLOOR = 0.15
    _WF_TRADING_DAYS = 252

    def _walk_forward_gate(self, engine_result, engine_config, probe) -> dict:
        """R5/R6/DATA-001 stability gate on the run's own equity curve.

        The strategy parameters are fixed a priori (no re-optimization inside
        the gate), so the honest walk-forward question is: is the FULL run —
        positions carried, exactly as it would trade live — consistently
        profitable across time, or did all its performance concentrate in one
        lucky stretch? We slice the run's equity curve into 5 sequential
        windows and demand consistent profitability (R5), a sane
        parameters/observations ratio (R6) and note that purged CV
        (DATA-001) does not apply without in-gate re-optimization.

        Re-running the strategy in isolated windows (the classic IS->OOS
        layout) would measure signal incidence, not the strategy: a slow
        rotational strategy with no rebalance inside a window would show a
        flat 0% window while fully invested in reality.

        Never raises: a failed gate flows into the verdict as REJECTED.
        """
        import math

        by_ts: dict = {}
        for ts, value in engine_result.equity_curve or []:
            by_ts[ts] = float(value)
        series = sorted(by_ts.items())
        if len(series) < 50:
            return {
                "passed": None,
                "degradation": None,
                "windows": 0,
                "summary": "walk-forward: insufficient equity history for stability windows",
                "failures": [],
            }

        n = self._WF_MIN_CYCLES
        size = len(series) // n
        rf = float(engine_config.risk_free_rate)
        stats = []
        for i in range(n):
            chunk = series[i * size : (i + 1) * size if i < n - 1 else len(series)]
            values = [v for _ts, v in chunk]
            days = max(1, len(values))
            years = days / self._WF_TRADING_DAYS
            ret = values[-1] / values[0] - 1.0
            ann = (1.0 + ret) ** (1.0 / years) - 1.0 if years > 0 and values[0] > 0 else 0.0
            rets = [(b / a - 1.0) for a, b in zip(values[:-1], values[1:], strict=True) if a > 0]
            mean = sum(rets) / len(rets) if rets else 0.0
            var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
            vol = max(math.sqrt(var) * math.sqrt(self._WF_TRADING_DAYS), self._WF_VOL_FLOOR)
            sharpe = (mean * self._WF_TRADING_DAYS - rf) / vol
            peak, mdd = values[0], 0.0
            for v in values:
                peak = max(peak, v)
                mdd = min(mdd, v / peak - 1.0)
            stats.append({"ret": ret, "ann": ann, "sharpe": sharpe, "mdd": mdd})

        profitable = sum(1 for w in stats if w["ret"] > 0)
        consistency = profitable / n
        worst = min(stats, key=lambda w: w["ann"])
        mean_sharpe = sum(w["sharpe"] for w in stats) / n
        # "degradation" here = depth of the worst window (time-instability);
        # there is no IS/OOS refit, so classic degradation is not definable.
        degradation = max(0.0, -worst["ret"])

        failures = []
        if consistency < 0.6:
            failures.append(
                f"R5 consistency {consistency:.0%} ({profitable}/{n} profitable windows) < 60%"
            )
        if worst["mdd"] < -0.30:
            failures.append(f"R5 worst-window drawdown {worst['mdd']:.0%} < -30%")
        if mean_sharpe <= 0:
            failures.append(f"R5 mean window Sharpe {mean_sharpe:.2f} <= 0")
        n_parameters = max(1, len(getattr(probe, "get_required_parameters", list)() or []))
        ratio = n_parameters / len(series)
        if ratio > 1 / 30:
            failures.append(
                f"R6 parameters/observations {n_parameters}/{len(series)} = {ratio:.4f} > 1/30"
            )

        passed = not failures
        window_txt = ", ".join(f"{w['ret']:+.0%}" for w in stats)
        summary = (
            f"{n} sequential windows [{window_txt}]; worst {worst['ret']:+.0%}; "
            f"mean Sharpe {mean_sharpe:.2f}; R6 {n_parameters}:{len(series)}; "
            "DATA-001 n/a (fixed params, no in-gate refit); "
            + ("PASSED" if passed else "FAILED: " + "; ".join(failures[:4]))
        )
        return {
            "passed": passed,
            "degradation": degradation,
            "windows": n,
            "summary": summary,
            "failures": failures,
        }

    def _map_engine_result(
        self,
        config,
        engine_result,
        start_dt,
        end_dt,
        gate: dict | None = None,
        benchmark: dict | None = None,
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
            benchmark_symbol=str((benchmark or {}).get("symbol") or ""),
            benchmark_return_pct=(benchmark or {}).get("return_pct"),
            excess_return_pct=(
                (metrics.total_return_pct - benchmark["return_pct"]).quantize(Decimal("0.01"))
                if benchmark and benchmark.get("return_pct") is not None
                else None
            ),
            benchmark_curve=list((benchmark or {}).get("curve") or []),
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
