# orchestrator.py

## Purpose
Coordination and orchestration for backtesting operations including result management, defaults configuration, and multi-strategy execution coordination.

---

## Type Definitions / Data Classes

### BacktestDefaults (Dataclass-like)
```python
class BacktestDefaults:
    COMMISSION: Decimal = Decimal("10.0")           # $10 per trade
    SLIPPAGE: Decimal = Decimal("0.1")              # 0.1%
    INITIAL_CAPITAL: Decimal = Decimal("100000")    # $100k
    MAX_POSITION_SIZE: Decimal = Decimal("0.10")    # 10% of capital
    RISK_FREE_RATE: Decimal = Decimal("0.02")       # 2% annual
    STOP_LOSS_PERCENTAGE: Decimal = Decimal("5.0")  # 5%
    TAKE_PROFIT_PERCENTAGE: Decimal = Decimal("10.0")  # 10%
```
**Validation Rules:**
- All values are positive Decimal numbers
- Percentages are expressed as decimals (0.10 = 10%)
- Used ONLY when configuration is not provided
- **CRITICAL:** Always use proper YAML configuration with risk management parameters in production

### BoundedResults
```python
class BoundedResults:
    _results: deque                 # Thread-safe bounded storage
    _lock: Lock                    # Threading lock for safety
    _maxlen: int                   # Maximum capacity
```
**Validation Rules:**
- maxlen defaults to 1000
- Cleanup triggered at 80% capacity (keeps at 80%)
- Thread-safe via Lock
- Automatic cleanup when limit exceeded

### OrchestrationResult
```python
class OrchestrationResult:
    results: List[Any]             # List of backtest results
    total: int                     # Total count
    config: Optional[BacktestConfig]  # Config used
    _summary: Dict[str, Any]       # Cached summary
```
**Validation Rules:**
- Lazy calculation of summary (cached)
- Handles both dict and BacktestResult objects
- Success criteria: final_capital > 0 or dict['final_capital'] > 0

---

## Function Signatures (Contracts)

### `BacktestDefaults (class constants)`
**Pre:** None (class-level constants)
**Post:** Provides default values for backtesting
**Raises:** No
**Retry:** No
**Side Effects:** None (class constants)

### `BoundedResults.__init__(maxlen: int = 1000) -> None`
**Pre:** maxlen > 0
**Post:** Initialized with empty deque, lock, and maxlen
**Raises:** No
**Retry:** No
**Side Effects:** Creates deque and Lock

### `BoundedResults.add(result: Dict[str, Any]) -> None`
**Pre:** result is valid dict
**Post:** Result added to deque, cleanup triggered if needed
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe append to deque, potential cleanup

### `BoundedResults.extend(results: List[Dict[str, Any]]) -> None`
**Pre:** results is list of valid dicts
**Post:** All results added to deque, cleanup triggered if needed
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe extend of deque, potential cleanup

### `BoundedResults.get_all() -> List[Dict[str, Any]]`
**Pre:** None
**Post:** Returns list of all results (copy, not reference)
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe read

### `BoundedResults.get_latest(n: int) -> List[Dict[str, Any]]`
**Pre:** n > 0
**Post:** Returns last n results (or all if fewer)
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe read

### `BoundedResults.clear() -> None`
**Pre:** None
**Post:** All results removed
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe clear of deque

### `BoundedResults._cleanup_if_needed() -> None`
**Pre:** None
**Post:** Results reduced to 80% of maxlen if exceeded
**Raises:** No
**Retry:** No
**Side Effects:** Removes oldest entries via popleft()

### `OrchestrationResult.__init__(results: List[Any], config: Optional[BacktestConfig] = None) -> None`
**Pre:** results is list (may be empty)
**Post:** Result initialized with results, total count, config, and None summary
**Raises:** No
**Retry:** No
**Side Effects:** None

### `OrchestrationResult.summary (property) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns cached summary or calculates and caches it
**Raises:** No
**Retry:** No
**Side Effects:** May calculate summary if first access

### `OrchestrationResult._calculate_summary() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with total, successful, failed, and optional metrics
**Raises:** No
**Retry:** No
**Side Effects:** None (pure calculation)

### `OrchestrationResult._is_successful(result: Any) -> bool`
**Pre:** result is dict or BacktestResult
**Post:** Returns True if final_capital > 0, False otherwise
**Raises:** No
**Retry:** No
**Side Effects:** None

### `OrchestrationResult.get_best_result(metric: str = 'sharpe_ratio') -> Optional[Any]`
**Pre:** metric is valid key in results
**Post:** Returns result with highest metric value or None if empty
**Raises:** No
**Retry:** No
**Side Effects:** None

### `OrchestrationResult.filter_results(**criteria) -> List[Any]`
**Pre:** criteria are key-value pairs
**Post:** Returns filtered list of dict results matching all criteria
**Raises:** No
**Retry:** No
**Side Effects:** None (pure filtering)

