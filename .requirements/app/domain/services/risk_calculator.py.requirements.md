# risk_calculator.py

## Purpose
Risk Calculator domain service - provides pure risk calculation logic for portfolios and positions including VaR, volatility, drawdown, concentration, and Sharpe/Sortino ratios.

---

## Type Definitions / Data Classes

### RiskMetrics DataClass
```python
@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or position."""

    # Value at Risk metrics
    var_95: Decimal                          # REQUIRED - VaR at 95% confidence
    var_99: Decimal                          # REQUIRED - VaR at 99% confidence

    # Volatility metrics
    daily_volatility: Decimal                # REQUIRED - Daily volatility
    annualized_volatility: Decimal           # REQUIRED - Annualized volatility

    # Drawdown metrics
    max_drawdown: Decimal                    # REQUIRED - Maximum drawdown
    avg_drawdown: Decimal                    # REQUIRED - Average drawdown

    # Concentration metrics
    concentration: Decimal                   # REQUIRED - Highest position concentration
    herfindahl_index: Decimal                # REQUIRED - Portfolio concentration index

    # Risk limits
    utilisation: Decimal                     # REQUIRED - Risk utilisation as % of limits
```

### RiskCalculator Class
```python
class RiskCalculator:
    """Domain service for calculating risk metrics."""

    _risk_free_rate: Decimal                  # PRIVATE - Risk-free rate for Sharpe ratio
```

---

## Function Signatures (Contracts)

### Initialization

### `RiskCalculator.__init__(self, risk_free_rate: Decimal = Decimal("0.02")) -> None`
**Pre:** None
**Post:** Calculator initialized with risk-free rate
**Raises:** No
**Retry:** No
**Side Effects:** None

**Default:** 2% annual risk-free rate

### Portfolio Risk Methods

### `calculate_portfolio_risk(self, portfolio: Portfolio) -> RiskMetrics`
**Pre:** portfolio has positions
**Post:** Returns comprehensive risk metrics
**Raises:** No
**Retry:** No
**Side Effects:** None

**Returns:**
- VaR at 95% and 99% confidence
- Daily and annualized volatility
- Max and average drawdown
- Concentration metrics
- Herfindahl index
- Risk utilisation

**Edge Cases:**
- Returns zero metrics if total_value == 0
- Returns zero metrics if no positions

### `calculate_position_risk(self, position: Position, portfolio_value: Decimal) -> Dict[str, Decimal]`
**Pre:** position valid
**Post:** Returns position risk metrics
**Raises:** No
**Retry:** No
**Side Effects:** None

**Returns:**
- position_value: Total position value
- position_pct: Position as % of portfolio
- risk_amount: Risk amount (unrealized loss or 5%)
- unrealized_pnl: Current unrealized P&L
- pnl_percent: P&L as percentage

### Ratio Calculation Methods

### `calculate_sharpe_ratio(self, returns: List[Decimal], annualized: bool = True) -> Decimal`
**Pre:** returns has at least 2 values
**Post:** Returns Sharpe ratio
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (mean_return - risk_free_rate) / std_return

**Annualization:** Multiplies by sqrt(252) if annualized=True

**Edge Cases:**
- Returns 0 if returns empty
- Returns 0 if len(returns) < 2
- Returns 0 if std_return == 0

### `calculate_sortino_ratio(self, returns: List[Decimal], target_return: Decimal = Decimal("0"), annualized: bool = True) -> Decimal`
**Pre:** returns has at least 2 values
**Post:** Returns Sortino ratio
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (mean_return - target_return) / downside_deviation

**Downside Deviation:** Std dev of returns below target

**Annualization:** Multiplies by sqrt(252) if annualized=True

### Helper Methods

### `_calculate_concentration(self, portfolio: Portfolio) -> Decimal`
**Pre:** portfolio has positions
**Post:** Returns highest position concentration
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** max(position_value / total_value)

### `_calculate_herfindahl(self, portfolio: Portfolio) -> Decimal`
**Pre:** portfolio has positions
**Post:** Returns Herfindahl-Hirschman Index
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** sum(weight^2 for each position)
- Range: 1/n to 1.0
- Higher = more concentrated

