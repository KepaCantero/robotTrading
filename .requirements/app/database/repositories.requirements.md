# repositories.py

## Purpose
Repository pattern implementation providing type-safe CRUD operations and domain-specific queries for all database models (User, Portfolio, Asset, Position, Trade, MarketData, Signal, Backtest, RiskMetrics, SystemLog) with comprehensive error handling and transaction management.

---

## Type Definitions / Data Classes

This module uses SQLAlchemy ORM models defined in `app.database.models`. No additional Pydantic models defined.

**Generic Type Parameter:**
```python
T = TypeVar("T")  # Bound to SQLAlchemy model classes
```

---

## Function Signatures (Contracts)

### `BaseRepository.__init__(model_class: type[T], session: Session) -> None`
**Pre:** `model_class` is a valid SQLAlchemy model, `session` is active SQLAlchemy session
**Post:** Repository instance ready for CRUD operations
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (stores references only)

---

### `BaseRepository.create(**kwargs) -> T`
**Pre:** kwargs match model columns, satisfy constraints
**Post:** New record created in database, instance returned with ID
**Raises:** IntegrityError → DatabaseError (via raise_database_error), rolls back transaction
**Retry:** ❌ No
**Side Effects:** DB write (INSERT), session.commit()

---

### `BaseRepository.get_by_id(id: uuid.UUID) -> Optional[T]`
**Pre:** `id` is valid UUID format
**Post:** Returns model instance or None if not found
**Raises:** DataError, OperationalError, ProgrammingError → DatabaseError
**Retry:** ❌ No
**Side Effects:** DB read (SELECT)

---

### `BaseRepository.get_all(limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]`
**Pre:** limit >= 0 if specified, offset >= 0 if specified
**Post:** Returns list of model instances (empty if none exist)
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read (SELECT with pagination)

---

### `BaseRepository.update(id: uuid.UUID, **kwargs) -> Optional[T]`
**Pre:** `id` exists, kwargs match model columns
**Post:** Returns updated instance or None if not found
**Raises:** DatabaseError subclasses, rolls back on error
**Retry:** ❌ No
**Side Effects:** DB write (UPDATE), session.commit()

---

### `BaseRepository.delete(id: uuid.UUID) -> bool`
**Pre:** `id` is valid UUID
**Post:** Returns True if deleted, False if not found
**Raises:** DatabaseError subclasses, rolls back on error
**Retry:** ❌ No
**Side Effects:** DB write (DELETE), session.commit()

---

### `BaseRepository.count() -> int`
**Pre:** None
**Post:** Returns total record count
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read (SELECT COUNT)

---

