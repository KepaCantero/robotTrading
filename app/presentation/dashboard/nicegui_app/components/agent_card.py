"""Agent card component for the Swarm Mission Control page.

One card per CAPA 2 component (T1.1-T10.1): avatar, name, status chip,
duration, XP. The card pulses while the agent runs, flashes when it
completes, and opens a details dialog (input/output JSON) on click.
"""

from __future__ import annotations

from typing import Any, Callable

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS

STATUS_STYLES: dict[str, dict[str, str]] = {
    "IDLE": {"label": "IDLE", "color": "#9E9E9E", "bg": "rgba(158,158,158,.15)"},
    "RUNNING": {"label": "RUNNING", "color": COLORS["primary"], "bg": "rgba(33,150,243,.18)"},
    "DONE": {"label": "DONE", "color": COLORS["profit"], "bg": "rgba(76,175,80,.15)"},
    "FAILED": {"label": "FAILED", "color": COLORS["loss"], "bg": "rgba(244,67,54,.15)"},
    "SKIPPED": {"label": "SKIPPED", "color": "#9E9E9E", "bg": "rgba(158,158,158,.08)"},
}


def status_style(status: str) -> dict[str, str]:
    return STATUS_STYLES.get(status, STATUS_STYLES["IDLE"])


class AgentCard:
    """Live card for one swarm agent, updated via :meth:`update`."""

    def __init__(self, spec, on_click: Callable[[str], None]) -> None:
        self.spec = spec
        self.agent: Any = None

        with (
            ui.card()
            .classes("swarm-card q-pa-md cursor-pointer")
            .style(f"border-left: 4px solid {spec.color}; border-radius: 10px; min-height: 118px")
            .on("click", lambda: on_click(spec.agent_id))
        ):
            self.card = ui.element("div")
            with ui.row().classes("w-full items-center no-wrap gap-sm"):
                ui.label(spec.emoji).classes("text-h5").style("font-size: 1.7rem")
                with ui.column().classes("gap-0 flex-1"):
                    ui.label(spec.name).classes("text-subtitle1 font-bold")
                    ui.label(spec.description).classes("text-caption text-grey").style(
                        "white-space: normal"
                    )

            with ui.row().classes("w-full items-center q-mt-sm no-wrap"):
                self.status_chip = (
                    ui.element("span")
                    .classes("text-caption font-bold q-px-sm q-py-xs")
                    .style("border-radius: 10px")
                )
                self.spinner = ui.spinner(size="sm", color="primary").classes("hidden")
                self.duration_label = ui.label("").classes("text-caption text-grey q-ml-auto")
            self.xp_label = ui.label("").classes("text-caption").style(f"color: {COLORS['accent']}")

        self.update(None)

    def update(self, agent: Any) -> None:
        """Refresh the card from an AgentState (or reset to IDLE on None)."""
        self.agent = agent
        status = getattr(agent, "status", "IDLE")
        style = status_style(status)

        self.status_chip.text = style["label"]
        self.status_chip.style(
            f"color: {style['color']}; background: {style['bg']}; border: 1px solid {style['color']}"
        )
        self.card.style(
            f"border-left: 4px solid {self.spec.color if status != 'FAILED' else COLORS['loss']}"
        )

        if status == "RUNNING":
            self.spinner.classes(remove="hidden")
            self.card.classes(add="swarm-card-running")
        else:
            self.spinner.classes(add="hidden")
            self.card.classes(remove="swarm-card-running")

        duration_ms = getattr(agent, "duration_ms", 0) or 0
        if status in {"DONE", "FAILED"} and duration_ms:
            self.duration_label.text = f"{duration_ms:.0f} ms"
        elif status == "RUNNING":
            self.duration_label.text = "…"
        else:
            self.duration_label.text = ""

        error = getattr(agent, "error", None)
        if error:
            self.xp_label.text = f"⚠ {error[:60]}"
            self.xp_label.style(f"color: {COLORS['loss']}")
        elif getattr(agent, "xp", 0):
            self.xp_label.text = f"+{agent.xp} XP"
            self.xp_label.style(f"color: {COLORS['accent']}")
        else:
            self.xp_label.text = ""

        if status == "DONE":
            self.status_chip.classes(add="swarm-pop")
