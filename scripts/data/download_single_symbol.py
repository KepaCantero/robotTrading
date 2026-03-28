#!/usr/bin/env python3
"""
Download Single Symbol with Extended Delays.

Use this to download symbols one at a time with very long delays
to avoid rate limiting completely.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd


def download_symbol(symbol: str, years: int = 10, output_dir: str = "data/historical"):
    """Download single symbol with extended wait time."""
    output_path = Path(output_dir) / f"{symbol}.csv"

    if output_path.exists():
        print(f"✅ {symbol}.csv already exists")
        return True

    print(f"📥 Downloading {symbol}...")
    print("   Waiting 5 minutes to avoid rate limits...")

    # Wait 5 minutes before download
    for i in range(5):
        print(f"   {5-i} minutes remaining...")
        time.sleep(60)  # 1 minute

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval="1d")

        if hist.empty:
            print(f"❌ No data for {symbol}")
            return False

        df = pd.DataFrame(
            {
                'date': hist.index,
                'timestamp': hist.index,
                'open': hist['Open'],
                'high': hist['High'],
                'low': hist['Low'],
                'close': hist['Close'],
                'volume': hist['Volume'],
            }
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        print(f"✅ {symbol}: {len(df)} rows saved to {output_path}")
        return True

    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        print(f"❌ Error downloading {symbol}: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_single_symbol.py SYMBOL [years]")
        print("Example: python scripts/download_single_symbol.py AEP 10")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print("=" * 80)
    print(f"📥 Single Symbol Download: {symbol}")
    print("=" * 80)
    print(f"⚠️  This will wait 5 minutes before downloading to avoid rate limits")
    print(f"    You can cancel with Ctrl+C if needed")
    print("=" * 80)

    success = download_symbol(symbol, years)
    sys.exit(0 if success else 1)
