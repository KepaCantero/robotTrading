"""
PHASE 1: Unit Tests for Capital Tier Selector (T1.1)

Tests:
- Capital tier detection
- Strategy feature activation
- Risk profile scaling
- Module gating
"""

from decimal import Decimal

import pytest

from app.application.orchestration.target_optimization.capital_tier_selector import (
    CapitalTierSelector,
    RiskProfileScaler,
    StrategyFeatureGatekeeper,
)
from app.application.orchestration.target_optimization.models import (
    CapitalTier,
    StrategyFeatures,
)


class TestCapitalTierDetection:
    """Test capital tier detection."""

    def test_micro_tier_upper_bound(self):
        """Test MICRO tier upper boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("14999"))
        assert tier == CapitalTier.MICRO

    def test_micro_tier_lower_bound(self):
        """Test MICRO tier lower boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("1"))
        assert tier == CapitalTier.MICRO

    def test_small_tier_lower_bound(self):
        """Test SMALL tier lower boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("15000"))
        assert tier == CapitalTier.SMALL

    def test_small_tier_upper_bound(self):
        """Test SMALL tier upper boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("49999"))
        assert tier == CapitalTier.SMALL

    def test_medium_tier_lower_bound(self):
        """Test MEDIUM tier lower boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("50000"))
        assert tier == CapitalTier.MEDIUM

    def test_medium_tier_upper_bound(self):
        """Test MEDIUM tier upper boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("249999"))
        assert tier == CapitalTier.MEDIUM

    def test_large_tier_lower_bound(self):
        """Test LARGE tier lower boundary."""
        tier = CapitalTierSelector.detect_tier(Decimal("250000"))
        assert tier == CapitalTier.LARGE

    def test_large_tier_high_capital(self):
        """Test LARGE tier with high capital."""
        tier = CapitalTierSelector.detect_tier(Decimal("1000000"))
        assert tier == CapitalTier.LARGE

    def test_invalid_negative_capital(self):
        """Test that negative capital raises error."""
        with pytest.raises(ValueError):
            CapitalTierSelector.detect_tier(Decimal("-1000"))

    def test_invalid_zero_capital(self):
        """Test that zero capital raises error."""
        with pytest.raises(ValueError):
            CapitalTierSelector.detect_tier(Decimal("0"))


class TestStrategySelection:
    """Test strategy selection for tiers."""

    def test_micro_tier_strategy(self):
        """Test MICRO tier gets CONSERVATIVE strategy."""
        result = CapitalTierSelector.select_strategy(Decimal("10000"))
        assert result.tier == CapitalTier.MICRO
        assert result.strategy_type == "CONSERVATIVE"
        assert result.leverage_multiplier == Decimal("0")

    def test_small_tier_strategy(self):
        """Test SMALL tier gets BALANCED strategy."""
        result = CapitalTierSelector.select_strategy(Decimal("30000"))
        assert result.tier == CapitalTier.SMALL
        assert result.strategy_type == "BALANCED"
        assert result.leverage_multiplier == Decimal("0.5")

    def test_medium_tier_strategy(self):
        """Test MEDIUM tier gets AGGRESSIVE strategy."""
        result = CapitalTierSelector.select_strategy(Decimal("100000"))
        assert result.tier == CapitalTier.MEDIUM
        assert result.strategy_type == "AGGRESSIVE"
        assert result.leverage_multiplier == Decimal("1.5")

    def test_large_tier_strategy(self):
        """Test LARGE tier gets AGGRESSIVE strategy."""
        result = CapitalTierSelector.select_strategy(Decimal("500000"))
        assert result.tier == CapitalTier.LARGE
        assert result.strategy_type == "AGGRESSIVE"
        assert result.leverage_multiplier == Decimal("2.5")

    def test_strategy_has_correct_capital(self):
        """Test selected strategy contains input capital."""
        capital = Decimal("75000")
        result = CapitalTierSelector.select_strategy(capital)
        assert result.capital == capital

    def test_strategy_max_position_size_eur(self):
        """Test max position size calculation in EUR."""
        capital = Decimal("50000")
        result = CapitalTierSelector.select_strategy(capital)
        # MEDIUM tier has 10% max position
        expected_max = capital * Decimal("0.10")
        assert result.max_position_size_eur == expected_max


