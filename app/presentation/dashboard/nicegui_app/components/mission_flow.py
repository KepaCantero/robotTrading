"""MissionFlow — the live pipeline strip (theme v2, owner 31-10).

Replaces the office-scene + plain rail ('lo veo aburrido'): one strip
that MOVES — a status ticker with a progress ring and a live elapsed
timer, a shimmer progress bar, and a metro rail whose stations check
off, ping while running and whose connectors FLOW towards the active
step. Sober fintech palette (teal/sage/honey/terracotta), no gamified
wording, every animation off under prefers-reduced-motion.

Keeps the old StepTrack DOM contract (classes ``pnode``/``t-connector``,
markers ``step_node_*``, the NOW panel's role=status and its idle copy)
so existing tests and muscle memory keep working.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from nicegui import ui

from app.presentation.dashboard.nicegui_app.components.agent_card import step_title
from app.services.agent_swarm.executor import AGENT_SPECS

CSS = """
<style>
.mf-ticker {
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 16px 20px; box-shadow: var(--shadow-1);
  transition: border-color .3s ease, background .3s ease;
}
.mf-ticker[data-state="running"] { border-color: color-mix(in srgb, var(--run) 40%, var(--line)); }
.mf-ticker[data-state="done"]    { border-color: color-mix(in srgb, var(--ok) 35%, var(--line)); }
.mf-ticker[data-state="bad"]     { border-color: color-mix(in srgb, var(--bad) 40%, var(--line)); }
.mf-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--tx3); flex: none; }
.mf-ticker[data-state="running"] .mf-dot {
  background: var(--run); box-shadow: 0 0 0 0 color-mix(in srgb, var(--run) 45%, transparent);
  animation: mf-ping 1.4s cubic-bezier(.4,0,.6,1) infinite;
}
.mf-ticker[data-state="done"] .mf-dot { background: var(--ok); }
.mf-ticker[data-state="bad"] .mf-dot { background: var(--bad); }
.mf-title { font-size: 1.15rem; font-weight: 650; letter-spacing: .1px; }
.mf-ring {
  --p: 0; width: 74px; height: 74px; border-radius: 50%; flex: none; position: relative;
  display: flex; align-items: center; justify-content: center;
  background: conic-gradient(var(--run) calc(var(--p) * 1%), var(--line) 0);
  transition: background .5s ease;
}
.mf-ring::before { content: ""; position: absolute; inset: 6px; border-radius: 50%;
  background: var(--card); }
.mf-ring-pct { position: relative; font-size: .95rem; font-weight: 700; color: var(--run-deep); }
.mf-elapsed { font-variant-numeric: tabular-nums; color: var(--tx2); font-size: .85rem; }

.mf-bar { height: 6px; border-radius: 4px; background: var(--line); overflow: hidden;
  margin: 12px 2px 18px 2px; }
.mf-bar-fill { height: 100%; width: 0%; border-radius: 4px;
  background: linear-gradient(90deg, var(--run), color-mix(in srgb, var(--run) 55%, var(--ok)));
  background-size: 200% 100%; transition: width .45s ease; }
.mf-bar-fill.is-running { animation: mf-shimmer 1.6s linear infinite; }

/* ── metro rail (overrides the base pnode look on this page) ── */
.mf-rail { overflow-x: auto; padding: 8px 2px 14px 2px; }
.pnode {
  width: 46px; height: 46px; border-radius: 50%; position: relative; flex: none;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  border: 2px solid var(--line-hi); background: var(--card); color: var(--tx2);
  font-size: .95rem; font-weight: 600; box-shadow: var(--shadow-1);
  transition: transform .18s ease, border-color .25s ease, background .25s ease, color .25s ease;
}
.pnode:hover { transform: translateY(-3px) scale(1.06); }
.pnode.n-idle { color: var(--tx3); }
.pnode.n-done { border-color: var(--ok); background: var(--ok); color: #fffdf6;
  animation: mf-pop .3s cubic-bezier(.3,1.6,.5,1); }
.pnode.n-running { border-color: var(--run); color: var(--run-deep); font-weight: 700;
  animation: mf-breathe 1.8s ease-in-out infinite; }
