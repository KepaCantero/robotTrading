"""Config Viewer page - display configuration parameters.

Read-only view of all config parameters from
config/portfolio/profile_batch_backtest.yaml, grouped by category:
Strategy (objectives), Risk, Optimization, Validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from nicegui import ui

from app.presentation.dashboard.nicegui_app import design_system as ds

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/portfolio/profile_batch_backtest.yaml")

# Categories to display, mapping config section key to display name.
_CATEGORIES = [
    ("objective_parameters", "Strategy / Objectives"),
    ("risk_parameters", "Risk"),
    ("optimization", "Optimization"),
    ("validation", "Validation"),
    ("acceptance_criteria", "Acceptance Criteria"),
    ("capital_tiers", "Capital Tiers"),
    ("investment_horizons", "Investment Horizons"),
    ("modules", "Modules"),
    ("parallelization", "Parallelization"),
    ("reporting", "Reporting"),
    ("backtest_period", "Backtest Period"),
]


def _load_config() -> dict[str, Any]:
    """Load the YAML config file."""
    try:
        with open(_CONFIG_PATH) as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.warning("Config file not found: %s", _CONFIG_PATH)
        return {}
    except yaml.YAMLError:
        logger.exception("Failed to parse YAML config")
        return {}


def _render_dict_card(title: str, data: dict[str, Any], depth: int = 0) -> None:
    """Render a dictionary as a card with key-value pairs."""
    with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
        ui.label(title).classes("text-h6 q-mb-sm")
        ui.separator().classes("q-mb-sm")

        for key, value in data.items():
            with ui.row().classes("w-full items-baseline"):
                ui.label(f"{key}:").classes("text-weight-medium q-mr-sm").style("min-width: 180px")
                if isinstance(value, dict):
                    _render_nested_dict(value)
                elif isinstance(value, list):
                    ui.label(str(value)).classes("text-grey")
                elif isinstance(value, bool):
                    from app.presentation.dashboard.nicegui_app.theme import COLORS

                    color = COLORS["profit"] if value else COLORS["loss"]
                    ui.label(str(value)).style(f"color: {color}")
                else:
                    ui.label(str(value)).classes("text-body2")


def _render_nested_dict(data: dict[str, Any]) -> None:
    """Render a nested dictionary inline."""
    with ui.column().classes("q-ml-md"):
        for k, v in data.items():
            with ui.row().classes("items-baseline"):
                ui.label(f"{k}:").classes("text-caption q-mr-sm").style("min-width: 120px")
                if isinstance(v, dict):
                    _render_nested_dict(v)
                else:
                    ui.label(str(v)).classes("text-caption text-grey")


def _render_risk_section(risk_params: dict[str, Any]) -> None:
    """Render risk parameters with sub-cards per risk level."""
    with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
        ui.label("Risk Parameters").classes("text-h6 q-mb-sm")
        ui.separator().classes("q-mb-sm")

        for level, params in risk_params.items():
            from app.presentation.dashboard.nicegui_app.theme import COLORS

            with (
                ui.element("div")
                .classes("panel q-pa-md w-full q-mb-sm")
                .style(f"border-left: 4px solid {COLORS['warning']}")
            ):
                ui.label(f"Risk Level: {level}").classes("text-subtitle1 font-bold")
                with ui.row().classes("w-full wrap gap-lg q-mt-sm"):
                    for key, value in params.items():
                        with ui.column().classes("min-w-[150px]"):
                            ui.label(key).classes("text-caption text-grey")
                            ui.label(str(value)).classes("text-body2")


def _render_objective_section(objectives: dict[str, Any]) -> None:
    """Render objective parameters with sub-cards per objective."""
    with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
        ui.label("Strategy / Objective Parameters").classes("text-h6 q-mb-sm")
        ui.separator().classes("q-mb-sm")

        for objective, params in objectives.items():
            from app.presentation.dashboard.nicegui_app.theme import COLORS

            with (
                ui.element("div")
                .classes("panel q-pa-md w-full q-mb-sm")
                .style(f"border-left: 4px solid {COLORS['primary']}")
            ):
                ui.label(f"Objective: {objective}").classes("text-subtitle1 font-bold")
                with ui.row().classes("w-full wrap gap-lg q-mt-sm"):
                    for key, value in params.items():
                        with ui.column().classes("min-w-[180px]"):
                            ui.label(key).classes("text-caption text-grey")
                            ui.label(str(value)).classes("text-body2")


def _render_simple_section(title: str, data: Any) -> None:
    """Render a simple section (not a dict of dicts)."""
    if isinstance(data, dict):
        with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
            ui.label(title).classes("text-h6 q-mb-sm")
            ui.separator().classes("q-mb-sm")

            with ui.row().classes("w-full wrap gap-lg"):
                for key, value in data.items():
                    with ui.column().classes("min-w-[150px]"):
                        ui.label(key).classes("text-caption text-grey")
                        ui.label(str(value)).classes("text-body2")
    elif isinstance(data, list):
        with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
            ui.label(title).classes("text-h6 q-mb-sm")
            ui.separator().classes("q-mb-sm")
            with ui.row().classes("w-full wrap gap-md"):
                for item in data:
                    ui.badge(str(item), color="#607D8B")


# ── Page Render ───────────────────────────────────────────────────────────────


def render() -> None:
    """Render the Config Viewer page content."""
    ds.inject()
    with ui.column().classes("w-full q-pa-lg"):
        ds.section_heading("Config Viewer", f"Configuration loaded from: {_CONFIG_PATH}")

        config = _load_config()

        if not config:
            ui.label("No configuration data found.").classes("text-negative")
            return

        # ── Database & Output ──────────────────────────────────────────────
        if "database" in config:
            _render_simple_section("Database", config["database"])
        if "output_dir" in config:
            _render_simple_section(
                "Output Directory",
                {"output_dir": config["output_dir"]},
            )

        # ── Backtest Period ────────────────────────────────────────────────
        if "backtest_period" in config:
            _render_simple_section("Backtest Period", config["backtest_period"])

        # ── Capital Tiers ──────────────────────────────────────────────────
        if "capital_tiers" in config:
            _render_simple_section("Capital Tiers", config["capital_tiers"])

        # ── Investment Horizons ────────────────────────────────────────────
        if "investment_horizons" in config:
            _render_simple_section("Investment Horizons", config["investment_horizons"])

        # ── Symbols ────────────────────────────────────────────────────────
        if "symbols" in config:
            _render_simple_section("Symbols Universe", {"count": len(config["symbols"])})
            with ui.element("div").classes("panel q-pa-md w-full q-mb-md"):
                ui.label("Symbols").classes("text-h6 q-mb-sm")
                ui.separator().classes("q-mb-sm")
                with ui.row().classes("w-full wrap gap-xs"):
                    for sym in config["symbols"]:
                        ui.badge(sym, color="#00BCD4").classes("q-ma-xs")

        # ── Objectives (Strategy) ──────────────────────────────────────────
        if "objective_parameters" in config:
            _render_objective_section(config["objective_parameters"])

        # ── Risk Parameters ────────────────────────────────────────────────
        if "risk_parameters" in config:
            _render_risk_section(config["risk_parameters"])

        # ── Optimization ───────────────────────────────────────────────────
        if "optimization" in config:
            _render_dict_card("Optimization Settings", config["optimization"])

        # ── Validation ─────────────────────────────────────────────────────
        if "validation" in config:
            _render_dict_card("Validation Settings", config["validation"])

        # ── Acceptance Criteria ────────────────────────────────────────────
        if "acceptance_criteria" in config:
            _render_simple_section("Acceptance Criteria", config["acceptance_criteria"])

        # ── Modules ────────────────────────────────────────────────────────
        if "modules" in config:
            _render_dict_card("Modules Configuration", config["modules"])

        # ── Parallelization ────────────────────────────────────────────────
        if "parallelization" in config:
            _render_simple_section("Parallelization", config["parallelization"])

        # ── Reporting ──────────────────────────────────────────────────────
        if "reporting" in config:
            _render_dict_card("Reporting", config["reporting"])

        # ── Logging ────────────────────────────────────────────────────────
        if "logging" in config:
            _render_simple_section("Logging", config["logging"])