class TestFeatureActivation:
    """Test strategy feature activation."""

    def test_micro_tier_features_minimal(self):
        """Test MICRO tier activates only momentum."""
        gatekeeper = StrategyFeatureGatekeeper()
        features = gatekeeper.activate_features(Decimal("10000"))
        assert features.momentum is True
        assert features.mean_reversion is False
        assert features.machine_learning is False
        assert features.deep_learning is False

    def test_small_tier_features_moderate(self):
        """Test SMALL tier activates momentum and mean reversion."""
        gatekeeper = StrategyFeatureGatekeeper()
        features = gatekeeper.activate_features(Decimal("30000"))
        assert features.momentum is True
        assert features.mean_reversion is True
        assert features.machine_learning is False
        assert features.regime_detection is True
        assert features.volatility_targeting is True

    def test_medium_tier_features_full(self):
        """Test MEDIUM tier activates most features."""
        gatekeeper = StrategyFeatureGatekeeper()
        features = gatekeeper.activate_features(Decimal("100000"))
        assert features.momentum is True
        assert features.machine_learning is True
        assert features.ensemble is True
        assert features.regime_detection is True

    def test_large_tier_features_complete(self):
        """Test LARGE tier activates all features."""
        gatekeeper = StrategyFeatureGatekeeper()
        features = gatekeeper.activate_features(Decimal("500000"))
        assert features.deep_learning is True
        assert features.machine_learning is True
        assert features.ensemble is True

    def test_feature_gating_rejects_unavailable(self):
        """Test that unavailable features are rejected."""
        gatekeeper = StrategyFeatureGatekeeper()
        requested = StrategyFeatures(machine_learning=True, deep_learning=True)
        result = gatekeeper.activate_features(Decimal("20000"), requested)
        # SMALL tier doesn't have ML/DL
        assert result.machine_learning is False
        assert result.deep_learning is False

    def test_can_use_feature_micro_tier(self):
        """Test feature availability check for MICRO tier."""
        gatekeeper = StrategyFeatureGatekeeper()
        assert gatekeeper.can_use_feature(Decimal("10000"), "momentum") is True
        assert gatekeeper.can_use_feature(Decimal("10000"), "machine_learning") is False

    def test_can_use_feature_large_tier(self):
        """Test feature availability check for LARGE tier."""
        gatekeeper = StrategyFeatureGatekeeper()
        assert gatekeeper.can_use_feature(Decimal("500000"), "deep_learning") is True
        assert gatekeeper.can_use_feature(Decimal("500000"), "machine_learning") is True


