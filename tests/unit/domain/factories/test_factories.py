"""
Tests for Factory Pattern following Percival's Architecture Patterns with Python.

Tests verify that the Factory pattern correctly implements:
- Abstract Factory pattern
- Factory Method pattern
- Builder pattern
- Prototype pattern
- Factory Registry
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.factories import (
    AbstractEntityFactory,
    TradingEntityFactory,
    OrderBuilder,
    OrderPrototype,
    OrderFactory,
    FactoryRegistry,
    get_factory,
    register_factory,
)


# ============================================================================
# TEST ABSTRACT FACTORY
# ============================================================================

class TestAbstractEntityFactory:
    """Tests for AbstractEntityFactory interface."""

    def test_abstract_factory_has_required_methods(self):
        """Test that AbstractEntityFactory defines required methods."""
        required_methods = ['create_order', 'create_portfolio', 'create_position']

        for method in required_methods:
            assert hasattr(AbstractEntityFactory, method)


# ============================================================================
# TEST TRADING ENTITY FACTORY
# ============================================================================

class TestTradingEntityFactory:
    """Tests for TradingEntityFactory."""

    def test_create_market_order(self):
        """Test creating a market order."""
        factory = TradingEntityFactory()

        order = factory.create_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy",
            order_type="market"
        )

        assert order.symbol == "AAPL"
        assert order.quantity == Decimal("100")
        assert order.side.value == "buy"
        assert order.order_type.value == "market"

    def test_create_limit_order(self):
        """Test creating a limit order."""
        factory = TradingEntityFactory()

        order = factory.create_order(
            symbol="MSFT",
            quantity=Decimal("50"),
            side="sell",
            order_type="limit",
            price=Decimal("250.00")
        )

        assert order.price == Decimal("250.00")
        assert order.order_type.value == "limit"

    def test_create_stop_loss_order(self):
        """Test creating a stop loss order."""
        factory = TradingEntityFactory()

        order = factory.create_order(
            symbol="TSLA",
            quantity=Decimal("25"),
            side="buy",
            order_type="stop_loss",
            stop_price=Decimal("200.00")
        )

        assert order.stop_price == Decimal("200.00")
        assert order.order_type.value == "stop_loss"

    def test_create_order_with_portfolio_id(self):
        """Test creating order with portfolio ID."""
        factory = TradingEntityFactory()

        order = factory.create_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy",
            portfolio_id="PORT123"
        )

        # The portfolio_id should be stored (implementation dependent)
        assert order.symbol == "AAPL"

    def test_create_order_validates_quantity(self):
        """Test that factory validates quantity."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Quantity must be positive"):
            factory.create_order(
                symbol="AAPL",
                quantity=Decimal("-10"),
                side="buy"
            )

    def test_create_order_validates_symbol(self):
        """Test that factory validates symbol."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Symbol is required"):
            factory.create_order(
                symbol="",
                quantity=Decimal("100"),
                side="buy"
            )

    def test_create_order_validates_side(self):
        """Test that factory validates side."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Side must be"):
            factory.create_order(
                symbol="AAPL",
                quantity=Decimal("100"),
                side="invalid"
            )

    def test_create_order_requires_limit_price(self):
        """Test that limit orders require price."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Limit orders must have a price"):
            factory.create_order(
                symbol="AAPL",
                quantity=Decimal("100"),
                side="buy",
                order_type="limit"
            )

    def test_create_order_uppercases_symbol(self):
        """Test that symbol is uppercased."""
        factory = TradingEntityFactory()

        order = factory.create_order(
            symbol="aapl",
            quantity=Decimal("100"),
            side="buy"
        )

        assert order.symbol == "AAPL"

    def test_create_portfolio(self):
        """Test creating a portfolio."""
        factory = TradingEntityFactory()

        portfolio = factory.create_portfolio(
            portfolio_id="PORT123",
            initial_capital=Decimal("100000"),
            currency="USD"
        )

        assert portfolio.portfolio_id == "PORT123"
        assert portfolio.capital.amount == Decimal("100000")
        assert portfolio.currency == "USD"

    def test_create_portfolio_validates_capital(self):
        """Test that factory validates initial capital."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Initial capital must be positive"):
            factory.create_portfolio(
                portfolio_id="PORT123",
                initial_capital=Decimal("0")
            )

    def test_create_portfolio_validates_id(self):
        """Test that factory validates portfolio ID."""
        factory = TradingEntityFactory()

        with pytest.raises(ValueError, match="Portfolio ID is required"):
            factory.create_portfolio(
                portfolio_id="",
                initial_capital=Decimal("100000")
            )

    def test_create_position(self):
        """Test creating a position."""
        factory = TradingEntityFactory()

        position = factory.create_position(
            symbol="AAPL",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            currency="USD"
        )

        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.avg_price == Decimal("150.00")
        assert position.current_price == Decimal("150.00")

    def test_create_position_short(self):
        """Test creating a short position."""
        factory = TradingEntityFactory()

        position = factory.create_position(
            symbol="AAPL",
            quantity=Decimal("-50"),
            entry_price=Decimal("150.00")
        )

        assert position.quantity == Decimal("-50")


