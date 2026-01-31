# pre_trade_analysis.py

## Purpose
Pre-Trade Analysis Entity - Domain layer entity representing comprehensive pre-trade analysis from all 17 trading systems.

---

## Type Definitions / Data Classes

### PreTradeAnalysis
```python
@dataclass
class PreTradeAnalysis:
    # Basic decision
    can_execute: bool                      # REQUIRED - Whether trade can execute
    confidence: float                      # REQUIRED - Confidence score (0-1)
    reasons: List[str]                     # Default: [] - Execution reasons

    # ========== 8 MAIN SYSTEMS ==========

    # 1. Backtesting Engine
    backtest_confidence: float             # Default: 0.0
    backtest_period: Optional[str]         # Default: None
    historical_sharpe: Optional[float]      # Default: None

    # 2. Risk Engine
    portfolio_var: Optional[float]         # Default: None
    position_limit_ok: bool                # Default: True
    leverage_ratio: float                  # Default: 0.0
    drawdown_limit_ok: bool                # Default: True

    # 3. Portfolio Engine
    current_exposure: float                # Default: 0.0
    diversification_score: float           # Default: 0.0
    correlation_risk: float                # Default: 0.0

    # 4. Data Engine
    data_freshness_ms: float               # Default: 0.0
    data_quality_score: float              # Default: 100.0
    missing_data_detected: bool            # Default: False

    # 5. Context Engine
    market_regime: Optional[str]           # Default: None
    volatility_regime: str                 # Default: "NORMAL"
    correlation_regime: str                # Default: "NORMAL"
    regime_confidence: float               # Default: 0.0

    # 6. Execution Engine
    execution_probability: float           # Default: 0.95
    estimated_slippage_bps: float          # Default: 0.0
    optimal_participation_rate: float      # Default: 0.0

    # 7. Strategies
    strategy_signal: float                 # Default: 0.0
    strategy_health: float                 # Default: 100.0

    # 8. Live/Paper Trading
    account_balance_ok: bool               # Default: True
    buying_power_ok: bool                  # Default: True
    day_trading_count: int                 # Default: 0
    pattern_day_trader_ok: bool            # Default: True

    # ========== 12 COMPLIANCE SYSTEMS ==========

    # 1. Ernest Chan (Rule 1)
    chan_regime: Optional[str]             # Default: None
    chan_factor_scores: Dict[str, float]   # Default: {}
    chan_optimization_method: str          # Default: "mean_variance"
    chan_execution_algo: Optional[str]     # Default: None

    # 2. Narang (Rule 2)
    narang_alpha_signal: Optional[float]   # Default: None
    narang_alpha_quality: str              # Default: "UNKNOWN"
    narang_recommended_holding_period: Optional[int]  # Default: None
    narang_transaction_cost_bps: float    # Default: 0.0

    # 3. Lopez de Prado (Rule 3)
    sample_weights_available: bool         # Default: False
    meta_labeling_signal: Optional[float]  # Default: None
    purged_cv_score: Optional[float]       # Default: None
    mcc_metric: Optional[float]            # Default: None

    # 4. Tomasini (Rule 4)
    tomasini_architecture_score: float     # Default: 100.0
    walk_forward_passed: bool              # Default: True
    overfitting_risk: str                  # Default: "LOW"

    # 5. Hastie (Rule 5)
    statistical_model_health: float        # Default: 100.0
    cross_validation_score: Optional[float]  # Default: None
    regularization_strength: float         # Default: 0.0
    feature_importance_stable: bool        # Default: True

    # 6. Harris (Rule 6)
    harris_order_book_depth_ok: bool       # Default: True
    harris_liquidity_score: float          # Default: 50.0
    harris_vpin: float                     # Default: 0.0
    harris_pin: float                      # Default: 0.0
    bid_ask_bounce_risk: str               # Default: "LOW"

    # 7. O'Hara (Rule 7)
    ohara_liquidity_regime: str            # Default: "NORMAL"
    ohara_order_flow_toxicity: float       # Default: 0.0
    ohara_price_discovery_score: float    # Default: 50.0
    dark_pool_available: bool              # Default: False

    # 8. Percival (Rule 8)
    architecture_pattern_compliance: float # Default: 100.0
    clean_architecture_score: float        # Default: 100.0
    dependency_health: float               # Default: 100.0

    # 9. Hull (Rule 13)
    hull_var_1d_95: Optional[float]         # Default: None
    hull_var_1d_99: Optional[float]         # Default: None
    hull_greeks_delta: Optional[float]      # Default: None
    hull_greeks_gamma: Optional[float]      # Default: None
    hull_stress_test_passed: bool           # Default: True

    # 10. Google SRE (Rule 20)
    slo_compliance: bool                   # Default: True
    error_budget_remaining: float          # Default: 100.0
    latency_p95_ms: float                  # Default: 0.0
    golden_signals_health: float           # Default: 100.0

    # 11. Beck TDD (Rule 21)
    test_coverage: float                   # Default: 100.0
    tests_passing: bool                    # Default: True
    tdd_compliance: float                  # Default: 100.0

    # 12. Martin Clean Arch (Rule 18)
    martin_layer_separation: float         # Default: 100.0
    martin_dependency_rule: float          # Default: 100.0
    martin_interface_health: float         # Default: 100.0

    # ========== AGGREGATED METRICS ==========
    liquidity_score: float                 # Default: 50.0
    liquidity_regime: str                  # Default: "NORMAL"
    market_impact_bps: float               # Default: 0.0
    timing_cost_bps: float                  # Default: 0.0
    total_cost_bps: float                   # Default: 0.0
    venue: str                              # Default: "lit_exchange"
    algorithm: str                          # Default: "LIMIT"
    limit_price: Optional[Decimal]          # Default: None
    systems_contributed: int                # Default: 0
    systems_total: int                      # Default: 17
```

