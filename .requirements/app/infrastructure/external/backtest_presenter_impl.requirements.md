# backtest_presenter_impl.py

## Purpose
Backtest Presenter Implementation - Humble Object for UI/visualization. Provides presentation logic for backtest results, following the Humble Object pattern to keep UI code testable.

---

## Type Definitions / Data Classes

### BacktestPresenterImpl(BacktestPresenter)
```python
class BacktestPresenterImpl(BacktestPresenter):
    """
    Implementation of backtest presenter for UI layer.

    This class is a humble object that formats domain entities
    for presentation in the UI layer. It contains minimal logic
    and delegates business operations to use cases.
    """
```

**Dependencies:**
- `BacktestRepository` - for fetching backtest data
- `AnalyzeBacktestResultsUseCase` - for business logic

**Inheritance:** Implements `BacktestPresenter` (application interface)

**Pattern:** Humble Object Pattern - thin presenters, delegate to use cases

---

## Function Signatures (Contracts)

### `BacktestPresenterImpl.__init__(
    backtest_repository: BacktestRepository,
    analyzer: AnalyzeBacktestResultsUseCase,
) -> None`
**Pre:** backtest_repository and analyzer are valid
**Post:** Presenter initialized with dependencies
**Raises:** None
**Retry:** No
**Side Effects:** Stores repository and analyzer references

**Dependency Injection:** Both dependencies injected via constructor

### `BacktestPresenterImpl.present_backtest_result(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns presentation-ready dictionary or error dict
**Raises:** None (returns error dict on failure)
**Retry:** No
**Side Effects:** Calls repository.find_by_id()

**Process Flow:**
1. Fetch backtest from repository
2. Return error dict if not found
3. Format and return via `_format_backtest()`

### `BacktestPresenterImpl.present_backtest_list(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]`
**Pre:** limit >= 0; offset >= 0
**Post:** Returns list of presentation-ready dictionaries
**Raises:** None
**Retry:** No
**Side Effects:** Calls repository.find_all()

**Process Flow:**
1. Fetch backtests from repository (with pagination)
2. Format each via `_format_backtest_summary()`
3. Return list

### `BacktestPresenterImpl.present_performance_summary(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns presentation-ready summary or error dict
**Raises:** None (returns error dict on failure)
**Retry:** No
**Side Effects:** Calls analyzer.get_performance_summary()

**Process Flow:**
1. Get summary from analyzer use case
2. Return error dict if no data
3. Return wrapped summary dict

**Output Format:**
```python
{
    'status': 'success',
    'data': {...summary from analyzer...}
}
```

### `BacktestPresenterImpl.present_comparison(backtest_ids: List[str]) -> Optional[Dict[str, Any]]`
**Pre:** backtest_ids is non-empty list
**Post:** Returns presentation-ready comparison or error dict
**Raises:** None (returns error dict on failure)
**Retry:** No
**Side Effects:** Calls analyzer.compare_backtests()

**Process Flow:**
1. Get comparison from analyzer use case
2. Return error dict if comparison fails
3. Return wrapped comparison dict

**Output Format:**
```python
{
    'status': 'success',
    'data': {...comparison from analyzer...}
}
```

### `BacktestPresenterImpl.present_error(error_message: str) -> Dict[str, Any]`
**Pre:** error_message is non-empty string
**Post:** Returns error dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure formatting)

**Output Format:**
```python
{
    'status': 'error',
    'error': error_message
}
```

### `BacktestPresenterImpl._format_backtest(backtest: Backtest) -> Dict[str, Any]`
**Pre:** backtest is valid entity
**Post:** Returns formatted dictionary for UI
**Raises:** None
**Retry:** No
**Side Effects:** None (pure formatting)

**Output Fields:**
- status: 'success'
- data.backtest_id, strategy, status
- data.created_at, started_at, completed_at (ISO format)
- data.duration_seconds
- data.results (initial_capital, final_capital, total_return_pct, sharpe_ratio, max_drawdown, total_trades, win_rate)
- data.error

### `BacktestPresenterImpl._format_backtest_summary(backtest: Backtest) -> Dict[str, Any]`
**Pre:** backtest is valid entity
**Post:** Returns formatted summary dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure formatting)

**Output Fields (for list views):**
- backtest_id, strategy, status
- created_at, completed_at (ISO format)
- total_return_pct, sharpe_ratio

---

