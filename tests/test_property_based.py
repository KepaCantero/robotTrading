"""
Property-Based Testing for AlgoTrading
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

import pytest
from hypothesis import given, strategies as st, settings, example
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from app.core.centralized_config import TradingThresholds, StrategyConfig
from app.core.test_config import TestEnvironmentConfig
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.market_data import Quote
from app.models.portfolio import Portfolio, Position
from app.models.order import Order, OrderSide, OrderType, OrderStatus


class TestTradingThresholdsPropertyBased:
    """Property-based tests for TradingThresholds."""
    
    @given(
        max_position_size=st.floats(min_value=0.01, max_value=1.0),
        stop_loss_pct=st.floats(min_value=0.001, max_value=0.5),
        take_profit_pct=st.floats(min_value=0.001, max_value=0.5)
    )
    def test_trading_thresholds_valid_values(self, max_position_size, stop_loss_pct, take_profit_pct):
        """Test that valid trading threshold values are accepted."""
        thresholds = TradingThresholds(
            max_position_size=Decimal(str(max_position_size)),
            stop_loss_pct=Decimal(str(stop_loss_pct)),
            take_profit_pct=Decimal(str(take_profit_pct))
        )
        
        assert thresholds.max_position_size == Decimal(str(max_position_size))
        assert thresholds.stop_loss_pct == Decimal(str(stop_loss_pct))
        assert thresholds.take_profit_pct == Decimal(str(take_profit_pct))
    
    @given(
        max_position_size=st.floats(min_value=0.0, max_value=0.01).filter(lambda x: x <= 0),
        stop_loss_pct=st.floats(min_value=0.0, max_value=0.001).filter(lambda x: x <= 0),
        take_profit_pct=st.floats(min_value=0.0, max_value=0.001).filter(lambda x: x <= 0)
    )
    def test_trading_thresholds_invalid_values(self, max_position_size, stop_loss_pct, take_profit_pct):
        """Test that invalid trading threshold values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            TradingThresholds(
                max_position_size=Decimal(str(max_position_size)),
                stop_loss_pct=Decimal(str(stop_loss_pct)),
                take_profit_pct=Decimal(str(take_profit_pct))
            )
    
    @given(
        max_position_size=st.floats(min_value=1.01, max_value=2.0),
        stop_loss_pct=st.floats(min_value=0.51, max_value=1.0),
        take_profit_pct=st.floats(min_value=0.51, max_value=1.0)
    )
    def test_trading_thresholds_out_of_range_values(self, max_position_size, stop_loss_pct, take_profit_pct):
        """Test that out-of-range trading threshold values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            TradingThresholds(
                max_position_size=Decimal(str(max_position_size)),
                stop_loss_pct=Decimal(str(stop_loss_pct)),
                take_profit_pct=Decimal(str(take_profit_pct))
            )


class TestSignalPropertyBased:
    """Property-based tests for Signal model."""
    
    @given(
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        signal_type=st.sampled_from(list(SignalType)),
        strength=st.floats(min_value=0.0, max_value=100.0),
        confidence=st.floats(min_value=0.0, max_value=100.0),
        price=st.floats(min_value=0.01, max_value=10000.0),
        volume=st.floats(min_value=0.01, max_value=1000000.0)
    )
    def test_signal_valid_values(self, symbol, signal_type, strength, confidence, price, volume):
        """Test that valid signal values are accepted."""
        signal = Signal(
            id=str(uuid.uuid4()),
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            price=Decimal(str(price)),
            volume=Decimal(str(volume)),
            timestamp=datetime.now(),
            strategy="test_strategy",
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL_ANALYSIS
        )
        
        assert signal.symbol == symbol
        assert signal.signal_type == signal_type
        assert signal.strength == strength
        assert signal.confidence == confidence
        assert signal.price == Decimal(str(price))
        assert signal.volume == Decimal(str(volume))
    
    @given(
        strength=st.floats(min_value=-100.0, max_value=-0.1),
        confidence=st.floats(min_value=-100.0, max_value=-0.1)
    )
    def test_signal_invalid_strength_confidence(self, strength, confidence):
        """Test that invalid strength and confidence values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            Signal(
                id=str(uuid.uuid4()),
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                price=Decimal("150.00"),
                volume=Decimal("100.00"),
                timestamp=datetime.now(),
                strategy="test_strategy",
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL_ANALYSIS
            )
    
    @given(
        price=st.floats(min_value=-1000.0, max_value=-0.01),
        volume=st.floats(min_value=-1000000.0, max_value=-0.01)
    )
    def test_signal_invalid_price_volume(self, price, volume):
        """Test that invalid price and volume values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            Signal(
                id=str(uuid.uuid4()),
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=75.0,
                confidence=80.0,
                price=Decimal(str(price)),
                volume=Decimal(str(volume)),
                timestamp=datetime.now(),
                strategy="test_strategy",
                liquidity_score=50.0,
                priority_score=50.0,
                source=SignalSource.TECHNICAL_ANALYSIS
            )


class TestQuotePropertyBased:
    """Property-based tests for Quote model."""
    
    @given(
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        last=st.floats(min_value=0.01, max_value=10000.0),
        bid=st.floats(min_value=0.01, max_value=10000.0),
        ask=st.floats(min_value=0.01, max_value=10000.0),
        volume=st.integers(min_value=1, max_value=1000000000)
    )
    def test_quote_valid_values(self, symbol, last, bid, ask, volume):
        """Test that valid quote values are accepted."""
        # Ensure bid <= last <= ask
        if bid > last:
            bid = last
        if ask < last:
            ask = last
        
        quote = Quote(
            symbol=symbol,
            last=Decimal(str(last)),
            bid=Decimal(str(bid)),
            ask=Decimal(str(ask)),
            volume=volume,
            timestamp=datetime.now(),
            open=Decimal(str(last)),
            high=Decimal(str(last + 1.0)),
            low=Decimal(str(last - 1.0))
        )
        
        assert quote.symbol == symbol
        assert quote.last == Decimal(str(last))
        assert quote.bid == Decimal(str(bid))
        assert quote.ask == Decimal(str(ask))
        assert quote.volume == volume
    
    @given(
        last=st.floats(min_value=0.01, max_value=10000.0),
        bid=st.floats(min_value=0.01, max_value=10000.0),
        ask=st.floats(min_value=0.01, max_value=10000.0)
    )
    def test_quote_bid_ask_relationship(self, last, bid, ask):
        """Test that bid <= last <= ask relationship is maintained."""
        # Ensure bid <= last <= ask
        if bid > last:
            bid = last
        if ask < last:
            ask = last
        
        quote = Quote(
            symbol="AAPL",
            last=Decimal(str(last)),
            bid=Decimal(str(bid)),
            ask=Decimal(str(ask)),
            volume=1000000,
            timestamp=datetime.now(),
            open=Decimal(str(last)),
            high=Decimal(str(last + 1.0)),
            low=Decimal(str(last - 1.0))
        )
        
        assert quote.bid <= quote.last <= quote.ask
        assert quote.spread == quote.ask - quote.bid


class TestPortfolioPropertyBased:
    """Property-based tests for Portfolio model."""
    
    @given(
        name=st.text(min_size=1, max_size=50),
        total_equity=st.floats(min_value=1000.0, max_value=10000000.0),
        cash=st.floats(min_value=0.0, max_value=10000000.0)
    )
    def test_portfolio_valid_values(self, name, total_equity, cash):
        """Test that valid portfolio values are accepted."""
        # Ensure cash <= total_equity
        if cash > total_equity:
            cash = total_equity
        
        portfolio = Portfolio(
            id=str(uuid.uuid4()),
            name=name,
            total_equity=Decimal(str(total_equity)),
            cash=Decimal(str(cash)),
            positions=[],
            daily_pnl=Decimal("0.00"),
            total_pnl=Decimal("0.00"),
            max_drawdown=Decimal("0.00"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert portfolio.name == name
        assert portfolio.total_equity == Decimal(str(total_equity))
        assert portfolio.cash == Decimal(str(cash))
    
    @given(
        total_equity=st.floats(min_value=-1000000.0, max_value=-0.01),
        cash=st.floats(min_value=-1000000.0, max_value=-0.01)
    )
    def test_portfolio_invalid_values(self, total_equity, cash):
        """Test that invalid portfolio values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            Portfolio(
                id=str(uuid.uuid4()),
                name="Test Portfolio",
                total_equity=Decimal(str(total_equity)),
                cash=Decimal(str(cash)),
                positions=[],
                daily_pnl=Decimal("0.00"),
                total_pnl=Decimal("0.00"),
                max_drawdown=Decimal("0.00"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


class TestOrderPropertyBased:
    """Property-based tests for Order model."""
    
    @given(
        symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        side=st.sampled_from(list(OrderSide)),
        order_type=st.sampled_from(list(OrderType)),
        quantity=st.floats(min_value=0.01, max_value=100000.0),
        price=st.floats(min_value=0.01, max_value=10000.0)
    )
    def test_order_valid_values(self, symbol, side, order_type, quantity, price):
        """Test that valid order values are accepted."""
        order = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price)),
            status=OrderStatus.PENDING,
            timestamp=datetime.now(),
            strategy="test_strategy",
            portfolio_id=str(uuid.uuid4())
        )
        
        assert order.symbol == symbol
        assert order.side == side
        assert order.order_type == order_type
        assert order.quantity == Decimal(str(quantity))
        assert order.price == Decimal(str(price))
    
    @given(
        quantity=st.floats(min_value=-100000.0, max_value=-0.01),
        price=st.floats(min_value=-10000.0, max_value=-0.01)
    )
    def test_order_invalid_values(self, quantity, price):
        """Test that invalid order values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            Order(
                id=str(uuid.uuid4()),
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal(str(quantity)),
                price=Decimal(str(price)),
                status=OrderStatus.PENDING,
                timestamp=datetime.now(),
                strategy="test_strategy",
                portfolio_id=str(uuid.uuid4())
            )


class TestStrategyConfigPropertyBased:
    """Property-based tests for StrategyConfig model."""
    
    @given(
        name=st.text(min_size=1, max_size=50),
        enabled=st.booleans(),
        weight=st.floats(min_value=0.0, max_value=1.0),
        max_position_size=st.floats(min_value=0.01, max_value=1.0),
        stop_loss_pct=st.floats(min_value=0.001, max_value=0.5),
        take_profit_pct=st.floats(min_value=0.001, max_value=0.5)
    )
    def test_strategy_config_valid_values(self, name, enabled, weight, max_position_size, stop_loss_pct, take_profit_pct):
        """Test that valid strategy config values are accepted."""
        config = StrategyConfig(
            name=name,
            enabled=enabled,
            weight=Decimal(str(weight)),
            max_position_size=Decimal(str(max_position_size)),
            stop_loss_pct=Decimal(str(stop_loss_pct)),
            take_profit_pct=Decimal(str(take_profit_pct))
        )
        
        assert config.name == name
        assert config.enabled == enabled
        assert config.weight == Decimal(str(weight))
        assert config.max_position_size == Decimal(str(max_position_size))
        assert config.stop_loss_pct == Decimal(str(stop_loss_pct))
        assert config.take_profit_pct == Decimal(str(take_profit_pct))
    
    @given(
        weight=st.floats(min_value=-1.0, max_value=-0.01),
        max_position_size=st.floats(min_value=-1.0, max_value=-0.01),
        stop_loss_pct=st.floats(min_value=-0.5, max_value=-0.001),
        take_profit_pct=st.floats(min_value=-0.5, max_value=-0.001)
    )
    def test_strategy_config_invalid_values(self, weight, max_position_size, stop_loss_pct, take_profit_pct):
        """Test that invalid strategy config values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            StrategyConfig(
                name="test_strategy",
                enabled=True,
                weight=Decimal(str(weight)),
                max_position_size=Decimal(str(max_position_size)),
                stop_loss_pct=Decimal(str(stop_loss_pct)),
                take_profit_pct=Decimal(str(take_profit_pct))
            )


