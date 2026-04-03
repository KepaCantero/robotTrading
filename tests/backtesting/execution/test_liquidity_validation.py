"""
CRITICAL TESTS: Liquidity Validation (HIGH PRIORITY #1)

These tests implement the audit recommendation for liquidity validation:
- Volume-based rejection (>10% of daily volume)
- Warning for large orders (>5% of daily volume)
- Partial fills for orders that exceed available liquidity
- Market impact calculation

Audit Finding: Backtesting executes orders without validating available liquidity,
leading to unrealistic fill assumptions and inflated backtest results.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.liquidity_validator import FillResult, LiquidityValidator
from app.domain.models.market_data import Quote


# Helper function to create timestamps
def past_time(hours_ago=1):
    """Create a datetime in the past for testing."""
    return datetime.utcnow() - timedelta(hours=hours_ago)


def create_market_bar(
    symbol: str = "AAPL",
    close: Decimal = Decimal("100"),
    volume: Decimal = Decimal("1000000"),
    timestamp: datetime = None,
) -> Quote:
    """Create a market data bar for testing.

    Note: Default symbol parameter kept for backward compatibility.
    Tests should pass default_symbol explicitly.
    """
    if timestamp is None:
        timestamp = past_time(hours_ago=1)

    return Quote(
        symbol=symbol,
        timestamp=timestamp,
        bid=close - Decimal("0.5"),
        ask=close + Decimal("0.5"),
        last=close,
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=volume,
        spread=Decimal("1.0"),
    )


class TestLiquidityValidatorBasic:
    """Test basic liquidity validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create default liquidity validator."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),  # 10%
            warning_order_pct_of_volume=Decimal("0.05"),  # 5%
            partial_fill_pct=Decimal("0.05"),  # 5%
        )

    def test_normal_order_accepted(self, validator, default_symbol):
        """Test that normal orders (<5% of volume) are accepted."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))  # 1M shares daily

        # Normal order: 1,000 shares = 0.1% of volume
        is_valid, reason = validator.validate_order(
            order_quantity=Decimal("1000"), symbol=default_symbol, current_bar=bar, order_side="buy"
        )

        assert is_valid, f"Normal order should be valid, got: {reason}"
        assert reason == "OK"

    def test_large_order_warned_but_accepted(self, validator, default_symbol):
        """Test that large orders (5-10% of volume) trigger warning but execute."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))  # 1M shares daily

        # Large order: 75,000 shares = 7.5% of volume (triggers warning)
        is_valid, reason = validator.validate_order(
            order_quantity=Decimal("75000"),
            symbol=default_symbol,
            current_bar=bar,
            order_side="buy",
        )

        assert is_valid, f"Large order should be valid, got: {reason}"
        assert reason == "OK"

    def test_excessive_order_rejected(self, validator, default_symbol):
        """Test that excessive orders (>10% of volume) are rejected."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))  # 1M shares daily

        # Excessive order: 150,000 shares = 15% of volume (rejected)
        is_valid, reason = validator.validate_order(
            order_quantity=Decimal("150000"),
            symbol=default_symbol,
            current_bar=bar,
            order_side="buy",
        )

        assert not is_valid, "Excessive order should be rejected"
        assert "exceeds maximum" in reason.lower()
        assert "10" in reason  # Check for 10 (could be "10%" or "10.0%")

    def test_exact_threshold_order(self, validator, default_symbol):
        """Test order exactly at 10% threshold (triggers warning, not rejection)."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))  # 1M shares daily

        # Exact threshold: 100,000 shares = 10% of volume
        is_valid, reason = validator.validate_order(
            order_quantity=Decimal("100000"),
            symbol=default_symbol,
            current_bar=bar,
            order_side="buy",
        )

        # At exactly 10%, order is valid but triggers a warning in simulate_fill
        # (The validate_order method only rejects > 10%, not >= 10%)
        # However, simulate_fill will do partial fill for 5-10% range
        assert is_valid, "Order at exact 10% threshold should pass validate_order"

    def test_no_volume_data(self, validator, default_symbol):
        """Test that orders without volume data are rejected."""
        # Create bar without volume
        bar = Quote(
            symbol=default_symbol,
            timestamp=past_time(),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("0"),  # No volume
            spread=Decimal("1.0"),
        )

        is_valid, reason = validator.validate_order(
            order_quantity=Decimal("1000"), symbol=default_symbol, current_bar=bar, order_side="buy"
        )

        assert not is_valid, "Order without volume data should be rejected"
        assert "volume" in reason.lower()


