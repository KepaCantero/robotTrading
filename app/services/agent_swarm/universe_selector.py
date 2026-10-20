"""Automatic run-universe derivation from the local CSV corpus.

When a swarm request carries no explicit symbols the universe is derived
from the CSVs in ``data/historical``: a deterministic quality screen
(minimum history, freshness, liquidity floor) followed by a top-K ranking
by average dollar volume. Every decision the screen makes is reported
(scanned / kept / dropped per reason) so logs and the UI can show exactly
what was picked and why.

``DEFAULT_UNIVERSE`` (the historical 10-symbol showcase list) lives here as
the last-resort fallback when the corpus is empty or unreadable.

Caveat: dollar volume is measured in each symbol's native currency, so the
ranking compares nominal traded value across currencies (a ¥-quoted share
out-ranks an economically similar €-quoted one). For a top-K liquidity
screen that distortion is acceptable; the goal is to surface investable,
liquid names, not to price anything.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

#: default corpus location — the same relative path DataLoader uses
DEFAULT_DATA_DIR = Path("data/historical")

#: last-resort universe when the corpus is empty or unreadable
DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "SAN",
    "ITX.MC",
    "MC.PA",
    "SAP.DE",
    "6758.T",
    "SPY",
    "IBEX",
]

#: how many symbols an auto-picked universe contains
AUTO_UNIVERSE_SIZE = 30
#: minimum bar count to trade a symbol automatically (~2 years daily)
MIN_BARS = 500
#: a CSV whose last bar is older than this is stale and never auto-traded
MAX_STALE_DAYS = 120
#: liquidity floor: average daily traded value (close × volume) of the
#: recent window, in the symbol's native currency
MIN_DOLLAR_VOLUME = 1_000_000.0
#: trailing window (bars) used to measure recent liquidity (~1 year daily)
LIQUIDITY_WINDOW = 252

#: columns read from each CSV — nothing else enters memory
_USECOLS = ["date", "Close", "Volume"]


@dataclass(frozen=True)
class CorpusSymbol:
    """Quality metrics of one CSV in the corpus."""

    symbol: str
    first_date: date
    last_date: date
    bars: int
    avg_dollar_volume: float


@dataclass(frozen=True)
class CorpusScan:
    """Full scan of one corpus folder (cached per process)."""

    symbols: tuple[CorpusSymbol, ...]
    unreadable: tuple[str, ...]

    @property
    def symbol_names(self) -> list[str]:
        return [s.symbol for s in self.symbols]


@dataclass(frozen=True)
class AutoUniverseResult:
    """Outcome of the automatic universe screen, diagnostics included."""

    symbols: list[str]
    scanned: int
    kept: int
    dropped: dict[str, int]
    fallback_used: bool

    def summary(self) -> str:
        one_liner = "auto universe: "
        if self.fallback_used:
            return one_liner + f"corpus unusable ({self.scanned} CSVs) -> fallback DEFAULT_UNIVERSE"
        dropped = ", ".join(
            f"{count} {reason}" for reason, count in sorted(self.dropped.items()) if count
        )
        return (
            one_liner
            + f"{self.scanned} CSVs scanned -> {self.kept} valid"
            + (f" (dropped: {dropped})" if dropped else "")
            + f" -> top {len(self.symbols)} by liquidity"
        )


def corpus_symbol_names(data_dir: Path | str = DEFAULT_DATA_DIR) -> list[str]:
    """Symbol names of every CSV in the corpus (glob only, no reading)."""
    folder = Path(data_dir)
    if not folder.is_dir():
        return []
    return sorted(path.stem.upper() for path in folder.glob("*.csv"))


@lru_cache(maxsize=4)
def scan_corpus(data_dir: Path) -> CorpusScan:
    """Scan every CSV in ``data_dir`` and compute per-symbol metrics.

    Expensive (~seconds over the full corpus): read once per process and
    reuse through the cache. Files that are not readable OHLCV CSVs are
    reported in ``unreadable`` instead of failing the scan.
    """
    symbols: list[CorpusSymbol] = []
    unreadable: list[str] = []
    if not data_dir.is_dir():
        logger.warning("Corpus folder %s does not exist", data_dir)
        return CorpusScan(symbols=(), unreadable=())

    for csv_path in sorted(data_dir.glob("*.csv")):
        try:
            frame = pd.read_csv(csv_path, usecols=_USECOLS)
            dates = pd.to_datetime(frame["date"])
            window = frame.tail(LIQUIDITY_WINDOW)
            avg_volume = float((window["Close"] * window["Volume"]).mean())
        except (ValueError, KeyError, pd.errors.ParserError):
            unreadable.append(csv_path.stem.upper())
            continue
        if frame.empty or math.isnan(avg_volume):
            unreadable.append(csv_path.stem.upper())
            continue
        symbols.append(
            CorpusSymbol(
                symbol=csv_path.stem.upper(),
                first_date=dates.min().date(),
                last_date=dates.max().date(),
                bars=len(frame),
                avg_dollar_volume=avg_volume,
            )
        )
    logger.info(
        "Corpus scan of %s: %d readable, %d unreadable",
        data_dir,
        len(symbols),
        len(unreadable),
    )
    return CorpusScan(symbols=tuple(symbols), unreadable=tuple(unreadable))


def auto_universe(
    data_dir: Path | str = DEFAULT_DATA_DIR,
    k: int = AUTO_UNIVERSE_SIZE,
    today: date | None = None,
) -> AutoUniverseResult:
    """Derive the run universe from the corpus (deterministic).

    Filters: enough history (``MIN_BARS``), fresh data (``MAX_STALE_DAYS``),
    enough liquidity (``MIN_DOLLAR_VOLUME``); then ranks the survivors by
    average dollar volume (ties broken alphabetically) and keeps the top
    ``k``. Falls back to ``DEFAULT_UNIVERSE`` — loudly — when nothing
    survives the screen.
    """
    effective_today = today or date.today()
    scan = scan_corpus(Path(data_dir))
    dropped: dict[str, int] = {
        "unreadable": len(scan.unreadable),
        "short-history": 0,
        "stale": 0,
        "illiquid": 0,
    }
    candidates: list[CorpusSymbol] = []
    for sym in scan.symbols:
        if sym.bars < MIN_BARS:
            dropped["short-history"] += 1
        elif (effective_today - sym.last_date).days > MAX_STALE_DAYS:
            dropped["stale"] += 1
        elif sym.avg_dollar_volume < MIN_DOLLAR_VOLUME:
            dropped["illiquid"] += 1
        else:
            candidates.append(sym)

    scanned = len(scan.symbols) + len(scan.unreadable)
    if not candidates:
        logger.warning(
            "Auto universe: no valid symbols among %d CSVs in %s -> DEFAULT_UNIVERSE",
            scanned,
            data_dir,
        )
        return AutoUniverseResult(
            symbols=list(DEFAULT_UNIVERSE),
            scanned=scanned,
            kept=0,
            dropped=dropped,
            fallback_used=True,
        )

    ranked = sorted(candidates, key=lambda s: (-s.avg_dollar_volume, s.symbol))
    picked = [s.symbol for s in ranked[:k]]
    return AutoUniverseResult(
        symbols=picked,
        scanned=scanned,
        kept=len(candidates),
        dropped=dropped,
        fallback_used=False,
    )
