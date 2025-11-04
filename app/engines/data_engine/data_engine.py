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

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pathlib import Path

from .sources.base_source import BaseDataSource
from .sources.ohlcv_sources import IBKRSource, BinanceSource, AlpacaSource, PolygonSource
from .sources.fundamental_sources import FinancialModelingPrepSource, AlphaVantageFundamentalSource
from .sources.sentiment_sources import TwitterSentimentSource, RedditSentimentSource, NewsSentimentSource
from .sources.options_sources import OptionsVolatilitySource

from .normalizers.unified_normalizer import UnifiedNormalizer

from .validators.data_cleaning_pipeline import DataCleaningPipeline

from .versioning.schema_versioner import SchemaVersioner
from .versioning.data_lineage import DataLineageTracker
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
            config: Configuración completa del engine
        """
        config = config or {}
        self.config = config
        
        # Inicializar componentes
        self.sources: Dict[str, BaseDataSource] = {}
        self.normalizer = UnifiedNormalizer(config.get('normalizer_config', {}))
        self.cleaning_pipeline = DataCleaningPipeline(config.get('cleaning_config', {}))
        
        self.schema_versioner = SchemaVersioner(config.get('schema_config', {}))
        self.lineage_tracker = DataLineageTracker(config.get('lineage_config', {}))
        self.version_manager = DataVersionManager(config.get('version_config', {}))
        
        # Cache (simple dict, puede mejorarse con Redis)
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hora
        
        # Inicializar fuentes configuradas
        self._initialize_sources(config.get('sources', {}))
    
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
            self.sources['options_volatility'] = OptionsVolatilitySource(options_sources['volatility'])
        
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
            except Exception as e:
                logger.error(f"Error conectando a {source_name}: {e}")
                connection_status[source_name] = False
        
        return connection_status
    
    async def disconnect_all(self) -> None:
        """Desconectar de todas las fuentes."""
        for source_name, source in self.sources.items():
            try:
                await source.disconnect()
                logger.info(f"Desconectado de {source_name}")
            except Exception as e:
                logger.error(f"Error desconectando de {source_name}: {e}")
    
    async def get_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        source: Optional[str] = None,
        frequency: str = '1d',
        normalize: bool = True,
        clean: bool = True
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
        
        Returns:
            Lista de datos OHLCV
        """
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
        except Exception as e:
            logger.error(f"Error obteniendo OHLCV de {ohlcv_source.name}: {e}")
            return []
        
        if not raw_data:
            return []
        
        # Normalizar
        if normalize:
            raw_data = self.normalizer.normalize_ohlcv_data(raw_data, symbol, source=ohlcv_source.name)
        
        # Limpiar
        if clean:
            cleaning_result = self.cleaning_pipeline.clean(raw_data, symbol, 'ohlcv')
            raw_data = cleaning_result['cleaned_data']
        
        return raw_data
    
    async def get_fundamentals(
        self,
        symbol: str,
        source: Optional[str] = None,
        data_type: str = 'profile'  # profile, metrics, statements
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener datos fundamentales.
        
        Args:
            symbol: Símbolo del instrumento
            source: Fuente específica (fmp, alpha_vantage_fundamental)
            data_type: Tipo de datos (profile, metrics, statements)
        
        Returns:
            Dict con datos fundamentales
        """
        # Determinar fuente
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
        try:
            if isinstance(fundamental_source, FinancialModelingPrepSource):
                if data_type == 'profile':
                    return await fundamental_source.get_company_profile(symbol)
                elif data_type == 'metrics':
                    return {'metrics': await fundamental_source.get_key_metrics(symbol)}
                elif data_type == 'statements':
                    return {
                        'income': await fundamental_source.get_financial_statements(symbol, 'income-statement'),
                        'balance': await fundamental_source.get_financial_statements(symbol, 'balance-sheet-statement'),
                        'cashflow': await fundamental_source.get_financial_statements(symbol, 'cash-flow-statement')
                    }
            
            elif isinstance(fundamental_source, AlphaVantageFundamentalSource):
                if data_type == 'profile':
                    return await fundamental_source.get_company_overview(symbol)
                elif data_type == 'earnings':
                    return await fundamental_source.get_earnings(symbol)
            
        except Exception as e:
            logger.error(f"Error obteniendo fundamentales de {fundamental_source.name}: {e}")
            return None
        
        return None
    
    async def get_sentiment(
        self,
        symbol: str,
        source: Optional[str] = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        Obtener sentimiento para un símbolo.
        
        Args:
            symbol: Símbolo del instrumento
            source: Fuente específica (twitter, reddit, news)
            max_results: Número máximo de resultados
        
        Returns:
            Dict con sentimiento agregado
        """
        sentiment_sources_to_use = []
        
        if source:
            if source in self.sources:
                sentiment_sources_to_use.append(source)
        else:
            # Usar todas las fuentes disponibles
            sentiment_sources_to_use = [name for name in ['twitter', 'reddit', 'news'] if name in self.sources]
        
        if not sentiment_sources_to_use:
            logger.warning("No hay fuente de sentimiento disponible")
            return {
                'sentiment_score': 0.0,
                'total_sources': 0,
                'sources': {}
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
            except Exception as e:
                logger.error(f"Error obteniendo sentimiento de {source_name}: {e}")
        
        # Agregar sentimientos
        if sentiment_results:
            scores = [r.get('sentiment_score', 0.0) for r in sentiment_results.values()]
            avg_score = sum(scores) / len(scores) if scores else 0.0
        else:
            avg_score = 0.0
        
        return {
            'sentiment_score': float(avg_score),
            'total_sources': len(sentiment_results),
            'sources': sentiment_results
        }
    
    async def get_options_chain(
        self,
        symbol: str,
        expiry_date: Optional[datetime] = None
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
        except Exception as e:
            logger.error(f"Error obteniendo option chain: {e}")
        
        return []
    
    async def get_volatility_surface(
        self,
        symbol: str,
        expiry_dates: Optional[List[datetime]] = None
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
            return {
                'expiry_dates': [],
                'strikes': [],
                'implied_volatility': {},
                'surface_data': []
            }
        
        source = self.sources['options_volatility']
        
        if not source.is_connected:
            await source.connect()
        
        try:
            if hasattr(source, 'get_volatility_surface'):
                return await source.get_volatility_surface(symbol, expiry_dates)
        except Exception as e:
            logger.error(f"Error obteniendo volatility surface: {e}")
        
        return {
            'expiry_dates': [],
            'strikes': [],
            'implied_volatility': {},
            'surface_data': []
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del Data Engine."""
        return {
            'sources': {
                name: {
                    'is_connected': source.is_connected,
                    'status': source.get_status()
                }
                for name, source in self.sources.items()
            },
            'cache_size': len(self.cache),
            'normalizer_enabled': self.normalizer is not None,
            'cleaning_enabled': self.cleaning_pipeline is not None,
            'versioning_enabled': self.version_manager is not None
        }

