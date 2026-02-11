# ofi_calculator.py

## Purpose
Calculate Order Flow Imbalance (OFI) from order book snapshots to measure buy/sell pressure and predict short-term price movements.

---

## Type Definitions / Data Classes

### OFIResult Class (dataclass)
```python
@dataclass
class OFIResult:
    ofi: float                     # REQUIRED - Normalized OFI value [-1, 1]
    bid_volume: int                # REQUIRED - Total bid volume across all levels
    ask_volume: int                # REQUIRED - Total ask volume across all levels
    total_volume: int              # REQUIRED - Sum of bid + ask volume
    timestamp: datetime            # REQUIRED - Calculation timestamp
    is_valid: bool                 # REQUIRED - Validation status (volume/spread checks)
    reason: Optional[str]          # OPTIONAL - Validation failure reason if invalid
```

**Validation Rules:**
- `ofi` must be clamped to [-1, 1] for numerical stability
- `total_volume = bid_volume + ask_volume`
- `is_valid = False` when `total_volume < min_volume` or `spread_bps > max_spread_bps`

### OFICalculator Class
```python
class OFICalculator:
    config: OFIConfig                    # Configuration parameters
    _ofi_history: Deque[float]           # Rolling OFI history (maxlen=lookback_periods)
    _cofi_tracker: Optional[CumulativeOFI] # Cumulative OFI tracking instance
```

---

## Function Signatures (Contracts)

### `__init__(config: Optional[OFIConfig] = None) -> None`
**Pre:** config must be OFIConfig instance or None (uses defaults)
**Post:** Calculator initialized with config, empty OFI history
**Raises:** TypeError if config is invalid type
**Retry:** No
**Side Effects:** None

### `calculate_ofi(order_book: OrderBookSnapshot) -> OFIResult`
**Pre:** order_book must have bids and asks lists
**Post:** Returns OFIResult with normalized OFI [-1, 1]
**Raises:** None (returns invalid OFIResult on validation failure)
**Retry:** No
**Side Effects:** Appends OFI to _ofi_history deque

### `calculate_cumulative_ofi(ofi_history: List[float]) -> List[float]`
**Pre:** ofi_history must be list of floats in [-1, 1]
**Post:** Returns list of cumulative sums (same length as input)
**Raises:** None (returns [] if empty)
**Retry:** No
**Side Effects:** None

### `calculate_ofi_momentum(ofi_history: List[float], window: int = 10) -> float`
**Pre:** ofi_history length >= window * 2
**Post:** Returns momentum (recent_avg - previous_avg)
**Raises:** None (returns 0.0 if insufficient data)
**Retry:** No
**Side Effects:** None

### `calculate_smoothed_ofi(ofi_history: List[float], window: Optional[int] = None) -> List[float]`
**Pre:** ofi_history not empty
**Post:** Returns exponentially weighted moving average of OFI values
**Raises:** None (returns [] if empty)
**Retry:** No
**Side Effects:** None

### `calculate_ofi_statistics(ofi_history, returns_history, symbol, period_start, period_end) -> Optional[OFIStatistics]`
**Pre:** ofi_history length >= 5, returns_history matches ofi_history length if provided
**Post:** Returns OFIStatistics with comprehensive metrics
**Raises:** None (returns None if insufficient data)
**Retry:** No
**Side Effects:** None

### `get_cofi_tracker(symbol: str, start_time: datetime) -> CumulativeOFI`
**Pre:** symbol not empty, start_time is datetime
**Post:** Returns existing or new CumulativeOFI instance
**Raises:** None
**Retry:** No
**Side Effects:** Creates new CumulativeOFI if symbol changed or None

### `update_cofi(ofi_value: float, timestamp: datetime) -> float`
**Pre:** cofi_tracker initialized (call get_cofi_tracker first)
**Post:** Returns updated cumulative OFI value
**Raises:** Warning logged if tracker not initialized
**Retry:** No
**Side Effects:** Updates cofi_tracker state

---

## Acceptance Criteria
- [ ] OFI calculation normalized to [-1, 1] range
- [ ] Volume validation rejects OFI when total_volume < min_volume
- [ ] Spread validation rejects OFI when spread_bps > max_spread_bps
- [ ] Weighted OFI calculation uses distance-based weighting for top levels
- [ ] Cumulative OFI maintains running sum across updates
- [ ] Momentum calculation uses sliding window comparison
- [ ] Smoothed OFI uses exponential weighting (alpha = 2/(window+1))
- [ ] Statistics include mean, std, min, max, median, skewness, kurtosis
- [ ] Autocorrelation calculated at lag 1
- [ ] Predictive power computed as correlation with future returns

---


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit v2.0) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 2 P3 |
| **Notes** | All critical rules verified. scipy.signal import may be unused (P3). See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix positive semidefinite | ✅ OK - Not applicable (no covariance) |
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - Validation in calculate_ofi |
| TRD-005 | BASE_RULES | Price validation | ✅ FIXED - Added _validate_price() with negative/zero/NaN checks |
| ARCH-001 | BASE_RULES | Layered architecture dependencies inward | ✅ OK - Only imports from models |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Uses validation returns, logs exceptions |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses logger with extra dict |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ✅ OK - exc_info=True in exception handler |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Validates OrderBookSnapshot |
| QL-002 | BASE_RULES | No dead code | ⚠️ PARTIAL - scipy.signal imported but may be unused |
| PERF-001 | BASE_RULES | Use numpy for operations | ✅ OK - Uses np.mean, np.std, np.corrcoef |

---

## Dependencies
- **External:** numpy (np), scipy.signal, decimal (Decimal), datetime, dataclasses, typing, collections
- **Internal:** app.market_microstructure.ofi.models (OFIConfig, CumulativeOFI, OFIStatistics, OrderBookSnapshot)

---

## Required Tests
- **tests/market_microstructure/ofi/test_ofi_calculator.py:**
  - Test OFI calculation with valid order book (success path)
  - Test OFI validation failure on low volume (error path)
  - Test OFI validation failure on wide spread (error path)
  - Test weighted OFI vs simple OFI comparison
  - Test cumulative OFI accumulation accuracy
  - Test OFI momentum detection (positive/negative/zero)
  - Test smoothed OFI exponential weighting
  - Test OFI statistics calculation (all metrics)
  - Test autocorrelation at various lags
  - Test predictive power calculation with returns
  - Test edge cases: empty order book, zero volume, single level

---

## Notes
OFI values > 0 indicate buying pressure, < 0 indicate selling pressure. Uses methodology from Cont & Kukanov (2017). Volume-weighted OFI gives more importance to orders closer to mid price.
