# Configuration Consolidation Summary

## Overview

This document summarizes the consolidation of backtesting configuration files to eliminate duplication and establish clear separation of concerns.

**Date**: 2026-01-26
**Status**: Complete
**Backward Compatibility**: Maintained

---

## Problem Statement

The project had two configuration files with overlapping responsibilities:

1. **`config/backtesting/profile_optimization.yaml`** - Detailed parameters for optimization
2. **`config/profile_batch_backtest.yaml`** - Workflow orchestration

This caused confusion about:
- Which config to use for specific settings
- Where to add new parameters
- How to maintain consistency between files

---

## Solution Design

### Clear Separation of Concerns

#### **`profile_batch_backtest.yaml` - Workflow Configuration**

**Purpose**: Orchestrates batch testing workflow

**Contains**:
- Database connection settings
- Output directories and report formats
- Symbol universe and backtest period
- Profile generation (capital tiers, investment horizons, risk levels)
- Parallel execution settings (profile-level)
- Logging configuration
- Module enable/disable flags

**Key Principle**: This file controls **what** gets tested and **how** the workflow executes.

#### **`profile_optimization.yaml` - Parameters Configuration**

**Purpose**: Defines all parameter values and search spaces

**Contains**:
- Common backtesting parameters (random_state, cv_folds, test_size)
- Threading/worker pool settings (backtest-level)
- Model parameters (RF, XGBoost, LightGBM, SVM, etc.)
- Reinforcement learning config
- Threshold optimization search spaces
- Validation method parameters (walk-forward, Monte Carlo, OOS)
- Module-specific parameters (filters, market detectors)
- Profile-specific overrides (conservative, balanced, aggressive, etc.)
- Tier-specific overrides (micro, small, medium, large)

**Key Principle**: This file defines **parameter values** and **optimization ranges**.

---

## Configuration Hierarchy

When loading configuration, values are applied in this order:

1. **Default values** (defined in `profile_optimization.yaml` base sections)
2. **Profile-specific overrides** (from `profile_optimization.yaml` profiles section)
   - conservative, balanced, aggressive, income, growth, dividendos
3. **Tier-specific overrides** (from `profile_optimization.yaml` tiers section)
   - micro, small, medium, large
4. **Runtime overrides** (code-level overrides take precedence)

**Precedence Rule**: When there's a conflict between workflow settings (batch config) and parameter settings (optimization config), workflow settings take precedence for batch execution.

---

## Cross-References Added

### In `profile_batch_backtest.yaml`

```yaml
# COMPLEMENTARY CONFIGURATION:
# - Strategy/optimization parameters: config/backtesting/profile_optimization.yaml
# - Module filter parameters: config/backtesting/profile_optimization.yaml
# - Validation thresholds: config/backtesting/profile_optimization.yaml

# PRECEDENCE:
# - This config defines workflow orchestration
# - profile_optimization.yaml defines parameter values and search spaces
# - When in doubt, workflow settings here take precedence for batch execution

# USAGE EXAMPLES:
#   # Run all 180 profile combinations
#   python run_profile_batch_backtester.py --all
#
#   # Run specific tier and risk level
#   python run_profile_batch_backtester.py --tier medio --risk alto
```

### In `profile_optimization.yaml`

```yaml
# COMPLEMENTARY CONFIGURATION:
# - Workflow orchestration: config/profile_batch_backtest.yaml
#   (database, output directories, symbol lists, profile generation)

# SEPARATION OF CONCERNS:
# - This file (profile_optimization.yaml): Parameters and search spaces
# - profile_batch_backtest.yaml: Workflow orchestration and execution

# USAGE EXAMPLES:
#   # Load default parameters
#   from app.core.config.profile_config_loader import get_profile_config_loader
#   loader = get_profile_config_loader()
#
#   # Load with profile override
#   loader = get_profile_config_loader(profile="aggressive", tier="medium")
```

---

## Configuration Validation

### New Validator Classes

#### **`ProfileOptimizationConfigValidator`**

Validates:
- Common parameters (test_size, cv_folds, random_state)
- Threading parameters (worker_multiplier, batch_size)
- Validation thresholds (min_sharpe, max_drawdown, min_win_rate)
- Threshold optimization ranges (min < max for all ranges)
- Profile overrides (conservative, balanced, aggressive, etc.)
- Tier overrides (micro, small, medium, large)