class TestTestEnvironmentConfigPropertyBased:
    """Property-based tests for TestEnvironmentConfig model."""
    
    @given(
        environment=st.text(min_size=1, max_size=20),
        debug=st.booleans(),
        test_db_port=st.integers(min_value=1024, max_value=65535),
        test_redis_port=st.integers(min_value=1024, max_value=65535),
        test_api_port=st.integers(min_value=1024, max_value=65535)
    )
    def test_test_environment_config_valid_values(self, environment, debug, test_db_port, test_redis_port, test_api_port):
        """Test that valid test environment config values are accepted."""
        config = TestEnvironmentConfig(
            environment=environment,
            debug=debug,
            test_db_port=test_db_port,
            test_redis_port=test_redis_port,
            test_api_port=test_api_port
        )
        
        assert config.environment == environment
        assert config.debug == debug
        assert config.test_db_port == test_db_port
        assert config.test_redis_port == test_redis_port
        assert config.test_api_port == test_api_port
    
    @given(
        test_db_port=st.integers(min_value=0, max_value=1023),
        test_redis_port=st.integers(min_value=0, max_value=1023),
        test_api_port=st.integers(min_value=0, max_value=1023)
    )
    def test_test_environment_config_invalid_ports(self, test_db_port, test_redis_port, test_api_port):
        """Test that invalid port values are rejected."""
        with pytest.raises(Exception):  # ValidationError
            TestEnvironmentConfig(
                test_db_port=test_db_port,
                test_redis_port=test_redis_port,
                test_api_port=test_api_port
            )


