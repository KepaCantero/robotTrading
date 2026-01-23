"""
Unit Tests for T0.1.1: Capital Viability Validator

Tests three critical scenarios:
1. Unreachable goal on small capital ($10k)
2. Reachable goal on large capital ($100k)
3. Boundary condition (exactly at threshold)
"""

from decimal import Decimal

from app.services.capital_viability_gate import CapitalViabilityValidator


class TestCapitalViabilityValidator:
    """Tests for profit goal viability detection"""

    def test_unreachable_goal_10k_capital_500_monthly(self):
        """
        Scenario: $10k capital, $3000/month goal (30% of capital!)
        Expected: UNREACHABLE - requires ~30% alpha, achievable ~2%
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("3000"),  # $3000 = 30% of capital is insane
            tax_rate=Decimal("0.40"),  # 40% tax
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
            expected_alpha_per_trade=None,  # Use default estimate
        )

        assert not result["is_viable"]
        assert "UNREACHABLE" in result["reason"] or "DIFFICULT" in result["reason"]
        assert result["severity"] == "CRITICAL"
        assert result["recommendation"] in ["INCREASE_CAPITAL", "REDUCE_GOAL"]
        assert result["required_alpha_pct"] > Decimal("0.20")  # > 20% = CRITICAL

    def test_reachable_goal_100k_capital_500_monthly(self):
        """
        Scenario: $100k capital, $500/month goal
        Expected: REACHABLE - requires ~0.75% alpha, achievable ~5%
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("100000"),
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
            expected_alpha_per_trade=None,
        )

        assert result["is_viable"]
        assert result["severity"] == "OK"
        assert result["recommendation"] == "PROCEED"
        assert result["required_alpha_pct"] < Decimal("0.10")
        assert result["expected_alpha_pct"] >= result["required_alpha_pct"]

    def test_boundary_condition_25k_capital_exact_threshold(self):
        """
        Scenario: $25k capital, goal at exact viability boundary
        Expected: Test boundary handling
        """
        # Goal that pushes alpha requirement to ~10% (boundary)
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("25000"),
            monthly_goal=Decimal("250"),  # $250/month on $25k = 1%/month
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
            expected_alpha_per_trade=None,
        )

        # Should be viable - 1% is achievable
        assert result["is_viable"]
        assert result["recommendation"] == "PROCEED"

    def test_minimum_viable_capital_calculation(self):
        """
        Test: What capital is needed for $500/month goal?
        Expected: Formula calculates correctly
        """
        min_capital = CapitalViabilityValidator.get_minimum_viable_capital(
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
            target_alpha_pct=Decimal("0.05"),  # 5% achievable
        )

        # Verify it's reasonable (at least $10k)
        assert min_capital > Decimal("10000")
        # Gross goal: $500 / 0.6 = $833.33
        # Commission: $15 * 10 = $150
        # Total needed: $983.33
        # Capital at 5% alpha: $983.33 / 0.05 = $19,666
        assert min_capital < Decimal("50000")

        # Validate the calculated capital is actually viable
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=min_capital,
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )
        assert result["is_viable"]

    def test_zero_capital_rejected(self):
        """Zero or negative capital should be rejected"""
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("0"),
            monthly_goal=Decimal("100"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        assert not result["is_viable"]
        assert result["severity"] == "CRITICAL"

    def test_negative_goal_rejected(self):
        """Negative profit goal should be rejected"""
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("-500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        assert not result["is_viable"]

    def test_invalid_tax_rate_rejected(self):
        """Tax rate >= 100% or < 0% should be rejected"""
        # Test 100% tax
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("1.0"),  # 100% tax
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        assert not result["is_viable"]
        assert result["severity"] == "CRITICAL"

        # Test negative tax
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("-0.10"),  # Negative tax
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        assert not result["is_viable"]

    def test_high_commission_scenario(self):
        """
        Test: High commission environment (forex, fees, etc.)
        Expected: Increases required capital significantly
        """
        result_low_commission = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("20000"),
            monthly_goal=Decimal("200"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("5"),  # Low commission
            expected_trades_per_month=10,
        )

        result_high_commission = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("20000"),
            monthly_goal=Decimal("200"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("50"),  # High commission
            expected_trades_per_month=10,
        )

        # High commission should require more alpha
        assert (
            result_high_commission["required_alpha_pct"]
            > result_low_commission["required_alpha_pct"]
        )

        # Low commission should be viable, high commission might not be
        if not result_high_commission["is_viable"]:
            assert result_low_commission["is_viable"]

    def test_log_viability_check(self, caplog):
        """
        Test: Logging for audit trail
        Expected: Creates audit trail entry
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("50000"),
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        log_msg = CapitalViabilityValidator.log_viability_check(
            capital=Decimal("50000"),
            monthly_goal=Decimal("500"),
            result=result,
            account_id="TEST_ACCOUNT_001",
        )

        # Verify log message contains key info
        assert "TEST_ACCOUNT_001" in log_msg
        assert "$50,000" in log_msg
        assert "$500" in log_msg
        assert "VIABLE" in log_msg or "UNREACHABLE" in log_msg


class TestCapitalTierRequirements:
    """Test requirements for different capital tiers"""

    def test_micro_tier_10k_challenges(self):
        """
        Micro tier ($10k): Most goals unreachable
        """
        # Very modest goal: $100/month
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("100"),  # 1% monthly
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=5,
        )

        # Even modest goals are hard on $10k
        # Required alpha: ($100/0.6 + $75) / $10k = 2.25%
        # Achievable: 2% (for $10k accounts)
        # Should be right on boundary
        assert result["severity"] in ["OK", "WARNING"]

    def test_small_tier_25k_viable(self):
        """
        Small tier ($25k): Reasonable goals become viable
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("25000"),
            monthly_goal=Decimal("200"),  # 0.8% monthly on $25k
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        # Should be viable
        assert result["is_viable"]
        assert result["severity"] == "OK"

    def test_medium_tier_50k_flexible(self):
        """
        Medium tier ($50k): Good flexibility in goal setting
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("50000"),
            monthly_goal=Decimal("500"),  # 1% monthly on $50k
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        # Should be easily viable
        assert result["is_viable"]
        assert result["severity"] == "OK"
        assert result["required_alpha_pct"] < Decimal("0.04")


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_zero_goal_with_no_trades(self):
        """$0 goal with $0 trades should always be viable"""
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("1000"),
            monthly_goal=Decimal("0"),  # $0 goal
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=0,  # No trades means no commission cost
        )

        assert result["is_viable"]
        # No alpha needed if goal is $0 and no trades
        assert result["required_alpha_pct"] == Decimal("0")

    def test_zero_trades_per_month_with_nonzero_goal(self):
        """
        If no trades expected, any non-zero goal is viable
        (because there are no commission costs)
        """
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000"),
            monthly_goal=Decimal("100"),  # Any goal
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=0,  # No trades = no commission
        )

        # With zero trades, commissions are zero, so goal is viable
        # (Though practically unrealistic to make $100 with zero trades)
        assert result["is_viable"]
        assert result["required_alpha_pct"] < Decimal("0.02")  # Very small alpha needed

    def test_very_high_capital(self):
        """Very high capital should make any goal viable"""
        result = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("10000000"),  # $10M
            monthly_goal=Decimal("50000"),  # $50k/month
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        # Should be viable
        assert result["is_viable"]
        # Required alpha should be tiny (<1%)
        assert result["required_alpha_pct"] < Decimal("0.01")
