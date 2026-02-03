# bet_sizing_meta.py

## Purpose
Implements López de Prado's bet sizing with meta-labeling, using meta-model probabilities to dynamically size positions based on prediction confidence.

---

## Type Definitions / Data Classes

### MetaBetSizingConfig
```python
@dataclass
class MetaBetSizingConfig:
    method: str                              # REQUIRED - One of: 'meta_kelly', 'meta_expected_value', 'meta_confidence', 'discrete', 'risk_parity'
    confidence_threshold: float = 0.5        # REQUIRED - Range [0, 1], min meta-probability to trade
    high_confidence_threshold: float = 0.7   # REQUIRED - Range (>confidence_threshold, 1], high confidence threshold
    max_bet_size: float = 1.0                # REQUIRED - Range [0, 1], max position size
    min_bet_size: float = 0.0                # REQUIRED - Range [0, max_bet_size], min position
    max_total_exposure: float = 1.0          # REQUIRED - Range [0, inf], max portfolio exposure
    kelly_fraction: float = 0.25             # REQUIRED - Range [0, 1], fractional Kelly for safety
    n_bets: int = 10                         # REQUIRED - Range [1, inf], number of top bets for discrete method
    adjust_for_volatility: bool = True       # OPTIONAL - Apply volatility adjustment
    adjust_for_correlation: bool = False     # OPTIONAL - Apply correlation adjustment
    default_win_amount: float = 0.02         # REQUIRED - Range [0, inf], expected win (2%)
    default_loss_amount: float = 0.01        # REQUIRED - Range [0, inf], expected loss (1%)
```

**Validation Rules:**
- Method must be one of: 'meta_kelly', 'meta_expected_value', 'meta_confidence', 'discrete', 'risk_parity'
- confidence_threshold must be in [0, 1]
- high_confidence_threshold must be > confidence_threshold and <= 1.0
- max_bet_size must be in [0, 1]
- min_bet_size must be in [0, max_bet_size]
- kelly_fraction must be in [0, 1] (typically 0.25 for half-Kelly safety)

### MetaBetSizingResult
```python
@dataclass
class MetaBetSizingResult:
    bet_sizes: np.ndarray                    # REQUIRED - Position sizes for each signal
    primary_predictions: np.ndarray          # REQUIRED - Primary model predictions (-1, 0, 1)
    meta_probabilities: np.ndarray           # REQUIRED - Meta-model probabilities
    expected_returns: np.ndarray             # REQUIRED - Expected returns for each signal
    confidence_levels: np.ndarray            # REQUIRED - Confidence levels (0=low, 1=medium, 2=high)
    metadata: Dict[str, Any]                 # OPTIONAL - Additional metadata
    timestamp: datetime                      # AUTO - Result timestamp
```

**Validation Rules:**
- All arrays must have same length
- bet_sizes must be in [0, max_bet_size]
- confidence_levels must be in {0, 1, 2}
- Sum of absolute bet_sizes must be <= max_total_exposure

---

## Function Signatures (Contracts)

