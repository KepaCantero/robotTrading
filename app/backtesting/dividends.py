"""Dividend distribution events, income ledger and metrics (Fase 4, D01/D04).

Separates RENTA (cash distributions actually collected) from RETURNS (price
appreciation): two portfolios with the same total return and different
distributions now produce different income metrics — the audited gap D01.

Honesty rules (plan §Fase 4):
- Events come from a real source (yfinance dividend history, downloaded by
  scripts/download_dividends.py to data/dividends/<SYMBOL>.csv). Missing
  files are MISSING DATA, never filled with constant yields (D04).
- Whatever cannot be computed is named in the report (coverage_gaps,
  assumptions); nothing is silently invented.
- Payment dates are not available from the free source: cash is credited at
  the ex-date and the assumption is recorded. Free-data limitation, shown
  not hidden (plan §5: "La indisponibilidad de datos gratuitos se mostrará
  como una limitación").
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

#: Repo's dividend-history corpus (one CSV per symbol: date,amount,currency).
DIVIDEND_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dividends"

#: Default withholding on US distributions for a Spanish resident with
#: W-8BEN in force (treaty rate). Per-symbol overrides possible; this is a
#: CONFIGURABLE assumption, always surfaced in the metrics.
DEFAULT_WITHHOLDING_RATE = Decimal("0.15")


@dataclass(frozen=True)
class DistributionEvent:
    """A per-share cash distribution, known as of `knowledge_date`.

    Free EOD sources publish the ex-date and the per-share amount; the pay
    date is generally unknown and stays None (credited at ex-date, flagged).
    """

    symbol: str
    ex_date: date
    amount_per_share: Decimal
    currency: str = "USD"
    source: str = "yfinance"
    knowledge_date: date | None = None
    pay_date: date | None = None

    def __post_init__(self) -> None:
        if self.amount_per_share <= 0:
            raise ValueError(
                f"non-positive distribution for {self.symbol}: {self.amount_per_share}"
            )


@dataclass
class SymbolDividendCoverage:
    """What we actually know about a symbol's distributions."""

    symbol: str
    has_data: bool = False
    events: int = 0
    first_date: date | None = None
    last_date: date | None = None


def load_distributions(symbol: str, data_dir: Path = DIVIDEND_DATA_DIR) -> list[DistributionEvent]:
    """Load a symbol's distribution history; empty list when no file exists.

    The empty list is an explicit coverage gap the caller must surface —
    never a placeholder yield.
    """
    path = data_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        return []
    events: list[DistributionEvent] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            events.append(
                DistributionEvent(
                    symbol=symbol.upper(),
                    ex_date=date.fromisoformat(row["date"]),
                    amount_per_share=Decimal(str(row["amount"])),
                    currency=row.get("currency") or "USD",
                    source=row.get("source") or "yfinance",
                )
            )
    events.sort(key=lambda e: e.ex_date)
    return events


def coverage(symbol: str, data_dir: Path = DIVIDEND_DATA_DIR) -> SymbolDividendCoverage:
    """Summarize known distribution data for one symbol."""
    events = load_distributions(symbol, data_dir)
    return SymbolDividendCoverage(
        symbol=symbol.upper(),
        has_data=bool(events),
        events=len(events),
        first_date=events[0].ex_date if events else None,
        last_date=events[-1].ex_date if events else None,
    )


@dataclass(frozen=True)
class LedgerEntry:
    """One collected (or missed) distribution against the executed book."""

    symbol: str
    ex_date: date
    units_entitled: Decimal
    amount_per_share: Decimal
    gross: Decimal
    withholding_rate: Decimal
    withholding: Decimal
    net: Decimal
    currency: str
    pay_date_known: bool = False


@dataclass
class DividendMetrics:
    """Income metrics, separate from total return (D01).

    `computable` is False when a held symbol lacks distribution data: the
    totals would silently understate income, so the report carries the gap
    instead of a made-up number.
    """

    gross_total: Decimal = Decimal("0")
    net_total: Decimal = Decimal("0")
    withholding_total: Decimal = Decimal("0")
    net_by_year: dict[int, Decimal] = field(default_factory=dict)
    events_collected: int = 0
    currency: str = "USD"
    computable: bool = True
    coverage_gaps: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def income_on_initial_capital(self, initial_capital: Decimal) -> Decimal | None:
        """Net collected income per unit of initial capital; None if unknown."""
        if initial_capital <= 0:
            return None
        return self.net_total / initial_capital


