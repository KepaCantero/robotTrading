"""
Tests for Base Repository Pattern following Percival's Architecture Patterns with Python.

Tests verify that the Repository pattern correctly implements:
- Abstract repository interface
- Generic repository with type hints
- Queryable repository
- Cached repository
- Error handling
"""
import pytest
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.repositories.base_repository import (
    AbstractRepository,
    QueryableRepository,
    CachedRepository,
    RepositoryError,
    NotFoundError,
    DuplicateError,
)


# ============================================================================
# TEST ENTITIES
# ============================================================================

class TestEntity:
    """Simple test entity."""

    def __init__(self, id: str, name: str, value: int):
        self.id = id
        self.name = name
        self.value = value

    def __eq__(self, other):
        return isinstance(other, TestEntity) and self.id == other.id

    def __repr__(self):
        return f"TestEntity(id={self.id}, name={self.name}, value={self.value})"


# ============================================================================
# IN-MEMORY REPOSITORY IMPLEMENTATION
# ============================================================================

class InMemoryRepository(AbstractRepository[TestEntity, str]):
    """In-memory repository for testing."""

    def __init__(self):
        self._items: dict[str, TestEntity] = {}

    async def add(self, entity: TestEntity) -> None:
        if entity.id in self._items:
            raise DuplicateError(entity.id, "InMemoryRepository")
        self._items[entity.id] = entity

    async def get(self, entity_id: str) -> Optional[TestEntity]:
        return self._items.get(entity_id)

    async def update(self, entity: TestEntity) -> None:
        if entity.id not in self._items:
            raise NotFoundError(entity.id, "InMemoryRepository")
        self._items[entity.id] = entity

    async def delete(self, entity_id: str) -> None:
        if entity_id not in self._items:
            raise NotFoundError(entity_id, "InMemoryRepository")
        del self._items[entity_id]

    async def list_all(self) -> list[TestEntity]:
        return list(self._items.values())


class QueryableInMemoryRepository(QueryableRepository[TestEntity, str]):
    """Queryable in-memory repository for testing."""

    def __init__(self):
        self._items: dict[str, TestEntity] = {}

    async def add(self, entity: TestEntity) -> None:
        self._items[entity.id] = entity

    async def get(self, entity_id: str) -> Optional[TestEntity]:
        return self._items.get(entity_id)

    async def update(self, entity: TestEntity) -> None:
        if entity.id in self._items:
            self._items[entity.id] = entity

    async def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)

    async def list_all(self) -> list[TestEntity]:
        return list(self._items.values())

    async def find_by_criteria(self, **criteria) -> list[TestEntity]:
        results = list(self._items.values())
        for key, value in criteria.items():
            results = [e for e in results if getattr(e, key, None) == value]
        return results

    async def find_first(self, **criteria) -> Optional[TestEntity]:
        results = await self.find_by_criteria(**criteria)
        return results[0] if results else None

    async def find_by_specification(self, specification) -> list[TestEntity]:
        return [e for e in self._items.values() if specification(e)]


# ============================================================================
# TESTS
# ============================================================================