.pnode.n-running::after { content: ""; position: absolute; inset: -7px; border-radius: 50%;
  border: 2px solid color-mix(in srgb, var(--run) 55%, transparent);
  animation: mf-ping 1.4s cubic-bezier(.4,0,.6,1) infinite; }
.pnode.n-failed { border-color: var(--bad); background: var(--bad); color: #fffdf6; }
.pnode.n-skipped { opacity: .35; }

.t-connector { flex: 1 1 0; min-width: 14px; height: 4px; border-radius: 3px;
  background: var(--line); position: relative; overflow: hidden;
  transition: background .3s ease; }
.t-connector.filled { background: color-mix(in srgb, var(--ok) 65%, var(--run)); }
.t-connector.flow {
  background: repeating-linear-gradient(90deg,
    color-mix(in srgb, var(--run) 75%, transparent) 0 8px, var(--line) 8px 16px);
  background-size: 16px 100%; animation: mf-flow .5s linear infinite; }

@keyframes mf-ping { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--run) 45%, transparent); }
  70%,100% { box-shadow: 0 0 0 12px transparent; } }
@keyframes mf-shimmer { 0% { background-position: 0% 0; } 100% { background-position: -200% 0; } }
@keyframes mf-flow { 0% { background-position: 0 0; } 100% { background-position: 16px 0; } }
@keyframes mf-pop { 0% { transform: scale(.7); } 100% { transform: scale(1); } }
@keyframes mf-breathe { 0%,100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--run) 30%, transparent); }
  50% { box-shadow: 0 0 0 7px transparent; } }
