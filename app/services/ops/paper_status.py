"""Fase 6 parte 2 — local ops status aggregation.

One honest answer to "is the paper stack healthy?" built from REAL
sources only:

- **database** — can we actually query the live-trading tables?
- **uncertain orders** — intents whose outcome is still unknown
  (PENDING/SUBMITTED/ACKNOWLEDGED) and old enough that silence is a
  signal, not patience.
- **accounting divergence** — orders marked executed WITHOUT fills, and
  fills whose quantity doesn't sum to the ordered quantity.
- **quote staleness** — the freshest EOD bar in the local corpus; a
  corpus older than a week means the data pipeline is broken.
- **tasks** — the paper stack deploys NO scheduler/executor yet (F6 v1
  removed the fake workers); reported as ``not_deployed`` instead of a
  fabricated heartbeat. When the portfolio runner lands (ROBO P5) this
  becomes its heartbeat table.

Nothing here mutates state and nothing invents numbers: a check that
cannot run says so.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.services.live_trading.trade_persistence import OrderRecord, TradeRecord

logger = logging.getLogger(__name__)

#: outcomes that are legitimately unknown YET — beyond this age, silence
#: needs an operator's eyes (a paper fill resolves in seconds)
UNCERTAIN_STATES = ("PENDING", "SUBMITTED", "ACKNOWLEDGED")
UNCERTAIN_AFTER_MINUTES = 10

#: the local corpus refreshes weekly; older than this = pipeline broken
STALE_CORPUS_DAYS = 5

#: statuses that claim money moved — they MUST have fills
_EXECUTED_STATES = ("EXECUTED", "FILLED")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def newest_bar_age_days(data_dir: Path) -> float | None:
    """Age (days) of the newest EOD bar across the corpus, or None.

    Reads only each CSV's last line — the corpus is 700+ files and only
    the freshest date matters.
    """
    newest: datetime | None = None
    if not data_dir.is_dir():
        return None
    for csv_path in data_dir.glob("*.csv"):
        try:
            with csv_path.open("rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 256))
                tail = fh.read().decode("utf-8", errors="ignore").strip().splitlines()
            last = tail[-1].split(",")[0]
            stamp = datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if newest is None or stamp > newest:
                newest = stamp
        except (OSError, IndexError, ValueError):
            continue
    if newest is None:
        return None
    return (_utcnow() - newest).total_seconds() / 86400


async def collect_status(session_factory, data_dir: Path) -> dict[str, Any]:
    """Aggregate every ops signal from real sources. Never raises."""
    report: dict[str, Any] = {
        "timestamp": _utcnow().isoformat(),
        "database": {"status": "unknown"},
        "uncertain_orders": {"status": "unknown"},
        "accounting_divergence": {"status": "unknown"},
        "quote_staleness": {"status": "unknown"},
        "tasks": {
            "status": "not_deployed",
            "message": "no scheduler/executor in the paper stack (F6 v1 removed the fake workers)",
        },
    }
    degraded = False

    # ── database + order/live-trading signals ─────────────────────────
    try:
        async with session_factory() as session:
            await session.execute(select(1))

            cutoff = _utcnow() - timedelta(minutes=UNCERTAIN_AFTER_MINUTES)
            uncertain = (
                (
                    await session.execute(
                        select(OrderRecord)
                        .where(OrderRecord.status.in_(UNCERTAIN_STATES))
                        .where(OrderRecord.created_at < cutoff)
                    )
                )
                .scalars()
                .all()
            )
            report["uncertain_orders"] = {
                "status": "degraded" if uncertain else "healthy",
                "count": len(uncertain),
                "oldest_created_at": (
                    min(o.created_at for o in uncertain).isoformat() if uncertain else None
                ),
                "symbols": sorted({o.symbol for o in uncertain}),
            }
            degraded = degraded or bool(uncertain)

            executed = (
                (
                    await session.execute(
                        select(OrderRecord).where(OrderRecord.status.in_(_EXECUTED_STATES))
                    )
                )
                .scalars()
                .all()
            )
            missing_fills = []
            quantity_mismatch = []
            for order in executed:
                fills = (
                    (
                        await session.execute(
                            select(TradeRecord).where(TradeRecord.order_id == order.order_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                if not fills:
                    missing_fills.append(order.order_id)
                else:
                    filled_qty = sum(f.quantity for f in fills)
                    if filled_qty != order.quantity:
                        quantity_mismatch.append(order.order_id)
            divergence = {
                "executed_without_fills": missing_fills,
                "fill_quantity_mismatch": quantity_mismatch,
            }
            has_divergence = bool(missing_fills or quantity_mismatch)
            report["accounting_divergence"] = {
                "status": "degraded" if has_divergence else "healthy",
                **divergence,
            }
            degraded = degraded or has_divergence
        report["database"] = {"status": "healthy"}
    except Exception as exc:  # noqa: BLE001 - the panel must answer, not crash
        report["database"] = {"status": "unhealthy", "error": str(exc)[:200]}
        return {**report, "status": "unhealthy"}

    # ── corpus freshness (filesystem, not DB) ──────────────────────────
    age = newest_bar_age_days(data_dir)
    if age is None:
        report["quote_staleness"] = {"status": "unknown", "message": "no corpus found"}
    else:
        stale = age > STALE_CORPUS_DAYS
        report["quote_staleness"] = {
            "status": "degraded" if stale else "healthy",
            "newest_bar_age_days": round(age, 2),
            "threshold_days": STALE_CORPUS_DAYS,
        }
        degraded = degraded or stale

    return {**report, "status": "degraded" if degraded else "healthy"}
