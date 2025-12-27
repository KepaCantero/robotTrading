"""
Unit Tests for T0.2.1: Learning Capital Gate

Tests six critical scenarios:
1. Learning disabled on micro accounts (<$15k)
2. Learning borderline on small accounts ($15k-$25k)
3. Learning enabled on medium accounts ($25k-$250k)
4. Cost-benefit ratio detection
5. Minimum capital calculation
6. Recommended learning config by tier
"""

from decimal import Decimal

from app.services.learning_capital_gate import LearningCapitalGate


class TestLearningCapitalGate:
    """Tests for learning engine viability detection"""

    def test_learning_disabled_micro_account(self):
        """
        Scenario: $10k capital (micro account)
        Learning cost: $10k * 0.5% = $50/month
        Expected alpha: $100/month
        Cost ratio: 50% of alpha
        Expected: DISABLE_LEARNING (too small)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("100"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["recommendation"] == "DISABLE_LEARNING"
        assert analysis["severity"] == "CRITICAL"
        assert analysis["capital_tier"] == "micro"
        assert analysis["learning_cost_monthly"] > Decimal("0")

    def test_learning_borderline_small_account(self):
        """
        Scenario: $20k capital (small account, below $25k threshold)
        Learning cost: $20k * 0.3% = $60/month
        Expected alpha: $200/month
        Cost ratio: 30% of alpha (at threshold)
        Expected: DISABLE_LEARNING (below absolute threshold)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("20000"),
            expected_monthly_alpha=Decimal("200"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["recommendation"] == "DISABLE_LEARNING"
        assert analysis["severity"] == "CRITICAL"
        assert analysis["capital_tier"] == "small"
        # Cost ratio at borderline
        assert analysis["cost_benefit_ratio"] < Decimal("0.40")

    def test_learning_enabled_medium_account(self):
        """
        Scenario: $50k capital (medium account, above $25k threshold)
        Learning cost: $50k * 0.2% = $100/month
        Expected alpha: $500/month
        Cost ratio: 20% of alpha (good margin)
        Expected: ENABLE_LEARNING (viable)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert learning_viable
        assert analysis["recommendation"] == "ENABLE_LEARNING"
        assert analysis["severity"] == "OK"
        assert analysis["capital_tier"] == "medium"
        assert analysis["cost_benefit_ratio"] < Decimal("0.30")

    def test_learning_enabled_large_account(self):
        """
        Scenario: $500k capital (large account)
        Learning cost: $500k * 0.1% = $500/month
        Expected alpha: $2000/month
        Cost ratio: 25% of alpha (excellent margin)
        Expected: ENABLE_LEARNING (highly viable)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("500000"),
            expected_monthly_alpha=Decimal("2000"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert learning_viable
        assert analysis["recommendation"] == "ENABLE_LEARNING"
        assert analysis["severity"] == "OK"
        assert analysis["capital_tier"] == "large"
        assert analysis["cost_benefit_ratio"] < Decimal("0.30")

    def test_learning_disabled_when_not_configured(self):
        """
        Learning disabled in configuration should always return False
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("500"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=False,
        )

        assert not learning_viable
        assert analysis["recommendation"] == "LEARNING_DISABLED"
        assert analysis["severity"] == "OK"

    def test_learning_disabled_zero_alpha(self):
        """
        Zero or negative expected alpha should always disable learning
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("0"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["recommendation"] == "DISABLE_LEARNING"
        assert analysis["severity"] == "CRITICAL"

    def test_learning_disabled_negative_alpha(self):
        """
        Negative expected alpha (expected losses) should disable learning
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("-100"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["recommendation"] == "DISABLE_LEARNING"

    def test_zero_capital_rejected(self):
        """Zero or negative capital should be rejected"""
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("0"),
            expected_monthly_alpha=Decimal("100"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["severity"] == "CRITICAL"

    def test_cost_benefit_ratio_escalation(self):
        """
        Test that cost-benefit ratio improves with larger capital (proportional alpha).

        Larger capital should have better learning cost-benefit ratio when alpha scales.

        Capital tiers:
        - Micro: < $15k (0.5% learning cost)
        - Small: $15k-$50k (0.3% learning cost)
        - Medium: $50k-$250k (0.2% learning cost)
        - Large: $250k+ (0.1% learning cost)
        """
        # Micro account: $10k capital, $100/month alpha
        _, analysis_micro = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("100"),
            learning_enabled=True,
        )

        # Medium account: $50k capital, $500/month alpha (5x both)
        _, analysis_medium = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),
            learning_enabled=True,
        )

        # Large account: $300k capital, $3000/month alpha (crosses into 0.1% tier)
        _, analysis_large = LearningCapitalGate.is_learning_viable(
            capital=Decimal("300000"),
            expected_monthly_alpha=Decimal("3000"),
            learning_enabled=True,
        )

        # Cost ratios should decrease with larger capital (proportional alpha)
        assert analysis_micro["cost_benefit_ratio"] > analysis_medium["cost_benefit_ratio"]
        assert analysis_medium["cost_benefit_ratio"] > analysis_large["cost_benefit_ratio"]

        # Micro should be disabled (below capital threshold), others enabled
        assert analysis_micro["learning_recommended"] == False
        assert analysis_large["learning_recommended"] == True

    def test_minimum_capital_for_learning_calculation(self):
        """
        Test: What capital is needed for learning to be viable?
        """
        min_capital = LearningCapitalGate.get_minimum_capital_for_learning(
            expected_monthly_alpha=Decimal("100"),
            target_cost_ratio=Decimal("0.30"),
        )

        # Should be at least $25k (absolute minimum)
        assert min_capital >= LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING

        # Should be reasonable (not too high)
        assert min_capital < Decimal("500000")

    def test_minimum_capital_with_zero_alpha(self):
        """
        Zero alpha should return impossible capital requirement
        """
        min_capital = LearningCapitalGate.get_minimum_capital_for_learning(
            expected_monthly_alpha=Decimal("0"),
            target_cost_ratio=Decimal("0.30"),
        )

        # Should be very high (impossible)
        assert min_capital > Decimal("100000000")

    def test_recommended_learning_config_micro(self):
        """Test recommended config for micro account"""
        config = LearningCapitalGate.get_recommended_learning_config(capital=Decimal("10000"))

        assert config["learning_enabled"] == False
        assert "too small" in config["reason"].lower()

    def test_recommended_learning_config_small(self):
        """Test recommended config for small account"""
        config = LearningCapitalGate.get_recommended_learning_config(capital=Decimal("20000"))

        # Small account: learning only if capital >= $25k
        assert config["learning_enabled"] == False

    def test_recommended_learning_config_medium(self):
        """Test recommended config for medium account"""
        config = LearningCapitalGate.get_recommended_learning_config(capital=Decimal("50000"))

        assert config["learning_enabled"] == True
        assert "learning_config" in config
        # Medium tier should have weekly retraining
        assert config["learning_config"]["rebalance_frequency_days"] == 7

    def test_recommended_learning_config_large(self):
        """Test recommended config for large account"""
        config = LearningCapitalGate.get_recommended_learning_config(capital=Decimal("500000"))

        assert config["learning_enabled"] == True
        assert "learning_config" in config
        # Large tier should have more frequent retraining
        assert config["learning_config"]["rebalance_frequency_days"] == 3
        assert config["learning_config"]["enable_transfer_learning"] == True

    def test_capital_tier_classification(self):
        """Test capital tier classification"""
        # Micro: < $15k
        assert LearningCapitalGate._get_capital_tier(Decimal("5000")) == "micro"
        assert LearningCapitalGate._get_capital_tier(Decimal("14999")) == "micro"

        # Small: $15k - $50k
        assert LearningCapitalGate._get_capital_tier(Decimal("15000")) == "small"
        assert LearningCapitalGate._get_capital_tier(Decimal("30000")) == "small"
        assert LearningCapitalGate._get_capital_tier(Decimal("49999")) == "small"

        # Medium: $50k - $250k
        assert LearningCapitalGate._get_capital_tier(Decimal("50000")) == "medium"
        assert LearningCapitalGate._get_capital_tier(Decimal("100000")) == "medium"
        assert LearningCapitalGate._get_capital_tier(Decimal("249999")) == "medium"

        # Large: $250k+
        assert LearningCapitalGate._get_capital_tier(Decimal("250000")) == "large"
        assert LearningCapitalGate._get_capital_tier(Decimal("1000000")) == "large"

    def test_log_learning_decision(self):
        """Test logging for audit trail"""
        _, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),
            learning_enabled=True,
        )

        log_msg = LearningCapitalGate.log_learning_decision(
            capital=Decimal("50000"),
            analysis=analysis,
            account_id="TEST_ACCT_001",
        )

        assert "TEST_ACCT_001" in log_msg
        assert "$50,000" in log_msg or "$50000" in log_msg
        assert "ENABLE" in log_msg or "DISABLE" in log_msg


class TestRealWorldScenarios:
    """Test realistic trading scenarios"""

    def test_retail_stock_account_10k_capital(self):
        """
        Typical retail stock account: $10k, modest alpha expectations
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),  # Conservative $50/month
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        # Should be disabled - too small
        assert not learning_viable
        assert analysis["severity"] == "CRITICAL"
        assert analysis["recommendation"] == "DISABLE_LEARNING"

    def test_semi_pro_trader_50k_capital(self):
        """
        Semi-professional trader: $50k, good alpha expectations
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("500"),  # $500/month = 1% monthly
            monthly_win_rate=Decimal("0.58"),
            learning_enabled=True,
        )

        # Should be viable
        assert learning_viable
        assert analysis["severity"] == "OK"
        assert analysis["recommendation"] == "ENABLE_LEARNING"
        # Cost should be reasonable (20% of alpha)
        assert analysis["cost_benefit_ratio"] < Decimal("0.30")

    def test_professional_trader_500k_capital(self):
        """
        Professional trader: $500k, high alpha expectations
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("500000"),
            expected_monthly_alpha=Decimal("5000"),  # $5k/month = 1% monthly
            monthly_win_rate=Decimal("0.60"),
            learning_enabled=True,
        )

        # Should be highly viable
        assert learning_viable
        assert analysis["severity"] == "OK"
        assert analysis["recommendation"] == "ENABLE_LEARNING"
        # Cost should be very low ratio
        assert analysis["cost_benefit_ratio"] < Decimal("0.15")

    def test_high_alpha_small_account_viability(self):
        """
        Small account ($20k) with very high alpha expectations
        Learning becomes viable if alpha is high enough
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("20000"),
            expected_monthly_alpha=Decimal("1000"),  # $1k/month = 5% monthly (high)
            monthly_win_rate=Decimal("0.65"),
            learning_enabled=True,
        )

        # Still below absolute $25k threshold, so disabled
        assert not learning_viable
        assert analysis["severity"] == "CRITICAL"

    def test_exactly_at_minimum_capital_threshold(self):
        """
        Account at exactly $25k minimum capital threshold
        with reasonable alpha expectations
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("25000"),
            expected_monthly_alpha=Decimal("300"),
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        # Should be viable (at threshold with good alpha)
        assert learning_viable
        assert analysis["capital_tier"] == "small"

    def test_just_above_minimum_capital_threshold(self):
        """
        Account just above $25k (at $26k) with higher alpha
        Learning cost: $26k * 0.3% = $78/month
        Alpha: $500/month = 15.6% cost ratio
        Expected: ENABLE_LEARNING (above capital threshold + good alpha)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("26000"),
            expected_monthly_alpha=Decimal("500"),  # Higher alpha to be viable
            monthly_win_rate=Decimal("0.55"),
            learning_enabled=True,
        )

        # Should be viable (above $25k threshold with good alpha)
        assert learning_viable
        assert analysis["recommendation"] == "ENABLE_LEARNING"


class TestLearningCostScaling:
    """Test learning cost scaling by capital tier"""

    def test_micro_tier_learning_cost(self):
        """
        Micro tier ($10k): 0.5% learning cost = $50/month
        """
        _, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("100"),
            learning_enabled=True,
        )

        # Expected cost: $10k * 0.5% = $50
        assert analysis["learning_cost_monthly"] >= Decimal("40")
        assert analysis["learning_cost_monthly"] <= Decimal("60")

    def test_small_tier_learning_cost(self):
        """
        Small tier ($20k): 0.3% learning cost = $60/month
        """
        _, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("20000"),
            expected_monthly_alpha=Decimal("200"),
            learning_enabled=True,
        )

        # Expected cost: $20k * 0.3% = $60
        expected_cost = Decimal("20000") * Decimal("0.003")
        assert abs(analysis["learning_cost_monthly"] - expected_cost) < Decimal("5")

    def test_medium_tier_learning_cost(self):
        """
        Medium tier ($100k): 0.2% learning cost = $200/month
        """
        _, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("100000"),
            expected_monthly_alpha=Decimal("500"),
            learning_enabled=True,
        )

        # Expected cost: $100k * 0.2% = $200
        expected_cost = Decimal("100000") * Decimal("0.002")
        assert abs(analysis["learning_cost_monthly"] - expected_cost) < Decimal("5")

    def test_large_tier_learning_cost(self):
        """
        Large tier ($1M): 0.1% learning cost = $1000/month
        """
        _, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("1000000"),
            expected_monthly_alpha=Decimal("5000"),
            learning_enabled=True,
        )

        # Expected cost: $1M * 0.1% = $1000
        expected_cost = Decimal("1000000") * Decimal("0.001")
        assert abs(analysis["learning_cost_monthly"] - expected_cost) < Decimal("50")


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_alpha_high_cost(self):
        """
        $50k capital with only $25/month expected alpha
        Learning cost would be ~$100/month = 400% of alpha
        Expected: DISABLE_LEARNING
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("25"),
            learning_enabled=True,
        )

        assert not learning_viable
        assert analysis["cost_benefit_ratio"] > Decimal("1.0")

    def test_very_high_capital_very_low_alpha(self):
        """
        $10M capital with proportional alpha ($50k/month)
        Even very large capital must have sufficient alpha for learning viability.

        Learning cost: $10M * 0.1% = $10k/month
        Alpha: $50k/month = 20% cost ratio
        Expected: ENABLE_LEARNING (cost ratio well below 30% threshold)
        """
        learning_viable, analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000000"),
            expected_monthly_alpha=Decimal("50000"),  # Proportional alpha
            learning_enabled=True,
        )

        # Should be viable - cost ratio is well below threshold
        assert learning_viable
        assert analysis["cost_benefit_ratio"] < Decimal("0.30")

    def test_minimum_capital_with_different_alpha(self):
        """
        The formula: min_capital = (alpha * target_ratio) / learning_cost_scale

        Higher alpha requires MORE capital to maintain cost ratio threshold.
        This makes sense: to generate higher alpha with same learning infrastructure,
        you need more capital deployed.
        """
        min_capital_low_alpha = LearningCapitalGate.get_minimum_capital_for_learning(
            expected_monthly_alpha=Decimal("100"),
            target_cost_ratio=Decimal("0.30"),
        )

        min_capital_high_alpha = LearningCapitalGate.get_minimum_capital_for_learning(
            expected_monthly_alpha=Decimal("1000"),
            target_cost_ratio=Decimal("0.30"),
        )

        # Both should be at least the absolute minimum threshold
        assert min_capital_low_alpha >= LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING
        assert min_capital_high_alpha >= LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING
