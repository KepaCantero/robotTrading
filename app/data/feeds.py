"""
Market Data Feed Interfaces

This module defines abstract interfaces and concrete implementations for
market data feeds from various providers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from app.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    Quote,
)

logger = logging.getLogger(__name__)


class DataFeedInterface(ABC):
    """Abstract interface for market data feeds."""

    def __init__(self, config: DataFeedConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(config.rate_limit)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data feed."""

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the data feed."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol."""

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get historical data for a symbol."""

    @abstractmethod
    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to real-time updates for symbols."""

    async def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        async with self._rate_limiter:
            if not self.session:
                raise ConnectionError("Not connected to data feed")

            try:
                async with self.session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.config.error_count = 0
                        self.config.last_updated = datetime.utcnow()
                        return data
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}",
                        )
            except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
                self.config.error_count += 1
                logger.error(f"Request failed for {url}: {e}")
                raise


class AlphaVantageFeed(DataFeedInterface):
    """Alpha Vantage market data feed implementation."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = "https://www.alphavantage.co/query"

    async def connect(self) -> bool:
        """Connect to Alpha Vantage API."""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("Connected to Alpha Vantage API")
            return True
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to connect to Alpha Vantage: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Alpha Vantage API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Alpha Vantage API")
        return True

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from Alpha Vantage."""
        if not self.config.api_key:
            logger.error("Alpha Vantage API key not configured")
            return None

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.config.api_key,
        }

        try:
            data = await self._make_request(self.base_url, params)

            if "Global Quote" not in data:
                logger.warning(f"No quote data for {symbol}")
                return None

            quote_data = data["Global Quote"]

            return Quote(  # type: ignore
                symbol=symbol,
                bid=Decimal(quote_data.get("05. price", "0")),
                ask=Decimal(quote_data.get("05. price", "0")),
                last=Decimal(quote_data.get("05. price", "0")),
                open=Decimal(quote_data.get("02. open", "0")),
                high=Decimal(quote_data.get("03. high", "0")),
                low=Decimal(quote_data.get("04. low", "0")),
                close=Decimal(quote_data.get("08. previous close", "0")),
                volume=Decimal(quote_data.get("06. volume", "0")),
                spread=Decimal("0.01"),  # Default spread
                change=Decimal(quote_data.get("09. change", "0")),
                change_percent=Decimal(quote_data.get("10. change percent", "0").replace("%", "")),
                feed_type=DataFeedType.ALPHA_VANTAGE,
                metadata={"raw_data": quote_data},
            )
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get historical data from Alpha Vantage."""
        if not self.config.api_key:
            logger.error("Alpha Vantage API key not configured")
            return []

        # Map frequency to Alpha Vantage function
        function_map = {
            DataFrequency.DAILY: "TIME_SERIES_DAILY",
            DataFrequency.HOURLY: "TIME_SERIES_INTRADAY",
            DataFrequency.FIVE_MINUTES: "TIME_SERIES_INTRADAY",
        }

        function = function_map.get(frequency, "TIME_SERIES_DAILY")
        params = {"function": function, "symbol": symbol, "apikey": self.config.api_key}

        if frequency in [DataFrequency.HOURLY, DataFrequency.FIVE_MINUTES]:
            params["interval"] = "5min" if frequency == DataFrequency.FIVE_MINUTES else "60min"

        try:
            data = await self._make_request(self.base_url, params)

            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break

            if not time_series_key:
                logger.warning(f"No historical data for {symbol}")
                return []

            historical_data = []
            time_series = data[time_series_key]

            for date_str, values in time_series.items():
                date = datetime.strptime(date_str, "%Y-%m-%d")

                if start_date <= date <= end_date:
                    historical_data.append(
                        HistoricalData(  # type: ignore
                            symbol=symbol,
                            timestamp=date,
                            open=Decimal(values["1. open"]),
                            high=Decimal(values["2. high"]),
                            low=Decimal(values["3. low"]),
                            close=Decimal(values["4. close"]),
                            volume=Decimal(values["5. volume"]),
                            feed_type=DataFeedType.ALPHA_VANTAGE,
                            frequency=frequency,
                            metadata={"raw_data": values},
                        )
                    )

            return sorted(historical_data, key=lambda x: x.timestamp)
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Alpha Vantage doesn't support real-time subscriptions."""
        logger.warning("Alpha Vantage doesn't support real-time subscriptions")
        return False


