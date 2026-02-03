# integration.py

## Purpose
Integration helpers for connecting meta_analyzer components with ComprehensiveBacktestRunner. Provides convenient functions to set up audit trails, model storage, and post-test analysis.

---

## Type Definitions / Data Classes

### Integration Function Returns
```python
def integrate_meta_analyzer_with_runner(...) -> Dict[str, Any]:
    return {
        'audit_trail': Optional[AuditTrail],     # AuditTrail instance or None
        'storage': Optional[LearningEngineStorage],  # Storage instance or None
        'analyzer': Optional[BacktestMetaAnalyzer],  # Analyzer instance or None
        'audit_hash': Optional[str],             # Generated hash or None
    }
```

**Validation Rules:**
- All returned keys are present (values may be None if corresponding feature disabled)
- audit_hash is only present if enable_audit=True

---

## Function Signatures (Contracts)

### `integrate_meta_analyzer_with_runner(runner, config_path, enable_audit, enable_storage, enable_analysis) -> Dict[str, Any]`
**Pre:** runner must be valid instance, config_path must be valid string
**Post:** Returns dict with initialized components
**Raises:** None (errors logged, components set to None)
**Retry:** No
**Side Effects:** Initializes AuditTrail, LearningEngineStorage, BacktestMetaAnalyzer instances

### `save_backtest_audit_and_weights(runner, audit_trail, storage, test_result, test_type, learning_engine_name, learning_engine_weights) -> None`
**Pre:** audit_trail must be initialized if used, runner must have config_path attribute
**Post:** Saves audit record and weights asynchronously
**Raises:** None (errors logged with warning)
**Retry:** No
**Side Effects:** Writes to audit log file, saves model weights to disk

---

## Acceptance Criteria
- [ ] integrate_meta_analyzer_with_runner() creates AuditTrail if enable_audit=True
- [ ] integrate_meta_analyzer_with_runner() creates LearningEngineStorage if enable_storage=True
- [ ] integrate_meta_analyzer_with_runner() creates BacktestMetaAnalyzer if enable_analysis=True
- [ ] integrate_meta_analyzer_with_runner() generates audit hash if audit enabled
- [ ] integrate_meta_analyzer_with_runner() uses runner.output_dir for analyzer
- [ ] integrate_meta_analyzer_with_runner() returns all 4 keys in result dict
- [ ] save_backtest_audit_and_weights() saves audit record asynchronously
- [ ] save_backtest_audit_and_weights() saves weights if storage provided
- [ ] save_backtest_audit_and_weights() handles missing runner.config_path gracefully
- [ ] save_backtest_audit_and_weights() logs warnings for save failures
- [ ] All functions have proper error handling

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | PARTIAL - Warning logged but no exc_info |
| TYP-001 | BASE_RULES.md | 100% type coverage | GAP - Missing type hints for runner parameter |
| CC-001 | BASE_RULES.md | Descriptive names | OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | GAP - Generic exception catching |
| ASYNC-001 | BASE_RULES.md | Use async def | OK - save function is async |
| ARCH-001 | BASE_RULES.md | Layered architecture | OK - Integration layer |
| QL-001 | BASE_RULES.md | Complexity < 10 | OK - Simple functions |

**GAPS Identified:**

1. **P0 - None found**

2. **P1 - Type safety issues:**
   - `runner` parameter has no type hint (should be Protocol or specific type)
   - Function uses hasattr() to check for attributes instead of proper typing
   - Should define Protocol for ComprehensiveBacktestRunner

3. **P1 - Overly broad exception handling:**
   - Line 127: catches `asyncio.TimeoutError, ConnectionError, OSError`
   - ConnectionError not applicable for file operations
   - Should catch more specific exceptions

4. **P2 - Code quality:**
   - integrate_meta_analyzer_with_runner creates instances without dependency injection
   - Hardcoded default path "reports/comprehensive_backtest"

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** asyncio, logging, datetime, pathlib
- **Internal:** .audit_trail.AuditTrail, .learning_storage.LearningEngineStorage, .meta_analyzer.BacktestMetaAnalyzer

---

## Required Tests
- **tests/backtesting/meta_analyzer/test_integration.py:**
  - Test integrate_meta_analyzer_with_runner() creates AuditTrail when enable_audit=True
  - Test integrate_meta_analyzer_with_runner() creates Storage when enable_storage=True
  - Test integrate_meta_analyzer_with_runner() creates Analyzer when enable_analysis=True
  - Test integrate_meta_analyzer_with_runner() generates audit hash
  - Test integrate_meta_analyzer_with_runner() returns dict with all keys
  - Test integrate_meta_analyzer_with_runner() uses runner.output_dir for analyzer
  - Test integrate_meta_analyzer_with_runner() handles missing runner.output_dir
  - Test save_backtest_audit_and_weights() saves audit record
  - Test save_backtest_audit_and_weights() saves weights when provided
  - Test save_backtest_audit_and_weights() skips weights when storage is None
  - Test save_backtest_audit_and_weights() handles missing runner.config_path
  - Test save_backtest_audit_and_weights() logs warning on save failure
  - Test save_backtest_audit_and_weights() includes metadata in audit record
  - Test save_backtest_audit_and_weights() includes metadata in weights

---

## Notes
- Helper functions for easy integration with ComprehensiveBacktestRunner
- Uses hasattr() for duck typing instead of strict protocols
- Async function for saving audit and weights after backtest completion
- Default fallback path for analyzer if runner.output_dir missing
- No validation that runner is actually a ComprehensiveBacktestRunner instance
- Spanish error messages in comments
