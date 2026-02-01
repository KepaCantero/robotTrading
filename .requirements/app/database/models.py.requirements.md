# models.py

## Purpose
SQLAlchemy ORM models for the algoTrading platform database schema, defining all entities for users, portfolios, trades, market data, signals, backtests, risk metrics, and system logging.

---

## Type Definitions / Data Classes

### User Class
```python
class User(Base):
    id: uuid.UUID                    # REQUIRED - Primary key, auto-generated
    username: str                    # REQUIRED, unique, max 50 chars, indexed
    email: str                       # REQUIRED, unique, max 255 chars, indexed
    hashed_password: str             # REQUIRED, max 255 chars - bcrypt hashed
    is_active: bool                  # REQUIRED, default True
    is_superuser: bool               # REQUIRED, default False
    created_at: datetime             # REQUIRED, auto-set on creation
    updated_at: datetime             # REQUIRED, auto-updated on modification
    last_login: datetime | None      # OPTIONAL - Last successful login timestamp
    portfolios: List[Portfolio]      # RELATIONSHIP - cascade delete-orphan
    api_keys: List[APIKey]           # RELATIONSHIP - cascade delete-orphan
```

**Validation Rules:**
- `username` must be unique across all users
- `email` must be unique and valid email format
- `hashed_password` uses bcrypt, never store plaintext
- `id` uses PostgreSQL UUID type with uuid4 default
- Indexes on `email`, `username`, `created_at` for query performance

### APIKey Class
```python
class APIKey(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    user_id: uuid.UUID               # REQUIRED, FK → users.id
    name: str                        # REQUIRED, max 100 chars - descriptive name
    key_hash: str                    # REQUIRED, unique, max 255 chars - SHA-256 hash
    permissions: dict                # REQUIRED, JSON - e.g., {"read": True, "trade": False}
    is_active: bool                  # REQUIRED, default True
    expires_at: datetime | None      # OPTIONAL - API key expiration
    last_used: datetime | None       # OPTIONAL - Last usage timestamp
    created_at: datetime             # REQUIRED, auto-set on creation
    user: User                       # RELATIONSHIP - back_populates
```

**Validation Rules:**
- `key_hash` must be unique (prevent hash collisions)
- `permissions` is JSON dict with capability flags
- Check expiration on every API key validation
- Indexes on `key_hash`, `user_id`, `expires_at`

