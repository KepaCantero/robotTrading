# quality_screen.py

## Purpose
Quality Investing strategy domain service - selects stocks based on profitability, financial health, and earnings quality metrics.

---

## Type Definitions / Data Classes

### QualitySignal (Enum)
```python
class QualitySignal(str, Enum):
    HIGH_QUALITY = "high_quality"      # Top quality stocks (score >= 0.8)
    GOOD_QUALITY = "good_quality"      # Above average quality (score >= 0.6)
    AVERAGE_QUALITY = "average_quality"  # Average quality (score >= 0.4)
    LOW_QUALITY = "low_quality"        # Below average quality (score >= 0.2)
    POOR_QUALITY = "poor_quality"      # Poor quality (score < 0.2)
```

### QualityMetrics
```python
@dataclass
class QualityMetrics:
    symbol: str                         # REQUIRED - Stock symbol

    # Profitability metrics
    gross_profit_margin: float          # REQUIRED - Gross profit / revenue
    operating_profit_margin: float      # REQUIRED - Operating income / revenue
    net_profit_margin: float            # REQUIRED - Net income / revenue
    return_on_equity: float             # REQUIRED - ROE
    return_on_assets: float             # REQUIRED - ROA
    return_on_invested_capital: float   # REQUIRED - ROIC
    free_cash_flow_margin: float        # REQUIRED - FCF / revenue

    # Financial health
    current_ratio: float                # REQUIRED - Current assets / current liabilities
    quick_ratio: float                  # REQUIRED - (Current assets - inventory) / current liabilities
    debt_to_equity: float               # REQUIRED - D/E ratio
    interest_coverage: float            # REQUIRED - EBIT / interest expense
    altman_z_score: float               # REQUIRED - Bankruptcy risk score

    # Earnings quality
    accruals: float                     # REQUIRED - Net income - cash flow from operations
    earnings_smoothness: float          # REQUIRED - Std dev of earnings (lower is better)
    earnings_consistency: float         # REQUIRED - Years of positive earnings

    # Growth metrics
    revenue_growth: float               # REQUIRED - Revenue CAGR
    earnings_growth: float              # REQUIRED - Earnings CAGR
    fcf_growth: float                   # REQUIRED - Free cash flow CAGR

    # Valuation (for quality-adjusted value)
    price_to_book: float                # REQUIRED - P/B ratio
    price_to_earnings: float            # REQUIRED - P/E ratio
    enterprise_value_to_ebitda: float   # REQUIRED - EV/EBITDA
```

**Properties:**
- `profitability_score` - Returns score (0-1) based on margins, ROE, ROIC, FCF
- `financial_health_score` - Returns score (0-1) based on liquidity, solvency, coverage
- `overall_quality_score` - Returns composite score: 50% profitability + 30% health + 20% earnings quality
- `quality_category` - Returns QualitySignal based on overall_score
- `is_quality_stock(threshold)` - Returns True if overall_quality_score >= threshold

### QualityPortfolio
```python
@dataclass
class QualityPortfolio:
    positions: Dict[str, float]         # REQUIRED - Symbol -> weight
    portfolio_quality_score: float      # REQUIRED - Weighted avg quality score
    portfolio_profitability: float      # REQUIRED - Weighted avg profitability
    portfolio_financial_health: float   # REQUIRED - Weighted avg financial health
```

**Properties:**
- `quality_grade` - Returns QualitySignal based on portfolio_quality_score

---

## Function Signatures (Contracts)

### `QualityInvesting.__init__(min_quality_score, min_roe, min_profit_margin, max_debt_to_equity, min_interest_coverage, quality_weight, value_weight) -> None`
**Pre:** min_quality_score in [0, 1]; min_roe >= 0; min_profit_margin >= 0; max_debt_to_equity >= 0; min_interest_coverage >= 0; quality_weight + value_weight = 1
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** No
**Side Effects:** None (initialization only)

### `screen_quality_stocks(quality_metrics) -> List[str]`
**Pre:** quality_metrics is dict of symbol -> QualityMetrics
**Post:** Returns list of symbols passing all screening criteria
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_passes_screen(metrics) -> bool` (private)
**Pre:** metrics valid
**Post:** Returns True if stock passes all screening criteria (quality >= 0.6, ROE >= 10%, margin >= 5%, D/E <= 1.0, coverage >= 2, Z-score >= 1.8)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `rank_quality_stocks(quality_metrics) -> List[Tuple[str, float]]`
**Pre:** quality_metrics is dict of symbol -> QualityMetrics
**Post:** Returns list of (symbol, score) sorted by score (descending)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_calculate_quality_value_score(metrics) -> float` (private)
**Pre:** metrics valid
**Post:** Returns composite score: 70% quality + 30% value (inverted P/B, P/E, EV/EBITDA)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `construct_portfolio(quality_metrics, capital, max_positions, min_weight, max_weight) -> QualityPortfolio`
**Pre:** quality_metrics non-empty; capital > 0; max_positions >= 1; 0 < min_weight <= max_weight <= 1
**Post:** Returns quality portfolio with weights summing to 1.0
**Raises:** None (returns empty portfolio if no stocks pass screen)
**Retry:** No
**Side Effects:** None (pure computation)

