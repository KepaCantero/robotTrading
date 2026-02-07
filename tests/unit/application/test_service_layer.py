"""
Tests for Service Layer Pattern following Percival's Architecture Patterns with Python.

Tests verify that the Service Layer pattern correctly implements:
- Application services
- Command Query Responsibility Segregation (CQRS)
- Command handlers
- Query handlers
- Service orchestration
"""
from decimal import Decimal
from typing import List, Optional

import pytest

from app.application.services import (
    CancelOrderCommand,
    CreateOrderCommand,
    GetOrderQuery,
    OrderApplicationService,
    PortfolioApplicationService,
    ServiceOrchestrator,
    SubmitOrderCommand,
)
from app.domain.entities.order import Order, OrderSide, OrderStatus, OrderType
from app.domain.entities.portfolio import Portfolio
from app.domain.repositories.base_repository import AbstractRepository
from app.domain.repositories.unit_of_work import AbstractUnitOfWork

# ============================================================================
# MOCK REPOSITORIES
# ============================================================================


class MockOrderRepository(AbstractRepository[Order, str]):
    """Mock order repository for testing."""

    def __init__(self):
        self._orders: dict[str, Order] = {}

    async def add(self, order: Order) -> None:
        self._orders[order.order_id] = order

    async def get(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    async def update(self, order: Order) -> None:
        if order.order_id in self._orders:
            self._orders[order.order_id] = order

    async def delete(self, order_id: str) -> None:
        self._orders.pop(order_id, None)

    async def list_all(self) -> List[Order]:
        return list(self._orders.values())


class MockPortfolioRepository(AbstractRepository[Portfolio, str]):
    """Mock portfolio repository for testing."""

    def __init__(self):
        self._portfolios: dict[str, Portfolio] = {}

    async def add(self, portfolio: Portfolio) -> None:
        self._portfolios[portfolio.portfolio_id] = portfolio

    async def get(self, portfolio_id: str) -> Optional[Portfolio]:
        return self._portfolios.get(portfolio_id)

    async def update(self, portfolio: Portfolio) -> None:
        if portfolio.portfolio_id in self._portfolios:
            self._portfolios[portfolio.portfolio_id] = portfolio

    async def delete(self, portfolio_id: str) -> None:
        self._portfolios.pop(portfolio_id, None)

    async def list_all(self) -> List[Portfolio]:
        return list(self._portfolios.values())


# ============================================================================
# MOCK UNIT OF WORK
# ============================================================================


class MockUnitOfWork(AbstractUnitOfWork):
    """Mock Unit of Work for testing."""

    def __init__(self):
        self.orders = MockOrderRepository()
        self.portfolios = MockPortfolioRepository()
        self._committed = False

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._committed = False

    def collect_new_events(self) -> List:
        return []


class MockUnitOfWorkFactory:
    """Factory for creating MockUnitOfWork instances."""

    def __call__(self):
        return MockUnitOfWork()


# ============================================================================
# TEST COMMANDS
# ============================================================================


class TestCreateOrderCommand:
    """Tests for CreateOrderCommand."""

    def test_valid_command(self):
        """Test creating valid order command."""
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        assert command.validate() is True

    def test_invalid_quantity_raises_error(self):
        """Test that invalid quantity raises error."""
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("-10"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            command.validate()

    def test_limit_order_without_price_raises_error(self):
        """Test that limit order without price raises error."""
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=None,
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        with pytest.raises(ValueError, match="Limit orders must have a price"):
            command.validate()

    def test_invalid_side_raises_error(self):
        """Test that invalid side raises error."""
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="invalid",
            portfolio_id="PORT123",
        )

        with pytest.raises(ValueError, match="Side must be"):
            command.validate()

    def test_empty_symbol_raises_error(self):
        """Test that empty symbol raises error."""
        command = CreateOrderCommand(
            symbol="",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        with pytest.raises(ValueError, match="Symbol is required"):
            command.validate()


# ============================================================================
# TEST QUERIES
# ============================================================================


class TestGetOrderQuery:
    """Tests for GetOrderQuery."""

    @pytest.mark.asyncio
    async def test_execute_query(self):
        """Test executing get order query."""
        uow = MockUnitOfWork()

        # Create order
        order = Order(
            order_id="ORD123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
        )
        await uow.orders.add(order)

        # Execute query
        query = GetOrderQuery("ORD123")
        result = await query.execute(uow)

        assert result is not None
        assert result.order_id == "ORD123"

    @pytest.mark.asyncio
    async def test_execute_query_not_found(self):
        """Test executing query for non-existent order."""
        uow = MockUnitOfWork()

        query = GetOrderQuery("NONEXISTENT")
        result = await query.execute(uow)

        assert result is None


# ============================================================================
# TEST ORDER APPLICATION SERVICE
# ============================================================================


class TestOrderApplicationService:
    """Tests for OrderApplicationService."""

    @pytest.mark.asyncio
    async def test_create_order(self):
        """Test creating an order."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        # First create a portfolio
        async with MockUnitOfWork() as uow:
            from app.domain.value_objects.capital import Capital
            from app.domain.value_objects.risk_parameters import RiskParameters

            portfolio = Portfolio(
                portfolio_id="PORT123",
                capital=Capital(amount=Decimal("100000"), currency="USD"),
                risk_parameters=RiskParameters(
                    max_position_size=Decimal("20000"), max_portfolio_exposure=Decimal("80000")
                ),
            )
            await uow.portfolios.add(portfolio)
            uow.commit()

        # Create order
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        order_id = await service.create_order(command)

        assert order_id is not None
        assert order_id.startswith("ORD_")

    @pytest.mark.asyncio
    async def test_create_order_portfolio_not_found(self):
        """Test creating order with non-existent portfolio."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="NONEXISTENT",
        )

        with pytest.raises(ValueError, match="Portfolio .* not found"):
            await service.create_order(command)

    @pytest.mark.asyncio
    async def test_submit_order(self):
        """Test submitting an order."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        # Create order
        async with MockUnitOfWork() as uow:
            order = Order(
                order_id="ORD123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                status=OrderStatus.VALIDATED,
            )
            await uow.orders.add(order)
            uow.commit()

        # Submit order
        command = SubmitOrderCommand("ORD123")
        await service.submit_order(command)

        # Verify
        async with MockUnitOfWork() as uow:
            submitted = await uow.orders.get("ORD123")
            assert submitted.status == OrderStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_submit_order_not_found(self):
        """Test submitting non-existent order."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        command = SubmitOrderCommand("NONEXISTENT")

        with pytest.raises(ValueError, match="Order .* not found"):
            await service.submit_order(command)

    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """Test canceling an order."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        # Create order
        async with MockUnitOfWork() as uow:
            order = Order(
                order_id="ORD123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
                status=OrderStatus.ACKNOWLEDGED,
            )
            await uow.orders.add(order)
            uow.commit()

        # Cancel order
        command = CancelOrderCommand("ORD123")
        await service.cancel_order(command)

        # Verify
        async with MockUnitOfWork() as uow:
            canceled = await uow.orders.get("ORD123")
            assert canceled.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_order(self):
        """Test getting an order."""
        service = OrderApplicationService(MockUnitOfWorkFactory())

        # Create order
        async with MockUnitOfWork() as uow:
            order = Order(
                order_id="ORD123",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("100"),
                price=Decimal("150.00"),
            )
            await uow.orders.add(order)
            uow.commit()

        # Get order
        query = GetOrderQuery("ORD123")
        result = await service.get_order(query)

        assert result is not None
        assert result.order_id == "ORD123"


# ============================================================================
# TEST PORTFOLIO APPLICATION SERVICE
# ============================================================================


class TestPortfolioApplicationService:
    """Tests for PortfolioApplicationService."""

    @pytest.mark.asyncio
    async def test_create_portfolio(self):
        """Test creating a portfolio."""
        service = PortfolioApplicationService(MockUnitOfWorkFactory())

        portfolio_id = await service.create_portfolio(
            portfolio_id="PORT123", initial_capital=Decimal("100000"), currency="USD"
        )

        assert portfolio_id == "PORT123"

    @pytest.mark.asyncio
    async def test_add_position(self):
        """Test adding a position to portfolio."""
        service = PortfolioApplicationService(MockUnitOfWorkFactory())

        # Create portfolio
        async with MockUnitOfWork() as uow:
            from app.domain.value_objects.capital import Capital
            from app.domain.value_objects.risk_parameters import RiskParameters

            portfolio = Portfolio(
                portfolio_id="PORT123",
                capital=Capital(amount=Decimal("100000"), currency="USD"),
                risk_parameters=RiskParameters(
                    max_position_size=Decimal("20000"), max_portfolio_exposure=Decimal("80000")
                ),
            )
            await uow.portfolios.add(portfolio)
            uow.commit()

        # Add position
        await service.add_position(
            portfolio_id="PORT123", symbol="AAPL", quantity=Decimal("100"), price=Decimal("150.00")
        )

        # Verify
        async with MockUnitOfWork() as uow:
            portfolio = await uow.portfolios.get("PORT123")
            assert "AAPL" in portfolio.positions

    @pytest.mark.asyncio
    async def test_update_position_prices(self):
        """Test updating position prices."""
        service = PortfolioApplicationService(MockUnitOfWorkFactory())

        # Create portfolio with position
        async with MockUnitOfWork() as uow:
            from app.domain.value_objects.capital import Capital
            from app.domain.value_objects.risk_parameters import RiskParameters

            portfolio = Portfolio(
                portfolio_id="PORT123",
                capital=Capital(amount=Decimal("100000"), currency="USD"),
                risk_parameters=RiskParameters(
                    max_position_size=Decimal("20000"), max_portfolio_exposure=Decimal("80000")
                ),
            )
            position = Portfolio.Position(
                symbol="AAPL",
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                current_price=Decimal("150.00"),
            )
            portfolio.positions["AAPL"] = position
            await uow.portfolios.add(portfolio)
            uow.commit()

        # Update prices
        await service.update_position_prices(
            portfolio_id="PORT123", prices={"AAPL": Decimal("155.00")}
        )

        # Verify
        async with MockUnitOfWork() as uow:
            portfolio = await uow.portfolios.get("PORT123")
            position = portfolio.get_position("AAPL")
            assert position.current_price == Decimal("155.00")


# ============================================================================
# TEST SERVICE ORCHESTRATOR
# ============================================================================


class TestServiceOrchestrator:
    """Tests for ServiceOrchestrator."""

    @pytest.mark.asyncio
    async def test_register_and_get_service(self):
        """Test registering and getting services."""
        orchestrator = ServiceOrchestrator()
        uow_factory = MockUnitOfWorkFactory()

        order_service = OrderApplicationService(uow_factory)
        portfolio_service = PortfolioApplicationService(uow_factory)

        orchestrator.register_service("orders", order_service)
        orchestrator.register_service("portfolios", portfolio_service)

        assert orchestrator._services["orders"] is order_service
        assert orchestrator._services["portfolios"] is portfolio_service

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test executing a workflow."""
        orchestrator = ServiceOrchestrator()
        uow_factory = MockUnitOfWorkFactory()

        # Create portfolio first
        async with MockUnitOfWork() as uow:
            from app.domain.value_objects.capital import Capital
            from app.domain.value_objects.risk_parameters import RiskParameters

            portfolio = Portfolio(
                portfolio_id="PORT123",
                capital=Capital(amount=Decimal("100000"), currency="USD"),
                risk_parameters=RiskParameters(
                    max_position_size=Decimal("20000"), max_portfolio_exposure=Decimal("80000")
                ),
            )
            await uow.portfolios.add(portfolio)
            uow.commit()

        # Register services
        order_service = OrderApplicationService(uow_factory)
        orchestrator.register_service("orders", order_service)

        # Execute workflow
        command = CreateOrderCommand(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            order_type="limit",
            side="buy",
            portfolio_id="PORT123",
        )

        order_id = await orchestrator.execute_workflow(
            "create_and_submit_order", order_command=command
        )

        assert order_id is not None

    @pytest.mark.asyncio
    async def test_execute_unknown_workflow_raises_error(self):
        """Test that unknown workflow raises error."""
        orchestrator = ServiceOrchestrator()

        with pytest.raises(ValueError, match="Unknown workflow"):
            await orchestrator.execute_workflow("unknown_workflow")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
