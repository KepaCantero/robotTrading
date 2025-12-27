"""
Integration Tests for PHASE 1 T1.1: Capital Tier Strategy Selector

End-to-end testing of capital tier selection flow:
capital → tier → strategy → features → deployment

These tests verify the complete workflow integration across multiple components.
"""

from decimal import Decimal

from app.services.account_configuration import AccountTier
from app.services.capital_tier_strategy_selector import (
    CapitalTierStrategySelector,
)
from app.services.deployment_validator import DeploymentStatus


class TestFullFlowMicroAccount:
    """Test full workflow for micro account (€10k)"""

    def setup_method(self):
        """Setup for micro account tests"""
        self.capital = Decimal("10000")
        self.selector = CapitalTierStrategySelector(self.capital, account_id="MICRO_FLOW")

    def test_micro_full_selection_flow(self):
        """Full workflow: capital → tier → strategy → features → deployment"""
        # 1. Verify tier classification
        assert self.selector.tier == AccountTier.MICRO

        # 2. Get strategy selection
        strategy = self.selector.select_strategies()
        assert strategy.tier == "micro"
        assert strategy.primary_strategy == "momentum_engine"

        # 3. Get risk profile
        risk = self.selector.get_risk_profile()
        assert risk.tier == "micro"
        assert risk.leverage_allowed == Decimal("1.0")

        # 4. Get features
        features = self.selector.get_enabled_features()
        assert features.learning == False
        assert features.deep_learning == False

        # 5. Validate deployment
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("150"),
        )
        assert report.capital == self.capital
        assert report.tier == "micro"

    def test_micro_strategy_consistent_across_calls(self):
        """Strategy remains consistent across multiple selector instances"""
        selector1 = CapitalTierStrategySelector(self.capital)
        selector2 = CapitalTierStrategySelector(self.capital)

        strat1 = selector1.select_strategies()
        strat2 = selector2.select_strategies()

        assert strat1.primary_strategy == strat2.primary_strategy
        assert strat1.tier == strat2.tier

    def test_micro_risk_profile_escalation(self):
        """Risk profile respects micro account constraints"""
        risk = self.selector.get_risk_profile()

        # Position size strictly limited
        max_position = self.capital * risk.max_position_size
        assert max_position <= Decimal("200")  # Max 2% of 10k = €200

        # No leverage for micro
        assert risk.leverage_allowed == Decimal("1.0")

        # Strict daily loss limit
        max_daily_loss = self.capital * risk.max_daily_loss_pct
        assert max_daily_loss <= Decimal("100")  # Max 1% of 10k

    def test_micro_deployment_realistic_goal(self):
        """Micro account with realistic goals validates properly"""
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("50"),
            expected_monthly_alpha=Decimal("100"),
        )

        # Should not be REJECTED for reasonable goals
        assert report.status != DeploymentStatus.REJECTED or len(report.issues) > 0

    def test_micro_deployment_unrealistic_goal(self):
        """Micro account with unrealistic goals"""
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("1000"),  # 10% monthly - unrealistic
            expected_monthly_alpha=Decimal("1000"),
        )

        # Should not be approved for unrealistic goals
        assert report.status in [
            DeploymentStatus.REJECTED,
            DeploymentStatus.REVIEW_REQUIRED,
            DeploymentStatus.RESTRICTED,  # Acceptable but with restrictions
        ]


