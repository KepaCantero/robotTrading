#!/usr/bin/env python3
"""Bloque 1 (PLAN_DATOS_REALES_Y_EJECUCION) — SimFin bulk fundamentals.

Downloads the statement datasets with the user's free-tier API key
(SIMFIN_API_KEY env var, NEVER in the repo — this script refuses to run
without it) into data/fundamentals/ via the official `simfin` package
(handles auth, zips and on-disk cache; a re-run only refreshes when the
files are missing or --refresh is passed).

Datasets (market=us, free tier):
  us-income-annual / us-income-quarterly
  us-balance-annual / us-balance-quarterly
  us-cashflow-annual / us-cashflow-quarterly
  us-companies-general  (ticker ↔ SimFinId, sector, industry)

Every statement carries Publish Date — the point-in-time contract the
whole Bloque 1 stands on (a figure is only visible from its publish date
onward).

  SIMFIN_API_KEY=... python scripts/download_simfin.py [--refresh]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "data" / "fundamentals"

DATASETS: list[tuple[str, str, str]] = [
    # (statement, variant, filename)
    ("income", "annual", "us-income-annual.csv"),
    ("income", "quarterly", "us-income-quarterly.csv"),
    ("balance", "annual", "us-balance-annual.csv"),
    ("balance", "quarterly", "us-balance-quarterly.csv"),
    ("cashflow", "annual", "us-cashflow-annual.csv"),
    ("cashflow", "quarterly", "us-cashflow-quarterly.csv"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="force re-download")
    parser.add_argument(
        "--with-prices",
        action="store_true",
        help="also download us-shareprices-daily (~300MB, market-cap PIT source; "
        "local-only, never committed)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("SIMFIN_API_KEY", "").strip()
    if not api_key:
        print(
            "SIMFIN_API_KEY no está en el entorno. Clave gratuita en simfin.com →\n"
            "export SIMFIN_API_KEY='<tu clave>'   (nunca se commitea: el repo es público)"
        )
        return 2

    import pandas as pd
    import simfin as sf

    sf.set_api_key(api_key)
    sf.set_data_dir(str(DATA_DIR))

    loaders = {
        "income": sf.load_income,
        "balance": sf.load_balance,
        "cashflow": sf.load_cashflow,
    }
    total_rows = 0
    for statement, variant, filename in DATASETS:
        target = DATA_DIR / filename
        if target.exists() and not args.refresh:
            df = pd.read_csv(target)
            print(f"{filename}: ya en disco ({len(df)} filas)")
        else:
            # refresh_days=0 forces the download when --refresh is passed
            df = loaders[statement](
                variant=variant, market="us", refresh_days=0 if args.refresh else 30
            )
            df = df.reset_index()
            df.to_csv(target, index=False)
            print(f"{filename}: descargado ({len(df)} filas)")
        if "Publish Date" not in df.columns and statement != "companies":
            print(f"  ¡AVISO! {filename} sin Publish Date — PIT imposible")
            return 1
        total_rows += len(df)

    if args.with_prices:
        sp = sf.load_shareprices(
            variant="daily", market="us", refresh_days=0 if args.refresh else 30
        )
        sp.reset_index().to_csv(DATA_DIR / "us-shareprices-daily.csv", index=False)
        print(f"us-shareprices-daily.csv: ({len(sp)} filas — local, no commiteado)")

    # ticker ↔ SimFinId map + sector/industry for the universe builder
    companies_path = DATA_DIR / "us-companies-general.csv"
    if not companies_path.exists() or args.refresh:
        comp = sf.load_companies(market="us", refresh_days=0 if args.refresh else 30)
        comp.to_csv(companies_path, index=False)
        print(
            f"us-companies-general.csv: {'descargado' if args.refresh else ''} ({len(comp)} filas)"
        )
    else:
        comp = pd.read_csv(companies_path)
        print(f"us-companies-general.csv: ya en disco ({len(comp)} filas)")

    print(f"TOTAL: {total_rows} filas de estados + {len(comp)} compañías → {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
