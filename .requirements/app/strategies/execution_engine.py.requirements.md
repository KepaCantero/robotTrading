# execution_engine.py

## Purpose
Motor de ejecución centralizado - Coordina la ejecución de estrategias activas, generación de señales, validación de riesgo y ejecución de órdenes.

---

## Type Definitions / Data Classes

No custom dataclasses defined

---

## Function Signatures (Contracts)

### `ExecutionEngine.__init__(registry: StrategyRegistry, logger: StrategyLogger)`
**Pre:** registry and logger are initialized
**Post:** Engine initialized with registry and logger
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ExecutionEngine.start() -> None`
**Pre:** Engine not running
**Post:** Engine is_running = True
**Raises:** None (logs warning if already running)
**Retry:** No
**Side Effects:** Sets is_running flag

### `ExecutionEngine.stop() -> None`
**Pre:** Engine is running
**Post:** Engine is_running = False
**Raises:** None (logs warning if not running)
**Retry:** No
**Side Effects:** Resets is_running flag

### `ExecutionEngine.run_cycle(market_data: Quote, portfolio: Portfolio) -> List[Signal]`
**Pre:** Engine is running, market_data and portfolio are valid
**Post:** Returns list of validated signals
**Raises:** None (logs errors, returns empty list)
**Retry:** No
**Side Effects:** Increments cycle_count, generates signals, logs to strategy_logger

### `ExecutionEngine.execute_signal(signal: Signal, execution_price: Optional[Decimal] = None) -> bool`
**Pre:** signal is valid
**Post:** Returns True if execution successful
**Raises:** None (logs errors, returns False)
**Retry:** Yes (execution can be retried)
**Side Effects:** Logs to strategy_logger, increments total_signals_executed

### `ExecutionEngine.execute_signals(signals: List[Signal], execution_prices: Optional[Dict[str, Decimal]] = None) -> Dict[str, bool]`
**Pre:** signals list is non-empty
**Post:** Returns dict of execution results
**Raises:** None
**Retry:** Per-signal retry available
**Side Effects:** Executes all signals, logs results

### `ExecutionEngine.validate_market_data(market_data: Quote) -> bool`
**Pre:** market_data is not None
**Post:** Returns True if valid, False otherwise
**Raises:** None (logs errors, returns False)
**Retry:** No
**Side Effects:** None

### `ExecutionEngine.validate_portfolio(portfolio: Portfolio) -> bool`
**Pre:** portfolio is not None
**Post:** Returns True if valid, False otherwise
**Raises:** None (logs errors, returns False)
**Retry:** No
**Side Effects:** None

### `ExecutionEngine.run_cycle_with_validation(market_data: Quote, portfolio: Portfolio) -> List[Signal]`
**Pre:** market_data and portfolio are not None
**Post:** Returns list of validated signals or empty list
**Raises:** None (logs errors, returns empty list)
**Retry:** No
**Side Effects:** Validates inputs, runs cycle

### `ExecutionEngine.get_execution_stats() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns execution statistics
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ExecutionEngine.reset_stats() -> None`
**Pre:** None
**Post:** Statistics reset to zero
**Raises:** None
**Retry:** No
**Side Effects:** Resets counters

---

## Acceptance Criteria
- [ ] Engine only runs cycles when is_running is True
- [ ] run_cycle generates signals from active strategy
- [ ] run_cycle validates signals with risk_check
- [ ] run_cycle logs generated and rejected signals
- [ ] execute_signal logs execution to strategy_logger
- [ ] execute_signal returns True on success, False on failure
- [ ] validate_market_data checks symbol, price, volume
- [ ] validate_portfolio checks cash and position quantities
- [ ] run_cycle_with_validation skips cycle if validation fails
- [ ] get_execution_stats calculates execution_rate correctly

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-python-expert (via Tech Lead Orchestrator) |
| **GAPs Fixed** | 0 / ? total |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| LOG-001 | BASE_RULES | Structured logging | ✅ FIXED - Changed to structured logging (lines 92, 102, 106, 110, 114, 142) |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - Added exc_info=True (lines 108, 112, 147, 153, 240, 270) |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - Uses specific exceptions (lines 108, 112, 147, 240, 270) |
| TRD-002 | BASE_RULES | Risk validation | ✅ OK - Validates signals with risk_check |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - All operations logged |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ✅ OK - Most functions <20 lines |

---

## Dependencies
- **External:** logging, datetime, decimal, typing
- **Internal:** 
  - app.models.market_data.Quote
  - app.models.portfolio.Portfolio
  - app.models.signal.Signal
  - .registry.StrategyRegistry
  - .strategy_logger.StrategyLogger

---

## Required Tests
- **tests/strategies/test_execution_engine.py:**
  - Test start sets is_running to True
  - Test start when already running (logs warning)
  - Test stop sets is_running to False
  - Test run_cycle with active strategy
  - Test run_cycle without active strategy (returns empty)
  - Test run_cycle when not running (returns empty)
  - Test run_cycle logs generated signals
  - Test run_cycle logs rejected signals
  - Test execute_signal returns True on success
  - Test execute_signal returns False on failure
  - Test execute_signals processes multiple signals
  - Test validate_market_data with valid data
  - Test validate_market_data with missing symbol
  - Test validate_market_data with invalid price
  - Test validate_portfolio with valid portfolio
  - Test validate_portfolio with negative cash
  - Test validate_portfolio with negative position quantity
  - Test get_execution_stats returns correct stats
  - Test reset_stats resets counters

---

## Notes
- Spanish language comments and docstrings
- Uses StrategyRegistry for active strategy management
- Uses StrategyLogger for structured logging
- Validates inputs before processing
- Tracks execution statistics (cycles, signals generated/executed)
