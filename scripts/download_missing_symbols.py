#!/usr/bin/env python3
"""
Download Missing Symbols - Standalone Script

Downloads historical market data for specific symbols without dependencies on project modules.
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

def download_symbol(symbol: str, start_date: datetime, end_date: datetime, output_file: Path, delay: float = 7.0) -> bool:
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
    
    try:
        print(f"  📥 {symbol}: Downloading...", end=" ", flush=True)
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 429:
            print(f"⏳ Rate limited, waiting {delay*2:.0f}s...", flush=True)
            time.sleep(delay * 2)
            return False
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return False
        
        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            print(f"❌ Invalid JSON: {e}")
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
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # Symbols to download
    symbols = ["ADBE", "AMD", "AVGO", "CRM", "CRWD", "CSCO", "INTC", "NET", "ORCL", "QCOM", "SHOP", "SNOW", "SQ"]
    
    # Date range: 10 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)
    
    output_dir = Path("data/historical")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("📊 Download Missing Symbols (Yahoo Finance v8 API)")
    print("=" * 80)
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (10 years)")
    print(f"Output: {output_dir}")
    print(f"Delay: 7.0s between downloads")
    print(f"Symbols: {len(symbols)}")
    print("=" * 80)
    print("\n🚀 Starting download...")
    print("-" * 80)
    
    successful = []
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] ", end="")
        
        output_file = output_dir / f"{symbol}.csv"
        
        success = download_symbol(symbol, start_date, end_date, output_file, delay=7.0)
        
        if success:
            successful.append(symbol)
        else:
            failed.append(symbol)
    
    print("\n" + "=" * 80)
    print("📊 Download Summary")
    print("=" * пти)
    print(f"✅ Successful: {len(successful)}/{len(symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(symbols)}")
    
    if failed:
        print(f"\n❌ Failed to download:")
        for symbol in failed:
            print(f"   - {symbol}")
        print(f"\n💡 Tip: Retry failed symbols later")
    
    if successful:
        print(f"\n✅ Successfully downloaded:")
        for symbol in successful:
            print(f"   - {symbol}")
    
    print("\n" + "=" * 80)
    print(f"📁 CSV files saved to: {output_dir.absolute()}")
    print("=" * 80)
    
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