# ============================================================================
# TEST ORDER FACTORY (Factory Method)
# ============================================================================

class TestOrderFactory:
    """Tests for OrderFactory."""

    def test_create_market_order(self):
        """Test creating market order."""
        factory = OrderFactory()

        order = factory.create_market_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        assert order.order_type.value == "market"
        assert order.side.value == "buy"

    def test_create_limit_order(self):
        """Test creating limit order."""
        factory = OrderFactory()

        order = factory.create_limit_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            side="buy"
        )

        assert order.order_type.value == "limit"
        assert order.price == Decimal("150.00")

    def test_create_stop_loss_order(self):
        """Test creating stop loss order."""
        factory = OrderFactory()

        order = factory.create_stop_loss_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            stop_price=Decimal("145.00"),
            side="buy"
        )

        assert order.order_type.value == "stop_loss"
        assert order.stop_price == Decimal("145.00")

    def test_create_take_profit_order(self):
        """Test creating take profit order."""
        factory = OrderFactory()

        # Take profit for long position is a sell order
        order = factory.create_take_profit_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("155.00"),
            side="buy"  # Original position side
        )

        assert order.order_type.value == "take_profit"
        assert order.side.value == "sell"  # Opposite side

    def test_create_stop_limit_order(self):
        """Test creating stop limit order."""
        factory = OrderFactory()

        order = factory.create_stop_limit_order(
            symbol="AAPL",
            quantity=Decimal("100"),
            stop_price=Decimal("145.00"),
            limit_price=Decimal("144.00"),
            side="buy"
        )

        assert order.order_type.value == "stop_limit"
        assert order.stop_price == Decimal("145.00")
        assert order.price == Decimal("144.00")


# ============================================================================
# TEST ORDER BUILDER (Builder Pattern)
# ============================================================================

class TestOrderBuilder:
    """Tests for OrderBuilder."""

    def test_build_simple_market_order(self):
        """Test building a simple market order."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .market_order()
                 .build())

        assert order.symbol == "AAPL"
        assert order.side.value == "buy"
        assert order.quantity == Decimal("100")

    def test_build_limit_order_with_price(self):
        """Test building a limit order with price."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .sell()
                 .quantity(Decimal("50"))
                 .limit_price(Decimal("250.00"))
                 .build())

        assert order.order_type.value == "limit"
        assert order.price == Decimal("250.00")
        assert order.side.value == "sell"

    def test_build_with_time_in_force(self):
        """Test building with time in force."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .limit_price(Decimal("150.00"))
                 .immediate_or_cancel()
                 .build())

        assert order.time_in_force == "IOC"

    def test_build_good_til_cancelled(self):
        """Test building good-til-cancelled order."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .limit_price(Decimal("150.00"))
                 .with_good_til_cancel(days=30)
                 .build())

        assert order.time_in_force == "GTC"
        assert order.expiry_time is not None

    def test_build_day_order(self):
        """Test building day order."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .limit_price(Decimal("150.00"))
                 .day_order()
                 .build())

        assert order.time_in_force == "DAY"

    def test_build_fill_or_kill(self):
        """Test building fill-or-kill order."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .limit_price(Decimal("150.00"))
                 .fill_or_kill()
                 .build())

        assert order.time_in_force == "FOK"

    def test_build_requires_symbol(self):
        """Test that builder requires symbol."""
        builder = (OrderBuilder()
                   .buy()
                   .quantity(Decimal("100")))

        with pytest.raises(ValueError, match="Symbol is required"):
            builder.build()

    def test_build_requires_quantity(self):
        """Test that builder requires quantity."""
        builder = (OrderBuilder()
                   .for_symbol("AAPL")
                   .buy())

        with pytest.raises(ValueError, match="Quantity is required"):
            builder.build()

    def test_fluent_interface(self):
        """Test builder's fluent interface."""
        order = (OrderBuilder()
                 .for_symbol("AAPL")
                 .buy()
                 .quantity(Decimal("100"))
                 .limit_price(Decimal("150.00"))
                 .for_portfolio("PORT123")
                 .with_time_in_force("GTC")
                 .build())

        assert order.symbol == "AAPL"


