# bet_sizing.py

## Purpose
Bet sizing implementation for Financial ML based on López de Prado's "Advances in Financial Machine Learning", Chapter 10. Determines optimal position sizes using Kelly Criterion, probability scaling, risk parity, and ML-based meta-labeling approaches.

---

## Type Definitions / Data Classes

### BetSizingConfig Class
```python
@dataclass
class BetSizingConfig:
    method: str                              # REQUIRED - Bet sizing method: 'kelly', 'probability', 'risk_parity', 'fixed'
    kelly_fraction: float = 0.25            # REQUIRED - Fraction of full Kelly (0-1), default 0.25 for safety
    min_kelly: float = 0.01                 # REQUIRED - Minimum bet size (>= 0)
    max_kelly: float = 0.25                 # REQUIRED - Maximum bet size (<= 1)
    prob_threshold: float = 0.5             # REQUIRED - Minimum probability to take trade (0-1)
    prob_scaling: str = "linear"            # REQUIRED - Scaling type: 'linear', 'sigmoid', 'softmax'
    risk_target: float = 0.15               # REQUIRED - Target annualized risk (default 15%)
    risk_window: int = 20                   # REQUIRED - Window for volatility calculation (> 0)
    max_position_size: float = 1.0          # REQUIRED - Maximum position size per signal (0-1)
    max_portfolio_exposure: float = 1.0     # REQUIRED - Maximum total exposure (0-1)
    concentration_limit: float = 0.3        # REQUIRED - Max exposure per signal/asset (0-1)
    max_drawdown: float = 0.2               # REQUIRED - Maximum drawdown (default 20%)
    drawdown_lookback: int = 252            # REQUIRED - Lookback for drawdown calculation (> 0)
    adjust_for_volatility: bool = True      # REQUIRED - Apply volatility adjustment
    adjust_for_correlation: bool = True     # REQUIRED - Apply correlation adjustment
    adjust_for_regime: bool = False         # REQUIRED - Apply regime adjustment (not yet implemented)
```

**Validation Rules:**
- `method` must be one of `["kelly", "probability", "risk_parity", "fixed"]`
- `kelly_fraction` must be between 0 and 1 (exclusive)
- `prob_threshold` must be between 0 and 1 (inclusive)
- `max_position_size` must be between 0 and 1 (inclusive)
- All float parameters must be finite and non-negative where appropriate
- Raises `ValueError` if validation fails in `__post_init__`

### BetSizingResult Class
```python
@dataclass
class BetSizingResult:
    bet_sizes: np.ndarray                   # REQUIRED - Position sizes for each signal (same length as inputs)
    expected_returns: np.ndarray           # REQUIRED - Expected returns for each signal
    risk_contribution: np.ndarray          # REQUIRED - Risk contribution of each position
    kelly_fractions: np.ndarray            # REQUIRED - Kelly criterion fractions (for reference)
    metadata: Dict = field(default_factory=dict)  # OPTIONAL - Additional metadata
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO - Timestamp of calculation
```

**Validation Rules:**
- All numpy arrays must have same length
- `bet_sizes` must be non-negative (>= 0)
- `risk_contribution` should sum to 1.0 (normalized)
- `metadata` dictionary contains: method, n_signals, avg_bet_size, total_exposure, max_exposure

**Methods:**
- `to_dict() -> Dict`: Converts result to dictionary with lists for arrays and ISO format timestamp

---

## Function Signatures (Contracts)

### `BetSizing.__init__(config: Optional[BetSizingConfig] = None) -> None`
**Pre:** config is None or valid BetSizingConfig instance
**Post:** Instance initialized with config (defaults to BetSizingConfig() if None)
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** None

### `BetSizing.calculate_sizes(predictions, probabilities, expected_returns, volatilities, correlation_matrix, current_capital, current_drawdown) -> BetSizingResult`
**Pre:** predictions is np.ndarray with values in [-1, 0, 1]; all optional arrays have same length as predictions
**Post:** Returns BetSizingResult with bet_sizes in [0, max_position_size]; total_exposure <= max_portfolio_exposure
**Raises:** ValueError if method is unknown; ValueError if drawdown constraint active and scaling fails
**Retry:** No
**Side Effects:** None (pure calculation)

