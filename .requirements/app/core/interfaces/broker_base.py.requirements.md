# broker_base.py

## Purpose
Universal abstract interface for all trading brokers - defines contract that ALL brokers must implement for normalized trading operations.

---

## Type Definitions / Data Classes

### Enums
```python
class BrokerType(str, Enum):
    CRYPTO = "crypto"           # Binance, Coinbase, Kraken
    FOREX = "forex"             # OANDA, FXCM, Forex.com
    STOCKS_US = "stocks_us"     # Alpaca, IBKR US
    STOCKS_EU = "stocks_eu"     # Degiro, Saxo, Trading 212

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACK_RECEIVED = "ack_received"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"
```

### DataClasses
```python
@dataclass
class Balance:
    currency: str                       # REQUIRED - Currency code
    available: Decimal                  # REQUIRED - Available amount
    locked: Decimal                     # REQUIRED - Locked amount
    total: Decimal                      # REQUIRED - Total balance
    # Validation: available + locked == total

@dataclass
class Ticker:
    symbol: str                         # REQUIRED - Symbol
    bid: Decimal                        # REQUIRED - Bid price
    ask: Decimal                        # REQUIRED - Ask price
    last: Decimal                       # REQUIRED - Last price
    timestamp: datetime                 # REQUIRED - Price timestamp
    volume: Optional[Decimal] = None    # OPTIONAL - Volume

@dataclass
class Order:
    order_id: str                       # REQUIRED - Unique ID
    symbol: str                         # REQUIRED - Trading symbol
    side: OrderSide                     # REQUIRED - BUY or SELL
    type: OrderType                     # REQUIRED - Order type
    quantity: Decimal                   # REQUIRED - Order quantity
    price: Optional[Decimal] = None     # OPTIONAL - Limit price
    stop_price: Optional[Decimal] = None # OPTIONAL - Stop price
    status: OrderStatus = PENDING       # REQUIRED - Current status
    filled_quantity: Decimal = 0        # REQUIRED - Filled amount
    avg_fill_price: Optional[Decimal] = None # OPTIONAL - Average fill
    created_at: datetime = None         # REQUIRED - Creation time
    updated_at: datetime = None         # REQUIRED - Update time

@dataclass
class OrderResult:
    order_id: str                       # REQUIRED - Order ID
    status: OrderStatus                 # REQUIRED - Final status
    message: Optional[str] = None       # OPTIONAL - Status message
    execution_price: Optional[Decimal] = None # OPTIONAL - Fill price
    filled_quantity: Decimal = 0        # REQUIRED - Filled quantity
    fees: Decimal = 0                   # REQUIRED - Trading fees
    timestamp: datetime = None          # REQUIRED - Execution time

@dataclass
class Position:
    symbol: str                         # REQUIRED - Position symbol
    quantity: Decimal                   # REQUIRED - Position quantity
    avg_entry_price: Decimal            # REQUIRED - Average entry
    current_price: Decimal              # REQUIRED - Current price
    unrealized_pnl: Decimal             # REQUIRED - Unrealized P&L
    side: OrderSide                     # REQUIRED - Position side
    # Property: market_value = quantity * current_price

@dataclass
class BrokerConfig:
    broker_type: BrokerType             # REQUIRED - Broker type
    api_key: str                        # REQUIRED - API key
    api_secret: Optional[str] = None    # OPTIONAL - API secret
    sandbox: bool = True                # REQUIRED - Start in sandbox
    rate_limit_per_second: int = 10     # REQUIRED - Rate limit
    websocket_enabled: bool = True      # REQUIRED - WebSocket support
    shadow_mode: bool = False           # REQUIRED - Shadow mode
```

### Exceptions
```python
class BrokerError(Exception)           # Base broker error
class RateLimitError(BrokerError)      # Rate limit exceeded
class ConnectionError(BrokerError)     # Connection failed
class OrderRejectedError(BrokerError)  # Order rejected
```

---

## Function Signatures (Abstract Methods)

### Metadata Methods

### `abstract get_broker_type(self) -> BrokerType`
**Pre:** None
**Post:** Returns broker type
**Raises:** No
**Retry:** No
**Side Effects:** None

### `abstract get_broker_name(self) -> str`
**Pre:** None
**Post:** Returns broker name (e.g., 'binance', 'degiro')
**Raises:** No
**Retry:** No
**Side Effects:** None

### Connection Methods

### `abstract async connect(self, config: BrokerConfig) -> bool`
**Pre:** config has valid api_key
**Post:** Connected to broker, session established, rate limit initialized
**Raises:** ConnectionError, BrokerError
**Retry:** Yes (with exponential backoff)
**Side Effects:** Opens REST API session, WebSocket if enabled

