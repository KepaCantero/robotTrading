# Quick Profile Test - Analysis and Issues

## Overview

This document analyzes the `quick_profile_test.py` script against the requirements for 10 backtesting types over a 5-day period.

---

## Current Implementation Status

### What Works ✅

| Feature | Status | Notes |
|---------|--------|-------|
| SOLID Principles | ✅ Implemented | SRP, OCP, LSP, ISP, DIP via Protocols |
| Silent Killers Protection | ✅ Implemented | PERF-002 (gc.collect), TRD-005 (NaN detection), Idempotency (UUID) |
| Symbol Categories | ✅ Updated | 5 categories: ETFs, Stocks, Dividendos, Cryptos, Forex (250 total) |
| 5-Day Test Period | ✅ Configured | Auto-calculated as most recent 5 trading days |
| Profile Combinations | ✅ Working | 60 profiles (5 objectives × 3 risks × 4 horizons) |
| AAA Pattern | ✅ Implemented | Arrange-Act-Assert in `run_single()` |

### What's Missing ❌

| Requirement | Status | Issue |
|-------------|--------|-------|
| 10 Backtest Types | ❌ NOT IMPLEMENTED | Only profile-based testing |
| Baseline Backtest | ⚠️ PARTIAL | Runs via profile, not as separate backtest type |
| Learning Engines | ⚠️ PARTIAL | Configured but not individually tested |
| Walk-Forward | ❌ MISSING | Not implemented |
| Monte Carlo | ❌ MISSING | Not implemented |
| Grid Search | ❌ MISSING | Not implemented |
| Ablation Study | ❌ MISSING | Not implemented |
| Out-of-Sample | ❌ MISSING | Not implemented |
| Multi-Strategy | ❌ MISSING | Not implemented |
| Regime Test | ❌ MISSING | Not implemented |
| Hyperparameter Opt | ❌ MISSING | Not implemented |

---

## Detailed Issues

### Issue #1: Architecture Mismatch

**Problem**: The current script uses `ProfileBatchBacktester` which is designed for profile-based backtesting, NOT for the 10 different backtest types.

**Evidence**:
```python
# Current implementation (line 323)
result_obj = self._backtester.run_single_profile(profile, multi_strategy=True)
```

**Impact**: Cannot run:
- Walk-forward (needs train/test windows)
- Monte Carlo (needs simulation loops)
- Grid Search (needs parameter iteration)
- Ablation (needs module isolation)
- etc.

**Solution Required**: Either:
1. Replace `ProfileBatchBacktester` with `ComprehensiveBacktestRunner`
2. Create individual runners for each backtest type (like in `comprehensive_5day_test.py`)

---

### Issue #2: 5-Day Data Limitation

**Problem**: Some backtest types require more data than 5 days.

| Backtest Type | Min Data Required | 5-Day Feasibility |
|---------------|-------------------|-------------------|
| Baseline | 5 days | ✅ Yes |
| Learning Engines | 100+ days | ⚠️ Barely usable |
| Walk-Forward | Train+Test+Step | ❌ Needs 20+ days |
| Monte Carlo | Any (but needs meaningful data) | ⚠️ Limited value |
| Grid Search | Depends on parameter space | ⚠️ Limited value |
| Ablation | Any | ✅ Yes |
| Out-of-Sample | Train+Val+Test | ❌ Needs 30+ days |
| Multi-Strategy | Any | ✅ Yes |
| Regime Test | 100+ days (for regime detection) | ❌ Not feasible |
| Hyperparameter | 100+ days | ⚠️ Barely usable |

**Recommendation**: For meaningful results, use at least 252 trading days (1 year).

---

### Issue #3: Symbol Category Support

**Problem**: Not all symbols may be supported by the data loader.

**Questionable Symbols**:
- **Cryptos** (BTCUSD, ETHUSD, etc.) - Does the data loader support crypto data?
- **Forex** (EURUSD, GBPUSD, etc.) - Does the data loader support forex data?

**Verification Needed**:
```python
# Need to verify DataLoader supports:
loader = DataLoader()
crypto_quotes = loader.load_market_data("BTCUSD", ...)  # Will this work?
forex_quotes = loader.load_market_data("EURUSD", ...)  # Will this work?
```