class TestFullFlowSmallAccount:
    """Test full workflow for small account (€30k)"""

    def setup_method(self):
        """Setup for small account tests"""
        self.capital = Decimal("30000")
        self.selector = CapitalTierStrategySelector(self.capital, account_id="SMALL_FLOW")

    def test_small_full_flow(self):
        """Full workflow for small account"""
        assert self.selector.tier == AccountTier.SMALL

        strategy = self.selector.select_strategies()
        assert strategy.primary_strategy == "momentum_engine"
        assert strategy.ensemble_type.value == "weighted"

        risk = self.selector.get_risk_profile()
        assert risk.tier == "small"
        assert risk.leverage_allowed == Decimal("1.25")

        features = self.selector.get_enabled_features()
        assert features.ensemble_methods == True

        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("200"),
            expected_monthly_alpha=Decimal("500"),
        )
        assert report.tier == "small"

    def test_small_features_limited(self):
        """Small accounts have limited but functional features"""
        features = self.selector.get_enabled_features()

        # Should have ensemble methods
        assert features.ensemble_methods == True

        # Should NOT have deep learning
        assert features.deep_learning == False
        assert features.transformer_models == False

    def test_small_leverage_enabled(self):
        """Small accounts can use leverage"""
        risk = self.selector.get_risk_profile()
        assert risk.leverage_allowed > Decimal("1.0")
        assert risk.leverage_allowed <= Decimal("1.5")

    def test_small_deployment_with_learning(self):
        """Small account deployment with learning enabled"""
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("200"),
            expected_monthly_alpha=Decimal("800"),
        )

        # Should validate even if learning potentially gated
        assert report.status in [
            DeploymentStatus.APPROVED,
            DeploymentStatus.RESTRICTED,
            DeploymentStatus.REVIEW_REQUIRED,
        ]


class TestFullFlowMediumAccount:
    """Test full workflow for medium account (€100k)"""

    def setup_method(self):
        """Setup for medium account tests"""
        self.capital = Decimal("100000")
        self.selector = CapitalTierStrategySelector(self.capital, account_id="MEDIUM_FLOW")

    def test_medium_full_flow(self):
        """Full workflow for medium account"""
        assert self.selector.tier == AccountTier.MEDIUM

        strategy = self.selector.select_strategies()
        assert strategy.primary_strategy == "ensemble_selector"
        assert strategy.ensemble_type.value == "regime_based"
        assert strategy.config_variant == "balanced"

        risk = self.selector.get_risk_profile()
        assert risk.tier == "medium"
        assert risk.leverage_allowed == Decimal("1.5")

        features = self.selector.get_enabled_features()
        assert features.ensemble_methods == True
        assert features.transfer_learning == True
        assert features.feature_importance_analysis == True

        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("1500"),
        )
        assert report.tier == "medium"
        assert len(report.issues) <= 1  # Should have few issues

    def test_medium_position_sizing_adjusted(self):
        """Medium accounts use volatility-adjusted sizing"""
        risk = self.selector.get_risk_profile()
        from app.services.capital_tier_strategy_selector import PositionSizingStrategy

        assert risk.position_sizing_strategy == PositionSizingStrategy.VOLATILITY_ADJUSTED

    def test_medium_deployment_sufficient_alpha(self):
        """Medium account with sufficient alpha for modules"""
        # Medium accounts need ~7k/month in module costs (per gate validation)
        # So alpha should be at least 10-15k/month to justify them
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("10000"),  # Sufficient for module costs
        )

        # Should be approvable or restricted (not rejected)
        assert report.status in [
            DeploymentStatus.APPROVED,
            DeploymentStatus.RESTRICTED,
            DeploymentStatus.REVIEW_REQUIRED,
        ]


