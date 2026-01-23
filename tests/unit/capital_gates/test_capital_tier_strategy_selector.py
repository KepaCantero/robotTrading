"""
Unit Tests for PHASE 1 T1.1: Capital Tier Strategy Selector

Tests capital tier classification, strategy selection, risk profiling,
and feature gating for different account capital levels.
"""

from decimal import Decimal

import pytest

from app.services.account_configuration import AccountTier
from app.services.capital_tier_strategy_selector import (
    CapitalTierStrategySelector,
    EnsembleType,
    PositionSizingStrategy,
    StrategySelection,
    get_selector,
)
from app.services.deployment_validator import DeploymentStatus


class TestCapitalTierStrategyInitialization:
    """Test selector initialization"""

    def test_init_valid_capital(self):
        """Initialize with valid capital"""
        selector = CapitalTierStrategySelector(Decimal("50000"))
        assert selector.capital == Decimal("50000")
        assert selector.tier == AccountTier.MEDIUM

    def test_init_with_account_id(self):
        """Initialize with account ID"""
        selector = CapitalTierStrategySelector(Decimal("100000"), account_id="ACC_001")
        assert selector.account_id == "ACC_001"

    def test_init_zero_capital_raises(self):
        """Initialize with zero capital should raise"""
        with pytest.raises(ValueError):
            CapitalTierStrategySelector(Decimal("0"))

    def test_init_negative_capital_raises(self):
        """Initialize with negative capital should raise"""
        with pytest.raises(ValueError):
            CapitalTierStrategySelector(Decimal("-10000"))

    def test_tier_classification_micro(self):
        """Classify €10k as micro"""
        selector = CapitalTierStrategySelector(Decimal("10000"))
        assert selector.tier == AccountTier.MICRO

    def test_tier_classification_small(self):
        """Classify €30k as small"""
        selector = CapitalTierStrategySelector(Decimal("30000"))
        assert selector.tier == AccountTier.SMALL

    def test_tier_classification_medium(self):
        """Classify €100k as medium"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        assert selector.tier == AccountTier.MEDIUM

    def test_tier_classification_large(self):
        """Classify €500k as large"""
        selector = CapitalTierStrategySelector(Decimal("500000"))
        assert selector.tier == AccountTier.LARGE

    def test_tier_boundary_14999(self):
        """Classify €14,999 as micro (just below small boundary)"""
        selector = CapitalTierStrategySelector(Decimal("14999"))
        assert selector.tier == AccountTier.MICRO

    def test_tier_boundary_15000(self):
        """Classify €15,000 as small (at boundary)"""
        selector = CapitalTierStrategySelector(Decimal("15000"))
        assert selector.tier == AccountTier.SMALL

    def test_tier_boundary_50000(self):
        """Classify €50,000 as medium (at boundary)"""
        selector = CapitalTierStrategySelector(Decimal("50000"))
        assert selector.tier == AccountTier.MEDIUM

    def test_tier_boundary_250000(self):
        """Classify €250,000 as large (at boundary)"""
        selector = CapitalTierStrategySelector(Decimal("250000"))
        assert selector.tier == AccountTier.LARGE


class TestStrategySelection:
    """Test strategy selection logic"""

    def test_micro_strategy_selection(self):
        """Micro accounts select single momentum strategy"""
        selector = CapitalTierStrategySelector(Decimal("10000"))
        selection = selector.select_strategies()

        assert selection.primary_strategy == "momentum_engine"
        assert selection.ensemble_type == EnsembleType.NONE
        assert selection.config_variant == "conservative"
        assert selection.tier == "micro"

    def test_small_strategy_selection(self):
        """Small accounts select weighted ensemble"""
        selector = CapitalTierStrategySelector(Decimal("30000"))
        selection = selector.select_strategies()

        assert selection.primary_strategy == "momentum_engine"
        assert selection.ensemble_type == EnsembleType.WEIGHTED
        assert selection.config_variant == "conservative"
        assert len(selection.secondary_strategies) >= 1

    def test_medium_strategy_selection(self):
        """Medium accounts select regime-based ensemble"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        selection = selector.select_strategies()

        assert selection.primary_strategy == "ensemble_selector"
        assert selection.ensemble_type == EnsembleType.REGIME_BASED
        assert selection.config_variant == "balanced"

    def test_large_strategy_selection(self):
        """Large accounts select full ensemble"""
        selector = CapitalTierStrategySelector(Decimal("500000"))
        selection = selector.select_strategies()

        assert selection.primary_strategy == "ensemble_selector"
        assert selection.ensemble_type == EnsembleType.REGIME_BASED
        assert selection.config_variant == "aggressive"

    def test_strategy_selection_has_reasoning(self):
        """Strategy selection includes reasoning"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        selection = selector.select_strategies()

        assert len(selection.reasoning) > 0
        assert isinstance(selection, StrategySelection)

    def test_strategy_selection_secondary_strategies(self):
        """All tiers have fallback secondary strategies"""
        for capital in [Decimal("10000"), Decimal("30000"), Decimal("100000"), Decimal("500000")]:
            selector = CapitalTierStrategySelector(capital)
            selection = selector.select_strategies()

            if selection.ensemble_type == EnsembleType.NONE:
                # Micro should still have fallback
                assert len(selection.secondary_strategies) > 0
            else:
                # Ensemble tiers should have secondary
                assert len(selection.secondary_strategies) >= 1


class TestRiskProfile:
    """Test risk profile configuration"""

    def test_micro_risk_profile(self):
        """Micro accounts have conservative risk limits"""
        selector = CapitalTierStrategySelector(Decimal("10000"))
        profile = selector.get_risk_profile()

        assert profile.tier == "micro"
        assert profile.max_position_size == Decimal("0.02")  # 2%
        assert profile.leverage_allowed == Decimal("1.0")  # No leverage
        assert profile.max_drawdown_pct == Decimal("0.05")  # 5%
        assert profile.max_daily_loss_pct <= Decimal("0.02")

    def test_small_risk_profile(self):
        """Small accounts have moderate risk limits"""
        selector = CapitalTierStrategySelector(Decimal("30000"))
        profile = selector.get_risk_profile()

        assert profile.tier == "small"
        assert profile.leverage_allowed == Decimal("1.25")
        assert profile.max_drawdown_pct == Decimal("0.08")

    def test_medium_risk_profile(self):
        """Medium accounts have balanced risk limits"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        profile = selector.get_risk_profile()

        assert profile.tier == "medium"
        assert profile.leverage_allowed == Decimal("1.5")
        assert profile.max_drawdown_pct == Decimal("0.10")

    def test_large_risk_profile(self):
        """Large accounts have aggressive risk limits"""
        selector = CapitalTierStrategySelector(Decimal("500000"))
        profile = selector.get_risk_profile()

        assert profile.tier == "large"
        assert profile.leverage_allowed == Decimal("2.5")
        assert profile.max_drawdown_pct == Decimal("0.15")

    def test_leverage_scales_with_capital(self):
        """Leverage increases with capital tier"""
        leverage_micro = (
            CapitalTierStrategySelector(Decimal("10000")).get_risk_profile().leverage_allowed
        )
        leverage_large = (
            CapitalTierStrategySelector(Decimal("500000")).get_risk_profile().leverage_allowed
        )

        assert leverage_micro < leverage_large

    def test_drawdown_tolerance_scales(self):
        """Drawdown tolerance increases with capital"""
        dd_micro = CapitalTierStrategySelector(Decimal("10000")).get_risk_profile().max_drawdown_pct
        dd_large = (
            CapitalTierStrategySelector(Decimal("500000")).get_risk_profile().max_drawdown_pct
        )

        assert dd_micro < dd_large

    def test_position_sizing_strategy(self):
        """Different tiers use different position sizing strategies"""
        micro_pos = (
            CapitalTierStrategySelector(Decimal("10000"))
            .get_risk_profile()
            .position_sizing_strategy
        )
        large_pos = (
            CapitalTierStrategySelector(Decimal("500000"))
            .get_risk_profile()
            .position_sizing_strategy
        )

        # Micro should use simple fixed %, large should use Kelly
        assert micro_pos == PositionSizingStrategy.FIXED_PCT
        assert large_pos == PositionSizingStrategy.KELLY_CRITERION

    def test_risk_profile_validation(self):
        """Risk profile validates correctly"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        profile = selector.get_risk_profile()

        is_valid, reason = profile.validate()
        assert is_valid, f"Profile should be valid: {reason}"

    def test_risk_profile_max_position_positive(self):
        """Max position size is positive"""
        for capital in [Decimal("10000"), Decimal("100000"), Decimal("500000")]:
            profile = CapitalTierStrategySelector(capital).get_risk_profile()
            assert profile.max_position_size > Decimal("0")

    def test_concurrent_trades_scales(self):
        """Max concurrent trades increases with tier"""
        trades_micro = (
            CapitalTierStrategySelector(Decimal("10000")).get_risk_profile().max_concurrent_trades
        )
        trades_large = (
            CapitalTierStrategySelector(Decimal("500000")).get_risk_profile().max_concurrent_trades
        )

        assert trades_micro < trades_large


class TestFeatureCapabilities:
    """Test feature gating"""

    def test_micro_features_disabled(self):
        """Micro accounts have minimal features"""
        selector = CapitalTierStrategySelector(Decimal("10000"))
        capabilities = selector.get_enabled_features()

        assert not capabilities.learning
        assert not capabilities.deep_learning
        assert not capabilities.transformer_models
        assert not capabilities.ensemble_methods

    def test_small_features_minimal(self):
        """Small accounts have minimal features"""
        selector = CapitalTierStrategySelector(Decimal("30000"))
        capabilities = selector.get_enabled_features()

        # Small accounts may have learning conditionally
        # but not deep learning
        assert not capabilities.deep_learning
        assert not capabilities.transformer_models

    def test_medium_features_enabled(self):
        """Medium accounts have moderate features"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        capabilities = selector.get_enabled_features()

        # Medium should have transfer learning and ensemble methods
        assert capabilities.ensemble_methods
        assert capabilities.feature_importance_analysis

    def test_large_features_full(self):
        """Large accounts have all features"""
        selector = CapitalTierStrategySelector(Decimal("500000"))
        capabilities = selector.get_enabled_features()

        # Large accounts should have most features
        assert capabilities.learning
        assert capabilities.ensemble_methods
        assert capabilities.feature_importance_analysis
        # Note: transformer_models depends on config

    def test_transformer_only_for_large(self):
        """Transformer models only for large accounts"""
        for capital in [Decimal("10000"), Decimal("30000"), Decimal("100000")]:
            capabilities = CapitalTierStrategySelector(capital).get_enabled_features()
            assert not capabilities.transformer_models

    def test_transfer_learning_medium_plus(self):
        """Transfer learning available for medium+ accounts"""
        micro_cap = CapitalTierStrategySelector(Decimal("10000")).get_enabled_features()
        small_cap = CapitalTierStrategySelector(Decimal("30000")).get_enabled_features()
        medium_cap = CapitalTierStrategySelector(Decimal("100000")).get_enabled_features()

        assert not micro_cap.transfer_learning
        assert not small_cap.transfer_learning
        assert medium_cap.transfer_learning

    def test_ensemble_methods_small_plus(self):
        """Ensemble methods for small+ accounts"""
        micro_cap = CapitalTierStrategySelector(Decimal("10000")).get_enabled_features()
        small_cap = CapitalTierStrategySelector(Decimal("30000")).get_enabled_features()

        assert not micro_cap.ensemble_methods
        assert small_cap.ensemble_methods