class TestRiskProfileScaling:
    """Test risk profile scaling by capital."""

    def test_micro_risk_profile_conservative(self):
        """Test MICRO tier risk profile is conservative."""
        scaler = RiskProfileScaler()
        profile = scaler.scale_risk_profile(Decimal("10000"))
        assert profile.risk_level == 1
        assert profile.leverage_allowed == Decimal("0")
        assert profile.max_drawdown_acceptable == Decimal("0.03")

    def test_small_risk_profile_moderate(self):
        """Test SMALL tier risk profile is moderate."""
        scaler = RiskProfileScaler()
        profile = scaler.scale_risk_profile(Decimal("30000"))
        assert profile.risk_level == 2
        assert profile.leverage_allowed == Decimal("0.5")
        assert profile.max_position_size == Decimal("0.05")

    def test_medium_risk_profile_aggressive(self):
        """Test MEDIUM tier risk profile is aggressive."""
        scaler = RiskProfileScaler()
        profile = scaler.scale_risk_profile(Decimal("100000"))
        assert profile.risk_level == 5
        assert profile.leverage_allowed == Decimal("1.5")

    def test_risk_level_increases_with_capital(self):
        """Test risk level increases with capital."""
        scaler = RiskProfileScaler()
        micro_level = scaler.get_risk_level(Decimal("10000"))
        large_level = scaler.get_risk_level(Decimal("500000"))
        assert large_level > micro_level

    def test_max_leverage_increases_with_capital(self):
        """Test leverage increases with capital."""
        scaler = RiskProfileScaler()
        micro_leverage = scaler.get_max_leverage(Decimal("10000"))
        large_leverage = scaler.get_max_leverage(Decimal("500000"))
        assert large_leverage > micro_leverage

    def test_max_position_size_eur_calculation(self):
        """Test max position size EUR calculation."""
        scaler = RiskProfileScaler()
        capital = Decimal("100000")
        max_position_eur = scaler.get_max_position_size_eur(capital)
        # MEDIUM tier = 10% max position
        expected = capital * Decimal("0.10")
        assert max_position_eur == expected

    def test_max_daily_loss_scales_with_capital(self):
        """Test max daily loss scales with capital."""
        scaler = RiskProfileScaler()
        micro_loss = scaler.get_max_daily_loss_eur(Decimal("10000"))
        large_loss = scaler.get_max_daily_loss_eur(Decimal("500000"))
        assert large_loss > micro_loss


class TestExpectedReturns:
    """Test expected return ranges by tier."""

    def test_micro_tier_expected_return_range(self):
        """Test MICRO tier expected return range."""
        result = CapitalTierSelector.select_strategy(Decimal("10000"))
        min_ret, max_ret = result.expected_annual_return_pct_range
        assert min_ret == Decimal("2")
        assert max_ret == Decimal("5")

    def test_small_tier_expected_return_range(self):
        """Test SMALL tier expected return range."""
        result = CapitalTierSelector.select_strategy(Decimal("30000"))
        min_ret, max_ret = result.expected_annual_return_pct_range
        assert min_ret == Decimal("3")
        assert max_ret == Decimal("7")

    def test_medium_tier_expected_return_range(self):
        """Test MEDIUM tier expected return range."""
        result = CapitalTierSelector.select_strategy(Decimal("100000"))
        min_ret, max_ret = result.expected_annual_return_pct_range
        assert min_ret == Decimal("4")
        assert max_ret == Decimal("10")

    def test_large_tier_expected_return_range(self):
        """Test LARGE tier expected return range."""
        result = CapitalTierSelector.select_strategy(Decimal("500000"))
        min_ret, max_ret = result.expected_annual_return_pct_range
        assert min_ret == Decimal("3")
        assert max_ret == Decimal("8")


class TestModuleGating:
    """Test module activation gating."""

    def test_micro_enabled_modules_count(self):
        """Test MICRO tier has minimal modules."""
        result = CapitalTierSelector.select_strategy(Decimal("10000"))
        assert len(result.modules_enabled) == 1
        assert "momentum" in result.modules_enabled

    def test_small_enabled_modules_count(self):
        """Test SMALL tier has moderate modules."""
        result = CapitalTierSelector.select_strategy(Decimal("30000"))
        assert len(result.modules_enabled) >= 3
        assert "momentum" in result.modules_enabled
        assert "mean_reversion" in result.modules_enabled

    def test_medium_enabled_modules_count(self):
        """Test MEDIUM tier has many modules."""
        result = CapitalTierSelector.select_strategy(Decimal("100000"))
        assert len(result.modules_enabled) >= 6
        assert "machine_learning" in result.modules_enabled

    def test_large_enabled_modules_count(self):
        """Test LARGE tier has all modules."""
        result = CapitalTierSelector.select_strategy(Decimal("500000"))
        assert len(result.modules_enabled) >= 8
        assert "deep_learning" in result.modules_enabled

    def test_modules_enabled_list_consistency(self):
        """Test modules_enabled list matches enabled_features."""
        result = CapitalTierSelector.select_strategy(Decimal("100000"))
        expected_modules = result.enabled_features.enabled_modules()
        assert set(result.modules_enabled) == set(expected_modules)
