"""
OHLCV Sources - Implementaciones de fuentes de datos OHLCV.

Fuentes soportadas:
- IBKR (Interactive Brokers)
- Binance (Crypto)
- Alpaca
- Polygon
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp  # noqa: F401
from aiohttp import ClientError

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)


class IBKRSource(BaseDataSource):
    """
    Fuente de datos de Interactive Brokers TWS/IB Gateway.

    Requiere conexión a TWS o IB Gateway con API habilitada.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente IBKR.

        Args:
            config: Configuración con:
                - host: Host de TWS/IB Gateway (default: localhost)
                - port: Puerto (default: 7497 para paper, 7496 para live)
                - client_id: ID del cliente
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 7497)  # Paper trading default
        self.client_id = config.get('client_id', 1)
        self._ib_connection = None  # Se inicializará con ib_insync si está disponible

    async def connect(self) -> bool:
        """Conectar a IBKR TWS/IB Gateway."""
        try:
            # Intentar importar ib_insync
            if self._ib and self.is_connected:
                await self._ib.disconnect()
                self.is_connected = False
                logger.info("Desconectado de IBKR")
            return True
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Error desconectando de IBKR: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected:
            return False
        try:
            # Verificar que la conexión está activa
            return self._ib.isConnected() if hasattr(self, '_ib') else False
        except (asyncio.TimeoutError, ConnectionError, OSError):
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, bar_size: str = "1 day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de IBKR.

        Args:
            symbol: Símbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            bar_size: Tamaño de barra (1 sec, 5 secs, 1 min, 1 day, etc.)

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
            # Crear contrato
            contract = Stock(symbol, 'SMART', 'USD')

            # Obtener datos históricos
            bars = await self._ib.reqHistoricalData(
                contract,
                endDateTime=end_date,
                durationStr=f'{(end_date - start_date).days} D',
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
            )

            # Convertir a formato estándar
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
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de IBKR para {symbol}: {e}")
            return []


class BinanceSource(BaseDataSource):
    """
    Fuente de datos de Binance (crypto).

    Usa la API pública de Binance para datos históricos y en tiempo real.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Binance.

        Args:
            config: Configuración con:
                - api_key: API key (opcional, para endpoints privados)
                - api_secret: API secret (opcional)
                - testnet: Usar testnet (default: False)
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.testnet = config.get('testnet', False)
        self.base_url = (
            'https://testnet.binance.vision' if self.testnet else 'https://api.binance.com'
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Binance API."""
        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info(f"Conectado a Binance API (testnet={self.testnet})")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Binance: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de Binance."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de Binance")
            return True
        except (asyncio.TimeoutError, ClientError, OSError) as e:
            logger.error(f"Error desconectando de Binance: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Ping a la API
            async with self.session.get(f"{self.base_url}/api/v3/ping") as response:
                return response.status == 200
        except (asyncio.TimeoutError, ClientError, OSError):
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Binance.

        Args:
            symbol: Par de trading (ej: BTCUSDT)
            start_date: Fecha de inicio
            end_date: Fecha de fin
            interval: Intervalo (1m, 5m, 1h, 1d, etc.)

        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self.session:
            logger.error("No conectado a Binance")
            return []

        try:
            # Convertir fechas a timestamps
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)

            url = f"{self.base_url}/api/v3/klines"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 1000,  # Máximo por request
            }

            ohlcv_data = []

            # Binance limita a 1000 candles por request, necesitamos paginar
            while start_ms < end_ms:
                params['startTime'] = start_ms

                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Error en Binance API: {response.status}")
                        break

                    data = await response.json()

                    for candle in data:
                        ohlcv_data.append(
                            {
                                'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                                'open': Decimal(str(candle[1])),
                                'high': Decimal(str(candle[2])),
                                'low': Decimal(str(candle[3])),
                                'close': Decimal(str(candle[4])),
                                'volume': Decimal(str(candle[5])),
                            }
                        )

                    # Si tenemos menos de 1000, terminamos
                    if len(data) < 1000:
                        break

                    # Actualizar start_ms al último timestamp
                    start_ms = data[-1][0] + 1

            return ohlcv_data

        except (asyncio.TimeoutError, ClientError, OSError) as e:
            logger.error(f"Error obteniendo OHLCV de Binance para {symbol}: {e}")
            return []


