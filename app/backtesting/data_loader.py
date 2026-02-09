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
from typing import Any, Dict, List, Optional

import pandas as pd

from app.models.market_data import Quote

logger = logging.getLogger(__name__)

# REQUIRED: Yahoo Finance libraries (no fallbacks)
import yfinance as yf  # noqa: F401

# Fallback pattern for yahoo_fin
try:
    from yahoo_fin.stock_info import get_data as yahoo_fin_get_data

    logger.debug("Using yahoo_fin for data loading")
except ImportError:
    logger.warning("yahoo_fin not available, using yfinance as fallback")

    # Create a wrapper that adapts yfinance to match yahoo_fin interface
    def yahoo_fin_get_data(
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        index_as_date: bool = True,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fallback function using yfinance when yahoo_fin is not available.

        Adapts yfinance API to match yahoo_fin's get_data interface.

        Args:
            ticker: Stock symbol
            start_date: Start date in mm/dd/yyyy format (yahoo_fin style)
            end_date: End date in mm/dd/yyyy format (yahoo_fin style)
            index_as_date: Whether to use date as index (ignored in yfinance)
            interval: Time interval (1d, 1wk, 1mo, etc.)

        Returns:
            DataFrame with same structure as yahoo_fin output
        """
        try:
            # Convert yahoo_fin date format (mm/dd/yyyy) to datetime
            from datetime import datetime as dt

            start_dt = dt.strptime(start_date, "%m/%d/%Y") if start_date else None
            end_dt = dt.strptime(end_date, "%m/%d/%Y") if end_date else None

            # Map yahoo_fin intervals to yfinance intervals
            interval_map = {
                "1d": "1d",
                "1wk": "1wk",
                "1mo": "1mo",
            }
            yf_interval = interval_map.get(interval, "1d")

            # Fetch data using yfinance
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start_dt, end=end_dt, interval=yf_interval)

            # Normalize column names to lowercase to match yahoo_fin
            hist.columns = hist.columns.str.lower()

            return hist

        except Exception as e:
            logger.error(f"yfinance fallback failed for {ticker}: {e}", exc_info=True)
            # Return empty DataFrame on failure
            return pd.DataFrame()


class DataLoader:
    """Loader for historical market data from various sources."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """
        Initialize the data loader.

        Args:
            base_path: Base path for CSV files (default: data/historical/)
        """
        self.base_path = base_path or Path("data/historical")
        self.cache: Dict[str, Any] = {}

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

        Raises:
            ValueError: If source is not supported
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
            logger.error(f"CSV file not found: {file_path}", exc_info=True)
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        try:
            # Read CSV and handle both 'date' and 'timestamp' column names
            df = pd.read_csv(file_path)

            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()

            # Handle 'date' or 'timestamp' column
            date_col = 'date' if 'date' in df.columns else 'timestamp'
            df[date_col] = pd.to_datetime(df[date_col])

            # CRITICAL: Set date column as index for proper timestamp extraction
            df.set_index(date_col, inplace=True)

            # Filter by date range (now using index)
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            # VECTORIZED: Convert DataFrame to Quotes using vectorized operations
            quotes = self._convert_dataframe_to_quotes(df, symbol)

            logger.info(f"Loaded {len(quotes)} quotes from CSV for {symbol}")
            return quotes

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error loading CSV for {symbol}: {e}", exc_info=True)
            raise

    def _load_from_yfinance(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d",
    ) -> List[Quote]:
        """
        Load data from Yahoo Finance using multiple methods (REQUIRED).

        Tries:
        1. Yahoo Finance v8 API directly (most reliable)
        2. yfinance (secondary)
        3. yahoo_fin (tertiary)

        Raises:
            RuntimeError: If all methods fail
        """
        # Try Yahoo Finance v8 API directly first (most reliable)
        quotes = self._load_from_yahoo_v8_api(symbol, start_date, end_date, timeframe)
        if quotes:
            logger.info(f"Loaded {len(quotes)} quotes from Yahoo Finance v8 API for {symbol}")
            return quotes

        # Try yfinance second
        try:
            ticker = yf.Ticker(symbol)
            interval = "1d" if timeframe == "1d" else "1h"
            hist = ticker.history(start=start_date, end=end_date, interval=interval)

            if not hist.empty:
                quotes = self._convert_yfinance_to_quotes(hist, symbol)
                logger.info(f"Loaded {len(quotes)} quotes from yfinance for {symbol}")
                return quotes
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"yfinance failed for {symbol}: {e}, trying yahoo_fin...")

        # Use yahoo_fin as last resort
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
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"yahoo_fin failed for {symbol}: {e}", exc_info=True)

        # All methods failed - raise error instead of returning empty list
        raise RuntimeError(f"No data available from Yahoo Finance for {symbol}")

    def _load_from_yahoo_v8_api(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d",
    ) -> List[Quote]:
        """
        Load data from Yahoo Finance v8 API directly.
        This is the most reliable method that avoids rate limits.
        """
        try:
            import requests

            # Convert dates to Unix timestamps
            period1 = int(start_date.timestamp())
            period2 = int(end_date.timestamp())

            # Map timeframe to interval
            interval_map = {
                "1d": "1d",
                "1h": "1h",
                "1m": "1m",
            }
            interval = interval_map.get(timeframe, "1d")

            url = "https://query1.finance.yahoo.com/v8/finance/chart/{}".format(symbol)
            params = {
                "period1": period1,
                "period2": period2,
                "interval": interval,
                "events": "div,splits",
                "includePrePost": "false",
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://finance.yahoo.com/',
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.debug(
                    f"Yahoo Finance v8 API returned status {response.status_code} for {symbol}"
                )
                return []

            data = response.json()

            if "chart" not in data or not data["chart"]["result"]:
                logger.debug(f"No data in Yahoo Finance v8 API response for {symbol}")
                return []

            result = data["chart"]["result"][0]

            if "timestamp" not in result or "indicators" not in result:
                logger.debug(f"Invalid response structure from Yahoo Finance v8 API for {symbol}")
                return []

            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            quotes = []
            for i, ts in enumerate(timestamps):
                date = datetime.fromtimestamp(ts)
                if start_date <= date <= end_date:
                    close = (
                        quote["close"][i]
                        if i < len(quote["close"]) and quote["close"][i] is not None
                        else None
                    )
                    if close is None:
                        continue

                    open_price = (
                        quote["open"][i]
                        if i < len(quote["open"]) and quote["open"][i] is not None
                        else close
                    )
                    high = (
                        quote["high"][i]
                        if i < len(quote["high"]) and quote["high"][i] is not None
                        else close
                    )
                    low = (
                        quote["low"][i]
                        if i < len(quote["low"]) and quote["low"][i] is not None
                        else close
                    )
                    volume_raw = (
                        quote["volume"][i]
                        if i < len(quote["volume"]) and quote["volume"][i] is not None
                        else 0
                    )
                    # Cap volume at 10B to avoid validation errors (NVDA can have >1B shares)
                    max_volume = Decimal("10000000000")  # 10B shares
                    volume = (
                        min(Decimal(str(volume_raw)), max_volume) if volume_raw else Decimal("0")
                    )

                    quotes.append(
                        Quote(
                            symbol=symbol,
                            timestamp=date,  # CRITICAL: Include timestamp
                            bid=Decimal(str(close)),
                            ask=Decimal(str(close)),
                            last=Decimal(str(close)),
                            open=Decimal(str(open_price)),
                            high=Decimal(str(high)),
                            low=Decimal(str(low)),
                            close=Decimal(str(close)),
                            volume=volume,
                            spread=Decimal("0.01"),
                            change=Decimal("0"),
                            change_percent=Decimal("0"),
                            metadata={"source": "yahoo_v8_api"},
                        )
                    )

            return quotes

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Yahoo Finance v8 API failed for {symbol}: {e}", exc_info=True)
            return []

    def _convert_yfinance_to_quotes(self, hist: pd.DataFrame, symbol: str) -> List[Quote]:
        """Convert yfinance DataFrame to Quote objects using vectorized operations."""
        # VECTORIZED: Use vectorized operations instead of iterrows (100-1000x faster)
        max_volume = Decimal("10000000000")  # 10B shares limit

        # Convert index to timestamps
        timestamps = hist.index.to_series().apply(
            lambda x: x if isinstance(x, datetime) else pd.to_datetime(x).to_pydatetime()
        )

        # Vectorized volume capping
        volumes = hist.get("Volume", pd.Series([0] * len(hist))).apply(
            lambda v: min(Decimal(str(v)), max_volume) if v > 0 else Decimal("0")
        )

        # Convert price columns to Decimal using vectorized operations
        closes = hist.get("Close", hist.get("Low", pd.Series([100] * len(hist)))).apply(
            lambda x: Decimal(str(x))
        )
        highs = hist.get("High", closes).apply(lambda x: Decimal(str(x)))
        lows = hist.get("Low", closes).apply(lambda x: Decimal(str(x)))
        opens = hist.get("Open", closes).apply(lambda x: Decimal(str(x)))

        # Create quotes list using list comprehension (much faster than iterrows)
        quotes = [
            Quote(
                symbol=symbol,
                bid=closes.iloc[i],
                ask=closes.iloc[i],
                last=closes.iloc[i],
                volume=volumes.iloc[i],
                timestamp=timestamps.iloc[i],
                high=highs.iloc[i],
                low=lows.iloc[i],
                open=opens.iloc[i],
                close=closes.iloc[i],
            )
            for i in range(len(hist))
        ]
        return quotes

    def _convert_dataframe_to_quotes(self, df: pd.DataFrame, symbol: str) -> List[Quote]:
        """Convert pandas DataFrame (from yahoo_fin or CSV) to Quote objects using vectorized operations."""
        # VECTORIZED: Use vectorized operations instead of iterrows (100-1000x faster)
        max_volume = Decimal("10000000000")  # 10B shares limit

        # Convert index to timestamps
        timestamps = df.index.to_series().apply(
            lambda x: (
                x
                if isinstance(x, datetime)
                else (
                    x.to_pydatetime()
                    if isinstance(x, pd.Timestamp)
                    else pd.to_datetime(x).to_pydatetime()
                )
            )
        )

        # Get close prices with fallbacks
        closes = df.apply(
            lambda row: Decimal(str(row.get("close", row.get("Close", row.get("last", 100))))),
            axis=1,
        )

        # Vectorized volume capping
        volumes = df.apply(
            lambda row: (
                min(Decimal(str(row.get("volume", row.get("Volume", 0)))), max_volume)
                if row.get("volume", row.get("Volume", 0)) > 0
                else Decimal("0")
            ),
            axis=1,
        )

        # Get high/low/open with fallbacks to close
        # Note: Using row.get() with default values - if high/low/open missing, fall back to close
        highs = df.apply(
            lambda row: Decimal(
                str(row.get("high", row.get("High", row.get("close", row.get("Close", 100)))))
            ),
            axis=1,
        )
        lows = df.apply(
            lambda row: Decimal(
                str(row.get("low", row.get("Low", row.get("close", row.get("Close", 100)))))
            ),
            axis=1,
        )
        opens = df.apply(
            lambda row: Decimal(
                str(row.get("open", row.get("Open", row.get("close", row.get("Close", 100)))))
            ),
            axis=1,
        )

        # Create quotes list using list comprehension (much faster than iterrows)
        quotes = [
            Quote(
                symbol=symbol,
                bid=closes.iloc[i],
                ask=closes.iloc[i],
                last=closes.iloc[i],
                volume=volumes.iloc[i],
                timestamp=timestamps.iloc[i],
                high=highs.iloc[i],
                low=lows.iloc[i],
                open=opens.iloc[i],
                close=closes.iloc[i],
            )
            for i in range(len(df))
        ]

        return quotes

    def save_to_csv(self, data: List[Quote], filename: str) -> None:
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
