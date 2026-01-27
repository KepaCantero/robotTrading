# Acceptance Criteria Configuration - Implementation Summary

**Date**: 2026-01-26
**Component**: Profile Batch Backtester
**File**: `app/backtesting/profile_batch_backtester.py`
**Config**: `config/profile_batch_backtest.yaml`

## Overview

Fixed hardcoded acceptance criteria and statistical significance thresholds to make them configurable via YAML. This improves maintainability and allows profile-specific overrides without code changes.

## Changes Made

### 1. Config File Updates (`config/profile_batch_backtest.yaml`)

Added new keys to the `acceptance_criteria` section:

```yaml
acceptance_criteria:
  # Existing keys (unchanged)
  min_sharpe: 1.0
  min_return: 0.10
  max_drawdown: -0.25
  min_win_rate: 0.45

  # NEW: Improvement thresholds (percentage values)
  significance_threshold: 5        # 5% improvement for statistical significance
  strong_significance_threshold: 10  # 10% improvement for strong significance
  degradation_threshold: -5        # -5% improvement indicates degradation

  # NEW: Confidence levels for recommendations (0-1 scale)
  confidence_high: 0.8             # High confidence threshold
  confidence_medium: 0.7           # Medium confidence threshold
  confidence_low: 0.5              # Low confidence threshold

  # NEW: Revision multiplier for marginal performance
  revision_multiplier: 0.8         # Multiplier for min_sharpe to determine "REVISION" status
```

### 2. Code Updates

#### 2.1 `_generate_comparison()` Method (Lines ~1573-1643)

**Before:**
```python
# Statistical significance (simplified)
n_trials = optuna_results.get("n_trials", 100)
sharpe_sig = sharpe_imp > 5  # 5% improvement threshold (HARDCODED)
return_sig = return_imp > 5

# Recommendation
if sharpe_imp > 10 and sharpe_sig:  # HARDCODED
    recommended = "optimized"
    confidence = 0.8  # HARDCODED
    reason = f"Optimized strategy shows {sharpe_imp:.1f}% Sharpe improvement..."
elif sharpe_imp < -5:  # HARDCODED
    recommended = "baseline"
    confidence = 0.7  # HARDCODED
    reason = "Optimization degraded performance, baseline is preferred"
else:
    recommended = "inconclusive"
    confidence = 0.5  # HARDCODED
    reason = "Insufficient evidence to favor either configuration"
```

**After:**
```python
# Get thresholds from config
acceptance_criteria = self.config.get("acceptance_criteria", {})
significance_threshold = acceptance_criteria.get("significance_threshold", 5)
strong_significance_threshold = acceptance_criteria.get("strong_significance_threshold", 10)
degradation_threshold = acceptance_criteria.get("degradation_threshold", -5)
confidence_high = acceptance_criteria.get("confidence_high", 0.8)
confidence_medium = acceptance_criteria.get("confidence_medium", 0.7)
confidence_low = acceptance_criteria.get("confidence_low", 0.5)

# Statistical significance (simplified)
n_trials = optuna_results.get("n_trials", 100)
sharpe_sig = sharpe_imp > significance_threshold  # CONFIG-DRIVEN
return_sig = return_imp > significance_threshold

# Recommendation using config-driven thresholds
if sharpe_imp > strong_significance_threshold and sharpe_sig:  # CONFIG-DRIVEN
    recommended = "optimized"
    confidence = confidence_high  # CONFIG-DRIVEN
    reason = f"Optimized strategy shows {sharpe_imp:.1f}% Sharpe improvement..."
elif sharpe_imp < degradation_threshold:  # CONFIG-DRIVEN
    recommended = "baseline"
    confidence = confidence_medium  # CONFIG-DRIVEN
    reason = "Optimization degraded performance, baseline is preferred"
else:
    recommended = "inconclusive"
    confidence = confidence_low  # CONFIG-DRIVEN
    reason = "Insufficient evidence to favor either configuration"
```

#### 2.2 `_evaluate_readiness()` Method (Lines ~1692-1723)

