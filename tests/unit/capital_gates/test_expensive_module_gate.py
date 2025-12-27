"""
Unit Tests for T0.2.2: Expensive Module Gate

Tests six critical scenarios:
1. Module enabling/disabling on different capital tiers
2. Cost estimation accuracy
3. Cost-benefit ratio enforcement
4. Module recommendations by tier
5. Total cost calculation
6. Fallback suggestions
"""

from decimal import Decimal

from app.services.expensive_module_gate import ExpenseLevelEnum, ExpensiveModuleGate


class TestExpensiveModuleGate:
    """Tests for expensive module enabling/disabling"""

    def test_transformer_engine_disabled_small_capital(self):
        """
        TransformerEngine is VERY_EXPENSIVE, needs $100k minimum.
        Small account ($10k) should have it disabled.
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="transformer_engine",
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("100"),
        )

        assert should_enable == False
        assert analysis["recommendation"] == "DISABLE"
        assert "fallback" in analysis
        assert analysis["fallback"] == "supervised_learning_engine"

    def test_transformer_engine_enabled_large_capital(self):
        """
        TransformerEngine enabled on $100k+ capital
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="transformer_engine",
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("500"),
        )

        assert should_enable == True
        assert analysis["recommendation"] == "ENABLE"
        assert analysis["enabled"] == True

    def test_deep_learning_disabled_small_capital(self):
        """
        DeepLearningEngine needs $50k minimum.
        Small account ($25k) should have it disabled.
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("25000"),
            expected_monthly_alpha=Decimal("200"),
        )

        assert should_enable == False
        assert analysis["recommendation"] == "DISABLE"
        assert "$50,000" in analysis["reason"]

    def test_deep_learning_enabled_medium_capital(self):
        """
        DeepLearningEngine enabled on $50k+ capital
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("300"),
        )

        assert should_enable == True
        assert analysis["recommendation"] == "ENABLE"

    def test_transfer_learning_enabled_small_capital(self):
        """
        TransferLearning has lower minimum ($25k).
        Should be enabled on $30k account.
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="transfer_learning",
            capital=Decimal("30000"),
            expected_monthly_alpha=Decimal("200"),
        )

        assert should_enable == True
        assert analysis["recommendation"] == "ENABLE"

    def test_feature_importance_enabled_medium_capital(self):
        """
        FeatureImportance is MODERATE expense, $25k minimum.
        Should be enabled on $40k account.
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="feature_importance_analysis",
            capital=Decimal("40000"),
            expected_monthly_alpha=Decimal("200"),
        )

        assert should_enable == True
        assert analysis["recommendation"] == "ENABLE"

    def test_invalid_module_name(self):
        """
        Invalid module name should return not found
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="nonexistent_module",
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("100"),
        )

        assert should_enable == False
        assert analysis["recommendation"] == "NOT_FOUND"

    def test_zero_capital_rejected(self):
        """Zero capital should be rejected"""
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("0"),
            expected_monthly_alpha=Decimal("100"),
        )

        assert should_enable == False
        assert analysis["recommendation"] == "INCREASE_CAPITAL"

    def test_cost_estimation_transformer_engine(self):
        """
        TransformerEngine cost: 2% of capital
        $100k capital should have ~$2k/month cost
        """
        _, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="transformer_engine",
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("1000"),
        )

        expected_cost = Decimal("100000") * Decimal("0.02")
        assert abs(analysis["cost_estimate_monthly"] - expected_cost) < Decimal("10")

    def test_cost_estimation_deep_learning_engine(self):
        """
        DeepLearningEngine cost: 1% of capital
        $100k capital should have ~$1k/month cost
        """
        _, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("1000"),
        )

        expected_cost = Decimal("100000") * Decimal("0.01")
        assert abs(analysis["cost_estimate_monthly"] - expected_cost) < Decimal("10")

    def test_cost_ratio_with_alpha(self):
        """
        Test cost-benefit ratio calculation.
        Cost ratio = cost / alpha
        """
        _, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),
        )

        # Cost: $50k * 1% = $500
        # Ratio: $500 / $500 = 100%
        expected_ratio = Decimal("500") / Decimal("500")  # = 1.0
        assert abs(analysis["cost_ratio"] - expected_ratio) < Decimal("0.1")


class TestModuleRecommendations:
    """Test module recommendations by capital tier"""

    def test_micro_tier_recommendations(self):
        """
        Micro tier ($10k): All expensive modules disabled
        """
        recommendations = ExpensiveModuleGate.get_recommended_modules(capital=Decimal("10000"))

        # All should be False for micro tier
        assert recommendations["transformer_engine"] == False
        assert recommendations["deep_learning_engine"] == False
        assert recommendations["reinforcement_learning_engine"] == False
        assert recommendations["hyperparameter_optimizer"] == False

    def test_small_tier_recommendations(self):
        """
        Small tier ($25k): Most expensive modules disabled
        Only simple transfer learning and feature analysis might be enabled
        """
        recommendations = ExpensiveModuleGate.get_recommended_modules(capital=Decimal("25000"))

        # Deep learning should still be disabled
        assert recommendations["deep_learning_engine"] == False
        assert recommendations["transformer_engine"] == False

    def test_medium_tier_recommendations(self):
        """
        Medium tier ($100k): Moderate modules enabled
        """
        recommendations = ExpensiveModuleGate.get_recommended_modules(capital=Decimal("100000"))

        # Moderate modules should be enabled
        assert recommendations["transfer_learning"] == True
        assert recommendations["feature_importance_analysis"] == True
        assert recommendations["deep_learning_engine"] == True
        assert recommendations["hyperparameter_optimizer"] == True
        # Transformer is VERY_EXPENSIVE and should be disabled even at $100k
        assert recommendations["transformer_engine"] == False

    def test_large_tier_recommendations(self):
        """
        Large tier ($500k): All modules enabled
        """
        recommendations = ExpensiveModuleGate.get_recommended_modules(capital=Decimal("500000"))

        # All should be True for large tier
        assert recommendations["transformer_engine"] == True
        assert recommendations["deep_learning_engine"] == True
        assert recommendations["reinforcement_learning_engine"] == True
        assert recommendations["hyperparameter_optimizer"] == True

    def test_capital_tier_classification(self):
        """Test capital tier boundaries"""
        # Micro
        assert ExpensiveModuleGate._get_capital_tier(Decimal("5000")) == "micro"
        assert ExpensiveModuleGate._get_capital_tier(Decimal("14999")) == "micro"

        # Small
        assert ExpensiveModuleGate._get_capital_tier(Decimal("15000")) == "small"
        assert ExpensiveModuleGate._get_capital_tier(Decimal("49999")) == "small"

        # Medium
        assert ExpensiveModuleGate._get_capital_tier(Decimal("50000")) == "medium"
        assert ExpensiveModuleGate._get_capital_tier(Decimal("249999")) == "medium"

        # Large
        assert ExpensiveModuleGate._get_capital_tier(Decimal("250000")) == "large"
        assert ExpensiveModuleGate._get_capital_tier(Decimal("1000000")) == "large"


class TestGetEnabledModules:
    """Test bulk module enabling/disabling"""

    def test_get_enabled_modules_micro_account(self):
        """
        Micro account should have all expensive modules disabled
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("100"),
        )

        # All modules should be disabled
        assert all(enabled == False for enabled in enabled_modules.values())

    def test_get_enabled_modules_medium_account(self):
        """
        Medium account should have some modules enabled
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("500"),
        )

        # Some modules should be enabled
        assert any(enabled == True for enabled in enabled_modules.values())
        # Deep learning should be enabled
        assert enabled_modules["deep_learning_engine"] == True

    def test_get_enabled_modules_large_account(self):
        """
        Large account should have most modules enabled
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("500000"),
            expected_monthly_alpha=Decimal("2000"),
        )

        # Most modules should be enabled
        enabled_count = sum(1 for v in enabled_modules.values() if v)
        assert enabled_count >= 4  # At least 4 modules


