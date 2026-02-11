# backtest_result.py

## Purpose
BacktestResult Value Object - Immutable results from backtesting operations with comprehensive performance metrics.

---

## Type Definitions / Data Classes

### BacktestResultValue (frozen=True)
```python
@dataclass(frozen=True)
class BacktestResultValue:
    # Basic metrics (REQUIRED)
    initial_capital: Decimal               # REQUIRED - Starting capital (> 0)
    final_capital: Decimal                 # REQUIRED - Ending capital
    total_return: Decimal                  # REQUIRED - Total return (absolute)
    total_return_pct: Decimal              # REQUIRED - Total return (percentage)

    # Risk metrics (OPTIONAL)
    sharpe_ratio: Optional[Decimal]        # Default: None - Sharpe ratio
    sortino_ratio: Optional[Decimal]       # Default: None - Sortino ratio
    max_drawdown: Optional[Decimal]        # Default: None - Maximum drawdown
    volatility: Optional[Decimal]          # Default: None - Annualized volatility
    var_95: Optional[Decimal]              # Default: None - 95% Value at Risk

    # Trading metrics
    total_trades: int                      # Default: 0 - Total number of trades
    winning_trades: int                    # Default: 0 - Number of winning trades
    losing_trades: int                     # Default: 0 - Number of losing trades
    win_rate: Optional[Decimal]            # Default: None - Win rate (0-1)
    avg_win: Optional[Decimal]             # Default: None - Average winning trade
    avg_loss: Optional[Decimal]            # Default: None - Average losing trade
    profit_factor: Optional[Decimal]       # Default: None - Profit factor

    # Trade level metrics (OPTIONAL)
    avg_trade_duration: Optional[Decimal]  # Default: None - Average trade duration
    avg_hold_time: Optional[Decimal]       # Default: None - Average hold time

    # Advanced metrics (OPTIONAL)
    calmar_ratio: Optional[Decimal]        # Default: None - Calmar ratio
    omega_ratio: Optional[Decimal]         # Default: None - Omega ratio
    tail_ratio: Optional[Decimal]          # Default: None - Tail ratio

    # Regression metrics (OPTIONAL)
    hit_rate: Optional[Decimal]            # Default: None - Hit rate
    precision: Optional[Decimal]           # Default: None - Precision score
    recall: Optional[Decimal]              # Default: None - Recall score
    f1_score: Optional[Decimal]            # Default: None - F1 score

    # Additional statistics
    additional_stats: Dict[str, Any]       # Default: {} - Additional custom metrics
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by all metrics, no identity)

**Invariants (enforced in __post_init__):**
- `initial_capital` > 0
- `total_trades` >= 0
- `winning_trades` >= 0
- `losing_trades` >= 0
- `winning_trades + losing_trades` <= `total_trades`

---

## Function Signatures (Contracts)

### `BacktestResultValue.__post_init__() -> None`
**Pre:** None
**Post:** Result validated
**Raises:** `ValueError` if any invariant violated
**Retry:** No
**Side Effects:** None (validation only)

### `roi (property) -> Decimal`
**Pre:** None
**Post:** Returns total_return (alias for ROI)
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

### `is_profitable (property) -> bool`
**Pre:** None
**Post:** Returns True if total_return > 0
**Raises:** None
**Retry:** No
**Side Effects:** None (property getter)

### `has_acceptable_drawdown(threshold: Decimal = Decimal('0.20')) -> bool` (method)
**Pre:** threshold >= 0
**Post:** Returns True if max_drawdown is None OR abs(max_drawdown) <= threshold
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Default Threshold:** 20% (0.20)

### `to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns result as dictionary with all values as strings or native types
**Raises:** None
**Retry:** No
**Side Effects:** None (pure serialization)

**Output Format:**
- Decimals: String representation
- Optional fields: None if not provided
- additional_stats: Passed through as-is

---

## Acceptance Criteria
- [ ] **AC-001:** initial_capital must be positive (> 0)
- [ ] **AC-002:** total_trades must be non-negative (>= 0)
- [ ] **AC-003:** winning_trades must be non-negative (>= 0)
- [ ] **AC-004:** losing_trades must be non-negative (>= 0)
- [ ] **AC-005:** winning_trades + losing_trades <= total_trades
- [ ] **AC-006:** roi property returns total_return
- [ ] **AC-007:** is_profitable returns True when total_return > 0
- [ ] **AC-008:** has_acceptable_drawdown returns True when max_drawdown <= threshold
- [ ] **AC-009:** has_acceptable_drawdown returns True when max_drawdown is None
- [ ] **AC-010:** Value object is immutable (frozen=True)
- [ ] **AC-011:** to_dict() serializes all fields correctly
- [ ] **AC-012:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (BacktestResult Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Initial capital positive | Risk management | initial_capital > 0 | ✅ OK - __post_init__ |
| Non-negative trades | Integrity | trades >= 0 | ✅ OK - __post_init__ |
| Trade count consistency | Integrity | win + loss <= total | ✅ OK - __post_init__ |
| ROI calculation | Pardo (2008) | total_return | ✅ OK - roi property |
| Profitability check | Trading | total_return > 0 | ✅ OK - is_profitable |
| Sharpe ratio | Sharpe (1966) | Risk-adjusted return | ✅ OK - sharpe_ratio |
| Sortino ratio | Sortino | Downside risk adj. return | ✅ OK - sortino_ratio |
| Max drawdown | Risk management | Peak-to-trough decline | ✅ OK - max_drawdown |
| Volatility | Risk metrics | Annualized std dev | ✅ OK - volatility |
| VAR 95% | Hull (2018) | 95% Value at Risk | ✅ OK - var_95 |
| Win rate | Trading | winning_trades / total_trades | ✅ OK - win_rate |
| Profit factor | Trading | avg_win / avg_loss (abs) | ✅ OK - profit_factor |
| Calmar ratio | Risk metrics | return / max_drawdown | ✅ OK - calmar_ratio |
| Omega ratio | Risk metrics | Probability-weighted returns | ✅ OK - omega_ratio |
| Drawdown threshold | Risk management | Configurable limit | ✅ OK - has_acceptable_drawdown |
| Dict serialization | Clean code | to_dict() | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and trading performance standards.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std), `typing` (std)
- **Internal:** None (value object)

