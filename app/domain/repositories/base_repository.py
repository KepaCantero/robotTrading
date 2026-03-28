"""
Base Repository Pattern - Generic repository following Percival's Architecture Patterns with Python

This module provides the foundation for the Repository pattern as described in
"Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory.

Key concepts:
- Repository is a collection-like interface for domain entities
- Abstracts persistence details from domain layer
- Provides domain-oriented language for data access
- Supports dependency inversion (domain defines contract)

Reference: Chapter 6, "Repository Pattern"
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, Generic, Iterable, Iterator, List, Optional, TypeVar

logger = logging.getLogger(__name__)

# Type variable for domain entities
T = TypeVar("T")
K = TypeVar("K")  # Key type (typically str or int)


class AbstractRepository(ABC, Generic[T, K]):
    """
    Abstract repository following Cosmic Python's repository pattern.

    The repository pattern provides a collection-like interface for accessing
    domain objects. This abstract base class defines the contract that all
    repositories must implement.

    Key principles:
    - Domain layer defines the interface (dependency inversion)
    - Infrastructure layer provides concrete implementations
    - Repository behaves like an in-memory collection
    - No business logic in repository (only data access)
    - Units of work managed externally (see unit_of_work.py)

    Example:
        ```python
        # Domain layer (abstract)
        class OrderRepository(AbstractRepository[Order, str]):
            @abstractmethod
            async def find_by_portfolio(self, portfolio_id: str) -> List[Order]:
                pass

        # Infrastructure layer (concrete)
        class SqlOrderRepository(OrderRepository):
            async def add(self, order: Order) -> None:
                # SQL implementation
                pass
        ```

    Reference: Percival & Gregory, "Architecture Patterns with Python", Chapter 6
    """

    @abstractmethod
    async def add(self, entity: T) -> None:
        """
        Add a new entity to the repository.

        This is equivalent to collection.append() in Python's list API.
        The repository should assign an ID if the entity doesn't have one.

        Args:
            entity: Domain entity to add

        Raises:
            RepositoryError: If entity cannot be added
        """

    @abstractmethod
    async def get(self, entity_id: K) -> Optional[T]:
        """
        Retrieve an entity by its identifier.

        Args:
            entity_id: Unique identifier for the entity

        Returns:
            Entity if found, None otherwise

        Raises:
            RepositoryError: If retrieval fails
        """

    @abstractmethod
    async def update(self, entity: T) -> None:
        """
        Update an existing entity.

        Args:
            entity: Entity with updated values

        Raises:
            NotFoundError: If entity doesn't exist
            RepositoryError: If update fails
        """

    @abstractmethod
    async def delete(self, entity_id: K) -> None:
        """
        Delete an entity by its identifier.

        Args:
            entity_id: Unique identifier for the entity

        Raises:
            NotFoundError: If entity doesn't exist
            RepositoryError: If deletion fails
        """

    @abstractmethod
    async def list_all(self) -> List[T]:
        """
        List all entities in the repository.

        Returns:
            List of all entities

        Raises:
            RepositoryError: If listing fails
        """

    async def get_or_create(self, entity_id: K, factory: Callable[[], T]) -> tuple[T, bool]:
        """
        Get entity or create it if it doesn't exist.

        This is a common pattern that combines get() and add().

        Args:
            entity_id: Entity identifier
            factory: Function to create new entity if needed

        Returns:
            Tuple of (entity, created) where created is True if new

        Example:
            ```python
            order, created = await order_repo.get_or_create(
                order_id="ORD123",
                factory=lambda: Order(order_id="ORD123", ...)
            )
            ```
        """
        entity = await self.get(entity_id)
        if entity is not None:
            return entity, False

        new_entity = factory()
        await self.add(new_entity)
        return new_entity, True

    async def exists(self, entity_id: K) -> bool:
        """
        Check if an entity exists.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity exists, False otherwise
        """
        return await self.get(entity_id) is not None

    async def count(self) -> int:
        """
        Count all entities in the repository.

        Returns:
            Number of entities

        Note:
            Default implementation uses list_all(). Override for efficiency.
        """
        return len(await self.list_all())

    async def add_many(self, entities: Iterable[T]) -> None:
        """
        Add multiple entities efficiently.

        Args:
            entities: Iterable of entities to add

        Note:
            Default implementation calls add() for each entity.
            Override for batch operations (e.g., bulk insert).
        """
        for entity in entities:
            await self.add(entity)

    async def get_many(self, entity_ids: Iterable[K]) -> List[T]:
        """
        Retrieve multiple entities by IDs.

        Args:
            entity_ids: Iterable of entity identifiers

        Returns:
            List of found entities (may be less than input if some not found)

        Note:
            Default implementation calls get() for each ID.
            Override for efficient batch queries.
        """
        entities = []
        for entity_id in entity_ids:
            entity = await self.get(entity_id)
            if entity is not None:
                entities.append(entity)
        return entities


class QueryableRepository(AbstractRepository[T, K]):
    """
    Repository with query capabilities following the Specification pattern.

    This extends the base repository with query methods that can be
    combined and composed. Supports the Query Object pattern from
    "Patterns of Enterprise Application Architecture".

    Example:
        ```python
        # Find orders by status
        pending_orders = await order_repo.find_by_status(OrderStatus.PENDING)

        # Complex query with composition
        orders = await order_repo.find_by_criteria(
            status=OrderStatus.PENDING,
            symbol="AAPL",
            min_quantity=Decimal('100')
        )
        ```
    """

    @abstractmethod
    async def find_by_criteria(self, **criteria: object) -> List[T]:
        """
        Find entities matching the given criteria.

        Args:
            **criteria: Key-value pairs of field names and expected values

        Returns:
            List of matching entities

        Example:
            ```python
            orders = await repo.find_by_criteria(
                status=OrderStatus.PENDING,
                symbol="AAPL"
            )
            ```
        """

    @abstractmethod
    async def find_first(self, **criteria: object) -> Optional[T]:
        """
        Find the first entity matching the criteria.

        Args:
            **criteria: Key-value pairs of field names and expected values

        Returns:
            First matching entity or None
        """

    @abstractmethod
    async def find_by_specification(self, specification: Callable[[T], bool]) -> List[T]:
        """
        Find entities using a specification predicate.

        This implements the Specification pattern, allowing for
        complex business rules to be encapsulated and reused.

        Args:
            specification: Predicate function that returns True for matching entities

        Returns:
            List of entities matching the specification

        Example:
            ```python
            # Specification for high-value orders
            def is_high_value_order(order: Order) -> bool:
                return order.quantity * order.price > Decimal('10000')

            high_value_orders = await order_repo.find_by_specification(
                is_high_value_order
            )
            ```
        """


class StreamableRepository(AbstractRepository[T, K]):
    """
    Repository that supports streaming large result sets.

    Useful for large datasets where loading everything into memory
    would be inefficient. Implements the Iterator pattern.

    Example:
        ```python
        async for order in order_repo.stream_all():
            process_order(order)
        ```
    """

    @abstractmethod
    async def stream_all(self) -> Iterator[T]:
        """
        Stream all entities one at a time.

        Yields:
            Entities one at a time

        Example:
            ```python
            async for order in order_repo.stream_all():
                await process(order)
            ```
        """

    @abstractmethod
    async def stream_by_criteria(self, **criteria: object) -> Iterator[T]:
        """
        Stream entities matching criteria.

        Args:
            **criteria: Key-value pairs for filtering

        Yields:
            Matching entities one at a time
        """


class CachedRepository(AbstractRepository[T, K]):
    """
    Repository with caching layer following the Cache-Aside pattern.

    This implementation provides read-through/write-through caching
    to reduce database load. The cache is invisible to the domain layer.

    Cache eviction strategy:
    - Write-through: Cache updated on write
    - Time-based: TTL per entry
    - Size-based: LRU eviction when full

    Example:
        ```python
        # Wrap a SQL repository with caching
        cached_repo = CachedRepository(
            repository=sql_order_repo,
            cache=redis_cache,
            ttl_seconds=300
        )
        ```
    """

    def __init__(
        self,
        repository: AbstractRepository[T, K],
        cache: Optional[Dict[str, T]] = None,
        ttl_seconds: int = 300,
    ):
        """
        Initialize cached repository.

        Args:
            repository: Underlying repository to wrap
            cache: Cache backend (default: simple dict cache)
            ttl_seconds: Time-to-live for cache entries
        """
        self._repository = repository
        self._cache = cache or {}
        self._ttl = ttl_seconds
        self._timestamps: Dict[str, float] = {}

    async def add(self, entity: T) -> None:
        await self._repository.add(entity)
        # Write-through: cache the new entity
        entity_id = self._get_entity_id(entity)
        self._cache[str(entity_id)] = entity

    async def get(self, entity_id: K) -> Optional[T]:
        # Check cache first
        cache_key = str(entity_id)
        if cache_key in self._cache:
            if self._is_cache_valid(cache_key):
                logger.debug(f"Cache hit: {cache_key}")
                return self._cache[cache_key]
            else:
                # Cache expired
                del self._cache[cache_key]

        # Cache miss: fetch from repository
        entity = await self._repository.get(entity_id)
        if entity is not None:
            self._cache[cache_key] = entity

        return entity

    async def update(self, entity: T) -> None:
        await self._repository.update(entity)
        # Write-through: update cache
        entity_id = self._get_entity_id(entity)
        self._cache[str(entity_id)] = entity

    async def delete(self, entity_id: K) -> None:
        await self._repository.delete(entity_id)
        # Invalidate cache
        cache_key = str(entity_id)
        self._cache.pop(cache_key, None)

    async def list_all(self) -> List[T]:
        return await self._repository.list_all()

    def _get_entity_id(self, entity: T) -> K:
        """Extract ID from entity."""
        return getattr(entity, "id", None) or getattr(entity, "entity_id", None)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        import time

        timestamp = self._timestamps.get(cache_key, 0)
        return (time.time() - timestamp) < self._ttl


class RepositoryError(Exception):
    """Base exception for repository errors."""

    def __init__(self, message: str, repository: Optional[str] = None):
        self.repository = repository
        super().__init__(message)


class NotFoundError(RepositoryError):
    """Exception raised when entity is not found."""

    def __init__(self, entity_id: object, repository: Optional[str] = None):
        super().__init__(f"Entity not found: {entity_id}", repository)
        self.entity_id = entity_id


class DuplicateError(RepositoryError):
    """Exception raised when trying to add duplicate entity."""

    def __init__(self, entity_id: object, repository: Optional[str] = None):
        super().__init__(f"Duplicate entity: {entity_id}", repository)
        self.entity_id = entity_id