class TestDeploymentValidation:
    """Test deployment validation integration"""

    def test_micro_deployment_with_reasonable_goal(self):
        """Micro account with reasonable goals"""
        selector = CapitalTierStrategySelector(Decimal("10000"), account_id="MICRO_TEST")
        report = selector.validate_deployment(
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("200"),
        )

        assert report.account_id == "MICRO_TEST"
        assert report.tier == "micro"
        assert report.capital == Decimal("10000")
        # Should have issues or be restricted due to small capital
        assert report.status in [
            DeploymentStatus.REJECTED,
            DeploymentStatus.RESTRICTED,
            DeploymentStatus.REVIEW_REQUIRED,
        ]

    def test_medium_deployment_with_reasonable_goal(self):
        """Medium account with reasonable goals"""
        selector = CapitalTierStrategySelector(Decimal("100000"), account_id="MEDIUM_TEST")
        report = selector.validate_deployment(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("1500"),
        )

        assert report.tier == "medium"
        # Should have minimal issues
        assert len(report.issues) <= 1

    def test_large_deployment_with_sufficient_alpha(self):
        """Large account with sufficient alpha for modules"""
        selector = CapitalTierStrategySelector(Decimal("500000"), account_id="LARGE_TEST")
        report = selector.validate_deployment(
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("50000"),
        )

        assert report.tier == "large"
        assert report.status in [DeploymentStatus.APPROVED, DeploymentStatus.RESTRICTED]
        # Large accounts with high alpha should have no issues
        assert len(report.issues) == 0

    def test_deployment_report_structure(self):
        """Deployment report has all required fields"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        report = selector.validate_deployment(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("1500"),
        )

        assert hasattr(report, "status")
        assert hasattr(report, "account_id")
        assert hasattr(report, "issues")
        assert hasattr(report, "warnings")
        assert hasattr(report, "recommendations")
        assert hasattr(report, "tier")
        assert hasattr(report, "capital")
        assert isinstance(report.issues, list)
        assert isinstance(report.warnings, list)
        assert isinstance(report.recommendations, list)


class TestTierInformation:
    """Test information retrieval methods"""

    def test_get_tier_info(self):
        """Get tier information"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        info = selector.get_tier_info()

        assert info["tier"] == "medium"
        assert info["capital"] == 100000.0
        assert "position_size" in info
        assert "max_concurrent_trades" in info
        assert "learning_enabled" in info

    def test_get_upgrade_path(self):
        """Get upgrade path for tier"""
        selector = CapitalTierStrategySelector(Decimal("30000"))
        upgrade_path = selector.get_upgrade_path()

        assert "current_tier" in upgrade_path
        assert upgrade_path["current_tier"] == "small"
        # Should suggest medium tier
        assert upgrade_path["next_tier"] == "medium"

    def test_large_tier_has_no_upgrade(self):
        """Large tier is max tier"""
        selector = CapitalTierStrategySelector(Decimal("500000"))
        upgrade_path = selector.get_upgrade_path()

        assert upgrade_path["is_max_tier"]
        assert upgrade_path["next_tier"] is None


