"""
Backtest Configuration Module
Handles configuration creation and management for different backtest types.

This module was extracted from comprehensive_backtest_runner.py (lines 3343-3550)
as part of the Clean Architecture refactoring initiative.

Responsibilities:
- Create strategy configurations from YAML
- Extract filter and threshold configurations
- Generate parameter grids for optimization
- Create backtest-specific configurations

Clean Architecture Layer: Use Case / Application Business Rules
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from app.backtesting.core import BacktestConfig
from app.backtesting.data_loader import DataLoader
from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

logger = logging.getLogger(__name__)


class BacktestConfigFactory:
    """
    Factory for creating backtest configurations.

    Centralizes configuration logic and ensures consistency
    across different backtest types. This class follows the
    Factory pattern to create complex configuration objects.

    Examples:
        >>> factory = BacktestConfigFactory(raw_config)
        >>> strategy_config = factory.create_strategy_config()
        >>> ablation_config = factory.create_ablation_config('rsi_filter')
    """

    def __init__(self, raw_config: Dict[str, Any]):
        """
        Initialize factory with raw YAML configuration.

        Args:
            raw_config: Dictionary from loaded YAML configuration file
        """
        self.raw_config = raw_config

    def create_strategy_config(self) -> Dict[str, Any]:
        """
        Create base strategy configuration from YAML.

        Builds the complete strategy configuration including:
        - Strategy type (modular_momentum)
        - Enabled filters with their parameters
        - Presets (combination mode, min confidence)

        Returns:
            Dictionary with complete strategy configuration
        """
        return {
            'type': 'modular_momentum',
            'preset': 'custom',
            'modules': self.get_filter_config(),
            'presets': {
                'custom': {
                    'combination_mode': 'MAJORITY',
                    'min_confidence': 0.7,
                    'learning_mode': 'supervised'
                }
            }
        }

    def create_strategy_config_for_type(
        self,
        strategy_name: str,
        strategy_mapping
    ) -> Dict[str, Any]:
        """
        Create strategy configuration for specific strategy type.

        Handles different strategy types with their specific
        configuration requirements. Maps YAML strategy names
        to factory names and applies type-specific settings.

        Args:
            strategy_name: Name of strategy from YAML config
            strategy_mapping: Strategy mapping object with risk profile

        Returns:
            Dictionary with strategy-specific configuration

        Raises:
            ValueError: If strategy name is not recognized
        """
        # Map YAML names to factory names
        STRATEGY_NAME_MAP = {
            'momentum_modular': 'modular_momentum',
            'mean_reversion_modular': 'mean_reversion',
            'pairs_trading_modular': 'pairs_trading',
            'dividend_screener': 'modular_momentum',
            'portfolio_optimization': 'modular_momentum',
        }

        mapped_strategy_name = STRATEGY_NAME_MAP.get(
            strategy_name,
            'modular_momentum'  # Default fallback
        )

        # Build base configuration
        base_config = {
            "type": mapped_strategy_name,
            "symbols": self.raw_config.get("input", {}).get("symbols", []),
            "parameters": {
                "risk_profile": getattr(strategy_mapping, 'risk_profile', 'moderate'),
                "leverage": getattr(strategy_mapping, 'leverage', 1.0),
                "max_position_size": getattr(
                    strategy_mapping,
                    'max_position_size',
                    0.2
                ),
                "max_sector_allocation": getattr(
                    strategy_mapping,
                    'max_sector_allocation',
                    0.3
                ),
            },
            "thresholds": {
                "buy_threshold": 0.7,
                "sell_threshold": 0.3,
                "stop_loss": -0.05,
                "take_profit": 0.10,
            },
        }

        # Add type-specific configuration
        if strategy_name == "momentum_modular":
            base_config.update({
                "preset": "custom",
                "modules": self.get_filter_config(),
                "presets": {
                    "custom": {
                        "combination_mode": "MAJORITY",
                        "min_confidence": 0.7,
                    }
                },
            })
        elif strategy_name == "mean_reversion_modular":
            base_config["parameters"].update({
                "lookback_period": 20,
                "entry_threshold": 2.0,
                "exit_threshold": 0.5,
            })
        elif strategy_name == "dividend_screener":
            base_config["parameters"].update({
                "min_dividend_yield": 0.03,
                "max_payout_ratio": 0.8,
                "min_growth_rate": 0.05,
            })

        return base_config

    def create_ablation_config(self, disabled_filter: str) -> Dict[str, Any]:
        """
        Create strategy configuration with specific filter disabled.

        Used for ablation testing to measure the impact of individual
        filters by disabling them one at a time.

        Args:
            disabled_filter: Name of filter to disable

        Returns:
            Strategy configuration dictionary with filter disabled
        """
        if 'modules' not in self.raw_config or 'filters' not in self.raw_config['modules']:
            logger.warning("No filter configuration found, returning base config")
            return self.create_strategy_config()

        # Build filters config excluding disabled filter
        filters_config = {}
        filters = self.raw_config['modules']['filters']

        for filter_name, filter_config in filters.items():
            # Skip the disabled filter
            if filter_name == disabled_filter:
                logger.debug(f"Disabling filter: {filter_name}")
                continue

            if filter_config.get('enabled', False):
                # Extract default parameters
                filter_params = {
                    param_name: param_config['default']
                    for param_name, param_config in filter_config.get('parameters', {}).items()
                    if 'default' in param_config
                }

                filters_config[filter_name] = {
                    'enabled': True,
                    **filter_params
                }

        return {
            'type': 'modular_momentum',
            'preset': 'custom',
            'modules': filters_config,
            'presets': {
                'custom': {
                    'combination_mode': 'MAJORITY',
                    'min_confidence': 0.7,
                    'learning_mode': 'supervised'
                }
            }
        }

    def create_input_profile_from_config(self):
        """
        Create InputProfile from configuration.

        Extracts profile settings from YAML config for use
        in profile-based trading strategies.

        Returns:
            InputProfile object with profile settings
        """
        # Import here to avoid circular dependency
        from app.services.profile_driven_trading.profiles import (
            InputProfile,
            ObjetivoInversion,
            RiskTolerance,
        )

        profile_config = self.raw_config.get('profile', {})

        return InputProfile(
            objetivo_inversion=ObjetivoInversion(
                profile_config.get('objetivo', 'crecimiento')
            ),
            risk_tolerance=RiskTolerance(
                profile_config.get('risk_tolerance', 'moderado')
            ),
            capital_tier=profile_config.get('capital_tier', 'tier_3'),
            investment_horizon=profile_config.get('horizon', 'medio_plazo'),
        )

    def get_filter_config(self) -> Dict[str, Any]:
        """
        Get filter configuration from YAML.

        Extracts enabled filters and their default parameters
        from the configuration file.

        Returns:
            Dictionary with filter configurations
        """
        filters_config = {}

        if "modules" in self.raw_config and "filters" in self.raw_config["modules"]:
            filters = self.raw_config["modules"]["filters"]

            for filter_name, filter_config in filters.items():
                if filter_config.get("enabled", False):
                    # Extract default parameters
                    filter_params = {}
                    for param_name, param_config in filter_config.get(
                        "parameters", {}
                    ).items():
                        if "default" in param_config:
                            filter_params[param_name] = param_config["default"]

                    filters_config[filter_name] = {
                        "enabled": True,
                        **filter_params
                    }

        return filters_config

    def extract_thresholds(
        self,
        strategy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract thresholds from strategy configuration.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Dictionary with threshold values
        """
        return strategy_config.get('thresholds', {})

    def get_strategy_name(self, strategy: Any) -> str:
        """
        Get strategy name for logging and reporting.

        Args:
            strategy: Strategy instance

        Returns:
            Strategy name as string
        """
        if hasattr(strategy, '__class__'):
            return strategy.__class__.__name__
        return type(strategy).__name__

    def create_backtest_config(self) -> BacktestConfig:
        """
        Create BacktestConfig object from YAML configuration.

        Returns:
            BacktestConfig object with all settings
        """
        from decimal import Decimal

        input_config = self.raw_config.get('input', {})
        backtest_config = self.raw_config.get('backtest_config', {})

        return BacktestConfig(
            initial_capital=Decimal(str(input_config.get('initial_capital', 100000))),
            commission_per_trade=Decimal(str(
                backtest_config.get('commission_per_trade', 0.001)
            )),
            slippage_percentage=Decimal(str(
                backtest_config.get('slippage_percentage', 0.0001)
            )),
            max_position_size=Decimal(str(
                backtest_config.get('max_position_size', 0.2)
            )),
            stop_loss_percentage=Decimal(str(
                backtest_config.get('stop_loss_percentage', 0.05)
            )),
            take_profit_percentage=Decimal(str(
                backtest_config.get('take_profit_percentage', 0.10)
            )),
            risk_free_rate=float(backtest_config.get('risk_free_rate', 0.02)),
        )

    def get_monte_carlo_config(self) -> Dict[str, Any]:
        """
        Get Monte Carlo specific configuration.

        Returns:
            Dictionary with Monte Carlo settings
        """
        return self.raw_config.get('backtests', {}).get('monte_carlo', {
            'enabled': False,
            'num_simulations': 100,
            'volatility_multiplier': {'default': 1.0}
        })

    def get_walk_forward_config(self) -> Dict[str, Any]:
        """
        Get walk-forward specific configuration.

        Returns:
            Dictionary with walk-forward settings
        """
        return self.raw_config.get('backtests', {}).get('walk_forward', {
            'enabled': False,
            'train_pct': 0.70,
            'test_pct': 0.30,
            'min_train_days': 252,
            'step_size_days': 63
        })

    def get_grid_search_config(self) -> Dict[str, Any]:
        """
        Get grid search specific configuration.

        Returns:
            Dictionary with grid search settings
        """
        return self.raw_config.get('backtests', {}).get('grid_search', {
            'enabled': False,
            'param_grid': {}
        })

    def get_regime_test_config(self) -> Dict[str, Any]:
        """
        Get regime test specific configuration.

        Returns:
            Dictionary with regime test settings
        """
        return self.raw_config.get('backtests', {}).get('regime_test', {
            'enabled': False,
            'detection_method': 'hmm',
            'n_regimes': 3,
            'min_regime_samples': 50
        })


