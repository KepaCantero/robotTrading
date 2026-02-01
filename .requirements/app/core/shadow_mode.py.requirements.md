# shadow_mode.py

## Purpose
Implements Shadow Mode for safe production testing - intercepts real API calls and simulates execution without actual trades.

---

## Type Definitions / Data Classes

### ShadowModeType Enum
```python
class ShadowModeType(str, Enum):
    DRY_RUN = "dry_run"      # Validate only, don't execute
    SHADOW = "shadow"        # Record to WAL, simulate execution
    PRODUCTION = "production"  # Real execution
```

### ShadowModeConfig DataClass
```python
@dataclass
class ShadowModeConfig:
    enabled: bool = False                              # REQUIRED - Is shadow mode active
    shadow_type: ShadowModeType = ShadowModeType.DRY_RUN  # REQUIRED - Execution type
    fill_simulation_model: str = "realistic"           # REQUIRED - Simulation model
    slippage_bps: int = 5                              # REQUIRED - Default slippage (>= 0)
    fill_delay_ms: int = 100                           # REQUIRED - Fill delay (>= 0)
    partial_fill_probability: float = 0.1              # REQUIRED - Range [0, 1]
    rejection_probability: float = 0.01                # REQUIRED - Range [0, 1]
    enable_comparison: bool = True                     # REQUIRED - Track comparisons
    comparison_window_minutes: int = 60                # REQUIRED - Time window
    max_shadow_orders_per_day: int = 1000              # REQUIRED - Safety limit
    audit_log_path: Optional[str] = None               # OPTIONAL - Audit log file
```

**Validation Rules:**
- slippage_bps >= 0
- fill_delay_ms >= 0
- 0 <= partial_fill_probability <= 1
- 0 <= rejection_probability <= 1

### ShadowExecutionResult DataClass
```python
@dataclass
class ShadowExecutionResult:
    order_id: str                                      # REQUIRED - Original order ID
    shadow_order_id: str                               # REQUIRED - Shadow order ID
    symbol: str                                        # REQUIRED - Trading symbol
    side: str                                          # REQUIRED - BUY or SELL
    quantity: Decimal                                  # REQUIRED - Order quantity
    requested_price: Optional[Decimal]                 # OPTIONAL - Limit price
    simulated_fill_price: Optional[Decimal]            # OPTIONAL - Simulated fill
    simulated_fill_quantity: Decimal                   # REQUIRED - Filled quantity
    status: str                                        # REQUIRED - Execution status
    execution_time_ms: int                             # REQUIRED - Execution time
    slippage_bps: Optional[int] = None                 # OPTIONAL - Applied slippage
    was_rejected: bool = False                         # REQUIRED - Rejection flag
    rejection_reason: Optional[str] = None             # OPTIONAL - Rejection reason
    was_partial_fill: bool = False                     # REQUIRED - Partial fill flag
    wal_recorded: bool = True                          # REQUIRED - WAL write success
    timestamp: datetime                                # REQUIRED - Execution time
    metadata: Dict[str, Any]                           # REQUIRED - Additional data
```

### ShadowRealComparison DataClass
```python
@dataclass
class ShadowRealComparison:
    symbol: str                                        # REQUIRED - Trading symbol
    shadow_order_id: str                               # REQUIRED - Shadow order ID
    real_order_id: Optional[str]                       # OPTIONAL - Real order ID
    shadow_price: Optional[Decimal]                    # OPTIONAL - Shadow fill price
    real_price: Optional[Decimal]                      # OPTIONAL - Real fill price
    shadow_fill_time_ms: int                           # REQUIRED - Shadow fill time
    real_fill_time_ms: Optional[int]                   # OPTIONAL - Real fill time
    price_difference_bps: Optional[int]                # OPTIONAL - Price diff in bps
    timing_difference_ms: Optional[int]                # OPTIONAL - Timing diff in ms
    shadow_status: str                                 # REQUIRED - Shadow status
    real_status: Optional[str]                         # OPTIONAL - Real status
    timestamp: datetime                                # REQUIRED - Comparison time
```

---

## Function Signatures (Contracts)

### `ShadowModeExecutor.__init__(broker_client: Any, wal_manager: OrderStateMachine, sanity_layer: Optional[DataSanityLayer] = None, config: Optional[ShadowModeConfig] = None) -> None`
**Pre:** broker_client implements get_live_ticker, wal_manager initialized
**Post:** Executor initialized with tracking structures
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `async execute_order_shadow(symbol: str, side: str, quantity: Decimal, price: Optional[Decimal] = None, order_type: str = "MARKET", metadata: Optional[Dict[str, Any]] = None) -> ShadowExecutionResult`
**Pre:** Shadow mode enabled, symbol valid, quantity > 0
**Post:** Order written to WAL, simulated fill executed, result tracked
**Raises:** ValueError if validation fails, RuntimeError if disabled
**Retry:** No
**Side Effects:** WAL writes, logging, tracking updates

