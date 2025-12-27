"""
T1.1: Capital Tier Strategy Selector

Dynamically selects strategy configuration based on available capital:
- Determines capital tier (MICRO/SMALL/MEDIUM/LARGE)
- Activates appropriate strategy features
- Scales risk profile by tier
- Configures leverage limits
"""

import logging
from decimal import Decimal
from typing import Optional

from .models import (
    CapitalTier,
    CapitalTierResult,
    RiskProfile,
    StrategyFeatures,
)

logger = logging.getLogger(__name__)


class CapitalTierSelector:
    """
    T1.1.1: Capital Tier Selector
    Maps capital amount to tier and determines tier-specific parameters.
    """

    THRESHOLDS = {
        CapitalTier.MICRO: (Decimal("0"), Decimal("15000")),
        CapitalTier.SMALL: (Decimal("15000"), Decimal("50000")),
        CapitalTier.MEDIUM: (Decimal("50000"), Decimal("250000")),
        CapitalTier.LARGE: (Decimal("250000"), Decimal("999999999")),
    }

    TIER_CONFIGS = {
        CapitalTier.MICRO: {
            "strategy_type": "CONSERVATIVE",
            "expected_alpha_range": (Decimal("2"), Decimal("5")),
            "risk_profile": RiskProfile(
                risk_level=1,
                max_position_size=Decimal("0.02"),
                max_drawdown_acceptable=Decimal("0.03"),
                leverage_allowed=Decimal("0"),
                max_daily_loss=Decimal("100"),
                diversification_min=1,
                pain_tolerance="VERY_LOW",
            ),
            "enabled_features": StrategyFeatures(
                momentum=True,
                mean_reversion=False,
                machine_learning=False,
                deep_learning=False,
                ensemble=False,
                synthetic_data=False,
                regime_detection=False,
                volatility_targeting=False,
                currency_hedging=False,
            ),
        },
        CapitalTier.SMALL: {
            "strategy_type": "BALANCED",
            "expected_alpha_range": (Decimal("3"), Decimal("7")),
            "risk_profile": RiskProfile(
                risk_level=2,
                max_position_size=Decimal("0.05"),
                max_drawdown_acceptable=Decimal("0.07"),
                leverage_allowed=Decimal("0.5"),
                max_daily_loss=Decimal("250"),
                diversification_min=2,
                pain_tolerance="LOW",
            ),
            "enabled_features": StrategyFeatures(
                momentum=True,
                mean_reversion=True,
                machine_learning=False,
                deep_learning=False,
                ensemble=False,
                synthetic_data=False,
                regime_detection=True,
                volatility_targeting=True,
                currency_hedging=False,
            ),
        },
        CapitalTier.MEDIUM: {
            "strategy_type": "AGGRESSIVE",
            "expected_alpha_range": (Decimal("4"), Decimal("10")),
            "risk_profile": RiskProfile(
                risk_level=5,
                max_position_size=Decimal("0.10"),
                max_drawdown_acceptable=Decimal("0.15"),
                leverage_allowed=Decimal("1.5"),
                max_daily_loss=Decimal("1000"),
                diversification_min=5,
                pain_tolerance="MEDIUM",
            ),
            "enabled_features": StrategyFeatures(
                momentum=True,
                mean_reversion=True,
                machine_learning=True,
                deep_learning=False,
                ensemble=True,
                synthetic_data=True,
                regime_detection=True,
                volatility_targeting=True,
                currency_hedging=True,
            ),
        },
        CapitalTier.LARGE: {
            "strategy_type": "AGGRESSIVE",
            "expected_alpha_range": (Decimal("3"), Decimal("8")),
            "risk_profile": RiskProfile(
                risk_level=6,
                max_position_size=Decimal("0.15"),
                max_drawdown_acceptable=Decimal("0.20"),
                leverage_allowed=Decimal("2.5"),
                max_daily_loss=Decimal("3000"),
                diversification_min=8,
                pain_tolerance="HIGH",
            ),
            "enabled_features": StrategyFeatures(
                momentum=True,
                mean_reversion=True,
                machine_learning=True,
                deep_learning=True,
                ensemble=True,
                synthetic_data=True,
                regime_detection=True,
                volatility_targeting=True,
                currency_hedging=True,
            ),
        },
    }

    @classmethod
    def detect_tier(cls, capital: Decimal) -> CapitalTier:
        """
        Determine capital tier from capital amount.

        Args:
            capital: Capital amount in EUR

        Returns:
            CapitalTier enum value

        Raises:
            ValueError: If capital is negative or zero
        """
        if capital <= 0:
            raise ValueError(f"Capital must be positive, got {capital}")

        for tier, (min_cap, max_cap) in cls.THRESHOLDS.items():
            if min_cap <= capital < max_cap:
                logger.info(f"✅ Capital €{capital} detected as {tier.value} tier")
                return tier

        # Should not reach here due to LARGE tier's high max
        raise ValueError(f"Capital €{capital} exceeds maximum threshold")

    @classmethod
    def get_tier_config(cls, tier: CapitalTier) -> dict:
        """Get configuration for a specific tier."""
        return cls.TIER_CONFIGS.get(tier)

    @classmethod
    def select_strategy(cls, capital: Decimal) -> CapitalTierResult:
        """
        Select complete strategy configuration for given capital.

        Args:
            capital: Capital amount in EUR

        Returns:
            CapitalTierResult with complete configuration
        """
        tier = cls.detect_tier(capital)
        config = cls.get_tier_config(tier)

        result = CapitalTierResult(
            tier=tier,
            capital=capital,
            risk_profile=config["risk_profile"],
            enabled_features=config["enabled_features"],
            strategy_type=config["strategy_type"],
            expected_annual_return_pct_range=config["expected_alpha_range"],
            modules_enabled=config["enabled_features"].enabled_modules(),
            leverage_multiplier=config["risk_profile"].leverage_allowed,
            max_position_size_eur=capital * config["risk_profile"].max_position_size,
        )

        logger.info(
            f"📊 Strategy selected for €{capital}: {tier.value} tier, "
            f"{config['strategy_type']} strategy, {len(result.modules_enabled)} modules"
        )
        return result


