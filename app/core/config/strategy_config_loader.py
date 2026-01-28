"""
Strategy Configuration Loader
Centralized loader for accessing strategy, risk, and capital tier configuration.

This module provides:
- Loading of indicator thresholds (RSI, MA, ATR, etc.)
- Loading of risk management parameters (stop loss, take profit, position sizing)
- Loading of capital tier configurations
- Type-safe access to configuration values
- Fallback values for missing configuration
- Convenience methods for common parameter access

Usage:
    from app.core.config.strategy_config_loader import get_strategy_config

    config = get_strategy_config()

    # Get RSI thresholds
    rsi_period = config.get_rsi_period()
    rsi_oversold = config.get_rsi_threshold('extreme_low')
    rsi_overbought = config.get_rsi_threshold('extreme_high')

    # Get position sizing
    max_position = config.get_max_position_size(tier='medium')
    default_position = config.get_default_position_size(tier='medium')

    # Get risk parameters
    stop_loss = config.get_stop_loss(strategy='momentum')
    take_profit = config.get_take_profit(strategy='momentum')
"""

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class StrategyConfigLoader:
    """
    Load strategy configuration from YAML files.

    This class provides centralized access to all strategy-related configuration,
    including indicators, risk management, and capital tier settings.

    Features:
    - Load from YAML config files
    - Type conversion (Decimal for financial values)
    - Tier-specific overrides
    - Strategy-specific overrides
    - Fallback values for missing config
    - Caching for performance
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the strategy config loader.

        Args:
            config_dir: Directory containing config files.
                       Defaults to project root /config/
        """
        if config_dir is None:
            # Assume we're in the project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = config_dir
        self._cache: Dict[str, Any] = {}

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load a YAML configuration file.

        Args:
            filename: Name of the YAML file (without path)

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if filename in self._cache:
            return self._cache[filename]

        config_path = self.config_dir / filename

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {}

        try:
            import yaml

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}

            self._cache[filename] = config
            return config

        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}

    def _get_nested(self, data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """
        Get a nested value from a dictionary using dot notation.

        Args:
            data: Source dictionary
            key_path: Dot-separated path to the value (e.g., "rsi.thresholds.extreme_low")
            default: Default value if key not found

        Returns:
            Value at key path or default
        """
        keys = key_path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    # ========================================================================
    # INDICATOR CONFIGURATION
    # ========================================================================

    def get_indicator_config(self) -> Dict[str, Any]:
        """Load indicator configuration from indicators.yaml."""
        return self._load_yaml("indicators.yaml")

    def get_rsi_period(self, variant: str = "default") -> int:
        """
        Get RSI period.

        Args:
            variant: Period variant (default, short, long)

        Returns:
            RSI period value
        """
        config = self.get_indicator_config()
        return self._get_nested(config, f"rsi.period.{variant}", 14)

    def get_rsi_threshold(self, threshold: str) -> int:
        """
        Get RSI threshold value.

        Args:
            threshold: Threshold name (extreme_low, extreme_high, buy_signal, sell_signal)

        Returns:
            RSI threshold value

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_rsi_threshold('extreme_low')
            30
            >>> config.get_rsi_threshold('extreme_high')
            70
        """
        config = self.get_indicator_config()
        return self._get_nested(config, f"rsi.thresholds.{threshold}", 30)

    def get_rsi_adaptive_threshold(self, market_type: str, threshold_type: str) -> int:
        """
        Get adaptive RSI threshold for market type.

        Args:
            market_type: Market regime (balanced, volatile, trending, etc.)
            threshold_type: Type of threshold (buy_threshold, sell_threshold)

        Returns:
            RSI threshold value

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_rsi_adaptive_threshold('volatile', 'buy_threshold')
            25
        """
        config = self.get_indicator_config()
        return self._get_nested(
            config,
            f"rsi.adaptive.{market_type}.{threshold_type}",
            30
        )

    def get_ma_period(self, length: str = "medium") -> int:
        """
        Get moving average period.

        Args:
            length: Period length (very_short, short, medium, long, very_long)

        Returns:
            MA period value
        """
        config = self.get_indicator_config()
        return self._get_nested(config, f"moving_averages.periods.{length}", 20)

    def get_atr_period(self, variant: str = "default") -> int:
        """
        Get ATR period.

        Args:
            variant: Period variant (default, short, long)

        Returns:
            ATR period value
        """
        config = self.get_indicator_config()
        return self._get_nested(config, f"atr.period.{variant}", 14)

    def get_atr_multiplier(self, variant: str = "default_stop") -> float:
        """
        Get ATR multiplier for stop loss calculation.

        Args:
            variant: Multiplier variant (tight_stop, default_stop, wide_stop)

        Returns:
            ATR multiplier value

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_atr_multiplier('default_stop')
            2.0
        """
        config = self.get_indicator_config()
        return float(self._get_nested(config, f"atr.multipliers.{variant}", 2.0))

    # ========================================================================
    # RISK MANAGEMENT CONFIGURATION
    # ========================================================================

    def get_risk_config(self) -> Dict[str, Any]:
        """Load risk management configuration from risk_management.yaml."""
        return self._load_yaml("risk_management.yaml")

    def get_position_sizing(
        self,
        tier: str = "medium",
        variant: str = "default"
    ) -> Decimal:
        """
        Get position sizing as percentage of capital.

        Args:
            tier: Capital tier (micro, small, medium, large)
            variant: Sizing variant (default, max, min)

        Returns:
            Position size as Decimal (0-1 range)

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_position_sizing('medium', 'default')
            Decimal('0.10')
        """
        config = self.get_risk_config()

        # Try tier-specific first
        value = self._get_nested(
            config,
            f"position_sizing.by_tier.{tier}.default_percent",
            None
        )

        if value is None:
            # Fall back to general variant
            value = self._get_nested(
                config,
                f"position_sizing.{variant}.percent",
                0.10
            )

        return Decimal(str(value))

    def get_max_position_size(self, tier: str = "medium") -> Decimal:
        """
        Get maximum position size for a tier.

        Args:
            tier: Capital tier (micro, small, medium, large)

        Returns:
            Maximum position size as Decimal (0-1 range)
        """
        config = self.get_risk_config()
        value = self._get_nested(
            config,
            f"position_sizing.by_tier.{tier}.max_percent",
            0.25
        )
        return Decimal(str(value))

    def get_stop_loss(
        self,
        strategy: str = "momentum",
        variant: str = "default"
    ) -> Decimal:
        """
        Get stop loss percentage.

        Args:
            strategy: Strategy name (momentum, mean_reversion, pairs_trading)
            variant: Variant (tight, default, wide)

        Returns:
            Stop loss percentage as Decimal (0-1 range)

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_stop_loss('momentum', 'default')
            Decimal('0.05')
        """
        config = self.get_risk_config()
        value = self._get_nested(
            config,
            f"stop_loss.by_strategy.{strategy}.{variant}",
            0.05
        )
        return Decimal(str(value))

    def get_take_profit(
        self,
        strategy: str = "momentum",
        variant: str = "default"
    ) -> Decimal:
        """
        Get take profit percentage.

        Args:
            strategy: Strategy name (momentum, mean_reversion, pairs_trading)
            variant: Variant (conservative, default, aggressive)

        Returns:
            Take profit percentage as Decimal (0-1 range)

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_take_profit('momentum', 'default')
            Decimal('0.08')
        """
        config = self.get_risk_config()
        value = self._get_nested(
            config,
            f"take_profit.by_strategy.{strategy}.{variant}",
            0.10
        )
        return Decimal(str(value))

    def get_risk_reward_ratio(self, strategy: str = "momentum") -> float:
        """
        Get minimum risk/reward ratio for a strategy.

        Args:
            strategy: Strategy name

        Returns:
            Risk/reward ratio (e.g., 2.0 means 2:1)
        """
        config = self.get_risk_config()
        return float(
            self._get_nested(
                config,
                f"risk_reward.by_strategy.{strategy}.min_ratio",
                2.0
            )
        )

    def get_max_leverage(self, tier: str = "medium") -> float:
        """
        Get maximum leverage for a tier.

        Args:
            tier: Capital tier

        Returns:
            Maximum leverage multiplier
        """
        config = self.get_risk_config()
        return float(
            self._get_nested(
                config,
                f"leverage.max_leverage.{tier}",
                1.0
            )
        )

    # ========================================================================
    # CAPITAL TIER CONFIGURATION
    # ========================================================================

    def get_tier_config(self) -> Dict[str, Any]:
        """Load capital tier configuration from capital_tiers.yaml."""
        return self._load_yaml("capital_tiers.yaml")

    def get_tier_thresholds(self) -> Dict[str, int]:
        """
        Get capital tier thresholds.

        Returns:
            Dictionary mapping tier names to minimum capital values

        Examples:
            >>> config = StrategyConfigLoader()
            >>> thresholds = config.get_tier_thresholds()
            >>> thresholds['micro']
            0
            >>> thresholds['small']
            15000
        """
        config = self.get_tier_config()
        thresholds = config.get('thresholds', {})

        return {
            'micro': 0,
            'small': thresholds.get('micro_small', 15000),
            'medium': thresholds.get('small_medium', 50000),
            'large': thresholds.get('medium_large', 250000),
            'institutional': thresholds.get('large_institutional', 1000000),
        }

    def get_tier_from_capital(self, capital: Union[int, float, Decimal]) -> str:
        """
        Determine tier from capital amount.

        Args:
            capital: Capital amount in EUR

        Returns:
            Tier name (micro, small, medium, large, institutional)

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_tier_from_capital(10000)
            'micro'
            >>> config.get_tier_from_capital(100000)
            'medium'
        """
        capital_decimal = Decimal(str(capital))
        thresholds = self.get_tier_config().get('tiers', {})

        # Use min_capital thresholds for proper tier determination
        small_min = Decimal(str(thresholds.get('small', {}).get('min_capital', 15000)))
        medium_min = Decimal(str(thresholds.get('medium', {}).get('min_capital', 50000)))
        large_min = Decimal(str(thresholds.get('large', {}).get('min_capital', 250000)))
        institutional_min = Decimal(str(thresholds.get('institutional', {}).get('min_capital', 1000000)))

        if capital_decimal < small_min:
            return 'micro'
        elif capital_decimal < medium_min:
            return 'small'
        elif capital_decimal < large_min:
            return 'medium'
        elif capital_decimal < institutional_min:
            return 'large'
        else:
            return 'institutional'

    def get_tier_config_value(self, tier: str, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value for a specific tier.

        Args:
            tier: Tier name
            key_path: Dot-separated path to the value
            default: Default value if not found

        Returns:
            Configuration value

        Examples:
            >>> config = StrategyConfigLoader()
            >>> config.get_tier_config_value('medium', 'max_positions')
            10
        """
        config = self.get_tier_config()
        return self._get_nested(config, f"tiers.{tier}.{key_path}", default)

    def get_max_positions(self, tier: str = "medium") -> int:
        """Get maximum number of positions for a tier."""
        return self.get_tier_config_value(tier, 'max_positions', 10)

    def get_enabled_strategies(self, tier: str = "medium") -> list:
        """Get list of enabled strategies for a tier."""
        return self.get_tier_config_value(tier, 'enabled_strategies', ['momentum_strategy'])

    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================

    def reload_config(self):
        """Clear cache and reload configuration."""
        self._cache.clear()
        logger.info("Strategy configuration cache cleared")

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as a single dictionary.

        Returns:
            Combined configuration from all files
        """
        return {
            'indicators': self.get_indicator_config(),
            'risk_management': self.get_risk_config(),
            'capital_tiers': self.get_tier_config(),
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_config_loader: Optional[StrategyConfigLoader] = None


def get_strategy_config(config_dir: Optional[Path] = None) -> StrategyConfigLoader:
    """
    Get the global strategy configuration loader instance.

    Args:
        config_dir: Optional config directory (uses default if None)

    Returns:
        StrategyConfigLoader instance

    Examples:
        >>> from app.core.config.strategy_config_loader import get_strategy_config
        >>> config = get_strategy_config()
        >>> rsi_period = config.get_rsi_period()
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = StrategyConfigLoader(config_dir)

    return _config_loader


def reload_strategy_config():
    """Reload the global configuration loader."""
    global _config_loader
    if _config_loader is not None:
        _config_loader.reload_config()
