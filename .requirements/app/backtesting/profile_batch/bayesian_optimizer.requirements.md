# bayesian_optimizer.py

## Purpose
Performs Bayesian optimization using Optuna to efficiently explore hyperparameter space and find optimal strategy parameters.

---

## Type Definitions / Data Classes
No custom dataclasses defined - uses standard Dict and Any types.

---

## Function Signatures (Contracts)

### `optimize(profile, config, multi_strategy) -> Dict[str, Any]`
**Pre:** profile is valid InputProfile, config has strategy section
**Post:** Returns dict with best_params, best_metrics, best_value, history, n_trials
**Raises:** Returns dict with empty metrics on backtest failure
**Retry:** No (Optuna handles internal retries)
**Side Effects:** Creates temporary YAML config file, runs backtests, deletes temp file

### `_get_parameter_ranges() -> tuple`
**Pre:** profile_config_loader is initialized (optional)
**Post:** Returns (rsi_buy_min, rsi_buy_max, vol_min, vol_max)
**Raises:** Returns defaults (20, 35, 1.0, 1.5) on config error
**Retry:** No
**Side Effects:** None (reads config)

### `_run_backtest_with_params(profile, config, params, multi_strategy) -> Dict[str, Any]`
**Pre:** profile and config are valid, params has all required strategy parameters
**Post:** Returns metrics dict with sharpe_ratio, return_pct, etc.
**Raises:** Returns empty metrics dict on failure
**Retry:** No
**Side Effects:** Creates/deletes temp YAML file, runs ComprehensiveBacktestRunner

---

## Acceptance Criteria
- [ ] Bayesian optimization uses Optuna with direction="maximize"
- [ ] Objective function maximizes Sharpe ratio (or combined Sharpe for multi-strategy)
- [ ] Parameter ranges: rsi_threshold (20-35), ema_short (5-20), ema_long (20-50), volume_threshold (1.0-1.5), stop_loss (0.01-0.05), take_profit (0.05-0.20)
- [ ] Study name includes objective and profile input_id
- [ ] Returns best_params, best_metrics (from re-run), best_value, history (all trials), n_trials
- [ ] Failed trials return -1.0 and are logged
- [ ] Temporary config files created with unique UUID names
- [ ] Temporary config files cleaned up in finally block
- [ ] Supports both single-strategy and multi-strategy modes
- [ ] Parameter ranges loaded from ProfileConfigLoader if available

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Catches ValueError, TypeError, KeyError, etc. |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ⚠️ NOT APPLIED - optimize() > 20 lines |
| BT-003 | BASE_RULES | No look-ahead bias | ✅ OK - Each trial independent |
| BT-004 | BASE_RULES | Realistic costs | ✅ OK - Uses config from backtest runner |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - History provides audit trail |

**NOTE:** Optuna's Bayesian optimization is more efficient than grid search - explores promising areas of parameter space.

---

## Dependencies
- **External:** logging, pathlib, typing, optuna, yaml
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_bayesian_optimizer.py:**
  - Test optimize() returns best parameters
  - Test optimize() with multi_strategy=True uses combined metrics
  - Test optimize() history contains all trials
  - Test failed trial returns -1.0 and is logged
  - Test _get_parameter_ranges() loads from ProfileConfigLoader
  - Test _get_parameter_ranges() falls back to defaults on error
  - Test _run_backtest_with_params() creates and deletes temp file
  - Test _run_backtest_with_params() returns empty metrics on failure
  - Test objective function suggests int for rsi_threshold
  - Test objective function suggests float for volume_threshold
  - Test study name includes objective and input_id
  - Test cleanup of temp file in finally block

---

## Notes
Bayesian optimization is much more efficient than grid/random search for hyperparameter tuning, especially with expensive-to-evaluate functions like backtesting.
