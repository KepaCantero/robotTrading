"""Import a real portfolio as a named portfolio's baseline target."""

from __future__ import annotations

from decimal import Decimal as D
from pathlib import Path

import pytest

from app.services.portfolio_management.import_snapshot import (
    ImportedPosition,
    Snapshot,
    SnapshotError,
    import_portfolio,
    load_snapshot,
    portfolio_warnings,
    to_holdings,
)
from app.services.portfolio_management.models import TargetPortfolio
from app.services.portfolio_management.named_portfolios import get_portfolio, open_store


def _snapshot_file(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "snap.json"
    path.write_text(body)
    return path


class TestLoadSnapshot:
    def test_fx_conversion_of_positions_and_cash(self, tmp_path):
        path = _snapshot_file(
            tmp_path,
            """
            {"base_currency": "EUR", "fx": {"USD": "1.12"},
             "cash": [{"currency": "EUR", "value": "562"},
                      {"currency": "USD", "value": "432"}],
             "positions": [
               {"symbol": "vhyl", "market_value": "41156", "currency": "EUR"},
               {"symbol": "VZ", "quantity": "100", "price": "43.70", "currency": "USD"}
             ]}
            """,
        )
        snap = load_snapshot(path)
        assert snap.base_currency == "EUR"
        assert snap.cash == D("562") + D("432") * D("1.12")
        vhyl = next(p for p in snap.positions if p.symbol == "VHYL")
        vz = next(p for p in snap.positions if p.symbol == "VZ")
        assert vhyl.market_value == D("41156")
        assert vz.market_value == (D("100") * D("43.70") * D("1.12"))

    def test_market_value_wins_over_quantity_times_price(self, tmp_path):
        path = _snapshot_file(
            tmp_path,
            """
            {"base_currency": "EUR",
             "positions": [{"symbol": "KO", "quantity": "10", "price": "92",
                            "market_value": "1000"}]}
            """,
        )
        snap = load_snapshot(path)
        assert snap.positions[0].market_value == D("1000")

    def test_missing_fx_rate_refuses(self, tmp_path):
        path = _snapshot_file(
            tmp_path,
            """
            {"base_currency": "EUR",
             "positions": [{"symbol": "VZ", "market_value": "100", "currency": "USD"}]}
            """,
        )
        with pytest.raises(SnapshotError, match="no fx rate"):
            load_snapshot(path)

    def test_position_without_any_value_refuses(self, tmp_path):
        path = _snapshot_file(
            tmp_path,
            '{"base_currency": "EUR", "positions": [{"symbol": "VZ"}]}',
        )
        with pytest.raises(SnapshotError, match="needs market_value"):
            load_snapshot(path)

    def test_non_positive_value_refuses(self, tmp_path):
        path = _snapshot_file(
            tmp_path,
            '{"base_currency": "EUR", "positions": [{"symbol": "VZ", "market_value": "-100"}]}',
        )
        with pytest.raises(SnapshotError, match="long-only"):
            load_snapshot(path)

    def test_no_positions_refuses(self, tmp_path):
        path = _snapshot_file(tmp_path, '{"base_currency": "EUR", "positions": []}')
        with pytest.raises(SnapshotError, match="no positions"):
            load_snapshot(path)

    def test_unreadable_file_refuses(self, tmp_path):
        with pytest.raises(SnapshotError, match="cannot read"):
            load_snapshot(tmp_path / "missing.json")


class TestToHoldings:
    def test_weights_are_shares_of_positions_plus_cash(self):
        positions = [
            ImportedPosition(symbol="A", market_value=D("75")),
            ImportedPosition(symbol="B", market_value=D("25")),
        ]
        holdings, skipped, total = to_holdings(positions, cash=D("100"))
        assert total == D("200")
        assert not skipped
        weights = {h.symbol: h.weight for h in holdings}
        assert weights["A"] == D("0.375")
        assert weights["B"] == D("0.125")
        assert sum(weights.values()) == D("0.5")  # cash keeps the other half

    def test_dust_positions_skipped_and_reported(self):
        positions = [
            ImportedPosition(symbol="BIG", market_value=D("999.5")),
            ImportedPosition(symbol="TINY", market_value=D("0.5")),  # 0.05% = dust
        ]
        holdings, skipped, total = to_holdings(positions, cash=D("0"))
        assert [h.symbol for h in holdings] == ["BIG"]
        assert skipped and skipped[0]["symbol"] == "TINY"
        assert total == D("1000")

    def test_weight_exactly_at_dust_threshold_is_kept(self):
        positions = [ImportedPosition(symbol="T", market_value=D("1"))]  # 0.1% exactly
        holdings, skipped, _ = to_holdings(positions, cash=D("999"))
        assert [h.symbol for h in holdings] == ["T"]
        assert not skipped

    def test_zero_account_refuses(self):
        with pytest.raises(SnapshotError, match="zero"):
            to_holdings([], cash=D("0"))


class TestPortfolioWarnings:
    def _target(self) -> TargetPortfolio:
        target = TargetPortfolio(max_position_pct=D("40"), equity_max_pct=D("90"))
        return target

    def test_cap_violation_reported(self):
        from app.services.portfolio_management.models import Holding

        target = self._target()
        holdings = [
            Holding(symbol="VHYL", weight=D("0.45")),  # > 40% cap
            Holding(symbol="VWCE", weight=D("0.45")),  # equity
        ]
        warnings = portfolio_warnings(holdings, target)
        assert any("VHYL" in w and "single-position cap" in w for w in warnings)
        # equity = 0.90 exactly → at the ceiling is not a violation
        assert not any("equity share" in w for w in warnings)

    def test_equity_ceiling_counts_bonds_correctly(self):
        from app.services.portfolio_management.models import Holding

        target = self._target()
        holdings = [
            Holding(symbol="VHYL", weight=D("0.45")),
            Holding(symbol="VWCE", weight=D("0.45")),
            Holding(symbol="IBTS", weight=D("0.10")),  # bond sleeve
        ]
        warnings = portfolio_warnings(holdings, target)
        assert not any("equity share" in w for w in warnings)  # 90% == ceiling

    def test_clean_portfolio_no_warnings(self):
        from app.services.portfolio_management.models import Holding

        target = self._target()
        holdings = [
            Holding(symbol="VWCE", weight=D("0.35")),
            Holding(symbol="IBTS", weight=D("0.30")),
        ]
        assert portfolio_warnings(holdings, target) == []


class TestImportPortfolio:
    async def test_import_writes_named_portfolio_and_target(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path)
        snap = Snapshot(
            base_currency="EUR",
            cash=D("100"),
            positions=[
                ImportedPosition(symbol="VWCE", market_value=D("600")),
                ImportedPosition(symbol="IBTS", market_value=D("300")),
            ],
        )
        report = await import_portfolio("Live Test", snap, risk_level="aggressive")
        assert report.slug == "live-test"
        assert report.version == 1
        assert report.total_value == D("1000")
        assert get_portfolio("live-test")["initial_cash"] == "1000"

        engine, store = open_store("live-test")
        try:
            target = await store.get_active_target()
            assert target is not None
            assert target.source == "import"
            assert target.decision_status == "IMPORTED"
            weights = {h.symbol: h.weight for h in target.holdings}
            assert weights["VWCE"] == D("0.6")
            assert weights["IBTS"] == D("0.3")
            # aggressive rules applied as the rebalancing config
            assert target.max_position_pct == D("40")
        finally:
            await engine.dispose()

    async def test_import_refuses_main(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path)
        snap = Snapshot(positions=[ImportedPosition(symbol="A", market_value=D("10"))])
        with pytest.raises(ValueError, match="main"):
            await import_portfolio("MAIN", snap)

    async def test_reimport_creates_new_version_not_a_reset(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path)
        snap = Snapshot(positions=[ImportedPosition(symbol="A", market_value=D("100"))])
        first = await import_portfolio("Drift Watch", snap)
        snap.positions.append(ImportedPosition(symbol="B", market_value=D("100")))
        second = await import_portfolio("Drift Watch", snap)
        assert second.version == first.version + 1

        engine, store = open_store("drift-watch")
        try:
            target = await store.get_active_target()
            assert {h.symbol for h in target.holdings} == {"A", "B"}
        finally:
            await engine.dispose()

    async def test_live_like_snapshot_reports_equity_violation(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.portfolio_management.named_portfolios.DATA_DIR", tmp_path)
        snap = Snapshot(
            cash=D("10"),
            positions=[
                ImportedPosition(symbol="VHYL", market_value=D("41156")),
                ImportedPosition(symbol="VWCE", market_value=D("38563")),
                ImportedPosition(symbol="VZ", market_value=D("4883")),
                ImportedPosition(symbol="IBTS", market_value=D("4114")),
            ],
        )
        report = await import_portfolio("Live", snap, risk_level="aggressive")
        # 92.6% equity (IBTS is a bond) vs the aggressive 90% ceiling
        assert any("equity share" in w for w in report.warnings)