class MonteCarloDataGenerator:
    """
    Generates realistic data for Monte Carlo simulations.

    Uses the RealisticDataGenerator to create Monte Carlo scenarios
    with realistic market characteristics including volatility
    clustering and regime switching.
    """

    def create_monte_carlo_quotes(
        self,
        base_quotes: List,
        volatility_multiplier: float = 1.0,
        random_state: int = 42
    ) -> List:
        """
        Create Monte Carlo quotes with realistic volatility.

        Replaces simplistic random shocks with realistic market data
        generation using GARCH models and regime switching.

        Args:
            base_quotes: Base quotes to use as template
            volatility_multiplier: Multiplier for volatility
            random_state: Random seed for reproducibility

        Returns:
            List of realistically generated quotes
        """
        from app.models.market_data import DataFeedType, Quote
        from app.backtesting.realistic_data_generator import RealisticDataGenerator

        # If no base quotes, generate new data
        if not base_quotes:
            logger.warning("No base quotes available, generating new data")
            gen = RealisticDataGenerator(
                seed=random_state,
                base_price=100.0,
                base_volume=50_000_000,
            )
            from datetime import datetime
            start_date = datetime.now()
            return gen.generate_realistic_quotes(
                symbol='SYNTH',
                n_days=252,
                start_date=start_date,
                use_regime_switching=True,
            )

        # Use realistic generator for Monte Carlo scenarios
        gen = RealisticDataGenerator(
            seed=random_state,
            base_price=float(base_quotes[0].close),
            base_volume=int(base_quotes[0].volume) if base_quotes[0].volume else 50_000_000,
        )

        from datetime import datetime
        start_date = base_quotes[0].timestamp if base_quotes else datetime.now()

        modified_quotes = gen.generate_realistic_quotes(
            symbol=base_quotes[0].symbol if base_quotes else 'SYNTH',
            n_days=len(base_quotes),
            start_date=start_date,
            use_regime_switching=True,
            initial_regime='volatile',  # Use volatile regime for Monte Carlo
        )

        logger.info(
            f"Generated {len(modified_quotes)} realistic Monte Carlo quotes "
            f"(replacing simplistic random shocks)"
        )

        return modified_quotes