### `BetSizing._kelly_sizing(predictions, probabilities, expected_returns) -> np.ndarray`
**Pre:** All arrays same length; predictions in [-1, 0, 1]; probabilities in [0, 1]
**Post:** Returns array with non-negative values; zeros for pred == 0 or negative Kelly
**Raises:** ZeroDivisionError if expected_return calculations fail (should be handled internally)
**Retry:** No
**Side Effects:** None

### `BetSizing._probability_sizing(predictions, probabilities) -> np.ndarray`
**Pre:** predictions in [-1, 0, 1]; probabilities in [0, 1]
**Post:** Returns array with sizes in [0, 1] based on confidence scaling
**Raises:** ValueError if prob_scaling is unknown
**Retry:** No
**Side Effects:** None

### `BetSizing._risk_parity_sizing(predictions, volatilities, correlation_matrix) -> np.ndarray`
**Pre:** predictions in [-1, 0, 1]; volatilities is None or positive array
**Post:** Returns array where weights proportional to 1/volatility for active signals
**Raises:** No explicit raises
**Retry:** No
**Side Effects:** None

### `BetSizing._adjust_for_volatility(bet_sizes, volatilities) -> np.ndarray`
**Pre:** bet_sizes non-negative; volatilities positive (no zeros)
**Post:** Returns adjusted bet_sizes (inverse volatility scaling)
**Raises:** No explicit raises (adds 1e-10 to prevent div by zero)
**Retry:** No
**Side Effects:** None

### `BetSizing._adjust_for_correlation(bet_sizes, correlation_matrix) -> np.ndarray`
**Pre:** bet_sizes non-negative; correlation_matrix is square matrix
**Post:** Returns bet_sizes reduced for highly correlated positions
**Raises:** IndexError if correlation_matrix dimensions don't match bet_sizes
**Retry:** No
**Side Effects:** None

### `BetSizing._apply_concentration_limit(bet_sizes) -> np.ndarray`
**Pre:** bet_sizes non-negative
**Post:** Returns bet_sizes with all values <= concentration_limit
**Raises:** No
**Retry:** No
**Side Effects:** None

### `BetSizing._apply_exposure_limit(bet_sizes) -> np.ndarray`
**Pre:** bet_sizes non-negative
**Post:** Returns bet_sizes where sum <= max_portfolio_exposure
**Raises:** No
**Retry:** No
**Side Effects:** None

### `BetSizing._calculate_risk_contribution(bet_sizes, volatilities, correlation_matrix) -> np.ndarray`
**Pre:** bet_sizes non-negative; volatilities is None or positive
**Post:** Returns array summing to 1.0 (normalized risk contribution)
**Raises:** No
**Retry:** No
**Side Effects:** None

### `BetSizing._calculate_kelly_fractions(predictions, probabilities, expected_returns) -> np.ndarray`
**Pre:** All arrays same length; predictions in [-1, 0, 1]
**Post:** Returns array with Kelly fractions (0 for pred == 0 or negative Kelly)
**Raises:** No
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes(predictions, probabilities, method, **kwargs) -> np.ndarray`
**Pre:** predictions in [-1, 0, 1]; method in ['kelly', 'probability', 'risk_parity', 'fixed']
**Post:** Returns bet_sizes array (same length as predictions)
**Raises:** ValueError if method unknown
**Retry:** No
**Side Effects:** None (convenience function)

### `calculate_bet_sizes_ml(meta_proba, primary_predictions, expected_returns, method, confidence_threshold, max_bet_size, min_bet_size) -> np.ndarray`
**Pre:** meta_proba in [0, 1]; primary_predictions in [-1, 0, 1]; method in ['meta_kelly', 'meta_probability', 'meta_expected_value', 'meta_confidence']
**Post:** Returns bet_sizes clipped to [min_bet_size, max_bet_size]; zeros for pred == 0 or prob < threshold
**Raises:** ValueError if method unknown
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_with_discrete_allocation(meta_proba, primary_predictions, n_bets, method) -> np.ndarray`
**Pre:** meta_proba in [0, 1]; primary_predictions in [-1, 0, 1]; n_bets > 0; method in ['top_k', 'threshold', 'optimal_f']
**Post:** Returns bet_sizes with exactly n_bets non-zero values (or fewer if not enough active signals)
**Raises:** No
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_with_risk_target(meta_proba, primary_predictions, volatilities, risk_target, max_position_size) -> np.ndarray`
**Pre:** meta_proba in [0, 1]; primary_predictions in [-1, 0, 1]; volatilities positive; risk_target > 0
**Post:** Returns bet_sizes targeting portfolio_vol ≈ risk_target; all values <= max_position_size
**Raises:** No
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_expected_value(predictions, probabilities, win_amount, loss_amount, kelly_fraction) -> np.ndarray`
**Pre:** predictions in [-1, 0, 1]; probabilities in [0, 1]; win_amount, loss_amount > 0; kelly_fraction in (0, 1]
**Post:** Returns bet_sizes with positive Kelly only; max capped at 0.25
**Raises:** No
**Retry:** No
**Side Effects:** None

