"""
Options Sources - Fuentes de datos de opciones.

Fuentes soportadas:
- Volatility surfaces (Polygon, IBKR, etc.)
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp

from app.shared.config.api_endpoints import APIEndpoints
from app.shared.config.timeout_config import get_timeouts

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)

# Get centralized timeouts
_TIMEOUTS = get_timeouts()


class OptionsVolatilitySource(BaseDataSource):
    """
    Fuente de datos de volatilidad de opciones.

    Proporciona:
    - Volatility surfaces (implied volatility por strike/expiry)
    - Greeks (delta, gamma, theta, vega)
    - Option chains

    Uses centralized endpoint configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente de volatilidad de opciones.

        Args:
            config: Configuración con:
                - provider: Proveedor (polygon, ibkr, etc.)
                - api_key: API key si es necesario
        """
        super().__init__(config)
        self.provider = config.get('provider', 'polygon')
        self.api_key = config.get('api_key')
        # Use centralized endpoint configuration
        self.base_url = self._get_base_url()
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_base_url(self) -> str:
        """Obtener base URL según provider using centralized configuration."""
        url_map = {'polygon': APIEndpoints.POLYGON, 'ibkr': None}  # Requiere conexión TWS
        return url_map.get(self.provider, APIEndpoints.POLYGON)

    async def connect(self) -> bool:
        """Conectar a fuente de opciones."""
        try:
            if self.provider == 'ibkr':
                # IBKR requiere conexión TWS (similar a IBKRSource)
                logger.warning("IBKR options source requiere conexión TWS (no implementado aún)")
                self.is_connected = False
                return False

            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info(f"Conectado a Options Volatility Source ({self.provider})")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Options Source: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de fuente de opciones."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de Options Source")
            return True
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error desconectando de Options Source: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        return True

    async def get_option_chain(
        self, symbol: str, expiry_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener cadena de opciones para un símbolo.

        Args:
            symbol: Símbolo del subyacente
            expiry_date: Fecha de expiración específica (opcional, retorna todas si None)

        Returns:
            Lista de opciones con strikes, IV, Greeks, etc.
        """
        if not self.is_connected or not self.session:
            logger.error("No conectado a Options Source")
            return []

        try:
            if self.provider == 'polygon':
                return await self._get_polygon_option_chain(symbol, expiry_date)
            else:
                logger.warning(f"Provider {self.provider} no implementado para option chains")
                return []

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error obteniendo option chain para {symbol}: {e}")
            return []

    async def _get_polygon_option_chain(
        self, symbol: str, expiry_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Obtener option chain de Polygon."""
        if not self.api_key:
            logger.warning("Polygon API key requerido para option chains")
            return []

        try:
            # Polygon option chains endpoint
            url = f"{self.base_url}/v3/snapshot/options/{symbol}"
            params = {'apiKey': self.api_key}

            if expiry_date:
                params['expiration_date'] = expiry_date.strftime('%Y-%m-%d')

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Polygon API error: {response.status}")
                    return []

                data = await response.json()

                if data.get('status') != 'OK' or 'results' not in data:
                    return []

                options = []
                for result in data['results']:
                    options.append(
                        {
                            'contract_type': result.get('contract_type'),  # call/put
                            'strike_price': Decimal(str(result.get('strike_price', 0))),
                            'expiry_date': datetime.fromisoformat(result.get('expiration_date')),
                            'implied_volatility': Decimal(str(result.get('implied_volatility', 0))),
                            'delta': Decimal(str(result.get('delta', 0))),
                            'gamma': Decimal(str(result.get('gamma', 0))),
                            'theta': Decimal(str(result.get('theta', 0))),
                            'vega': Decimal(str(result.get('vega', 0))),
                            'bid': Decimal(str(result.get('bid', 0))),
                            'ask': Decimal(str(result.get('ask', 0))),
                            'last_price': Decimal(str(result.get('last_quote', {}).get('last', 0))),
                            'volume': Decimal(str(result.get('day', {}).get('volume', 0))),
                        }
                    )

                return options

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo option chain de Polygon: {e}")
            return []

    async def get_volatility_surface(
        self, symbol: str, expiry_dates: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Obtener volatility surface (IV por strike/expiry).

        Args:
            symbol: Símbolo del subyacente
            expiry_dates: Lista de fechas de expiración (opcional)

        Returns:
            Dict con volatility surface:
                {
                    'expiry_dates': List[datetime],
                    'strikes': List[Decimal],
                    'implied_volatility': Dict[datetime, Dict[Decimal, float]],
                    'surface_data': List[Dict]
                }
        """
        if not self.is_connected:
            logger.error("No conectado a Options Source")
            return {'expiry_dates': [], 'strikes': [], 'implied_volatility': {}, 'surface_data': []}

        try:
            # Obtener option chains para múltiples expirations
            option_chains = await self.get_option_chain(symbol)

            if not option_chains:
                return {
                    'expiry_dates': [],
                    'strikes': [],
                    'implied_volatility': {},
                    'surface_data': [],
                }

            # Extraer strikes y expiries únicos
            strikes = sorted({opt['strike_price'] for opt in option_chains})
            expiry_dates = sorted({opt['expiry_date'] for opt in option_chains})

            # Filtrar por expiry_dates si se proporcionan
            if expiry_dates:
                option_chains = [opt for opt in option_chains if opt['expiry_date'] in expiry_dates]
                expiry_dates = [
                    ed for ed in expiry_dates if ed in [opt['expiry_date'] for opt in option_chains]
                ]

            # Construir surface
            iv_surface = {}
            surface_data = []

            for expiry in expiry_dates:
                iv_surface[expiry] = {}
                expiry_options = [opt for opt in option_chains if opt['expiry_date'] == expiry]

                for option in expiry_options:
                    strike = option['strike_price']
                    iv = float(option['implied_volatility'])
                    iv_surface[expiry][strike] = iv

                    surface_data.append(
                        {
                            'expiry_date': expiry,
                            'strike_price': strike,
                            'implied_volatility': iv,
                            'contract_type': option.get('contract_type'),
                            'delta': float(option.get('delta', 0)),
                            'gamma': float(option.get('gamma', 0)),
                            'theta': float(option.get('theta', 0)),
                            'vega': float(option.get('vega', 0)),
                        }
                    )

            return {
                'expiry_dates': expiry_dates,
                'strikes': strikes,
                'implied_volatility': iv_surface,
                'surface_data': surface_data,
            }

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error obteniendo volatility surface para {symbol}: {e}")
            return {'expiry_dates': [], 'strikes': [], 'implied_volatility': {}, 'surface_data': []}
