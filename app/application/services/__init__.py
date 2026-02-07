"""
Service Layer Pattern - Application services following Percival's Architecture Patterns with Python

This module implements the Service Layer pattern as described in
"Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory.

Key concepts:
- Application services orchestrate business use cases
- Coordinate between domain entities and repositories
- Implement transaction boundaries
- Handle cross-cutting concerns (logging, validation)
- No business logic (delegates to domain entities)

Reference: Chapter 11, "Service Layer"

The Service Layer pattern is especially valuable for:
1. Encapsulating use case logic
2. Coordinating multiple aggregates
3. Managing transactions
4. Separating concerns from domain layer
5. Providing API for higher layers
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from app.domain.entities.order import Order, OrderSide, OrderType
from app.domain.entities.portfolio import Portfolio, Position
from app.domain.repositories.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# COMMAND QUERY RESPONSIBILITY SEGREGATION (CQRS)
# ============================================================================


class Command(ABC):
    """
    Base class for commands following CQRS pattern.

    Commands represent intent to change system state. They are
    imperative (DoSomething) and should be named accordingly.

    Command principles:
    - Command changes state
    - Command returns nothing (void) or minimal result
    - Command name is imperative (CreateOrder, SubmitOrder)
    - Command is validated before execution
    - Command execution is atomic (within UoW)

    Example:
        ```python
        class CreateOrderCommand(Command):
            def __init__(self, symbol: str, quantity: Decimal, price: Decimal):
                self.symbol = symbol
                self.quantity = quantity
                self.price = price

            def validate(self) -> bool:
                return self.quantity > 0 and self.price > 0
        ```
    """

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate command before execution.

        Returns:
            True if command is valid

        Raises:
            ValidationError: If command is invalid
        """


class Query(ABC, Generic[T]):
    """
    Base class for queries following CQRS pattern.

    Queries represent intent to read system state. They do not
    modify state and should return data.

    Query principles:
    - Query reads state
    - Query returns data
    - Query name is declarative (GetOrder, FindOrdersByStatus)
    - Query never modifies state
    - Query can be cached

    Example:
        ```python
        class GetOrderQuery(Query[Order]):
            def __init__(self, order_id: str):
                self.order_id = order_id

            def execute(self, uow: AbstractUnitOfWork) -> Optional[Order]:
                return uow.orders.get(self.order_id)
        ```
    """

    @abstractmethod
    async def execute(self, uow: AbstractUnitOfWork) -> T:
        """
        Execute the query.

        Args:
            uow: Unit of Work for repository access

        Returns:
            Query result

        Note:
            This method should NOT modify any state
        """


# ============================================================================
# COMMAND HANDLERS
# ============================================================================


class CommandHandler(ABC):
    """
    Base class for command handlers.

    Command handlers execute commands within a Unit of Work boundary.
    They coordinate between repositories and domain entities to
    fulfill the command's intent.

    Example:
        ```python
        class CreateOrderHandler(CommandHandler):
            async def handle(self, command: CreateOrderCommand, uow: AbstractUnitOfWork):
                order = Order(
                    order_id=generate_id(),
                    symbol=command.symbol,
                    quantity=command.quantity,
                    price=command.price
                )
                order.validate()
                uow.orders.add(order)
        ```
    """

    @abstractmethod
    async def handle(self, command: Command, uow: AbstractUnitOfWork) -> None:
        """
        Handle the command.

        Args:
            command: Command to execute
            uow: Unit of Work for repository access

        Raises:
            ValidationError: If command is invalid
            BusinessRuleError: If business rule is violated
        """


# ============================================================================
# APPLICATION SERVICE BASE
# ============================================================================


class ApplicationService:  # Concrete base class with shared functionality
    """
    Base class for application services.

    Application services orchestrate use cases by:
    1. Validating input
    2. Coordinating domain objects
    3. Managing transactions
    4. Handling errors
    5. Publishing events

    They do NOT contain business logic - that belongs in domain entities.

    Example:
        ```python
        class OrderService(ApplicationService):
            def __init__(self, uow_factory):
                self.uow_factory = uow_factory

            async def create_order(self, command: CreateOrderCommand) -> str:
                async with self.uow_factory() as uow:
                    order = Order(...)
                    uow.orders.add(order)
                    return order.order_id
        ```
    """

    def __init__(self, uow_factory: Any):
        """
        Initialize service with Unit of Work factory.

        Args:
            uow_factory: Factory function for creating Unit of Work instances
        """
        self.uow_factory = uow_factory

    async def _execute_in_transaction(
        self, operation: Callable, uow: Optional[AbstractUnitOfWork] = None
    ) -> Any:
        """
        Execute an operation within a transaction.

        Args:
            operation: Async function to execute
            uow: Optional existing Unit of Work

        Returns:
            Operation result
        """
        if uow:
            return await operation(uow)

        async with self.uow_factory() as uow:
            return await operation(uow)


