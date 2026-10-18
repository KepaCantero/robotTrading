"""Unit tests for the CAPA 2 swarm executor (real component chaining)."""

from decimal import Decimal

from app.services.agent_swarm import events as ev
from app.services.agent_swarm.executor import (
    AGENT_SPECS,
    XP_COMPLETE_BONUS,
    XP_PER_STAGE,
    Capa2PipelineExecutor,
    StageFailure,
    SwarmRunRequest,
)


def make_request(**overrides) -> SwarmRunRequest:
    defaults = {
        "capital_initial": Decimal("100000"),
        "objetivo_inversion": "MAXIMIZAR_CAPITAL",
        "risk_tolerance": "MEDIO",
        "investment_horizon": 24,
    }
    defaults.update(overrides)
    return SwarmRunRequest(**defaults)


class TestFullRun:
    async def test_all_ten_agents_complete(self):
        state = await Capa2PipelineExecutor().run(make_request())

        assert state.status == "completed"
        assert state.completed_count() == len(AGENT_SPECS)
        assert all(a.status == "DONE" for a in state.agents.values())

    async def test_xp_accounting(self):
        state = await Capa2PipelineExecutor().run(make_request())

        expected = len(AGENT_SPECS) * XP_PER_STAGE + XP_COMPLETE_BONUS
        assert state.xp == expected
        assert state.agents["t11"].xp == XP_PER_STAGE

    async def test_events_emitted_in_order(self):
        executor = Capa2PipelineExecutor()
        queue = executor.bus.subscribe()

        state = await executor.run(make_request())

        types = [e.type for e in state.events]
        assert types[0] == ev.RUN_STARTED
        assert types[-1] == ev.RUN_COMPLETED
        assert types.count(ev.STAGE_STARTED) == len(AGENT_SPECS)
        assert types.count(ev.STAGE_COMPLETED) == len(AGENT_SPECS)
        assert ev.STAGE_FAILED not in types
        assert ev.ACHIEVEMENT_UNLOCKED in types

        # Every event also reached the bus
        assert queue.qsize() == len(state.events)

    async def test_stage_events_carry_input_and_output(self):
        state = await Capa2PipelineExecutor().run(make_request())

        started = [e for e in state.events if e.type == ev.STAGE_STARTED and e.agent_id == "t11"]
        completed = [
            e for e in state.events if e.type == ev.STAGE_COMPLETED and e.agent_id == "t11"
        ]
        assert started[0].payload["input"]["capital_initial"] == "100000"
        assert completed[0].payload["duration_ms"] >= 0
        assert state.agents["t11"].input_payload is not None
        assert state.agents["t11"].output_payload is not None

    async def test_results_include_capa2_compatible_keys(self):
        state = await Capa2PipelineExecutor().run(make_request())

        for key in (
            "input_profile",
            "investment_profile",
            "module_parameters",
            "backtest_result",
            "validation",
            "recommendation",
            "portfolio",
            "risk_scaling",
            "report",
            "deployment_decision",
        ):
            assert key in state.results, f"missing {key}"
        assert isinstance(state.decision, dict)
        assert state.decision["status"] in {"APPROVED", "CONDITIONAL", "REJECTED"}

    async def test_achievements_reflect_real_outcomes(self):
        state = await Capa2PipelineExecutor().run(make_request())

        achievement_ids = {a["id"] for a in state.achievements}
        assert "first_launch" in achievement_ids
        assert "pipeline_complete" in achievement_ids
        # deploy_approved only when the real decision was APPROVED
        if "deploy_approved" in achievement_ids:
            assert state.decision["status"] == "APPROVED"

    async def test_on_event_callback_invoked(self):
        seen = []

        def callback(event):
            seen.append(event.type)

        await Capa2PipelineExecutor().run(make_request(), on_event=callback)

        assert ev.RUN_STARTED in seen
        assert ev.RUN_COMPLETED in seen

    async def test_run_is_registered_and_retrievable(self):
        executor = Capa2PipelineExecutor()
        state = await executor.run(make_request(), run_id="my_run")

        assert executor.get_run("my_run") is state
        assert executor.latest_run is state


