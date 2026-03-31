"""
PHASE 0 - Account Configuration (T0.4)

Provides pre-configured settings and recommendations for different account
capital tiers. Each tier has optimal settings for position sizing, risk
management, and feature enablement.

Tiers:
- Micro (<$15k): Conservative, minimal features, small positions
- Small ($15k-$50k): Cautious, selective feature enabling
- Medium ($50k-$250k): Balanced, most features enabled
- Large ($250k+): Aggressive, all features available
"""

from __future__ import annotations

import logging
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Optional, Union

logger = logging.getLogger(__name__)


class AccountTier(str, Enum):
    """Capital tier classifications"""

    MICRO = "micro"  # < $15k
    SMALL = "small"  # $15k - $50k
    MEDIUM = "medium"  # $50k - $250k
    LARGE = "large"  # $250k+


class AccountConfiguration:
    """
    Provides recommended configuration for each account tier.

    Balances aggressiveness with safety by adjusting position sizing,
    risk limits, and feature availability based on capital.
    """

    # Tier definitions with capital ranges
    TIER_BOUNDARIES: ClassVar[dict[AccountTier, tuple[Decimal, Decimal]]] = {
        AccountTier.MICRO: (Decimal("0"), Decimal("15000")),
        AccountTier.SMALL: (Decimal("15000"), Decimal("50000")),
        AccountTier.MEDIUM: (Decimal("50000"), Decimal("250000")),
        AccountTier.LARGE: (Decimal("250000"), Decimal("999999999")),
    }

    # Recommended configurations per tier
    TIER_CONFIGS: ClassVar[dict[AccountTier, dict[str, Union[Decimal, int, str, bool]]]] = {
        AccountTier.MICRO: {
            "position_size_pct": Decimal("0.02"),  # 2% per position
            "max_concurrent_trades": 1,
            "rebalance_frequency_days": 30,  # Monthly rebalancing
            "learning_enabled": False,
            "expensive_modules_enabled": False,
            "max_daily_loss_pct": Decimal("0.01"),  # 1% daily loss limit
            "max_positions": 3,
            "min_position_alpha": Decimal("50"),  # Min $50 alpha per trade
            "trading_frequency": "low",  # 5-10 trades/month
            "risk_level": "conservative",
            "recommendation": "Focus on simple momentum strategies, manual optimization",
        },
        AccountTier.SMALL: {
            "position_size_pct": Decimal("0.05"),  # 5% per position
            "max_concurrent_trades": 2,
            "rebalance_frequency_days": 14,  # Bi-weekly rebalancing
            "learning_enabled": True,  # Conditional on alpha
            "expensive_modules_enabled": False,
            "max_daily_loss_pct": Decimal("0.02"),  # 2% daily loss limit
            "max_positions": 5,
            "min_position_alpha": Decimal("100"),  # Min $100 alpha per trade
            "trading_frequency": "medium",  # 10-20 trades/month
            "risk_level": "moderate",
            "recommendation": "Enable learning if monthly alpha > $500, avoid expensive modules",
        },
        AccountTier.MEDIUM: {
            "position_size_pct": Decimal("0.08"),  # 8% per position
            "max_concurrent_trades": 3,
            "rebalance_frequency_days": 7,  # Weekly rebalancing
            "learning_enabled": True,
            "expensive_modules_enabled": True,  # Selective
            "max_daily_loss_pct": Decimal("0.03"),  # 3% daily loss limit
            "max_positions": 8,
            "min_position_alpha": Decimal("150"),  # Min $150 alpha per trade
            "trading_frequency": "high",  # 20-40 trades/month
            "risk_level": "balanced",
            "recommendation": "Enable deep learning, use selective transformer modules for regime detection",
        },
        AccountTier.LARGE: {
            "position_size_pct": Decimal("0.10"),  # 10% per position
            "max_concurrent_trades": 5,
            "rebalance_frequency_days": 3,  # Frequent rebalancing
            "learning_enabled": True,
            "expensive_modules_enabled": True,  # All
            "max_daily_loss_pct": Decimal("0.05"),  # 5% daily loss limit
            "max_positions": 12,
            "min_position_alpha": Decimal("200"),  # Min $200 alpha per trade
            "trading_frequency": "very_high",  # 40+ trades/month
            "risk_level": "aggressive",
            "recommendation": "Utilize all available features, enable ensemble methods and ensemble learning",
        },
    }

    @staticmethod
    def get_tier(capital: Decimal) -> AccountTier:
        """Classify capital into a tier"""
        for tier, (min_capital, max_capital) in AccountConfiguration.TIER_BOUNDARIES.items():
            if min_capital <= capital < max_capital:
                return tier
        return AccountTier.LARGE

    @staticmethod
    def get_configuration(capital: Decimal) -> dict:
        """
        Get recommended configuration for the given capital amount.

        Args:
            capital: Account capital in dollars

        Returns:
            Dict with recommended settings for this capital tier
        """
        tier = AccountConfiguration.get_tier(capital)
        config = AccountConfiguration.TIER_CONFIGS[tier].copy()
        config["tier"] = tier.value
        config["capital"] = capital

        return config

    @staticmethod
    def get_all_tier_recommendations() -> dict[str, dict]:
        """Get recommendations for all tiers"""
        recommendations = {}
        for tier in AccountTier:
            recommendations[tier.value] = AccountConfiguration.TIER_CONFIGS[tier].copy()
        return recommendations

    @staticmethod
    def validate_position_size(
        capital: Decimal,
        position_size: Decimal,
    ) -> tuple[bool, str]:
        """
        Validate if position size is acceptable for account capital.

        Args:
            capital: Account capital
            position_size: Proposed position size

        Returns:
            (is_valid: bool, reason: str)
        """
        tier = AccountConfiguration.get_tier(capital)
        config = AccountConfiguration.TIER_CONFIGS[tier]
        position_size_pct = config["position_size_pct"]
        assert isinstance(position_size_pct, Decimal)
        max_position = capital * position_size_pct

        if position_size > max_position:
            return False, (
                f"Position size ${position_size:,.0f} exceeds maximum "
                f"${max_position:,.0f} for {tier.value} tier "
                f"({position_size_pct:.0%} of ${capital:,.0f})"
            )

        return True, f"Position size ${position_size:,.0f} acceptable for {tier.value} tier"

    @staticmethod
    def get_tier_upgrade_capital(current_capital: Decimal) -> dict[str, object]:
        """
        Calculate what capital is needed to upgrade to the next tier.

        Args:
            current_capital: Current account capital

        Returns:
            Dict with upgrade path and capital needed
        """
        current_tier = AccountConfiguration.get_tier(current_capital)

        tier_list = [AccountTier.MICRO, AccountTier.SMALL, AccountTier.MEDIUM, AccountTier.LARGE]
        current_index = tier_list.index(current_tier)

        if current_index >= len(tier_list) - 1:
            return {
                "current_tier": current_tier.value,
                "is_max_tier": True,
                "next_tier": None,
                "capital_needed": None,
            }

        next_tier = tier_list[current_index + 1]
        min_capital, _ = AccountConfiguration.TIER_BOUNDARIES[next_tier]

        return {
            "current_tier": current_tier.value,
            "next_tier": next_tier.value,
            "is_max_tier": False,
            "capital_needed": min_capital,
            "capital_shortfall": max(Decimal("0"), min_capital - current_capital),
            "benefits_after_upgrade": (
                AccountConfiguration.TIER_CONFIGS[next_tier].get("recommendation", "")
            ),
        }

    @staticmethod
    def get_safe_trading_limits(capital: Decimal) -> dict:
        """
        Get maximum safe trading parameters for this capital level.

        Returns:
            Dict with conservative trading limits
        """
        tier = AccountConfiguration.get_tier(capital)
        config = AccountConfiguration.TIER_CONFIGS[tier]
        position_size_pct = config["position_size_pct"]
        max_daily_loss_pct = config["max_daily_loss_pct"]
        assert isinstance(position_size_pct, Decimal)
        assert isinstance(max_daily_loss_pct, Decimal)

        return {
            "tier": tier.value,
            "max_concurrent_trades": config["max_concurrent_trades"],
            "max_position_size": capital * position_size_pct,
            "max_daily_loss_dollars": capital * max_daily_loss_pct,
            "max_daily_loss_pct": float(max_daily_loss_pct),
            "max_positions": config["max_positions"],
            "rebalance_frequency_days": config["rebalance_frequency_days"],
            "risk_level": config["risk_level"],
        }

    @staticmethod
    def is_feature_recommended(capital: Decimal, feature: str) -> bool:
        """
        Check if a feature is recommended for this capital level.

        Features: learning, expensive_modules, ensemble_methods, transfer_learning

        Args:
            capital: Account capital
            feature: Feature name

        Returns:
            Whether feature is recommended
        """
        tier = AccountConfiguration.get_tier(capital)
        config = AccountConfiguration.TIER_CONFIGS[tier]

        feature_map: dict[str, bool] = {
            "learning": bool(config.get("learning_enabled", False)),
            "expensive_modules": bool(config.get("expensive_modules_enabled", False)),
        }

        return feature_map.get(feature, False)

    @staticmethod
    def log_configuration(capital: Decimal, account_id: Optional[str] = None) -> str:
        """Log account configuration recommendation"""
        tier = AccountConfiguration.get_tier(capital)
        config = AccountConfiguration.TIER_CONFIGS[tier]

        log_msg = (
            f"Account Configuration: {tier.value.upper()} tier | "
            f"Capital: ${capital:,.0f} | "
            f"Max Position: {config['position_size_pct']:.0%} | "
            f"Learning: {'Enabled' if config['learning_enabled'] else 'Disabled'}"
        )

        if account_id:
            log_msg = f"[{account_id}] {log_msg}"

        logger.info(log_msg)
        logger.info(f"  Recommendation: {config['recommendation']}")

        return log_msg
