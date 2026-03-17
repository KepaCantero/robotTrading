"""
Base Repository Pattern Implementation for Database Access.

This module provides the base repository class with common CRUD operations
and the Protocol for type-safe SQLAlchemy model access.
"""

from __future__ import annotations

import uuid
from typing import Generic, Protocol, TypeVar, runtime_checkable

from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.orm import Session
from structlog import get_logger

from app.shared.exceptions.exceptions import raise_database_error

# pylint: disable=inconsistent-return-statements
# The raise_database_error function always raises an exception, so pylint
# incorrectly reports inconsistent return statements. This is intentional.


@runtime_checkable
class HasIdAndTableName(Protocol):
    """Protocol for SQLAlchemy models with id and __tablename__."""

    id: uuid.UUID
    __tablename__: str


T = TypeVar("T", bound=HasIdAndTableName)
logger = get_logger(__name__)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model_class: type[T], session: Session):
        self.model_class = model_class
        self.session = session

    def create(self, **kwargs) -> T:
        """Create a new record."""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            logger.info(
                "created_record",
                model=self.model_class.__name__,
                id=str(instance.id),
            )
            return instance
        except IntegrityError as e:
            self.session.rollback()
            logger.error(
                "create_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to create {self.model_class.__name__}: {str(e)}",
                "create",
                self.model_class.__tablename__,
            )

    def get_by_id(self, id: uuid.UUID) -> T | None:  # pylint: disable=redefined-builtin
        """Get record by ID."""
        try:
            result = self.session.query(self.model_class).filter(self.model_class.id == id).first()
            logger.debug(
                "queried_by_id",
                model=self.model_class.__name__,
                id=str(id),
                found=result is not None,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_by_id_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to get {self.model_class.__name__} by ID: {str(e)}",
                "get_by_id",
                self.model_class.__tablename__,
            )

    def get_all(self, limit: int | None = None, offset: int | None = None) -> list[T]:
        """Get all records with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            result = query.all()
            logger.debug(
                "queried_all",
                model=self.model_class.__name__,
                count=len(result),
                limit=limit,
                offset=offset,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "get_all_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to get all {self.model_class.__name__}: {str(e)}",
                "get_all",
                self.model_class.__tablename__,
            )

    def update(self, id: uuid.UUID, **kwargs) -> T | None:
        """Update record by ID."""
        try:
            instance = self.get_by_id(id)
            if not instance:
                logger.warning(
                    "update_not_found",
                    model=self.model_class.__name__,
                    id=str(id),
                )
                return None
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
            logger.info(
                "updated_record",
                model=self.model_class.__name__,
                id=str(id),
                fields=list(kwargs.keys()),
            )
            return instance
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "update_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to update {self.model_class.__name__}: {str(e)}",
                "update",
                self.model_class.__tablename__,
            )

    def delete(self, id: uuid.UUID) -> bool:
        """Delete record by ID."""
        try:
            instance = self.get_by_id(id)
            if not instance:
                logger.warning(
                    "delete_not_found",
                    model=self.model_class.__name__,
                    id=str(id),
                )
                return False
            self.session.delete(instance)
            self.session.commit()
            logger.info(
                "deleted_record",
                model=self.model_class.__name__,
                id=str(id),
            )
            return True
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            self.session.rollback()
            logger.error(
                "delete_failed",
                model=self.model_class.__name__,
                id=str(id),
                error=str(e),
            )
            raise_database_error(
                f"Failed to delete {self.model_class.__name__}: {str(e)}",
                "delete",
                self.model_class.__tablename__,
            )

    def count(self) -> int:
        """Count total records."""
        try:
            result = self.session.query(self.model_class).count()
            logger.debug(
                "counted_records",
                model=self.model_class.__name__,
                count=result,
            )
            return result
        except (IntegrityError, DataError, OperationalError, ProgrammingError, DatabaseError) as e:
            logger.error(
                "count_failed",
                model=self.model_class.__name__,
                error=str(e),
            )
            raise_database_error(
                f"Failed to count {self.model_class.__name__}: {str(e)}",
                "count",
                self.model_class.__tablename__,
            )


__all__ = [
    "BaseRepository",
    "HasIdAndTableName",
    "T",
    "logger",
]