**CRITICAL FLOW:**
1. Validate API keys
2. Establish REST API session
3. Establish WebSocket if enabled
4. Initialize Rate Limit Governor

### `abstract async disconnect(self) -> None`
**Pre:** Connected to broker
**Post:** Disconnected, resources cleaned
**Raises:** No
**Retry:** No
**Side Effects:** Closes REST, WebSocket, subscriptions

### `abstract is_connected(self) -> bool`
**Pre:** None
**Post:** Returns connection status
**Raises:** No
**Retry:** No
**Side Effects:** None

### `abstract async ping(self) -> bool`
**Pre:** None
**Post:** Returns True if broker responds
**Raises:** No
**Retry:** Yes
**Side Effects:** Sends ping request

### Account Data Methods

### `abstract async get_normalized_balance(self) -> Dict[str, Balance]`
**Pre:** Connected to broker
**Post:** Returns normalized balances
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** None

**CRITICAL:** Uses Symbol Mapper internally to normalize symbols

### `abstract async get_account_id(self) -> str`
**Pre:** Connected to broker
**Post:** Returns unique account ID
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** None

**CRITICAL:** Required for FIFO and tax calculations

### Market Data Methods

### `abstract async get_live_ticker(self, symbol: str) -> Ticker`
**Pre:** Connected, symbol is normalized
**Post:** Returns current ticker
**Raises:** RateLimitError, ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** Uses WebSocket if available, else REST with rate limit

**CRITICAL:** Use WebSocket data if available, apply Rate Limit Governor for REST

### `abstract async get_historical_ohlcv(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> List[dict]`
**Pre:** Connected, symbol normalized, start < end
**Post:** Returns OHLCV data
**Raises:** RateLimitError, ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** Rate limit applied

### Order Execution Methods (CRITICAL - WAL Integration)

### `abstract async execute_order_with_wal(self, order: Order, dry_run: bool = False) -> OrderResult`
**Pre:** Order validated, WAL initialized
**Post:** Order executed, WAL updated
**Raises:** BrokerError, OrderRejectedError
**Retry:** No (order execution should not be retried automatically)
**Side Effects:** WAL writes, broker API call

**CRITICAL FLOW (MUST follow exactly):**
1. PERSIST to WAL: `await self.wal.write(OrderLog(state="SUBMITTING"))`
2. If shadow_mode=True: `return await self._simulate_execution(order)`
3. Call broker API
4. PERSIST to WAL: `await self.wal.write(OrderLog(state="ACK_RECEIVED"))`
5. Return OrderResult

### `abstract async cancel_order(self, order_id: str) -> bool`
**Pre:** order_id exists, order is open
**Post:** Order cancelled
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** Broker API call

### `abstract async get_order_status(self, order_id: str) -> OrderStatus`
**Pre:** order_id exists
**Post:** Returns current status
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** None

**CRITICAL:** Required for Boot Reconciler

### Position Methods

### `abstract async get_all_open_positions(self) -> List[Position]`
**Pre:** Connected to broker
**Post:** Returns all open positions with normalized symbols
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** None

**CRITICAL:** Required for Boot Reconciler

### `abstract async close_position(self, symbol: str, quantity: Optional[Decimal] = None) -> OrderResult`
**Pre:** symbol normalized, position exists
**Post:** Position closed (fully or partially)
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** Executes order

### Streaming Methods (WebSocket)

### `abstract async start_ticker_stream(self, symbols: List[str], callback) -> None`
**Pre:** Connected, WebSocket enabled
**Post:** Streaming ticker updates via callback
**Raises:** ConnectionError, BrokerError
**Retry:** Yes
**Side Effects:** Opens WebSocket

**CRITICAL:** Use WebSocket, NOT polling REST

### `abstract async stop_ticker_stream(self) -> None`
**Pre:** Stream active
**Post:** Stream stopped, WebSocket closed
**Raises:** No
**Retry:** No
**Side Effects:** Closes WebSocket

### Symbol Mapping Methods (CRITICAL for FIFO)

### `abstract map_internal_to_broker(self, internal_symbol: str) -> str`
**Pre:** internal_symbol is normalized
**Post:** Returns broker ticker format
**Raises:** No
**Retry:** No
**Side Effects:** None

**Examples:**
- Binance: "BTC" → "BTCUSDT"
- OANDA: "BTC" → "BTC_USD"
- IBKR: "BTC" → "IBKR:BTC"

