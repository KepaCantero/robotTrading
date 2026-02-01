# analyze_backtest_results_use_case.py

## Purpose
Application layer use case for analyzing backtest results. Provides performance metrics, risk assessment, and comparison capabilities for backtest results.

---

## Type Definitions / Data Classes

This file uses domain entities from the backtest module. No new data classes are defined in this file.

---

## Function Signatures (Contracts)

### `__init__(backtest_repository: BacktestRepository)`
**Pre:** `backtest_repository` must be non-null instance
**Post:** Use case initialized with repository dependency
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** Stores repository as private attribute

### `get_performance_summary(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** `backtest_id` non-empty string
**Post:** Returns performance summary dict or None if not found
**Raises:** No exceptions (handles missing backtest gracefully)
**Retry:** No
**Side Effects:** No state changes

**Returns:**
```python
{
    'backtest_id': str,
    'total_return': str,  # Decimal as string
    'sharpe_ratio': Optional[str],
    'max_drawdown': Optional[str],
    'win_rate': Optional[str],
    'total_trades': int,
    'is_profitable': bool,
}
```

### `compare_backtests(backtest_ids: List[str]) -> Optional[Dict[str, Any]]`
**Pre:** `backtest_ids` non-empty list
**Post:** Returns comparison dict or None if no backtests found
**Raises:** No exceptions (handles missing backtests gracefully)
**Retry:** No
**Side Effects:** No state changes

**Returns:**
```python
{
    'backtest_count': int,
    'avg_return': str,
    'best_return': str,
    'worst_return': str,
    'avg_sharpe': Optional[str],
    'avg_drawdown': Optional[str],
    'best_backtest': str,  # ID of best performing
}
```

### `get_risk_metrics(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** `backtest_id` non-empty string
**Post:** Returns risk metrics dict or None if not found
**Raises:** No exceptions (handles missing backtest gracefully)
**Retry:** No
**Side Effects:** No state changes

**Returns:**
```python
{
    'backtest_id': str,
    'max_drawdown': Optional[str],
    'volatility': Optional[str],
    'var_95': Optional[str],
    'sortino_ratio': Optional[str],
    'calmar_ratio': Optional[str],
    'tail_ratio': Optional[str],
}
```

### `assess_acceptable_risk(backtest_id: str, max_drawdown_threshold: Decimal = Decimal('0.20')) -> Optional[Dict[str, Any]]`
**Pre:** `backtest_id` non-empty string, `max_drawdown_threshold` between 0 and 1
**Post:** Returns risk assessment dict or None if not found
**Raises:** No exceptions (handles missing backtest gracefully)
**Retry:** No
**Side Effects:** No state changes

**Returns:**
```python
{
    'backtest_id': str,
    'is_acceptable': bool,
    'max_drawdown': Optional[str],
    'threshold': str,
    'is_profitable': bool,
    'sharpe_ratio': Optional[str],
}
```

---

## Acceptance Criteria
- [ ] get_performance_summary() returns None for non-existent backtest
- [ ] get_performance_summary() returns dict with all fields for valid backtest
- [ ] get_performance_summary() converts Decimal values to strings
- [ ] get_performance_summary() handles None optional metrics
- [ ] compare_backtests() returns None if no backtests found
- [ ] compare_backtests() includes only backtests with results
- [ ] compare_backtests() calculates average return correctly
- [ ] compare_backtests() identifies best and worst returns
- [ ] compare_backtests() calculates average Sharpe if available
- [ ] compare_backtests() identifies best_backtest ID correctly
- [ ] get_risk_metrics() returns None for non-existent backtest
- [ ] get_risk_metrics() returns dict with all risk fields
- [ ] assess_acceptable_risk() uses default 20% drawdown threshold
- [ ] assess_acceptable_risk() calls has_acceptable_drawdown() on result
- [ ] assess_acceptable_risk() includes threshold in return dict
- [ ] All methods handle missing backtest results gracefully

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - Analysis only | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depends on repository abstraction | ✅ OK |
| ARCH-001 | BASE_RULES.md | Layered architecture - Application layer use case | ✅ OK |
| DP-004 | BASE_RULES.md | Dependency injection - Repository injected | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax | ⚠️ PARTIAL - Uses `Dict` and `List` instead of `dict` and `list` |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Handles None gracefully |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `logging`, `decimal.Decimal`, `typing`
- **Internal:**
  - `app.domain.repositories.backtest_repository` (BacktestRepository)

---

## Required Tests
- **test_analyze_backtest_results_use_case.py:**
  - Test get_performance_summary() returns None for non-existent backtest
  - Test get_performance_summary() returns summary for valid backtest
  - Test get_performance_summary() includes all required fields
  - Test get_performance_summary() converts Decimal to string
  - Test compare_backtests() returns None when no backtests found
  - Test compare_backtests() compares multiple backtests correctly
  - Test compare_backtests() calculates averages correctly
  - Test compare_backtests() identifies best performing backtest
  - Test compare_backtests() handles missing Sharpe ratios
  - Test get_risk_metrics() returns None for non-existent backtest
  - Test get_risk_metrics() returns all risk metrics
  - Test get_risk_metrics() handles None values
  - Test assess_acceptable_risk() uses default threshold
  - Test assess_acceptable_risk() uses custom threshold
  - Test assess_acceptable_risk() checks drawdown acceptance
  - Test assess_acceptable_risk() returns None for non-existent backtest

---

## Notes
**Analysis Focus:** This use case is focused on read-only operations for analyzing backtest results. It does not modify any state, making it safe for reporting and dashboard interfaces.

**Decimal Serialization:** All Decimal values are converted to strings in the returned dictionaries to ensure JSON serializability for API responses.

**Graceful Degradation:** All methods return None when backtests are not found, allowing calling code to handle missing data gracefully without exceptions.

**Comparison Logic:** The `compare_backtests()` method only includes backtests that have results (backtest.result is not None). Backtests without results are silently excluded from the comparison.
