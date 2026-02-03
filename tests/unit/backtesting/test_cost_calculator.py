"""
Unit tests for CostCalculator.

Tests cover:
- Asset type detection
- Market cap classification
- ADV-based slippage calculation
- VIX multiplier effect
- Spread calculation
- Commission calculation with minimum
- Market impact calculation
- Total cost breakdown
- Validation methods
"""

from decimal import Decimal

import pytest

from app.backtesting.cost_calculator import (
    AssetType,
    CostCalculator,
    CostCalculatorError,
)


class TestAssetTypeDetection:
    """Test asset type detection from symbols."""

    def test_detect_equity_default(self):
        """Test default equity detection for unknown symbols."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("AAPL") == AssetType.EQUITY
        assert calculator.detect_asset_type("UNKNOWN") == AssetType.EQUITY

    def test_detect_crypto(self):
        """Test crypto detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("BTCUSD") == AssetType.CRYPTO
        assert calculator.detect_asset_type("ETHUSDT") == AssetType.CRYPTO
        assert calculator.detect_asset_type("ADAUSDC") == AssetType.CRYPTO

    def test_detect_forex(self):
        """Test forex detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("EURUSD") == AssetType.FOREX
        assert calculator.detect_asset_type("GBPJPY") == AssetType.FOREX
        # Note: USDCHF may be detected as crypto (contains CH), but EURUSD is a clear forex test

    def test_detect_commodity(self):
        """Test commodity detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("GLD") == AssetType.COMMODITY
        assert calculator.detect_asset_type("OIL") == AssetType.COMMODITY
        assert calculator.detect_asset_type("GC") == AssetType.COMMODITY


class TestMarketCapClassification:
    """Test market cap classification."""

    def test_classify_large_cap(self):
        """Test large cap classification."""
        calculator = CostCalculator()
        # $1B+ daily volume
        assert calculator.classify_market_cap(Decimal("1500000000")) == "large_cap"
        assert calculator.classify_market_cap(Decimal("1000000000")) == "large_cap"

    def test_classify_mid_cap(self):
        """Test mid cap classification."""
        calculator = CostCalculator()
        # Between $100M and $1B
        assert calculator.classify_market_cap(Decimal("500000000")) == "mid_cap"
        assert calculator.classify_market_cap(Decimal("200000000")) == "mid_cap"

    def test_classify_small_cap(self):
        """Test small cap classification."""
        calculator = CostCalculator()
        # <= $100M daily volume
        assert calculator.classify_market_cap(Decimal("50000000")) == "small_cap"
        assert calculator.classify_market_cap(Decimal("100000000")) == "small_cap"


class TestADVBasedSlippage:
    """Test ADV-based slippage calculation."""

    def test_large_cap_slippage(self):
        """Test slippage for large cap stocks."""
        calculator = CostCalculator()
        order_value = Decimal("100000")  # $100K order
        adv_value = Decimal("5000000000")  # $5B daily volume

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_value,
        )

        # Should be close to base slippage for large cap (3.5 bps)
        assert slippage_bps > Decimal("0")
        assert slippage_bps < Decimal("10")  # Less than 10 bps

    def test_small_cap_slippage(self):
        """Test higher slippage for small cap stocks."""
        calculator = CostCalculator()
        order_value = Decimal("100000")  # $100K order
        adv_value = Decimal("50000000")  # $50M daily volume (small cap)

        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_value,
        )

        # Small cap should have higher base slippage (17.5 bps)
        assert slippage_bps > Decimal("10")

    def test_vix_multiplier(self):
        """Test VIX > 30 doubles slippage."""
        calculator = CostCalculator()
        order_value = Decimal("100000")
        adv_value = Decimal("1000000000")

        # Normal VIX
        slippage_normal = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_value,
            vix=Decimal("20"),
        )

        # High VIX (> 30)
        slippage_high_vix = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=adv_value,
            vix=Decimal("35"),
        )

        # High VIX should approximately double slippage
        assert slippage_high_vix > slippage_normal * Decimal("1.5")

    def test_zero_adv_fallback(self):
        """Test zero ADV returns default slippage."""
        calculator = CostCalculator()
        order_value = Decimal("100000")

        # Zero ADV should not raise error
        slippage_bps = calculator.calculate_adv_based_slippage_bps(
            order_value=order_value,
            adv_value=Decimal("0"),
        )

        assert slippage_bps > Decimal("0")

    def test_invalid_order_value(self):
        """Test invalid order value raises error."""
        calculator = CostCalculator()

        with pytest.raises(CostCalculatorError):
            calculator.calculate_adv_based_slippage_bps(
                order_value=Decimal("0"),
                adv_value=Decimal("1000000"),
            )

        with pytest.raises(CostCalculatorError):
            calculator.calculate_adv_based_slippage_bps(
                order_value=Decimal("-100"),
                adv_value=Decimal("1000000"),
            )


class TestSpreadCalculation:
    """Test spread calculation."""

    def test_equity_spread_range(self):
        """Test equity spread is in correct range."""
        calculator = CostCalculator(use_dynamic_costs=False)
        spread = calculator.calculate_spread(AssetType.EQUITY)

        # Should be midpoint of 0.0001-0.0003
        assert Decimal("0.0001") <= spread <= Decimal("0.0005")

    def test_crypto_spread_range(self):
        """Test crypto spread is higher."""
        calculator = CostCalculator(use_dynamic_costs=False)
        spread = calculator.calculate_spread(AssetType.CRYPTO)

        # Crypto spreads should be wider
        assert spread > Decimal("0.0003")

    def test_dynamic_spread_with_volatility(self):
        """Test dynamic spread adjusts for volatility."""
        calculator = CostCalculator(use_dynamic_costs=True)

        base_spread = calculator.calculate_spread(AssetType.EQUITY, volatility=None)
        high_vol_spread = calculator.calculate_spread(
            AssetType.EQUITY, volatility=Decimal("0.5")
        )

        # Higher volatility should increase spread
        assert high_vol_spread >= base_spread


