#!/usr/bin/env python3
"""
Test StrategyStockAllocator with Yahoo Finance Data

This script:
1. Downloads stock data using yfinance
2. Tests StrategyStockAllocator filtering and classification
3. Runs a simple backtest with allocated stocks
4. Documents services NOT integrated in comprehensive_5day_test.py

Usage:
    python scripts/test_strategy_stock_allocator.py
"""

from __future__ import annotations

import gc
import logging
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Thread safety (CRITICAL - must be BEFORE imports)
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from app.services.strategy_stock_allocator import StrategyStockAllocator


# ============================================================================
# Data Download with Yahoo Finance
# ============================================================================

def download_yfinance_data(
    symbols: list[str],
    period: str = "1y",
    interval: str = "1d"
) -> dict[str, pd.DataFrame]:
    """
    Load historical data from CSV files or download from Yahoo Finance.

    Args:
        symbols: List of ticker symbols
        period: Time period (1y, 6mo, 3mo, etc.)
        interval: Data interval (1d, 1wk, 1h)

    Returns:
        Dictionary mapping symbol to DataFrame with OHLCV data
    """
    logger.info(f"Loading data for {len(symbols)} symbols...")
    logger.info(f"  Source: CSV files (data/historical/) with yfinance fallback")

    data = {}
    failed = []

    for symbol in symbols:
        csv_path = Path(f"data/historical/{symbol}.csv")

        # Try CSV first
        if csv_path.exists():
            try:
                logger.info(f"  Loading {symbol} from CSV...")
                df = pd.read_csv(csv_path)

                # Normalize column names to lowercase
                df.columns = df.columns.str.lower()

                # Parse date column
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                elif 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)

                data[symbol] = df
                logger.info(f"    ✅ {len(df)} records from CSV")

            except Exception as e:
                logger.warning(f"    CSV load failed for {symbol}: {e}")
                failed.append(symbol)
                continue
        else:
            # Try yfinance if CSV doesn't exist
            try:
                logger.info(f"  Downloading {symbol} from Yahoo Finance...")
                ticker = yf.Ticker(symbol)

                hist = ticker.history(period=period, interval=interval, progress=False)

                if hist.empty:
                    logger.warning(f"    No data for {symbol}")
                    failed.append(symbol)
                    continue

                # Normalize column names to lowercase
                hist.columns = hist.columns.str.lower()

                data[symbol] = hist
                logger.info(f"    ✅ {len(hist)} records from Yahoo Finance")

            except Exception as e:
                logger.error(f"    ❌ Error loading {symbol}: {e}")
                failed.append(symbol)

    logger.info(f"Load complete: {len(data)}/{len(symbols)} symbols successful")

    if failed:
        logger.warning(f"Failed symbols: {failed}")

    return data


# ============================================================================
# Test StrategyStockAllocator
# ============================================================================

