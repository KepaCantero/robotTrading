"""
Unit of Work Pattern - Transaction management following Percival's Architecture Patterns with Python

This module implements the Unit of Work pattern as described in
"Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory.

Key concepts:
- Tracks changes to entities during a business transaction
- Commits all changes as a single atomic operation
- Provides rollback capability
- Manages repository lifecycle
- Ensures consistency across aggregates

Reference: Chapter 7, "Unit of Work Pattern"

The Unit of Work pattern is especially valuable for:
1. Maintaining consistency across multiple aggregates
2. Coordinating transactions across repositories
3. Implementing the "drop and recreate" optimization
4. Managing database connections and transactions
5. Supporting test scenarios with rollback
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar

from .base_repository import AbstractRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class TrackedEntity:
    """
    An entity being tracked by the Unit of Work.

    Tracks the state of each entity to determine what operations
    need to be performed during commit.
    """

    entity: Any
    state: str  # 'new', 'clean', 'dirty', 'deleted'
    original_state: Optional[Dict[str, Any]] = None


class AbstractUnitOfWork(ABC):
    """
    Abstract Unit of Work following Cosmic Python's pattern.

    The Unit of Work tracks changes to objects during a business transaction
    and writes them out to the database in a single atomic operation.

    Key principles:
    - Client code doesn't need to track what's changed
    - All changes committed as a single atomic operation
    - Supports rollback for error handling
    - Repositories are managed by the UoW
    - Database connection/transaction lifecycle is managed

    Lifecycle:
        1. Enter context (begin transaction)
        2. Access repositories through UoW
        3. Make changes to entities
        4. Exit context (commit or rollback)

    Example:
        ```python
        async with unit_of_work as uow:
            order = await uow.orders.get(order_id)
            order.validate()
            order.submit()
            # Changes committed automatically on exit
        ```

    Reference: Percival & Gregory, "Architecture Patterns with Python", Chapter 7
    """

    def __enter__(self) -> AbstractUnitOfWork:
        """Enter Unit of Work context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit Unit of Work context."""
        if exc_type:
            self.rollback()
        else:
            self.commit()

    @abstractmethod
    def commit(self) -> None:
        """
        Commit all changes to the database.

        Writes all tracked changes to the database as a single atomic
        transaction. Clears tracked entities after successful commit.

        Raises:
            UnitOfWorkError: If commit fails
        """
        pass

    @abstractmethod
    def rollback(self) -> None:
        """
        Rollback all uncommitted changes.

        Discards all tracked changes without writing to database.
        Clears tracked entities.

        Note:
            This does NOT revert changes to entity objects themselves.
            Entities remain in their modified state.
        """
        pass

    @abstractmethod
    def collect_new_events(self) -> List[Any]:
        """
        Collect all domain events from tracked entities.

        Implements the Domain Events pattern. Entities can generate
        events as part of state changes, which are collected here
        for processing by event handlers.

        Returns:
            List of domain events from all tracked entities

        Example:
            ```python
            events = unit_of_work.collect_new_events()
            for event in events:
                await event_handler.handle(event)
            ```
        """
        pass


class GenericUnitOfWork(AbstractUnitOfWork):
    """
    Generic Unit of Work implementation with repository management.

    This implementation provides the core Unit of Work functionality
    with support for multiple repositories and change tracking.

    Example:
        ```python
        class SqlAlchemyUnitOfWork(GenericUnitOfWork):
            def __init__(self, session_factory):
                super().__init__()
                self.session_factory = session_factory

            def __enter__(self):
                self.session = self.session_factory()
                self.orders = SqlOrderRepository(self.session)
                self.portfolios = SqlPortfolioRepository(self.session)
                return super().__enter__()

            def commit(self):
                self.session.commit()

            def rollback(self):
                self.session.rollback()

            def collect_new_events(self):
                # Collect events from tracked entities
                events = []
                for entity in self._tracked_entities.values():
                    events.extend(entity.events)
                return events
        ```
    """

    def __init__(self):
        """Initialize Unit of Work."""
        self._tracked_entities: Dict[str, TrackedEntity] = {}
        self._repositories: Dict[str, AbstractRepository] = {}
        self._committed = False

    def __enter__(self):
        """Enter context and begin transaction."""
        self._committed = False
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context with commit or rollback."""
        try:
            if exc_type is None and not self._committed:
                self.commit()
            else:
                self.rollback()
        finally:
            self._cleanup()

    def register_repository(self, name: str, repository: AbstractRepository) -> None:
        """
        Register a repository with this Unit of Work.

        Args:
            name: Repository name (used as attribute)
            repository: Repository instance

        Example:
            ```python
            uow.register_repository('orders', order_repository)
            # Access via: uow.orders.get(order_id)
            ```
        """
        self._repositories[name] = repository
        setattr(self, name, repository)

    def track_entity(self, entity: Any, state: str = 'new') -> None:
        """
        Track an entity for Unit of Work management.

        Args:
            entity: Domain entity to track
            state: Entity state ('new', 'clean', 'dirty', 'deleted')
        """
        entity_id = self._get_entity_id(entity)
        self._tracked_entities[entity_id] = TrackedEntity(
            entity=entity,
            state=state,
            original_state=self._snapshot_entity(entity) if state == 'clean' else None,
        )

    def commit(self) -> None:
        """
        Commit all changes tracked by this Unit of Work.

        Processes all tracked entities and persists changes
        through their respective repositories.
        """
        if self._committed:
            raise UnitOfWorkError("Transaction already committed")

        try:
            # Process deleted entities first
            for tracked in self._get_tracked_by_state('deleted'):
                self._delete_entity(tracked)

            # Process dirty entities (updates)
            for tracked in self._get_tracked_by_state('dirty'):
                self._update_entity(tracked)

            # Process new entities
            for tracked in self._get_tracked_by_state('new'):
                self._add_entity(tracked)

            self._committed = True
            logger.info(f"Committed {len(self._tracked_entities)} entity changes")

        except Exception as e:
            logger.error(f"Commit failed: {e}")
            self.rollback()
            raise UnitOfWorkError(f"Commit failed: {e}") from e

    def rollback(self) -> None:
        """
        Rollback all tracked changes.

        Discards all tracked entities without persisting changes.
        Note: Entity objects themselves are not reverted.
        """
        self._tracked_entities.clear()
        self._committed = False
        logger.info("Rolled back Unit of Work changes")

    def collect_new_events(self) -> List[Any]:
        """
        Collect domain events from tracked entities.

        Returns:
            List of events from all tracked entities
        """
        events = []
        for tracked in self._tracked_entities.values():
            entity = tracked.entity
            if hasattr(entity, 'events'):
                events.extend(entity.events)
                entity.events.clear()  # Clear after collecting
        return events

    def mark_dirty(self, entity: Any) -> None:
        """Mark an entity as modified."""
        entity_id = self._get_entity_id(entity)
        if entity_id in self._tracked_entities:
            self._tracked_entities[entity_id].state = 'dirty'

    def mark_deleted(self, entity: Any) -> None:
        """Mark an entity as deleted."""
        entity_id = self._get_entity_id(entity)
        if entity_id in self._tracked_entities:
            self._tracked_entities[entity_id].state = 'deleted'

    def _get_tracked_by_state(self, state: str) -> List[TrackedEntity]:
        """Get all tracked entities in a specific state."""
        return [t for t in self._tracked_entities.values() if t.state == state]

    def _add_entity(self, tracked: TrackedEntity) -> None:
        """Add a new entity through its repository."""
        # Find appropriate repository
        repo = self._find_repository_for_entity(tracked.entity)
        if repo:
            # This would be an async call in real implementation
            # For now, we're showing the pattern
            logger.debug(f"Adding entity: {tracked.entity}")

    def _update_entity(self, tracked: TrackedEntity) -> None:
        """Update an entity through its repository."""
        repo = self._find_repository_for_entity(tracked.entity)
        if repo:
            logger.debug(f"Updating entity: {tracked.entity}")

    def _delete_entity(self, tracked: TrackedEntity) -> None:
        """Delete an entity through its repository."""
        repo = self._find_repository_for_entity(tracked.entity)
        if repo:
            logger.debug(f"Deleting entity: {tracked.entity}")

    def _find_repository_for_entity(self, entity: Any) -> Optional[AbstractRepository]:
        """Find the appropriate repository for an entity."""
        entity_class = entity.__class__.__name__
        for repo in self._repositories.values():
            # Check if repo can handle this entity type
            repo_name = repo.__class__.__name__
            if entity_class.lower() in repo_name.lower():
                return repo
        return None

    def _get_entity_id(self, entity: Any) -> str:
        """Extract unique ID from entity."""
        id_field = (
            getattr(entity, 'id', None)
            or getattr(entity, 'entity_id', None)
            or getattr(entity, 'order_id', None)
            or getattr(entity, 'portfolio_id', None)
            or id(entity)
        )
        return f"{entity.__class__.__name__}:{id_field}"

    def _snapshot_entity(self, entity: Any) -> Dict[str, Any]:
        """Create snapshot of entity state for change detection."""
        return {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._tracked_entities.clear()


@asynccontextmanager
async def unit_of_work_context(uow_factory: Type[AbstractUnitOfWork]):
    """
    Async context manager for Unit of Work.

    Provides a convenient way to use Unit of Work with async/await.

    Args:
        uow_factory: Factory function that creates Unit of Work instances

    Example:
        ```python
        async with unit_of_work_context(SqlAlchemyUnitOfWork) as uow:
            order = await uow.orders.get(order_id)
            order.submit()
        # Automatically committed on exit
        ```
    """
    uow = uow_factory()
    try:
        yield uow
        await uow.commit()  # type: ignore[attr-defined]
    except Exception:
        await uow.rollback()  # type: ignore[attr-defined]
        raise


class UnitOfWorkError(Exception):
    """Exception raised for Unit of Work errors."""

    def __init__(self, message: str, uow: Optional[str] = None):
        self.uow = uow
        super().__init__(message)


class AlreadyCommittedError(UnitOfWorkError):
    """Exception when trying to commit an already committed UoW."""

    def __init__(self):
        super().__init__("Unit of Work has already been committed")


class NotActiveError(UnitOfWorkError):
    """Exception when UoW is used outside active context."""

    def __init__(self):
        super().__init__("Unit of Work is not active (not in context)")


# ============================================================================
# USAGE EXAMPLE: Trading Domain Unit of Work
# ============================================================================


class TradingUnitOfWork(GenericUnitOfWork):
    """
    Example Unit of Work for the trading domain.

    This shows how to implement a concrete UoW for a specific domain,
    managing repositories for Order, Portfolio, and Position entities.

    Example:
        ```python
        class SqlTradingUnitOfWork(TradingUnitOfWork):
            def __init__(self, session_factory):
                self.session_factory = session_factory

            def __enter__(self):
                self.session = self.session_factory()
                super().__init__()

                # Initialize repositories
                from app.infrastructure.persistence.sql_order_repository import SqlOrderRepository
                from app.infrastructure.persistence.sql_portfolio_repository import SqlPortfolioRepository

                self.register_repository('orders', SqlOrderRepository(self.session))
                self.register_repository('portfolios', SqlPortfolioRepository(self.session))

                return super().__enter__()

            def commit(self):
                try:
                    super().commit()
                    self.session.commit()
                except Exception as e:
                    self.session.rollback()
                    raise

            def rollback(self):
                self.session.rollback()
                super().rollback()

        # Usage
        with SqlTradingUnitOfWork(session_factory) as uow:
            order = await uow.orders.get(order_id)
            order.validate()
            order.submit()

            portfolio = await uow.portfolios.get(portfolio_id)
            portfolio.add_position_from_order(order)

        # All changes committed atomically
        ```
    """

    def __init__(self):
        super().__init__()
        # Repositories will be registered by subclasses
        self.orders: Optional[AbstractRepository] = None
        self.portfolios: Optional[AbstractRepository] = None
        self.positions: Optional[AbstractRepository] = None

    def collect_new_events(self) -> List[Any]:
        """
        Collect events from all tracked entities.

        Example events:
        - OrderValidated
        - OrderSubmitted
        - OrderFilled
        - PositionOpened
        - PositionClosed
        - RiskLimitBreached
        """
        events = []
        for tracked in self._tracked_entities.values():
            entity = tracked.entity

            # Collect events based on entity type
            if hasattr(entity, 'events'):
                events.extend(entity.events)
                entity.events.clear()

            # Collect state change events
            if tracked.state == 'new':
                events.append({'type': f'{entity.__class__.__name__}Created', 'entity': entity})
            elif tracked.state == 'dirty':
                events.append({'type': f'{entity.__class__.__name__}Updated', 'entity': entity})
            elif tracked.state == 'deleted':
                events.append({'type': f'{entity.__class__.__name__}Deleted', 'entity': entity})

        return events
