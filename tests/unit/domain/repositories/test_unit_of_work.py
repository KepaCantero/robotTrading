"""
Tests for Unit of Work Pattern following Percival's Architecture Patterns with Python.

Tests verify that the Unit of Work pattern correctly implements:
- Transaction boundaries
- Change tracking
- Rollback capability
- Domain event collection
- Repository management
"""

from decimal import Decimal
from typing import List, Optional

import pytest

from app.domain.repositories.base_repository import AbstractRepository
from app.domain.repositories.unit_of_work import (
    AlreadyCommittedError,
    GenericUnitOfWork,
    NotActiveError,
    UnitOfWorkError,
)

# ============================================================================
# TEST ENTITIES
# ============================================================================


class Order:
    """Test order entity."""

    def __init__(self, order_id: str, symbol: str, quantity: Decimal):
        self.order_id = order_id
        self.symbol = symbol
        self.quantity = quantity
        self.status = "pending"
        self.events = []

    def submit(self):
        """Submit order."""
        self.status = "submitted"
        self.events.append({"type": "OrderSubmitted", "order_id": self.order_id})

    def __repr__(self):
        return f"Order({self.order_id}, {self.symbol}, {self.quantity})"


class Portfolio:
    """Test portfolio entity."""

    def __init__(self, portfolio_id: str, capital: Decimal):
        self.portfolio_id = portfolio_id
        self.capital = capital
        self.events = []


# ============================================================================
# IN-MEMORY REPOSITORIES
# ============================================================================


class InMemoryOrderRepository(AbstractRepository[Order, str]):
    """In-memory order repository."""

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


class InMemoryPortfolioRepository(AbstractRepository[Portfolio, str]):
    """In-memory portfolio repository."""

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
# TEST UNIT OF WORK
# ============================================================================


class TestUnitOfWork(GenericUnitOfWork):
    """Test Unit of Work implementation."""

    def __init__(self):
        super().__init__()
        self.committed = False
        self.rolled_back = False

        # Create repositories
        self.orders = InMemoryOrderRepository()
        self.portfolios = InMemoryPortfolioRepository()

        # Register with UoW
        self.register_repository('orders', self.orders)
        self.register_repository('portfolios', self.portfolios)

    def commit(self) -> None:
        """Commit changes."""
        if self._committed:
            raise AlreadyCommittedError()

        super().commit()
        self.committed = True

    def rollback(self) -> None:
        """Rollback changes."""
        super().rollback()
        self.rolled_back = True

    def collect_new_events(self) -> List:
        """Collect events from tracked entities."""
        events = []
        for tracked in self._tracked_entities.values():
            entity = tracked.entity
            if hasattr(entity, 'events'):
                events.extend(entity.events)
                entity.events.clear()
        return events


# ============================================================================
# TESTS
# ============================================================================


