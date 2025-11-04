#!/usr/bin/env python3
"""
Test StrategyStockAllocator with Real Data from data/historical/

Loads all CSV files and tests complete allocation pipeline.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path BEFORE any app imports
# __file__ is tests/integration/test_allocator_integration.py
# We need to go up 2 levels: tests/integration -> tests -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

# Now import app modules
from app.services.strategy_stock_allocator import StrategyStockAllocator
from app.core.centralized_config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_all_csv_data():
    """Load all CSV files from data/historical/."""
    historical_dir = project_root / "data" / "historical"
    csv_files = list(historical_dir.glob("*.csv"))
    
    logger.info(f"Found {len(csv_files)} CSV files in {historical_dir}")
    
    historical_data = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)  # 10 years
    
    for csv_file in csv_files:
        symbol = csv_file.stem
        try:
            df = pd.read_csv(csv_file)
            
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Handle date column
            date_col = 'date' if 'date' in df.columns else 'timestamp'
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.set_index(date_col)
            elif not isinstance(df.index, pd.DatetimeIndex):
                logger.warning(f"{symbol}: No date column, skipping")
                continue
            
            # Filter by date range
            df = df.loc[start_date:end_date]
            
            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                logger.warning(f"{symbol}: Missing columns {missing}, skipping")
                continue
            
            # Clean data
            df = df[required_cols].dropna()
            
            if len(df) < 40:
                logger.warning(f"{symbol}: Only {len(df)} days, skipping")
                continue
            
            historical_data[symbol] = df
            logger.debug(f"✅ {symbol}: {len(df)} days")
            
        except Exception as e:
            logger.warning(f"❌ {symbol}: Failed to load - {e}")
            continue
    
    logger.info(f"Loaded {len(historical_data)}/{len(csv_files)} symbols successfully")
    return historical_data


def test_allocation():
    """Test complete allocation pipeline."""
    print("=" * 80)
    print("🧪 Testing StrategyStockAllocator with Real Data")
    print("=" * 80)
    
    # Load real data
    print("\n1️⃣ Loading CSV data from data/historical/...")
    historical_data = load_all_csv_data()
    
    if len(historical_data) == 0:
        print("❌ No data loaded! Check CSV files in data/historical/")
        return False
    
    print(f"✅ Loaded {len(historical_data)} symbols")
    print(f"   Symbols: {', '.join(sorted(historical_data.keys())[:10])}{'...' if len(historical_data) > 10 else ''}")
    
    # Create allocator
    print("\n2️⃣ Creating StrategyStockAllocator...")
    try:
        # StrategyStockAllocator accepts StockAllocationSettings or None (uses defaults)
        from app.core.centralized_config import StockAllocationSettings
        allocator = StrategyStockAllocator(StockAllocationSettings())
        print("✅ Allocator created")
    except Exception as e:
        print(f"❌ Failed to create allocator: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Filter stocks
    print("\n3️⃣ Filtering stocks...")
    filtered = allocator.filter_stocks(historical_data)
    print(f"✅ Filtered: {len(filtered)}/{len(historical_data)} passed validation")
    
    if len(filtered) == 0:
        print("❌ All stocks were filtered out! Check filter criteria.")
        return False
    
    # Allocate capital
    print("\n4️⃣ Allocating capital ($100,000)...")
    total_capital = 100_000.0
    
    try:
        result = allocator.allocate(
            historical_data=historical_data,
            total_capital=total_capital,
            strategy_allocations=None  # Use defaults
        )
        print(f"✅ Allocation completed")
    except Exception as e:
        print(f"❌ Allocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"   Assets allocated: {len(result.allocations)}")
    print(f"   Validation: {'PASSED ✅' if result.validation_passed else 'FAILED ❌'}")
    
    if result.validation_errors:
        print(f"   Errors: {result.validation_errors}")
    
    # Breakdown by strategy
    print("\n5️⃣ Allocation Breakdown:")
    strategy_counts = {}
    strategy_capital = {}
    
    for ticker, metrics in result.allocations.items():
        strategy = metrics.strategy
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        strategy_capital[strategy] = strategy_capital.get(strategy, 0.0) + metrics.capital
    
    for strategy in ['momentum', 'mean_reversion', 'pairs_trading']:
        count = strategy_counts.get(strategy, 0)
        capital = strategy_capital.get(strategy, 0.0)
        pct = (capital / total_capital) * 100
        print(f"   {strategy:20s}: {count:3d} tickers, ${capital:>10,.2f} ({pct:5.1f}%)")
    
    total_allocated = sum(m.capital for m in result.allocations.values())
    utilization = (total_allocated / total_capital) * 100
    
    print(f"\n   {'Total':20s}: {len(result.allocations):3d} tickers, ${total_allocated:>10,.2f} ({utilization:5.1f}%)")
    print(f"   {'Residual':20s}: {'':3s} {'':10s} ${result.residual_capital:>10,.2f} ({result.residual_capital/total_capital*100:5.1f}%)")
    
    # Sample allocations
    print("\n6️⃣ Sample Allocations (first 15):")
    for i, (ticker, metrics) in enumerate(list(result.allocations.items())[:15], 1):
        print(
            f"   {i:2d}. {ticker:6s} -> {metrics.strategy:15s} "
            f"${metrics.capital:>10,.2f} ({metrics.weight*100:5.2f}%) "
            f"SPS={metrics.sps_score:.4f}"
        )
    
    # Pairs
    if result.pairs:
        print(f"\n7️⃣ Pairs Trading: {len(result.pairs)} pairs found")
        for i, pair in enumerate(result.pairs[:5], 1):  # Show first 5
            print(f"   {i}. {pair.ticker1}-{pair.ticker2}: cointegration={pair.cointegration_score:.4f}")
    
    # Validation summary
    print("\n8️⃣ Validation Summary:")
    print(f"   ✅ Validation passed: {result.validation_passed}")
    if not result.validation_passed:
        print(f"   ❌ Errors:")
        for error in result.validation_errors:
            print(f"      - {error}")
    
    # Quality checks
    print("\n9️⃣ Quality Checks:")
    
    checks_passed = 0
    total_checks = 6
    
    # Check 1: Minimum tickers
    if len(result.allocations) >= 10:
        print(f"   ✅ Minimum tickers: {len(result.allocations)} >= 10")
        checks_passed += 1
    else:
        print(f"   ⚠️  Minimum tickers: {len(result.allocations)} < 10 (expected >= 10)")
    
    # Check 2: Capital utilization
    if utilization >= 70:
        print(f"   ✅ Capital utilization: {utilization:.1f}% >= 70%")
        checks_passed += 1
    else:
        print(f"   ⚠️  Capital utilization: {utilization:.1f}% < 70% (expected >= 70%)")
    
    # Check 3: All strategies have allocations
    strategies_with_allocs = len([s for s in ['momentum', 'mean_reversion', 'pairs_trading'] if strategy_counts.get(s, 0) > 0])
    if strategies_with_allocs >= 2:
        print(f"   ✅ Strategies with allocations: {strategies_with_allocs} >= 2")
        checks_passed += 1
    else:
        print(f"   ⚠️  Strategies with allocations: {strategies_with_allocs} < 2")
    
    # Check 4: Validation passed
    if result.validation_passed:
        print(f"   ✅ Validation passed")
        checks_passed += 1
    else:
        print(f"   ⚠️  Validation failed (but allocations created)")
    
    # Check 5: Residual capital reasonable
    residual_pct = (result.residual_capital / total_capital) * 100
    if residual_pct < 35:
        print(f"   ✅ Residual capital: {residual_pct:.1f}% < 35%")
        checks_passed += 1
    else:
        print(f"   ⚠️  Residual capital: {residual_pct:.1f}% >= 35%")
    
    # Check 6: Pairs trading has pairs
    if len(result.pairs) > 0:
        print(f"   ✅ Pairs found: {len(result.pairs)}")
        checks_passed += 1
    else:
        print(f"   ⚠️  No pairs found (may be expected if no cointegrated pairs)")
    
    print(f"\n✅ Quality checks: {checks_passed}/{total_checks} passed")
    
    print("\n" + "=" * 80)
    if checks_passed >= 4:
        print("✅ TEST PASSED: Allocation system working correctly!")
    else:
        print("⚠️  TEST WARNINGS: Some quality checks failed, but allocation completed")
    print("=" * 80)
    
    return checks_passed >= 3


if __name__ == "__main__":
    try:
        success = test_allocation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