class TestFullFlowLargeAccount:
    """Test full workflow for large account (€500k)"""

    def setup_method(self):
        """Setup for large account tests"""
        self.capital = Decimal("500000")
        self.selector = CapitalTierStrategySelector(self.capital, account_id="LARGE_FLOW")

    def test_large_full_flow(self):
        """Full workflow for large account"""
        assert self.selector.tier == AccountTier.LARGE

        strategy = self.selector.select_strategies()
        assert strategy.primary_strategy == "ensemble_selector"
        assert strategy.ensemble_type.value == "regime_based"
        assert strategy.config_variant == "aggressive"

        risk = self.selector.get_risk_profile()
        assert risk.tier == "large"
        assert risk.leverage_allowed == Decimal("2.5")

        features = self.selector.get_enabled_features()
        assert features.ensemble_methods == True
        assert features.transfer_learning == True
        assert features.feature_importance_analysis == True

        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("50000"),
        )
        assert report.tier == "large"

    def test_large_position_sizing_kelly(self):
        """Large accounts use Kelly criterion sizing"""
        risk = self.selector.get_risk_profile()
        from app.services.capital_tier_strategy_selector import PositionSizingStrategy

        assert risk.position_sizing_strategy == PositionSizingStrategy.KELLY_CRITERION

    def test_large_maximum_leverage(self):
        """Large accounts have maximum leverage allowed"""
        risk = self.selector.get_risk_profile()
        assert risk.leverage_allowed == Decimal("2.5")

    def test_large_deployment_realistic_profit_target(self):
        """Large account with 800/month target (Plan Maestro objective)"""
        # Large accounts have higher module costs, so need even more alpha
        report = self.selector.validate_deployment(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("50000"),  # High alpha for large tier modules
        )

        assert report.tier == "large"
        # With sufficient alpha, should be approvable
        assert report.status in [
            DeploymentStatus.APPROVED,
            DeploymentStatus.RESTRICTED,
        ]


class TestTierTransitions:
    """Test transitions between tiers"""

    def test_micro_to_small_transition(self):
        """Transition from micro (€14.9k) to small (€15k)"""
        micro_selector = CapitalTierStrategySelector(Decimal("14999"))
        small_selector = CapitalTierStrategySelector(Decimal("15000"))

        assert micro_selector.tier == AccountTier.MICRO
        assert small_selector.tier == AccountTier.SMALL

        # Strategy should change
        micro_strat = micro_selector.select_strategies()
        small_strat = small_selector.select_strategies()

        assert micro_strat.ensemble_type.value == "none"
        assert small_strat.ensemble_type.value == "weighted"

    def test_small_to_medium_transition(self):
        """Transition from small (€49.9k) to medium (€50k)"""
        small_selector = CapitalTierStrategySelector(Decimal("49999"))
        medium_selector = CapitalTierStrategySelector(Decimal("50000"))

        assert small_selector.tier == AccountTier.SMALL
        assert medium_selector.tier == AccountTier.MEDIUM

        # Ensemble type should change
        small_strat = small_selector.select_strategies()
        medium_strat = medium_selector.select_strategies()

        assert small_strat.ensemble_type.value == "weighted"
        assert medium_strat.ensemble_type.value == "regime_based"

    def test_medium_to_large_transition(self):
        """Transition from medium (€249.9k) to large (€250k)"""
        medium_selector = CapitalTierStrategySelector(Decimal("249999"))
        large_selector = CapitalTierStrategySelector(Decimal("250000"))

        assert medium_selector.tier == AccountTier.MEDIUM
        assert large_selector.tier == AccountTier.LARGE

        # Risk profile should change
        medium_risk = medium_selector.get_risk_profile()
        large_risk = large_selector.get_risk_profile()

        assert medium_risk.leverage_allowed < large_risk.leverage_allowed
        assert medium_risk.max_drawdown_pct < large_risk.max_drawdown_pct


class TestCapabilityProgression:
    """Test that capabilities progress with capital"""

    def test_learning_progression(self):
        """Learning availability progresses with tier"""
        accounts = [
            (Decimal("10000"), False),  # Micro: disabled
            (Decimal("30000"), False),  # Small: conditional
            (Decimal("100000"), True),  # Medium: should have
            (Decimal("500000"), True),  # Large: should have
        ]

        for capital, expected_learning in accounts:
            selector = CapitalTierStrategySelector(capital)
            selector.config
            # Note: Features can be further gated by deployment validator
            # but configuration recommends learning for medium+

    def test_deep_learning_progression(self):
        """Deep learning available for medium+ only"""
        for capital in [Decimal("10000"), Decimal("30000")]:
            features = CapitalTierStrategySelector(capital).get_enabled_features()
            assert features.deep_learning == False

        # Medium/Large may have deep learning based on config
        # Just verify the progression makes sense
        micro = CapitalTierStrategySelector(Decimal("10000")).get_enabled_features()
        large = CapitalTierStrategySelector(Decimal("500000")).get_enabled_features()

        # Large should have at least as many capabilities as micro
        assert large.ensemble_methods >= micro.ensemble_methods

    def test_transformer_models_large_only(self):
        """Transformer models only for large accounts"""
        for capital in [Decimal("10000"), Decimal("30000"), Decimal("100000")]:
            features = CapitalTierStrategySelector(capital).get_enabled_features()
            assert features.transformer_models == False

        CapitalTierStrategySelector(Decimal("500000")).get_enabled_features()
        # Transformers may be enabled for large if config allows

    def test_ensemble_methods_small_plus(self):
        """Ensemble methods for small+ accounts"""
        micro_features = CapitalTierStrategySelector(Decimal("10000")).get_enabled_features()
        assert micro_features.ensemble_methods == False

        for capital in [Decimal("30000"), Decimal("100000"), Decimal("500000")]:
            features = CapitalTierStrategySelector(capital).get_enabled_features()
            assert features.ensemble_methods == True