class YahooFinanceFeed(DataFeedInterface):
    """Yahoo Finance market data feed implementation."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    async def connect(self) -> bool:
        """Connect to Yahoo Finance API."""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("Connected to Yahoo Finance API")
            return True
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to connect to Yahoo Finance: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Yahoo Finance API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Yahoo Finance API")
        return True

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from Yahoo Finance."""
        url = f"{self.base_url}/{symbol}"
        params = {"range": "1d", "interval": "1m", "includePrePost": "true"}

        try:
            data = await self._make_request(url, params)

            if "chart" not in data or not data["chart"]["result"]:
                logger.warning(f"No quote data for {symbol}")
                return None

            result = data["chart"]["result"][0]
            meta = result["meta"]
            quote = result["indicators"]["quote"][0]

            # Get latest data point
            timestamps = result["timestamp"]
            if not timestamps:
                logger.warning(f"No timestamp data for {symbol}")
                return None

            latest_idx = -1
            latest_close = quote["close"][latest_idx]

            if latest_close is None:
                logger.warning(f"No close price for {symbol}")
                return None

            return Quote(  # type: ignore
                symbol=symbol,
                bid=Decimal(str(latest_close)),
                ask=Decimal(str(latest_close)),
                last=Decimal(str(latest_close)),
                open=Decimal(str(quote["open"][latest_idx] or latest_close)),
                high=Decimal(str(quote["high"][latest_idx] or latest_close)),
                low=Decimal(str(quote["low"][latest_idx] or latest_close)),
                close=Decimal(str(latest_close)),
                volume=Decimal(str(quote["volume"][latest_idx] or 0)),
                spread=Decimal("0.01"),  # Default spread
                change=Decimal(str(meta.get("regularMarketChange", 0))),
                change_percent=Decimal(str(meta.get("regularMarketChangePercent", 0))),
                feed_type=DataFeedType.YAHOO_FINANCE,
                metadata={"raw_data": result},
            )
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get historical data from Yahoo Finance."""
        # Map frequency to Yahoo Finance interval
        interval_map = {
            DataFrequency.DAILY: "1d",
            DataFrequency.HOURLY: "1h",
            DataFrequency.FIVE_MINUTES: "5m",
            DataFrequency.FIFTEEN_MINUTES: "15m",
        }

        interval = interval_map.get(frequency, "1d")

        # Convert dates to timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        url = f"{self.base_url}/{symbol}"
        params = {
            "period1": start_timestamp,
            "period2": end_timestamp,
            "interval": interval,
            "includePrePost": "true",
        }

        try:
            data = await self._make_request(url, params)

            if "chart" not in data or not data["chart"]["result"]:
                logger.warning(f"No historical data for {symbol}")
                return []

            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            historical_data = []

            for i, timestamp in enumerate(timestamps):
                date = datetime.fromtimestamp(timestamp)

                if start_date <= date <= end_date:
                    historical_data.append(
                        HistoricalData(  # type: ignore
                            symbol=symbol,
                            timestamp=date,
                            open=Decimal(str(quote["open"][i] or 0)),
                            high=Decimal(str(quote["high"][i] or 0)),
                            low=Decimal(str(quote["low"][i] or 0)),
                            close=Decimal(str(quote["close"][i] or 0)),
                            volume=Decimal(str(quote["volume"][i] or 0)),
                            feed_type=DataFeedType.YAHOO_FINANCE,
                            frequency=frequency,
                            metadata={"raw_data": result},
                        )
                    )

            return historical_data
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Yahoo Finance doesn't support real-time subscriptions."""
        logger.warning("Yahoo Finance doesn't support real-time subscriptions")
        return False