---

## Function Signatures (Contracts)

### `get_execution_summary() -> str`
**Pre:** None
**Post:** Returns human-readable execution summary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Output Format:**
- If can_execute: "Execute {algorithm} @ {price} on {venue} (confidence: X%, est. cost: X bps)"
- If not: "Cannot execute: {reasons}"

### `get_risk_summary() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with portfolio_var, position_limit_ok, drawdown_limit_ok, hull_var_1d_95, leverage_ratio, liquidity_score
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_compliance_summary() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with slo_compliance, test_coverage, clean_architecture_score, architecture_pattern_compliance
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** can_execute boolean indicates trade execution decision
- [ ] **AC-002:** confidence score in range [0, 1]
- [ ] **AC-003:** reasons list provides explanation for decision
- [ ] **AC-004:** All 8 main systems have data fields
- [ ] **AC-005:** All 12 compliance systems have data fields
- [ ] **AC-006:** systems_contributed ≤ systems_total (17)
- [ ] **AC-007:** total_cost_bps = market_impact_bps + timing_cost_bps
- [ ] **AC-008:** get_execution_summary() returns human-readable string
- [ ] **AC-009:** get_risk_summary() returns risk metrics dict
- [ ] **AC-010:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Pre-Trade Analysis):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| 8 Main Systems | Ralphex architecture | All systems analyzed | ✅ OK - Fields present |
| 12 Compliance Systems | Ralphex architecture | All compliance checked | ✅ OK - Fields present |
| Chan regime detection | Chan (2013) | Regime-based optimization | ✅ OK - chan_regime |
| Narang alpha quality | Narang (2013) | Alpha signal quality | ✅ OK - narang_alpha_quality |
| Meta-labeling | López de Prado (2018) | Purged CV, MCC | ✅ OK - meta_labeling_signal |
| Walk-forward | Tomasini (2008) | Overfitting check | ✅ OK - walk_forward_passed |
| Cross-validation | Hastie et al. (2009) | CV score, regularization | ✅ OK - cross_validation_score |
| Order book depth | Harris (2003) | VPIN, PIN metrics | ✅ OK - harris_vpin, harris_pin |
| Liquidity regime | O'Hara (1995) | Order flow toxicity | ✅ OK - ohara_order_flow_toxicity |
| VAR | Hull (2018) | 1-day 95%/99% VAR | ✅ OK - hull_var_1d_95/99 |
| Greeks | Hull (2018) | Delta, gamma | ✅ OK - hull_greeks_delta/gamma |
| SLO compliance | Google SRE | Error budget, latency | ✅ OK - slo_compliance |
| TDD compliance | Beck (2002) | Test coverage | ✅ OK - test_coverage |
| Clean Architecture | Martin (2017) | Layer separation | ✅ OK - martin_layer_separation |
| Aggregated metrics | Trading standard | Combined scores | ✅ OK - liquidity_score |
| Execution recommendation | Trading standard | Venue, algo, price | ✅ OK - venue, algorithm, limit_price |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and trading system rules from the 80 rule files.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std), `typing` (std)
- **Internal:** None (domain entity)

