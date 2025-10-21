"""
Tests for Domain Validation in Models

This module tests the domain validation rules implemented in the trading models.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Position, AssetClass
from app.models.order import Order, OrderType, OrderSide, OrderStatus, MarketData


class TestSignalDomainValidation:
    """Test domain validation for Signal model."""
    
    def test_valid_signal(self):
        """Test valid signal passes validation."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow()
        )
        assert signal.confidence == 80.0
        assert signal.price == Decimal("150.0")
    
    def test_confidence_out_of_range(self):
        """Test confidence validation."""
        with pytest.raises(ValidationError, match="Input should be less than or equal to 100"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=150.0,  # Invalid: > 100
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000")
            )
    
    def test_negative_price(self):
        """Test price validation."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("-150.0"),  # Invalid: negative
                volume=Decimal("1000")
            )
    
    def test_excessive_price(self):
        """Test price limit validation."""
        with pytest.raises(ValidationError, match="Price exceeds maximum limit"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("2000000.0"),  # Invalid: > $1M
                volume=Decimal("1000")
            )
    
    def test_future_timestamp(self):
        """Test timestamp validation."""
        future_time = datetime.utcnow() + timedelta(days=1)
        with pytest.raises(ValidationError, match="Timestamp cannot be in the future"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000"),
                timestamp=future_time
            )
    
    def test_old_timestamp(self):
        """Test timestamp age validation."""
        old_time = datetime.utcnow() - timedelta(days=400)
        with pytest.raises(ValidationError, match="Timestamp is too old"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=80.0,
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000"),
                timestamp=old_time
            )
    
    def test_strong_signal_low_confidence(self):
        """Test signal consistency validation."""
        with pytest.raises(ValidationError, match="Strong signal.*with low confidence"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=50.0,  # Invalid: strong signal with low confidence
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000")
            )
    
    def test_weak_signal_high_confidence(self):
        """Test signal consistency validation."""
        with pytest.raises(ValidationError, match="Weak signal with high confidence"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=90.0,  # Invalid: weak signal with high confidence
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000")
            )
    
    def test_hold_signal_very_high_confidence(self):
        """Test HOLD signal consistency validation."""
        with pytest.raises(ValidationError, match="HOLD signal with very high confidence"):
            Signal(
                symbol="AAPL",
                signal_type=SignalType.HOLD,
                strength=SignalStrength.MODERATE,
                confidence=95.0,  # Invalid: HOLD signal with very high confidence
                liquidity_score=75.0,
                priority_score=85.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("150.0"),
                volume=Decimal("1000")
            )


class TestPositionDomainValidation:
    """Test domain validation for Position model."""
    
    def test_valid_position(self):
        """Test valid position passes validation."""
        position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.0"),
            market_price=Decimal("155.0"),
            unrealized_pnl=Decimal("500.0"),
            broker="IBKR"
        )
        assert position.quantity == Decimal("100")
        assert position.avg_price == Decimal("150.0")
    
    def test_zero_quantity(self):
        """Test zero quantity validation."""
        with pytest.raises(ValidationError, match="Position quantity cannot be zero"):
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("0"),  # Invalid: zero quantity
                avg_price=Decimal("150.0"),
                market_price=Decimal("155.0"),
                unrealized_pnl=Decimal("0"),
                broker="IBKR"
            )
    
    def test_negative_price(self):
        """Test price validation."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("-150.0"),  # Invalid: negative price
                market_price=Decimal("155.0"),
                unrealized_pnl=Decimal("500.0"),
                broker="IBKR"
            )
    
    def test_excessive_value(self):
        """Test value limit validation."""
        with pytest.raises(ValidationError, match="Price exceeds maximum limit"):
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("2000000000.0"),  # Invalid: > $1B
                market_price=Decimal("155.0"),
                unrealized_pnl=Decimal("500.0"),
                broker="IBKR"
            )
    
    def test_pnl_calculation_mismatch(self):
        """Test P&L calculation validation."""
        with pytest.raises(ValidationError, match="Unrealized P&L calculation mismatch"):
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.0"),
                market_price=Decimal("155.0"),
                unrealized_pnl=Decimal("1000.0"),  # Invalid: should be 500.0
                broker="IBKR"
            )


