#!/usr/bin/env python3
"""
Download Portfolio Historical Data.

Downloads historical market data for all symbols in portfolio.yaml configuration
and saves them as CSV files for faster backtesting without rate limits.
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.services.portfolio_builder import PortfolioBuilder
import yfinance as yf
import pandas as pd

def download_symbol_data(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    output_dir: Path,
    retry_delay: float = 2.0,
    max_retries: int = 3,
) -> bool:
    """
    Download historical data for a symbol and save as CSV.
    
    Args:
        symbol: Stock symbol
        start_date: Start date
        end_date: End date
        output_dir: Output directory for CSV files
        retry_delay: Delay between retries (seconds)
        max_retries: Maximum retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    output_file = output_dir / f"{symbol}.csv"
    
    # Skip if file already exists
    if output_file.exists():
        print(f"  ✓ {symbol}: CSV already exists, skipping...")
        return True
    
    for attempt in range(max_retries):
        try:
            print(f"  📥 {symbol}: Downloading...", end=" ", flush=True)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if hist.empty:
                print("❌ No data")
                return False
            
            # Prepare DataFrame with standard columns
            df = pd.DataFrame({
                'date': hist.index,
                'timestamp': hist.index,  # Both for compatibility
                'open': hist['Open'],
                'high': hist['High'],
                'low': hist['Low'],
                'close': hist['Close'],
                'volume': hist['Volume'],
            })
            
            # Save to CSV
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_file, index=False)
            
            print(f"✅ {len(df)} rows saved")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "too many requests" in error_msg:
                if attempt < max_retries - 1:
                    # Exponential backoff: 5s, 15s, 45s
                    wait_time = 5 * (3 ** attempt)
                    print(f"⏳ Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Rate limited after {max_retries} attempts")
                    print(f"   💡 Tip: Wait 5-10 minutes and retry this symbol, or reduce --delay")
                    return False
            else:
                print(f"❌ Error: {e}")
                return False
    
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Download historical data for portfolio symbols"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years of historical data (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/historical",
        help="Output directory for CSV files (default: data/historical)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between downloads in seconds (default: 2.0, increase if rate limited)",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=None,
        help="Maximum symbols to download (default: all)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        nargs="+",
        help="Specific symbols to download (overrides portfolio config)",
    )
    
    args = parser.parse_args()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)
    
    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("📊 Portfolio Data Downloader")
    print("=" * 80)
    print(f"Period: {start_date.date()} to {end_date.date()} ({args.years} years)")
    print(f"Output: {output_dir}")
    print("=" * 80)
    
    # Get symbols to download
    if args.symbols:
        symbols = args.symbols
        print(f"\n📋 Downloading {len(symbols)} specified symbols:")
        print(f"   {', '.join(symbols)}")
    else:
        # Get symbols from portfolio config
        portfolio_config = get_portfolio_config_manager()
        portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
        
        portfolio_summary = portfolio_builder.get_portfolio_summary()
        all_symbols = portfolio_summary["all_symbols"]
        
        if args.max_symbols:
            all_symbols = all_symbols[:args.max_symbols]
        
        symbols = all_symbols
        
        print(f"\n📋 Portfolio symbols from config ({len(symbols)} total):")
        print(f"   Strategies: {', '.join(portfolio_summary['enabled_strategies'])}")
        print(f"   Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    
    print("\n🚀 Starting download...")
    print("-" * 80)
    
    # Download each symbol
    successful = []
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}", end=": ")
        
        success = download_symbol_data(
            symbol,
            start_date,
            end_date,
            output_dir,
            retry_delay=args.delay * 2,
        )
        
        if success:
            successful.append(symbol)
        else:
            failed.append(symbol)
        
        # Add delay between downloads to avoid rate limiting
        # Use longer delay if we just hit rate limits
        if i < len(symbols):
            delay = args.delay
            # Increase delay if recent failures due to rate limiting
            if failed and "rate limit" in str(failed[-1]).lower() if failed else False:
                delay = args.delay * 3  # Triple delay after rate limit
            
            time.sleep(delay)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Download Summary")
    print("=" * 80)
    print(f"✅ Successful: {len(successful)}/{len(symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(symbols)}")
    
    if successful:
        print(f"\n✅ Downloaded:")
        for symbol in successful:
            print(f"   - {symbol}.csv")
    
    if failed:
        print(f"\n❌ Failed to download:")
        for symbol in failed:
            print(f"   - {symbol}")
        print("\n💡 Tip: Retry failed symbols later or check if symbols are valid")
    
    print("\n" + "=" * 80)
    print(f"📁 CSV files saved to: {output_dir.absolute()}")
    print("=" * 80)
    
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

