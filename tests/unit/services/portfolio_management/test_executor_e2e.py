"""E2E: a plan goes through OrderManager → RiskGates → PaperAdapter and
lands as positions, lots and history (P4 acceptance).

Deterministic price source injected into PaperAdapter; auto-fill on so
market orders fill immediately, exactly as the daily runner does.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.live_trading.broker_connector import BrokerConnector, BrokerType
from app.services.portfolio_management.executor import RebalanceExecutor
from app.services.portfolio_management.models import (
    PlannedTrade,
    PlanStatus,
    RebalancePlan,
    RebalanceTrigger,
)
from app.services.portfolio_management.store import PortfolioManagementStore

D = Decimal

PRICES = {"SCHD": D("100"), "BND": D("80")}


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


@pytest.fixture
async def broker():
    connector = BrokerConnector(BrokerType.PAPER)
    connector.adapter.auto_fill_orders = True
    connector.adapter.set_price_source(lambda symbol: (PRICES.get(symbol), datetime.utcnow()))
    assert await connector.connect()
    yield connector
    await connector.disconnect()


def _plan(*trades: PlannedTrade) -> RebalancePlan:
    return RebalancePlan(
        event_id="e2e-1",
        status=PlanStatus.PROACTIVE,
        trigger=RebalanceTrigger.DRIFT,
        trades=list(trades),
        summary="E2E: buy the underweight with new cash.",
    )


async def test_buy_fills_creates_lot_and_history(store, broker):
    buy = PlannedTrade(
        symbol="SCHD",
        side="BUY",
        quantity=D("12.345678"),  # fractional by default (requirement 9)
        price=D("100"),
        value=D("1234.5678"),
        reason="Buying €1235 of SCHD back to target.",
    )
    executor = RebalanceExecutor(store, broker)
    outcome = await executor.execute(_plan(buy))

    assert outcome.ok, outcome.failed
    assert len(outcome.executed) == 1
    position = await broker.get_position("SCHD")
    assert position is not None
    assert position.quantity == D("12.345678")  # fractional shares held exactly

    lots = await store.get_lots("SCHD")
    assert len(lots) == 1
    assert lots[0].quantity == D("12.345678")
    assert lots[0].purchase_price == D("100")

    events = await store.list_events()
    assert events[0]["action"] == "executed"
    assert events[0]["details"]["executed"], events[0]


async def test_sell_consumes_lots_fifo_and_credits_cash(store, broker):
    # open 2 lots (100 @80 then 50 @100), sell 120 -> FIFO takes 100@80 + 20@100
    await store.add_lot("SCHD", D("100"), D("80"), purchased_at=datetime(2024, 1, 1))
    await store.add_lot("SCHD", D("50"), D("100"), purchased_at=datetime(2024, 6, 1))
    # seed the paper position manually (the adapter has no lot import)
    from app.services.live_trading.broker_connector import BrokerPosition

    broker.adapter.positions["SCHD"] = BrokerPosition(
        symbol="SCHD",
        quantity=D("150"),
        avg_price=D("86.666667"),
        current_price=D("100"),
        market_value=D("15000"),
        unrealized_pl=D("500"),
        unrealized_pl_pct=D("3.4"),
    )

    sell = PlannedTrade(
        symbol="SCHD",
        side="SELL",
        quantity=D("120"),
        price=D("100"),
        value=D("12000"),
        reason="Selling the overweight back inside the band.",
    )
    executor = RebalanceExecutor(store, broker)
    outcome = await executor.execute(_plan(sell))

    assert outcome.ok, outcome.failed
    remaining = await store.get_lots("SCHD")
    assert len(remaining) == 1
    assert remaining[0].quantity == D("30")
    assert remaining[0].purchase_price == D("100")
    position = await broker.get_position("SCHD")
    assert position is not None and position.quantity == D("30")


async def test_dry_run_records_plan_but_places_nothing(store, broker):
    buy = PlannedTrade(
        symbol="BND",
        side="BUY",
        quantity=D("10"),
        price=D("80"),
        value=D("800"),
        reason="Dry run.",
    )
    executor = RebalanceExecutor(store, broker)
    outcome = await executor.execute(_plan(buy), dry_run=True)
    assert outcome.ok and not outcome.executed
    assert await broker.get_position("BND") is None
    events = await store.list_events()
    assert events[0]["action"] == "planned"
