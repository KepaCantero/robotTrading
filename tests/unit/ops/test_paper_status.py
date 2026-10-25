"""Fase 6 parte 2 — ops status aggregation, tested against real tables.

The aggregator is the engine behind GET /ops/status: uncertain orders,
accounting divergence, corpus staleness and the honest not_deployed
scheduler note. Each rule gets a seeded sqlite proof.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.live_trading.trade_persistence import OrderRecord, TradeRecord
from app.services.ops.paper_status import collect_status, newest_bar_age_days


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: OrderRecord.metadata.create_all(
                sync_conn, tables=[OrderRecord.__table__, TradeRecord.__table__]
            )
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _order(order_id="o1", symbol="SCHD", status="FILLED", qty=10, created=None):
    return OrderRecord(
        order_id=order_id,
        symbol=symbol,
        side="BUY",
        quantity=Decimal(str(qty)),
        order_type="MARKET",
        status=status,
        broker_name="paper",
        created_at=created or datetime.now(timezone.utc),
    )


class TestUncertainOrders:
    async def test_old_pending_is_degraded(self, session_factory):
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        async with session_factory() as s:
            s.add(_order(status="PENDING", created=old))
            await s.commit()

        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["status"] == "degraded"
        assert report["uncertain_orders"]["count"] == 1
        assert report["uncertain_orders"]["symbols"] == ["SCHD"]

    async def test_fresh_pending_is_healthy(self, session_factory):
        """A few seconds of silence is patience, not an incident."""
        async with session_factory() as s:
            s.add(_order(status="SUBMITTED"))
            await s.commit()

        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["uncertain_orders"]["count"] == 0
        assert report["uncertain_orders"]["status"] == "healthy"


class TestAccountingDivergence:
    async def test_executed_without_fills_is_degraded(self, session_factory):
        async with session_factory() as s:
            s.add(_order(status="EXECUTED"))
            await s.commit()

        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["accounting_divergence"]["executed_without_fills"] == ["o1"]
        assert report["status"] == "degraded"

    async def test_partial_fill_sum_mismatch_is_degraded(self, session_factory):
        async with session_factory() as s:
            s.add(_order(status="FILLED", qty=10))
            s.add(
                TradeRecord(
                    trade_id="t1",
                    order_id="o1",
                    symbol="SCHD",
                    quantity=Decimal("6"),  # 6 of 10 — where is the rest?
                    execution_price=Decimal("75"),
                    execution_time=datetime.now(timezone.utc),
                    side="BUY",
                    fill_type="PARTIAL",
                )
            )
            await s.commit()

        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["accounting_divergence"]["fill_quantity_mismatch"] == ["o1"]

    async def test_matching_fill_is_healthy(self, session_factory):
        async with session_factory() as s:
            s.add(_order(status="FILLED", qty=10))
            s.add(
                TradeRecord(
                    trade_id="t1",
                    order_id="o1",
                    symbol="SCHD",
                    quantity=Decimal("10"),
                    execution_price=Decimal("75"),
                    execution_time=datetime.now(timezone.utc),
                    side="BUY",
                    fill_type="FULL",
                )
            )
            await s.commit()

        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["accounting_divergence"]["status"] == "healthy"


class TestQuoteStaleness:
    def test_newest_bar_age_from_tail_only(self, tmp_path):
        (tmp_path / "AAA.csv").write_text(
            "date,Open,High,Low,Close,Volume\n2026-01-02,1,1,1,1,1\n2026-01-05,1,1,1,1,1\n"
        )
        age = newest_bar_age_days(tmp_path)
        assert age is not None and age > 100  # 2026-01 is far in the past of test time

    def test_missing_dir_is_none(self, tmp_path):
        assert newest_bar_age_days(tmp_path / "nope") is None

    async def test_fresh_corpus_healthy(self, session_factory, tmp_path):
        fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        (tmp_path / "AAA.csv").write_text(f"date,Open,High,Low,Close,Volume\n{fresh},1,1,1,1,1\n")

        report = await collect_status(session_factory, tmp_path)
        assert report["quote_staleness"]["status"] == "healthy"


class TestDatabaseAndHonesty:
    async def test_dead_database_reports_unhealthy(self):
        class BrokenFactory:
            def __call__(self):
                raise RuntimeError("db down")

        report = await collect_status(BrokenFactory(), Path("/nonexistent"))
        assert report["status"] == "unhealthy"
        assert report["database"]["status"] == "unhealthy"

    async def test_tasks_reported_not_deployed(self, session_factory):
        """No scheduler exists in this stack — say so, never fake it."""
        report = await collect_status(session_factory, Path("/nonexistent"))
        assert report["tasks"]["status"] == "not_deployed"

    async def test_clean_stack_is_healthy(self, session_factory, tmp_path):
        fresh = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        (tmp_path / "AAA.csv").write_text(f"date,Open,High,Low,Close,Volume\n{fresh},1,1,1,1,1\n")

        report = await collect_status(session_factory, tmp_path)
        assert report["status"] == "healthy"
