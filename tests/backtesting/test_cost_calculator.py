"""
Test suite for app.backtesting.cost_calculator

Addresses TST-005: Test coverage for CostCalculator
"""

from decimal import Decimal

import pytest

from app.backtesting.cost_calculator import AssetType, CostCalculator, CostCalculatorError


class TestCostCalculatorImport:
    """Test module imports and initialization."""

    def test_import_asset_type(self):
        """Test that AssetType enum can be imported."""
        from app.backtesting.cost_calculator import AssetType

        assert AssetType.EQUITY == "equity"
        assert AssetType.CRYPTO == "crypto"
        assert AssetType.FOREX == "forex"
        assert AssetType.COMMODITY == "commodity"

    def test_import_cost_calculator(self):
        """Test that CostCalculator class can be imported."""
        from app.backtesting.cost_calculator import CostCalculator

        assert CostCalculator is not None

    def test_import_cost_calculator_error(self):
        """Test that CostCalculatorError can be imported."""
        from app.backtesting.cost_calculator import CostCalculatorError

        assert issubclass(CostCalculatorError, ValueError)


class TestCostCalculatorInitialization:
    """Test CostCalculator initialization."""

    def test_default_initialization(self):
        """Test that CostCalculator can be initialized with defaults."""
        calculator = CostCalculator()
        assert calculator.use_dynamic_costs is True

    def test_static_mode_initialization(self):
        """Test initialization with dynamic costs disabled."""
        calculator = CostCalculator(use_dynamic_costs=False)
        assert calculator.use_dynamic_costs is False


