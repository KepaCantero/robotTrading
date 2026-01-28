"""
YAML Config Updater - Actualiza archivos YAML con parámetros optimizados.

Crea backups automáticos antes de modificar y mantiene un historial de cambios.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class YAMLConfigUpdater:
    """
    Actualiza archivos YAML de configuración con parámetros optimizados.

    Funcionalidades:
    - Backup automático con timestamp antes de modificar
    - Actualización de filtros, detectores, estrategias
    - Soporte para tier-specific overrides
    - Historial de cambios
    - Validación de YAML antes y después
    """

    def __init__(self, config_dir: Path = Path("config"), backup_dir: Optional[Path] = None):
        """
        Inicializar updater.

        Args:
            config_dir: Directorio de configuración (default: "config")
            backup_dir: Directorio para backups (default: config/backups)
        """
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else self.config_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._change_history: list = []

        logger.info(
            f"YAMLConfigUpdater initialized: config_dir={self.config_dir}, backup_dir={self.backup_dir}"
        )

    # ========================================================================
    # UPDATE METHODS
    # ========================================================================

    def update_filter_thresholds(
        self,
        filter_name: str,
        optimized_params: Dict[str, float],
        tier: Optional[str] = None,
        preset: Optional[str] = None,
    ) -> bool:
        """
        Actualiza thresholds de filtros en momentum_filters.yaml.

        Args:
            filter_name: Nombre del filtro (ej: "rsi_filter", "momentum_filter")
            optimized_params: Parámetros optimizados {param_name: value}
            tier: Capital tier ("micro", "small", "medium", "large") si aplica
            preset: Preset ("balanced", "conservative", "aggressive") si aplica

        Returns:
            True si se actualizó correctamente
        """
        config_file = self.config_dir / "momentum_filters.yaml"

        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return False

        try:
            # Crear backup
            self._create_backup(config_file)

            # Cargar YAML
            with open(config_file) as f:
                config = yaml.safe_load(f)

            # Actualizar parámetros
            updated = False

            if tier:
                # Actualizar tier-specific overrides
                if "tiers" in config and tier in config["tiers"]:
                    tier_config = config["tiers"][tier]
                    if filter_name in tier_config:
                        if "thresholds" in tier_config[filter_name]:
                            tier_config[filter_name]["thresholds"].update(optimized_params)
                            updated = True
                            logger.info(f"Updated {filter_name} thresholds for tier={tier}")
            else:
                # Actualizar parámetros base
                if filter_name in config:
                    # Buscar sección de thresholds
                    if "thresholds" in config[filter_name]:
                        config[filter_name]["thresholds"].update(optimized_params)
                        updated = True
                        logger.info(f"Updated {filter_name} base thresholds")

            # Si no se encontró thresholds, crear la sección
            if not updated and filter_name in config:
                config[filter_name]["thresholds"] = optimized_params
                updated = True
                logger.info(f"Created thresholds section for {filter_name}")

            if not updated:
                logger.warning(f"Could not find {filter_name} in config")
                return False

            # Validar YAML
            self._validate_yaml(config)

            # Guardar
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            # Registrar cambio
            self._register_change(
                file=str(config_file),
                section=f"{filter_name}/thresholds",
                params=optimized_params,
                tier=tier,
            )

            logger.info(f"✅ Successfully updated {filter_name} in {config_file}")
            return True

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error updating {filter_name} thresholds: {e}", exc_info=True)
            return False

    def update_detector_params(
        self,
        detector_name: str,
        optimized_params: Dict[str, Any],
        tier: Optional[str] = None,
    ) -> bool:
        """
        Actualiza parámetros de detectores en market_detectors.yaml.

        Args:
            detector_name: Nombre del detector (ej: "trend_detector", "volatility_detector")
            optimized_params: Parámetros optimizados
            tier: Capital tier si aplica

        Returns:
            True si se actualizó correctamente
        """
        config_file = self.config_dir / "market_detectors.yaml"

        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return False

        try:
            self._create_backup(config_file)

            with open(config_file) as f:
                config = yaml.safe_load(f)

            updated = False

            if tier:
                if "tiers" in config and tier in config["tiers"]:
                    tier_config = config["tiers"][tier]
                    if detector_name in tier_config:
                        tier_config[detector_name].update(optimized_params)
                        updated = True
                        logger.info(f"Updated {detector_name} params for tier={tier}")
            else:
                if detector_name in config:
                    config[detector_name].update(optimized_params)
                    updated = True
                    logger.info(f"Updated {detector_name} base params")

            if not updated:
                logger.warning(f"Could not find {detector_name} in config")
                return False

            self._validate_yaml(config)

            with open(config_file, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            self._register_change(
                file=str(config_file), section=detector_name, params=optimized_params, tier=tier
            )

            logger.info(f"✅ Successfully updated {detector_name} in {config_file}")
            return True

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error updating {detector_name}: {e}", exc_info=True)
            return False

    def update_strategy_params(
        self,
        strategy_name: str,
        optimized_params: Dict[str, Any],
        tier: Optional[str] = None,
    ) -> bool:
        """
        Actualiza parámetros de estrategia en strategy_defaults.yaml.

        Args:
            strategy_name: Nombre de estrategia (ej: "momentum_strategy", "mean_reversion_strategy")
            optimized_params: Parámetros optimizados
            tier: Capital tier si aplica

        Returns:
            True si se actualizó correctamente
        """
        config_file = self.config_dir / "strategy_defaults.yaml"

        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return False

        try:
            self._create_backup(config_file)

            with open(config_file) as f:
                config = yaml.safe_load(f)

            updated = False

            if tier:
                if "tiers" in config and tier in config["tiers"]:
                    tier_config = config["tiers"][tier]
                    if strategy_name in tier_config:
                        tier_config[strategy_name].update(optimized_params)
                        updated = True
                        logger.info(f"Updated {strategy_name} params for tier={tier}")
            else:
                if strategy_name in config:
                    config[strategy_name].update(optimized_params)
                    updated = True
                    logger.info(f"Updated {strategy_name} base params")

            if not updated:
                logger.warning(f"Could not find {strategy_name} in config")
                return False

            self._validate_yaml(config)

            with open(config_file, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            self._register_change(
                file=str(config_file), section=strategy_name, params=optimized_params, tier=tier
            )

            logger.info(f"✅ Successfully updated {strategy_name} in {config_file}")
            return True

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error updating {strategy_name}: {e}", exc_info=True)
            return False

    def update_learning_params(
        self,
        section: str,
        optimized_params: Dict[str, Any],
        tier: Optional[str] = None,
    ) -> bool:
        """
        Actualiza parámetros de learning en learning_parameters.yaml.

        Args:
            section: Sección a actualizar (ej: "supervised_learning", "threshold_optimization")
            optimized_params: Parámetros optimizados
            tier: Capital tier si aplica

        Returns:
            True si se actualizó correctamente
        """
        config_file = self.config_dir / "learning_parameters.yaml"

        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return False

        try:
            self._create_backup(config_file)

            with open(config_file) as f:
                config = yaml.safe_load(f)

            updated = False

            if tier:
                if "tiers" in config and tier in config["tiers"]:
                    tier_config = config["tiers"][tier]
                    if section in tier_config:
                        tier_config[section].update(optimized_params)
                        updated = True
                        logger.info(f"Updated {section} learning params for tier={tier}")
            else:
                if section in config:
                    config[section].update(optimized_params)
                    updated = True
                    logger.info(f"Updated {section} base learning params")

            if not updated:
                # Crear sección si no existe
                config[section] = optimized_params
                updated = True
                logger.info(f"Created {section} section in learning params")

            self._validate_yaml(config)

            with open(config_file, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            self._register_change(
                file=str(config_file), section=section, params=optimized_params, tier=tier
            )

            logger.info(f"✅ Successfully updated {section} in {config_file}")
            return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error updating {section}: {e}", exc_info=True)
            return False

    # ========================================================================
    # BATCH UPDATE METHODS
    # ========================================================================

    def update_multiple_filters(
        self, filter_updates: Dict[str, Dict[str, float]], tier: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Actualiza múltiples filtros en una sola operación.

        Args:
            filter_updates: {filter_name: {param: value}}
            tier: Capital tier si aplica

        Returns:
            {filter_name: success}
        """
        results = {}

        for filter_name, params in filter_updates.items():
            results[filter_name] = self.update_filter_thresholds(filter_name, params, tier)

        logger.info(f"Batch filter update: {sum(results.values())}/{len(results)} successful")
        return results

    def update_from_optimization_results(
        self, optimization_results: Dict[str, Any], tier: Optional[str] = None
    ) -> bool:
        """
        Actualiza configs desde resultados de optimización completos.

        Expected format:
        {
            'filters': {filter_name: {param: value}},
            'detectors': {detector_name: {param: value}},
            'strategies': {strategy_name: {param: value}},
            'learning': {section: {param: value}}
        }

        Args:
            optimization_results: Resultados completos de optimización
            tier: Capital tier si aplica

        Returns:
            True si todas las actualizaciones fueron exitosas
        """
        all_success = True

        # Actualizar filtros
        if "filters" in optimization_results:
            results = self.update_multiple_filters(optimization_results["filters"], tier)
            if not all(results.values()):
                all_success = False

        # Actualizar detectores
        if "detectors" in optimization_results:
            for detector_name, params in optimization_results["detectors"].items():
                if not self.update_detector_params(detector_name, params, tier):
                    all_success = False

        # Actualizar estrategias
        if "strategies" in optimization_results:
            for strategy_name, params in optimization_results["strategies"].items():
                if not self.update_strategy_params(strategy_name, params, tier):
                    all_success = False

        # Actualizar learning params
        if "learning" in optimization_results:
            for section, params in optimization_results["learning"].items():
                if not self.update_learning_params(section, params, tier):
                    all_success = False

        if all_success:
            logger.info("✅ All optimization results successfully saved to YAML")
        else:
            logger.warning("⚠️ Some optimization results failed to save")

        return all_success

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _create_backup(self, file_path: Path) -> Path:
        """
        Crea backup del archivo con timestamp.

        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}.yaml"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        logger.debug(f"📦 Backup created: {backup_path}")

        return backup_path

    def _validate_yaml(self, config: Dict) -> bool:
        """
        Valida que la config YAML sea correcta.

        Returns:
            True si es válida
        """
        try:
            # Intentar convertir a YAML y volver a leer
            yaml_str = yaml.safe_dump(config)
            yaml.safe_load(yaml_str)
            return True
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"YAML validation failed: {e}")
            return False

    def _register_change(
        self, file: str, section: str, params: Dict, tier: Optional[str] = None
    ) -> None:
        """
        Registra un cambio en el historial.
        """
        change = {
            "timestamp": datetime.now().isoformat(),
            "file": file,
            "section": section,
            "tier": tier,
            "params": params,
        }

        self._change_history.append(change)

    def get_change_history(self) -> list:
        """Retorna el historial de cambios."""
        return self._change_history.copy()

    def save_change_history(self, output_path: Optional[Path] = None) -> Path:
        """
        Guarda el historial de cambios a archivo JSON.

        Args:
            output_path: Ruta de salida (default: config/backups/change_history.json)

        Returns:
            Ruta del archivo guardado
        """
        if output_path is None:
            output_path = self.backup_dir / "change_history.json"

        import json

        with open(output_path, "w") as f:
            json.dump(self._change_history, f, indent=2)

        logger.info(f"Change history saved to {output_path}")
        return output_path

    def list_backups(self) -> list:
        """Lista todos los backups disponibles."""
        backup_files = list(self.backup_dir.glob("*.yaml"))
        return sorted([f.name for f in backup_files])

    def restore_from_backup(self, backup_name: str, original_name: str) -> bool:
        """
        Restaura un archivo desde backup.

        Args:
            backup_name: Nombre del archivo backup
            original_name: Nombre del archivo original a restaurar

        Returns:
            True si se restauró correctamente
        """
        backup_path = self.backup_dir / backup_name
        original_path = self.config_dir / original_name

        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False

        try:
            shutil.copy2(backup_path, original_path)
            logger.info(f"Restored {original_name} from {backup_name}")
            return True
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
