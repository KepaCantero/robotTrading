# bet_sizing.py

## Purpose
Bet Sizing Implementation for Financial ML - Implements various bet sizing methods including Kelly criterion, probability scaling, risk parity, and ML-based meta-labeling for optimal position sizing based on López de Prado's "Advances in Financial Machine Learning", Chapter 10.

---

## Type Definitions / Data Classes

### BetSizingConfig
```python
@dataclass
class BetSizingConfig:
    """Configuration for bet sizing."""
    method: str = "kelly"                      # kelly, probability, risk_parity, fixed
    kelly_fraction: float = 0.25               # Fraction of full Kelly (safety)
    min_kelly: float = 0.01                    # Minimum bet size
    max_kelly: float = 0.25                    # Maximum bet size
    prob_threshold: float = 0.5                # Minimum probability to trade
    prob_scaling: str = "linear"               # linear, sigmoid, softmax
    risk_target: float = 0.15                  # Target annualized risk (15%)
    risk_window: int = 20                      # Volatility calculation window
    max_position_size: float = 1.0             # Maximum position size
    max_portfolio_exposure: float = 1.0        # Maximum total exposure
    concentration_limit: float = 0.3           # Max exposure per signal/asset
    max_drawdown: float = 0.2                  # Maximum drawdown (20%)
    drawdown_lookback: int = 252                # Drawdown calculation lookback
    adjust_for_volatility: bool = True
    adjust_for_correlation: bool = True
    adjust_for_regime: bool = False
```

**Validation in __post_init__:**
- method must be one of: kelly, probability, risk_parity, fixed
- kelly_fraction must be between 0 and 1
- prob_threshold must be between 0 and 1
- max_position_size must be between 0 and 1

### BetSizingResult
```python
@dataclass
class BetSizingResult:
    """Result of bet sizing calculation."""
    bet_sizes: np.ndarray                       # Position sizes for each signal
    expected_returns: np.ndarray                # Expected returns
    risk_contribution: np.ndarray               # Risk contribution
    kelly_fractions: np.ndarray                 # Kelly fractions
    metadata: Dict                              # Additional metadata
    timestamp: datetime                         # Calculation time
```

---

## Function Signatures (Contracts)

### `BetSizing.__init__(config: Optional[BetSizingConfig] = None) -> None`
**Pre:** None
**Post:** Bet sizing calculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores config (or creates default)

### `BetSizing.calculate_sizes(
    predictions: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    expected_returns: Optional[np.ndarray] = None,
    volatilities: Optional[np.ndarray] = None,
    correlation_matrix: Optional[np.ndarray] = None,
    current_capital: float = 1_000_000.0,
    current_drawdown: float = 0.0,
) -> BetSizingResult`
**Pre:** predictions is array of -1, 0, 1; arrays have compatible lengths
**Post:** Returns BetSizingResult with position sizes
**Raises:** ValueError if unknown method
**Retry:** No
**Side Effects:** None (pure computation)

**Process Flow:**
1. Initialize defaults for probabilities/expected_returns
2. Calculate bet sizes based on method (kelly/probability/risk_parity/fixed)
3. Apply volatility adjustment (if enabled)
4. Apply correlation adjustment (if enabled)
5. Apply concentration limits
6. Apply position size limits
7. Apply portfolio exposure limit
8. Apply drawdown constraint (if exceeded)
9. Calculate risk contribution and Kelly fractions

### `BetSizing._kelly_sizing(predictions, probabilities, expected_returns) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns Kelly bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Kelly Formula:** `f* = (bp - q) / b`
- b = odds (win/loss ratio)
- p = probability of winning
- q = 1 - p

**Safety:** Applies fractional Kelly (config.kelly_fraction) and clips to bounds

### `BetSizing._probability_sizing(predictions, probabilities) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns probability-scaled bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Scaling Methods:**
- **linear:** `(prob - threshold) / (1 - threshold)`
- **sigmoid:** `1 / (1 + exp(-5 × (x - 0.5)))`
- **softmax:** `exp(prob - 1) / (1 + exp(prob - 1))`

### `BetSizing._risk_parity_sizing(predictions, volatilities, correlation_matrix) -> np.ndarray`
**Pre:** predictions non-empty; volatilities optional
**Post:** Returns risk parity bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `weight = 1/volatility` (inverse volatility weighting)

### `BetSizing._fixed_sizing(predictions) -> np.ndarray`
**Pre:** predictions is array
**Post:** Returns fixed bet sizes (equal for all active signals)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `size = 1/n_active` (equal allocation)

### `BetSizing._adjust_for_volatility(bet_sizes, volatilities) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns volatility-adjusted bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `bet_size × (1 / (vol/mean_vol))`

### `BetSizing._adjust_for_correlation(bet_sizes, correlation_matrix) -> np.ndarray`
**Pre:** bet_sizes and correlation_matrix compatible
**Post:** Returns correlation-adjusted bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `bet_size × (1 / (1 + avg_correlation))`

### `BetSizing._apply_concentration_limit(bet_sizes) -> np.ndarray`
**Pre:** bet_sizes is array
**Post:** Returns concentration-limited bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Rule:** `min(bet_size, concentration_limit)` for each position

