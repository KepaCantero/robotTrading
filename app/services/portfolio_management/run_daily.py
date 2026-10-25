"""Daily portfolio runner (paper): ``python -m app.services.portfolio_management.run_daily``

One session of the robo-advisor loop against the deterministic PaperAdapter
(first rung of the production ladder; the same service connects to IBKR
unchanged once Fase 3 lands its adapter):

1. Adopt a target if none is active (latest swarm winner, curated seed
   otherwise).
2. Read positions + cash from the broker, prices from real quotes.
3. Plan (cooldown → cash-first → tax-aware proactive) and print the
   plain-language summary with its tax impact.
4. ``--execute`` sends the diff-orders through the risk-gated order path;
   without it the run is a dry-run and only records the preview.

Exit codes: 0 clean (also when nothing needed doing), 1 partial failures,
2 the portfolio could not be read at all.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.agent_swarm.store import DEFAULT_SWARM_DB_PATH
from app.services.live_trading.broker_connector import BrokerConnector, BrokerType
from app.services.live_trading.order_manager import OrderManager

from .executor import RebalanceExecutor
from .models import ProfileAnswers
from .planner import PlanContext, plan_rebalance
from .store import PortfolioManagementStore
from .tax import SpainRebalanceTax
from .winner_adoption import adopt_target

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/portfolio_management.db"


def _async_url() -> str:
    """The configured application database, as an async URL."""
    from app.infrastructure.persistence.database import get_database_url

    url = get_database_url()
    if url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise ValueError(f"unsupported database URL for the async runner: {url!r}")


async def _ensure_tables(engine) -> None:
    """Create the three portfolio-management tables when the target schema
    does not exist yet (standalone DB file; the app DB goes via alembic)."""
    from app.infrastructure.persistence.database import Base

    from . import store as store_module

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all,
            tables=[
                store_module.TargetPortfolioRecord.__table__,
                store_module.PortfolioLotRecord.__table__,
                store_module.RebalanceEventRecord.__table__,
            ],
        )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily portfolio rebalance runner (paper)")
    parser.add_argument("--execute", action="store_true", help="send orders (default: dry-run)")
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="SQLite path for portfolio state (default: %(default)s)",
    )
    parser.add_argument(
        "--swarm-db",
        default=DEFAULT_SWARM_DB_PATH,
        help="swarm_runs.db path to adopt winners from",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    await _ensure_tables(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store_ = PortfolioManagementStore(session_factory)

    broker = BrokerConnector(BrokerType.PAPER)
    connected = await broker.connect()
    if not connected:
        logger.error("Could not connect the paper broker")
        return 2
    order_manager = OrderManager(broker=broker)

    # 1 ── target: adopt from the latest winner (or seed) when absent.
    target = await store_.get_active_target()
    if target is None:
        target = await adopt_target(
            store_,
            ProfileAnswers(),
            swarm_db_path=args.swarm_db,
        )
        logger.info(
            "No active target: adopted v%s (%s) from %s",
            target.version,
            ", ".join(h.symbol for h in target.holdings),
            target.source,
        )

    # 2 ── read the account: positions, cash, real prices.
    account = await broker.get_account_info()
    positions_map = await broker.get_positions()
    if account is None:
        logger.error("No paper account available")
        return 2
    positions = {p.symbol: p.market_value for p in positions_map.values()}
    prices: dict[str, Decimal] = {}
    for symbol in {h.symbol for h in target.holdings} | set(positions):
        quote = await broker.get_quote(symbol)
        if quote is not None:
            prices[symbol] = quote.price
    cash = account.cash_available

    # 3 ── plan.
    lots = await store_.get_lots()
    lots_by_symbol: dict[str, list] = {}
    for lot in lots:
        lots_by_symbol.setdefault(lot.symbol, []).append(lot)
    last_rebalance = await store_.last_rebalance_at()

    ctx = PlanContext(
        target=target,
        positions=positions,
        cash=cash,
        prices=prices,
        lots=lots_by_symbol,
        last_rebalance=last_rebalance,
    )
    tax = SpainRebalanceTax()
    plan = plan_rebalance(ctx, tax_preview=tax.preview_sell)

    print(f"\n=== Rebalance plan ({plan.status.value}, trigger {plan.trigger.value}) ===")
    print(plan.summary)
    for trade in plan.trades:
        tax_note = f" | tax ≈ €{trade.tax_impact.tax:.2f}" if trade.tax_impact else ""
        print(
            f"  {trade.side:4} {trade.quantity:>12} {trade.symbol}  ≈ €{trade.value:.2f}{tax_note}"
        )
        print(f"       {trade.reason}")
    for reason in plan.reasons:
        if reason not in {t.reason for t in plan.trades}:
            print(f"  · {reason}")

    # 4 ── execute or leave as a recorded preview.
    if plan.trades:
        executor = RebalanceExecutor(store_, broker, order_manager=order_manager)
        if args.execute:
            outcome = await executor.execute(plan)
            print(
                f"\nExecuted {len(outcome.executed)} order(s)"
                + (f", {len(outcome.failed)} FAILED" if outcome.failed else "")
            )
            for failure in outcome.failed:
                print(f"  ✗ {failure['symbol']}: {failure['error']}")
            await broker.disconnect()
            await engine.dispose()
            return 0 if outcome.ok else 1
        print("\nDry-run: pass --execute to send these orders through the risk gates.")

    await broker.disconnect()
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
