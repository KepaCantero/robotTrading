# orchestrator.py

## Purpose
Provides coordination, result management, and orchestration for backtesting operations including thread-safe bounded results and parallel execution support.

---

## Type Definitions / Data Classes

### BacktestDefaults Class
```python
class BacktestDefaults:
    COMMISSION: Decimal           # = Decimal("10.0") - $10 per trade
    SLIPPAGE: Decimal             # = Decimal("0.1") - 0.1% slippage
    INITIAL_CAPITAL: Decimal      # = Decimal("100000") - Starting capital
    MAX_POSITION_SIZE: Decimal    # = Decimal("0.10") - 10% max position
    RISK_FREE_RATE: Decimal       # = Decimal("0.02") - 2% annual
    STOP_LOSS_PERCENTAGE: Decimal # = Decimal("5.0") - 5% stop loss
    TAKE_PROFIT_PERCENTAGE: Decimal # = Decimal("10.0") - 10% take profit
    SHARPE_RATIO_EXCELLENT: float # = 2.0
    SHARPE_RATIO_GOOD: float      # = 1.0
    SHARPE_RATIO_WARNING: float   # = 0.5
    MAX_DRAWDOWN_WARNING: Decimal # = Decimal("-0.20") - -20%
    MAX_DRAWDOWN_CRITICAL: Decimal # = Decimal("-0.50") - -50%
    WIN_RATE_EXCELLENT: Decimal   # = Decimal("0.60") - 60%
    WIN_RATE_GOOD: Decimal        # = Decimal("0.50") - 50%
    WIN_RATE_WARNING: Decimal     # = Decimal("0.40") - 40%
```

**Validation Rules:**
- All values are Decimal for financial precision
- Used ONLY when config not provided (should use YAML config in production)

### BoundedResults Class
```python
class BoundedResults:
    _results: deque              # REQUIRED - Deque with maxlen for auto-cleanup
    _lock: Lock                  # REQUIRED - Threading lock for thread-safety
    _maxlen: int                 # REQUIRED - Maximum size (default: 1000)
```

**Validation Rules:**
- Thread-safe add/extend/get_all/clear operations
- Automatic cleanup at 80% capacity (keeps at 80% of maxlen)
- maxlen enforced by deque itself

### OrchestrationResult Class
```python
class OrchestrationResult:
    results: List[Any]           # REQUIRED - List of backtest results
    total: int                   # REQUIRED - Total count
    config: Optional[BacktestConfig] # OPTIONAL - Config used
    _summary: Dict[str, Any] | None  # PRIVATE - Cached summary
```

**Validation Rules:**
- summary property is lazy-calculated and cached
- Successful if final_capital > 0 or dict['final_capital'] > 0

### BacktestOrchestrator Class
```python
class BacktestOrchestrator:
    config: BacktestConfig        # REQUIRED - Backtest configuration
    executor: Optional[BacktestExecutor] # OPTIONAL - Created from config if None
    results: BoundedResults       # REQUIRED - Thread-safe results storage
    _execution_count: int         # PRIVATE - Number of executions
```

**Validation Rules:**
- executor created lazily if not provided
- max_results defaults to 1000

---

## Function Signatures (Contracts)

### `BoundedResults.__init__(maxlen: int = 1000) -> None`
**Pre:** maxlen > 0
**Post:** Thread-safe bounded container initialized
**Raises:** No
**Retry:** No
**Side Effects:** Creates deque(maxlen=maxlen) and Lock()

### `BoundedResults.add(result: Dict[str, Any]) -> None`
**Pre:** result is dict
**Post:** result added, cleanup triggered if >80% capacity
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe append, potential cleanup

### `BoundedResults.extend(results: List[Dict[str, Any]]) -> None`
**Pre:** results is list of dicts
**Post:** All results added, cleanup triggered if needed
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe extend, potential cleanup

### `BoundedResults.get_all() -> List[Dict[str, Any]]`
**Pre:** None
**Post:** Returns list of all results (copy)
**Raises:** No
**Retry:** No
**Side Effects:** None (thread-safe read)

### `BoundedResults.get_latest(n: int) -> List[Dict[str, Any]]`
**Pre:** n > 0
**Post:** Returns latest n results or all if n > len(results)
**Raises:** No
**Retry:** No
**Side Effects:** None (thread-safe read)

