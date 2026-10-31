"""Agent Swarm — pipeline control page (light, simple, animated).

Runs the real CAPA 2 pipeline (T1.1→T10.1) with a novice-friendly UI in
English: a guided configuration card on the left, a plain-language
"What is happening" step list with live status, and an explained result
card (verdict, key numbers, what it means, next steps). Technical detail
(log, stage durations) and history/replay live behind progressive
disclosure.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds
from app.presentation.dashboard.nicegui_app.components.agent_card import StepTrack
from app.presentation.dashboard.nicegui_app.components.mission_log import MissionLog
from app.presentation.dashboard.nicegui_app.components.office_scene import OfficeScene
from app.presentation.dashboard.nicegui_app.components.swarm_fx import install as install_fx
from app.services.agent_swarm.executor import (
    AGENT_SPECS,
    SPEC_BY_AGENT,
    AgentState,
    SwarmRunRequest,
)
from app.services.agent_swarm.universe_selector import (
    DEFAULT_DATA_DIR,
    DEFAULT_UNIVERSE,
    corpus_symbol_names,
)

if TYPE_CHECKING:
    from app.services.agent_swarm.executor import Capa2PipelineExecutor, RunState
    from app.services.agent_swarm.store import SwarmRunStore

logger = logging.getLogger(__name__)

OBJECTIVES = {
    "MAXIMIZAR_CAPITAL": "Grow capital",
    "MAXIMIZAR_DIVIDENDOS": "Maximise dividends",
    "CAPITAL_PRESERVATION": "Preserve capital",
    "BALANCED_GROWTH": "Balanced growth",
    "INCOME_GENERATION": "Generate income",
    "VIVIR_DE_LA_CARTERA": "Live off it — total return (UCITS)",
    "ACUMULAR": "Accumulate — total return (UCITS ACC)",
}

VERDICT_ES: dict[str, tuple[str, str, str]] = {}  # kept name for compatibility
VERDICTS = {
    "APPROVED": ("ok", "APPROVED", "The simulation meets the goal — this setup is viable."),
    "CONDITIONAL": (
        "mid",
        "CONDITIONAL",
        "Viable, but review the recommendations before investing.",
    ),
    "REJECTED": (
        "bad",
        "REJECTED",
        "This setup does not reach the goal. Try more capital or a more modest target.",
    ),
}

# Sector mapping for the portfolio view (symbol → sector label)
_SECTOR_MAP: dict[str, str] = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "META": "Technology",
    "AMZN": "Consumer",
    "NVDA": "Technology",
    "TSLA": "Consumer",
    "JPM": "Financials",
    "JNJ": "Healthcare",
    "XOM": "Energy",
    "KO": "Consumer",
    "SPY": "Index Fund",
    "QQQ": "Index Fund",
    "SAN": "Financials",
    "BBVA": "Financials",
    "IBE.MC": "Utilities",
    "ITX.MC": "Consumer",
    "SAP.DE": "Technology",
    "SIE.DE": "Industrial",
    "MC.PA": "Consumer",
    "ASML.AS": "Technology",
    "NESN.SW": "Consumer",
    "6758.T": "Technology",
    "7203.T": "Consumer",
    "IBEX": "Index Fund",
    "INTC": "Technology",
    "AMD": "Technology",
    "PFE": "Healthcare",
    "V": "Financials",
    "MA": "Financials",
    "PG": "Consumer",
    "DIS": "Consumer",
    "CSCO": "Technology",
    "WMT": "Consumer",
    "MRK.DE": "Healthcare",
    "GE": "Industrial",
    "F": "Consumer",
    "BA": "Industrial",
    "AXP": "Financials",
    # ── ETFs: familia → sector legible ─────────────────────────────
    "IVV": "Index Fund",
    "VOO": "Index Fund",
    "DIA": "Index Fund",
    "IWM": "Index Fund",
    "IJH": "Index Fund",
    "IWF": "Index Fund",
    "VTV": "Index Fund",
    "VEA": "Index Fund",
    "EFA": "Index Fund",
    "EEM": "Index Fund",
    "VTI": "Index Fund",
    "XLK": "Technology",
    "VGT": "Technology",
    "SMH": "Technology",
    "SOXX": "Technology",
    "XLF": "Financials",
    "VFH": "Financials",
    "XLE": "Energy",
    "VDE": "Energy",
    "XLV": "Healthcare",
    "VHT": "Healthcare",
    "XLI": "Industrial",
    "VIS": "Industrial",
    "XLY": "Consumer",
    "VCR": "Consumer",
    "XLP": "Consumer",
    "VDC": "Consumer",
    "XLU": "Utilities",
    "VPU": "Utilities",
    "XLB": "Materials",
    "VAW": "Materials",
    "XLC": "Technology",
    "VNQ": "Real Estate",
    "VOX": "Technology",
    "GLD": "Commodities",
    "IAU": "Commodities",
    "SLV": "Commodities",
    "TLT": "Bonds",
    "IEF": "Bonds",
    "LQD": "Bonds",
    "VCIT": "Bonds",
    "AGG": "Bonds",
    "BND": "Bonds",
    "BIV": "Bonds",
    "SCHD": "Dividend ETF",
    "VIG": "Dividend ETF",
    "VYM": "Dividend ETF",
    "DGRO": "Dividend ETF",
    "DGRW": "Dividend ETF",
    "DVY": "Dividend ETF",
    "SDY": "Dividend ETF",
    "NOBL": "Dividend ETF",
    "DLN": "Dividend ETF",
    "PEY": "Dividend ETF",
    "FDVV": "Dividend ETF",
    "DTD": "Dividend ETF",
}


#: universo de ETFs de dividendo U2 — re-seleccionado OOS-limpio sobre
#: 2016-2024 (Sharpe 0.67, el mejor de 6 candidatos) y validado virgen en
#: 2024-2026 (Sharpe 1.35). Un ETF por función: calidad US (SCHD), alto
#: yield US amplio (VYM), alto yield internacional (VYMI), crecimiento de
#: dividendo (VIG). Sin BND (el refugio-a-bono vendió en el suelo de 2022:
#: 77% vs 127% del mismo run) ni DGRO/DGRW (solapados con VIG/SCHD).
DIVIDEND_ETF_UNIVERSE = ["SCHD", "VYM", "VYMI", "VIG"]

#: universo de dividendo con histórico profundo (2003-2007 en adelante) para
#: horizontes largos: con el universo de 10 años un run de 20 años se
#: truncaría silenciosamente a la década disponible. Solo ETFs de dividendo
#: (BIV fuera: es un bono, no un generador de renta)
DEEP_DIVIDEND_ETF_UNIVERSE = ["SDY", "DLN", "DVY", "PEY"]

#: a partir de este horizonte (meses) el preset de dividendos usa el universo profundo
LONG_HORIZON_MONTHS = 180

#: universo sectorial Vanguard para la anomalía de baja volatilidad
LOW_VOL_UNIVERSE = ["VDC", "VCR", "VDE", "VFH", "VHT", "VIS", "VGT", "VAW", "VNQ", "VPU", "VOX"]

#: objetivo → (estrategia real, universo) que la UI preselecciona.
#: Dividendos 2026-10-27 (user: "dejalo por default la que pase"): el
#: preset pasa a static_ew con universo AUTOMÁTICO (None) — es el
#: veredicto que el propio sistema da en cada run ("deploy the static
#: portfolio") y la única configuración que pasa los gates honestos en
#: esta ventana (CONDITIONAL). dividend_tracking sigue en el dropdown.
GOAL_PRESETS: dict[str, tuple[str, list[str] | None]] = {
    "MAXIMIZAR_DIVIDENDOS": ("static_ew", None),
    "CAPITAL_PRESERVATION": ("low_volatility", LOW_VOL_UNIVERSE),
    # Retorno total "vivir de la cartera" (29-10): universo UCITS EUR
    # explícito — el acumulador como núcleo (EUNL.DE hace de VWCE
    # pre-2019), VHYL/IDVY de renta y IBGS.AS de colchón. Todo con
    # ≥13 años de histórico local, suficiente para horizontes de ~10-11
    # años (el gate de cobertura reporta si la ventana pide más).
    # Retorno total "vivir de la cartera" (29-10): universo UCITS EUR por
    # pantalla AUTOMÁTICA (regla 30-10 del dueño: por defecto TODO el
    # universo del objetivo, decidido por ventana — nada de listas
    # clavadas). El acumulador de núcleo (EUNL.DE hace de VWCE pre-2019),
    # VHYL/IDVY de renta y IBGS.AS de colchón.
    "VIVIR_DE_LA_CARTERA": ("static_ew", None),
    # Acumulación pura (30-10): la fase ANTES de vivir de la cartera —
    # mismo principio, TODO el universo del objetivo vía AUTOMÁTICO: la
    # pantalla decide por ventana quién cubre. En 10 años: EUNL/IUSQ/
    # EIMI/VHYL/IDVY + IBGS de colchón; en ventanas cortas entran también
    # VWCE y QDIV (nacen 2019/2018 y sí cubren). Sin reparto no hay IRPF
    # anual — Hacienda espera a que el dueño venda.
    "ACUMULAR": ("static_ew", None),
}

#: objetivo → universo alternativo cuando el horizonte es largo
LONG_HORIZON_UNIVERSES: dict[str, list[str]] = {
    "MAXIMIZAR_DIVIDENDOS": DEEP_DIVIDEND_ETF_UNIVERSE,
}


def preset_for_goal(
    goal: str | None, horizon_months: float | None = None
) -> tuple[str, list[str] | None] | None:
    """Preset (estrategia, universo) para un objetivo, insensible a mayúsculas.

    Con ``horizon_months`` >= LONG_HORIZON_MONTHS el universo cambia al de
    histórico profundo si el objetivo tiene uno.
    """
    if not goal:
        return None
    key = str(goal).upper()
    preset = GOAL_PRESETS.get(key)
    if preset is None:
        return None
    strategy_name, universe = preset
    # universos manuales alternativos solo cuando el preset trae lista;
    # un preset con universo AUTOMÁTICO (None) deja que la pantalla del
    # corpus decima por ventana, que es el camino verificado.
    if (
        isinstance(universe, list)
        and horizon_months is not None
        and horizon_months >= LONG_HORIZON_MONTHS
    ):
        universe = LONG_HORIZON_UNIVERSES.get(key, universe)
    return strategy_name, universe


DATA_DIR = DEFAULT_DATA_DIR

PERIOD_DAYS = {"6m": 183, "1y": 365, "2y": 730, "5y": 1825, "10y": 3650}

#: "All available data" sin límites conocidos (universo Automatic): 20 años
MAX_PERIOD_FALLBACK_DAYS = 7300

#: días por mes medio (365.25 / 12) para convertir ventanas en horizonte
_DAYS_PER_MONTH = 30.4375


def horizon_months(start_iso: str, end_iso: str) -> int:
    """Investment horizon (months) = the backtest window itself.

    The user stays invested for the whole tested period, so there is no
    separate "months you plan to stay invested" question: a 10-year backtest
    IS a 10-year horizon. Never below 1 month.
    """
    start = _to_day(start_iso)
    end = _to_day(end_iso)
    if start is None or end is None:
        return 1
    return max(1, round((end - start).days / _DAYS_PER_MONTH))


def period_months(preset: str, custom_start: Any, custom_end: Any) -> int | None:
    """Approximate months a period selection spans, before touching the data.

    Used to pick a universe while the user is still configuring: fixed
    presets map through PERIOD_DAYS, custom dates are measured directly, and
    "max" (all available data) counts as a long horizon so the deepest
    history gets used. None when unknown.
    """
    if preset == "max":
        return LONG_HORIZON_MONTHS
    if preset == "custom":
        start, end = _to_day(custom_start), _to_day(custom_end)
        if start is None or end is None or end <= start:
            return None
        return horizon_months(start.isoformat(), end.isoformat())
    days = PERIOD_DAYS.get(preset)
    return None if days is None else max(1, round(days / _DAYS_PER_MONTH))


SPANISH_PROVINCES = [
    "A Coruña",
    "Álava",
    "Albacete",
    "Alicante",
    "Almería",
    "Asturias",
    "Ávila",
    "Badajoz",
    "Barcelona",
    "Burgos",
    "Cáceres",
    "Cádiz",
    "Cantabria",
    "Castellón",
    "Ceuta",
    "Ciudad Real",
    "Córdoba",
    "Cuenca",
    "Girona",
    "Granada",
    "Guadalajara",
    "Guipúzcoa",
    "Huelva",
    "Huesca",
    "Islas Baleares",
    "Jaén",
    "La Rioja",
    "Las Palmas",
    "León",
    "Lleida",
    "Lugo",
    "Madrid",
    "Málaga",
    "Melilla",
    "Murcia",
    "Navarra",
    "Ourense",
    "Palencia",
    "Pontevedra",
    "Salamanca",
    "Santa Cruz de Tenerife",
    "Segovia",
    "Sevilla",
    "Soria",
    "Tarragona",
    "Teruel",
    "Toledo",
    "Valencia",
    "Valladolid",
    "Vizcaya",
    "Zamora",
    "Zaragoza",
]


def available_universe(data_dir: Path | str = DATA_DIR) -> list[str]:
    """Symbols that have historical CSV data (falls back to the defaults)."""
    symbols = corpus_symbol_names(data_dir)
    return symbols or list(DEFAULT_UNIVERSE)


def data_window(
    symbols: list[str] | None, data_dir: Path | str = DATA_DIR
) -> tuple[date, date] | None:
    """Earliest and latest date covered by the CSVs of the given symbols.

    ``None`` (auto universe, not yet resolved) → no bounds: the period is
    resolved without clamping, like custom dates.
    """
    if not symbols:
        return None
    earliest: date | None = None
    latest: date | None = None
    for symbol in symbols:
        csv_path = Path(data_dir) / f"{symbol}.csv"
        if not csv_path.is_file():
            continue
        try:
            with csv_path.open() as handle:
                handle.readline()  # header
                first = handle.readline().split(",")[0]
                last = ""
                for line in handle:
                    if line.strip():
                        last = line
            day_first = date.fromisoformat(first.strip())
            day_last = date.fromisoformat(last.split(",")[0].strip())
        except (ValueError, OSError, IndexError):
            continue
        earliest = day_first if earliest is None else min(earliest, day_first)
        latest = day_last if latest is None else max(latest, day_last)
    return (earliest, latest) if earliest and latest else None


def _to_day(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def resolve_period(
    preset: str,
    custom_start: Any,
    custom_end: Any,
    bounds: tuple[date, date] | None,
    today: date | None = None,
) -> tuple[str, str]:
    """Turn a preset (or custom dates) into a (start, end) ISO window.

    The window is clamped to the available data so the backtest never asks
    for dates we have no candles for.
    """
    today = today or date.today()
    data_min, data_max = bounds if bounds else (None, None)
    end = data_max or today

    if preset == "custom":
        start = _to_day(custom_start) or (end - timedelta(days=365))
        end = _to_day(custom_end) or end
    elif preset == "max":
        # sin símbolos conocidos (universo Automatic) no hay data_min: pedir
        # 20 años — el selector elige fondos que cubren la ventana y el
        # cargador recorta cada símbolo a su propio histórico
        start = data_min or (end - timedelta(days=MAX_PERIOD_FALLBACK_DAYS))
    else:
        start = end - timedelta(days=PERIOD_DAYS.get(preset, 365))

    if data_min:
        start = max(start, data_min)
    if start >= end:  # never return an empty/inverted window
        end = start + timedelta(days=30)
    return start.isoformat(), end.isoformat()


# ── Pure helpers (unit-tested without a UI) ───────────────────────────────────


def format_log_line(event: Any) -> str:
    """Human-readable line for the execution log (AgentEvent or persisted dict)."""
    if isinstance(event, dict):
        etype = event.get("type")
        agent_id = event.get("agent_id")
        payload = event.get("payload") or {}
    else:
        etype = event.type
        agent_id = event.agent_id
        payload = event.payload or {}
    spec = SPEC_BY_AGENT.get(agent_id) if agent_id else None
    name = spec.name if spec else "Agent"

    if etype == "run_started":
        request = payload.get("request", {})
        capital = request.get("capital_initial", "?")
        objective = request.get("objetivo_inversion", "?")
        return f"Pipeline started — capital €{capital} · objective {objective}"
    if etype == "stage_started":
        return f"{name} started"
    if etype == "stage_completed":
        duration = payload.get("duration_ms", 0)
        return f"{name} completed in {duration:.0f} ms (+{payload.get('xp', 0)} XP)"
    if etype == "stage_failed":
        return f"{name} FAILED — {payload.get('error', 'unknown error')}"
    if etype == "stage_skipped":
        return f"{name} skipped"
    if etype == "achievement_unlocked":
        return f"Milestone reached: {payload.get('label', '?')}"
    if etype == "run_completed":
        decision = payload.get("decision") or {}
        return (
            f"Pipeline complete — {payload.get('xp', 0)} XP · verdict {decision.get('status', '?')}"
        )
    if etype == "run_failed":
        return f"Pipeline FAILED — {payload.get('completed', 0)}/10 agents completed"
    return str(etype)


def apply_event_to_states(states: dict[str, AgentState], event: dict) -> None:
    """Fold a persisted event dict into a dict of AgentState (replay mode)."""
    etype = event.get("type")
    agent_id = event.get("agent_id")
    payload = event.get("payload") or {}

    if etype == "stage_started" and agent_id in states:
        states[agent_id].status = "RUNNING"
        states[agent_id].input_payload = payload.get("input")
    elif etype == "stage_completed" and agent_id in states:
        state = states[agent_id]
        state.status = "DONE"
        state.output_payload = payload.get("output")
        state.duration_ms = payload.get("duration_ms", 0) or 0
        state.warnings = list(payload.get("warnings", []))
        state.xp = payload.get("xp", 0) or 0
    elif etype == "stage_failed" and agent_id in states:
        states[agent_id].status = "FAILED"
        states[agent_id].error = payload.get("error")
    elif etype == "stage_skipped" and agent_id in states:
        states[agent_id].status = "SKIPPED"


def extract_result_metrics(results: dict) -> dict:
    """Pull novice-readable key numbers out of a run's results payload."""
    backtest = results.get("backtest_result") or {}
    inner = backtest.get("backtest_result") or {}
    metrics = inner.get("metrics") or {}
    recommendation = results.get("recommendation") or {}
    decision = results.get("deployment_decision") or {}
    # max_drawdown_pct is already in percent units ([-100, 0])
    drawdown = _as_float(metrics.get("max_drawdown_pct"))
    return {
        "total_return": metrics.get("total_return_pct"),
        "sharpe": metrics.get("sharpe_ratio"),
        "drawdown": round(drawdown, 2),
        "feasibility": backtest.get("feasibility_ratio"),
        # la estrategia EJECUTADA (static_ew aunque T6 recomiende módulos):
        # el tile "Recommended strategy" no puede decir dividend_tracking
        # cuando el motor corrió el pasivo
        "strategy": (
            backtest.get("strategy_name")
            or inner.get("strategy_name")
            or recommendation.get("recommended_strategy")
        ),
        "universe_ew": inner.get("universe_ew_return_pct"),
        "excess_vs_universe_ew": inner.get("excess_vs_universe_ew_pct"),
        "tax_efficiency": inner.get("tax_efficiency"),
        "verdict": decision.get("status"),
        "reasons": list(decision.get("reasons") or [])[:4],
        "next_steps": list(decision.get("next_steps") or [])[:3],
        "benchmark_symbol": inner.get("benchmark_symbol") or "",
        "benchmark_return": inner.get("benchmark_return_pct"),
        "excess_return": inner.get("excess_return_pct"),
        "symbols": [str(s) for s in inner.get("symbols") or []],
    }


