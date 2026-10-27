"""Named paper portfolios — one engine instance per name.

A paper portfolio = a NAME + its own store database + its own paper
account state file + its starting cash. The engine (store, planner,
executor, broker) is reused VERBATIM per name — no schema changes, full
isolation between portfolios. The default name "main" maps to the
historical paths, so everything that existed before keeps working.

The user's rule this serves: from Agent Swarm a validated run must be
sendable to paper trading UNDER A NAME, and paper trading holds MORE
THAN ONE portfolio at once (each watched separately).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
DEFAULT_SLUG = "main"
_META_PREFIX = "paper_portfolio_"
_NAME_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """"Dividendos 2026!" → "dividendos-2026" (stable, filesystem-safe)."""
    slug = _NAME_RE.sub("-", str(name).strip().lower()).strip("-")
    if not slug:
        slug = f"portfolio-{datetime.utcnow():%Y%m%d%H%M%S}"
    return slug[:48]


def store_path(slug: str) -> Path:
    """:class:`PortfolioManagementStore` database for one portfolio."""
    if slug == DEFAULT_SLUG:
        return DATA_DIR / "portfolio_management.db"
    return DATA_DIR / f"portfolio_management_{slug}.db"


def paper_state_path(slug: str) -> Path:
    """Persisted paper-account snapshot for one portfolio."""
    from .paper_state import DEFAULT_PAPER_STATE_PATH

    if slug == DEFAULT_SLUG:
        return Path(DEFAULT_PAPER_STATE_PATH)
    return DATA_DIR / f"paper_account_{slug}.json"


def meta_path(slug: str) -> Path:
    return DATA_DIR / f"{_META_PREFIX}{slug}.json"


#: starting cash of a fresh paper portfolio (matches the historical default)
DEFAULT_INITIAL_CASH = Decimal("100000")


def create_portfolio(
    name: str,
    source_run_id: str = "",
    strategy_name: str = "",
    decision_status: str = "",
    initial_cash: Decimal = DEFAULT_INITIAL_CASH,
) -> dict[str, Any]:
    """Register a named portfolio (idempotent on the slug: re-creating
    keeps the existing account, only refreshes display metadata)."""
    slug = slugify(name)
    meta = {
        "slug": slug,
        "name": str(name).strip(),
        "source_run_id": source_run_id,
        "strategy_name": strategy_name,
        "decision_status": decision_status,
        "initial_cash": str(initial_cash),
        "created_at": datetime.utcnow().isoformat(),
    }
    existing = get_portfolio(slug)
    if existing:
        # same portfolio again: never silently reset the account
        meta["created_at"] = existing.get("created_at") or meta["created_at"]
        meta["initial_cash"] = existing.get("initial_cash") or meta["initial_cash"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    meta_path(slug).write_text(json.dumps(meta, indent=1))
    return meta


def get_portfolio(slug: str) -> dict[str, Any] | None:
    path = meta_path(slug)
    if not path.exists():
        return None
    try:
        meta = json.loads(path.read_text())
    except ValueError:
        return None
    meta.setdefault("slug", slug)
    meta.setdefault("name", slug)
    return meta


def list_portfolios() -> list[dict[str, Any]]:
    """Every portfolio, main first (it always exists, even without meta)."""
    out: list[dict[str, Any]] = []
    main_meta = get_portfolio(DEFAULT_SLUG)
    out.append(
        {
            "slug": DEFAULT_SLUG,
            "name": (main_meta or {}).get("name", "Main"),
            **{k: v for k, v in (main_meta or {}).items() if k not in ("slug", "name")},
        }
    )
    if DATA_DIR.is_dir():
        for path in sorted(DATA_DIR.glob(f"{_META_PREFIX}*.json")):
            slug = path.stem[len(_META_PREFIX) :]
            if slug == DEFAULT_SLUG:
                continue
            meta = get_portfolio(slug)
            if meta:
                out.append(meta)
    return out


def open_store(slug: str):
    """A :class:`PortfolioManagementStore` bound to this portfolio's db.

    Same construction the /portfolio page always used; CALL `await
    prepare_store(store)` (below) to create tables before first use.
    Returns (engine, store).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from . import store as store_module

    path = store_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    store = store_module.PortfolioManagementStore(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    return engine, store


async def prepare_store(engine) -> None:
    """Create the portfolio tables on this engine if missing (idempotent)."""
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


async def open_broker(slug: str, initial_cash: Decimal | None = None):
    """A paper :class:`BrokerConnector` restored from this portfolio's
    persisted account (cash + positions), auto-fill on — the exact recipe
    the /portfolio page uses, per portfolio."""
    from app.services.live_trading.broker_connector import (
        BrokerConnector,
        BrokerPosition,
        BrokerType,
    )
    from .paper_state import load_paper_state

    if initial_cash is None:
        meta = get_portfolio(slug)
        initial_cash = Decimal(str((meta or {}).get("initial_cash") or DEFAULT_INITIAL_CASH))
    connector = BrokerConnector(BrokerType.PAPER)
    connector.adapter.initial_cash = initial_cash
    connector.adapter.auto_fill_orders = True
    await connector.connect()
    state = load_paper_state(paper_state_path(slug))
    if state is not None and connector.adapter.account is not None:
        cash, positions = state
        connector.adapter.account.cash_available = cash
        for symbol, data in positions.items():
            quote = await connector.get_quote(symbol)
            price = quote.price if quote else data["avg_price"]
            quantity = data["quantity"]
            connector.adapter.positions[symbol] = BrokerPosition(
                symbol=symbol,
                quantity=quantity,
                avg_price=data["avg_price"],
                current_price=price,
                market_value=quantity * price,
                unrealized_pl=(price - data["avg_price"]) * quantity,
                unrealized_pl_pct=Decimal("0"),
            )
    return connector
