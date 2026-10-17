"""Unit tests for the Agent Swarm pipeline-control page helpers.

The NiceGUI rendering itself is covered headlessly by test_swarm_render.py;
these tests cover the pure logic: log formatting, replay event folding,
the duration chart option and the result-metrics extraction.
"""

from datetime import date

from app.presentation.dashboard.nicegui_app.pages import swarm
from app.services.agent_swarm.events import AgentEvent
from app.services.agent_swarm.executor import AGENT_SPECS, AgentState


def fresh_states() -> dict[str, AgentState]:
    return {spec.agent_id: AgentState() for spec in AGENT_SPECS}


class TestFormatLogLine:
    def test_run_started(self):
        event = AgentEvent(
            "run_started",
            "r1",
            payload={"request": {"capital_initial": "100000", "objetivo_inversion": "MAX"}},
        )
        line = swarm.format_log_line(event)
        assert "Pipeline started" in line
        assert "€100000" in line

    def test_stage_started_and_completed(self):
        started = AgentEvent("stage_started", "r1", agent_id="t11")
        completed = AgentEvent(
            "stage_completed", "r1", agent_id="t21", payload={"duration_ms": 12.3, "xp": 50}
        )
        assert "T1.1 Input Processor started" == swarm.format_log_line(started)
        line = swarm.format_log_line(completed)
        assert "T2.1 Profile Generator completed in 12 ms (+50 XP)" == line

    def test_stage_failed_and_skipped(self):
        failed = AgentEvent("stage_failed", "r1", agent_id="t41", payload={"error": "boom"})
        skipped = AgentEvent("stage_skipped", "r1", agent_id="t51")
        assert "T4.1 Backtest Orchestrator FAILED — boom" == swarm.format_log_line(failed)
        assert "skipped" in swarm.format_log_line(skipped)

    def test_run_completed_and_failed(self):
        done = AgentEvent(
            "run_completed", "r1", payload={"xp": 600, "decision": {"status": "APPROVED"}}
        )
        failed = AgentEvent("run_failed", "r1", payload={"completed": 3})
        assert "600 XP" in swarm.format_log_line(done)
        assert "APPROVED" in swarm.format_log_line(done)
        assert "3/10" in swarm.format_log_line(failed)

    def test_milestone_wording(self):
        event = AgentEvent("achievement_unlocked", "r1", payload={"label": "First execution"})
        assert "Milestone reached: First execution" == swarm.format_log_line(event)

    def test_accepts_plain_dicts_too(self):
        event = {"type": "achievement_unlocked", "payload": {"label": "Clean run"}}
        assert "Clean run" in swarm.format_log_line(event)


class TestApplyEventToStates:
    def test_full_stage_lifecycle(self):
        states = fresh_states()
        swarm.apply_event_to_states(
            states, {"type": "stage_started", "agent_id": "t11", "payload": {"input": {"a": 1}}}
        )
        assert states["t11"].status == "RUNNING"
        assert states["t11"].input_payload == {"a": 1}

        swarm.apply_event_to_states(
            states,
            {
                "type": "stage_completed",
                "agent_id": "t11",
                "payload": {
                    "output": {"b": 2},
                    "duration_ms": 5.0,
                    "warnings": ["w1"],
                    "xp": 50,
                },
            },
        )
        assert states["t11"].status == "DONE"
        assert states["t11"].output_payload == {"b": 2}
        assert states["t11"].duration_ms == 5.0
        assert states["t11"].xp == 50

    def test_failure_and_skip(self):
        states = fresh_states()
        swarm.apply_event_to_states(
            states, {"type": "stage_failed", "agent_id": "t31", "payload": {"error": "nope"}}
        )
        swarm.apply_event_to_states(states, {"type": "stage_skipped", "agent_id": "t41"})
        assert states["t31"].status == "FAILED"
        assert states["t31"].error == "nope"
        assert states["t41"].status == "SKIPPED"

    def test_run_level_events_ignored(self):
        states = fresh_states()
        for etype in ("run_started", "run_completed", "run_failed", "achievement_unlocked"):
            swarm.apply_event_to_states(states, {"type": etype, "agent_id": None})
        assert all(s.status == "IDLE" for s in states.values())

    def test_unknown_agent_ignored(self):
        states = fresh_states()
        swarm.apply_event_to_states(
            states, {"type": "stage_started", "agent_id": "t99", "payload": {}}
        )
        assert all(s.status == "IDLE" for s in states.values())