### Portfolio Class
```python
class Portfolio(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    user_id: uuid.UUID               # REQUIRED, FK → users.id
    name: str                        # REQUIRED, max 100 chars
    description: str | None          # OPTIONAL, Text - portfolio description
    initial_cash: Decimal            # REQUIRED, Numeric(15,2) - starting capital
    current_cash: Decimal            # REQUIRED, Numeric(15,2) - available cash
    total_value: Decimal             # REQUIRED, Numeric(15,2) - total portfolio value
    is_active: bool                  # REQUIRED, default True
    created_at: datetime             # REQUIRED, auto-set
    updated_at: datetime             # REQUIRED, auto-updated
    positions: List[Position]        # RELATIONSHIP - cascade delete-orphan
    trades: List[Trade]              # RELATIONSHIP - cascade delete-orphan
    backtests: List[Backtest]        # RELATIONSHIP - cascade delete-orphan
    user: User                       # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Unique constraint on (`user_id`, `name`) - one portfolio name per user
- All monetary fields use `Numeric(15,2)` for precision
- `total_value = current_cash + sum(positions.value)`
- Indexes on `user_id`, `name`, `created_at`

### Asset Class
```python
class Asset(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    symbol: str                      # REQUIRED, unique, max 20 chars - ticker symbol
    name: str                        # REQUIRED, max 200 chars - full asset name
    asset_class: str                 # REQUIRED, max 50 chars - stock/etf/crypto/etc
    exchange: str | None             # OPTIONAL, max 50 chars - exchange name
    currency: str                    # REQUIRED, max 3 chars - ISO 4217 currency code
    is_active: bool                  # REQUIRED, default True
    created_at: datetime             # REQUIRED, auto-set
    updated_at: datetime             # REQUIRED, auto-updated
    positions: List[Position]        # RELATIONSHIP - back_populates
    trades: List[Trade]              # RELATIONSHIP - back_populates
    market_data: List[MarketData]    # RELATIONSHIP - back_populates
```

**Validation Rules:**
- `symbol` must be unique (e.g., "AAPL", "BTC-USD")
- `currency` defaults to "USD"
- `asset_class` enum: stock, etf, crypto, forex, commodity, bond
- Indexes on `symbol`, `asset_class`, `exchange`, `currency`

### Position Class
```python
class Position(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    portfolio_id: uuid.UUID          # REQUIRED, FK → portfolios.id
    asset_id: uuid.UUID              # REQUIRED, FK → assets.id
    quantity: Decimal                # REQUIRED, Numeric(15,8) - position size
    average_price: Decimal           # REQUIRED, Numeric(15,4) - avg entry price
    current_price: Decimal | None    # OPTIONAL, Numeric(15,4) - market price
    unrealized_pnl: Decimal | None   # OPTIONAL, Numeric(15,2) - unrealized P&L
    realized_pnl: Decimal            # REQUIRED, Numeric(15,2), default 0
    created_at: datetime             # REQUIRED, auto-set
    updated_at: datetime             # REQUIRED, auto-updated
    portfolio: Portfolio             # RELATIONSHIP - back_populates
    asset: Asset                     # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Unique constraint on (`portfolio_id`, `asset_id`) - one position per asset
- Check constraint: `quantity != 0` - positions closed when quantity hits zero
- `quantity` can be positive (long) or negative (short)
- `unrealized_pnl = (current_price - average_price) * quantity`
- Indexes on `portfolio_id`, `asset_id`, `updated_at`

### Trade Class
```python
class Trade(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    portfolio_id: uuid.UUID          # REQUIRED, FK → portfolios.id
    asset_id: uuid.UUID              # REQUIRED, FK → assets.id
    order_id: str | None             # OPTIONAL, max 100 chars - external order ID
    side: str                        # REQUIRED, max 4 chars - BUY or SELL
    quantity: Decimal                # REQUIRED, Numeric(15,8) - trade quantity
    price: Decimal                   # REQUIRED, Numeric(15,4) - execution price
    commission: Decimal              # REQUIRED, Numeric(15,4), default 0
    slippage: Decimal                # REQUIRED, Numeric(15,4), default 0
    total_cost: Decimal              # REQUIRED, Numeric(15,2) - total transaction cost
    status: str                      # REQUIRED, max 20 chars, default FILLED
    executed_at: datetime            # REQUIRED, execution timestamp
    created_at: datetime             # REQUIRED, record creation timestamp
    portfolio: Portfolio             # RELATIONSHIP - back_populates
    asset: Asset                     # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Check constraint: `side IN ('BUY', 'SELL')`
- Check constraint: `quantity > 0`
- Check constraint: `price > 0`
- `total_cost = (price * quantity) + commission`
- `status` enum: PENDING, FILLED, CANCELLED
- Indexes on `portfolio_id`, `asset_id`, `order_id`, `executed_at`, `side`

### MarketData Class
```python
class MarketData(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    asset_id: uuid.UUID              # REQUIRED, FK → assets.id
    timestamp: datetime              # REQUIRED, indexed - data timestamp
    open_price: Decimal              # REQUIRED, Numeric(15,4) - OHLC open
    high_price: Decimal              # REQUIRED, Numeric(15,4) - OHLC high
    low_price: Decimal               # REQUIRED, Numeric(15,4) - OHLC low
    close_price: Decimal             # REQUIRED, Numeric(15,4) - OHLC close
    volume: Decimal                  # REQUIRED, Numeric(20,0) - trading volume
    adjusted_close: Decimal | None   # OPTIONAL, Numeric(15,4) - split/dividend adjusted
    created_at: datetime             # REQUIRED, record creation timestamp
    asset: Asset                     # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Unique constraint on (`asset_id`, `timestamp`) - one data point per asset per timestamp
- Check constraints: all prices > 0, volume >= 0
- Check constraint: `high_price >= low_price`
- Check constraint: `low_price <= close_price <= high_price`
- Indexes on `asset_id`, `timestamp`, composite (`asset_id`, `timestamp`)

### Signal Class
```python
class Signal(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    asset_id: uuid.UUID              # REQUIRED, FK → assets.id
    strategy_name: str               # REQUIRED, max 100 chars - strategy identifier
    signal_type: str                 # REQUIRED, max 10 chars - BUY/SELL/HOLD
    strength: str                    # REQUIRED, max 20 chars - WEAK/MODERATE/STRONG
    confidence: Decimal              # REQUIRED, Numeric(5,2) - 0.00 to 100.00
    price: Decimal                   # REQUIRED, Numeric(15,4) - signal price
    volume: Decimal | None           # OPTIONAL, Numeric(15,8) - signal volume
    meta_data: dict                  # REQUIRED, JSON - strategy-specific data
    created_at: datetime             # REQUIRED, signal generation timestamp
    asset: Asset                     # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Check constraint: `signal_type IN ('BUY', 'SELL', 'HOLD')`
- Check constraint: `strength IN ('WEAK', 'MODERATE', 'STRONG')`
- Check constraint: `confidence >= 0 AND confidence <= 100`
- Check constraint: `price > 0`
- Indexes on `asset_id`, `strategy_name`, `signal_type`, `created_at`

### Backtest Class
```python
class Backtest(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    portfolio_id: uuid.UUID          # REQUIRED, FK → portfolios.id
    strategy_name: str               # REQUIRED, max 100 chars
    start_date: datetime             # REQUIRED, backtest start date
    end_date: datetime               # REQUIRED, backtest end date
    initial_capital: Decimal         # REQUIRED, Numeric(15,2)
    final_capital: Decimal           # REQUIRED, Numeric(15,2)
    total_return: Decimal            # REQUIRED, Numeric(8,4) - percentage
    sharpe_ratio: Decimal | None     # OPTIONAL, Numeric(8,4)
    max_drawdown: Decimal | None     # OPTIONAL, Numeric(8,4)
    win_rate: Decimal | None         # OPTIONAL, Numeric(5,2) - percentage
    total_trades: int                # REQUIRED, default 0
    parameters: dict                 # REQUIRED, JSON - strategy parameters
    results: dict                    # REQUIRED, JSON - detailed metrics
    status: str                      # REQUIRED, default COMPLETED
    created_at: datetime             # REQUIRED, backtest creation timestamp
    completed_at: datetime | None    # OPTIONAL, backtest completion timestamp
    portfolio: Portfolio             # RELATIONSHIP - back_populates
```

**Validation Rules:**
- Check constraint: `status IN ('RUNNING', 'COMPLETED', 'FAILED')`
- Check constraint: `start_date < end_date`
- Check constraint: `initial_capital > 0`
- Indexes on `portfolio_id`, `strategy_name`, `start_date`, `end_date`, `status`

### RiskMetrics Class
```python
class RiskMetrics(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    portfolio_id: uuid.UUID          # REQUIRED, FK → portfolios.id
    calculation_date: datetime       # REQUIRED, indexed - calculation timestamp
    var_95: Decimal | None           # OPTIONAL, Numeric(15,2) - Value at Risk 95%
    var_99: Decimal | None           # OPTIONAL, Numeric(15,2) - Value at Risk 99%
    expected_shortfall: Decimal | None # OPTIONAL, Numeric(15,2) - Conditional VaR
    volatility: Decimal | None       # OPTIONAL, Numeric(8,4) - annualized volatility
    beta: Decimal | None             # OPTIONAL, Numeric(8,4) - portfolio beta
    correlation_matrix: dict | None  # OPTIONAL, JSON - asset correlations
    created_at: datetime             # REQUIRED, record creation timestamp
    portfolio: Portfolio             # RELATIONSHIP
```

**Validation Rules:**
- Composite index on (`portfolio_id`, `calculation_date`)
- Indexes on `portfolio_id`, `calculation_date`

### SystemLog Class
```python
class SystemLog(Base):
    id: uuid.UUID                    # REQUIRED - Primary key
    level: str                       # REQUIRED, max 20 chars, indexed - log level
    service: str                     # REQUIRED, max 50 chars, indexed - service name
    message: str                     # REQUIRED, Text - log message
    meta_data: dict | None           # OPTIONAL, JSON - additional context
    timestamp: datetime              # REQUIRED, indexed - log timestamp
    created_at: datetime             # REQUIRED, record creation timestamp
```

**Validation Rules:**
- Check constraint: `level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')`
- Composite index on (`level`, `service`)
- Indexes on `level`, `service`, `timestamp`

### PositionState Class
```python
class PositionState(Base):
    id: int                          # REQUIRED - Primary key, auto-increment
    monitor_id: str                  # REQUIRED, max 255 chars, indexed - monitor identifier
    positions_json: str              # REQUIRED, Text - JSON serialized positions
    last_sync: datetime              # REQUIRED, indexed - last sync timestamp
    is_active: bool                  # REQUIRED, default True
    version: int                     # REQUIRED, default 1 - conflict resolution
    created_at: datetime             # REQUIRED, auto-set
    updated_at: datetime             # REQUIRED, auto-updated
```

**Validation Rules:**
- `positions_json` must be valid JSON (validate on deserialization)
- `version` increments on each update for optimistic locking
- Indexes on `monitor_id`, `last_sync`, `is_active`
- Critical for position recovery after system restart

---

## Function Signatures (Contracts)

### `__repr__() -> str` (PositionState only)
**Pre:** Object is initialized
**Post:** Returns string representation with monitor_id and version
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All models have proper foreign key constraints with correct `ondelete` behavior
- [ ] All Decimal fields use appropriate precision for financial calculations (no floating point)
- [ ] All UUID fields use `UUID(as_uuid=True)` for proper PostgreSQL UUID type
- [ ] All datetime fields have `server_default=sa.text("CURRENT_TIMESTAMP")` in migrations
- [ ] All check constraints are properly defined and enforced at database level
- [ ] All indexes are created for query performance on foreign keys and frequently queried fields
- [ ] All relationships have proper `back_populates` for bidirectional navigation
- [ ] Cascade delete-orphan is used for child entities that should not exist without parent
- [ ] Unique constraints are properly defined for business rules (username, email, etc.)
- [ ] No mutable defaults (use `default=dict` not `default={}`)
- [ ] PositionState model is properly used for position monitoring persistence
- [ ] All financial fields use Numeric type with appropriate precision (no Float)

---

## Critical Rules (MUST NOT BREAK)

**Universal rules:** See `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-003 | BASE_RULES.md | Domain has no framework dependencies | ✅ FIXED - 2026-02-01 - Documented: Infrastructure layer uses SQLAlchemy appropriately |
| FMT-007 | BASE_RULES.md | No mutable defaults | ⚠️ CHECK - Verify `default=dict` not `default={}` used |
| SEC-010 | BASE_RULES.md | Encryption at rest for sensitive data | ⚠️ CHECK - APIKey.key_hash must be hashed, never plaintext |
| TRD-004 | BASE_RULES.md | Audit trail for trading operations | ✅ OK - Trade model logs all executions |
| TRD-006 | BASE_RULES.md | Transaction costs in models | ✅ OK - Trade has commission, slippage, total_cost |
| ARCH-001 | BASE_RULES.md | Layered architecture - models in infrastructure | ✅ OK - In app.database (infrastructure layer) |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All fields use Mapped[type] syntax |
| FMT-008 | BASE_RULES.md | Context managers for resources | ⚠️ N/A - Models are declarative, no resources to manage |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ⚠️ CHECK - Ensure never log hashed_password or key_hash |
| RSK-001 | BASE_RULES.md | VaR calculation support | ✅ OK - RiskMetrics model has var_95, var_99 |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ N/A - Declarative models, no error handling needed |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each model has single responsibility |

**Additional Database-Specific Rules:**

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| DB-001 | Precision for money | Always use Numeric, never Float for financial data | **P0** |
| DB-002 | Foreign key indexing | All FK columns must have indexes | P1 |
| DB-003 | Cascade behavior | Define appropriate ON DELETE behavior | **P0** |
| DB-004 | Check constraints | Business rules enforced at DB level | **P0** |
| DB-005 | Unique constraints | Prevent duplicate data at DB level | **P0** |
| DB-006 | Index naming | Use consistent naming: idx_tablename_columns | P2 |
| DB-007 | Constraint naming | Use consistent naming: ck_tablename_rule | P2 |
| DB-008 | UUID primary keys | Use UUID for all public-facing entities | P1 |
| DB-009 | Soft deletes | Use is_active flag instead of DELETE | P1 |
| DB-010 | Audit timestamps | All tables have created_at, updated_at | P1 |

---

## Dependencies
- **External:**
  - `sqlalchemy` - ORM framework
  - `sqlalchemy.dialects.postgresql` - PostgreSQL-specific types (UUID, JSONB)
  - `uuid` - UUID generation
  - `decimal` - Decimal type for precision
  - `datetime` - Datetime handling
  - `typing` - Type hints (List, Optional)

- **Internal:**
  - `app.database.Base` - Base declarative class for all models

---

## Required Tests
- **tests/database/models/test_user.py:**
  - User creation with valid data
  - Unique constraint violation on username/email
  - Cascade delete of portfolios and api_keys on user deletion
  - Default values for is_active, is_superuser, timestamps

- **tests/database/models/test_portfolio.py:**
  - Portfolio creation and cash tracking
  - Unique constraint on (user_id, name)
  - Position and trade cascade deletion
  - Total value calculation accuracy

- **tests/database/models/test_position.py:**
  - Position creation and updates
  - Unique constraint on (portfolio_id, asset_id)
  - Check constraint: quantity != 0
  - Realized/unrealized P&L calculations

- **tests/database/models/test_trade.py:**
  - Trade creation with execution data
  - Check constraints: side, quantity > 0, price > 0
  - Total cost calculation: (price * quantity) + commission
  - Status transitions: PENDING → FILLED/CANCELLED

- **tests/database/models/test_market_data.py:**
  - Market data insertion and retrieval
  - Unique constraint on (asset_id, timestamp)
  - Check constraints: prices > 0, high >= low
  - Composite index query performance

- **tests/database/models/test_backtest.py:**
  - Backtest creation with results
  - Check constraint: start_date < end_date
  - Sharpe ratio, max drawdown calculations
  - Status transitions: RUNNING → COMPLETED/FAILED

- **tests/database/models/test_position_state.py:**
  - Position state serialization/deserialization
  - Version increment on update
  - State recovery after restart
  - Concurrent update handling (optimistic locking)

---

## Notes
- PositionState model is critical for position monitoring recovery - enables system restart without losing track of active positions
- All financial fields use Decimal with explicit precision to avoid floating-point rounding errors
- PostgreSQL UUID type is used instead of VARCHAR for better performance and automatic index generation
- JSON fields are used for flexible metadata (permissions, meta_data) but should be validated at application level