class TestAssetTypeDetection:
    """Test asset type detection."""

    def test_detect_equity(self):
        """Test equity detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("AAPL") == AssetType.EQUITY
        assert calculator.detect_asset_type("MSFT") == AssetType.EQUITY
        assert calculator.detect_asset_type("GOOGL") == AssetType.EQUITY

    def test_detect_crypto(self):
        """Test cryptocurrency detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("BTCUSD") == AssetType.CRYPTO
        assert calculator.detect_asset_type("ETHUSDT") == AssetType.CRYPTO
        assert calculator.detect_asset_type("BTC") == AssetType.CRYPTO

    def test_detect_forex(self):
        """Test forex detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("EURUSD") == AssetType.FOREX
        assert calculator.detect_asset_type("GBPJPY") == AssetType.FOREX
        assert calculator.detect_asset_type("USDCHF") == AssetType.FOREX

    def test_detect_commodity(self):
        """Test commodity detection."""
        calculator = CostCalculator()
        assert calculator.detect_asset_type("GC") == AssetType.COMMODITY  # Gold
        assert calculator.detect_asset_type("SI") == AssetType.COMMODITY  # Silver
        assert calculator.detect_asset_type("CL") == AssetType.COMMODITY  # Oil


class TestMarketCapClassification:
    """Test market cap classification."""

    def test_classify_large_cap(self):
        """Test large cap classification."""
        calculator = CostCalculator()
        assert calculator.classify_market_cap(Decimal("2000000000")) == "large_cap"
        assert calculator.classify_market_cap(Decimal("1000000000")) == "large_cap"

    def test_classify_small_cap(self):
        """Test small cap classification."""
        calculator = CostCalculator()
        assert calculator.classify_market_cap(Decimal("50000000")) == "small_cap"
        assert calculator.classify_market_cap(Decimal("100000000")) == "small_cap"

    def test_classify_mid_cap(self):
        """Test mid cap classification."""
        calculator = CostCalculator()
        assert calculator.classify_market_cap(Decimal("500000000")) == "mid_cap"


class TestSpreadCalculation:
    """Test spread calculation."""

    def test_calculate_spread_equity(self):
        """Test spread calculation for equity."""
        calculator = CostCalculator()
        spread = calculator.calculate_spread(AssetType.EQUITY)
        assert Decimal("0.0001") <= spread <= Decimal("0.0003")

    def test_calculate_spread_crypto(self):
        """Test spread calculation for crypto."""
        calculator = CostCalculator()
        spread = calculator.calculate_spread(AssetType.CRYPTO)
        assert Decimal("0.0005") <= spread <= Decimal("0.002")

    def test_calculate_spread_with_volatility(self):
        """Test spread with volatility adjustment."""
        calculator = CostCalculator(use_dynamic_costs=True)
        spread_low_vol = calculator.calculate_spread(AssetType.EQUITY, Decimal("0.1"))
        spread_high_vol = calculator.calculate_spread(AssetType.EQUITY, Decimal("0.5"))
        assert spread_high_vol >= spread_low_vol


class TestCommissionCalculation:
    """Test commission calculation."""

    def test_calculate_commission_equity(self):
        """Test commission calculation for equity."""
        calculator = CostCalculator()
        commission = calculator.calculate_commission(AssetType.EQUITY, Decimal("10000"))
        assert commission >= Decimal("1.0")  # Minimum commission

    def test_calculate_commission_minimum(self):
        """Test minimum commission enforcement."""
        calculator = CostCalculator()
        commission = calculator.calculate_commission(AssetType.EQUITY, Decimal("100"))
        assert commission == Decimal("1.0")

    def test_calculate_commission_zero_value(self):
        """Test commission with zero trade value."""
        calculator = CostCalculator()
        commission = calculator.calculate_commission(AssetType.EQUITY, Decimal("0"))
        assert commission == Decimal("0")


class TestADVBasedSlippage:
    """Test ADV-based slippage calculation."""

    def test_calculate_adv_slippage_large_cap(self):
        """Test ADV slippage for large cap."""
        calculator = CostCalculator()
        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"),
            adv_value=Decimal("2000000000"),
            asset_type=AssetType.EQUITY,
        )
        assert slippage > 0

    def test_calculate_adv_slippage_small_cap(self):
        """Test ADV slippage for small cap."""
        calculator = CostCalculator()
        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"),
            adv_value=Decimal("50000000"),
            asset_type=AssetType.EQUITY,
        )
        assert slippage > 0

    def test_calculate_adv_slippage_zero_adv(self):
        """Test ADV slippage with zero ADV (uses default)."""
        calculator = CostCalculator()
        slippage = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"), adv_value=Decimal("0"), asset_type=AssetType.EQUITY
        )
        assert slippage > 0

    def test_calculate_adv_slippage_vix_multiplier(self):
        """Test VIX multiplier for high volatility."""
        calculator = CostCalculator()
        slippage_normal = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"),
            adv_value=Decimal("2000000000"),
            vix=Decimal("20"),
            asset_type=AssetType.EQUITY,
        )
        slippage_high_vol = calculator.calculate_adv_based_slippage_bps(
            order_value=Decimal("100000"),
            adv_value=Decimal("2000000000"),
            vix=Decimal("35"),
            asset_type=AssetType.EQUITY,
        )
        assert slippage_high_vol > slippage_normal


class TestValidation:
    """Test input validation."""

    def test_validate_negative_trade_value(self):
        """Test validation rejects negative trade value."""
        calculator = CostCalculator()
        with pytest.raises(CostCalculatorError):
            calculator.calculate_commission(AssetType.EQUITY, Decimal("-100"))

    def test_validate_zero_order_value_for_slippage(self):
        """Test validation rejects zero order value for slippage."""
        calculator = CostCalculator()
        with pytest.raises(CostCalculatorError):
            calculator.calculate_adv_based_slippage_bps(
                order_value=Decimal("0"), adv_value=Decimal("1000000")
            )


class TestTotalCostCalculation:
    """Test total cost calculation."""

    def test_calculate_total_cost_buy(self):
        """Test total cost for buy order."""
        calculator = CostCalculator()
        total_cost, adjustment = calculator.calculate_total_cost(
            symbol="AAPL", trade_value=Decimal("10000"), is_buy=True
        )
        assert total_cost >= 0
        assert adjustment > 0  # Buy: pay ask (higher)

    def test_calculate_total_cost_sell(self):
        """Test total cost for sell order."""
        calculator = CostCalculator()
        total_cost, adjustment = calculator.calculate_total_cost(
            symbol="AAPL", trade_value=Decimal("10000"), is_buy=False
        )
        assert total_cost >= 0
        assert adjustment < 0  # Sell: receive bid (lower)


class TestExecutionPriceAdjustment:
    """Test execution price adjustment."""

    def test_apply_execution_costs_buy(self):
        """Test execution cost for buy order."""
        calculator = CostCalculator()
        adjusted_price = calculator.apply_execution_costs(
            base_price=Decimal("100"), symbol="AAPL", is_buy=True
        )
        assert adjusted_price > Decimal("100")

    def test_apply_execution_costs_sell(self):
        """Test execution cost for sell order."""
        calculator = CostCalculator()
        adjusted_price = calculator.apply_execution_costs(
            base_price=Decimal("100"), symbol="AAPL", is_buy=False
        )
        assert adjusted_price < Decimal("100")


class TestMarketImpactCalculation:
    """Test market impact calculation."""

    def test_calculate_market_impact(self):
        """Test market impact calculation."""
        calculator = CostCalculator()
        impact = calculator.calculate_market_impact(
            trade_value=Decimal("100000"), order_size_pct=Decimal("0.01")
        )
        assert impact >= 0

    def test_calculate_market_impact_no_order_size(self):
        """Test market impact with no order size percentage."""
        calculator = CostCalculator()
        impact = calculator.calculate_market_impact(
            trade_value=Decimal("100000"), order_size_pct=None
        )
        assert impact == 0
