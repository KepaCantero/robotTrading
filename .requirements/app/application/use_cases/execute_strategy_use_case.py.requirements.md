# execute_strategy_use_case.py

## Purpose
Orchestrates strategy execution by generating trading signals from market data and converting them to actionable orders with full audit trail.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses multiple external types that must be properly validated.

### External Type: `Quote` (from app.models.market_data)
**Type:** Pydantic BaseModel
**Purpose:** Real-time market data with OHLCV prices and validation

**Key Fields:**
```python
symbol: str                    # REQUIRED - Trading symbol
timestamp: datetime            # REQUIRED - Quote timestamp (UTC)
bid: Decimal                   # REQUIRED - Bid price (> 0)
ask: Decimal                   # REQUIRED - Ask price (> 0)
last: Decimal                  # REQUIRED - Last traded price (> 0)
volume: Decimal                # REQUIRED - Trading volume (>= 0)
spread: Decimal                # OPTIONAL - Bid-ask spread (auto-calculated)
```

**Validation Rules:**
- All price fields must be positive (bid, ask, last > 0)
- Volume must be non-negative
- bid <= ask (spread validation)
- high >= low (OHLC consistency)
- open/close must be between high and low
- Price limit: max $1M per share
- Volume limit: max 10B shares

---

### External Type: `Signal` (from app.models.signal)
**Type:** Pydantic BaseModel
**Purpose:** Trading signal with scoring and metadata

**Key Fields:**
```python
signal_id: str                 # REQUIRED - Unique signal ID (auto-generated)
symbol: str                    # REQUIRED - Trading symbol
signal_type: SignalType        # REQUIRED - BUY/SELL/HOLD enum
strength: SignalStrength       # REQUIRED - WEAK/MODERATE/STRONG/VERY_STRONG
confidence: float              # REQUIRED - 0.0 to 100.0
liquidity_score: float         # REQUIRED - 0.0 to 100.0
priority_score: float          # REQUIRED - 0.0 to 100.0
source: SignalSource           # REQUIRED - Signal source enum
price: Decimal                 # REQUIRED - Signal price (> 0)
volume: Decimal                # REQUIRED - Signal volume (>= 0)
timestamp: datetime            # REQUIRED - Signal timestamp
metadata: Dict[str, Any]       # OPTIONAL - Additional signal data
```

**Validation Rules:**
- All scores (confidence, liquidity, priority) must be 0.0-100.0
- Strong signals (STRONG/VERY_STRONG) require confidence >= 70.0
- Weak signals require confidence <= 80.0
- HOLD signals require moderate confidence (<= 90.0)
- Price must be positive, max $1M
- Volume must be non-negative, max 10B shares
- Timestamp cannot be in the future

**Critical Property:**
```python
@property
def is_actionable(self) -> bool:
    """Confidence > 60.0 is required for signal to generate order"""
    return self.confidence > 60.0
```

---

### External Type: `Order` (from app.domain.entities.order)
**Type:** dataclass
**Purpose:** Trading order with state machine and event tracking

**Key Fields:**
```python
order_id: str                  # REQUIRED - Unique order identifier
symbol: str                    # REQUIRED - Trading symbol
side: OrderSide                # REQUIRED - BUY/SELL enum
order_type: OrderType          # REQUIRED - MARKET/LIMIT/STOP_LOSS/etc.
quantity: Decimal              # REQUIRED - Order quantity (> 0)
price: Optional[Decimal]       # OPTIONAL - Limit price (required for LIMIT orders)
status: OrderStatus            # REQUIRED - Initial status (PENDING)
created_at: datetime           # REQUIRED - Creation timestamp
event_history: List[Dict]      # REQUIRED - Audit trail of all events
```

**State Machine (Tomasini):**
- States: PENDING -> VALIDATED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED
- Alternative paths: CANCEL_PENDING -> CANCELLED, REJECTED, EXPIRED, SUSPENDED
- Terminal states: FILLED, CANCELLED, REJECTED, EXPIRED

**Validation Rules (in __post_init__):**
- order_id cannot be empty
- quantity must be positive
- price (if provided) must be positive
- stop_price (if provided) must be positive

---

### External Type: `BaseStrategy` (from app.strategies.base)
**Type:** Abstract Base Class (ABC)
**Purpose:** Strategy interface with signal generation and parameter management