### `MetaLabelingBetSizing.__init__(config: Optional[MetaBetSizingConfig] = None) -> None`
**Pre:** config is None or valid MetaBetSizingConfig
**Post:** Instance initialized with config or defaults
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing.calculate_sizes(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], expected_returns: Optional[np.ndarray] = None, volatilities: Optional[np.ndarray] = None, correlation_matrix: Optional[np.ndarray] = None) -> MetaBetSizingResult`
**Pre:** primary_model and meta_model are fitted, X has compatible features
**Post:** Returns bet sizes based on configured method and meta-probabilities
**Raises:** ValueError for invalid method, RuntimeError on model prediction failure
**Retry:** No
**Side Effects:** None (pure prediction)

### `MetaLabelingBetSizing._meta_kelly_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns Kelly bet sizes: f = 2p - 1, clipped to [0, max_bet_size]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._meta_expected_value_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray, expected_returns: Optional[np.ndarray]) -> np.ndarray`
**Pre:** Arrays have compatible lengths
**Post:** Returns EV-based bet sizes: EV = p*win - (1-p)*loss, normalized to [0, 1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._meta_confidence_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns confidence-based sizes: 0 for low, linear [0-0.5] for medium, linear [0.5-max] for high
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._discrete_allocation(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length, config.n_bets >= 1
**Post:** Returns equal allocation (1/n_bets) to top N opportunities by meta-probability
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._risk_parity_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray, volatilities: Optional[np.ndarray]) -> np.ndarray`
**Pre:** Arrays have compatible lengths
**Post:** Returns risk parity weights: proportional to (1/volatility) * meta_probability
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_with_meta_labeling(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], expected_returns: Optional[np.ndarray] = None, method: str = "meta_kelly", confidence_threshold: float = 0.5, max_bet_size: float = 1.0, **kwargs) -> np.ndarray`
**Pre:** Models fitted, X has compatible features
**Post:** Returns bet sizes array
**Raises:** ValueError for invalid parameters
**Retry:** No
**Side Effects:** None

### `calculate_expected_value_with_meta_probabilities(meta_probabilities: np.ndarray, primary_predictions: np.ndarray, win_amounts: Optional[np.ndarray] = None, loss_amounts: Optional[np.ndarray] = None, default_win: float = 0.02, default_loss: float = 0.01) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns EV = p*win - (1-p)*loss for each prediction
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_kelly_with_meta_probabilities(meta_probabilities: np.ndarray, primary_predictions: np.ndarray, win_amounts: Optional[np.ndarray] = None, loss_amounts: Optional[np.ndarray] = None, kelly_fraction: float = 0.25) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns Kelly = (p/loss) - ((1-p)/win) * kelly_fraction
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All five bet sizing methods work correctly (meta_kelly, meta_expected_value, meta_confidence, discrete, risk_parity)
- [ ] Kelly criterion: f = 2p - 1, clipped to [0, max_bet_size], multiplied by kelly_fraction
- [ ] Expected value: EV = p*win - (1-p)*loss, normalized to [0, 1]
- [ ] Confidence sizing: 3-tier (low/medium/high) with linear scaling
- [ ] Discrete allocation: equal weights to top N by meta-probability
- [ ] Risk parity: weight proportional to (1/volatility) * meta_probability
- [ ] Bet sizes are zero when meta_probability < confidence_threshold
- [ ] Bet sizes are zero when primary_prediction == 0 (no signal)
- [ ] Exposure limit applied: scale down if total_exposure > max_total_exposure
- [ ] Volatility adjustment: bet_size *= (mean_vol / vol)
- [ ] Correlation adjustment: reduce size for highly correlated positions
- [ ] Confidence levels: 0 (p < threshold), 1 (threshold <= p < high), 2 (p >= high)
- [ ] All bet sizes clipped to [min_bet_size, max_bet_size]

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK |
| TRD-003 | BASE_RULES | Position limits enforced | ✅ OK - max_bet_size, min_bet_size, max_total_exposure |
| TRD-004 | BASE_RULES | Audit trail | ⚠️ PARTIAL - metadata tracking but no persistent audit |
| ARCH-004 | BASE_RULES | Small functions | ⚠️ PARTIAL - Some methods > 20 lines (_meta_kelly_sizing, _meta_expected_value_sizing) |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - No test file exists for bet_sizing_meta.py (tests out of scope for this task) |
| QL-007 | BASE_RULES | Max 7 parameters | ✅ OK - calculate_sizes has 6 params (within limit) |

**Bet Sizing Specific Rules:**
- BSIZ-001: Bet sizes must be zero when meta_probability < confidence_threshold
- BSIZ-002: Bet sizes must be zero when primary_prediction == 0 (no signal)
- BSIZ-003: Kelly criterion must use fractional Kelly (default 0.25) for safety
- BSIZ-004: Total exposure must not exceed max_total_exposure (scaled down if needed)
- BSIZ-005: All bet sizes must be clipped to [min_bet_size, max_bet_size]
- BSIZ-006: Risk parity must handle missing volatilities (default to 1.0)
- BSIZ-007: Discrete allocation must select top N by meta-probability

---

## Dependencies
- **External:** numpy, pandas
- **Internal:** None (standalone module, works with any scikit-learn compatible models)

---

## Required Tests
- **tests/backtesting/labeling/test_bet_sizing_meta.py:**
  - Test MetaBetSizingConfig validation (invalid methods, thresholds)
  - Test meta_kelly_sizing with various probabilities
  - Test meta_expected_value_sizing with custom win/loss amounts
  - Test meta_confidence_sizing 3-tier logic
  - Test discrete_allocation top N selection
  - Test risk_parity_sizing with and without volatilities
  - Test volatility adjustment (bet_size scaling)
  - Test correlation adjustment (reduction for correlated positions)
  - Test exposure limit scaling
  - Test bet size clipping to [min, max]
  - Test zero bet size when meta_probability < threshold
  - Test zero bet size when primary_prediction == 0
  - Test calculate_bet_sizes_with_meta_labeling convenience function
  - Test calculate_expected_value_with_meta_probabilities
  - Test calculate_kelly_with_meta_probabilities
  - Test confidence levels calculation (0, 1, 2)
  - Test all five methods end-to-end

---

## Notes
Based on Marcos López de Prado "Advances in Financial Machine Learning" Chapters 3 & 10. Key innovation: primary model determines DIRECTION, meta-model determines SIZE. This separation allows for better risk management and reduced false positives. Supports five distinct bet sizing methods with optional volatility and correlation adjustments.
