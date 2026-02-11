# metrics.py

## Purpose
Performance Metrics Calculator for Backtesting - Calculates comprehensive performance metrics including CAGR, Sharpe ratio, Sortino ratio, max drawdown, win rate, profit factor, expectancy, and López de Prado advanced metrics (stability, concentration, turnover-adjusted Sharpe).

---

## Type Definitions / Data Classes

No custom data classes defined in this file (uses domain entities and imported types).

**Domain Dependencies:**
- `PerformanceMetrics` model (from app.backtesting.models)
- `Trade` model (from app.backtesting.models)
- `AdvancedMetricsCalculator` (from app.backtesting.advanced_metrics)
- López de Prado metrics components (from app.backtesting.lopez_de_prado_metrics)

---

## Function Signatures (Contracts)

### `MetricsCalculator.__init__(risk_free_rate: Decimal = Decimal("0.02")) -> None`
**Pre:** risk_free_rate >= 0
**Post:** Calculator initialized with risk-free rate
**Raises:** None
**Retry:** No
**Side Effects:** Initializes López de Prado metrics components

**Default:** risk_free_rate = 2% annual

### `MetricsCalculator.calculate_all_metrics(
    trades: List[Trade],
    initial_capital: Decimal,
    final_capital: Decimal,
    start_date: datetime,
    end_date: datetime,
) -> PerformanceMetrics`
**Pre:** trades non-empty; initial_capital > 0; final_capital > 0; start_date < end_date
**Post:** Returns complete PerformanceMetrics object
**Raises:** ValueError if initial_capital <= 0
**Retry:** No
**Side Effects:** None (pure computation)

**Metrics Calculated:**
- **Basic:** total_trades, winning_trades, losing_trades, win_rate, total_pnl, total_pnl_percentage
- **Risk:** max_drawdown, max_drawdown_percentage, sharpe_ratio, sortino_ratio
- **Trade Statistics:** avg_win, avg_loss, largest_win, largest_loss, risk_reward_ratio
- **Advanced:** calmar_ratio, omega_ratio, ulcer_index, volatility_annualized, recovery_factor, profit_factor, skewness, kurtosis, var_95, cvar_95
- **Time:** total_days, avg_trade_duration
- **Expectancy:** Expected value per trade

### `MetricsCalculator._empty_metrics(
    initial_capital: Decimal,
    final_capital: Decimal,
    start_date: datetime,
    end_date: datetime,
) -> PerformanceMetrics`
**Pre:** initial_capital > 0; start_date < end_date
**Post:** Returns PerformanceMetrics with zero/None values
**Raises:** ValueError if initial_capital <= 0
**Retry:** No
**Side Effects:** None (pure factory)

### `MetricsCalculator._build_equity_curve(trades: List[Trade], initial_capital: Decimal) -> List[Decimal]`
**Pre:** trades is list (may be empty); initial_capital > 0
**Post:** Returns equity curve starting with initial_capital
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `MetricsCalculator._calculate_max_drawdown(equity_curve: List[Decimal]) -> Decimal`
**Pre:** equity_curve has at least 1 element
**Post:** Returns maximum drawdown (negative or zero)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `drawdown = equity - peak` (minimum value)

### `MetricsCalculator._calculate_sharpe_ratio(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns is list of Decimal
**Post:** Returns Sharpe ratio or None if insufficient data
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `(annual_return - risk_free) / annual_std`
**Annualization:** Multiplies by 252 for daily returns
**Fallback:** Uses empyrical if available, else manual calculation

### `MetricsCalculator._calculate_sortino_ratio(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns is list of Decimal
**Post:** Returns Sortino ratio or None if insufficient data
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `(annual_return - risk_free) / annual_downside_std`
**Downside Deviation:** `sqrt(mean(min(r - target, 0)^2))` where target = daily_risk_free
**Annualization:** Multiplies by √252 for daily returns

### `MetricsCalculator._calculate_risk_reward_ratio(trades: List[Trade]) -> Optional[Decimal]`
**Pre:** trades is non-empty list
**Post:** Returns risk/reward ratio or None if insufficient data
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `avg_win / avg_loss` (absolute values)
**Target:** ≥ 3:1 (for every $1 risked, expect $3 reward)

### `MetricsCalculator.calculate_cagr(
    initial_capital: Decimal,
    final_capital: Decimal,
    start_date: datetime,
    end_date: datetime,
) -> Decimal`
**Pre:** initial_capital > 0; final_capital > 0; start_date < end_date
**Post:** Returns CAGR as percentage
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `((final_capital / initial_capital)^(1/years) - 1) × 100`
**Years:** Calculated as days / 365.25

### `calculate_profit_factor(winning_trades: List[Trade], losing_trades: List[Trade]) -> Decimal`
**Pre:** Both lists are valid Trade lists
**Post:** Returns profit factor
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `gross_profit / gross_loss`
**Edge Cases:** Returns 999 if no losing trades; 0 if no trades

### `calculate_expectancy(
    winning_trades: List[Trade],
    losing_trades: List[Trade],
) -> Decimal`
**Pre:** Both lists are valid Trade lists
**Post:** Returns expected value per trade
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `(win_rate × avg_win) - (loss_rate × avg_loss)`
**Interpretation:**
- Positive: Strategy makes money on average
- Negative: Strategy loses money on average
- Zero: Break-even (before costs)

### `calculate_expectancy_with_confidence(
    winning_trades: List[Trade],
    losing_trades: List[Trade],
    confidence_level: float = 0.95,
) -> Dict[str, Decimal]`
**Pre:** Both lists are valid Trade lists; confidence_level in (0, 1)
**Post:** Returns dict with expectancy, bounds, std_error
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output Format:**
```python
{
    'expectancy': Decimal,      # Mean P&L per trade
    'lower_bound': Decimal,     # CI lower bound
    'upper_bound': Decimal,     # CI upper bound
    'std_error': Decimal        # Standard error
}
```

**Method:** T-distribution with n-1 degrees of freedom

### `calculate_f1_score(y_true: np.ndarray, y_pred: np.ndarray, average: str = "weighted") -> float`
**Pre:** y_true and y_pred have same length; average is valid
**Post:** Returns F1 score (0-1, higher is better)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `F1 = 2 × (precision × recall) / (precision + recall)`
**Averages:** 'weighted', 'macro', 'micro', 'binary'

### `calculate_matthews_corrcoef(y_true: np.ndarray, y_pred: np.ndarray) -> float`
**Pre:** y_true and y_pred have same length
**Post:** Returns MCC coefficient (-1 to +1)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Range:**
- +1: Perfect prediction
- 0: Random prediction
- -1: Total disagreement

**Formula:** `(TP × TN - FP × FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))`

### `calculate_classification_metrics_imbalanced(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
) -> Dict[str, float]`
**Pre:** y_true and y_pred have same length
**Post:** Returns comprehensive metrics dict
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output Metrics:**
- f1_weighted, f1_macro, f1_binary
- mcc (Matthews Correlation Coefficient)
- balanced_accuracy
- confusion_matrix (as list)
- true_positives, true_negatives, false_positives, false_negatives (if binary)
- pr_auc (if y_proba provided)

### `LopezDePradoMetricsCalculator.__init__(
    risk_free_rate: float = 0.02,
    stability_threshold: float = 70.0,
    transaction_cost_bps: float = 10.0,
) -> None`
**Pre:** risk_free_rate >= 0; stability_threshold in [0, 100]; transaction_cost_bps >= 0
**Post:** Calculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Initializes sub-calculators

### `LopezDePradoMetricsCalculator.combine_strategy_sharpes(
    sharpes: List[float],
    returns_matrix: np.ndarray,
    method: str = "optimal",
) -> SharpeCombinationResult`
**Pre:** sharpes non-empty; returns_matrix is T×N matrix
**Post:** Returns combined Sharpe with weights
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Methods:** 'optimal', 'hierarchical', 'spectral', 'average'

### `LopezDePradoMetricsCalculator.validate_portfolio_stability(
    weights_history: List[np.ndarray],
    returns_history: Optional[np.ndarray] = None,
    period_length_days: int = 30,
) -> PortfolioStabilityMetrics`
**Pre:** weights_history non-empty
**Post:** Returns stability metrics
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `LopezDePradoMetricsCalculator.calculate_turnover_adjusted_metrics(
    returns: np.ndarray,
    weights_history: List[np.ndarray],
    period_length_days: int = 30,
) -> TurnoverAdjustedMetrics`
**Pre:** returns and weights_history compatible
**Post:** Returns turnover-adjusted Sharpe
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `LopezDePradoMetricsCalculator.analyze_portfolio_concentration(weights: np.ndarray) -> ConcentrationMetrics`
**Pre:** weights sums to 1.0
**Post:** Returns concentration metrics
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `LopezDePradoMetricsCalculator.generate_comprehensive_report(
    sharpes: List[float],
    returns_matrix: np.ndarray,
    weights_history: List[np.ndarray],
    portfolio_returns: np.ndarray,
    current_weights: np.ndarray,
) -> Dict[str, Any]`
**Pre:** All inputs compatible and non-empty
**Post:** Returns comprehensive report with all metrics
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Report Contents:**
- overall_score (0-100)
- sharpe_combination metrics
- stability metrics
- turnover metrics
- concentration metrics
- recommendations list
- timestamp

---

## Acceptance Criteria
- [ ] **AC-001:** calculate_all_metrics() returns PerformanceMetrics
- [ ] **AC-002:** Sharpe ratio uses empyrical if available
- [ ] **AC-003:** Sharpe ratio annualized with √252
- [ ] **AC-004:** Sortino ratio uses downside deviation
- [ ] **AC-005:** Max drawdown is negative or zero
- [ ] **AC-006:** CAGR formula is correct
- [ ] **AC-007:** Expectancy formula is (win_rate × avg_win) - (loss_rate × avg_loss)
- [ ] **AC-008:** Risk/reward ratio is avg_win / avg_loss
- [ ] **AC-009:** F1 score handles imbalanced data
- [ ] **AC-010:** MCC returns value in [-1, +1]
- [ ] **AC-011:** López de Prado calculator combines Sharpes
- [ ] **AC-012:** Portfolio stability validation works
- [ ] **AC-013:** Turnover-adjusted Sharpe calculated
- [ ] **AC-014:** Concentration analysis returns HHI and effective N
- [ ] **AC-015:** Comprehensive report includes recommendations
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

### Reglas ESPECÍFICAS de este archivo (Metrics Calculator):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Service pattern | Clean Architecture | Calculation service | ✅ OK - MetricsCalculator |
| Sharpe ratio | Sharpe (1966) | Risk-adjusted return | ✅ OK - _calculate_sharpe_ratio() |
| Sortino ratio | Sortino (1992) | Downside risk | ✅ OK - _calculate_sortino_ratio() |
| CAGR | Investment standard | Compound annual growth | ✅ OK - calculate_cagr() |
| Max drawdown | Risk management | Peak-to-trough | ✅ OK - _calculate_max_drawdown() |
| Expectancy | Trading | Expected value per trade | ✅ OK - calculate_expectancy() |
| Profit factor | Trading | Gross profit / gross loss | ✅ OK - calculate_profit_factor() |
| Imbalanced metrics | López de Prado (2018) | F1, MCC | ✅ OK - calculate_*() |
| López de Prado metrics | López de Prado (2020) | Advanced ML metrics | ✅ OK - LopezDePradoMetricsCalculator |
| Sharpe combination | López de Prado (2020) | Chapter 8 | ✅ OK - combine_strategy_sharpes() |
| Portfolio stability | López de Prado (2020) | Chapter 9 | ✅ OK - validate_portfolio_stability() |
| Turnover analysis | López de Prado (2020) | Chapter 10 | ✅ OK - calculate_turnover_adjusted_metrics() |
| Concentration | López de Prado (2020) | Chapter 11 | ✅ OK - analyze_portfolio_concentration() |
| Optional dependency | Clean code | Graceful degradation | ✅ OK - EMPYRICAL_AVAILABLE |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and López de Prado (2018, 2020) for ML metrics standards.

---

## Dependencies
- **External:** `numpy`, `decimal` (std), `datetime` (std), `typing` (std), `logging` (std)
- **Optional:** `empyrical` (for Sharpe/Sortino), `scipy` (for t-distribution), `sklearn` (for classification metrics)
- **Internal:**
  - `app.backtracking.advanced_metrics.AdvancedMetricsCalculator`
  - `app.backtesting.lopez_de_prado_metrics.*`
  - `app.backtesting.models.PerformanceMetrics`
  - `app.backtesting.models.Trade`

---

## Required Tests
- **test_metrics.py:**
  - `test_metrics_calculator_init()` - Initializes with risk-free rate
  - `test_calculate_all_metrics()` - Returns PerformanceMetrics
  - `test_empty_metrics()` - Returns zero/None values
  - `test_build_equity_curve()` - Starts with initial_capital
  - `test_max_drawdown()` - Returns negative or zero
  - `test_sharpe_ratio_empyrical()` - Uses empyrical if available
  - `test_sharpe_ratio_manual()` - Manual calculation fallback
  - `test_sharpe_ratio_annualized()` - Multiplied by √252
  - `test_sortino_ratio_downside_deviation()` - Uses downside std
  - `test_risk_reward_ratio()` - Avg win / avg loss
  - `test_cagr_formula()` - Correct calculation
  - `test_cagr_validation()` - Raises on invalid inputs
  - `test_profit_factor()` - Gross profit / gross loss
  - `test_profit_factor_no_losses()` - Returns 999
  - `test_expectancy()` - (win_rate × avg_win) - (loss_rate × avg_loss)
  - `test_expectancy_positive()` - Positive when profitable
  - `test_expectancy_confidence()` - Returns bounds
  - `test_f1_score()` - Returns 0-1
  - `test_matthews_corrcoef()` - Returns -1 to +1
  - `test_classification_metrics_imbalanced()` - All metrics present
  - `test_lopez_de_prado_init()` - Initializes sub-calculators
  - `test_combine_sharpes_optimal()` - Returns combined Sharpe
  - `test_validate_stability()` - Returns stability metrics
  - `test_turnover_adjusted()` - Adjusts Sharpe for turnover
  - `test_concentration_analysis()` - Returns HHI, effective N
  - `test_comprehensive_report()` - Includes all 4 sections
  - `test_overall_score()` - Returns 0-100
  - `test_recommendations()` - Returns actionable suggestions

---

## Notes
- **Critical:** MetricsCalculator is an APPLICATION SERVICE (Clean Architecture)
- **López de Prado Reference:** "Machine Learning for Asset Managers" (2020) - Advanced ML metrics
- **Sharpe Ratio:** Industry standard for risk-adjusted returns
  - Formula: `(return - risk_free) / volatility`
  - Annualization: Multiply by √252 for daily returns
  - Uses empyrical library if available (industry standard)
- **Sortino Ratio:** Improvement over Sharpe that only penalizes downside risk
  - Formula: `(return - risk_free) / downside_std`
  - Downside deviation: sqrt(mean(min(r - target, 0)²))
  - Target: daily risk-free rate
- **CAGR:** Compound Annual Growth Rate
  - Formula: `((final / initial)^(1/years) - 1) × 100`
  - Measures annualized growth rate
- **Max Drawdown:** Maximum peak-to-trough decline
  - Always negative or zero
  - Bounded by -initial_capital (can't lose more than you started with)
- **Expectancy:** Expected value per trade
  - Positive = profitable strategy
  - Negative = unprofitable strategy
  - Critical for determining long-term viability
- **Profit Factor:** Gross profit / gross loss
  - > 1: Profitable
  - < 1: Unprofitable
  - Returns 999 if no losing trades (perfect scenario)
- **F1 Score:** Harmonic mean of precision and recall
  - Better than accuracy for imbalanced data
  - Used for ML classification evaluation
- **MCC (Matthews Correlation Coefficient):** Balanced measure for imbalanced binary classification
  - Range: -1 to +1
  - Considered one of the best metrics for imbalanced data
- **López de Prado Advanced Metrics:**
  1. **Sharpe Combination:** Optimal combination of multiple strategies
  2. **Portfolio Stability:** Validates consistency across time periods
  3. **Turnover-Adjusted Sharpe:** Adjusts for transaction costs
  4. **Concentration Analysis:** HHI, effective N, diversification metrics
- **Optional Dependencies:** Graceful degradation when empyrical, scipy, or sklearn unavailable
- **NumPy 2.0 Compatibility:** Uses np.ndarray instead of np aliases

---

**File Reference:** `app/backtesting/metrics.py`
**Last Audited:** 2026-02-01