# ============================================================================
# TRADING DOMAIN APPLICATION SERVICES
# ============================================================================


# Commands
@dataclass
class CreateOrderCommand(Command):
    """Command to create a new order."""

    symbol: str
    quantity: Decimal
    price: Optional[Decimal]
    order_type: str  # 'market', 'limit', etc.
    side: str  # 'buy', 'sell'
    portfolio_id: str

    def validate(self) -> bool:
        """Validate order command."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.order_type == 'limit' and (not self.price or self.price <= 0):
            raise ValueError("Limit orders must have a positive price")
        if self.side not in ('buy', 'sell'):
            raise ValueError("Side must be 'buy' or 'sell'")
        if not self.symbol:
            raise ValueError("Symbol is required")
        return True


@dataclass
class SubmitOrderCommand(Command):
    """Command to submit an order for execution."""

    order_id: str

    def validate(self) -> bool:
        """Validate submit command."""
        if not self.order_id:
            raise ValueError("Order ID is required")
        return True


@dataclass
class CancelOrderCommand(Command):
    """Command to cancel an order."""

    order_id: str
    reason: Optional[str] = None

    def validate(self) -> bool:
        """Validate cancel command."""
        if not self.order_id:
            raise ValueError("Order ID is required")
        return True


# Queries
class GetOrderQuery(Query[Optional[Order]]):
    """Query to get an order by ID."""

    def __init__(self, order_id: str):
        self.order_id = order_id

    async def execute(self, uow: AbstractUnitOfWork) -> Optional[Order]:
        """Execute query to find order."""
        return await uow.orders.get(self.order_id)


class GetPortfolioOrdersQuery(Query[List[Order]]):
    """Query to get all orders for a portfolio."""

    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id

    async def execute(self, uow: AbstractUnitOfWork) -> List[Order]:
        """Execute query to find portfolio orders."""
        return await uow.orders.find_by_portfolio(self.portfolio_id)  # type: ignore[attr-defined]


# Service
class OrderApplicationService(ApplicationService):
    """
    Application service for order management.

    This service coordinates order-related use cases:
    - Creating orders
    - Submitting orders
    - Canceling orders
    - Querying orders

    Business logic is delegated to domain entities (Order, Portfolio).
    This service only orchestrates the flow.

    Example:
        ```python
        order_service = OrderApplicationService(uow_factory)

        # Create order
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            order_type='limit',
            side='buy',
            portfolio_id='PORT123'
        )
        order_id = await order_service.create_order(command)

        # Submit order
        await order_service.submit_order(SubmitOrderCommand(order_id))
        ```
    """

    async def create_order(self, command: CreateOrderCommand) -> str:
        """
        Create a new order.

        Use case: User wants to place a new order.

        Args:
            command: Create order command

        Returns:
            ID of created order

        Raises:
            ValidationError: If command is invalid
            BusinessRuleError: If business rule is violated
        """
        # Validate command
        command.validate()

        async def _create(uow: AbstractUnitOfWork) -> str:
            # Load portfolio
            portfolio = await uow.portfolios.get(command.portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {command.portfolio_id} not found")

            # Create order entity (domain creates the ID)
            order_id = self._generate_order_id()
            order = Order(
                order_id=order_id,
                symbol=command.symbol,
                quantity=command.quantity,
                price=command.price,
                order_type=OrderType[command.order_type.upper()],
                side=OrderSide[command.side.upper()],
            )

            # Domain validates business rules
            if not order.validate():
                raise ValueError(f"Order validation failed: {order.validation_errors}")

            # Portfolio validates risk limits
            if portfolio.is_risk_limit_exceeded(command.quantity * (command.price or Decimal('0'))):
                raise ValueError("Order exceeds portfolio risk limits")

            # Save order
            await uow.orders.add(order)
            logger.info(f"Created order {order_id} for portfolio {command.portfolio_id}")

            return order_id

        return await self._execute_in_transaction(_create)

    async def submit_order(self, command: SubmitOrderCommand) -> None:
        """
        Submit an order for execution.

        Use case: User wants to submit a validated order.

        Args:
            command: Submit order command

        Raises:
            ValidationError: If order is not in valid state
        """
        command.validate()

        async def _submit(uow: AbstractUnitOfWork) -> None:
            order = await uow.orders.get(command.order_id)
            if not order:
                raise ValueError(f"Order {command.order_id} not found")

            # Domain handles state transition
            order.submit()

            # Update order
            await uow.orders.update(order)
            logger.info(f"Submitted order {command.order_id}")

        await self._execute_in_transaction(_submit)

    async def cancel_order(self, command: CancelOrderCommand) -> None:
        """
        Cancel an order.

        Use case: User wants to cancel a pending order.

        Args:
            command: Cancel order command

        Raises:
            ValidationError: If order cannot be canceled
        """
        command.validate()

        async def _cancel(uow: AbstractUnitOfWork) -> None:
            order = await uow.orders.get(command.order_id)
            if not order:
                raise ValueError(f"Order {command.order_id} not found")

            # Domain handles state transition
            order.request_cancel()
            order.confirm_cancel()

            # Update order
            await uow.orders.update(order)
            logger.info(f"Canceled order {command.order_id}")

        await self._execute_in_transaction(_cancel)

    async def get_order(self, query: GetOrderQuery) -> Optional[Order]:
        """
        Get an order by ID.

        Args:
            query: Get order query

        Returns:
            Order if found, None otherwise
        """
        async with self.uow_factory() as uow:
            return await query.execute(uow)

    async def get_portfolio_orders(self, query: GetPortfolioOrdersQuery) -> List[Order]:
        """
        Get all orders for a portfolio.

        Args:
            query: Get portfolio orders query

        Returns:
            List of orders
        """
        async with self.uow_factory() as uow:
            return await query.execute(uow)

    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ORD_{timestamp}"


# Portfolio Application Service
class PortfolioApplicationService(ApplicationService):
    """
    Application service for portfolio management.

    Coordinates portfolio-related use cases:
    - Creating portfolios
    - Adding/removing positions
    - Updating prices
    - Risk monitoring
    """

    async def create_portfolio(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
    ) -> str:
        """
        Create a new portfolio.

        Args:
            portfolio_id: Portfolio identifier
            initial_capital: Initial capital amount
            currency: Portfolio currency

        Returns:
            Portfolio ID
        """

        async def _create(uow: AbstractUnitOfWork) -> str:
            # pylint: disable=import-outside-toplevel
            from app.domain.value_objects.capital import Capital
            from app.domain.value_objects.risk_parameters import RiskParameters

            # Create portfolio entity
            # pylint: disable=no-value-for-parameter
            capital = Capital.from_amount(amount=initial_capital, currency=currency)
            portfolio = Portfolio(
                portfolio_id=portfolio_id,
                capital=capital,
                risk_parameters=RiskParameters.for_tier(tier=capital.tier.value),
            )
            # pylint: enable=no-value-for-parameter

            # Save portfolio
            await uow.portfolios.add(portfolio)
            logger.info(f"Created portfolio {portfolio_id} with capital {initial_capital}")

            return portfolio_id

        return await self._execute_in_transaction(_create)

    async def add_position(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        """
        Add a position to a portfolio.

        Args:
            portfolio_id: Portfolio ID
            symbol: Symbol for position
            quantity: Position quantity
            price: Entry price
        """

        async def _add(uow: AbstractUnitOfWork) -> None:
            portfolio = await uow.portfolios.get(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            # Create position
            position = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                currency=portfolio.currency,
            )

            # Portfolio validates business rules
            portfolio.add_position(position)

            # Save changes
            await uow.portfolios.update(portfolio)
            await uow.positions.save(portfolio_id, position)  # type: ignore[attr-defined]
            logger.info(f"Added position {symbol} to portfolio {portfolio_id}")

        await self._execute_in_transaction(_add)

    async def update_position_prices(self, portfolio_id: str, prices: Dict[str, Decimal]) -> None:
        """
        Update current prices for positions.

        Args:
            portfolio_id: Portfolio ID
            prices: Dictionary of symbol -> price
        """

        async def _update(uow: AbstractUnitOfWork) -> None:
            portfolio = await uow.portfolios.get(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            # Update each position
            for symbol, price in prices.items():
                position = portfolio.get_position(symbol)
                if position:
                    position.update_price(price)

            # Save changes
            await uow.portfolios.update(portfolio)
            logger.info(f"Updated prices for {len(prices)} positions")

        await self._execute_in_transaction(_update)


# ============================================================================
# SERVICE ORCHESTRATION
# ============================================================================


class ServiceOrchestrator:
    """
    Orchestrates multiple application services.

    Coordinates complex use cases that span multiple services
    while maintaining transaction boundaries.

    Example:
        ```python
        orchestrator = ServiceOrchestrator()
        orchestrator.register_service('orders', order_service)
        orchestrator.register_service('portfolios', portfolio_service)

        # Execute orchestrated workflow
        await orchestrator.execute_workflow(
            'create_and_submit_order',
            order_command=create_order_cmd,
            portfolio_command=update_portfolio_cmd
        )
        ```
    """

    def __init__(self):
        self._services: Dict[str, ApplicationService] = {}

    def register_service(self, name: str, service: ApplicationService) -> None:
        """Register an application service."""
        self._services[name] = service

    async def execute_workflow(self, workflow_name: str, **kwargs) -> Any:
        """
        Execute a multi-service workflow.

        Args:
            workflow_name: Name of workflow to execute
            **kwargs: Workflow parameters

        Returns:
            Workflow result
        """
        if workflow_name == 'create_and_submit_order':
            return await self._create_and_submit_order(**kwargs)
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

    async def _create_and_submit_order(self, order_command: CreateOrderCommand) -> str:
        """
        Create and submit an order in one workflow.

        This demonstrates how multiple services can be coordinated
        while maintaining transaction boundaries.
        """
        order_service = self._services.get('orders')
        if not order_service:
            raise ValueError("Order service not registered")

        # Create order
        order_id = await order_service.create_order(order_command)  # type: ignore[attr-defined]

        # Submit order (in same transaction if needed, or separate)
        await order_service.submit_order(SubmitOrderCommand(order_id))  # type: ignore[attr-defined]

        return order_id


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ValidationError(Exception):
    """Raised when command validation fails."""


class BusinessRuleError(Exception):
    """Raised when business rule is violated."""


class NotFoundError(Exception):
    """Raised when entity is not found."""


# ============================================================================
# INPUT PROFILE ROUTING & CONFIGURATION SERVICES
# ============================================================================

# pylint: disable=wrong-import-position  # Intentional: avoid circular imports
from .input_profile_router import (  # noqa: E402
    InputProfileRouter,
    OptimizationConfig,
    OptimizationType,
    RebalancingFrequency,
    RiskConfig,
    StrategyType,
    SystemConfiguration,
    TaxConfig,
)
from .risk_configurator import (  # noqa: E402
    DrawdownMetrics,
    RiskBudget,
    RiskConfigurator,
    RiskLimit,
    RiskLimitType,
    StressTestScenario,
    VaRResult,
)
from .tax_optimizer import (  # noqa: E402
    TaxCalculation,
    TaxJurisdiction,
    TaxLot,
    TaxMethod,
    TaxOptimizer,
)

# pylint: enable=wrong-import-position

__all__ = [
    # CQRS
    "Command",
    "Query",
    "CommandHandler",
    "ApplicationService",
    "ServiceOrchestrator",
    # Exceptions
    "ValidationError",
    "BusinessRuleError",
    "NotFoundError",
    # Order Service
    "CreateOrderCommand",
    "SubmitOrderCommand",
    "CancelOrderCommand",
    "GetOrderQuery",
    "GetPortfolioOrdersQuery",
    "OrderApplicationService",
    # Portfolio Service
    "PortfolioApplicationService",
    # InputProfile Router
    "InputProfileRouter",
    "SystemConfiguration",
    "StrategyType",
    "OptimizationType",
    "RebalancingFrequency",
    "RiskConfig",
    "OptimizationConfig",
    "TaxConfig",
    # Risk Configurator
    "RiskConfigurator",
    "RiskLimit",
    "RiskLimitType",
    "VaRResult",
    "DrawdownMetrics",
    "RiskBudget",
    "StressTestScenario",
    # Tax Optimizer
    "TaxOptimizer",
    "TaxLot",
    "TaxCalculation",
    "TaxMethod",
    "TaxJurisdiction",
]
