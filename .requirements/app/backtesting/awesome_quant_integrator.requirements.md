# awesome_quant_integrator.py

## Purpose
Integrates AWESOME-QUANT libraries (quantstats, empyrical, pyfolio) for advanced financial metrics with graceful fallback to numpy/scipy implementations when libraries are unavailable.

---

## Type Definitions / Data Classes

### AwesomeQuantIntegrator Class
```python
class AwesomeQuantIntegrator:
    risk_free_rate: float                    # REQUIRED - Risk-free rate for calculations (default: 2%)
```

**Validation Rules:**
- `risk_free_rate` must be positive (default: 0.02 for 2%)
- All external libraries are optional (quantstats, empyrical, pyfolio)

---

## Function Signatures (Contracts)

### `__init__(risk_free_rate: float = 0.02) -> None`
**Pre:** risk_free_rate >= 0
**Post:** Integrator initialized with risk-free rate
**Raises:** None
**Retry:** ❌ No
**Side Effects:** Logs which AWESOME-QUANT libraries are available

### `calculate_quantstats_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with quantstats-derived metrics (sharpe, sortino, calmar, etc.)
**Raises:** None (returns empty dict on error, logs error)
**Retry:** ❌ No
**Side Effects:** None (pure calculation)

### `calculate_empyrical_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with empyrical-derived metrics (omega_ratio, skewness, kurtosis, etc.)
**Raises:** None (returns empty dict on error, logs error)
**Retry:** ❌ No
**Side Effects:** None (pure calculation)

### `calculate_pyfolio_metrics(returns: pd.Series, positions: Optional[pd.DataFrame] = None, transactions: Optional[pd.DataFrame] = None) -> Dict[str, Any]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with pyfolio-derived metrics
**Raises:** None (returns empty dict on error, logs error)
**Retry:** ❌ No
**Side Effects:** None (pure calculation)

### `calculate_all_awesome_quant_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None, positions: Optional[pd.DataFrame] = None, transactions: Optional[pd.DataFrame] = None) -> Dict[str, Dict[str, float]]`
**Pre:** returns is non-empty Series
**Post:** Returns nested dict with metrics from all available libraries
**Raises:** None (returns partial results on error)
**Retry:** ❌ No
**Side Effects:** None (aggregates results)

### `get_unified_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns unified dict preferring quantstats > empyrical > pyfolio
**Raises:** None (returns partial results on error)
**Retry:** ❌ No
**Side Effects:** None (consolidates metrics)

### `is_available(library: str) -> bool`
**Pre:** library is one of: "quantstats", "empyrical", "pyfolio"
**Post:** Returns True if library is installed and importable
**Raises:** None (returns False for unknown library)
**Retry:** ❌ No
**Side Effects:** None (checks module availability)

### `get_available_libraries() -> list`
**Pre:** None
**Post:** Returns list of available library names
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `_calculate_fallback_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]`
**Pre:** returns is non-empty Series
**Post:** Returns dict with numpy/scipy-calculated metrics
**Raises:** None (returns empty dict on error)
**Retry:** ❌ No
**Side Effects:** None (fallback implementation)

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] No hardcoded secrets or sensitive data (SEC-001)
- [ ] Graceful fallback when AWESOME-QUANT libraries unavailable
- [ ] quantstats unavailable triggers fallback with warning log
- [ ] empyrical unavailable triggers fallback with warning log
- [ ] pyfolio unavailable triggers fallback with warning log
- [ ] Fallback implementation provides all core metrics (sharpe, sortino, calmar, etc.)
- [ ] Risk-free rate used in all ratio calculations
- [ ] Benchmark comparison only when benchmark_returns provided and same length
- [ ] All calculations handle division by zero (e.g., avg_loss <= 0, volatility <= 0)
- [ ] Omega ratio returns 'inf' when gains > 0 and losses == 0
- [ ] Metric dictionaries use float values (not numpy types)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK |
| TYP-003 | BASE_RULES.md | No Any without justification | ❌ GAP - Uses `Dict[str, Any]` in return |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK |
| TRD-007 | BASE_RULES.md | TRADING_DAYS constant documented | ❌ GAP - Uses 252 without constant |
| RSK-001 | BASE_RULES.md | VaR calculation included | ✅ OK - var_95, cvar_95 in fallback |

