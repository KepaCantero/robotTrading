"""
Market Data Feed Interfaces

This module defines abstract interfaces and concrete implementations for
market data feeds from various providers.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

import aiohttp
from aiohttp import ClientError

from app.domain.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    MetadataValue,
    Quote,
)
from app.shared.config.api_endpoints import ENDPOINTS

logger = logging.getLogger(__name__)


class DataFeedInterface(ABC):
    """Abstract interface for market data feeds."""

    def __init__(self, config: DataFeedConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None
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
    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol."""

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> list[HistoricalData]:
        """Get historical data for a symbol."""

    @abstractmethod
    async def subscribe_to_symbols(self, symbols: list[str]) -> bool:
        """Subscribe to real-time updates for symbols."""

    async def _make_request(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        logger.debug(
            "Making HTTP request",
            extra={
                "url": url,
                "params": params,
                "feed_type": (
                    self.config.feed_type.value
                    if hasattr(self.config.feed_type, "value")
                    else str(self.config.feed_type)
                ),
            },
        )
        async with self._rate_limiter:
            if not self.session:
                raise ConnectionError("Not connected to data feed")

            try:
                async with self.session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                ) as response:
                    logger.debug(
                        "HTTP response received",
                        extra={
                            "url": url,
                            "status_code": response.status,
                        },
                    )
                    if response.status == 200:
                        data = await response.json()
                        self.config.error_count = 0
                        self.config.last_updated = datetime.utcnow()
                        logger.debug(
                            "HTTP request successful",
                            extra={
                                "url": url,
                                "error_count": self.config.error_count,
                            },
                        )
                        return data
                    else:
                        logger.warning(
                            "HTTP request returned non-200 status",
                            extra={
                                "url": url,
                                "status_code": response.status,
                            },
                        )
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}",
                        )
            except (ConnectionError, TimeoutError, ClientError) as e:
                self.config.error_count += 1
                logger.error(
                    f"Request failed for {url}: {e}",
                    extra={
                        "url": url,
                        "error_type": type(e).__name__,
                        "error_count": self.config.error_count,
                    },
                )
                raise


