"""
SchemaVersioner - Sistema de versionado de schemas.

Maneja cambios en estructura de datos y migraciones.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SchemaVersioner:
    """
    Sistema de versionado de schemas.

    Trackea cambios en estructura de datos y permite migraciones.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar versioner.

        Args:
            config: Configuración
        """
        config = config or {}
        self.schema_registry_path = Path(
            config.get("schema_registry_path", "schemas/registry.json")
        )
        self.schema_registry_path.parent.mkdir(parents=True, exist_ok=True)

        self.schemas: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, list[str]] = {}  # schema_name -> [versions]

        self._load_registry()

    def _load_registry(self) -> None:
        """Cargar registry de schemas."""
        if self.schema_registry_path.exists():
            try:
                with open(self.schema_registry_path) as f:
                    registry = json.load(f)
                    self.schemas = registry.get("schemas", {})
                    self.versions = registry.get("versions", {})
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Error cargando schema registry: {e}")

    def _save_registry(self) -> None:
        """Guardar registry de schemas."""
        try:
            registry = {
                "schemas": self.schemas,
                "versions": self.versions,
                "updated_at": datetime.now().isoformat(),
            }
            with open(self.schema_registry_path, "w") as f:
                json.dump(registry, f, indent=2)
        except OSError as e:
            logger.error(f"Error guardando schema registry: {e}")

    def register_schema(
        self, schema_name: str, version: str, schema_definition: dict[str, Any]
    ) -> None:
        """
        Registrar un schema.

        Args:
            schema_name: Nombre del schema
            version: Versión (ej: '1.0.0')
            schema_definition: Definición del schema
        """
        key = f"{schema_name}_{version}"
        self.schemas[key] = {
            "schema_name": schema_name,
            "version": version,
            "definition": schema_definition,
            "registered_at": datetime.now().isoformat(),
        }

        if schema_name not in self.versions:
            self.versions[schema_name] = []
        if version not in self.versions[schema_name]:
            self.versions[schema_name].append(version)
            self.versions[schema_name].sort()  # Ordenar versiones

        self._save_registry()
        logger.info(f"Schema registrado: {schema_name} v{version}")

    def get_schema(
        self, schema_name: str, version: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Obtener schema.

        Args:
            schema_name: Nombre del schema
            version: Versión específica (opcional, retorna la más reciente si None)

        Returns:
            Schema definition o None
        """
        if version:
            key = f"{schema_name}_{version}"
            return self.schemas.get(key)
        else:
            # Retornar versión más reciente
            if self.versions.get(schema_name):
                latest_version = self.versions[schema_name][-1]
                key = f"{schema_name}_{latest_version}"
                return self.schemas.get(key)

        return None

    def get_latest_version(self, schema_name: str) -> Optional[str]:
        """Obtener versión más reciente de un schema."""
        if self.versions.get(schema_name):
            return self.versions[schema_name][-1]
        return None

    def migrate_data(
        self, data: dict[str, Any], schema_name: str, from_version: str, to_version: str
    ) -> dict[str, Any]:
        """
        Migrar datos de una versión a otra.

        Args:
            data: Datos a migrar
            schema_name: Nombre del schema
            from_version: Versión origen
            to_version: Versión destino

        Returns:
            Datos migrados
        """
        # Por ahora, implementación simple
        # En producción, esto requeriría reglas de migración específicas

        from_schema = self.get_schema(schema_name, from_version)
        to_schema = self.get_schema(schema_name, to_version)

        if not from_schema or not to_schema:
            logger.warning("No se pueden encontrar schemas para migración")
            return data

        # Migración básica: mantener campos comunes, agregar defaults para nuevos
        migrated_data = data.copy()

        from_schema["definition"].get("fields", {})
        to_fields = to_schema["definition"].get("fields", {})

        # Agregar campos nuevos con defaults
        for field_name, field_def in to_fields.items():
            if field_name not in migrated_data:
                default_value = field_def.get("default")
                if default_value is not None:
                    migrated_data[field_name] = default_value

        # Remover campos deprecados (opcional)
        for field_name in list(migrated_data.keys()):
            if field_name not in to_fields:
                # Campo deprecado - mantenerlo por compatibilidad o remover
                pass

        return migrated_data
