"""
Parameter Mapping Service - Maps optimization parameters to nested config structure.

Eliminates 4+ duplicate implementations across:
- profile_batch_backtester.py (140 lines)
- bayesian_optimizer.py (115 lines)
- optimization_validators.py (3 simplified versions)

This service handles the mapping between flat optimization parameters
and the nested YAML configuration structure used by strategies.
"""

import copy
from typing import Dict, List, Optional, Union

from app.backtesting.shared.types import ConfigKeys

# Type alias for nested configuration dictionaries
ConfigDict = Dict[str, Union[int, float, str, bool, "ConfigDict", List[Union[int, float, str, bool, "ConfigDict"]]]]
ParamValue = Union[int, float]
ParamDict = Dict[str, ParamValue]


class ParameterMappingService:
    """
    Maps optimization parameters to nested strategy configuration structure.

    The optimization produces flat parameters like:
        {
            "rsi_threshold": 25,
            "ema_short": 9,
            "ema_long": 35,
            "volume_threshold": 1.35,
            "stop_loss": 0.014,
            "take_profit": 0.126
        }

    Which need to be mapped to nested config structure:
        {
            "strategy": {
                "modules": {
                    "rsi_filter": {"adaptive_thresholds": {"trend_up": {"buy_threshold": 25}}},
                    "ema_filter": {"parameters": {"fast_period": 9, "slow_period": 35}},
                    ...
                }
            }
        }
    """

    # RSI context types that should receive the same threshold
    RSI_CONTEXTS: List[str] = ["trend_up", "trend_down", "range", "high_vol"]

    # Volume preset types that should receive the same threshold
    VOLUME_PRESETS: List[str] = ["conservative", "balanced", "aggressive"]

    # Parameter to config path mappings
    PARAMETER_MAPPINGS: Dict[str, Dict[str, Union[List[str], str]]] = {
        "rsi_threshold": {
            "path": ["modules", "rsi_filter", "adaptive_thresholds"],
            "contexts": RSI_CONTEXTS,
            "key": "buy_threshold",
        },
        "ema_short": {
            "path": ["modules", "ema_filter", "parameters"],
            "key": "fast_period",
        },
        "ema_long": {
            "path": ["modules", "ema_filter", "parameters"],
            "key": "slow_period",
        },
        "volume_threshold": {
            "path": ["modules", "volume_filter", "thresholds"],
            "contexts": VOLUME_PRESETS,
            "key": "min_volume_ratio",
        },
        "stop_loss": {
            "path": ["risk_manager", "stop_loss", "fixed_percentage"],
            "key": "value",
        },
        "take_profit": {
            "path": ["risk_manager", "take_profit", "fixed_percentage"],
            "key": "value",
        },
    }

    @classmethod
    def map_params_to_strategy_config(
        cls,
        params: ParamDict,
        base_config: Optional[ConfigDict] = None,
    ) -> ConfigDict:
        """
        Map optimization parameters to nested strategy configuration.

        Args:
            params: Flat optimization parameters from Optuna
            base_config: Optional base config to update (deep copied)

        Returns:
            Strategy config dict with mapped parameters
        """
        # Deep copy base config to avoid mutations
        config: ConfigDict = copy.deepcopy(base_config) if base_config else {}
        strategy = config.get(ConfigKeys.STRATEGY, {})

        # Ensure modules structure exists
        if ConfigKeys.MODULES not in strategy:
            strategy[ConfigKeys.MODULES] = {}

        # Map each parameter
        for param_name, param_value in params.items():
            if param_value is None:
                continue

            mapping = cls.PARAMETER_MAPPINGS.get(param_name)
            if mapping:
                cls._apply_mapping(strategy, mapping, param_value)
            else:
                # Unknown parameter - log warning but continue
                import logging

                logging.getLogger(__name__).debug(f"Unknown optimization parameter: {param_name}")

        config[ConfigKeys.STRATEGY] = strategy
        return config

    @classmethod
    def _apply_mapping(cls, strategy: ConfigDict, mapping: Dict[str, Union[List[str], str]], value: ParamValue) -> None:
        """
        Apply a parameter mapping to the strategy config.

        Args:
            strategy: Strategy config dict to update (mutated in place)
            mapping: Mapping definition from PARAMETER_MAPPINGS
            value: Parameter value to set
        """
        path = mapping["path"]
        key = mapping["key"]
        contexts = mapping.get("contexts")

        # Navigate/create path
        current = strategy
        for path_part in path:
            if path_part not in current:
                current[path_part] = {}
            current = current[path_part]

        # Set value(s)
        if contexts:
            # Set value for multiple contexts
            for context in contexts:
                if context not in current:
                    current[context] = {}
                current[context][key] = value
        else:
            # Set single value
            current[key] = value

    @classmethod
    def map_rsi_threshold(cls, strategy: ConfigDict, rsi_threshold: float) -> None:
        """
        Map RSI threshold to all adaptive threshold contexts.

        Args:
            strategy: Strategy config dict to update
            rsi_threshold: RSI buy threshold value
        """
        mapping = cls.PARAMETER_MAPPINGS["rsi_threshold"]
        cls._apply_mapping(strategy, mapping, rsi_threshold)

    @classmethod
    def map_ema_periods(cls, strategy: ConfigDict, ema_short: int, ema_long: int) -> None:
        """
        Map EMA periods to filter parameters.

        Args:
            strategy: Strategy config dict to update
            ema_short: Fast EMA period
            ema_long: Slow EMA period
        """
        if ema_short is not None:
            mapping = cls.PARAMETER_MAPPINGS["ema_short"]
            cls._apply_mapping(strategy, mapping, ema_short)
        if ema_long is not None:
            mapping = cls.PARAMETER_MAPPINGS["ema_long"]
            cls._apply_mapping(strategy, mapping, ema_long)

    @classmethod
    def map_volume_threshold(cls, strategy: ConfigDict, volume_threshold: float) -> None:
        """
        Map volume threshold to all presets.

        Args:
            strategy: Strategy config dict to update
            volume_threshold: Minimum volume ratio
        """
        mapping = cls.PARAMETER_MAPPINGS["volume_threshold"]
        cls._apply_mapping(strategy, mapping, volume_threshold)

    @classmethod
    def map_risk_params(
        cls, strategy: ConfigDict, stop_loss: float, take_profit: float
    ) -> None:
        """
        Map risk management parameters.

        Args:
            strategy: Strategy config dict to update
            stop_loss: Stop loss percentage (e.g., 0.02 for 2%)
            take_profit: Take profit percentage (e.g., 0.10 for 10%)
        """
        if stop_loss is not None:
            mapping = cls.PARAMETER_MAPPINGS["stop_loss"]
            cls._apply_mapping(strategy, mapping, stop_loss)
        if take_profit is not None:
            mapping = cls.PARAMETER_MAPPINGS["take_profit"]
            cls._apply_mapping(strategy, mapping, take_profit)

    @classmethod
    def convert_to_yaml_updater_format(cls, params: ParamDict) -> ConfigDict:
        """
        Convert optimization params to YAMLConfigUpdater format.

        Used for persisting optimized parameters to YAML config files.

        Args:
            params: Flat optimization parameters

        Returns:
            Nested dict in YAMLConfigUpdater format
        """
        return {
            "filters": {
                "rsi_filter": {
                    "adaptive_thresholds": {
                        ctx: {"buy_threshold": params.get("rsi_threshold", 30)}
                        for ctx in cls.RSI_CONTEXTS
                    }
                },
                "ema_filter": {
                    "parameters": {
                        "fast_period": params.get("ema_short", 12),
                        "slow_period": params.get("ema_long", 26),
                    }
                },
                "volume_filter": {
                    "thresholds": {
                        preset: {"min_volume_ratio": params.get("volume_threshold", 1.2)}
                        for preset in cls.VOLUME_PRESETS
                    }
                },
            },
            "strategies": {
                "momentum_modular": {
                    "risk_manager": {
                        "stop_loss": {"fixed_percentage": {"value": params.get("stop_loss", 0.02)}},
                        "take_profit": {
                            "fixed_percentage": {"value": params.get("take_profit", 0.10)}
                        },
                    }
                }
            },
        }


# Convenience function for backward compatibility
def map_params_to_config(
    params: ParamDict, base_config: Optional[ConfigDict] = None
) -> ConfigDict:
    """
    Convenience function for backward compatibility.

    Replaces duplicated parameter mapping code across the codebase.
    """
    return ParameterMappingService.map_params_to_strategy_config(params, base_config)