#### **`BatchBacktestConfigValidator`**

Validates:
- Database URL format and protocol
- Symbol list (non-empty, max 100 symbols)
- Backtest period dates (YYYY-MM-DD format, start < end)
- Capital tiers (at least one defined)
- Investment horizons (at least one defined)
- Optimization settings (n_trials, n_jobs ranges)
- Parallelization limits (max_profiles range)
- Cross-config references (module names)

### Validation Commands

```bash
# Validate batch backtest config only
python -m app.core.config_validator --batch-config

# Validate profile optimization config only
python -m app.core.config_validator --profile-optimization

# Validate all backtesting configs
python -m app.core.config_validator --all-backtesting

# Validate production config
python -m app.core.config_validator --environment production --env-file .env.prod
```

### Validation Results

Both configurations pass validation successfully:

```
=== Batch Backtest Config ===
Configuration validation passed: All checks OK

=== Profile Optimization Config ===
Configuration validation passed: All checks OK

All backtesting configurations are valid!
```

---

## Files Modified

### `/Users/kepa.cantero/Projects/algoTrading/config/profile_batch_backtest.yaml`

**Changes**:
- Added comprehensive header documentation
- Added cross-references to `profile_optimization.yaml`
- Removed duplicate search space definitions (now reference profile_optimization.yaml)
- Removed duplicate module parameter definitions (now reference profile_optimization.yaml)
- Removed duplicate validation settings (now reference profile_optimization.yaml)
- Added validation section documentation

**Key Sections**:
- Database configuration
- Output configuration
- Capital tiers and investment horizons
- Backtest period and symbols
- Risk and objective parameters
- Optimization workflow control (n_trials, n_jobs)
- Validation enable flags
- Module enable flags
- Reporting configuration
- Parallel execution (profile-level)
- Logging

### `/Users/kepa.cantero/Projects/algoTrading/config/backtesting/profile_optimization.yaml`

**Changes**:
- Added comprehensive header documentation
- Added cross-references to `profile_batch_backtest.yaml`
- Clarified configuration hierarchy
- Added usage examples in comments
- Documented profile and tier override system

**Key Sections**:
- Common parameters (random_state, test_size, cv_folds)
- Threading configuration (backtest-level workers, batch size)
- Model parameters (RF, XGBoost, LightGBM, SVM, LR)
- Reinforcement learning config (environment, rewards, algorithms)
- Threshold optimization search spaces (all indicators)
- Validation parameters (walk-forward, Monte Carlo, OOS)
- Reporting configuration
- Memory management
- Profile-specific overrides
- Tier-specific overrides
- Backtest type specific parameters
- Debugging and logging

### `/Users/kepa.cantero/Projects/algoTrading/app/core/config_validator.py`

**Changes**:
- Added `ProfileOptimizationConfigValidator` class
- Added `BatchBacktestConfigValidator` class
- Added `validate_profile_optimization_config()` method
- Added `validate_batch_backtest_config()` method
- Added `_validate_threshold_ranges()` helper
- Added `_validate_profile_overrides()` helper
- Added `_validate_tier_overrides()` helper
- Added `_validate_cross_config_references()` helper
- Updated CLI with new options:
  - `--batch-config`
  - `--profile-optimization`
  - `--all-backtesting`

---

## Usage Examples

### Loading Configuration in Code

```python
# Load profile optimization parameters
from app.core.config.profile_config_loader import get_profile_config_loader

# Default parameters
loader = get_profile_config_loader()
random_state = loader.get_random_state()  # 42

# With profile override
loader = get_profile_config_loader(profile="aggressive", tier="medium")
rf_params = loader.get_random_forest_params()

# Get threshold ranges
rsi_config = loader.get_threshold_config("rsi")
buy_min, buy_max, buy_step = loader.get_parameter_range(
    "threshold_optimization.rsi.buy_threshold"
)

# Validate config
from app.core.config_validator import ConfigValidator
validator = ConfigValidator()
result = validator.validate_batch_backtest_config()
result.print_summary()
```

