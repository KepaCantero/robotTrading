"""Download historical OHLCV data into data/historical/*.csv.

Fetches daily bars from Yahoo Finance (via yfinance) for a curated
multi-market universe and writes them in the exact format the backtesting
DataLoader expects: date,open,high,low,close,volume.

Usage:
    python scripts/download_market_data.py                  # curated universe
    python scripts/download_market_data.py --years 10
    python scripts/download_market_data.py --tickers SAN BBVA IBE
    python scripts/download_market_data.py --tickers-all    # refresh everything

Prices are split/dividend-adjusted (auto_adjust=True) so strategies see a
consistent series across corporate actions. Non-US tickers are in their
local currency — the engine treats them as quoted (no FX conversion).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "historical"

# Curated multi-market universe: US mega-caps + wide US exposure, Spain,
# core Europe, Japan ADRs/local, plus an index proxy for the IBEX.
UNIVERSE: dict[str, str] = {
    # US — mega caps (existing)
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "AMZN": "Amazon",
    "NVDA": "Nvidia",
    "TSLA": "Tesla",
    # US — diversifiers (new)
    "JPM": "JPMorgan",
    "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil",
    "KO": "Coca-Cola",
    # US — market proxies (new)
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    # Spain (new)
    "SAN": "Santander",
    "BBVA": "BBVA",
    "IBE": "Iberdrola",
    "ITX": "Inditex",
    # Core Europe (new)
    "SAP.DE": "SAP",
    "SIE.DE": "Siemens",
    "MC.PA": "LVMH",
    "ASML.AS": "ASML",
    "NESN.SW": "Nestlé",
    # Japan (new)
    "6758.T": "Sony",
    "7203.T": "Toyota",
    # Index proxy (new)
    "^IBEX": "IBEX 35",
}


def _safe_name(ticker: str) -> str:
    """File stem for a ticker (^IBEX → IBEX so it survives every filesystem)."""
    return ticker.lstrip("^").replace("/", "-")


def download_one(ticker: str, years: int, out_dir: Path) -> tuple[str, int, str]:
    """Download one ticker and write its CSV. Returns (stem, rows, note)."""
    import yfinance as yf

    frame = yf.download(
        ticker,
        period=f"{years}y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if frame is None or frame.empty:
        return _safe_name(ticker), 0, "NO DATA"

    # yfinance ≥0.2 returns MultiIndex columns (field, ticker)
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame[["Open", "High", "Low", "Close", "Volume"]].dropna()
    frame.index.name = "date"

    # Round to 6 decimals: adjusted prices carry float noise that can push
    # close a hair above high and trip the Quote validator (1e-16 style).
    for column in ("Open", "High", "Low", "Close"):
        frame[column] = frame[column].astype(float).round(6)
    csv_path = out_dir / f"{_safe_name(ticker)}.csv"
    frame.to_csv(csv_path, date_format="%Y-%m-%d")
    first = str(frame.index[0].date())
    last = str(frame.index[-1].date())
    return _safe_name(ticker), len(frame), f"{first} → {last}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years", type=int, default=10, help="years of history to fetch (default 10)"
    )
    parser.add_argument(
        "--tickers", nargs="*", default=None, help="specific tickers (default: curated universe)"
    )
    parser.add_argument(
        "--out", type=Path, default=OUT_DIR, help="output directory (default data/historical)"
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    tickers = args.tickers if args.tickers else list(UNIVERSE)

    failures: list[str] = []
    for ticker in tickers:
        try:
            stem, rows, note = download_one(ticker, args.years, args.out)
        except Exception as exc:  # noqa: BLE001 - keep downloading the rest
            stem, rows, note = _safe_name(ticker), 0, f"ERROR {exc}"
        status = "OK " if rows > 0 else "!! "
        print(f"{status}{stem:<10} {rows:>6} rows  {note}")
        if rows == 0:
            failures.append(stem)

    print(f"\n{len(tickers) - len(failures)}/{len(tickers)} downloaded to {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
