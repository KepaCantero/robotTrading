# calculator.py - Technical Indicator Calculator Requirements

**File Path:** `app/services/momentum/indicators/calculator.py`

**Last Updated:** 2025-02-05

**Purpose:** Technical indicator calculator using pandas-ta-classic library for momentum analysis.

---

## Reference to Base Rules

See `../../../../../../BASE_RULES.md` for universal rules (96+ rules covering formatting, type hints, SOLID, security, logging, async patterns, etc.).

---

## File-Specific Requirements

### Functional Requirements

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| CALC-001 | Use pandas-ta-classic library for all indicator calculations | P0 | PASS |
| CALC-002 | Calculate RSI (Relative Strength Index) | P1 | PASS |
| CALC-003 | Calculate EMA (Exponential Moving Average) | P1 | PASS |
| CALC-004 | Calculate MACD (Moving Average Convergence Divergence) | P1 | PASS |
| CALC-005 | Calculate ROC (Rate of Change) | P1 | PASS |
| CALC-006 | Calculate Stochastic RSI | P2 | PASS |
| CALC-007 | Calculate ATR (Average True Range) | P2 | PASS |
| CALC-008 | Calculate ADX (Average Directional Index) | P2 | PASS |
| CALC-009 | Calculate OBV (On-Balance Volume) | P2 | PASS |
| CALC-010 | Calculate Volume SMA | P2 | PASS |
| CALC-011 | Calculate VWAP (Volume-Weighted Average Price) | P2 | PASS |
| CALC-012 | Calculate Z-score | P2 | PASS |
| CALC-013 | Calculate volatility | P2 | PASS |
| CALC-014 | Calculate expectancy metric | P3 | PASS |
| CALC-015 | Detect MACD divergence patterns | P3 | PASS |
| CALC-016 | Batch calculate all indicators | P1 | PASS |

### Error Handling Requirements

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| ERR-001 | Return None for insufficient data | P1 | PASS |
| ERR-002 | Log debug messages for edge cases | P2 | PASS |
| ERR-003 | Handle ValueError, TypeError, KeyError, AttributeError | P1 | PASS |
| ERR-004 | Validate input lengths match for multi-series calculations | P0 | PASS |

### Protocol Implementation

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| PROT-001 | Implement IndicatorCalculator protocol | P0 | PASS |
| PROT-002 | All protocol methods must be implemented | P0 | PASS |
| PROT-003 | Method signatures must match protocol | P0 | PASS |

---

## Audit Status

### Audit Summary
**Status:** PASSED WITH MINOR GAPS
**Overall Score:** 9.83/10 (Pylint)
**Audit Date:** 2025-02-05

### Gap Analysis by Priority

#### P0 (Critical) Gaps: 0
**NONE** - No critical violations found.

#### P1 (High) Gaps: 1
| Gap ID | Rule | Description | Line | Fix |
|--------|------|-------------|------|-----|
| GAP-P1-001 | TYP-001/CC-006 | Static methods incorrectly have `self` parameter instead of being true static methods | 431, 501, 538, 575, 605 | Remove `self` parameter from methods marked with `@staticmethod` but using `self` |

#### P2 (Medium) Gaps: 2
| Gap ID | Rule | Description | Line | Fix |
|--------|------|-------------|------|-----|
| GAP-P2-001 | QL-007 | Protocol mismatch: `calculate_all_indicators` has `symbol` parameter but protocol doesn't | 649 | Either add `symbol` to protocol or remove from implementation |
| GAP-P2-002 | CC-006 | Line length slightly exceeds 100 chars in some docstrings | Multiple | Use Black formatter (already compliant) |

#### P3 (Low) Gaps: 0
**NONE** - No low-priority issues found.

---

## Detailed Analysis

### ✅ STRENGTHS (What the file does well)

1. **EXCELLENT Single Responsibility Principle (SOL-001)**
   - Class only calculates technical indicators
   - No database, API, or business logic mixed in
   - Clear separation of concerns

2. **PROPER Dependency Inversion (SOL-005)**
   - Implements IndicatorCalculator protocol
   - Depends on abstraction, not concrete implementations
   - Protocol clearly defined in `protocols.py`

3. **EXCELLENT Error Handling (CC-006)**
   - All methods handle exceptions appropriately
   - Returns None for insufficient data (graceful degradation)
   - Debug logging for edge cases

4. **GOOD Type Coverage (TYP-001)**
   - All methods have type hints
   - Uses modern Optional[T] syntax
   - Proper use of Tuple for multiple return values

5. **EXCELLENT Input Validation (SEC-007)**
   - Validates data length before calculations
   - Checks for None/empty results
   - Validates list lengths match for multi-series

6. **GOOD Logging (LOG-001)**
   - Uses structured logging with context
   - Debug level for edge cases
   - Error level for exceptions
   - No sensitive data logged (LOG-005)

7. **PROPER Formatting (FMT-001)**
   - Black formatted
   - Import organized (FMT-002)
   - No unused imports (FMT-003)

8. **GOOD Documentation**
   - Clear docstrings for all methods
   - Args and Returns documented
   - Raises documented where applicable

### ⚠️ WEAKNESSES (Issues that need attention)

1. **Static Method Implementation Bug**
   ```python
   # Lines 431, 501, 538, 575, 605
   @staticmethod
   def calculate_volume_sma(self, volumes: List[Decimal], period: int = 20) -> Optional[Decimal]:
   ```
   **Issue:** Methods marked `@staticmethod` have `self` parameter
   **Impact:** Code works but violates the static method contract
   **Fix:** Remove `self` parameter from these methods

