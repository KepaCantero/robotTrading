"""
Data Loader for Backtesting

Provides functionality to load historical market data from various sources:
- CSV files from data/historical/
- External APIs (yfinance, Interactive Brokers)
- Market data feeds
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pandas as pd

# Try multiple Yahoo Finance libraries as fallbacks
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from yahoo_fin.stock_info import get_data as yahoo_fin_get_data
    HAS_YAHOO_FIN = True
except ImportError:
    HAS_YAHOO_FIN = False

from app.models.market_data import Quote

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
            # Read CSV and handle both 'date' and 'timestamp' column names
            df = pd.read_csv(file_path)

            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()

            # Handle 'date' or 'timestamp' column
            date_col = 'date' if 'date' in df.columns else 'timestamp'
            df[date_col] = pd.to_datetime(df[date_col])

            # Filter by date range
            df = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]

            quotes = []
            for _, row in df.iterrows():
                timestamp = (
                    row[date_col]
                    if isinstance(row[date_col], datetime)
                    else pd.to_datetime(row[date_col]).to_pydatetime()
                )

                quote = Quote(
                    symbol=symbol,
                    bid=Decimal(str(row["close"])),
                    ask=Decimal(str(row["close"])),
                    last=Decimal(str(row["close"])),
                    volume=Decimal(str(row["volume"])),
                    timestamp=timestamp,
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    open=Decimal(str(row["open"])),
                    close=Decimal(str(row["close"])),
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
        """
        Load data from Yahoo Finance using multiple libraries as fallbacks.
        
        Tries:
        1. yfinance (primary)
        2. yahoo_fin (fallback)
        """
        # Try yfinance first
        if HAS_YFINANCE:
            try:
                ticker = yf.Ticker(symbol)
                interval = "1d" if timeframe == "1d" else "1h"
                hist = ticker.history(start=start_date, end=end_date, interval=interval)

                if not hist.empty:
                    quotes = self._convert_yfinance_to_quotes(hist, symbol)
                    logger.info(f"Loaded {len(quotes)} quotes from yfinance for {symbol}")
                    return quotes
            except Exception as e:
                logger.debug(f"yfinance failed for {symbol}: {e}, trying yahoo_fin...")
        
        # Fallback to yahoo_fin
        if HAS_YAHOO_FIN:
            try:
                # yahoo_fin uses mm/dd/yyyy format
                start_str = start_date.strftime("%m/%d/%Y")
                end_str = end_date.strftime("%m/%d/%Y")
                interval = "1d" if timeframe == "1d" else "1wk"
                
                df = yahoo_fin_get_data(
                    symbol,
                    start_date=start_str,
                    end_date=end_str,
                    index_as_date=True,
                    interval=interval,
                )
                
                if df is not None and not df.empty:
                    quotes = self._convert_dataframe_to_quotes(df, symbol)
                    logger.info(f"Loaded {len(quotes)} quotes from yahoo_fin for {symbol}")
                    return quotes
            except Exception as e:
                logger.debug(f"yahoo_fin failed for {symbol}: {e}")
        
        logger.warning(f"No data available from Yahoo Finance libraries for {symbol}")
        return []
    
    def _convert_yfinance_to_quotes(self, hist: pd.DataFrame, symbol: str) -> List[Quote]:
        """Convert yfinance DataFrame to Quote objects."""
        quotes = []
        for idx, row in hist.iterrows():
            timestamp = idx if isinstance(idx, datetime) else pd.to_datetime(idx).to_pydatetime()
            
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
        return quotes
    
    def _convert_dataframe_to_quotes(self, df: pd.DataFrame, symbol: str) -> List[Quote]:
        """Convert pandas DataFrame (from yahoo_fin or CSV) to Quote objects."""
        quotes = []
        
        for idx, row in df.iterrows():
            # Handle date index
            if isinstance(idx, datetime):
                timestamp = idx
            elif isinstance(idx, pd.Timestamp):
                timestamp = idx.to_pydatetime()
            else:
                timestamp = pd.to_datetime(idx).to_pydatetime()
            
            # Get close price (primary price)
            close = Decimal(str(row.get("close", row.get("Close", row.get("last", 100)))))
            
            quote = Quote(
                symbol=symbol,
                bid=close,
                ask=close,
                last=close,
                volume=Decimal(str(row.get("volume", row.get("Volume", 0)))),
                timestamp=timestamp,
                high=Decimal(str(row.get("high", row.get("High", close)))),
                low=Decimal(str(row.get("low", row.get("Low", close)))),
                open=Decimal(str(row.get("open", row.get("Open", close)))),
                close=close,
            )
            quotes.append(quote)
        
        return quotes

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