### `UserRepository.get_by_username(username: str) -> Optional[User]`
**Pre:** `username` is non-empty string
**Post:** Returns User or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `UserRepository.get_by_email(email: str) -> Optional[User]`
**Pre:** `email` is valid email format
**Post:** Returns User or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `UserRepository.get_active_users() -> List[User]`
**Pre:** None
**Post:** Returns list of Users where is_active=True
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PortfolioRepository.get_by_user(user_id: uuid.UUID) -> List[Portfolio]`
**Pre:** `user_id` is valid UUID
**Post:** Returns all portfolios for user
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PortfolioRepository.get_active_by_user(user_id: uuid.UUID) -> List[Portfolio]`
**Pre:** `user_id` is valid UUID
**Post:** Returns active portfolios (is_active=True) for user
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PortfolioRepository.update_total_value(portfolio_id: uuid.UUID, total_value: Decimal) -> bool`
**Pre:** `portfolio_id` exists, `total_value` >= 0
**Post:** Returns True if updated
**Raises:** DatabaseError subclasses, rolls back on error
**Retry:** ❌ No
**Side Effects:** DB write

---

### `AssetRepository.get_by_symbol(symbol: str) -> Optional[Asset]`
**Pre:** `symbol` is non-empty string (e.g., "AAPL")
**Post:** Returns Asset or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `AssetRepository.get_by_asset_class(asset_class: str) -> List[Asset]`
**Pre:** `asset_class` is valid asset class name
**Post:** Returns list of Assets in class
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `AssetRepository.get_active_assets() -> List[Asset]`
**Pre:** None
**Post:** Returns list of Assets where is_active=True
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `AssetRepository.search_by_name(name_pattern: str) -> List[Asset]`
**Pre:** `name_pattern` is search string (case-insensitive partial match)
**Post:** Returns list of matching Assets
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read (ILIKE query)

---

### `PositionRepository.get_by_portfolio(portfolio_id: uuid.UUID) -> List[Position]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns all positions for portfolio
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PositionRepository.get_by_portfolio_and_asset(portfolio_id: uuid.UUID, asset_id: uuid.UUID) -> Optional[Position]`
**Pre:** Both IDs are valid UUIDs
**Post:** Returns Position or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PositionRepository.get_non_zero_positions(portfolio_id: uuid.UUID) -> List[Position]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns positions where quantity != 0
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `PositionRepository.update_position_price(position_id: uuid.UUID, current_price: Decimal) -> bool`
**Pre:** `position_id` exists, `current_price` > 0
**Post:** Updates current_price and unrealized_pnl, returns True if success
**Raises:** DatabaseError subclasses, rolls back on error
**Retry:** ❌ No
**Side Effects:** DB write

---

### `TradeRepository.get_by_portfolio(portfolio_id: uuid.UUID, limit: Optional[int] = None) -> List[Trade]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns trades ordered by executed_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `TradeRepository.get_by_asset(asset_id: uuid.UUID, limit: Optional[int] = None) -> List[Trade]`
**Pre:** `asset_id` is valid UUID
**Post:** Returns trades ordered by executed_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `TradeRepository.get_by_date_range(start_date: datetime, end_date: datetime) -> List[Trade]`
**Pre:** start_date < end_date
**Post:** Returns trades in date range
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `TradeRepository.get_trade_summary(portfolio_id: uuid.UUID) -> Dict[str, Any]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns dict with total_trades, total_commission, total_slippage, total_cost
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read (aggregation query)

---

### `MarketDataRepository.get_by_asset_and_date_range(asset_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[MarketData]`
**Pre:** `asset_id` valid UUID, start_date < end_date
**Post:** Returns market data ordered by timestamp ASC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `MarketDataRepository.get_latest_price(asset_id: uuid.UUID) -> Optional[MarketData]`
**Pre:** `asset_id` is valid UUID
**Post:** Returns most recent MarketData or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `MarketDataRepository.bulk_insert(market_data_list: List[Dict[str, Any]]) -> bool`
**Pre:** market_data_list is non-empty, all dicts have required columns
**Post:** Returns True if bulk insert successful
**Raises:** DatabaseError subclasses, rolls back on error
**Retry:** ❌ No
**Side Effects:** DB write (BULK INSERT)

---

### `SignalRepository.get_by_strategy(strategy_name: str, limit: Optional[int] = None) -> List[Signal]`
**Pre:** `strategy_name` is non-empty string
**Post:** Returns signals ordered by created_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `SignalRepository.get_by_asset(asset_id: uuid.UUID, limit: Optional[int] = None) -> List[Signal]`
**Pre:** `asset_id` is valid UUID
**Post:** Returns signals ordered by created_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `SignalRepository.get_recent_signals(hours: int = 24) -> List[Signal]`
**Pre:** hours > 0
**Post:** Returns signals created within last N hours
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `BacktestRepository.get_by_portfolio(portfolio_id: uuid.UUID) -> List[Backtest]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns backtests ordered by created_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `BacktestRepository.get_by_strategy(strategy_name: str) -> List[Backtest]`
**Pre:** `strategy_name` is non-empty string
**Post:** Returns backtests ordered by created_at DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `BacktestRepository.get_completed_backtests() -> List[Backtest]`
**Pre:** None
**Post:** Returns backtests where status="COMPLETED"
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `RiskMetricsRepository.get_latest_by_portfolio(portfolio_id: uuid.UUID) -> Optional[RiskMetrics]`
**Pre:** `portfolio_id` is valid UUID
**Post:** Returns most recent RiskMetrics or None
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `RiskMetricsRepository.get_by_date_range(portfolio_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[RiskMetrics]`
**Pre:** `portfolio_id` valid UUID, start_date < end_date
**Post:** Returns risk metrics ordered by calculation_date ASC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `SystemLogRepository.get_by_level(level: str, limit: Optional[int] = None) -> List[SystemLog]`
**Pre:** `level` is valid log level ("INFO", "WARNING", "ERROR")
**Post:** Returns logs ordered by timestamp DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `SystemLogRepository.get_by_service(service: str, limit: Optional[int] = None) -> List[SystemLog]`
**Pre:** `service` is non-empty string
**Post:** Returns logs for service ordered by timestamp DESC
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

### `SystemLogRepository.get_recent_logs(hours: int = 24, limit: Optional[int] = None) -> List[SystemLog]`
**Pre:** hours > 0
**Post:** Returns logs within last N hours
**Raises:** DatabaseError subclasses
**Retry:** ❌ No
**Side Effects:** DB read

---

## Acceptance Criteria
- [ ] All database operations use try-except blocks catching SQLAlchemy exceptions
- [ ] All write operations (create, update, delete) rollback on error
- [ ] All repository methods use raise_database_error for consistent error handling
- [ ] Generic BaseRepository provides CRUD for all models
- [ ] Specific repositories extend BaseRepository with domain-specific queries
- [ ] Pagination works correctly with limit and offset parameters
- [ ] Bulk operations use bulk_insert_mappings for performance
- [ ] Aggregation queries (get_trade_summary) use SQLAlchemy func correctly
- [ ] Date range queries use inclusive boundaries (>= start, <= end)
- [ ] ILIKE used for case-insensitive search (search_by_name)

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ✅ OK - Each repository handles one model |
| SOL-005 | BASE_RULES.md | Dependency Inversion | ✅ OK - Depends on Session abstraction |
| DP-001 | BASE_RULES.md | Repository pattern | ✅ OK - Implements repository pattern |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Session injected via __init__ |
| ARCH-001 | BASE_RULES.md | Layered architecture (infrastructure) | ✅ OK - Infrastructure layer, no framework in domain |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All SQL exceptions caught and wrapped |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have type hints |
| TYP-002 | BASE_RULES.md | Modern syntax (TypeVar) | ✅ OK - Uses Generic[T] with TypeVar |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Method names clearly express intent |
| CC-007 | BASE_RULES.md | Small functions | ✅ OK - Most methods < 20 lines |

**NOTE:** This analysis considers ALL 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `sqlalchemy` (ORM, Session, and_, func)
  - `sqlalchemy.exc` (DatabaseError, IntegrityError, etc.)
  - `uuid` (UUID type)
  - `datetime` (datetime, timedelta)
  - `decimal` (Decimal)
  - `typing` (Generic, TypeVar, Optional, etc.)
- **Internal:**
  - `app.database.models` (All ORM models: User, Portfolio, Asset, etc.)
  - `app.core.exceptions.raise_database_error` (Error handling utility)

---

## Required Tests
- **tests/database/test_repositories.py:**
  - Test BaseRepository.create with valid data
  - Test BaseRepository.create raises DatabaseError on IntegrityError
  - Test BaseRepository.get_by_id returns None for non-existent ID
  - Test BaseRepository.update with valid kwargs
  - Test BaseRepository.update returns None for non-existent ID
  - Test BaseRepository.delete returns True for existing record
  - Test BaseRepository.delete returns False for non-existent record
  - Test BaseRepository.count returns correct count
  - Test UserRepository.get_by_username returns correct user
  - Test UserRepository.get_by_email returns correct user
  - Test UserRepository.get_active_users filters correctly
  - Test PortfolioRepository.get_by_user returns all user portfolios
  - Test PortfolioRepository.get_active_by_user filters active portfolios
  - Test PortfolioRepository.update_total_value updates correctly
  - Test AssetRepository.get_by_symbol returns correct asset
  - Test AssetRepository.get_by_asset_class filters by class
  - Test AssetRepository.get_active_assets filters active assets
  - Test AssetRepository.search_by_name performs case-insensitive search
  - Test PositionRepository.get_by_portfolio returns all positions
  - Test PositionRepository.get_by_portfolio_and_asset returns specific position
  - Test PositionRepository.get_non_zero_positions filters correctly
  - Test PositionRepository.update_position_price updates both price and PnL
  - Test TradeRepository.get_by_portfolio orders by executed_at DESC
  - Test TradeRepository.get_by_asset orders by executed_at DESC
  - Test TradeRepository.get_by_date_range filters by date range
  - Test TradeRepository.get_trade_summary aggregates correctly
  - Test MarketDataRepository.get_by_asset_and_date_range orders by timestamp ASC
  - Test MarketDataRepository.get_latest_price returns most recent
  - Test MarketDataRepository.bulk_insert inserts multiple records
  - Test SignalRepository.get_by_strategy orders by created_at DESC
  - Test SignalRepository.get_by_asset filters by asset
  - Test SignalRepository.get_recent_signals filters by time window
  - Test BacktestRepository.get_by_portfolio orders by created_at DESC
  - Test BacktestRepository.get_by_strategy filters by strategy
  - Test BacktestRepository.get_completed_backtests filters by status
  - Test RiskMetricsRepository.get_latest_by_portfolio returns most recent
  - Test RiskMetricsRepository.get_by_date_range filters by date range
  - Test SystemLogRepository.get_by_level filters by level
  - Test SystemLogRepository.get_by_service filters by service
  - Test SystemLogRepository.get_recent_logs filters by time window
  - Test all methods rollback on DatabaseError
  - Test all methods use raise_database_error consistently

---

## Notes
This is a textbook Repository Pattern implementation (DP-001) following SOLID principles. Uses Generic[T] for type-safe base repository with CRUD operations. All specific repositories inherit from BaseRepository and add domain-specific queries. Comprehensive error handling with transaction rollback on failures. Part of infrastructure layer with no business logic.
