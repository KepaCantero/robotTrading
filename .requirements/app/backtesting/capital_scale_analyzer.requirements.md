# capital_scale_analyzer.py

## Purpose
Analyze strategy performance across multiple capital levels (€1K, €5K, €10K, €50K, €100K) to detect scalability issues, liquidity constraints, commission impact degradation, and alpha degradation.

---

## Type Definitions / Data Classes

### CapitalLevelResult (dataclass)
```python
@dataclass
class CapitalLevelResult:
    capital_level: Decimal                    # REQUIRED - Capital level tested
    initial_capital: Decimal                  # REQUIRED - Starting capital
    final_capital: Decimal                    # REQUIRED - Ending capital
    total_return: Decimal                     # REQUIRED - Absolute return
    total_return_pct: Decimal                 # REQUIRED - Percentage return
    cagr: Decimal                             # REQUIRED - Compound annual growth rate
    sharpe_ratio: Optional[Decimal] = None    # OPTIONAL - Risk-adjusted return
    max_drawdown_pct: Decimal                 # REQUIRED - Maximum drawdown %
    total_trades: int                         # REQUIRED - Total trades executed
    win_rate: Decimal                         # REQUIRED - Win rate %
    total_commissions: Decimal                # REQUIRED - Total commission paid
    gross_profit: Decimal                     # REQUIRED - Total profit from winners
    gross_return: Decimal                     # REQUIRED - Gross profit + gross loss
    commission_impact_ratio: Decimal          # REQUIRED - Commissions / Gross Return
    partial_fills: int                        # REQUIRED - Number of trades reduced by ADV rule
    rejected_orders: int                      # REQUIRED - Number of orders rejected
    performance_metrics: Optional[PerformanceMetrics] = None
    equity_curve: List[Tuple[datetime, Decimal]] = field(default_factory=list)
```

### CapitalScaleAnalysisReport (dataclass)
```python
@dataclass
class CapitalScaleAnalysisReport:
    strategy_name: str
    timestamp: datetime
    start_date: datetime
    end_date: datetime
    capital_level_results: List[CapitalLevelResult]
    adv_rule_enabled: bool
    adv_limit_pct: Decimal
    alpha_degradation: Decimal                # CAGR difference between smallest and largest
    commission_impact_gradient: List[Decimal] # Commission impact by level
    scalability_score: Decimal                # 0-100 score
    recommended_capital: Decimal              # Optimal capital level
    warnings: List[str] = field(default_factory=list)
    passed: bool = True
```

**Validation Rules:**
- `commission_impact_ratio` = commissions / gross_return
- `scalability_score` between 0-100
- `alpha_degradation` non-negative

---

## Function Signatures (Contracts)

### `CapitalScaleAnalyzer.__init__(capital_levels: Optional[List[Decimal]] = None, adv_limit_pct: Optional[Decimal] = None, enable_adv_rule: bool = True, enable_adaptive_commission: bool = True)`
**Pre:** capital_levels non-empty if provided, adv_limit_pct 0-1 range
**Post:** Analyzer initialized with default or custom capital levels
**Raises:** None
**Retry:** No
**Side Effects:** Creates CostCalculator instance

### `calculate_commission_for_level(capital_level: Decimal, trade_value: Decimal) -> Decimal`
**Pre:** capital_level > 0, trade_value > 0
**Post:** Returns commission amount based on capital level model
**Raises:** None
**Retry:** No
**Side Effects:** None

### `apply_adv_limit(order_size: Decimal, adv: Decimal, symbol: str) -> Tuple[Decimal, bool, bool]`
**Pre:** order_size > 0, adv > 0
**Post:** Returns (adjusted_size, was_partial_fill, was_rejected)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `simulate_single_capital_level(quotes: List[Quote], signals: List[Any], base_config: BacktestConfig, capital_level: Decimal, adv_data: Optional[Dict[str, Decimal]] = None) -> CapitalLevelResult`
**Pre:** quotes non-empty, base_config valid
**Post:** Returns CapitalLevelResult with metrics
**Raises:** Logs errors, returns None if critical failure
**Retry:** No
**Side Effects:** Runs complete backtest for capital level

