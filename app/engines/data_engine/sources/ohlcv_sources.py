"""
OHLCV Sources - Data source implementations with configurable timeouts.

Fuentes soportadas:
- IBKR (Interactive Brokers)
- Binance (Crypto)
- Alpaca
- Polygon
- Yahoo Finance

"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError

from app.shared.config.timeout_config import get_timeouts

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when a data source operation times out."""


class IBKRSource(BaseDataSource):
    """
    Fuente de datos de Interactive Brokers TWS/IB Gateway.

    Requiere conexion a TWS o IB Gateway con API habilitada.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 7497)
        self.client_id = config.get('client_id', 1)
        self._ib_connection = None
        self._timeouts = get_timeouts()

    async def connect(self) -> bool:
        """Conectar a IBKR TWS/IB Gateway."""
        try:
            from ib_insync import IB
        except ImportError:
            logger.error("ib_insync no disponible")
            return False
        try:
            self._ib = IB()
            await asyncio.wait_for(
                self._ib.connect(self.host, self.port, clientId=self.client_id),
                timeout=self._timeouts.ib_connect,
            )
            self.is_connected = True
            logger.info(f"Conectado a IBKR ({self.host}:{self.port})")
            return True
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout conectando a IBKR: {e}")
            return False
        except OSError as e:
            logger.error(f"Error conectando a IBKR: {e}")
            return False

    async def disconnect(self) -> bool:
        """Desconectar de IBKR."""
        if not self.is_connected or not self._ib:
            return True
        try:
            await asyncio.wait_for(self._ib.disconnect(), timeout=self._timeouts.ib_connect)
            self.is_connected = False
            logger.info("Desconectado de IBKR")
            return True
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout desconectando de IBKR: {e}")
            return False
        except OSError as e:
            logger.error(f"Error desconectando de IBKR: {e}")
            return False

    async def health_check(self) -> bool:
        """verificar salud de la conexion."""
        if not self.is_connected or not self._ib:
            return False
        try:
            connected = await asyncio.wait_for(
                self._ib.isConnected(), timeout=self._timeouts.ib_read
            )
            return connected
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"IBKR health check failed: {e}")
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de IBKR.
        Args:
            symbol: Simbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamano de barra (1 sec, 5 secs, 1 min, 1 day, etc.)
        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected:
            logger.error("No conectado a IBKR")
            return []
        try:
            from ib_insync import Stock
        except ImportError:
            logger.error("ib_insync no disponible")
            return []
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            bars = await asyncio.wait_for(
                self._ib.reqHistoricalData(
                    contract,
                    endDateTime=end_date,
                    durationStr=f'{(end_date - start_date).days} D',
                    barSizeSetting=bar_size,
                    whatToShow='TRADES',
                    useRTH=True,
                ),
                timeout=self._timeouts.ib_read,
            )
            ohlcv_data = []
            for bar in bars:
                ohlcv_data.append(
                    {
                        'timestamp': bar.date,
                        'open': Decimal(str(bar.open)),
                        'high': Decimal(str(bar.high)),
                        'low': Decimal(str(bar.low)),
                        'close': Decimal(str(bar.close)),
                        'volume': Decimal(str(bar.volume)),
                    }
                )
            return ohlcv_data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout obteniendo OHLCV de IBKR para {symbol}: {e}")
            return []
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de IBKR para {symbol}: {e}")
            return []


class BinanceSource(BaseDataSource):
    """
    Fuente de datos de Binance (crypto).
    Usa la API publica de Binance para datos historicos y en tiempo real.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.binance.com')
        self._timeouts = get_timeouts()
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Binance API."""
        timeout = aiohttp.ClientTimeout(
            total=self._timeouts.binance_connect + self._timeouts.binance_read
        )
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.is_connected = True
        logger.info(f"Conectado a Binance ({self.base_url})")
        return True

    async def disconnect(self) -> bool:
        """desconectar de Binance."""
        if self._session:
            await asyncio.wait_for(self._session.close(), timeout=self._timeouts.binance_connect)
            self._session = None
        self.is_connected = False
        logger.info("Desconectado de Binance")
        return True

    async def health_check(self) -> bool:
        """verificar salud de la conexion."""
        if not self.is_connected or not self._session:
            return False
        try:
            async with self._session.get(
                f"{self.base_url}/api/v3/ping", timeout=self._timeouts.binance_read
            ) as response:
                return response.status == 200
            return False
        except (asyncio.TimeoutError, ClientError) as e:
            logger.warning(f"Binance health check failed: {e}")
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Binance.
        Args:
            symbol: Simbolo del instrumento (ej: BTCUSDT, ETHUSDT)
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamano de barra (1m, 5m, 15m, 1h, 1d, 1w, 1M)
        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self._session:
            logger.error("No conectado a Binance")
            return []
        # Map bar size to Binance format
        binance_interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "1d": "1d",
            "1w": "1w",
            "1M": "1M",
        }
        interval = binance_interval_map.get(bar_size, "1d")
        # Convert dates to timestamps
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": 1000,
        }
        try:
            async with self._session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Binance API error: {response.status}")
                    return []
                data = await response.json()
                ohlcv_data = []
                for kline in data:
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromtimestamp(kline[0] / 1000),
                            "open": Decimal(str(kline[1])),
                            "high": Decimal(str(kline[2])),
                            "low": Decimal(str(kline[3])),
                            "close": Decimal(str(kline[4])),
                            "volume": Decimal(str(kline[5])),
                        }
                    )
                return ohlcv_data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout obteniendo OHLCV de Binance para {symbol}: {e}")
            return []
        except (ClientError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Binance para {symbol}: {e}")
            return []


class AlpacaSource(BaseDataSource):
    """
    Fuente de datos de Alpaca.
    Requiere autenticacion con API keys.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.base_url = config.get('base_url', 'https://paper-api.alpaca.markets')
        self._timeouts = get_timeouts()
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Alpaca API."""
        timeout = aiohttp.ClientTimeout(
            total=self._timeouts.alpaca_connect + self._timeouts.alpaca_read
        )
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.is_connected = True
        logger.info(f"Conectado a Alpaca ({self.base_url})")
        return True

    async def disconnect(self) -> bool:
        """desconectar de Alpaca."""
        if self._session:
            await asyncio.wait_for(self._session.close(), timeout=self._timeouts.alpaca_connect)
            self._session = None
        self.is_connected = False
        logger.info("Desconectado de Alpaca")
        return True

    async def health_check(self) -> bool:
        """verificar salud de la conexion."""
        if not self.is_connected or not self._session:
            return False
        try:
            async with self._session.get(
                f"{self.base_url}/v2/account",
                headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret},
                timeout=self._timeouts.alpaca_read,
            ) as response:
                return response.status == 200
            return False
        except (asyncio.TimeoutError, ClientError) as e:
            logger.warning(f"Alpaca health check failed: {e}")
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Alpaca.
        Args:
            symbol: Simbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamano de barra
        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self._session:
            logger.error("No conectado a Alpaca")
            return []
        # Alpaca bar size format
        alpaca_timeframe_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1h": "1Hour",
            "1d": "1Day",
        }
        timeframe = alpaca_timeframe_map.get(bar_size, "1Day")
        # Convert dates to ISO format
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        url = f"{self.base_url}/v2/stocks/{symbol}/bars"
        params = {
            "start": start_str,
            "end": end_str,
            "timeframe": timeframe,
            "limit": 10000,
        }
        try:
            async with self._session.get(
                url,
                params=params,
                headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret},
                timeout=self._timeouts.alpaca_read,
            ) as response:
                if response.status != 200:
                    logger.error(f"Alpaca API error: {response.status}")
                    return []
                data = await response.json()
                bars = data.get("bars", [])
                ohlcv_data = []
                for bar in bars:
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromisoformat(bar["t"]),
                            "open": Decimal(str(bar["o"])),
                            "high": Decimal(str(bar["h"])),
                            "low": Decimal(str(bar["l"])),
                            "close": Decimal(str(bar["c"])),
                            "volume": Decimal(str(bar["v"])),
                        }
                    )
                return ohlcv_data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout obteniendo OHLCV de Alpaca para {symbol}: {e}")
            return []
        except (ClientError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Alpaca para {symbol}: {e}")
            return []


class PolygonSource(BaseDataSource):
    """
    Fuente de datos de Polygon.io.
    Requiere API key.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.polygon.io')
        self._timeouts = get_timeouts()
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Polygon API."""
        timeout = aiohttp.ClientTimeout(
            total=self._timeouts.polygon_connect + self._timeouts.polygon_read
        )
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.is_connected = True
        logger.info(f"Conectado a Polygon ({self.base_url})")
        return True

    async def disconnect(self) -> bool:
        """desconectar de Polygon."""
        if self._session:
            await asyncio.wait_for(self._session.close(), timeout=self._timeouts.polygon_connect)
            self._session = None
        self.is_connected = False
        logger.info("Desconectado de Polygon")
        return True

    async def health_check(self) -> bool:
        """verificar salud de la conexion."""
        if not self.is_connected or not self._session:
            return False
        try:
            async with self._session.get(
                f"{self.base_url}/v2/aggs/ticker",
                params={"apiKey": self.api_key},
                timeout=self._timeouts.polygon_read,
            ) as response:
                return response.status == 200
        except (asyncio.TimeoutError, ClientError) as e:
            logger.warning(f"Polygon health check failed: {e}")
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Polygon.
        Args:
            symbol: Simbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamano de barra
        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self._session:
            logger.error("No conectado a Polygon")
            return []
        # Polygon timespan format
        timespan_map = {
            "1m": "minute",
            "5m": "minute",
            "15m": "minute",
            "1h": "hour",
            "1d": "day",
        }
        timespan = timespan_map.get(bar_size, "day")
        # Convert dates to timestamps
        int(start_date.timestamp() * 1000)
        int(end_date.timestamp() * 1000)
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{timespan}"
        params = {
            "apiKey": self.api_key,
            "sort": "asc",
            "limit": 50000,
        }
        try:
            async with self._session.get(
                url, params=params, timeout=self._timeouts.polygon_read
            ) as response:
                if response.status != 200:
                    logger.error(f"Polygon API error: {response.status}")
                    return []
                data = await response.json()
                results = data.get("results", [])
                ohlcv_data = []
                for result in results:
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromtimestamp(result["t"] / 1000),
                            "open": Decimal(str(result["o"])),
                            "high": Decimal(str(result["h"])),
                            "low": Decimal(str(result["l"])),
                            "close": Decimal(str(result["c"])),
                            "volume": Decimal(str(result["v"])),
                        }
                    )
                return ohlcv_data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout obteniendo OHLCV de Polygon para {symbol}: {e}")
            return []
        except (ClientError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Polygon para {symbol}: {e}")
            return []


class YahooFinanceSource(BaseDataSource):
    """
    Fuente de datos de Yahoo Finance.
    Usa la API gratuita de Yahoo Finance para datos historicos.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://query1.finance.yahoo.com/v8/finance/chart')
        self._timeouts = get_timeouts()
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Yahoo Finance API."""
        timeout = aiohttp.ClientTimeout(
            total=self._timeouts.yahoo_finance_connect + self._timeouts.yahoo_finance_read
        )
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.is_connected = True
        logger.info(f"Conectado a Yahoo Finance ({self.base_url})")
        return True

    async def disconnect(self) -> bool:
        """desconectar de Yahoo Finance."""
        if self._session:
            await asyncio.wait_for(
                self._session.close(), timeout=self._timeouts.yahoo_finance_connect
            )
            self._session = None
        self.is_connected = False
        logger.info("Desconectado de Yahoo Finance")
        return True

    async def health_check(self) -> bool:
        """verificar salud de la conexion."""
        if not self.is_connected or not self._session:
            return False
        try:
            # Simple ping to check connectivity
            async with self._session.get(
                f"{self.base_url}/AAPL", timeout=self._timeouts.yahoo_finance_read
            ) as response:
                return response.status == 200 or response.status == 429
            return False
        except (asyncio.TimeoutError, ClientError) as e:
            logger.warning(f"Yahoo Finance health check failed: {e}")
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Yahoo Finance.
        Args:
            symbol: Simbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamano de barra
        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self._session:
            logger.error("No conectado a Yahoo Finance")
            return []
        # Convert dates to Unix timestamps
        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())
        url = f"{self.base_url}/{symbol}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
        }
        try:
            async with self._session.get(
                url, params=params, timeout=self._timeouts.yahoo_finance_read
            ) as response:
                if response.status != 200:
                    logger.error(f"Yahoo Finance API error: {response.status}")
                    return []
                data = await response.json()
                # Parse Yahoo Finance response
                result_data = data.get("chart", {}).get("result", [])
                if not result_data:
                    logger.error("No data returned from Yahoo Finance")
                    return []
                quote = result_data[0]
                ohlcv_data = []
                for item in quote.get("indicators", {}).get("quote", []):
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromtimestamp(item.get("timestamp", 0)),
                            "open": Decimal(str(item.get("open", 0))),
                            "high": Decimal(str(item.get("high", 0))),
                            "low": Decimal(str(item.get("low", 0))),
                            "close": Decimal(str(item.get("close", 0))),
                            "volume": Decimal(str(item.get("volume", 0))),
                        }
                    )
                return ohlcv_data
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout obteniendo OHLCV de Yahoo Finance para {symbol}: {e}")
            return []
        except (ClientError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Yahoo Finance para {symbol}: {e}")
            return []