@media (prefers-reduced-motion: reduce) {
  .pnode, .pnode.n-running, .pnode.n-running::after, .pnode.n-done,
  .t-connector.flow, .mf-bar-fill.is-running, .mf-dot { animation: none !important; }
}
</style>
"""


class MissionFlow:
    """The live pipeline strip — one glance answers 'where are we?'."""

    def __init__(self, on_click: Callable[[str], None]) -> None:
        ui.add_head_html(CSS)
        self._t0: float | None = None

        # ── status ticker (keeps the NOW panel contract) ────────────
        self.panel = ui.element("div").classes("mf-ticker w-full")
        self.panel.props("role=status aria-live=polite data-state=none")
        with self.panel:
            ui.element("span").classes("mf-dot")
            with ui.column().classes("gap-0 flex-1").style("min-width: 200px"):
                self.now_title = ui.label("Ready to start").classes("mf-title")
                self.now_desc = ui.label(
                    "Press Run my backtest — the team will get to work."
                ).classes("help")
            with ui.column().classes("items-end gap-xxs").style("flex:none"):
                self.ring = ui.element("div").classes("mf-ring").props("aria-hidden=true")
                with self.ring:
                    self.ring_pct = ui.label("0%").classes("mf-ring-pct")
                self.elapsed = ui.label("").classes("mf-elapsed")

        # ── shimmer progress bar ────────────────────────────────────
        self.bar = ui.element("div").classes("mf-bar")
        with self.bar:
            self.bar_fill = ui.element("div").classes("mf-bar-fill")

        # ── metro rail ──────────────────────────────────────────────
        self.nodes: dict[str, ui.element] = {}
        self.numbers: dict[str, ui.label] = {}
        self.connectors: list[ui.element] = []
        with ui.element("div").classes("mf-rail w-full"):
            with ui.row().classes("track-row w-full items-center no-wrap"):
                for index, spec in enumerate(AGENT_SPECS, start=1):
                    title, desc = step_title(spec.agent_id)
                    node = (
                        ui.element("div")
                        .classes("pnode n-idle")
                        .mark(f"step_node_{spec.agent_id}")
                        .props(f'tabindex=0 role=button aria-label="Step {index}: {title}"')
                        .tooltip(f"{index} · {title} — {desc}")
                        .on("click", lambda _, aid=spec.agent_id: on_click(aid))
                        .on("keyup.enter", lambda _, aid=spec.agent_id: on_click(aid))
                        .on("keyup.space", lambda _, aid=spec.agent_id: on_click(aid))
                    )
                    with node:
                        self.numbers[spec.agent_id] = ui.label(str(index)).classes("pnode-num")
                    self.nodes[spec.agent_id] = node
                    if index < len(AGENT_SPECS):
                        connector = (
                            ui.element("div").classes("t-connector").props("aria-hidden=true")
                        )
                        self.connectors.append(connector)

        ui.timer(1.0, self._tick_elapsed)

    # ── updates ─────────────────────────────────────────────────────
    def update(self, states: dict) -> None:
        """Refresh ticker, ring, bar and rail from AgentStates."""
        statuses = {
            spec.agent_id: getattr(states.get(spec.agent_id), "status", "IDLE")
            for spec in AGENT_SPECS
        }
        for spec in AGENT_SPECS:
            status = statuses[spec.agent_id]
            node = self.nodes.get(spec.agent_id)
            if node is None:
                continue
            node.classes(remove="n-idle n-running n-done n-failed n-skipped")
            node.classes(add=f"n-{status.lower()}")
            index = AGENT_SPECS.index(spec) + 1
            title, _ = step_title(spec.agent_id)
            node.props(f'aria-label="Step {index}: {title} — {status.lower()}"')
            # done stations check off; anything active/idle shows its number
            self.numbers[spec.agent_id].set_text("✓" if status == "DONE" else str(index))

        running = any(s == "RUNNING" for s in statuses.values())
        failed = any(s == "FAILED" for s in statuses.values())

        # a connector FILLS when its step finished, and FLOWS while the
        # pipeline is moving towards the next one
        for i, connector in enumerate(self.connectors):
            previous = statuses[AGENT_SPECS[i].agent_id]
            nxt = statuses[AGENT_SPECS[i + 1].agent_id] if i + 1 < len(AGENT_SPECS) else "IDLE"
            connector.classes(remove="filled flow")
            if previous in {"DONE", "FAILED"}:
                if running and nxt in {"IDLE", "RUNNING"}:
                    connector.classes(add="flow")
                else:
                    connector.classes(add="filled")

        done = sum(1 for s in statuses.values() if s == "DONE")
        pct = int(round(done / len(AGENT_SPECS) * 100))
        self.ring.style(f"--p: {pct}")
        self.ring_pct.set_text(f"{pct}%")
        self.bar_fill.style(f"width: {pct}%")
        if running:
            self.bar_fill.classes(add="is-running")
        else:
            self.bar_fill.classes(remove="is-running")

        if running and self._t0 is None:
            self._t0 = time.monotonic()
        if not running and not failed:
            self._t0 = None
            self.elapsed.set_text("")
        elif not running and failed:
            self._t0 = None

        self._update_now_panel(statuses, states)

    def _tick_elapsed(self) -> None:
        if self._t0 is not None:
            seconds = int(time.monotonic() - self._t0)
            self.elapsed.set_text(f"⏱ {seconds // 60}:{seconds % 60:02d}")

    def _update_now_panel(self, statuses: dict, states: dict) -> None:
        active = next((s for s in AGENT_SPECS if statuses[s.agent_id] == "RUNNING"), None)
        failed = next((s for s in AGENT_SPECS if statuses[s.agent_id] == "FAILED"), None)
        done = [s for s in AGENT_SPECS if statuses[s.agent_id] == "DONE"]

        if active is not None:
            index = AGENT_SPECS.index(active) + 1
            title, desc = step_title(active.agent_id)
            self._set_now("running", f"{index} · {title}", desc)
        elif failed is not None:
            index = AGENT_SPECS.index(failed) + 1
            title, _ = step_title(failed.agent_id)
            self._set_now(
                "bad",
                f"Stopped at {index} · {title}",
                "This step failed — click it to see the error.",
            )
        elif done:
            last = done[-1]
            index = AGENT_SPECS.index(last) + 1
            title, desc = step_title(last.agent_id)
            agent: Any = states.get(last.agent_id)
            duration = getattr(agent, "duration_ms", 0) or 0
            timing = f"{duration:.0f} ms" if duration >= 1 else "<1 ms"
            self._set_now("done", f"Completed · {index} · {title}", f"{desc} — {timing}")
        else:
            self._set_now(
                "", "Ready to start", "Press Run my backtest — the team will get to work."
            )

    def _set_now(self, state: str, title: str, desc: str) -> None:
        self.panel.props(f"data-state={state}" if state else "data-state=none")
        self.now_title.set_text(title)
        self.now_desc.set_text(desc)