**GAP Violations Found:**

1. **TYP-003** (P1 - High): Uses `Any` type in return value
   - **Location**: Line 209: `def calculate_pyfolio_metrics(...) -> Dict[str, Any]`
   - **Fix**: Should be `Dict[str, float]` since all values are floats
   ```python
   def calculate_pyfolio_metrics(...) -> Dict[str, float]:
   ```

2. **TRD-007** (P2 - Medium): Magic number 252 for trading days not documented
   - **Location**: Lines 167, 232, 238, 399, 416, 425, 433
   - **Issue**: Uses 252 for trading days per year without constant
   - **Fix**: Define constant at top of file:
   ```python
   TRADING_DAYS_PER_YEAR = 252  # US market trading days
   ```

3. **Missing Validation** (P1): No validation for returns Series emptiness
   - **Location**: All calculate_* methods
   - **Issue**: Could receive empty Series causing division by zero
   - **Fix**: Add validation:
   ```python
   if len(returns) == 0:
       logger.warning("Empty returns series")
       return {}
   ```

4. **Infinite Return Value** (P2): Omega ratio can return float('inf')
   - **Location**: Line 449: `metrics["omega_ratio"] = float('inf') if gains.sum() > 0 else 0.0`
   - **Issue**: Infinity can cause serialization issues
   - **Fix**: Use large finite value:
   ```python
   metrics["omega_ratio"] = 999.99 if gains.sum() > 0 and losses.sum() == 0 else gains.sum() / losses.sum()
   ```

---

## Dependencies
- **External:**
  - **Required:** numpy, pandas, logging, typing
  - **Optional:** quantstats (QUANTSTATS_AVAILABLE flag), empyrical (EMPYRICAL_AVAILABLE flag), pyfolio (PYFOLIO_AVAILABLE flag)
- **Internal:** None (standalone metrics module)

---

## Required Tests
- **tests/unit/backtesting/test_awesome_quant_integrator.py:**
  - Test initialization with default risk-free rate
  - Test initialization with custom risk-free rate
  - Test quantstats metrics calculation when available
  - Test quantstats fallback when unavailable
  - Test empyrical metrics calculation when available
  - Test empyrical fallback when unavailable
  - Test pyfolio metrics calculation when available
  - Test pyfolio fallback when unavailable
  - Test unified metrics prefers quantstats > empyrical > pyfolio
  - Test is_available for all three libraries
  - Test get_available_libraries returns correct list
  - Test fallback metrics calculation with valid data
  - Test fallback metrics handles empty returns
  - Test fallback metrics handles division by zero (zero volatility)
  - Test fallback metrics handles zero losses (omega ratio)
  - Test benchmark comparison with matching lengths
  - Test benchmark comparison with mismatched lengths (should skip)
  - Test all metrics return float (not numpy types)

---

## Notes
- **Optional Dependencies**: All three AWESOME-QUANT libraries are optional
- **Fallback Implementation**: Comprehensive numpy/scipy fallback when libraries unavailable
- **Risk-Free Rate**: Default 2% (0.02), used in Sharpe/Sortino calculations
- **Trading Days**: Uses 252 for US market (should be documented as constant)
- **Metric Priority**: get_unified_metrics prefers quantstats > empyrical > pyfolio
- **Availability Flags**: QUANTSTATS_AVAILABLE, EMPYRICAL_AVAILABLE, PYFOLIO_AVAILABLE for testing
- **Infinite Values**: Omega ratio can return float('inf') which may cause JSON serialization issues
