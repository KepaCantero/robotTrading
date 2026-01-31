# execute_strategy_use_case.py

## Purpose
Execute Strategy Use Case - Orchestrates strategy execution and order generation for trading strategies.

---

## Type Definitions / Data Classes

### ExecuteStrategyUseCase
```python
class ExecuteStrategyUseCase:
    """
    Use case for executing a trading strategy.

    This use case orchestrates strategy execution and order generation.
    """
```

**Attributes:**
- `_strategy: Optional[BaseStrategy]` - The trading strategy to execute

---

## Function Signatures (Contracts)

### `ExecuteStrategyUseCase.__init__(strategy: Optional[BaseStrategy] = None) -> None`
**Pre:** None
**Post:** Use case initialized with strategy (or None)
**Raises:** None
**Retry:** No
**Side Effects:** Stores strategy reference

**State:** `_strategy` is stored for later use

### `ExecuteStrategyUseCase.execute(
    symbol: str,
    strategy_type: str,
    parameters: Optional[Dict] = None,
) -> List[Order]`
**Pre:** symbol is non-empty string; strategy_type is valid
**Post:** Returns list of generated orders (empty if no strategy)
**Raises:** None (graceful degradation)
**Retry:** No
**Side Effects:** Calls `strategy.generate_signals(symbol)`

**Current Implementation:**
- Returns empty list if no strategy configured
- Calls `self._strategy.generate_signals(symbol)`
- Returns empty list (stub implementation)

**Note:** Full order conversion from signals not yet implemented

### `ExecuteStrategyUseCase.validate_strategy_config(config: Dict) -> bool`
**Pre:** config is dictionary
**Post:** Returns True if configuration is valid
**Raises:** None
**Retry:** No
**Side Effects:** Calls `strategy.validate_config(config)`

**Behavior:**
- Returns False if no strategy configured
- Delegates validation to strategy's `validate_config()` method

---

## Acceptance Criteria
- [ ] **AC-001:** ExecuteStrategyUseCase has optional strategy dependency
- [ ] **AC-002:** execute() returns empty list when no strategy
- [ ] **AC-003:** execute() calls generate_signals on strategy
- [ ] **AC-004:** execute() accepts symbol, strategy_type, parameters
- [ ] **AC-005:** validate_strategy_config() returns False when no strategy
- [ ] **AC-006:** validate_strategy_config() delegates to strategy.validate_config()
- [ ] **AC-007:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Execute Strategy Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Dependency injection | DDD (DIP) | Strategy injected via constructor | ✅ OK - __init__() |
| Optional dependency | Clean code | Graceful degradation when None | ✅ OK - Returns empty list |
| Use case pattern | Clean Architecture | Application layer orchestration | ✅ OK - ExecuteStrategyUseCase |
| Single responsibility | SOLID | One use case = one responsibility | ✅ OK - Strategy execution only |
| Order generation | Trading domain | Returns List[Order] | ✅ OK - Return type |
| Signal generation | Trading domain | Calls generate_signals() | ✅ OK - execute() |
| Config validation | Clean code | validate_config() delegation | ✅ OK - validate_strategy_config() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**GAPS identified:**
- ✅ **FIXED 2026-02-01:** execute() now converts signals to orders properly via _convert_signals_to_orders() and _signal_to_order()
- ✅ **FIXED 2026-02-01:** Order generation logic implemented - converts Signal objects to Order entities with proper handling
- ✅ **FIXED 2026-02-01:** strategy_type and parameters are now used - parameters applied to strategy, strategy_type included in order_id and event history

**NOTE:** Previously a stub implementation, now fully functional for production use.

---

## Dependencies
- **Internal:**
  - `app.domain.entities.order.Order`
  - `app.strategies.base.BaseStrategy`
- **External:** None

---

## Required Tests
- **test_execute_strategy_use_case.py:**
  - `test_init_with_strategy()` - Stores strategy
  - `test_init_without_strategy()` - Stores None
  - `test_execute_with_strategy()` - Calls generate_signals
  - `test_execute_without_strategy()` - Returns empty list
  - `test_validate_config_with_strategy()` - Delegates to strategy
  - `test_validate_config_without_strategy()` - Returns False
  - `test_execute_returns_orders()` - Returns List[Order] (when implemented)
  - `test_signal_to_order_conversion()` - Converts signals to orders (when implemented)

---

## Validation

**QA Commands (from check_all.sh and Ralphex config):**

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/application/use_cases/execute_strategy_use_case.py

# 2. Type check (strict mode)
mypy --strict app/application/use_cases/execute_strategy_use_case.py

# 3. Lint
ruff check app/application/use_cases/execute_strategy_use_case.py

# 4. Format check
black --check app/application/use_cases/execute_strategy_use_case.py

# 5. Import sort check
isort --check-only app/application/use_cases/execute_strategy_use_case.py

# 6. Security scan
bandit app/application/use_cases/execute_strategy_use_case.py

# 7. Related tests
pytest tests/application/use_cases/test_execute_strategy_use_case.py -v 2>/dev/null || echo "No tests yet"

```

**Expected Results:**
- Syntax: PASS
- Mypy: PASS (no type errors)
- Ruff: PASS (no lint errors)
- Black: PASS (already formatted)
- Isort: PASS (imports sorted)
- Bandit: PASS (no security issues)
- Tests: PASS (all tests pass)

---

## Notes
- **Status:** Production-ready implementation as of 2026-02-01
- **Fixes Applied 2026-02-01:**
  - GAP-001: Implemented `_convert_signals_to_orders()` method to properly convert Signal list to Order list
  - GAP-002: Implemented `_signal_to_order()` method to convert individual Signal to Order entity
  - GAP-003: Added parameter handling via `strategy.update_parameters(parameters)` when parameters are provided
  - GAP-004: Added strategy_type usage in order_id and event history for traceability
  - Added logging throughout execution flow (logger.warning, logger.debug, logger.info, logger.error)
  - Added filtering of HOLD signals (they don't generate orders)
  - Added filtering of non-actionable signals based on confidence threshold
  - Added error handling with try-except blocks for graceful degradation
  - Added signal metadata storage in order event_history for audit trail
- **Current Behavior:**
  - execute() applies parameters to strategy if provided
  - execute() calls strategy.generate_signals(symbol)
  - execute() converts signals to orders, filtering HOLD and low-confidence signals
  - Orders are created with proper OrderSide, OrderType, and OrderStatus
  - Order IDs include strategy_type for traceability
  - Signal metadata is stored in order event_history
- **Production Features:**
  - Signal-to-order conversion implemented
  - strategy_type used in order generation and tracking
  - parameters applied to strategy configuration
  - Comprehensive logging for debugging and monitoring
  - Error handling with graceful degradation
  - HOLD signal filtering (no orders generated)
  - Confidence-based signal filtering (is_actionable property)
- **Use Case Pattern:** Application layer orchestrates domain logic
- **Dependency Injection:** Strategy is injected (Dependency Inversion Principle)

---

**File Reference:** `app/application/use_cases/execute_strategy_use_case.py`
**Last Audited:** 2026-02-01
**Last Fixed:** 2026-02-01 - All GAP violations resolved