**Required Methods:**
```python
@abstractmethod
def generate_signals(self, market_data: Quote) -> List[Signal]:
    """Generate trading signals from market data"""

@abstractmethod
def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
    """Validate signal against risk criteria"""

@abstractmethod
def get_required_parameters(self) -> List[str]:
    """Return list of required parameter names"""
```

**Optional Methods:**
```python
def update_parameters(self, params: Dict[str, Any]) -> None:
    """Update strategy parameters dynamically"""

def validate_config(self) -> bool:
    """Validate strategy configuration"""
```

---

## Function Signatures (Contracts)

### `__init__(strategy: Optional[BaseStrategy] = None)`
**Pre:** None (strategy can be None)
**Post:** Instance created with strategy reference or None
**Raises:** None
**Retry:** N/A
**Side Effects:** Stores strategy reference (no external state change)

---

### `execute(market_data: Quote, strategy_type: str, parameters: Optional[Dict[str, Any]] = None) -> List[Order]`
**Pre:**
- market_data is a validated Quote instance
- strategy_type is a non-empty string
- parameters (if provided) is a dict of valid strategy parameters

**Post:**
- Returns list of Order objects (empty if no strategy or signal generation fails)
- All returned orders have PENDING status
- All returned orders have event_history with "generated_from_signal" event
- Strategy parameters applied if provided

**Raises:**
- ValueError: If parameter application fails (invalid parameters)

**Retry:** No
**Side Effects:**
- Calls strategy.generate_signals() (external side effect)
- Calls strategy.update_parameters() if parameters provided
- Logs signal generation and order creation events

---

### `_convert_signals_to_orders(signals: List[Signal], strategy_type: str) -> List[Order]`
**Pre:**
- signals is a list (possibly empty)
- strategy_type is a non-empty string

**Post:**
- Returns list of Order objects (empty if no actionable signals)
- HOLD signals are filtered out (no orders generated)
- Non-actionable signals (confidence <= 60.0) are filtered out
- All returned orders have proper event history

**Raises:** None (errors logged and signal skipped)
**Retry:** No
**Side Effects:** Logs order creation and conversion errors

---

### `_signal_to_order(signal: Signal, strategy_type: str) -> Optional[Order]`
**Pre:**
- signal is a validated Signal instance
- strategy_type is a non-empty string

**Post:**
- Returns Order object or None (for HOLD signals)
- Order has unique ID: "order_{strategy_type}_{symbol}_{timestamp}"
- Order side matches signal type (BUY -> OrderSide.BUY, SELL -> OrderSide.SELL)
- Order is MARKET type
- Order quantity = signal.volume
- Order price = signal.price
- Order status = PENDING
- Order event_history contains "generated_from_signal" with metadata

**Raises:** None
**Retry:** No
**Side Effects:** None (pure conversion function)

---

### `validate_strategy_config(config: Dict) -> bool`
**Pre:**
- config is a dictionary
- Strategy is initialized (not None)

**Post:**
- Returns True if strategy config is valid
- Returns False if strategy is None
- Returns result of strategy.validate_config()

**Raises:** None
**Retry:** No
**Side Effects:** None (pure validation function)

---

## Acceptance Criteria

- [ ] **AC-001: Type hints coverage**
  - All public methods have return type hints
  - All parameters have type hints
  - Check: `mypy --strict app/application/use_cases/execute_strategy_use_case.py`

- [ ] **AC-002: Strategy None handling**
  - When strategy is None, execute() returns empty list
  - Warning logged when strategy is None
  - Test: Create use case without strategy, call execute(), verify empty list returned

- [ ] **AC-003: Parameter validation**
  - Invalid parameters raise ValueError with descriptive message
  - Error logged when parameter application fails
  - Test: Pass invalid parameters, verify ValueError raised and logged

- [ ] **AC-004: Signal generation error handling**
  - When strategy.generate_signals() raises exception, empty list returned
  - Error logged with symbol context
  - Test: Mock strategy to raise exception, verify empty list and error log

- [ ] **AC-005: HOLD signal filtering**
  - HOLD signals do not generate orders
  - Debug log for skipped HOLD signals
  - Test: Create HOLD signal, verify no order generated and debug log present

- [ ] **AC-006: Non-actionable signal filtering**
  - Signals with confidence <= 60.0 are filtered out
  - Debug log with confidence value
  - Test: Create signal with confidence 50.0, verify no order generated

- [ ] **AC-007: Order ID format**
  - Order ID follows pattern: "order_{strategy_type}_{symbol}_{timestamp}"
  - Timestamp format: "%Y%m%d_%H%M%S_%f"
  - Test: Generate order, verify ID format matches pattern

