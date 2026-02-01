# acceptance_criteria.py

## Purpose
Validates strategy viability against institutional standards (Req #17) including Sharpe > 1.0, Max DD < 25%, Profit Factor > 1.3, Monte Carlo P5 > -20%, and excess return vs benchmark > 3%.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### VerdictStatus Enum
```python
class VerdictStatus(str, Enum):
    APPROVED = "APPROVED"    # Strategy meets all criteria
    REVISION = "REVISION"    # Strategy partially meets, needs review
    REJECTED = "REJECTED"    # Strategy fails critical criteria
```

**Validation Rules:**
- Must be one of: APPROVED, REVISION, REJECTED

### CriterionResult DataClass
```python
@dataclass
class CriterionResult:
    name: str                  # REQUIRED - Criterion name
    passed: bool               # REQUIRED - True if criterion met
    value: float               # REQUIRED - Actual metric value
    threshold: float           # REQUIRED - Required threshold value
    description: str           # REQUIRED - Human-readable description
```

**Validation Rules:**
- `name` must be non-empty
- `threshold` must match criterion definition
- `description` must explain the requirement

### AcceptanceReport DataClass
```python
@dataclass
class AcceptanceReport:
    strategy_name: str                        # REQUIRED - Name of validated strategy
    timestamp: datetime                       # REQUIRED - Validation timestamp
    verdict: VerdictStatus                    # REQUIRED - Final verdict (APPROVED/REVISION/REJECTED)
    overall_score: float                      # REQUIRED - Score 0-100
    basic_criteria: List[CriterionResult]     # REQUIRED - Primary criteria results
    advanced_criteria: List[CriterionResult]  # OPTIONAL - Advanced criteria (empty in current impl)
    rejection_criteria: List[CriterionResult] # REQUIRED - Deal-breaker criteria
    beats_benchmark: bool                     # REQUIRED - True if excess_return > min_excess_return
    excess_return: float                      # REQUIRED - Strategy return - benchmark return
    warnings: List[str]                       # OPTIONAL - Warning messages
    recommendations: List[str]                # OPTIONAL - Improvement suggestions
    sharpe_ratio: Optional[float]             # OPTIONAL - Sharpe ratio from backtest
    max_drawdown: Optional[float]             # OPTIONAL - Max drawdown from backtest
    profit_factor: Optional[float]            # OPTIONAL - Profit factor from backtest
    commission_impact: Optional[float]        # OPTIONAL - Commissions as % of gross profit
    monte_carlo_p5: Optional[float]           # OPTIONAL - Monte Carlo 5th percentile return
```

**Validation Rules:**
- `overall_score` must be in range [0, 100]
- `verdict` must be REJECTED if any rejection criterion fails
- `verdict` must be APPROVED only if all basic criteria pass
- `verdict` must be REVISION if score >= 60 but not all criteria pass
- `verdict` must be REJECTED if score < 60

---

## Function Signatures (Contracts)

### `AcceptanceCriteria.__init__(min_sharpe: float = 1.0, max_drawdown: float = -0.25, min_profit_factor: float = 1.3, min_monte_carlo_p5: float = -0.20, min_excess_return: float = 0.03) -> None`
**Pre:** min_sharpe > 0, max_drawdown < 0, min_profit_factor > 1.0, min_monte_carlo_p5 < 0, min_excess_return > 0
**Post:** AcceptanceCriteria initialized with Req #17 thresholds
**Raises:** None
**Retry:** No
**Side Effects:** None

### `validate_strategy(backtest_result: BacktestResult, benchmark_return: float, monte_carlo_p5_return: Optional[float] = None, commission_impact: Optional[float] = None, failed_regimes: Optional[int] = None, equity_curve_last_years: Optional[List[float]] = None) -> AcceptanceReport`
**Pre:** backtest_result.performance is not None
**Post:** Returns AcceptanceReport with verdict, score, and all criteria results
**Raises:** None
**Retry:** No
**Side Effects:** None (pure validation)

### `_calculate_score(criteria: List[CriterionResult]) -> float`
**Pre:** criteria is list of CriterionResult
**Post:** Returns score 0-100 (20 points per passed criterion)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_determine_verdict(criteria: List[CriterionResult], rejection: List[CriterionResult], score: float) -> tuple[VerdictStatus, List[str], List[str]]`
**Pre:** criteria and rejection are lists of results
**Post:** Returns (verdict, warnings, recommendations) based on rules
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_summary_markdown(report: AcceptanceReport) -> str`
**Pre:** report is valid AcceptanceReport
**Post:** Returns formatted markdown string with report content
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Sharpe Ratio (OOS) must be >= 1.0 for approval
- [ ] Max Drawdown must be >= -25% (less negative) for approval
- [ ] Profit Factor must be >= 1.3 for approval
- [ ] Monte Carlo P5 return must be >= -20% for approval
- [ ] Excess return vs benchmark must be >= 3% for approval
- [ ] Commission impact must be <= 20% of gross profit (rejection criterion)
- [ ] Failed market regimes must be <= 2 (rejection criterion)
- [ ] Equity curve must be positive in last 2 years (rejection criterion)
- [ ] Overall score calculated as 20 points per passed basic criterion
- [ ] Verdict APPROVED: all basic criteria pass, no rejection failures
- [ ] Verdict REVISION: score >= 60 but some criteria fail
- [ ] Verdict REJECTED: any rejection criterion fails OR score < 60
- [ ] Invalid backtest (no performance data) returns REJECTED with score 0
- [ ] Markdown summary includes all criteria, warnings, recommendations

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Only validates acceptance criteria |
| TYP-001 Type hints | 02-type-hints.md | All functions have type hints | ✅ OK - Complete type coverage |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ⚠️ NOT APPLIED - Uses dataclass (by design for validation results) |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ✅ FIXED - 2026-02-01 - Added validation for performance data |
| ERR-001 Exception handling | 05-error-handling.md | Handle missing optional data gracefully | ✅ OK - Handles None for optional parameters |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ FIXED - 2026-02-01 - Added structured logging for validation results |
| TEST-001 Deterministic | 10-testing.md | Tests must be reproducible | ✅ OK - Pure functions, no side effects |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** dataclasses, datetime, enum, logging, typing
- **Internal:** `app.backtesting.models.BacktestResult`

---

## Required Tests
- **test_acceptance_criteria.py:**
  - Success: APPROVED when all basic criteria pass and no rejection failures
  - Success: REVISION when score >= 60 but some criteria fail
  - Success: REJECTED when score < 60
  - Success: REJECTED when commission impact > 20%
  - Success: REJECTED when failed regimes > 2
  - Success: REJECTED when equity curve flat/negative last 2 years
  - Success: Score calculation: 20 points per passed criterion
  - Success: Sharpe threshold check (>= 1.0)
  - Success: Max drawdown threshold check (>= -25%)
  - Success: Profit factor threshold check (>= 1.3)
  - Success: Monte Carlo P5 threshold check (>= -20%)
  - Success: Excess return threshold check (>= 3%)
  - Edge: None values for optional parameters treated as not applicable
  - Edge: Invalid backtest (no performance) returns REJECTED
  - Integration: Markdown summary generated correctly
  - Integration: Warnings and recommendations populated based on failures

---

## Notes
This implements Req #17 - institutional-grade acceptance criteria. The module enforces strict thresholds: Sharpe > 1.0, Max DD < 25%, Profit Factor > 1.3, Monte Carlo P5 > -20%, excess return > 3%. Rejection criteria are hard stops: commission > 20% gross profit, > 2 failed regimes, flat/negative equity in last 2 years. Scoring is simple: 20 points per basic criterion (5 criteria = 100 max). Verdict logic: (1) Check rejection criteria first -> REJECTED if any fail, (2) All basic pass -> APPROVED, (3) Score >= 60 -> REVISION, (4) Otherwise -> REJECTED. The VerdictStatus enum provides three clear states for strategy evaluation.
