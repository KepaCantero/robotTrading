# analyze_backtest_results_use_case.py

## Purpose
Analyze Backtest Results Use Case - Application layer orchestrator for analyzing backtest results, providing performance summaries, comparisons, and risk assessments.

---

## Type Definitions / Data Classes

No custom data classes defined in this file (uses domain entities).

**Domain Dependencies:**
- `Backtest` entity
- `BacktestResultValue` value object
- `BacktestRepository` interface

---

## Function Signatures (Contracts)

### `AnalyzeBacktestResultsUseCase.__init__(backtest_repository: BacktestRepository) -> None`
**Pre:** backtest_repository is valid BacktestRepository
**Post:** Use case initialized with repository
**Raises:** None
**Retry:** No
**Side Effects:** Stores repository reference

### `get_performance_summary(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns performance summary dict or None if not found/no results
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

**Output Format:**
```python
{
    'backtest_id': str,
    'total_return': str,           # Decimal as string
    'sharpe_ratio': Optional[str],
    'max_drawdown': Optional[str],
    'win_rate': Optional[str],
    'total_trades': int,
    'is_profitable': bool
}
```

### `compare_backtests(backtest_ids: List[str]) -> Optional[Dict[str, Any]]`
**Pre:** backtest_ids is non-empty list
**Post:** Returns comparison dict or None if no valid backtests found
**Raises:** None
**Retry:** No
**Side Effects:** None (queries via repository)

**Output Format:**
```python
{
    'backtest_count': int,
    'avg_return': str,
    'best_return': str,
    'worst_return': str,
    'avg_sharpe': Optional[str],
    'avg_drawdown': Optional[str],
    'best_backtest': str           # backtest_id with highest return
}
```

**Calculation:** Skips backtests without results; computes averages across available metrics

### `get_risk_metrics(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns risk metrics dict or None if not found/no results
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

**Output Format:**
```python
{
    'backtest_id': str,
    'max_drawdown': Optional[str],
    'volatility': Optional[str],
    'var_95': Optional[str],           # Value at Risk 95%
    'sortino_ratio': Optional[str],
    'calmar_ratio': Optional[str],
    'tail_ratio': Optional[str]
}
```

### `assess_acceptable_risk(
    backtest_id: str,
    max_drawdown_threshold: Decimal = Decimal('0.20')
) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty; max_drawdown_threshold in (0, 1)
**Post:** Returns risk assessment dict or None if not found/no results
**Raises:** None
**Retry:** No
**Side Effects:** None (query via repository)

**Output Format:**
```python
{
    'backtest_id': str,
    'is_acceptable': bool,             # result.has_acceptable_drawdown(threshold)
    'max_drawdown': Optional[str],
    'threshold': str,
    'is_profitable': bool,
    'sharpe_ratio': Optional[str]
}
```

**Default:** max_drawdown_threshold = 20% (0.20)

---

## Acceptance Criteria
- [ ] **AC-001:** get_performance_summary() returns None if backtest not found
- [ ] **AC-002:** get_performance_summary() returns None if backtest has no results
- [ ] **AC-003:** get_performance_summary() contains all 7 fields
- [ ] **AC-004:** compare_backtests() returns None if no valid backtests found
- [ ] **AC-005:** compare_backtests() skips backtests without results
- [ ] **AC-006:** compare_backtests() identifies best_backtest correctly
- [ ] **AC-007:** get_risk_metrics() returns 6 risk metrics
- [ ] **AC-008:** assess_acceptable_risk() uses default 20% threshold
- [ ] **AC-009:** assess_acceptable_risk() delegates to has_acceptable_drawdown()
- [ ] **AC-010:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Analyze Backtest Results Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Use case pattern | Clean Architecture | Application orchestrator | ✅ OK - AnalyzeBacktestResultsUseCase |
| Repository pattern | DDD (Evans) | Persistence abstraction | ✅ OK - BacktestRepository |
| Dependency injection | SOLID (DIP) | Repository injected | ✅ OK - __init__() |
| Read-only operations | Query pattern | No state mutations | ✅ OK - All methods read-only |
| Null safety | Clean code | Returns None on not found | ✅ OK - All query methods |
| Dictionary output | DTO pattern | Structured data transfer | ✅ OK - Dict[str, Any] returns |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Clean Architecture patterns.

---

## Dependencies
- **External:** `logging` (std), `decimal` (std), `typing` (std)
- **Internal:**
  - `app.domain.repositories.backtest_repository.BacktestRepository`

---

## Required Tests
- **test_analyze_backtest_results_use_case.py:**
  - `test_init()` - Initializes with repository
  - `test_get_performance_summary_found()` - Returns summary dict
  - `test_get_performance_summary_not_found()` - Returns None
  - `test_get_performance_summary_no_results()` - Returns None
  - `test_get_performance_summary_all_fields()` - 7 fields present
  - `test_compare_backtests_all_found()` - Returns comparison
  - `test_compare_backtests_partial_missing()` - Skips missing
  - `test_compare_backtests_none_found()` - Returns None
  - `test_compare_backtests_identifies_best()` - Correct best_backtest
  - `test_get_risk_metrics_found()` - Returns 6 metrics
  - `test_get_risk_metrics_not_found()` - Returns None
  - `test_assess_acceptable_risk_default_threshold()` - 20%
  - `test_assess_acceptable_risk_custom_threshold()` - Uses provided
  - `test_assess_acceptable_risk_delegates()` - Calls has_acceptable_drawdown()

---

## Notes
- **Critical:** AnalyzeBacktestResultsUseCase is a USE CASE (Clean Architecture application layer)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Use Case Pattern:** Read-only orchestrator for backtest result analysis
- **Repository Pattern:** Abstracts persistence via BacktestRepository interface
- **Query Methods:** All methods are read-only queries (no mutations)
- **Null Safety:** Returns None when backtest not found or has no results
- **Dictionary Output:** Returns Dict[str, Any] for flexible data transfer (DTO pattern)
- **Comparison Logic:** compare_backtests() identifies best performing backtest by total_return_pct
- **Risk Assessment:** assess_acceptable_risk() delegates to domain logic (has_acceptable_drawdown)
- **Metrics Included:**
  - Performance: total_return, sharpe_ratio, max_drawdown, win_rate, total_trades
  - Risk: volatility, var_95, sortino_ratio, calmar_ratio, tail_ratio
  - Comparison: avg/best/worst returns, best_backtest identification
- **Decimal to String Conversion:** All Decimal values converted to strings for JSON serialization

---

**File Reference:** `app/application/use_cases/analyze_backtest_results_use_case.py`
**Last Audited:** 2026-02-01
