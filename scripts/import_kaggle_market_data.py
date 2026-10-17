"""Import Kaggle stock-history datasets into data/historical/*.csv.

Two Kaggle datasets are supported, both one manual download with a Kaggle
account:

- jacksoncrow/stock-market-dataset: stocks/AAPL.csv + etfs/SPY.csv with
  Date,Open,High,Low,Close,Adj Close,Volume (Yahoo export, history through
  the dataset's 2020 update). Preferred: freshest, and Adj Close lets the
  importer rescale OHLC by adj/close so the series is dividend-adjusted
  exactly like the yfinance-curated CSVs.
- borismarjanovic/huge-stock-market-dataset: Data/Stocks/aapl.us.txt +
  Data/ETFs/spy.us.txt with Date,Open,High,Low,Close,Volume[,OpenInt]
  (Stooq export, frozen ~2017-11, split-adjusted at best; still useful for
  breadth and later-delisted names Yahoo no longer serves).

Both are converted into the exact schema the backtesting DataLoader expects
(date,Open,High,Low,Close,Volume) with the same guarantees the Yahoo
downloader provides: sorted unique dates, positive prices, OHLC-coherent
rows rounded to 6 decimals.

Usage:
    python scripts/import_kaggle_market_data.py --dir ~/Downloads/archive-3 --tickers INTC GE F
    python scripts/import_kaggle_market_data.py --dir ~/Downloads/archive --etfs
    python scripts/import_kaggle_market_data.py --dir ~/Downloads/archive-3 --min-rows 500 --dry-run

Existing CSVs are never overwritten unless --overwrite is passed: mixing
adjustment regimes (split-only vs split+dividend) or splicing a frozen
dataset under fresh Yahoo rows in one file would fake price jumps. Import
these for breadth/history; keep refreshing recent data with
scripts/download_market_data.py.
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
FOLDER_LAYOUT_DIRS = {"stocks", "etfs"}


def kaggle_stem(filename: str) -> str:
    """Output stem for a Stooq-layout file name (aapl.us.txt → AAPL)."""
    stem = Path(filename).stem  # strips only the last suffix (.txt)
    if stem.lower().endswith(".us"):
        stem = stem[: -len(".us")]
    return stem.upper()


def source_stem(rel_path: str) -> str | None:
    """Ticker stem for a dataset-relative path, or None if not a data file.

    Recognizes the two Kaggle layouts:
    - Stooq (borismarjanovic): Data/Stocks/aapl.us.txt
    - folder (jacksoncrow): stocks/AAPL.csv — only .csv files whose parent
      directory is stocks/ or etfs/, so symbols_valid_meta.csv stays out.
    """
    if rel_path.lower().endswith(".us.txt"):
        return kaggle_stem(rel_path)
    parts = rel_path.split("/")
    if (
        len(parts) >= 2
        and parts[-1].lower().endswith(".csv")
        and parts[-2].lower() in FOLDER_LAYOUT_DIRS
    ):
        return parts[-1][: -len(".csv")].upper()
    return None


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

    # Old Yahoo bars often carry Open=0/NaN with valid H/L/C (PG 1962-69,
    # AMD 1980-83). Dropping the row would waste years of history; the
    # DataLoader's own Yahoo path falls back open→close, so do the same here.
    # Rows with a bad high/low/close stay dropped below.
    bad_open = frame["open"].isna() | (frame["open"] <= 0)
    valid_rest = frame[["high", "low", "close"]].notna().all(axis=1) & (
        frame[["high", "low", "close"]] > 0
    ).all(axis=1)
    repaired = bad_open & valid_rest
    repair_count = int(repaired.sum())
    frame.loc[repaired, "open"] = frame.loc[repaired, "close"]

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
    notes = []
    if repair_count:
        notes.append(f"repaired {repair_count} zero-opens")
    notes.append(f"dropped {dropped} rows" if dropped else "clean")
    return normalized, ", ".join(notes)


def _candidate_rels_from_zip(zip_path: Path, include_etfs: bool) -> list[str]:
    """Dataset member names inside the archive that match the selection."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    return [
        name
        for name in names
        if source_stem(name) is not None and (include_etfs or "etf" not in name.lower())
    ]


def _candidate_rels_from_dir(dir_path: Path, include_etfs: bool) -> list[str]:
    """Dataset-relative paths on disk (extracted archive or a subset folder)."""
    rels = {
        path.relative_to(dir_path).as_posix()
        for pattern in ("*.us.txt", "*.csv")
        for path in dir_path.rglob(pattern)
    }
    return [
        rel
        for rel in sorted(rels)
        if source_stem(rel) is not None and (include_etfs or "etf" not in rel.lower())
    ]


def _read_frame(base: Path, rel: str) -> pd.DataFrame:
    """Read one dataset file, from a zip archive or from an extracted tree."""
    if base.is_file():
        with zipfile.ZipFile(base) as archive, archive.open(rel) as handle:
            return pd.read_csv(handle)
    return pd.read_csv(base / rel)


def import_one(
    base: Path,
    rel: str,
    out_dir: Path,
    min_rows: int,
    overwrite: bool,
    dry_run: bool,
) -> tuple[str, int, str]:
    """Convert one dataset file and write its CSV. Returns (stem, rows, note)."""
    stem = source_stem(rel) or rel
    csv_path = out_dir / f"{stem}.csv"
    if csv_path.exists() and not overwrite:
        return stem, 0, "SKIP (exists)"

    frame, note = normalize_frame(_read_frame(base, rel))
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
    source_group.add_argument("--zip", type=Path, help="path to a downloaded dataset .zip")
    source_group.add_argument("--dir", type=Path, help="path to an extracted dataset folder")
    parser.add_argument(
        "--tickers", nargs="*", default=None, help="specific tickers (default: all)"
    )
    parser.add_argument("--etfs", action="store_true", help="also import etfs/ files")
    parser.add_argument(
        "--min-rows", type=int, default=0, help="skip files with fewer rows (default 0)"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT_DIR, help="output directory (default data/historical)"
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing CSVs")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    sources: list[tuple[Path, str]] = []
    if args.zip is not None:
        if not args.zip.is_file():
            parser.error(f"zip not found: {args.zip}")
        sources = [(args.zip, rel) for rel in _candidate_rels_from_zip(args.zip, args.etfs)]
    elif args.dir is not None:
        if not args.dir.is_dir():
            parser.error(f"directory not found: {args.dir}")
        sources = [(args.dir, rel) for rel in _candidate_rels_from_dir(args.dir, args.etfs)]

    wanted = {ticker.upper() for ticker in args.tickers} if args.tickers else None
    if wanted is not None:
        sources = [(base, rel) for base, rel in sources if source_stem(rel) in wanted]

    args.out.mkdir(parents=True, exist_ok=True)
    imported, skipped, failures = 0, 0, []
    for base, rel in sources:
        try:
            stem, rows, note = import_one(
                base, rel, args.out, args.min_rows, args.overwrite, args.dry_run
            )
        except Exception as exc:  # noqa: BLE001 - keep importing the rest
            stem, rows, note = source_stem(rel) or rel, 0, f"ERROR {exc}"
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