class TestPartialFills:
    """Test partial fill functionality."""

    @pytest.fixture
    def validator_with_partial_fills(self):
        """Create validator with partial fills enabled."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),  # Fill up to 5% of volume
        )

    @pytest.fixture
    def validator_without_partial_fills(self):
        """Create validator with partial fills disabled."""
        return LiquidityValidator(
            enable_partial_fills=False,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),
        )

    def test_full_fill_for_normal_order(self, validator_with_partial_fills, default_symbol):
        """Test that normal orders get full fills."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))

        result = validator_with_partial_fills.simulate_fill(
            order_quantity=Decimal("1000"), current_bar=bar, order_side="buy", symbol=default_symbol
        )

        assert result.fill_status == "FILLED"
        assert result.filled_quantity == Decimal("1000")
        assert result.requested_quantity == Decimal("1000")
        assert result.fill_price > Decimal("100")  # Buy orders pay more
        assert result.market_impact is not None

    def test_partial_fill_for_large_order(self, validator_with_partial_fills, default_symbol):
        """Test that large orders get partial fills."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))

        # Request 75,000 shares (7.5% of volume)
        # Should get partial fill of 50,000 shares (5% of volume)
        result = validator_with_partial_fills.simulate_fill(
            order_quantity=Decimal("75000"),
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        assert result.fill_status == "PARTIAL"
        assert result.filled_quantity == Decimal("50000")  # 5% of 1M
        assert result.requested_quantity == Decimal("75000")
        assert result.fill_price > Decimal("100")

    def test_rejection_when_partial_fills_disabled(
        self, validator_without_partial_fills, default_symbol
    ):
        """Test that large orders are rejected when partial fills disabled."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))

        # Request 75,000 shares (7.5% of volume)
        result = validator_without_partial_fills.simulate_fill(
            order_quantity=Decimal("75000"),
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        assert result.fill_status == "REJECTED"
        assert result.filled_quantity == Decimal("0")
        assert result.rejection_reason is not None
        assert "partial fills are disabled" in result.rejection_reason.lower()

    def test_excessive_order_rejected_even_with_partial_fills(
        self, validator_with_partial_fills, default_symbol
    ):
        """Test that orders >10% are rejected even with partial fills enabled."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))

        # Request 150,000 shares (15% of volume)
        result = validator_with_partial_fills.simulate_fill(
            order_quantity=Decimal("150000"),
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        assert result.fill_status == "REJECTED"
        assert "exceeds maximum" in result.rejection_reason.lower()


class TestMarketImpact:
    """Test market impact calculation."""

    @pytest.fixture
    def validator(self):
        """Create liquidity validator with explicit thresholds."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),
        )

    def test_market_impact_increases_with_size(self, validator):
        """Test that market impact increases with order size."""
        bar = create_market_bar(volume=Decimal("1000000"))

        # Small order: minimal impact
        impact_small = validator.calculate_market_impact(
            order_quantity=Decimal("1000"), current_bar=bar, order_side="buy"
        )

        # Large order: significant impact
        impact_large = validator.calculate_market_impact(
            order_quantity=Decimal("50000"), current_bar=bar, order_side="buy"
        )

        assert impact_large > impact_small, "Market impact should increase with order size"

    def test_market_impact_capped(self, validator):
        """Test that market impact is capped at reasonable maximum."""
        bar = create_market_bar(volume=Decimal("1000000"))

        # Extremely large order
        impact = validator.calculate_market_impact(
            order_quantity=Decimal("900000"), current_bar=bar, order_side="buy"  # 90% of volume
        )

        # Should be capped at 5%
        assert impact <= Decimal("0.05"), f"Market impact should be capped at 5%, got {impact}"

    def test_buy_price_includes_market_impact(self, validator, default_symbol):
        """Test that buy execution price includes market impact."""
        bar = create_market_bar(
            symbol=default_symbol, close=Decimal("100"), volume=Decimal("1000000")
        )

        result = validator.simulate_fill(
            order_quantity=Decimal("50000"),  # 5% of volume - should have impact
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        # Buy price should be higher than close price
        assert result.fill_price > Decimal(
            "100"
        ), f"Buy price ${result.fill_price} should be higher than $100 due to market impact"

    def test_sell_price_includes_market_impact(self, validator, default_symbol):
        """Test that sell execution price includes market impact."""
        bar = create_market_bar(
            symbol=default_symbol, close=Decimal("100"), volume=Decimal("1000000")
        )

        result = validator.simulate_fill(
            order_quantity=Decimal("50000"),  # 5% of volume
            current_bar=bar,
            order_side="sell",
            symbol=default_symbol,
        )

        # Sell price should be lower than close price
        assert result.fill_price < Decimal(
            "100"
        ), f"Sell price ${result.fill_price} should be lower than $100 due to market impact"


class TestFillResult:
    """Test FillResult dataclass."""

    def test_fill_result_defaults(self):
        """Test that FillResult sets reasonable defaults."""
        result = FillResult(
            requested_quantity=Decimal("1000"),
            filled_quantity=Decimal("1000"),
            fill_price=Decimal("100.50"),
            fill_status="FILLED",
        )

        # avg_fill_price should default to fill_price
        assert result.avg_fill_price == Decimal("100.50")

    def test_fill_result_with_market_impact(self):
        """Test FillResult with market impact."""
        result = FillResult(
            requested_quantity=Decimal("1000"),
            filled_quantity=Decimal("1000"),
            fill_price=Decimal("100.50"),
            fill_status="FILLED",
            market_impact=Decimal("0.01"),
        )

        assert result.market_impact == Decimal("0.01")

    def test_fill_result_rejection(self):
        """Test FillResult for rejected orders."""
        result = FillResult(
            requested_quantity=Decimal("100000"),
            filled_quantity=Decimal("0"),
            fill_price=Decimal("0"),
            fill_status="REJECTED",
            rejection_reason="Order exceeds 10% of daily volume",
        )

        assert result.fill_status == "REJECTED"
        assert result.filled_quantity == Decimal("0")
        assert result.rejection_reason is not None


class TestLiquidityMetrics:
    """Test liquidity metrics calculation."""

    @pytest.fixture
    def validator(self):
        """Create liquidity validator with explicit 10%/5%/5% thresholds."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),  # 10%
            warning_order_pct_of_volume=Decimal("0.05"),  # 5%
            partial_fill_pct=Decimal("0.05"),  # 5%
        )

    def test_liquidity_metrics_without_order(self, validator):
        """Test liquidity metrics without order context."""
        bar = create_market_bar(volume=Decimal("1000000"))

        metrics = validator.get_liquidity_metrics(current_bar=bar)

        assert metrics["daily_volume"] == 1000000.0
        assert metrics["max_order_size"] == 100000.0  # 10% of volume
        assert metrics["warning_threshold"] == 50000.0  # 5% of volume
        assert metrics["partial_fill_size"] == 50000.0  # 5% of volume

    def test_liquidity_metrics_with_order(self, validator):
        """Test liquidity metrics with order context."""
        bar = create_market_bar(volume=Decimal("1000000"))

        metrics = validator.get_liquidity_metrics(current_bar=bar, order_quantity=Decimal("75000"))

        assert metrics["order_quantity"] == 75000.0
        assert metrics["order_pct_of_volume"] == 0.075  # 7.5%
        assert metrics["would_reject"] == False  # < 10%
        assert metrics["would_warn"] == True  # > 5%

    def test_liquidity_metrics_rejection_case(self, validator):
        """Test liquidity metrics for rejection case."""
        bar = create_market_bar(volume=Decimal("1000000"))

        metrics = validator.get_liquidity_metrics(current_bar=bar, order_quantity=Decimal("150000"))

        assert metrics["order_pct_of_volume"] == 0.15  # 15%
        assert metrics["would_reject"] == True  # > 10%
        assert metrics["would_warn"] == True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def validator(self):
        """Create default liquidity validator."""
        return LiquidityValidator()

    def test_zero_volume(self, validator, default_symbol):
        """Test handling of zero volume."""
        bar = create_market_bar(symbol=default_symbol, volume=Decimal("0"))

        result = validator.simulate_fill(
            order_quantity=Decimal("100"), current_bar=bar, order_side="buy", symbol=default_symbol
        )

        assert result.fill_status == "REJECTED"

    def test_custom_thresholds(self, default_symbol):
        """Test validator with custom thresholds."""
        custom_validator = LiquidityValidator(
            max_order_pct_of_volume=Decimal("0.05"),  # 5% max
            warning_order_pct_of_volume=Decimal("0.02"),  # 2% warning
            partial_fill_pct=Decimal("0.02"),  # 2% partial fill
        )

        bar = create_market_bar(symbol=default_symbol, volume=Decimal("1000000"))

        # 3% order should get partial fill with custom thresholds (between 2% and 5%)
        result = custom_validator.simulate_fill(
            order_quantity=Decimal("30000"),
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        # 3% is > 2% partial_fill_pct, so should get partial fill
        assert result.fill_status == "PARTIAL"
        assert result.filled_quantity == Decimal("20000")  # 2% of 1M

    def test_buy_vs_sell_prices(self, validator, default_symbol):
        """Test that buy and sell prices are calculated differently."""
        bar = create_market_bar(
            symbol=default_symbol, close=Decimal("100"), volume=Decimal("1000000")
        )

        buy_result = validator.simulate_fill(
            order_quantity=Decimal("1000"), current_bar=bar, order_side="buy", symbol=default_symbol
        )

        sell_result = validator.simulate_fill(
            order_quantity=Decimal("1000"),
            current_bar=bar,
            order_side="sell",
            symbol=default_symbol,
        )

        # Buy price should be higher than sell price (adverse selection)
        assert buy_result.fill_price > Decimal(
            "100"
        ), f"Buy price ${buy_result.fill_price} should be > $100"
        assert sell_result.fill_price < Decimal(
            "100"
        ), f"Sell price ${sell_result.fill_price} should be < $100"
        assert (
            buy_result.fill_price > sell_result.fill_price
        ), "Buy price should be higher than sell price"


class TestIntegrationScenarios:
    """Integration test scenarios for liquidity validation."""

    @pytest.fixture
    def validator(self):
        """Create liquidity validator with explicit 10%/5%/5% thresholds."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),  # 10%
            warning_order_pct_of_volume=Decimal("0.05"),  # 5%
            partial_fill_pct=Decimal("0.05"),  # 5%
        )

    def test_illiquid_stock_scenario(self, validator):
        """Test trading an illiquid stock with low volume."""
        # Illiquid stock: only 10,000 shares daily volume
        bar = create_market_bar(symbol="PENNY", close=Decimal("5"), volume=Decimal("10000"))

        # Try to buy 1,000 shares (10% of volume - at partial fill threshold)
        result = validator.simulate_fill(
            order_quantity=Decimal("1000"), current_bar=bar, order_side="buy", symbol="PENNY"
        )

        # Should get partial fill (at 10% threshold, gets 5% partial fill)
        assert result.fill_status == "PARTIAL"
        assert result.filled_quantity == Decimal("500")  # 5% of 10,000

        # Try smaller order: 400 shares (4% of volume)
        result = validator.simulate_fill(
            order_quantity=Decimal("400"), current_bar=bar, order_side="buy", symbol="PENNY"
        )

        # Should be accepted
        assert result.fill_status == "FILLED"

    def test_highly_liquid_stock_scenario(self, validator):
        """Test trading a highly liquid stock with high volume."""
        # Highly liquid stock: 100M shares daily volume
        bar = create_market_bar(symbol="NVDA", close=Decimal("500"), volume=Decimal("100000000"))

        # Large order: 1M shares (1% of volume)
        result = validator.simulate_fill(
            order_quantity=Decimal("1000000"), current_bar=bar, order_side="buy", symbol="NVDA"
        )

        # Should be accepted with minimal market impact
        assert result.fill_status == "FILLED"
        assert result.market_impact <= Decimal(
            "0.01"
        ), f"Market impact should be minimal for liquid stock, got {result.market_impact}"

    def test_scalping_strategy_scenario(self, validator, default_symbol):
        """Test liquidity validation for a high-frequency scalping strategy."""
        bar = create_market_bar(
            symbol=default_symbol, close=Decimal("100"), volume=Decimal("1000000")
        )

        # Scalping: Many small orders
        results = []
        for i in range(10):
            result = validator.simulate_fill(
                order_quantity=Decimal("500"),  # Small order
                current_bar=bar,
                order_side="buy" if i % 2 == 0 else "sell",
                symbol=default_symbol,
            )
            results.append(result)

        # All orders should be filled
        for result in results:
            assert (
                result.fill_status == "FILLED"
            ), f"Scalping order should be filled, got {result.fill_status}"