### `_estimate_portfolio_volatility(self, weights: List[Decimal], values: List[Decimal]) -> Decimal`
**Pre:** weights and values same length
**Post:** Returns estimated portfolio volatility
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** Simplified weighted std dev

### `_calculate_var(self, total_value: Decimal, volatility: Decimal, z_score: Decimal) -> Decimal`
**Pre:** total_value > 0
**Post:** Returns Value at Risk
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** total_value * volatility * z_score

**Z-Scores:**
- 95% confidence: 1.65
- 99% confidence: 2.33

### `_estimate_max_drawdown(self, weights: List[Decimal]) -> Decimal`
**Pre:** weights not empty
**Post:** Returns estimated max drawdown
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** Simplified estimation based on weights

### `_calculate_risk_utilisation(self, portfolio: Portfolio) -> Decimal`
**Pre:** portfolio has risk parameters
**Post:** Returns risk utilisation as percentage
**Raises:** No
**Retry:** No
**Side Effects:** None

**Calculation:** (used_risk / max_risk) * 100

---

## Acceptance Criteria
- [ ] Risk-free rate configurable (default 2%)
- [ ] Portfolio risk returns all metrics
- [ ] Portfolio risk handles empty portfolios (returns zeros)
- [ ] Position risk calculated relative to portfolio
- [ ] Sharpe ratio calculated correctly
- [ ] Sharpe ratio annualized with sqrt(252)
- [ ] Sortino ratio uses downside deviation
- [ ] VaR calculated at 95% and 99% confidence
- [ ] Volatility annualized with sqrt(252)
- [ ] Concentration is max position weight
- [ ] Herfindahl index calculated
- [ ] Risk utilisation calculated
- [ ] All calculations use Decimal
- [ ] Numpy used for statistical operations

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Decimal Precision | CRITICAL_RULES.md | Use Decimal for money | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Error Handling | BASE_RULES.md | No exceptions raised | ✅ OK |
| Domain Service | BASE_RULES.md | Stateless service | ✅ OK |
| Pure Functions | BASE_RULES.md | No side effects | ✅ OK |
| Numpy Integration | BASE_RULES.md | Convert for calculation | ✅ OK |
| Annualization | CRITICAL_RULES.md | sqrt(252) for daily | ✅ OK |

---

## Dependencies
- **External:** dataclasses, decimal, typing, numpy
- **Internal:**
  - app.domain.entities.portfolio.Portfolio
  - app.domain.entities.position.Position

---

## Required Tests
- **test_risk_calculator.py:**
  - Test RiskCalculator.__init__ with default risk-free rate
  - Test RiskCalculator.__init__ with custom risk-free rate
  - Test calculate_portfolio_risk with positions
  - Test calculate_portfolio_risk with empty portfolio (returns zeros)
  - Test calculate_position_risk metrics
  - Test calculate_position_risk with zero portfolio_value
  - Test calculate_sharpe_ratio with returns
  - Test calculate_sharpe_ratio with empty returns (returns 0)
  - Test calculate_sharpe_ratio with single return (returns 0)
  - Test calculate_sharpe_ratio with zero volatility (returns 0)
  - Test calculate_sharpe_ratio annualization
  - Test calculate_sortino_ratio with returns
  - Test calculate_sortino_ratio with target_return
  - Test calculate_sortino_ratio annualization
  - Test _calculate_concentration returns max weight
  - Test _calculate_herfindahl calculation
  - Test _calculate_var with different z-scores
  - Test _estimate_max_drawdown calculation
  - Test _calculate_risk_utilisation
  - Test all metrics use Decimal
  - Test numpy integration for statistics

---

## Notes
- CRITICAL: This is a core domain service
- Pure risk calculation logic (no external dependencies)
- Stateless (all state passed as parameters)
- Uses numpy for statistical operations
- All financial values use Decimal
- Annualization uses sqrt(252) for trading days
- VaR uses parametric approach (simplified)
- Concentration metrics for diversification analysis
- Sharpe/Sortino for risk-adjusted returns
