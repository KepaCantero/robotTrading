#!/usr/bin/env python
"""Download per-symbol dividend history to data/dividends/<SYMBOL>.csv.

Fase 4 (plan de producción paper): free-source distribution events for the
income ledger. One row per event: date (ex-date), amount (per share),
currency, source. Idempotent: existing files are refreshed unless --skip.

Usage:
    .venv/bin/python scripts/download_dividends.py SCHD VYM VYMI VIG BND
    .venv/bin/python scripts/download_dividends.py --all-strategy-symbols
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "dividends"

#: Universe presets from the dividend strategy (config/trading_strategies +
#: dashboard presets): core + satellites + defensive + deep-dividend set.
STRATEGY_SYMBOLS = [
    # core
    "SCHD",
    "VIG",
    "DGRO",
    "DGRW",
    "VYM",
    # international high-yield satellite
    "VYMI",
    "IDVY",
    "VHYL",
    # high-yield domestic
    "DVY",
    "DLN",
    "PEY",
    "SDY",
    # defensive
    "BND",
    "BIV",
    # benchmarks
    "SPY",
    "IVV",
    "VT",
]


def fetch_dividends(symbol: str) -> list[dict]:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    series = ticker.dividends
    currency = "USD"
    try:
        currency = ticker.fast_info.get("currency") or ticker.info.get("currency") or "USD"
    except Exception:  # noqa: BLE001 - currency is cosmetic; default USD
        pass
    rows = []
    for ts, amount in series.items():
        rows.append(
            {
                "date": ts.date().isoformat(),
                "amount": f"{float(amount):.6f}",
                "currency": currency,
                "source": "yfinance",
            }
        )
    rows.sort(key=lambda r: r["date"])
    return rows


def save(symbol: str, rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol.upper()}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "amount", "currency", "source"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{symbol.upper()}: {len(rows)} events -> {path.relative_to(DATA_DIR.parent.parent)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbols", nargs="*", help="symbols to download")
    parser.add_argument("--all-strategy-symbols", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args(argv)

    symbols = [s.upper() for s in args.symbols]
    if args.all_strategy_symbols:
        symbols = STRATEGY_SYMBOLS
    if not symbols:
        parser.error("give symbols or --all-strategy-symbols")

    failures: list[str] = []
    for symbol in symbols:
        if args.skip_existing and (DATA_DIR / f"{symbol}.csv").exists():
            print(f"{symbol}: exists, skipped")
            continue
        try:
            rows = fetch_dividends(symbol)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append(symbol)
            print(f"{symbol}: FAILED ({exc})", file=sys.stderr)
            continue
        if not rows:
            failures.append(symbol)
            print(f"{symbol}: no dividend history", file=sys.stderr)
            continue
        save(symbol, rows)
    return 1 if failures and len(failures) == len(symbols) else 0


if __name__ == "__main__":
    raise SystemExit(main())