**Before:**
```python
def _evaluate_readiness(self, profile, optimized, improvements):
    """Evaluate if strategy is ready for paper trading."""
    # Get thresholds from config
    thresholds = self.config.get("acceptance_criteria", {})

    min_sharpe = thresholds.get("min_sharpe", 1.0)
    min_return = thresholds.get("min_return", 0.10)
    max_dd = thresholds.get("max_drawdown", -0.25)

    sharpe = optimized.optimized_metrics.get("sharpe_ratio", 0)
    total_return = optimized.optimized_metrics.get("return_pct", 0)
    max_dd = optimized.optimized_metrics.get("max_drawdown", 0)

    # Check thresholds
    checks = [
        sharpe >= min_sharpe,
        total_return >= min_return,
        max_dd >= max_dd,
        optimized.ready_for_paper_trading,
    ]

    if all(checks):
        return True, "APPROVED: All acceptance criteria met"
    elif sharpe >= min_sharpe * 0.8:  # HARDCODED 0.8
        return False, "REVISION: Marginal performance, review recommended"
    else:
        return False, "REJECTED: Insufficient performance"
```

**After:**
```python
def _evaluate_readiness(self, profile, optimized, improvements):
    """Evaluate if strategy is ready for paper trading."""
    # Get thresholds from config
    thresholds = self.config.get("acceptance_criteria", {})

    min_sharpe = thresholds.get("min_sharpe", 1.0)
    min_return = thresholds.get("min_return", 0.10)
    max_dd = thresholds.get("max_drawdown", -0.25)

    sharpe = optimized.optimized_metrics.get("sharpe_ratio", 0)
    total_return = optimized.optimized_metrics.get("return_pct", 0)
    max_dd = optimized.optimized_metrics.get("max_drawdown", 0)

    # Get revision multiplier from config
    revision_multiplier = thresholds.get("revision_multiplier", 0.8)  # CONFIG-DRIVEN

    # Check thresholds
    checks = [
        sharpe >= min_sharpe,
        total_return >= min_return,
        max_dd >= max_dd,
        optimized.ready_for_paper_trading,
    ]

    if all(checks):
        return True, "APPROVED: All acceptance criteria met"
    elif sharpe >= min_sharpe * revision_multiplier:  # CONFIG-DRIVEN
        return False, "REVISION: Marginal performance, review recommended"
    else:
        return False, "REJECTED: Insufficient performance"
```

## Configuration Keys Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `significance_threshold` | float | 5 | Minimum % improvement for statistical significance |
| `strong_significance_threshold` | float | 10 | Minimum % improvement for strong recommendation |
| `degradation_threshold` | float | -5 | Maximum % degradation before preferring baseline |
| `confidence_high` | float | 0.8 | Confidence level for strong recommendations (0-1) |
| `confidence_medium` | float | 0.7 | Confidence level for medium recommendations (0-1) |
| `confidence_low` | float | 0.5 | Confidence level for inconclusive cases (0-1) |
| `revision_multiplier` | float | 0.8 | Multiplier for min_sharpe to determine "REVISION" status |

## Profile-Specific Overrides

The system supports profile-specific overrides by modifying the config:

```yaml
# Example: More aggressive thresholds for high-risk profiles
acceptance_criteria:
  significance_threshold: 3  # Lower threshold for aggressive profiles
  strong_significance_threshold: 7
  revision_multiplier: 0.9  # Closer to minimum for revision status
```

## Backward Compatibility

All hardcoded values have been preserved as defaults in the `get()` calls:
- If config keys are missing, the original hardcoded values are used
- Existing configs continue to work without modification
- No breaking changes to the API or behavior

## Testing Recommendations

1. **Test with default config**: Verify behavior matches previous hardcoded values
2. **Test with custom thresholds**: Modify config values and verify they're applied
3. **Test edge cases**:
   - Missing config section (should use defaults)
   - Missing individual keys (should use defaults)
   - Extreme values (e.g., 0, negative, >100)
4. **Test profile-specific overrides**: Create test configs with different thresholds

## Files Modified

1. `/Users/kepa.cantero/Projects/algoTrading/config/profile_batch_backtest.yaml`
   - Added 6 new keys to `acceptance_criteria` section

2. `/Users/kepa.cantero/Projects/algoTrading/app/backtesting/profile_batch_backtester.py`
   - Updated `_generate_comparison()` method (lines ~1573-1643)
   - Updated `_evaluate_readiness()` method (lines ~1692-1723)

## Benefits

1. **Maintainability**: Thresholds can be adjusted without code changes
2. **Flexibility**: Different profiles can use different acceptance criteria
3. **Transparency**: All thresholds are visible in config files
4. **Backward Compatibility**: Existing configs continue to work
5. **Documentation**: Config keys are self-documenting with comments
