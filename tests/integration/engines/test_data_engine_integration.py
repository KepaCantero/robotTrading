"""
Integration Tests: DataEngine (Módulo 1)

Tests para verificar funcionalidad completa del DataEngine:
- Múltiples fuentes de datos
- Normalización
- Limpieza de datos
- Versionado
- Cache distribuido
- Streaming WebSocket
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.data_engine import DataEngine
from app.engines.data_engine.cache.distributed_cache import DistributedCache
from app.engines.data_engine.streaming.websocket_streaming import WebSocketStreamingManager


@pytest.fixture
def data_engine_config():
    """Configuración básica para DataEngine."""
    return {
        'cache_config': {
            'use_redis': False,  # Usar solo memoria para tests
            'use_postgres': False,
            'default_ttl': 3600
        },
        'streaming_config': {
            'heartbeat_interval': 30,
            'max_connections': 10
        },
        'streaming_enabled': False,  # Deshabilitar streaming por defecto en tests
        'sources': {}
    }


@pytest.fixture
def data_engine(data_engine_config):
    """Crear instancia de DataEngine para tests."""
    engine = DataEngine(data_engine_config)
    return engine


class TestDataEngineInitialization:
    """Tests de inicialización del DataEngine."""
    
    def test_data_engine_creation(self, data_engine_config):
        """Test creación básica."""
        engine = DataEngine(data_engine_config)
        
        assert engine is not None
        assert engine.normalizer is not None
        assert engine.cleaning_pipeline is not None
        assert engine.cache is not None
        assert engine.streaming_manager is not None
    
    def test_data_engine_status(self, data_engine):
        """Test obtener estado."""
        status = data_engine.get_status()
        
        assert 'sources' in status
        assert 'cache' in status
        assert 'streaming' in status
        assert 'normalizer_enabled' in status
        assert 'cleaning_enabled' in status
        assert 'versioning_enabled' in status


class TestCacheIntegration:
    """Tests de integración del cache distribuido."""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, data_engine):
        """Test guardar y obtener del cache."""
        cache = data_engine.cache
        
        # Guardar
        key = "test:key:123"
        value = {"test": "data", "number": 42}
        success = await cache.set(key, value, ttl=60)
        assert success == True
        
        # Obtener
        cached = await cache.get(key)
        assert cached == value
        
        # Obtener inexistente
        missing = await cache.get("test:missing")
        assert missing is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, data_engine):
        """Test eliminar del cache."""
        cache = data_engine.cache
        
        # Guardar
        key = "test:delete:123"
        await cache.set(key, {"data": "test"}, ttl=60)
        
        # Verificar que existe
        assert await cache.get(key) is not None
        
        # Eliminar
        success = await cache.delete(key)
        assert success == True
        
        # Verificar que no existe
        assert await cache.get(key) is None
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, data_engine):
        """Test expiración de cache."""
        cache = data_engine.cache
        
        # Guardar con TTL muy corto
        key = "test:expire:123"
        await cache.set(key, {"data": "test"}, ttl=1)
        
        # Verificar que existe
        assert await cache.get(key) is not None
        
        # Esperar expiración
        await asyncio.sleep(2)
        
        # Limpiar expirados
        count = await cache.clear_expired()
        assert count >= 1
        
        # Verificar que no existe
        assert await cache.get(key) is None
    
    @pytest.mark.asyncio
    async def test_cache_status(self, data_engine):
        """Test estado del cache."""
        cache = data_engine.cache
        status = cache.get_status()
        
        assert 'redis_enabled' in status
        assert 'postgres_enabled' in status
        assert 'memory_cache_size' in status
        assert 'default_ttl' in status


class TestStreamingIntegration:
    """Tests de integración del streaming WebSocket."""
    
    def test_streaming_manager_creation(self, data_engine_config):
        """Test creación del streaming manager."""
        streaming_config = data_engine_config.get('streaming_config', {})
        manager = WebSocketStreamingManager(streaming_config)
        
        assert manager is not None
        assert manager.heartbeat_interval == 30
        assert manager.max_connections == 10
    
    @pytest.mark.asyncio
    async def test_streaming_manager_start_stop(self, data_engine_config):
        """Test iniciar y detener streaming manager."""
        streaming_config = data_engine_config.get('streaming_config', {})
        manager = WebSocketStreamingManager(streaming_config)
        
        # Iniciar
        await manager.start()
        assert manager._running == True
        
        # Detener
        await manager.stop()
        assert manager._running == False
    
    def test_streaming_manager_status(self, data_engine_config):
        """Test estado del streaming manager."""
        streaming_config = data_engine_config.get('streaming_config', {})
        manager = WebSocketStreamingManager(streaming_config)
        
        status = manager.get_status()
        
        assert 'active_connections' in status
        assert 'total_subscriptions' in status
        assert 'symbols_subscribed' in status
        assert 'max_connections' in status
        assert 'running' in status


class TestDataEngineAPIs:
    """Tests de APIs del DataEngine."""
    
    @pytest.mark.asyncio
    async def test_get_ohlcv_cache_integration(self, data_engine):
        """Test get_ohlcv con cache."""
        # Este test requiere fuentes configuradas
        # Por ahora solo verificamos que el método existe y maneja cache
        
        # Sin fuentes configuradas, debería retornar lista vacía
        result = await data_engine.get_ohlcv(
            symbol="AAPL",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            use_cache=True
        )
        
        # Sin fuentes, debería retornar lista vacía
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_fundamentals_cache_integration(self, data_engine):
        """Test get_fundamentals con cache."""
        # Sin fuentes configuradas, debería retornar None
        result = await data_engine.get_fundamentals(
            symbol="AAPL",
            data_type="profile",
            use_cache=True
        )
        
        # Sin fuentes, debería retornar None
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_get_sentiment(self, data_engine):
        """Test get_sentiment."""
        result = await data_engine.get_sentiment(
            symbol="AAPL",
            max_results=10
        )
        
        # Debería retornar dict con estructura de sentimiento
        assert isinstance(result, dict)
        assert 'sentiment_score' in result
        assert 'total_sources' in result
        assert 'sources' in result


class TestDataEngineLifecycle:
    """Tests de ciclo de vida del DataEngine."""
    
    @pytest.mark.asyncio
    async def test_initialize_shutdown(self, data_engine):
        """Test inicialización y cierre."""
        # Inicializar
        await data_engine.initialize()
        
        # Verificar estado
        status = data_engine.get_status()
        assert status is not None
        
        # Cerrar
        await data_engine.shutdown()
        
        # Verificar que se cerró correctamente
        # (no debería lanzar errores)


class TestDataEngineIntegration:
    """Tests de integración completa."""
    
    @pytest.mark.asyncio
    async def test_cache_with_ohlcv(self, data_engine):
        """Test integración de cache con get_ohlcv."""
        # Este test verifica que el cache funciona con get_ohlcv
        # Sin fuentes configuradas, no puede obtener datos reales
        # pero verifica que el código de cache no causa errores
        
        result = await data_engine.get_ohlcv(
            symbol="TEST",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            use_cache=True
        )
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_cache_with_fundamentals(self, data_engine):
        """Test integración de cache con get_fundamentals."""
        result = await data_engine.get_fundamentals(
            symbol="TEST",
            use_cache=True
        )
        
        # Sin fuentes, debería retornar None
        assert result is None or isinstance(result, dict)
    
    def test_distributed_cache_fallback(self):
        """Test que DistributedCache funciona sin Redis/PostgreSQL."""
        config = {
            'use_redis': False,
            'use_postgres': False,
            'default_ttl': 3600
        }
        
        cache = DistributedCache(config)
        
        assert cache is not None
        assert cache.use_redis == False
        assert cache.use_postgres == False
        
        status = cache.get_status()
        assert status['redis_enabled'] == False
        assert status['postgres_enabled'] == False

