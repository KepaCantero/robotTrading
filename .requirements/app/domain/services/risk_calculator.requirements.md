# risk_calculator.py

## Purpose
Risk Calculator Domain Service - Provides domain logic for calculating risk metrics for portfolios and positions. Based on John Hull's risk management principles and industry-standard risk calculations.

---

## Type Definitions / Data Classes

### RiskMetrics(dataclass)
```python
@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or position."""

    # Value at Risk metrics
    var_95: Decimal  # Value at Risk at 95% confidence
    var_99: Decimal  # Value at Risk at 99% confidence

    # Volatility metrics
    daily_volatility: Decimal
    annualized_volatility: Decimal

    # Drawdown metrics
    max_drawdown: Decimal
    avg_drawdown: Decimal

    # Concentration metrics
    concentration: Decimal  # Highest position concentration
    herfindahl_index: Decimal  # Portfolio concentration index

    # Risk limits
    utilisation: Decimal  # Risk utilisation as % of limits
```

**Purpose:** Container for all risk metrics returned by calculations
**Validation:** All values are Decimal for precision
**Risk Metrics:** VaR, volatility, drawdown, concentration, risk utilisation

### RiskCalculator
```python
class RiskCalculator:
    """
    Domain service for calculating risk metrics.

    Provides pure risk calculation logic without external dependencies.
    """
```

**Pattern:** Domain Service (DDD)
**Purpose:** Pure risk calculation logic
**Dependency:** None (stateless calculator with configurable risk_free_rate)

---

## Function Signatures (Contracts)

### `RiskCalculator.__init__(risk_free_rate: Decimal = Decimal("0.02")) -> None`
**Pre:** risk_free_rate >= 0
**Post:** Calculator initialized with risk-free rate
**Raises:** None
**Retry:** No
**Side Effects:** Stores _risk_free_rate

**Default:** 2% annual risk-free rate

### `RiskCalculator.calculate_portfolio_risk(portfolio: Portfolio) -> RiskMetrics`
**Pre:** portfolio is valid entity with positions
**Post:** Returns RiskMetrics with all fields calculated
**Raises:** None (returns zero metrics if empty portfolio)
**Retry:** No
**Side Effects:** None (pure calculation)

**Calculation Steps:**
1. Get position values and total portfolio value
2. Return zero metrics if total_value == 0 or no positions
3. Calculate concentration and Herfindahl index
4. Estimate volatility from position weights
5. Calculate parametric VaR at 95% and 99%
6. Estimate max drawdown and average drawdown
7. Calculate risk utilisation vs limits

**Formulas:**
- `annual_vol = daily_vol * sqrt(252)`
- `var_95 = portfolio_value * daily_vol * 1.65`
- `var_99 = portfolio_value * daily_vol * 2.33`
- `herfindahl = sum(weight_i^2)` for all positions

### `RiskCalculator.calculate_position_risk(position: Position, portfolio_value: Decimal) -> Dict[str, Decimal]`
**Pre:** position is valid; portfolio_value > 0
**Post:** Returns dict with position risk metrics
**Raises:** None
**Retry:** No
**Side Effects:** None (pure calculation)

**Returns:**
```python
{
    "position_value": Decimal,
    "position_pct": Decimal,  # % of portfolio
    "risk_amount": Decimal,  # abs(unrealized_pnl) or 5% of value
    "unrealized_pnl": Decimal,
    "pnl_percent": Decimal,
}
```

### `RiskCalculator.calculate_sharpe_ratio(returns: List[Decimal], annualized: bool = True) -> Decimal`
**Pre:** returns has at least 2 values
**Post:** Returns Sharpe ratio (mean - rf) / std
**Raises:** None (returns 0 if insufficient data)
**Retry:** No
**Side Effects:** None (pure calculation)

**Formula:** `(mean_return - risk_free_rate) / std_return * sqrt(252)` if annualized

### `RiskCalculator.calculate_sortino_ratio(returns: List[Decimal], target_return: Decimal = Decimal("0"), annualized: bool = True) -> Decimal`
**Pre:** returns has at least 2 values
**Post:** Returns Sortino ratio using downside deviation
**Raises:** None (returns 999 if no downside)
**Retry:** No
**Side Effects:** None (pure calculation)

**Formula:** `(mean_return - target_return) / downside_deviation * sqrt(252)`

**Special Case:** Returns 999 if no downside returns (infinite Sortino)

### `RiskCalculator.calculate_beta(asset_returns: List[Decimal], market_returns: List[Decimal]) -> Decimal`
**Pre:** len(asset_returns) == len(market_returns) >= 2
**Post:** Returns beta (covariance / variance)
**Raises:** None (returns 1.0 if insufficient data)
**Retry:** No
**Side Effects:** None (pure calculation)

