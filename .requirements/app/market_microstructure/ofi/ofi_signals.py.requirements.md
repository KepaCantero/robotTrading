# ofi_signals.py

## Purpose
Generate trading signals from Order Flow Imbalance with threshold-based, mean reversion, and momentum strategies.

---

## Type Definitions / Data Classes

### OFISignalGenerator Class
```python
class OFISignalGenerator:
    config: OFISignalConfig          # Signal configuration
    calculator: OFICalculator        # OFI calculator instance
    predictor: OFIPredictor          # OFI predictor instance
    buy_threshold: float             # Buy signal threshold
    sell_threshold: float            # Sell signal threshold (negative)
    confidence_scale: float          # Confidence scaling factor
    _recent_signals: List[datetime]   # Recent signal timestamps for rate limiting
```

---

## Function Signatures (Contracts)

### `__init__(config, calculator, predictor) -> None`
**Pre:** config is OFISignalConfig or None, calculator and predictor are instances or None
**Post:** Signal generator initialized with defaults if None provided
**Raises:** None
**Retry:** No
**Side Effects:** Creates calculator/predictor if None

### `generate_signal(order_book, historical_ofi, historical_returns, cofi_tracker) -> Optional[OFISignal]`
**Pre:** order_book has bids/asks, historical_ofi has momentum_window elements
**Post:** Returns OFISignal or None if no signal generated
**Raises:** None (returns None on invalid OFI or failed prediction)
**Retry:** No
**Side Effects:** None (read-only)

### `_generate_threshold_signal(order_book, historical_ofi, historical_returns, ofi_result) -> Optional[OFISignal]`
**Pre:** ofi_result.is_valid == True
**Post:** Returns OFISignal if OFI crosses threshold, else None
**Raises:** None
**Retry:** No
**Side Effects:** May call predictor.predict_direction()

### `_generate_mean_reversion_signal(order_book, cofi_tracker, ofi_result) -> Optional[OFISignal]`
**Pre:** cofi_tracker initialized, ofi_result valid
**Post:** Returns OFISignal if COFI extreme (>threshold std), else None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_generate_momentum_signal(order_book, historical_ofi, ofi_result) -> Optional[OFISignal]`
**Pre:** historical_ofi length >= momentum_window
**Post:** Returns OFISignal if momentum > threshold, else None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_confidence(ofi: float, action: str) -> float`
**Pre:** ofi in [-1, 1], action in ["BUY", "SELL"]
**Post:** Returns confidence in [min_confidence, 1.0]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `filter_signals(signals: List[OFISignal], min_confidence: Optional[float] = None) -> List[OFISignal]`
**Pre:** signals is list of OFISignal
**Post:** Returns signals with confidence >= threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rank_signals(signals: List[OFISignal]) -> List[OFISignal]`
**Pre:** signals is list of OFISignal
**Post:** Returns signals sorted by confidence (descending)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `validate_signal(signal: OFISignal) -> bool`
**Pre:** signal is OFISignal
**Post:** Returns True if signal meets trading criteria
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Mean reversion signals checked first (highest priority)
- [ ] Momentum signals checked second
- [ ] Threshold signals checked last
- [ ] Buy signal when OFI >= buy_threshold
- [ ] Sell signal when OFI <= sell_threshold
- [ ] Mean reversion: COFI z-score > 2 → SELL, < -2 → BUY
- [ ] Momentum: momentum > 0.1 → BUY, < -0.1 → SELL
- [ ] Confidence = min(1.0, |OFI|/scale + threshold_distance*2)
- [ ] Horizon based on OFI magnitude and momentum
- [ ] Reasoning includes OFI description and volume info

---


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit v2.0) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 1 P3 |
| **Notes** | All critical rules verified. Recent signals tracking unused (P3). See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - validate_signal() checks criteria |
| TRD-004 | BASE_RULES | Audit trail for trades | ✅ OK - OFISignal includes reasoning |
| LOG-001 | BASE_RULES | Structured logging with context | ✅ FIXED - All logging uses extra={} |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ✅ FIXED - All exceptions logged with exc_info=True |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| SEC-007 | BASE_RULES | Input validation | ✅ OK - Validates OFI before signal gen |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - Specific exceptions: SignalGenerationError, InvalidOFIError |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Imports from OFI module only |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - calculator/predictor injected |

---

## Dependencies
- **External:** numpy (np), datetime, decimal (Decimal), typing, logging
- **Internal:** app.market_microstructure.ofi.models (all OFI models), app.market_microstructure.ofi.ofi_calculator (OFICalculator, OFIResult), app.market_microstructure.ofi.ofi_predictor (OFIPredictor)

---

## Required Tests
- **tests/market_microstructure/ofi/test_ofi_signals.py:**
  - Test threshold signal generation (buy/sell/none)
  - Test mean reversion signal (extreme high/low)
  - Test momentum signal (positive/negative/none)
  - Test confidence calculation
  - Test horizon determination logic
  - Test reasoning generation
  - Test signal filtering by confidence
  - Test signal ranking by confidence
  - Test signal validation criteria
  - Test batch signal generation
  - Test edge cases: invalid OFI, empty history

---

## Notes
Signal priority: mean reversion > momentum > threshold. Mean reversion expects reversal at extremes. Momentum expects continuation. Based on Cont & Kukanov (2017) and Aldridge (2013).
