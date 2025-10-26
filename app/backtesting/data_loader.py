"""
Data Loader for Backtesting

Provides functionality to load historical market data from various sources:
- CSV files from data/historical/
- External APIs (yfinance, Interactive Brokers)
- Market data feeds
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pandas as pd
import yfinance as yf

from app.models.market_data import DataFrequency, Quote

logger = logging.getLogger(__name__)


class DataLoader:
    """Loader for historical market data from various sources."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the data loader.

        Args:
            base_path: Base path for CSV files (default: data/historical/)
        """
        self.base_path = base_path or Path("data/historical")
        self.cache = {}

    def load_market_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d",
        source: str = "csv",
    ) -> List[Quote]:
        """
        Load market data for a symbol.

        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe (1d, 1h, 15m, etc.)
            source: Data source ("csv", "yfinance", "ibkr")

        Returns:
            List of Quote objects
        """
        if source == "csv":
            return self._load_from_csv(symbol, start_date, end_date)
        elif source == "yfinance":
            return self._load_from_yfinance(symbol, start_date, end_date, timeframe)
        else:
            raise ValueError(f"Unsupported data source: {source}")

    def _load_from_csv(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Quote]:
        """Load data from CSV file."""
        file_path = self.base_path / f"{symbol}.csv"

        if not file_path.exists():
            logger.warning(f"CSV file not found: {file_path}. Trying yfinance...")
            return self._load_from_yfinance(symbol, start_date, end_date)

        try:
            df = pd.read_csv(
                file_path,
                parse_dates=["timestamp"],
                index_col="timestamp",
            )

            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            quotes = []
            for idx, row in df.iterrows():
                quote = Quote(
                    symbol=symbol,
                    bid=Decimal(str(row.get("bid", row.get("close", 100)))),
                    ask=Decimal(str(row.get("ask", row.get("close", 100)))),
                    last=Decimal(str(row.get("close", 100))),
                    volume=Decimal(str(row.get("volume", 0))),
                    timestamp=(
                        idx if isinstance(idx, datetime) else datetime.fromisoformat(str(idx))
                    ),
                    high=Decimal(str(row.get("high", row.get("close", 100)))),
                    low=Decimal(str(row.get("low", row.get("close", 100)))),
                    open=Decimal(str(row.get("open", row.get("close", 100)))),
                    close=Decimal(str(row.get("close", 100))),
                )
                quotes.append(quote)

            logger.info(f"Loaded {len(quotes)} quotes from CSV for {symbol}")
            return quotes

        except Exception as e:
            logger.error(f"Error loading CSV for {symbol}: {e}")
            logger.warning("Falling back to yfinance...")
            return self._load_from_yfinance(symbol, start_date, end_date)

    def _load_from_yfinance(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d",
    ) -> List[Quote]:
        """Load data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            interval = "1d" if timeframe == "1d" else "1h"
            hist = ticker.history(start=start_date, end=end_date, interval=interval)

            if hist.empty:
                logger.warning(f"No data from yfinance for {symbol}")
                return []

            quotes = []
            for idx, row in hist.iterrows():
                # Convert index to datetime if needed
                timestamp = idx if isinstance(idx, datetime) else datetime.fromisoformat(str(idx))

                quote = Quote(
                    symbol=symbol,
                    bid=Decimal(str(row.get("Close", row.get("Low", 100)))),
                    ask=Decimal(str(row.get("Close", row.get("High", 100)))),
                    last=Decimal(str(row.get("Close", 100))),
                    volume=Decimal(str(row.get("Volume", 0))),
                    timestamp=timestamp,
                    high=Decimal(str(row.get("High", row.get("Close", 100)))),
                    low=Decimal(str(row.get("Low", row.get("close", 100)))),
                    open=Decimal(str(row.get("Open", row.get("Close", 100)))),
                    close=Decimal(str(row.get("Close", 100))),
                )
                quotes.append(quote)

            logger.info(f"Loaded {len(quotes)} quotes from yfinance for {symbol}")
            return quotes

        except Exception as e:
            logger.error(f"Error loading from yfinance for {symbol}: {e}")
            return []

    def save_to_csv(self, data: List[Quote], filename: str):
        """
        Save quotes to CSV file.

        Args:
            data: List of Quote objects
            filename: Output filename
        """
        file_path = self.base_path / filename

        # Convert to DataFrame
        rows = []
        for quote in data:
            rows.append(
                {
                    "timestamp": quote.timestamp,
                    "symbol": quote.symbol,
                    "open": float(quote.open),
                    "high": float(quote.high),
                    "low": float(quote.low),
                    "close": float(quote.close),
                    "volume": float(quote.volume),
                    "bid": float(quote.bid),
                    "ask": float(quote.ask),
                }
            )

        df = pd.DataFrame(rows)
        df.to_csv(file_path, index=False)
        logger.info(f"Saved {len(data)} quotes to {file_path}")


def load_market_data(
    symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d"
) -> List[Quote]:
    """
    Convenience function to load market data.

    Args:
        symbol: Trading symbol
        start_date: Start date
        end_date: End date
        timeframe: Timeframe string

    Returns:
        List of Quote objects
    """
    loader = DataLoader()
    return loader.load_market_data(symbol, start_date, end_date, timeframe)
