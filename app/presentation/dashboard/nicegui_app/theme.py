"""Theme configuration for the NiceGUI backtesting dashboard.

Provides color palette, dark/light mode constants, and shared style definitions.
Trading industry standard: dark mode by default.
"""

from __future__ import annotations

# ── Color Palette ──────────────────────────────────────────────────────────────
# Semantic colors - consistent across the entire dashboard

COLORS: dict[str, str] = {
    # Profit / Loss
    "profit": "#4CAF50",
    "loss": "#F44336",
    "warning": "#FF9800",
    "neutral": "#9E9E9E",
    # Status
    "pass_": "#4CAF50",
    "fail": "#F44336",
    "inconclusive": "#FFC107",
    # Brand
    "primary": "#2196F3",
    "secondary": "#607D8B",
    "accent": "#00BCD4",
    # Backgrounds (dark mode)
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
    {"name": "Backtest Runner", "icon": "play_circle", "route": "/"},
    {"name": "Results", "icon": "analytics", "route": "/results"},
    {"name": "History & Compare", "icon": "history", "route": "/history"},
    {"name": "Config Viewer", "icon": "settings", "route": "/config"},
    {"name": "Profitability", "icon": "trending_up", "route": "/profitability"},
]


def profitability_color(verdict: str) -> str:
    """Return the color for a profitability verdict."""
    mapping = {
        "PASS": COLORS["profit"],
        "FAIL": COLORS["loss"],
        "INCONCLUSIVE": COLORS["inconclusive"],
    }
    return mapping.get(verdict.upper(), COLORS["neutral"])
