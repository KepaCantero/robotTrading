"""
DataLineage - Tracking de lineage de datos.

Rastrea el origen y transformaciones de datos.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DataLineageTracker:
    """
    Tracker de lineage de datos.

    Rastrea:
    - Origen de datos
    - Transformaciones aplicadas
    - Dependencias entre datasets
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Inicializar tracker.

        Args:
            config: Configuración
        """
        config = config or {}
        self.lineage_db_path = Path(config.get("lineage_db_path", "lineage/db.json"))
        self.lineage_db_path.parent.mkdir(parents=True, exist_ok=True)

        self.lineage_records: dict[str, dict[str, Any]] = {}
        self._load_lineage_db()

    def _load_lineage_db(self) -> None:
        """Cargar base de datos de lineage."""
        if self.lineage_db_path.exists():
            try:
                with open(self.lineage_db_path) as f:
                    self.lineage_records = json.load(f)
            except OSError as e:
                logger.warning(f"Error cargando lineage DB: {e}")

    def _save_lineage_db(self) -> None:
        """Guardar base de datos de lineage."""
        try:
            with open(self.lineage_db_path, "w") as f:
                json.dump(self.lineage_records, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Error guardando lineage DB: {e}")

    def record_data_source(
        self,
        data_id: str,
        source_type: str,
        source_config: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Registrar origen de datos.

        Args:
            data_id: ID único del dataset
            source_type: Tipo de fuente (binance, polygon, etc.)
            source_config: Configuración de la fuente
            metadata: Metadata adicional

        Returns:
            lineage_id
        """
        lineage_id = str(uuid4())

        record = {
            "lineage_id": lineage_id,
            "data_id": data_id,
            "source_type": source_type,
            "source_config": source_config,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "transformations": [],
            "dependencies": [],
        }

        self.lineage_records[lineage_id] = record
        self._save_lineage_db()

        logger.debug(f"Lineage registrado: {lineage_id} para data {data_id}")
        return lineage_id

    def record_transformation(
        self,
        lineage_id: str,
        transformation_type: str,
        transformation_config: dict[str, Any],
        output_data_id: str | None = None,
    ) -> None:
        """
        Registrar una transformación aplicada.

        Args:
            lineage_id: ID del lineage
            transformation_type: Tipo de transformación (normalize, clean, etc.)
            transformation_config: Configuración de la transformación
            output_data_id: ID del dataset de salida (opcional)
        """
        if lineage_id not in self.lineage_records:
            logger.warning(f"Lineage {lineage_id} no encontrado")
            return

        transformation = {
            "type": transformation_type,
            "config": transformation_config,
            "output_data_id": output_data_id,
            "applied_at": datetime.now().isoformat(),
        }

        self.lineage_records[lineage_id]["transformations"].append(transformation)
        self._save_lineage_db()

        logger.debug(f"Transformación registrada: {transformation_type} en {lineage_id}")

    def record_dependency(
        self, lineage_id: str, dependency_lineage_id: str, dependency_type: str = "derived_from"
    ) -> None:
        """
        Registrar dependencia entre datasets.

        Args:
            lineage_id: ID del lineage
            dependency_lineage_id: ID del lineage del que depende
            dependency_type: Tipo de dependencia
        """
        if lineage_id not in self.lineage_records:
            logger.warning(f"Lineage {lineage_id} no encontrado")
            return

        dependency = {
            "lineage_id": dependency_lineage_id,
            "type": dependency_type,
            "recorded_at": datetime.now().isoformat(),
        }

        self.lineage_records[lineage_id]["dependencies"].append(dependency)
        self._save_lineage_db()

    def get_lineage(self, lineage_id: str) -> dict[str, Any] | None:
        """Obtener lineage completo."""
        return self.lineage_records.get(lineage_id)

    def trace_lineage(self, lineage_id: str) -> dict[str, Any]:
        """
        Trazar lineage completo (recursivo).

        Args:
            lineage_id: ID del lineage

        Returns:
            Dict con árbol completo de lineage
        """
        if lineage_id not in self.lineage_records:
            return {}

        record = self.lineage_records[lineage_id].copy()

        # Trazar dependencias recursivamente
        dependencies_trace = []
        for dep in record.get("dependencies", []):
            dep_id = dep.get("lineage_id")
            if dep_id:
                dep_trace = self.trace_lineage(dep_id)
                if dep_trace:
                    dependencies_trace.append(dep_trace)

        record["dependencies_trace"] = dependencies_trace
        return record

    def query_lineage(
        self,
        source_type: str | None = None,
        data_id: str | None = None,
        transformation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query lineage por criterios.

        Args:
            source_type: Filtrar por tipo de fuente
            data_id: Filtrar por data_id
            transformation_type: Filtrar por tipo de transformación

        Returns:
            Lista de records que coinciden
        """
        results = []

        for record in self.lineage_records.values():
            match = True

            if source_type and record.get("source_type") != source_type:
                match = False

            if data_id and record.get("data_id") != data_id:
                match = False

            if transformation_type:
                transformations = record.get("transformations", [])
                if not any(t.get("type") == transformation_type for t in transformations):
                    match = False

            if match:
                results.append(record)

        return results