class TestGenericUnitOfWork:
    """Tests for GenericUnitOfWork."""

    def test_initialization(self):
        """Test Unit of Work initialization."""
        uow = GenericUnitOfWork()
        assert uow._committed is False
        assert len(uow._tracked_entities) == 0

    def test_register_repository(self):
        """Test repository registration."""
        uow = GenericUnitOfWork()
        repo = InMemoryOrderRepository()

        uow.register_repository('orders', repo)

        assert hasattr(uow, 'orders')
        assert uow.orders is repo

    def test_track_entity(self):
        """Test entity tracking."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))

        uow.track_entity(order, state='new')

        assert len(uow._tracked_entities) == 1
        assert "Order:ORD1" in uow._tracked_entities

    def test_mark_dirty(self):
        """Test marking entity as dirty."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))
        uow.track_entity(order, state='clean')

        uow.mark_dirty(order)

        tracked = uow._tracked_entities.get("Order:ORD1")
        assert tracked is not None
        assert tracked.state == 'dirty'

    def test_mark_deleted(self):
        """Test marking entity as deleted."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))
        uow.track_entity(order, state='clean')

        uow.mark_deleted(order)

        tracked = uow._tracked_entities.get("Order:ORD1")
        assert tracked is not None
        assert tracked.state == 'deleted'

    def test_commit_success(self):
        """Test successful commit."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))
        uow.track_entity(order, state='new')

        uow.commit()

        assert uow.committed is True
        assert uow._committed is True

    def test_commit_already_committed(self):
        """Test that double commit raises error."""
        uow = TestUnitOfWork()
        uow.commit()

        with pytest.raises(AlreadyCommittedError):
            uow.commit()

    def test_rollback(self):
        """Test rollback."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))
        uow.track_entity(order, state='new')

        uow.rollback()

        assert uow.rolled_back is True
        assert len(uow._tracked_entities) == 0

    def test_collect_events(self):
        """Test collecting domain events."""
        uow = TestUnitOfWork()
        order = Order("ORD1", "AAPL", Decimal("100"))
        uow.track_entity(order, state='clean')

        # Generate event
        order.submit()

        events = uow.collect_new_events()

        assert len(events) == 1
        assert events[0]["type"] == "OrderSubmitted"

    def test_context_manager_commit_on_success(self):
        """Test context manager commits on success."""
        uow = TestUnitOfWork()

        with uow:
            order = Order("ORD1", "AAPL", Decimal("100"))
            uow.track_entity(order, state='new')

        assert uow.committed is True
        assert uow.rolled_back is False

    def test_context_manager_rollback_on_error(self):
        """Test context manager rolls back on error."""
        uow = TestUnitOfWork()

        with pytest.raises(ValueError), uow:
            order = Order("ORD1", "AAPL", Decimal("100"))
            uow.track_entity(order, state='new')
            raise ValueError("Test error")

        assert uow.rolled_back is True
        assert uow.committed is False


class TestUnitOfWorkScenarios:
    """Integration tests for Unit of Work scenarios."""

    def test_create_and_submit_order(self):
        """Test complete order lifecycle."""
        uow = TestUnitOfWork()

        with uow:
            # Create order
            order = Order("ORD1", "AAPL", Decimal("100"))
            uow.orders.add(order)
            uow.track_entity(order, state='new')

            # Submit order
            order.submit()
            uow.mark_dirty(order)

        # Verify committed
        assert uow.committed is True

        # Verify persisted
        retrieved = uow.orders.get("ORD1")
        assert retrieved is not None
        assert retrieved.status == "submitted"

    def test_multiple_aggregates(self):
        """Test coordinating multiple aggregates."""
        uow = TestUnitOfWork()

        with uow:
            # Create portfolio
            portfolio = Portfolio("PORT1", Decimal("10000"))
            uow.portfolios.add(portfolio)
            uow.track_entity(portfolio, state='new')

            # Create order
            order = Order("ORD1", "AAPL", Decimal("100"))
            uow.orders.add(order)
            uow.track_entity(order, state='new')

        # Both should be committed
        assert uow.committed is True

        assert uow.portfolios.get("PORT1") is not None
        assert uow.orders.get("ORD1") is not None

    def test_rollback_preserves_other_entities(self):
        """Test rollback with partial failure."""
        uow = TestUnitOfWork()

        # First successful transaction
        with uow:
            order1 = Order("ORD1", "AAPL", Decimal("100"))
            uow.orders.add(order1)
        assert uow.committed is True

        # Second transaction that fails
        uow2 = TestUnitOfWork()
        # Load first order
        order1 = uow2.orders.get("ORD1")
        assert order1 is not None

        try:
            with uow2:
                order2 = Order("ORD2", "MSFT", Decimal("200"))
                uow2.orders.add(order2)
                uow2.track_entity(order2, state='new')
                raise ValueError("Simulated failure")
        except ValueError:
            pass

        # First order should still exist
        assert uow2.orders.get("ORD1") is not None
        # Second order should not exist
        assert uow2.orders.get("ORD2") is None

    def test_collect_events_from_multiple_entities(self):
        """Test collecting events from multiple entities."""
        uow = TestUnitOfWork()

        with uow:
            order = Order("ORD1", "AAPL", Decimal("100"))
            order.submit()
            uow.orders.add(order)
            uow.track_entity(order, state='new')

            portfolio = Portfolio("PORT1", Decimal("10000"))
            uow.portfolios.add(portfolio)
            uow.track_entity(portfolio, state='new')

        events = uow.collect_new_events()

        assert len(events) == 2
        event_types = [e.get("type") for e in events]
        assert "OrderSubmitted" in event_types


class TestUnitOfWorkExceptions:
    """Tests for Unit of Work exceptions."""

    def test_unit_of_work_error(self):
        """Test UnitOfWorkError."""
        error = UnitOfWorkError("Test error", "TestUoW")
        assert str(error) == "Test error"
        assert error.uow == "TestUoW"

    def test_already_committed_error(self):
        """Test AlreadyCommittedError."""
        error = AlreadyCommittedError()
        assert "already been committed" in str(error)

    def test_not_active_error(self):
        """Test NotActiveError."""
        error = NotActiveError()
        assert "not active" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
