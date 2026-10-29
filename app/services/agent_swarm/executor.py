"""Real executor for the CAPA 2 parametrization pipeline (T1.1 → T10.1).

Chains the ten actual components in order, treating each one as an "agent"
in the swarm. Around every agent the executor emits events carrying the
agent's input, output, duration and status, which feed the Mission Control
dashboard; it also awards XP and unlocks achievements tied to real pipeline
outcomes (feasibility gate, deploy decision, clean run).

The chaining (output of one component = input of the next) mirrors the
conventions of ``tests/unit/parametrization_framework/`` and
``tests/integration/parametrization_framework/test_capa2_end_to_end.py``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Awaitable, Callable

from app.services.agent_swarm.events import (
    ACHIEVEMENT_UNLOCKED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_STARTED,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_SKIPPED,
    STAGE_STARTED,
    AgentEvent,
    AgentEventBus,
)
from app.services.agent_swarm.serialization import safe_json
from app.services.agent_swarm.store import SwarmRunStore
from app.services.agent_swarm.universe_selector import DEFAULT_UNIVERSE, auto_universe

logger = logging.getLogger(__name__)

XP_PER_STAGE = 50
XP_COMPLETE_BONUS = 100

# RiskTolerance (bajo/medio/alto) → RiskProfile used by T2+
RISK_TOLERANCE_MAP = {
    "bajo": "conservative",
    "medio": "moderate",
    "alto": "aggressive",
}
# RiskProfile → the vocabulary T7 expects
RISK_PROFILE_PORTFOLIO_MAP = {
    "conservative": "conservative",
    "moderate": "balanced",
    "aggressive": "aggressive",
}

DEFAULT_MAX_DRAWDOWN_PCT = Decimal("20")


def _to_date(iso: str | None) -> date | None:
    """Parse an ISO date string, returning None on absence or bad format."""
    if not iso:
        return None
    try:
        return date.fromisoformat(str(iso)[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class AgentSpec:
    """Static identity of one agent (one CAPA 2 component)."""

    agent_id: str
    name: str
    emoji: str
    color: str
    description: str
    stage_slug: str  # slug used by /capa2 workflow-status for backward compat


AGENT_SPECS: list[AgentSpec] = [
    AgentSpec(
        "t11",
        "T1.1 Input Processor",
        "📥",
        "#4FC3F7",
        "Parses and validates raw user input into an InputProfile",
        "input_processing",
    ),
    AgentSpec(
        "t21",
        "T2.1 Profile Generator",
        "🧭",
        "#81C784",
        "Builds the InvestmentProfile: capital tier, modules, risk",
        "profile_generation",
    ),
    AgentSpec(
        "t31",
        "T3.1 Module Parametrizer",
        "⚙️",
        "#FFB74D",
        "Applies capital gating and assigns parameters per module",
        "module_parametrization",
    ),
    AgentSpec(
        "t41",
        "T4.1 Backtest Orchestrator",
        "📊",
        "#64B5F6",
        "Runs the backtest and computes the feasibility ratio",
        "backtest_execution",
    ),
    AgentSpec(
        "t51",
        "T5.1 Validation Engine",
        "🛡️",
        "#9575CD",
        "Validation gates: capital, costs, feasibility, learning…",
        "validation",
    ),
    AgentSpec(
        "t61",
        "T6.1 Strategy Recommender",
        "🎯",
        "#F06292",
        "Ranks strategies and recommends the best fit for the objective",
        "recommendation",
    ),
    AgentSpec(
        "t71",
        "T7.1 Portfolio Constructor",
        "🧺",
        "#4DB6AC",
        "Optimizes capital allocation across enabled modules",
        "portfolio_construction",
    ),
    AgentSpec(
        "t81",
        "T8.1 Risk Scaling",
        "⚖️",
        "#FFD54F",
        "Adjusts allocations for market regime, volatility and drawdown",
        "risk_scaling",
    ),
    AgentSpec(
        "t91",
        "T9.1 Reporting Generator",
        "📝",
        "#A1887F",
        "Produces the performance report: rating, strengths, weaknesses",
        "reporting",
    ),
    AgentSpec(
        "t101",
        "T10.1 Deploy Decision",
        "🚦",
        "#EF5350",
        "Synthesizes everything into APPROVED / CONDITIONAL / REJECTED",
        "deployment_decision",
    ),
]

SPEC_BY_AGENT: dict[str, AgentSpec] = {spec.agent_id: spec for spec in AGENT_SPECS}


def _strategy_overrides_from(modules: dict, strategy: str) -> dict:
    """D03: translate a T3.1 ModuleParameterSet into strategy overrides.

    ``module_specific`` keys (rebalance_days, satellite_top_k, ...) pass
    through verbatim; ``max_position_size`` maps verbatim to the strategy's
    ``weight_cap`` — BOTH are fractions 0-1 (module_parameters.yaml and
    trading_config define max_position_size as "Maximum position size (0-1)").
    A /100 here once poisoned every weight cap (0.10 → 0.001 → engine
    position floor 1% → ALL buys rejected → zero-trade REJECTED runs).
    Returns {} when T3.1 produced nothing usable — never invents params.
    """
    config = modules.get(strategy) if modules else None
    if config is None and modules:
        config = next(iter(modules.values()))
    if config is None:
        return {}
    overrides: dict = dict(getattr(config, "module_specific", None) or {})
    max_position_size = getattr(config, "max_position_size", None)
    if max_position_size is not None:
        try:
            overrides.setdefault("weight_cap", float(max_position_size))
        except (TypeError, ValueError):
            pass
    return overrides


@dataclass
class SwarmRunRequest:
    """Launch parameters for a swarm mission (matches /capa2 complete-workflow)."""

    capital_initial: Decimal
    objetivo_inversion: str
    risk_tolerance: str
    investment_horizon: int
    target_monthly_return_eur: Decimal | None = None
    constraints: dict | None = None
    market_regime: str = "sideways"  # bull / sideways / bear
    volatility_level: str = "normal"  # low / normal / high
    #: Automatic universe WITHOUT the curated goal screen: every corpus
    #: symbol that survives freshness/liquidity/history AND covers the
    #: window (395 names on 10y). Honest cost: a 25+ minute run.
    exhaustive_universe: bool = False
    backtest_start: str | None = None  # ISO date the test window opens
    backtest_end: str | None = None  # ISO date the test window closes
    symbols: list[str] | None = None  # universe to test over
    investor_age: int | None = None  # years, for suitability context
    tax_province: str | None = None  # Spanish province → ES tax rules
    #: Real engine strategy to run. Default None: the strategy is DERIVED
    #: from objetivo_inversion (D02 — the old mean_reversion default ran a
    #: mean-reversion backtest for dividend requests that omitted strategy).
    strategy: str | None = None
    commission_per_trade: Decimal | None = None  # engine cost model (€/trade)
    slippage_pct: Decimal | None = None  # engine cost model (%)
    stop_loss_pct: Decimal | None = None  # per-trade stop (%)
    take_profit_pct: Decimal | None = None  # per-trade take profit (%)

    def to_dict(self) -> dict:
        return {
            "capital_initial": str(self.capital_initial),
            "objetivo_inversion": self.objetivo_inversion,
            "risk_tolerance": self.risk_tolerance,
            "investment_horizon": self.investment_horizon,
            "target_monthly_return_eur": (
                str(self.target_monthly_return_eur) if self.target_monthly_return_eur else None
            ),
            "constraints": self.constraints,
            "market_regime": self.market_regime,
            "volatility_level": self.volatility_level,
            "backtest_start": self.backtest_start,
            "backtest_end": self.backtest_end,
            "symbols": self.symbols,
            "investor_age": self.investor_age,
            "tax_province": self.tax_province,
            "strategy": self.strategy,
            "commission_per_trade": (
                str(self.commission_per_trade) if self.commission_per_trade is not None else None
            ),
            "slippage_pct": (str(self.slippage_pct) if self.slippage_pct is not None else None),
            "stop_loss_pct": (str(self.stop_loss_pct) if self.stop_loss_pct is not None else None),
            "take_profit_pct": (
                str(self.take_profit_pct) if self.take_profit_pct is not None else None
            ),
        }


class StageFailure(Exception):
    """Raised when a component fails (exception or success=False)."""


@dataclass
class AgentState:
    """Live state of one agent inside a run."""

    status: str = "IDLE"  # IDLE / RUNNING / DONE / FAILED / SKIPPED
    input_payload: Any = None
    output_payload: Any = None
    duration_ms: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    xp: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "input": self.input_payload,
            "output": self.output_payload,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "warnings": self.warnings,
            "xp": self.xp,
        }


@dataclass
class RunState:
    """Full live state of one swarm run, polled by the dashboard."""

    run_id: str
    request: SwarmRunRequest
    status: str = "running"  # running / completed / failed
    agents: dict[str, AgentState] = field(
        default_factory=lambda: {spec.agent_id: AgentState() for spec in AGENT_SPECS}
    )
    events: list[AgentEvent] = field(default_factory=list)
    xp: int = 0
    achievements: list[dict] = field(default_factory=list)
    results: dict = field(default_factory=dict)  # JSON-ready, /capa2 compatible
    decision: dict | None = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str | None = None
    version: int = 0  # bumped on every mutation, lets the UI skip no-op refreshes

    def completed_count(self) -> int:
        return sum(1 for a in self.agents.values() if a.status == "DONE")

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "request": self.request.to_dict(),
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "xp": self.xp,
            "achievements": self.achievements,
            "results": self.results,
            "decision": self.decision,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class _Ctx:
    """Intermediate objects handed from one stage to the next."""

    request: SwarmRunRequest
    target_monthly: Decimal
    auto_symbols: list[str] | None = None  # corpus-derived universe (T4.1)
    auto_universe_summary: str = ""  # human-readable screen diagnostics
    input_profile: Any = None
    profile: Any = None  # InvestmentProfile (T2)
    param_result: Any = None  # ParameterizationResult (T3)
    param_set_id: str = ""
    backtest: Any = None  # BacktestOrchestrationResult (T4)
    validation: Any = None  # ValidationResult (T5)
    recommendation: Any = None  # recommendation (T6)
    portfolio: Any = None  # PortfolioAllocation (T7)
    risk_scaled: Any = None  # RiskAdjustedPortfolio (T8)
    report: Any = None  # PerformanceReport (T9)
    decision: Any = None  # DeploymentDecision (T10)


class Capa2PipelineExecutor:
    """Runs the real T1.1→T10.1 chain, emitting events and awarding XP."""

    def __init__(
        self,
        bus: AgentEventBus | None = None,
        store: SwarmRunStore | None = None,
    ) -> None:
        self.bus = bus or AgentEventBus()
        self.store = store
        self.runs: dict[str, RunState] = {}
        self.active_run_id: str | None = None

    # ── Public API ───────────────────────────────────────────────────────────

    def get_run(self, run_id: str) -> RunState | None:
        return self.runs.get(run_id)

    @property
    def latest_run(self) -> RunState | None:
        return self.runs.get(self.active_run_id) if self.active_run_id else None

    async def run(
        self,
        request: SwarmRunRequest,
        run_id: str | None = None,
        on_event: Callable[[AgentEvent], None] | None = None,
    ) -> RunState:
        """Execute the full pipeline. Returns the final RunState."""
        run_id = run_id or f"swarm_{uuid.uuid4().hex[:8]}"
        if self.store is not None and not self.store.is_initialized:
            try:
                await self.store.initialize()
            except Exception:  # noqa: BLE001 - dashboard works without persistence
                logger.exception("SwarmRunStore init failed; continuing without persistence")
                self.store = None
        state = RunState(run_id=run_id, request=request)
        self.runs[run_id] = state
        self.active_run_id = run_id

        ctx = _Ctx(request=request, target_monthly=self._resolve_target(request))

        if not request.symbols:
            # sin selección manual: el universo se deriva del corpus de CSVs,
            # consciente del objetivo (dividendos -> ETFs de dividendo del
            # corpus; preservar capital -> defensivos) y de la ventana (en
            # cada familia de solapamiento gana el fondo que CUBRE el run) —
            # escaneo costoso → hilo aparte para no bloquear el event loop
            window_start = None
            if request.backtest_start:
                try:
                    from datetime import date as _date

                    window_start = _date.fromisoformat(str(request.backtest_start)[:10])
                except ValueError:
                    window_start = None
            # Universo AUTOMÁTICO: por defecto el cribado consciente del
            # objetivo (familias de solapamiento — el camino verificado
            # que PASA en ~40s). ``exhaustive_universe`` (UI: "Automatic
            # (all symbols)") lo quita: todos los símbolos que cubren la
            # ventana — 395 en 10y — con el coste honesto: 25+ min/run.
            goal_key = str(request.objetivo_inversion or "").upper()
            auto = await asyncio.to_thread(
                auto_universe,
                goal=request.objetivo_inversion,
                window_start=window_start,
                exhaustive=bool(getattr(request, "exhaustive_universe", False)),
            )
            ctx.auto_symbols = auto.symbols
            ctx.auto_universe_summary = auto.summary()
            logger.info("Run %s %s", run_id, ctx.auto_universe_summary)

        self._emit(
            state,
            AgentEvent(
                RUN_STARTED,
                run_id,
                payload={
                    "request": safe_json(request.to_dict()),
                    "agents": [spec.agent_id for spec in AGENT_SPECS],
                },
            ),
            on_event,
        )
        await self._persist_create(state)

        stages: list[
            tuple[AgentSpec, Callable[[_Ctx], Any], Callable[[_Ctx, Any], Awaitable[Any]]]
        ] = [
            (AGENT_SPECS[0], self._t11_input, self._t11_run),
            (AGENT_SPECS[1], self._t21_input, self._t21_run),
            (AGENT_SPECS[2], self._t31_input, self._t31_run),
            (AGENT_SPECS[3], self._t41_input, self._t41_run),
            (AGENT_SPECS[4], self._t51_input, self._t51_run),
            (AGENT_SPECS[5], self._t61_input, self._t61_run),
            (AGENT_SPECS[6], self._t71_input, self._t71_run),
            (AGENT_SPECS[7], self._t81_input, self._t81_run),
            (AGENT_SPECS[8], self._t91_input, self._t91_run),
            (AGENT_SPECS[9], self._t101_input, self._t101_run),
        ]

        failed = False
        for spec, build_input, run_stage in stages:
            if failed:
                state.agents[spec.agent_id].status = "SKIPPED"
                self._emit(
                    state,
                    AgentEvent(
                        STAGE_SKIPPED,
                        run_id,
                        agent_id=spec.agent_id,
                        payload={"reason": "pipeline stopped after failure"},
                    ),
                    on_event,
                )
                continue
            try:
                await self._execute_stage(state, spec, ctx, build_input, run_stage, on_event)
            except StageFailure as exc:
                failed = True
                state.agents[spec.agent_id].status = "FAILED"
                state.agents[spec.agent_id].error = str(exc)
                self._emit(
                    state,
                    AgentEvent(
                        STAGE_FAILED, run_id, agent_id=spec.agent_id, payload={"error": str(exc)}
                    ),
                    on_event,
                )
                logger.warning("Swarm run %s failed at %s: %s", run_id, spec.agent_id, exc)
            except Exception as exc:  # noqa: BLE001 - a crashing component fails the stage
                failed = True
                state.agents[spec.agent_id].status = "FAILED"
                state.agents[spec.agent_id].error = f"{type(exc).__name__}: {exc}"
                self._emit(
                    state,
                    AgentEvent(
                        STAGE_FAILED,
                        run_id,
                        agent_id=spec.agent_id,
                        payload={"error": f"{type(exc).__name__}: {exc}"},
                    ),
                    on_event,
                )
                logger.exception("Swarm run %s crashed at %s", run_id, spec.agent_id)

        if ctx.decision is not None:
            state.decision = safe_json(ctx.decision)
        state.results = self._build_results(state)

        if failed:
            state.status = "failed"
            state.finished_at = datetime.utcnow().isoformat()
            self._emit(
                state,
                AgentEvent(RUN_FAILED, run_id, payload={"completed": state.completed_count()}),
                on_event,
            )
        else:
            state.xp += XP_COMPLETE_BONUS
            self._evaluate_achievements(state, on_event)
            state.status = "completed"
            state.finished_at = datetime.utcnow().isoformat()
            self._emit(
                state,
                AgentEvent(
                    RUN_COMPLETED,
                    run_id,
                    payload={
                        "xp": state.xp,
                        "achievements": [a["id"] for a in state.achievements],
                        "decision": state.decision,
                    },
                ),
                on_event,
            )

        await self._persist_finish(state)
        logger.info("Swarm run %s %s (xp=%s)", run_id, state.status, state.xp)
        return state

    # ── Stage execution wrapper ──────────────────────────────────────────────

    async def _execute_stage(self, state, spec, ctx, build_input, run_stage, on_event) -> None:
        agent = state.agents[spec.agent_id]
        stage_input = build_input(ctx)
        agent.status = "RUNNING"
        agent.input_payload = safe_json(stage_input)
        self._emit(
            state,
            AgentEvent(
                STAGE_STARTED,
                state.run_id,
                agent_id=spec.agent_id,
                payload={"input": agent.input_payload},
            ),
            on_event,
        )

        start = datetime.utcnow()
        output = await run_stage(ctx, stage_input)
        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000

        if getattr(output, "success", None) is False:
            message = getattr(output, "error_message", None) or f"{spec.name} returned failure"
            raise StageFailure(str(message))

        agent.status = "DONE"
        agent.duration_ms = duration_ms
        agent.output_payload = safe_json(self._stage_output(spec.agent_id, ctx))
        agent.warnings = self._collect_warnings(spec.agent_id, ctx)
        agent.xp = XP_PER_STAGE
        state.xp += XP_PER_STAGE
        self._emit(
            state,
            AgentEvent(
                STAGE_COMPLETED,
                state.run_id,
                agent_id=spec.agent_id,
                payload={
                    "output": agent.output_payload,
                    "duration_ms": round(duration_ms, 1),
                    "warnings": agent.warnings,
                    "xp": XP_PER_STAGE,
                },
            ),
            on_event,
        )

    # ── T1.1 Input Processor ─────────────────────────────────────────────────

    def _t11_input(self, ctx: _Ctx) -> dict:
        user_input = {
            "capital_initial": ctx.request.capital_initial,
            "objetivo_inversion": ctx.request.objetivo_inversion.lower().strip(),
            "risk_tolerance": ctx.request.risk_tolerance.lower().strip(),
            "investment_horizon": ctx.request.investment_horizon,
            "constraints": ctx.request.constraints or {},
        }
        if ctx.request.investor_age is not None:
            user_input["investor_age"] = ctx.request.investor_age
        if ctx.request.tax_province:
            from app.domain.models.input_profile import TaxResidence

            user_input["tax_residence"] = TaxResidence(country_code="ES", country_name="Spain")
        return user_input

    async def _t11_run(self, ctx: _Ctx, user_input: dict):
        from app.domain.models.input_profile import InputProcessor

        ctx.input_profile = InputProcessor().process_input(user_input)
        return ctx.input_profile

    # ── T2.1 Profile Generator ───────────────────────────────────────────────

    def _t21_input(self, ctx: _Ctx):
        from app.services.profile_generator.models import (
            InvestmentObjective,
            ProfileGenerationRequest,
            RiskProfile,
        )

        return ProfileGenerationRequest(
            input_id=ctx.input_profile.input_id,
            capital_initial=ctx.input_profile.capital_initial,
            objective=InvestmentObjective(ctx.input_profile.objetivo_inversion.value),
            risk_tolerance=RiskProfile(RISK_TOLERANCE_MAP[ctx.input_profile.risk_tolerance.value]),
            target_monthly_return_eur=ctx.target_monthly,
            time_horizon_months=ctx.input_profile.investment_horizon,
        )

    async def _t21_run(self, ctx: _Ctx, request):
        from app.services.profile_generator.profile_generator import ProfileGenerator

        result = await ProfileGenerator().generate(request)
        ctx.profile = result.profile
        return result

    # ── T3.1 Module Parametrizer ─────────────────────────────────────────────

    def _t31_input(self, ctx: _Ctx):
        from app.services.module_parametrizer.models import ParameterizationRequest

        profile = ctx.profile
        return ParameterizationRequest(
            profile_id=profile.profile_id,
            input_id=profile.input_id,
            capital_tier=profile.capital_tier.value,
            objective=profile.objective.value,
            risk_profile=profile.risk_profile.value,
            enabled_modules=[m.name for m in profile.enabled_modules if m.enabled],
            initial_capital=profile.initial_capital,
        )

    async def _t31_run(self, ctx: _Ctx, request):
        from app.services.module_parametrizer.module_parametrizer import ModuleParametrizer

        result = await ModuleParametrizer().parametrize(request)
        ctx.param_result = result
        ctx.param_set_id = f"params_{uuid.uuid4().hex[:8]}"
        return result

    # ── T4.1 Backtest Orchestrator ───────────────────────────────────────────

    #: objetivo → estrategia real (espejo del preset de swarm.py, D02).
    #: Dividendos 2026-10-27: el default es EL QUE PASA — el pasivo que el
    #: propio veredicto recomienda en cada run ("deploy the static
    #: portfolio"); dividend_tracking sigue seleccionable a mano.
    _GOAL_STRATEGY: dict[str, str] = {
        "MAXIMIZAR_DIVIDENDOS": "static_ew",
        "CAPITAL_PRESERVATION": "low_volatility",
    }

    def _resolve_strategy(self, ctx: _Ctx) -> str:
        """Effective strategy. Priority (user 2026-10-27: "dejalo por
        default la que pasa"): explicit request override > the GOAL's
        preset (the default the UI applies — for dividends, the passive
        that passes honestly) > the T3.1 module > momentum. D02's rule
        stands: a goal-only request never silently runs an unrelated
        strategy."""
        if ctx.request.strategy:
            return ctx.request.strategy
        goal = str(getattr(ctx.request, "objetivo_inversion", "") or "").upper()
        if goal in self._GOAL_STRATEGY:
            return self._GOAL_STRATEGY[goal]
        param_set = getattr(ctx, "param_result", None)
        modules = (
            list(param_set.parameter_set.module_parameters.keys())
            if param_set and param_set.parameter_set
            else []
        )
        if modules:
            return modules[0]
        return "momentum_modular"

    def _t41_input(self, ctx: _Ctx):
        from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

        # Strategy resolution lives in _resolve_strategy (D02): explicit
        # request override > T3.1 module > objective preset.
        end = _to_date(ctx.request.backtest_end) or date.today()
        start = _to_date(ctx.request.backtest_start) or end - timedelta(days=365)
        if start >= end:
            raise StageFailure(f"Invalid test period: start {start} must be before end {end}")
        return BacktestOrchestrationRequest(
            profile_id=ctx.profile.profile_id,
            input_id=ctx.input_profile.input_id,
            module_parameter_set_id=ctx.param_set_id,
            initial_capital=ctx.input_profile.capital_initial,
            target_monthly_return_eur=ctx.target_monthly,
            objective=ctx.profile.objective.value,
            risk_profile=ctx.profile.risk_profile.value,
            start_date=start,
            end_date=end,
            strategy_name=self._resolve_strategy(ctx),
            symbols=ctx.request.symbols or ctx.auto_symbols or list(DEFAULT_UNIVERSE),
            commission_per_trade=ctx.request.commission_per_trade,
            slippage_percentage=ctx.request.slippage_pct,
            stop_loss_percentage=ctx.request.stop_loss_pct,
            take_profit_percentage=ctx.request.take_profit_pct,
        )

    async def _t41_run(self, ctx: _Ctx, request):
        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

        orchestrator = BacktestOrchestrator()
        # D03: T3.1 module parameters GOVERN the backtest — same injection
        # path the optimizer uses (_build_strategy merges them into the
        # strategy config). Without this the profile's limits only ever
        # lived in the intermediate JSON.
        strategy = self._resolve_strategy(ctx)
        param_set = getattr(ctx, "param_result", None)
        modules = (
            param_set.parameter_set.module_parameters
            if param_set and param_set.parameter_set
            else {}
        )
        overrides = _strategy_overrides_from(modules, strategy)
        # ADOPTED params close the loop: "Adopt best parameters" (optimizer)
        # saved a set per strategy — applying it here is the only way the
        # adoption changes the NEXT run (before, the button was decorative).
        # Adopted values WIN over the profile's generic ones: they were
        # explicitly chosen for this strategy on real engine results.
        if self.store is not None and self.store.is_initialized:
            try:
                adopted = await self.store.get_active_param_set(strategy)
            except Exception:  # noqa: BLE001 - a param-set read must never kill a run
                logger.warning("Could not read adopted params for %s", strategy, exc_info=True)
                adopted = None
            if adopted and adopted.get("params"):
                overrides.update({k: v for k, v in adopted["params"].items()})
        if overrides:
            orchestrator._strategy_param_overrides = overrides  # noqa: SLF001

        ctx.backtest = await orchestrator.orchestrate(request)
        return ctx.backtest

    # ── T5.1 Validation Engine ───────────────────────────────────────────────

    def _t51_input(self, ctx: _Ctx):
        from app.services.validation_engine.models import ValidationRequest

        metrics = ctx.backtest.backtest_result.metrics
        return ValidationRequest(
            profile_id=ctx.profile.profile_id,
            input_id=ctx.input_profile.input_id,
            initial_capital=ctx.input_profile.capital_initial,
            target_monthly_return_eur=ctx.target_monthly,
            module_parameter_set_id=ctx.param_set_id,
            backtest_feasibility_ratio=ctx.backtest.feasibility_ratio,
            backtest_sharpe_ratio=metrics.sharpe_ratio,
            backtest_max_drawdown_pct=abs(metrics.max_drawdown_pct),
            tax_rate=self._effective_tax_rate(ctx),
            walk_forward_passed=ctx.backtest.backtest_result.walk_forward_passed,
            walk_forward_failures=list(ctx.backtest.backtest_result.validation_failures),
            risk_profile=ctx.profile.risk_profile.value,
        )

    def _effective_tax_rate(self, ctx: _Ctx) -> Decimal:
        """Effective Spanish savings-tax rate on the simulated gain.

        Uses the real SpainTaxEngine progressive brackets (19/21/23%).
        Falls back to a flat 21% if the engine is unavailable.
        """
        result = ctx.backtest.backtest_result
        gain = result.ending_capital - result.starting_capital
        if gain <= 0:
            return Decimal("0")
        try:
            from app.services.tax_efficiency.engines.spain_tax_engine import SpainTaxEngine

            tax = SpainTaxEngine().calculate_capital_gains_tax(gain)
            return (tax / gain).quantize(Decimal("0.001"))
        except Exception:  # noqa: BLE001 - tax engine must not break validation
            logger.warning("SpainTaxEngine unavailable; using flat 21%%", exc_info=True)
            return Decimal("0.21")

    async def _t51_run(self, ctx: _Ctx, request):
        from app.services.validation_engine.validation_engine import ValidationEngine

        ctx.validation = await ValidationEngine().validate(request)
        return ctx.validation

    # ── T6.1 Strategy Recommender ────────────────────────────────────────────

    def _t61_input(self, ctx: _Ctx):
        """One ranked strategy per enabled module.

        Scores are derived deterministically from the parametrized module
        config (improvement estimate, preset, exposure) so the recommender
        receives real, profile-dependent inputs.
        """
        from app.services.strategy_recommendation.strategy_ranker import RankedStrategy

        param_set = ctx.param_result.parameter_set
        modules = sorted(param_set.module_parameters.items(), key=lambda kv: kv[1].priority)
        total = max(1, len(modules))
        ranked: list[RankedStrategy] = []
        # SCORE DESDE EL BACKTEST REAL, no fórmula estática (que daba 61.0
        # en TODAS las ejecuciones sin importar Sharpe/CAGR). Componentes:
        # Sharpe (0-30), MaxDD (0-25), Feasibility (0-25), Excess (0-10), WF (0-10).
        backtest = getattr(ctx, "backtest", None)
        metrics = getattr(getattr(backtest, "backtest_result", None), "metrics", None)
        sharpe = float(getattr(metrics, "sharpe_ratio", 0) or 0) if metrics else 0.0
        max_dd = abs(float(getattr(metrics, "max_drawdown_pct", 0) or 0)) if metrics else 100.0
        feasibility = float(getattr(backtest, "feasibility_ratio", 0) or 0) if backtest else 0.0
        # excess contra el benchmark HONESTO de la estrategia: para dividendos
        # el equal-weight del propio universo (SPY es mega-cap tech y resta
        # puntos estructuralmente); si no hay, el benchmark de mercado
        payload = getattr(backtest, "backtest_result", None)
        excess = -100.0
        if payload is not None:
            ew = getattr(payload, "excess_vs_universe_ew_pct", None)
            mkt = getattr(payload, "excess_return_pct", None)
            source = ew if ew is not None else mkt
            if source is not None:
                excess = float(source)
        wf_passed = bool(getattr(payload, "walk_forward_passed", False)) if payload else False
        ew_sharpe = float(getattr(payload, "universe_ew_sharpe", 0) or 0) if payload else 0.0

        # Sharpe RELATIVO al del propio universo EW: la pregunta correcta es
        # si el diseño activo conserva la eficiencia-riesgo de su universo,
        # no si alcanza el listón institucional 1.0 que ni el propio mercado
        # supera en muchas décadas (SPY 2016-2026 ≈ 0.8).
        if ew_sharpe > 0.05:
            ratio = sharpe / ew_sharpe
            sharpe_pts = 30 if ratio >= 1.0 else 20 if ratio >= 0.75 else 10 if ratio >= 0.5 else 0
        else:
            sharpe_pts = 30 if sharpe >= 1.0 else 20 if sharpe >= 0.5 else 10 if sharpe >= 0 else 0
        # DD por NORMA ACCIONARIAL: <20% excepcional, <25% sólido, <30% un
        # oso normal, <40% doloroso. Las bandas anteriores (<15 para el
        # máximo) no las cumplía NI SPY en 2016-2026.
        # RELATIVO cuando existe el gemelo buy&hold del propio universo
        # (mismo principio que el Sharpe relativo): la caída del MERCADO no
        # es un demérito del diseño — la pregunta es si cayó MÁS que su
        # universo. COVID 2020: -33% del pasivo juzgado por la banda
        # absoluta daba 5/25 solo por existir.
        ew_dd = (
            float(getattr(payload, "universe_ew_max_dd_pct", 0) or 0) if payload else 0.0
        )
        if ew_dd >= 1.0:
            dd_ratio = max_dd / ew_dd
            dd_pts = (
                25
                if dd_ratio <= 1.05
                else 15
                if dd_ratio <= 1.15
                else 10
                if dd_ratio <= 1.30
                else 5
                if max_dd < 40
                else 0
            )
        else:
            dd_pts = (
                25
                if max_dd < 20
                else 15
                if max_dd < 25
                else 10
                if max_dd < 30
                else 5
                if max_dd < 40
                else 0
            )
        feas_pts = (
            25
            if feasibility >= 2.0
            else 15
            if feasibility >= 1.5
            else 10
            if feasibility >= 1.0
            else 0
        )
        excess_pts = 10 if excess > 0 else 5 if excess > -50 else 0
        wf_pts = 10 if wf_passed else 0
        base_components = sharpe_pts + dd_pts + feas_pts + excess_pts + wf_pts

        # INCOME (F4·T6.1): para objetivos de RENTA el score debe premiar la
        # renta neta REAL cobrada (D01) contra el capital inicial, no solo
        # el retorno total — una cartera puede empatar en Sharpe y aun así
        # retirar menos efectivo. Los cinco componentes de mercado se
        # comprimen al 75% para dejarle 25 puntos; sin evidencia de renta
        # (sin datos, o cobertura con gaps → computable=False) son 0
        # puntos y el máximo alcanzable baja a 75: no se puntúa lo que no
        # se puede medir.
        objective = getattr(ctx.profile, "objective", "")
        objective = getattr(objective, "value", objective)
        income_objective = str(objective).lower() in ("maximizar_dividendos", "income_generation")
        income_pts = 0.0
        if income_objective:
            div = getattr(payload, "dividend_metrics", None) if payload is not None else None
            initial = float(getattr(ctx.profile, "initial_capital", 0) or 0)
            if div is not None and getattr(div, "computable", False) and initial > 0:
                years = div.net_by_year or {}
                net_total = float(div.net_total or 0)
                per_year = net_total / len(years) if years else net_total
                annual_yield = per_year / initial * 100.0
                income_pts = (
                    25.0
                    if annual_yield >= 4.0
                    else 20.0
                    if annual_yield >= 3.0
                    else 15.0
                    if annual_yield >= 2.0
                    else 8.0
                    if annual_yield >= 1.0
                    else 4.0
                    if annual_yield > 0
                    else 0.0
                )
        if income_objective:
            base = Decimal(str(min(100.0, base_components * 0.75 + income_pts)))
        else:
            base = Decimal(str(min(100, base_components)))

        for rank, (name, config) in enumerate(modules, start=1):
            preset = str(getattr(config, "preset", "balanced")).lower()
            return_bonus = Decimal("6") if "aggressive" in preset else Decimal("0")
            safety = Decimal("6") if "conservative" in preset else Decimal("0")
            exposure_penalty = min(Decimal("25"), config.max_exposure * Decimal("80"))
            ranked.append(
                RankedStrategy(
                    rank=rank,
                    strategy_name=name,
                    overall_score=base,
                    return_score=min(Decimal("97"), base + return_bonus),
                    risk_score=max(Decimal("20"), Decimal("88") - exposure_penalty + safety),
                    stability_score=max(Decimal("20"), base - Decimal("2") + safety),
                    consistency_score=max(Decimal("20"), base - Decimal("1") + safety),
                    percentile=Decimal("100") * (Decimal("1") - Decimal(rank - 1) / total),
                )
            )
        return ranked

    async def _t61_run(self, ctx: _Ctx, ranked):
        from app.services.strategy_recommendation.strategy_recommender import StrategyRecommender

        ctx.recommendation = await StrategyRecommender().recommend_strategy(
            ranked_strategies=ranked,
            objective=ctx.profile.objective.value,
            risk_profile=ctx.profile.risk_profile.value,
        )
        return ctx.recommendation

    # ── T7.1 Portfolio Constructor ───────────────────────────────────────────

    def _t71_input(self, ctx: _Ctx):
        from app.services.portfolio_constructor.models import PortfolioConstructionRequest

        param_set = ctx.param_result.parameter_set
        return PortfolioConstructionRequest(
            profile_id=ctx.profile.profile_id,
            input_id=ctx.input_profile.input_id,
            capital_eur=ctx.input_profile.capital_initial,
            risk_profile=RISK_PROFILE_PORTFOLIO_MAP[ctx.profile.risk_profile.value],
            investment_objective=ctx.profile.objective.value,
            enabled_modules=list(param_set.module_parameters.keys()),
            target_annual_return_pct=ctx.profile.required_annual_return_pct or Decimal("10"),
            max_acceptable_drawdown_pct=DEFAULT_MAX_DRAWDOWN_PCT,
        )

    async def _t71_run(self, ctx: _Ctx, request):
        from app.services.agent_swarm.portfolio_allocation import allocation_from_backtest
        from app.services.portfolio_constructor.portfolio_constructor import PortfolioConstructor

        # LA CARtera real del run: exposición media ponderada por tiempo de
        # los trades reales del backtest. El constructor genérico (pesos por
        # características de módulo inventadas) queda como fallback sin datos.
        bt = getattr(ctx.backtest, "backtest_result", None)
        if bt is not None and bt.trades_summary:
            try:
                ctx.portfolio = allocation_from_backtest(
                    profile_id=ctx.profile.profile_id,
                    capital_eur=ctx.input_profile.capital_initial,
                    trades_summary=bt.trades_summary,
                    annual_return_pct=bt.achieved_annual_return_pct,
                    sharpe_ratio=bt.metrics.sharpe_ratio,
                    max_drawdown_pct=bt.metrics.max_drawdown_pct,
                )
                return ctx.portfolio
            except ValueError:
                logger.warning("T7.1: no usable trade exposure -> generic constructor")
        ctx.portfolio = await PortfolioConstructor().construct_portfolio(request)
        return ctx.portfolio

    # ── T8.1 Risk Scaling ────────────────────────────────────────────────────

    def _t81_input(self, ctx: _Ctx):
        from app.services.risk_scaling_application.models import RiskScalingRequest

        metrics = ctx.backtest.backtest_result.metrics
        return RiskScalingRequest(
            profile_id=ctx.profile.profile_id,
            input_id=ctx.input_profile.input_id,
            base_portfolio=ctx.portfolio,
            market_regime=ctx.request.market_regime,
            volatility_level=ctx.request.volatility_level,
            current_drawdown_pct=abs(metrics.max_drawdown_pct),
            max_acceptable_drawdown_pct=DEFAULT_MAX_DRAWDOWN_PCT,
            phase3_enabled=ctx.profile.risk_scaling_enabled,
        )

    async def _t81_run(self, ctx: _Ctx, request):
        from app.services.risk_scaling_application.risk_scaling_applicator import (
            RiskScalingApplication,
        )

        ctx.risk_scaled = await RiskScalingApplication().apply_risk_scaling(request)
        return ctx.risk_scaled

    # ── T9.1 Reporting Generator ─────────────────────────────────────────────

    def _t91_input(self, ctx: _Ctx):
        from app.services.reporting_generator.models import (
            AllocationSnapshot,
            ReportGenerationRequest,
            StrategyMetrics,
        )

        m = ctx.backtest.backtest_result.metrics
        metrics = StrategyMetrics(
            annual_return_pct=m.annual_return_pct,
            sharpe_ratio=m.sharpe_ratio,
            sortino_ratio=m.sortino_ratio,
            max_drawdown_pct=m.max_drawdown_pct,
            win_rate_pct=m.win_rate_pct,
            profit_factor=m.profit_factor,
            calmar_ratio=m.calmar_ratio,
            volatility_pct=m.volatility_pct,
            cumulative_return_pct=m.total_return_pct,
            num_trades=m.total_trades,
        )
        allocations = [
            AllocationSnapshot(
                module_name=a.module_name,
                allocation_pct=a.weight_pct,
                expected_return_contribution_pct=(
                    a.weight_pct * ctx.portfolio.expected_portfolio_return_pct / Decimal("100")
                ),
                risk_contribution_pct=(
                    a.weight_pct * ctx.portfolio.expected_portfolio_drawdown_pct / Decimal("100")
                ),
            )
            for a in ctx.portfolio.allocations
        ]
        return ReportGenerationRequest(
            report_id=f"RPT-{uuid.uuid4().hex[:8]}",
            profile_id=ctx.profile.profile_id,
            input_id=ctx.input_profile.input_id,
            strategy_name=ctx.recommendation.recommended_strategy,
            backtest_metrics=metrics,
            allocations=allocations,
            capital_eur=ctx.input_profile.capital_initial,
            target_annual_return_pct=ctx.profile.required_annual_return_pct or Decimal("10"),
            max_acceptable_drawdown_pct=DEFAULT_MAX_DRAWDOWN_PCT,
        )

    async def _t91_run(self, ctx: _Ctx, request):
        from app.services.reporting_generator.reporting_generator import ReportingGenerator

        ctx.report = await ReportingGenerator().generate_report(request)
        return ctx.report

    # ── T10.1 Deploy Decision ────────────────────────────────────────────────

    def _t101_input(self, ctx: _Ctx) -> dict:
        m = ctx.backtest.backtest_result.metrics
        payload = ctx.backtest.backtest_result
        return {
            "validation_report": {
                "overall_status": "APPROVED" if ctx.validation.passed else "REJECTED",
                "passed_gates": 6 if ctx.validation.passed else 3,
                "total_gates": 6,
                "critical_failures": list(ctx.validation.critical_failures),
                "warnings": list(ctx.validation.warnings),
            },
            "backtest_result": {
                "feasibility_ratio": float(ctx.backtest.feasibility_ratio),
                "sharpe_ratio": float(m.sharpe_ratio),
                "total_return": float(m.total_return_pct),
                "max_drawdown": abs(float(m.max_drawdown_pct)),
                "win_rate": float(m.win_rate_pct),
                "universe_ew_return_pct": (
                    float(payload.universe_ew_return_pct)
                    if getattr(payload, "universe_ew_return_pct", None) is not None
                    else 0.0
                ),
                # Sharpe del gemelo pasivo: el explicador del score lo nombra
                # (qué arrastra el score, en unidades que el usuario compara)
                "universe_ew_sharpe": (
                    float(payload.universe_ew_sharpe)
                    if getattr(payload, "universe_ew_sharpe", None) is not None
                    else None
                ),
            },
            "recommendation": {
                "score": float(ctx.recommendation.overall_score),
                "confidence_level": ctx.recommendation.confidence_level,
                "recommendation": ctx.recommendation.recommended_strategy,
                # la estrategia EJECUTADA (puede ser static_ew aunque T6
                # recomiende módulos): el veredicto distingue "capa de
                # gestión que resta valor" de "coste real de ejecución"
                "executed_strategy": self._resolve_strategy(ctx),
            },
            "allocation": {
                "allocation": {
                    a.module_name: float(a.weight_pct) / 100 for a in ctx.portfolio.allocations
                },
                "sharpe_ratio": float(ctx.portfolio.expected_portfolio_sharpe),
                "diversification_ratio": float(ctx.portfolio.diversification_ratio),
            },
            "investment_profile": safe_json(ctx.profile.to_dict()),
        }

    async def _t101_run(self, ctx: _Ctx, inputs: dict):
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        ctx.decision = await DeployDecisionOrchestrator().orchestrate(**inputs)
        return ctx.decision

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _resolve_target(self, request: SwarmRunRequest) -> Decimal:
        """Default monthly target: 0.3% of capital (keeps feasibility reachable)."""
        if request.target_monthly_return_eur is not None:
            return request.target_monthly_return_eur
        return (request.capital_initial * Decimal("0.003")).quantize(Decimal("1"))

    _MAX_EQUITY_POINTS = 300
    _MAX_TRADES_SUMMARY = 400

    def _slim_backtest(self, backtest: Any) -> Any:
        """Adelgaza el payload del backtest para la UI/store.

        Con universos grandes el payload completo (curva de equity + todos los
        trades con Decimales largos) supera el límite de safe_json y se
        trunca ENTERO a un preview inútil. Aquí mantenemos todo lo que la UI
        pinta —métricas completas, feasibility, equity diezmada, últimos
        trades— con tamaño acotado.
        """
        if backtest is None:
            return None
        data = backtest if isinstance(backtest, dict) else None
        inner = (
            getattr(backtest, "backtest_result", None)
            if data is None
            else (backtest.get("backtest_result") or {})
        )
        if data is None:
            data = {
                k: getattr(backtest, k, None)
                for k in (
                    "success",
                    "feasibility_ratio",
                    "feasibility_status",
                    "warnings",
                    # la estrategia EJECUTADA viaja con el payload: el tile
                    # de la UI no debe decir "dividend_tracking" cuando el
                    # motor corrió static_ew
                    "strategy_name",
                )
            }
        if isinstance(inner, dict):
            slim_inner = dict(inner)
        elif dataclasses.is_dataclass(inner) and not isinstance(inner, type):
            slim_inner = dataclasses.asdict(inner)
        elif hasattr(inner, "model_dump"):
            slim_inner = inner.model_dump()
        else:
            slim_inner = {}
        eq = slim_inner.get("equity_curve")
        if isinstance(eq, (list, tuple)) and len(eq) > self._MAX_EQUITY_POINTS:
            step = max(1, len(eq) // self._MAX_EQUITY_POINTS)
            slim_inner["equity_curve"] = list(eq)[::step]
        ts = slim_inner.get("trades_summary")
        if isinstance(ts, (list, tuple)) and len(ts) > self._MAX_TRADES_SUMMARY:
            slim_inner["trades_summary"] = list(ts)[-self._MAX_TRADES_SUMMARY :]
        data["backtest_result"] = slim_inner
        return data

    def _stage_output(self, agent_id: str, ctx: _Ctx) -> Any:
        return {
            "t11": lambda: ctx.input_profile,
            "t21": lambda: ctx.profile,
            "t31": lambda: ctx.param_result,
            "t41": lambda: self._slim_backtest(ctx.backtest),
            "t51": lambda: ctx.validation,
            "t61": lambda: ctx.recommendation,
            "t71": lambda: ctx.portfolio,
            "t81": lambda: ctx.risk_scaled,
            "t91": lambda: ctx.report,
            "t101": lambda: ctx.decision,
        }[agent_id]()

    def _collect_warnings(self, agent_id: str, ctx: _Ctx) -> list[str]:
        source = self._stage_output(agent_id, ctx)
        warnings = [str(w) for w in getattr(source, "warnings", None) or []]
        if agent_id == "t41" and ctx.auto_universe_summary:
            warnings = [ctx.auto_universe_summary, *warnings]
        return warnings

    def _evaluate_achievements(self, state: RunState, on_event) -> None:
        unlocked: list[tuple[str, str, str]] = [("first_launch", "◦", "First execution")]

        if state.completed_count() == len(AGENT_SPECS):
            unlocked.append(("pipeline_complete", "◦", "Full pipeline 10/10"))
        backtest = state.agents["t41"].output_payload or {}
        if (
            state.agents["t41"].status == "DONE"
            and isinstance(backtest, dict)
            and str(backtest.get("feasibility_status", "")).upper() == "APPROVED"
        ):
            unlocked.append(("feasibility_pass", "◦", "Feasibility gate passed"))
        if (state.decision or {}).get("status") == "APPROVED":
            unlocked.append(("deploy_approved", "◦", "Deploy approved"))
        if state.completed_count() == len(AGENT_SPECS) and not any(
            a.warnings for a in state.agents.values()
        ):
            unlocked.append(("clean_run", "◦", "Clean run"))

        for ach_id, emoji, label in unlocked:
            entry = {"id": ach_id, "emoji": emoji, "label": label}
            state.achievements.append(entry)
            self._emit(
                state,
                AgentEvent(ACHIEVEMENT_UNLOCKED, state.run_id, payload=entry),
                on_event,
            )

    def _emit(self, state: RunState, event: AgentEvent, on_event=None) -> None:
        state.events.append(event)
        state.version += 1
        self.bus.publish(event)
        if on_event is not None:
            try:
                on_event(event)
            except Exception:  # noqa: BLE001 - callbacks must not break the run
                logger.exception("on_event callback failed")

    async def _persist_create(self, state: RunState) -> None:
        if self.store is None:
            return
        try:
            await self.store.create_run(
                state.run_id, safe_json(state.request.to_dict()), state.started_at
            )
        except Exception:  # noqa: BLE001 - persistence must not break the run
            logger.exception("Failed to persist swarm run start")

    async def _persist_finish(self, state: RunState) -> None:
        if self.store is None:
            return
        try:
            await self.store.finish_run(
                state.run_id,
                state.status,
                state.finished_at or datetime.utcnow().isoformat(),
                total_xp=state.xp,
                achievements=state.achievements,
                results=state.results,
            )
            for event in state.events:
                await self.store.append_event(event)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist swarm run finish")

    def _build_results(self, state: RunState) -> dict:
        """JSON-ready aggregated results, compatible with /capa2 workflow-status."""
        results: dict[str, Any] = {}
        keys = [
            ("input_profile", "t11"),
            ("investment_profile", "t21"),
            ("module_parameters", "t31"),
            ("backtest_result", "t41"),
            ("validation", "t51"),
            ("recommendation", "t61"),
            ("portfolio", "t71"),
            ("risk_scaling", "t81"),
            ("report", "t91"),
            ("deployment_decision", "t101"),
        ]
        for key, agent_id in keys:
            payload = state.agents[agent_id].output_payload
            if payload is not None:
                results[key] = payload

        if isinstance(results.get("report"), dict) and results["report"].get("report_id"):
            results["report_id"] = results["report"]["report_id"]
        return results
