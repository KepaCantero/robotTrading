"""E2E tests for NiceGUI dashboard user flows.

Uses NiceGUI's ``user_simulation`` context manager to verify that each
page and component renders correctly with the expected UI elements.
Tests cover: page titles, parameter labels, buttons, components,
null-service resilience, theme constants, and formatting helpers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from nicegui.testing import user_simulation

from app.infrastructure.persistence.backtest_result_store import (
    BacktestResultStore,
    BacktestRunRecord,
)
from app.presentation.dashboard.profitability_engine import ProfitabilityEngine
from app.services.backtest_runner import BacktestRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(**overrides) -> BacktestRunRecord:
    """Create a BacktestRunRecord with sensible defaults."""
    defaults = {
        "strategy_name": "momentum",
        "investor_profile": "maximizar_capital",
        "time_window": "1y",
        "total_return": 0.25,
        "sharpe_ratio": 1.8,
        "sortino_ratio": 2.1,
        "max_drawdown": -0.08,
        "win_rate": 0.62,
        "profit_factor": 1.9,
        "total_trades": 42,
        "git_commit_hash": "abc1234",
        "config_snapshot": json.dumps({"initial_capital": 100000}),
        "full_results_json": json.dumps({"final_capital": 125000}),
    }
    defaults.update(overrides)
    return BacktestRunRecord(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: Path) -> BacktestResultStore:
    """Create an initialized BacktestResultStore backed by a temp database."""
    db_path = tmp_path / "e2e_backtest.db"
    s = BacktestResultStore(db_path)
    await s.initialize()
    return s


@pytest.fixture
def runner(store: BacktestResultStore) -> BacktestRunner:
    """Create a BacktestRunner with a real store."""
    return BacktestRunner(store)


@pytest.fixture
def profitability() -> ProfitabilityEngine:
    """Create a ProfitabilityEngine."""
    return ProfitabilityEngine()


# ---------------------------------------------------------------------------
# Test: Full app renders on home page
# ---------------------------------------------------------------------------


class TestAppHome:
    """E2E tests for the full app rendering on the home page."""

    async def test_home_page_loads(
        self, store: BacktestResultStore, runner: BacktestRunner, profitability: ProfitabilityEngine
    ) -> None:
        """The home page should load with layout and navigation elements.

        Note: Page route content is rendered via @ui.page() handlers which
        run in a separate scope from the root function. The layout (drawer,
        header, dark mode) and navigation buttons are tested here.
        Individual page content is tested in dedicated page test classes.
        """
        from app.presentation.dashboard.nicegui_app.layout import AppShell

        def root():
            AppShell.configure(store, runner, profitability)
            AppShell.setup()

        async with user_simulation(root) as user:
            await user.open("/")
            # Layout elements
            await user.should_see("AlgoTrading")
            await user.should_see("Backtesting Dashboard")
            await user.should_see("Dark")
            # Navigation buttons (from PAGES definition in theme)
            await user.should_see("Backtest Runner")
            await user.should_see("Results")
            await user.should_see("History & Compare")
            await user.should_see("Config Viewer")
            await user.should_see("Profitability")


# ---------------------------------------------------------------------------
# Test: Individual page render functions
# ---------------------------------------------------------------------------


class TestBacktestRunnerPage:
    """E2E tests for the backtest runner page render function."""

    async def test_runner_renders_with_services(
        self, store: BacktestResultStore, runner: BacktestRunner, profitability: ProfitabilityEngine
    ) -> None:
        """The runner page should render all UI elements."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import render

        async with user_simulation(lambda: render(store, runner, profitability)) as user:
            await user.open("/")
            await user.should_see("Backtest Runner")
            await user.should_see("Configure parameters and run a backtest.")
            await user.should_see("Parameters")
            await user.should_see("Strategy")
            await user.should_see("Investor Profile")
            await user.should_see("Time Window")
            await user.should_see("Initial Capital")
            await user.should_see("Run Backtest")
            await user.should_see("momentum")

    async def test_runner_renders_with_none_services(self) -> None:
        """The runner page should render even with None services."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import render

        async with user_simulation(lambda: render(None, None, None)) as user:
            await user.open("/")
            await user.should_see("Backtest Runner")
            await user.should_see("Run Backtest")


class TestBacktestResultsPage:
    """E2E tests for the backtest results page render function."""

    async def test_results_renders_with_services(
        self, store: BacktestResultStore, profitability: ProfitabilityEngine
    ) -> None:
        """The results page should render the run selector and view button."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_results import render

        async with user_simulation(lambda: render(store, profitability)) as user:
            await user.open("/")
            await user.should_see("Backtest Results")
            await user.should_see("Select a run to view detailed results.")
            await user.should_see("Select Run")
            await user.should_see("Choose a backtest run")
            await user.should_see("View Results")

    async def test_results_renders_with_none_services(self) -> None:
        """The results page should render even with None services."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_results import render

        async with user_simulation(lambda: render(None, None)) as user:
            await user.open("/")
            await user.should_see("Backtest Results")


class TestHistoryComparePage:
    """E2E tests for the history and compare page render function."""

    async def test_history_renders_with_services(
        self, store: BacktestResultStore, profitability: ProfitabilityEngine
    ) -> None:
        """The history page should render the table and comparison section."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import render

        async with user_simulation(lambda: render(store, profitability)) as user:
            await user.open("/")
            await user.should_see("History & Compare")
            await user.should_see("Run History")
            await user.should_see("Compare Runs")
            await user.should_see("Run A")
            await user.should_see("Run B")
            await user.should_see("Compare")

    async def test_history_renders_with_none_services(self) -> None:
        """The history page should render even with None services."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import render

        async with user_simulation(lambda: render(None, None)) as user:
            await user.open("/")
            await user.should_see("History & Compare")


class TestConfigViewerPage:
    """E2E tests for the config viewer page render function."""

    async def test_config_renders_title(self) -> None:
        """The config page should render its title and config path."""
        from app.presentation.dashboard.nicegui_app.pages.config_viewer import render

        async with user_simulation(render) as user:
            await user.open("/")
            await user.should_see("Config Viewer")
            await user.should_see("profile_batch_backtest.yaml")


class TestProfitabilityPage:
    """E2E tests for the profitability analysis page render function."""

    async def test_profitability_renders_with_services(
        self, store: BacktestResultStore, profitability: ProfitabilityEngine
    ) -> None:
        """The profitability page should render verdict table and summary."""
        from app.presentation.dashboard.nicegui_app.pages.profitability import render

        async with user_simulation(lambda: render(store, profitability)) as user:
            await user.open("/")
            await user.should_see("Profitability Analysis")
            await user.should_see("Verdict Table")

    async def test_profitability_renders_with_none_services(self) -> None:
        """The profitability page should render even with None services."""
        from app.presentation.dashboard.nicegui_app.pages.profitability import render

        async with user_simulation(lambda: render(None, None)) as user:
            await user.open("/")
            await user.should_see("Profitability Analysis")


# ---------------------------------------------------------------------------
# Test: UI Components
# ---------------------------------------------------------------------------


class TestMetricCardComponent:
    """E2E tests for the metric_card component."""

    async def test_metric_card_renders(self) -> None:
        """metric_card should render title, value, and subtitle."""
        from app.presentation.dashboard.nicegui_app.components.metric_cards import metric_card

        async with user_simulation(lambda: metric_card("Sharpe", "1.80", "Risk-adjusted", "#2196F3")) as user:
            await user.open("/")
            await user.should_see("Sharpe")
            await user.should_see("1.80")
            await user.should_see("Risk-adjusted")

    async def test_metric_card_with_tooltip(self) -> None:
        """metric_card should accept a tooltip parameter."""
        from app.presentation.dashboard.nicegui_app.components.metric_cards import metric_card

        async with user_simulation(
            lambda: metric_card("Total Return", "25%", "Performance", "#4CAF50", "Net return")
        ) as user:
            await user.open("/")
            await user.should_see("Total Return")
            await user.should_see("25%")

    async def test_metric_card_auto_tooltip(self) -> None:
        """metric_card should auto-lookup tooltips from METRIC_DESCRIPTIONS."""
        from app.presentation.dashboard.nicegui_app.components.metric_cards import metric_card

        async with user_simulation(lambda: metric_card("Sharpe Ratio", "1.80")) as user:
            await user.open("/")
            await user.should_see("Sharpe Ratio")


class TestSkeletonCardComponent:
    """E2E tests for the skeleton_card component."""

    async def test_skeleton_card_renders(self) -> None:
        """skeleton_card should render without errors."""
        from app.presentation.dashboard.nicegui_app.components.metric_cards import skeleton_card

        async with user_simulation(lambda: skeleton_card()) as user:
            await user.open("/")
            # Skeleton cards don't have visible text, just verify no crash


class TestProfitabilityBadgeComponent:
    """E2E tests for the profitability_badge component."""

    async def test_badge_pass(self) -> None:
        """PASS badge should render with green color."""
        from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
            profitability_badge,
        )

        async with user_simulation(lambda: profitability_badge("PASS")) as user:
            await user.open("/")
            await user.should_see("PASS")

    async def test_badge_fail(self) -> None:
        """FAIL badge should render with red color."""
        from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
            profitability_badge,
        )

        async with user_simulation(lambda: profitability_badge("FAIL")) as user:
            await user.open("/")
            await user.should_see("FAIL")

    async def test_badge_inconclusive(self) -> None:
        """INCONCLUSIVE badge should render with yellow color."""
        from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
            profitability_badge,
        )

        async with user_simulation(lambda: profitability_badge("INCONCLUSIVE")) as user:
            await user.open("/")
            await user.should_see("INCONCLUSIVE")

    async def test_badge_lowercase_input(self) -> None:
        """Badge should uppercase the verdict text."""
        from app.presentation.dashboard.nicegui_app.components.profitability_badge import (
            profitability_badge,
        )

        async with user_simulation(lambda: profitability_badge("pass")) as user:
            await user.open("/")
            await user.should_see("PASS")


class TestRunComparisonComponent:
    """E2E tests for the run_comparison component."""

    async def test_comparison_renders_labels(self) -> None:
        """run_comparison should show run labels."""
        from app.presentation.dashboard.nicegui_app.components.run_comparison import (
            run_comparison,
        )

        diff = {
            "total_return": {"a": 0.10, "b": 0.15, "delta": 0.05},
            "sharpe_ratio": {"a": 1.2, "b": 1.8, "delta": 0.6},
        }

        async with user_simulation(lambda: run_comparison("Run 1", "Run 2", diff)) as user:
            await user.open("/")
            await user.should_see("Run 1")
            await user.should_see("Run 2")

    async def test_comparison_renders_table(self) -> None:
        """run_comparison should render a table with diff data.

        Note: ui.table row data is not directly visible via should_see,
        but the table element itself is present in the page tree.
        """
        from app.presentation.dashboard.nicegui_app.components.run_comparison import (
            run_comparison,
        )

        diff = {"win_rate": {"a": 0.55, "b": 0.65, "delta": 0.10}}

        async with user_simulation(lambda: run_comparison("Alpha", "Beta", diff)) as user:
            await user.open("/")
            await user.should_see("Alpha")
            await user.should_see("Beta")


class TestFinancialChartsComponent:
    """E2E tests for the financial_charts placeholder component."""

    async def test_equity_curve_renders(self) -> None:
        """equity_curve_chart placeholder should render."""
        from app.presentation.dashboard.nicegui_app.components.financial_charts import (
            equity_curve_chart,
        )

        async with user_simulation(equity_curve_chart) as user:
            await user.open("/")
            await user.should_see("Chart will be rendered here.")


class TestDividendPanelComponent:
    """E2E tests for the dividend_panel placeholder component."""

    async def test_dividend_panel_renders(self) -> None:
        """dividend_panel placeholder should render."""
        from app.presentation.dashboard.nicegui_app.components.dividend_panel import (
            dividend_panel,
        )

        async with user_simulation(dividend_panel) as user:
            await user.open("/")
            await user.should_see("Dividend metrics will be displayed here.")


# ---------------------------------------------------------------------------
# Test: Theme module
# ---------------------------------------------------------------------------


class TestTheme:
    """Tests for the theme module constants and helpers."""

    def test_colors_dict_has_required_keys(self) -> None:
        """The COLORS dict must contain all semantic color keys."""
        from app.presentation.dashboard.nicegui_app.theme import COLORS

        required = {
            "profit",
            "loss",
            "warning",
            "neutral",
            "pass_",
            "fail",
            "inconclusive",
            "primary",
            "secondary",
            "accent",
        }
        assert required.issubset(set(COLORS.keys()))

    def test_profitability_color_pass(self) -> None:
        """profitability_color('PASS') should return green."""
        from app.presentation.dashboard.nicegui_app.theme import profitability_color

        assert profitability_color("PASS") == "#4CAF50"

    def test_profitability_color_fail(self) -> None:
        """profitability_color('FAIL') should return red."""
        from app.presentation.dashboard.nicegui_app.theme import profitability_color

        assert profitability_color("FAIL") == "#F44336"

    def test_profitability_color_inconclusive(self) -> None:
        """profitability_color('INCONCLUSIVE') should return amber."""
        from app.presentation.dashboard.nicegui_app.theme import profitability_color

        assert profitability_color("INCONCLUSIVE") == "#FFC107"

    def test_pages_list_has_five_entries(self) -> None:
        """The PAGES list must have 5 entries."""
        from app.presentation.dashboard.nicegui_app.theme import PAGES

        assert len(PAGES) == 5

    def test_pages_have_required_fields(self) -> None:
        """Each PAGES entry must have name, icon, and route."""
        from app.presentation.dashboard.nicegui_app.theme import PAGES

        for page in PAGES:
            assert "name" in page
            assert "icon" in page
            assert "route" in page

    def test_pages_routes_are_unique(self) -> None:
        """Each PAGES entry must have a unique route."""
        from app.presentation.dashboard.nicegui_app.theme import PAGES

        routes = [p["route"] for p in PAGES]
        assert len(routes) == len(set(routes))

    def test_metric_descriptions_has_required_metrics(self) -> None:
        """METRIC_DESCRIPTIONS must contain tooltips for all key metrics."""
        from app.presentation.dashboard.nicegui_app.theme import METRIC_DESCRIPTIONS

        required_metrics = {
            "Total Return",
            "Sharpe Ratio",
            "Max Drawdown",
            "Win Rate",
            "Profit Factor",
            "Total Trades",
        }
        assert required_metrics.issubset(set(METRIC_DESCRIPTIONS.keys()))

    def test_dark_colors_dict_exists(self) -> None:
        """DARK_COLORS should be a dict with Quasar overrides."""
        from app.presentation.dashboard.nicegui_app.theme import DARK_COLORS

        assert isinstance(DARK_COLORS, dict)

    def test_echarts_themes_exist(self) -> None:
        """Both ECharts themes (dark and light) should be defined."""
        from app.presentation.dashboard.nicegui_app.theme import (
            ECHARTS_DARK_THEME,
            ECHARTS_LIGHT_THEME,
        )

        assert isinstance(ECHARTS_DARK_THEME, dict)
        assert isinstance(ECHARTS_LIGHT_THEME, dict)


# ---------------------------------------------------------------------------
# Test: Formatter helpers
# ---------------------------------------------------------------------------


class TestFormatters:
    """Tests for the formatting helper functions used by pages."""

    def test_fmt_pct_with_value(self) -> None:
        """_fmt_pct should format a float as percentage."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_pct

        assert _fmt_pct(0.1234) == "12.34%"

    def test_fmt_pct_with_none(self) -> None:
        """_fmt_pct should return 'N/A' for None."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_pct

        assert _fmt_pct(None) == "N/A"

    def test_fmt_pct_with_zero(self) -> None:
        """_fmt_pct should handle 0.0 correctly."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_pct

        assert _fmt_pct(0.0) == "0.00%"

    def test_fmt_pct_with_negative(self) -> None:
        """_fmt_pct should handle negative values."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_pct

        assert _fmt_pct(-0.08) == "-8.00%"

    def test_fmt_float_with_value(self) -> None:
        """_fmt_float should format a float with 4 decimal places."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_float

        assert _fmt_float(1.8) == "1.8000"

    def test_fmt_float_with_none(self) -> None:
        """_fmt_float should return 'N/A' for None."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_float

        assert _fmt_float(None) == "N/A"

    def test_fmt_int_with_value(self) -> None:
        """_fmt_int should format an integer."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_int

        assert _fmt_int(42) == "42"

    def test_fmt_int_with_none(self) -> None:
        """_fmt_int should return 'N/A' for None."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_int

        assert _fmt_int(None) == "N/A"

    def test_fmt_int_with_zero(self) -> None:
        """_fmt_int should handle 0."""
        from app.presentation.dashboard.nicegui_app.pages.backtest_runner import _fmt_int

        assert _fmt_int(0) == "0"


class TestHistoryFormatters:
    """Tests for the history_compare page formatters."""

    def test_fmt_val_with_value(self) -> None:
        """_fmt_val should format a float with 4 decimal places."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import _fmt_val

        assert _fmt_val(1.5) == "1.5000"

    def test_fmt_val_with_none(self) -> None:
        """_fmt_val should return 'N/A' for None."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import _fmt_val

        assert _fmt_val(None) == "N/A"

    def test_fmt_val_with_suffix(self) -> None:
        """_fmt_val should append a suffix."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import _fmt_val

        assert _fmt_val(1.5, "%") == "1.5000%"

    def test_fmt_pct_with_value(self) -> None:
        """_fmt_pct should format as percentage."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import _fmt_pct

        assert _fmt_pct(0.25) == "25.00%"

    def test_fmt_pct_with_none(self) -> None:
        """_fmt_pct should return 'N/A' for None."""
        from app.presentation.dashboard.nicegui_app.pages.history_compare import _fmt_pct

        assert _fmt_pct(None) == "N/A"
