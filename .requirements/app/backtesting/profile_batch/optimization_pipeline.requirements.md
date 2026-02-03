# optimization_pipeline.py

## Purpose
Orchestrates complete optimization workflow: Bayesian optimization, walk-forward validation, Monte Carlo simulation, out-of-sample validation, comparison, and recommendation generation.

---

## Type Definitions / Data Classes

### BaselineOptimizationComparison Class
```python
@dataclass
class BaselineOptimizationComparison:
    sharpe_improvement: float              # REQUIRED - Sharpe improvement percentage
    return_improvement: float              # REQUIRED - Return improvement percentage
    max_dd_improvement: float              # REQUIRED - Max DD improvement percentage
    win_rate_improvement: float            # REQUIRED - Win rate improvement percentage
    sharpe_significant: bool               # REQUIRED - Sharpe improvement exceeds threshold
    return_significant: bool               # REQUIRED - Return improvement exceeds threshold
    parameter_importance: Dict[str, float] # REQUIRED - Parameter importance scores
    recommended: str                       # REQUIRED - "optimized" | "baseline" | "inconclusive"
    confidence: float                      # REQUIRED - 0-1 confidence score
    reason: str                            # REQUIRED - Text explanation
```

**Validation Rules:**
- confidence in range [0, 1]
- recommended must be one of three valid values
- reason must be non-empty

### OptimizedStrategy Class
```python
@dataclass
class OptimizedStrategy:
    profile_id: str                                # REQUIRED - Profile identifier
    baseline_metrics: Dict[str, Any]                # REQUIRED - Baseline metrics
    optimized_metrics: Dict[str, Any]               # REQUIRED - Optimized metrics
    best_parameters: Dict[str, Any]                 # REQUIRED - Best parameters found
    optimization_history: list[Dict[str, Any]]       # REQUIRED - All Optuna trials
    walk_forward_results: Dict[str, Any] | None     # OPTIONAL - Walk-forward validation
    monte_carlo_results: Dict[str, Any] | None      # OPTIONAL - Monte Carlo results
    out_of_sample_results: Dict[str, Any] | None    # OPTIONAL - Out-of-sample validation
    comparison: BaselineOptimizationComparison      # REQUIRED - Comparison object
    ready_for_paper_trading: bool                   # REQUIRED - Paper trading ready
    recommendation: str                             # REQUIRED - Text recommendation
```

**Validation Rules:**
- profile_id non-empty
- At least one validation result should be non-None
- ready_for_paper_trading requires all three validations to pass

---

## Function Signatures (Contracts)

### `run_optimization_pipeline(profile, config, baseline_metrics, multi_strategy) -> OptimizedStrategy`
**Pre:** profile is valid, config has strategy section, baseline_metrics populated
**Post:** Returns OptimizedStrategy with all 5 stages completed
**Raises:** Returns partial results if any stage fails
**Retry:** No
**Side Effects:** Runs backtests, creates temp files, calls validators

### `_generate_comparison(baseline, optimized, optuna_results) -> BaselineOptimizationComparison`
**Pre:** baseline and optimized dicts have matching metrics, optuna_results has history
**Post:** Returns comparison with improvements, significance, parameter importance, recommendation
**Raises:** None
**Retry:** No
**Side Effects:** None (calculation)

### `_calculate_parameter_importance(history) -> Dict[str, float]`
**Pre:** history list has dicts with 'value' and 'params' keys
**Post:** Returns dict with normalized importance scores (0-1)
**Raises:** Returns empty dict on error
**Retry:** No
**Side Effects:** None (calculates correlation)

### `_pct_improvement(baseline, optimized) -> float`
**Pre:** baseline and optimized are numeric
**Post:** Returns percentage improvement
**Raises:** ZeroDivisionError if baseline is 0 (returns 0)
**Retry:** No
**Side Effects:** None (calculation)

### `_generate_recommendation(comparison, ready) -> str`
**Pre:** comparison has recommended and reason fields
**Post:** Returns recommendation string based on ready flag and comparison
**Raises:** None
**Retry:** No
**Side Effects:** None (string formatting)

---

## Acceptance Criteria
- [ ] Pipeline executes 5 stages in order: Bayesian optimization, walk-forward, Monte Carlo, OOS, comparison
- [ ] Ready for paper trading requires ALL three validations to pass (walk_forward, monte_carlo, oos)
- [ ] Significance threshold: 5% improvement (configurable via acceptance_criteria)
- [ ] Strong significance threshold: 10% improvement
- [ ] Degradation threshold: -5% (worse than baseline)
- [ ] Recommendation logic: "optimized" if sharpe_imp > 10% AND significant, "baseline" if sharpe_imp < -5%, "inconclusive" otherwise
- [ ] Confidence scores: 0.8 for optimized, 0.7 for baseline, 0.5 for inconclusive
- [ ] Parameter importance calculated from correlation between param and objective value
- [ ] Importance normalized to 0-1 scale
- [ ] Handles multi-strategy mode with combined metrics

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Validators handle errors |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ NOT APPLIED - run_optimization_pipeline > 20 lines |
| BT-001 | BASE_RULES | Walk-forward validation | ✅ OK - Stage 2 of pipeline |
| BT-002 | BASE_RULES | Out-of-sample testing | ✅ OK - Stage 4 of pipeline |
| BT-005 | BASE_RULES | Multiple periods | ✅ OK - Walk-forward tests multiple windows |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - History provides audit trail |

**NOTE:** Pipeline design follows clean architecture with dependency injection - all components injected via constructor.

---

## Dependencies
- **External:** logging, dataclasses, pathlib, typing, numpy, pandas
- **Internal:**
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile`
  - `.bayesian_optimizer.BayesianOptimizer`
  - `.optimization_validators.WalkForwardValidator`
  - `.optimization_validators.MonteCarloSimulator`
  - `.optimization_validators.OutOfSampleValidator`

---

## Required Tests
- **tests/backtesting/profile_batch/test_optimization_pipeline.py:**
  - Test run_optimization_pipeline() executes all 5 stages
  - Test run_optimization_pipeline() with multi_strategy=True
  - Test _generate_comparison() with significant improvement
  - Test _generate_comparison() with degradation
  - Test _generate_comparison() inconclusive case
  - Test _calculate_parameter_importance() normalizes to 0-1
  - Test _calculate_parameter_importance() handles empty history
  - Test _pct_improvement() with zero baseline
  - Test _generate_recommendation() for ready=True
  - Test _generate_recommendation() for ready=False
  - Test ready_for_paper_trading requires all validations pass
  - Test confidence scores match recommendation type

---

## Notes
Pipeline is designed to be sequential and synchronous. For production with many profiles, consider parallel execution at profile level.
