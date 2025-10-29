#!/usr/bin/env python3
"""
Download Portfolio Data in Batches.

Downloads symbols in smaller batches with pauses between batches
to avoid rate limiting. Use this if the main script hits rate limits.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.download_portfolio_data import download_symbol_data
from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.services.portfolio_builder import PortfolioBuilder
from datetime import datetime, timedelta

def main():
    # Get all symbols
    portfolio_config = get_portfolio_config_manager()
    portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
    portfolio_summary = portfolio_builder.get_portfolio_summary()
    all_symbols = portfolio_summary["all_symbols"]
    
    # Download 10 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)
    output_dir = Path("data/historical")
    
    # Split into batches of 5 symbols
    batch_size = 5
    batches = [all_symbols[i:i + batch_size] for i in range(0, len(all_symbols), batch_size)]
    
    print("=" * 80)
    print(f"📊 Batch Download: {len(all_symbols)} symbols in {len(batches)} batches")
    print("=" * 80)
    
    successful = []
    failed = []
    
    for batch_num, batch in enumerate(batches, 1):
        print(f"\n🔄 Batch {batch_num}/{len(batches)}: {', '.join(batch)}")
        print("-" * 80)
        
        for symbol in batch:
            success = download_symbol_data(symbol, start_date, end_date, output_dir)
            if success:
                successful.append(symbol)
            else:
                failed.append(symbol)
            time.sleep(3.0)  # 3 second delay between symbols
        
        # Longer pause between batches
        if batch_num < len(batches):
            print(f"\n⏸️  Pausing 30 seconds before next batch...")
            time.sleep(30)
    
    print("\n" + "=" * 80)
    print(f"✅ Successful: {len(successful)}/{len(all_symbols)}")
    print(f"❌ Failed: {len(failed)}/{len(all_symbols)}")
    
    if failed:
        print(f"\n💡 Retry failed symbols:")
        print(f"   python scripts/download_portfolio_data.py --symbols {' '.join(failed)} --delay 5.0")
    
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