def units_held_at(trades, symbol: str, at: datetime) -> Decimal:
    """Executed units of `symbol` held at `at`, from the engine's canonical
    Trade records.

    The engine emits each position as ONE record: side=buy, entry_time =
    open, exit_time = close (a paired sell row repeats the same interval —
    it closes the buy, never opens a short on this long-only executor).
    A position contributes while entry_time <= at < exit_time.
    """
    held = Decimal("0")
    for trade in trades:
        if trade.symbol != symbol:
            continue
        if str(trade.side).lower() != "buy":
            continue
        if trade.entry_time <= at and (trade.exit_time is None or trade.exit_time > at):
            held += trade.quantity
    return held


class DividendLedger:
    """Accounting of collected distributions against the EXECUTED book.

    The strategy's internal wishes never enter here — only fills (the D05
    distinction between theoretical and executed positions).
    """

    def __init__(
        self,
        withholding_rate: Decimal = DEFAULT_WITHHOLDING_RATE,
        withholding_overrides: dict[str, Decimal] | None = None,
    ):
        self.withholding_rate = withholding_rate
        self.withholding_overrides = withholding_overrides or {}

    def record(
        self,
        trades,
        symbols: list[str],
        window_start: datetime,
        window_end: datetime,
        data_dir: Path = DIVIDEND_DATA_DIR,
    ) -> tuple[list[LedgerEntry], DividendMetrics]:
        """Collect every event in the window the executed book was entitled to.

        Returns the entries plus the income metrics with explicit coverage
        gaps for symbols without distribution data.
        """
        entries: list[LedgerEntry] = []
        metrics = DividendMetrics()
        metrics.assumptions.append(
            "payment dates unknown from the free source: cash credited at ex-date"
        )
        metrics.assumptions.append(
            f"withholding {self.withholding_rate:.0%} (configurable; treaty default)"
        )

        currencies: set[str] = set()
        for symbol in symbols:
            events = load_distributions(symbol, data_dir)
            if not events:
                metrics.coverage_gaps.append(
                    f"{symbol}: sin historial de distribuciones — renta no computable"
                )
                continue
            rate = self.withholding_overrides.get(symbol.upper(), self.withholding_rate)
            for event in events:
                if not (
                    window_start
                    <= datetime.combine(event.ex_date, datetime.min.time())
                    <= window_end
                ):
                    continue
                units = units_held_at(
                    trades, event.symbol, datetime.combine(event.ex_date, datetime.min.time())
                )
                if units <= 0:
                    continue
                gross = (units * event.amount_per_share).quantize(Decimal("0.01"))
                withholding = (gross * rate).quantize(Decimal("0.01"))
                entries.append(
                    LedgerEntry(
                        symbol=event.symbol,
                        ex_date=event.ex_date,
                        units_entitled=units,
                        amount_per_share=event.amount_per_share,
                        gross=gross,
                        withholding_rate=rate,
                        withholding=withholding,
                        net=gross - withholding,
                        currency=event.currency,
                        pay_date_known=event.pay_date is not None,
                    )
                )
                currencies.add(event.currency)

        metrics.gross_total = sum((e.gross for e in entries), Decimal("0"))
        metrics.withholding_total = sum((e.withholding for e in entries), Decimal("0"))
        metrics.net_total = sum((e.net for e in entries), Decimal("0"))
        metrics.events_collected = len(entries)
        for entry in entries:
            year = entry.ex_date.year
            metrics.net_by_year[year] = metrics.net_by_year.get(year, Decimal("0")) + entry.net
        if len(currencies) > 1:
            metrics.assumptions.append(
                f"multiple currencies {sorted(currencies)}: totals are a naive sum, no FX applied"
            )
        elif currencies:
            metrics.currency = next(iter(currencies))
        metrics.computable = not metrics.coverage_gaps
        return entries, metrics
