#!/usr/bin/env python3
"""
Download Portfolio Historical Data.

Downloads historical market data for all symbols in portfolio.yaml configuration
using Yahoo Finance v8 API and saves them as CSV files for faster backtesting.
"""

import argparse
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.portfolio_config_manager import get_portfolio_config_manager
import pandas as pd
import requests

def download_symbol_v8_api(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    output_file: Path,
    delay: float = 6.0,
    max_retries: int = 5,
) -> bool:
    """Download symbol using Yahoo Finance v8 API."""
    
    # Skip if file already exists
    if output_file.exists():
        print(f"  ✓ {symbol}: CSV already exists, skipping...")
        return True
    
    # Convert dates to Unix timestamps
    period1 = int(start_date.timestamp())
    period2 = int(end_date.timestamp())
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "div,splits",
        "includePrePost": "false",
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://finance.yahoo.com/',
    }
    
    for attempt in range(max_retries):
        try:
            print(f"  📥 {symbol}: Downloading...", end=" ", flush=True)
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = delay * (2 ** attempt)
                print(f"⏳ Rate limited, waiting {wait_time:.0f}s...", flush=True)
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                return False
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                return False
            
            # Extract data from response
            if "chart" not in data or not data["chart"]["result"]:
                print(f"❌ No data in response")
                return False
            
            result = data["chart"]["result"][0]
            
            if "timestamp" not in result or "indicators" not in result:
                print(f"❌ Invalid response structure")
                return False
            
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]
            
            # Build DataFrame
            rows = []
            for i, ts in enumerate(timestamps):
                date = datetime.fromtimestamp(ts)
                if start_date <= date <= end_date:
                    close = quote["close"][i] if i < len(quote["close"]) and quote["close"][i] is not None else None
                    if close is None:
                        continue
                    
                    rows.append({
                        'date': date,
                        'timestamp': date,
                        'open': quote["open"][i] if i < len(quote["open"]) and quote["open"][i] is not None else close,
                        'high': quote["high"][i] if i < len(quote["high"]) and quote["high"][i] is not None else close,
                        'low': quote["low"][i] if i < len(quote["low"]) and quote["low"][i] is not None else close,
                        'close': close,
                        'volume': quote["volume"][i] if i < len(quote["volume"]) and quote["volume"][i] is not None else 0,
                    })
            
            if not rows:
                print(f"❌ No data in date range")
                return False
            
            # Create DataFrame and save
            df = pd.DataFrame(rows)
            df = df.dropna(subset=['close'])
            
            if df.empty:
                print(f"❌ No valid data after filtering")
                return False
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_file, index=False)
            
            print(f"✅ {len(df)} rows saved")
            
            # Delay between downloads
            time.sleep(delay)
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                time.sleep(wait_time)
                continue
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            return False
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Download portfolio historical data")
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols to download (default: all from portfolio.yaml)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Years of historical data (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=6.0,
        help="Delay in seconds between downloads (default: 6.0)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/historical",
        help="Output directory for CSV files (default: data/historical)",
    )
    
    args = parser.parse_args()
    
    # Get symbols
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        # Load from portfolio.yaml
        try:
            config_manager = get_portfolio_config_manager()
            symbols = config_manager.get_all_symbols()
            if not symbols:
                print("❌ No symbols found in portfolio.yaml")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading portfolio config: {e}")
            sys.exit(1)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    
    print("=" * 80)
    print("📊 Portfolio Data Downloader (Yahoo Finance v8 API)")
    print("=" * 80)
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.years} years)")
    print(f"Output: {args.output_dir}")
    print(f"Delay: {args.delay}s between downloads")
    print("=" * 80)
    
    if args.symbols:
        print(f"\n📋 Downloading {len(symbols)} specified symbols:")
    else:
        print(f"\n📋 Downloading {len(symbols)} symbols from portfolio.yaml:")
    
    for symbol in symbols[:10]:
        print(f"   {symbol}")
    if len(symbols) > 10:
        print(f"   ... and {len(symbols) - 10} more")
    
    print("\n🚀 Starting download...")
    print("-" * 80)
    
    output_dir = Path(args.output_dir)
    successful = []
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] ", end="")
        
        output_file = output_dir / f"{symbol}.csv"
        
        success = download_symbol_v8_api(
            symbol,
            start_date,
            end_date,
            output_file,
            delay=args.delay,
        )
        
        if success:
            successful.append(symbol)
        else:
            failed.append(symbol)
    
    print("\n" + "=" * 80)
    print("📊 Download Summary")
    print("=" * 80)
    print(f"✅ Successful: {len(successful)}/{len(symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(symbols)}")
    
    if failed:
        print(f"\n❌ Failed to download:")
        for symbol in failed:
            print(f"   - {symbol}")
        print(f"\n💡 Tip: Retry failed symbols later or check if symbols are valid")
    
    print("\n" + "=" * 80)
    print(f"📁 CSV files saved to: {output_dir.absolute()}")
    print("=" * 80)
    
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
