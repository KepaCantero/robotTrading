"""Named paper portfolios: one engine per name, main = historical paths."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.services.portfolio_management.named_portfolios import (
    DEFAULT_SLUG,
    create_portfolio,
    get_portfolio,
    list_portfolios,
    open_broker,
    open_store,
    paper_state_path,
    prepare_store,
    slugify,
    store_path,
)


class TestSlugAndPaths:
    def test_slugify_stable_and_safe(self):
        assert slugify("Dividendos 2026!") == "dividendos-2026"
        assert slugify("  MAIN  ") == "main"
        assert slugify("???")  # never empty: falls back to a dated slug

    def test_main_maps_to_historical_paths(self):
        assert store_path("main").name == "portfolio_management.db"
        assert paper_state_path("main").name == "paper_account.json"

    def test_other_slug_gets_own_files(self):
        assert store_path("hold-10y").name == "portfolio_management_hold-10y.db"
        assert paper_state_path("hold-10y").name == "paper_account_hold-10y.json"
        assert store_path("hold-10y") != store_path("main")


class TestRegistry:
    def test_create_and_list_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path
        )
        create_portfolio(
            "Hold 10y",
            source_run_id="swarm_x",
            strategy_name="static_ew",
            decision_status="CONDITIONAL",
            initial_cash=D("50000"),
        )
        meta = get_portfolio("hold-10y")
        assert meta is not None
        assert meta["name"] == "Hold 10y"
        assert meta["initial_cash"] == "50000"

        names = {p["slug"]: p["name"] for p in list_portfolios()}
        assert names["main"]  # main always present
        assert names.get("hold-10y") == "Hold 10y"

    def test_recreate_keeps_account_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path
        )
        create_portfolio("P1", initial_cash=D("100000"))
        create_portfolio("P1", initial_cash=D("999"))  # same slug, never resets
        assert get_portfolio("p1")["initial_cash"] == "100000"


class TestIsolation:
    @pytest.mark.asyncio
    async def test_two_portfolios_isolated_stores_and_accounts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path
        )
        from app.services.portfolio_management.models import ProfileAnswers
        from app.services.portfolio_management.winner_adoption import build_target

        # portfolio A saves a target; portfolio B starts empty
        engine_a, store_a = open_store("alpha")
        await prepare_store(engine_a)
        target = build_target(ProfileAnswers(), None)  # seed
        await store_a.save_target(target)

        engine_b, store_b = open_store("beta")
        await prepare_store(engine_b)
        assert await store_a.get_active_target() is not None
        assert await store_b.get_active_target() is None

        broker_b = await open_broker("beta", initial_cash=D("25000"))
        account_b = await broker_b.get_account_info()
        assert account_b.cash_available == D("25000")
        assert account_b.currency == "EUR"
        assert not paper_state_path("beta").exists()  # nothing persisted yet


class TestWinnerFromResults:
    def test_extracts_adoptable_run(self):
        from app.services.portfolio_management.winner_adoption import winner_from_results

        results = {
            "deployment_decision": {"status": "CONDITIONAL", "strategy_name": "static_ew"},
            "validation": {"passed": True},
            "portfolio": {
                "allocations": [
                    {"module_name": "SCHD", "weight_pct": "50"},
                    {"module_name": "VIG", "weight_pct": "50"},
                ]
            },
        }
        winner = winner_from_results("swarm_abc", results)
        assert winner is not None
        assert winner["decision_status"] == "CONDITIONAL"
        assert {h.symbol for h in winner["holdings"]} == {"SCHD", "VIG"}

    def test_rejected_run_not_adoptable(self):
        from app.services.portfolio_management.winner_adoption import winner_from_results

        assert winner_from_results("r", {"deployment_decision": {"status": "REJECTED"}}) is None
        assert winner_from_results("r", {}) is None
