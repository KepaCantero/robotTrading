"""Bloque 3 — PIT FX history and rate differentials from the local corpus.

Replaces the invented constants (EUR/USD 1.08, USD/JPY 150.0…) in every
data-facing path with the downloaded ECB/FRED corpus:

- ``data/fx/<PAIR>.csv``  — daily closes (date,close), ECB-derived
- ``data/rates/<CCY>.csv`` — policy/interbank rates (date,rate_pct)

Strict by design (D04): a pair/currency/date the corpus cannot answer
returns ``None`` — callers decide, numbers are never invented. Every
answer carries its OBSERVATION date so point-in-time honesty is visible:
asking for 2024-07-14 (a Sunday) returns Friday's fix LABELLED as such.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

#: how stale an FX observation may be before it stops answering (FX fixes
#: are daily business-day; >7d means the corpus itself has a hole)
_MAX_FX_AGE_DAYS = 7
#: policy/interbank series are monthly — a quarter of staleness is data
#: lag, not invention (the observation date is still returned)
_MAX_RATE_AGE_DAYS = 120


@dataclass(frozen=True)
class FxPoint:
    """One observed value with the date it was FIXED (not asked for)."""

    rate: Decimal
    observed: date

    @property
    def age_days(self) -> int:
        return (date.today() - self.observed).days


class FxHistory:
    """Point-in-time FX and rate lookups over the local corpus.

    >>> fx = FxHistory()
    >>> p = fx.rate("USDJPY", date(2024, 1, 15))
    >>> p.rate, p.observed  # the fix of Jan 15 (or the last one before)
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or _DATA_DIR
        self._fx: dict[str, list[tuple[date, Decimal]]] = {}
        self._rates: dict[str, list[tuple[date, Decimal]]] = {}

    # ------------------------------------------------------------------
    def _load_series(self, folder: str, key: str) -> list[tuple[date, Decimal]]:
        cache = self._fx if folder == "fx" else self._rates
        if key in cache:
            return cache[key]
        path = self.data_dir / folder / f"{key}.csv"
        rows: list[tuple[date, Decimal]] = []
        if path.exists():
            with path.open() as fh:
                for row in csv.DictReader(fh):
                    try:
                        rows.append(
                            (
                                date.fromisoformat(row["date"]),
                                Decimal(row["close" if folder == "fx" else "rate_pct"]),
                            )
                        )
                    except (KeyError, ValueError):
                        continue
        rows.sort()
        cache[key] = rows
        return rows

    # ------------------------------------------------------------------
    def rate(self, pair: str, as_of: date) -> FxPoint | None:
        """Last known close for `pair` on/before `as_of`, or None.

        Pairs use CCY1CCY2 format (USDJPY). None means MISSING DATA —
        the caller must fail or degrade loudly, never substitute.
        """
        rows = self._load_series("fx", pair.upper().replace("/", ""))
        if not rows:
            return None
        chosen: tuple[date, Decimal] | None = None
        for d, value in rows:
            if d <= as_of:
                chosen = (d, value)
            else:
                break
        if chosen is None:
            return None
        observed, value = chosen
        if (as_of - observed).days > _MAX_FX_AGE_DAYS:
            return None  # corpus hole, not a stale-but-usable fix
        return FxPoint(rate=value, observed=observed)

    def policy_rate(self, currency: str, as_of: date) -> FxPoint | None:
        """Last KNOWN policy/interbank rate (percent) on/before `as_of`."""
        rows = self._load_series("rates", currency.upper())
        if not rows:
            return None
        chosen: tuple[date, Decimal] | None = None
        for d, value in rows:
            if d <= as_of:
                chosen = (d, value)
            else:
                break
        if chosen is None:
            return None
        observed, value = chosen
        if (as_of - observed).days > _MAX_RATE_AGE_DAYS:
            return None
        return FxPoint(rate=value, observed=observed)

    def carry_differential(self, pair: str, as_of: date) -> FxPoint | None:
        """Interest differential (base − quote, percentage points) for a pair.

        Market convention for BASE/QUOTE: LONG the pair holds the base
        currency, so positive ⇒ a long position EARNS carry (2024 USD/JPY ≈
        +5.3pp: long USD vs JPY). Any missing leg → None (D04: no invented
        spreads).
        """
        pair = pair.upper().replace("/", "")
        base, quote = pair[:3], pair[3:]
        long_leg = self.policy_rate(base, as_of)
        short_leg = self.policy_rate(quote, as_of)
        if long_leg is None or short_leg is None:
            return None
        return FxPoint(
            rate=long_leg.rate - short_leg.rate,
            observed=min(long_leg.observed, short_leg.observed),
        )

    # ------------------------------------------------------------------
    def coverage(self) -> dict[str, dict]:
        """First/last/rows per series — gaps visible, never interpolated."""
        out: dict[str, dict] = {"fx": {}, "rates": {}}
        for folder, keys in (("fx", self._fx), ("rates", self._rates)):
            for key, rows in keys.items():
                out[folder][key] = {
                    "rows": len(rows),
                    "first": rows[0][0].isoformat() if rows else None,
                    "last": rows[-1][0].isoformat() if rows else None,
                }
        return out


def latest_rate(pair: str, as_of: datetime | date | None = None) -> FxPoint | None:
    """Convenience: freshest fix for `pair` (paper/live paths)."""
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    return FxHistory().rate(pair, as_of or date.today())


def _days_ago(n: int) -> date:
    return date.today() - timedelta(days=n)