**CRITICAL FLOW:**
1. Validate order for shadow mode
2. Check daily limits
3. Validate price with Data Sanity Layer
4. Write SUBMITTING to WAL (BEFORE execution)
5. Simulate fill
6. Write ACK_RECEIVED to WAL
7. Write final state to WAL
8. Track result
9. Log with SHADOW prefix
10. Write to audit log if configured

### `async validate_order_for_shadow(symbol: str, side: str, quantity: Decimal, price: Optional[Decimal], order_type: str) -> None`
**Pre:** All parameters provided
**Post:** Validation passes or raises ValueError
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** None

### `async simulate_fill(shadow_order_id: str, symbol: str, side: str, quantity: Decimal, price: Optional[Decimal], order_type: str) -> ShadowExecutionResult`
**Pre:** Order validated, broker available for market data
**Post:** Fill simulated with realistic behavior
**Raises:** ValueError if LIMIT order missing price
**Retry:** No
**Side Effects:** Async delay, random number generation

### `async shadow_to_production_transition(validation_period_minutes: int = 60) -> Dict[str, Any]`
**Pre:** Shadow mode has results to validate
**Post:** Transition report generated with validation results
**Raises:** None (returns report with errors)
**Retry:** No
**Side Effects:** Logging, WAL reads

**CRITICAL VALIDATIONS:**
1. Success rate >= 95%
2. WAL consistency (pending orders <= 10% of recent)
3. No critical errors
4. Shadow vs real price difference <= 50 bps

### `async compare_shadow_vs_real(limit: int = 100) -> List[ShadowRealComparison]`
**Pre:** enable_comparison is True
**Post:** Comparisons generated and tracked
**Raises:** None
**Retry:** No
**Side Effects:** Updates comparisons list

### `async get_shadow_statistics(minutes: int = 60) -> Dict[str, Any]`
**Pre:** None
**Post:** Statistics returned for time window
**Raises:** None
**Retry:** No
**Side Effects:** None

### `detect_shadow_mode_from_env() -> ShadowModeConfig`
**Pre:** Environment variables set (optional)
**Post:** Config created from env vars with defaults
**Raises:** ValueError if SHADOW_MODE_TYPE invalid
**Retry:** No
**Side Effects:** Logging if enabled

---

## Acceptance Criteria
- [ ] Shadow mode intercepts place_order calls
- [ ] All shadow orders written to WAL with SUBMITTING → ACK_RECEIVED → FILLED/REJECTED
- [ ] Daily order limits enforced
- [ ] Price validation via Data Sanity Layer
- [ ] Audit logging with SHADOW prefix
- [ ] Shadow vs real comparison tracking
- [ ] Safe transition validation to production
- [ ] Comprehensive error handling with WAL writes

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Shadow Mode Safety | CRITICAL_RULES.md | Shadow orders NEVER execute on real broker | ✅ OK |
| WAL Integration | CRITICAL_RULES.md | All shadow orders written to WAL | ✅ OK |
| Audit Trail | CRITICAL_RULES.md | SHADOW prefix in all logs | ✅ OK |
| Error Handling | BASE_RULES.md | All async operations catch exceptions | ✅ OK |
| Type Hints | BASE_RULES.md | All functions have type hints | ✅ OK |
| Validation | BASE_RULES.md | Input validation before operations | ✅ OK |
| Daily Limits | CRITICAL_RULES.md | Max orders per day enforced | ✅ OK |
| DataClass Validation | BASE_RULES.md | __post_init__ validates config | ✅ OK |
| Async Safety | CRITICAL_RULES.md | Locking for shared state | ✅ OK |
| Decimal Precision | CRITICAL_RULES.md | Financial calculations use Decimal | ✅ OK |

---

## Dependencies
- **External:** asyncio, logging, uuid, decimal, datetime, dataclasses, enum, random, aiofiles
- **Internal:**
  - app.core.interfaces.broker_base.Order
  - app.sre.data_integrity.sanity_layer.DataSanityLayer, SanityCheckResult
  - app.sre.state_machine.wal_persistence.OrderLog, OrderState, OrderStateMachine

---

## Required Tests
- **test_shadow_mode.py:**
  - Test shadow order execution flow
  - Test WAL state transitions
  - Test daily limit enforcement
  - Test price validation integration
  - Test fill simulation (instant, realistic, slippage)
  - Test partial fills and rejections
  - Test shadow vs real comparison
  - Test transition validation
  - Test statistics calculation
  - Test audit logging
  - Test environment variable detection

---

## Notes
- CRITICAL: This is production safety infrastructure
- Shadow mode is DIFFERENT from paper trading (real API, simulated execution)
- WAL integration enables crash recovery testing
- All shadow operations logged with SHADOW prefix