### `BetSizing._apply_exposure_limit(bet_sizes) -> np.ndarray`
**Pre:** bet_sizes is array
**Post:** Returns exposure-limited bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Rule:** Scale down if total exposure exceeds max

### `BetSizing._calculate_risk_contribution(bet_sizes, volatilities, correlation_matrix) -> np.ndarray`
**Pre:** Arrays have compatible lengths
**Post:** Returns risk contribution array
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `risk_contrib = (weight × volatility) / total_risk`

### `BetSizing._calculate_kelly_fractions(predictions, probabilities, expected_returns) -> np.ndarray`
**Pre:** Arrays have same length
**Post:** Returns Kelly fractions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_bet_sizes(
    predictions: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    method: str = "kelly",
    **kwargs,
) -> np.ndarray`
**Pre:** predictions is array of -1, 0, 1
**Post:** Returns bet sizes array
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Convenience Function:** Simplified interface for bet sizing

### `calculate_bet_sizes_ml(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
    method: str = "meta_kelly",
    confidence_threshold: float = 0.5,
    max_bet_size: float = 1.0,
    min_bet_size: float = 0.0,
) -> np.ndarray`
**Pre:** meta_proba and primary_predictions have same length
**Post:** Returns ML-based bet sizes
**Raises:** ValueError if unknown method
**Retry:** No
**Side Effects:** None (pure computation)

**ML Methods:**
- **meta_kelly:** Kelly criterion using meta-model probabilities
- **meta_probability:** Direct probability scaling
- **meta_expected_value:** Size based on expected value
- **meta_confidence:** Confidence-based sizing with threshold

**Key Insight:** Primary model determines DIRECTION, meta-model determines SIZE

### `calculate_bet_sizes_with_discrete_allocation(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    n_bets: int = 10,
    method: str = "top_k",
) -> np.ndarray`
**Pre:** meta_proba and primary_predictions have same length; n_bets > 0
**Post:** Returns discrete allocation bet sizes (0 or 1/n_bets)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Methods:**
- **top_k:** Equal size to top k bets by probability
- **threshold:** Allocate to all bets above percentile threshold
- **optimal_f:** Kelly optimal f allocation

### `calculate_bet_sizes_with_risk_target(
    meta_proba: np.ndarray,
    primary_predictions: np.ndarray,
    volatilities: np.ndarray,
    risk_target: float = 0.15,
    max_position_size: float = 1.0,
) -> np.ndarray`
**Pre:** Arrays have same length; risk_target > 0
**Post:** Returns risk-targeted bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** Risk parity weights adjusted by meta-model probability

### `calculate_bet_sizes_expected_value(
    predictions: np.ndarray,
    probabilities: np.ndarray,
    win_amount: np.ndarray,
    loss_amount: np.ndarray,
    kelly_fraction: float = 0.25,
) -> np.ndarray`
**Pre:** Arrays have same length; amounts > 0
**Post:** Returns EV-based bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Kelly Formula:** `f* = p/d - q/v`
- p = win probability
- q = 1 - p
- v = win amount per unit bet
- d = loss amount per unit bet

### `calculate_kelly_criterion(
    win_probability: float,
    win_amount: float = 1.0,
    loss_amount: float = 1.0,
    fraction: float = 1.0,
) -> float`
**Pre:** win_probability in (0, 1); amounts > 0
**Post:** Returns optimal bet size as fraction of capital
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `f* = (bp - q) / b` where b = win_amount / loss_amount

### `calculate_bet_sizes_with_meta_model(
    meta_model: Any,
    X: np.ndarray,
    primary_predictions: np.ndarray,
    expected_returns: Optional[np.ndarray] = None,
    method: str = "kelly",
    confidence_threshold: float = 0.5,
) -> np.ndarray`
**Pre:** meta_model has predict_proba or predict method; arrays compatible
**Post:** Returns meta-model-based bet sizes
**Raises:** None
**Retry:** No
**Side Effects:** Calls meta_model.predict_proba() or predict()

**Process:**
1. Get meta-model probabilities
2. Convert to bet sizes using calculate_bet_sizes_ml
3. Return bet sizes

---

## Acceptance Criteria
- [ ] **AC-001:** BetSizingConfig validates parameters in __post_init__
- [ ] **AC-002:** calculate_sizes() supports kelly method
- [ ] **AC-003:** calculate_sizes() supports probability method
- [ ] **AC-004:** calculate_sizes() supports risk_parity method
- [ ] **AC-005:** calculate_sizes() supports fixed method
- [ ] **AC-006:** Kelly criterion formula is (bp - q) / b
- [ ] **AC-007:** Fractional Kelly applied for safety
- [ ] **AC-008:** Volatility adjustment reduces size for higher vol
- [ ] **AC-009:** Correlation adjustment reduces size for correlated bets
- [ ] **AC-010:** Concentration limit caps position size
- [ ] **AC-011:** Exposure limit scales down total exposure
- [ ] **AC-012:** Drawdown constraint activates when exceeded
- [ ] **AC-013:** calculate_bet_sizes_ml() implements meta_kelly
- [ ] **AC-014:** calculate_bet_sizes_ml() only sizes when primary has signal
- [ ] **AC-015:** calculate_kelly_criterion() returns correct formula
- [ ] **AC-016:** NumPy 2.0 compatible (no np aliases)
- [ ] **AC-017:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Bet Sizing):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Kelly Criterion | Kelly (1956) | Optimal bet size | ✅ OK - _kelly_sizing() |
| Meta-labeling | López de Prado (2018) | Direction vs Size | ✅ OK - calculate_bet_sizes_ml() |
| Risk Parity | Portfolio theory | Inverse volatility | ✅ OK - _risk_parity_sizing() |
| Fractional Kelly | Risk management | Safety fraction | ✅ OK - kelly_fraction |
| Volatility adjustment | Risk management | Size ∝ 1/vol | ✅ OK - _adjust_for_volatility() |
| Correlation adjustment | Risk management | Reduce correlated | ✅ OK - _adjust_for_correlation() |
| Concentration limit | Risk management | Max position size | ✅ OK - _apply_concentration_limit() |
| Drawdown constraint | Risk management | Scale when DD high | ✅ OK - calculate_sizes() |
| Expected Value | Probability | EV sizing | ✅ OK - calculate_bet_sizes_expected_value() |
| ML-based sizing | López de Prado (2018) | Chapter 10 | ✅ OK - calculate_bet_sizes_with_meta_model() |
| Configuration validation | Clean code | __post_init__ | ✅ OK - BetSizingConfig |
| Dataclass | Clean code | Immutable results | ✅ OK - BetSizingResult |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and López de Prado (2018) for ML bet sizing standards.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `datetime` (std), `logging` (std), `typing` (std), `math` (std)
- **Internal:** None (infrastructure layer)

---

## Required Tests
- **test_bet_sizing.py:**
  - `test_bet_sizing_config_validation()` - Validates parameters
  - `test_calculate_sizes_kelly()` - Kelly method works
  - `test_calculate_sizes_probability()` - Probability method works
  - `test_calculate_sizes_risk_parity()` - Risk parity works
  - `test_calculate_sizes_fixed()` - Fixed method works
  - `test_kelly_formula()` - (bp - q) / b
  - `test_fractional_kelly()` - Applies kelly_fraction
  - `test_kelly_clips_to_bounds()` - Min/max bounds enforced
  - `test_volatility_adjustment()` - Higher vol = smaller size
  - `test_correlation_adjustment()` - Correlated positions reduced
  - `test_concentration_limit()` - Caps position size
  - `test_exposure_limit()` - Scales total exposure
  - `test_drawdown_constraint()` - Activates when exceeded
  - `test_calculate_bet_sizes_ml_meta_kelly()` - ML-based Kelly
  - `test_calculate_bet_sizes_ml_no_signal()` - Zero when pred = 0
  - `test_calculate_bet_sizes_ml_threshold()` - Respects confidence_threshold
  - `test_discrete_allocation_top_k()` - Selects top k
  - `test_risk_target()` - Targets specific risk level
  - `test_expected_value_sizing()` - EV-based sizing
  - `test_calculate_kelly_criterion()` - Correct formula
  - `test_calculate_kelly_criterion_negative_ev()` - Returns 0
  - `test_meta_model_sizing()` - Uses meta_model.predict_proba()

---

## Notes
- **Critical:** Bet sizing is KEY to risk management and maximizing risk-adjusted returns
- **López de Prado Reference:** "Advances in Financial Machine Learning" (2018) - Chapter 10 "Bet Sizing"
- **Kelly Criterion:** Optimal bet size for maximizing long-term growth
  - Formula: `f* = (bp - q) / b`
  - b = odds (win/loss ratio)
  - p = probability of winning, q = 1-p
  - Only bet if positive expected value
- **Fractional Kelly:** Most traders use 25% Kelly (kelly_fraction = 0.25) for safety
  - Full Kelly can be too aggressive
  - Fractional Kelly reduces volatility while maintaining growth
- **Meta-Labeling (López de Prado):**
  - **Primary Model:** Determines DIRECTION (buy/sell)
  - **Meta Model:** Determines SIZE (how much to bet)
  - This separation improves risk-adjusted returns
- **Risk Parity:** Equalize risk contribution across positions
  - Weight ∝ 1/volatility
  - Popularized by Bridgewater (All Weather strategy)
- **Volatility Adjustment:** Higher volatility → smaller position size
  - Formula: `bet_size × (mean_vol / current_vol)`
- **Correlation Adjustment:** Reduce size for correlated positions
  - Highly correlated positions should be smaller
  - Formula: `bet_size × (1 / (1 + avg_correlation))`
- **Concentration Limit:** Cap individual position sizes (default: 30%)
- **Drawdown Constraint:** Scale down positions when drawdown exceeds limit
  - Prevents further losses during drawdowns
- **Discrete Allocation:** Allocate to top k opportunities (concentrated portfolio)
- **Production Rule:** Always use fractional Kelly (25%) for production trading

---

**File Reference:** `app/backtesting/labeling/bet_sizing.py`
**Last Audited:** 2026-02-01