class TestAbstractRepository:
    """Tests for AbstractRepository."""

    @pytest.mark.asyncio
    async def test_add_and_get_entity(self):
        """Test adding and retrieving an entity."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)

        await repo.add(entity)
        retrieved = await repo.get("1")

        assert retrieved is not None
        assert retrieved.id == "1"
        assert retrieved.name == "Test"
        assert retrieved.value == 42

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self):
        """Test getting a non-existent entity."""
        repo = InMemoryRepository()
        entity = await repo.get("nonexistent")
        assert entity is None

    @pytest.mark.asyncio
    async def test_update_entity(self):
        """Test updating an entity."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)
        await repo.add(entity)

        # Update
        updated = TestEntity(id="1", name="Updated", value=100)
        await repo.update(updated)

        retrieved = await repo.get("1")
        assert retrieved.name == "Updated"
        assert retrieved.value == 100

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity(self):
        """Test updating a non-existent entity."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)

        with pytest.raises(NotFoundError):
            await repo.update(entity)

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        """Test deleting an entity."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)
        await repo.add(entity)

        await repo.delete("1")

        retrieved = await repo.get("1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entity(self):
        """Test deleting a non-existent entity."""
        repo = InMemoryRepository()

        with pytest.raises(NotFoundError):
            await repo.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_list_all(self):
        """Test listing all entities."""
        repo = InMemoryRepository()
        await repo.add(TestEntity(id="1", name="A", value=1))
        await repo.add(TestEntity(id="2", name="B", value=2))
        await repo.add(TestEntity(id="3", name="C", value=3))

        entities = await repo.list_all()
        assert len(entities) == 3

    @pytest.mark.asyncio
    async def test_add_duplicate_raises_error(self):
        """Test that adding duplicate raises error."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)
        await repo.add(entity)

        with pytest.raises(DuplicateError):
            await repo.add(entity)

    @pytest.mark.asyncio
    async def test_get_or_create_new(self):
        """Test get_or_create when entity doesn't exist."""
        repo = InMemoryRepository()

        entity, created = await repo.get_or_create(
            "1",
            factory=lambda: TestEntity(id="1", name="New", value=100)
        )

        assert created is True
        assert entity.id == "1"

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self):
        """Test get_or_create when entity exists."""
        repo = InMemoryRepository()
        original = TestEntity(id="1", name="Original", value=42)
        await repo.add(original)

        entity, created = await repo.get_or_create(
            "1",
            factory=lambda: TestEntity(id="1", name="New", value=100)
        )

        assert created is False
        assert entity.name == "Original"

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test exists returns True for existing entity."""
        repo = InMemoryRepository()
        entity = TestEntity(id="1", name="Test", value=42)
        await repo.add(entity)

        assert await repo.exists("1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test exists returns False for non-existing entity."""
        repo = InMemoryRepository()
        assert await repo.exists("1") is False

    @pytest.mark.asyncio
    async def test_count(self):
        """Test counting entities."""
        repo = InMemoryRepository()
        assert await repo.count() == 0

        await repo.add(TestEntity(id="1", name="A", value=1))
        await repo.add(TestEntity(id="2", name="B", value=2))
        await repo.add(TestEntity(id="3", name="C", value=3))

        assert await repo.count() == 3

    @pytest.mark.asyncio
    async def test_add_many(self):
        """Test adding multiple entities."""
        repo = InMemoryRepository()
        entities = [
            TestEntity(id="1", name="A", value=1),
            TestEntity(id="2", name="B", value=2),
            TestEntity(id="3", name="C", value=3),
        ]

        await repo.add_many(entities)

        assert await repo.count() == 3

    @pytest.mark.asyncio
    async def test_get_many(self):
        """Test getting multiple entities."""
        repo = InMemoryRepository()
        await repo.add(TestEntity(id="1", name="A", value=1))
        await repo.add(TestEntity(id="2", name="B", value=2))
        await repo.add(TestEntity(id="3", name="C", value=3))

        entities = await repo.get_many(["1", "3", "999"])

        assert len(entities) == 2
        ids = [e.id for e in entities]
        assert "1" in ids
        assert "3" in ids
        assert "999" not in ids