class PolygonFeed(DataFeedInterface):
    """Polygon.io (massive.com) market data feed implementation for real-time data."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = "https://api.massive.com"

    async def connect(self) -> bool:
        """Connect to Massive.com (Polygon.io) API."""
        try:
            self.session = aiohttp.ClientSession()
            logger.info("Connected to Massive.com (Polygon.io) API")
            return True
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to connect to Massive.com: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Massive.com API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Massive.com (Polygon.io) API")
        return True

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from Massive.com (Polygon.io)."""
        if not self.config.api_key:
            logger.error("Massive.com API key not configured")
            return None

        # Massive.com snapshot endpoint
        url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        params = {"apiKey": self.config.api_key}

        try:
            data = await self._make_request(url, params)

            if data.get("status") != "OK" or not data.get("snapshot"):
                logger.warning(f"No quote data for {symbol}")
                return None

            snapshot = data["snapshot"]

            # Extract quote data from snapshot
            day_data = snapshot.get("day", {})
            quote_data = snapshot.get("lastQuote", {})
            prev_day = snapshot.get("prevDay", {})

            close = Decimal(str(day_data.get("c", 0)))
            high = Decimal(str(day_data.get("h", 0)))
            low = Decimal(str(day_data.get("l", 0)))
            open_price = Decimal(str(day_data.get("o", 0)))
            volume = Decimal(str(day_data.get("v", 0)))

            # Get bid/ask from last quote
            bid = Decimal(str(quote_data.get("p", 0))) if quote_data else close
            ask = Decimal(str(quote_data.get("P", 0))) if quote_data else close

            # Calculate change
            prev_close = Decimal(str(prev_day.get("c", 0))) if prev_day else close
            change = close - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else Decimal("0")

            # Spread calculation
            calculated_spread = ask - bid if bid > 0 and ask > 0 else Decimal("0.01")

            return Quote(  # type: ignore
                symbol=symbol,
                bid=bid if bid > 0 else close,
                ask=ask if ask > 0 else close,
                last=close,
                open=open_price if open_price > 0 else close,
                high=high if high > 0 else close,
                low=low if low > 0 else close,
                close=close,
                volume=volume,
                spread=calculated_spread if calculated_spread > 0 else Decimal("0.01"),
                change=change,
                change_percent=change_percent,
                feed_type=DataFeedType.POLYGON,
                metadata={"raw_data": snapshot},
            )
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get historical data from Massive.com (Polygon.io)."""
        if not self.config.api_key:
            logger.error("Massive.com API key not configured")
            return []

        # Map frequency to Massive timespan
        timespan_map = {
            DataFrequency.DAILY: "day",
            DataFrequency.HOURLY: "hour",
            DataFrequency.FIVE_MINUTES: "minute",
            DataFrequency.FIFTEEN_MINUTES: "minute",
        }

        # Map frequency to Massive multiplier
        multiplier_map = {
            DataFrequency.DAILY: 1,
            DataFrequency.HOURLY: 1,
            DataFrequency.FIVE_MINUTES: 5,
            DataFrequency.FIFTEEN_MINUTES: 15,
        }

        timespan = timespan_map.get(frequency, "day")
        multiplier = multiplier_map.get(frequency, 1)

        # Convert dates to timestamps (milliseconds)
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_timestamp}/{end_timestamp}"
        params = {"apiKey": self.config.api_key, "adjusted": "true"}

        try:
            data = await self._make_request(url, params)

            if not data.get("results"):
                logger.warning(f"No historical data for {symbol}")
                return []

            historical_data = []

            for result in data["results"]:
                timestamp = datetime.fromtimestamp(result["t"] / 1000)

                if start_date <= timestamp <= end_date:
                    historical_data.append(
                        HistoricalData(  # type: ignore
                            symbol=symbol,
                            timestamp=timestamp,
                            open=Decimal(str(result.get("o", 0))),
                            high=Decimal(str(result.get("h", 0))),
                            low=Decimal(str(result.get("l", 0))),
                            close=Decimal(str(result.get("c", 0))),
                            volume=Decimal(str(result.get("v", 0))),
                            feed_type=DataFeedType.POLYGON,
                            frequency=frequency,
                            metadata={"raw_data": result},
                        )
                    )

            return historical_data
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Massive.com supports real-time subscriptions via WebSocket (not implemented here)."""
        logger.warning("Massive.com WebSocket subscriptions not implemented in HTTP mode")
        return False


def create_data_feed(config: DataFeedConfig) -> DataFeedInterface:
    """
    Factory function to create data feed instances.

    NOTE: Mock data has been removed - only real data sources are supported.
    For backtesting, use Yahoo Finance (free) or configure Polygon/AlphaVantage API keys.
    """
    if config.feed_type == DataFeedType.ALPHA_VANTAGE:
        return AlphaVantageFeed(config)
    elif config.feed_type == DataFeedType.YAHOO_FINANCE:
        return YahooFinanceFeed(config)
    elif config.feed_type == DataFeedType.POLYGON:
        return PolygonFeed(config)
    else:
        raise ValueError(
            f"Unsupported feed type: {config.feed_type}. "
            f"Please use YAHOO_FINANCE (free) or configure API keys for POLYGON/ALPHA_VANTAGE."
        )