- [ ] **AC-008: Order event history**
  - All orders have "generated_from_signal" event in event_history
  - Event contains: signal_id, signal_type, signal_confidence, signal_source, strategy_type
  - Test: Create order, verify event_history populated correctly

- [ ] **AC-009: Order side mapping**
  - BUY signals create BUY orders
  - SELL signals create SELL orders
  - HOLD signals return None
  - Test: Create BUY/SELL/HOLD signals, verify correct order side or None

- [ ] **AC-010: Order initial state**
  - All orders have status PENDING
  - All orders have order_type MARKET
  - All orders have created_at timestamp
  - Test: Generate order, verify initial state

- [ ] **AC-011: Error isolation in conversion**
  - Single signal conversion failure doesn't stop other signals
  - Error logged for failed conversion
  - Test: Mock one signal to fail, verify other signals still converted

- [ ] **AC-012: Validation delegation**
  - validate_strategy_config() returns False when strategy is None
  - Delegates to strategy.validate_config() when strategy exists
  - Test: Call with None strategy, verify False returned

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - One class, one reason to change | ✅ OK - Class only handles strategy execution and signal-to-order conversion |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depend on abstractions (Protocol/ABC) | ✅ OK - Depends on BaseStrategy ABC |
| CC-006 | BASE_RULES.md | Explicit error handling - Specific exceptions raised/caught | ✅ FIXED - 2026-02-01 - All exception handlers now catch specific exception types |
| LOG-004 | BASE_RULES.md | Error logging - Log exceptions with stack traces | ✅ FIXED - 2026-02-01 - All error logging calls now include exc_info=True |
| LOG-005 | BASE_RULES.md | No sensitive data - Never log passwords/tokens | ✅ OK - No sensitive data in logs |
| TRD-004 | BASE_RULES.md | Audit trail - Log all trade decisions | ✅ OK - All order creations logged with signal metadata |
| ARCH-005 | BASE_RULES.md | Early returns - Use guard clauses to reduce nesting | ✅ OK - Early returns for HOLD and non-actionable signals |
| TYP-001 | BASE_RULES.md | 100% type coverage - All functions have type hints | ✅ FIXED - 2026-02-01 - All methods now have return type hints |
| TYP-002 | BASE_RULES.md | Modern syntax - Use `list[T]`, `dict[K,V]`, `X \| None` | ✅ FIXED - 2026-02-01 - Migrated to modern Python 3.10+ syntax (list[T], T | None) |
| CC-007 | BASE_RULES.md | Small functions - Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - execute() is 27 lines, acceptable for orchestration logic |

---

### Critical Gaps Analysis

#### ✅ GAP-001: Missing Return Type Hints (TYP-001 - P1) - FIXED 2026-02-01
**Issue:** All methods lack return type annotations in the source code
**Impact:** Reduced type safety, harder IDE autocomplete, potential runtime errors
**Fix Applied:** Added `-> list[Order]`, `-> Order | None`, `-> bool`, `-> None` to all method signatures

#### ✅ GAP-002: Old Type Syntax (TYP-002 - P2) - FIXED 2026-02-01
**Issue:** Uses `List[T]` and `Optional[T]` instead of modern Python 3.10+ syntax
**Impact:** Less readable, not using modern Python capabilities
**Fix Applied:** Replaced `List[Order]` with `list[Order]`, `Optional[T]` with `T | None`

#### ✅ GAP-003: Generic Exception Handling (CC-006 - P0) - FIXED 2026-02-01
**Issue:** Lines 57, 65, 116 catch generic `Exception` instead of specific exceptions
**Impact:** May catch unexpected errors, harder to debug
**Fix Applied:**
- Line 57: Changed to `except (TypeError, KeyError, ValueError) as e`
- Line 65: Changed to `except (AttributeError, ValueError, TypeError) as e`
- Line 116: Changed to `except (ValueError, TypeError, AttributeError) as e`

#### ✅ GAP-004: Missing Stack Traces in Error Logs (LOG-004 - P0) - FIXED 2026-02-01
**Issue:** logger.error() calls don't include `exc_info=True` for exception stack traces
**Impact:** Harder to debug issues in production
**Fix Applied:** Added `exc_info=True` parameter to all 3 error logging calls

---

## Dependencies

### External Dependencies
- **logging:** Standard library logging module
- **datetime:** Standard library for timestamps
- **typing:** Type hints (List, Dict, Any, Optional)