### `calculate_kelly_criterion(win_probability, win_amount, loss_amount, fraction) -> float`
**Pre:** win_probability in (0, 1); win_amount, loss_amount > 0; fraction in (0, 1]
**Post:** Returns Kelly fraction in [0, 1]; 0 if non-positive EV
**Raises:** No
**Retry:** No
**Side Effects:** None

### `calculate_bet_sizes_with_meta_model(meta_model, X, primary_predictions, expected_returns, method, confidence_threshold) -> np.ndarray`
**Pre:** meta_model has predict_proba or predict method; X is feature matrix; primary_predictions in [-1, 0, 1]
**Post:** Returns bet_sizes based on meta-model predictions
**Raises:** AttributeError if meta_model lacks predict methods
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-TYP-001:** All functions have complete type hints (return types and parameters)
- [ ] **AC-TST-001:** Kelly criterion calculations match formula: f* = (bp - q) / b
- [ ] **AC-TST-002:** Bet sizes are always non-negative (>= 0)
- [ ] **AC-TST-003:** Bet sizes never exceed max_position_size (default 1.0)
- [ ] **AC-TST-004:** Total exposure never exceeds max_portfolio_exposure (default 1.0)
- [ ] **AC-TST-005:** Concentration limit enforced per position (default 0.3)
- [ ] **AC-TST-006:** Drawdown constraint scales positions when current_drawdown > max_drawdown
- [ ] **AC-TST-007:** Risk parity weights proportional to 1/volatility
- [ ] **AC-TST-008:** Probability scaling respects prob_threshold (no trades below threshold)
- [ ] **AC-TST-009:** Correlation adjustment reduces sizes for highly correlated positions
- [ ] **AC-TST-010:** Volatility adjustment uses inverse volatility scaling
- [ ] **AC-TST-011:** Meta-labeling bet sizes use meta-model probabilities correctly
- [ ] **AC-TST-012:** Discrete allocation selects exactly n_bets positions
- [ ] **AC-TST-013:** Risk target sizing achieves target portfolio volatility
- [ ] **AC-TST-014:** Expected value Kelly uses formula: f* = p/d - q/v
- [ ] **AC-TST-015:** All configuration validation raises ValueError for invalid inputs
- [ ] **AC-TST-016:** BetSizingResult.to_dict() returns serializable dictionary
- [ ] **AC-TST-017:** Zero predictions return zero bet sizes
- [ ] **AC-TST-018:** Handle edge cases: empty arrays, all zeros, all ones
- [ ] **AC-TST-019:** Logging occurs for drawdown constraint activation
- [ ] **AC-TST-020:** No division by zero errors (protected by epsilon = 1e-10)

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 1 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 2 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 13 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage for all functions | ✅ OK |
| TYP-002 | 02-type-hints.md | Use modern syntax `X \| None` not `Optional[X]` | ❌ GAP - Uses `Optional[X]` in line 30, 148-154, 641-648, etc. |
| TYP-003 | 02-type-hints.md | No `Any` type without justification | ❌ GAP - Line 1033 uses `Any` for meta_model without Protocol/justification |
| TYP-004 | 02-type-hints.md | All `# type: ignore` have explanation | ⚠️ NOT APPLIED - No type ignore comments found |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - Uses `field(default_factory=...)` |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some functions exceed for valid reasons (complex calculations) |
| ARCH-006 | 05-architecture.md | Value objects immutable | ⚠️ PARTIAL - BetSizingConfig and BetSizingResult are dataclasses but not frozen |
| CC-001 | 05-architecture.md | Descriptive names revealing intent | ✅ OK |
| CC-002 | 05-architecture.md | DRY - No code duplication | ⚠️ NOT APPLIED - Some Kelly calculation duplication between methods |
| CC-006 | 05-architecture.md | Explicit error handling | ⚠️ PARTIAL - Has validation but missing explicit error types in some places |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ⚠️ PARTIAL - Only one warning log (line 222), missing info/debug for key operations |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ❌ GAP - No logging of exceptions or validation errors |
| TRD-001 | 13-john-hull | Covariance matrix validation | ❌ GAP - No validation that correlation_matrix is positive semidefinite |
| TRD-002 | 13-john-hull | Risk validation before sizing | ⚠️ PARTIAL - Has limits but no pre-validation of risk parameters |
| TRD-003 | 13-john-hull | Position limits enforcement | ✅ OK - max_position_size, concentration_limit enforced |
| TRD-004 | 13-john-hull | Audit trail | ❌ GAP - No audit logging of bet sizing decisions |
| TRD-005 | 13-john-hull | Price validation | ⚠️ NOT APPLIED - This module doesn't handle prices directly |
| BT-003 | 10-robert-carver | No look-ahead bias | ✅ OK - Pure calculation, no future data access |
| PERF-002 | 19-high-performance-python | Use generators for large data | ⚠️ NOT APPLIED - Uses numpy arrays (appropriate for numerical computing) |
| PERF-005 | 19-high-performance-python | Use Numba JIT for hot paths | ⚠️ NOT APPLIED - Could benefit from Numba for Kelly calculations |

