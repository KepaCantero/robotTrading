"""
Unit Tests for T0.4: Account Configuration

Tests account tier classification and configuration recommendations.
"""

from decimal import Decimal

from app.services.account_configuration import (
    AccountConfiguration,
    AccountTier,
)


class TestAccountTierClassification:
    """Test capital tier classification"""

    def test_micro_tier_boundary_low(self):
        """Capital <$15k should be micro tier"""
        assert AccountConfiguration.get_tier(Decimal("5000")) == AccountTier.MICRO
        assert AccountConfiguration.get_tier(Decimal("10000")) == AccountTier.MICRO
        assert AccountConfiguration.get_tier(Decimal("14999")) == AccountTier.MICRO

    def test_small_tier_boundary(self):
        """Capital $15k-$50k should be small tier"""
        assert AccountConfiguration.get_tier(Decimal("15000")) == AccountTier.SMALL
        assert AccountConfiguration.get_tier(Decimal("25000")) == AccountTier.SMALL
        assert AccountConfiguration.get_tier(Decimal("49999")) == AccountTier.SMALL

    def test_medium_tier_boundary(self):
        """Capital $50k-$250k should be medium tier"""
        assert AccountConfiguration.get_tier(Decimal("50000")) == AccountTier.MEDIUM
        assert AccountConfiguration.get_tier(Decimal("100000")) == AccountTier.MEDIUM
        assert AccountConfiguration.get_tier(Decimal("249999")) == AccountTier.MEDIUM

    def test_large_tier_boundary(self):
        """Capital $250k+ should be large tier"""
        assert AccountConfiguration.get_tier(Decimal("250000")) == AccountTier.LARGE
        assert AccountConfiguration.get_tier(Decimal("500000")) == AccountTier.LARGE
        assert AccountConfiguration.get_tier(Decimal("1000000")) == AccountTier.LARGE


class TestAccountConfigurationRetrieval:
    """Test configuration retrieval"""

    def test_get_configuration_micro(self):
        """Get configuration for micro account"""
        config = AccountConfiguration.get_configuration(Decimal("10000"))

        assert config["tier"] == "micro"
        assert config["position_size_pct"] == Decimal("0.02")
        assert config["learning_enabled"] == False
        assert config["expensive_modules_enabled"] == False

    def test_get_configuration_small(self):
        """Get configuration for small account"""
        config = AccountConfiguration.get_configuration(Decimal("30000"))

        assert config["tier"] == "small"
        assert config["position_size_pct"] == Decimal("0.05")
        assert config["learning_enabled"] == True  # Conditional
        assert config["expensive_modules_enabled"] == False

    def test_get_configuration_medium(self):
        """Get configuration for medium account"""
        config = AccountConfiguration.get_configuration(Decimal("100000"))

        assert config["tier"] == "medium"
        assert config["position_size_pct"] == Decimal("0.08")
        assert config["learning_enabled"] == True
        assert config["expensive_modules_enabled"] == True

    def test_get_configuration_large(self):
        """Get configuration for large account"""
        config = AccountConfiguration.get_configuration(Decimal("500000"))

        assert config["tier"] == "large"
        assert config["position_size_pct"] == Decimal("0.10")
        assert config["learning_enabled"] == True
        assert config["expensive_modules_enabled"] == True

    def test_configuration_includes_capital(self):
        """Configuration should include account capital"""
        capital = Decimal("50000")
        config = AccountConfiguration.get_configuration(capital)

        assert config["capital"] == capital


class TestPositionSizeValidation:
    """Test position sizing validation"""

    def test_micro_max_position_2_percent(self):
        """Micro tier max position should be 2% of capital"""
        is_valid, reason = AccountConfiguration.validate_position_size(
            capital=Decimal("10000"),
            position_size=Decimal("200"),  # Exactly 2%
        )

        assert is_valid == True

    def test_micro_rejects_oversized_position(self):
        """Micro tier should reject positions > 2%"""
        is_valid, reason = AccountConfiguration.validate_position_size(
            capital=Decimal("10000"),
            position_size=Decimal("500"),  # 5% - too large
        )

        assert is_valid == False
        assert "$500" in reason

    def test_small_max_position_5_percent(self):
        """Small tier max position should be 5% of capital"""
        is_valid, reason = AccountConfiguration.validate_position_size(
            capital=Decimal("30000"),
            position_size=Decimal("1500"),  # Exactly 5%
        )

        assert is_valid == True

    def test_large_max_position_10_percent(self):
        """Large tier max position should be 10% of capital"""
        is_valid, reason = AccountConfiguration.validate_position_size(
            capital=Decimal("500000"),
            position_size=Decimal("50000"),  # Exactly 10%
        )

        assert is_valid == True

    def test_position_validation_includes_reason(self):
        """Position validation should include helpful reason"""
        is_valid, reason = AccountConfiguration.validate_position_size(
            capital=Decimal("50000"),
            position_size=Decimal("10000"),  # 20% - too large
        )

        assert "Position size" in reason
        assert "exceeds maximum" in reason


