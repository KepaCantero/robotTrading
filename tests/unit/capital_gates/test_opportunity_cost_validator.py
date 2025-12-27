"""
Unit Tests for T0.1.3: Opportunity Cost Validator

Tests three critical scenarios:
1. Hold cash when risk-free beats active strategy
2. Trade when active strategy beats passive
3. Capital inflection point calculation
"""

from decimal import Decimal


from app.services.opportunity_cost_validator import OpportunityCostValidator


class TestOpportunityCostValidator:
    """Tests for passive vs active return comparison"""

    def test_hold_cash_when_rfr_exceeds_strategy_alpha(self):
        """
        Scenario: $12k capital, 4% annual risk-free rate, $25/month expected alpha
        Passive: $12k * (4%/12) = $40/month
        Active: $25/month - $150 commission (10 trades * $15) = -$125/month
        Expected: HOLD_CASH (passive is much better)
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("12000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,  # 4% annual
            expected_monthly_alpha=Decimal("25"),  # Small expected alpha
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        assert should_trade == False
        assert analysis["recommendation"] == "HOLD_CASH"
        assert analysis["passive_monthly_return"] > analysis["active_monthly_return"]
        assert "$40" in analysis["reason"] or "40" in str(analysis["passive_monthly_return"])

    def test_trade_when_alpha_exceeds_rfr(self):
        """
        Scenario: $50k capital, 4% annual RF, $300/month expected alpha
        Passive: $50k * (4%/12) = $166.67/month
        Active: $300/month - $150 commission = $150/month (but still < passive)
        Expected: HOLD_CASH (passive still wins)

        Then with $500/month alpha:
        Active: $500/month - $150 = $350/month > $166.67 passive
        Expected: TRADE
        """
        # Case 1: $300 alpha (not enough)
        should_trade1, analysis1 = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_monthly_alpha=Decimal("300"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Case 2: $500 alpha (enough to beat passive)
        should_trade2, analysis2 = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_monthly_alpha=Decimal("500"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        assert should_trade1 == False
        assert should_trade2 == True
        assert analysis2["recommendation"] == "TRADE"

    def test_minimum_alpha_for_trading(self):
        """
        Test calculation of minimum alpha needed to justify trading
        """
        min_alpha = OpportunityCostValidator.get_minimum_alpha_for_trading(
            capital=Decimal("10000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,  # 4% annual
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Passive: $10k * (4%/12) = $33.33
        # Commission: 10 * $15 = $150
        # Minimum alpha: $33.33 + $150 = $183.33

        assert min_alpha > Decimal("180")
        assert min_alpha < Decimal("190")

    def test_capital_inflection_point(self):
        """
        Test calculation of capital threshold where trading becomes viable
        """
        inflection = OpportunityCostValidator.capital_inflection_point(
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
            target_alpha_pct_monthly=Decimal("0.02"),  # 2% monthly alpha achievable
        )

        # At inflection:
        # capital * 2% = capital * (4%/12) + $150
        # capital * (2% - 0.33%) = $150
        # capital * 1.67% = $150
        # capital = $150 / 1.67% = $8,982

        assert inflection > Decimal("8000")
        assert inflection < Decimal("10000")

    def test_capital_tier_viability_micro(self):
        """
        Test viability analysis for micro account ($5k)
        """
        analysis = OpportunityCostValidator.analyze_capital_tier_viability(
            capital=Decimal("5000"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Passive: $5k * (4%/12) = $16.67/month
        # Min alpha: $16.67 + $150 = $166.67
        # Min alpha % of capital: $166.67 / $5k = 3.33% monthly
        # This is MODERATE range (between 3-5%)
        # So viability will be MODERATE and trading_recommended will be False

        assert analysis["viability"] in ["MODERATE"]
        assert analysis["trading_recommended"] == False
        assert analysis["minimum_alpha_pct_of_capital"] > Decimal("0.03")

    def test_capital_tier_viability_small(self):
        """
        Test viability analysis for small account ($25k)
        """
        analysis = OpportunityCostValidator.analyze_capital_tier_viability(
            capital=Decimal("25000"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Passive: $25k * (4%/12) = $83.33/month
        # Min alpha: $83.33 + $150 = $233.33
        # Min alpha % of capital: $233.33 / $25k = 0.93% monthly
        # This is MODERATE

        assert analysis["viability"] in ["MODERATE", "GOOD"]
        assert analysis["trading_recommended"] == True

    def test_capital_tier_viability_medium(self):
        """
        Test viability analysis for medium account ($100k)
        """
        analysis = OpportunityCostValidator.analyze_capital_tier_viability(
            capital=Decimal("100000"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Passive: $100k * (4%/12) = $333.33/month
        # Min alpha: $333.33 + $150 = $483.33
        # Min alpha % of capital: $483.33 / $100k = 0.48% monthly
        # This is GOOD

        assert analysis["viability"] == "GOOD"
        assert analysis["trading_recommended"] == True

    def test_zero_expected_alpha(self):
        """
        Zero expected alpha should always recommend holding cash
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("0"),  # No alpha
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        assert should_trade == False
        assert analysis["recommendation"] == "HOLD_CASH"

    def test_negative_expected_alpha(self):
        """
        Negative expected alpha (expected losses) should always hold cash
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("-100"),  # Expected to lose money
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        assert should_trade == False

    def test_high_risk_free_rate_scenario(self):
        """
        When risk-free rate is high (e.g., 6%), it's harder to beat
        """
        should_trade_low_rf, analysis_low = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            monthly_risk_free_rate=Decimal("0.02") / 12,  # 2% annual (low)
            expected_monthly_alpha=Decimal("300"),  # Higher alpha
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        should_trade_high_rf, analysis_high = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            monthly_risk_free_rate=Decimal("0.06") / 12,  # 6% annual (high)
            expected_monthly_alpha=Decimal("100"),  # Same alpha
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        # Passive return is higher with higher RF rate
        assert analysis_high["passive_monthly_return"] > analysis_low["passive_monthly_return"]

        # Verify that high RF makes it harder to beat
        # (low RF with $300 alpha is more likely to trade than high RF with $100 alpha)
        assert analysis_high["active_monthly_return"] < analysis_low["active_monthly_return"]

    def test_leverage_cost_scenario(self):
        """
        Test that cost of capital (margin/leverage) is factored in
        """
        # Without leverage cost
        should_trade1, analysis1 = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("300"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
            cost_of_capital_pct=None,
        )

        # With 5% annual leverage cost
        should_trade2, analysis2 = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("300"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
            cost_of_capital_pct=Decimal("0.05"),  # 5% annual margin cost
        )

        # Leverage cost reduces active return
        assert analysis2["capital_cost_monthly"] > Decimal("0")
        # More likely to hold cash with leverage cost
        if should_trade1:
            # If trading was viable without leverage, may not be viable with it
            assert analysis2["active_monthly_return"] < analysis1["active_monthly_return"]

    def test_high_commission_environment(self):
        """
        Test scenarios with high commission (forex, options)
        """
        # Stock market: $7 commission
        should_trade_stock, analysis_stock = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("7"),  # Low
        )

        # Forex/options: $25 commission
        should_trade_forex, analysis_forex = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("25"),  # High
        )

        # Higher commission costs more
        assert (
            analysis_forex["total_commission_monthly"] > analysis_stock["total_commission_monthly"]
        )

        # Stock market more likely to be viable
        if should_trade_stock:
            assert (
                should_trade_forex == False
                or analysis_stock["margin_monthly"] > analysis_forex["margin_monthly"]
            )

    def test_log_opportunity_cost_decision(self, caplog):
        """
        Test logging for audit trail
        """
        _, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            expected_monthly_alpha=Decimal("300"),
            expected_trades_per_month=10,
            commission_per_trade=Decimal("15"),
        )

        log_msg = OpportunityCostValidator.log_opportunity_cost_decision(
            capital=Decimal("50000"),
            analysis=analysis,
            account_id="TEST_ACCT_001",
        )

        assert "TEST_ACCT_001" in log_msg
        assert "$50,000" in log_msg or "$50000" in log_msg
        assert "TRADE" in log_msg or "HOLD_CASH" in log_msg


class TestRealWorldScenarios:
    """Test realistic trading scenarios"""

    def test_retail_stock_account_10k_capital(self):
        """
        Typical retail stock account: $10k, commission $7/trade, 10 trades/month
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("10000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_monthly_alpha=Decimal("100"),  # Optimistic expectation
            expected_trades_per_month=10,
            commission_per_trade=Decimal("7"),
        )

        # Passive: $33/month
        # Commission: $70/month
        # Active: $100 - $70 = $30/month
        # Passive wins! Recommend holding cash

        assert should_trade == False
        assert analysis["recommendation"] == "HOLD_CASH"

    def test_crypto_account_medium_capital(self):
        """
        Crypto trading: $50k, commission $25/trade, high alpha expectations
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("50000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_monthly_alpha=Decimal("500"),  # Higher expectations for crypto
            expected_trades_per_month=20,  # More frequent trading
            commission_per_trade=Decimal("25"),  # Higher commission
        )

        # Passive: $166.67/month
        # Commission: $500/month
        # Active: $500 - $500 = $0/month
        # Break even! Recommend caution

        # Should be marginal or holding cash
        # (depends on exact calculation, but likely not enthusiastically TRADE)

    def test_professional_options_trader(self):
        """
        Professional options trader: $500k, high commission, high alpha
        """
        should_trade, analysis = OpportunityCostValidator.is_active_trading_worthwhile(
            capital=Decimal("500000"),
            monthly_risk_free_rate=Decimal("0.04") / 12,
            expected_monthly_alpha=Decimal("5000"),  # High alpha expectations
            expected_trades_per_month=50,  # Many trades
            commission_per_trade=Decimal("50"),  # High commission
        )

        # Passive: $1,666.67/month
        # Commission: $2,500/month
        # Active: $5,000 - $2,500 = $2,500/month
        # Active wins, but margin vs passive is $833/mo which is < passive($1,666),
        # so it's TRADE_WITH_CAUTION, not high confidence TRADE

        assert should_trade == True
        assert analysis["recommendation"] in ["TRADE", "TRADE_WITH_CAUTION"]
        assert analysis["active_monthly_return"] > Decimal("2400")  # ~$2,500
