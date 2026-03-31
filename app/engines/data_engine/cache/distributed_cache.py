"""
Distributed Cache - Sistema de cache distribuido con Redis y PostgreSQL.

Proporciona:
- Cache rapido con Redis (TTL, expiracion automatica) - REQUIRED
- Persistencia con PostgreSQL (datos historicos, metadata) - REQUIRED
- Cache en memoria como respaldo temporal

REQUIREMENTS:
- redis>=5.0.0 (OPTIONAL - will use in-memory fallback if not available)
- sqlalchemy>=2.0.0 must be installed
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Union

# Fallback pattern: Try to import redis, provide in-memory fallback if not available
REDIS_AVAILABLE = False
_redis_from_url: object = None
try:
    _redis_async_mod = importlib.import_module("redis.asyncio")
    _redis_from_url = _redis_async_mod.from_url
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis package not installed. Using in-memory cache fallback only.")

if TYPE_CHECKING:
    from redis.asyncio import Redis

from sqlalchemy import Column, DateTime, Index, LargeBinary, String, Text, create_engine
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.security.secrets.secure_serialization import sign_and_dump, verify_and_load

logger = logging.getLogger(__name__)


# Base para modelos SQLAlchemy - using DeclarativeBase for proper mypy support
class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""


class CacheEntry(Base):
    """Modelo de entrada de cache en PostgreSQL."""

    __tablename__ = "cache_entries"

    key = Column(String(255), primary_key=True)
    data = Column(LargeBinary, nullable=False)
    data_type = Column(String(50), nullable=False)
    symbol = Column(String(50), index=True)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, index=True)
    metadata_json = Column(Text)  # JSON metadata

    __table_args__ = (
        Index("idx_symbol_source", "symbol", "source"),
        Index("idx_expires_at", "expires_at"),
    )


# Type alias for cached values
CacheValue = Union[str, int, float, bool, dict[str, object], list[object]]

# Type alias for memory cache entries
MemoryCacheEntry = dict[
    str, Union[str, int, float, bool, dict[str, object], list[object], datetime]
]


class DistributedCache:
    """
    Sistema de cache distribuido.

    Usa Redis para cache rapido y PostgreSQL para persistencia.
    Fallback a cache en memoria si Redis no esta disponible.
    """

    def __init__(self, config: dict[str, str | int | float | bool] | None = None):
        """
        Inicializar cache distribuido.

        Args:
            config: Configuracion con:
                - redis_url: URL de Redis (opcional, desde YAML o env)
                - postgres_url: URL de PostgreSQL (opcional, desde YAML o env)
                - default_ttl: TTL por defecto en segundos (desde YAML)
                - use_redis: Usar Redis si esta disponible (desde YAML)
                - use_postgres: Usar PostgreSQL si esta disponible (desde YAML)
                - postgres_schema: Configuracion de esquema PostgreSQL (desde YAML)
        """
        config = config or {}
        self.config = config

        # Todos los valores deben venir de config, NO hardcodeados
        if "default_ttl" not in config:
            raise ValueError("default_ttl debe estar en config (cargado desde YAML)")
        if "use_redis" not in config:
            raise ValueError("use_redis debe estar en config (cargado desde YAML)")
        if "use_postgres" not in config:
            raise ValueError("use_postgres debe estar en config (cargado desde YAML)")

        self.default_ttl: int = int(config["default_ttl"])
        self.use_redis: bool = bool(config.get("use_redis", False))
        self.use_postgres: bool = bool(config.get("use_postgres", False))

        # Redis client
        self.redis_client: Redis | None = None
        if self.use_redis:
            if not REDIS_AVAILABLE or _redis_from_url is None:
                logger.warning(
                    "Redis package not installed. Disabling Redis cache, using in-memory fallback."
                )
                self.use_redis = False
            else:
                try:
                    redis_url = config.get("redis_url")
                    if not redis_url:
                        raise ValueError("redis_url debe estar en config cuando use_redis=True")
                    assert callable(_redis_from_url)
                    self.redis_client = _redis_from_url(redis_url, decode_responses=False)
                    logger.info("Redis cache inicializado")
                except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                    logger.warning(f"No se pudo conectar a Redis: {e}. Usando cache en memoria.")
                    self.use_redis = False

        # PostgreSQL connection
        self.postgres_engine = None
        self.postgres_session = None
        if self.use_postgres:
            try:
                postgres_url = config.get("postgres_url")
                if not postgres_url:
                    logger.warning("PostgreSQL URL no proporcionada. Cache solo en Redis/memoria.")
                    self.use_postgres = False
                else:
                    self.postgres_engine = create_engine(str(postgres_url))
                    Session = sessionmaker(bind=self.postgres_engine)
                    self.postgres_session = Session()

                    # Configurar esquema desde config
                    raw_schema_val: object = config.get("postgres_schema", {})
                    postgres_schema: dict[str, str] = (
                        dict(raw_schema_val) if isinstance(raw_schema_val, dict) else {}
                    )
                    CacheEntry.__tablename__ = postgres_schema.get(
                        "table_name", "data_engine_cache"
                    )

                    # Crear tablas si no existen
                    Base.metadata.create_all(self.postgres_engine)
                    logger.info("PostgreSQL cache inicializado")
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(
                    f"No se pudo conectar a PostgreSQL: {e}. Usando cache en Redis/memoria."
                )
                self.use_postgres = False

        # Fallback: cache en memoria (bounded)
        self.memory_cache: dict[str, MemoryCacheEntry] = {}
        self._max_memory_cache_size = 10000

        logger.info(
            f"DistributedCache inicializado: Redis={self.use_redis}, PostgreSQL={self.use_postgres}"
        )

    def _evict_memory_cache(self) -> None:
        """Evict expired and oldest entries when memory cache exceeds limit."""
        now = datetime.utcnow()
        # First pass: remove expired entries
        expired_keys = [
            k
            for k, v in self.memory_cache.items()
            if isinstance(v["expires_at"], datetime) and v["expires_at"] <= now
        ]
        for k in expired_keys:
            del self.memory_cache[k]
        # Second pass: if still over limit, drop oldest
        if len(self.memory_cache) > self._max_memory_cache_size:
            sorted_keys = sorted(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]["expires_at"],
            )
            to_remove = len(self.memory_cache) - self._max_memory_cache_size
            for k in sorted_keys[:to_remove]:
                del self.memory_cache[k]

    def _make_key(self, prefix: str, symbol: str, **kwargs: object) -> str:
        """Crear clave de cache."""
        parts = [prefix, symbol]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                parts.append(f"{key}:{value}")
        return ":".join(parts)

    async def get(self, key: str, default: CacheValue | None = None) -> CacheValue | None:
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
                    # SECURE: Use JSON+HMAC verification instead of pickle
                    result = verify_and_load(cached_data)
                    if isinstance(result, (str, int, float, bool, dict, list)):
                        return result
                    return None
            except ValueError as e:
                logger.warning(f"Security error getting from Redis: {e}")
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.warning(f"Error obteniendo de Redis: {e}")

        # Intentar PostgreSQL (offloaded to thread to avoid blocking event loop)
        if self.use_postgres and self.postgres_session:
            try:
                entry = await asyncio.to_thread(self._pg_get, key)

                if entry:
                    # SECURE: Use JSON+HMAC verification instead of pickle
                    result = verify_and_load(entry.data)
                    if isinstance(result, (str, int, float, bool, dict, list)):
                        return result
                    return None
            except ValueError as e:
                logger.warning(f"Security error getting from PostgreSQL: {e}")
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.warning(f"Error obteniendo de PostgreSQL: {e}")

        # Fallback a memoria
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            expires_at_value = entry["expires_at"]
            if isinstance(expires_at_value, datetime) and expires_at_value > datetime.utcnow():
                data_value = entry["data"]
                if isinstance(data_value, (str, int, float, bool, dict, list)):
                    return data_value
            else:
                # Expirar entrada
                del self.memory_cache[key]

        return default

    async def set(
        self,
        key: str,
        value: CacheValue,
        ttl: int | None = None,
        metadata: dict[str, str | int | float | bool] | None = None,
    ) -> bool:
        """
        Guardar valor en cache.

        Args:
            key: Clave del cache
            value: Valor a cachear
            ttl: TTL en segundos (usa default_ttl si None)
            metadata: Metadata adicional

        Returns:
            True si se guardo correctamente
        """
        effective_ttl: int = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=effective_ttl)
        # SECURE: Use JSON+HMAC instead of pickle
        serialized_data = sign_and_dump(value)

        success = True

        # Guardar en Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.setex(key, effective_ttl, serialized_data)
            except (asyncio.TimeoutError, OSError) as e:
                logger.warning(f"Error guardando en Redis: {e}")
                success = False

        # Guardar en PostgreSQL (offloaded to thread)
        if self.use_postgres and self.postgres_session:
            try:
                # Extraer metadata util
                metadata_json = json.dumps(metadata) if metadata else None
                symbol = metadata.get("symbol") if metadata else None
                source = metadata.get("source") if metadata else None
                data_type = metadata.get("data_type", "unknown") if metadata else "unknown"

                entry = CacheEntry(
                    key=key,
                    data=serialized_data,
                    data_type=data_type,
                    symbol=symbol,
                    source=source,
                    expires_at=expires_at,
                    metadata_json=metadata_json,
                )

                await asyncio.to_thread(self._pg_set, entry)
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.warning(f"Error guardando en PostgreSQL: {e}")
                if self.postgres_session:
                    self.postgres_session.rollback()
                success = False

        # Fallback a memoria
        self.memory_cache[key] = {"data": value, "expires_at": expires_at}
        self._evict_memory_cache()

        return success

    async def delete(self, key: str) -> bool:
        """Eliminar clave del cache."""
        success = True

        # Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.delete(key)
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.warning(f"Error eliminando de Redis: {e}")
                success = False

        # PostgreSQL (offloaded to thread)
        if self.use_postgres and self.postgres_session:
            try:
                await asyncio.to_thread(self._pg_delete, key)
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
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
            Numero de entradas eliminadas
        """
        now = datetime.utcnow()

        count = 0
        # PostgreSQL (offloaded to thread)
        if self.use_postgres and self.postgres_session:
            try:
                count += await asyncio.to_thread(self._pg_clear_expired, now)
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.warning(f"Error limpiando PostgreSQL: {e}")

        # Memoria
        expired_keys = [
            key
            for key, entry in self.memory_cache.items()
            if isinstance(entry["expires_at"], datetime) and entry["expires_at"] < now
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        count += len(expired_keys)

        return count

    async def close(self) -> None:
        """Cerrar conexiones."""
        if self.redis_client:
            await self.redis_client.close()

        if self.postgres_session:
            self.postgres_session.close()

        if self.postgres_engine:
            self.postgres_engine.dispose()

    # --- Thread-offload helpers for synchronous PostgreSQL operations ---

    def _pg_get(self, key: str) -> CacheEntry | None:
        """Synchronous PG get - call via asyncio.to_thread()."""
        if not self.postgres_session:
            return None
        return (
            self.postgres_session.query(CacheEntry)
            .filter(CacheEntry.key == key, CacheEntry.expires_at > datetime.utcnow())
            .first()
        )

    def _pg_set(self, entry: CacheEntry) -> None:
        """Synchronous PG upsert - call via asyncio.to_thread()."""
        if not self.postgres_session:
            return
        existing = self.postgres_session.query(CacheEntry).filter_by(key=entry.key).first()
        if existing:
            for attr, val in entry.__dict__.items():
                if attr != "_sa_instance_state":
                    setattr(existing, attr, val)
        else:
            self.postgres_session.add(entry)
        self.postgres_session.commit()

    def _pg_delete(self, key: str) -> None:
        """Synchronous PG delete - call via asyncio.to_thread()."""
        if not self.postgres_session:
            return
        self.postgres_session.query(CacheEntry).filter_by(key=key).delete()
        self.postgres_session.commit()

    def _pg_clear_expired(self, now: datetime) -> int:
        """Synchronous PG expired cleanup - call via asyncio.to_thread()."""
        if not self.postgres_session:
            return 0
        expired = self.postgres_session.query(CacheEntry).filter(CacheEntry.expires_at < now).all()
        count = len(expired)
        for entry in expired:
            self.postgres_session.delete(entry)
        self.postgres_session.commit()
        return count

    def get_status(self) -> dict[str, str | int | float | bool | None]:
        """Obtener estado del cache."""
        return {
            "redis_enabled": self.use_redis,
            "postgres_enabled": self.use_postgres,
            "memory_cache_size": len(self.memory_cache),
            "default_ttl": self.default_ttl,
        }