### `BoundedResults.clear() -> None`
**Pre:** None
**Post:** All results removed
**Raises:** No
**Retry:** No
**Side Effects:** Thread-safe clear

### `BoundedResults._cleanup_if_needed() -> None`
**Pre:** None (private method)
**Post:** If >80% capacity, reduces to 80% by removing oldest
**Raises:** No
**Retry:** No
**Side Effects:** Removes oldest results via popleft()

### `OrchestrationResult.summary property -> Dict[str, Any]`
**Pre:** None
**Post:** Returns cached or calculated summary statistics
**Raises:** No
**Retry:** No
**Side Effects:** None (lazy calculation)

### `OrchestrationResult.get_best_result(metric: str = 'sharpe_ratio') -> Optional[Any]`
**Pre:** metric is valid attribute name
**Post:** Returns best result by metric or None
**Raises:** No
**Retry:** No
**Side Effects:** None

### `OrchestrationResult.filter_results(**criteria) -> List[Any]`
**Pre:** criteria are key-value pairs
**Post:** Returns filtered list of dict results
**Raises:** No
**Retry:** No
**Side Effects:** None

### `BacktestOrchestrator.run_all(quotes: List[Any], strategies: List[Any], **kwargs) -> OrchestrationResult`
**Pre:** quotes non-empty, strategies non-empty
**Post:** Returns OrchestrationResult with all results
**Raises:** No (errors caught and logged)
**Retry:** No
**Side Effects:** Executes each strategy, stores results

### `BacktestOrchestrator.execution_count property -> int`
**Pre:** None
**Post:** Returns number of executions performed
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-ORCH-001: BoundedResults enforces maxlen via deque
- [ ] AC-ORCH-002: BoundedResults.cleanup keeps at 80% capacity
- [ ] AC-ORCH-003: BoundedResults is thread-safe (Lock used)
- [ ] AC-ORCH-004: OrchestrationResult.summary calculates success/failed counts
- [ ] AC-ORCH-005: OrchestrationResult.summary includes avg_return/best_return if BacktestResult
- [ ] AC-ORCH-006: BacktestOrchestrator.run_all executes all strategies despite individual failures
- [ ] AC-ORCH-007: BacktestDefaults values are all Decimal type

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules with 23 P0)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ORCH-001 | BASE_RULES.md (CC-007) | Thread-safety for concurrent access | ✅ OK - Uses threading.Lock |
| ORCH-002 | BASE_RULES.md (TRD-001) | Decimal for financial values | ✅ OK - BacktestDefaults uses Decimal |
| ORCH-003 | BASE_RULES.md (DP-005) | Observer pattern for results | ⚠️ NOT APPLIED - Not using observer |
| ORCH-004 | BASE_RULES.md (ARCH-004) | Small functions | ✅ OK - Methods focused and concise |
| ORCH-005 | BASE_RULES.md (TYP-001) | Type hints coverage | ✅ OK - All methods have type hints |
| ORCH-006 | BASE_RULES.md (LOG-001) | Structured logging | ✅ OK - Uses logger |
| ORCH-007 | BASE_RULES.md (BT-002) | Out-of-sample testing | ⚠️ GAP - No validation of data splits |

**GAP Analysis:**
- **ORCH-003:** Could implement observer pattern for result notifications (optional enhancement, not critical)
- **ORCH-007:** Orchestrator doesn't validate train/test splits. Add validation for walk-forward testing.

---

## Dependencies
- **External:** collections.deque, threading.Lock, decimal.Decimal
- **Internal:**
  - `app.backtesting.models.BacktestConfig`
  - `app.backtesting.models.BacktestResult`

---

## Required Tests
- **tests/backtesting/core/test_orchestrator.py:**
  - Test BoundedResults enforces maxlen
  - Test BoundedResults.cleanup at 80% capacity
  - Test BoundedResults thread-safety (concurrent add/extend)
  - Test OrchestrationResult.summary calculation
  - Test OrchestrationResult.get_best_result() metrics
  - Test OrchestrationResult.filter_results()
  - Test BacktestOrchestrator.run_all() with multiple strategies
  - Test BacktestOrchestrator handles individual strategy failures
  - Test BacktestDefaults are Decimal type
  - Test _result_to_dict() conversion

---

## Notes
Core coordination layer for backtesting. BoundedResults critical for memory management. BacktestDefaults provide fallback but YAML config should be used in production.
