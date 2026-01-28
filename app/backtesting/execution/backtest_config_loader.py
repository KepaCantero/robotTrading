"""
Backtest Config Loader - Loads and validates backtest configurations

This module is responsible for loading backtest configurations from
YAML files and validating them according to business rules.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


class BacktestConfigLoader:
    """
    Loads and validates backtest configurations from YAML files.

    This class is responsible for:
    - Loading YAML configuration files
    - Validating required fields
    - Providing default values
    - Merging with base configurations
    """

    DEFAULT_CONFIG = {
        'input': {
            'start_date': '2020-01-01',
            'end_date': '2023-12-31',
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
        },
        'strategy': {
            'name': 'momentum_modular',
            'parameters': {},
        },
        'capital': {
            'initial': 100000,
            'currency': 'USD',
        },
        'risk': {
            'max_position_size': 0.10,
            'stop_loss': 0.03,
            'take_profit': 0.06,
        },
        'execution': {
            'commission': 0.001,
            'slippage': 0.0001,
        },
        'reporting': {
            'output_directory': 'results',
            'save_results': True,
        },
        'parallelization': {
            'enabled': True,
            'max_workers': None,
        },
        'meta_analysis': {
            'enabled': False,
            'enable_audit': True,
            'enable_storage': True,
            'enable_analysis': True,
        },
    }

    def __init__(self, config_path: str):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.raw_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Merge with defaults
            merged_config = self._merge_with_defaults(config)
            logger.info(f"Loaded configuration from {self.config_path}")
            return merged_config

        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded config with defaults.

        Args:
            config: Loaded configuration

        Returns:
            Merged configuration
        """
        merged = self.DEFAULT_CONFIG.copy()

        for key, value in config.items():
            if key in merged and isinstance(merged[key], dict):
                merged[key].update(value)
            else:
                merged[key] = value

        return merged

    def get_backtest_config(self) -> Dict[str, Any]:
        """
        Get backtest-specific configuration.

        Returns:
            Backtest configuration dictionary
        """
        return {
            'strategy_name': self.raw_config.get('strategy', {}).get('name', ''),
            'strategy_params': self.raw_config.get('strategy', {}).get('parameters', {}),
            'symbols': self.raw_config.get('input', {}).get('symbols', []),
            'start_date': self.raw_config.get('input', {}).get('start_date'),
            'end_date': self.raw_config.get('input', {}).get('end_date'),
            'initial_capital': self.raw_config.get('capital', {}).get('initial', 100000),
            'max_position_size': self.raw_config.get('risk', {}).get('max_position_size', 0.10),
            'stop_loss': self.raw_config.get('risk', {}).get('stop_loss', 0.03),
            'take_profit': self.raw_config.get('risk', {}).get('take_profit', 0.06),
            'commission': self.raw_config.get('execution', {}).get('commission', 0.001),
            'slippage': self.raw_config.get('execution', {}).get('slippage', 0.0001),
            'output_directory': self.raw_config.get('reporting', {}).get(
                'output_directory', 'results'
            ),
        }

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate required fields
        required_fields = ['input', 'strategy', 'capital']
        for field in required_fields:
            if field not in self.raw_config:
                errors.append(f"Missing required field: {field}")

        # Validate input section
        if 'input' in self.raw_config:
            input_config = self.raw_config['input']
            if 'symbols' not in input_config or not input_config['symbols']:
                errors.append("Input must have at least one symbol")

        # Validate strategy section
        if 'strategy' in self.raw_config:
            strategy_config = self.raw_config['strategy']
            if 'name' not in strategy_config or not strategy_config['name']:
                errors.append("Strategy must have a name")

        # Validate capital section
        if 'capital' in self.raw_config:
            capital_config = self.raw_config['capital']
            initial_capital = capital_config.get('initial', 0)
            if initial_capital <= 0:
                errors.append("Initial capital must be positive")

        return errors

    def is_valid(self) -> bool:
        """
        Check if configuration is valid.

        Returns:
            True if configuration is valid
        """
        return len(self.validate()) == 0
