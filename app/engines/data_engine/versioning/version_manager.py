"""
DataVersionManager - Gestor de versionado de datos.

Maneja versionado completo de datasets con rollback capabilities.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class DataVersionManager:
    """
    Gestor de versionado de datos.

    Permite:
    - Versionado de datasets
    - Rollback a versiones anteriores
    - Historial de cambios
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar version manager.

        Args:
            config: Configuración
        """
        config = config or {}
        self.versions_dir = Path(config.get("versions_dir", "data/versions"))
        self.versions_dir.mkdir(parents=True, exist_ok=True)

        self.version_history: dict[str, list[dict[str, Any]]] = {}
        self._load_version_history()

    def _load_version_history(self) -> None:
        """Cargar historial de versiones."""
        history_file = self.versions_dir / "version_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    self.version_history = json.load(f)
            except OSError as e:
                logger.warning(f"Error cargando version history: {e}")

    def _save_version_history(self) -> None:
        """Guardar historial de versiones."""
        history_file = self.versions_dir / "version_history.json"
        try:
            with open(history_file, "w") as f:
                json.dump(self.version_history, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Error guardando version history: {e}")

    def create_version(
        self,
        dataset_id: str,
        data: Union[list, dict, str],
        version_tag: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Crear nueva versión de un dataset.

        Args:
            dataset_id: ID del dataset
            data: Datos a versionar
            version_tag: Tag de versión (opcional, auto-generado si None)
            metadata: Metadata adicional

        Returns:
            version_id
        """
        # Generar version_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"{dataset_id}_{timestamp}"
        if version_tag:
            version_id = f"{dataset_id}_{version_tag}"

        # Guardar datos
        version_dir = self.versions_dir / dataset_id / version_id
        version_dir.mkdir(parents=True, exist_ok=True)

        # Guardar datos (asumir que es serializable)
        data_file = version_dir / "data.json"
        try:
            if isinstance(data, (list, dict)):
                with open(data_file, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                # Otros tipos - guardar como string
                with open(data_file, "w") as f:
                    f.write(str(data))
        except OSError as e:
            logger.error(f"Error guardando datos de versión: {e}")
            raise

        # Guardar metadata
        metadata_file = version_dir / "metadata.json"
        version_metadata = {
            "version_id": version_id,
            "dataset_id": dataset_id,
            "version_tag": version_tag,
            "created_at": datetime.now().isoformat(),
            "data_size": len(str(data)),
            **(metadata or {}),
        }

        with open(metadata_file, "w") as f:
            json.dump(version_metadata, f, indent=2)

        # Registrar en historial
        if dataset_id not in self.version_history:
            self.version_history[dataset_id] = []

        self.version_history[dataset_id].append(
            {
                "version_id": version_id,
                "version_tag": version_tag,
                "created_at": datetime.now().isoformat(),
                "metadata": version_metadata,
            }
        )

        self._save_version_history()

        logger.info(f"Versión creada: {version_id}")
        return version_id

    def get_version(self, dataset_id: str, version_id: str) -> Optional[dict[str, Any]]:
        """
        Obtener datos de una versión específica.

        Args:
            dataset_id: ID del dataset
            version_id: ID de la versión

        Returns:
            Dict con datos y metadata
        """
        version_dir = self.versions_dir / dataset_id / version_id

        if not version_dir.exists():
            logger.warning(f"Versión no encontrada: {version_id}")
            return None

        try:
            # Cargar datos
            data_file = version_dir / "data.json"
            with open(data_file) as f:
                data = json.load(f)

            # Cargar metadata
            metadata_file = version_dir / "metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)

            return {
                "data": data,
                "metadata": metadata,
                "version_id": version_id,
                "dataset_id": dataset_id,
            }

        except OSError as e:
            logger.error(f"Error cargando versión {version_id}: {e}")
            return None

    def list_versions(self, dataset_id: str) -> list[dict[str, Any]]:
        """
        Listar todas las versiones de un dataset.

        Args:
            dataset_id: ID del dataset

        Returns:
            Lista de versiones
        """
        if dataset_id not in self.version_history:
            return []

        return self.version_history[dataset_id]

    def get_latest_version(self, dataset_id: str) -> Optional[str]:
        """
        Obtener ID de la versión más reciente.

        Args:
            dataset_id: ID del dataset

        Returns:
            version_id o None
        """
        versions = self.list_versions(dataset_id)
        if versions:
            # Ordenar por created_at y retornar la más reciente
            sorted_versions = sorted(versions, key=lambda x: x.get("created_at", ""), reverse=True)
            return sorted_versions[0].get("version_id")
        return None

    def rollback(self, dataset_id: str, version_id: str) -> bool:
        """
        Hacer rollback a una versión anterior.

        Args:
            dataset_id: ID del dataset
            version_id: ID de la versión a restaurar

        Returns:
            True si el rollback fue exitoso
        """
        version_data = self.get_version(dataset_id, version_id)
        if not version_data:
            logger.error(f"No se puede hacer rollback: versión {version_id} no encontrada")
            return False

        # Crear nueva versión con los datos restaurados
        new_version_id = self.create_version(
            dataset_id,
            version_data["data"],
            version_tag=f"rollback_to_{version_id}",
            metadata={"rollback_from": version_id, "rollback_at": datetime.now().isoformat()},
        )

        logger.info(f"Rollback completado: {dataset_id} -> {new_version_id} (desde {version_id})")
        return True

    def delete_version(self, dataset_id: str, version_id: str) -> bool:
        """
        Eliminar una versión.

        Args:
            dataset_id: ID del dataset
            version_id: ID de la versión

        Returns:
            True si se eliminó correctamente
        """
        version_dir = self.versions_dir / dataset_id / version_id

        if not version_dir.exists():
            logger.warning(f"Versión no encontrada para eliminar: {version_id}")
            return False

        try:
            shutil.rmtree(version_dir)

            # Remover de historial
            if dataset_id in self.version_history:
                self.version_history[dataset_id] = [
                    v for v in self.version_history[dataset_id] if v.get("version_id") != version_id
                ]
                self._save_version_history()

            logger.info(f"Versión eliminada: {version_id}")
            return True

        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.error(f"Error eliminando versión {version_id}: {e}")
            return False