def build_fan_chart_option(boot: dict, equity_curve: list | None = None) -> dict:
    """ECharts fan chart: P5–P95 band, P25–P75 band, median, and the run's
    REAL path (dashed) — no JS functions (NiceGUI renders them as text),
    only "{value}" templates."""
    bands = boot.get("bands") or []
    if len(bands) != 5:
        return {}
    p5, p25, p50, p75, p95 = [[round(float(v), 3) for v in band] for band in bands]
    n = len(p5)
    outer = [round(p95[i] - p5[i], 3) for i in range(n)]
    inner = [round(p75[i] - p25[i], 3) for i in range(n)]
    years = float(boot.get("horizon_years") or 1)
    x = [f"{years * i / max(n - 1, 1):.0f}y" for i in range(n)]
    series = [
        {
            "name": "P5",
            "type": "line",
            "data": p5,
            "stack": "outer",
            "symbol": "none",
            "lineStyle": {"opacity": 0},
            "silent": True,
        },
        {
            "name": "Range P5–P95",
            "type": "line",
            "data": outer,
            "stack": "outer",
            "symbol": "none",
            "lineStyle": {"opacity": 0},
            "areaStyle": {"opacity": 0.15},
            "color": "#3e7d4f",
        },
        {
            "name": "P25",
            "type": "line",
            "data": p25,
            "stack": "inner",
            "symbol": "none",
            "lineStyle": {"opacity": 0},
            "silent": True,
        },
        {
            "name": "Range P25–P75",
            "type": "line",
            "data": inner,
            "stack": "inner",
            "symbol": "none",
            "lineStyle": {"opacity": 0},
            "areaStyle": {"opacity": 0.35},
            "color": "#3e7d4f",
        },
        {
            "name": "Median",
            "type": "line",
            "data": p50,
            "symbol": "none",
            "lineStyle": {"width": 2, "color": "#3e7d4f"},
            "color": "#3e7d4f",
        },
    ]
    if equity_curve:
        try:
            vals = [float(p["value"]) if isinstance(p, dict) else float(p[1]) for p in equity_curve]
            if vals and vals[0] > 0:
                step = max(1, len(vals) // n)
                actual = [round(v / vals[0], 3) for v in vals[::step]][:n]
                series.append(
                    {
                        "name": "This run",
                        "type": "line",
                        "data": actual,
                        "symbol": "none",
                        "lineStyle": {"width": 2, "type": "dashed", "color": "#ab4f3f"},
                        "color": "#ab4f3f",
                    }
                )
        except (TypeError, ValueError, KeyError, IndexError):
            pass
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 0},
        "grid": {"left": 48, "right": 16, "top": 32, "bottom": 24},
        "xAxis": {"type": "category", "data": x, "boundaryGap": False},
        "yAxis": {"type": "value", "scale": True, "axisLabel": {"formatter": "{value}×"}},
        "series": series,
    }


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def extract_portfolio(results: dict) -> dict:
    """Portfolio composition from the real T7.1/T8.1 output payloads."""
    portfolio = results.get("portfolio") or {}
    risk = results.get("risk_scaling") or {}

    allocations = [
        {
            "module": str(a.get("module_name", "?")),
            "weight": _as_float(a.get("weight_pct")),
            "capital": _as_float(a.get("capital_allocation_eur")),
            "rationale": str(a.get("rationale", "")),
        }
        for a in portfolio.get("allocations") or []
    ]
    adjusted = [
        {
            "module": str(a.get("module_name", "?")),
            "weight": _as_float(a.get("adjusted_weight_pct")),
            "original": _as_float(a.get("original_weight_pct")),
        }
        for a in risk.get("adjusted_allocations") or []
    ]
    return {
        "method": portfolio.get("allocation_method"),
        "expected_return": portfolio.get("expected_portfolio_return_pct"),
        "expected_sharpe": portfolio.get("expected_portfolio_sharpe"),
        "diversification": portfolio.get("diversification_ratio"),
        "allocations": allocations,
        "adjusted": adjusted,
        "risk_applied": bool(risk.get("risk_scaling_applied", False)),
    }


WARM_PALETTE = ds.CHART_MUTED


def build_allocation_chart(allocations: list[dict]) -> dict | None:
    """ECharts donut of the portfolio weights, or None if empty."""
    if not allocations:
        return None
    return {
        "backgroundColor": "transparent",
        "color": WARM_PALETTE,
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}% ({d}%)"},
        "legend": {"bottom": 0, "textStyle": {"color": "#6f6858"}, "itemWidth": 12},
        "series": [
            {
                "type": "pie",
                "radius": ["42%", "70%"],
                "center": ["50%", "42%"],
                "itemStyle": {
                    "borderRadius": 6,
                    "borderColor": "#fffdf6",
                    "borderWidth": 2,
                },
                "label": {"color": "#3e3a31", "formatter": "{b}\n{d}%"},
                "data": [
                    {"name": a["module"], "value": round(a["weight"], 2)} for a in allocations
                ],
                "animationType": "scale",
                "animationEasing": "elasticOut",
                "animationDuration": 700,
            }
        ],
    }


def build_module_exposure_chart(parameter_set: dict) -> dict | None:
    """Bars of max exposure per module from the T3.1 parameter set."""
    modules = parameter_set.get("module_parameters") or {}
    rows = [
        {"module": name, "exposure": _as_float(cfg.get("max_exposure")) * 100}
        for name, cfg in modules.items()
    ]
    if not rows:
        return None
    rows = list(reversed(rows))
    return {
        "backgroundColor": "transparent",
        "color": WARM_PALETTE,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 120, "right": 30, "top": 10, "bottom": 24},
        "xAxis": {"type": "value", "axisLabel": {"color": "#6f6858", "formatter": "{value}%"}},
        "yAxis": {
            "type": "category",
            "data": [r["module"] for r in rows],
            "axisLabel": {"color": "#3e3a31"},
        },
        "series": [
            {
                "type": "bar",
                "barMaxWidth": 14,
                "data": [round(r["exposure"], 1) for r in rows],
                "animationDuration": 500,
            }
        ],
    }


