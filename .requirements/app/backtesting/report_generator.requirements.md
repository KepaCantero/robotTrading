# report_generator.py

## Purpose
Generates comprehensive, auditable backtest reports with executive summary, technical analysis, risk metrics, performance attribution, and improvement recommendations.

---

## Type Definitions / Data Classes
No custom dataclasses defined - uses standard library types and BacktestResult from models.

---

## Function Signatures (Contracts)

### `generate_comprehensive_report(result, config, backtest_id) -> Dict[str, Path]`
**Pre:** result has valid performance metrics, config has strategy_name
**Post:** Returns dict with file paths to generated reports (executive, technical, risk, metrics, recommendations)
**Raises:** OSError if output_dir not writable
**Retry:** No
**Side Effects:** Creates 5 files in output_dir (markdown + JSON)

### `_generate_executive_summary(result, config) -> str`
**Pre:** result.performance is not None
**Post:** Returns markdown-formatted executive summary with performance overview
**Raises:** ValueError if performance data missing
**Retry:** No
**Side Effects:** None (string generation)

### `_generate_technical_analysis(result, config) -> str`
**Pre:** result has equity_curve and performance data
**Post:** Returns markdown with detailed technical metrics and analysis
**Raises:** ValueError if required fields missing
**Retry:** No
**Side Effects:** None (string generation)

### `_generate_risk_analysis(result, config) -> str`
**Pre:** result.performance has risk metrics
**Post:** Returns markdown with VaR, drawdown, volatility analysis
**Raises:** ValueError if performance data missing
**Retry:** No
**Side Effects:** None (string generation)

### `_generate_recommendations(result, config, metrics) -> str`
**Pre:** metrics dict contains key performance indicators
**Post:** Returns markdown with prioritized recommendations
**Raises:** None (returns empty recommendations on error)
**Retry:** No
**Side Effects:** None (string generation)

### `_extract_detailed_metrics(result, config) -> Dict[str, Any]`
**Pre:** result has complete performance data
**Post:** Returns dict with all metrics serializable to JSON
**Raises:** TypeError if non-serializable data present
**Retry:** No
**Side Effects:** None (dict construction)

---

## Acceptance Criteria
- [ ] Generates 5 report files: executive summary (MD), technical analysis (MD), risk analysis (MD), metrics (JSON), recommendations (MD)
- [ ] Executive summary includes performance assessment (Excellent/Good/Marginal/Poor)
- [ ] Technical analysis includes CAGR, Kelly criterion, trade statistics
- [ ] Risk analysis includes VaR 95%, VaR 99%, drawdown duration
- [ ] Recommendations are prioritized (HIGH/MEDIUM/LOW)
- [ ] JSON metrics file contains all performance data in serializable format
- [ ] All files use timestamp in filename for uniqueness
- [ ] Critical issues identification includes negative returns, low win rate, high drawdown

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ⚠️ NOT APPLIED - Uses basic logging |
| CC-002 | BASE_RULES | DRY - No duplication | ⚠️ NOT APPLIED - String formatting repeated |
| CC-006 | BASE_RULES | Explicit error handling | ❌ GAP - Missing exception handling in file operations |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ❌ GAP - Many functions exceed 20 lines (template strings) |
| BT-004 | BASE_RULES | Realistic costs in reports | ✅ OK - Includes commission/slippage from config |
| RSK-001 | BASE_RULES | VaR calculation | ✅ OK - Calculates VaR 95% and 99% |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Reports provide audit trail |

**NOTE:** Several helper methods are placeholders (`_analyze_trade_distribution`, `_analyze_market_conditions`) indicating incomplete implementation.

---

## Dependencies
- **External:** json, logging, datetime, pathlib, typing (stdlib)
- **Internal:**
  - `app.backtesting.models.BacktestConfig`
  - `app.backtesting.models.BacktestResult`
  - `app.backtesting.models.PerformanceMetrics`

---

## Required Tests
- **tests/backtesting/test_report_generator.py:**
  - Test comprehensive report generation creates all 5 files
  - Test executive summary with positive returns
  - Test executive summary with negative returns
  - Test technical analysis includes CAGR calculation
  - Test Kelly criterion calculation with win/loss data
  - Test risk analysis VaR calculations
  - Test recommendations prioritization (HIGH/MEDIUM/LOW)
  - Test JSON metrics file is valid and complete
  - Test file timestamp uniqueness
  - Test critical issues identification

---

## Notes
Several analysis methods are placeholders and return static text. Implement actual analysis for production use.
