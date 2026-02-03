# Task: Refactor app/api/health.py - Move Database Logic to Service Layer

## Context

This task addresses **ARCH-001 violation** found during GAP audit in `app/api/health.py`.

### Issue Summary
**File:** `app/api/health.py`
**Line:** 87-93
**Violation:** ARCH-001 (Layering violation - API layer should not contain infrastructure logic)

### Current Code (Lines 87-93)
```python
def check_database(self) -> HealthCheckResult:
    """Check database connectivity and integrity."""
    try:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check connection
        cursor.execute("SELECT 1")
        cursor.fetchone()

        # Check table integrity
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        conn.close()
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message=f"Database OK: {len(tables)} tables",
            details={"tables": len(tables)}
        )
    except Exception as e:
        return HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {str(e)}",
            details={"error": str(e)}
        )
```

### Problem
- **API layer contains database access logic** - violates clean architecture
- **Direct SQLite import in API layer** - tight coupling to SQLite
- **Cannot easily switch database implementations** - violates Open/Closed Principle
- **Difficult to test** - requires actual database file
- **Violates BASE_RULES.md ARCH-001:** "Layered architecture - API layer should not contain business logic or data access"
- **Violates BASE_RULES.md ARCH-003:** "Framework dependencies should be isolated"

---

## Task Requirements

### 1. Create Database Health Check Service

Create `app/infrastructure/health/database_health_checker.py`:

```python
"""Database health checker for infrastructure layer."""
from pathlib import Path
from typing import Protocol
import sqlite3
from dataclasses import dataclass

from app.api.health import HealthCheckResult, HealthStatus


class DatabaseHealthCheckerProtocol(Protocol):
    """Protocol for database health checking."""

    def check_health(self) -> HealthCheckResult:
        """Check database connectivity and integrity."""
        ...


@dataclass
class DatabaseHealthConfig:
    """Configuration for database health checker."""
    db_path: Path


class SQLiteDatabaseHealthChecker:
    """SQLite implementation of database health checker."""

    def __init__(self, config: DatabaseHealthConfig) -> None:
        """Initialize with configuration."""
        self.config = config
        self._db_path = config.db_path

    def check_health(self) -> HealthCheckResult:
        """Check database connectivity and integrity."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check connection
                cursor.execute("SELECT 1")
                cursor.fetchone()

                # Check table integrity
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message=f"Database OK: {len(tables)} tables",
                    details={"tables": len(tables), "db_type": "sqlite"}
                )
        except sqlite3.Error as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                details={"error": str(e), "db_type": "sqlite"}
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected error: {str(e)}",
                details={"error": str(e)}
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with context manager support."""
        return sqlite3.connect(str(self._db_path))


# Factory for creating health checkers
class DatabaseHealthCheckerFactory:
    """Factory for creating database health checkers."""

    @staticmethod
    def create_sqlite_checker(db_path: Path) -> SQLiteDatabaseHealthChecker:
        """Create SQLite health checker."""
        config = DatabaseHealthConfig(db_path=db_path)
        return SQLiteDatabaseHealthChecker(config)

    @staticmethod
    def create_from_config(config: dict) -> DatabaseHealthCheckerProtocol:
        """Create health checker from configuration dict."""
        db_type = config.get("db_type", "sqlite")
        db_path = Path(config.get("db_path", "data/trading_metrics.db"))

        if db_type == "sqlite":
            return DatabaseHealthCheckerFactory.create_sqlite_checker(db_path)

        raise ValueError(f"Unsupported database type: {db_type}")
```

### 2. Update app/api/health.py

Refactor to use the new service:

```python
# BEFORE (Lines 87-93)
def check_database(self) -> HealthCheckResult:
    """Check database connectivity and integrity."""
    try:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        # ... database logic ...

# AFTER
from app.infrastructure.health.database_health_checker import (
    DatabaseHealthCheckerFactory,
    DatabaseHealthCheckerProtocol
)

class HealthChecker:
    """Health checker for application components."""

    def __init__(
        self,
        db_health_checker: DatabaseHealthCheckerProtocol | None = None
    ) -> None:
        """Initialize health checker with optional dependencies."""
        self.db_health_checker = db_health_checker

    def check_database(self) -> HealthCheckResult:
        """Check database connectivity and integrity."""
        if self.db_health_checker is None:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Database health checker not configured",
                details={"error": "no_checker"}
            )

        return self.db_health_checker.check_health()
```

### 3. Update FastAPI Dependencies

Create dependency injection setup:

```python
from fastapi import Depends
from app.core.config import get_settings
from app.infrastructure.health.database_health_checker import (
    DatabaseHealthCheckerFactory
)

def get_db_health_checker() -> DatabaseHealthCheckerProtocol:
    """FastAPI dependency for database health checker."""
    settings = get_settings()
    return DatabaseHealthCheckerFactory.create_sqlite_checker(
        db_path=Path(settings.database_path)
    )

def get_health_checker(
    db_checker: DatabaseHealthCheckerProtocol = Depends(get_db_health_checker)
) -> HealthChecker:
    """FastAPI dependency for health checker."""
    return HealthChecker(db_health_checker=db_checker)

# Update endpoint
@router.get("/health", response_model=HealthResponse)
async def health_check(
    checker: HealthChecker = Depends(get_health_checker)
) -> HealthResponse:
    """Health check endpoint."""
    # ... use checker instead of self ...
```

### 4. Acceptance Criteria

- [ ] `app/infrastructure/health/database_health_checker.py` created
- [ ] `app/api/health.py` refactored to use service layer
- [ ] No `sqlite3` import in API layer
- [ ] No database logic in API layer
- [ ] FastAPI dependencies created for DI
- [ ] Syntax check passes: `python -m py_compile app/api/health.py`
- [ ] Syntax check passes: `python -m py_compile app/infrastructure/health/database_health_checker.py`
- [ ] Type check passes: `mypy app/api/health.py`
- [ ] Requirements document updated at `.requirements/app/api/health.py.requirements.md`
- [ ] Health check endpoint still works correctly

### 5. Testing Strategy

Create tests in `tests/infrastructure/health/test_database_health_checker.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from app.infrastructure.health.database_health_checker import (
    SQLiteDatabaseHealthChecker,
    DatabaseHealthCheckerFactory,
    DatabaseHealthConfig
)

def test_sqlite_health_checker_healthy(temp_db_path: Path):
    """Test health checker with healthy database."""
    config = DatabaseHealthConfig(db_path=temp_db_path)
    checker = SQLiteDatabaseHealthChecker(config)

    result = checker.check_health()

    assert result.status.value == "healthy"
    assert "Database OK" in result.message
    assert result.details["tables"] >= 0

def test_sqlite_health_checker_unhealthy():
    """Test health checker with non-existent database."""
    config = DatabaseHealthConfig(db_path=Path("/nonexistent/path.db"))
    checker = SQLiteDatabaseHealthChecker(config)

    result = checker.check_health()

    assert result.status.value == "unhealthy"
    assert "error" in result.details

def test_database_health_checker_factory():
    """Test factory creates correct checker type."""
    checker = DatabaseHealthCheckerFactory.create_sqlite_checker(
        db_path=Path("data/test.db")
    )

    assert isinstance(checker, SQLiteDatabaseHealthChecker)
    assert checker.config.db_path == Path("data/test.db")

def test_factory_from_config():
    """Test factory creates from config dict."""
    config = {
        "db_type": "sqlite",
        "db_path": "data/test.db"
    }
    checker = DatabaseHealthCheckerFactory.create_from_config(config)

    assert isinstance(checker, SQLiteDatabaseHealthChecker)

def test_factory_unsupported_db_type():
    """Test factory raises on unsupported db type."""
    config = {
        "db_type": "postgresql",
        "db_path": "host=localhost"
    }

    with pytest.raises(ValueError, match="Unsupported database type"):
        DatabaseHealthCheckerFactory.create_from_config(config)
```

---

## BASE_RULES Compliance

| Rule ID | Description | Status |
|---------|-------------|--------|
| ARCH-001 | Layered Architecture | ✅ TO FIX |
| ARCH-003 | Framework Dependencies | ✅ TO FIX |
| SOL-002 | Open/Closed Principle | ✅ PASS |
| DEP-001 | Dependency Inversion | ✅ PASS |
| TEST-001 | Testability | ✅ PASS |

---

## Implementation Notes

1. **Directory Structure:** Create `app/infrastructure/health/` if it doesn't exist
2. **Protocol Usage:** Use Protocol for type safety and testability
3. **Factory Pattern:** Factory allows easy extension for other database types (PostgreSQL, MySQL)
4. **Context Manager:** Use context manager for database connections
5. **Configuration:** Support configuration-driven instantiation
6. **Error Handling:** Distinguish between sqlite3.Error and generic Exception

---

## Related Files

- `app/api/health.py` - File to refactor
- `app/infrastructure/health/database_health_checker.py` - New service to create
- `app/core/config.py` - Settings for database path
- `tests/infrastructure/health/test_database_health_checker.py` - New tests
- `.requirements/app/api/health.py.requirements.md` - Requirements to update

---

## Dependencies

- Depends on: None (can be done independently)
- Blocks: None

---

## Future Enhancements

1. **PostgreSQL Support:** Add `PostgreSQLDatabaseHealthChecker` implementation
2. **Connection Pooling:** Add connection pool health checks
3. **Query Performance:** Add query timing thresholds
4. **Migration Status:** Check if migrations are up to date
5. **Backup Status:** Check if recent backups exist

---

**Created:** 2026-02-02
**Priority:** P1 (High)
**Estimated Effort:** 2-3 hours
**Assigned:** @agent-backend-developer
