# backtest.py

## Purpose
Backtest Entity - Core business object for backtesting operations with configuration, execution state, and results.

---

## Type Definitions / Data Classes

### BacktestStatus (Enum)
```python
class BacktestStatus(Enum):
    PENDING = "pending"          # Not yet started
    RUNNING = "running"          # Currently executing
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Failed with error
    CANCELLED = "cancelled"      # Cancelled by user
```

### BacktestType (Enum)
```python
class BacktestType(Enum):
    BASELINE = "baseline"                      # Baseline backtest
    LEARNING_ENGINES = "learning_engines"      # Learning engines test
    WALK_FORWARD = "walk_forward"              # Walk-forward validation
    MONTE_CARLO = "monte_carlo"                # Monte Carlo simulation
    TRANSFORMER_OPTIMIZATION = "transformer_optimization"  # Transformer optimization
    ABLATION = "ablation"                      # Ablation study
    GRID_SEARCH = "grid_search"                # Grid search optimization
    OUT_OF_SAMPLE = "out_of_sample"            # Out-of-sample test
    MULTI_STRATEGY = "multi_strategy"          # Multi-strategy test
    REGIME_TEST = "regime_test"                # Market regime test
```

### Backtest
```python
@dataclass
class Backtest:
    backtest_id: str                           # REQUIRED - Unique backtest identifier
    config: BacktestConfigValue                # REQUIRED - Backtest configuration
    status: BacktestStatus                     # Default: PENDING
    result: Optional[BacktestResultValue]      # Default: None
    error_message: Optional[str]               # Default: None
    created_at: datetime                       # Default: utcnow()
    started_at: Optional[datetime]             # Default: None
    completed_at: Optional[datetime]           # Default: None
```

**Invariants (enforced in __post_init__):**
- `backtest_id` must be non-empty
- `config` must be provided

---

## Function Signatures (Contracts)

### `Backtest.__post_init__() -> None`
**Pre:** None
**Post:** Backtest validated
**Raises:** `ValueError` if backtest_id is empty or config is None
**Retry:** No
**Side Effects:** Validates invariants

### `start() -> None`
**Pre:** status == PENDING
**Post:** status = RUNNING; started_at set
**Raises:** `ValueError` if status != PENDING
**Retry:** No
**Side Effects:** Updates status and timestamp

### `complete(result) -> None`
**Pre:** status == RUNNING; result is valid BacktestResultValue
**Post:** status = COMPLETED; result set; completed_at set
**Raises:** `ValueError` if status != RUNNING
**Retry:** No
**Side Effects:** Updates status, result, and timestamp

### `fail(error_message) -> None`
**Pre:** status != COMPLETED
**Post:** status = FAILED; error_message set; completed_at set
**Raises:** `ValueError` if status == COMPLETED
**Retry:** No
**Side Effects:** Updates status, error_message, and timestamp

### `cancel() -> None`
**Pre:** status not in [COMPLETED, FAILED]
**Post:** status = CANCELLED; completed_at set
**Raises:** `ValueError` if status in terminal states
**Retry:** No
**Side Effects:** Updates status and timestamp

