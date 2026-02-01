# awesome_quant_integrator.py

## Purpose
Integration module for AWESOME-QUANT libraries (quantstats, empyrical, pyfolio) providing comprehensive financial metrics with fallback implementations.

---

## Type Definitions / Data Classes

### AwesomeQuantIntegrator Class
```python
class AwesomeQuantIntegrator:
    risk_free_rate: float  # REQUIRED - Risk-free rate for Sharpe/Sortino calculations (default: 0.02)
```

**Validation Rules:**
- `risk_free_rate` must be non-negative
- Module-level flags track library availability: `QUANTSTATS_AVAILABLE`, `EMPYRICAL_AVAILABLE`, `PYFOLIO_AVAILABLE`

---

## Function Signatures (Contracts)

### `calculate_quantstats_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series of returns; benchmark_returns same length if provided
**Post:** Returns dict with 20+ metrics (sharpe, sortino, calmar, drawdowns, etc.) or empty dict on error
**Raises:** ValueError, TypeError, KeyError, AttributeError (logged, returns {})
**Retry:** No
**Side Effects:** Logs metrics count; uses fallback if quantstats unavailable

### `calculate_empyrical_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with 16+ empyrical metrics or empty dict on error
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError (logged, returns {})
**Retry:** No
**Side Effects:** Logs metrics count; uses fallback if empyrical unavailable

### `calculate_pyfolio_metrics(returns: pd.Series, positions: Optional[pd.DataFrame] = None, transactions: Optional[pd.DataFrame] = None) -> Dict[str, Any]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with basic metrics (no pyfolio dependency) or empty dict on error
**Raises:** ValueError, TypeError, KeyError, AttributeError (logged, returns {})
**Retry:** No
**Side Effects:** Always calculates (no pyfolio import check)

### `calculate_all_awesome_quant_metrics(...) -> Dict[str, Dict[str, float]]`
**Pre:** returns is non-empty Series
**Post:** Returns nested dict with keys "quantstats", "empyrical", "pyfolio"
**Raises:** Exceptions from individual methods (logged)
**Retry:** No
**Side Effects:** Logs total metrics count

### `get_unified_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns unified metrics dict (priority: quantstats > empyrical > pyfolio)
**Raises:** Exceptions from individual methods (logged)
**Retry:** No
**Side Effects:** Logs unified metrics count

### `is_available(library: str) -> bool`
**Pre:** library is "quantstats", "empyrical", or "pyfolio"
**Post:** Returns True if library imported successfully
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_fallback_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns 25+ numpy/scipy calculated metrics or empty dict on error
**Raises:** ValueError, TypeError, KeyError, AttributeError (logged, returns {})
**Retry:** No
**Side Effects:** Comprehensive fallback when AWESOME-QUANT libraries unavailable

---

## Acceptance Criteria
- [ ] All library imports wrapped in try/except with availability flags
- [ ] Fallback implementation provides 25+ metrics when libraries unavailable
- [ ] All metric calculation functions return empty dict on error (not None)
- [ ] Warning logged when no AWESOME-QUANT libraries available
- [ ] Type hints present on all public methods
- [ ] All functions handle empty returns Series gracefully

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage on all functions | ✅ OK - All methods have type hints |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK - All error handlers use exc_info=True |
| LOG-005 | 09-logging-observability.md | No sensitive data in logs | ✅ OK - Only metric values logged |
| CC-001 | 05-architecture.md | Descriptive names | ⚠️ NOT APPLIED - Some generic names like `metrics` |
| TST-005 | 06-testing.md | Coverage > 80% | ❌ GAP - No test file found |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** quantstats (optional), empyrical (optional), pyfolio (optional), numpy, pandas
- **Internal:** None (standalone metrics module)

---

## Required Tests
- **tests/unit/backtesting/test_awesome_quant_integrator.py:**
  - Test quantstats metrics calculation with/without library
  - Test empyrical metrics calculation with/without library
  - Test pyfolio metrics calculation
  - Test fallback metrics when no libraries available
  - Test unified metrics merging logic
  - Test library availability checks
  - Test error handling (empty returns, NaN values)
  - Test benchmark_returns parameter handling

---

## Notes
- **Critical Design:** Module provides graceful degradation - works even if all AWESOME-QUANT libraries missing
- **Performance Note:** Fallback implementation uses pure numpy/pandas for basic metrics
