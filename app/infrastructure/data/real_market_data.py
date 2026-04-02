from __future__ import annotations

# mypy: ignore-errors
# mypy: ignore-errors
"""
Real Market Data Fetcher - Alpha Vantage Integration

This module provides functionality to fetch REAL market data from Alpha Vantage
for backtesting the profile-driven trading algorithm.

Features:
- Fetch historical OHLCV data from Alpha Vantage
- Rate limiting (5 calls/minute for free tier)
- Data caching to avoid re-fetching
- Real S&P 500 top 50 stocks by market cap
- Error handling and logging

Author: AlgoTrading System
Date: 2025-01-25
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import pandas as pd
from requests.exceptions import HTTPError, RequestException

from app.shared.config.api_endpoints import APIEndpoints
from app.shared.config.timeout_config import get_timeouts

logger = logging.getLogger(__name__)

# Get centralized timeouts
_TIMEOUTS = get_timeouts()


# Real S&P 500 Top 50 Stocks by Market Cap (2025)
SP500_TOP_50 = [
    "AAPL",  # Apple Inc.
    "MSFT",  # Microsoft Corporation
    "GOOGL",  # Alphabet Inc.
    "AMZN",  # Amazon.com Inc.
    "NVDA",  # NVIDIA Corporation
    "TSLA",  # Tesla Inc.
    "META",  # Meta Platforms Inc.
    "GOOG",  # Alphabet Inc. Class C
    "BRK.B",  # Berkshire Hathaway Inc.
    "LLY",  # Eli Lilly and Company
    "AVGO",  # Broadcom Inc.
    "JPM",  # JPMorgan Chase & Co.
    "V",  # Visa Inc.
    "XOM",  # Exxon Mobil Corporation
    "UNH",  # UnitedHealth Group Incorporated
    "MA",  # Mastercard Incorporated
    "JNJ",  # Johnson & Johnson
    "HD",  # The Home Depot Inc.
    "PG",  # Procter & Gamble Co.
    "COST",  # Costco Wholesale Corporation
    "MRK",  # Merck & Co. Inc.
    "CVX",  # Chevron Corporation
    "ABBV",  # AbbVie Inc.
    "PEP",  # PepsiCo Inc.
    "BAC",  # Bank of America Corporation
    "KO",  # Coca-Cola Company
    "ADBE",  # Adobe Inc.
    "WMT",  # Walmart Inc.
    "CRM",  # Salesforce Inc.
    "MCD",  # McDonald's Corporation
    "NFLX",  # Netflix Inc.
    "AMD",  # Advanced Micro Devices Inc.
    "CSCO",  # Cisco Systems Inc.
    "ORCL",  # Oracle Corporation
    "CMCSA",  # Comcast Corporation
    "ACN",  # Accenture plc
    "INTC",  # Intel Corporation
    "DIS",  # The Walt Disney Company
    "QCOM",  # QUALCOMM Incorporated
    "TXN",  # Texas Instruments Incorporated
    "IBM",  # International Business Machines
    "AMGN",  # Amgen Inc.
    "BA",  # The Boeing Company
    "NKE",  # Nike Inc.
    "DHR",  # Danaher Corporation
    "HON",  # Honeywell International Inc.
    "CAT",  # Caterpillar Inc.
    "GE",  # General Electric Company
    "MDT",  # Medtronic plc
    "NOW",  # ServiceNow Inc.
    "ISRG",  # Intuitive Surgical Inc.
    "PLD",  # Prologis Inc.
]


class RealMarketDataFetcher:
    """
    Fetch real market data from Alpha Vantage API.

    Handles:
    - Rate limiting (5 calls/minute for free tier)
    - Data caching to disk
    - Error handling and retries
    - Progress logging
    """

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: str = "data/historical",
        rate_limit_calls: int = 5,
        rate_limit_period: int = 60,  # seconds
    ):
        """
        Initialize the real market data fetcher.

        Args:
            api_key: Alpha Vantage API key (reads from ALPHA_VANTAGE_API_KEY env var if None)
            cache_dir: Directory to cache fetched data
            rate_limit_calls: Number of API calls allowed in rate_limit_period
            rate_limit_period: Time period in seconds for rate limiting
        """
        logger.info(
            "Initializing RealMarketDataFetcher",
            extra={
                "cache_dir": cache_dir,
                "rate_limit_calls": rate_limit_calls,
                "rate_limit_period": rate_limit_period,
            },
        )

        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logger.error("Alpha Vantage API key not found", extra={"error": "api_key_missing"})
            raise ValueError(
                "Alpha Vantage API key not found. "
                "Set ALPHA_VANTAGE_API_KEY environment variable or pass api_key parameter."
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Use centralized endpoint configuration
        self.base_url = os.getenv("ALPHA_VANTAGE_URL", APIEndpoints.ALPHA_VANTAGE)
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period

        # Rate limiting tracking
        self.call_timestamps: list[datetime] = []

        # Session for HTTP requests
        self.session: aiohttp.ClientSession | None = None

        logger.info(
            "RealMarketDataFetcher initialized successfully",
            extra={
                "cache_dir": str(self.cache_dir),
                "rate_limit": f"{rate_limit_calls} calls per {rate_limit_period}s",
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> bool:
        """Connect to Alpha Vantage API."""
        logger.debug(
            "Attempting to connect to Alpha Vantage API", extra={"base_url": self.base_url}
        )
        try:
            self.session = aiohttp.ClientSession()
            logger.info(
                "Connected to Alpha Vantage API successfully",
                extra={"base_url": self.base_url, "connected": True},
            )
            return True
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(
                f"Failed to connect to Alpha Vantage: {e}",
                extra={
                    "base_url": self.base_url,
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Alpha Vantage API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Alpha Vantage API", extra={"connected": False})
        return True

    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limit."""
        logger.debug(
            "Checking rate limit",
            extra={
                "rate_limit_calls": self.rate_limit_calls,
                "rate_limit_period": self.rate_limit_period,
                "current_calls": len(self.call_timestamps),
            },
        )
        now = datetime.now()

        # Remove timestamps older than rate limit period
        self.call_timestamps = [
            ts for ts in self.call_timestamps if (now - ts).total_seconds() < self.rate_limit_period
        ]

        # If we've hit the limit, wait
        if len(self.call_timestamps) >= self.rate_limit_calls:
            wait_time = self.rate_limit_period - (now - self.call_timestamps[0]).total_seconds()
            if wait_time > 0:
                logger.info(
                    f"Rate limit reached, waiting {wait_time:.1f} seconds",
                    extra={
                        "wait_time_seconds": wait_time,
                        "calls_in_window": len(self.call_timestamps),
                        "rate_limit": self.rate_limit_calls,
                    },
                )
                await asyncio.sleep(wait_time)
                # Clean up old timestamps after waiting
                self.call_timestamps = []

    async def _fetch_from_alpha_vantage(self, symbol: str) -> dict | None:
        """
        Fetch daily time series data from Alpha Vantage.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            Raw JSON response or None if error
        """
        logger.debug(
            "Fetching data from Alpha Vantage", extra={"symbol": symbol, "base_url": self.base_url}
        )
        await self._wait_for_rate_limit()

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full",  # Get full history (up to 20 years)
            "apikey": self.api_key,
        }

        try:
            if not self.session:
                raise ConnectionError("Not connected to Alpha Vantage API")

            async with self.session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check for API error messages
                    if "Error Message" in data:
                        logger.error(
                            f"Alpha Vantage API error for {symbol}: {data['Error Message']}",
                            extra={"symbol": symbol, "api_error": data["Error Message"]},
                        )
                        return None

                    if "Note" in data:
                        logger.warning(
                            f"Alpha Vantage rate limit note for {symbol}: {data['Note']}",
                            extra={"symbol": symbol, "rate_limit_note": data["Note"]},
                        )
                        return None

                    # Record this call
                    self.call_timestamps.append(datetime.now())

                    return data
                else:
                    logger.error(
                        f"HTTP {response.status} for {symbol}",
                        extra={"symbol": symbol, "status_code": response.status},
                    )
                    return None

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout fetching data for {symbol}",
                extra={"symbol": symbol, "error_type": "TimeoutError"},
            )
            return None
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(
                f"Error fetching data for {symbol}: {e}",
                extra={"symbol": symbol, "error_type": type(e).__name__},
            )
            return None

    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        return self.cache_dir / f"{symbol}_daily.json"

    def _load_from_cache(self, symbol: str) -> pd.DataFrame | None:
        """
        Load data from cache if available.

        Checks both JSON cache (Alpha Vantage format) and CSV cache.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with OHLCV data or None
        """
        logger.debug(
            "Loading data from cache", extra={"symbol": symbol, "cache_dir": str(self.cache_dir)}
        )
        # First try JSON cache (Alpha Vantage format)
        cache_path = self._get_cache_path(symbol)

        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    data = json.load(f)

                # Check if cache is recent (less than 1 day old)
                cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
                if (datetime.now() - cache_time).days < 1:
                    logger.debug(
                        f"Loading {symbol} from JSON cache",
                        extra={"symbol": symbol, "cache_type": "json"},
                    )
                    return self._parse_alpha_vantage_data(data, symbol)
            except OSError as e:
                logger.debug(
                    f"Failed to load JSON cache for {symbol}: {e}",
                    extra={"symbol": symbol, "error_type": type(e).__name__},
                )

        # Try CSV cache (fallback for existing cached data)
        csv_path = self.cache_dir / f"{symbol}.csv"
        if csv_path.exists():
            try:
                logger.debug(
                    f"Loading {symbol} from CSV cache",
                    extra={"symbol": symbol, "cache_type": "csv"},
                )
                df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
                # Ensure we have the right columns
                required_cols = ["open", "high", "low", "close", "volume"]
                if all(col in df.columns for col in required_cols):
                    logger.info(
                        f"Loaded {symbol} from CSV cache ({len(df)} rows)",
                        extra={"symbol": symbol, "cache_type": "csv", "rows": len(df)},
                    )
                    # Don't check staleness for CSV files - they can be used for backtesting
                    return df.sort_index()
            except OSError as e:
                logger.warning(
                    f"Failed to load CSV cache for {symbol}: {e}",
                    extra={"symbol": symbol, "error_type": type(e).__name__},
                )

        return None

    def _save_to_cache(self, symbol: str, data: dict):
        """
        Save fetched data to cache.

        Args:
            symbol: Stock symbol
            data: Raw JSON data from Alpha Vantage
        """
        cache_path = self._get_cache_path(symbol)

        try:
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(
                f"Cached data for {symbol}", extra={"symbol": symbol, "cache_path": str(cache_path)}
            )
        except OSError as e:
            logger.warning(
                f"Failed to cache data for {symbol}: {e}",
                extra={"symbol": symbol, "error_type": type(e).__name__},
            )

    def _parse_alpha_vantage_data(self, data: dict, symbol: str) -> pd.DataFrame | None:
        """
        Parse Alpha Vantage time series data into DataFrame.

        Args:
            data: Raw JSON response from Alpha Vantage
            symbol: Stock symbol

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        logger.debug(
            "Parsing Alpha Vantage data", extra={"symbol": symbol, "data_keys": list(data.keys())}
        )
        try:
            # Find the time series key
            time_series_key = None
            for key in data:
                if "Time Series" in key:
                    time_series_key = key
                    break

            if not time_series_key:
                logger.warning(
                    f"No time series data for {symbol}",
                    extra={"symbol": symbol, "data_keys": list(data.keys())},
                )
                return None

            time_series = data[time_series_key]

            # Parse into DataFrame
            records = []
            for date_str, values in time_series.items():
                records.append(
                    {
                        "date": pd.to_datetime(date_str),
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": int(values["5. volume"]),
                    }
                )

            df = pd.DataFrame(records)
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            return df

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(
                f"Failed to parse data for {symbol}: {e}",
                extra={"symbol": symbol, "error_type": type(e).__name__},
            )
            return None

    async def fetch_symbol_data(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame | None:
        """
        Fetch historical data for a single symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            start_date: Start date for filtering (default: 1 year ago)
            end_date: End date for filtering (default: today)
            use_cache: Whether to use cached data if available

        Returns:
            DataFrame with OHLCV data or None if error
        """
        logger.info(
            f"Fetching data for {symbol}",
            extra={
                "symbol": symbol,
                "use_cache": use_cache,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        )

        # Try cache first
        if use_cache:
            cached_df = self._load_from_cache(symbol)
            if cached_df is not None:
                logger.debug(
                    f"Using cached data for {symbol}", extra={"symbol": symbol, "cache_hit": True}
                )
                return self._filter_by_date(cached_df, start_date, end_date)

        # Fetch from API
        raw_data = await self._fetch_from_alpha_vantage(symbol)

        if raw_data is None:
            logger.warning(
                f"Failed to fetch data for {symbol}", extra={"symbol": symbol, "cache_hit": False}
            )
            return None

        # Parse data
        df = self._parse_alpha_vantage_data(raw_data, symbol)

        if df is None:
            logger.error(f"Failed to parse data for {symbol}", extra={"symbol": symbol})
            return None

        # Save to cache
        self._save_to_cache(symbol, raw_data)

        # Filter by date
        df = self._filter_by_date(df, start_date, end_date)

        logger.info(
            f"Successfully retrieved {len(df)} data points for {symbol}",
            extra={
                "symbol": symbol,
                "data_points": len(df),
                "start": df.index[0].isoformat() if len(df) > 0 else None,
                "end": df.index[-1].isoformat() if len(df) > 0 else None,
            },
        )
        return df

    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> pd.DataFrame:
        """Filter DataFrame by date range."""
        if start_date is not None:
            df = df[df.index >= start_date]
        if end_date is not None:
            df = df[df.index <= end_date]
        return df

    async def fetch_multiple_symbols(
        self,
        symbols: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        use_cache: bool = True,
        show_progress: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date for filtering (default: 1 year ago)
            end_date: End date for filtering (default: today)
            use_cache: Whether to use cached data if available
            show_progress: Whether to show progress logging

        Returns:
            Dict of symbol -> DataFrame with OHLCV data
        """
        logger.info(
            f"Fetching data for {len(symbols)} symbols...",
            extra={
                "symbol_count": len(symbols),
                "use_cache": use_cache,
                "show_progress": show_progress,
            },
        )

        # Set default date range
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)  # 1 year

        results = {}

        for i, symbol in enumerate(symbols):
            if show_progress:
                logger.info(
                    f"[{i + 1}/{len(symbols)}] Fetching {symbol}...",
                    extra={
                        "symbol": symbol,
                        "progress": f"{i + 1}/{len(symbols)}",
                        "progress_pct": round((i + 1) / len(symbols) * 100, 1),
                    },
                )

            df = await self.fetch_symbol_data(
                symbol,
                start_date=start_date,
                end_date=end_date,
                use_cache=use_cache,
            )

            if df is not None and len(df) > 0:
                results[symbol] = df
            else:
                logger.warning(f"Failed to fetch data for {symbol}", extra={"symbol": symbol})

        logger.info(
            f"Successfully fetched data for {len(results)}/{len(symbols)} symbols",
            extra={
                "success_count": len(results),
                "total_count": len(symbols),
                "success_rate": round(len(results) / len(symbols) * 100, 1) if symbols else 0,
            },
        )

        return results

    async def fetch_sp500_top_n(
        self,
        n: int = 50,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical data for top N S&P 500 stocks.

        Args:
            n: Number of top stocks to fetch (default: 50)
            start_date: Start date for filtering
            end_date: End date for filtering
            use_cache: Whether to use cached data

        Returns:
            Dict of symbol -> DataFrame with OHLCV data
        """
        symbols = SP500_TOP_50[:n]
        logger.info(f"Fetching top {n} S&P 500 stocks...", extra={"n": n, "symbols": symbols})

        return await self.fetch_multiple_symbols(
            symbols,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get statistics about cached data.

        Returns:
            Dict with cache statistics
        """
        logger.debug("Getting cache statistics", extra={"cache_dir": str(self.cache_dir)})
        cache_files = list(self.cache_dir.glob("*_daily.json"))

        stats = {
            "total_cached_symbols": len(cache_files),
            "cache_size_mb": sum(f.stat().st_size for f in cache_files) / (1024 * 1024),
        }

        # Get age of oldest and newest cache files
        if cache_files:
            mtimes = [f.stat().st_mtime for f in cache_files]
            stats["oldest_cache_days"] = (datetime.now().timestamp() - max(mtimes)) / 86400
            stats["newest_cache_days"] = (datetime.now().timestamp() - min(mtimes)) / 86400

        return stats

    def clear_cache(self, symbol: str | None = None):
        """
        Clear cached data.

        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            cache_path = self._get_cache_path(symbol)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(
                    f"Cleared cache for {symbol}", extra={"symbol": symbol, "action": "clear_cache"}
                )
        else:
            # Clear all cache files
            cache_files = list(self.cache_dir.glob("*_daily.json"))
            for f in cache_files:
                f.unlink()
            logger.info(
                f"Cleared {len(cache_files)} cached files",
                extra={"files_cleared": len(cache_files), "action": "clear_all_cache"},
            )


def get_default_symbols(count: int = 50) -> list[str]:
    """
    Get default list of S&P 500 top symbols.

    Args:
        count: Number of symbols to return

    Returns:
        List of stock symbols
    """
    return SP500_TOP_50[:count]
