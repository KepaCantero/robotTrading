# insight_generator.py

## Purpose
Generates deterministic, template-based insights, risk warnings, and actionable recommendations from backtest metrics without using LLM/NLP.

---

## Type Definitions / Data Classes
No custom dataclasses defined - uses standard Dict and List types.

---

## Function Signatures (Contracts)

### `generate_statistical_insights(metrics) -> List[str]`
**Pre:** metrics is dict with keys: return_pct, sharpe_ratio, max_drawdown, win_rate, volatility, profit_factor
**Post:** Returns list of insight strings with emoji indicators (✅/⚠️/❌)
**Raises:** Returns empty list on error (caught exceptions)
**Retry:** No
**Side Effects:** Updates self.insights internal state

### `generate_risk_warnings(metrics) -> List[Dict[str, Any]]`
**Pre:** metrics dict contains numeric values for risk metrics
**Post:** Returns list of warning dicts with keys: level, metric, value, message
**Raises:** Returns empty list on error (caught exceptions)
**Retry:** No
**Side Effects:** Updates self.warnings internal state

### `generate_recommendations(metrics, regimes) -> List[Dict[str, Any]]`
**Pre:** metrics has performance data, regimes is optional dict
**Post:** Returns list of recommendation dicts with keys: priority, action, rationale
**Raises:** Returns empty list on error (caught exceptions)
**Retry:** No
**Side Effects:** Updates self.recommendations internal state

### `format_markdown_report(strategy_name, metrics, regimes, include_warnings, include_recommendations) -> str`
**Pre:** strategy_name is non-empty, metrics dict is complete
**Post:** Returns markdown-formatted report with all sections
**Raises:** Returns error message string on exception
**Retry:** No
**Side Effects:** None (string generation)

### `get_insights() -> List[str]`
**Pre:** generate_statistical_insights() has been called
**Post:** Returns last generated insights list
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_warnings() -> List[Dict[str, Any]]`
**Pre:** generate_risk_warnings() has been called
**Post:** Returns last generated warnings list
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_recommendations() -> List[Dict[str, Any]]`
**Pre:** generate_recommendations() has been called
**Post:** Returns last generated recommendations list
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

---

## Acceptance Criteria
- [ ] Statistical insights generated for all 6 key metrics (return, sharpe, drawdown, win rate, volatility, profit factor)
- [ ] Insights use emoji indicators: ✅ (good), ⚠️ (warning), ❌ (poor)
- [ ] Risk warnings include CRITICAL, WARNING, INFO levels
- [ ] Risk warnings trigger at: DD < -50%, Sharpe < 0, volatility > 50%, win rate < 40%, profit factor < 1.0
- [ ] Recommendations are prioritized HIGH/MEDIUM/LOW
- [ ] Recommendations include actionable steps with rationale
- [ ] Markdown report includes performance summary table with all metrics
- [ ] Markdown report is well-formed with proper headers and formatting
- [ ] All methods handle empty/None metrics gracefully
- [ ] No LLM/NLP used - all output is deterministic and template-based

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Uses logging with context |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - All methods catch and log exceptions |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ NOT APPLIED - format_markdown_report > 20 lines |
| BT-004 | BASE_RULES | Realistic costs | ⚠️ NOT APPLIED - Uses provided metrics |
| RSK-001 | BASE_RULES | VaR/ES calculation | ⚠️ NOT APPLIED - Uses provided metrics |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Logging provides audit trail |

**NOTE:** Deterministic output (no LLM) is a key design requirement for traceability and regulatory compliance.

---

## Dependencies
- **External:** logging, datetime, typing, numpy (stdlib + numpy)
- **Internal:** None (standalone module)

---

## Required Tests
- **tests/backtesting/test_insight_generator.py:**
  - Test statistical insights for all metric ranges (excellent/good/marginal/poor)
  - Test risk warnings for all threshold levels (CRITICAL/WARNING/INFO)
  - Test recommendations generation for HIGH/MEDIUM/LOW priorities
  - Test markdown report formatting with all sections
  - Test empty/None metrics handling
  - Test regime-based recommendations (high variance detection)
  - Test backtest_only flag triggers paper trading recommendation
  - Test emoji indicators match metric thresholds
  - Test getter methods return correct internal state
  - Test exception handling returns empty lists gracefully

---

## Notes
This module provides deterministic, auditable insights without AI/LLM, ensuring reproducible results for compliance and regulatory requirements.
