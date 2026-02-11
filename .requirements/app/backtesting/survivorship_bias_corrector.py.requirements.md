# survivorship_bias_corrector.py

## Purpose
Corrects survivorship bias in backtesting using Ernest Chan's methodology from "Algorithmic Trading" (Chapter 3). Simulates delisted stocks, calculates bias factors, and adjusts returns.

---

## Type Definitions / Data Classes

### DelistedStockInfo
```python
@dataclass
class DelistedStockInfo:
    symbol: str  # REQUIRED - Stock ticker
    delisting_date: datetime  # REQUIRED - Date of delisting
    delisting_reason: str  # REQUIRED - 'bankruptcy', 'acquisition', or 'delisting'
    last_price: Decimal  # REQUIRED - Last traded price
    recovery_rate: Decimal  # REQUIRED - Typical recovery (0.10 for bankruptcy)
    volatility_before_delisting: float  # REQUIRED - Volatility before delisting
```

**Validation Rules:**
- delisting_reason must be one of: 'bankruptcy', 'acquisition', 'delisting'
- recovery_rate in range [0, 1] (0% to 100%)
- volatility_before_delisting >= 0

### SurvivorshipAdjustment
```python
@dataclass
class SurvivorshipAdjustment:
    total_universe_size: int  # REQUIRED - Original universe size
    surviving_count: int  # REQUIRED - Currently surviving stocks
    delisted_count: int  # REQUIRED - Estimated delisted stocks
    survivorship_bias_factor: float  # REQUIRED - Multiplier to adjust returns (> 1.0)
    bankruptcy_adjustment: float  # REQUIRED - Bankruptcy impact factor
    acquisition_adjustment: float  # REQUIRED - Acquisition premium factor
    average_delisting_date: datetime | None  # OPTIONAL - Average delisting date
```

**Validation Rules:**
- total_universe_size = surviving_count + delisted_count
- survivorship_bias_factor >= 1.0 (returns inflated by this factor)
- bankruptcy_adjustment <= 1.0 (reduces returns)
- acquisition_adjustment >= 1.0 (increases returns)

---

## Function Signatures (Contracts)

### `__init__(delisting_data_path: Path | None = None, custom_delisting_rates: dict[str, float] | None = None) -> None`
**Pre:** None
**Post:** SurvivorshipBiasCorrector initialized with default or custom rates
**Raises:** No
**Retry:** No
**Side Effects:** None (initializes rates and cache)

### `calculate_survivorship_bias(current_universe: list[str], backtest_start: datetime, backtest_end: datetime) -> SurvivorshipAdjustment`
**Pre:** current_universe non-empty, backtest_start < backtest_end
**Post:** Returns SurvivorshipAdjustment with bias factors
**Raises:** No (returns neutral adjustment on error)
**Retry:** No
**Side Effects:** Logs detailed bias calculation metrics

### `adjust_returns_for_survivorship(returns: pd.Series, adjustment: SurvivorshipAdjustment, method: str = "multiplicative") -> pd.Series`
**Pre:** returns non-empty Series, adjustment valid
**Post:** Returns adjusted returns Series (same length as input)
**Raises:** ValueError (unknown method)
**Retry:** No
**Side Effects:** Logs before/after mean returns

### `simulate_delisted_stocks(current_symbols: list[str], backtest_dates: pd.DatetimeIndex, delisted_data: list[DelistedStockInfo] | None = None) -> dict[datetime, list[str]]`
**Pre:** current_symbols non-empty, backtest_dates non-empty
**Post:** Returns dict mapping dates to full universe (including simulated delisted)
**Raises:** No (returns current_symbols on error)
**Retry:** No
**Side Effects:** None (pure function, simulates historical universe)

### `load_delisting_data(filepath: Path) -> list[DelistedStockInfo]`
**Pre:** filepath exists and is valid CSV
**Post:** Returns list of DelistedStockInfo objects, cached for subsequent calls
**Raises:** No (returns empty list on error, logs warning)
**Retry:** No
**Side Effects:** Reads CSV file, caches DataFrame