### Internal Dependencies
- **app.domain.entities.order:** Order entity and enums (OrderSide, OrderStatus, OrderType)
- **app.models.market_data:** Quote model for market data
- **app.models.signal:** Signal model and enums (Signal, SignalType)
- **app.strategies.base:** BaseStrategy abstract base class

---

## Required Tests

### **test_execute_strategy_use_case.py**

#### Success Paths
- `test_execute_with_valid_strategy_generates_orders`
  - Mock strategy returning BUY/SELL signals
  - Verify orders generated with correct properties
  - Verify event history populated

- `test_execute_with_hold_signals_filters_correctly`
  - Mock strategy returning HOLD signals
  - Verify empty list returned
  - Verify debug log for HOLD filtering

- `test_execute_with_low_confidence_signals_filters_correctly`
  - Mock strategy returning signals with confidence <= 60.0
  - Verify empty list returned
  - Verify debug log with confidence value

- `test_execute_applies_parameters_to_strategy`
  - Pass parameters dict
  - Verify strategy.update_parameters() called
  - Verify parameters logged

- `test_convert_signals_to_orders_with_multiple_signals`
  - Mock list of mixed signals (BUY, SELL, HOLD)
  - Verify only BUY/SELL orders created
  - Verify correct side mapping

- `test_signal_to_order_creates_correct_order_structure`
  - Create BUY signal
  - Verify order_id format, side, type, status
  - Verify event_history contains signal metadata

- `test_validate_strategy_config_with_none_strategy`
  - Create use case without strategy
  - Verify validate_strategy_config() returns False

- `test_validate_strategy_config_delegates_to_strategy`
  - Mock strategy with validate_config() returning True/False
  - Verify delegation result matches

#### Error Paths
- `test_execute_with_invalid_parameters_raises_value_error`
  - Mock strategy.update_parameters() to raise exception
  - Verify ValueError raised with descriptive message
  - Verify error logged

- `test_execute_with_signal_generation_error_returns_empty_list`
  - Mock strategy.generate_signals() to raise exception
  - Verify empty list returned
  - Verify error logged with symbol

- `test_convert_signals_to_orders_isolates_conversion_errors`
  - Mock list where one signal fails conversion
  - Verify other signals still converted
  - Verify error logged for failed signal

- `test_signal_to_order_with_hold_signal_returns_none`
  - Create HOLD signal
  - Verify None returned

- `test_execute_with_none_strategy_returns_empty_list`
  - Create use case without strategy
  - Verify execute() returns empty list
  - Verify warning logged

#### Edge Cases
- `test_execute_with_empty_signal_list`
  - Mock strategy returning empty list
  - Verify empty order list returned

- `test_execute_with_signal_confidence_exactly_60`
  - Create signal with confidence = 60.0 (boundary)
  - Verify signal filtered (not actionable)

- `test_execute_with_signal_confidence_exactly_60_1`
  - Create signal with confidence = 60.1 (boundary)
  - Verify order created (actionable)

- `test_order_id_uniqueness_with_rapid_calls`
  - Generate multiple orders in same microsecond
  - Verify unique order IDs (timestamp with microseconds)

- `test_signal_to_order_preserves_signal_metadata_in_event_history`
  - Create signal with various metadata fields
  - Verify all metadata copied to event history

---

## Notes

**Design Decisions:**
1. **Optional Strategy Pattern:** Strategy can be None, allowing graceful degradation in testing or setup scenarios
2. **Signal Filtering Confidence Threshold:** 60.0 confidence threshold is hardcoded (matches Signal.is_actionable property)
3. **Market Order Default:** All generated orders are MARKET type, not LIMIT or STOP_LOSS
4. **Order ID Format:** Includes strategy_type, symbol, and microsecond timestamp for uniqueness
5. **Error Isolation:** Individual signal conversion failures don't stop batch processing
6. **Event History:** Every order tracks its source signal for full audit trail

**Trading Safety:**
- Orders start in PENDING status (not automatically submitted)
- Full signal metadata stored in order event_history
- Risk validation delegated to strategy (strategy.risk_check())
- No automatic position sizing (uses signal.volume directly)

**Potential Improvements:**
- Add retry logic for transient signal generation failures
- Add circuit breaker if strategy consistently fails
- Add metrics for signal conversion success rate
- Add support for limit orders with price validation
- Add position size validation against portfolio limits
