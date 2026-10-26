"""Bloque 1 — point-in-time fundamentals from the SimFin corpus.

The PIT contract: a figure becomes visible ONLY from its Publish Date.
Every accessor returns the value AND the publish date it became known,
and refuses (None) anything published after the requested date — the
anti-look-ahead guarantee the backtest depends on (D04 applied to
fundamentals).

Corpus: data/fundamentals/*.csv via scripts/download_simfin.py
(free-tier SimFin; key in SIMFIN_API_KEY env, never in the repo).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "fundamentals"


@dataclass(frozen=True)
class Fundamental:
    """One published figure with the date it BECAME known."""

    ticker: str
    field: str
    value: Decimal
    report_date: date  # fiscal period the figure describes
    publish_date: date  # the day the market could first see it

    @property
    def is_visible_on(self, as_of: date) -> bool:
        return self.publish_date <= as_of


def _to_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.split(" ")[0], fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


class FundamentalsSource:
    """PIT reader over the SimFin statement corpus (CSV, no network).

    >>> src = FundamentalsSource("us-income-annual")
    >>> f = src.figure("AAPL", "Revenue", date(2020, 2, 1))
    >>> f.value, f.publish_date  # FY2019 revenue, published 2019-10-30
    """

    def __init__(self, dataset: str = "us-income-annual", data_dir: Path | None = None):
        self.path = (data_dir or _DATA_DIR) / f"{dataset}.csv"
        self.dataset = dataset
        #: ticker -> [(publish_date, report_date, field, value), ...] sorted
        self._rows: dict[str, list[tuple]] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded or not self.path.exists():
            self._loaded = True
            return
        with self.path.open() as fh:
            for row in csv.DictReader(fh):
                ticker = (row.get("Ticker") or "").strip().upper()
                publish = _to_date(row.get("Publish Date") or "")
                report = _to_date(row.get("Report Date") or "")
                if not ticker or publish is None or report is None:
                    continue
                for field, raw in row.items():
                    if field in (
                        "Ticker",
                        "Report Date",
                        "Publish Date",
                        "Restated Date",
                        "SimFinId",
                        "Currency",
                        "Fiscal Year",
                        "Fiscal Period",
                    ):
                        continue
                    try:
                        value = Decimal(str(raw))
                    except (InvalidOperation, TypeError, ValueError):
                        continue
                    self._rows.setdefault(ticker, []).append((publish, report, field, value))
        for rows in self._rows.values():
            rows.sort(key=lambda r: (r[0], r[1]))
        self._loaded = True

    def figure(self, ticker: str, field: str, as_of: date) -> Fundamental | None:
        """Latest PUBLISHED value of `field` for `ticker` as of `as_of`.

        Returns None when the ticker/field has nothing published by then
        (missing data stays missing — never interpolated, never future).
        """
        self._load()
        if not self._rows:
            return None
        field = field.strip()
        best: tuple | None = None
        for publish, report, name, value in self._rows.get(ticker.upper(), ()):
            if name != field or publish > as_of:
                continue
            # latest publish wins; same publish → latest report
            if best is None or (publish, report) >= (best[0], best[1]):
                best = (publish, report, value)
        if best is None:
            return None
        publish, report, value = best
        return Fundamental(
            ticker=ticker.upper(),
            field=field,
            value=value,
            report_date=report,
            publish_date=publish,
        )

    def figure_history(self, ticker: str, field: str, as_of: date) -> list[Fundamental]:
        """All figures of `field` published on/before `as_of`, oldest first."""
        self._load()
        out: list[Fundamental] = []
        for publish, report, name, value in self._rows.get(ticker.upper(), ()):
            if name == field.strip() and publish <= as_of:
                out.append(Fundamental(ticker.upper(), field.strip(), value, report, publish))
        return out

    def tickers(self) -> list[str]:
        self._load()
        return sorted(self._rows)

    def coverage(self, ticker: str) -> dict:
        """First/last publish dates for a ticker — gaps visible."""
        self._load()
        rows = self._rows.get(ticker.upper(), [])
        if not rows:
            return {"ticker": ticker.upper(), "rows": 0, "first": None, "last": None}
        return {
            "ticker": ticker.upper(),
            "rows": len(rows),
            "first": min(r[0] for r in rows).isoformat(),
            "last": max(r[0] for r in rows).isoformat(),
        }