**CRITICAL GAPS (P0/P1):**
1. **TYP-003 (P1):** `meta_model: Any` on line 1033 should use Protocol for type safety
2. **LOG-004 (P0):** Missing exception logging - all validation errors should be logged
3. **TRD-001 (P0):** No validation that correlation_matrix is valid (symmetric, positive semidefinite, diagonal = 1)
4. **TRD-004 (P0):** No audit trail - bet sizing decisions should be logged for debugging/risk management

**MODERATE GAPS (P2):**
1. **TYP-002 (P2):** Uses `Optional[X]` instead of modern `X | None` syntax
2. **ARCH-006 (P1):** Dataclasses should be frozen for immutability
3. **LOG-003 (P1):** Insufficient logging - should log calculation steps, method used, constraints applied
4. **TRD-002 (P0):** Missing validation of risk parameters (volatilities > 0, risk_target > 0)

---

## Dependencies
- **External:**
  - `numpy` (np) - Array operations and numerical calculations
  - `logging` - Structured logging
  - `dataclasses` - BetSizingConfig, BetSizingResult
  - `datetime` - Timestamps
  - `typing` - Type hints (Dict, Optional)
  - `math` - Sigmoid/softmax calculations (imported locally)

- **Internal:**
  - None (standalone module, no internal imports)

---

## Required Tests

### `tests/backtesting/labeling/test_bet_sizing.py`
- **TestBetSizingConfig:** Validation of all config parameters (edge cases: 0, 1, negative, > 1)
- **TestBetSizingInit:** Default config creation, custom config passing
- **TestKellySizing:**
  - Correct Kelly formula application
  - Zero predictions return zero bet sizes
  - Fractional Kelly applied correctly
  - Min/max Kelly bounds enforced
  - Positive EV only (no bets on negative Kelly)
- **TestProbabilitySizing:**
  - Linear scaling from threshold to 1
  - Sigmoid scaling smoothness
  - Softmax scaling
  - Respects prob_threshold
  - Zero for pred == 0
- **TestRiskParitySizing:**
  - Weights proportional to 1/volatility
  - Handles None volatilities (default to ones)
  - Normalizes weights to sum to 1
  - Only active signals get non-zero
- **TestVolatilityAdjustment:**
  - Inverse volatility scaling
  - Handles edge case (volatility = 0 with epsilon)
  - Higher vol → smaller size