class TestFailureHandling:
    async def test_failure_stops_pipeline_and_skips_rest(self):
        executor = Capa2PipelineExecutor()

        async def broken_t41(ctx, request):
            raise RuntimeError("backtest exploded")

        executor._t41_run = broken_t41  # noqa: SLF001 - patching for the test
        state = await executor.run(make_request())

        assert state.status == "failed"
        assert state.agents["t41"].status == "FAILED"
        assert "backtest exploded" in state.agents["t41"].error
        for spec in AGENT_SPECS[4:]:
            assert state.agents[spec.agent_id].status == "SKIPPED"
        types = [e.type for e in state.events]
        assert ev.STAGE_FAILED in types
        assert types.count(ev.STAGE_SKIPPED) == len(AGENT_SPECS) - 4
        assert types[-1] == ev.RUN_FAILED
        assert state.xp == 3 * XP_PER_STAGE  # t11, t21, t31 completed

    async def test_success_false_output_raises_stage_failure(self):
        executor = Capa2PipelineExecutor()

        class FailedResult:
            success = False
            error_message = "component said no"

        async def failing_stage(ctx, request):
            return FailedResult()

        executor._t21_run = failing_stage  # noqa: SLF001
        state = await executor.run(make_request())

        assert state.status == "failed"
        assert state.agents["t21"].status == "FAILED"
        assert state.agents["t21"].error == "component said no"


class TestRequestHandling:
    def test_resolve_target_default_is_03_percent(self):
        executor = Capa2PipelineExecutor()
        target = executor._resolve_target(make_request())  # noqa: SLF001
        assert target == Decimal("300")

    def test_resolve_target_respects_explicit_value(self):
        executor = Capa2PipelineExecutor()
        request = make_request(target_monthly_return_eur=Decimal("750"))
        assert executor._resolve_target(request) == Decimal("750")  # noqa: SLF001

    def test_request_to_dict_is_json_ready(self):
        data = make_request().to_dict()
        assert data["capital_initial"] == "100000"
        assert data["objetivo_inversion"] == "MAXIMIZAR_CAPITAL"

    async def test_stage_failure_is_an_exception(self):
        assert issubclass(StageFailure, Exception)