def test_strategy_stock_allocator(
    data: dict[str, pd.DataFrame],
    total_capital: float = 100000,
) -> dict:
    """
    Test StrategyStockAllocator with downloaded data.

    Args:
        data: Dictionary mapping symbol to DataFrame
        total_capital: Total capital to allocate

    Returns:
        Dictionary with test results
    """
    logger.info("=" * 80)
    logger.info("Testing StrategyStockAllocator")
    logger.info("=" * 80)

    # Initialize allocator
    allocator = StrategyStockAllocator(use_yaml=True)

    # Step 1: Filter stocks
    logger.info("\n--- Step 1: Filtering Stocks ---")
    filtered = allocator.filter_stocks(data)
    logger.info(f"Filtered: {len(filtered)}/{len(data)} stocks passed")

    if len(filtered) == 0:
        logger.error("❌ No stocks passed filtering!")
        return {"success": False, "error": "No stocks passed filtering"}

    # Log filtered stocks
    logger.info("Filtered stocks:")
    for symbol, df in filtered.items():
        logger.info(f"  {symbol}: {len(df)} records, ${df['close'].iloc[-1]:.2f}")

    # Step 2: Allocate capital
    logger.info("\n--- Step 2: Allocating Capital ---")
    logger.info(f"Total capital: ${total_capital:,.2f}")

    result = allocator.allocate(
        historical_data=filtered,
        total_capital=total_capital,
        strategy_allocations={
            "momentum": 0.40,      # 40% to momentum
            "mean_reversion": 0.35,  # 35% to mean reversion
            "pairs_trading": 0.25,   # 25% to pairs trading
        }
    )

    # Step 3: Display results
    logger.info("\n--- Step 3: Allocation Results ---")
    logger.info(f"Validation passed: {result.validation_passed}")

    if result.validation_errors:
        logger.error(f"Validation errors: {result.validation_errors}")

    # Display allocations by strategy
    allocations_by_strategy = {
        "momentum": [],
        "mean_reversion": [],
        "pairs_trading": [],
        "unassigned": []
    }

    for symbol, metrics in result.allocations.items():
        strategy = metrics.strategy or "unassigned"
        allocations_by_strategy[strategy].append((symbol, metrics))

    for strategy, items in allocations_by_strategy.items():
        if items:
            logger.info(f"\n{strategy.upper()} ({len(items)} stocks):")
            total_allocated = sum(m.capital for _, m in items)
            logger.info(f"  Total allocated: ${total_allocated:,.2f}")

            for symbol, metrics in sorted(items, key=lambda x: x[1].capital, reverse=True):
                logger.info(
                    f"    {symbol}: ${metrics.capital:,.2f} ({metrics.weight:.2%}) - "
                    f"SPE={metrics.sps_score:.3f}"
                )

    # Display pairs
    if result.pairs:
        logger.info(f"\nPAIRS TRADING ({len(result.pairs)} pairs):")
        for pair in result.pairs:
            logger.info(
                f"  {pair.ticker1} + {pair.ticker2}: "
                f"cointegration={pair.cointegration_score:.3f}, "
                f"correlation={pair.correlation:.3f}"
            )

    # Display decision logs
    if result.decision_logs:
        logger.info(f"\nDecision Logs ({len(result.decision_logs)} items):")
        for log in result.decision_logs[:10]:  # Show first 10
            logger.info(f"  {log}")

    return {
        "success": result.validation_passed,
        "filtered_count": len(filtered),
        "total_count": len(data),
        "allocations": result.allocations,
        "pairs": result.pairs,
        "residual_capital": result.residual_capital,
    }


# ============================================================================
# Simple Backtest with Allocated Stocks
# ============================================================================

def run_simple_backtest(
    data: dict[str, pd.DataFrame],
    allocations: dict,
    test_days: int = 30,
) -> dict:
    """
    Run a simple backtest with the allocated stocks.

    Uses a simple buy-and-hold strategy on the last N days.

    Args:
        data: Original historical data
        allocations: Allocation results from StrategyStockAllocator
        test_days: Number of days to backtest

    Returns:
        Dictionary with backtest results
    """
    logger.info("\n" + "=" * 80)
    logger.info("Running Simple Backtest")
    logger.info("=" * 80)

    # Get the most common data length
    min_length = min(len(df) for df in data.values())
    if min_length < test_days + 50:
        logger.warning(f"Insufficient data for {test_days}-day backtest (need at least {test_days + 50} days)")
        return {"success": False, "error": "Insufficient data"}

    # Calculate returns for each allocated stock
    stock_returns = {}

    for symbol, metrics in allocations.items():
        if symbol not in data:
            continue

        df = data[symbol]

        if len(df) < test_days:
            continue

        # Get last test_days of data
        test_data = df.tail(test_days)

        # Calculate buy-and-hold return
        initial_price = test_data['close'].iloc[0]
        final_price = test_data['close'].iloc[-1]
        return_pct = (final_price - initial_price) / initial_price

        stock_returns[symbol] = {
            "return_pct": return_pct,
            "weight": metrics.weight,
            "capital": metrics.capital,
            "initial_price": initial_price,
            "final_price": final_price,
        }

    if not stock_returns:
        logger.error("No stocks to backtest")
        return {"success": False, "error": "No stocks to backtest"}

    # Calculate portfolio return
    portfolio_return = sum(
        r["return_pct"] * r["weight"]
        for r in stock_returns.values()
    )

    # Calculate total capital
    total_capital = sum(r["capital"] for r in stock_returns.values())

    # Log results
    logger.info(f"\nBacktest Results ({test_days} days):")
    logger.info(f"  Portfolio Return: {portfolio_return:.2%}")
    logger.info(f"  Total Capital: ${total_capital:,.2f}")
    logger.info(f"  Final Value: ${total_capital * (1 + portfolio_return):,.2f}")
    logger.info(f"  Profit/Loss: ${total_capital * portfolio_return:,.2f}")

    logger.info(f"\nIndividual Stock Returns:")
    for symbol, result in sorted(
        stock_returns.items(),
        key=lambda x: x[1]["return_pct"],
        reverse=True
    ):
        logger.info(
            f"  {symbol}: {result['return_pct']:+.2%} "
            f"(${result['initial_price']:.2f} -> ${result['final_price']:.2f})"
        )

    return {
        "success": True,
        "portfolio_return": portfolio_return,
        "total_capital": total_capital,
        "final_value": total_capital * (1 + portfolio_return),
        "profit_loss": total_capital * portfolio_return,
        "stock_returns": stock_returns,
    }