---

## Required Tests
- **test_pre_trade_analysis_entity.py:**
  - `test_can_execute_true()` - Trade allowed
  - `test_can_execute_false()` - Trade blocked
  - `test_confidence_range()` - 0 to 1
  - `test_reasons_list()` - Reasons provided
  - `test_8_main_systems_present()` - All fields present
  - `test_12_compliance_systems_present()` - All fields present
  - `test_systems_contributed()` - Count contributed systems
  - `test_liquidity_score_aggregation()` - Harris + O'Hara combined
  - `test_total_cost_calculation()` - market_impact + timing_cost
  - `test_get_execution_summary_can_execute()` - Human-readable summary
  - `test_get_execution_summary_cannot_execute()` - Shows reasons
  - `test_get_risk_summary()` - Risk metrics dict
  - `test_get_compliance_summary()` - Compliance metrics dict
  - `test_chan_regime_detection()` - Chan regime field
  - `test_narang_alpha_quality()` - Alpha quality field
  - `test_meta_labeling()` - López de Prado fields
  - `test_walk_forward_passed()` - Tomasini field
  - `test_harris_vpin()` - VPIN metric
  - `test_ohara_order_flow_toxicity()` - Order flow metric
  - `test_hull_var()` - VAR metrics
  - `test_slo_compliance()` - Google SRE fields
  - `test_tdd_compliance()` - Beck TDD fields
  - `test_martin_clean_arch()` - Martin architecture fields

---

## Notes
- **Critical:** PreTradeAnalysis aggregates results from ALL 17 systems before trade execution
- **17 Systems Total:** 8 Main (Backtesting, Risk, Portfolio, Data, Context, Execution, Strategies, Trading) + 12 Compliance (Chan, Narang, López de Prado, Tomasini, Hastie, Harris, O'Hara, Percival, Hull, Google SRE, Beck TDD, Martin)
- **Decision Model:** can_execute + confidence + reasons
- **Chan Reference:** "Algorithmic Trading: Winning Strategies and Their Rationale" (2013) - regime-based optimization
- **Narang Reference:** "Inside the Black Box" (2013) - alpha quality assessment
- **López de Prado Reference:** "Advances in Financial Machine Learning" (2018) - meta-labeling, purged CV
- **Tomasini Reference:** "Trading Systems" (2008) - walk-forward validation, overfitting detection
- **Hastie Reference:** "The Elements of Statistical Learning" (2009) - cross-validation, regularization
- **Harris Reference:** "Trading and Exchanges" (2003) - market microstructure, VPIN, PIN
- **O'Hara Reference:** "Market Microstructure Theory" (1995) - order flow toxicity, liquidity
- **Hull Reference:** "Options, Futures, and Other Derivatives" (2018) - VAR, Greeks
- **Google SRE Reference:** Site Reliability Engineering - SLO, error budgets
- **Beck Reference:** "Test-Driven Development" (2002) - TDD compliance
- **Martin Reference:** "Clean Architecture" (2017) - layer separation, dependency rules
- **Aggregated Liquidity:** Combines Harris (liquidity_score) + O'Hara (liquidity_regime)
- **Cost Estimation:** market_impact_bps + timing_cost_bps = total_cost_bps
- **Execution Recommendation:** Suggests venue (lit_exchange/dark_pool), algorithm (LIMIT/MARKET/TWAP/VWAP), limit_price
- **Confidence Score:** 0-1 indicating likelihood of successful execution
- **System Participation:** systems_contributed / systems_total shows how many systems provided input

---

**File Reference:** `app/domain/entities/pre_trade_analysis.py`
**Last Audited:** 2026-02-01
