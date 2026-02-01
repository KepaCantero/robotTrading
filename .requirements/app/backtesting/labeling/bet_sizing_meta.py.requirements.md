# bet_sizing_meta.py

## Purpose
Implements meta-labeling-based bet sizing using primary model (direction) and meta-model (confidence) to calculate optimal position sizes via multiple methods (Kelly, expected value, confidence-based, discrete, risk parity).

---

## Type Definitions / Data Classes

### MetaBetSizingConfig Class/DataClass
```python
@dataclass
class MetaBetSizingConfig:
    method: str = "meta_kelly"                        # REQUIRED - Sizing method
    confidence_threshold: float = 0.5                 # REQUIRED - Min probability [0,1]
    high_confidence_threshold: float = 0.7            # REQUIRED - High confidence [0,1], > confidence_threshold
    max_bet_size: float = 1.0                         # REQUIRED - Max position [0,1]
    min_bet_size: float = 0.0                         # REQUIRED - Min position [0, max_bet_size]
    max_total_exposure: float = 1.0                   # REQUIRED - Total exposure limit [0,1]
    kelly_fraction: float = 0.25                      # REQUIRED - Fraction of full Kelly (0,1]
    n_bets: int = 10                                  # REQUIRED - Number of top bets > 0
    adjust_for_volatility: bool = True                # OPTIONAL - Apply volatility adjustment
    adjust_for_correlation: bool = False              # OPTIONAL - Apply correlation adjustment
    default_win_amount: float = 0.02                  # OPTIONAL - Expected win (positive)
    default_loss_amount: float = 0.01                 # OPTIONAL - Expected loss (positive)
```

**Validation Rules:**
- method must be in ['meta_kelly', 'meta_expected_value', 'meta_confidence', 'discrete', 'risk_parity']
- confidence_threshold must be in [0, 1]
- high_confidence_threshold must be > confidence_threshold and <= 1
- max_bet_size must be in [0, 1]
- min_bet_size must be in [0, max_bet_size]
- max_total_exposure must be in [0, 1]
- kelly_fraction must be in (0, 1]
- n_bets must be > 0

### MetaBetSizingResult Class/DataClass
```python
@dataclass
class MetaBetSizingResult:
    bet_sizes: np.ndarray                    # REQUIRED - Position sizes for each signal
    primary_predictions: np.ndarray          # REQUIRED - Primary model predictions
    meta_probabilities: np.ndarray           # REQUIRED - Meta-model probabilities
    expected_returns: np.ndarray             # REQUIRED - Expected returns
    confidence_levels: np.ndarray            # REQUIRED - Confidence levels (0,1,2)
    metadata: Dict[str, Any]                 # OPTIONAL - Additional metadata
    timestamp: datetime = field(default_factory=datetime.now)
```

**Validation Rules:**
- All arrays must have same length
- bet_sizes must be in [0, max_bet_size]
- confidence_levels must be in {0, 1, 2} (low, medium, high)
- Sum of bet_sizes must not exceed max_total_exposure

---

## Function Signatures (Contracts)

### `MetaLabelingBetSizing.__init__(config: Optional[MetaBetSizingConfig] = None) -> None`
**Pre:** config is None or valid MetaBetSizingConfig
**Post:** Instance initialized with config
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing.calculate_sizes(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], expected_returns: Optional[np.ndarray] = None, volatilities: Optional[np.ndarray] = None, correlation_matrix: Optional[np.ndarray] = None) -> MetaBetSizingResult`
**Pre:** primary_model and meta_model are fitted with predict() and predict_proba() methods, X is 2D array
**Post:** Returns MetaBetSizingResult with bet_sizes clipped to limits and exposure applied
**Raises:** ValueError on invalid config or model methods
**Retry:** No
**Side Effects:** None (pure calculation)

### `MetaLabelingBetSizing._meta_kelly_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length, meta_probabilities in [0,1]
**Post:** Returns Kelly bet sizes: f = 2p - 1, clipped to [0, max_bet_size], only positive EV bets
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._meta_expected_value_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray, expected_returns: Optional[np.ndarray]) -> np.ndarray`
**Pre:** Arrays have compatible lengths, probabilities in [0,1]
**Post:** Returns EV-based sizes: EV = p*win - (1-p)*loss, normalized to [0,1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._meta_confidence_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length, probabilities in [0,1]
**Post:** Returns confidence-based sizes with linear scaling between thresholds
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._discrete_allocation(primary_predictions: np.ndarray, meta_probabilities: np.ndarray) -> np.ndarray`
**Pre:** Arrays have same length, config.n_bets > 0
**Post:** Returns equal allocation to top n_bets by meta_probability
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._risk_parity_sizing(primary_predictions: np.ndarray, meta_probabilities: np.ndarray, volatilities: Optional[np.ndarray]) -> np.ndarray`
**Pre:** Arrays have compatible lengths, volatilities positive if provided
**Post:** Returns inverse-volatility weighted sizes adjusted by meta_probability
**Raises:** None
**Retry:** No
**Side Effects:** None

### `MetaLabelingBetSizing._apply_exposure_limit(bet_sizes: np.ndarray) -> np.ndarray`
**Pre:** bet_sizes is non-negative array
**Post:** Returns bet_sizes scaled down if sum > max_total_exposure
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_with_meta_labeling(primary_model: Any, meta_model: Any, X: Union[pd.DataFrame, np.ndarray], expected_returns: Optional[np.ndarray] = None, method: str = "meta_kelly", confidence_threshold: float = 0.5, max_bet_size: float = 1.0, **kwargs) -> np.ndarray`
**Pre:** Models are fitted, X has valid shape
**Post:** Returns bet_sizes array
**Raises:** ValueError on invalid parameters
**Retry:** No
**Side Effects:** Creates MetaLabelingBetSizing instance

