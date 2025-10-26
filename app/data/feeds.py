"""
Market Data Feed Interfaces

This module defines abstract interfaces and concrete implementations for
market data feeds from various providers.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from app.models.market_data import (
    DataFeedConfig,
    DataFeedType,
    DataFrequency,
    HistoricalData,
    MarketDataStatus,
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
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the data feed."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol."""
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get historical data for a symbol."""
        pass

    @abstractmethod
    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to real-time updates for symbols."""
        pass

    async def _make_request(
        self, url: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
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
            except Exception as e:
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
        except Exception as e:
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
                change_percent=Decimal(
                    quote_data.get("10. change percent", "0").replace("%", "")
                ),
                feed_type=DataFeedType.ALPHA_VANTAGE,
                metadata={"raw_data": quote_data},
            )
        except Exception as e:
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
            params["interval"] = (
                "5min" if frequency == DataFrequency.FIVE_MINUTES else "60min"
            )

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
                            metadata={"raw_data": values},
                        )
                    )

            return sorted(historical_data, key=lambda x: x.timestamp)
        except Exception as e:
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
        except Exception as e:
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
                metadata={"raw_data": result},
            )
        except Exception as e:
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
                            metadata={"raw_data": result},
                        )
                    )

            return historical_data
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return []

    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Yahoo Finance doesn't support real-time subscriptions."""
        logger.warning("Yahoo Finance doesn't support real-time subscriptions")
        return False


class MockDataFeed(DataFeedInterface):
    """Mock data feed for testing and development."""

    def __init__(self, config: DataFeedConfig):
        super().__init__(config)
        self._mock_data = self._generate_mock_data()

    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock market data."""
        return {
            "AAPL": {
                "quote": {
                    "bid": Decimal("150.00"),
                    "ask": Decimal("150.01"),
                    "last": Decimal("150.00"),
                    "open": Decimal("149.50"),
                    "high": Decimal("150.50"),
                    "low": Decimal("149.00"),
                    "close": Decimal("150.00"),
                    "volume": Decimal("1000000"),
                    "change": Decimal("0.50"),
                    "change_percent": Decimal("0.33"),
                },
                "historical": [],
            },
            "MSFT": {
                "quote": {
                    "bid": Decimal("300.00"),
                    "ask": Decimal("300.01"),
                    "last": Decimal("300.00"),
                    "open": Decimal("299.50"),
                    "high": Decimal("300.50"),
                    "low": Decimal("299.00"),
                    "close": Decimal("300.00"),
                    "volume": Decimal("800000"),
                    "change": Decimal("0.50"),
                    "change_percent": Decimal("0.17"),
                },
                "historical": [],
            },
            "CUSTOM": {
                "quote": {
                    "bid": Decimal("100.00"),
                    "ask": Decimal("100.01"),
                    "last": Decimal("100.00"),
                    "open": Decimal("99.50"),
                    "high": Decimal("100.50"),
                    "low": Decimal("99.00"),
                    "close": Decimal("100.00"),
                    "volume": Decimal("500000"),
                    "change": Decimal("0.50"),
                    "change_percent": Decimal("0.50"),
                },
                "historical": [],
            },
        }

    async def connect(self) -> bool:
        """Mock connection."""
        logger.info("Connected to Mock Data Feed")
        return True

    async def disconnect(self) -> bool:
        """Mock disconnection."""
        logger.info("Disconnected from Mock Data Feed")
        return True

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get mock quote."""
        if symbol not in self._mock_data:
            logger.warning(f"No mock data for {symbol}")
            return None

        quote_data = self._mock_data[symbol]["quote"]

        return Quote(
            symbol=symbol,
            bid=quote_data["bid"],
            ask=quote_data["ask"],
            last=quote_data["last"],
            open=quote_data["open"],
            high=quote_data["high"],
            low=quote_data["low"],
            close=quote_data["close"],
            volume=quote_data["volume"],
            spread=quote_data["ask"] - quote_data["bid"],
            change=quote_data["change"],
            change_percent=quote_data["change_percent"],
            feed_type=DataFeedType.MOCK,
            metadata={"mock": True},
        )

    async def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: DataFrequency = DataFrequency.DAILY,
    ) -> List[HistoricalData]:
        """Get mock historical data."""
        if symbol not in self._mock_data:
            logger.warning(f"No mock data for {symbol}")
            return []

        # Generate mock historical data
        historical_data = []
        current_date = start_date
        base_price = Decimal("150.00")

        while current_date <= end_date:
            # Generate realistic price movement
            price_change = Decimal(
                str(0.01 * (hash(str(current_date)) % 20 - 10))
            )  # ±10%
            price = base_price * (Decimal("1") + price_change)

            historical_data.append(
                HistoricalData(
                    symbol=symbol,
                    timestamp=current_date,
                    open=price,
                    high=price * Decimal("1.02"),
                    low=price * Decimal("0.98"),
                    close=price,
                    volume=Decimal("1000000"),
                    feed_type=DataFeedType.MOCK,
                    frequency=frequency,
                    metadata={"mock": True},
                )
            )

            current_date += timedelta(days=1)

        return historical_data

    async def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """Mock subscription."""
        logger.info(f"Mock subscribed to symbols: {symbols}")
        return True


def create_data_feed(config: DataFeedConfig) -> DataFeedInterface:
    """Factory function to create data feed instances."""
    if config.feed_type == DataFeedType.ALPHA_VANTAGE:
        return AlphaVantageFeed(config)
    elif config.feed_type == DataFeedType.YAHOO_FINANCE:
        return YahooFinanceFeed(config)
    elif config.feed_type == DataFeedType.MOCK:
        return MockDataFeed(config)
    else:
        raise ValueError(f"Unsupported feed type: {config.feed_type}")