**Formula:** `cov(asset, market) / var(market)`

### `RiskCalculator._calculate_concentration(portfolio: Portfolio) -> Decimal`
**Pre:** portfolio is valid
**Post:** Returns highest position concentration %
**Raises:** None
**Retry:** No
**Side Effects:** None

**Implementation:** `portfolio.get_max_concentration()[1]`

### `RiskCalculator._calculate_herfindahl(portfolio: Portfolio) -> Decimal`
**Pre:** portfolio is valid with positions
**Post:** Returns Herfindahl-Hirschman Index (HHI)
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:** `sum(weight_i^2)` for all positions

**Interpretation:** Lower = more diversified, Higher = more concentrated

### `RiskCalculator._estimate_portfolio_volatility(weights: List[Decimal], values: List[Decimal]) -> Decimal`
**Pre:** weights and values have same length
**Post:** Returns estimated daily volatility
**Raises:** None
**Retry:** No
**Side Effects:** None

**Simplified:** Assumes 2% vol per position * sqrt(n) for uncorrelated

**Note:** This is a simplification - production should use covariance matrix

### `RiskCalculator._calculate_var(portfolio_value: Decimal, volatility: Decimal, z_score: Decimal) -> Decimal`
**Pre:** All values positive
**Post:** Returns parametric VaR
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:** `portfolio_value * volatility * z_score`

**Z-scores:** 1.65 for 95%, 2.33 for 99%

### `RiskCalculator._estimate_max_drawdown(weights: List[Decimal]) -> Decimal`
**Pre:** weights non-empty
**Post:** Returns estimated max drawdown
**Raises:** None
**Retry:** No
**Side Effects:** None

**Simplified:** `max_weight * 0.2` (assumes 20% drawdown on largest position)

### `RiskCalculator._calculate_risk_utilisation(portfolio: Portfolio) -> Decimal`
**Pre:** portfolio is valid
**Post:** Returns risk utilisation as % (capped at 100%)
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:** `(current_exposure / max_exposure) * 100`

### `RiskCalculator.get_risk_summary(metrics: RiskMetrics) -> Dict[str, str]`
**Pre:** metrics is valid
**Post:** Returns human-readable risk assessment
**Raises:** None
**Retry:** No
**Side Effects:** None (pure formatting)

**Returns:**
```python
{
    "volatility_level": "Low" | "Medium" | "High",
    "concentration_level": "Well diversified" | "Moderately concentrated" | "Highly concentrated",
    "utilisation_level": "Low" | "Moderate" | "High" utilisation,
    "var_95_pct": "X.X%",
}
```

---

## Acceptance Criteria
- [ ] **AC-001:** RiskMetrics is a dataclass with 9 Decimal fields
- [ ] **AC-002:** calculate_portfolio_risk() returns zero metrics for empty portfolio
- [ ] **AC-003:** calculate_portfolio_risk() uses sqrt(252) for annualization
- [ ] **AC-004:** VaR calculations use z-scores 1.65 (95%) and 2.33 (99%)
- [ ] **AC-005:** Herfindahl index calculates sum of squared weights
- [ ] **AC-006:** Sharpe ratio returns 0 for insufficient data
- [ ] **AC-007:** Sortino ratio returns 999 for no downside
- [ ] **AC-008:** Beta returns 1.0 for insufficient data or zero variance
- [ ] **AC-009:** calculate_position_risk() returns 5 risk metrics
- [ ] **AC-010:** get_risk_summary() classifies volatility/ concentration/utilisation
- [ ] **AC-011:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Risk Calculator Domain Service):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Domain Service pattern | DDD | Pure domain logic | ✅ OK - No external dependencies |
| Decimal precision | BASE_RULES.md (TYP-001) | All monetary values Decimal | ✅ OK - All Decimal |
| Hull risk principles | Hull, Ch. 18 | VaR calculation | ✅ OK - Parametric VaR |
| Herfindahl index | Portfolio theory | Concentration measure | ✅ OK - Implemented |
| Sharpe ratio | Modern Portfolio Theory | Risk-adjusted return | ✅ OK - Correct formula |
| Sortino ratio | Post-modern portfolio theory | Downside deviation | ✅ OK - Implemented |
| Beta calculation | CAPM theory | Market sensitivity | ✅ OK - Cov/var formula |
| Risk utilisation | Risk management | Exposure vs limits | ✅ OK - Percentage |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**GAPS IDENTIFIED:**
| Rule | Source | Issue | Priority |
|------|--------|-------|----------|
| Historical VaR | Hull Ch. 18 | Missing historical simulation | P1 |
| Covariance matrix | MPT theory | Volatility uses simplification | P1 |
| CVaR/Expected Shortfall | Basel III | Missing conditional VaR | P2 |
| Stress testing | Risk management | Missing scenario analysis | P2 |
| Greeks (options) | Hull Ch. 17 | Not implemented | P3 |