class TestCostCalculation:
    """Test total cost calculation"""

    def test_total_cost_single_module(self):
        """
        Calculate cost for a single enabled module
        """
        capital = Decimal("100000")
        enabled_modules = {
            "transformer_engine": False,
            "deep_learning_engine": True,  # 1% = $1000/month
            "reinforcement_learning_engine": False,
            "multitask_learning_engine": False,
            "transfer_learning": False,
            "hyperparameter_optimizer": False,
            "feature_importance_analysis": False,
        }

        total_cost = ExpensiveModuleGate.get_total_expensive_module_cost(capital, enabled_modules)

        expected_cost = Decimal("100000") * Decimal("0.01")
        assert abs(total_cost - expected_cost) < Decimal("10")

    def test_total_cost_multiple_modules(self):
        """
        Calculate cost for multiple enabled modules (cost stacks)
        """
        capital = Decimal("200000")
        enabled_modules = {
            "transformer_engine": False,
            "deep_learning_engine": True,  # 1%
            "reinforcement_learning_engine": True,  # 1%
            "multitask_learning_engine": False,
            "transfer_learning": True,  # 0.5%
            "hyperparameter_optimizer": False,
            "feature_importance_analysis": True,  # 0.5%
        }

        total_cost = ExpensiveModuleGate.get_total_expensive_module_cost(capital, enabled_modules)

        # Total: 1% + 1% + 0.5% + 0.5% = 3%
        expected_cost = Decimal("200000") * Decimal("0.03")
        assert abs(total_cost - expected_cost) < Decimal("10")

    def test_cost_summary(self):
        """
        Test comprehensive cost summary
        """
        capital = Decimal("100000")
        enabled_modules = {
            "transformer_engine": True,  # 2%
            "deep_learning_engine": True,  # 1%
            "reinforcement_learning_engine": False,
            "multitask_learning_engine": False,
            "transfer_learning": False,
            "hyperparameter_optimizer": False,
            "feature_importance_analysis": False,
        }
        expected_alpha = Decimal("500")

        summary = ExpensiveModuleGate.get_cost_summary(capital, enabled_modules, expected_alpha)

        # Total cost: 3% = $3000
        assert summary["total_cost_monthly"] == Decimal("3000")
        # Cost ratio: $3000 / $500 = 600%
        assert summary["cost_ratio_of_alpha"] == Decimal("6")
        # Should be COST_CRITICAL
        assert summary["recommendation"] == "COST_CRITICAL"
        # Enabled count: 2 modules
        assert summary["enabled_module_count"] == 2


