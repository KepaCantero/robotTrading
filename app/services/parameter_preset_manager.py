"""
Parameter Preset Manager - TASK-PARAM-1

Manages and loads parameter presets (Conservative/Aggressive/Balanced)
with sensible ranges per indicator (TASK-PARAM-3).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ParameterPresetManager:
    """
    Parameter Preset Manager - TASK-PARAM-1

    Loads and manages parameter presets from configuration file,
    providing access to Conservative, Moderate, and Aggressive presets
    with sensible indicator ranges (TASK-PARAM-3).
    """

    def __init__(self, config_path: str = "config/parameter_presets.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load preset configuration from YAML."""
        if not self.config_path.exists():
            logger.warning(f"Preset config not found: {self.config_path}")
            return

        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded parameter presets from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading preset config: {e}")

    def get_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific preset.

        Args:
            preset_name: Name of preset (conservative, moderate, aggressive)

        Returns:
            Preset configuration dictionary or None
        """
        presets = self.config.get("presets", {})
        return presets.get(preset_name.lower())

    def get_strategy_params(self, preset_name: str, strategy_name: str) -> Dict[str, Any]:
        """
        Get parameters for a specific strategy within a preset.

        Args:
            preset_name: Name of preset
            strategy_name: Name of strategy (momentum, mean_reversion, pairs_trading)

        Returns:
            Strategy parameters dictionary
        """
        preset = self.get_preset(preset_name)
        if not preset:
            return {}

        return preset.get(strategy_name, {})

    def get_indicator_range(self, indicator_name: str) -> Dict[str, Any]:
        """
        Get sensible range for an indicator - TASK-PARAM-3.

        Args:
            indicator_name: Name of indicator (rsi, atr_multiplier, volume_ratio, etc.)

        Returns:
            Range dictionary with min, max, default values
        """
        ranges = self.config.get("indicator_ranges", {})
        return ranges.get(indicator_name, {})

    def get_all_presets(self) -> List[str]:
        """Get list of available preset names."""
        presets = self.config.get("presets", {})
        return list(presets.keys())

    def get_preset_description(self, preset_name: str) -> str:
        """Get description for a preset."""
        preset = self.get_preset(preset_name)
        return preset.get("description", "") if preset else ""

    def validate_parameter_in_range(
        self, indicator_name: str, value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that a parameter value is within sensible range - TASK-PARAM-3.

        Args:
            indicator_name: Name of indicator
            value: Parameter value to validate

        Returns:
            (is_valid, error_message)
        """
        range_config = self.get_indicator_range(indicator_name)
        if not range_config:
            return True, None  # No range defined, assume valid

        min_val = range_config.get("min")
        max_val = range_config.get("max")

        if min_val is not None and value < min_val:
            return False, f"{indicator_name} value {value} below minimum {min_val}"

        if max_val is not None and value > max_val:
            return False, f"{indicator_name} value {value} above maximum {max_val}"

        return True, None


# Global instance
_preset_manager: Optional[ParameterPresetManager] = None


def get_preset_manager() -> ParameterPresetManager:
    """Get global preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = ParameterPresetManager()
    return _preset_manager
