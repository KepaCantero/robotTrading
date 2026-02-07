# Requirements: backtesting/feature_engineering/__init__.py

## Source File Analysis
- **File Path**: `app/backtesting/feature_engineering/__init__.py`
- **Lines of Code**: 79
- **Layer**: Backtesting Layer
- **Purpose**: Barrel export for feature engineering module

## Purpose

This module provides advanced feature engineering techniques for financial time series, following Marcos López de Prado's "Advances in Financial Machine Learning".

Main Components:
- FractionalDifferentiation: Stationary features with memory preservation
- FeatureImportance: MDI, MDA, and SFI importance methods
- Visualization utilities for analysis and debugging

## Dependencies

### Internal
- `.feature_importance` - FeatureImportanceMDA, FeatureImportanceMDI, FeatureImportanceSFI
- `.feature_importance_uniqueness` - MDAWithUniqueness, MDIWithUniqueness, UniquenessCalculator
- `.fractional_differentiation` - FractionalDifferentiation, FractionalDiffTransformer

### External
- None

## Classes/Functions

### Fractional Differentiation
- `FractionalDifferentiation` - Main class for fractional differentiation
- `FractionalDiffTransformer` - Transformer class
- `get_weights` - Calculate weights for fracdiff
- `fractional_diff` - Apply fractional differencing
- `find_optimal_d` - Find optimal differencing parameter
- `apply_frac_diff_to_dataframe` - Apply to DataFrame

### Feature Importance
- `FinancialMLFeatureImportance` - Main feature importance class
- `FeatureImportanceMDI` - Mean Decrease Impurity
- `FeatureImportanceMDA` - Mean Decrease Accuracy
- `FeatureImportanceSFI` - Single Feature Importance
- `calculate_feature_importance` - Main calculation function

### Feature Importance with Uniqueness
- `FinancialMLFeatureImportanceWithUniqueness` - Extended with uniqueness
- `MDIWithUniqueness` - MDI with uniqueness
- `MDAWithUniqueness` - MDA with uniqueness
- `UniquenessCalculator` - Calculate uniqueness
- `FeatureClusterer` - Cluster features

## Business Logic

This is an export module - no business logic contained here.

## Data Models

- `FeatureImportanceConfig` - Configuration class
- `ImportanceResult` - Result data structure
- `UniquenessConfig` - Uniqueness configuration
- `UniquenessResult` - Uniqueness result structure

## API Contracts

Example:
```python
from app.backtesting.feature_engineering import FractionalDifferentiation

fd = FractionalDifferentiation()
optimal_d, p_value, _ = fd.find_optimal_d(price_series)
frac_diff_series = fd.fractional_diff(price_series, d=optimal_d)
```

## Error Handling

This is an export module - no error handling contained here.

## Performance Considerations

None - export module only.

## Testing Strategy

- Verify all imports resolve correctly
- Verify __all__ exports are complete

## Critical Rules (from BASE_RULES.md)

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| FMT-003 | No unused imports | ✅ PASS | All imports used in __all__ |
| ARCH-004 | Small functions | ✅ PASS | Export module only |

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:38:00Z |
| **Audit Status** | PASSED |

## Notes

1. Clean barrel export pattern
2. Complete __all__ definition with 19 exports
3. References López de Prado's work in docstring
4. Includes example usage in docstring

## Acceptance Criteria

- [x] All imports resolve correctly
- [x] __all__ is complete
- [x] Module is well-documented
- [x] No unused imports

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Last updated: 2026-02-07T05:38:00Z*