### `abstract map_broker_to_internal(self, broker_symbol: str) -> str`
**Pre:** broker_symbol is valid
**Post:** Returns normalized symbol
**Raises:** No
**Retry:** No
**Side Effects:** None

### Rate Limiting Methods

### `abstract async acquire_rate_limit_token(self) -> None`
**Pre:** Rate limit governor initialized
**Post:** Token acquired (or waited)
**Raises:** No
**Retry:** No (handles internally)
**Side Effects:** Consumes token from bucket

**CRITICAL:** MUST be called before EVERY REST request

### `abstract get_rate_limit_stats(self) -> dict`
**Pre:** Rate limit governor initialized
**Post:** Returns statistics
**Raises:** No
**Retry:** No
**Side Effects:** None

**Returns:**
```python
{
    'tokens_remaining': int,
    'tokens_capacity': int,
    'requests_last_second': int,
    'blocked_requests': int
}
```

### Shadow Mode Methods

### `abstract is_shadow_mode_enabled(self) -> bool`
**Pre:** None
**Post:** Returns shadow mode status
**Raises:** No
**Retry:** No
**Side Effects:** None

### `abstract async _simulate_execution(self, order: Order) -> OrderResult`
**Pre:** Shadow mode enabled
**Post:** Order simulated, WAL updated
**Raises:** No
**Retry:** No
**Side Effects:** WAL writes

**CRITICAL FLOW:**
1. Validate order
2. Write to WAL (SUBMITTING)
3. Simulate ACK_RECEIVED
4. Return OrderResult

---

## Helper Functions

### `validate_order(order: Order) -> Tuple[bool, Optional[str]]`
**Pre:** order has all required fields
**Post:** Returns (is_valid, error_message)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Validations:**
- quantity > 0
- LIMIT orders have price
- STOP orders have stop_price

### `normalize_symbol(symbol: str) -> str`
**Pre:** symbol is broker format
**Post:** Returns normalized symbol
**Raises:** No
**Retry:** No
**Side Effects:** None

**Transformations:**
- Removes suffixes (USDT, USD, _USD, etc.)
- Removes prefixes (IBKR:, etc.)
- Returns uppercase

---

## Acceptance Criteria
- [ ] All brokers implement IBroker interface
- [ ] execute_order_with_wal follows CRITICAL flow exactly
- [ ] Symbol mapping normalizes all symbols
- [ ] Rate limit token acquired before every REST call
- [ ] Shadow mode simulates without broker calls
- [ ] WebSocket used for streaming (not polling)
- [ ] All methods handle BrokerError appropriately
- [ ] get_normalized_balance uses Symbol Mapper

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| WAL Integration | CRITICAL_RULES.md | execute_order_with_wal MUST write to WAL | ✅ OK (in contract) |
| Symbol Normalization | CRITICAL_RULES.md | All symbols normalized internally | ✅ OK (in contract) |
| Rate Limiting | CRITICAL_RULES.md | Token acquired before REST calls | ✅ OK (in contract) |
| Shadow Mode | CRITICAL_RULES.md | Shadow mode never calls broker | ✅ OK (in contract) |
| WebSocket Priority | CRITICAL_RULES.md | Use WebSocket for streaming | ✅ OK (in contract) |
| Type Safety | BASE_RULES.md | All methods typed | ✅ OK |
| Decimal Precision | CRITICAL_RULES.md | Financial calculations use Decimal | ✅ OK |
| Abstract Contract | BASE_RULES.md | All methods abstract | ✅ OK |

---

## Dependencies
- **External:** abc, dataclasses, datetime, decimal, enum, typing
- **Internal:** None (base interface)

---

## Required Tests
- **test_broker_base.py:**
  - Test all abstract method signatures
  - Test Balance validation (available + locked == total)
  - Test Order __post_init__ sets timestamps
  - Test OrderResult __post_init__ sets timestamp
  - Test Position market_value property
  - Test validate_order with valid orders
  - Test validate_order rejects invalid orders
  - Test validate_order rejects LIMIT without price
  - Test validate_order rejects STOP without stop_price
  - Test normalize_symbol removes suffixes
  - Test normalize_symbol removes prefixes
  - Test normalize_symbol returns uppercase
  - Test all enum values

---

## Notes
- CRITICAL: This is the foundation for ALL broker implementations
- EVERY broker (Binance, Degiro, OANDA, etc.) MUST implement this interface
- Symbol mapping is CRITICAL for FIFO and tax calculations
- WAL integration is CRITICAL for crash recovery
- Rate limiting is CRITICAL to avoid being banned
- Shadow mode is CRITICAL for safe testing