def build_equity_curve_chart(equity_points: list) -> dict | None:
    """ECharts area-line of the portfolio's equity over the test period.

    Points come as [iso_ts, value_str] pairs from the real engine's equity
    curve. Styled like a broker's portfolio evolution chart.
    """
    if not equity_points or len(equity_points) < 2:
        return None
    # Accept both [ts, value] lists and {"ts": ..., "value": ...} dicts
    if isinstance(equity_points[0], dict):
        dates = [str(pt.get("ts", ""))[:10] for pt in equity_points]
        values = [round(_as_float(pt.get("value")), 2) for pt in equity_points]
    else:
        dates = [str(pt[0])[:10] for pt in equity_points]
        values = [round(_as_float(pt[1]), 2) for pt in equity_points]
    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "grid": {"left": 80, "right": 24, "top": 40, "bottom": 50},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLabel": {"color": "#6f6858", "rotate": 35, "fontSize": 11},
            "boundaryGap": False,
            "axisLine": {"lineStyle": {"color": "#d8cdb4"}},
        },
        "yAxis": {
            "type": "value",
            "name": "Portfolio value",
            "nameTextStyle": {"color": "#6f6858", "padding": [0, 0, 0, 30]},
            "axisLabel": {
                "color": "#6f6858",
                "fontSize": 12,
                "formatter": "{value} €",
            },
            "splitLine": {"show": True, "lineStyle": {"color": "#e7dfcc", "width": 1}},
            "scale": True,
        },
        "series": [
            {
                "type": "line",
                "data": values,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"color": "#3e7d4f", "width": 2.5},
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(62,125,79,.25)"},
                            {"offset": 1, "color": "rgba(62,125,79,.02)"},
                        ],
                    }
                },
                "animationDuration": 800,
                "animationEasing": "linear",
            }
        ],
    }


def build_risk_adjustment_chart(adjusted: list[dict]) -> dict | None:
    """Grouped bars: base weight vs risk-adjusted weight per module."""
    if not adjusted:
        return None
    adjusted = list(reversed(adjusted))  # categories bottom-up
    modules = [a["module"] for a in adjusted]
    return {
        "backgroundColor": "transparent",
        "color": ["#a9bfd3", "#d0a8a3"],
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 0, "textStyle": {"color": "#6f6858"}},
        "grid": {"left": 110, "right": 24, "top": 34, "bottom": 24},
        "xAxis": {"type": "value", "axisLabel": {"color": "#6f6858"}},
        "yAxis": {"type": "category", "data": modules, "axisLabel": {"color": "#3e3a31"}},
        "series": [
            {
                "name": "Base weight %",
                "type": "bar",
                "barMaxWidth": 14,
                "data": [round(a["original"], 2) for a in adjusted],
                "animationDuration": 500,
            },
            {
                "name": "After risk adjustment %",
                "type": "bar",
                "barMaxWidth": 14,
                "data": [round(a["weight"], 2) for a in adjusted],
                "animationDuration": 700,
            },
        ],
    }


def build_duration_chart_option(states: dict[str, AgentState]) -> dict | None:
    """ECharts horizontal-bar option of per-step durations, or None if empty."""
    done = [
        (spec, states[spec.agent_id])
        for spec in AGENT_SPECS
        if states.get(spec.agent_id) and states[spec.agent_id].status == "DONE"
    ]
    if not done:
        return None
    done.reverse()  # ECharts draws categories bottom-up
    return {
        "backgroundColor": "transparent",
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 170, "right": 40, "top": 10, "bottom": 24},
        "xAxis": {"type": "value", "name": "ms", "axisLabel": {"color": "#8a97ab"}},
        "yAxis": {
            "type": "category",
            "data": [f"{spec.emoji} {spec.name}" for spec, _ in done],
            "axisLabel": {"color": "#17233b"},
        },
        "series": [
            {
                "type": "bar",
                "data": [
                    {
                        "value": round(agent.duration_ms, 1),
                        "itemStyle": {"color": spec.color},
                    }
                    for spec, agent in done
                ],
                "barMaxWidth": 16,
                "barMinHeight": 2,
                "animationDuration": 500,
            }
        ],
    }


def _parse_ts(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


@dataclass
class _ReplaySnapshot:
    """Result-shaped summary reconstructed from replayed events."""

    status: str
    achievements: list = field(default_factory=list)
    decision: dict | None = None
    started_at: str = ""
    finished_at: str = ""
    agents: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)


def _render_payload(title: str, payload: Any) -> None:
    with ui.column().classes("w-full gap-xs"):
        ui.label(title).classes("lbl")
        if payload is None:
            ui.label("— awaiting data —").classes("term-line term-ts")
        elif isinstance(payload, str):
            ui.html(f'<pre class="swarm-json">{html.escape(payload[:8000])}</pre>').classes(
                "w-full"
            )
        else:
            text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
            ui.html(f'<pre class="swarm-json">{html.escape(text[:16000])}</pre>').classes("w-full")


def _fmt_short(value: Any) -> str:
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".") or "0"
    except (TypeError, ValueError):
        return "—"


def _metric_tile(label: str, value: Any, delay: float) -> None:
    if value is None or value == "":
        text = "—"
    else:
        try:
            number = float(value)
            text = f"{number:.2f}".rstrip("0").rstrip(".") or "0"
        except (ValueError, TypeError):
            text = str(value)
    with ui.element("div").classes("metric-tile").style(f"animation-delay: {delay:.2f}s"):
        ui.label(label).classes("k")
        ui.label(text).classes("v")


def _chip(text: str, klass: str = "c-idle") -> ui.label:
    return ui.label(str(text)).classes(f"sc-chip {klass}")


def t21_profile_payload(payload: Any) -> dict:
    """Normalise the T2.1 step payload to the InvestmentProfile dict.

    The executor stores the profile ITSELF (flat: capital_tier, risk_profile,
    enabled_modules, …) as the step output; the dialog used to expect it
    nested under "profile" and rendered "?" everywhere.
    """
    if not isinstance(payload, dict):
        return {}
    nested = payload.get("profile")
    return nested if isinstance(nested, dict) else payload


def _render_step_visual(agent_id: str, payload: Any) -> None:
    """Friendly, chart-backed rendering of a step's output payload."""
    if not isinstance(payload, dict):
        ui.label("— awaiting data —").classes("help")
        return

    if agent_id == "t11":
        with ui.row().classes("w-full gap-sm wrap"):
            _metric_tile("Capital", f"€{payload.get('capital_initial', '?')}", 0)
            _metric_tile("Goal", payload.get("objetivo_inversion", "?"), 0.05)
            _metric_tile("Risk", payload.get("risk_tolerance", "?"), 0.1)
            _metric_tile("Horizon (months)", payload.get("investment_horizon", "?"), 0.15)
            _metric_tile(
                "Tax residence", (payload.get("tax_residence") or {}).get("country_code", "—"), 0.2
            )

    elif agent_id == "t21":
        profile = t21_profile_payload(payload)
        modules = profile.get("enabled_modules") or []
        with ui.row().classes("w-full gap-sm wrap"):
            _metric_tile("Capital tier", profile.get("capital_tier", "?"), 0)
            _metric_tile("Risk profile", profile.get("risk_profile", "?"), 0.05)
            _metric_tile("Modules enabled", len(modules), 0.1)
            _metric_tile(
                "Required return %/yr", profile.get("required_annual_return_pct", "—"), 0.15
            )
            _metric_tile("Position size %", profile.get("position_size_pct", "—"), 0.2)
        if modules:
            ui.label("ENABLED MODULES").classes("lbl q-mt-md q-mb-xs")
            with ui.row().classes("gap-xs wrap"):
                for module in modules[:10]:
                    _chip(module.get("name", "?"), "c-done")

    elif agent_id == "t31":
        parameter_set = payload.get("parameter_set") or {}
        with ui.row().classes("w-full gap-sm wrap"):
            _metric_tile("Modules", parameter_set.get("total_modules_enabled", "?"), 0)
            _metric_tile(
                "Total exposure %",
                round(_as_float(parameter_set.get("total_max_exposure")) * 100, 1),
                0.05,
            )
            _metric_tile("Cost $/mo", parameter_set.get("total_estimated_cost_usd", "—"), 0.1)
            _metric_tile(
                "Est. improvement %",
                parameter_set.get("total_estimated_improvement_pct", "—"),
                0.15,
            )
        exposure = build_module_exposure_chart(parameter_set)
        if exposure is not None:
            ui.label("MAX EXPOSURE PER MODULE").classes("lbl q-mt-md q-mb-xs")
            ui.echart(exposure).props(
                "role=img aria-label='Bar chart of max exposure per module'"
            ).classes("w-full").style("height: 220px")
        disabled = payload.get("disabled_modules") or []
        if disabled:
            ui.label("DISABLED BY CAPITAL GATING").classes("lbl q-mt-md q-mb-xs")
            with ui.row().classes("gap-xs wrap"):
                for name in disabled:
                    _chip(name, "c-failed")

    elif agent_id == "t41":
        inner = payload.get("backtest_result") or {}
        metrics = inner.get("metrics") or {}
        with ui.row().classes("w-full gap-sm wrap"):
            _metric_tile("Return %", metrics.get("total_return_pct"), 0)
            _metric_tile("Annual %", metrics.get("annual_return_pct"), 0.04)
            _metric_tile("Sharpe", metrics.get("sharpe_ratio"), 0.08)
            _metric_tile("Sortino", metrics.get("sortino_ratio"), 0.12)
            _metric_tile("Drawdown %", metrics.get("max_drawdown_pct"), 0.16)
            _metric_tile("Win rate %", metrics.get("win_rate_pct"), 0.2)
            _metric_tile("Profit factor", metrics.get("profit_factor"), 0.24)
            _metric_tile("Trades", metrics.get("total_trades"), 0.28)
            _metric_tile("Feasibility", payload.get("feasibility_ratio"), 0.32)
        status = str(payload.get("feasibility_status", "")).upper()
        if status:
            chip = _chip(
                status,
                "c-done"
                if status == "APPROVED"
                else "c-failed"
                if status == "REJECTED"
                else "c-idle",
            )
            chip.classes("q-mt-sm")

    elif agent_id == "t51":
        recommendation = str(payload.get("overall_recommendation", "?"))
        chip_klass = (
            "c-done"
            if recommendation == "APPROVE"
            else "c-failed"
            if recommendation == "REJECT"
            else "c-idle"
        )
        with ui.row().classes("w-full items-center gap-md q-mb-sm"):
            _chip(recommendation, chip_klass)
            _chip(f"confidence: {payload.get('confidence_level', '?')}", "c-idle")
            _chip(
                "passed" if payload.get("passed") else "failed",
                "c-done" if payload.get("passed") else "c-failed",
            )
        feasibility = payload.get("feasibility") or {}
        if feasibility:
            ui.label(
                f"Feasibility: {feasibility.get('feasibility_status', '?')} — "
                f"{feasibility.get('reason', '')}"
            ).classes("help q-mb-xs")
        capital = payload.get("capital_viability") or {}
        if capital:
            ui.label(f"Capital: {capital.get('reason', '')}").classes("help q-mb-xs")
        modules = payload.get("module_viabilities") or {}
        if modules:
            ui.label("MODULE GATES").classes("lbl q-mt-sm q-mb-xs")
            for name, info in list(modules.items())[:10]:
                with ui.row().classes("w-full items-center no-wrap gap-sm"):
                    mark = "✓" if info.get("enabled") else "✗"
                    color = "term-good" if info.get("enabled") else "term-bad"
                    ui.label(mark).classes(f"term-line {color}")
                    ui.label(name).classes("pstep-name")
                    ui.label(info.get("reason", "")).classes("help q-ml-auto")

    elif agent_id == "t61":
        score = payload.get("overall_score")
        try:
            score_num = f"{float(score):.0f}/100"
        except (TypeError, ValueError):
            score_num = "—"
        with ui.row().classes("w-full gap-sm wrap"):
            _metric_tile("Score", score_num, 0)
            _metric_tile("Recommended", payload.get("recommended_strategy", "?"), 0.05)
            _metric_tile("Confidence", payload.get("confidence_level", "?"), 0.1)
            _metric_tile("Suitability", payload.get("suitability_score", "—"), 0.15)
            _metric_tile("Est. annual return", payload.get("estimated_annual_return"), 0.2)
            _metric_tile("Max drawdown", payload.get("max_expected_drawdown"), 0.25)
        alternatives = payload.get("alternatives") or []
        if alternatives:
            ui.label("ALTERNATIVES").classes("lbl q-mt-md q-mb-xs")
            with ui.row().classes("gap-xs wrap"):
                for name in alternatives[:6]:
                    _chip(name, "c-idle")

    elif agent_id == "t71":
        portfolio = extract_portfolio({"portfolio": payload})
        is_real = portfolio["method"] == "backtest_positions"
        with ui.row().classes("w-full gap-sm wrap q-mb-sm"):
            _metric_tile("Method", str(portfolio["method"] or "?").replace("_", " "), 0)
            _metric_tile(
                "Return %/yr (run)" if is_real else "Expected return %",
                portfolio["expected_return"],
                0.05,
            )
            _metric_tile(
                "Sharpe (run)" if is_real else "Sharpe",
                portfolio["expected_sharpe"],
                0.1,
            )
            _metric_tile("Diversification", portfolio["diversification"], 0.15)
        donut = build_allocation_chart(portfolio["allocations"])
        if donut is not None:
            ui.label("ALLOCATION").classes("lbl q-mt-sm q-mb-xs")
            ui.echart(donut).props(
                "role=img aria-label='Donut chart of portfolio weights'"
            ).classes("w-full").style("height: 260px")

    elif agent_id == "t81":
        if payload.get("risk_scaling_applied"):
            with ui.row().classes("w-full gap-sm wrap q-mb-sm"):
                _metric_tile("Scaling factor", payload.get("scaling_factor"), 0)
                _metric_tile("Regime", payload.get("market_regime", "?"), 0.05)
                _metric_tile("Volatility", payload.get("volatility_level", "?"), 0.1)
            adjusted = extract_portfolio({"risk_scaling": payload})["adjusted"]
            risk_chart = build_risk_adjustment_chart(adjusted)
            if risk_chart is not None:
                ui.label("BASE VS ADJUSTED WEIGHTS").classes("lbl q-mt-sm q-mb-xs")
                ui.echart(risk_chart).props(
                    "role=img aria-label='Bar chart comparing base and risk-adjusted weights'"
                ).classes("w-full").style("height: 220px")
        else:
            ui.label("No risk adjustment was applied for these market conditions.").classes("help")
        if payload.get("adjustment_rationale"):
            ui.label(payload["adjustment_rationale"]).classes("help q-mt-xs")

    elif agent_id == "t91":
        rating = str(payload.get("overall_rating", "neutral"))
        kind = {"excellent": "ok", "good": "ok", "neutral": "mid", "poor": "bad"}.get(rating, "mid")
        ui.label(rating.upper()).classes(f"verdict {kind}").style(
            "font-size: 16px; padding: 6px 14px"
        )
        if payload.get("summary"):
            ui.label(payload["summary"]).classes("help q-mt-sm")
        for title, key, mark, color in (
            ("STRENGTHS", "strengths", "✓", "term-good"),
            ("WEAKNESSES", "weaknesses", "✗", "term-bad"),
            ("RECOMMENDATIONS", "recommendations", "→", "term-info"),
        ):
            items = payload.get(key) or []
            if items:
                ui.label(title).classes("lbl q-mt-md q-mb-xs")
                for item in items[:5]:
                    ui.label(f"{mark} {item}").classes(f"term-line {color}")

    elif agent_id == "t101":
        verdict = str(payload.get("status", "?"))
        kind = VERDICTS.get(verdict, ("mid", verdict, ""))[0]
        ui.label(verdict).classes(f"verdict {kind}").style("font-size: 18px; padding: 8px 16px")
        with ui.row().classes("w-full gap-sm wrap q-mt-sm"):
            _metric_tile("Confidence", payload.get("confidence_level", "?"), 0)
            _metric_tile("Feasibility", payload.get("feasibility_ratio"), 0.05)
            _metric_tile("Score", payload.get("recommendation_score"), 0.1)
            _metric_tile(
                "Validation", "passed" if payload.get("validation_passed") else "failed", 0.15
            )
        for title, key, mark in (
            ("WHY", "reasons", "•"),
            ("RISKS", "risks", "⚠"),
            ("NEXT STEPS", "next_steps", "→"),
            ("RECOMMENDATIONS", "recommendations", "→"),
        ):
            items = payload.get(key) or []
            if items:
                ui.label(title).classes("lbl q-mt-md q-mb-xs")
                for item in items[:5]:
                    ui.label(f"{mark} {item}").classes("help")


