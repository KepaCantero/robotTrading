"""
YAML Configuration Loader

Carga configuraciones desde archivos YAML con validación y fallback a valores por defecto.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class YAMLConfigLoader:
    """
    Cargador de configuraciones YAML con validación y soporte para defaults.

    Features:
    - Carga segura de YAML (yaml.safe_load)
    - Fallback a valores por defecto si el archivo no existe
    - Soporte para anidación de claves con notación de puntos
    - Logging de configuración cargada
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Inicializa el cargador de configuración.

        Args:
            config_dir: Directorio de configuración. Por defecto: config/
        """
        self.config_dir = config_dir or Path("config")
        self._cache: Dict[str, Any] = {}

    def load(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Carga un archivo YAML desde el directorio de configuración.

        Args:
            filename: Nombre del archivo YAML (ej: "strategy_stock_allocator.yaml")
            use_cache: Si True, usa caché para archivos ya cargados

        Returns:
            Diccionario con el contenido del YAML

        Raises:
            FileNotFoundError: Si el archivo no existe y no hay fallback
            yaml.YAMLError: Si el archivo tiene formato inválido
        """
        cache_key = filename

        if use_cache and cache_key in self._cache:
            logger.debug(f"Loading {filename} from cache")
            return self._cache[cache_key]

        config_path = self.config_dir / filename

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {}

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}

            self._cache[cache_key] = config
            logger.info(f"Loaded config from {config_path}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML from {config_path}: {e}")
            return {}

    def get_nested(
        self,
        config: Dict[str, Any],
        key_path: str,
        default: Any = None,
        separator: str = ".",
    ) -> Any:
        """
        Obtiene un valor anidado usando notación de puntos.

        Args:
            config: Diccionario de configuración
            key_path: Ruta de la clave (ej: "data_validation.lookback_max_days")
            default: Valor por defecto si la clave no existe
            separator: Separador de claves (por defecto: ".")

        Returns:
            Valor de la clave o default si no existe

        Examples:
            >>> loader.get_nested(config, "data_validation.lookback_max_days", 126)
            126
        """
        keys = key_path.split(separator)
        value = config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def load_with_tier_override(
        self,
        filename: str,
        tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Carga configuración con overrides por capital tier.

        Args:
            filename: Nombre del archivo YAML
            tier: Capital tier ("micro", "small", "medium", "large")

        Returns:
            Diccionario con configuración base + overrides del tier

        Examples:
            >>> loader.load_with_tier_override("strategy_stock_allocator.yaml", "micro")
            {
                "data_validation": {"lookback_max_days": 126, ...},
                "exposure": {"max_strategy_exposure": 0.30, ...},  # Overridden
                ...
            }
        """
        config = self.load(filename)

        if tier and "tiers" in config and tier in config["tiers"]:
            tier_overrides = config["tiers"][tier]

            # Apply tier overrides recursively
            config = self._apply_overrides(config, tier_overrides)
            logger.info(f"Applied {tier} tier overrides to config")

        return config

    def _apply_overrides(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica overrides recursivamente a la configuración base.

        Args:
            base: Configuración base
            overrides: Overrides a aplicar

        Returns:
            Configuración con overrides aplicados
        """
        result = base.copy()

        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._apply_overrides(result[key], value)
            else:
                result[key] = value

        return result

    def get_strategy_stock_allocator_config(self, tier: Optional[str] = None) -> Dict[str, Any]:
        """
        Carga la configuración del Strategy Stock Allocator.

        Args:
            tier: Capital tier para aplicar overrides

        Returns:
            Configuración completa del Strategy Stock Allocator
        """
        return self.load_with_tier_override("strategy_stock_allocator.yaml", tier)

    def clear_cache(self) -> None:
        """Limpia la caché de configuraciones."""
        self._cache.clear()
        logger.debug("Config cache cleared")


# Singleton instance for easy access
_default_loader: Optional[YAMLConfigLoader] = None


def get_config_loader() -> YAMLConfigLoader:
    """
    Obtiene la instancia singleton del cargador de configuración.

    Returns:
        Instancia de YAMLConfigLoader
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = YAMLConfigLoader()
    return _default_loader


def load_strategy_stock_allocator_config(
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para cargar la configuración del Strategy Stock Allocator.

    Args:
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración completa del Strategy Stock Allocator
    """
    return get_config_loader().get_strategy_stock_allocator_config(tier)


def load_momentum_filters_config(
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para cargar la configuración de Momentum Filters.

    Args:
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración completa de Momentum Filters
    """
    return get_config_loader().load_with_tier_override("momentum_filters.yaml", tier)


def load_market_detectors_config(
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para cargar la configuración de Market Detectors.

    Args:
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración completa de Market Detectors
    """
    return get_config_loader().load_with_tier_override("market_detectors.yaml", tier)


def load_strategy_defaults_config(
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para cargar la configuración de Strategy Defaults.

    Args:
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración completa de Strategy Defaults
    """
    return get_config_loader().load_with_tier_override("strategy_defaults.yaml", tier)


def load_learning_parameters_config(
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de conveniencia para cargar la configuración de Learning Parameters.

    Args:
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración completa de Learning Parameters
    """
    return get_config_loader().load_with_tier_override("learning_parameters.yaml", tier)


def get_filter_config(
    filter_name: str,
    tier: Optional[str] = None,
    preset: str = "balanced",
) -> Dict[str, Any]:
    """
    Obtiene la configuración de un filtro específico desde momentum_filters.yaml.

    Args:
        filter_name: Nombre del filtro (ej: "rsi_filter", "momentum_filter")
        tier: Capital tier para aplicar overrides
        preset: Preset a usar ("conservative", "balanced", "aggressive")

    Returns:
        Configuración del filtro con thresholds del preset
    """
    config = load_momentum_filters_config(tier)

    # Obtener configuración específica del filtro
    filter_config = config.get(filter_name, {})

    # Añadir thresholds del preset
    thresholds = filter_config.get("thresholds", {})
    preset_thresholds = thresholds.get(preset, thresholds.get("balanced", {}))

    result = filter_config.copy()
    result["preset_thresholds"] = preset_thresholds

    return result


def get_detector_config(
    detector_name: str,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Obtiene la configuración de un detector específico desde market_detectors.yaml.

    Args:
        detector_name: Nombre del detector (ej: "trend_detector", "volatility_detector")
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración del detector
    """
    config = load_market_detectors_config(tier)
    return config.get(detector_name, {})


def get_strategy_config(
    strategy_name: str,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Obtiene la configuración de una estrategia específica desde strategy_defaults.yaml.

    Args:
        strategy_name: Nombre de la estrategia (ej: "momentum_strategy", "mean_reversion_strategy")
        tier: Capital tier para aplicar overrides

    Returns:
        Configuración de la estrategia
    """
    config = load_strategy_defaults_config(tier)
    return config.get(strategy_name, {})
