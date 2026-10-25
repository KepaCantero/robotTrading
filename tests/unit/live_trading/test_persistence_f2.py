"""Fase 2 recoverable execution (hallazgos A09/A20).

- A09: the order INTENT is persisted BEFORE the broker send (a crash
  between intent and ack leaves a recoverable row keyed by the stable
  client_order_id); rejections update the row; persistence failures never
  block paper trading but are logged loudly.
- A20: `alembic upgrade head` on an empty database creates the live-trading
  tables (order_records, trade_records, position_history,
  trade_statistics) — the audit acceptance: base vacía → upgrade head →
  guardar y leer orden.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

import app.services.live_trading.trade_persistence as trade_persistence_module
from app.services.live_trading.broker_connector import OrderSide
from app.services.live_trading.order_manager import OrderManager
from app.services.live_trading.risk_gates import RiskGates
from tests.unit.live_trading.test_order_path_f2 import OrderPathBroker, fresh_quote


class RecordingPersistence:
    """Persistence double that records calls into a shared event list."""

    def __init__(self, events: list[str], fail_saves_after: int | None = None):
        self.events = events
        self.saved: list[dict] = []
        self.updated: list[tuple[str, str]] = []
        self.fail_saves_after = fail_saves_after

    async def save_order(self, order_data):
        if self.fail_saves_after is not None and len(self.saved) >= self.fail_saves_after:
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("stmt", {}, Exception("duplicate broker_order_id"))
        self.saved.append(order_data)
        self.events.append("persist-intent")
        return f"row_{len(self.saved)}"

    async def update_order_status(self, order_id, status, executed_at=None):
        del executed_at
        self.updated.append((order_id, status))
        self.events.append("persist-update")
        return True


@pytest.fixture
def events() -> list[str]:
    return []


@pytest.fixture
def holder(events, monkeypatch):
    """Route get_trade_persistence_manager to the test's recorder."""
    box: dict = {}

    def getter():
        if "recorder" not in box:
            raise AssertionError("test did not install a recorder")
        return box["recorder"]

    monkeypatch.setattr(trade_persistence_module, "get_trade_persistence_manager", getter)
    box["events"] = events
    return box


def wired_manager(broker, recorder) -> OrderManager:
    manager = OrderManager(broker=broker, risk_gates=RiskGates(broker=broker))
    manager._test_persistence = recorder  # noqa: SLF001 - test hook
    return manager


class TestIntentPersistence:
    """A09."""

    @pytest.mark.asyncio
    async def test_intent_persisted_before_send(self, holder, events):
        broker = OrderPathBroker(quotes={"SPY": fresh_quote("SPY", "400")})
        recorder = RecordingPersistence(events)
        manager = wired_manager(broker, recorder)
        holder["recorder"] = recorder

        original_send = broker.place_order

        async def send_recording(**kwargs):
            events.append("broker-send")
            return await original_send(**kwargs)

        broker.place_order = send_recording

        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"))
        assert order is not None

        assert events.index("persist-intent") < events.index("broker-send")
        assert recorder.saved[0]["status"] == "PENDING"
        assert recorder.saved[0]["broker_order_id"].startswith("trade_")
        assert recorder.updated and recorder.updated[0][0] == "row_1"

    @pytest.mark.asyncio
    async def test_rejection_updates_intent(self, holder, events):
        broker = OrderPathBroker(quotes={"SPY": fresh_quote("SPY", "400")})

        async def failing_send(**kwargs):
            return None  # broker rejects

        broker.place_order = failing_send
        recorder = RecordingPersistence(events)
        manager = wired_manager(broker, recorder)
        holder["recorder"] = recorder

        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"))
        assert order is None
        assert any("rejected" in status.lower() for _row, status in recorder.updated)

    @pytest.mark.asyncio
    async def test_duplicate_intent_does_not_block_the_retry(self, holder, events):
        class DedupingBroker(OrderPathBroker):
            """Mirrors PaperAdapter: same client_order_id returns the same order."""

            async def place_order(self, symbol, side, quantity, **kwargs):
                client_order_id = kwargs.get("client_order_id")
                if client_order_id:
                    for existing in self.orders.values():
                        if existing.client_order_id == client_order_id:
                            return existing
                return await super().place_order(symbol, side, quantity, **kwargs)

        broker = DedupingBroker(quotes={"SPY": fresh_quote("SPY", "400")})
        recorder = RecordingPersistence(events, fail_saves_after=1)
        manager = wired_manager(broker, recorder)
        holder["recorder"] = recorder

        first = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"), order_ref="signal-77")
        second = await manager.place_order(
            "SPY", OrderSide.BUY, Decimal("1"), order_ref="signal-77"
        )
        assert first is not None and second is not None
        assert first.order_id == second.order_id  # deduped at the adapter

    @pytest.mark.asyncio
    async def test_persistence_failure_never_blocks_paper(self, monkeypatch):
        def raising_getter():
            raise RuntimeError("database down")

        monkeypatch.setattr(
            trade_persistence_module,
            "get_trade_persistence_manager",
            raising_getter,
        )
        broker = OrderPathBroker(quotes={"SPY": fresh_quote("SPY", "400")})
        manager = OrderManager(broker=broker, risk_gates=RiskGates(broker=broker))

        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("1"))
        assert order is not None  # loud CRITICAL logged, trading continues


class TestLiveTradingMigration:
    """A20: alembic upgrade head creates the live-trading tables."""

    def test_upgrade_head_creates_live_trading_tables(self, tmp_path, monkeypatch):
        import sqlite3

        db_path = tmp_path / "mig_test.db"
        monkeypatch.setenv("ALEMBIC_DB_URL", f"sqlite:///{db_path}")

        repo_root = __file__.split("/tests/")[0]
        cfg = AlembicConfig()
        cfg.set_main_option(
            "script_location",
            f"{repo_root}/app/infrastructure/persistence/database/migrations",
        )
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            tables = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        finally:
            conn.close()

        assert {"order_records", "trade_records", "position_history", "trade_statistics"} <= tables
