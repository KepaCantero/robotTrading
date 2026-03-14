# pylint: disable=arguments-differ
"""
Factory Pattern - Domain entity factories following Percival's Architecture Patterns with Python

This module implements the Factory pattern as described in
"Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory.

Key concepts:
- Abstract factories for creating families of related objects
- Factory methods for complex object construction
- Encapsulates creation logic from client code
- Supports dependency injection
- Enables testing with test doubles

Reference: Chapter 5, "Factories and Entities"

The Factory pattern is especially valuable for:
1. Complex object construction logic
2. Creating objects with valid initial state
3. Encapsulating dependencies
4. Supporting different implementations
5. Facilitating testing
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, TypeVar, Union

from typing_extensions import Protocol, runtime_checkable

from ..entities.order import Order, OrderSide, OrderStatus, OrderType
from ..entities.portfolio import Portfolio, PortfolioStatus, Position
from ..entities.position import PositionSide
from ..value_objects.capital import Capital
from ..value_objects.risk_parameters import RiskParameters

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================


# Protocol for factory interface
@runtime_checkable
class EntityFactoryProtocol(Protocol):
    """Protocol for entity factory implementations."""

    def create_order(
        self,
        symbol: str,
        quantity: Decimal,
        side: str = "buy",
        order_type: str = "market",
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        portfolio_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """Create an Order entity."""
        ...

    def create_portfolio(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        **kwargs,
    ) -> Portfolio:
        """Create a Portfolio entity."""
        ...

    def create_position(
        self,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        currency: str = "USD",
        side: Optional[str] = None,
        **kwargs,
    ) -> Position:
        """Create a Position entity."""
        ...


# ============================================================================
# ABSTRACT FACTORY - Creating families of related objects
# ============================================================================


class AbstractEntityFactory(ABC):
    """
    Abstract factory for creating domain entities.

    Following the Abstract Factory pattern, this defines the interface
    for creating families of related entities. Concrete implementations
    can provide different creation strategies.

    Example:
        ```python
        class TradingEntityFactory(AbstractEntityFactory):
            def create_order(self, **kwargs) -> Order:
                return Order(**kwargs)

            def create_portfolio(self, **kwargs) -> Portfolio:
                return Portfolio(**kwargs)
        ```
    """

    @abstractmethod
    def create_order(
        self,
        symbol: str,
        quantity: Decimal,
        side: str = "buy",
        order_type: str = "market",
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        portfolio_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """Create an Order entity."""

    @abstractmethod
    def create_portfolio(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        max_position_size_pct: Decimal = Decimal('0.2'),
        max_portfolio_exposure_pct: Decimal = Decimal('0.8'),
        **kwargs,
    ) -> Portfolio:
        """Create a Portfolio entity."""

    @abstractmethod
    def create_position(
        self,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        currency: str = "USD",
        side: Optional[str] = None,
        **kwargs,
    ) -> Position:
        """Create a Position entity."""


# ============================================================================
# CONCRETE FACTORY - Default implementation
# ============================================================================


class TradingEntityFactory(AbstractEntityFactory):
    """
    Concrete factory for creating trading domain entities.

    This factory provides methods to create entities with valid initial state,
    handling all the complex construction logic. Client code doesn't need
    to know the details of entity initialization.

    Example:
        ```python
        factory = TradingEntityFactory()

        # Create order with defaults
        order = factory.create_order(
            symbol="AAPL",
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            side='buy'
        )

        # Create portfolio with risk parameters
        portfolio = factory.create_portfolio(
            portfolio_id="PORT123",
            initial_capital=Decimal('100000'),
            currency="USD"
        )
        ```
    """

    def create_order(
        self,
        symbol: str,
        quantity: Decimal,
        side: str = "buy",
        order_type: str = "market",
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        portfolio_id: Optional[str] = None,
        **kwargs,
    ) -> Order:
        """
        Create an Order entity with valid initial state.

        Handles the complexity of order creation:
        - Validates inputs
        - Sets defaults
        - Generates IDs
        - Initializes callbacks

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', etc.)
            price: Limit price (required for limit orders)
            stop_price: Stop price (for stop orders)
            portfolio_id: Associated portfolio ID
            **kwargs: Additional order attributes

        Returns:
            Order entity ready for use

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate and normalize inputs
        if not symbol:
            raise ValueError("Symbol is required")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if side not in ('buy', 'sell'):
            raise ValueError("Side must be 'buy' or 'sell'")

        # Set price defaults based on order type
        if order_type == 'limit' and price is None:
            raise ValueError("Limit orders must have a price")
        if order_type in ('stop_loss', 'stop_limit') and stop_price is None:
            raise ValueError(f"{order_type} orders must have a stop price")

        # Generate order ID
        order_id = kwargs.get('order_id') or self._generate_order_id(symbol)

        # Create order entity
        order = Order(
            order_id=order_id,
            symbol=symbol.upper(),
            side=OrderSide[side.upper()],
            order_type=OrderType[order_type.upper()],
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            **kwargs,
        )

        logger.debug(f"Created order {order_id} for {symbol}")
        return order

    def create_portfolio(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        max_position_size_pct: Decimal = Decimal('0.2'),
        max_portfolio_exposure_pct: Decimal = Decimal('0.8'),
        **kwargs,
    ) -> Portfolio:
        """
        Create a Portfolio entity with valid initial state.

        Args:
            portfolio_id: Portfolio identifier
            initial_capital: Initial capital amount
            currency: Portfolio currency
            max_position_size_pct: Max position size as % of capital
            max_portfolio_exposure_pct: Max exposure as % of capital
            **kwargs: Additional portfolio attributes

        Returns:
            Portfolio entity ready for use

        Raises:
            ValueError: If parameters are invalid
        """
        if not portfolio_id:
            raise ValueError("Portfolio ID is required")
        if initial_capital <= 0:
            raise ValueError("Initial capital must be positive")

        # Create value objects
        capital = Capital.from_amount(amount=initial_capital, currency=currency)

        risk_parameters = RiskParameters(
            max_position_size=initial_capital * max_position_size_pct,
            max_portfolio_exposure=initial_capital * max_portfolio_exposure_pct,
            stop_loss_pct=Decimal("0.05"),
            take_profit_pct=Decimal("0.10"),
        )

        # Create portfolio entity
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            capital=capital,
            risk_parameters=risk_parameters,
            status=PortfolioStatus.ACTIVE,
            currency=currency,
            **kwargs,
        )

        logger.debug(f"Created portfolio {portfolio_id} with capital {initial_capital}")
        return portfolio

    def create_position(
        self,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        currency: str = "USD",
        side: Optional[str] = None,
        **kwargs,
    ) -> Position:
        """
        Create a Position entity.

        Args:
            symbol: Position symbol
            quantity: Position quantity (positive, side determines long/short)
            entry_price: Average entry price
            currency: Position currency
            side: Position side ('long' or 'short', auto-detected if not specified)
            **kwargs: Additional position attributes

        Returns:
            Position entity

        Raises:
            ValueError: If parameters are invalid

        Note:
            This method automatically determines the position side based on quantity sign:
            - Negative quantity -> short position (with positive quantity stored)
            - Positive quantity -> long position
            This provides backward compatibility with code that uses negative quantities
            for short positions while correctly using the PositionSide enum.
        """
        if not symbol:
            raise ValueError("Symbol is required")
        if quantity == 0:
            raise ValueError("Quantity cannot be zero")
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")

        # Auto-detect side from quantity if not explicitly provided
        # This maintains backward compatibility while properly setting the PositionSide enum
        if side is None:
            if quantity < 0:
                # Negative quantity means short - convert to positive and set side
                position_side = PositionSide.SHORT
                quantity = abs(quantity)
            else:
                position_side = PositionSide.LONG
        else:
            # Use explicit side parameter
            if side.lower() not in ('long', 'short'):
                raise ValueError("Side must be 'long' or 'short'")
            position_side = PositionSide[side.upper()]
            # Ensure quantity is positive regardless of side
            quantity = abs(quantity)

        position = Position(
            symbol=symbol.upper(),
            quantity=quantity,
            avg_price=entry_price,
            current_price=entry_price,
            side=position_side,
            currency=currency,
            **kwargs,
        )

        logger.debug(f"Created {position_side.value} position {symbol} with quantity {quantity}")
        return position

    def _generate_order_id(self, symbol: str) -> str:
        """Generate unique order ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ORD_{symbol}_{timestamp}"


# ============================================================================
# FACTORY METHOD - Parameterized creation
# ============================================================================


class OrderFactory:
    """
    Factory for creating different types of orders.

    Demonstrates the Factory Method pattern where each method
    creates a specific type of object with predefined parameters.

    Example:
        ```python
        factory = OrderFactory()

        # Create specific order types
        market_order = factory.create_market_order("AAPL", Decimal('100'), 'buy')
        limit_order = factory.create_limit_order("AAPL", Decimal('100'), Decimal('150'), 'buy')
        stop_loss = factory.create_stop_loss_order("AAPL", Decimal('100'), Decimal('145'), 'buy')
        ```
    """

    def __init__(self, entity_factory: Optional[AbstractEntityFactory] = None):
        """
        Initialize with optional entity factory.

        Args:
            entity_factory: Factory for creating entities (default: TradingEntityFactory)
        """
        self.entity_factory = entity_factory or TradingEntityFactory()

    def create_market_order(
        self, symbol: str, quantity: Decimal, side: str, portfolio_id: Optional[str] = None
    ) -> Order:
        """Create a market order (executes at current market price)."""
        return self.entity_factory.create_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type='market',
            portfolio_id=portfolio_id,
        )

    def create_limit_order(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        side: str,
        portfolio_id: Optional[str] = None,
    ) -> Order:
        """Create a limit order (executes at specified price or better)."""
        return self.entity_factory.create_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side=side,
            order_type='limit',
            portfolio_id=portfolio_id,
        )

    def create_stop_loss_order(
        self,
        symbol: str,
        quantity: Decimal,
        stop_price: Decimal,
        side: str,
        portfolio_id: Optional[str] = None,
    ) -> Order:
        """Create a stop-loss order (triggers when price hits stop price)."""
        return self.entity_factory.create_order(
            symbol=symbol,
            quantity=quantity,
            stop_price=stop_price,
            side=side,
            order_type='stop_loss',
            portfolio_id=portfolio_id,
        )

    def create_take_profit_order(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        side: str,
        portfolio_id: Optional[str] = None,
    ) -> Order:
        """Create a take-profit order (closes position at target price)."""
        # Take profit is opposite side of current position
        original_side = 'buy' if side == 'sell' else 'sell'
        return self.entity_factory.create_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side=original_side,
            order_type='take_profit',
            portfolio_id=portfolio_id,
        )

    def create_stop_limit_order(
        self,
        symbol: str,
        quantity: Decimal,
        stop_price: Decimal,
        limit_price: Decimal,
        side: str,
        portfolio_id: Optional[str] = None,
    ) -> Order:
        """Create a stop-limit order (combines stop and limit orders)."""
        return self.entity_factory.create_order(
            symbol=symbol,
            quantity=quantity,
            stop_price=stop_price,
            price=limit_price,
            side=side,
            order_type='stop_limit',
            portfolio_id=portfolio_id,
        )


# ============================================================================
# BUILDER FACTORY - Step-by-step construction
# ============================================================================


class OrderBuilder:
    """
    Builder for complex order construction.

    The Builder pattern provides a fluent interface for constructing
    complex objects step by step.

    Example:
        ```python
        order = (OrderBuilder()
            .for_symbol("AAPL")
            .buy()
            .quantity(100)
            .limit_price(150.00)
            .with_time_in_force("GTC")
            .with_good_til_cancel(days=30)
            .build())
        ```
    """

    def __init__(self):
        """Initialize builder with defaults."""
        self._symbol: Optional[str] = None
        self._side: str = "buy"
        self._quantity: Optional[Decimal] = None
        self._price: Optional[Decimal] = None
        self._stop_price: Optional[Decimal] = None
        self._order_type: str = "market"
        self._portfolio_id: Optional[str] = None
        self._time_in_force: str = "GTC"
        self._expiry_time: Optional[datetime] = None
        self._entity_factory = TradingEntityFactory()

    def for_symbol(self, symbol: str) -> "OrderBuilder":
        """Set the trading symbol."""
        self._symbol = symbol
        return self

    def buy(self) -> "OrderBuilder":
        """Set order side to buy."""
        self._side = "buy"
        return self

    def sell(self) -> "OrderBuilder":
        """Set order side to sell."""
        self._side = "sell"
        return self

    def quantity(self, qty: Decimal) -> "OrderBuilder":
        """Set order quantity."""
        self._quantity = qty
        return self

    def market_order(self) -> "OrderBuilder":
        """Set order type to market."""
        self._order_type = "market"
        return self

    def limit_price(self, price: Decimal) -> "OrderBuilder":
        """Set limit price (makes it a limit order)."""
        self._price = price
        self._order_type = "limit"
        return self

    def stop_price(self, price: Decimal) -> "OrderBuilder":
        """Set stop price (makes it a stop order)."""
        self._stop_price = price
        self._order_type = "stop_loss"
        return self

    def for_portfolio(self, portfolio_id: str) -> "OrderBuilder":
        """Set the portfolio ID."""
        self._portfolio_id = portfolio_id
        return self

    def with_time_in_force(self, tif: str) -> "OrderBuilder":
        """Set time in force (GTC, IOC, FOK, DAY)."""
        self._time_in_force = tif
        return self

    def with_good_til_cancel(self, days: int = 30) -> "OrderBuilder":
        """Set good-til-cancelled with expiry days."""
        from datetime import timedelta

        self._time_in_force = "GTC"
        self._expiry_time = datetime.utcnow() + timedelta(days=days)
        return self

    def day_order(self) -> "OrderBuilder":
        """Set as day order (expires at end of day)."""
        self._time_in_force = "DAY"
        return self

    def immediate_or_cancel(self) -> "OrderBuilder":
        """Set as immediate-or-cancel (IOC)."""
        self._time_in_force = "IOC"
        return self

    def fill_or_kill(self) -> "OrderBuilder":
        """Set as fill-or-kill (FOK)."""
        self._time_in_force = "FOK"
        return self

    def with_factory(self, factory: AbstractEntityFactory) -> "OrderBuilder":
        """Set custom entity factory."""
        self._entity_factory = factory
        return self

    def build(self) -> Order:
        """
        Build the order with all specified parameters.

        Returns:
            Order entity

        Raises:
            ValueError: If required parameters are missing
        """
        if not self._symbol:
            raise ValueError("Symbol is required")
        if not self._quantity:
            raise ValueError("Quantity is required")

        return self._entity_factory.create_order(
            symbol=self._symbol,
            quantity=self._quantity,
            side=self._side,
            order_type=self._order_type,
            price=self._price,
            stop_price=self._stop_price,
            portfolio_id=self._portfolio_id,
            time_in_force=self._time_in_force,
            expiry_time=self._expiry_time,
        )


# ============================================================================
# PROTOTYPE FACTORY - Cloning existing objects
# ============================================================================


class OrderPrototype:
    """
    Prototype for creating orders by cloning.

    Useful when you need to create many similar orders with
    minor variations.

    Example:
        ```python
        # Create prototype
        prototype = OrderPrototype(symbol="AAPL", quantity=Decimal('100'), side='buy')

        # Create variations
        order1 = prototype.with_price(Decimal('150.00')).build()
        order2 = prototype.with_price(Decimal('151.00')).build()
        order3 = prototype.with_price(Decimal('152.00')).build()
        ```
    """

    def __init__(
        self,
        *,
        symbol: str,
        quantity: Decimal,
        side: str = "buy",
        order_type: str = "market",
        portfolio_id: Optional[str] = None,
        price: Optional[Decimal] = None,
    ):
        """Initialize prototype with base parameters."""
        self._symbol: str = symbol
        self._quantity: Decimal = quantity
        self._side: str = side
        self._order_type: str = order_type
        self._portfolio_id: Optional[str] = portfolio_id
        self._price: Optional[Decimal] = price
        self._factory = TradingEntityFactory()

    def with_price(self, price: Decimal) -> "OrderPrototype":
        """Create prototype with specific price."""
        return OrderPrototype(
            symbol=self._symbol,
            quantity=self._quantity,
            side=self._side,
            order_type='limit',
            portfolio_id=self._portfolio_id,
            price=price,
        )

    def with_quantity(self, quantity: Decimal) -> "OrderPrototype":
        """Create prototype with specific quantity."""
        return OrderPrototype(
            symbol=self._symbol,
            quantity=quantity,
            side=self._side,
            order_type=self._order_type,
            portfolio_id=self._portfolio_id,
            price=self._price,
        )

    def for_symbol(self, symbol: str) -> "OrderPrototype":
        """Create prototype for different symbol."""
        return OrderPrototype(
            symbol=symbol,
            quantity=self._quantity,
            side=self._side,
            order_type=self._order_type,
            portfolio_id=self._portfolio_id,
            price=self._price,
        )

    def build(
        self,
        symbol: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        side: Optional[str] = None,
        order_type: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        price: Optional[Decimal] = None,
        **kwargs,
    ) -> Order:
        """
        Build order from prototype with optional overrides.

        Args:
            symbol: Override symbol
            quantity: Override quantity
            side: Override side
            order_type: Override order type
            portfolio_id: Override portfolio ID
            price: Override price
            **kwargs: Additional parameters

        Returns:
            Order entity
        """
        return self._factory.create_order(
            symbol=symbol or self._symbol,
            quantity=quantity or self._quantity,
            side=side or self._side,
            order_type=order_type or self._order_type,
            portfolio_id=portfolio_id or self._portfolio_id,
            price=price or self._price,
            **kwargs,
        )


# ============================================================================
# FACTORY REGISTRY - Managing multiple factories
# ============================================================================


class FactoryRegistry:
    """
    Registry for managing multiple factories.

    Provides a central point for accessing different factories
    and supports dependency injection.

    Example:
        ```python
        registry = FactoryRegistry()
        registry.register('orders', OrderFactory())
        registry.register('portfolios', PortfolioFactory())

        order_factory = registry.get('orders')
        order = order_factory.create_market_order("AAPL", 100, 'buy')
        ```
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._factories: Dict[
            str, Union[AbstractEntityFactory, "OrderFactory", "OrderBuilder", "OrderPrototype"]
        ] = {}

    def register(
        self,
        name: str,
        factory: Union[AbstractEntityFactory, "OrderFactory", "OrderBuilder", "OrderPrototype"],
    ) -> None:
        """
        Register a factory.

        Args:
            name: Factory name
            factory: Factory instance
        """
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")

    def get(
        self, name: str
    ) -> Union[AbstractEntityFactory, "OrderFactory", "OrderBuilder", "OrderPrototype"]:
        """
        Get a registered factory.

        Args:
            name: Factory name

        Returns:
            Factory instance

        Raises:
            KeyError: If factory not registered
        """
        if name not in self._factories:
            raise KeyError(f"Factory '{name}' not registered")
        return self._factories[name]

    def list_factories(self) -> List[str]:
        """List all registered factory names."""
        return list(self._factories.keys())


# ============================================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================================

# Default global registry
_default_registry = FactoryRegistry()
_default_registry.register('entity', TradingEntityFactory())
_default_registry.register('order', OrderFactory())


def get_factory(
    name: str,
) -> Union[AbstractEntityFactory, "OrderFactory", "OrderBuilder", "OrderPrototype"]:
    """
    Get a factory from the default registry.

    Args:
        name: Factory name

    Returns:
        Factory instance
    """
    return _default_registry.get(name)


def register_factory(
    name: str,
    factory: Union[AbstractEntityFactory, "OrderFactory", "OrderBuilder", "OrderPrototype"],
) -> None:
    """
    Register a factory in the default registry.

    Args:
        name: Factory name
        factory: Factory instance
    """
    _default_registry.register(name, factory)
