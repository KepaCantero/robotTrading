# statsmodels_fallback.py Requirements

**File:** `app/core/statsmodels_fallback.py`  
**Purpose:** Fallback implementations for statsmodels functions using scipy/numpy  
**Audit Status:** NEEDS_AUDIT

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **statsmodels:** https://www.statsmodels.org/
- **Related Files:** All statistical analysis modules

---

## Purpose & Scope

This module provides fallback implementations when statsmodels is not available. It implements commonly used statistical tests using scipy, numpy, and pandas.

**Critical for Production:** Ensures system continues to work when statsmodels is not installed, but logs warnings to indicate reduced functionality.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods |
|-------|---------|---------|
| `OLS` | Ordinary Least Squares regression fallback | `fit()`, `summary()` |
| `AutoReg` | Autoregressive model fallback | `fit()`, `predict()` |
| `AutoRegResults` | Results class for AutoReg | `summary()`, `predict()` |
| `DecomposeResult` | Seasonal decomposition result | `plot()` |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `adfuller()` | Augmented Dickey-Fuller unit root test | `Tuple[float, float, int, Dict, float]` |
| `coint()` | Cointegration test | `Union[Tuple, object]` |
| `seasonal_decompose()` | Seasonal decomposition | `DecomposeResult` |
| `acorr_ljungbox()` | Ljung-Box test for autocorrelation | `Union[DataFrame, Dict]` |
| `pacf()` | Partial autocorrelation | `ndarray` |
| `grangercausalitytests()` | Granger causality tests | `Dict` |

---

## File-Specific Requirements

### FAL-001: Fallback Warning Logging
**Priority:** P1 (High - User awareness)

**Requirement:** All fallback implementations must log warnings indicating reduced functionality.

**Acceptance Criteria:**
```python
# When using fallback, warning must be logged
result = adfuller(data)
# Should log: "Using fallback implementation for adfuller"
assert USING_FALLBACK == True
```

**Check:** _log_fallback_warning() is called

---

### FAL-002: API Compatibility
**Priority:** P1 (High - Drop-in replacement)

**Requirement:** Fallback functions must have same signature as statsmodels equivalents.

**Acceptance Criteria:**
```python
# Can replace statsmodels with fallback
from statsmodels.tsa.stattools import adfuller as sm_adfuller
from app.core.statsmodels_fallback import adfuller as fb_adfuller

# Both accept same arguments
sm_result = sm_adfuller(x, maxlag=12, regression="c")
fb_result = fb_adfuller(x, maxlag=12, regression="c")
# Return types should match
```

**Check:** Function signatures match statsmodels

---

### FAL-003: ADF Test Accuracy
**Priority:** P2 (Medium - Statistical validity)

**Requirement:** ADF fallback should provide reasonable approximation of full statsmodels implementation.

**Acceptance Criteria:**
```python
# Fallback should detect stationarity
stationary = np.random.randn(100)  # Stationary
non_stationary = np.cumsum(np.random.randn(100))  # Random walk

stat1, p1, _, _, _ = adfuller(stationary)
stat2, p2, _, _, _ = adfuller(non_stationary)

assert p1 < 0.05  # Reject non-stationary for stationary data
assert p2 > 0.05  # Fail to reject for non-stationary data
```

**Check:** Statistical test validity

---

### FAL-004: Cointegration Test Validity
**Priority:** P2 (Medium - Statistical validity)

**Requirement:** Cointegration fallback should apply ADF test to residuals.

**Acceptance Criteria:**
```python
# Cointegrated series should be detected
y1 = np.cumsum(np.random.randn(100))
y2 = y1 + np.random.randn(100) * 0.1  # Cointegrated

t_stat, pvalue, _ = coint(y1, y2)
assert pvalue < 0.05  # Should detect cointegration
```

**Check:** Residual-based ADF test

---

### FAL-005: OLS Regression Accuracy
**Priority:** P2 (Medium - Statistical validity)

**Requirement:** OLS fallback should compute correct coefficients and statistics.

