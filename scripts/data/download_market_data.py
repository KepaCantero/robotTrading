#!/usr/bin/env python3
"""
Download market data from Yahoo Finance and save to CSV files.

This script:
1. Downloads historical data for all required symbols
2. Saves to CSV files in data/historical/
3. Handles rate limiting with delays
4. Reports download status

Usage:
    python scripts/download_market_data.py
"""

from __future__ import annotations

import logging
import sys
import time
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


# Symbols to download (matching comprehensive_5day_test.py)
SYMBOLS = [
    # ETFs
    "SPY", "QQQ", "IWM",
    # Tech stocks
    "AAPL", "MSFT", "GOOGL",
    # Dividend stocks
    "O", "MAIN",
    # Crypto (yfinance format)
    "BTC-USD",
    # Forex (yfinance format)
    "EURUSD=X",
]

# Additional symbols for more comprehensive testing
ADDITIONAL_SYMBOLS = [
    # More ETFs
    "GLD", "TLT", "HYG", "LQD",
    # More stocks
    "AMZN", "TSLA", "META", "NVDA", "JPM", "JNJ",
    # More dividend stocks
    "NEE", "WMT", "PLD",
]

# Download settings
PERIOD = "2y"  # 2 years of data for full compliance (needs 252+ trading days)
INTERVAL = "1d"
DELAY_BETWEEN_REQUESTS = 1.0  # Seconds between requests to avoid rate limiting
OUTPUT_DIR = Path("data/historical")


def download_symbol(symbol: str, period: str = PERIOD, interval: str = INTERVAL) -> pd.DataFrame | None:
    """Download data for a single symbol.

    Args:
        symbol: Ticker symbol
        period: Time period (1y, 2y, etc.)
        interval: Data interval (1d, 1wk, etc.)

    Returns:
        DataFrame with OHLCV data, or None if download failed
    """
    try:
        logger.info(f"  Downloading {symbol}...")

        # Create ticker object
        ticker = yf.Ticker(symbol)

        # Download historical data (note: progress parameter removed in yfinance >= 0.2)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            logger.warning(f"    No data for {symbol}")
            return None

        # Normalize column names to lowercase
        hist.columns = hist.columns.str.lower()

        # Reset index to make date a column
        hist = hist.reset_index()

        # Rename date column if needed
        if 'date' not in hist.columns and hist.index.name == 'Date':
            hist.columns = hist.columns.str.lower()

        logger.info(f"    ✅ {len(hist)} records downloaded")

        return hist

    except Exception as e:
        logger.error(f"    ❌ Error downloading {symbol}: {e}")
        return None


def save_to_csv(df: pd.DataFrame, symbol: str, output_dir: Path) -> bool:
    """Save DataFrame to CSV file.

    Args:
        df: DataFrame with OHLCV data
        symbol: Ticker symbol
        output_dir: Output directory

    Returns:
        True if successful, False otherwise
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean symbol name for file (replace special characters)
        clean_symbol = symbol.replace("=", "_").replace("-", "_")

        output_path = output_dir / f"{clean_symbol}.csv"

        # Save to CSV
        df.to_csv(output_path, index=False)

        logger.info(f"    💾 Saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"    ❌ Error saving {symbol}: {e}")
        return False


def download_all_symbols(symbols: list[str], period: str = PERIOD) -> dict[str, pd.DataFrame]:
    """Download data for all symbols.

    Args:
        symbols: List of ticker symbols
        period: Time period

    Returns:
        Dictionary mapping symbol to DataFrame
    """
    logger.info(f"Downloading data for {len(symbols)} symbols (period={period})...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Delay between requests: {DELAY_BETWEEN_REQUESTS}s")

    data = {}
    failed = []
    skipped = []

    for i, symbol in enumerate(symbols, 1):
        # Check if file already exists
        clean_symbol = symbol.replace("=", "_").replace("-", "_")
        csv_path = OUTPUT_DIR / f"{clean_symbol}.csv"

        if csv_path.exists():
            logger.info(f"[{i}/{len(symbols)}] {symbol}: CSV exists, skipping")
            try:
                df = pd.read_csv(csv_path)
                data[symbol] = df
                skipped.append(symbol)
            except Exception as e:
                logger.warning(f"  Error reading existing CSV: {e}, will re-download")
                # Fall through to download
            else:
                continue

        # Download data
        logger.info(f"[{i}/{len(symbols)}] {symbol}:")

        df = download_symbol(symbol, period)

        if df is not None and not df.empty:
            # Save to CSV
            if save_to_csv(df, symbol, OUTPUT_DIR):
                data[symbol] = df
            else:
                failed.append(symbol)
        else:
            failed.append(symbol)

        # Delay to avoid rate limiting
        if i < len(symbols):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total symbols: {len(symbols)}")
    logger.info(f"✅ Successfully downloaded: {len(data)}")
    logger.info(f"⏭️  Skipped (already exists): {len(skipped)}")
    logger.info(f"❌ Failed: {len(failed)}")

    if failed:
        logger.warning(f"Failed symbols: {failed}")

    return data


def validate_data(data: dict[str, pd.DataFrame]) -> bool:
    """Validate downloaded data.

    Args:
        data: Dictionary mapping symbol to DataFrame

    Returns:
        True if validation passes, False otherwise
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("VALIDATING DATA")
    logger.info("=" * 80)

    all_valid = True

    for symbol, df in data.items():
        issues = []

        # Check required columns
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        # Map lowercase column names
        cols_lower = {col.lower(): col for col in df.columns}

        missing_cols = [col for col in required_cols if col.lower() not in cols_lower]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")

        # Check data length (need at least 252 trading days for full compliance)
        if len(df) < 252:
            issues.append(f"Insufficient data: {len(df)} < 252 days")

        # Check for NaN values
        nan_counts = df[required_cols].isna().sum() if all(col in df.columns for col in required_cols) else {}
        if nan_counts.any():
            issues.append(f"NaN values found: {nan_counts[nan_counts > 0].to_dict()}")

        if issues:
            logger.warning(f"❌ {symbol}: {', '.join(issues)}")
            all_valid = False
        else:
            logger.info(f"✅ {symbol}: Valid ({len(df)} records)")

    return all_valid


def main() -> int:
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("Market Data Downloader - Yahoo Finance")
    logger.info("=" * 80)

    # Combine all symbols
    all_symbols = SYMBOLS + ADDITIONAL_SYMBOLS

    # Download all symbols
    data = download_all_symbols(all_symbols)

    if not data:
        logger.error("❌ No data downloaded!")
        return 1

    # Validate data
    is_valid = validate_data(data)

    if not is_valid:
        logger.warning("⚠️  Some data validation issues detected")
    else:
        logger.info("✅ All data validated successfully")

    # Report data availability
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATA AVAILABILITY")
    logger.info("=" * 80)

    for symbol, df in sorted(data.items(), key=lambda x: x[0]):
        start_date = df['date'].iloc[0] if 'date' in df.columns else df.index[0]
        end_date = df['date'].iloc[-1] if 'date' in df.columns else df.index[-1]
        logger.info(f"  {symbol}: {len(df)} records ({start_date} to {end_date})")

    logger.info("")
    logger.info("✅ Download complete!")
    logger.info(f"Data saved to: {OUTPUT_DIR.absolute()}")
    logger.info("")
    logger.info("You can now run the comprehensive test:")
    logger.info("  python scripts/comprehensive_5day_test.py")

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
