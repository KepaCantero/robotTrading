"""
Fundamental Sources - Fuentes de datos fundamentales.

Fuentes soportadas:
- Financial Modeling Prep
- Alpha Vantage
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp  # noqa: F401

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)


class FinancialModelingPrepSource(BaseDataSource):
    """
    Fuente de datos fundamentales de Financial Modeling Prep.

    Proporciona:
    - Financial statements (income, balance sheet, cash flow)
    - Key metrics (P/E, P/B, etc.)
    - Company profiles
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente FMP.

        Args:
            config: Configuración con:
                - api_key: FMP API key
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        if not self.api_key:
            logger.warning("FMP API key no configurado")
        self.base_url = 'https://financialmodelingprep.com/api/v3'
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a FMP API."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp no disponible. FMPSource no puede conectarse.")
            self.last_error = "aiohttp no disponible"
            return False

        if not self.api_key:
            logger.error("FMP API key requerido")
            self.last_error = "API key missing"
            raise ValueError("FMP API key requerido")

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info("Conectado a Financial Modeling Prep API")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a FMP: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de FMP."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de FMP")
            return True
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Error desconectando de FMP: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Test con endpoint simple
            url = f"{self.base_url}/profile/AAPL"
            async with self.session.get(url, params={'apikey': self.api_key}) as response:
                return response.status == 200
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError):
            return False

    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtener perfil de la compañía.

        Args:
            symbol: Símbolo del ticker

        Returns:
            Dict con información del perfil
        """
        if not self.is_connected or not self.session:
            return None

        try:
            url = f"{self.base_url}/profile/{symbol}"
            async with self.session.get(url, params={'apikey': self.api_key}) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Error obteniendo perfil de {symbol}: {e}")
            return None

    async def get_key_metrics(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Obtener métricas clave (P/E, P/B, etc.).

        Args:
            symbol: Símbolo del ticker

        Returns:
            Lista de métricas por período
        """
        if not self.is_connected or not self.session:
            return []

        try:
            url = f"{self.base_url}/key-metrics/{symbol}"
            async with self.session.get(
                url, params={'apikey': self.api_key, 'limit': 5}
            ) as response:
                if response.status != 200:
                    return []

                return await response.json()

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Error obteniendo métricas de {symbol}: {e}")
            return []

    async def get_financial_statements(
        self, symbol: str, statement_type: str = "income-statement"
    ) -> List[Dict[str, Any]]:
        """
        Obtener estados financieros.

        Args:
            symbol: Símbolo del ticker
            statement_type: Tipo (income-statement, balance-sheet-statement, cash-flow-statement)

        Returns:
            Lista de estados financieros por período
        """
        if not self.is_connected or not self.session:
            return []

        try:
            url = f"{self.base_url}/{statement_type}/{symbol}"
            async with self.session.get(
                url, params={'apikey': self.api_key, 'limit': 5}
            ) as response:
                if response.status != 200:
                    return []

                return await response.json()

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Error obteniendo estados financieros de {symbol}: {e}")
            return []


class AlphaVantageFundamentalSource(BaseDataSource):
    """
    Fuente de datos fundamentales de Alpha Vantage.

    Proporciona datos fundamentales complementarios.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Alpha Vantage Fundamentales.

        Args:
            config: Configuración con:
                - api_key: Alpha Vantage API key
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        if not self.api_key:
            logger.warning("Alpha Vantage API key no configurado")
        self.base_url = 'https://www.alphavantage.co/query'
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Conectar a Alpha Vantage API."""
        if not self.api_key:
            logger.error("Alpha Vantage API key requerido")
            self.last_error = "API key missing"
            raise ValueError("Alpha Vantage API key requerido")

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info("Conectado a Alpha Vantage Fundamental API")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Alpha Vantage: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de Alpha Vantage."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de Alpha Vantage")
            return True
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"Error desconectando de Alpha Vantage: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Test con endpoint simple
            params = {'function': 'OVERVIEW', 'symbol': 'AAPL', 'apikey': self.api_key}
            async with self.session.get(self.base_url, params=params) as response:
                return response.status == 200
        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            return False

    async def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtener overview de la compañía.

        Args:
            symbol: Símbolo del ticker

        Returns:
            Dict con overview
        """
        if not self.is_connected or not self.session:
            return None

        try:
            params = {'function': 'OVERVIEW', 'symbol': symbol, 'apikey': self.api_key}

            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                # Alpha Vantage retorna error como dict con "Error Message" o "Note"
                if 'Error Message' in data or 'Note' in data:
                    logger.warning(
                        f"Alpha Vantage error para {symbol}: {data.get('Error Message', data.get('Note'))}"
                    )
                    return None

                return data

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error obteniendo overview de {symbol}: {e}")
            return None

    async def get_earnings(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtener earnings de la compañía.

        Args:
            symbol: Símbolo del ticker

        Returns:
            Dict con earnings
        """
        if not self.is_connected or not self.session:
            return None

        try:
            params = {'function': 'EARNINGS', 'symbol': symbol, 'apikey': self.api_key}

            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if 'Error Message' in data or 'Note' in data:
                    logger.warning(
                        f"Alpha Vantage error para {symbol}: {data.get('Error Message', data.get('Note'))}"
                    )
                    return None

                return data

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error obteniendo earnings de {symbol}: {e}")
            return None
