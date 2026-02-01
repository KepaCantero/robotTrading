# database.py

## Purpose
Database connection and session management using SQLAlchemy with connection pooling and thread safety.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses SQLAlchemy ORM components.

### Database Configuration
```python
class DatabaseConfig(BaseSettings):
    url: str = Field(default="sqlite:///data/trading.db")
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout: int = Field(default=30, ge=1)
    echo: bool = Field(default=False)
```

---

## Function Signatures (Contracts)

### `init_db(config: DatabaseConfig) -> Engine`
**Pre:** config.url is valid database URL
**Post:** Returns SQLAlchemy engine with connection pool
**Raises:** OperationalError if database connection fails
**Retry:** ✅ Yes (3 attempts with exponential backoff)
**Side Effects:** Creates database engine, may create database file

### `get_session() -> Generator[Session, None, None]`
**Pre:** Database initialized
**Post:** Yields Session for database operations
**Raises:** InvalidRequestError if database not initialized
**Retry:** No
**Side Effects:** Creates session, closes on exit

### `create_tables() -> None`
**Pre:** Database initialized, models imported
**Post:** All tables created in database
**Raises:** OperationalError if table creation fails
**Retry:** ✅ Yes (3 attempts)
**Side Effects:** Writes schema to database

---

## Acceptance Criteria
- [ ] CFG-001: Pydantic Settings for config
- [ ] CFG-002: Environment variables for database URL
- [ ] ASYNC-003: Async context managers for sessions
- [ ] FMT-008: Context managers for resource cleanup
- [ ] Connection pooling configured
- [ ] Thread-safe session management
- [ ] Engine is singleton
- [ ] Sessions properly closed on exit

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES.md | Pydantic Settings | ✅ OK |
| CFG-002 | BASE_RULES.md | Environment variables | ✅ OK |
| ASYNC-003 | BASE_RULES.md | Async context managers | ✅ OK |
| FMT-008 | BASE_RULES.md | Context managers | ✅ OK |
| SEC-003 | BASE_RULES.md | TLS/SSL required | ⚠️ GAP - SQLite used, no TLS |

---

## Dependencies
- **External:** sqlalchemy, pydantic-settings
- **Internal:** None

---

## Required Tests
- **tests/core/test_database.py:**
  - Test init_db() creates engine
  - Test get_session() yields and closes session
  - Test create_tables() creates schema
  - Test connection pooling works
  - Test retry on connection failure
  - Test session cleanup on exception

---

## Notes
Uses SQLite by default. For production, use PostgreSQL with SSL/TLS (SEC-003). Connection pooling reduces overhead.