### `BacktestOrchestrator.__init__(config, executor=None, max_results=1000) -> None`
**Pre:** config is valid BacktestConfig
**Post:** Orchestrator initialized with config, optional executor, and bounded results
**Raises:** No
**Retry:** No
**Side Effects:** Creates BoundedResults instance

### `BacktestOrchestrator.run_all(quotes, strategies, **kwargs) -> OrchestrationResult`
**Pre:** quotes is non-empty list, strategies is non-empty list
**Post:** Returns OrchestrationResult with all results (some may have failed)
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** Executes each strategy, adds results to BoundedResults, logs errors

### `BacktestOrchestrator._run_single(quotes, strategy, **kwargs) -> BacktestResult`
**Pre:** quotes non-empty, strategy valid
**Post:** Returns BacktestResult from executor, increments execution_count
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError (propagated)
**Retry:** No
**Side Effects:** Creates executor if None, executes backtest

### `BacktestOrchestrator._result_to_dict(result: BacktestResult) -> Dict[str, Any]`
**Pre:** result is BacktestResult or dict
**Post:** Returns dict with key metrics
**Raises:** No (handles non-BacktestResult gracefully)
**Retry:** No
**Side Effects:** None (conversion only)

---

## Acceptance Criteria
- [ ] BacktestDefaults provides all required default values
- [ ] BoundedResults maintains thread-safe operations
- [ ] BoundedResults automatically cleans up at 80% capacity
- [ ] OrchestrationResult calculates summary statistics correctly
- [ ] OrchestrationResult identifies successful results (final_capital > 0)
- [ ] OrchestrationResult.get_best_result returns result with highest metric
- [ ] BacktestOrchestrator.run_all executes all strategies
- [ ] BacktestOrchestrator.run_all handles failures gracefully
- [ ] BacktestOrchestrator.run_all stores results in BoundedResults
- [ ] BacktestOrchestrator creates executor if not provided
- [ ] execution_count increments with each execution

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` for 96 universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | OK - Each class has single responsibility |
| SOL-005 | BASE_RULES.md | Dependency Inversion | NOT APPLIED - Simple orchestrator, direct dependencies acceptable |
| TYP-001 | BASE_RULES.md | 100% type coverage | GAP - Missing return types for some methods, TYPE_CHECKING used but incomplete |
| TYP-003 | BASE_RULES.md | No Any without justification | GAP - List[Any], Dict[str, Any], Any used throughout (could use Protocol for duck typing) |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ FIXED - 2026-02-03 - Added structured logging with context via extra={} |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | OK - Line 321 has exc_info=True |
| CC-001 | BASE_RULES.md | Descriptive names | OK |
| CC-006 | BASE_RULES.md | Explicit error handling | OK - Catches specific exception types |
| ARCH-006 | BASE_RULES.md | Value objects immutable | GAP - BacktestDefaults should be frozen dataclass or use Constants |
| TRD-002 | BASE_RULES.md | Risk validation | NOT APPLIED - Orchestrator doesn't validate, delegates to executor |

---

## Dependencies
- **External:** logging, collections.deque, decimal.Decimal, threading.Lock, typing
- **Internal:** app.backtesting.models (BacktestConfig, BacktestResult)
- **Internal (Forward Reference):** app.backtesting.core.executor.BacktestExecutor (TYPE_CHECKING only)

---

## Required Tests
- **tests/unit/backtesting/core/test_orchestrator.py:**
  - Test BacktestDefaults constants are positive Decimals
  - Test BoundedResults.add adds result thread-safely
  - Test BoundedResults.extend adds multiple results
  - Test BoundedResults.cleanup triggers at 80% capacity
  - Test BoundedResults.get_all returns copy of results
  - Test BoundedResults.get_latest returns n results
  - Test BoundedResults.clear removes all results
  - Test OrchestrationResult.summary calculates statistics
  - Test OrchestrationResult.summary handles empty results
  - Test OrchestrationResult._is_successful identifies positive capital
  - Test OrchestrationResult.get_best_result returns max metric
  - Test OrchestrationResult.filter_results filters by criteria
  - Test BacktestOrchestrator.run_all executes all strategies
  - Test BacktestOrchestrator.run_all handles failures
  - Test BacktestOrchestrator._run_single creates executor if None
  - Test BacktestOrchestrator._result_to_dict converts BacktestResult
  - Test BacktestOrchestrator._result_to_dict handles dict input
  - Test execution_count increments
  - Test BoundedResults thread safety with concurrent access

---

## Notes
- BacktestDefaults are fallback values; production should always use YAML configuration with risk management
- BoundedResults uses deque for O(1) append/popleft operations
- OrchestrationResult supports both dict and BacktestResult for flexibility
- Summary is lazy-calculated and cached for performance
- Thread-safe operations via Lock for concurrent execution scenarios
