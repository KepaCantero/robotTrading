"""Durable state for the paper account (portfolio-management sessions).

PaperAdapter keeps cash and positions in memory, so the dashboard process
and the daily runner each used to own a DIFFERENT paper portfolio, and a
restart reset both. Until Fase 3 gives the product a real broker with a
server-side account, the portfolio-management loop snapshots the paper
account to a JSON file after every execution and restores it on connect —
one shared, restart-proof paper account.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.live_trading.broker_connector import BrokerPosition

logger = logging.getLogger(__name__)

DEFAULT_PAPER_STATE_PATH = "data/paper_account.json"


def save_paper_state(
    path: str | Path,
    cash: Decimal,
    positions: dict[str, "BrokerPosition"],
) -> None:
    state: dict[str, Any] = {
        "cash": str(cash),
        "positions": {
            symbol: {
                "quantity": str(position.quantity),
                "avg_price": str(position.avg_price),
            }
            for symbol, position in sorted(positions.items())
        },
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2))
    logger.debug("Paper state saved: cash=%s, %s position(s)", cash, len(positions))


def load_paper_state(
    path: str | Path,
    price_source=None,
) -> tuple[Decimal, dict[str, dict[str, Decimal]]] | None:
    """(cash, positions) from the snapshot, priced with the CURRENT quote
    so market values are real; None when no snapshot exists yet."""
    source = Path(path)
    if not source.exists():
        return None
    try:
        state = json.loads(source.read_text())
        cash = Decimal(str(state.get("cash", "0")))
        positions: dict[str, dict[str, Decimal]] = {}
        for symbol, data in (state.get("positions") or {}).items():
            positions[symbol.upper()] = {
                "quantity": Decimal(str(data.get("quantity", "0"))),
                "avg_price": Decimal(str(data.get("avg_price", "0"))),
            }
        return cash, positions
    except (ValueError, KeyError, TypeError, ArithmeticError):
        logger.exception("Corrupt paper state at %s — starting fresh", path)
        return None