- **TestCorrelationAdjustment:**
  - Reduces sizes for highly correlated positions
  - No adjustment for single position
  - Calculates average correlation correctly
- **TestConcentrationLimit:**
  - Caps individual position sizes
  - Respects concentration_limit config
- **TestExposureLimit:**
  - Scales down if total > max_portfolio_exposure
  - Preserves relative weights when scaling
- **TestDrawdownConstraint:**
  - No scaling if drawdown < max_drawdown
  - Scales proportionally when exceeded
  - Logs warning when active
  - Never scales below zero
- **TestRiskContribution:**
  - Calculates weighted volatility
  - Normalizes to sum to 1
  - Returns zeros if no volatility data
- **TestKellyFractions:**
  - Calculates reference Kelly fractions
  - Returns zero for negative Kelly
  - Matches _kelly_sizing logic
- **TestCalculateSizes:**
  - Integration test: full pipeline
  - Correct method dispatch
  - All adjustments applied in order
  - Returns valid BetSizingResult
  - Metadata populated correctly
- **TestBetSizingResult:**
  - to_dict() returns serializable output
  - Timestamp auto-generated
  - All arrays converted to lists
- **TestCalculateBetSizes:**
  - Convenience function works
  - Defaults applied correctly
  - Returns bet_sizes array
- **TestCalculateBetSizesML:**
  - Meta-Kelly: f = 2p - 1
  - Meta-probability: direct scaling
  - Meta-expected value: EV calculation
  - Meta-confidence: step function
  - Respects confidence_threshold
  - Clips to [min_bet_size, max_bet_size]
  - Zero for pred == 0
- **TestDiscreteAllocation:**
  - Top-k: selects exactly k positions
  - Threshold: percentile-based selection
  - Optimal f: Kelly-based allocation
  - Equal weighting for selected
  - Handles insufficient active signals
- **TestRiskTargetSizing:**
  - Achieves target portfolio volatility
  - Uses inverse volatility weighting
  - Adjusts by meta-model probability
  - Respects max_position_size
  - Normalizes if sum > 1
- **TestExpectedValueSizing:**
  - Correct Kelly formula: f* = p/d - q/v
  - Positive EV only
  - Applies fractional Kelly
  - Caps at 0.25
  - Skips prob <= 0.5
- **TestCalculateKellyCriterion:**
  - Basic formula: f* = (bp - q) / b
  - Returns 0 for non-positive EV
  - Applies fraction parameter
  - Caps at 1.0
  - Edge cases: p=0, p=1, b=0
- **TestCalculateBetSizesWithMetaModel:**
  - Uses predict_proba if available
  - Falls back to predict if needed
  - Handles binary classification (2 classes)
  - Handles multi-class (max probability)
  - Passes through to calculate_bet_sizes_ml
- **TestEdgeCases:**
  - Empty arrays
  - All zeros predictions
  - All ones predictions
  - Single prediction
  - Volatility = 0 (epsilon handling)
  - Correlation matrix dimension mismatch
  - Negative probabilities (should handle/raise)
  - Probabilities > 1 (should handle/raise)
- **TestLogging:**
  - Drawdown warning logged
  - Method selection logged
  - Constraint violations logged
  - Errors logged with context
- **TestValidation:**
  - Invalid method raises ValueError
  - Invalid kelly_fraction raises ValueError
  - Invalid prob_threshold raises ValueError
  - Invalid max_position_size raises ValueError
  - Correlation matrix validation (P0 gap)
  - Volatility validation (P0 gap)

---

## Notes
- This is a **core financial ML module** implementing López de Prado's bet sizing methodology
- **Key distinction:** Primary model determines DIRECTION, meta-model determines SIZE
- **Risk management:** Multiple layers of protection (concentration, exposure, drawdown)
- **Performance:** Could benefit from Numba JIT for hot paths (Kelly calculations in loops)
- **Audit gap:** Missing logging of sizing decisions - critical for production trading systems
- **Type safety:** meta_model should use Protocol instead of Any for better type checking
- **Immutability:** Config and Result dataclasses should be frozen to prevent accidental mutation
- **Testing gap:** Needs comprehensive unit tests for all bet sizing methods and edge cases
