"""Convert the Kaggle news archive into daily per-symbol sentiment series.

Input: the archive-4 CSVs (analyst_ratings_processed.csv /
raw_analyst_ratings.csv / raw_partner_headlines.csv from the Kaggle
analyst-ratings / financial-news datasets): one headline per row with a
text column (title or headline), a date, and a stock/symbol column.
~1.4M headlines covering roughly 2009-2020.

Output: data/news_sentiment/<SYMBOL>.csv — one row per day:
date,news_count,sentiment_mean,sentiment_sum. The mean/sum are over
headline scores in [-1, 1], so any backtest can join on date and treat
them as point-in-time news tone; NewsEventHandler-style EMA smoothing can
run on top. news_count alone (coverage volume) is already a signal.

Scoring is a finance-tuned lexicon with negation ("not profitable") and
intensifier ("sharply higher") handling, implemented in-repo: no new
dependencies, deterministic, unit-testable. It is a v1 — good enough to
gate backtests on news tone; to upgrade, replace score_headline() with
FinBERT and keep this output schema.

Usage:
    python scripts/import_news_archive.py --csv ~/Downloads/archive-4/analyst_ratings_processed.csv
    python scripts/import_news_archive.py --csv <file> --symbols AAPL TSLA GE
    python scripts/import_news_archive.py --csv <file> --symbols ... --dry-run
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "news_sentiment"

TEXT_COLUMNS = ("title", "headline", "text")
SYMBOL_COLUMNS = ("stock", "symbol", "ticker")
DATE_COLUMNS = ("date", "datetime", "published", "published_at")

# Finance-tuned polarity lexicon (|score| <= 1). Kept small on purpose:
# every entry must earn its place against real headlines.
LEXICON: dict[str, float] = {
    # strong positive
    "surge": 1.0,
    "surges": 1.0,
    "surged": 1.0,
    "soar": 1.0,
    "soars": 1.0,
    "soared": 1.0,
    "skyrocket": 1.0,
    "rally": 0.9,
    "rallies": 0.9,
    "record-high": 1.0,
    "outperform": 0.9,
    "upgrade": 0.9,
    "upgraded": 0.9,
    "upgrades": 0.9,
    "bullish": 0.9,
    "blowout": 0.9,
    # positive
    "rises": 0.6,
    "rise": 0.6,
    "rose": 0.6,
    "gains": 0.6,
    "gain": 0.6,
    "gained": 0.6,
    "climbs": 0.6,
    "climbed": 0.6,
    "grows": 0.6,
    "beats": 0.7,
    "beat": 0.7,
    "tops": 0.6,
    "profit": 0.5,
    "profits": 0.5,
    "profitable": 0.5,
    "raises": 0.5,
    "boost": 0.6,
    "boosts": 0.6,
    "wins": 0.6,
    "approval": 0.6,
    "expands": 0.5,
    "improves": 0.6,
    "upbeat": 0.7,
    "recover": 0.6,
    "recovers": 0.6,
    "rebound": 0.6,
    "rebounds": 0.6,
    "highs": 0.5,
    "strong": 0.5,
    "higher": 0.4,
    "growth": 0.5,
    "dividend": 0.3,
    "buyback": 0.5,
    # negative
    "falls": -0.6,
    "fall": -0.6,
    "fell": -0.6,
    "drops": -0.6,
    "drop": -0.6,
    "dropped": -0.6,
    "declines": -0.6,
    "decline": -0.6,
    "loses": -0.6,
    "loss": -0.5,
    "losses": -0.6,
    "cuts": -0.6,
    "cut": -0.5,
    "slashes": -0.8,
    "misses": -0.7,
    "miss": -0.7,
    "missed": -0.7,
    "warns": -0.7,
    "weak": -0.6,
    "lower": -0.4,
    "layoffs": -0.7,
    "restructuring": -0.4,
    "dips": -0.4,
    "unprofitable": -0.5,
    "slides": -0.6,
    "concern": -0.5,
    "concerns": -0.5,
    "probe": -0.6,
    "investigation": -0.6,
    "lawsuit": -0.6,
    "sued": -0.6,
    "recall": -0.6,
    "downside": -0.5,
    "lows": -0.5,
    "lowered": -0.5,
    # strong negative
    "plunge": -1.0,
    "plunges": -1.0,
    "plunged": -1.0,
    "crash": -1.0,
    "crashes": -1.0,
    "crashed": -1.0,
    "collapse": -0.9,
    "collapses": -0.9,
    "tumbles": -0.9,
    "tumble": -0.9,
    "sinks": -0.9,
    "sink": -0.9,
    "slump": -0.8,
    "slumps": -0.8,
    "bankruptcy": -1.0,
    "bankrupt": -1.0,
    "downgrade": -0.9,
    "downgraded": -0.9,
    "downgrades": -0.9,
    "bearish": -0.9,
    "fraud": -1.0,
    "halted": -0.8,
    "delisted": -0.9,
}

NEGATORS = {"not", "no", "n't", "without", "fails", "fail", "lacks", "denies"}
INTENSIFIERS = {"sharply", "significantly", "strongly", "dramatically", "massively"}

_WORD_RE = re.compile(r"[a-z'-]+")


def score_headline(text: str) -> float:
    """Lexicon sentiment for one headline, in [-1, 1].

    Word polarities are summed with negation (sign flip on the following
    scored word) and intensifier (x1.5) handling, then squashed with
    tanh so long headlines cannot overflow the [-1, 1] range. Headlines
    with no lexicon hits score 0.0 (neutral).
    """
    total = 0.0
    negate = False
    intensity = 1.0
    for word in _WORD_RE.findall(text.lower()):
        if word in NEGATORS:
            negate = True
            continue
        if word in INTENSIFIERS:
            intensity = 1.5
            continue
        polarity = LEXICON.get(word)
        if polarity is None:
            continue
        total += polarity * intensity * (-1.0 if negate else 1.0)
        negate = False
        intensity = 1.0
    return math.tanh(total / 2.0)


def _pick_column(columns: list[str], candidates: tuple[str, ...]) -> str:
    """First column matching any candidate name, case/space-insensitive."""
    normalized = {str(column).strip().lower().replace(" ", "_"): column for column in columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    raise ValueError(f"no {candidates} column found in {list(columns)}")


def _load_headlines(path: Path, symbols: set[str] | None) -> pd.DataFrame:
    """Read one archive file into (symbol, date, score) rows."""
    frame = pd.read_csv(path)
    text_column = _pick_column(list(frame.columns), TEXT_COLUMNS)
    symbol_column = _pick_column(list(frame.columns), SYMBOL_COLUMNS)
    date_column = _pick_column(list(frame.columns), DATE_COLUMNS)

    frame = frame[[symbol_column, date_column, text_column]]
    frame.columns = ["symbol", "date", "text"]
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    if symbols is not None:
        frame = frame[frame["symbol"].isin(symbols)]
    frame = frame.dropna(subset=["date", "text"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="coerce").dt.date
    frame = frame.dropna(subset=["date"])
    if frame.empty:
        return frame
    frame["score"] = frame["text"].astype(str).map(score_headline)
    return frame


def _aggregate(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse scored headlines into one row per symbol-day."""
    daily = (
        frame.groupby(["symbol", "date"])["score"]
        .agg(news_count="count", sentiment_mean="mean", sentiment_sum="sum")
        .reset_index()
    )
    daily["sentiment_mean"] = daily["sentiment_mean"].round(6)
    daily["sentiment_sum"] = daily["sentiment_sum"].round(6)
    return daily


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv", type=Path, nargs="+", required=True, help="news archive CSV file(s)"
    )
    parser.add_argument(
        "--symbols", nargs="*", default=None, help="specific symbols (default: all in file)"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT_DIR, help="output directory (default data/news_sentiment)"
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing CSVs")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    for path in args.csv:
        if not path.is_file():
            parser.error(f"csv not found: {path}")

    wanted = {symbol.upper() for symbol in args.symbols} if args.symbols else None
    args.out.mkdir(parents=True, exist_ok=True)

    imported, skipped, failures = 0, 0, []
    for path in args.csv:
        try:
            headlines = _load_headlines(path, wanted)
        except Exception as exc:  # noqa: BLE001 - keep importing the rest
            print(f"!! {path.name:<35} ERROR {exc}")
            failures.append(path.name)
            continue
        if headlines.empty:
            print(f"!! {path.name:<35} no rows after filtering")
            continue
        for symbol, daily in _aggregate(headlines).groupby("symbol", sort=True):
            csv_path = args.out / f"{symbol}.csv"
            if csv_path.exists() and not args.overwrite:
                skipped += 1
                print(f"!! {symbol:<10} SKIP (exists)")
                continue
            daily = daily.drop(columns=["symbol"]).sort_values("date")
            if not args.dry_run:
                daily.to_csv(csv_path, index=False)
            imported += 1
            span = f"{daily['date'].iloc[0]} → {daily['date'].iloc[-1]}"
            print(
                f"OK {symbol:<10} {len(daily):>5} days  {daily['news_count'].sum():>7} headlines  "
                f"mean {daily['sentiment_mean'].mean():+.3f}  {span}"
            )

    if wanted is not None and not args.dry_run:
        failures.extend(symbol for symbol in wanted if not (args.out / f"{symbol}.csv").exists())

    print(
        f"\n{imported} imported, {skipped} skipped, {len(failures)} failed "
        f"→ {args.out}{' (dry run)' if args.dry_run else ''}"
    )
    if failures:
        print(f"not imported: {', '.join(sorted(set(failures)))}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
