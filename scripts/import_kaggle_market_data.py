"""Import the Kaggle "Huge Stock Market Dataset" into data/historical/*.csv.

The dataset (kaggle.com/datasets/borismarjanovic/huge-stock-market-dataset,
one manual download with a Kaggle account) ships one Stooq-format file per
US ticker under Data/Stocks/ and Data/ETFs/: daily rows of
Date,Open,High,Low,Close,Volume. It includes delisted tickers, which the
Yahoo downloader cannot see — that is its main value for backtesting.

This script converts those files into the exact schema the backtesting
DataLoader expects (date,Open,High,Low,Close,Volume) with the same
guarantees the Yahoo downloader provides: sorted unique dates, positive
prices, OHLC-coherent rows rounded to 6 decimals. If a file carries an
"Adjusted Close" column, OHLC is rescaled by adj/close so the series becomes
dividend-adjusted like the yfinance files; without it, rows stay as shipped
(split-adjusted at best — treat cross-ticker return comparisons accordingly).

Usage:
    python scripts/import_kaggle_market_data.py --zip archive.zip --tickers AAPL GE F
    python scripts/import_kaggle_market_data.py --dir extracted/Data/Stocks --etfs
    python scripts/import_kaggle_market_data.py --zip archive.zip --min-rows 500 --dry-run

Existing CSVs are never overwritten unless --overwrite is passed: Kaggle rows
are split-adjusted while the curated CSVs are Yahoo auto_adjust (split +
dividend), so splicing both regimes into one file would fake price jumps.
Kaggle history ends around 2017 — import it for breadth/delisted names, and
keep refreshing recent data with scripts/download_market_data.py.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "historical"

PRICE_FIELDS = ("open", "high", "low", "close")
OUTPUT_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def kaggle_stem(filename: str) -> str:
    """Output stem for a dataset file name (aapl.us.txt → AAPL)."""
    stem = Path(filename).stem  # strips only the last suffix (.txt)
    if stem.lower().endswith(".us"):
        stem = stem[: -len(".us")]
    return stem.upper()


def normalize_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Coerce one dataset file into the loader schema.

    Returns the normalized frame and a human note about dropped rows.
    """
    original_rows = len(frame)
    frame = frame.copy()
    frame.columns = frame.columns.str.strip().str.lower().str.replace(" ", "_")

    if "volume" not in frame.columns:
        frame["volume"] = 0

    adj_columns = [column for column in frame.columns if "adj" in column]
    if adj_columns:
        adjusted = pd.to_numeric(frame[adj_columns[0]], errors="coerce")
        close = pd.to_numeric(frame["close"], errors="coerce")
        factor = adjusted / close
        for column in PRICE_FIELDS[:-1]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce") * factor
        frame["close"] = adjusted

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in PRICE_FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0)

    frame = frame.dropna(subset=["date", *PRICE_FIELDS])
    frame = frame.set_index("date").sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]

    coherent = (frame["high"] + 1e-9 >= frame[["open", "close"]].max(axis=1)) & (
        frame["low"] - 1e-9 <= frame[["open", "close"]].min(axis=1)
    )
    positive = (frame[list(PRICE_FIELDS)] > 0).all(axis=1)
    frame = frame[coherent & positive]

    normalized = pd.DataFrame(
        {
            "Open": frame["open"].astype(float).round(6),
            "High": frame["high"].astype(float).round(6),
            "Low": frame["low"].astype(float).round(6),
            "Close": frame["close"].astype(float).round(6),
            "Volume": frame["volume"].astype("int64"),
        },
        index=frame.index,
    )
    normalized.index.name = "date"

    dropped = original_rows - len(normalized)
    note = f"dropped {dropped} rows" if dropped else "clean"
    return normalized, note


