#!/usr/bin/env python3
"""
Download using yahoo_fin directly (bypass yfinance).

This script uses yahoo_fin exclusively to avoid yfinance rate limits.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from yahoo_fin.stock_info import get_data as yahoo_fin_get_data
except ImportError:
    print("❌ yahoo_fin not installed. Run: pip install yahoo-fin requests-html")
    sys.exit(1)


def download_symbol(
    symbol: str, years: int = 10, output_dir: str = "data/historical", delay: float = 3.0
):
    """Download single symbol using yahoo_fin."""
    output_path = Path(output_dir) / f"{symbol}.csv"

    if output_path.exists():
        print(f"  ✓ {symbol}: CSV already exists")
        return True

    try:
        print(f"  📥 {symbol}: Downloading with yahoo_fin...", end=" ", flush=True)

        # Calculate dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)

        # yahoo_fin uses mm/dd/yyyy format
        start_str = start_date.strftime("%m/%d/%Y")
        end_str = end_date.strftime("%m/%d/%Y")

        # Download data
        df = yahoo_fin_get_data(symbol, start_date=start_str, end_date=end_str, interval="1d")

        if df is None or df.empty:
            print("❌ No data")
            return False

        # Reset index and ensure timestamp column
        df = df.reset_index()
        if 'timestamp' not in df.columns:
            df['timestamp'] = df.get('date', df.index)

        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        print(f"✅ {len(df)} rows saved")
        time.sleep(delay)  # Delay between downloads
        return True

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        print(f"❌ Error: {e}")
        time.sleep(delay)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_with_yahoo_fin.py SYMBOL [SYMBOL2 ...]")
        print("Example: python scripts/download_with_yahoo_fin.py AEP BAC KO")
        sys.exit(1)

    symbols = [s.upper() for s in sys.argv[1:]]

    print("=" * 80)
    print("📥 Download using yahoo_fin (bypassing yfinance)")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print("=" * 80)

    successful = []
    failed = []

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}: ", end="", flush=True)

        success = download_symbol(symbol, delay=3.0)

        if success:
            successful.append(symbol)
        else:
            failed.append(symbol)

    print("\n" + "=" * 80)
    print(f"✅ Successful: {len(successful)}/{len(symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(symbols)}")

    if successful:
        print(f"\n✅ Downloaded: {', '.join(successful)}")

    if failed:
        print(f"\n❌ Failed: {', '.join(failed)}")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