class AlphaVantageFeed(DataFeedInterface):
    """Alpha Vantage market data feed implementation."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = ENDPOINTS.ALPHA_VANTAGE

    async def connect(self) -> bool:
        """Connect to Alpha Vantage API."""
        logger.debug("Connecting to Alpha Vantage API", extra={"base_url": self.base_url})
        try:
            self.session = aiohttp.ClientSession()
            logger.info(
                "Connected to Alpha Vantage API",
                extra={"base_url": self.base_url, "connected": True},
            )
            return True
        except (ConnectionError, TimeoutError, ClientError) as e:
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

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote from Alpha Vantage."""
        logger.debug(
            "Getting quote from Alpha Vantage",
            extra={"symbol": symbol, "feed_type": "alpha_vantage"},
        )
        if not self.config.api_key:
            logger.error("Alpha Vantage API key not configured", extra={"symbol": symbol})
            return None

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.config.api_key,
        }

        try:
            data = await self._make_request(self.base_url, params)

            if "Global Quote" not in data:
                logger.warning(
                    f"No quote data for {symbol}",
                    extra={"symbol": symbol, "response_keys": list(data.keys())},
                )
                return None

            quote_data = data["Global Quote"]

            # Convert raw_data to MetadataDict format (flatten nested values to strings)
            raw_metadata: dict[str, MetadataValue] = {
                f"raw_{k}": str(v) for k, v in quote_data.items()
            }
            return Quote(
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
                metadata=raw_metadata,
            )
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(
                f"Failed to get quote for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> list[HistoricalData]:
        """Get historical data from Alpha Vantage."""
        logger.debug(
            "Getting historical data from Alpha Vantage",
            extra={
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "frequency": frequency.value,
            },
        )
        if not self.config.api_key:
            logger.error("Alpha Vantage API key not configured", extra={"symbol": symbol})
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
            for key in data:
                if "Time Series" in key:
                    time_series_key = key
                    break

            if not time_series_key:
                logger.warning(
                    f"No historical data for {symbol}",
                    extra={"symbol": symbol, "response_keys": list(data.keys())},
                )
                return []

            historical_data = []
            time_series = data[time_series_key]

            for date_str, values in time_series.items():
                date = datetime.strptime(date_str, "%Y-%m-%d")

                if start_date <= date <= end_date:
                    # Convert values to MetadataDict format
                    values_metadata: dict[str, MetadataValue] = {
                        f"raw_{k}": str(v) for k, v in values.items()
                    }
                    historical_data.append(
                        HistoricalData(
                            symbol=symbol,
                            timestamp=date,
                            open=Decimal(values["1. open"]),
                            high=Decimal(values["2. high"]),
                            low=Decimal(values["3. low"]),
                            close=Decimal(values["4. close"]),
                            volume=Decimal(values["5. volume"]),
                            feed_type=DataFeedType.ALPHA_VANTAGE,
                            frequency=frequency,
                            metadata=values_metadata,
                        )
                    )

            return sorted(historical_data, key=lambda x: x.timestamp)
        except (ConnectionError, TimeoutError, ClientError) as e:
            logger.error(
                f"Failed to get historical data for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return []

    async def subscribe_to_symbols(self, symbols: list[str]) -> bool:
        """Alpha Vantage doesn't support real-time subscriptions."""
        logger.warning(
            "Alpha Vantage doesn't support real-time subscriptions",
            extra={"symbols": symbols, "supported": False},
        )
        return False


class YahooFinanceFeed(DataFeedInterface):
    """Yahoo Finance market data feed implementation."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = ENDPOINTS.YAHOO_FINANCE_V8

    async def connect(self) -> bool:
        """Connect to Yahoo Finance API."""
        logger.debug("Connecting to Yahoo Finance API", extra={"base_url": self.base_url})
        try:
            self.session = aiohttp.ClientSession()
            logger.info(
                "Connected to Yahoo Finance API",
                extra={"base_url": self.base_url, "connected": True},
            )
            return True
        except (ConnectionError, TimeoutError, ClientError) as e:
            logger.error(
                f"Failed to connect to Yahoo Finance: {e}",
                extra={
                    "base_url": self.base_url,
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Yahoo Finance API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Yahoo Finance API", extra={"connected": False})
        return True

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote from Yahoo Finance."""
        logger.debug(
            "Getting quote from Yahoo Finance",
            extra={"symbol": symbol, "feed_type": "yahoo_finance"},
        )
        url = f"{self.base_url}/{symbol}"
        params = {"range": "1d", "interval": "1m", "includePrePost": "true"}

        try:
            data = await self._make_request(url, params)

            if "chart" not in data or not data["chart"]["result"]:
                logger.warning(f"No quote data for {symbol}", extra={"symbol": symbol})
                return None

            result = data["chart"]["result"][0]
            meta = result["meta"]
            quote = result["indicators"]["quote"][0]

            # Get latest data point
            timestamps = result["timestamp"]
            if not timestamps:
                logger.warning(f"No timestamp data for {symbol}", extra={"symbol": symbol})
                return None

            latest_idx = -1
            latest_close = quote["close"][latest_idx]

            if latest_close is None:
                logger.warning(f"No close price for {symbol}", extra={"symbol": symbol})
                return None

            # Convert result to MetadataDict format (flatten nested structures)
            yahoo_metadata: dict[str, MetadataValue] = {
                "symbol": str(meta.get("symbol", symbol)),
                "currency": str(meta.get("currency", "USD")),
                "exchangeName": str(meta.get("exchangeName", "")),
                "regularMarketTime": int(meta.get("regularMarketTime", 0)),
            }
            return Quote(
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
                metadata=yahoo_metadata,
            )
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(
                f"Failed to get quote for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> list[HistoricalData]:
        """Get historical data from Yahoo Finance."""
        logger.debug(
            "Getting historical data from Yahoo Finance",
            extra={
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "frequency": frequency.value,
            },
        )
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
                logger.warning(f"No historical data for {symbol}", extra={"symbol": symbol})
                return []

            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            historical_data = []

            for i, timestamp in enumerate(timestamps):
                date = datetime.fromtimestamp(timestamp)

                if start_date <= date <= end_date:
                    # Create minimal metadata for historical data
                    hist_metadata: dict[str, MetadataValue] = {
                        "data_index": i,
                        "timestamp_unix": int(timestamp),
                    }
                    historical_data.append(
                        HistoricalData(
                            symbol=symbol,
                            timestamp=date,
                            open=Decimal(str(quote["open"][i] or 0)),
                            high=Decimal(str(quote["high"][i] or 0)),
                            low=Decimal(str(quote["low"][i] or 0)),
                            close=Decimal(str(quote["close"][i] or 0)),
                            volume=Decimal(str(quote["volume"][i] or 0)),
                            feed_type=DataFeedType.YAHOO_FINANCE,
                            frequency=frequency,
                            metadata=hist_metadata,
                        )
                    )

            return historical_data
        except (ConnectionError, TimeoutError, ClientError) as e:
            logger.error(
                f"Failed to get historical data for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return []

    async def subscribe_to_symbols(self, symbols: list[str]) -> bool:
        """Yahoo Finance doesn't support real-time subscriptions."""
        logger.warning(
            "Yahoo Finance doesn't support real-time subscriptions",
            extra={"symbols": symbols, "supported": False},
        )
        return False


class PolygonFeed(DataFeedInterface):
    """Polygon.io (massive.com) market data feed implementation for real-time data."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self.base_url = ENDPOINTS.MASSIVE

    async def connect(self) -> bool:
        """Connect to Massive.com (Polygon.io) API."""
        logger.debug(
            "Connecting to Massive.com (Polygon.io) API", extra={"base_url": self.base_url}
        )
        try:
            self.session = aiohttp.ClientSession()
            logger.info(
                "Connected to Massive.com (Polygon.io) API",
                extra={"base_url": self.base_url, "connected": True},
            )
            return True
        except (ConnectionError, TimeoutError, ClientError) as e:
            logger.error(
                f"Failed to connect to Massive.com: {e}",
                extra={
                    "base_url": self.base_url,
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Massive.com API."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info(
                "Disconnected from Massive.com (Polygon.io) API", extra={"connected": False}
            )
        return True

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote from Massive.com (Polygon.io)."""
        logger.debug(
            "Getting quote from Massive.com (Polygon.io)",
            extra={"symbol": symbol, "feed_type": "polygon"},
        )
        if not self.config.api_key:
            logger.error("Massive.com API key not configured", extra={"symbol": symbol})
            return None

        # Massive.com snapshot endpoint
        url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        params = {"apiKey": self.config.api_key}

        try:
            data = await self._make_request(url, params)

            if data.get("status") != "OK" or not data.get("snapshot"):
                logger.warning(
                    f"No quote data for {symbol}",
                    extra={"symbol": symbol, "status": data.get("status")},
                )
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

            # Convert snapshot to MetadataDict format
            polygon_metadata: dict[str, MetadataValue] = {
                "ticker": str(snapshot.get("ticker", symbol)),
                "day_volume": float(day_data.get("v", 0)),
                "day_vwap": float(day_data.get("vw", 0)),
                "prev_close": float(prev_day.get("c", 0)) if prev_day else 0.0,
            }
            return Quote(
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
                metadata=polygon_metadata,
            )
        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(
                f"Failed to get quote for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return None

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> list[HistoricalData]:
        """Get historical data from Massive.com (Polygon.io)."""
        logger.debug(
            "Getting historical data from Massive.com (Polygon.io)",
            extra={
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "frequency": frequency.value,
            },
        )
        if not self.config.api_key:
            logger.error("Massive.com API key not configured", extra={"symbol": symbol})
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
                logger.warning(f"No historical data for {symbol}", extra={"symbol": symbol})
                return []

            historical_data = []

            for result in data["results"]:
                timestamp = datetime.fromtimestamp(result["t"] / 1000)

                if start_date <= timestamp <= end_date:
                    # Convert result dict to MetadataDict format (flatten nested values)
                    raw_metadata: dict[str, MetadataValue] = {
                        "ticker": str(symbol),
                        "open": float(result.get("o", 0)),
                        "high": float(result.get("h", 0)),
                        "low": float(result.get("l", 0)),
                        "close": float(result.get("c", 0)),
                        "volume": float(result.get("v", 0)),
                        "timestamp_unix": int(result.get("t", 0)),
                        "num_trades": int(result.get("n", 0)),
                        "vwap": float(result.get("vw", 0)),
                    }
                    historical_data.append(
                        HistoricalData(
                            symbol=symbol,
                            timestamp=timestamp,
                            open=Decimal(str(result.get("o", 0))),
                            high=Decimal(str(result.get("h", 0))),
                            low=Decimal(str(result.get("l", 0))),
                            close=Decimal(str(result.get("c", 0))),
                            volume=Decimal(str(result.get("v", 0))),
                            feed_type=DataFeedType.POLYGON,
                            frequency=frequency,
                            metadata=raw_metadata,
                        )
                    )

            return historical_data
        except (ConnectionError, TimeoutError, ClientError) as e:
            logger.error(
                f"Failed to get historical data for {symbol}: {e}",
                extra={
                    "symbol": symbol,
                    "error_type": type(e).__name__,
                },
            )
            return []

    async def subscribe_to_symbols(self, symbols: list[str]) -> bool:
        """Massive.com supports real-time subscriptions via WebSocket (not implemented here)."""
        logger.warning(
            "Massive.com WebSocket subscriptions not implemented in HTTP mode",
            extra={"symbols": symbols, "supported": False},
        )
        return False


def create_data_feed(config: DataFeedConfig) -> DataFeedInterface:
    """
    Factory function to create data feed instances.

    NOTE: Mock data has been removed - only real data sources are supported.
    For backtesting, use Yahoo Finance (free) or configure Polygon/AlphaVantage API keys.
    """
    logger.debug(
        "Creating data feed",
        extra={
            "feed_type": (
                config.feed_type.value
                if hasattr(config.feed_type, "value")
                else str(config.feed_type)
            )
        },
    )
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