---

## Dependencies
- **External:** numpy (for statistical calculations)
- **Internal:**
  - `app.domain.entities.portfolio.Portfolio`
  - `app.domain.entities.portfolio.Position`

---

## Required Tests
- **test_risk_calculator.py:**
  - `test_init_default_risk_free_rate()` - Default 2%
  - `test_init_custom_risk_free_rate()` - Custom rate
  - `test_calculate_portfolio_risk_empty()` - Returns zero metrics
  - `test_calculate_portfolio_risk_single_position()` - Single position
  - `test_calculate_portfolio_risk_multiple_positions()` - Multiple positions
  - `test_var_95_uses_z_score_1_65()` - Correct z-score
  - `test_var_99_uses_z_score_2_33()` - Correct z-score
  - `test_annualized_volatility_uses_sqrt_252()` - Correct annualization
  - `test_herfindahl_index_calculation()` - Sum of squared weights
  - `test_concentration_calculation()` - Max position %
  - `test_risk_utilisation_calculation()` - Current vs max exposure
  - `test_risk_utilisation_capped_at_100()` - Cap logic
  - `test_sharpe_ratio_empty_returns()` - Returns 0
  - `test_sharpe_ratio_single_return()` - Returns 0
  - `test_sharpe_ratio_correct_formula()` - (mean - rf) / std
  - `test_sharpe_ratio_annualized()` - Multiplies by sqrt(252)
  - `test_sortino_ratio_no_downside()` - Returns 999
  - `test_sortino_ratio_downside_deviation()` - Correct formula
  - `test_beta_empty_arrays()` - Returns 1.0
  - `test_beta_mismatched_lengths()` - Returns 1.0
  - `test_beta_zero_variance()` - Returns 1.0
  - `test_beta_correct_formula()` - Cov/var
  - `test_calculate_position_risk()` - All 5 metrics
  - `test_position_risk_pct_of_portfolio()` - Correct %
  - `test_get_risk_summary_low_volatility()` - < 15%
  - `test_get_risk_summary_medium_volatility()` - 15-25%
  - `test_get_risk_summary_high_volatility()` - > 25%
  - `test_get_risk_summary_well_diversified()` - < 10%
  - `test_get_risk_summary_highly_concentrated()` - > 25%
  - `test_get_risk_summary_low_utilisation()` - < 50%
  - `test_get_risk_summary_high_utilisation()` - > 80%

---

## Notes
- **Critical:** This is a DOMAIN SERVICE - pure calculation logic only
- **Domain Service Pattern (DDD):**
  - Stateless calculator (no persistent state)
  - Pure functions (no side effects)
  - Domain logic encapsulation
  - No infrastructure dependencies
- **Risk Metrics (John Hull References):**
  - **VaR (Chapter 18):** Maximum loss at confidence level
  - **Volatility:** Standard deviation of returns
  - **Beta:** Covariance with market / Market variance
  - **Sharpe Ratio:** (Return - Risk-free) / Volatility
  - **Sortino Ratio:** Uses downside deviation only
- **Simplifications (Phase 0.3):**
  - Portfolio volatility assumes uncorrelated positions
  - Drawdown is estimated from position weights
  - Parametric VaR (not historical simulation)
  - No conditional VaR (CVaR/Expected Shortfall)
- **Production Improvements Needed:**
  - Use covariance matrix for portfolio volatility
  - Implement historical VaR simulation
  - Add conditional VaR (Expected Shortfall)
  - Add stress testing scenarios
  - Use actual historical returns for drawdown
- **Concentration Metrics:**
  - **Herfindahl-Hirschman Index:** Sum of squared weights
    - < 0.10 = Highly diversified
    - 0.10-0.18 = Moderately concentrated
    - > 0.18 = Highly concentrated
  - **Max Concentration:** Largest single position %
- **Risk Utilisation:**
  - Current exposure vs. max allowed exposure
  - Capped at 100% for display
  - Used for position sizing and limits
- **Z-Scores for VaR:**
  - 95% confidence: 1.645 (rounded to 1.65)
  - 99% confidence: 2.326 (rounded to 2.33)
- **Annualization Factor:**
  - Daily to annual: multiply by sqrt(252)
  - Assumes 252 trading days per year
- **Infinite Sortino (999):**
  - Returned when no downside returns exist
  - Indicates perfect downside protection
- **Beta Default (1.0):**
  - Returned when insufficient data
  - Assumes market-like sensitivity
- **Production Rule:** Always use Decimal for monetary calculations, never float

---

**File Reference:** `app/domain/services/risk_calculator.py`
**Last Audited:** 2026-02-01
