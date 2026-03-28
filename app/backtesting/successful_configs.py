"""
Módulo para gestionar configuraciones exitosas de backtests.

Permite:
- Guardar configuraciones que han demostrado buena performance
- Cargar configuraciones guardadas para reutilizar
- Comparar configuraciones por métricas
- Gestionar historial de configuraciones exitosas
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SuccessfulConfigManager:
    """
    Gestiona configuraciones de backtests que han demostrado buena performance.
    """

    def __init__(self, storage_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Inicializar gestor de configuraciones exitosas.

        Args:
            storage_dir: Directorio donde guardar configuraciones (str o Path).
                Por defecto: config/successful_configs/
        """
        if storage_dir is None:
            self.storage_dir: Path = Path("config") / "successful_configs"
        else:
            self.storage_dir = Path(storage_dir) if isinstance(storage_dir, str) else storage_dir

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.configs_file = self.storage_dir / "successful_configs.json"
        self._configs = self._load_configs()

    def _load_configs(self) -> List[Dict[str, Any]]:
        """Cargar configuraciones guardadas desde disco."""
        if not self.configs_file.exists():
            return []

        try:
            with open(self.configs_file, 'r') as f:
                return json.load(f)
        except OSError as e:
            logger.warning(f"Error cargando configuraciones guardadas: {e}")
            return []

    def _save_configs(self) -> None:
        """Guardar configuraciones a disco."""
        try:
            with open(self.configs_file, 'w') as f:
                json.dump(self._configs, f, indent=2, default=str)
            logger.info(f"✅ Configuraciones guardadas: {len(self._configs)} configs")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error guardando configuraciones: {e}")

    def save_config(
        self,
        name: str,
        config: Dict[str, Any],
        metrics: Dict[str, Any],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        before_training_metrics: Optional[Dict[str, Any]] = None,
        after_training_metrics: Optional[Dict[str, Any]] = None,
        improvement_pct: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Guardar una configuración exitosa.

        Args:
            name: Nombre único para esta configuración
            config: Configuración completa del backtest (YAML como dict)
            metrics: Métricas de performance (sharpe, return, win_rate, etc.)
            description: Descripción opcional
            tags: Tags para categorizar (ej: ['momentum', 'supervised', 'high_sharpe'])
            before_training_metrics: Métricas antes del entrenamiento (baseline)
            after_training_metrics: Métricas después del entrenamiento
            improvement_pct: Mejora porcentual por métrica (ej: {'sharpe_ratio': 15.5, 'return_pct': 8.2})

        Returns:
            ID único de la configuración guardada
        """
        config_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        config_record = {
            'id': config_id,
            'name': name,
            'description': description or "",
            'tags': tags or [],
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'metrics': metrics,
            'before_training_metrics': before_training_metrics,
            'after_training_metrics': after_training_metrics,
            'improvement_pct': improvement_pct or {},
            # Métricas clave para filtrado/búsqueda
            'sharpe_ratio': metrics.get('sharpe_ratio'),
            'return_pct': metrics.get('return_pct'),
            'win_rate': metrics.get('win_rate'),
            'max_drawdown': metrics.get('max_drawdown'),
            'total_pnl': metrics.get('total_pnl'),
        }

        # Verificar si ya existe una configuración con el mismo nombre
        existing_idx = None
        for i, existing in enumerate(self._configs):
            if existing.get('name') == name:
                existing_idx = i
                break

        if existing_idx is not None:
            # Actualizar existente
            self._configs[existing_idx] = config_record
            logger.info(f"✅ Configuración '{name}' actualizada")
        else:
            # Agregar nueva
            self._configs.append(config_record)
            logger.info(f"✅ Nueva configuración guardada: '{name}' (ID: {config_id})")

        self._save_configs()

        # También guardar como archivo individual para fácil acceso
        config_file = self.storage_dir / f"{config_id}.json"
        with open(config_file, 'w') as f:
            json.dump(config_record, f, indent=2, default=str)

        return config_id

    def load_config(
        self, config_id: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cargar una configuración guardada.

        Args:
            config_id: ID de la configuración
            name: Nombre de la configuración (alternativa a config_id)

        Returns:
            Configuración guardada o None si no se encuentra
        """
        if config_id:
            for config in self._configs:
                if config.get('id') == config_id:
                    return config
        elif name:
            for config in self._configs:
                if config.get('name') == name:
                    return config

        logger.warning(f"Configuración no encontrada: id={config_id}, name={name}")
        return None

    def list_configs(
        self,
        min_sharpe: Optional[float] = None,
        min_return: Optional[float] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = 'sharpe_ratio',
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Listar configuraciones guardadas con filtros opcionales.

        Args:
            min_sharpe: Filtrar por Sharpe ratio mínimo
            min_return: Filtrar por return % mínimo
            tags: Filtrar por tags (debe contener todos)
            sort_by: Ordenar por ('sharpe_ratio', 'return_pct', 'win_rate', 'timestamp')
            limit: Límite de resultados

        Returns:
            Lista de configuraciones filtradas y ordenadas
        """
        filtered = self._configs.copy()

        # Filtrar por Sharpe
        if min_sharpe is not None:
            filtered = [
                c
                for c in filtered
                if c.get('sharpe_ratio') is not None and c.get('sharpe_ratio') >= min_sharpe
            ]

        # Filtrar por Return
        if min_return is not None:
            filtered = [
                c
                for c in filtered
                if c.get('return_pct') is not None and c.get('return_pct') >= min_return
            ]

        # Filtrar por tags
        if tags:
            filtered = [c for c in filtered if all(tag in c.get('tags', []) for tag in tags)]

        # Ordenar
        reverse = True  # Por defecto descendente
        if sort_by == 'timestamp':
            reverse = False  # Timestamp más reciente primero

        filtered.sort(
            key=lambda x: x.get(sort_by) or (0 if sort_by != 'timestamp' else ''), reverse=reverse
        )

        # Limitar
        if limit:
            filtered = filtered[:limit]

        return filtered

    def delete_config(self, config_id: Optional[str] = None, name: Optional[str] = None) -> bool:
        """
        Eliminar una configuración guardada.

        Args:
            config_id: ID de la configuración
            name: Nombre de la configuración

        Returns:
            True si se eliminó, False si no se encontró
        """
        removed = False
        for i, config in enumerate(self._configs):
            if (config_id and config.get('id') == config_id) or (
                name and config.get('name') == name
            ):
                self._configs.pop(i)
                removed = True
                break

        if removed:
            self._save_configs()
            # Eliminar archivo individual
            if config_id:
                config_file = self.storage_dir / f"{config_id}.json"
                if config_file.exists():
                    config_file.unlink()
            logger.info(f"✅ Configuración eliminada: id={config_id}, name={name}")
        else:
            logger.warning(
                f"Configuración no encontrada para eliminar: id={config_id}, name={name}"
            )

        return removed

    def get_config_for_runner(
        self, config_id: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener configuración en formato para ComprehensiveBacktestRunner.

        Args:
            config_id: ID de la configuración
            name: Nombre de la configuración

        Returns:
            Configuración lista para usar en runner o None
        """
        config_record = self.load_config(config_id=config_id, name=name)
        if not config_record:
            return None

        # Extraer solo la configuración (sin metadatos)
        return config_record.get('config')

    def compare_configs(self, config_id1: str, config_id2: str) -> Dict[str, Any]:
        """
        Comparar dos configuraciones guardadas.

        Args:
            config_id1: ID de la primera configuración
            config_id2: ID de la segunda configuración

        Returns:
            Dict con comparación de métricas
        """
        config1 = self.load_config(config_id=config_id1)
        config2 = self.load_config(config_id=config_id2)

        if not config1 or not config2:
            return {'error': 'Una o ambas configuraciones no encontradas'}

        metrics1 = config1.get('metrics', {})
        metrics2 = config2.get('metrics', {})

        comparison = {
            'config1': {'name': config1.get('name'), 'id': config1.get('id'), 'metrics': metrics1},
            'config2': {'name': config2.get('name'), 'id': config2.get('id'), 'metrics': metrics2},
            'differences': {},
        }

        # Calcular diferencias para métricas numéricas
        numeric_metrics = [
            'sharpe_ratio',
            'return_pct',
            'win_rate',
            'max_drawdown',
            'total_pnl',
            'sortino_ratio',
        ]
        for metric in numeric_metrics:
            val1 = metrics1.get(metric)
            val2 = metrics2.get(metric)
            if val1 is not None and val2 is not None:
                diff = val2 - val1
                diff_pct = (diff / abs(val1) * 100) if val1 != 0 else 0
                comparison['differences'][metric] = {
                    'absolute': diff,
                    'percentage': diff_pct,
                    'winner': config1.get('name') if diff < 0 else config2.get('name'),
                }

        return comparison
