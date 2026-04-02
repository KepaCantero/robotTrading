"""
DataEngine Config Loader - Cargador de configuración desde YAML.

Garantiza que todos los parámetros provengan de configuración,
eliminando números mágicos del código.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class DataEngineConfigLoader:
    """Cargador de configuración para DataEngine."""

    def __init__(self, config_path: str = "config/market/data_engine.yaml"):
        """
        Inicializar cargador de configuración.

        Args:
            config_path: Ruta al archivo YAML de configuración
        """
        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Cargar configuración desde YAML."""
        if not self.config_path.exists():
            logger.warning(f"DataEngine config not found: {self.config_path}. Using defaults.")
            self.config = self._get_default_config()
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            logger.info(f"DataEngine config loaded from {self.config_path}")
        except OSError as e:
            logger.error(f"Error loading DataEngine config: {e}. Using defaults.")
            self.config = self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Configuración por defecto si no existe archivo."""
        return {
            "cache": {
                "enabled": True,
                "default_ttl_seconds": 3600,
                "redis": {"enabled": True, "url": ""},
                "postgres": {"enabled": True, "url": ""},
            },
            "streaming": {
                "enabled": False,
                "heartbeat_interval_seconds": 30,
                "max_connections": 100,
            },
        }

    def get_cache_config(
        self, env_redis_url: str | None = None, env_postgres_url: str | None = None
    ) -> dict[str, Any]:
        """
        Obtener configuración de cache.

        Args:
            env_redis_url: URL de Redis desde variables de entorno
            env_postgres_url: URL de PostgreSQL desde variables de entorno

        Returns:
            Configuración de cache
        """
        cache_config = self.config.get("cache", {})

        # Usar URL de entorno si no está especificada en YAML
        redis_url = cache_config.get("redis", {}).get("url") or env_redis_url
        postgres_url = cache_config.get("postgres", {}).get("url") or env_postgres_url

        return {
            "enabled": cache_config.get("enabled", True),
            "default_ttl": cache_config.get("default_ttl_seconds", 3600),
            "use_redis": cache_config.get("redis", {}).get("enabled", True),
            "use_postgres": cache_config.get("postgres", {}).get("enabled", True),
            "redis_url": redis_url,
            "postgres_url": postgres_url,
            "postgres_schema": cache_config.get("postgres_schema", {}),
        }

    def get_streaming_config(self) -> dict[str, Any]:
        """Obtener configuración de streaming."""
        streaming_config = self.config.get("streaming", {})

        return {
            "enabled": streaming_config.get("enabled", False),
            "heartbeat_interval": streaming_config.get("heartbeat_interval_seconds", 30),
            "max_connections": streaming_config.get("max_connections", 100),
            "websocket_path": streaming_config.get("websocket_path", "/ws/data/{client_id}"),
            "max_connection_code": streaming_config.get("max_connection_code", 1008),
            "connection_reason_max_reached": streaming_config.get(
                "connection_reason_max_reached", "Maximum connections reached"
            ),
        }

    def get_source_config(self, source_type: str, source_name: str | None = None) -> dict[str, Any]:
        """
        Obtener configuración de fuente específica.

        Args:
            source_type: Tipo de fuente (ohlcv, fundamental, sentiment, options)
            source_name: Nombre específico de fuente (opcional)

        Returns:
            Configuración de fuente
        """
        sources_config = self.config.get("sources", {})
        source_type_config = sources_config.get(source_type, {})

        if source_name:
            return source_type_config.get(source_name, {})

        return source_type_config

    def get_ibkr_config(self) -> dict[str, Any]:
        """Obtener configuración de IBKR."""
        ibkr_config = self.config.get("ibkr", {})

        return {
            "paper_trading_port": ibkr_config.get("paper_trading_port", 7497),
            "live_trading_port": ibkr_config.get("live_trading_port", 7496),
            "default_client_id": ibkr_config.get("default_client_id", 1),
            "default_bar_size": ibkr_config.get("default_bar_size", "1 day"),
        }

    def get_api_config(self) -> dict[str, Any]:
        """Obtener configuración de API."""
        api_config = self.config.get("api", {})

        return {
            "success_status": api_config.get("success_status", 200),
            "error_status": api_config.get("error_status", 500),
        }

    def get_sentiment_config(self, source_name: str | None = None) -> dict[str, Any]:
        """
        Obtener configuración de análisis de sentimiento.

        Args:
            source_name: Nombre de fuente específica (twitter, reddit, news)

        Returns:
            Configuración de sentimiento
        """
        sentiment_config = self.config.get("sentiment", {})
        sources_config = self.config.get("sources", {}).get("sentiment", {})

        config = {
            "default_score": sentiment_config.get("default_score", 0.0),
            "default_counts": sentiment_config.get(
                "default_counts", {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            ),
            "default_max_results": sources_config.get("default_max_results", 100),
        }

        if source_name and source_name in sources_config:
            source_specific = sources_config[source_name]
            config.update(
                {
                    "max_results_limit": source_specific.get("max_results_limit", 100),
                    "sample_size": source_specific.get("sample_size", 10),
                    "default_sentiment_values": source_specific.get(
                        "default_sentiment_values",
                        {"positive": 0.5, "negative": -0.5, "neutral": 0.0},
                    ),
                }
            )

            # Configuraciones específicas por fuente
            if source_name == "twitter":
                config["max_results_limit"] = source_specific.get("max_results_limit", 100)
            elif source_name == "reddit":
                config["reddit_api_limit"] = source_specific.get("reddit_api_limit", 25)
            elif source_name == "news":
                config["news_api_limit"] = source_specific.get("news_api_limit", 100)
                config["sample_feed_size"] = source_specific.get("sample_feed_size", 5)

        return config

    def get_normalization_config(self) -> dict[str, Any]:
        """Obtener configuración de normalización."""
        norm_config = self.config.get("normalization", {})

        return {
            "timestamp_format": norm_config.get("timestamp_format", "%Y-%m-%d %H:%M:%S"),
            "timezone": norm_config.get("timezone", "UTC"),
        }

    def get_cleaning_config(self) -> dict[str, Any]:
        """Obtener configuración de limpieza."""
        cleaning_config = self.config.get("cleaning", {})

        return {
            "enabled": cleaning_config.get("enabled", True),
            "outlier_detection": cleaning_config.get("outlier_detection", {}),
            "gap_interpolation": cleaning_config.get("gap_interpolation", {}),
        }

    def get_versioning_config(self) -> dict[str, Any]:
        """Obtener configuración de versionado."""
        versioning_config = self.config.get("versioning", {})

        return {
            "enabled": versioning_config.get("enabled", True),
            "schema_version": versioning_config.get("schema_version", "1.0.0"),
            "data_lineage_enabled": versioning_config.get("data_lineage_enabled", True),
        }