class AlpacaSource(BaseDataSource):
    """
    Fuente de datos de Alpaca Markets.

    Soporta datos históricos y en tiempo real de acciones y crypto.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Alpaca.

        Args:
            config: Configuración con:
                - api_key: Alpaca API key
                - api_secret: Alpaca API secret
                - base_url: Base URL (default: paper trading)
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.base_url = config.get('base_url', 'https://paper-api.alpaca.markets')
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Alpaca API."""
        if not self.api_key or not self.api_secret:
            logger.error("Alpaca API key y secret requeridos")
            self.last_error = "API credentials missing"
            raise ValueError("Alpaca API key y secret requeridos")

        try:
            self.session = aiohttp.ClientSession(
                headers={'APCA-API-KEY-ID': self.api_key, 'APCA-API-SECRET-KEY': self.api_secret}
            )
            self.is_connected = True
            logger.info("Conectado a Alpaca API")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Alpaca: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de Alpaca."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de Alpaca")
            return True
        except (asyncio.TimeoutError, ClientError, OSError) as e:
            logger.error(f"Error desconectando de Alpaca: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Verificar cuenta
            async with self.session.get(f"{self.base_url}/v2/account") as response:
                return response.status == 200
        except (asyncio.TimeoutError, ClientError, OSError):
            return False

    async def get_ohlcv(
        self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1Day"
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Alpaca.

        Args:
            symbol: Símbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            timeframe: Timeframe (1Min, 5Min, 1Hour, 1Day, etc.)

        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self.session:
            logger.error("No conectado a Alpaca")
            return []

        try:
            url = f"{self.base_url}/v2/stocks/{symbol}/bars"
            params = {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'timeframe': timeframe,
                'limit': 10000,
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Error en Alpaca API: {response.status}")
                    return []

                data = await response.json()

                if 'bars' not in data:
                    return []

                ohlcv_data = []
                for bar in data['bars']:
                    ohlcv_data.append(
                        {
                            'timestamp': datetime.fromisoformat(bar['t'].replace('Z', '+00:00')),
                            'open': Decimal(str(bar['o'])),
                            'high': Decimal(str(bar['h'])),
                            'low': Decimal(str(bar['l'])),
                            'close': Decimal(str(bar['c'])),
                            'volume': Decimal(str(bar['v'])),
                        }
                    )

                return ohlcv_data

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Alpaca para {symbol}: {e}")
            return []


class PolygonSource(BaseDataSource):
    """
    Fuente de datos de Polygon.io.

    Soporta datos históricos y en tiempo real de acciones, forex, crypto.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Polygon.

        Args:
            config: Configuración con:
                - api_key: Polygon API key
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        if not self.api_key:
            logger.warning("Polygon API key no configurado")
        self.base_url = 'https://api.polygon.io'
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Polygon API."""
        if not self.api_key:
            logger.warning("Polygon API key no configurado")

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info("Conectado a Polygon API")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Polygon: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de Polygon."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de Polygon")
            return True
        except (asyncio.TimeoutError, ClientError, OSError) as e:
            logger.error(f"Error desconectando de Polygon: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Verificar con endpoint de status
            async with self.session.get(
                f"{self.base_url}/v2/reference/status", params={'apiKey': self.api_key}
            ) as response:
                return response.status == 200
        except (asyncio.TimeoutError, ClientError, OSError):
            return False

    async def get_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timespan: str = "day",
        multiplier: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV de Polygon.

        Args:
            symbol: Símbolo del instrumento (con prefijo T: para trades, Q: para quotes)
            start_date: Fecha de inicio
            end_date: Fecha de fin
            timespan: Timespan (minute, hour, day, week, month, quarter, year)
            multiplier: Multiplicador del timespan

        Returns:
            Lista de diccionarios con datos OHLCV
        """
        if not self.is_connected or not self.session:
            logger.error("No conectado a Polygon")
            return []

        try:
            # Formatear fechas
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')

            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
            params = {'apiKey': self.api_key}

            ohlcv_data = []

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Error en Polygon API: {response.status}")
                    return []

                data = await response.json()

                if data.get('status') != 'OK' or 'results' not in data:
                    logger.warning(
                        f"Polygon API retornó: {data.get('statusMessage', 'Unknown error')}"
                    )
                    return []

                for result in data['results']:
                    # Convertir timestamp de ms a datetime
                    timestamp = datetime.fromtimestamp(result['t'] / 1000)

                    ohlcv_data.append(
                        {
                            'timestamp': timestamp,
                            'open': Decimal(str(result['o'])),
                            'high': Decimal(str(result['h'])),
                            'low': Decimal(str(result['l'])),
                            'close': Decimal(str(result['c'])),
                            'volume': Decimal(str(result['v'])),
                        }
                    )

                return sorted(ohlcv_data, key=lambda x: x['timestamp'])

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo OHLCV de Polygon para {symbol}: {e}")
            return []
