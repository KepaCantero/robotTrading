"""Config Viewer page - display configuration parameters.

Read-only view of all config parameters grouped by category.
"""

from nicegui import ui


def render() -> None:
    """Render the Config Viewer page content."""
    with ui.card().classes("w-full"):
        ui.label("Config Viewer").classes("text-h5")
        ui.label("View current configuration parameters (read-only).")
