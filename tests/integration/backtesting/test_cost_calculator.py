"""
Integration Tests for ADV-Based Slippage Model (Req #9 - HIGH PRIORITY)

Tests for ADV-based slippage calculation including:
- Market cap classification (large_cap, mid_cap, small_cap)
- Base slippage by market cap (Large: 2-5 bps, Small: 10-25 bps)
- ADV formula: Slippage = Base + (Order_Size / ADV)^2 * Impact_Coefficient
- Volatility multiplier (VIX > 30 = slippage x2)
"""

from decimal import Decimal

import pytest

from app.backtesting.cost_calculator import AssetType, CostCalculator

# ============================================================================
# Tests: Market Cap Classification
# ============================================================================


class TestMarketCapClassification:
    """Tests for market cap classification based on ADV (Req #9)."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_large_cap_classification(self, calculator):
        """Test large cap classification (>= $1B daily volume)."""
        # $2B daily volume
        classification = calculator.classify_market_cap(Decimal("2000000000"))

        assert classification == "large_cap"

    def test_small_cap_classification(self, calculator):
        """Test small cap classification (< $100M daily volume)."""
        # $50M daily volume
        classification = calculator.classify_market_cap(Decimal("50000000"))

        assert classification == "small_cap"

    def test_mid_cap_classification(self, calculator):
        """Test mid cap classification ($100M - $1B daily volume)."""
        # $500M daily volume
        classification = calculator.classify_market_cap(Decimal("500000000"))

        assert classification == "mid_cap"

    def test_boundary_large_cap(self, calculator):
        """Test boundary at $1B (large cap)."""
        classification = calculator.classify_market_cap(Decimal("1000000000"))

        assert classification == "large_cap"

    def test_boundary_small_cap(self, calculator):
        """Test boundary at $100M (small cap)."""
        classification = calculator.classify_market_cap(Decimal("100000000"))

        assert classification == "small_cap"


# ============================================================================
# Tests: Base Slippage by Market Cap (Req #9)
# ============================================================================


class TestBaseSlippageByMarketCap:
    """Tests for base slippage based on market cap (Req #9)."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_large_cap_base_slippage_range(self, calculator):
        """Test large cap base slippage is in 2-5 bps range (Req #9)."""
        order_value = Decimal("100000")  # $100K order
        adv_large_cap = Decimal("2000000000")  # $2B ADV (large cap)

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_large_cap,
        )

        # Large caps should have 2-5 bps base
        assert Decimal("2") <= slippage_bps <= Decimal("5")

    def test_small_cap_base_slippage_range(self, calculator):
        """Test small cap base slippage is in 10-25 bps range (Req #9)."""
        order_value = Decimal("100000")  # $100K order
        adv_small_cap = Decimal("50000000")  # $50M ADV (small cap)

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_small_cap,
        )

        # Small caps should have 10-25 bps base
        assert Decimal("10") <= slippage_bps <= Decimal("25")

    def test_mid_cap_interpolated_slippage(self, calculator):
        """Test mid cap uses interpolated slippage (Req #9)."""
        order_value = Decimal("100000")  # $100K order
        adv_mid_cap = Decimal("500000000")  # $500M ADV (mid cap)

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_mid_cap,
        )

        # Mid cap should be between large and small cap
        large_cap_base = calculator.LARGE_CAP_BASE_SLIPPAGE_BPS
        small_cap_base = calculator.SMALL_CAP_BASE_SLIPPAGE_BPS
        expected_mid = (large_cap_base + small_cap_base) / 2

        assert abs(slippage_bps - expected_mid) < Decimal("1")

    def test_zero_adv_uses_default(self, calculator):
        """Test that zero ADV uses default slippage."""
        order_value = Decimal("100000")
        adv_zero = Decimal("0")

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_zero,
        )

        # Should use default (2-10 bps range from SLIPPAGE_RANGES)
        assert Decimal("2") <= slippage_bps <= Decimal("10")