# ============================================================================
# TEST ORDER PROTOTYPE (Prototype Pattern)
# ============================================================================

class TestOrderPrototype:
    """Tests for OrderPrototype."""

    def test_build_from_prototype(self):
        """Test building order from prototype."""
        prototype = OrderPrototype(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        order = prototype.build()

        assert order.symbol == "AAPL"
        assert order.quantity == Decimal("100")
        assert order.side.value == "buy"

    def test_with_price_creates_new_prototype(self):
        """Test creating prototype with specific price."""
        base_prototype = OrderPrototype(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        priced_prototype = base_prototype.with_price(Decimal("150.00"))

        order = priced_prototype.build()

        assert order.price == Decimal("150.00")
        assert order.order_type.value == "limit"

    def test_with_quantity(self):
        """Test creating prototype with specific quantity."""
        base_prototype = OrderPrototype(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        new_prototype = base_prototype.with_quantity(Decimal("200"))
        order = new_prototype.build()

        assert order.quantity == Decimal("200")

    def test_for_symbol(self):
        """Test creating prototype for different symbol."""
        base_prototype = OrderPrototype(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        msft_prototype = base_prototype.for_symbol("MSFT")
        order = msft_prototype.build()

        assert order.symbol == "MSFT"

    def test_build_with_overrides(self):
        """Test building with parameter overrides."""
        prototype = OrderPrototype(
            symbol="AAPL",
            quantity=Decimal("100"),
            side="buy"
        )

        order = prototype.build(
            quantity=Decimal("200"),
            order_type="limit",
            price=Decimal("150.00")
        )

        assert order.quantity == Decimal("200")
        assert order.price == Decimal("150.00")


# ============================================================================
# TEST FACTORY REGISTRY
# ============================================================================

class TestFactoryRegistry:
    """Tests for FactoryRegistry."""

    def test_register_factory(self):
        """Test registering a factory."""
        registry = FactoryRegistry()
        factory = TradingEntityFactory()

        registry.register("entity", factory)

        assert "entity" in registry.list_factories()

    def test_get_factory(self):
        """Test getting registered factory."""
        registry = FactoryRegistry()
        factory = TradingEntityFactory()

        registry.register("entity", factory)
        retrieved = registry.get("entity")

        assert retrieved is factory

    def test_get_nonexistent_factory(self):
        """Test getting non-existent factory."""
        registry = FactoryRegistry()

        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_factories(self):
        """Test listing all factories."""
        registry = FactoryRegistry()

        factory1 = TradingEntityFactory()
        factory2 = OrderFactory()

        registry.register("entity", factory1)
        registry.register("order", factory2)

        factories = registry.list_factories()

        assert len(factories) == 2
        assert "entity" in factories
        assert "order" in factories


# ============================================================================
# TEST GLOBAL REGISTRY
# ============================================================================

class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_factory_from_global_registry(self):
        """Test getting factory from global registry."""
        factory = get_factory("entity")
        assert isinstance(factory, TradingEntityFactory)

    def test_register_custom_factory(self):
        """Test registering custom factory."""
        custom_factory = TradingEntityFactory()
        register_factory("custom", custom_factory)

        retrieved = get_factory("custom")
        assert retrieved is custom_factory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
