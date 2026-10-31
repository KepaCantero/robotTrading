"""Theme configuration for the NiceGUI backtesting dashboard.

Provides color palette, dark/light mode constants, and shared style definitions.
Semantic colors are sourced from the UI-0 design-system TOKENS
(design_system.py) so every consumer speaks the one cream/teal palette;
the legacy Material values (#4CAF50/#F44336/#2196F3…) failed the AA bar
on cream and split the visual language.
"""

from __future__ import annotations

from app.presentation.dashboard.nicegui_app.design_system import TOKENS

_T = TOKENS["color"]

# ── Color Palette ──────────────────────────────────────────────────────────────
# Semantic colors - consistent across the entire dashboard

COLORS: dict[str, str] = {
    # Profit / Loss
    "profit": _T["good"],
    "loss": _T["bad"],
    "warning": _T["warn"],
    "neutral": _T["text_soft"],
    # Status
    "pass_": _T["good"],
    "fail": _T["bad"],
    "inconclusive": _T["honey_deep"],
    # Brand
    "primary": _T["teal_deep"],
    "secondary": _T["text_soft"],
    "accent": _T["teal"],
    # Backgrounds (dark mode) — legacy dark chrome kept for the dark-mode
    # toggle; the shell renders light by default and nothing on the live
    # page path reads these keys today.
    "bg_dark": "#1a1a2e",
    "bg_card_dark": "#16213e",
    "bg_header_dark": "#0f3460",
    # Backgrounds (light mode)
    "bg_light": "#f5f5f5",
    "bg_card_light": "#ffffff",
    "bg_header_light": "#e0e0e0",
}

# ── Typography ─────────────────────────────────────────────────────────────────

FONT_FAMILY = "Roboto, 'Segoe UI', Arial, sans-serif"

# ── Quasar Dark Mode Override ──────────────────────────────────────────────────

DARK_COLORS: dict[str, str] = {
    "dark": COLORS["bg_dark"],
    "dark-page": COLORS["bg_dark"],
}

# ── ECharts Theme (Dark) ──────────────────────────────────────────────────────

ECHARTS_DARK_THEME = {
    "backgroundColor": COLORS["bg_dark"],
    "textStyle": {"color": "#e0e0e0"},
    "title": {"textStyle": {"color": "#e0e0e0"}},
    "legend": {"textStyle": {"color": "#e0e0e0"}},
    "categoryAxis": {
        "axisLine": {"lineStyle": {"color": "#555"}},
        "axisLabel": {"color": "#aaa"},
    },
    "valueAxis": {
        "axisLine": {"lineStyle": {"color": "#555"}},
        "axisLabel": {"color": "#aaa"},
        "splitLine": {"lineStyle": {"color": "#333"}},
    },
}

ECHARTS_LIGHT_THEME = {
    "backgroundColor": "#ffffff",
    "textStyle": {"color": "#333"},
    "title": {"textStyle": {"color": "#333"}},
}

# ── Page Definitions ───────────────────────────────────────────────────────────

PAGES = [
    {"name": "Agent Swarm", "icon": "smart_toy", "route": "/"},
    {"name": "Start", "icon": "flag", "route": "/start"},
    {"name": "Portfolio", "icon": "account_balance", "route": "/portfolio"},
    {"name": "Results", "icon": "analytics", "route": "/results"},
    {"name": "History & Compare", "icon": "history", "route": "/history"},
    {"name": "Objectives", "icon": "fact_check", "route": "/objectives"},
    {"name": "Config Viewer", "icon": "settings", "route": "/config"},
    {"name": "Profitability", "icon": "trending_up", "route": "/profitability"},
    {"name": "Documentation", "icon": "menu_book", "route": "/docs/"},
    {"name": "Trust & Risk", "icon": "verified_user", "route": "/trust"},
    {"name": "Glossary", "icon": "menu_book", "route": "/glossary"},
]


def profitability_color(verdict: str) -> str:
    """Return the color for a profitability verdict."""
    mapping = {
        "PASS": COLORS["profit"],
        "FAIL": COLORS["loss"],
        "INCONCLUSIVE": COLORS["inconclusive"],
    }
    return mapping.get(verdict.upper(), COLORS["neutral"])


# ── Metric Descriptions (tooltips) ───────────────────────────────────────────

METRIC_DESCRIPTIONS: dict[str, str] = {
    "Total Return": "Total percentage gain or loss over the backtest period.",
    "Sharpe Ratio": "Risk-adjusted return. Higher is better (>1.0 is good, >2.0 is excellent).",
    "Sortino Ratio": "Like Sharpe but only penalizes downside volatility. Better for asymmetric returns.",
    "Max Drawdown": "Largest peak-to-trough decline. Represents worst-case loss from a high point.",
    "Win Rate": "Percentage of trades that were profitable.",
    "Profit Factor": "Ratio of gross profits to gross losses. Above 1.5 is considered good.",
    "Total Trades": "Number of executed trades during the backtest period.",
}
