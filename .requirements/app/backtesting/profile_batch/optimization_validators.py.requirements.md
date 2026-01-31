# optimization_validators.py

## Purpose
Provides validation components for the optimization pipeline including walk-forward validation, Monte Carlo simulation, and out-of-sample validation to ensure strategy robustness and prevent overfitting.

---

## Type Definitions / Data Classes

### WalkForwardValidator Class
```python
class WalkForwardValidator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]          # REQUIRED - Validation configuration parameters
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `output_dir` must exist or be creatable
- `validation_config` must contain "walk_forward" key with n_windows and train_percentage
- Minimum 365 days of data required for validation

### MonteCarloSimulator Class
```python
class MonteCarloSimulator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]          # REQUIRED - Validation configuration parameters
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `n_simulations` must be >= 100 (default: 1000)
- `min_profitable_pct` must be between 0 and 1 (default: 0.95)
- Returns empty dict if backtest fails

### OutOfSampleValidator Class
```python
class OutOfSampleValidator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]          # REQUIRED - Validation configuration parameters
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `train_percentage` must be between 0.5 and 0.9 (default: 0.7)
- `min_oos_sharpe` must be >= 0 (default: 0.5)
- `max_performance_decay` must be between 0 and 1 (default: 0.3)

---

## Function Signatures (Contracts)

### `WalkForwardValidator.validate(profile, config, params) -> Dict[str, Any]`
**Pre:** profile must be valid InputProfile, config must have start/end dates, params must be valid strategy parameters
**Post:** Returns dict with 'passed' bool and validation metrics including avg_sharpe, std_sharpe, n_windows
**Raises:** ValueError, TypeError, KeyError, AttributeError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Creates temporary YAML files, runs multiple backtests, writes logs

### `MonteCarloSimulator.simulate(profile, config, params) -> Dict[str, Any]`
**Pre:** profile must be valid, config valid, backtest must return trade data or returns_series
**Post:** Returns dict with 'passed' bool and simulation metrics including profitable_pct, avg_return, std_return
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Runs backtest, performs bootstrap sampling, writes logs

### `OutOfSampleValidator.validate(profile, config, params) -> Dict[str, Any]`
**Pre:** profile valid, config has start/end dates with sufficient range, params valid
**Post:** Returns dict with 'passed' bool, train_sharpe, oos_sharpe, sharpe_decay
**Raises:** ValueError, TypeError, KeyError, AttributeError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Runs train/test backtests, creates temp YAML files, writes logs

---

## Acceptance Criteria
- [ ] Walk-forward validation requires minimum 365 days of data (auto-fails if insufficient)
- [ ] Monte Carlo simulation returns profitable_pct >= 0.95 for passing strategies
- [ ] Out-of-sample validation requires oos_sharpe >= 0.5 and sharpe_decay <= 0.3
- [ ] All validators create temporary config files with unique UUIDs
- [ ] All validators clean up temporary files after execution
- [ ] All validators return consistent dict structure with 'passed' key
- [ ] Failed validations return error message in 'error' key
- [ ] All backtest errors are caught and logged without crashing

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets in validators |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - All exceptions logged with exc_info=True |
| BT-001 | BASE_RULES.md | Walk-forward validation required | ✅ OK - Implemented in WalkForwardValidator |
| BT-002 | BASE_RULES.md | Out-of-sample testing required | ✅ OK - Implemented in OutOfSampleValidator |
| BT-005 | BASE_RULES.md | Test across different market regimes | ⚠️ PARTIAL - Walk-forward covers regimes but no explicit regime detection |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Missing return type hints for private methods |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming throughout |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| TRD-004 | BASE_RULES.md | Audit trail logging | ⚠️ PARTIAL - Logging present but not structured as audit trail |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas, yaml, uuid, logging, pathlib
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_optimization_validators.py:**
  - Test WalkForwardValidator.validate() with sufficient data (365+ days)
  - Test WalkForwardValidator.validate() with insufficient data (<365 days) - should fail
  - Test WalkForwardValidator.validate() creates and cleans up temp files
  - Test MonteCarloSimulator.simulate() with valid backtest results
  - Test MonteCarloSimulator.simulate() with no trade data - should fail gracefully
  - Test MonteCarloSimulator.simulate() bootstrap sampling accuracy
  - Test OutOfSampleValidator.validate() with valid train/test split
  - Test OutOfSampleValidator.validate() with performance decay > threshold
  - Test OutOfSampleValidator.validate() with low OOS Sharpe - should fail
  - Test all validators handle exceptions and return error dict
  - Test _run_backtest_with_params() temp file cleanup
  - Test _get_empty_metrics() returns correct structure

---

## Notes
- All three validators are independent and can be used in any combination
- Each validator runs its own backtests with temporary config files
- UUID hex is used for temp file naming to avoid collisions
- Missing `uuid` import in WalkForwardValidator._run_backtest_with_params() (line 151)
- All validators use the same _get_empty_metrics() structure for consistency
