"""LSE Data adapter — optional, degrades to None without a key.

Coverage reality (checked 31-10): US/UK/Canadian stocks, FX, crypto,
futures, indices, commodities, US options. NO European exchanges yet
(Xetra/Euronext — where VWCE.AS/AGGH.AS/EUNL.DE live; "LSE/Eurex coming
soon"), so this adapter is for the US leg (SCHD, VYM, BND, SPY…) and
for DIVIDEND histories — our dividend ledger shows 'non-computable' on
every UCITS name, and ``dividends()``/``factors()`` are the fix when
they list Europe.

Data terms (lse-data LICENSE): research/trading use of retrieved data
is fine; redistribution is NOT — this adapter exists to enrich OUR
local corpus, never to republish. The client is MIT.

Requires: ``pip install lse-data`` and ``LSE_API_KEY`` in the env. No
key / no package → ``None`` everywhere, loudly logged once — never an
exception in the product path.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_warned = False


def _client() -> Any | None:
    """A live LSE client, or None (no key / no package — degraded)."""
    global _warned
    if not os.environ.get("LSE_API_KEY"):
        if not _warned:
            logger.info("LSE_DATA: no LSE_API_KEY in env — adapter disabled")
            _warned = True
        return None
    try:
        from lse import LSE
    except ImportError:
        if not _warned:
            logger.info("LSE_DATA: `pip install lse-data` to enable the adapter")
            _warned = True
        return None
    return LSE()


def available() -> bool:
    """True when the adapter can talk (key + package present)."""
    return _client() is not None


def dividends(symbol: str) -> list[dict[str, Any]] | None:
    """Dividend history [(ex_date, amount)] for a US-listed symbol."""
    client = _client()
    if client is None:
        return None
    try:
        return client.dividends(symbol)
    except Exception:  # noqa: BLE001 - a failed lookup never breaks the caller
        logger.warning("LSE_DATA dividends(%s) failed", symbol, exc_info=True)
        return None


def splits(symbol: str) -> list[dict[str, Any]] | None:
    client = _client()
    if client is None:
        return None
    try:
        return client.splits(symbol)
    except Exception:  # noqa: BLE001
        logger.warning("LSE_DATA splits(%s) failed", symbol, exc_info=True)
        return None


def backfill_daily_csv(symbol: str, out_dir: Path = _DATA_DIR / "historical") -> Path | None:
    """US backfill: full daily history as one of OUR canonical CSVs
    (date,open,high,low,close,volume) — the format DataLoader reads.

    Only overwrites when the fetched history STARTS EARLIER than the
    local file (extends history; never shortens a longer local series).
    """
    client = _client()
    if client is None:
        return None
    try:
        rows = client.candles(symbol, "1d", limit=5000, order="asc")
    except Exception:  # noqa: BLE001
        logger.warning("LSE_DATA candles(%s) failed", symbol, exc_info=True)
        return None
    if not rows:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}.csv"
    lines = ["date,open,high,low,close,volume"]
    for r in rows:
        lines.append(
            f"{str(r.get('timestamp'))[:10]},{r.get('open')},{r.get('high')},"
            f"{r.get('low')},{r.get('close')},{r.get('volume')}"
        )
    existing = path.read_text().splitlines() if path.exists() else []
    new_first = lines[1][:10] if len(lines) > 1 else "9999"
    old_first = existing[1][:10] if len(existing) > 1 else "9999"
    if new_first >= old_first and existing:
        logger.info("LSE_DATA: local %s starts earlier — kept", symbol)
        return None
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("LSE_DATA: wrote %s (%s rows)", path, len(rows))
    return path
