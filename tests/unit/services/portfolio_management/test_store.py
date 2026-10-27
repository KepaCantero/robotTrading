"""Persistence round-trips: versioned targets, FIFO lots, event history."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.portfolio_management.models import (
    Holding,
    ProfileAnswers,
    RebalancePlan,
    RebalanceTrigger,
)
from app.services.portfolio_management.store import PortfolioManagementStore

D = Decimal


@pytest.fixture
async def store(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/pm.db")
    from app.infrastructure.persistence.database import Base
    from app.services.portfolio_management import store as store_module

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all,
            tables=[
                store_module.TargetPortfolioRecord.__table__,
                store_module.PortfolioLotRecord.__table__,
                store_module.RebalanceEventRecord.__table__,
            ],
        )
    yield PortfolioManagementStore(async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()


def _target(reactive_only: bool = False):
    from app.services.portfolio_management.models import TargetPortfolio

    return TargetPortfolio(
        source="seed",
        holdings=[
            Holding(symbol="SCHD", weight=D("0.5"), rationale="core"),
            Holding(symbol="BND", weight=D("0.5")),
        ],
        profile=ProfileAnswers(risk_level="medium"),
        reactive_only=reactive_only,
    )


async def test_target_versioning_keeps_single_active(store):
    first = await store.save_target(_target())
    second = await store.save_target(_target(reactive_only=True))
    assert first.version == 1 and second.version == 2
    active = await store.get_active_target()
    assert active is not None and active.version == 2
    assert active.reactive_only is True


async def test_lots_fifo_consume(store):
    await store.add_lot("SCHD", D("10"), D("80"), purchased_at=datetime(2024, 1, 1))
    await store.add_lot("SCHD", D("10"), D("90"), purchased_at=datetime(2024, 6, 1))
    matched = await store.consume_lots_fifo("SCHD", D("15"))
    assert [(m.purchase_price, m.quantity) for m in matched] == [
        (D("80"), D("10")),
        (D("90"), D("5")),
    ]
    remaining = await store.get_lots("SCHD")
    assert len(remaining) == 1
    assert remaining[0].quantity == D("5") and remaining[0].purchase_price == D("90")


async def test_clear_lots_for_fresh_paper_start(store):
    """The supervised reset must leave zero open lots (audit events stay)."""
    await store.add_lot("SCHD", D("10"), D("80"), purchased_at=datetime(2024, 1, 1))
    await store.add_lot("BND", D("5"), D("70"), purchased_at=datetime(2024, 2, 1))
    cleared = await store.clear_lots()
    assert cleared == 2
    assert await store.get_lots() == []
    assert await store.clear_lots() == 0  # idempotent


async def test_event_history_and_cooldown_anchor(store):
    await store.append_event("drift", "skipped", "all inside band")
    plan = RebalancePlan(
        event_id="e1", trigger=RebalanceTrigger.DRIFT, summary="sold VYM back to band"
    )
    await store.record_plan(plan, action="executed")
    events = await store.list_events()
    assert len(events) == 2
    assert events[0]["action"] == "executed"  # newest first
    assert await store.last_rebalance_at() is not None