### Running Batch Backtests

```bash
# Run all 180 profile combinations
python run_profile_batch_backtester.py --all

# Run specific tier and risk level
python run_profile_batch_backtester.py --tier medio --risk alto

# Validate configs before running
python -m app.core.config_validator --all-backtesting
```

---

## Backward Compatibility

### Maintained

1. **Existing code paths**: All existing code that loads these configs continues to work
2. **Parameter structure**: No changes to parameter names or structure
3. **Profile and tier overrides**: Override system unchanged
4. **Config loader**: `ProfileConfigLoader` API unchanged

### Migration Path

For code that has hardcoded parameter ranges:

**Before**:
```python
# Hardcoded in profile_batch_backtest.yaml
search_space:
  rsi_threshold:
    low: 30
    high: 70
```

**After**:
```python
# Now loaded from profile_optimization.yaml
loader = get_profile_config_loader()
rsi_config = loader.get_threshold_config("rsi")
search_space = {
    "low": rsi_config["buy_threshold"]["min"],
    "high": rsi_config["buy_threshold"]["max"]
}
```

---

## Benefits of Consolidation

### 1. **Clear Separation**
- Workflow vs. parameters
- Orchestration vs. optimization
- Execution vs. configuration

### 2. **Reduced Duplication**
- Single source of truth for parameter values
- No conflicting definitions
- Easier to maintain

### 3. **Better Documentation**
- Clear comments in each file
- Cross-references between files
- Usage examples

### 4. **Improved Validation**
- Automatic validation of both configs
- Cross-config reference checking
- Clear error messages

### 5. **Easier Extension**
- Know where to add new parameters
- Clear override hierarchy
- Documented precedence rules

---

## Testing

### Validation Tests

```bash
# All configs pass validation
python -m app.core.config_validator --all-backtesting
# Output: All backtesting configurations are valid!

# Individual validation
python -m app.core.config_validator --batch-config
# Output: Configuration validation passed: All checks OK

python -m app.core.config_validator --profile-optimization
# Output: Configuration validation passed: All checks OK
```

### Integration Tests

Existing tests continue to pass:
- `tests/unit/core/test_config_validator.py`
- `tests/integration/backtesting/test_profile_batch_backtester.py`

---

## Next Steps

### Recommended Actions

1. **Update Documentation**
   - Update developer docs to reflect new config structure
   - Add config examples to README

2. **Migrate Hardcoded Values**
   - Find code with hardcoded parameter ranges
   - Migrate to use `ProfileConfigLoader`

3. **Add More Validations**
   - Add validation for cross-config consistency
   - Add validation for profile/tier combination validity

4. **Performance Testing**
   - Test config loading performance
   - Optimize if needed

### Future Enhancements

1. **Config Migration Tool**
   - Auto-migrate old config files to new structure
   - Validate and report conflicts

2. **Config Diff Tool**
   - Compare two config files
   - Show parameter differences

3. **Config Generator**
   - Generate config from template
   - Validate before saving

---

## Appendix: Quick Reference

### Config File Locations

```
config/
├── profile_batch_backtest.yaml          # Workflow orchestration
└── backtesting/
    └── profile_optimization.yaml        # Parameter configuration
```

### Key Code Locations

```
app/core/
├── config/
│   ├── profile_config_loader.py         # Load profile_optimization.yaml
│   └── config_validator.py              # Validate both configs
└── config_loader.py                     # Generic YAML loader

app/backtesting/
└── profile_batch_backtester.py          # Uses profile_batch_backtest.yaml
```

### Validation Commands

```bash
# Quick validation
python -m app.core.config_validator --all-backtesting

# Detailed validation
python -m app.core.config_validator --batch-config
python -m app.core.config_validator --profile-optimization

# Help
python -m app.core.config_validator --help
```

### Configuration Precedence

```
1. Default values (profile_optimization.yaml)
2. Profile overrides (profile_optimization.yaml -> profiles)
3. Tier overrides (profile_optimization.yaml -> tiers)
4. Runtime overrides (code)
5. Workflow settings (profile_batch_backtest.yaml) - takes precedence
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-26
**Author**: Claude (Backend Developer)
**Status**: Complete and Validated