class TestExtractResultMetrics:
    def test_extracts_key_numbers(self):
        results = {
            "backtest_result": {
                "backtest_result": {
                    "metrics": {
                        "total_return_pct": "5.0",
                        "sharpe_ratio": "1.2",
                        "max_drawdown_pct": "6.25",
                    }
                },
                "feasibility_ratio": "1.39",
            },
            "recommendation": {"recommended_strategy": "momentum_modular"},
            "deployment_decision": {
                "status": "REJECTED",
                "reasons": ["r1", "r2", "r3", "r4", "r5"],
                "next_steps": ["s1", "s2", "s3", "s4"],
            },
        }
        metrics = swarm.extract_result_metrics(results)
        assert metrics["total_return"] == "5.0"
        assert metrics["sharpe"] == "1.2"
        assert metrics["drawdown"] == "6.25"
        assert metrics["feasibility"] == "1.39"
        assert metrics["strategy"] == "momentum_modular"
        assert metrics["verdict"] == "REJECTED"
        assert len(metrics["reasons"]) == 4  # capped
        assert len(metrics["next_steps"]) == 3  # capped

    def test_empty_results_give_placeholders(self):
        metrics = swarm.extract_result_metrics({})
        assert metrics["total_return"] is None
        assert metrics["verdict"] is None
        assert metrics["reasons"] == []

    def test_verdict_copy_exists_for_all_statuses(self):
        for status in ("APPROVED", "CONDITIONAL", "REJECTED"):
            kind, title, meaning = swarm.VERDICTS[status]
            assert kind in {"ok", "mid", "bad"}
            assert title == status
            assert meaning


class TestExtractPortfolio:
    def _results(self):
        return {
            "portfolio": {
                "allocation_method": "efficient_frontier",
                "expected_portfolio_return_pct": "12",
                "expected_portfolio_sharpe": "1.5",
                "diversification_ratio": "1.3",
                "allocations": [
                    {
                        "module_name": "momentum",
                        "weight_pct": "40",
                        "capital_allocation_eur": "40000",
                        "rationale": "High-return growth module",
                    },
                    {
                        "module_name": "mean_reversion",
                        "weight_pct": "60",
                        "capital_allocation_eur": "60000",
                        "rationale": "Stable mean reversion strategy",
                    },
                ],
            },
            "risk_scaling": {
                "risk_scaling_applied": True,
                "adjusted_allocations": [
                    {
                        "module_name": "momentum",
                        "original_weight_pct": "40",
                        "adjusted_weight_pct": "25",
                    },
                    {
                        "module_name": "mean_reversion",
                        "original_weight_pct": "60",
                        "adjusted_weight_pct": "75",
                    },
                ],
            },
        }

    def test_extracts_allocations_with_floats(self):
        portfolio = swarm.extract_portfolio(self._results())
        assert portfolio["method"] == "efficient_frontier"
        assert len(portfolio["allocations"]) == 2
        assert portfolio["allocations"][0]["module"] == "momentum"
        assert portfolio["allocations"][0]["weight"] == 40.0
        assert portfolio["allocations"][0]["capital"] == 40000.0
        assert portfolio["risk_applied"] is True
        assert portfolio["adjusted"][0]["weight"] == 25.0

    def test_empty_results_give_empty_portfolio(self):
        portfolio = swarm.extract_portfolio({})
        assert portfolio["allocations"] == []
        assert portfolio["risk_applied"] is False

    def test_allocation_chart_donut(self):
        portfolio = swarm.extract_portfolio(self._results())
        option = swarm.build_allocation_chart(portfolio["allocations"])
        assert option is not None
        assert option["series"][0]["type"] == "pie"
        assert option["series"][0]["data"][0] == {"name": "momentum", "value": 40.0}

    def test_allocation_chart_none_when_empty(self):
        assert swarm.build_allocation_chart([]) is None

    def test_risk_adjustment_chart_groups_base_and_adjusted(self):
        portfolio = swarm.extract_portfolio(self._results())
        option = swarm.build_risk_adjustment_chart(portfolio["adjusted"])
        assert option is not None
        names = [s["name"] for s in option["series"]]
        assert "Base weight %" in names and "After risk adjustment %" in names
        assert option["yAxis"]["data"] == ["mean_reversion", "momentum"]  # reversed

    def test_risk_adjustment_chart_none_when_empty(self):
        assert swarm.build_risk_adjustment_chart([]) is None


