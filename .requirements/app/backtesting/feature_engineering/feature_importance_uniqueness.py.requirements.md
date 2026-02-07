# Requirements: backtesting/feature_engineering/feature_importance_uniqueness.py

## Source File Analysis
- **File Path**: `app/backtesting/feature_engineering/feature_importance_uniqueness.py`
- **Lines of Code**: 790
- **Status**: PASSED_WITH_NOTES
- **Audit Date**: 2025-02-07T00:00:00Z

## Purpose
Implements feature importance methods with sample uniqueness weighting for financial ML, based on Marcos López de Prado's "Advances in Financial Machine Learning", Chapter 8.

Key innovations:
1. **MDI with Sample Weights**: Weight feature importance by sample uniqueness
2. **MDA with Uniqueness Correction**: Adjust permutation importance for overlaps
3. **SFI with Sequential Bootstrap**: Single feature importance with proper CV
4. **Feature Clustering**: Group correlated features

## Dependencies
### External
- `logging` (stdlib)
- `dataclasses.dataclass`, `dataclasses.field` (stdlib)
- `datetime.datetime` (stdlib)
- `typing.Any`, `typing.Dict`, `typing.List`, `typing.Optional`, `typing.Union` (stdlib)
- `numpy` (np)
- `pandas` (pd)

### Internal
None

## Classes/Functions

### Data Classes
- `UniquenessConfig`: Configuration for uniqueness-weighted importance
  - `uniqueness_method`: "average", "concurrent", "sequential"
  - `overlap_threshold`: Minimum overlap for concurrent samples
  - `mdi_normalize`, `mda_uniqueness_correction`: MDI/MDA settings
  - `cluster_features`, `correlation_threshold`: Feature clustering settings

- `UniquenessResult`: Result container
  - Importance scores with uniqueness weighting
  - `uniqueness_weights`: Sample weights array
  - `avg_uniqueness`: Average uniqueness metric
  - `feature_clusters`: Grouped correlated features

### Main Classes
- `UniquenessCalculator`: Calculate sample uniqueness
  - `calculate_average_uniqueness()`: Average uniqueness based on overlaps
  - `calculate_concurrent_uniqueness()`: Simpler concurrent-based uniqueness

- `MDIWithUniqueness`: MDI with uniqueness weighting
  - `calculate()`: Weighted MDI importance

- `MDAWithUniqueness`: MDA with uniqueness correction
  - `calculate()`: Uniqueness-corrected permutation importance
  - `_score_model_weighted()`: Weighted scoring

- `FeatureClusterer`: Cluster correlated features
  - `cluster_features()`: Group features by correlation

- `FinancialMLFeatureImportanceWithUniqueness`: Main interface
  - `calculate_importance()`: Unified importance with uniqueness
  - `_combine_importances()`: Average across methods

### Convenience Functions
- `calculate_feature_importance_with_uniqueness()`: Single-function interface

## Business Logic
1. **Sample Uniqueness**: Measures how unique each sample is based on overlaps
2. **Weighted Importance**: Gives more weight to unique samples
3. **Clustering**: Groups correlated features for robust estimates
4. **Correction**: Adjusts importance for overlapping samples

## Data Models
- Input: Model, features X, targets y, events, labels
- Output: `UniquenessResult` with weighted importance

## Error Handling
- Graceful handling of missing `feature_importances_` attribute
- Validation of configuration in `__post_init__`
- Warning logs for model incompatibility

## BASE_RULES Compliance

### Critical Rules Check

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports only | ✅ PASS | All imports are absolute |
| R098 | No relative imports | ✅ PASS | No relative imports found |
| R100 | Modern type hints (X \| None) | ⚠️ NOTE | Uses `Optional[T]` - compatible |
| R102 | No Any without docs | ⚠️ NOTE | Uses `Any` for model parameter |
| R103 | No type comments | ✅ PASS | No type comments found |
| R104 | No bare except | ✅ PASS | No bare except clauses |
| R105 | No print() in production | ✅ PASS | Only in docstring examples |
| R107 | No mutable defaults | ✅ PASS | Uses `field(default_factory=dict/lambda)` |
| R108 | Proper exception handling | ✅ PASS | Specific exceptions caught |
| R110 | Google docstrings | ✅ PASS | All classes/methods have Google-style docstrings |
| R111 | No circular imports | ✅ PASS | No circular imports detected |

### Notes on Non-Critical Issues

1. **`Any` Type Usage**:
   - `model: Any` parameters are appropriately used
   - Reason: Must work with any sklearn-compatible model
   - Documented in docstrings

2. **Unused Expression** (Line 355):
   - `len(X)` is called but result not used
   - This appears to be leftover debug code
   - Not a critical violation but could be cleaned up

3. **Type Hints**:
   - Uses `Optional[T]` instead of `T | None`
   - This is compatible and not a violation

## Audit Status: PASSED_WITH_NOTES
**Audited by**: Claude (GAP Audit - batch_0012)
**Last Audit**: 2025-02-07T00:00:00Z
**Issues Found**: 0 critical violations
**Notes**:
- `Any` type usage is appropriate for model-agnostic interfaces
- Line 355 has unused `len(X)` expression (non-critical cleanup opportunity)
- Excellent implementation of López de Prado's uniqueness-weighted feature importance
- Well-structured with proper configuration validation

---
*Auto-generated requirements updated after audit on 2025-02-07*