class TestOrderDomainValidation:
    """Test domain validation for Order model."""
    
    def test_valid_order(self):
        """Test valid order passes validation."""
        order = Order(
            id="order_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.0")
        )
        assert order.quantity == Decimal("100")
        assert order.price == Decimal("150.0")
    
    def test_limit_order_without_price(self):
        """Test limit order price requirement."""
        with pytest.raises(ValidationError, match="Limit orders must have a price"):
            Order(
                id="order_123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=None  # Invalid: limit order without price
            )
    
    def test_stop_order_without_stop_price(self):
        """Test stop order stop price requirement."""
        with pytest.raises(ValidationError, match="Stop orders must have a stop price"):
            Order(
                id="order_123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP,
                quantity=Decimal("100"),
                stop_price=None  # Invalid: stop order without stop price
            )
    
    def test_stop_limit_order_price_logic(self):
        """Test stop-limit order price logic."""
        with pytest.raises(ValidationError, match="Stop-limit order price must be greater than stop price"):
            Order(
                id="order_123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP_LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.0"),  # Invalid: price <= stop_price
                stop_price=Decimal("160.0")
            )
    
    def test_filled_quantity_exceeds_order(self):
        """Test filled quantity validation."""
        with pytest.raises(ValidationError, match="Filled quantity.*cannot exceed order quantity"):
            Order(
                id="order_123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                filled_quantity=Decimal("150")  # Invalid: exceeds order quantity
            )
    
    def test_filled_order_without_price(self):
        """Test filled order price requirement."""
        with pytest.raises(ValidationError, match="Filled orders must have a filled price"):
            Order(
                id="order_123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("100"),
                filled_quantity=Decimal("50"),
                filled_price=None  # Invalid: filled order without price
            )


class TestMarketDataDomainValidation:
    """Test domain validation for MarketData model."""
    
    def test_valid_market_data(self):
        """Test valid market data passes validation."""
        market_data = MarketData(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open_price=Decimal("150.0"),
            high_price=Decimal("155.0"),
            low_price=Decimal("148.0"),
            close_price=Decimal("152.0"),
            volume=Decimal("1000000"),
            bid=Decimal("151.5"),
            ask=Decimal("152.5")
        )
        assert market_data.high_price == Decimal("155.0")
        assert market_data.low_price == Decimal("148.0")
    
    def test_high_less_than_low(self):
        """Test high-low price validation."""
        with pytest.raises(ValidationError, match="High price.*must be >= low price"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("150.0"),
                high_price=Decimal("148.0"),  # Invalid: high < low
                low_price=Decimal("155.0"),
                close_price=Decimal("152.0"),
                volume=Decimal("1000000")
            )
    
    def test_close_price_out_of_range(self):
        """Test close price range validation."""
        with pytest.raises(ValidationError, match="Close price.*160.0.*must be between low.*148.0.*and high.*155.0"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("150.0"),
                high_price=Decimal("155.0"),
                low_price=Decimal("148.0"),
                close_price=Decimal("160.0"),  # Invalid: close > high
                volume=Decimal("1000000")
            )
    
    def test_open_price_out_of_range(self):
        """Test open price range validation."""
        with pytest.raises(ValidationError, match="Open price.*140.0.*must be between low.*148.0.*and high.*155.0"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("140.0"),  # Invalid: open < low
                high_price=Decimal("155.0"),
                low_price=Decimal("148.0"),
                close_price=Decimal("152.0"),
                volume=Decimal("1000000")
            )
    
    def test_bid_ask_spread_logic(self):
        """Test bid-ask spread validation."""
        with pytest.raises(ValidationError, match="Bid price.*must be less than ask price"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("150.0"),
                high_price=Decimal("155.0"),
                low_price=Decimal("148.0"),
                close_price=Decimal("152.0"),
                volume=Decimal("1000000"),
                bid=Decimal("155.0"),  # Invalid: bid >= ask
                ask=Decimal("150.0")
            )
    
    def test_excessive_spread(self):
        """Test excessive spread validation."""
        with pytest.raises(ValidationError, match="Excessive spread detected"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("150.0"),
                high_price=Decimal("155.0"),
                low_price=Decimal("148.0"),
                close_price=Decimal("152.0"),
                volume=Decimal("1000000"),
                bid=Decimal("100.0"),  # Invalid: excessive spread
                ask=Decimal("200.0")
            )
    
    def test_negative_volume(self):
        """Test volume validation."""
        with pytest.raises(ValidationError, match="Price fields must be positive"):
            MarketData(
                symbol="AAPL",
                timestamp=datetime.utcnow(),
                open_price=Decimal("150.0"),
                high_price=Decimal("155.0"),
                low_price=Decimal("148.0"),
                close_price=Decimal("152.0"),
                volume=Decimal("-1000")  # Invalid: negative volume
            )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_confidence(self):
        """Test zero confidence is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,  # Valid: minimum confidence
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("1000")
        )
        assert signal.confidence == 0.0
    
    def test_maximum_confidence(self):
        """Test maximum confidence is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.VERY_STRONG,
            confidence=100.0,  # Valid: maximum confidence
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("1000")
        )
        assert signal.confidence == 100.0
    
    def test_minimum_price(self):
        """Test minimum price is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("0.01"),  # Valid: minimum price
            volume=Decimal("1000")
        )
        assert signal.price == Decimal("0.01")
    
    def test_maximum_price(self):
        """Test maximum price is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("1000000.0"),  # Valid: maximum price
            volume=Decimal("1000")
        )
        assert signal.price == Decimal("1000000.0")
    
    def test_zero_volume(self):
        """Test zero volume is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("0")  # Valid: zero volume
        )
        assert signal.volume == Decimal("0")
    
    def test_maximum_volume(self):
        """Test maximum volume is valid."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("150.0"),
            volume=Decimal("1000000000")  # Valid: maximum volume
        )
        assert signal.volume == Decimal("1000000000")