class TestDecimalPrecisionPropertyBased:
    """Property-based tests for Decimal precision handling."""
    
    @given(
        value=st.floats(min_value=0.000001, max_value=1000000.0)
    )
    def test_decimal_precision_consistency(self, value):
        """Test that Decimal values maintain precision consistency."""
        decimal_value = Decimal(str(value))
        
        # Test that conversion back to float maintains reasonable precision
        float_value = float(decimal_value)
        assert abs(float_value - value) < 1e-10
    
    @given(
        values=st.lists(st.floats(min_value=0.01, max_value=1000.0), min_size=2, max_size=10)
    )
    def test_decimal_arithmetic_precision(self, values):
        """Test that Decimal arithmetic maintains precision."""
        decimal_values = [Decimal(str(v)) for v in values]
        
        # Test addition
        sum_decimal = sum(decimal_values)
        sum_float = sum(values)
        
        assert abs(float(sum_decimal) - sum_float) < 1e-10
        
        # Test multiplication
        if len(values) >= 2:
            product_decimal = decimal_values[0] * decimal_values[1]
            product_float = values[0] * values[1]
            
            assert abs(float(product_decimal) - product_float) < 1e-10


class TestDateTimePropertyBased:
    """Property-based tests for DateTime handling."""
    
    @given(
        days_offset=st.integers(min_value=-365, max_value=365),
        hours_offset=st.integers(min_value=-23, max_value=23),
        minutes_offset=st.integers(min_value=-59, max_value=59)
    )
    def test_datetime_offset_handling(self, days_offset, hours_offset, minutes_offset):
        """Test that DateTime offset handling works correctly."""
        base_time = datetime.now()
        offset = timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
        offset_time = base_time + offset
        
        # Test that offset calculation is correct
        calculated_offset = offset_time - base_time
        assert calculated_offset == offset
    
    @given(
        timestamp1=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
        timestamp2=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))
    )
    def test_datetime_comparison(self, timestamp1, timestamp2):
        """Test that DateTime comparison works correctly."""
        if timestamp1 < timestamp2:
            assert timestamp1 < timestamp2
            assert timestamp1 <= timestamp2
            assert timestamp2 > timestamp1
            assert timestamp2 >= timestamp1
        elif timestamp1 > timestamp2:
            assert timestamp1 > timestamp2
            assert timestamp1 >= timestamp2
            assert timestamp2 < timestamp1
            assert timestamp2 <= timestamp1
        else:
            assert timestamp1 == timestamp2
            assert timestamp1 <= timestamp2
            assert timestamp1 >= timestamp2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