class TestModuleExposureChart:
    def test_bars_per_module(self):
        parameter_set = {
            "module_parameters": {
                "momentum": {"max_exposure": "0.25"},
                "mean_reversion": {"max_exposure": "0.40"},
            }
        }
        option = swarm.build_module_exposure_chart(parameter_set)
        assert option is not None
        assert option["yAxis"]["data"] == ["mean_reversion", "momentum"]
        assert option["series"][0]["data"] == [40.0, 25.0]

    def test_none_when_empty(self):
        assert swarm.build_module_exposure_chart({}) is None


class TestDurationChart:
    def test_none_when_no_done_agents(self):
        assert swarm.build_duration_chart_option(fresh_states()) is None

    def test_includes_only_done_agents(self):
        states = fresh_states()
        states["t11"].status = "DONE"
        states["t11"].duration_ms = 100.0
        states["t21"].status = "DONE"
        states["t21"].duration_ms = 50.0
        states["t31"].status = "FAILED"

        option = swarm.build_duration_chart_option(states)
        names = option["yAxis"]["data"]
        assert len(names) == 2
        values = [d["value"] for d in option["series"][0]["data"]]
        assert values == [50.0, 100.0]

    def test_values_are_rounded(self):
        states = fresh_states()
        states["t11"].status = "DONE"
        states["t11"].duration_ms = 100.123456
        option = swarm.build_duration_chart_option(states)
        assert option["series"][0]["data"][0]["value"] == 100.1


class TestRegistry:
    def test_spec_by_agent_complete(self):
        assert set(swarm.SPEC_BY_AGENT.keys()) == {spec.agent_id for spec in AGENT_SPECS}
        assert swarm.SPEC_BY_AGENT["t41"].stage_slug == "backtest_execution"

    def test_objective_labels_are_plain_english(self):
        for key, label in swarm.OBJECTIVES.items():
            assert label[0].isupper()
            assert " " in label  # plain wording, not the raw enum


class TestPeriodHelpers:
    def test_available_universe_reads_csvs(self, tmp_path):
        (tmp_path / "AAPL.csv").write_text("date,close\n2020-01-01,1\n")
        (tmp_path / "MSFT.csv").write_text("date,close\n2020-01-01,1\n")
        assert swarm.available_universe(tmp_path) == ["AAPL", "MSFT"]

    def test_available_universe_falls_back_without_data(self, tmp_path):
        assert swarm.available_universe(tmp_path) == swarm.DEFAULT_UNIVERSE

    def test_data_window_reads_first_and_last_rows(self, tmp_path):
        (tmp_path / "AAPL.csv").write_text("date,close\n2020-01-02,1\n2021-06-01,2\n2024-09-30,3\n")
        window = swarm.data_window(["AAPL"], tmp_path)
        assert window == (date(2020, 1, 2), date(2024, 9, 30))

    def test_data_window_ignores_missing_symbols(self, tmp_path):
        (tmp_path / "AAPL.csv").write_text("date,close\n2021-01-01,1\n2022-01-01,2\n")
        assert swarm.data_window(["AAPL", "NOPE"], tmp_path) == (
            date(2021, 1, 1),
            date(2022, 1, 1),
        )

    def test_resolve_period_presets(self):
        bounds = (date(2010, 1, 1), date(2024, 12, 31))
        start, end = swarm.resolve_period("1y", None, None, bounds, today=date(2024, 12, 31))
        assert (start, end) == ("2024-01-01", "2024-12-31")  # 2024 is a leap year

        start, end = swarm.resolve_period("max", None, None, bounds)
        assert start == "2010-01-01"

    def test_resolve_period_custom_dates(self):
        bounds = (date(2010, 1, 1), date(2024, 12, 31))
        start, end = swarm.resolve_period("custom", "2022-03-01", "2023-03-01", bounds)
        assert (start, end) == ("2022-03-01", "2023-03-01")

    def test_resolve_period_clamps_to_available_data(self):
        bounds = (date(2020, 1, 1), date(2024, 12, 31))
        start, end = swarm.resolve_period("custom", "1999-01-01", "2001-01-01", bounds)
        assert start >= "2020-01-01"

    def test_resolve_period_never_inverted(self):
        bounds = (date(2020, 1, 1), date(2020, 6, 1))
        start, end = swarm.resolve_period("custom", "2020-05-01", "2020-01-01", bounds)
        assert start < end

    def test_spanish_provinces_cover_all_52(self):
        assert len(swarm.SPANISH_PROVINCES) == 52
        assert "Madrid" in swarm.SPANISH_PROVINCES