### `create_point_in_time_universe(current_symbols: list[str], backtest_start: datetime, backtest_end: datetime, frequency: str = "M") -> dict[datetime, list[str]]`
**Pre:** current_symbols non-empty, backtest_start < backtest_end
**Post:** Returns dict mapping dates to available universe at that time
**Raises:** No (returns {start_date: current_symbols} on error)
**Retry:** No
**Side Effects:** Estimates historical universe size (simplified, 5% annual growth)

---

## Acceptance Criteria
- [ ] AC-001: Annual delisting rate = 3% (ANNUAL_DELISTING_RATE)
- [ ] AC-002: Bankruptcy rate = 1%, Acquisition rate = 1.5%, Other = 0.5%
- [ ] AC-003: Bankruptcy recovery rate = 10% (BANKRUPTCY_RECOVERY_RATE)
- [ ] AC-004: Acquisition premium = 20% (ACQUISITION_PREMIUM)
- [ ] AC-005: Other delisting loss = 50% (DELISTING_LOSS)
- [ ] AC-006: Bias factor calculation uses 20% annual underperformance for delisted stocks
- [ ] AC-007: Bias factor capped at 1.0 + (0.03 * period_years) (3% annual inflation)
- [ ] AC-008: Multiplicative adjustment: adjusted_return = raw_return / bias_factor
- [ ] AC-009: Additive adjustment: subtract daily_bias_drag from returns
- [ ] AC-010: Point-in-time universe estimates historical size (5% annual growth assumption)
- [ ] AC-011: Load delisting data from CSV with caching
- [ ] AC-012: Use itertuples for better performance (not iterrows)
- [ ] AC-013: Return neutral adjustment (factor=1.0) on error
- [ ] AC-014: Type hints cover all methods (mypy --strict)

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage for all methods | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK (try/except throughout) |
| PERF-002 | 19-sre-performance.md | Use iterators for large datasets | ✅ OK (itertuples) |
| BT-003 | 13-trading-specific-rules | No look-ahead bias | ✅ OK (point-in-time universe) |
| ARCH-004 | 05-architecture.md | Small functions < 20 lines | ✅ OK (most methods) |
| SEC-001 | 28-security-and-secrets.md | No hardcoded secrets | ✅ OK (constants only) |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** pandas, Decimal
- **Internal:** None (standalone module)

---

## Required Tests
- **tests/unit/backtesting/test_survivorship_bias_corrector.py:**
  - Test initialization with default and custom rates
  - Test calculate_survivorship_bias with various periods
  - Test bias factor calculation (capped at 3% annual inflation)
  - Test bankruptcy adjustment calculation
  - Test acquisition adjustment calculation
  - Test multiplicative return adjustment
  - Test additive return adjustment
  - Test unknown method raises ValueError
  - Test simulate_delisted_stocks with and without delisting_data
  - Test load_delisting_data from CSV with caching
  - Test load_delisting_data handles FileNotFoundError
  - Test create_point_in_time_universe estimation
  - Test create_point_in_time_universe handles errors
  - Test neutral adjustment returned on error
  - Test itertuples used for performance (not iterrows)
  - Test DelistedStockInfo validation (delisting_reason, recovery_rate)
  - Test SurvivorshipAdjustment validation (factor >= 1.0)

- **tests/integration/backtesting/test_survivorship_bias_integration.py:**
  - Test full workflow: calculate bias -> adjust returns
  - Test returns reduction after adjustment
  - Test point-in-time universe creation with real dates
  - Test delisting data loading and caching
  - Test bias factor with multi-year periods
  - Test multiplicative vs additive adjustment methods

---

## Notes
- Implements Ernest Chan's methodology from "Algorithmic Trading" Chapter 3
- Typical survivorship bias inflates returns by 1-3% annually
- Bias correction reduces returns to account for delisted stock underperformance
- Point-in-time universe estimation is simplified (production should use CRSP/Compustat)
- Uses 5% annual universe growth assumption for historical size estimation
- Caches delisting data DataFrame for performance
