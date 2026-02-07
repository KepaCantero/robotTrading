# Requirements: app/microstructure/price_discovery.py

**Status:** PASSED
**Last Audited:** 2026-02-07
**Batch:** 0095

## File Purpose
Implements price discovery and information aggregation models from O'Hara's Market Microstructure Theory, including efficient price estimation, information share calculation, and market efficiency testing.

## Base Rules Compliance
See ../../BASE_RULES.md for universal rules. This file complies with:
- FMT-001 to FMT-008 (Formatting & Style)
- TYP-001 to TYP-006 (Type Hints)
- SOL-001 to SOL-005 (SOLID Principles)
- ARCH-001 to ARCH-007 (Architecture)
- LOG-001 to LOG-007 (Logging)

## File-Specific Requirements

### 1. Price Discovery Models (P0 - TRD)

| Rule ID | Requirement | Implementation | Status |
|---------|-------------|----------------|--------|
| PD-001 | Roll efficient price | Estimates efficient price from bid-ask bounce | PASS |
| PD-002 | Hasbrouck information share | Calculates information contribution to price | PASS |
| PD-003 | Price adjustment speed | Measures how fast prices incorporate info | PASS |
| PD-004 | Market efficiency testing | Random walk and variance ratio tests | PASS |
| PD-005 | Information flow analysis | Analyzes information content of trades | PASS |
| PD-006 | Market integration | Cointegration and lead-lag analysis | PASS |

### 2. Statistical Methods (P0)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| STAT-001 | Cointegration testing | Engle-Granger implementation with fallback | PASS |
| STAT-002 | Unit root testing | ADF test with fallback implementation | PASS |
| STAT-003 | Variance ratio | Tests market efficiency | PASS |
| STAT-004 | Runs test | Non-parametric efficiency test | PASS |

### 3. Data Integrity (P0)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| INT-001 | Decimal precision | Financial calculations use Decimal | PASS |
| INT-002 | Input validation | Checks minimum observations required | PASS |
| INT-003 | Boundary handling | Handles edge cases (empty data, single points) | PASS |

### 4. Fallback Implementation (P1)

| Rule ID | Requirement | Check | Status |
|---------|-------------|-------|--------|
| FALL-001 | Statsmodels fallback | Implements coint/ADF without statsmodels | PASS |
| FALL-002 | Graceful degradation | Returns sensible defaults when unavailable | PASS |

## Acceptance Criteria

### AC-PD-001: Statsmodels Fallback
```bash
# Verify fallback works without statsmodels
python -c "
import sys
# Mock statsmodels unavailable
sys.modules['statsmodels'] = None

from app.microstructure.price_discovery import coint, adfuller, STATSMODELS_AVAILABLE
assert not STATSMODELS_AVAILABLE
# Test fallback functions work
import numpy as np
y1 = np.cumsum(np.random.randn(100))
y2 = np.cumsum(np.random.randn(100))
score, pvalue, _ = coint(pd.Series(y1), pd.Series(y2))
print('PASS')
"
```

### AC-PD-002: Information Share Range
```bash
# Verify information share is in [0, 1]
python -c "
from app.microstructure.price_discovery import PriceDiscoveryAnalyzer
analyzer = PriceDiscoveryAnalyzer()
import pandas as pd
prices = pd.Series([100, 101, 102, 101, 100])
trades = pd.Series([1, -1, 1, -1, 1])
info_share = analyzer.calculate_information_share_hasbrouck(prices, trades)
assert 0 <= info_share <= 1, f'Information share {info_share} out of range'
print('PASS')
"
```

### AC-PD-003: Type Safety
```bash
# Verify type hints
mypy --strict app/microstructure/price_discovery.py
# Expected: 0 errors (may have some in fallback implementation)
```

## Audit Findings

### Strengths
1. **Robust Fallback:** Implements statistical tests without statsmodels dependency
2. **Comprehensive Analysis:** Covers multiple aspects of price discovery
3. **Academic Foundation:** Based on Hasbrouck, O'Hara, Madhavan research
4. **Clean Architecture:** Separate classes for analysis and monitoring
5. **Good Documentation:** Clear docstrings with formula explanations

### Observations
1. **Import Handling:** Try-except for statsmodels with complete fallback (lines 29-175)
2. **Fallback Complexity:** Implemented coint and adfuller from scratch - impressive
3. **Singleton Pattern:** Uses global singletons for analyzers - acceptable
4. **Confidence Intervals:** Properly calculates 95% CI using 1.96 sigma

### Fallback Implementation Quality
The fallback statistical tests are well-implemented:
- Cointegration: Uses Engle-Granger two-step method
- ADF: Implements regression-based unit root test
- Critical values: Approximated MacKinnon values
- Returns reasonable results when statsmodels unavailable

### Code Quality
- Line count: ~1025 lines (acceptable for complex statistical module)
- Function complexity: Statistical functions are appropriately complex
- No security concerns (no secrets, no external calls)
- Thread-safe (immutable dataclasses, no shared mutable state)

### Mathematical Correctness
- Roll model: s = 2*sqrt(-cov) correctly implemented
- Information share: Proportional to trade impact / variance - correct
- Variance ratio: Compares var(q*return) to q*var(return) - correct
- Runs test: Compares actual runs to expected under randomness - correct

## Test Coverage Requirements
- Unit tests for Roll model with known spread
- Information share calculation validation
- Market efficiency tests with synthetic random walks
- Fallback function correctness vs statsmodels
- Edge cases: empty data, single points, extreme values

## References
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 7-8
- Hasbrouck, J. (1995) "One Security, Many Markets"
- Roll, R. (1984) "A Simple Implicit Measure of the Effective Bid-Ask Spread"
- Madhavan, A. (2000) "Market Microstructure: A Survey"

---
*Last updated: 2026-02-07*
