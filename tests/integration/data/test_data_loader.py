"""
Shared utilities for loading real historical data in integration tests.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


def load_all_csv_data(data_dir: Path = None, min_days: int = 40) -> Dict[str, pd.DataFrame]:
    """
    Load all CSV files from data/historical/ directory.
    
    Args:
        data_dir: Path to historical data directory. Defaults to project_root/data/historical/
        min_days: Minimum number of trading days required. Defaults to 40.
    
    Returns:
        Dictionary mapping symbol -> DataFrame with OHLCV data indexed by date.
    """
    if data_dir is None:
        # __file__ is tests/integration/data/test_data_loader.py
        # Go up 3 levels: tests/integration/data -> tests/integration -> tests -> project_root
        project_root = Path(__file__).parent.parent.parent.parent
        data_dir = project_root / "data" / "historical"
    
    csv_files = list(data_dir.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in {data_dir}")
    
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
            
            if len(df) < min_days:
                logger.warning(f"{symbol}: Only {len(df)} days (need {min_days}), skipping")
                continue
            
            historical_data[symbol] = df
            logger.debug(f"✅ {symbol}: {len(df)} days")
            
        except Exception as e:
            logger.warning(f"❌ {symbol}: Failed to load - {e}")
            continue
    
    logger.info(f"Loaded {len(historical_data)}/{len(csv_files)} symbols successfully")
    return historical_data

