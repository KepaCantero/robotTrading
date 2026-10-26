#!/usr/bin/env python3
"""Bloque 3 (PLAN_DATOS_REALES_Y_EJECUCION) — real FX + policy rates, free sources.

FX daily closes: ECB Data Portal reference rates (official, keyless,
16:00 CET fix, since 1999) for USD/JPY/GBP/AUD/CAD/NZD/CHF vs EUR. Every
carry pair derives exactly from the EUR crosses (USD/JPY = EURJPY/EURUSD,
GBP/USD = EURUSD/EURGBP, …). Dukascopy's freeserv blocks programmatic
access (bot wall) and tick-bulk is ~300k requests — documented as the
future intraday upgrade, not today's source.

Policy rates: FRED keyless CSV (fredgraph.csv) — official series for each
central bank (Fed target upper, ECB deposit facility, BoE bank rate,
BoJ/RBA/BoC/RBNZ via OECD immediate-rate series). Percent units.

Outputs:
  data/fx/ecb_exr.csv        date,currency,rate  (EUR-base, long format)
  data/fx/<PAIR>.csv         date,close          (EURUSD USDJPY GBPUSD
                              AUDUSD USDCAD NZDUSD USDCHF — derived)
  data/rates/<CCY>.csv       date,rate_pct
  + integrity/coverage report to stdout (gaps are REPORTED, never filled)

  python scripts/download_fx.py [--years 20]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[1]
FX_DIR = REPO / "data" / "fx"
RATES_DIR = REPO / "data" / "rates"

ECB_EXR = (
    "https://data-api.ecb.europa.eu/service/data/EXR/D.{ccy}.EUR.SP00.A"
    "?format=csvdata&startPeriod={start}"
)

#: carry pairs (plan §Bloque 3) → (numerator EUR-base, denominator EUR-base)
DERIVED_PAIRS: dict[str, tuple[str, str]] = {
    "EURUSD": ("USD", "USD"),  # identity: EURUSD = 1/EUR-base-USD
    "USDJPY": ("JPY", "USD"),
    "GBPUSD": ("USD", "GBP"),
    "AUDUSD": ("USD", "AUD"),
    "USDCAD": ("CAD", "USD"),
    "NZDUSD": ("USD", "NZD"),
    "USDCHF": ("CHF", "USD"),
}

#: currency → FRED series (percent). USD/EUR use the daily OFFICIAL policy
#: rates; the rest use 3-month interbank (IR3TIB01xxM156N) — the actual
#: tradable funding/investment rate a carry trade pays/receives, and the
#: series the OECD keeps current (the IRSTCB/BOERUKM picks came back
#: 404/empty/stale-2017). Choice documented in the coverage report.
FRED_RATES: dict[str, str] = {
    "USD": "DFEDTARU",  # Fed target range upper bound (daily)
    "EUR": "ECBDFR",  # ECB deposit facility rate (daily)
    "GBP": "IR3TIB01GBM156N",  # 3M interbank
    "JPY": "IR3TIB01JPM156N",  # 3M interbank
    "CHF": "IR3TIB01CHM156N",  # 3M interbank
    "CAD": "IR3TIB01CAM156N",  # 3M interbank
    "AUD": "IR3TIB01AUM156N",  # 3M interbank
    "NZD": "IR3TIB01NZM156N",  # 3M interbank
}

CURRENCIES = ["USD", "JPY", "GBP", "AUD", "CAD", "NZD", "CHF"]


def _get(url: str) -> str:
    import ssl

    import certifi

    ctx = ssl.create_default_context(cafile=certifi.where())
    req = Request(url, headers={"User-Agent": "robotTrading-data/1.0"})
    with urlopen(req, timeout=60, context=ctx) as resp:  # noqa: S310 - fixed https endpoints
        return resp.read().decode("utf-8")


def download_ecb(start: date) -> dict[str, dict[date, float]]:
    """EUR-base daily reference rates per currency."""
    series: dict[str, dict[date, float]] = {c: {} for c in CURRENCIES}
    for ccy in CURRENCIES:
        url = ECB_EXR.format(ccy=ccy, start=start.isoformat())
        body = _get(url)
        rows = list(csv.DictReader(body.splitlines()))
        for row in rows:
            try:
                series[ccy][date.fromisoformat(row["TIME_PERIOD"])] = float(row["OBS_VALUE"])
            except (KeyError, ValueError):
                continue  # malformed row → skip, coverage report tells the truth
        print(f"ECB {ccy}/EUR: {len(series[ccy])} días")
        time.sleep(0.4)  # be polite to the free endpoint
    return series


def download_fred(series_id: str) -> list[tuple[date, float]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    body = _get(url)
    out: list[tuple[date, float]] = []
    for row in csv.DictReader(body.splitlines()):
        try:
            value = float(row[series_id])
        except (KeyError, ValueError, TypeError):
            continue  # "." (missing) rows
        out.append((date.fromisoformat(row["observation_date"]), value))
    return out


def write_fx(series: dict[str, dict[date, float]]) -> None:
    FX_DIR.mkdir(parents=True, exist_ok=True)
    with open(FX_DIR / "ecb_exr.csv", "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "currency", "rate"])
        for ccy in CURRENCIES:
            for d in sorted(series[ccy]):
                writer.writerow([d.isoformat(), ccy, repr(series[ccy][d])])

    for pair, (num, den) in DERIVED_PAIRS.items():
        days = sorted(set(series[num]) & set(series[den]))
        with open(FX_DIR / f"{pair}.csv", "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["date", "close"])
            for d in days:
                # pair = BASE/QUOTE in QUOTE-per-BASE terms. From EUR-base
                # fixes: QUOTE per BASE = (QUOTE per EUR)/(BASE per EUR) =
                # r[num]/r[den] with num=QUOTE ccy, den=BASE ccy — so
                # USD/JPY = EURJPY/EURUSD ✓ and EURUSD = 1/EURUSD_base.
                # ECB quotes are "CCY per EUR": EURUSD IS series[USD]
                # directly (USD per EUR); the rest cross as num/den.
                value = (
                    Decimal(str(series[den][d]))
                    if pair == "EURUSD"
                    else Decimal(str(series[num][d])) / Decimal(str(series[den][d]))
                )
                writer.writerow([d.isoformat(), str(value)])


def write_rates() -> None:
    RATES_DIR.mkdir(parents=True, exist_ok=True)
    for ccy, series_id in FRED_RATES.items():
        try:
            rows = download_fred(series_id)
        except Exception as exc:  # noqa: BLE001 - declared gap, not a crash
            print(f"RATES {ccy} ({series_id}): FALLO {exc} — hueco declarado")
            rows = []
        with open(RATES_DIR / f"{ccy}.csv", "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["date", "rate_pct"])
            for d, value in rows:
                writer.writerow([d.isoformat(), repr(value)])
        print(f"RATES {ccy} ({series_id}): {len(rows)} observaciones")
        time.sleep(0.3)


def integrity_report() -> int:
    """Coverage per file: first/last date, rows, biggest gap. Gaps are
    normal in FX (weekends/holidays) — the report makes them visible."""
    problems = 0
    for path in sorted(FX_DIR.glob("*.csv")) + sorted(RATES_DIR.glob("*.csv")):
        rows = list(csv.DictReader(path.open()))
        if not rows:
            print(f"!! {path.name}: VACÍO — hueco de cobertura declarado")
            problems += 1
            continue
        dates = [date.fromisoformat(r["date"]) for r in rows]
        gaps = [(b - a).days for a, b in zip(sorted(dates), sorted(dates)[1:])]
        print(
            f"{path.name}: {len(rows)} filas · {min(dates)} → {max(dates)} · "
            f"máx gap {max(gaps) if gaps else 0}d"
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--rates-only", action="store_true")
    args = parser.parse_args()

    if not args.rates_only:
        start = date.today() - timedelta(days=365 * args.years)
        print(f"=== FX (ECB) desde {start} ===")
        write_fx(download_ecb(start))
    print("=== Tipos de política (FRED) ===")
    write_rates()
    print("=== Informe de integridad ===")
    return integrity_report()


if __name__ == "__main__":
    sys.exit(main())