# ── Page ──────────────────────────────────────────────────────────────────────


def render(
    executor: Capa2PipelineExecutor | None,
    store: SwarmRunStore | None,
) -> None:
    """Render the Agent Swarm pipeline-control page."""
    install_fx()
    ui.dark_mode(False)  # light page inside the dark shell

    view: dict[str, Any] = {
        "run_id": None,
        "version": -1,
        "log_index": 0,
        "finished_shown": False,
        "states": {spec.agent_id: AgentState() for spec in AGENT_SPECS},
    }

    def fresh_states() -> dict[str, AgentState]:
        return {spec.agent_id: AgentState() for spec in AGENT_SPECS}

    def fx(script: str) -> None:
        try:
            ui.run_javascript(script)
        except Exception:  # noqa: BLE001 - FX must never break the page
            logger.debug("FX script failed", exc_info=True)

    track: StepTrack | None = None

    with ui.column().classes("w-full"):
        with ui.element("div").classes("light-sheet w-full"):
            for blob in ("blob-a", "blob-b", "blob-c"):
                ui.element("div").classes(f"blob {blob}").props("aria-hidden=true")

            # ── Mission Control — the promise + the macro loop, full width.
            # (Was a squeezed middle column inside the config row — the
            # "broken carousel" sliver. A novice reads top-down: promise,
            # where I am, then what to do.)
            from app.presentation.dashboard.nicegui_app import design_system as _ds
            from app.presentation.dashboard.nicegui_app.components.mission_control import (
                mission_control_band as _mc_band,
            )
            from app.presentation.dashboard.nicegui_app.design_system import inject as _ds_inject

            _ds_inject()
            _ds.hero(
                "Mission Control",
                "Your whole investment loop, live: the robot below builds, "
                "tests and watches a portfolio you can actually understand.",
            )
            _mc_holder = ui.column().classes("w-full gap-0 q-mb-md")

            async def _mc_refresh() -> None:
                try:
                    _mc_runs = await store.list_runs(limit=30)
                except Exception:  # noqa: BLE001 - the band never blocks the page
                    _mc_runs = []
                _mc_holder.clear()
                with _mc_holder:
                    _mc_band(_mc_runs)

            _mc_holder.clear()
            with _mc_holder:
                _mc_band(None)  # first paint; real states arrive in a blink
            ui.timer(0.05, _mc_refresh, once=True)

            with ui.column().classes("w-full gap-lg q-mt-md"):
                # ── 1 · Set it up — a full-width strip, not a sidebar form.
                # Three answers across the page, one button, done.
                with ui.element("div").classes("panel q-pa-lg w-full"):
                    with ui.row().classes("items-center gap-sm q-mb-md no-wrap"):
                        ui.label("1 · SET IT UP").classes("lbl")
                        ui.label("START HERE").classes("start-pill")

                    # ── The three essentials, inline across the page ──
                    with ui.row().classes("w-full items-start gap-lg wrap"):
                        with ui.column().classes("gap-xs flex-1").style("min-width: 200px"):
                            capital = ui.number(
                                "Initial capital (€)",
                                value=100_000,
                                min=100,
                                max=10_000_000,
                                step=1000,
                            ).classes("w-full")
                            ui.label("How much money you want to start with.").classes("help")

                        with ui.column().classes("gap-xs flex-1").style("min-width: 240px"):
                            objetivo = ui.select(
                                # Default (user 2026-10-27): the configuration that PASSES honestly —
                                # dividends + 10y + High + Automatic (all symbols).
                                OBJECTIVES,
                                value="MAXIMIZAR_DIVIDENDOS",
                                label="Your goal",
                            ).classes("w-full")
                            ui.label("What you want to achieve with this investment.").classes(
                                "help"
                            )

                        universe_options = available_universe()
                        with ui.column().classes("gap-xs flex-1").style("min-width: 240px"):
                            periodo = ui.select(
                                {
                                    "6m": "Last 6 months",
                                    "1y": "Last year",
                                    "2y": "Last 2 years",
                                    "5y": "Last 5 years",
                                    "10y": "Last 10 years",
                                    "max": "All available data",
                                    "custom": "Custom dates…",
                                },
                                value="10y",
                                label="Investment period",
                            ).classes("w-full")
                            ui.label(
                                "How long you stay invested — tested on exactly "
                                "this slice of history, money never leaves."
                            ).classes("help")

                    # The action line: one button, its promise, and the live
                    # answer to "did it work?" — all on a single strip.
                    with ui.row().classes("w-full items-center gap-md wrap q-mt-md"):
                        run_button = (
                            ui.button("Run my backtest", icon="play_arrow")
                            .props("size=md unelevated")
                            .classes("run-btn")
                            .style("min-width: 240px")
                            .mark("run_pipeline")
                            .tooltip(
                                "Replays history with your settings — nothing is "
                                "bought or sold. Keyboard: ALT+R."
                            )
                        )
                        ui.label(
                            "Nothing is bought or sold: the plan is tested on history first."
                        ).classes("help").style("flex:1;min-width:220px")
                        state_chip = ui.element("div").classes("state-chip")
                        with state_chip:
                            ui.element("span").classes("dot")
                            state_text = ui.label("Ready").classes("state-text")
                        step_text = ui.label("Step 0 of 10").classes("pstep-meta")
                        replay_last_btn = (
                            ui.button("Replay last", icon="replay")
                            .props("flat dense")
                            .mark("replay_last")
                            .tooltip("Re-run the latest pipeline visually (ALT+P)")
                        )
                        replay_last_btn.disable()

                    async def replay_last() -> None:
                        last_id = view.get("last_run_id")
                        if last_id:
                            await replay_run(last_id)
                        else:
                            ui.notify("No previous runs yet.", type="warning")

                    replay_last_btn.on_click(replay_last)

                    with ui.element("div").classes("w-full q-mt-xs prog-wrap"):
                        prog_fill = ui.element("div").classes("prog-fill")

                    # ── Everything else is pre-set; open only to fine-tune ──
                    fine_tune = ui.expansion(
                        "Fine-tune — everything else is pre-set for you", icon="tune"
                    ).classes("w-full q-mt-md")
                    with fine_tune:
                        riesgo = ui.select(
                            {"bajo": "Low", "medio": "Medium", "alto": "High"},
                            value="alto",
                            label="Risk level",
                        ).classes("w-full")
                        ui.label("How much risk you are comfortable taking.").classes(
                            "help q-mb-sm"
                        )

                        edad = ui.number("Your age", value=35, min=18, max=100, step=1)
                        ui.label("Used for suitability and long-term planning.").classes(
                            "help q-mb-sm"
                        )

                        provincia = ui.select(
                            SPANISH_PROVINCES, value="Madrid", label="Province (tax residence)"
                        ).classes("w-full")
                        ui.label(
                            "Sets the Spanish tax rules applied to your gains (19/21/23%)."
                        ).classes("help q-mb-sm")

                        ui.separator().classes("q-mb-sm")
                        ui.label("Universe").classes("lbl q-mb-xs")
                        modo_universo = ui.toggle(
                            {
                                "auto": "Automatic",
                                "auto-all": "Automatic (all)",
                                "manual": "Manual",
                            },
                            value="auto",
                        ).classes("w-full")
                        ui.label(
                            "Automatic: the app screens your CSV library (fresh data, "
                            "liquidity, enough history) and tests the most liquid symbols. "
                            "'Automatic (all)': EVERY symbol covering the window — 395 on "
                            "10y, honest warning: 25+ minutes per run. Manual: pick below."
                        ).classes("help q-mb-sm")
                        # Choosing Manual must reveal the symbol picker below
                        # — otherwise the toggle seems to do nothing.
                        modo_universo.on_value_change(lambda e: fine_tune.set_value(True))
                        target = ui.number(
                            "Monthly target (€) — empty = automatic",
                            value=None,
                            min=0,
                            step=50,
                        )
                        with ui.row().classes("w-full gap-sm no-wrap"):
                            regime = ui.select(
                                {"bull": "Bull", "sideways": "Sideways", "bear": "Bear"},
                                value="sideways",
                                label="Market",
                            ).classes("flex-1")
                            volatilidad = ui.select(
                                {"low": "Low", "normal": "Normal", "high": "High"},
                                value="normal",
                                label="Volatility",
                            ).classes("flex-1")
                        universo = (
                            ui.select(
                                universe_options,
                                multiple=True,
                                # user rule 2026-10-27: Manual starts with EVERYTHING
                                # selected — you remove what you don't want, not
                                # hunt for what you do.
                                value=list(universe_options),
                                label="Universe (symbols with historical data)",
                            )
                            .classes("w-full")
                            .mark("universe_select")
                        )
                        with ui.row().classes("w-full gap-xs no-wrap"):
                            ui.button(
                                "Select all",
                                on_click=lambda: universo.set_value(list(universe_options)),
                            ).props("flat dense no-caps size=xs").mark("universe_all").tooltip(
                                f"All {len(universe_options)} symbols with data. Honest "
                                "warning: the run gets heavy (minutes) and the strict "
                                "coverage gate FAILS if any symbol doesn't cover the "
                                "whole test window — a shorter period or Automatic "
                                "keeps this usable."
                            )
                            ui.button(
                                "Clear",
                                on_click=lambda: universo.set_value([]),
                            ).props("flat dense no-caps size=xs").mark("universe_clear")

                        estrategia = ui.select(
                            {
                                "mean_reversion": "Mean reversion",
                                "momentum_modular": "Momentum (modular)",
                                "dividend_tracking": "Dividend ETFs (core-satellite)",
                                "low_volatility": "Low volatility (sector ETFs)",
                                "static_ew": "Static equal-weight (passive)",
                                "pairs_trading": "Pairs trading (spread z-score)",
                            },
                            value="static_ew",  # el default que pasa (preset dividendos)
                            label="Strategy (real engine)",
                        ).classes("w-full")
                        ui.label(
                            "Momentum is long-only and can yield zero trades in bearish windows."
                        ).classes("help")

                        def _apply_goal_preset() -> None:
                            """Objetivo con preset -> estrategia real y universo adecuados."""
                            preset = preset_for_goal(
                                objetivo.value,
                                period_months(periodo.value, custom_start.value, custom_end.value),
                            )
                            if preset is None:
                                return
                            strategy_name, preset_universe = preset
                            estrategia.value = strategy_name
                            if not preset_universe:
                                # universo AUTOMÁTICO (goal-aware): el
                                # camino verificado que pasa los gates
                                modo_universo.value = "auto"
                                return
                            modo_universo.value = "manual"
                            disponibles = (
                                {
                                    opt
                                    for grupo in (universo.options or {})
                                    for opt in (grupo if isinstance(grupo, list) else [grupo])
                                }
                                if isinstance(universo.options, dict)
                                else set(universo.options or [])
                            )
                            symbols = [
                                sym
                                for sym in preset_universe
                                if not disponibles or sym in disponibles
                            ]
                            if symbols:
                                # el preset trae su universo curado → modo manual
                                modo_universo.value = "manual"
                                universo.value = symbols

                        objetivo.on_value_change(lambda _e: _apply_goal_preset())
                        # el periodo decide el universo (10 años vs histórico profundo)
                        periodo.on_value_change(lambda _e: _apply_goal_preset())

                        with ui.row().classes("w-full gap-sm no-wrap"):
                            comision = ui.number(
                                "Commission (€/trade)", value=1.0, min=0, step=0.5
                            ).classes("flex-1")
                            slippage = ui.number(
                                "Slippage (%)", value=0.1, min=0, max=10, step=0.05
                            ).classes("flex-1")
                        with ui.row().classes("w-full gap-sm no-wrap"):
                            stop_loss = ui.number(
                                "Stop loss (%)", value=None, min=0, max=50, step=0.5
                            ).classes("flex-1")
                            take_profit = ui.number(
                                "Take profit (%)", value=None, min=0, max=100, step=0.5
                            ).classes("flex-1")
                        with ui.row().classes("w-full gap-sm no-wrap"):
                            custom_start = ui.date("Start date").classes("flex-1")
                            custom_end = ui.date("End date").classes("flex-1")
                        ui.label(
                            "Custom dates apply when 'Custom dates…' is selected above."
                        ).classes("help")
                        custom_start.on_value_change(lambda _e: _apply_goal_preset())
                        custom_end.on_value_change(lambda _e: _apply_goal_preset())

                    async def run_pipeline() -> None:
                        if executor is None:
                            ui.notify("Executor not available.", type="negative")
                            return
                        if not capital.value or capital.value <= 0:
                            ui.notify("Capital must be positive.", type="warning")
                            return
                        if modo_universo.value == "manual":
                            symbols = [str(s).upper() for s in (universo.value or [])]
                            if not symbols:
                                ui.notify(
                                    "Pick symbols under Advanced options or switch to Automatic.",
                                    type="warning",
                                )
                                return
                        else:
                            symbols = None  # la app deriva el universo del corpus
                        start_iso, end_iso = resolve_period(
                            periodo.value,
                            custom_start.value,
                            custom_end.value,
                            data_window(symbols),
                        )
                        request = SwarmRunRequest(
                            capital_initial=Decimal(str(capital.value)),
                            objetivo_inversion=objetivo.value,
                            risk_tolerance=riesgo.value,
                            investment_horizon=horizon_months(start_iso, end_iso),
                            target_monthly_return_eur=(
                                Decimal(str(target.value)) if target.value else None
                            ),
                            market_regime=regime.value,
                            volatility_level=volatilidad.value,
                            backtest_start=start_iso,
                            backtest_end=end_iso,
                            symbols=symbols,
                            exhaustive_universe=modo_universo.value == "auto-all",
                            investor_age=int(edad.value) if edad.value else None,
                            tax_province=provincia.value,
                            strategy=estrategia.value,
                            commission_per_trade=(
                                Decimal(str(comision.value)) if comision.value is not None else None
                            ),
                            slippage_pct=(
                                Decimal(str(slippage.value)) if slippage.value is not None else None
                            ),
                            stop_loss_pct=(
                                Decimal(str(stop_loss.value))
                                if stop_loss.value is not None
                                else None
                            ),
                            take_profit_pct=(
                                Decimal(str(take_profit.value))
                                if take_profit.value is not None
                                else None
                            ),
                        )
                        run_id = f"swarm_{uuid.uuid4().hex[:8]}"
                        reset_view()
                        view["run_id"] = run_id
                        view["version"] = -1
                        run_button.disable()
                        fx("swarmFX.sounds.start()")
                        ui.notify("Pipeline started", icon="play_arrow")
                        asyncio.create_task(_run_pipeline(request, run_id))

                    run_button.on_click(run_pipeline)

                # ── 2 · What is happening + result ───────────────────────
                with ui.column().classes("w-full gap-md"):
                    # Run theater — the page's status headline. One glance
                    # answers "what state am I in?" before any detail.
                    theater_holder = ui.column().classes("w-full gap-0")

                    def render_theater(state: str, title: str, sub: str) -> None:
                        theater_holder.clear()
                        tone = {
                            "idle": "var(--tx2)",
                            "running": "var(--run)",
                            "done": "var(--ok)",
                            "bad": "var(--bad)",
                        }[state]
                        with theater_holder:
                            with (
                                ui.element("div")
                                .classes("panel q-pa-md w-full run-theater")
                                .style(f"border-left:4px solid {tone}")
                            ):
                                ui.label(title).classes("theater-title").style(f"color:{tone}")
                                ui.label(sub).classes("help").style("margin-top:2px;font-size:13px")

                    render_theater(
                        "idle",
                        "Ready when you are.",
                        "Answer the three questions on the left and press Run — "
                        "the whole plan builds in about a second.",
                    )

                    with ui.element("div").classes("panel q-pa-md"):
                        ui.label("2 · WHAT IS HAPPENING").classes("lbl q-mb-xs")
                        ui.label(
                            "Each step runs a real component of the system — the team "
                            "below executes it live. Click any worker or step to see "
                            "exactly what went in and what came out."
                        ).classes("help q-mb-sm")
                        with ui.row().classes("gap-xs wrap q-mb-sm"):
                            for chip in (
                                "10 steps · about a second",
                                "real engine, real fees",
                                "€0 — nothing is bought",
                            ):
                                ui.label(chip).classes("hotkey-hint")
                        office = OfficeScene(on_click=lambda aid: open_details(aid))
                        track = StepTrack(on_click=lambda aid: open_details(aid))

                    result_container = ui.column().classes("w-full gap-md")
                    portfolio_container = ui.column().classes("w-full gap-md")
                    parameters_container = ui.column().classes("w-full gap-md")

                    with ui.expansion("Technical detail", icon="terminal").classes("w-full panel"):
                        log = MissionLog()
                        chart_container = ui.column().classes("w-full")

                    with ui.expansion("History & replay", icon="history").classes("w-full panel"):
                        with ui.row().classes("w-full items-center gap-md no-wrap"):
                            replay_select = ui.select(
                                options=[], with_input=True, label="Past runs"
                            ).classes("flex-1")
                            replay_knob = (
                                ui.knob(
                                    value=0.15,
                                    min=0.05,
                                    max=0.5,
                                    step=0.05,
                                    color="teal",
                                    show_value=True,
                                )
                                .props("size=64px")
                                .tooltip("Replay speed: delay between events (s)")
                            )
                            with ui.column().classes("gap-xs"):

                                async def refresh_history() -> None:
                                    if store is None:
                                        return
                                    if not store.is_initialized:
                                        ui.timer(0.5, refresh_history, once=True)
                                        return
                                    try:
                                        runs = await store.list_runs(limit=30)
                                    except Exception:
                                        logger.exception("Failed to list swarm runs")
                                        return
                                    replay_select.options = [
                                        {
                                            "label": (f"{r['started_at'][:16]} · {r['status']}"),
                                            "value": r["workflow_id"],
                                        }
                                        for r in runs
                                    ]
                                    replay_select.update()
                                    if runs:
                                        view["last_run_id"] = runs[0]["workflow_id"]
                                        replay_last_btn.enable()

                                ui.button(icon="refresh", on_click=refresh_history).props(
                                    "flat round dense color=grey-7 aria-label='Refresh run history'"
                                ).tooltip("Refresh")

                                async def _replay_clicked() -> None:
                                    if replay_select.value:
                                        await replay_run(replay_select.value)
                                    else:
                                        ui.notify("Select a run first.", type="warning")

                                ui.button("Replay", icon="replay").props(
                                    "outline dense color=teal"
                                ).on_click(_replay_clicked)
                        ui.timer(0.1, refresh_history, once=True)

    # ── Details dialog ────────────────────────────────────────────────────
    detail_dialog = ui.dialog().props("full-width")
    with detail_dialog, ui.element("div").classes("panel q-pa-lg w-full"):
        detail_title = ui.label("Step").classes("page-title").style("font-size: 1.1rem")
        ui.separator().classes("q-mb-sm")
        detail_body = ui.column().classes("w-full gap-sm")

    def open_details(agent_id: str) -> None:
        spec = SPEC_BY_AGENT[agent_id]
        agent = view["states"].get(agent_id)
        detail_title.text = f"Step {spec.name}"
        detail_body.clear()
        with detail_body:
            if agent is None:
                ui.label("No data yet.").classes("help")
            else:
                _render_step_visual(agent_id, agent.output_payload)
                if agent.warnings:
                    ui.label(f"⚠ Warnings: {len(agent.warnings)}").classes(
                        "term-line term-warn q-mt-sm"
                    )
                    for warning in agent.warnings[:5]:
                        ui.label(f"• {warning}").classes("term-line term-ts")
                if agent.error:
                    ui.label(f"✖ Error: {agent.error}").classes("term-line term-bad")
                with ui.expansion("Raw data (input & output JSON)").classes("w-full q-mt-sm"):
                    _render_payload("INPUT", agent.input_payload)
                    _render_payload("OUTPUT", agent.output_payload)
        detail_dialog.open()

    # ── State chip / progress / result ────────────────────────────────────

    def update_state(run: Any) -> None:
        if run is None:
            state_chip.classes(remove="running done bad")
            state_text.text = "Ready"
            step_text.text = "Step 0 of 10"
            prog_fill.style("width: 0%")
            prog_fill.classes(remove="full")
            render_theater(
                "idle",
                "Ready when you are.",
                "Answer the three questions on the left and press Run — "
                "the whole plan builds in about a second.",
            )
            return

        states = getattr(run, "agents", None) or view["states"]
        completed = sum(1 for a in states.values() if a.status == "DONE")
        running = any(a.status == "RUNNING" for a in states.values())
        status = getattr(run, "status", "running")

        state_chip.classes(remove="running done bad")
        if status == "running" or running:
            state_chip.classes(add="running")
            state_text.text = "Running…"
            step_text.text = f"Step {min(completed + 1, 10)} of 10"
            running_aid = next((aid for aid, a in states.items() if a.status == "RUNNING"), None)
            running_name = (
                SPEC_BY_AGENT[running_aid].name if running_aid else f"step {completed + 1}"
            )
            # Strip the internal T-codes ("T4.1 Backtest…" → "Backtest…"):
            # the theater speaks plain English only.
            running_name = re.sub(r"^T\d+(?:\.\d+)?\s+", "", running_name)
            render_theater(
                "running",
                f"Working: {running_name}",
                "Nothing is bought or sold — every step's input and output "
                "is recorded and inspectable.",
            )
        elif status == "failed":
            state_chip.classes(add="bad")
            state_text.text = "Failed"
            step_text.text = f"Step {completed + 1} of 10"
            render_theater(
                "bad",
                "Stopped — nothing hidden.",
                "A step reported a problem. Click it on the rail below for "
                "the exact error; nothing was traded.",
            )
        else:
            state_chip.classes(add="done")
            state_text.text = "Completed"
            step_text.text = f"Step {completed} of 10"
            render_theater(
                "done",
                "Done — your honest numbers are below.",
                "Verdict, fees, taxes and the exact portfolio the plan "
                "would hold, all from this one run.",
            )

        prog_fill.style(f"width: {completed * 10}%")
        prog_fill.classes(add="full") if status == "completed" else prog_fill.classes(remove="full")

    def render_portfolio(run: Any) -> None:
        results = getattr(run, "results", None) or {}
        inner = (results.get("backtest_result") or {}).get("backtest_result", {})
        portfolio = extract_portfolio(results)
        trades = inner.get("trades_summary") or []
        portfolio_container.clear()
        if not portfolio["allocations"] and not trades:
            return
        with portfolio_container:
            with ui.element("div").classes("panel q-pa-md w-full"):
                with ui.row().classes("w-full items-center no-wrap q-mb-xs"):
                    ui.label("PORTFOLIO").classes("lbl")
                    ui.element("div").classes("flex-1")
                    ui.button(
                        "Continue on paper →",
                        icon="science",
                        on_click=lambda: ui.navigate.to("/portfolio"),
                    ).props("flat dense no-caps").style("color:var(--ds-teal_deep)").tooltip(
                        "Take this plan to your paper account: real rules, "
                        "imaginary money, nothing to fear."
                    )

                # ── STOCK POSITIONS (IB-style table) ────────────────────
                if trades:
                    try:
                        from collections import Counter

                        per_symbol: dict[str, list] = {}
                        for t in trades:
                            per_symbol.setdefault(t.get("symbol", "?"), []).append(t)

                        rows = []
                        for sym, sym_trades in sorted(per_symbol.items()):
                            buys = [t for t in sym_trades if t.get("side") == "buy"]
                            sells = [t for t in sym_trades if t.get("side") == "sell"]
                            total_shares = sum(_as_float(t.get("quantity")) for t in buys)
                            avg_price = (
                                sum(
                                    _as_float(t.get("entry_price")) * _as_float(t.get("quantity"))
                                    for t in buys
                                )
                                / max(total_shares, 1)
                                if buys
                                else 0
                            )
                            realized = sum(_as_float(t.get("pnl") or 0) for t in sells)
                            # el motor fuerza el cierre de TODO al final de la
                            # ventana (P&L realizado): el neto debería ser 0;
                            # piernas de venta desparejadas (splits/stops) pueden
                            # dejar residuo — nunca mostrar shares negativos
                            open_shares = max(
                                0.0,
                                total_shares - sum(_as_float(t.get("quantity")) for t in sells),
                            )
                            rows.append(
                                {
                                    "symbol": sym,
                                    "sector": _SECTOR_MAP.get(sym, "Other"),
                                    "buys": len(buys),
                                    "sells": len(sells),
                                    "shares": round(open_shares, 1),
                                    "avg_price": round(avg_price, 2),
                                    "value": round(open_shares * avg_price, 0),
                                    "pnl": round(realized, 2),
                                }
                            )

                        ui.label("STOCK POSITIONS").classes("lbl q-mt-md q-mb-xs")
                        ui.label(f"{len(rows)} stocks · {len(trades)} trades").classes(
                            "help q-mb-sm"
                        )

                        with (
                            ui.row()
                            .classes("w-full no-wrap q-px-sm")
                            .style("border-bottom: 1px solid var(--line)")
                        ):
                            for col, flex in (
                                ("STOCK", "1.2"),
                                ("SECTOR", "1"),
                                ("BUYS", ".5"),
                                ("SELLS", ".5"),
                                ("SHARES", ".7"),
                                ("AVG €", ".8"),
                                ("VALUE €", ".9"),
                                ("P&L €", ".8"),
                            ):
                                ui.label(col).classes("lbl").style(f"flex: {flex}; min-width: 0")

                        for row in rows:
                            with (
                                ui.row()
                                .classes("w-full no-wrap q-px-sm q-py-xs")
                                .style("border-bottom: 1px solid var(--line)")
                            ):
                                ui.label(row["symbol"]).classes("pstep-name").style(
                                    "flex: 1.2; min-width: 0"
                                )
                                ui.label(row["sector"]).classes("help").style(
                                    "flex: 1; min-width: 0"
                                )
                                ui.label(str(row["buys"])).classes("pstep-meta").style("flex: .5")
                                ui.label(str(row["sells"])).classes("pstep-meta").style("flex: .5")
                                ui.label(str(row["shares"])).classes("pstep-meta").style("flex: .7")
                                ui.label(f"€{row['avg_price']}").classes("pstep-meta").style(
                                    "flex: .8"
                                )
                                ui.label(f"€{row['value']:,.0f}").classes("pstep-meta").style(
                                    "flex: .9"
                                )
                                pnl_color = "term-good" if row["pnl"] >= 0 else "term-bad"
                                ui.label(f"€{row['pnl']:,.0f}").classes(
                                    f"term-line {pnl_color}"
                                ).style("flex: .8")

                        sector_totals: dict[str, float] = Counter()
                        for row in rows:
                            sector_totals[row["sector"]] += row["value"]
                        total_sector = sum(sector_totals.values())
                        if total_sector > 0:
                            sector_chart = {
                                "backgroundColor": "transparent",
                                "color": WARM_PALETTE,
                                "tooltip": {"trigger": "item", "formatter": "{b}: €{c} ({d}%)"},
                                "legend": {"bottom": 0, "textStyle": {"color": "#6f6858"}},
                                "series": [
                                    {
                                        "type": "pie",
                                        "radius": ["38%", "65%"],
                                        "center": ["50%", "40%"],
                                        "itemStyle": {
                                            "borderRadius": 6,
                                            "borderColor": "#fffdf6",
                                            "borderWidth": 2,
                                        },
                                        "label": {"color": "#3e3a31", "formatter": "{b}\n{d}%"},
                                        "data": [
                                            {"name": s, "value": round(v, 0)}
                                            for s, v in sector_totals.most_common()
                                        ],
                                        "animationType": "scale",
                                        "animationEasing": "elasticOut",
                                        "animationDuration": 700,
                                    }
                                ],
                            }
                            with ui.row().classes("w-full items-start gap-md no-wrap q-mt-md"):
                                ui.echart(sector_chart).props(
                                    "role=img aria-label='Donut by sector'"
                                ).classes("flex-1").style("min-width: 240px; height: 260px")
                                with ui.column().classes("flex-1 gap-xs").style("min-width: 0"):
                                    ui.label("BY SECTOR").classes("lbl")
                                    for sector, value in sector_totals.most_common():
                                        pct = value / total_sector * 100 if total_sector > 0 else 0
                                        with ui.row().classes("w-full items-center no-wrap gap-sm"):
                                            ui.label(sector).classes("pstep-name")
                                            ui.label(f"€{value:,.0f} ({pct:.0f}%)").classes(
                                                "pstep-meta q-ml-auto"
                                            )
                    except Exception as exc:
                        ui.label(f"⚠ Stock table error: {exc}").classes("term-line term-warn")

                is_real_alloc = portfolio["method"] == "backtest_positions"
                summary_bits = [
                    bit
                    for bit in (
                        str(portfolio["method"] or "").replace("_", " "),
                        (
                            (
                                f"avg exposure · return {_fmt_short(portfolio['expected_return'])}%/yr"
                                if is_real_alloc
                                else f"expected return {_fmt_short(portfolio['expected_return'])}%"
                            )
                            if portfolio["expected_return"] is not None
                            else None
                        ),
                        (
                            f"Sharpe {_fmt_short(portfolio['expected_sharpe'])}"
                            if portfolio["expected_sharpe"] is not None
                            else None
                        ),
                    )
                    if bit
                ]
                if summary_bits:
                    ui.label(" · ".join(summary_bits)).classes("help q-mb-sm")

                equity_chart = build_equity_curve_chart(
                    (
                        (getattr(run, "results", None) or {})
                        .get("backtest_result", {})
                        .get("backtest_result", {})
                        .get("equity_curve", [])
                    )
                )
                if equity_chart is not None:
                    ui.label("PORTFOLIO EVOLUTION").classes("lbl q-mt-sm q-mb-xs")
                    ui.echart(equity_chart).props(
                        "role=img aria-label='Line chart of portfolio value over time'"
                    ).classes("w-full").style("height: 300px")

                with ui.row().classes("w-full items-start gap-md no-wrap"):
                    donut = build_allocation_chart(portfolio["allocations"])
                    if donut is not None:
                        ui.echart(donut).props(
                            "role=img aria-label='Donut chart of portfolio weights'"
                        ).classes("flex-1").style("min-width: 260px; height: 280px")
                    with ui.column().classes("flex-1 gap-xs").style("min-width: 0"):
                        ui.label("HOW YOUR CAPITAL IS SPREAD").classes("lbl")
                        for alloc in portfolio["allocations"][:6]:
                            with ui.row().classes("w-full items-center no-wrap gap-sm"):
                                ui.label(alloc["module"]).classes("pstep-name")
                                ui.label(
                                    f"{alloc['weight']:.1f}% · €{alloc['capital']:,.0f}"
                                ).classes("pstep-meta ok q-ml-auto")
                            if alloc["rationale"]:
                                ui.label(alloc["rationale"]).classes("help")
                if portfolio["risk_applied"] and portfolio["adjusted"]:
                    risk_chart = build_risk_adjustment_chart(portfolio["adjusted"])
                    if risk_chart is not None:
                        ui.label("RISK ADJUSTMENT").classes("lbl q-mt-md q-mb-xs")
                        ui.label(
                            "Weights after adapting to the market regime and "
                            "volatility you selected."
                        ).classes("help q-mb-sm")
                        ui.echart(risk_chart).props(
                            "role=img aria-label='Bar chart comparing base and risk-adjusted weights'"
                        ).classes("w-full").style("height: 240px")
                else:
                    ui.label(
                        "No risk adjustment was needed for the selected market conditions."
                    ).classes("help q-mt-sm")

    def render_parameters_section() -> None:
        """Parameter default & history (30-10, user: "quita el optimizador,
        se tiene que optimizar solo en el backtesting"). The grid search
        now runs INSIDE every backtest (T4.1) and offers to save better
        parameters as the default; this section only shows the saved
        history and lets you restore a previous set."""
        parameters_container.clear()
        with parameters_container:
            with ui.expansion("Parameters — default & history", icon="tune").classes(
                "w-full panel"
            ):
                ui.label(
                    "Every run searches the strategy's parameter grid inside the "
                    "backtest itself and offers to save better ones as the default. "
                    "This is the saved history — restore any previous set."
                ).classes("help q-mb-sm")
                param_history = ui.column().classes("w-full gap-xs")

                async def refresh_param_history() -> None:
                    if store is None:
                        return
                    try:
                        sets = await store.list_param_sets()
                    except Exception:
                        return
                    param_history.clear()
                    if not sets:
                        with param_history:
                            ui.label(
                                "No saved parameter sets yet — the first run that "
                                "finds an improvement will offer to save it."
                            ).classes("help")
                        return
                    with param_history:
                        for entry in sets[:8]:
                            with ui.row().classes("w-full items-center no-wrap gap-sm"):
                                active = "●" if entry["is_active"] else "○"
                                ui.label(active).classes(
                                    "term-good" if entry["is_active"] else "help"
                                )
                                ui.label(f"{entry['strategy']} · {entry['params']}").classes(
                                    "help"
                                ).style("min-width: 0; flex: 1")
                                ui.label(entry["created_at"][:16]).classes("help")
                                if not entry["is_active"]:
                                    restore_btn = ui.button("Restore", icon="history").props(
                                        "flat dense color=teal size=xs"
                                    )

                                    async def _restore(param_set_id: int = entry["id"]) -> None:
                                        if store is None:
                                            return
                                        await store.activate_param_set(param_set_id)
                                        ui.notify("Parameter set restored", type="positive")
                                        await refresh_param_history()

                                    restore_btn.on_click(_restore)

                ui.timer(0.1, refresh_param_history, once=True)

    def render_result(run: Any) -> None:
        results = getattr(run, "results", None) or {}
        metrics = extract_result_metrics(results)
        verdict = metrics.get("verdict") or (run.decision or {}).get("status")
        kind, title, meaning = VERDICTS.get(verdict, ("mid", verdict or "—", ""))

        request = getattr(run, "request", None)
        period = "—"
        universe = "—"
        if request is not None:
            if request.backtest_start and request.backtest_end:
                period = f"{request.backtest_start[:7]} → {request.backtest_end[:7]}"
            context_bits = [
                bit
                for bit in (
                    f"{request.investor_age} yrs" if request.investor_age else None,
                    request.tax_province,
                    "Spanish savings tax applied" if request.tax_province else None,
                )
                if bit
            ]
        else:
            context_bits = []
        # universo REAL del run: el manual, o el derivado del corpus (el
        # request no lo conoce — Automatic se resuelve en T4.1)
        universe_symbols = (
            list(getattr(request, "symbols", None) or []) or metrics.get("symbols") or []
        )
        if universe_symbols:
            universe = f"{len(universe_symbols)} symbols: {', '.join(universe_symbols[:4])}" + (
                "…" if len(universe_symbols) > 4 else ""
            )

        result_container.clear()
        with result_container:
            result_panel = (
                ui.element("div")
                .classes("panel q-pa-md w-full")
                .props("role=region aria-label='Pipeline result'")
            )
            with result_panel:
                ui.label("3 · RESULT").classes("lbl q-mb-sm")
                # The signature moment (direction: calm fintech): the ONE
                # number a novice came for, at headline size, honestly toned.
                ret_hero = _as_float(metrics.get("total_return"))
                if abs(ret_hero) < 0.05:
                    ret_hero = 0.0  # a window with no trades is "0.0%", never "-0.0%"
                hero_tone = {"ok": "var(--ok)", "mid": "var(--warn)", "bad": "var(--bad)"}[kind]
                with ui.row().classes("w-full items-end gap-lg wrap"):
                    with ui.column().classes("gap-xs"):
                        ui.label(f"{ret_hero:+,.1f}%").style(
                            f"font-size:52px;font-weight:800;letter-spacing:-0.02em;"
                            f"line-height:1;color:{hero_tone};"
                            "font-variant-numeric:tabular-nums"
                        )
                        ui.label(f"simulated over {period} · fees and slippage included").classes(
                            "help"
                        )
                    ui.label(title).classes(f"verdict {kind}")
                    ui.label(meaning).classes("page-sub").style("flex:1;min-width:220px")

                with ui.row().classes("w-full q-mt-md gap-sm wrap"):
                    _metric_tile("Sharpe ratio", metrics.get("sharpe"), 0.08)
                    _metric_tile("Max drawdown", metrics.get("drawdown"), 0.16)
                    _metric_tile("Feasibility", metrics.get("feasibility"), 0.24)
                    _metric_tile("Recommended strategy", metrics.get("strategy"), 0.32)
                    _metric_tile("Test period", period, 0.40)
                    _metric_tile("Universe", universe, 0.48)

                if metrics.get("benchmark_symbol") and metrics.get("benchmark_return") is not None:
                    bench = _as_float(metrics.get("benchmark_return"))
                    excess = metrics.get("excess_return")
                    excess_txt = (
                        f" · excess vs market {_as_float(excess):+,.1f}%"
                        if excess is not None
                        else ""
                    )
                    ui.label(
                        f"Market context: {metrics['benchmark_symbol']} buy&hold did "
                        f"{bench:+,.1f}% over the same period{excess_txt}."
                    ).classes("help q-mt-sm")

                if metrics.get("universe_ew") is not None:
                    ew = _as_float(metrics.get("universe_ew"))
                    xs = metrics.get("excess_vs_universe_ew")
                    xs_txt = f" ({_as_float(xs):+,.1f}% vs this strategy)" if xs is not None else ""
                    ui.label(
                        f"Peer benchmark: holding this same universe equal-weight "
                        f"did {ew:+,.1f}%{xs_txt} — the honest passive twin of "
                        "this portfolio."
                    ).classes("help q-mt-xs")

                te = metrics.get("tax_efficiency")
                if isinstance(te, dict) and te.get("all_accumulating"):
                    ui.label(
                        f"Tax note (Spain): all positions are accumulating UCITS — "
                        f"€0 yearly dividend drag; ~{te.get('accumulating_tax_at_exit_pct')}% "
                        f"deferred until you choose to sell."
                    ).classes("help")
                elif isinstance(te, dict) and te.get("avg_portfolio_yield_pct") is not None:
                    ui.label(
                        f"Tax note (Spain): portfolio yield ~{te.get('avg_portfolio_yield_pct')}%/yr. "
                        f"Distribution ETFs pay ~{te.get('distributing_drag_total_pct')}% IRPF drag "
                        f"over the period vs {te.get('accumulating_tax_at_exit_pct')}% deferred "
                        f"for accumulating UCITS — {te.get('recommendation')}."
                    ).classes("help")

                if metrics.get("dividend_tax_drag") is not None:
                    drag = _as_float(metrics.get("dividend_tax_drag"))
                    ui.label(
                        f"Spanish dividend tax drag: ~-{drag:.1f}% estimated IRPF on "
                        f"distributions over the period (net return would be lower)."
                    ).classes("help")

                if context_bits:
                    ui.label(f"Investor: {' · '.join(context_bits)}").classes("help q-mt-sm")

                # ── RELIABILITY (30-10): the fan, not just the path ─────
                inner_bt = (results.get("backtest_result") or {}).get("backtest_result") or {}
                boot = inner_bt.get("bootstrap_analysis")
                if isinstance(boot, dict) and boot.get("bands"):
                    ui.label("Reliability — 1,000 alternative histories").classes(
                        "lbl q-mt-md q-mb-xs"
                    )
                    ui.label(
                        f"We re-shuffled this portfolio's own daily returns "
                        f"({boot.get('n_paths')} times, one-month blocks) — same market, "
                        f"different order of events — to see the range of "
                        f"{boot.get('horizon_years')}-year outcomes."
                    ).classes("help q-mb-xs")
                    with ui.row().classes("w-full gap-lg wrap"):
                        for tile_label, tile_value in (
                            ("Worst 5% ends at", f"{boot.get('final_p05', 0):.2f}×"),
                            ("Median ends at", f"{boot.get('final_p50', 0):.2f}×"),
                            ("Best 5% ends at", f"{boot.get('final_p95', 0):.2f}×"),
                            ("Chance of loss", f"{boot.get('prob_loss', 0) * 100:.0f}%"),
                            ("Worst-5% max fall", f"{boot.get('max_dd_p05', 0) * 100:.0f}%"),
                        ):
                            with ui.column().classes("gap-xs"):
                                ui.label(tile_value).classes("help").style(
                                    "font-size:1.3rem;font-weight:600"
                                )
                                ui.label(tile_label).classes("help")
                    ui.echart(build_fan_chart_option(boot, inner_bt.get("equity_curve"))).props(
                        "role=img aria-label='Fan chart of bootstrap outcome bands with "
                        "the median line and this run path'"
                    ).classes("w-full").style("height: 260px")
                    # the existing MonteCarloValidator finally judges real data
                    from app.backtesting.acceptance.monte_carlo_validator import MonteCarloValidator

                    criterion = MonteCarloValidator().validate(boot.get("p5_return"))
                    ui.label(
                        f"{'✅' if criterion.passed else '⚠️'} Monte Carlo gate: worst-5% "
                        f"return {boot.get('p5_return', 0) * 100:+.1f}% vs "
                        f"{criterion.threshold * 100:.0f}% floor → "
                        f"{'PASS' if criterion.passed else 'below the floor'}"
                    ).classes("help q-mt-xs")

                wd = inner_bt.get("withdrawal_analysis")
                if isinstance(wd, dict):
                    rate = float(wd.get("withdrawal_rate_annual", 0)) * 100
                    ui.label(f"If you lived off it — {rate:.0f}% a year").classes(
                        "lbl q-mt-md q-mb-xs"
                    )
                    ui.label(
                        f"Withdrawing {rate:.0f}% of the starting capital every year for "
                        f"{wd.get('horizon_years')} years, across {boot.get('n_paths', 1000) if isinstance(boot, dict) else 1000} "
                        f"alternative sequences: the money runs out before the end in "
                        f"{float(wd.get('prob_exhausted', 0)) * 100:.0f}% of them; the "
                        f"median path finishes at {float(wd.get('final_p50', 0)):.2f}× "
                        f"and the worst 5% at {float(wd.get('final_p05', 0)):.2f}×."
                    ).classes("help")

                stress = inner_bt.get("stress_analysis")
                if isinstance(stress, dict) and any(v for v in stress.values()):
                    ui.label("Stress test — real crashes, this universe").classes(
                        "lbl q-mt-md q-mb-xs"
                    )
                    for stress_label, info in stress.items():
                        if isinstance(info, dict):
                            ui.label(
                                f"{stress_label}: {float(info.get('max_drawdown', 0)) * 100:+.1f}% "
                                f"worst fall ({float(info.get('total_return', 0)) * 100:+.1f}% "
                                f"over the episode · {info.get('symbols_used')} symbols with data)"
                            ).classes("help")

                # ── The REAL portfolio in this same simulation ──────────
                real_holder = ui.column().classes("w-full")

                async def _load_real_portfolio_card() -> None:
                    start = getattr(request, "backtest_start", None)
                    end = getattr(request, "backtest_end", None)
                    if not start or not end:
                        real_holder.clear()
                        return
                    try:
                        from app.services.portfolio_management.named_portfolios import (
                            open_store,
                            store_path,
                        )

                        if not store_path("live-ibkr").exists():
                            real_holder.clear()
                            return
                        _engine, real_store = open_store("live-ibkr")
                        try:
                            target = await real_store.get_active_target()
                        finally:
                            await _engine.dispose()
                        if not target or not target.holdings:
                            real_holder.clear()
                            return
                        weights = {
                            h.symbol: float(h.weight) for h in target.holdings if h.weight > 0
                        }
                        if not weights:
                            real_holder.clear()
                            return
                        from app.services.backtest_orchestration.reliability import (
                            portfolio_buyhold,
                        )

                        sim = await asyncio.to_thread(
                            portfolio_buyhold, weights, str(start)[:10], str(end)[:10]
                        )
                    except Exception:  # noqa: BLE001 - la tarjeta es best-effort
                        logger.warning("real-portfolio card failed", exc_info=True)
                        real_holder.clear()
                        return
                    if sim is None:
                        real_holder.clear()
                        return
                    real_holder.clear()
                    with real_holder:
                        ui.label("Your real portfolio (live-ibkr), same window").classes(
                            "lbl q-mt-md q-mb-xs"
                        )
                        coverage = float(sim.get("weight_covered", 0)) * 100
                        missing = sim.get("symbols_missing") or []
                        missing_note = (
                            f" · {len(missing)} position(s) lack data for this window and stay out"
                            if missing
                            else ""
                        )
                        ui.label(
                            f"Buy & hold of your real account weights over "
                            f"{sim.get('years')} years: "
                            f"{float(sim.get('total_return', 0)) * 100:+.1f}% "
                            f"({float(sim.get('cagr', 0)) * 100:+.1f}%/yr) · "
                            f"worst fall {float(sim.get('max_drawdown', 0)) * 100:.1f}% · "
                            f"covers {coverage:.0f}% of the portfolio's weight{missing_note}."
                        ).classes("help")

                ui.timer(0.1, _load_real_portfolio_card, once=True)

                if metrics.get("reasons"):
                    ui.label("Why").classes("lbl q-mt-md q-mb-xs")
                    for reason in metrics["reasons"]:
                        ui.label(f"• {reason}").classes("help")
                if metrics.get("next_steps"):
                    ui.label("Next steps").classes("lbl q-mt-md q-mb-xs")
                    for step_item in metrics["next_steps"]:
                        ui.label(f"→ {step_item}").classes("help")

                # A validated run is SENDABLE: named paper portfolio, its own
                # account, managed and rebalanced on the Portfolio page.
                if verdict in ("APPROVED", "CONDITIONAL"):
                    with ui.row().classes("q-mt-md gap-sm wrap"):
                        ui.button(
                            "Send to paper trading…",
                            icon="rocket_launch",
                            on_click=lambda: _send_to_paper_dialog(run, results, request),
                        ).props("unelevated no-caps").classes("run-btn").mark(
                            "send_to_paper"
                        ).tooltip(
                            "Creates a NAMED paper portfolio with these holdings and its "
                            "own starting cash — your other portfolios are untouched."
                        )

                        async def _toggle_saved(r=run) -> None:
                            if store is None:
                                return
                            new_value = not bool(getattr(r, "saved", False))
                            await store.set_saved(r.run_id, new_value)
                            r.saved = new_value  # type: ignore[attr-defined]
                            ui.notify(
                                "Backtest saved ★ — History & Compare → Saved only"
                                if new_value
                                else "Backtest unpinned",
                                type="positive",
                            )

                        ui.button(
                            "★ Save backtest",
                            icon="star",
                            on_click=lambda: _toggle_saved(),
                        ).props("outline no-caps").classes("run-btn").mark("save_backtest").tooltip(
                            "Pin this passing run — History & Compare filters by saved."
                        )

                # In-backtest optimization (30-10): the grid search the run
                # itself performed over this same window and universe.
                opt = results.get("optimization")
                if isinstance(opt, dict):
                    base = opt.get("baseline") or {}
                    best = opt.get("best") or {}
                    line = (
                        f"In-backtest optimization: {opt.get('trials')} parameter "
                        f"combinations tried on this window — Sharpe "
                        f"{_as_float(base.get('sharpe')):.2f} with your current "
                        f"parameters vs {_as_float(best.get('sharpe')):.2f} with the best."
                    )
                    if opt.get("params_changed"):
                        line += " The numbers above already use the best combination."
                    elif opt.get("improved"):
                        line += " Your saved default already IS the best."
                    else:
                        line += " Your current parameters were the best — nothing to change."
                    ui.label(line).classes("help q-mt-sm")

    def _send_to_paper_dialog(run: Any, results: dict, request: Any) -> None:
        from decimal import Decimal as _D

        strat = str(getattr(request, "strategy", "") or "portfolio")
        default_name = f"{strat} · {run.run_id[-6:]}"
        with ui.dialog() as dialog, ui.card().classes("min-w-[520px]"):
            ui.label("Send this portfolio to paper trading").classes("text-h6")
            ui.label(
                "You choose the name and the starting cash. Each paper portfolio "
                "keeps its own account, its own history and its own rebalances — "
                "you can run several side by side."
            ).classes("help")
            name_in = (
                ui.input("Portfolio name", value=default_name).classes("w-full").mark("paper_name")
            )
            cash_in = (
                ui.number(
                    "Starting cash (€)",
                    value=float(getattr(request, "capital_initial", 0) or 100000),
                    min=1000,
                    step=1000,
                )
                .classes("w-full")
                .mark("paper_cash")
            )
            with ui.row().classes("w-full justify-end gap-sm q-mt-md"):
                ui.button("Cancel", on_click=dialog.close).props("flat")

                async def _create() -> None:
                    await _create_paper_portfolio(
                        run, results, request, name_in.value, _D(str(cash_in.value or 100000))
                    )
                    dialog.close()

                ui.button("Create paper portfolio", icon="rocket_launch", on_click=_create).props(
                    "unelevated no-caps"
                ).classes("run-btn").mark("paper_create")
        dialog.open()

    async def _create_paper_portfolio(
        run: Any, results: dict, request: Any, name: str, cash: Decimal
    ) -> None:
        from app.services.portfolio_management.models import ProfileAnswers
        from app.services.portfolio_management.named_portfolios import (
            create_portfolio,
            open_store,
            prepare_store,
        )
        from app.services.portfolio_management.winner_adoption import (
            build_target,
            winner_from_results,
        )

        winner = winner_from_results(getattr(run, "run_id", ""), results)
        if winner is None:
            ui.notify("This run is not adoptable (verdict or validation).", type="warning")
            return
        meta = create_portfolio(
            name,
            source_run_id=str(getattr(run, "run_id", "")),
            strategy_name=str(winner.get("strategy_name") or ""),
            decision_status=str(winner.get("decision_status") or ""),
            initial_cash=cash,
        )
        engine, store = open_store(meta["slug"])
        await prepare_store(engine)
        risk_level = {"BAJO": "conservative", "MEDIO": "medium", "ALTO": "aggressive"}.get(
            str(getattr(request, "risk_tolerance", "") or "").upper(), "medium"
        )
        profile = ProfileAnswers(
            objective=str(getattr(request, "objetivo_inversion", "") or "BALANCED_GROWTH"),
            risk_level=risk_level,
            investor_age=getattr(request, "investor_age", None),
            horizon_months=int(getattr(request, "investment_horizon", 120) or 120),
            tax_province=str(getattr(request, "tax_province", "") or "Madrid"),
        )
        target = build_target(profile, winner)
        await store.save_target(target)
        ui.notify(
            f"Paper portfolio “{meta['name']}” created from the run's holdings "
            f"(your profile's risk rules applied) — €{cash:,.0f} starting cash. "
            "Confirm the buy orders on the next screen to invest it.",
            type="positive",
        )
        # Creating only WRITES the target; the cash is deployed when the owner
        # confirms the orders. Land them on that preview, not a dead end.
        ui.navigate.to(f"/portfolio?portfolio={meta['slug']}&deploy=1")

    # ── View updates ──────────────────────────────────────────────────────

    def refresh_cards() -> None:
        office.update(view["states"])
        if track is not None:
            track.update(view["states"])

    def reset_view() -> None:
        view["states"] = fresh_states()
        view["log_index"] = 0
        view["finished_shown"] = False
        office.update(view["states"])
        if track is not None:
            track.update(view["states"])
        log.clear()
        chart_container.clear()
        result_container.clear()
        portfolio_container.clear()
        parameters_container.clear()
        update_state(None)

    def drain_log(events: list, start: int) -> int:
        index = start
        while index < len(events):
            event = events[index]
            index += 1
            log.append(event.timestamp, event.type, format_log_line(event))
        return index

    def _save_params_dialog(run: RunState) -> None:
        """30-10: the backtest optimized itself and found BETTER
        parameters than the saved default — ask once whether to make
        them the default for future runs of this strategy."""
        opt = (run.results or {}).get("optimization") or {}
        base = opt.get("baseline") or {}
        best = opt.get("best") or {}
        metrics = extract_result_metrics(run.results or {})
        strategy = str(metrics.get("strategy") or getattr(run, "strategy", "") or "")
        with ui.dialog() as dialog, ui.card().classes("min-w-[520px]"):
            ui.label("Better parameters found").classes("text-h6")
            ui.label(
                f"Every backtest now searches its parameter grid internally. On this "
                f"window, {strategy} did better with:"
            ).classes("help")
            ui.label(f"{opt.get('best_params')}").classes("term-good")
            with ui.row().classes("w-full gap-md"):
                ui.label(
                    f"Current → Sharpe {_as_float(base.get('sharpe')):.2f}, "
                    f"return {_as_float(base.get('return_pct')):+,.1f}%"
                ).classes("help")
                ui.label(
                    f"Best → Sharpe {_as_float(best.get('sharpe')):.2f}, "
                    f"return {_as_float(best.get('return_pct')):+,.1f}%"
                ).classes("term-good")
            ui.label(
                "Save them as the default? Future runs of this strategy start from "
                "them (and keep optimizing). The full history stays restorable under "
                "Parameters."
            ).classes("help")
            with ui.row().classes("w-full justify-end gap-sm q-mt-md"):
                ui.button("Keep current", on_click=dialog.close).props("flat no-caps")

                async def _save() -> None:
                    if store is None:
                        ui.notify("Store not available.", type="warning")
                        return
                    await store.save_param_set(
                        strategy=strategy,
                        params=dict(opt.get("best_params") or {}),
                        metrics={
                            "return_pct": str(best.get("return_pct", "")),
                            "sharpe": str(best.get("sharpe", "")),
                            "trades": best.get("trades"),
                        },
                        source="auto-backtest",
                        note=f"run {run.run_id[-8:]}",
                        activate=True,
                    )
                    ui.notify("Saved as default — future runs will use them", type="positive")
                    dialog.close()
                    render_parameters_section()

                ui.button("Save as default", icon="check_circle", on_click=_save).props(
                    "unelevated no-caps"
                ).classes("run-btn").mark("save_params_default")
        dialog.open()

    def on_run_finished(run: RunState) -> None:
        good = run.status == "completed"
        fx("swarmFX.sounds.complete()" if good else "swarmFX.sounds.fail()")
        verdict = (run.decision or {}).get("status")
        ui.notify(
            f"Pipeline {run.status}" + (f" — verdict {verdict}" if verdict else ""),
            type="positive" if good else "negative",
            icon="check_circle" if good else "warning",
        )
        run_button.enable()
        view["last_run_id"] = run.run_id
        replay_last_btn.enable()
        if good:
            render_result(run)
            render_portfolio(run)
            render_parameters_section()
            # in-backtest optimization found better parameters than the
            # saved default → ask ONCE whether to make them the default
            opt = (run.results or {}).get("optimization") or {}
            if opt.get("params_changed"):
                _save_params_dialog(run)
            option = build_duration_chart_option(run.agents)
            chart_container.clear()
            if option is not None:
                with chart_container:
                    ui.label("STEP DURATIONS").classes("lbl q-mt-md q-mb-xs")
                    ui.echart(option).props(
                        "role=img aria-label='Bar chart of step durations'"
                    ).classes("w-full").style("height: 300px")

    def poll() -> None:
        if executor is None:
            return
        run_id = view["run_id"]
        run = executor.get_run(run_id) if run_id else None
        if run is None:
            return
        if run.version == view["version"]:
            return
        view["version"] = run.version
        view["states"] = dict(run.agents)
        refresh_cards()
        update_state(run)
        view["log_index"] = drain_log(run.events, view["log_index"])
        if run.status != "running" and not view["finished_shown"]:
            view["finished_shown"] = True
            update_state(run)
            on_run_finished(run)

    # ── Replay from the store ─────────────────────────────────────────────

    async def replay_run(run_id: str) -> None:
        if store is None:
            ui.notify("Store not available.", type="warning")
            return
        try:
            events = await store.get_run_events(run_id)
        except Exception:
            logger.exception("Failed to load run events")
            ui.notify("Failed to load run events.", type="negative")
            return
        if not events:
            ui.notify("No events for this run.", type="warning")
            return

        view["run_id"] = None  # detach live polling
        reset_view()
        states = fresh_states()
        decision: dict | None = None
        replay_select.disable()
        try:
            for event in events:
                etype = event["type"]
                if etype == "run_completed":
                    decision = (event.get("payload") or {}).get("decision") or decision
                apply_event_to_states(states, event)
                view["states"] = states
                refresh_cards()
                update_state({"agents": states, "status": "running"})
                log.append(event["timestamp"], etype, format_log_line(event))
                fx("swarmFX.sounds.tick()")
                await asyncio.sleep(float(replay_knob.value or 0.15))
        finally:
            replay_select.enable()

        status = "completed" if events[-1]["type"] == "run_completed" else "failed"
        snapshot = _ReplaySnapshot(
            status=status,
            decision=decision,
            agents=states,
            started_at=events[0]["timestamp"],
            finished_at=events[-1]["timestamp"],
        )
        update_state(snapshot)
        if status == "completed":
            # Reconstruir el results completo plegando los outputs persistidos
            # de cada stage (mismas claves que _build_results) para que el
            # resultado Y el portfolio rendericen igual que en vivo.
            stage_keys = [
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
            rebuilt: dict = {}
            for key, agent_id in stage_keys:
                agent_state = states.get(agent_id)
                out = getattr(agent_state, "output_payload", None) if agent_state else None
                if out is not None:
                    rebuilt[key] = out
            if decision and "deployment_decision" not in rebuilt:
                rebuilt["deployment_decision"] = decision
            snapshot.results = rebuilt
            render_result(snapshot)
            render_portfolio(snapshot)
            render_parameters_section()
            fx("swarmFX.sounds.complete()")

    # ── Keyboard shortcuts ────────────────────────────────────────────────

    def handle_key(e) -> None:
        if e.action != "keydown" or "alt" not in (e.modifiers or []):
            return
        if e.key == "r":
            asyncio.create_task(run_pipeline())
        elif e.key == "p":
            if replay_select.value:
                asyncio.create_task(replay_run(replay_select.value))
            else:
                asyncio.create_task(replay_last())

    ui.keyboard(on_key=handle_key)

    async def _run_pipeline(request: SwarmRunRequest, run_id: str) -> None:
        try:
            await executor.run(request, run_id=run_id)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 - notify instead of killing the task silently
            logger.exception("Swarm pipeline crashed")
            ui.notify("Pipeline crashed — see server logs.", type="negative")
            run_button.enable()

    # discreet sound toggle
    with ui.page_sticky(position="bottom-right", x_offset=14, y_offset=14):
        audio_button = (
            ui.button(icon="volume_off")
            .props("flat round dense color=grey-6 aria-label='Toggle sound cues'")
            .tooltip("Sound cues on/off")
        )

        def toggle_audio() -> None:
            on = "volume_up" not in (audio_button.props.get("icon") or "")
            fx(f"swarmFX.setAudio({str(on).lower()})")
            audio_button.props(f"icon={'volume_up' if on else 'volume_off'}")

        audio_button.on_click(toggle_audio)

    update_state(None)
    ui.timer(0.25, poll)