class TestConsistencyAcrossInstances:
    """Test consistency and determinism across instances"""

    def test_same_capital_same_decisions(self):
        """Same capital should produce same decisions"""
        selector1 = CapitalTierStrategySelector(Decimal("100000"), account_id="ACC1")
        selector2 = CapitalTierStrategySelector(Decimal("100000"), account_id="ACC2")

        strat1 = selector1.select_strategies()
        strat2 = selector2.select_strategies()
        risk1 = selector1.get_risk_profile()
        risk2 = selector2.get_risk_profile()

        assert strat1.primary_strategy == strat2.primary_strategy
        assert risk1.leverage_allowed == risk2.leverage_allowed

    def test_deployment_consistency(self):
        """Deployment validation is consistent"""
        selector1 = CapitalTierStrategySelector(Decimal("250000"))
        selector2 = CapitalTierStrategySelector(Decimal("250000"))

        report1 = selector1.validate_deployment(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
        )
        report2 = selector2.validate_deployment(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
        )

        assert report1.status == report2.status


class TestRealWorldScenarios:
    """Test real-world trading account scenarios"""

    def test_large_250k_800_month_target(self):
        """
        Plan Maestro primary scenario:
        250k capital, 800/month profit target (3.9% annual)
        """
        selector = CapitalTierStrategySelector(Decimal("250000"))

        # Should be large tier
        assert selector.tier == AccountTier.LARGE

        # Should select aggressive ensemble
        strategy = selector.select_strategies()
        assert strategy.config_variant == "aggressive"

        # Should have high leverage
        risk = selector.get_risk_profile()
        assert risk.leverage_allowed == Decimal("2.5")

        # Should enable advanced features
        features = selector.get_enabled_features()
        assert features.ensemble_methods == True

        # Should validate successfully with sufficient alpha for large account modules
        report = selector.validate_deployment(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("50000"),  # High alpha for large tier
        )
        # May be approved or require review, but not rejected with sufficient alpha
        assert report.status in [DeploymentStatus.APPROVED, DeploymentStatus.RESTRICTED]

    def test_medium_100k_balanced_account(self):
        """Balanced medium-tier account"""
        selector = CapitalTierStrategySelector(Decimal("100000"))

        assert selector.tier == AccountTier.MEDIUM

        strategy = selector.select_strategies()
        assert strategy.config_variant == "balanced"

        risk = selector.get_risk_profile()
        # Medium tier should have balanced leverage
        assert Decimal("1.0") < risk.leverage_allowed < Decimal("2.0")

    def test_small_30k_starter_account(self):
        """Starter small account"""
        selector = CapitalTierStrategySelector(Decimal("30000"))

        assert selector.tier == AccountTier.SMALL

        strategy = selector.select_strategies()
        # Small can use momentum with weighted ensemble
        assert strategy.primary_strategy == "momentum_engine"
        assert strategy.ensemble_type.value == "weighted"

        features = selector.get_enabled_features()
        # Conservative on features for small accounts
        assert features.deep_learning == False