class StrategyFeatureGatekeeper:
    """
    T1.1.2: Strategy Feature Gatekeeper
    Manages activation/deactivation of strategy features by capital tier.
    """

    def __init__(self):
        """Initialize feature gatekeeper."""
        self.logger = logging.getLogger(__name__)

    def activate_features(
        self, capital: Decimal, requested_features: Optional[StrategyFeatures] = None
    ) -> StrategyFeatures:
        """
        Activate appropriate features for capital tier.

        Args:
            capital: Capital amount in EUR
            requested_features: Optional requested features (will be gated)

        Returns:
            StrategyFeatures with tier-appropriate features activated
        """
        tier = CapitalTierSelector.detect_tier(capital)
        tier_config = CapitalTierSelector.get_tier_config(tier)
        base_features = tier_config["enabled_features"]

        # If specific features requested, validate against tier capabilities
        if requested_features:
            return self._validate_features(base_features, requested_features, tier)

        return base_features

    def _validate_features(
        self, tier_features: StrategyFeatures, requested: StrategyFeatures, tier: CapitalTier
    ) -> StrategyFeatures:
        """
        Validate requested features against tier capabilities.

        Only allow features that are enabled for the tier.
        """
        validated = StrategyFeatures()
        for feature_name in requested.enabled_modules():
            if getattr(tier_features, feature_name):
                setattr(validated, feature_name, True)
                self.logger.info(f"✅ Feature {feature_name} enabled for {tier.value} tier")
            else:
                self.logger.warning(
                    f"⚠️ Feature {feature_name} not available for {tier.value} tier, disabled"
                )

        return validated

    def can_use_feature(self, capital: Decimal, feature: str) -> bool:
        """
        Check if a specific feature is available for capital tier.

        Args:
            capital: Capital amount in EUR
            feature: Feature name (e.g., 'machine_learning')

        Returns:
            True if feature is available for tier, False otherwise
        """
        tier = CapitalTierSelector.detect_tier(capital)
        config = CapitalTierSelector.get_tier_config(tier)
        return getattr(config["enabled_features"], feature, False)


class RiskProfileScaler:
    """
    T1.1.3: Risk Profile Scaler
    Calculates and scales risk profile based on capital amount.
    """

    def __init__(self):
        """Initialize risk scaler."""
        self.logger = logging.getLogger(__name__)

    def scale_risk_profile(self, capital: Decimal) -> RiskProfile:
        """
        Get risk profile scaled for capital amount.

        Args:
            capital: Capital amount in EUR

        Returns:
            Scaled RiskProfile
        """
        tier = CapitalTierSelector.detect_tier(capital)
        config = CapitalTierSelector.get_tier_config(tier)
        risk_profile = config["risk_profile"]

        self.logger.info(
            f"📈 Risk profile for €{capital}: risk_level={risk_profile.risk_level}, "
            f"max_drawdown={risk_profile.max_drawdown_acceptable}, "
            f"leverage={risk_profile.leverage_allowed}x"
        )

        return risk_profile

    def get_risk_level(self, capital: Decimal) -> int:
        """Get risk level (1-7) for capital."""
        risk_profile = self.scale_risk_profile(capital)
        return risk_profile.risk_level

    def get_max_leverage(self, capital: Decimal) -> Decimal:
        """Get maximum allowed leverage for capital."""
        risk_profile = self.scale_risk_profile(capital)
        return risk_profile.leverage_allowed

    def get_max_position_size(self, capital: Decimal) -> Decimal:
        """Get maximum position size (as % of capital) for tier."""
        risk_profile = self.scale_risk_profile(capital)
        return risk_profile.max_position_size

    def get_max_position_size_eur(self, capital: Decimal) -> Decimal:
        """Get maximum position size in EUR for capital."""
        max_pct = self.get_max_position_size(capital)
        return (capital * max_pct).quantize(Decimal("0.01"))

    def get_max_daily_loss_eur(self, capital: Decimal) -> Decimal:
        """Get maximum acceptable daily loss in EUR."""
        risk_profile = self.scale_risk_profile(capital)
        return risk_profile.max_daily_loss
