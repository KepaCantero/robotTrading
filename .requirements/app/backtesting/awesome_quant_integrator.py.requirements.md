# awesome_quant_integrator.py

## Purpose
Integrates AWESOME-QUANT libraries (quantstats, empyrical, pyfolio) for advanced financial metrics. Provides unified interface with fallback implementation when libraries unavailable.

---

## Type Definitions / Data Classes

### AwesomeQuantIntegrator Class
```python
class AwesomeQuantIntegrator:
    risk_free_rate: float                    # REQUIRED - Risk-free rate for calculations (default: 2%)
```

**Validation Rules:**
- `risk_free_rate` must be positive (typically 0.0 to 0.1)
- Used in Sharpe, Sortino, alpha, and omega calculations

### Library Availability Flags
```python
QUANTSTATS_AVAILABLE: bool = False          # Set at import based on quantstats availability
EMPYRICAL_AVAILABLE: bool = False           # Set at import based on empyrical availability
PYFOLIO_AVAILABLE: bool = False             # Set at import based on pyfolio availability
```

**Validation Rules:**
- Set via try/except at import time
- Graceful degradation if libraries unavailable

---

## Function Signatures (Contracts)

### `AwesomeQuantIntegrator.calculate_quantstats_metrics(returns, benchmark_returns) -> Dict[str, float]`
**Pre:** returns must be pandas Series of returns, benchmark_returns optional Series
**Post:** Returns dict with 20+ quantstats metrics (return, sharpe, sortino, calmar, drawdown, etc.)
**Raises:** Returns empty dict on errors
**Retry:** ❌ No
**Side Effects:** None (calculations only)

### `AwesomeQuantIntegrator.calculate_empyrical_metrics(returns, benchmark_returns) -> Dict[str, float]`
**Pre:** returns must be pandas Series, benchmark_returns optional
**Post:** Returns dict with empyrical metrics (total_return, sharpe, sortino, omega, etc.)
**Raises:** Returns empty dict on errors
**Retry:** ❌ No
**Side Effects:** None (calculations only)

### `AwesomeQuantIntegrator.calculate_pyfolio_metrics(returns, positions, transactions) -> Dict[str, Any]`
**Pre:** returns must be pandas Series, positions/transactions optional DataFrames
**Post:** Returns dict with pyfolio-style metrics
**Raises:** Returns empty dict on errors
**Retry:** ❌ No
**Side Effects:** None (calculations only)

### `AwesomeQuantIntegrator.calculate_all_awesome_quant_metrics(returns, benchmark_returns, positions, transactions) -> Dict[str, Dict[str, float]]`
**Pre:** returns must be valid pandas Series
**Post:** Returns dict with 'quantstats', 'empyrical', 'pyfolio' keys
**Raises:** None (graceful degradation)
**Retry:** ❌ No
**Side Effects:** None (calculations only)

### `AwesomeQuantIntegrator.get_unified_metrics(returns, benchmark_returns) -> Dict[str, float]`
**Pre:** returns must be valid pandas Series
**Post:** Returns unified dict with priority: quantstats > empyrical > pyfolio
**Raises:** None (returns empty dict on errors)
**Retry:** ❌ No
**Side Effects:** None (calculations only)

### `AwesomeQuantIntegrator.is_available(library) -> bool`
**Pre:** library must be one of ['quantstats', 'empyrical', 'pyfolio']
**Post:** Returns True if library is available
**Raises:** None (returns False for invalid library names)
**Retry:** ❌ No
**Side Effects:** None (lookup only)

### `AwesomeQuantIntegrator.get_available_libraries() -> list`
**Pre:** None
**Post:** Returns list of available library names
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (lookup only)

### `AwesomeQuantIntegrator._calculate_fallback_metrics(returns, benchmark_returns) -> Dict[str, float]`
**Pre:** returns must be pandas Series
**Post:** Returns dict with basic financial metrics calculated using numpy/pandas
**Raises:** Returns empty dict on errors
**Retry:** ❌ No
**Side Effects:** None (calculations only)

---