class TestRealWorldScenarios:
    """Test realistic scenarios"""

    def test_retail_account_10k_capital(self):
        """
        Typical retail account with $10k capital.
        All expensive modules should be disabled.
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),
        )

        # All expensive modules disabled
        assert all(v == False for v in enabled_modules.values())

        # No cost
        total_cost = ExpensiveModuleGate.get_total_expensive_module_cost(
            Decimal("10000"), enabled_modules
        )
        assert total_cost == Decimal("0")

    def test_semi_pro_trader_50k_capital(self):
        """
        Semi-professional trader with $50k capital.
        Deep learning should be enabled, transfer learning optional.
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("300"),
        )

        # Deep learning should be borderline enabled
        assert enabled_modules["deep_learning_engine"] == True
        # Transfer learning should be enabled
        assert enabled_modules["transfer_learning"] == True
        # Transformer should be disabled
        assert enabled_modules["transformer_engine"] == False

    def test_professional_trader_500k_capital(self):
        """
        Professional trader with $500k capital.
        Most expensive modules should be enabled.
        """
        enabled_modules, analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("500000"),
            expected_monthly_alpha=Decimal("2000"),
        )

        # Most expensive modules enabled
        enabled_count = sum(1 for v in enabled_modules.values() if v)
        assert enabled_count >= 5  # At least 5 modules


class TestStrictCostRatioEnforcement:
    """Test strict cost-ratio enforcement"""

    def test_deep_learning_cost_ratio_acceptable(self):
        """
        With strict cost ratio: cost must be <30% of alpha
        $50k capital, deep learning $500/mo, $2000 alpha
        Cost ratio: 25% → ENABLED
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("2000"),
            enforce_strict_cost_ratio=True,
        )

        # Cost: $50k * 1% = $500
        # Ratio: $500 / $2000 = 25%
        assert should_enable == True
        assert analysis["cost_ratio"] < Decimal("0.30")

    def test_deep_learning_cost_ratio_excessive(self):
        """
        With strict cost ratio: cost must be <30% of alpha
        $50k capital, deep learning $500/mo, $500 alpha
        Cost ratio: 100% → DISABLED
        """
        should_enable, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),
            enforce_strict_cost_ratio=True,
        )

        # Cost: $50k * 1% = $500
        # Ratio: $500 / $500 = 100%
        assert should_enable == False
        assert analysis["cost_ratio"] > Decimal("0.30")


class TestModuleInfo:
    """Test module information and metadata"""

    def test_module_expense_levels(self):
        """Test module expense level classifications"""
        modules = ExpensiveModuleGate.MODULES

        # Check expense levels
        assert modules["transformer_engine"]["expense_level"] == ExpenseLevelEnum.VERY_EXPENSIVE
        assert modules["deep_learning_engine"]["expense_level"] == ExpenseLevelEnum.EXPENSIVE
        assert modules["transfer_learning"]["expense_level"] == ExpenseLevelEnum.MODERATE
        assert modules["feature_importance_analysis"]["expense_level"] == ExpenseLevelEnum.MODERATE

    def test_module_fallbacks(self):
        """Test fallback suggestions for disabled modules"""
        _, analysis_transformer = ExpensiveModuleGate.should_enable_module(
            module_name="transformer_engine",
            capital=Decimal("10000"),
        )
        # Transformer should fallback to supervised learning
        assert analysis_transformer["fallback"] == "supervised_learning_engine"

        _, analysis_transfer = ExpensiveModuleGate.should_enable_module(
            module_name="transfer_learning",
            capital=Decimal("10000"),
        )
        # Transfer learning fallback is "none" (can be disabled gracefully)
        assert analysis_transfer["fallback"] == "none"

    def test_log_module_decision(self):
        """Test logging functionality"""
        _, analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=Decimal("100000"),
        )

        log_msg = ExpensiveModuleGate.log_module_decision(
            module_name="deep_learning_engine",
            capital=Decimal("100000"),
            analysis=analysis,
            account_id="TEST_001",
        )

        assert "TEST_001" in log_msg
        assert "deep_learning_engine" in log_msg
        assert "ENABLE" in log_msg or "DISABLE" in log_msg