## Acceptance Criteria
- [ ] **AC-001:** BacktestPresenterImpl implements BacktestPresenter
- [ ] **AC-002:** __init__() injects BacktestRepository and AnalyzeBacktestResultsUseCase
- [ ] **AC-003:** present_backtest_result() returns error dict when not found
- [ ] **AC-004:** present_backtest_result() formats via _format_backtest()
- [ ] **AC-005:** present_backtest_list() applies limit and offset
- [ ] **AC-006:** present_backtest_list() uses _format_backtest_summary()
- [ ] **AC-007:** present_performance_summary() delegates to analyzer
- [ ] **AC-008:** present_comparison() delegates to analyzer
- [ ] **AC-009:** present_error() returns dict with 'status'='error'
- [ ] **AC-010:** _format_backtest() includes results metrics
- [ ] **AC-011:** _format_backtest_summary() includes summary fields
- [ ] **AC-012:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Backtest Presenter Implementation):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Humble Object pattern | Clean Architecture | Thin presenters, delegate to use cases | ✅ OK - Delegates to analyzer |
| Interface implementation | DDD (DIP) | Implements BacktestPresenter | ✅ OK - BacktestPresenterImpl(BacktestPresenter) |
| Dependency injection | DDD (DIP) | Constructor injection | ✅ OK - __init__() |
| Presentation layer | Clean Architecture | No business logic | ✅ OK - Only formatting |
| Error handling | Clean code | Return error dict, never raise | ✅ OK - present_error() |
| ISO format dates | JSON standard | Dates as ISO strings | ✅ OK - isoformat() |
| Decimal to string | JSON standard | Decimals as strings | ✅ OK - str() conversion |
| Null safety | Clean code | Handle None values | ✅ OK - Conditional checks |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Clean Architecture for layer separation.

---

## Dependencies
- **External:** None (std lib only: logging, typing)
- **Internal:**
  - `app.application.interfaces.backtest_presenter.BacktestPresenter`
  - `app.application.use_cases.analyze_backtest_results_use_case.AnalyzeBacktestResultsUseCase`
  - `app.domain.entities.backtest.Backtest`
  - `app.domain.repositories.backtest_repository.BacktestRepository`

---

## Required Tests
- **test_backtest_presenter_impl.py:**
  - `test_init_injects_dependencies()` - Stores repository and analyzer
  - `test_present_backtest_result_found()` - Returns formatted dict
  - `test_present_backtest_result_not_found()` - Returns error dict
  - `test_present_backtest_list_applies_pagination()` - Uses limit/offset
  - `test_present_backtest_list_formats_summary()` - Uses _format_backtest_summary
  - `test_present_performance_summary_success()` - Returns wrapped summary
  - `test_present_performance_summary_no_data()` - Returns error dict
  - `test_present_comparison_success()` - Returns wrapped comparison
  - `test_present_comparison_failure()` - Returns error dict
  - `test_present_error_format()` - Returns dict with status='error'
  - `test_format_backtest_includes_results()` - Includes all result fields
  - `test_format_backtest_handles_none_result()` - Handles missing result
  - `test_format_backtest_summary_includes_metrics()` - Includes summary fields
  - `test_format_dates_as_iso()` - Uses isoformat() for dates
  - `test_format_decimals_as_strings()` - Converts decimals to strings

---

## Notes
- **Critical:** This is infrastructure/presentation code - no business logic
- **Humble Object Pattern:**
  - Keep presenters thin and simple (<100 lines ideally)
  - Delegate all business logic to use cases
  - Only format data for UI consumption
  - Makes UI layer testable
- **Interface Implementation:**
  - Implements all 5 methods from BacktestPresenter
  - Follows contract exactly
  - Returns Dict[str, Any] for JSON serialization
- **Formatting Conventions:**
  - Dates: ISO format strings (`.isoformat()`)
  - Decimals: String representation (`.str()`)
  - Null values: Conditional checks, returns None
  - Status: 'success' or 'error'
- **Error Handling:**
  - Never raises exceptions to UI
  - Returns error dict with 'status': 'error'
  - Includes descriptive error message
  - UI can handle uniformly
- **Dependency Injection:**
  - Repository injected for data access
  - Analyzer injected for business logic
  - Follows Dependency Inversion Principle
- **Production Rule:** Keep presenter implementations trivial - only formatting, no logic

---

**File Reference:** `app/infrastructure/external/backtest_presenter_impl.py`
**Last Audited:** 2026-02-01