class TestQueryableRepository:
    """Tests for QueryableRepository."""

    @pytest.mark.asyncio
    async def test_find_by_criteria(self):
        """Test finding entities by criteria."""
        repo = QueryableInMemoryRepository()
        await repo.add(TestEntity(id="1", name="Test", value=42))
        await repo.add(TestEntity(id="2", name="Test", value=100))
        await repo.add(TestEntity(id="3", name="Other", value=42))

        # Find by name
        results = await repo.find_by_criteria(name="Test")
        assert len(results) == 2
        assert all(e.name == "Test" for e in results)

        # Find by value
        results = await repo.find_by_criteria(value=42)
        assert len(results) == 2

        # Multiple criteria
        results = await repo.find_by_criteria(name="Test", value=42)
        assert len(results) == 1
        assert results[0].id == "1"

    @pytest.mark.asyncio
    async def test_find_first(self):
        """Test finding first matching entity."""
        repo = QueryableInMemoryRepository()
        await repo.add(TestEntity(id="1", name="Test", value=42))
        await repo.add(TestEntity(id="2", name="Test", value=100))

        result = await repo.find_first(name="Test")
        assert result is not None
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_find_first_not_found(self):
        """Test find_first when no match."""
        repo = QueryableInMemoryRepository()
        result = await repo.find_first(name="Nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_specification(self):
        """Test finding by specification predicate."""
        repo = QueryableInMemoryRepository()
        await repo.add(TestEntity(id="1", name="A", value=10))
        await repo.add(TestEntity(id="2", name="B", value=42))
        await repo.add(TestEntity(id="3", name="C", value=100))

        # Find entities with value > 20
        results = await repo.find_by_specification(lambda e: e.value > 20)
        assert len(results) == 2
        assert all(e.value > 20 for e in results)

        # Complex specification
        def is_even_value_and_name_length_1(e):
            return e.value % 2 == 0 and len(e.name) == 1

        results = await repo.find_by_specification(is_even_value_and_name_length_1)
        assert len(results) == 2


class TestCachedRepository:
    """Tests for CachedRepository."""

    @pytest.mark.asyncio
    async def test_cache_hit_on_get(self):
        """Test that cache is used on subsequent gets."""
        base_repo = InMemoryRepository()
        cached_repo = CachedRepository(base_repo)

        entity = TestEntity(id="1", name="Test", value=42)
        await base_repo.add(entity)

        # First get - cache miss
        result1 = await cached_repo.get("1")
        assert result1 is not None

        # Second get - cache hit
        result2 = await cached_repo.get("1")
        assert result2 is not None

    @pytest.mark.asyncio
    async def test_write_through_on_add(self):
        """Test that add writes through to cache."""
        base_repo = InMemoryRepository()
        cached_repo = CachedRepository(base_repo)

        entity = TestEntity(id="1", name="Test", value=42)
        await cached_repo.add(entity)

        # Should be in cache
        result = await cached_repo.get("1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_delete(self):
        """Test that delete invalidates cache."""
        base_repo = InMemoryRepository()
        cached_repo = CachedRepository(base_repo)

        entity = TestEntity(id="1", name="Test", value=42)
        await cached_repo.add(entity)

        # Verify in cache
        result = await cached_repo.get("1")
        assert result is not None

        # Delete
        await cached_repo.delete("1")

        # Should not be in cache
        result = await cached_repo.get("1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_update_on_entity_update(self):
        """Test that cache updates when entity is updated."""
        base_repo = InMemoryRepository()
        cached_repo = CachedRepository(base_repo)

        original = TestEntity(id="1", name="Original", value=42)
        await cached_repo.add(original)

        # Update
        updated = TestEntity(id="1", name="Updated", value=100)
        await cached_repo.update(updated)

        # Cache should have updated version
        result = await cached_repo.get("1")
        assert result.name == "Updated"
        assert result.value == 100


class TestRepositoryExceptions:
    """Tests for repository exceptions."""

    def test_repository_error(self):
        """Test RepositoryError."""
        error = RepositoryError("Test error", "TestRepo")
        assert str(error) == "Test error"
        assert error.repository == "TestRepo"

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("123", "TestRepo")
        assert "123" in str(error)
        assert error.entity_id == "123"
        assert error.repository == "TestRepo"

    def test_duplicate_error(self):
        """Test DuplicateError."""
        error = DuplicateError("123", "TestRepo")
        assert "123" in str(error)
        assert "Duplicate" in str(error)
        assert error.entity_id == "123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
