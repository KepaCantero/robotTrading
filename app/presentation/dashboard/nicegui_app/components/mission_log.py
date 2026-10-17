"""Mission log component: a scrolling feed of swarm execution events."""

from __future__ import annotations

from nicegui import ui

from app.presentation.dashboard.nicegui_app.theme import COLORS

LINE_ICONS: dict[str, tuple[str, str]] = {
    "run_started": ("🚀", COLORS["accent"]),
    "stage_started": ("▶", COLORS["primary"]),
    "stage_completed": ("✅", COLORS["profit"]),
    "stage_failed": ("❌", COLORS["loss"]),
    "stage_skipped": ("⏭", COLORS["neutral"]),
    "achievement_unlocked": ("🏅", "#FFD54F"),
    "run_completed": ("🏁", COLORS["profit"]),
    "run_failed": ("💀", COLORS["loss"]),
}


def log_line_style(event_type: str) -> tuple[str, str]:
    """Return (icon, color) for an event type."""
    return LINE_ICONS.get(event_type, ("•", COLORS["neutral"]))


class MissionLog:
    """Scrollable event feed. Call :meth:`append` per event."""

    def __init__(self, max_lines: int = 400) -> None:
        self.max_lines = max_lines
        with ui.card().classes("w-full q-pa-md"):
            ui.label("Mission Log").classes("text-h6 q-mb-sm")
            self.scroll_area = ui.scroll_area().classes("w-full").style("height: 360px")
            with self.scroll_area:
                self.container = ui.column().classes("w-full gap-xs")

    def append(self, timestamp: str, event_type: str, text: str) -> None:
        icon, color = log_line_style(event_type)
        with self.container:
            with ui.row().classes("no-wrap items-start gap-xs w-full"):
                ui.label(icon).classes("text-caption")
                ui.label(text).classes("text-caption").style(f"color: {color}; white-space: normal")
                clock = timestamp[11:19] if len(timestamp) > 19 else timestamp
                ui.label(clock).classes("text-caption text-grey q-ml-auto").style("flex-shrink: 0")
        self._trim()
        self.scroll_area.scroll_to(percent=100)

    def _trim(self) -> None:
        children = list(self.container)
        for child in children[: max(0, len(children) - self.max_lines)]:
            child.delete()

    def clear(self) -> None:
        self.container.clear()