---

## Required Tests
- **test_backtest_result_value_object.py:**
  - `test_create_valid_result()` - Valid result created
  - `test_negative_initial_capital()` - Raises ValueError
  - `test_negative_total_trades()` - Raises ValueError
  - `test_negative_winning_trades()` - Raises ValueError
  - `test_negative_losing_trades()` - Raises ValueError
  - `test_trade_count_exceeds_total()` - Raises ValueError (win + loss > total)
  - `test_roi_property()` - Returns total_return
  - `test_is_profitable_true()` - total_return > 0
  - `test_is_profitable_false()` - total_return <= 0
  - `test_has_acceptable_drawdown_true()` - max_drawdown <= threshold
  - `test_has_acceptable_drawdown_false()` - max_drawdown > threshold
  - `test_has_acceptable_drawdown_none()` - True when max_drawdown is None
  - `test_has_acceptable_drawdown_custom_threshold()` - Uses provided threshold
  - `test_to_dict()` - Serializes all fields
  - `test_to_dict_optional_none()` - Optional fields as None
  - `test_to_dict_decimals_as_strings()` - Decimals as strings
  - `test_sharpe_ratio()` - Sharpe ratio stored
  - `test_sortino_ratio()` - Sortino ratio stored
  - `test_max_drawdown()` - Max drawdown stored
  - `test_volatility()` - Volatility stored
  - `test_var_95()` - VAR 95% stored
  - `test_win_rate()` - Win rate stored
  - `test_profit_factor()` - Profit factor stored
  - `test_calmar_ratio()` - Calmar ratio stored
  - `test_omega_ratio()` - Omega ratio stored
  - `test_tail_ratio()` - Tail ratio stored
  - `test_regression_metrics()` - hit_rate, precision, recall, f1_score
  - `test_additional_stats()` - Custom metrics stored
  - `test_immutability()` - Cannot modify after creation

---

## Notes
- **Critical:** BacktestResultValue is a VALUE OBJECT (immutable, defined by all metrics, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Basic Metrics:**
  - initial_capital: Starting capital (must be positive)
  - final_capital: Ending capital after backtest
  - total_return: Absolute return (final - initial)
  - total_return_pct: Percentage return ((final - initial) / initial × 100)
- **Risk Metrics:**
  - sharpe_ratio: (return - rf) / volatility - risk-adjusted return (Sharpe, 1966)
  - sortino_ratio: (return - rf) / downside_deviation - downside risk adjusted
  - max_drawdown: Maximum peak-to-trough decline
  - volatility: Annualized standard deviation of returns
  - var_95: 95% Value at Risk - maximum expected loss at 95% confidence (Hull, 2018)
- **Trading Metrics:**
  - total_trades: Total number of trades executed
  - winning_trades: Number of profitable trades
  - losing_trades: Number of unprofitable trades
  - win_rate: winning_trades / total_trades (0 to 1)
  - avg_win: Average profit from winning trades
  - avg_loss: Average loss from losing trades (typically negative)
  - profit_factor: sum(wins) / abs(sum(losses)) - > 1 indicates profitability
- **Trade Level Metrics:**
  - avg_trade_duration: Average time in trade
  - avg_hold_time: Average holding period
- **Advanced Metrics:**
  - calmar_ratio: annual_return / max_drawdown
  - omega_ratio: Probability-weighted ratio of gains to losses
  - tail_ratio: Ratio of tail gains to tail losses
- **Regression Metrics:**
  - hit_rate: Percentage of correct predictions
  - precision: True positive / (true positive + false positive)
  - recall: True positive / (true positive + false negative)
  - f1_score: Harmonic mean of precision and recall
- **Additional Stats:** Dictionary for custom or strategy-specific metrics
- **Properties:**
  - roi: Alias for total_return
  - is_profitable: True if total_return > 0
  - has_acceptable_drawdown: Checks if max_drawdown within threshold (default 20%)
- **Serialization:** to_dict() converts all fields to dictionary with string values for decimals

---

## GAP Fixes Applied

### GAP-001: has_acceptable_drawdown Property with Parameter (FIXED ✅)
**Issue:** Line 91 defined `has_acceptable_drawdown` as a `@property` with a `threshold` parameter, which is invalid Python syntax (properties cannot take parameters).

**Fix Applied (2026-02-04):**
- Removed `@property` decorator
- Converted to regular instance method
- Maintains same functionality with default threshold parameter

**Validation:**
```bash
python -m py_compile app/domain/value_objects/backtest_result.py ✓ PASSED
python -c "from app.domain.value_objects.backtest_result import BacktestResultValue; ... has_acceptable_drawdown() tests" ✓ PASSED
```

**Impact:** None - this was a bug fix. The method now correctly accepts the optional threshold parameter.

---

**File Reference:** `app/domain/value_objects/backtest_result.py`
**Last Audited:** 2026-02-01
**Last GAP Fix:** 2026-02-04