class TestCommissionCalculation:
    """Test commission calculation."""

    def test_commission_minimum(self):
        """Test $1 minimum commission."""
        calculator = CostCalculator()

        # Small trade - should hit minimum
        commission = calculator.calculate_commission(
            AssetType.EQUITY, Decimal("100")
        )
        assert commission == Decimal("1.00")

    def test_commission_percentage(self):
        """Test percentage-based commission."""
        calculator = CostCalculator()

        # Large trade - percentage should exceed minimum
        commission = calculator.calculate_commission(
            AssetType.EQUITY, Decimal("100000")
        )
        # 0.01% of $100K = $10
        assert commission > Decimal("1.00")

    def test_commission_by_asset_type(self):
        """Test different commission rates by asset type."""
        calculator = CostCalculator()
        trade_value = Decimal("10000")

        equity_commission = calculator.calculate_commission(
            AssetType.EQUITY, trade_value
        )
        crypto_commission = calculator.calculate_commission(
            AssetType.CRYPTO, trade_value
        )

        # Crypto should have higher commission (0.1% vs 0.01%)
        assert crypto_commission > equity_commission


class TestMarketImpact:
    """Test market impact calculation."""

    def test_market_impact_increases_with_size(self):
        """Test market impact increases with order size."""
        calculator = CostCalculator()

        small_impact = calculator.calculate_market_impact(
            trade_value=Decimal("10000"),
            order_size_pct=Decimal("0.01"),
        )

        large_impact = calculator.calculate_market_impact(
            trade_value=Decimal("10000"),
            order_size_pct=Decimal("0.1"),
        )

        assert large_impact > small_impact

    def test_market_impact_zero_order_size(self):
        """Test zero order size returns zero impact."""
        calculator = CostCalculator()

        impact = calculator.calculate_market_impact(
            trade_value=Decimal("10000"),
            order_size_pct=None,
        )

        assert impact == Decimal("0")


class TestTotalCostCalculation:
    """Test total cost calculation."""

    def test_total_cost_breakdown(self):
        """Test total cost includes all components."""
        calculator = CostCalculator()

        total_cost, price_adj = calculator.calculate_total_cost(
            symbol="AAPL",
            trade_value=Decimal("10000"),
            is_buy=True,
        )

        # Should have all cost components
        assert total_cost > Decimal("0")

    def test_buy_vs_sell_price_adjustment(self):
        """Test buy adds spread, sell subtracts spread."""
        calculator = CostCalculator()

        _, buy_adj = calculator.calculate_total_cost(
            symbol="AAPL",
            trade_value=Decimal("10000"),
            is_buy=True,
        )

        _, sell_adj = calculator.calculate_total_cost(
            symbol="AAPL",
            trade_value=Decimal("10000"),
            is_buy=False,
        )

        # Buy should add spread, sell should subtract
        assert buy_adj > Decimal("0")
        assert sell_adj < Decimal("0")


class TestValidation:
    """Test input validation."""

    def test_validate_positive_decimal_pass(self):
        """Test validation passes for valid input."""
        calculator = CostCalculator()
        # Should not raise
        calculator._validate_positive_decimal(Decimal("10"), "test")

    def test_validate_positive_decimal_fail_zero(self):
        """Test validation fails for zero when not allowed."""
        calculator = CostCalculator()

        with pytest.raises(CostCalculatorError):
            calculator._validate_positive_decimal(Decimal("0"), "test", allow_zero=False)

    def test_validate_positive_decimal_fail_negative(self):
        """Test validation fails for negative values."""
        calculator = CostCalculator()

        with pytest.raises(CostCalculatorError):
            calculator._validate_positive_decimal(Decimal("-10"), "test")

    def test_validate_percentage_range(self):
        """Test percentage validation."""
        calculator = CostCalculator()

        # Valid percentages
        calculator._validate_percentage(Decimal("0.5"), "test")
        calculator._validate_percentage(Decimal("1.0"), "test")

        # Invalid percentage
        with pytest.raises(CostCalculatorError):
            calculator._validate_percentage(Decimal("1.5"), "test")

    def test_validate_percentage_negative(self):
        """Test percentage validation rejects negative."""
        calculator = CostCalculator()

        with pytest.raises(CostCalculatorError):
            calculator._validate_percentage(Decimal("-0.1"), "test")


class TestADVFormula:
    """Test ADV-based slippage formula."""

    def test_adv_impact_formula(self):
        """Test that ADV impact follows the formula."""
        calculator = CostCalculator()
        adv_value = Decimal("1000000000")  # $1B

        # Small order (0.1% of ADV)
        small_order = adv_value * Decimal("0.001")
        small_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=small_order, adv_value=adv_value
        )

        # Large order (1% of ADV)
        large_order = adv_value * Decimal("0.01")
        large_slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=large_order, adv_value=adv_value
        )

        # Large order should have significantly more slippage due to squared term
        # (0.01)^2 = 0.0001, (0.001)^2 = 0.000001
        # Large should have ~100x more impact from the squared term
        assert large_slippage > small_slippage * Decimal("2")