class ParameterGridGenerator:
    """
    Generates parameter grids for hyperparameter optimization.

    Creates all combinations of parameters for grid search
    and provides default parameter grids for common strategies.
    """

    def generate_parameter_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from grid.

        Args:
            param_grid: Dictionary mapping parameter names to value lists

        Returns:
            List of parameter dictionaries, one per combination

        Example:
            >>> generator = ParameterGridGenerator()
            >>> grid = {'a': [1, 2], 'b': [3, 4]}
            >>> combinations = generator.generate_parameter_combinations(grid)
            >>> # Returns: [{'a': 1, 'b': 3}, {'a': 1, 'b': 4},
            >>> #           {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]
        """
        from itertools import product

        if not param_grid:
            return [{}]

        param_names = list(param_grid.keys())
        param_value_lists = list(param_grid.values())

        combinations = []
        for combination in product(*param_value_lists):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)

        return combinations

    def create_default_param_grid(self) -> Dict[str, List[float]]:
        """
        Create default parameter grid for momentum strategy.

        Returns:
            Dictionary with default parameter ranges
        """
        return {
            'buy_threshold': [0.60, 0.70, 0.80, 0.90],
            'sell_threshold': [0.10, 0.20, 0.30, 0.40],
            'stop_loss': [-0.03, -0.05, -0.07, -0.10],
            'take_profit': [0.05, 0.10, 0.15, 0.20],
            'min_confidence': [0.5, 0.6, 0.7, 0.8, 0.9],
        }