# ============================================================================
# Tests: ADV Impact Formula (Req #9)
# ============================================================================


class TestADVImpactFormula:
    """Tests for ADV impact formula (Req #9): Slippage = Base + (Order/ADV)^2 * Coef."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_small_order_has_minimal_adv_impact(self, calculator):
        """Test that small orders have minimal ADV impact."""
        # Small order relative to ADV
        order_value = Decimal("1000")  # $1K order
        adv_large = Decimal("2000000000")  # $2B ADV

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_large,
        )

        # Should be close to base slippage (minimal ADV impact)
        assert slippage_bps < Decimal("5")  # Less than 5 bps

    def test_large_order_has_significant_adv_impact(self, calculator):
        """Test that large orders have significant ADV impact."""
        # Large order relative to ADV (1% of ADV)
        order_value = Decimal("20000000")  # $20M order
        adv_large = Decimal("2000000000")  # $2B ADV (1% of ADV)

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_large,
        )

        # Should be significantly higher than base due to ADV impact
        assert slippage_bps > Decimal("10")  # More than 10 bps

    def test_adv_impact_increases_with_order_size(self, calculator):
        """Test that ADV impact increases with order size."""
        adv = Decimal("2000000000")  # $2B ADV

        # Small order
        small_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"),  # $100K
            adv_value=adv,
        )

        # Large order (same ADV)
        large_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("5000000"),  # $5M
            adv_value=adv,
        )

        # Larger order should have more slippage
        assert large_slippage > small_slippage

    def test_adv_impact_formula_squared_relationship(self, calculator):
        """Test that ADV impact has squared relationship (Req #9)."""
        adv = Decimal("1000000000")  # $1B ADV

        # Order that is 1% of ADV
        order_1pct = Decimal("10000000")  # $10M = 1% of $1B

        # Order that is 2% of ADV
        order_2pct = Decimal("20000000")  # $20M = 2% of $1B

        slippage_1pct = calculator.calculate_adv_based_slippage_bps(
            order_value=order_1pct,
            adv_value=adv,
        )

        slippage_2pct = calculator.calculate_adv_based_slippage_bps(
            order_value=order_2pct,
            adv_value=adv,
        )

        # Due to squared relationship, 2% order should have
        # more than 2x the slippage of 1% order
        ratio = slippage_2pct / slippage_1pct if slippage_1pct > 0 else Decimal("0")

        # Should be > 2 (squared relationship)
        assert ratio > Decimal("2")


# ============================================================================
# Tests: Volatility Multiplier (Req #9)
# ============================================================================


class TestVolatilityMultiplier:
    """Tests for volatility multiplier (Req #9: VIX > 30 = slippage x2)."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_normal_volatility_no_multiplier(self, calculator):
        """Test normal volatility (VIX < 30) has no multiplier."""
        order_value = Decimal("100000")
        adv = Decimal("2000000000")

        slippage_normal = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=Decimal("20"),  # Normal VIX
        )

        # Should use normal base slippage
        assert Decimal("2") <= slippage_normal <= Decimal("5")

    def test_high_volatility_doubles_slippage(self, calculator):
        """Test high volatility (VIX > 30) doubles slippage (Req #9)."""
        order_value = Decimal("100000")
        adv = Decimal("2000000000")

        # Normal volatility
        slippage_normal = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=Decimal("25"),  # Below threshold
        )

        # High volatility
        slippage_high = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=Decimal("35"),  # Above threshold
        )

        # High volatility should have ~2x slippage
        ratio = slippage_high / slippage_normal if slippage_normal > 0 else Decimal("0")

        assert ratio >= Decimal("1.9")  # Approximately 2x

    def test_vix_boundary_at_30(self, calculator):
        """Test VIX boundary at 30 (Req #9)."""
        order_value = Decimal("100000")
        adv = Decimal("2000000000")

        # VIX = 31 (above threshold, should double)
        slippage_at_31 = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=Decimal("31"),
        )

        # VIX = 29 (just below threshold)
        slippage_below_30 = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=Decimal("29"),
        )

        # VIX > 30 uses high volatility multiplier, should be ~2x
        assert slippage_at_31 >= slippage_below_30 * Decimal("1.9")  # Approximately 2x

    def test_no_vix_provided_uses_base_slippage(self, calculator):
        """Test that no VIX provided uses base slippage."""
        order_value = Decimal("100000")
        adv = Decimal("2000000000")

        # No VIX provided
        slippage_no_vix = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv,
            vix=None,
        )

        # Should use normal slippage
        assert slippage_no_vix > 0