class TestPeriodAndTax:
    async def test_backtest_window_reaches_t41_input(self):
        request = make_request(
            backtest_start="2024-01-01",
            backtest_end="2024-12-31",
            symbols=["MSFT", "NVDA"],
        )
        state = await Capa2PipelineExecutor().run(request)
        payload = state.agents["t41"].input_payload

        assert payload["start_date"] == "2024-01-01"
        assert payload["end_date"] == "2024-12-31"
        assert payload["symbols"] == ["MSFT", "NVDA"]

    async def test_default_window_is_one_year(self):
        state = await Capa2PipelineExecutor().run(make_request())
        payload = state.agents["t41"].input_payload
        assert payload["end_date"] > payload["start_date"]

    async def test_invalid_period_fails_the_stage(self):
        request = make_request(backtest_start="2024-12-31", backtest_end="2024-01-01")
        state = await Capa2PipelineExecutor().run(request)

        assert state.status == "failed"
        assert state.agents["t41"].status == "FAILED"

    async def test_backtest_runs_the_real_engine(self):
        """T4.1 executes the repo's real engine over real CSV candles."""
        request = make_request(
            backtest_start="2024-10-24",
            backtest_end="2025-10-24",
            symbols=["AAPL", "MSFT", "GOOGL"],
            strategy="mean_reversion",
        )
        state = await Capa2PipelineExecutor().run(request)

        assert state.status == "completed"
        metrics = state.agents["t41"].output_payload["backtest_result"]["metrics"]
        assert metrics["total_trades"] > 0, "real engine should have traded MSFT"
        assert metrics["win_rate_pct"] is not None

    async def test_engine_params_reach_t41(self):
        request = make_request(
            backtest_start="2024-10-24",
            backtest_end="2025-10-24",
            symbols=["MSFT"],
            strategy="mean_reversion",
            commission_per_trade=Decimal("2.5"),
            slippage_pct=Decimal("0.2"),
            stop_loss_pct=Decimal("5"),
            take_profit_pct=Decimal("15"),
        )
        state = await Capa2PipelineExecutor().run(request)
        payload = state.agents["t41"].input_payload

        assert payload["commission_per_trade"] == "2.5"
        assert payload["slippage_percentage"] == "0.2"
        assert payload["stop_loss_percentage"] == "5"
        assert payload["take_profit_percentage"] == "15"
        assert payload["strategy_name"] == "mean_reversion"

    async def test_province_sets_spanish_tax_residence(self):
        request = make_request(tax_province="Madrid")
        state = await Capa2PipelineExecutor().run(request)
        payload = state.agents["t11"].input_payload

        assert payload["tax_residence"]["country_code"] == "ES"

    async def test_effective_spanish_tax_on_gain(self):
        """T5.1 uses the real SpainTaxEngine rate on the backtest gain."""
        from types import SimpleNamespace

        executor = Capa2PipelineExecutor()
        winning = SimpleNamespace(
            backtest=SimpleNamespace(
                backtest_result=SimpleNamespace(
                    ending_capital=Decimal("105000"), starting_capital=Decimal("100000")
                )
            )
        )
        losing = SimpleNamespace(
            backtest=SimpleNamespace(
                backtest_result=SimpleNamespace(
                    ending_capital=Decimal("99000"), starting_capital=Decimal("100000")
                )
            )
        )

        # €5k gain → first IRPF savings bracket → 19%
        assert executor._effective_tax_rate(winning) == Decimal("0.19")  # noqa: SLF001
        # no gain → no tax
        assert executor._effective_tax_rate(losing) == Decimal("0")  # noqa: SLF001

    async def test_t51_receives_a_tax_rate(self):
        """Whatever the real gain, validation always gets an explicit rate."""
        state = await Capa2PipelineExecutor().run(make_request(tax_province="Sevilla"))
        payload = state.agents["t51"].input_payload
        assert "tax_rate" in payload

    async def test_investor_context_is_stored_on_the_request(self):
        request = make_request(investor_age=45, tax_province="Barcelona")
        data = request.to_dict()
        assert data["investor_age"] == 45
        assert data["tax_province"] == "Barcelona"


class TestPersistenceIntegration:
    async def test_run_persists_to_store(self, tmp_path):
        from app.services.agent_swarm.store import SwarmRunStore

        store = SwarmRunStore(str(tmp_path / "swarm_exec.db"))
        await store.initialize()
        executor = Capa2PipelineExecutor(store=store)

        await executor.run(make_request(), run_id="persisted_run")
        await store.close()

        reopened = SwarmRunStore(str(tmp_path / "swarm_exec.db"))
        await reopened.initialize()
        runs = await reopened.list_runs()
        assert runs[0]["workflow_id"] == "persisted_run"
        assert runs[0]["status"] == "completed"
        assert runs[0]["total_xp"] == len(AGENT_SPECS) * XP_PER_STAGE + XP_COMPLETE_BONUS
        events = await reopened.get_run_events("persisted_run")
        assert events[0]["type"] == ev.RUN_STARTED
        await reopened.close()

    async def test_store_failure_does_not_break_run(self, tmp_path, caplog):
        from app.services.agent_swarm.store import SwarmRunStore

        class BrokenStore(SwarmRunStore):
            async def create_run(self, *args, **kwargs):
                raise RuntimeError("db down")

        store = BrokenStore(str(tmp_path / "broken.db"))
        await store.initialize()

        state = await Capa2PipelineExecutor(store=store).run(make_request())
        assert state.status == "completed"