**Acceptance Criteria:**
```python
X = np.column_stack([np.random.randn(100), np.ones(100)])
y = 2 * X[:, 0] + 1 + np.random.randn(100) * 0.1

model = OLS(y, X)
result = model.fit()

assert abs(result.params[0] - 2) < 0.1  # Slope ~ 2
assert abs(result.params[1] - 1) < 0.1  # Intercept ~ 1
assert result.rsquared > 0.8  # Good fit
```

**Check:** OLS estimation accuracy

---

### FAL-006: Seasonal Decomposition Structure
**Priority:** P2 (Medium - API compatibility)

**Requirement:** Decomposition result must have same attributes as statsmodels.

**Acceptance Criteria:**
```python
result = seasonal_decompose(data, period=12)
assert hasattr(result, 'observed')
assert hasattr(result, 'trend')
assert hasattr(result, 'seasonal')
assert hasattr(result, 'resid')
assert hasattr(result, 'plot')
```

**Check:** Result object structure

---

### FAL-007: Ljung-Box Test Correctness
**Priority:** P2 (Medium - Statistical validity)

**Requirement:** Ljung-Box test should use correct formula and chi-square distribution.

**Acceptance Criteria:**
```python
# White noise should have no autocorrelation
white_noise = np.random.randn(200)
result = acorr_ljungbox(white_noise, lags=[10])

# p-value should be > 0.05 (fail to reject null)
assert result['lb_pvalue'].iloc[0] > 0.05
```

**Check:** Chi-square p-value calculation

---

### FAL-008: Error Handling
**Priority:** P1 (High - Robustness)

**Requirement:** All fallback functions must handle errors gracefully.

**Acceptance Criteria:**
```python
# Too short series should raise appropriate error
try:
    adfuller([1, 2, 3])  # Too short
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "too short" in str(e)
```

**Check:** Error messages are informative

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **LOG-004:** Error logging ✅
- **CC-006:** Explicit error handling ✅

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **LOG-003:** Appropriate log levels ✅ (warning for fallback)

### Medium Priority (P2)
- **QL-001:** Complexity reasonable ✅
- **CC-003:** KISS principle ✅ (simplified implementations)

---

## Known Issues & Technical Debt

### Issues
1. **Reduced accuracy** - Fallbacks are approximations, not full implementations
2. **Missing features** - Some statsmodels features not implemented
3. **Performance** - Fallbacks may be slower than native implementations

### Technical Debt
1. **Install statsmodels** - Should be required dependency
2. **Add more tests** - Statistical validity testing needed
3. **Document limitations** - Users need to know what's missing

---

## Testing Requirements

### Unit Tests
- [ ] Test ADF test detects stationarity
- [ ] Test cointegration test
- [ ] Test OLS regression accuracy
- [ ] Test seasonal decomposition
- [ ] Test Ljung-Box test
- [ ] Test error handling

### Integration Tests
- [ ] Test fallback behavior when statsmodels not installed
- [ ] Test API compatibility with statsmodels
- [ ] Test warning logging

---

## Security Considerations

1. **No injection attacks** ✅ (numpy arrays safe)
2. **No numeric overflow** ✅ (numpy handles this)
3. **Input validation** ✅ (length checks)

---

## Performance Considerations

1. **Fallback overhead** - May be slower than statsmodels
2. **Memory usage** - numpy arrays efficient ✅
3. **Computation complexity** - Similar to statsmodels

---

## Dependencies

**External:**
- `numpy` (required)
- `pandas` (required)
- `scipy` (required for chi2, f distributions)
- `logging` (stdlib)
- `warnings` (stdlib)
- `typing` (stdlib)

**Internal:**
- None (standalone module)

---

## Migration Notes

**From statsmodels:**
1. Install statsmodels: `pip install statsmodels`
2. Replace fallback imports with statsmodels imports
3. Test statistical accuracy

**To fallback:**
1. Use fallback imports when statsmodels not available
2. Monitor warnings for fallback usage
3. Document reduced functionality

---

## Changelog

### Version 1.0.0 (Initial)
- ADF test fallback
- Cointegration test fallback
- OLS regression fallback
- AutoReg model fallback
- Seasonal decomposition fallback
- Ljung-Box test fallback
- PACF fallback
- Granger causality test fallback

---

**Last Updated:** 2026-02-06  
**Next Review:** After statsmodels added to dependencies