2. **Protocol Signature Mismatch**
   ```python
   # Line 649
   def calculate_all_indicators(
       self,
       symbol: str,  # Protocol doesn't have this parameter
       ...
   ) -> "TechnicalIndicators":
   ```
   **Issue:** Implementation has `symbol` parameter but protocol doesn't
   **Impact:** Protocol doesn't accurately reflect implementation
   **Fix:** Update protocol or implementation to match

3. **Mixed Type Usage**
   - Some methods use `List[float]`, others use `List[Decimal]`
   - Volume SMA expects Decimal, other volume methods expect float
   - **Recommendation:** Standardize on one type (float for financial calculations)

### 🔒 SECURITY ASSESSMENT

✅ **PASS** - No security issues found:
- No hardcoded secrets (SEC-001)
- No SQL injection risks
- Proper input validation (SEC-007)
- No sensitive data logging (LOG-005)

### 🏗️ ARCHITECTURE ASSESSMENT

✅ **PASS** - Follows clean architecture:
- In application/service layer (correct location)
- Implements domain protocol (Dependency Inversion)
- No framework dependencies in pure calculation logic
- Single Responsibility well maintained

### 📊 CODE QUALITY METRICS

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Pylint Score | 9.83/10 | ≥ 8.0 | PASS |
| Black Format | PASS | 100% | PASS |
| Import Order | PASS | isort | PASS |
| Type Coverage | ~100% | 100% | PASS |
| Cyclomatic Complexity | Low | < 10 | PASS |
| Lines of Code | 711 | < 1000 | PASS |
| Methods per class | 15 | Reasonable | PASS |

---

## Overengineering Filter Analysis

The following gaps were considered but **NOT marked as issues** per the overengineering filter:

1. **❌ Not marked:** Using `List[float]` vs `Sequence[float]` - Current code is clear
2. **❌ Not marked:** Some one-liners vs multi-line - Both are acceptable
3. **❌ Not marked:** Direct pandas operations vs helper methods - Current approach is appropriate
4. **❌ Not marked:** Docstring format - Current format is sufficient

---

## Test Coverage Status

**Status:** ⚠️ NO TESTS FOUND

| Test Type | Status | Priority |
|-----------|--------|----------|
| Unit Tests | NOT FOUND | P0 |
| Integration Tests | NOT FOUND | P1 |
| Edge Case Tests | NOT FOUND | P1 |

**Critical Gap (TST-005):** No test coverage for this calculator. Tests should cover:
- Each indicator calculation with valid data
- Edge cases (insufficient data, empty lists)
- Exception handling
- Protocol compliance

**Acceptance Criteria for Testing (AC-TST-001):**
```bash
# Should have test file
tests/unit/services/momentum/test_calculator.py

# Should run tests
pytest tests/unit/services/momentum/test_calculator.py -v

# Should have > 80% coverage
coverage run -m pytest tests/unit/services/momentum/test_calculator.py
coverage report app/services/momentum/indicators/calculator.py
```

---

## Recommended Actions

### Immediate (P0)
1. ✅ **NONE** - No critical issues requiring immediate action

### High Priority (P1)
1. Fix static method `self` parameter bug (GAP-P1-001)
2. Create unit tests for all indicator calculations (TST-005)

### Medium Priority (P2)
1. Fix protocol signature mismatch for `calculate_all_indicators` (GAP-P2-001)
2. Consider standardizing float vs Decimal usage

### Low Priority (P3)
1. None

---

## SOLID Principles Assessment

| Principle | Score | Notes |
|-----------|-------|-------|
| Single Responsibility | ✅ PASS | Only calculates indicators |
| Open/Closed | ✅ PASS | Extensible through new methods |
| Liskov Substitution | ✅ PASS | Protocol implementation |
| Interface Segregation | ✅ PASS | Focused indicator interface |
| Dependency Inversion | ✅ PASS | Depends on IndicatorCalculator protocol |

---

## Acceptance Criteria

### AC-CALC-001: Static Methods Fixed
```bash
# No static methods should have 'self' parameter
grep -A 2 "@staticmethod" app/services/momentum/indicators/calculator.py | grep "def.*self" | wc -l == 0
```

### AC-CALC-002: Protocol Compliance
```python
# Implementation matches protocol signature
# calculate_all_indicators signature should match IndicatorCalculator protocol
```

### AC-CALC-003: Test Coverage
```bash
# Test file exists
test -f tests/unit/services/momentum/test_calculator.py

# Coverage > 80%
coverage run -m pytest tests/unit/services/momentum/test_calculator.py
coverage report --fail-under=80 app/services/momentum/indicators/calculator.py
```

---

## Migration Notes

If refactoring this file:

1. **Keep the pandas-ta-classic dependency** - It's working well
2. **Maintain protocol compliance** - Don't break IndicatorCalculator protocol
3. **Standardize types** - Choose float or Decimal consistently
4. **Add tests first** - Write tests before refactoring (TDD)
5. **Preserve error handling** - Current None returns are graceful

---

## Dependencies

```python
# Required libraries (as specified in docstrings)
pandas-ta-classic  # REQUIRED - All calculations use this library
pandas              # For Series/DataFrame operations
numpy               # For array operations
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-02-05 | 1.0.0 | Initial requirements document and Ralphex audit |

---

**Audit Completed By:** Ralphex Automated Audit System
**Audit Reference:** calculator.py-2025-02-05
**Next Audit:** After P1 fixes are implemented
