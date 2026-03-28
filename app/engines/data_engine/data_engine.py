"""
DataEngine - Engine principal unificado de gestión de datos.

Proporciona API unificada para:
- OHLCV de múltiples fuentes
- Datos fundamentales
- Sentimiento
- Opciones
- Normalización automática
- Limpieza de datos
- Versionado
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from .cache.distributed_cache import DistributedCache
from .config_loader import DataEngineConfigLoader
from .normalizers.unified_normalizer import UnifiedNormalizer
from .sources.base_source import BaseDataSource
from .sources.fundamental_sources import AlphaVantageFundamentalSource, FinancialModelingPrepSource
from .sources.ohlcv_sources import AlpacaSource, BinanceSource, IBKRSource, PolygonSource
from .sources.options_sources import OptionsVolatilitySource
from .sources.sentiment_sources import (
    NewsSentimentSource,
    RedditSentimentSource,
    TwitterSentimentSource,
)
from .streaming.websocket_streaming import WebSocketStreamingManager
from .validators.data_cleaning_pipeline import DataCleaningPipeline
from .versioning.data_lineage import DataLineageTracker
from .versioning.schema_versioner import SchemaVersioner
from .versioning.version_manager import DataVersionManager

logger = logging.getLogger(__name__)


class DataEngine:
    """
    Engine principal de gestión de datos.

    Coordina todas las fuentes, normalizadores, validadores y versionado.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar Data Engine.

        Args:
            config: Configuración completa del engine (opcional, usa YAML por defecto)
        """
        config = config or {}
        self.config = config

        # Cargar configuración desde YAML
        self.config_loader = DataEngineConfigLoader(
            config.get('config_path', 'config/data_engine.yaml')
        )

        # Obtener configuración de entorno si está disponible
        import os

        env_redis_url = os.getenv('REDIS_URL') or os.getenv('DATA_ENGINE_CACHE_REDIS_URL')
        env_postgres_url = os.getenv('DATABASE_URL') or os.getenv('DATA_ENGINE_CACHE_POSTGRES_URL')

        # Inicializar componentes
        self.sources: Dict[str, BaseDataSource] = {}
        self.normalizer = UnifiedNormalizer(self.config_loader.get_normalization_config())
        self.cleaning_pipeline = DataCleaningPipeline(self.config_loader.get_cleaning_config())

        versioning_config = self.config_loader.get_versioning_config()
        self.schema_versioner = SchemaVersioner(
            {'schema_version': versioning_config.get('schema_version', '1.0.0')}
        )
        self.lineage_tracker = DataLineageTracker(
            {'enabled': versioning_config.get('data_lineage_enabled', True)}
        )
        self.version_manager = DataVersionManager(
            {'enabled': versioning_config.get('enabled', True)}
        )

        # Cache distribuido (Redis + PostgreSQL con fallback a memoria)
        cache_config = self.config_loader.get_cache_config(env_redis_url, env_postgres_url)
        # Merge con config externo si existe
        if 'cache_config' in config:
            cache_config.update(config['cache_config'])
        self.cache = DistributedCache(cache_config)

        # Streaming manager (WebSocket)
        streaming_config = self.config_loader.get_streaming_config()
        # Merge con config externo si existe
        if 'streaming_config' in config:
            streaming_config.update(config['streaming_config'])
        self.streaming_manager = WebSocketStreamingManager(streaming_config)
        self.streaming_enabled = streaming_config.get('enabled', False)

        # Inicializar fuentes configuradas
        sources_config = config.get('sources', {})
        self._initialize_sources(sources_config)

    def _initialize_sources(self, sources_config: Dict[str, Any]) -> None:
        """Inicializar fuentes de datos configuradas."""
        # Fuentes OHLCV
        ohlcv_sources = sources_config.get('ohlcv', {})

        if 'ibkr' in ohlcv_sources:
            self.sources['ibkr'] = IBKRSource(ohlcv_sources['ibkr'])

        if 'binance' in ohlcv_sources:
            self.sources['binance'] = BinanceSource(ohlcv_sources['binance'])

        if 'alpaca' in ohlcv_sources:
            self.sources['alpaca'] = AlpacaSource(ohlcv_sources['alpaca'])

        if 'polygon' in ohlcv_sources:
            self.sources['polygon'] = PolygonSource(ohlcv_sources['polygon'])

        # Fuentes fundamentales
        fundamental_sources = sources_config.get('fundamental', {})

        if 'fmp' in fundamental_sources:
            self.sources['fmp'] = FinancialModelingPrepSource(fundamental_sources['fmp'])

        if 'alpha_vantage_fundamental' in fundamental_sources:
            self.sources['alpha_vantage_fundamental'] = AlphaVantageFundamentalSource(
                fundamental_sources['alpha_vantage_fundamental']
            )

        # Fuentes de sentimiento
        sentiment_sources = sources_config.get('sentiment', {})

        if 'twitter' in sentiment_sources:
            self.sources['twitter'] = TwitterSentimentSource(sentiment_sources['twitter'])

        if 'reddit' in sentiment_sources:
            self.sources['reddit'] = RedditSentimentSource(sentiment_sources['reddit'])

        if 'news' in sentiment_sources:
            self.sources['news'] = NewsSentimentSource(sentiment_sources['news'])

        # Fuentes de opciones
        options_sources = sources_config.get('options', {})

        if 'volatility' in options_sources:
            self.sources['options_volatility'] = OptionsVolatilitySource(
                options_sources['volatility']
            )

        logger.info(f"DataEngine inicializado con {len(self.sources)} fuentes")

    async def connect_all(self) -> Dict[str, bool]:
        """
        Conectar a todas las fuentes configuradas.

        Returns:
            Dict con estado de conexión por fuente
        """
        connection_status = {}

        for source_name, source in self.sources.items():
            try:
                connected = await source.connect()
                connection_status[source_name] = connected
                if connected:
                    logger.info(f"Conectado a {source_name}")
                else:
                    logger.warning(f"No se pudo conectar a {source_name}")
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error conectando a {source_name}: {e}")
                connection_status[source_name] = False

        return connection_status

    async def disconnect_all(self) -> None:
        """Desconectar de todas las fuentes."""
        for source_name, source in self.sources.items():
            try:
                await source.disconnect()
                logger.info(f"Desconectado de {source_name}")
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error desconectando de {source_name}: {e}")

    async def get_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        source: Optional[str] = None,
        frequency: str = '1d',
        normalize: bool = True,
        clean: bool = True,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Obtener datos OHLCV.

        Args:
            symbol: Símbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            source: Fuente específica (opcional, usa la primera disponible si None)
            frequency: Frecuencia (1d, 1h, 5m, etc.)
            normalize: Aplicar normalización
            clean: Aplicar limpieza
            use_cache: Usar cache si está disponible

        Returns:
            Lista de datos OHLCV
        """
        # Verificar cache
        if use_cache:
            cache_key = self.cache._make_key(
                'ohlcv',
                symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                frequency=frequency,
                source=source,
            )
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                logger.debug(f"Datos OHLCV obtenidos del cache para {symbol}")
                return cached_data

        # Determinar fuente
        ohlcv_source = None
        if source:
            ohlcv_source = self.sources.get(source)
        else:
            # Buscar primera fuente OHLCV disponible
            for name in ['polygon', 'alpaca', 'binance', 'ibkr']:
                if name in self.sources:
                    ohlcv_source = self.sources[name]
                    break

        if not ohlcv_source:
            logger.error("No hay fuente OHLCV disponible")
            return []

        # Verificar conexión
        if not ohlcv_source.is_connected:
            await ohlcv_source.connect()

        # Obtener datos
        try:
            if hasattr(ohlcv_source, 'get_ohlcv'):
                raw_data = await ohlcv_source.get_ohlcv(symbol, start_date, end_date)
            else:
                logger.error(f"Fuente {ohlcv_source.name} no implementa get_ohlcv")
                return []
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error obteniendo OHLCV de {ohlcv_source.name}: {e}")
            return []

        if not raw_data:
            return []

        # Normalizar
        if normalize:
            raw_data = self.normalizer.normalize_ohlcv_data(
                raw_data, symbol, source=ohlcv_source.name
            )

        # Limpiar
        if clean:
            cleaning_result = self.cleaning_pipeline.clean(raw_data, symbol, 'ohlcv')
            raw_data = cleaning_result['cleaned_data']

        # Guardar en cache
        if use_cache:
            await self.cache.set(
                cache_key,
                raw_data,
                metadata={
                    'symbol': symbol,
                    'source': ohlcv_source.name,
                    'data_type': 'ohlcv',
                    'frequency': frequency,
                },
            )

        # Broadcast si streaming está habilitado
        if self.streaming_enabled and self.streaming_manager:
            await self.streaming_manager.broadcast_ohlcv(symbol, raw_data)

        return raw_data

    async def get_fundamentals(
        self,
        symbol: str,
        source: Optional[str] = None,
        data_type: str = 'profile',  # profile, metrics, statements
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener datos fundamentales.

        Args:
            symbol: Símbolo del instrumento
            source: Fuente específica (fmp, alpha_vantage_fundamental)
            data_type: Tipo de datos (profile, metrics, statements)
            use_cache: Usar cache si está disponible

        Returns:
            Dict con datos fundamentales
        """
        # Verificar cache
        if use_cache:
            cache_key = self.cache._make_key(
                'fundamentals', symbol, data_type=data_type, source=source
            )
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                logger.debug(f"Datos fundamentales obtenidos del cache para {symbol}")
                return cached_data

        # Determinar fuente
        fundamental_source = None
        if source:
            fundamental_source = self.sources.get(source)
        else:
            # Buscar primera fuente fundamental disponible
            for name in ['fmp', 'alpha_vantage_fundamental']:
                if name in self.sources:
                    fundamental_source = self.sources[name]
                    break
            else:
                logger.error("No hay fuente fundamental disponible")
                return None

        if not fundamental_source:
            return None

        # Verificar conexión
        if not fundamental_source.is_connected:
            await fundamental_source.connect()

        # Obtener datos según tipo
        result = None
        try:
            if isinstance(fundamental_source, FinancialModelingPrepSource):
                if data_type == 'profile':
                    result = await fundamental_source.get_company_profile(symbol)
                elif data_type == 'metrics':
                    result = {'metrics': await fundamental_source.get_key_metrics(symbol)}
                elif data_type == 'statements':
                    result = {
                        'income': await fundamental_source.get_financial_statements(
                            symbol, 'income-statement'
                        ),
                        'balance': await fundamental_source.get_financial_statements(
                            symbol, 'balance-sheet-statement'
                        ),
                        'cashflow': await fundamental_source.get_financial_statements(
                            symbol, 'cash-flow-statement'
                        ),
                    }

            elif isinstance(fundamental_source, AlphaVantageFundamentalSource):
                if data_type == 'profile':
                    result = await fundamental_source.get_company_overview(symbol)
                elif data_type == 'earnings':
                    result = await fundamental_source.get_earnings(symbol)

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error obteniendo fundamentales de {fundamental_source.name}: {e}")
            return None

        # Guardar en cache
        if result and use_cache:
            await self.cache.set(
                cache_key,
                result,
                metadata={
                    'symbol': symbol,
                    'source': fundamental_source.name,
                    'data_type': f'fundamentals_{data_type}',
                },
            )

        return result

    async def get_sentiment(
        self, symbol: str, source: Optional[str] = None, max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener sentimiento para un símbolo.

        Args:
            symbol: Símbolo del instrumento
            source: Fuente específica (twitter, reddit, news)
            max_results: Número máximo de resultados (usa config YAML si None)

        Returns:
            Dict con sentimiento agregado
        """
        # Obtener max_results desde config si no se especifica
        if max_results is None:
            sentiment_config = self.config_loader.get_sentiment_config()
            max_results = sentiment_config.get('default_max_results', 100)

        sentiment_sources_to_use = []

        if source:
            if source in self.sources:
                sentiment_sources_to_use.append(source)
        else:
            # Usar todas las fuentes disponibles
            sentiment_sources_to_use = [
                name for name in ['twitter', 'reddit', 'news'] if name in self.sources
            ]

        if not sentiment_sources_to_use:
            logger.warning("No hay fuente de sentimiento disponible")
            sentiment_config = self.config_loader.get_sentiment_config()
            return {
                'sentiment_score': sentiment_config.get('default_score', 0.0),
                'total_sources': sentiment_config.get('default_counts', {}).get('total', 0),
                'sources': {},
            }

        # Obtener sentimiento de cada fuente
        sentiment_results = {}

        for source_name in sentiment_sources_to_use:
            sentiment_source = self.sources[source_name]

            if not sentiment_source.is_connected:
                await sentiment_source.connect()

            try:
                if hasattr(sentiment_source, 'get_sentiment'):
                    result = await sentiment_source.get_sentiment(symbol, max_results=max_results)
                    sentiment_results[source_name] = result
                else:
                    logger.warning(f"Fuente {source_name} no implementa get_sentiment")
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error obteniendo sentimiento de {source_name}: {e}")

        # Agregar sentimientos
        sentiment_config = self.config_loader.get_sentiment_config()
        default_score = sentiment_config.get('default_score', 0.0)

        if sentiment_results:
            scores = [r.get('sentiment_score', default_score) for r in sentiment_results.values()]
            avg_score = np.mean(scores) if scores else default_score
        else:
            avg_score = default_score

        return {
            'sentiment_score': float(avg_score),
            'total_sources': len(sentiment_results),
            'sources': sentiment_results,
        }

    async def get_options_chain(
        self, symbol: str, expiry_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener cadena de opciones.

        Args:
            symbol: Símbolo del subyacente
            expiry_date: Fecha de expiración específica (opcional)

        Returns:
            Lista de opciones
        """
        if 'options_volatility' not in self.sources:
            logger.error("Fuente de opciones no disponible")
            return []

        source = self.sources['options_volatility']

        if not source.is_connected:
            await source.connect()

        try:
            if hasattr(source, 'get_option_chain'):
                return await source.get_option_chain(symbol, expiry_date)
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error obteniendo option chain: {e}")

        return []

    async def get_volatility_surface(
        self, symbol: str, expiry_dates: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Obtener volatility surface.

        Args:
            symbol: Símbolo del subyacente
            expiry_dates: Fechas de expiración (opcional)

        Returns:
            Dict con volatility surface
        """
        if 'options_volatility' not in self.sources:
            logger.error("Fuente de opciones no disponible")
            return {'expiry_dates': [], 'strikes': [], 'implied_volatility': {}, 'surface_data': []}

        source = self.sources['options_volatility']

        if not source.is_connected:
            await source.connect()

        try:
            if hasattr(source, 'get_volatility_surface'):
                return await source.get_volatility_surface(symbol, expiry_dates)
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error obteniendo volatility surface: {e}")

        return {'expiry_dates': [], 'strikes': [], 'implied_volatility': {}, 'surface_data': []}

    async def initialize(self) -> None:
        """Inicializar Data Engine (conectar fuentes, iniciar streaming)."""
        await self.connect_all()

        if self.streaming_enabled and self.streaming_manager:
            await self.streaming_manager.start()

    async def shutdown(self) -> None:
        """Cerrar Data Engine (desconectar fuentes, detener streaming)."""
        await self.disconnect_all()

        if self.streaming_manager:
            await self.streaming_manager.stop()

        if self.cache:
            await self.cache.close()

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del Data Engine."""
        status = {
            'sources': {
                name: {'is_connected': source.is_connected, 'status': source.get_status()}
                for name, source in self.sources.items()
            },
            'cache': self.cache.get_status() if self.cache else None,
            'streaming': self.streaming_manager.get_status() if self.streaming_manager else None,
            'streaming_enabled': self.streaming_enabled,
            'normalizer_enabled': self.normalizer is not None,
            'cleaning_enabled': self.cleaning_pipeline is not None,
            'versioning_enabled': self.version_manager is not None,
        }
        return status