---

### Issue #4: Missing Configuration Sections

**Problem**: The config created in `_create_config()` may not include all required sections for 10 backtest types.

**Current Config Sections** (line 247-296):
```python
config = {
    "database": {...},
    "output_dir": str(self._output_dir),
    "capital_tiers": {...},
    "investment_horizons": {...},
    "backtest_period": {...},
    "input": {...},
    "parallel_execution": {...},
    "optimization": {...},
    "learning_engines": {...},
    "reporting": {...},
}
```

**Missing Sections**:
- `walk_forward` - Not configured
- `monte_carlo` - Not configured
- `grid_search` - Not configured
- `ablation` - Not configured
- `out_of_sample` - Not configured
- `multi_strategy` - Not configured
- `regime_test` - Not configured
- `hyperparameter_optimization` - Not configured

---

### Issue #5: Test Result Model Limitation

**Problem**: `TestResult` dataclass doesn't capture all metrics needed for 10 backtest types.

**Current Fields** (line 71-88):
```python
@dataclass
class TestResult:
    profile_id: str
    status: TestStatus
    baseline_return: float | None = None
    optimized_return: float | None = None
    improvement_pct: float = 0.0
    error_message: str | None = None
    execution_time: float = 0.0
    has_valid_weights: bool = False
    nan_count: int = 0
```

**Missing Fields**:
- `backtest_type: BacktestType` - Which backtest type was run
- `regime: str | None` - For regime tests
- `mc_var_95: float | None` - For Monte Carlo VaR
- `grid_best_params: dict | None` - For grid search
- `ablation_module: str | None` - For ablation study
- `oos_sharpe: float | None` - For out-of-sample validation

---

## Recommended Solutions

### Solution A: Use `comprehensive_5day_test.py` Instead

The `comprehensive_5day_test.py` script already implements:
- ✅ All 10 backtest type runners
- ✅ Proper result models for each type
- ✅ Configuration for all backtest types
- ✅ SOLID architecture

**Action**: Replace `quick_profile_test.py` usage with `comprehensive_5day_test.py`.

### Solution B: Refactor `quick_profile_test.py`

If `quick_profile_test.py` must be used:

1. **Add BacktestType enum and runners** (from `comprehensive_5day_test.py`):
```python
class BacktestType(Enum):
    BASELINE = "baseline"
    LEARNING_ENGINES = "learning_engines"
    # ... etc
```

2. **Replace `ProfileBatchBacktester` with `ComprehensiveBacktestRunner`**:
```python
self._backtester: ComprehensiveBacktestRunner | None = None
```

3. **Update configuration to include all backtest types**:
```python
config = {
    # ... existing ...
    "walk_forward": {"enabled": True, ...},
    "monte_carlo": {"enabled": True, ...},
    # ... etc
}
```

4. **Update `TestResult` to include backtest-specific metrics**

5. **Add 5-day feasibility checks**:
```python
def _is_feasible_for_5day(bt_type: BacktestType) -> bool:
    """Check if backtest type can run with 5-day data."""
    infeasible = [
        BacktestType.WALK_FORWARD,
        BacktestType.OUT_OF_SAMPLE,
        BacktestType.REGIME_TEST,
    ]
    return bt_type not in infeasible
```

---

## Decision Matrix

| Option | Effort | Time | Quality | Recommendation |
|--------|--------|------|---------|----------------|
| Use `comprehensive_5day_test.py` | Low | Immediate | High | ✅ **RECOMMENDED** |
| Refactor `quick_profile_test.py` | High | 2-3 hours | Medium | ⚠️ Only if profiles required |
| Extend test period to 1 year | Low | Immediate | High | ✅ Do this regardless |

---

## Conclusion

The `quick_profile_test.py` script is well-designed for profile-based testing but **cannot** currently run the 10 backtest types as required.

**Recommended Actions**:
1. Use `comprehensive_5day_test.py` for 10 backtest types
2. Extend test period from 5 days to 252 days (1 year) for meaningful results
3. Verify symbol support for cryptos and forex
4. Add 5-day feasibility warnings for incompatible backtest types

---

*Analysis Date: 2026-02-07*
*Analyzer: Claude Code*