### `_apply_weight_constraints(weights, min_weight, max_weight) -> Dict[str, float]` (private)
**Pre:** weights non-empty; 0 < min_weight <= max_weight <= 1
**Post:** Returns weights with min/max constraints applied
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `generate_signal(metrics, current_price, fair_value) -> QualitySignal`
**Pre:** metrics valid; current_price > 0; fair_value >= 0
**Post:** Returns QualitySignal based on quality category and valuation
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_gross_profitability_premium(quality_metrics, returns) -> Tuple[float, float]`
**Pre:** quality_metrics and returns have matching symbols
**Post:** Returns (high_gp_return, low_gp_return) comparing high (>40%) vs low (<20%) gross margin stocks
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Screening validates quality score, ROE, profit margin, D/E, interest coverage, Altman Z-score
- [ ] **AC-002:** Profitability score weights: gross margin (20%), operating margin (20%), ROE (20%), ROIC (20%), FCF margin (20%)
- [ ] **AC-003:** Financial health score weights: current ratio (20%), quick ratio (20%), D/E (30%), interest coverage (30%)
- [ ] **AC-004:** Overall quality = 50% profitability + 30% financial health + 20% earnings quality
- [ ] **AC-005:** Altman Z-score < 1.8 indicates distress zone (exclude)
- [ ] **AC-006:** Quality-value composite = 70% quality + 30% value
- [ ] **AC-007:** All public methods have complete type hints
- [ ] **AC-008:** NumPy 2.0 compatibility
- [ ] **AC-009:** All functions have docstrings following Google style

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Quality Investing):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate quality metrics range | ✅ OK - Checks in _passes_screen |
| Gross profitability | Novy-Marx (2013) | GP > 40% indicates high quality | ✅ OK - profitability_score |
| ROE threshold | Quality standard | ROE > 15% excellent | ✅ OK - profitability_score |
| ROIC threshold | Quality standard | ROIC > 12% excellent | ✅ OK - profitability_score |
| Altman Z-score | Altman (1968) | < 1.8 distress, > 3 safe | ✅ OK - _passes_screen |
| Debt-to-equity | Financial health | < 0.5 excellent, < 1.0 acceptable | ✅ OK - financial_health_score |
| Interest coverage | Financial health | > 5 excellent, > 2 minimum | ✅ OK - financial_health_score |
| Accruals | Earnings quality | Low accruals = high quality | ✅ OK - overall_quality_score |
| Earnings consistency | Quality standard | 5+ years excellent | ✅ OK - overall_quality_score |
| Quality-weighted portfolio | Quality investing | Higher quality = higher weight | ✅ OK - quality_adjustment |
| Value adjustment | Quality at reasonable price | Combine quality + value | ✅ OK - _calculate_quality_value_score |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Novy-Marx (2013) "The Other Side of Value: Gross Profitability Premium" for quality investing rules.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_quality_screen.py:**
  - `test_screen_pass()` - Stock passes all criteria
  - `test_screen_fail_quality_score()` - Quality score below minimum
  - `test_screen_fail_roe()` - ROE below minimum
  - `test_screen_fail_margin()` - Profit margin below minimum
  - `test_screen_fail_debt()` - D/E ratio too high
  - `test_screen_fail_coverage()` - Interest coverage too low
  - `test_screen_fail_z_score()` - Altman Z-score in distress zone
  - `test_profitability_score()` - Composite score calculation
  - `test_financial_health_score()` - Composite score calculation
  - `test_overall_quality_score()` - 50% profit + 30% health + 20% earnings
  - `test_quality_category()` - Score mapping to category
  - `test_quality_value_score()` - 70% quality + 30% value
  - `test_portfolio_construction()` - Weights sum to 1.0
  - `test_weight_constraints()` - Min/max weights enforced
  - `test_high_quality_buy_signal()` - High quality at discount
  - `test_poor_quality_avoid_signal()` - Poor quality stocks avoided
  - `test_gross_profitability_premium()` - High GP vs low GP returns

---

## Notes
- **Critical:** High profitability is the strongest quality indicator (Novy-Marx, 2013)
- **Novy-Marx Reference:** "The Other Side of Value: Gross Profitability Premium" (2013)
- **Gross Profit Margin:** > 40% excellent, > 30% good, > 20% acceptable
- **Operating Margin:** > 15% excellent, > 10% good, > 5% acceptable
- **ROE:** > 15% excellent, > 10% good, > 5% acceptable
- **ROIC:** > 12% excellent, > 8% good, > 4% acceptable
- **FCF Margin:** > 10% excellent, > 5% good, > 0% acceptable
- **Current Ratio:** > 2 excellent, > 1.5 good, > 1.0 acceptable
- **Quick Ratio:** > 1 excellent, > 0.8 acceptable
- **Debt-to-Equity:** < 0.3 excellent, < 0.5 good, < 1.0 acceptable
- **Interest Coverage:** > 10 excellent, > 5 good, > 2 minimum
- **Altman Z-Score:** < 1.8 distress zone, 1.8-3 grey zone, > 3 safe
- **Accruals:** < 5% of assets excellent, < 10% good, < 15% acceptable
- **Earnings Consistency:** 5+ years excellent, 3+ years good, 1+ year acceptable
- **Overall Quality:** 50% profitability + 30% financial health + 20% earnings quality
- **Quality Categories:** >= 0.8 HIGH, >= 0.6 GOOD, >= 0.4 AVERAGE, >= 0.2 LOW, < 0.2 POOR
- **Quality-Value Composite:** 70% quality score + 30% value score (inverted ratios)
- **Value Score:** Average of (1/(1+P/B), 1/(1+P/E), 1/(1+EV/EBITDA))
- **Weight Adjustment:** Base equal weight × (1 + 0.5 × (quality_score - 0.5))

---

**File Reference:** `app/domain/strategies/quality_screen.py`
**Last Audited:** 2026-02-01
