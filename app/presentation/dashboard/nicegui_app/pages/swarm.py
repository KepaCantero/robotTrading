"""Swarm Mission Control page.

Launches the real CAPA 2 pipeline (T1.1→T10.1) as a swarm of agents and
shows it live: one card per agent with status, input and output, a mission
log, XP, achievements tied to real outcomes, plus history replay from the
SQLite store.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.agent_card import AgentCard
from app.presentation.dashboard.nicegui_app.components.mission_log import MissionLog
from app.presentation.dashboard.nicegui_app.theme import COLORS
from app.services.agent_swarm.executor import (
    AGENT_SPECS,
    SPEC_BY_AGENT,
    AgentState,
    SwarmRunRequest,
)

if TYPE_CHECKING:
    from app.services.agent_swarm.executor import Capa2PipelineExecutor, RunState
    from app.services.agent_swarm.store import SwarmRunStore

logger = logging.getLogger(__name__)

OBJECTIVES = [
    "MAXIMIZAR_CAPITAL",
    "MAXIMIZAR_DIVIDENDOS",
    "CAPITAL_PRESERVATION",
    "BALANCED_GROWTH",
    "INCOME_GENERATION",
]

MEDAL_DEFS = [
    ("first_launch", "🎖️", "First Launch"),
    ("pipeline_complete", "🏆", "Pipeline 10/10"),
    ("feasibility_pass", "✅", "Feasibility PASS"),
    ("deploy_approved", "🚀", "Deploy APPROVED"),
    ("clean_run", "🧹", "Clean Run"),
]

DECISION_COLORS = {
    "APPROVED": COLORS["profit"],
    "CONDITIONAL": COLORS["warning"],
    "REJECTED": COLORS["loss"],
}

_CSS = """
@keyframes swarm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(33,150,243,.55); }
  50%      { box-shadow: 0 0 0 9px rgba(33,150,243,0); }
}
.swarm-card { transition: border-color .3s, box-shadow .3s, transform .15s; }
.swarm-card:hover { transform: translateY(-2px); }
.swarm-card-running { animation: swarm-pulse 1.1s infinite; }
@keyframes swarm-pop {
  0% { transform: scale(.6); opacity: 0; }
  60% { transform: scale(1.18); }
  100% { transform: scale(1); opacity: 1; }
}
.swarm-pop { animation: swarm-pop .45s ease; display: inline-block; }
.swarm-json {
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11.5px; line-height: 1.45;
  white-space: pre-wrap; word-break: break-word;
  color: #d7e0ea; background: #101522;
  padding: 12px; border-radius: 8px; margin: 0;
  max-height: 420px; overflow: auto;
}
"""


# ── Pure helpers (unit-tested without a UI) ───────────────────────────────────


def format_log_line(event: Any) -> str:
    """Human-readable line for the mission log (AgentEvent or persisted dict)."""
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
        return f"Mission started — capital €{capital} · objective {objective}"
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
        return f"Achievement unlocked: {payload.get('label', '?')}"
    if etype == "run_completed":
        decision = payload.get("decision") or {}
        return (
            f"Mission complete — {payload.get('xp', 0)} XP · decision {decision.get('status', '?')}"
        )
    if etype == "run_failed":
        return f"Mission FAILED — {payload.get('completed', 0)}/10 agents completed"
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


def build_duration_chart_option(states: dict[str, AgentState]) -> dict | None:
    """ECharts horizontal-bar option of per-agent durations, or None if empty."""
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
        "xAxis": {"type": "value", "name": "ms", "axisLabel": {"color": "#aaa"}},
        "yAxis": {
            "type": "category",
            "data": [f"{spec.emoji} {spec.name}" for spec, _ in done],
            "axisLabel": {"color": "#e0e0e0"},
        },
        "series": [
            {
                "type": "bar",
                "data": [
                    {"value": round(agent.duration_ms, 1), "itemStyle": {"color": spec.color}}
                    for spec, agent in done
                ],
                "barMaxWidth": 18,
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
    """Banner-shaped summary reconstructed from replayed events."""

    status: str
    xp: int
    achievements: list = field(default_factory=list)
    decision: dict | None = None
    started_at: str = ""
    finished_at: str = ""
    agents: dict = field(default_factory=dict)


def _render_payload(title: str, payload: Any) -> None:
    with ui.column().classes("w-full gap-xs"):
        ui.label(title).classes("text-subtitle2 text-grey")
        if payload is None:
            ui.label("— waiting —").classes("text-caption text-grey")
        elif isinstance(payload, str):
            ui.html(f'<pre class="swarm-json">{html.escape(payload[:8000])}</pre>').classes(
                "w-full"
            )
        else:
            text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
            ui.html(f'<pre class="swarm-json">{html.escape(text[:16000])}</pre>').classes("w-full")


# ── Page ──────────────────────────────────────────────────────────────────────


def render(
    executor: Capa2PipelineExecutor | None,
    store: SwarmRunStore | None,
) -> None:
    """Render the Agent Swarm Mission Control page."""
    ui.add_css(_CSS)

    view: dict[str, Any] = {
        "run_id": None,
        "version": -1,
        "log_index": 0,
        "finished_shown": False,
        "states": {spec.agent_id: AgentState() for spec in AGENT_SPECS},
    }

    def fresh_states() -> dict[str, AgentState]:
        return {spec.agent_id: AgentState() for spec in AGENT_SPECS}

    cards: dict[str, AgentCard] = {}

    with ui.column().classes("w-full q-pa-lg gap-md"):
        ui.label("Agent Swarm — Mission Control").classes("text-h4")
        ui.label(
            "Launch the real CAPA 2 parametrization pipeline: ten agents "
            "(T1.1 → T10.1) run in sequence — watch what each one executes, "
            "with its input and output. Click any card for details."
        ).classes("text-grey q-mb-sm")

        if executor is None:
            with (
                ui.card()
                .classes("w-full q-pa-md")
                .style(f"border-left: 4px solid {COLORS['warning']}")
            ):
                ui.label("Swarm executor not initialized — reload the dashboard.").classes(
                    "text-subtitle1"
                )

        # ── Launch form ───────────────────────────────────────────────────
        with ui.card().classes("w-full q-pa-md"):
            ui.label("🚀 Launch Mission").classes("text-h6 q-mb-sm")
            capital = ui.number(
                "Capital inicial (€)", value=100_000, min=100, max=10_000_000, step=1000
            )
            objetivo = ui.select(OBJECTIVES, value="MAXIMIZAR_CAPITAL", label="Objetivo").classes(
                "w-full"
            )
            riesgo = ui.select(
                {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}, value="medio", label="Riesgo"
            ).classes("w-full")
            horizonte = ui.number("Horizonte (meses)", value=24, min=1, max=600, step=1)
            target = ui.number("Objetivo mensual (€, opcional)", value=None, min=0, step=50)
            with ui.row().classes("w-full gap-sm no-wrap"):
                regime = ui.select(
                    {"bull": "📈 Bull", "sideways": "↔ Sideways", "bear": "📉 Bear"},
                    value="sideways",
                    label="Mercado",
                ).classes("flex-1")
                volatilidad = ui.select(
                    {"low": "Low", "normal": "Normal", "high": "High"},
                    value="normal",
                    label="Volatilidad",
                ).classes("flex-1")

            async def launch() -> None:
                if executor is None:
                    ui.notify("Executor not available.", type="negative")
                    return
                if not capital.value or capital.value <= 0:
                    ui.notify("Capital must be positive.", type="warning")
                    return
                request = SwarmRunRequest(
                    capital_initial=Decimal(str(capital.value)),
                    objetivo_inversion=objetivo.value,
                    risk_tolerance=riesgo.value,
                    investment_horizon=int(horizonte.value or 24),
                    target_monthly_return_eur=Decimal(str(target.value)) if target.value else None,
                    market_regime=regime.value,
                    volatility_level=volatilidad.value,
                )
                run_id = f"swarm_{uuid.uuid4().hex[:8]}"
                reset_view()
                view["run_id"] = run_id
                view["version"] = -1
                launch_button.disable()
                ui.notify("Mission launched 🚀", icon="rocket_launch")
                asyncio.create_task(_run_mission(request, run_id))

            launch_button = (
                ui.button("Launch Mission", icon="rocket_launch")
                .props("color=primary")
                .classes("w-full q-mt-sm")
                .on_click(launch)
            )

        async def _run_mission(request: SwarmRunRequest, run_id: str) -> None:
            try:
                await executor.run(request, run_id=run_id)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - notify instead of killing the task silently
                logger.exception("Swarm mission crashed")
                ui.notify("Mission crashed — see server logs.", type="negative")
                launch_button.enable()

        # ── Mission banner ────────────────────────────────────────────────
        with ui.card().classes("w-full q-pa-md"):
            with ui.row().classes("w-full items-center no-wrap"):
                banner_status = ui.label("NO MISSION").classes("text-h5 font-bold")
                decision_chip = (
                    ui.element("span")
                    .classes("text-caption font-bold q-px-md q-py-xs hidden")
                    .style("border-radius: 12px")
                )
                banner_xp = (
                    ui.label("0 XP")
                    .classes("text-h5 font-bold q-ml-auto")
                    .style(f"color: {COLORS['accent']}")
                )
            banner_progress = (
                ui.linear_progress(value=0, show_value=False)
                .props("instant-feedback")
                .classes("q-mt-sm")
            )
            with ui.row().classes("w-full q-mt-xs"):
                banner_progress_text = ui.label("0 / 10 stages").classes("text-caption text-grey")
                banner_elapsed = ui.label("").classes("text-caption text-grey q-ml-auto")

        def update_banner(run: Any) -> None:
            if run is None:
                banner_status.text = "NO MISSION"
                banner_status.style(f"color: {COLORS['neutral']}")
                banner_progress.set_value(0)
                banner_progress_text.text = "0 / 10 stages"
                banner_xp.text = "0 XP"
                banner_elapsed.text = ""
                decision_chip.classes(add="hidden")
                return

            states = getattr(run, "agents", None) or view["states"]
            completed = sum(1 for a in states.values() if a.status == "DONE")
            status = getattr(run, "status", "running")

            if status == "running":
                banner_status.text = "MISSION RUNNING"
                banner_status.style(f"color: {COLORS['primary']}")
            elif status == "failed":
                banner_status.text = "MISSION FAILED"
                banner_status.style(f"color: {COLORS['loss']}")
            else:
                banner_status.text = "MISSION COMPLETE"
                banner_status.style(f"color: {COLORS['profit']}")

            banner_progress.set_value(completed / len(AGENT_SPECS))
            banner_progress_text.text = f"{completed} / {len(AGENT_SPECS)} stages"
            banner_xp.text = f"{getattr(run, 'xp', 0)} XP"

            started = _parse_ts(getattr(run, "started_at", None))
            finished = _parse_ts(getattr(run, "finished_at", None))
            if started is not None:
                end = finished or datetime.utcnow()
                seconds = max(0, int((end - started).total_seconds()))
                banner_elapsed.text = f"{seconds // 60:02d}:{seconds % 60:02d}"

            decision = getattr(run, "decision", None)
            if isinstance(decision, dict) and decision.get("status"):
                color = DECISION_COLORS.get(decision["status"], COLORS["neutral"])
                decision_chip.classes(remove="hidden")
                decision_chip.text = (
                    f"{decision['status']} · {decision.get('confidence_level', '')}"
                )
                decision_chip.style(
                    f"border-radius: 12px; border: 1px solid {color}; color: {color}"
                )
            else:
                decision_chip.classes(add="hidden")

        # ── Achievements ──────────────────────────────────────────────────
        medals: dict[str, ui.element] = {}
        with ui.row().classes("w-full gap-sm wrap"):
            ui.label("🏅 Achievements").classes("text-subtitle1 q-mr-sm self-center")
            for ach_id, emoji, label in MEDAL_DEFS:
                chip = (
                    ui.element("span")
                    .classes("text-caption q-px-sm q-py-xs")
                    .style(
                        "border-radius: 12px; border: 1px dashed #666; "
                        "color: #777; transition: all .4s"
                    )
                    .tooltip(f"Achievement: {label}")
                )
                with chip:
                    ui.label(f"{emoji} {label}").classes("text-caption")
                medals[ach_id] = chip

        def unlock_medals(achievements: list) -> None:
            for entry in achievements:
                ach_id = entry if isinstance(entry, str) else entry.get("id")
                chip = medals.get(ach_id)
                if chip is not None:
                    chip.style(
                        "border-radius: 12px; border: 1px solid #FFD54F; "
                        "color: #FFD54F; background: rgba(255,213,79,.12)"
                    )
                    chip.classes(add="swarm-pop")

        def reset_medals() -> None:
            for chip in medals.values():
                chip.style("border-radius: 12px; border: 1px dashed #666; color: #777")
                chip.classes(remove="swarm-pop")

        # ── Agents grid + mission log ─────────────────────────────────────
        with ui.row().classes("w-full items-start gap-md no-wrap"):
            with ui.column().classes("flex-1 gap-sm"):
                ui.label("Agents").classes("text-h6")
                with ui.row().classes("w-full gap-sm wrap"):
                    for spec in AGENT_SPECS:
                        cards[spec.agent_id] = AgentCard(
                            spec, on_click=lambda aid: open_details(aid)
                        )
            log = MissionLog()

        # ── Completion chart ──────────────────────────────────────────────
        chart_container = ui.column().classes("w-full")

        # ── History ───────────────────────────────────────────────────────
        with ui.card().classes("w-full q-pa-md"):
            with ui.row().classes("w-full items-center gap-md no-wrap"):
                ui.label("📜 Mission History").classes("text-h6")
                replay_select = (
                    ui.select(options=[], with_input=True, label="Past runs")
                    .classes("flex-1")
                    .style("min-width: 280px")
                )

                async def refresh_history() -> None:
                    if store is None or not store.is_initialized:
                        return
                    try:
                        runs = await store.list_runs(limit=30)
                    except Exception:
                        logger.exception("Failed to list swarm runs")
                        return
                    replay_select.options = [
                        {
                            "label": (
                                f"{r['started_at'][:16]} · {r['status']} · {r['total_xp']} XP"
                            ),
                            "value": r["workflow_id"],
                        }
                        for r in runs
                    ]
                    replay_select.update()

                ui.button(icon="refresh", on_click=refresh_history).props("flat round").tooltip(
                    "Refresh history"
                )

                async def _replay_clicked() -> None:
                    if replay_select.value:
                        await replay_run(replay_select.value)
                    else:
                        ui.notify("Select a run first.", type="warning")

                ui.button("Replay", icon="play_arrow").props("outline").on_click(_replay_clicked)
            ui.timer(0.1, refresh_history, once=True)

    # ── Details dialog ────────────────────────────────────────────────────
    detail_dialog = ui.dialog().props("full-width")
    with detail_dialog, ui.card().classes("w-full"):
        detail_title = ui.label("Agent").classes("text-h6")
        ui.separator().classes("q-mb-sm")
        detail_body = ui.column().classes("w-full gap-sm")

    def open_details(agent_id: str) -> None:
        spec = SPEC_BY_AGENT[agent_id]
        agent = view["states"].get(agent_id)
        detail_title.text = f"{spec.emoji} {spec.name}"
        detail_body.clear()
        with detail_body:
            if agent is None:
                ui.label("No data yet.").classes("text-grey")
            else:
                _render_payload("Input", agent.input_payload)
                _render_payload("Output", agent.output_payload)
                if agent.warnings:
                    ui.label(f"⚠ Warnings: {len(agent.warnings)}").classes("text-caption").style(
                        f"color: {COLORS['warning']}"
                    )
                    for warning in agent.warnings[:5]:
                        ui.label(f"• {warning}").classes("text-caption text-grey")
                if agent.error:
                    ui.label(f"✖ Error: {agent.error}").classes("text-caption").style(
                        f"color: {COLORS['loss']}"
                    )
        detail_dialog.open()

    # ── Live polling / view updates ───────────────────────────────────────

    def refresh_cards() -> None:
        for spec in AGENT_SPECS:
            cards[spec.agent_id].update(view["states"][spec.agent_id])

    def reset_view() -> None:
        view["states"] = fresh_states()
        view["log_index"] = 0
        view["finished_shown"] = False
        for card in cards.values():
            card.update(None)
        log.clear()
        reset_medals()
        chart_container.clear()
        update_banner(None)

    def drain_log(events: list, start: int) -> int:
        index = start
        while index < len(events):
            event = events[index]
            index += 1
            log.append(event.timestamp, event.type, format_log_line(event))
        return index

    def on_run_finished(run: RunState) -> None:
        good = run.status == "completed"
        ui.notify(
            f"Mission {run.status} — {run.xp} XP"
            + (f" · decision {run.decision['status']}" if run.decision else ""),
            type="positive" if good else "negative",
            icon="emoji_events" if good else "warning",
        )
        launch_button.enable()
        option = build_duration_chart_option(run.agents)
        chart_container.clear()
        if option is not None:
            with chart_container:
                with ui.card().classes("w-full q-pa-md"):
                    ui.label("Stage durations").classes("text-h6 q-mb-sm")
                    ui.echart(option).classes("w-full").style("height: 320px")

    def poll() -> None:
        if executor is None:
            return
        run_id = view["run_id"]
        run = executor.get_run(run_id) if run_id else None
        if run is None:
            return
        if run.status == "running":
            update_banner(run)
        if run.version == view["version"]:
            return
        view["version"] = run.version
        view["states"] = dict(run.agents)
        refresh_cards()
        view["log_index"] = drain_log(run.events, view["log_index"])
        unlock_medals(run.achievements)
        if run.status != "running" and not view["finished_shown"]:
            view["finished_shown"] = True
            update_banner(run)
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
        achievements: list[dict] = []
        xp = 0
        decision: dict | None = None
        replay_select.disable()
        try:
            for event in events:
                etype = event["type"]
                if etype == "achievement_unlocked":
                    achievements.append(event.get("payload") or {})
                elif etype == "run_completed":
                    xp = (event.get("payload") or {}).get("xp", 0)
                    decision = (event.get("payload") or {}).get("decision") or decision
                apply_event_to_states(states, event)
                view["states"] = states
                refresh_cards()
                log.append(event["timestamp"], etype, format_log_line(event))
                await asyncio.sleep(0.15)
        finally:
            replay_select.enable()

        unlock_medals(achievements)
        status = "completed" if events[-1]["type"] == "run_completed" else "failed"
        update_banner(
            _ReplaySnapshot(
                status=status,
                xp=xp,
                achievements=achievements,
                decision=decision,
                started_at=events[0]["timestamp"],
                finished_at=events[-1]["timestamp"],
                agents=states,
            )
        )
        chart_container.clear()
        option = build_duration_chart_option(states)
        if option is not None:
            with chart_container:
                with ui.card().classes("w-full q-pa-md"):
                    ui.label("Stage durations (replayed)").classes("text-h6 q-mb-sm")
                    ui.echart(option).classes("w-full").style("height: 320px")

    update_banner(None)
    ui.timer(0.25, poll)
