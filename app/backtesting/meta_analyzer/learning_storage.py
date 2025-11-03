"""
LearningEngineStorage - Persistencia de pesos de modelos para aprendizaje incremental.

Permite guardar y cargar pesos de learning engines para:
- Continuar entrenamiento
- Compartir modelos entre tests
- Aprendizaje incremental
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Optional, List, Dict
from datetime import datetime
import asyncio

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class LearningEngineStorage:
    """
    Sistema de almacenamiento para pesos de learning engines.
    
    Soporta múltiples formatos:
    - PyTorch (.pt, .pth)
    - Pickle (.pkl)
    - NumPy (.npy) - futuro
    """
    
    def __init__(self, base_dir: str = "models/learning_engines"):
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
        format: Optional[str] = None
    ) -> str:
        """
        Guardar pesos de un learning engine.
        
        Args:
            engine_name: Nombre del engine (ej: 'supervised', 'deep', 'transformer')
            weights: Pesos a guardar (modelo, dict, tensor, etc.)
            test_id: Identificador único del test
            metadata: Metadatos adicionales (timestamp, métricas, etc.)
            format: Formato ('pt', 'pkl', 'auto') - auto detecta según tipo
        
        Returns:
            Ruta del archivo guardado
        """
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
                if not TORCH_AVAILABLE:
                    raise ImportError("PyTorch no disponible para guardar .pt")
                torch.save({
                    'weights': weights,
                    'metadata': metadata or {},
                    'engine_name': engine_name,
                    'test_id': test_id,
                    'timestamp': timestamp
                }, file_path)
            elif format == 'pkl':
                with open(file_path, 'wb') as f:
                    pickle.dump({
                        'weights': weights,
                        'metadata': metadata or {},
                        'engine_name': engine_name,
                        'test_id': test_id,
                        'timestamp': timestamp
                    }, f)
            else:
                raise ValueError(f"Formato no soportado: {format}")
            
            logger.info(f"✅ Pesos guardados: {file_path}")
            
            # Guardar metadatos adicionales
            if metadata:
                metadata_path = file_path.with_suffix('.metadata.json')
                self._save_metadata(metadata_path, metadata)
            
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Error guardando pesos: {e}", exc_info=True)
            raise
    
    async def save_weights_async(
        self,
        engine_name: str,
        weights: Any,
        test_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None
    ) -> str:
        """
        Guardar pesos de forma asíncrona (para I/O-bound).
        
        Args:
            engine_name: Nombre del engine
            weights: Pesos a guardar
            test_id: Identificador único del test
            metadata: Metadatos adicionales
            format: Formato ('pt', 'pkl', 'auto')
        
        Returns:
            Ruta del archivo guardado
        """
        # Para guardado asíncrono, primero serializar en memoria
        # Luego escribir el archivo de forma asíncrona
        
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
            if not TORCH_AVAILABLE:
                raise ImportError("PyTorch no disponible")
            # PyTorch no tiene API asíncrona directa, usar en thread
            data = {
                'weights': weights,
                'metadata': metadata or {},
                'engine_name': engine_name,
                'test_id': test_id,
                'timestamp': timestamp
            }
            # Guardar de forma bloqueante (en thread separado si es necesario)
            torch.save(data, file_path)
        elif format == 'pkl':
            # Serializar primero
            import io
            buffer = io.BytesIO()
            pickle.dump({
                'weights': weights,
                'metadata': metadata or {},
                'engine_name': engine_name,
                'test_id': test_id,
                'timestamp': timestamp
            }, buffer)
            buffer.seek(0)
            
            # Escribir de forma asíncrona
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(buffer.read())
            else:
                # Fallback síncrono
                with open(file_path, 'wb') as f:
                    f.write(buffer.read())
        else:
            raise ValueError(f"Formato no soportado: {format}")
        
        logger.info(f"✅ Pesos guardados (async): {file_path}")
        
        return str(file_path)
    
    def load_weights(
        self,
        engine_name: str,
        test_id: Optional[str] = None,
        latest: bool = True
    ) -> Dict[str, Any]:
        """
        Cargar pesos de un learning engine.
        
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
        
        # Buscar archivo
        if test_id:
            # Buscar por test_id
            files = list(engine_dir.glob(f"{test_id}_*.pt")) + \
                   list(engine_dir.glob(f"{test_id}_*.pth")) + \
                   list(engine_dir.glob(f"{test_id}_*.pkl"))
        else:
            # Buscar todos los archivos
            files = list(engine_dir.glob("*.pt")) + \
                   list(engine_dir.glob("*.pth")) + \
                   list(engine_dir.glob("*.pkl"))
        
        if not files:
            raise FileNotFoundError(f"No se encontraron pesos para {engine_name} (test_id={test_id})")
        
        # Si latest y múltiples archivos, obtener el más reciente
        if latest and len(files) > 1:
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        file_path = files[0]
        
        # Cargar según extensión
        try:
            if file_path.suffix in ['.pt', '.pth']:
                if not TORCH_AVAILABLE:
                    raise ImportError("PyTorch no disponible para cargar .pt")
                data = torch.load(file_path, map_location='cpu')
            elif file_path.suffix == '.pkl':
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
            else:
                raise ValueError(f"Formato no soportado: {file_path.suffix}")
            
            logger.info(f"✅ Pesos cargados: {file_path}")
            
            return data
        
        except Exception as e:
            logger.error(f"Error cargando pesos: {e}", exc_info=True)
            raise
    
    def list_available_weights(
        self,
        engine_name: str,
        test_id_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Listar pesos disponibles para un engine.
        
        Args:
            engine_name: Nombre del engine
            test_id_filter: Filtrar por test_id (opcional)
        
        Returns:
            Lista de dicts con información de cada archivo
        """
        engine_dir = self.base_dir / engine_name
        
        if not engine_dir.exists():
            return []
        
        # Buscar archivos
        files = list(engine_dir.glob("*.pt")) + \
               list(engine_dir.glob("*.pth")) + \
               list(engine_dir.glob("*.pkl"))
        
        weights_info = []
        for file_path in files:
            # Extraer test_id del nombre
            filename = file_path.stem
            parts = filename.split('_')
            test_id = '_'.join(parts[:-1]) if len(parts) > 1 else parts[0]
            
            # Filtrar por test_id si se especifica
            if test_id_filter and test_id_filter not in test_id:
                continue
            
            stat = file_path.stat()
            weights_info.append({
                'file_path': str(file_path),
                'test_id': test_id,
                'format': file_path.suffix[1:],  # Sin el punto
                'size_bytes': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Ordenar por fecha de modificación (más reciente primero)
        weights_info.sort(key=lambda x: x['modified'], reverse=True)
        
        return weights_info
    
    def delete_weights(
        self,
        engine_name: str,
        test_id: Optional[str] = None,
        keep_latest: bool = True
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
            except Exception as e:
                logger.error(f"Error eliminando {info['file_path']}: {e}")
        
        logger.info(f"✅ Eliminados {deleted} archivos de pesos")
        
        return deleted
    
    def _detect_format(self, weights: Any) -> str:
        """Detectar formato óptimo según tipo de pesos."""
        if TORCH_AVAILABLE and isinstance(weights, (torch.nn.Module, torch.Tensor)):
            return 'pt'
        else:
            return 'pkl'  # Formato por defecto para cualquier objeto Python
    
    def _save_metadata(self, metadata_path: Path, metadata: Dict[str, Any]) -> None:
        """Guardar metadatos en JSON separado."""
        import json
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"No se pudieron guardar metadatos: {e}")

