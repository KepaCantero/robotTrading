#!/usr/bin/env python
"""Backfill US symbols + dividend histories from LSE Data (optional).

    .venv/bin/python scripts/backfill_lse.py --symbols SCHD VYM BND
    .venv/bin/python scripts/backfill_lse.py --dividends SCHD

Needs `pip install lse-data` and LSE_API_KEY in the env. Without them
it exits 0 explaining exactly that — never fails the pipeline. European
listings (Xetra/Euronext) are NOT covered by LSE Data yet; for those,
our own download_market_data.py remains the source.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*", default=[], help="US symbols to backfill")
    parser.add_argument("--dividends", nargs="*", default=[], help="symbols for dividend history")
    args = parser.parse_args()

    from app.infrastructure.data_sources import lse_data

    if not lse_data.available():
        print(
            "LSE Data adapter disabled — set LSE_API_KEY and `pip install lse-data` to enable it."
        )
        return 0

    for sym in args.symbols:
        path = lse_data.backfill_daily_csv(sym.upper())
        print(f"{sym}: {'written ' + str(path) if path else 'no improvement over local'}")
    for sym in args.dividends:
        rows = lse_data.dividends(sym.upper())
        print(f"{sym} dividends: {len(rows) if rows else 0} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