### `get_duration() -> Optional[float]`
**Pre:** None
**Post:** Returns (completed_at - started_at).total_seconds() if both set, else None
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_running() -> bool`
**Pre:** None
**Post:** Returns True if status == RUNNING
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_completed() -> bool`
**Pre:** None
**Post:** Returns True if status == COMPLETED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_failed() -> bool`
**Pre:** None
**Post:** Returns True if status == FAILED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_roi() -> Optional[Decimal]`
**Pre:** None
**Post:** Returns (final_capital - initial_capital) / initial_capital if result exists, else None
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_sharpe_ratio() -> Optional[Decimal]`
**Pre:** None
**Post:** Returns sharpe_ratio from result if exists, else None
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

---

## Acceptance Criteria
- [ ] **AC-001:** Backtest ID must be non-empty
- [ ] **AC-002:** Configuration must be provided
- [ ] **AC-003:** Can only start from PENDING state
- [ ] **AC-004:** Can only complete from RUNNING state
- [ ] **AC-005:** Cannot fail a completed backtest
- [ ] **AC-006:** Cannot cancel from COMPLETED or FAILED state
- [ ] **AC-007:** Duration calculated from started_at to completed_at
- [ ] **AC-008:** ROI = (final - initial) / initial
- [ ] **AC-009:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Backtest Entity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Entity invariants | DDD (Evans) | Validate on creation | ✅ OK - __post_init__ |
| State machine | Backtesting standard | Valid state transitions only | ✅ OK - Enforced in methods |
| Terminal states | State machine | COMPLETED, FAILED are terminal | ✅ OK - Cannot fail completed |
| Backtest types | Pardo standard | 10 types supported | ✅ OK - BacktestType enum |
| Duration tracking | Backtesting standard | Track execution time | ✅ OK - get_duration() |
| ROI calculation | Finance standard | (final - initial) / initial | ✅ OK - get_roi() |
| Sharpe ratio | Pardo standard | Risk-adjusted return metric | ✅ OK - get_sharpe_ratio() |
| Configuration | Backtesting standard | Config value object required | ✅ OK - BacktestConfigValue |
| Results | Backtesting standard | Result value object | ✅ OK - BacktestResultValue |
| Error tracking | Backtesting standard | Error message on failure | ✅ OK - error_message |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only domain types |
| Value objects | DDD (Evans) | Config and Result are value objects | ✅ OK - Used correctly |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008) for backtesting standards.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:**
  - `app.domain.value_objects.backtest_config` (BacktestConfigValue)
  - `app.domain.value_objects.backtest_result` (BacktestResultValue)

---

## Required Tests
- **test_backtest_entity.py:**
  - `test_create_backtest_success()` - Valid backtest created
  - `test_create_backtest_empty_id()` - Raises ValueError
  - `test_create_backtest_no_config()` - Raises ValueError
  - `test_start_from_pending()` - Transitions to RUNNING
  - `test_start_from_running()` - Raises ValueError
  - `test_complete_from_running()` - Transitions to COMPLETED with result
  - `test_complete_from_pending()` - Raises ValueError
  - `test_fail_from_pending()` - Transitions to FAILED
  - `test_fail_from_completed()` - Raises ValueError
  - `test_cancel_from_pending()` - Transitions to CANCELLED
  - `test_cancel_from_completed()` - Raises ValueError
  - `test_cancel_from_failed()` - Raises ValueError
  - `test_get_duration_completed()` - Returns seconds
  - `test_get_duration_not_completed()` - Returns None
  - `test_is_running()` - True when RUNNING
  - `test_is_completed()` - True when COMPLETED
  - `test_is_failed()` - True when FAILED
  - `test_get_roi_with_result()` - Calculates ROI
  - `test_get_roi_no_result()` - Returns None
  - `test_get_sharpe_with_result()` - Returns sharpe_ratio
  - `test_get_sharpe_no_result()` - Returns None

---

## Notes
- **Critical:** Backtest is an entity representing a backtesting operation (not the backtesting engine itself)
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008)
- **State Machine:** PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
- **Terminal States:** COMPLETED, FAILED (no transitions allowed)
- **Duration:** Time from started_at to completed_at in seconds
- **ROI:** Return on Investment = (final_capital - initial_capital) / initial_capital
- **Sharpe Ratio:** Risk-adjusted return metric from result
- **Backtest Types:** 10 different types for various testing scenarios
  - BASELINE: Standard historical test
  - WALK_FORWARD: Rolling window validation
  - MONTE_CARLO: Probabilistic simulation
  - OUT_OF_SAMPLE: Test on unseen data
  - etc.
- **Error Handling:** error_message captures failure reason
- **Value Objects:** Uses BacktestConfigValue and BacktestResultValue
- **Timestamps:** created_at, started_at, completed_at for audit trail

---

**File Reference:** `app/domain/entities/backtest.py`
**Last Audited:** 2026-02-01
