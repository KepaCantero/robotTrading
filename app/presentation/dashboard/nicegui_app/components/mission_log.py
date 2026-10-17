"""Mission log component: a phosphor-green mission terminal.

Scrolling feed of swarm execution events styled like a CRT console
(Share Tech Mono, neon glow, blinking caret on the last line).
"""

from __future__ import annotations

from nicegui import ui

LINE_CLASSES: dict[str, str] = {
    "run_started": "term-good",
    "stage_started": "term-info",
    "stage_completed": "term-good",
    "stage_failed": "term-bad",
    "stage_skipped": "term-neutral",
    "achievement_unlocked": "term-warn",
    "run_completed": "term-good",
    "run_failed": "term-bad",
}

LINE_ICONS: dict[str, str] = {
    "run_started": "▶▶",
    "stage_started": "▶",
    "stage_completed": "✔",
    "stage_failed": "✖",
    "stage_skipped": "⏭",
    "achievement_unlocked": "★",
    "run_completed": "◆",
    "run_failed": "✖✖",
}


def log_line_class(event_type: str) -> str:
    return LINE_CLASSES.get(event_type, "term-neutral")


def log_line_icon(event_type: str) -> str:
    return LINE_ICONS.get(event_type, "•")


class MissionLog:
    """Terminal-style event feed. Call :meth:`append` per event."""

    def __init__(self, max_lines: int = 400) -> None:
        self.max_lines = max_lines
        self.last_line: ui.row | None = None
        with ui.element("div").classes("panel q-pa-md"):
            with ui.row().classes("w-full items-center no-wrap q-mb-sm"):
                ui.label("EXECUTION LOG").classes("lbl")
                ui.label("● live").classes("term-info").style(
                    "font-family:'JetBrains Mono',monospace;font-size:11px"
                )
            self.scroll_area = ui.scroll_area().classes("w-full").style("height: 330px")
            with self.scroll_area:
                self.container = ui.column().classes("w-full gap-xs")

    def append(self, timestamp: str, event_type: str, text: str) -> None:
        icon = log_line_icon(event_type)
        klass = log_line_class(event_type)
        clock = timestamp[11:19] if len(timestamp) > 19 else timestamp

        if self.last_line is not None:
            try:
                self.last_line.classes(remove="term-caret")
            except Exception:  # noqa: BLE001 - element may be gone after clear()
                self.last_line = None

        with self.container:
            row = ui.row().classes("items-start gap-xs w-full")
            with row:
                ui.label(clock).classes("term-line term-ts").style("flex-shrink:0")
                ui.label(f"{icon} {text}").classes(f"term-line {klass}").style(
                    "min-width: 0; flex: 1"
                )
        self.last_line = row
        row.classes(add="term-caret")

        self._trim()
        self.scroll_area.scroll_to(percent=100)

    def _trim(self) -> None:
        children = list(self.container)
        for child in children[: max(0, len(children) - self.max_lines)]:
            child.delete()

    def clear(self) -> None:
        self.container.clear()
        self.last_line = None