### `analyze_capital_scaling(quotes: List[Quote], signals: List[Any], config: BacktestConfig, start_date: datetime, end_date: datetime, adv_data: Optional[Dict[str, Decimal]] = None) -> CapitalScaleAnalysisReport`
**Pre:** quotes non-empty, config valid
**Post:** Returns complete analysis report with all capital levels
**Raises:** None (returns report with empty results if all fail)
**Retry:** No
**Side Effects:** Runs multiple backtests (one per capital level)

### `_calculate_alpha_degradation(results: List[CapitalLevelResult]) -> Decimal`
**Pre:** results has at least 2 entries
**Post:** Returns alpha degradation (non-negative)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_scalability_score(results: List[CapitalLevelResult], alpha_degradation: Decimal) -> Decimal`
**Pre:** results non-empty
**Post:** Returns score 0-100
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_find_optimal_capital(results: List[CapitalLevelResult]) -> Decimal`
**Pre:** results non-empty
**Post:** Returns capital level with best risk-adjusted return
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_summary_table(report: CapitalScaleAnalysisReport) -> str`
**Pre:** report valid
**Post:** Returns markdown table with results
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All default capital levels tested (€1K, €5K, €10K, €50K, €100K)
- [ ] ADV limit applied (2% default)
- [ ] Commission impact calculated for each level
- [ ] Alpha degradation < threshold (from config)
- [ ] Scalability score 0-100 calculated
- [ ] Warnings logged for commission impact > threshold
- [ ] Partial fills counted when ADV limit hit
- [ ] Rejected orders counted when fill < threshold
- [ ] Report marks as failed if critical thresholds exceeded
- [ ] Optimal capital recommended based on Sharpe and liquidity
- [ ] Adaptive commission models used (fixed, hybrid, tiered)

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

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ⚠️ GAP - Some Any types |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some functions > 20 lines |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| TRADING-004 | Custom | ADV rule enforcement (2% limit) | ✅ OK |
| TRADING-005 | Custom | Commission impact validation | ✅ OK |

**Configuration Constants (from BACKTESTING_CONSTANTS):**
- ADV_LIMIT_PCT_DEFAULT: 2%
- COMMISSION_IMPACT_WARNING_THRESHOLD: 20%
- COMMISSION_IMPACT_CRITICAL_THRESHOLD: 30%
- COMMISSION_IMPACT_EXCELLENT_THRESHOLD: 5%
- COMMISSION_IMPACT_GOOD_THRESHOLD: 10%
- COMMISSION_IMPACT_OPTIMAL_THRESHOLD: 15%
- ALPHA_DEGRADATION_THRESHOLD: 50%

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, dataclasses, datetime, decimal, typing, numpy
- **Internal:**
  - app.backtesting.constants.BACKTESTING_CONSTANTS
  - app.backtesting.cost_calculator.CostCalculator, AssetType
  - app.backtesting.engine.SimpleBacktester
  - app.backtesting.models (BacktestConfig, BacktestResult, PerformanceMetrics)
  - app.models.market_data.Quote

---

## Required Tests
- **test_capital_scale_analyzer.py:**
  - Success: All default capital levels tested
  - Success: ADV limit reduces order sizes correctly
  - Success: Commission impact increases at lower capital levels
  - Success: Alpha degradation calculated correctly
  - Success: Scalability score calculated
  - Success: Optimal capital recommended
  - Success: Adaptive commission models (fixed, hybrid, tiered)
  - Success: Partial fills counted
  - Success: Rejected orders counted
  - Success: Report passed when thresholds met
  - Error: Insufficient capital levels (returns empty report)
  - Edge: Zero ADV data (ADV rule disabled)
  - Edge: Single capital level
  - Integration: ADV rule causes partial fills
  - Integration: Commission impact exceeds critical threshold (report failed)
  - Integration: Alpha degradation exceeds threshold (report failed)

---

## Notes
- Addresses Req #1 (CRITICAL) from professional backtesting system
- Default capital levels: €1K, €5K, €10K, €50K, €100K
- ADV limit default: 2% of average daily volume
- Commission models by capital level (from config)
- Scalability score: alpha degradation (50 pts) + commission (30 pts) + stability (20 pts)
- Alpha degradation = (CAGR_small - CAGR_large) / |CAGR_small|
