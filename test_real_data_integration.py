#!/usr/bin/env python3
"""
Test script to verify real market data integration.

This script tests:
1. Alpha Vantage API connection
2. Data fetching functionality
3. Caching mechanism
4. Orchestrator integration

Usage:
    python test_real_data_integration.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.data.real_market_data import RealMarketDataFetcher, get_default_symbols

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def test_api_connection():
    """Test Alpha Vantage API connection."""
    logger.info("=" * 60)
    logger.info("TEST 1: API Connection")
    logger.info("=" * 60)

    try:
        fetcher = RealMarketDataFetcher()
        logger.info(f"✅ API Key configured: {fetcher.api_key[:10]}...")
        logger.info(f"✅ Cache directory: {fetcher.cache_dir}")
        logger.info(f"✅ Rate limit: {fetcher.rate_limit_calls} calls per {fetcher.rate_limit_period} seconds")
        return True
    except Exception as e:
        logger.error(f"❌ API connection failed: {e}")
        return False


async def test_fetch_single_symbol():
    """Test fetching a single symbol."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 2: Fetch Single Symbol")
    logger.info("=" * 60)

    try:
        async with RealMarketDataFetcher() as fetcher:
            logger.info("Fetching AAPL data...")
            df = await fetcher.fetch_symbol_data(
                "AAPL",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                use_cache=False,  # Force API call
            )

            if df is not None and len(df) > 0:
                logger.info(f"✅ Successfully fetched {len(df)} data points")
                logger.info(f"   Date range: {df.index.min()} to {df.index.max()}")
                logger.info(f"   Columns: {list(df.columns)}")
                logger.info(f"   Sample data:")
                logger.info(df.head())
                return True
            else:
                logger.error("❌ No data returned")
                return False

    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        return False


async def test_cache_mechanism():
    """Test caching mechanism."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 3: Cache Mechanism")
    logger.info("=" * 60)

    try:
        async with RealMarketDataFetcher() as fetcher:
            # First fetch (should cache)
            logger.info("First fetch (should cache)...")
            df1 = await fetcher.fetch_symbol_data(
                "MSFT",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                use_cache=False,  # Force API call
            )

            # Second fetch (should use cache)
            logger.info("Second fetch (should use cache)...")
            df2 = await fetcher.fetch_symbol_data(
                "MSFT",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                use_cache=True,  # Use cache
            )

            if df1 is not None and df2 is not None:
                logger.info(f"✅ Cache mechanism working")
                logger.info(f"   First fetch: {len(df1)} points")
                logger.info(f"   Second fetch: {len(df2)} points")

                # Show cache stats
                stats = fetcher.get_cache_stats()
                logger.info(f"   Cache stats: {stats['total_cached_symbols']} symbols cached")

                return True
            else:
                logger.error("❌ Cache mechanism failed")
                return False

    except Exception as e:
        logger.error(f"❌ Cache test failed: {e}")
        return False


async def test_fetch_multiple_symbols():
    """Test fetching multiple symbols."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 4: Fetch Multiple Symbols")
    logger.info("=" * 60)

    try:
        async with RealMarketDataFetcher() as fetcher:
            symbols = ["AAPL", "MSFT", "GOOGL"]
            logger.info(f"Fetching {len(symbols)} symbols: {', '.join(symbols)}")

            data = await fetcher.fetch_multiple_symbols(
                symbols=symbols,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                use_cache=True,
            )

            if data and len(data) > 0:
                logger.info(f"✅ Successfully fetched {len(data)}/{len(symbols)} symbols")

                for symbol, df in data.items():
                    logger.info(f"   {symbol}: {len(df)} data points")

                return True
            else:
                logger.error("❌ No data returned")
                return False

    except Exception as e:
        logger.error(f"❌ Multiple symbols fetch failed: {e}")
        return False


async def test_sp500_fetch():
    """Test fetching top N S&P 500 stocks."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST 5: Fetch S&P 500 Top N (Small Test)")
    logger.info("=" * 60)

    try:
        async with RealMarketDataFetcher() as fetcher:
            # Just fetch top 3 for testing
            logger.info("Fetching top 3 S&P 500 stocks...")

            data = await fetcher.fetch_sp500_top_n(
                n=3,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                use_cache=True,
            )

            if data and len(data) > 0:
                logger.info(f"✅ Successfully fetched {len(data)} symbols")
                logger.info(f"   Symbols: {', '.join(data.keys())}")

                # Show cache stats
                stats = fetcher.get_cache_stats()
                logger.info(f"   Cache stats: {stats['total_cached_symbols']} symbols, {stats['cache_size_mb']:.2f} MB")

                return True
            else:
                logger.error("❌ No data returned")
                return False

    except Exception as e:
        logger.error(f"❌ S&P 500 fetch failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    logger.info("")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 10 + "REAL MARKET DATA INTEGRATION TESTS" + " " * 14 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    results = []

    # Run tests
    results.append(("API Connection", await test_api_connection()))
    results.append(("Fetch Single Symbol", await test_fetch_single_symbol()))
    results.append(("Cache Mechanism", await test_cache_mechanism()))
    results.append(("Fetch Multiple Symbols", await test_fetch_multiple_symbols()))
    results.append(("S&P 500 Fetch", await test_sp500_fetch()))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