### `calculate_expected_value_with_meta_probabilities(meta_probabilities: np.ndarray, primary_predictions: np.ndarray, win_amounts: Optional[np.ndarray] = None, loss_amounts: Optional[np.ndarray] = None, default_win: float = 0.02, default_loss: float = 0.01) -> np.ndarray`
**Pre:** Arrays have same length, probabilities in [0,1]
**Post:** Returns EV array: p*win - (1-p)*loss
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_kelly_with_meta_probabilities(meta_probabilities: np.ndarray, primary_predictions: np.ndarray, win_amounts: Optional[np.ndarray] = None, loss_amounts: Optional[np.ndarray] = None, kelly_fraction: float = 0.25) -> np.ndarray`
**Pre:** Arrays have same length, probabilities in [0,1], win/loss amounts positive
**Post:** Returns Kelly fractions: (p/d - q/v) * kelly_fraction, only positive EV
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All public functions have complete type hints (TYP-001)
- [ ] MetaBetSizingConfig validates all constraints in __post_init__
- [ ] Bet sizes are always clipped to [min_bet_size, max_bet_size]
- [ ] Total exposure never exceeds max_total_exposure
- [ ] Kelly criterion only produces positive sizes when p > 0.5
- [ ] Confidence levels correctly map: <threshold=0, <high=1, >=high=2
- [ ] Risk parity handles missing volatilities (default to 1.0)
- [ ] Discrete allocation selects top n_bets by meta_probability
- [ ] Volatility adjustment uses inverse scaling (1/vol)
- [ ] Correlation adjustment reduces sizes for highly correlated positions
- [ ] All sizing methods skip primary_predictions == 0 (no signal)
- [ ] Expected value calculation handles missing win/loss amounts

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ⚠️ NOT APPLIED - Private methods missing some hints |
| TRD-001 | BASE_RULES.md | Trading system validation | ✅ OK - Config validates parameters |
| TRD-003 | BASE_RULES.md | Position limits enforced | ✅ OK - max_bet_size and max_total_exposure enforced |
| TRD-004 | BASE_RULES.md | Audit trail logging | ❌ GAP - No logging of bet sizing decisions |
| CC-006 | BASE_RULES.md | Explicit error handling | ❌ GAP - Missing ValueError in _calculate_bet_sizes |
| ARCH-004 | BASE_RULES.md | Small functions | ❌ GAP - _meta_kelly_sizing has loop that could be vectorized |
| PERF-001 | BASE_RULES.md | List comprehensions | ❌ GAP - Uses explicit loops instead of vectorized operations |
| LOG-004 | BASE_RULES.md | Error logging | ⚠️ NOT APPLIED - No error scenarios requiring logging |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Focuses on bet sizing calculations |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, logging, dataclasses
- **Internal:** None (standalone module, uses models from external libraries)

---

## Required Tests
- **tests/unit/backtesting/labeling/test_bet_sizing_meta.py:**
  - Test MetaBetSizingConfig validation for all parameters
  - Test calculate_sizes with all methods (kelly, ev, confidence, discrete, risk_parity)
  - Test Kelly criterion produces positive sizes only when p > 0.5
  - Test exposure limit enforcement scales down bet sizes
  - Test volatility adjustment using inverse scaling
  - Test correlation adjustment reduces highly correlated positions
  - Test confidence level calculation (0, 1, 2 mapping)
  - Test discrete allocation selects top n_bets
  - Test risk parity with and without volatilities
  - Test expected value calculation with defaults and custom amounts
  - Test Kelly calculation with win/loss amounts
  - Test edge cases: empty arrays, all zeros, all ones
  - Test that primary_predictions == 0 results in zero bet size

---

## Notes
Implements López de Prado's meta-labeling bet sizing approach. Critical for risk management and position sizing. The separation of direction (primary) and size (meta) is key to reducing false positives and improving risk-adjusted returns.