# ============================================================================
# Document Unintegrated Services
# ============================================================================

def document_unintegrated_services() -> dict:
    """
    Document services that are NOT integrated in comprehensive_5day_test.py.

    Returns:
        Dictionary of unintegrated services
    """
    logger.info("\n" + "=" * 80)
    logger.info("Services NOT Integrated in comprehensive_5day_test.py")
    logger.info("=" * 80)

    unintegrated = {
        "market_universe_services": {
            "service": "MarketUniverseLoader",
            "file": "app/services/market_universe_loader.py",
            "purpose": "Dynamically fetches stock/crypto universes from real markets",
            "features": [
                "S&P 500, NASDAQ 100, IBEX 35 constituents",
                "Top cryptocurrencies by market cap",
                "Parallel data downloading with rate limiting",
                "Liquidity and volatility filtering",
                "Automatic retry with exponential backoff",
                "Circuit breaker pattern",
            ],
            "integration_status": "NOT INTEGRATED - Symbols are hardcoded in config",
            "benefit": "Would automatically select best stocks based on liquidity/volatility",
        },

        "asset_identification": {
            "service": "AssetIdentificationService",
            "file": "app/services/asset_identification.py",
            "purpose": "Identify and rank liquid assets by class",
            "features": [
                "Identifies liquid equities, cryptos, forex, commodities",
                "Calculates liquidity scores",
                "Maintains asset rankings",
                "Filtering by asset class and criteria",
            ],
            "integration_status": "NOT INTEGRATED - No dynamic asset selection",
            "benefit": "Would provide ranked list of liquid assets for each class",
        },

        "strategy_stock_allocator": {
            "service": "StrategyStockAllocator",
            "file": "app/services/strategy_stock_allocator.py",
            "purpose": "Select and classify stocks for trading strategies",
            "features": [
                "Statistical classification (Hurst, ADF, KPSS, Half-Life)",
                "Momentum scoring engine",
                "Mean reversion scoring engine",
                "Pairs trading (cointegration) scoring",
                "Weighted Scoring Model (WSM)",
                "ERC / Risk Parity optimization",
            ],
            "integration_status": "NOT INTEGRATED - This test validates it separately",
            "benefit": "Would scientifically select best stocks for each strategy",
        },

        "profile_driven_trading": {
            "service": "ProfileDrivenTradingOrchestrator",
            "file": "app/services/profile_driven_trading/orchestrator.py",
            "purpose": "Complete 8-stage trading pipeline from profile to execution",
            "features": [
                "1. Profile Generation",
                "2. Universe Selection (MarketUniverseOrchestrator)",
                "3. Capital Allocation (StrategyStockAllocator)",
                "4. Signal Generation",
                "5. Tax Optimization",
                "6. Risk Validation",
                "7. Backtest Validation",
                "8. Trade Execution",
            ],
            "integration_status": "NOT INTEGRATED - Comprehensive test uses hardcoded approach",
            "benefit": "Would provide end-to-end profile-driven trading",
        },

        "market_universe_orchestrator": {
            "service": "MarketUniverseOrchestrator",
            "file": "app/services/market_universe_orchestrator.py",
            "purpose": "Orchestrates market universe loading and asset selection",
            "features": [
                "Combines MarketUniverseLoader + AssetIdentificationService",
                "Multi-asset universe management",
                "Dynamic symbol selection based on criteria",
            ],
            "integration_status": "NOT INTEGRATED",
            "benefit": "Centralized universe management",
        },

        "tax_optimization": {
            "service": "TaxOptimizer (referenced in orchestrator)",
            "file": "Unknown (likely app/services/tax_optimizer.py or similar)",
            "purpose": "Optimize trades for tax efficiency",
            "features": [
                "Tax-loss harvesting",
                "Long-term vs short-term gain optimization",
                "Wash sale avoidance",
            ],
            "integration_status": "NOT INTEGRATED",
            "benefit": "Would improve after-tax returns",
        },

        "risk_gates": {
            "service": "RiskGates (referenced in orchestrator)",
            "file": "Unknown",
            "purpose": "Validate trades against risk limits",
            "features": [
                "Position size limits",
                "Portfolio exposure limits",
                "Drawdown checks",
            ],
            "integration_status": "NOT INTEGRATED",
            "benefit": "Would prevent risky trades",
        },
    }

    for key, service in unintegrated.items():
        logger.info(f"\n{key}:")
        logger.info(f"  Service: {service['service']}")
        logger.info(f"  File: {service['file']}")
        logger.info(f"  Purpose: {service['purpose']}")
        logger.info(f"  Status: {service['integration_status']}")
        logger.info(f"  Benefit: {service['benefit']}")

    return unintegrated


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("StrategyStockAllocator Test with Yahoo Finance")
    logger.info("=" * 80)

    # Use symbols that exist in data/historical/
    # These are the CSV files we have available
    symbols = [
        # Tech
        "AAPL", "MSFT", "GOOGL", "META", "NVDA",
        # Finance
        "JPM", "BAC", "WFC", "GS",
        # Healthcare
        "ABT", "JNJ", "PFE", "TMO", "UNH",
        # Consumer/Discretionary
        "AMZN", "TSLA", "HD", "NKE", "SBUX",
        # Industrial/Other
        "CAT", "CRM", "CVX", "CSCO", "INTC", "ORCL",
        # Dividend stocks
        "MAIN", "O", "NEE", "PLD", "WMT", "XOM",
        # Communication
        "CMCSA", "DIS", "NFLX",
    ]

    # Step 1: Download data
    data = download_yfinance_data(
        symbols=symbols,
        period="1y",  # 1 year of data
        interval="1d"
    )

    if not data:
        logger.error("❌ No data downloaded, exiting")
        return 1

    # Step 2: Test StrategyStockAllocator
    allocator_result = test_strategy_stock_allocator(
        data=data,
        total_capital=100000,
    )

    if not allocator_result["success"]:
        logger.error("❌ StrategyStockAllocator test failed")
        return 1

    # Step 3: Run simple backtest
    backtest_result = run_simple_backtest(
        data=data,
        allocations=allocator_result["allocations"],
        test_days=30,
    )

    # Step 4: Document unintegrated services
    unintegrated = document_unintegrated_services()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Data downloaded: {len(data)}/{len(symbols)} symbols")
    logger.info(f"✅ Filtered stocks: {allocator_result['filtered_count']}/{allocator_result['total_count']}")
    logger.info(f"✅ Allocations made: {len(allocator_result['allocations'])} stocks")
    logger.info(f"✅ Pairs found: {len(allocator_result['pairs'])} pairs")
    logger.info(f"✅ Backtest return: {backtest_result['portfolio_return']:.2%}")
    logger.info(f"✅ Unintegrated services documented: {len(unintegrated)}")

    logger.info("\n✅ Test completed successfully!")
    logger.info("\nTo integrate these services into comprehensive_5day_test.py:")
    logger.info("  1. Replace hardcoded symbols with MarketUniverseLoader")
    logger.info("  2. Add StrategyStockAllocator for dynamic stock selection")
    logger.info("  3. Consider ProfileDrivenTradingOrchestrator for end-to-end flow")

    # Cleanup
    gc.collect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
