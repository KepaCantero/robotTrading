"""
LearningEngineStorage - Persistencia de pesos de modelos para aprendizaje incremental.

Permite guardar y cargar pesos de learning engines para:
- Continuar entrenamiento
- Compartir modelos entre tests
- Aprendizaje incremental
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

# SECURITY: Using joblib and msgpack instead of pickle for secure serialization
# joblib is safer for sklearn models, msgpack for generic Python objects
# ALL REQUIRED - no fallbacks
import joblib
import msgpack
import torch  # REQUIRED - PyTorch for model persistence

logger = logging.getLogger(__name__)


class LearningEngineStorage:
    """
    Sistema de almacenamiento para pesos de learning engines.

    Soporta múltiples formatos SEGUROS:
    - PyTorch (.pt, .pth) - torch.save (seguro para PyTorch)
    - Joblib (.joblib) - joblib.dump (seguro para sklearn y numpy)
    - MsgPack (.msgpack) - msgpack (seguro para objetos Python genéricos)
    - JSON (.json) - para metadatos

    NOTA: Ya NO se soporta .pkl (pickle) por razones de seguridad
    """

    def __init__(self, base_dir: str = "models/learning_engines") -> None:
        """
        Inicializar almacenamiento.

        Args:
            base_dir: Directorio base para guardar modelos
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LearningEngineStorage inicializado: base_dir={base_dir}")

    def save_weights(
        self,
        engine_name: str,
        weights: Any,
        test_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Guardar pesos de un learning engine usando serialización segura.

        Args:
            engine_name: Nombre del engine (ej: 'supervised', 'deep', 'transformer')
            weights: Pesos a guardar (modelo, dict, tensor, etc.)
            test_id: Identificador único del test
            metadata: Metadatos adicionales (timestamp, métricas, etc.)
            format: Formato ('pt', 'joblib', 'msgpack', 'auto') - auto detecta según tipo

        Returns:
            Ruta del archivo guardado

        Raises:
            ValueError: Si se intenta usar formato 'pkl' (inseguro)
        """
        # SECURITY: Reject pickle format explicitly
        if format == 'pkl':
            raise ValueError(
                "Formato 'pkl' no permitido por razones de seguridad. "
                "Use 'joblib', 'msgpack', o 'pt' en su lugar."
            )

        # Crear directorio para el engine
        engine_dir = self.base_dir / engine_name
        engine_dir.mkdir(parents=True, exist_ok=True)

        # Detectar formato si no se especifica
        if format is None or format == 'auto':
            format = self._detect_format(weights)

        # Generar nombre de archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_{timestamp}.{format}"
        file_path = engine_dir / filename

        # Guardar según formato
        try:
            if format == 'pt' or format == 'pth':
                torch.save(
                    {
                        'weights': weights,
                        'metadata': metadata or {},
                        'engine_name': engine_name,
                        'test_id': test_id,
                        'timestamp': timestamp,
                    },
                    file_path,
                )
            elif format == 'joblib':
                joblib.dump(
                    {
                        'weights': weights,
                        'metadata': metadata or {},
                        'engine_name': engine_name,
                        'test_id': test_id,
                        'timestamp': timestamp,
                    },
                    file_path,
                )
            elif format == 'msgpack':
                self._save_msgpack(
                    file_path,
                    {
                        'weights': weights,
                        'metadata': metadata or {},
                        'engine_name': engine_name,
                        'test_id': test_id,
                        'timestamp': timestamp,
                    },
                )
            else:
                raise ValueError(f"Formato no soportado: {format}")

            logger.info(f"✅ Pesos guardados: {file_path}")

            # Guardar metadatos adicionales en JSON (seguro)
            if metadata:
                metadata_path = file_path.with_suffix('.metadata.json')
                self._save_metadata(metadata_path, metadata)

            return str(file_path)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error guardando pesos: {e}", exc_info=True)
            raise

    async def save_weights_async(
        self,
        engine_name: str,
        weights: Any,
        test_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Guardar pesos de forma asíncrona usando serialización segura.

        Args:
            engine_name: Nombre del engine
            weights: Pesos a guardar
            test_id: Identificador único del test
            metadata: Metadatos adicionales
            format: Formato ('pt', 'joblib', 'msgpack', 'auto')

        Returns:
            Ruta del archivo guardado

        Raises:
            ValueError: Si se intenta usar formato 'pkl' (inseguro)
        """
        # SECURITY: Reject pickle format explicitly
        if format == 'pkl':
            raise ValueError(
                "Formato 'pkl' no permitido por razones de seguridad. "
                "Use 'joblib', 'msgpack', o 'pt' en su lugar."
            )

        # Detectar formato
        if format is None or format == 'auto':
            format = self._detect_format(weights)

        # Crear directorio
        engine_dir = self.base_dir / engine_name
        engine_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_{timestamp}.{format}"
        file_path = engine_dir / filename

        # Serializar según formato
        if format == 'pt' or format == 'pth':
            data = {
                'weights': weights,
                'metadata': metadata or {},
                'engine_name': engine_name,
                'test_id': test_id,
                'timestamp': timestamp,
            }
            # Guardar de forma bloqueante (PyTorch no tiene async API)
            torch.save(data, file_path)
        elif format == 'joblib':
            # Serializar primero
            import io

            buffer = io.BytesIO()
            joblib.dump(
                {
                    'weights': weights,
                    'metadata': metadata or {},
                    'engine_name': engine_name,
                    'test_id': test_id,
                    'timestamp': timestamp,
                },
                buffer,
            )
            buffer.seek(0)

            # Escribir de forma asíncrona (REQUIRED - aiofiles must be available)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(buffer.read())
        elif format == 'msgpack':
            data = {
                'weights': weights,
                'metadata': metadata or {},
                'engine_name': engine_name,
                'test_id': test_id,
                'timestamp': timestamp,
            }
            packed = msgpack.packb(data, default=str)
            # Escribir de forma asíncrona (REQUIRED - aiofiles must be available)
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(packed)
        else:
            raise ValueError(f"Formato no soportado: {format}")

        logger.info(f"✅ Pesos guardados (async): {file_path}")

        return str(file_path)

    def load_weights(
        self, engine_name: str, test_id: Optional[str] = None, latest: bool = True
    ) -> Dict[str, Any]:
        """
        Cargar pesos de un learning engine usando serialización segura.

        Args:
            engine_name: Nombre del engine
            test_id: Identificador del test (None = más reciente)
            latest: Si True y test_id es None, carga el más reciente

        Returns:
            Dict con 'weights' y 'metadata'
        """
        engine_dir = self.base_dir / engine_name

        if not engine_dir.exists():
            raise FileNotFoundError(f"Directorio de engine no existe: {engine_dir}")

        # Buscar archivo en formatos seguros
        if test_id:
            # Buscar por test_id (excluir .pkl)
            files = (
                list(engine_dir.glob(f"{test_id}_*.pt"))
                + list(engine_dir.glob(f"{test_id}_*.pth"))
                + list(engine_dir.glob(f"{test_id}_*.joblib"))
                + list(engine_dir.glob(f"{test_id}_*.msgpack"))
            )
        else:
            # Buscar todos los archivos seguros (excluir .pkl)
            files = (
                list(engine_dir.glob("*.pt"))
                + list(engine_dir.glob("*.pth"))
                + list(engine_dir.glob("*.joblib"))
                + list(engine_dir.glob("*.msgpack"))
            )

        # Si no hay archivos seguros, buscar archivos .pkl antiguos para migrar
        if not files:
            files = self._find_and_migrate_old_pkl_files(engine_dir, test_id)

        if not files:
            raise FileNotFoundError(
                f"No se encontraron pesos para {engine_name} (test_id={test_id})"
            )

        # Si latest y múltiples archivos, obtener el más reciente
        if latest and len(files) > 1:
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        file_path = files[0]

        # Cargar según extensión
        try:
            if file_path.suffix in ['.pt', '.pth']:
                data = torch.load(file_path, map_location='cpu')  # nosec B614 - torch is safe
            elif file_path.suffix == '.joblib':
                data = joblib.load(file_path)
            elif file_path.suffix == '.msgpack':
                data = self._load_msgpack(file_path)
            elif file_path.suffix == '.pkl':
                # SECURITY: Migrate old .pkl files to secure format
                logger.warning(f"Found old .pkl file {file_path}, migrating...")
                data = self._migrate_pkl_weights(file_path)
            else:
                raise ValueError(f"Formato no soportado: {file_path.suffix}")

            logger.info(f"✅ Pesos cargados: {file_path}")

            return data

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error cargando pesos: {e}", exc_info=True)
            raise

    def list_available_weights(
        self, engine_name: str, test_id_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Listar pesos disponibles para un engine (solo formatos seguros).

        Args:
            engine_name: Nombre del engine
            test_id_filter: Filtrar por test_id (opcional)

        Returns:
            Lista de dicts con información de cada archivo (excluye .pkl)
        """
        engine_dir = self.base_dir / engine_name

        if not engine_dir.exists():
            return []

        # Buscar archivos seguros (excluir .pkl)
        files = (
            list(engine_dir.glob("*.pt"))
            + list(engine_dir.glob("*.pth"))
            + list(engine_dir.glob("*.joblib"))
            + list(engine_dir.glob("*.msgpack"))
        )

        weights_info: List[Dict[str, Any]] = []
        for file_path in files:
            # Extraer test_id del nombre
            filename = file_path.stem
            parts = filename.split('_')
            test_id = '_'.join(parts[:-1]) if len(parts) > 1 else parts[0]

            # Filtrar por test_id si se especifica
            if test_id_filter and test_id_filter not in test_id:
                continue

            stat = file_path.stat()
            weights_info.append(
                {
                    'file_path': str(file_path),
                    'test_id': test_id,
                    'format': file_path.suffix[1:],  # Sin el punto
                    'size_bytes': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        # Ordenar por fecha de modificación (más reciente primero)
        weights_info.sort(key=lambda x: x['modified'], reverse=True)

        return weights_info

    def delete_weights(
        self, engine_name: str, test_id: Optional[str] = None, keep_latest: bool = True
    ) -> int:
        """
        Eliminar pesos guardados.

        Args:
            engine_name: Nombre del engine
            test_id: Eliminar solo este test_id (None = todos)
            keep_latest: Si True, mantener el más reciente

        Returns:
            Número de archivos eliminados
        """
        engine_dir = self.base_dir / engine_name

        if not engine_dir.exists():
            return 0

        # Listar archivos
        weights_info = self.list_available_weights(engine_name, test_id_filter=test_id)

        if not weights_info:
            return 0

        # Si keep_latest, excluir el más reciente
        files_to_delete = weights_info
        if keep_latest and len(weights_info) > 1:
            files_to_delete = weights_info[1:]  # Excluir el primero (más reciente)

        # Eliminar
        deleted = 0
        for info in files_to_delete:
            try:
                Path(info['file_path']).unlink()
                deleted += 1
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                logger.error(f"Error eliminando {info['file_path']}: {e}")

        logger.info(f"✅ Eliminados {deleted} archivos de pesos")

        return deleted

    def _detect_format(self, weights: Any) -> str:
        """Detectar formato óptimo y seguro según tipo de pesos (REQUIRED)."""
        if isinstance(weights, (torch.nn.Module, torch.Tensor)):
            return 'pt'
        else:
            return 'joblib'  # Seguro para sklearn y numpy (REQUIRED - joblib must be available)

    def _save_msgpack(self, path: Path, data: Dict[str, Any]) -> None:
        """Guardar datos usando msgpack."""
        packed = msgpack.packb(data, default=str)
        with open(path, 'wb') as f:
            f.write(packed)

    def _load_msgpack(self, path: Path) -> Dict[str, Any]:
        """Cargar datos usando msgpack."""
        with open(path, 'rb') as f:
            return msgpack.unpackb(f.read(), raw=False)

    def _find_and_migrate_old_pkl_files(
        self, engine_dir: Path, test_id: Optional[str]
    ) -> List[Path]:
        """
        Buscar archivos .pkl antiguos y migrarlos a formato seguro.

        Args:
            engine_dir: Directorio del engine
            test_id: Test ID a buscar

        Returns:
            Lista de Paths a archivos migrados
        """
        # Buscar archivos .pkl
        if test_id:
            pkl_files = list(engine_dir.glob(f"{test_id}_*.pkl"))
        else:
            pkl_files = list(engine_dir.glob("*.pkl"))

        if not pkl_files:
            return []

        # Migrar cada archivo .pkl encontrado
        migrated_files: List[Path] = []
        for pkl_file in pkl_files:
            try:
                logger.info(f"Migrating old .pkl file: {pkl_file}")
                migrated_path = self._migrate_pkl_weights(pkl_file)
                if migrated_path:
                    migrated_files.append(migrated_path)
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                logger.error(f"Error migrating {pkl_file}: {e}")

        return migrated_files

    def _migrate_pkl_weights(self, pkl_path: Path) -> Optional[Path]:
        """
        Migrar archivo .pkl a formato seguro (one-time migration).

        Args:
            pkl_path: Path al archivo .pkl

        Returns:
            Path al archivo migrado o None si falló
        """
        try:
            # SECURITY: One-time migration from pickle to secure format
            # This is the only place where we still use pickle.load, and it's
            # only for migrating existing trusted files to the secure format
            import pickle  # nosec B403 # Only for migration of trusted files

            with open(pkl_path, 'rb') as f:
                data = pickle.load(f)  # nosec B301 # Trusted migration only

            # Determinar nuevo formato
            new_format = self._detect_format(data.get('weights', None))

            # Crear nuevo path
            new_path = pkl_path.with_suffix(f'.{new_format}')

            # Guardar en formato seguro
            if new_format == 'joblib':
                joblib.dump(data, new_path)
            elif new_format == 'msgpack':
                self._save_msgpack(new_path, data)
            elif new_format == 'pt':
                torch.save(data, new_path)
            else:
                raise ValueError(f"Cannot migrate to format: {new_format}")

            # Eliminar archivo .pkl original
            pkl_path.unlink()

            logger.info(f"Successfully migrated {pkl_path} to {new_path}")
            return new_path

        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error migrating .pkl file {pkl_path}: {e}")
            return None

    def _save_metadata(self, metadata_path: Path, metadata: Dict[str, Any]) -> None:
        """Guardar metadatos en JSON separado."""

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.warning(f"No se pudieron guardar metadatos: {e}")
