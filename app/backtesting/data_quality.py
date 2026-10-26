"""Fase A (GATE_CALIDAD_DATOS_Y_OPTIMIZE) — data coverage gate.

Root fix for the silent-truncation class of bug: a CSV that starts late
used to be quietly clipped to whatever it had, and a symbol without data
vanished behind a `continue` — the exact recipe behind dishonest numbers
(dividends "+114.9%" measured over windows the data never covered).

`scan_data_coverage` reads ONLY the date column (cheap: `usecols`) and
answers, per symbol: does the CSV exist, where does it start/end, how
many rows fall inside the EXECUTION window, and does it cover the
window's start. The orchestrator runs this BEFORE loading quotes and
refuses (STRICT by default) when a requested symbol can't cover the
window — with the exact repair command in the error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass
class SymbolCoverage:
    """Coverage of one symbol's CSV against a requested window."""

    symbol: str
    csv_exists: bool = False
    first_date: datetime | None = None
    last_date: datetime | None = None
    rows_in_execution_window: int = 0
    #: True when first_date <= execution_start (the window is fully covered
    #: from its beginning; warm-up NEVER counts — it is best-effort)
    covers_window: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "csv_exists": self.csv_exists,
            "first_date": self.first_date.isoformat() if self.first_date else None,
            "last_date": self.last_date.isoformat() if self.last_date else None,
            "rows_in_execution_window": self.rows_in_execution_window,
            "covers_window": self.covers_window,
        }


@dataclass
class DataQualityReport:
    """Coverage of every requested symbol for one backtest run."""

    symbols: list[SymbolCoverage] = field(default_factory=list)
    execution_start: datetime | None = None
    execution_end: datetime | None = None

    @property
    def missing_symbols(self) -> list[str]:
        return [s.symbol for s in self.symbols if not s.csv_exists]

    @property
    def uncovered_symbols(self) -> list[str]:
        """Requested symbols whose data exists but starts too late."""
        return [s.symbol for s in self.symbols if s.csv_exists and not s.covers_window]

    def to_dict(self) -> dict:
        return {
            "execution_start": self.execution_start.isoformat() if self.execution_start else None,
            "execution_end": self.execution_end.isoformat() if self.execution_end else None,
            "missing_symbols": self.missing_symbols,
            "uncovered_symbols": self.uncovered_symbols,
            "symbols": [s.to_dict() for s in self.symbols],
        }


class InsufficientDataError(ValueError):
    """A requested symbol cannot cover the execution window.

    The message is ACTIONABLE: it names the symbol, what is available vs
    what was requested, and the repair command — so the fix is one copy
    paste away instead of an archaeology session.
    """

    def __init__(self, report: DataQualityReport, reason: str):
        self.report = report
        self.reason = reason
        missing = ", ".join(report.missing_symbols) or "—"
        uncovered: list[str] = []
        for s in report.symbols:
            if s.csv_exists and not s.covers_window and s.first_date is not None:
                uncovered.append(f"{s.symbol} (datos desde {s.first_date.date().isoformat()})")
        wanted = report.execution_start.date().isoformat() if report.execution_start else "?"
        super().__init__(
            f"{reason}. Ventana de ejecución pedida desde {wanted}. "
            f"Sin CSV: [{missing}]. Empiezan tarde: [{', '.join(uncovered) or '—'}]. "
            "Reparar con: python scripts/download_market_data.py --symbols "
            f"{','.join(report.missing_symbols + report.uncovered_symbols) or 'SIMBOLOS'}"
        )


def scan_data_coverage(
    symbols: list[str],
    base_path: Path,
    execution_start: datetime,
    execution_end: datetime,
    warmup_start: datetime | None = None,
) -> DataQualityReport:
    """Read only the date column of each CSV and report window coverage.

    Cheap by design: `pd.read_csv(usecols=[0])` on the date column only —
    no OHLC parsing, no Decimal conversion. `warmup_start` is accepted for
    context but warm-up coverage NEVER gates (best-effort by plan).
    """
    report = DataQualityReport(execution_start=execution_start, execution_end=execution_end)
    for symbol in symbols:
        entry = SymbolCoverage(symbol=symbol)
        path = base_path / f"{symbol.upper()}.csv"
        if not path.exists():
            report.symbols.append(entry)
            continue
        entry.csv_exists = True
        try:
            df = pd.read_csv(path, usecols=[0])
            date_col = df.columns[0]
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        except (OSError, ValueError, KeyError):
            report.symbols.append(entry)
            continue
        if dates.empty:
            report.symbols.append(entry)
            continue
        entry.first_date = dates.iloc[0].to_pydatetime()
        entry.last_date = dates.iloc[-1].to_pydatetime()
        in_window = dates[
            (dates >= pd.Timestamp(execution_start)) & (dates <= pd.Timestamp(execution_end))
        ]
        entry.rows_in_execution_window = int(len(in_window))
        entry.covers_window = bool(
            entry.first_date <= execution_start and entry.rows_in_execution_window > 0
        )
        report.symbols.append(entry)
    return report