class TestSingletonCaching:
    """Test caching of selector instances"""

    def test_get_selector_creates_instance(self):
        """get_selector creates new instance"""
        selector = get_selector(Decimal("100000"), account_id="TEST_ACC")
        assert selector.capital == Decimal("100000")
        assert selector.account_id == "TEST_ACC"

    def test_get_selector_caches_by_account_id(self):
        """get_selector caches instances"""
        selector1 = get_selector(Decimal("100000"), account_id="TEST_ACC_2")
        selector2 = get_selector(Decimal("100000"), account_id="TEST_ACC_2")

        # Should be same instance
        assert selector1 is selector2

    def test_different_account_ids_different_instances(self):
        """Different account IDs get different instances"""
        selector1 = get_selector(Decimal("100000"), account_id="ACC_A")
        selector2 = get_selector(Decimal("100000"), account_id="ACC_B")

        # Should be different instances
        assert selector1 is not selector2


class TestConsistency:
    """Test consistency across methods"""

    def test_all_tiers_have_consistent_profiles(self):
        """All tiers produce consistent profiles"""
        for capital in [Decimal("10000"), Decimal("30000"), Decimal("100000"), Decimal("500000")]:
            selector = CapitalTierStrategySelector(capital)

            strategy = selector.select_strategies()
            risk = selector.get_risk_profile()
            selector.get_enabled_features()

            # Verify all methods agree on tier
            assert strategy.tier == risk.tier
            assert strategy.tier in ["micro", "small", "medium", "large"]

    def test_leverage_consistent_across_methods(self):
        """Leverage is consistent between risk profile and tier"""
        for capital in [Decimal("10000"), Decimal("500000")]:
            selector = CapitalTierStrategySelector(capital)
            risk = selector.get_risk_profile()
            expected_leverage = selector.LEVERAGE_ALLOWANCES[selector.tier]

            assert risk.leverage_allowed == expected_leverage

    def test_learning_gated_consistently(self):
        """Learning status consistent across methods"""
        selector = CapitalTierStrategySelector(Decimal("100000"))

        config_learning = selector.config.get("learning_enabled", False)
        risk_learning = selector.get_risk_profile().learning_enabled
        selector.get_enabled_features().learning

        # All should align (though features_learning may be stricter)
        if config_learning:
            # Config says yes, but features may gate it
            assert risk_learning


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_capital_one_unit(self):
        """Handle minimal capital"""
        selector = CapitalTierStrategySelector(Decimal("1"))
        assert selector.tier == AccountTier.MICRO

    def test_very_large_capital(self):
        """Handle very large capital"""
        selector = CapitalTierStrategySelector(Decimal("10000000"))
        assert selector.tier == AccountTier.LARGE

    def test_decimal_precision(self):
        """Handle decimal precision correctly"""
        selector = CapitalTierStrategySelector(Decimal("100000.50"))
        assert selector.capital == Decimal("100000.50")

    def test_position_size_as_percentage(self):
        """Position size is correctly expressed as percentage"""
        selector = CapitalTierStrategySelector(Decimal("100000"))
        profile = selector.get_risk_profile()

        # Should be decimal between 0 and 1 (percentage)
        assert Decimal("0") < profile.max_position_size < Decimal("1")
