#!/usr/bin/env python3
"""Import Yahoo-format CSVs (Date,Open,High,Low,Close,Adj Close,Volume) into
data/historical in the repo's canonical format (date,Open,High,Low,Close,Volume,
adjusted prices), extending each series to today with yfinance when the local
file is stale.

Usage:
    python scripts/import_yahoo_csv.py PATH... [--out data/historical] [--refresh]

PATH may be a CSV file, or a directory (all *.csv inside, non-recursive).
Files whose stem already exists in the output dir are SKIPPED (the repo's own
fresh downloads win). With --refresh, stale imported series are extended via
yfinance instead of only being converted.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "historical"


def convert_one(src: Path, refresh: bool, out_dir: Path) -> tuple[str, int, str]:
    """Convert one Yahoo CSV to canonical form. Returns (stem, rows, note)."""
    frame = pd.read_csv(src)

    # Some archives use lowercase headers; normalize.
    frame.columns = [
        c.strip().capitalize().replace("Adj close", "Adj Close") for c in frame.columns
    ]
    needed = {"Date", "Open", "High", "Low", "Close"}
    if not needed.issubset(frame.columns):
        return src.stem, 0, f"skip: missing columns {sorted(needed - set(frame.columns))}"

    frame["Date"] = pd.to_datetime(frame["Date"])
    frame = frame.sort_values("Date").set_index("Date")

    # Adjust OHLC to the adjusted close (repo convention: adjusted prices).
    if "Adj Close" in frame.columns and frame["Close"].ne(0).all():
        ratio = frame["Adj Close"] / frame["Close"]
        for col in ("Open", "High", "Low", "Close"):
            frame[col] = frame[col] * ratio

    note = ""
    if refresh and not frame.empty:
        last = frame.index[-1]
        today = pd.Timestamp.now(tz=None).normalize()
        if (today - last).days > 5:
            try:
                import yfinance as yf

                tail = yf.download(
                    src.stem,
                    start=(last + pd.Timedelta(days=1)).date().isoformat(),
                    auto_adjust=True,
                    progress=False,
                )
                if not tail.empty:
                    if isinstance(tail.columns, pd.MultiIndex):
                        tail.columns = tail.columns.get_level_values(0)
                    tail.index = pd.to_datetime(tail.index).tz_localize(None)
                    tail = tail[~tail.index.isin(frame.index)]
                    frame = pd.concat([frame, list_of(tail)])
                    note = f"extended +{len(tail)}"
            except Exception as exc:  # noqa: BLE001 - keep importing the rest
                note = f"refresh failed ({exc})"

    frame = frame[["Open", "High", "Low", "Close", "Volume"]].astype(float).round(6)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame.index.name = "date"
    frame.to_csv(out_dir / f"{src.stem}.csv", date_format="%Y-%m-%d")
    first = str(frame.index[0].date())
    last = str(frame.index[-1].date())
    return src.stem, len(frame), f"{first} → {last} {note}".strip()


def list_of(tail: pd.DataFrame) -> pd.DataFrame:
    """Rename yfinance columns to match the local frame."""
    rename = {c: c for c in tail.columns}
    return tail.rename(columns=rename)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="CSV files or directories")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--refresh", action="store_true", help="extend stale series via yfinance")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in args.out.glob("*.csv")}

    files: list[Path] = []
    for path in args.paths:
        p = Path(path).expanduser()
        files.extend(sorted(p.glob("*.csv")) if p.is_dir() else [p])

    imported = skipped = failures = 0
    for src in files:
        if src.stem in existing:
            print(f"SKIP {src.stem:<10} (ya existe, gana la descarga fresca del repo)")
            skipped += 1
            continue
        try:
            stem, rows, note = convert_one(src, args.refresh, args.out)
        except Exception as exc:  # noqa: BLE001 - keep importing the rest
            stem, rows, note = src.stem, 0, f"ERROR {exc}"
        status = "OK  " if rows > 0 else "!!  "
        print(f"{status}{stem:<10} {rows:>6} rows  {note}")
        if rows > 0:
            imported += 1
            existing.add(stem)
        else:
            failures += 1

    print(f"\nimportados: {imported}, saltados (duplicados): {skipped}, fallos: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