## Acceptance Criteria
- [ ] calculate_quantstats_metrics() returns 20+ metrics when quantstats available
- [ ] calculate_quantstats_metrics() uses fallback when quantstats unavailable
- [ ] calculate_empyrical_metrics() returns 15+ metrics when empyrical available
- [ ] calculate_empyrical_metrics() uses fallback when empyrical unavailable
- [ ] calculate_pyfolio_metrics() returns basic metrics (no pyfolio dependency required)
- [ ] calculate_all_awesome_quant_metrics() returns all three metric dicts
- [ ] get_unified_metrics() prioritizes quantstats over empyrical over pyfolio
- [ ] get_unified_metrics() doesn't duplicate metric keys
- [ ] is_available() correctly reports library availability
- [ ] get_available_libraries() returns list of available libraries
- [ ] _calculate_fallback_metrics() implements all key metrics with numpy/pandas
- [ ] _calculate_fallback_metrics() calculates Sharpe ratio correctly
- [ ] _calculate_fallback_metrics() calculates Sortino ratio correctly
- [ ] _calculate_fallback_metrics() calculates Calmar ratio correctly
- [ ] _calculate_fallback_metrics() calculates Omega ratio correctly
- [ ] All metric functions handle empty returns gracefully
- [ ] All metric functions handle division by zero gracefully
- [ ] Benchmark comparisons only performed when benchmark_returns provided
- [ ] All metric values are floats (not numpy types)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - Complete type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure component |
| PERF-001 | BASE_RULES.md | List comprehensions | ✅ OK - Used throughout |
| QL-001 | BASE_RULES.md | Complexity < 10 | ✅ OK - Methods are focused |
| TRD-001 | BASE_RULES.md | Trading-specific rules | ✅ OK - Financial metrics |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - **Optional (with fallback):** quantstats, empyrical, pyfolio
  - **Required:** pandas, numpy, logging, typing
- **Internal:** None

---

## Required Tests
- **tests/backtesting/test_awesome_quant_integrator.py:**
  - Test __init__() sets risk_free_rate correctly
  - Test __init__() logs available libraries
  - Test __init__() logs warning when no libraries available
  - Test calculate_quantstats_metrics() with quantstats available
  - Test calculate_quantstats_metrics() uses fallback when quantstats unavailable
  - Test calculate_quantstats_metrics() includes benchmark metrics when provided
  - Test calculate_empyrical_metrics() with empyrical available
  - Test calculate_empyrical_metrics() uses fallback when empyrical unavailable
  - Test calculate_pyfolio_metrics() returns correct metrics
  - Test calculate_all_awesome_quant_metrics() returns all three dicts
  - Test calculate_all_awesome_quant_metrics() logs total metric count
  - Test get_unified_metrics() prioritizes quantstats
  - Test get_unified_metrics() doesn't duplicate keys
  - Test get_unified_metrics() includes empyrical-only metrics
  - Test get_unified_metrics() includes pyfolio-only metrics
  - Test is_available() returns True for available libraries
  - Test is_available() returns False for unavailable libraries
  - Test get_available_libraries() returns correct list
  - Test _calculate_fallback_metrics() calculates total_return correctly
  - Test _calculate_fallback_metrics() calculates sharpe_ratio correctly
  - Test _calculate_fallback_metrics() calculates sortino_ratio correctly
  - Test _calculate_fallback_metrics() calculates calmar_ratio correctly
  - Test _calculate_fallback_metrics() calculates omega_ratio correctly
  - Test _calculate_fallback_metrics() calculates var_95 correctly
  - Test _calculate_fallback_metrics() calculates cvar_95 correctly
  - Test _calculate_fallback_metrics() handles division by zero
  - Test _calculate_fallback_metrics() calculates alpha/beta with benchmark
  - Test all functions handle empty returns gracefully
  - Test all metric values are Python floats (not numpy types)

---

## Notes
- AWESOME-QUANT libraries are optional (graceful degradation)
- Fallback implementation provides all key metrics using numpy/pandas
- Priority order for unified metrics: quantstats > empyrical > pyfolio
- Lines 220-221: Comment says pyfolio is REQUIRED but it's optional with fallback
- Fallback implementation is comprehensive (150+ lines)
- Uses annualization factor of 252 trading days (line 392, 416)
- Risk-free rate converted to daily: rf/252 (lines 231, 416)
- Downside volatility calculated from negative returns only
- Omega ratio threshold uses risk-free rate
- Benchmark metrics (alpha, beta, information_ratio) only when benchmark provided
- Covariance calculated with np.cov() for beta calculation
- All metric functions return empty dict on errors (fail-safe)
- Logging at INFO level for successful calculations
- Logging at ERROR level with exc_info=True for failures
- Type hints use Optional for benchmark_returns
- Comment on line 328 says "all REQUIRED" but libraries are actually optional
