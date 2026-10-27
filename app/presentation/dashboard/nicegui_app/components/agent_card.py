"""Pipeline step track for the Agent Swarm page.

Replaces the old step list with a visual progress rail: ten numbered
nodes joined by connectors that fill as steps complete, the active node
pulsing, plus a "NOW" narration panel showing what the pipeline is doing
at this moment. Every node opens the step details dialog on click.
"""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from app.services.agent_swarm.executor import AGENT_SPECS

# Plain-English, novice-friendly presentation of each pipeline stage
STEP_TITLES: dict[str, tuple[str, str]] = {
    "t11": ("Check your inputs", "Makes sure capital, goal and time frame make sense"),
    "t21": ("Build your profile", "Classifies your capital and picks which modules to enable"),
    "t31": ("Tune the modules", "Sets each module's parameters to match your profile"),
    "t41": ("Simulate the strategy", "Backtest: runs the portfolio over the selected test period"),
    "t51": ("Validate the result", "Checks costs, capital and feasibility gates"),
    "t61": ("Pick the best strategy", "Scores the strategies and recommends the best fit"),
    "t71": ("Allocate capital", "Works out how much to invest in each module"),
    "t81": ("Adjust risk", "Adapts positions to market regime and volatility"),
    "t91": ("Generate the report", "Summarises strengths and weaknesses"),
    "t101": ("Decide", "Approved, conditional or rejected"),
}


def step_title(agent_id: str) -> tuple[str, str]:
    fallback = next((spec.name for spec in AGENT_SPECS if spec.agent_id == agent_id), "Step")
    return STEP_TITLES.get(agent_id, (fallback, ""))


class StepTrack:
    """Visual progress rail for the ten steps, updated via :meth:`update`."""

    def __init__(self, on_click: Callable[[str], None]) -> None:
        # ── NOW narration panel ──────────────────────────────────────────
        self.panel = ui.element("div").classes("now-panel w-full")
        self.panel.props("role=status aria-live=polite")
        with self.panel:
            with ui.row().classes("w-full items-center no-wrap gap-md"):
                ui.element("span").classes("now-dot")
                with ui.column().classes("gap-0 flex-1").style("min-width: 0"):
                    self.now_title = ui.label("Ready to start").classes("now-title")
                    self.now_desc = ui.label(
                        "Press Run my backtest — the team will get to work."
                    ).classes("help")
                self.now_meta = ui.label("").classes("pstep-meta")

        # ── node rail ─────────────────────────────────────────────────────
        self.nodes: dict[str, ui.element] = {}
        self.connectors: list[ui.element] = []
        with ui.element("div").classes("track-wrap w-full"):
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
                        ui.label(str(index)).classes("pnode-num")
                    self.nodes[spec.agent_id] = node
                    if index < len(AGENT_SPECS):
                        connector = (
                            ui.element("div").classes("t-connector").props("aria-hidden=true")
                        )
                        self.connectors.append(connector)

    def update(self, states: dict) -> None:
        """Refresh nodes, connectors and the NOW panel from AgentStates."""
        statuses = {
            spec.agent_id: getattr(states.get(spec.agent_id), "status", "IDLE")
            for spec in AGENT_SPECS
        }
        for spec, status in zip(AGENT_SPECS, statuses.values()):
            node = self.nodes.get(spec.agent_id)
            if node is not None:
                node.classes(remove="n-idle n-running n-done n-failed n-skipped")
                node.classes(add=f"n-{status.lower()}")
                index = AGENT_SPECS.index(spec) + 1
                title, _ = step_title(spec.agent_id)
                node.props(f'aria-label="Step {index}: {title} — {status.lower()}"')

        # a connector fills when the step before it has finished (done or failed)
        for index, connector in enumerate(self.connectors):
            previous_status = statuses[AGENT_SPECS[index].agent_id]
            if previous_status in {"DONE", "FAILED"}:
                connector.classes(add="filled")
            else:
                connector.classes(remove="filled")

        self._update_now_panel(statuses, states)

    def _update_now_panel(self, statuses: dict, states: dict) -> None:
        active = next((spec for spec in AGENT_SPECS if statuses[spec.agent_id] == "RUNNING"), None)
        failed = next((spec for spec in AGENT_SPECS if statuses[spec.agent_id] == "FAILED"), None)
        done = [spec for spec in AGENT_SPECS if statuses[spec.agent_id] == "DONE"]

        if active is not None:
            index = AGENT_SPECS.index(active) + 1
            title, desc = step_title(active.agent_id)
            self._set_now("running", f"{index} · {title}", desc, "···")
        elif failed is not None:
            index = AGENT_SPECS.index(failed) + 1
            title, _ = step_title(failed.agent_id)
            self._set_now(
                "bad",
                f"Stopped at {index} · {title}",
                "This step failed — click it to see the error.",
                "error",
            )
        elif done:
            last = done[-1]
            index = AGENT_SPECS.index(last) + 1
            title, desc = step_title(last.agent_id)
            agent: Any = states.get(last.agent_id)
            duration = getattr(agent, "duration_ms", 0) or 0
            timing = f"{duration:.0f} ms" if duration >= 1 else "<1 ms"
            self._set_now("done", f"Completed · {index} · {title}", desc, timing)
        else:
            self._set_now(
                "",
                "Ready to start",
                "Press Run my backtest — the team will get to work.",
                "",
            )

    def _set_now(self, state: str, title: str, desc: str, meta: str) -> None:
        if state:
            self.panel.props(f"data-state={state}")
        else:
            self.panel.props("data-state=none")
        self.now_title.text = title
        self.now_desc.text = desc
        self.now_meta.text = meta