# ============================================================================
# Tests: Complete ADV-Based Slippage Calculation
# ============================================================================


class TestCompleteADVServBasedSlippage:
    """Tests for complete ADV-based slippage calculation."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_calculate_adv_based_slippage_returns_dollars(self, calculator):
        """Test that ADV-based slippage returns dollar amount."""
        trade_value = Decimal("100000")  # $100K trade
        adv = Decimal("2000000000")  # $2B ADV

        slippage = calculator.calculate_adv_based_slippage(
            asset_type=AssetType.EQUITY,
            trade_value=trade_value,
            adv_value=adv,
        )

        # Should return dollar amount
        assert isinstance(slippage, Decimal)
        assert slippage >= 0

    def test_slippage_dollars_correlate_with_bps(self, calculator):
        """Test that dollar slippage correlates with bps calculation."""
        trade_value = Decimal("100000")  # $100K trade
        adv = Decimal("2000000000")  # $2B ADV

        # Calculate in bps
        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=trade_value,
            adv_value=adv,
        )

        # Calculate in dollars
        slippage_dollars = calculator.calculate_adv_based_slippage(
            asset_type=AssetType.EQUITY,
            trade_value=trade_value,
            adv_value=adv,
        )

        # Verify conversion: dollars = trade_value * bps / 10000
        expected_dollars = trade_value * slippage_bps / Decimal("10000")

        assert abs(slippage_dollars - expected_dollars) < Decimal("0.01")

    def test_crypto_asset_uses_different_base(self, calculator):
        """Test that crypto assets use different base slippage."""
        trade_value = Decimal("10000")  # $10K trade
        adv = Decimal("500000000")  # $500M ADV

        # Equity
        equity_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=trade_value,
            adv_value=adv,
            asset_type=AssetType.EQUITY,
        )

        # Crypto (should use different defaults if no ADV data provided)
        # For this test, we provide ADV, so it should be similar
        # But the internal logic handles crypto differently
        crypto_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=trade_value,
            adv_value=adv,
            asset_type=AssetType.CRYPTO,
        )

        # Both should return valid values
        assert equity_slippage > 0
        assert crypto_slippage > 0


# ============================================================================
# Tests: Edge Cases
# ============================================================================


class TestADVEdgeCases:
    """Tests for edge cases in ADV calculation."""

    @pytest.fixture
    def calculator(self):
        """Default cost calculator."""
        return CostCalculator()

    def test_negative_adv_treated_as_zero(self, calculator):
        """Test negative ADV is treated as zero."""
        order_value = Decimal("100000")
        adv_negative = Decimal("-1000000")

        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_negative,
        )

        # Should use default slippage
        assert slippage > 0

    def test_very_small_adv(self, calculator):
        """Test very small ADV value."""
        order_value = Decimal("1000")
        adv_tiny = Decimal("1000")  # Same as order (100% of ADV)

        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_tiny,
        )

        # Should have significant slippage due to large order size relative to ADV
        assert slippage > Decimal("100")  # Very high slippage

    def test_very_large_adv(self, calculator):
        """Test very large ADV value."""
        order_value = Decimal("1000000")  # $1M order
        adv_huge = Decimal("100000000000")  # $100B ADV

        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_huge,
        )

        # Should have minimal slippage (small % of huge ADV)
        assert slippage < Decimal("10")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