class TestTierUpgrade:
    """Test tier upgrade recommendations"""

    def test_micro_upgrade_path(self):
        """Micro tier should have upgrade path to small"""
        upgrade_path = AccountConfiguration.get_tier_upgrade_capital(Decimal("10000"))

        assert upgrade_path["current_tier"] == "micro"
        assert upgrade_path["next_tier"] == "small"
        assert not upgrade_path["is_max_tier"]
        assert upgrade_path["capital_needed"] == Decimal("15000")

    def test_small_upgrade_path(self):
        """Small tier should have upgrade path to medium"""
        upgrade_path = AccountConfiguration.get_tier_upgrade_capital(Decimal("30000"))

        assert upgrade_path["current_tier"] == "small"
        assert upgrade_path["next_tier"] == "medium"
        assert upgrade_path["capital_needed"] == Decimal("50000")

    def test_large_no_upgrade_path(self):
        """Large tier should have no upgrade path"""
        upgrade_path = AccountConfiguration.get_tier_upgrade_capital(Decimal("500000"))

        assert upgrade_path["current_tier"] == "large"
        assert upgrade_path["is_max_tier"] == True
        assert upgrade_path["next_tier"] is None

    def test_upgrade_capital_shortfall(self):
        """Upgrade path should show capital shortfall"""
        upgrade_path = AccountConfiguration.get_tier_upgrade_capital(Decimal("30000"))

        assert upgrade_path["capital_shortfall"] == Decimal("20000")


class TestSafeTradingLimits:
    """Test safe trading limits"""

    def test_micro_safe_limits(self):
        """Micro tier safe limits should be conservative"""
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("10000"))

        assert limits["tier"] == "micro"
        assert limits["max_concurrent_trades"] == 1
        assert limits["max_positions"] == 3
        assert limits["max_daily_loss_pct"] == 0.01  # 1%

    def test_small_safe_limits(self):
        """Small tier safe limits should be moderate"""
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("30000"))

        assert limits["tier"] == "small"
        assert limits["max_concurrent_trades"] == 2
        assert limits["max_positions"] == 5
        assert limits["max_daily_loss_pct"] == 0.02  # 2%

    def test_medium_safe_limits(self):
        """Medium tier safe limits should be balanced"""
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("100000"))

        assert limits["tier"] == "medium"
        assert limits["max_concurrent_trades"] == 3
        assert limits["max_positions"] == 8
        assert limits["max_daily_loss_pct"] == 0.03  # 3%

    def test_large_safe_limits(self):
        """Large tier safe limits should be permissive"""
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("500000"))

        assert limits["tier"] == "large"
        assert limits["max_concurrent_trades"] == 5
        assert limits["max_positions"] == 12
        assert limits["max_daily_loss_pct"] == 0.05  # 5%

    def test_safe_limits_include_dollar_amounts(self):
        """Safe limits should include dollar amounts"""
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("100000"))

        assert "max_position_size" in limits
        assert "max_daily_loss_dollars" in limits
        assert limits["max_position_size"] > 0
        assert limits["max_daily_loss_dollars"] > 0


class TestFeatureRecommendations:
    """Test feature recommendations by tier"""

    def test_micro_no_learning(self):
        """Micro tier should not recommend learning"""
        assert not AccountConfiguration.is_feature_recommended(Decimal("10000"), "learning")

    def test_small_learning_conditional(self):
        """Small tier learning is conditionally recommended"""
        assert AccountConfiguration.is_feature_recommended(Decimal("30000"), "learning")

    def test_micro_no_expensive_modules(self):
        """Micro tier should not recommend expensive modules"""
        assert not AccountConfiguration.is_feature_recommended(
            Decimal("10000"), "expensive_modules"
        )

    def test_medium_expensive_modules(self):
        """Medium tier should recommend expensive modules"""
        assert AccountConfiguration.is_feature_recommended(Decimal("100000"), "expensive_modules")

    def test_large_all_features(self):
        """Large tier should recommend all features"""
        assert AccountConfiguration.is_feature_recommended(Decimal("500000"), "learning")
        assert AccountConfiguration.is_feature_recommended(Decimal("500000"), "expensive_modules")


class TestAllTierRecommendations:
    """Test getting all tier recommendations"""

    def test_get_all_tier_recommendations(self):
        """Get recommendations for all tiers"""
        recommendations = AccountConfiguration.get_all_tier_recommendations()

        assert "micro" in recommendations
        assert "small" in recommendations
        assert "medium" in recommendations
        assert "large" in recommendations

    def test_all_recommendations_have_core_fields(self):
        """Each recommendation should have core configuration fields"""
        recommendations = AccountConfiguration.get_all_tier_recommendations()

        for tier, config in recommendations.items():
            assert "position_size_pct" in config
            assert "max_concurrent_trades" in config
            assert "learning_enabled" in config
            assert "recommendation" in config


class TestRealWorldScenarios:
    """Test real-world scenario configurations"""

    def test_retail_trader_10k(self):
        """Typical retail trader with $10k"""
        config = AccountConfiguration.get_configuration(Decimal("10000"))
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("10000"))

        assert config["tier"] == "micro"
        assert not config["learning_enabled"]
        assert limits["max_position_size"] == Decimal("200")
        assert limits["max_daily_loss_dollars"] == Decimal("100")

    def test_semi_pro_trader_50k(self):
        """Semi-professional with $50k"""
        config = AccountConfiguration.get_configuration(Decimal("50000"))
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("50000"))

        assert config["tier"] == "medium"
        assert config["learning_enabled"] == True
        assert limits["max_concurrent_trades"] == 3
        assert limits["max_position_size"] == Decimal("4000")

    def test_professional_trader_500k(self):
        """Professional with $500k"""
        config = AccountConfiguration.get_configuration(Decimal("500000"))
        limits = AccountConfiguration.get_safe_trading_limits(Decimal("500000"))

        assert config["tier"] == "large"
        assert config["expensive_modules_enabled"] == True
        assert limits["max_concurrent_trades"] == 5
        assert limits["max_position_size"] == Decimal("50000")
