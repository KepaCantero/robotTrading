# backtest_type.py

## Purpose
BacktestType Enum - Types of backtesting operations supported by the system.

---

## Type Definitions / Data Classes

### BacktestType (Enum)
```python
class BacktestType(Enum):
    BASELINE = "baseline"                      # Standard baseline backtest
    LEARNING_ENGINES = "learning_engines"      # Machine learning engine tests
    WALK_FORWARD = "walk_forward"              # Walk-forward optimization
    MONTE_CARLO = "monte_carlo"                # Monte Carlo simulation
    TRANSFORMER_OPTIMIZATION = "transformer_optimization"  # Transformer model optimization
    ABLATION = "ablation"                      # Ablation study (remove components)
    GRID_SEARCH = "grid_search"                # Grid search optimization
    OUT_OF_SAMPLE = "out_of_sample"            # Out-of-sample testing
    MULTI_STRATEGY = "multi_strategy"          # Multi-strategy comparison
    REGIME_TEST = "regime_test"                # Regime-based testing
```

**Properties:**
- Enum (string values)
- Immutable (Enum members are singletons)
- Hashable (can be used in sets and dicts)

---

## Function Signatures (Contracts)

No methods - pure enumeration type.

---

## Acceptance Criteria
- [ ] **AC-001:** 10 backtest types defined
- [ ] **AC-002:** All values are strings
- [ ] **AC-003:** BASELINE is the default backtest type
- [ ] **AC-004:** WALK_FORWARD for walk-forward optimization (Pardo)
- [ ] **AC-005:** MONTE_CARLO for Monte Carlo simulation

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (BacktestType Enum):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Enum immutability | Python std | Enum members are immutable | ✅ OK - Enum type |
| String values | Clean code | String values for serialization | ✅ OK - All strings |
| Baseline type | Pardo (2008) | Standard backtest | ✅ OK - BASELINE |
| Walk-forward | Pardo (2008) | Rolling window optimization | ✅ OK - WALK_FORWARD |
| Monte Carlo | Risk analysis | Monte Carlo simulation | ✅ OK - MONTE_CARLO |
| Ablation study | ML research | Component removal test | ✅ OK - ABLATION |
| Grid search | Optimization | Hyperparameter search | ✅ OK - GRID_SEARCH |
| Out-of-sample | Validation | Holdout validation | ✅ OK - OUT_OF_SAMPLE |
| Multi-strategy | Portfolio | Strategy comparison | ✅ OK - MULTI_STRATEGY |
| Regime test | Chan (2013) | Regime-specific testing | ✅ OK - REGIME_TEST |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008) for backtesting standards.

---

## Dependencies
- **External:** `enum` (std)
- **Internal:** None (enum type)

---

## Required Tests
- **test_backtest_type_enum.py:**
  - `test_all_types_defined()` - 10 types defined
  - `test_values_are_strings()` - All values are strings
  - `test_baseline_value()` - "baseline"
  - `test_walk_forward_value()` - "walk_forward"
  - `test_monte_carlo_value()` - "monte_carlo"
  - `test_learning_engines_value()` - "learning_engines"
  - `test_transformer_optimization_value()` - "transformer_optimization"
  - `test_ablation_value()` - "ablation"
  - `test_grid_search_value()` - "grid_search"
  - `test_out_of_sample_value()` - "out_of_sample"
  - `test_multi_strategy_value()` - "multi_strategy"
  - `test_regime_test_value()` - "regime_test"
  - `test_hashable()` - Can use in set/dict
  - `test_comparison()` - Enum comparison works
  - `test_string_representation()` - String value accessible

---

## Notes
- **Critical:** BacktestType is an ENUM (immutable, singleton members, string values)
- **Enum Type:** Python enum.Enum ensures each member is a singleton
- **String Values:** All values are lowercase strings with underscores for serialization
- **Backtest Types:**
  - **BASELINE:** Standard historical backtest (Pardo, 2008)
  - **LEARNING_ENGINES:** Tests for machine learning models
  - **WALK_FORWARD:** Walk-forward optimization with rolling windows (Pardo, 2008)
  - **MONTE_CARLO:** Monte Carlo simulation for risk analysis
  - **TRANSFORMER_OPTIMIZATION:** Transformer model hyperparameter optimization
  - **ABLATION:** Ablation study - test impact of removing components
  - **GRID_SEARCH:** Grid search over hyperparameter space
  - **OUT_OF_SAMPLE:** Out-of-sample validation on holdout data
  - **MULTI_STRATEGY:** Comparison of multiple strategies
  - **REGIME_TEST:** Test strategy performance under different market regimes (Chan, 2013)
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008) - walk-forward validation
- **Chan Reference:** "Algorithmic Trading" (2013) - regime detection and testing
- **Usage Pattern:** BacktestType categorizes backtests for configuration, routing, and analysis

---

**File Reference:** `app/domain/value_objects/backtest_type.py`
**Last Audited:** 2026-02-01
