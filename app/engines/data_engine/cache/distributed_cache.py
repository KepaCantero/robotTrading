"""
Distributed Cache - Sistema de cache distribuido con Redis y PostgreSQL.

Proporciona:
- Cache rápido con Redis (TTL, expiración automática)
- Persistencia con PostgreSQL (datos históricos, metadata)
- Fallback a cache en memoria si Redis no está disponible
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Redis (opcional)
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# PostgreSQL (opcional)
try:
    from sqlalchemy import Column, DateTime, Index, LargeBinary, String, Text, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    create_engine = None
    declarative_base = None
    sessionmaker = None

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
if POSTGRESQL_AVAILABLE:
    Base = declarative_base()

    class CacheEntry(Base):
        """Modelo de entrada de cache en PostgreSQL."""


        key = Column(String(255), primary_key=True)
        data = Column(LargeBinary, nullable=False)
        data_type = Column(String(50), nullable=False)
        symbol = Column(String(50), index=True)
        source = Column(String(50))
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        expires_at = Column(DateTime, index=True)
        metadata_json = Column(Text)  # JSON metadata

            Index('idx_symbol_source', 'symbol', 'source'),
            Index('idx_expires_at', 'expires_at'),
        )


class DistributedCache:
    """
    Sistema de cache distribuido.

    Usa Redis para cache rápido y PostgreSQL para persistencia.
    Fallback a cache en memoria si Redis no está disponible.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar cache distribuido.

        Args:
            config: Configuración con:
                - redis_url: URL de Redis (opcional, desde YAML o env)
                - postgres_url: URL de PostgreSQL (opcional, desde YAML o env)
                - default_ttl: TTL por defecto en segundos (desde YAML)
                - use_redis: Usar Redis si está disponible (desde YAML)
                - use_postgres: Usar PostgreSQL si está disponible (desde YAML)
                - postgres_schema: Configuración de esquema PostgreSQL (desde YAML)
        """
        config = config or {}
        self.config = config

        # Todos los valores deben venir de config, NO hardcodeados
        if 'default_ttl' not in config:
            raise ValueError("default_ttl debe estar en config (cargado desde YAML)")
        if 'use_redis' not in config:
            raise ValueError("use_redis debe estar en config (cargado desde YAML)")
        if 'use_postgres' not in config:
            raise ValueError("use_postgres debe estar en config (cargado desde YAML)")

        self.default_ttl = config['default_ttl']
        self.use_redis = config.get('use_redis', False) and REDIS_AVAILABLE
        self.use_postgres = config.get('use_postgres', False) and POSTGRESQL_AVAILABLE

        # Redis client
        self.redis_client: Optional[redis.Redis] = None
        if self.use_redis:
            try:
                redis_url = config.get('redis_url')
                if not redis_url:
                    raise ValueError("redis_url debe estar en config cuando use_redis=True")
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                logger.info("Redis cache inicializado")
            except Exception as e:
                logger.warning(f"No se pudo conectar a Redis: {e}. Usando cache en memoria.")
                self.use_redis = False

        # PostgreSQL connection
        self.postgres_engine = None
        self.postgres_session = None
        if self.use_postgres:
            try:
                postgres_url = config.get('postgres_url')
                if not postgres_url:
                    logger.warning("PostgreSQL URL no proporcionada. Cache solo en Redis/memoria.")
                    self.use_postgres = False
                else:
                    self.postgres_engine = create_engine(postgres_url)
                    Session = sessionmaker(bind=self.postgres_engine)
                    self.postgres_session = Session()

                    # Configurar esquema desde config
                    postgres_schema = config.get('postgres_schema', {})
                    if POSTGRESQL_AVAILABLE:
                        # Actualizar tabla si hay configuración personalizada
                        CacheEntry.__tablename__ = postgres_schema.get(
                            'table_name', 'data_engine_cache'
                        )

                    # Crear tablas si no existen
                    Base.metadata.create_all(self.postgres_engine)
                    logger.info("PostgreSQL cache inicializado")
            except Exception as e:
                logger.warning(
                    f"No se pudo conectar a PostgreSQL: {e}. Usando cache en Redis/memoria."
                )
                self.use_postgres = False

        # Fallback: cache en memoria
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"DistributedCache inicializado: Redis={self.use_redis}, PostgreSQL={self.use_postgres}"
        )

    def _make_key(self, prefix: str, symbol: str, **kwargs) -> str:
        """Crear clave de cache."""
        parts = [prefix, symbol]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                parts.append(f"{key}:{value}")
        return ":".join(parts)

    async def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Obtener valor del cache.

        Args:
            key: Clave del cache
            default: Valor por defecto si no existe

        Returns:
            Valor cacheado o default
        """
        # Intentar Redis primero
        if self.use_redis and self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                logger.warning(f"Error obteniendo de Redis: {e}")

        # Intentar PostgreSQL
        if self.use_postgres and self.postgres_session:
            try:
                entry = (
                    self.postgres_session.query(CacheEntry)
                    .filter(CacheEntry.key == key, CacheEntry.expires_at > datetime.utcnow())
                    .first()
                )

                if entry:
                    return pickle.loads(entry.data)
            except Exception as e:
                logger.warning(f"Error obteniendo de PostgreSQL: {e}")

        # Fallback a memoria
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if entry['expires_at'] > datetime.utcnow():
                return entry['data']
            else:
                # Expirar entrada
                del self.memory_cache[key]

        return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Guardar valor en cache.

        Args:
            key: Clave del cache
            value: Valor a cachear
            ttl: TTL en segundos (usa default_ttl si None)
            metadata: Metadata adicional

        Returns:
            True si se guardó correctamente
        """
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        serialized_data = pickle.dumps(value)

        success = True

        # Guardar en Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, serialized_data)
            except Exception as e:
                logger.warning(f"Error guardando en Redis: {e}")
                success = False

        # Guardar en PostgreSQL
        if self.use_postgres and self.postgres_session:
            try:
                # Extraer metadata útil
                metadata_json = json.dumps(metadata) if metadata else None
                symbol = metadata.get('symbol') if metadata else None
                source = metadata.get('source') if metadata else None
                data_type = metadata.get('data_type', 'unknown') if metadata else 'unknown'

                entry = CacheEntry(
                    key=key,
                    data=serialized_data,
                    data_type=data_type,
                    symbol=symbol,
                    source=source,
                    expires_at=expires_at,
                    metadata_json=metadata_json,
                )

                # Upsert
                existing = self.postgres_session.query(CacheEntry).filter_by(key=key).first()
                if existing:
                    for attr, val in entry.__dict__.items():
                        if attr != '_sa_instance_state':
                            setattr(existing, attr, val)
                else:
                    self.postgres_session.add(entry)

                self.postgres_session.commit()
            except Exception as e:
                logger.warning(f"Error guardando en PostgreSQL: {e}")
                if self.postgres_session:
                    self.postgres_session.rollback()
                success = False

        # Fallback a memoria
        self.memory_cache[key] = {'data': value, 'expires_at': expires_at}

        return success

    async def delete(self, key: str) -> bool:
        """Eliminar clave del cache."""
        success = True

        # Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Error eliminando de Redis: {e}")
                success = False

        # PostgreSQL
        if self.use_postgres and self.postgres_session:
            try:
                self.postgres_session.query(CacheEntry).filter_by(key=key).delete()
                self.postgres_session.commit()
            except Exception as e:
                logger.warning(f"Error eliminando de PostgreSQL: {e}")
                if self.postgres_session:
                    self.postgres_session.rollback()
                success = False

        # Memoria
        if key in self.memory_cache:
            del self.memory_cache[key]

        return success

    async def clear_expired(self) -> int:
        """
        Limpiar entradas expiradas.

        Returns:
            Número de entradas eliminadas
        """
        count = 0
        now = datetime.utcnow()

        # PostgreSQL
        if self.use_postgres and self.postgres_session:
            try:
                expired = (
                    self.postgres_session.query(CacheEntry)
                    .filter(CacheEntry.expires_at < now)
                    .all()
                )
                count += len(expired)
                for entry in expired:
                    self.postgres_session.delete(entry)
                self.postgres_session.commit()
            except Exception as e:
                logger.warning(f"Error limpiando PostgreSQL: {e}")

        # Memoria
        expired_keys = [
            key for key, entry in self.memory_cache.items() if entry['expires_at'] < now
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            count += 1

        return count

    async def close(self) -> None:
        """Cerrar conexiones."""
        if self.redis_client:
            await self.redis_client.close()

        if self.postgres_session:
            self.postgres_session.close()

        if self.postgres_engine:
            self.postgres_engine.dispose()

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del cache."""
        return {
            'redis_enabled': self.use_redis,
            'postgres_enabled': self.use_postgres,
            'memory_cache_size': len(self.memory_cache),
            'default_ttl': self.default_ttl,
        }