def _candidate_members(zip_path: Path, include_etfs: bool) -> list[str]:
    """Dataset file names inside the archive that match the selection."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    return [
        name
        for name in names
        if name.lower().endswith(".us.txt") and (include_etfs or "etf" not in name.lower())
    ]


def _candidate_files(dir_path: Path, include_etfs: bool) -> list[Path]:
    """Dataset files on disk (extracted archive or a subset folder)."""
    return [
        path
        for path in sorted(dir_path.rglob("*.us.txt"))
        if include_etfs or "etf" not in str(path).lower()
    ]


def _read_frame(source: Path, member: str | None) -> pd.DataFrame:
    """Read one dataset file, from a zip member or directly from disk."""
    if member is not None:
        with zipfile.ZipFile(source) as archive, archive.open(member) as handle:
            return pd.read_csv(handle)
    return pd.read_csv(source)


def _source_stem(source: Path, member: str | None) -> str:
    return kaggle_stem(member if member is not None else source.name)


def import_one(
    source: Path,
    member: str | None,
    out_dir: Path,
    min_rows: int,
    overwrite: bool,
    dry_run: bool,
) -> tuple[str, int, str]:
    """Convert one dataset file and write its CSV. Returns (stem, rows, note)."""
    stem = _source_stem(source, member)
    csv_path = out_dir / f"{stem}.csv"
    if csv_path.exists() and not overwrite:
        return stem, 0, "SKIP (exists)"

    frame, note = normalize_frame(_read_frame(source, member))
    if len(frame) < min_rows:
        return stem, 0, f"SKIP ({len(frame)} rows < {min_rows})"
    if not dry_run and not frame.empty:
        frame.to_csv(csv_path, date_format="%Y-%m-%d")
    first = str(frame.index[0].date()) if not frame.empty else "-"
    last = str(frame.index[-1].date()) if not frame.empty else "-"
    return stem, len(frame), f"{first} → {last} ({note})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--zip", type=Path, help="path to the downloaded dataset .zip")
    source_group.add_argument("--dir", type=Path, help="path to an extracted dataset folder")
    parser.add_argument(
        "--tickers", nargs="*", default=None, help="specific tickers (default: all)"
    )
    parser.add_argument("--etfs", action="store_true", help="also import Data/ETFs files")
    parser.add_argument(
        "--min-rows", type=int, default=0, help="skip files with fewer rows (default 0)"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT_DIR, help="output directory (default data/historical)"
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing CSVs")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    sources: list[tuple[Path, str | None]] = []
    if args.zip is not None:
        if not args.zip.is_file():
            parser.error(f"zip not found: {args.zip}")
        sources.extend((args.zip, member) for member in _candidate_members(args.zip, args.etfs))
    else:
        if args.dir is not None and not args.dir.is_dir():
            parser.error(f"directory not found: {args.dir}")
        sources.extend((path, None) for path in _candidate_files(args.dir, args.etfs))

    wanted = {ticker.upper() for ticker in args.tickers} if args.tickers else None
    if wanted is not None:
        sources = [
            (path, member) for path, member in sources if _source_stem(path, member) in wanted
        ]

    args.out.mkdir(parents=True, exist_ok=True)
    imported, skipped, failures = 0, 0, []
    for path, member in sources:
        try:
            stem, rows, note = import_one(
                path, member, args.out, args.min_rows, args.overwrite, args.dry_run
            )
        except Exception as exc:  # noqa: BLE001 - keep importing the rest
            stem, rows, note = _source_stem(path, member), 0, f"ERROR {exc}"
            failures.append(stem)
        if rows > 0:
            imported += 1
            status = "OK "
        else:
            skipped += 1
            status = "!! "
        print(f"{status}{stem:<10} {rows:>6} rows  {note}")

    if wanted is not None and not args.dry_run:
        # A requested ticker only succeeds if its CSV exists at the end:
        # missing from the dataset or skipped (min-rows) both mean "not imported".
        failures.extend(stem for stem in wanted if not (args.out / f"{stem}.csv").exists())

    print(
        f"\n{imported} imported, {skipped} skipped, {len(failures)} failed "
        f"→ {args.out}{' (dry run)' if args.dry_run else ''}"
    )
    if failures:
        print(f"not imported: {', '.join(sorted(set(failures)))}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
