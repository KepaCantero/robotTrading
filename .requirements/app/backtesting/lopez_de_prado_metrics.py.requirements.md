# Requirements: backtesting/lopez_de_prado_metrics.py

## Source File Analysis
- **File Path**: `app/backtesting/lopez_de_prado_metrics.py`
- **Lines of Code**: 1029
- **Module**: Backtesting - Advanced Metrics

## Purpose
Implements advanced metrics and methodologies from Marcos López de Prado's book
"Machine Learning for Asset Managers" (2020).

Key Features:
1. Sharpe Ratio Combination Methods (optimal, hierarchical, spectral)
2. Portfolio Stability Validation
3. Turnover-Adjusted Performance Metrics
4. Portfolio Concentration Metrics (HHI, Gini, Shannon Entropy)
5. Hierarchical Risk Parity (HRP) support
6. Spectral Risk Measures

## Dependencies

### External Dependencies
- `numpy` - Numerical computations
- `scipy` - Statistical functions, clustering, hierarchy
- `logging` - Structured logging
- `dataclasses` - Data models (SharpeCombinationResult, PortfolioStabilityMetrics, etc.)
- `datetime` - Timestamps

### Internal Dependencies
- None (self-contained module)

## Classes/Functions

### Data Models (dataclasses)
- `SharpeCombinationResult` - Result from Sharpe ratio combination analysis
- `PortfolioStabilityMetrics` - Portfolio stability validation metrics
- `TurnoverAdjustedMetrics` - Turnover-adjusted performance metrics
- `ConcentrationMetrics` - Portfolio concentration metrics

### Main Classes
- `SharpeRatioCombinator` - Implements Sharpe ratio combination methods
  - `combine_sharpes_optimal()` - Optimal combination using covariance matrix
  - `combine_sharpes_hierarchical()` - Hierarchical combination using HRP
  - `combine_sharpes_spectral()` - Spectral risk measure combination
  - `test_sharpe_significance()` - Jobson-Korkie test with Memmel correction

- `PortfolioStabilityValidator` - Portfolio stability validation
  - `validate_stability()` - Comprehensive stability analysis

- `TurnoverAdjustedCalculator` - Turnover-adjusted performance metrics
  - `calculate_turnover_adjusted_sharpe()` - Adjust Sharpe for transaction costs

- `ConcentrationAnalyzer` - Portfolio concentration metrics
  - `analyze_concentration()` - HHI, Gini, Shannon entropy, effective N

### Factory Functions
- `create_lopez_de_prado_suite()` - Create complete metrics suite

## Business Logic

### Sharpe Ratio Combination (Chapter 8)
- **Optimal Combination**: w ∝ Σ^(-1) * SR (inverse correlation matrix)
- **Hierarchical Combination**: Uses HRP clustering and recursive bisection
- **Spectral Combination**: Eigenvalue decomposition of covariance matrix
- **Significance Testing**: Jobson-Korkie test with Memmel correction

### Portfolio Stability (Chapter 9)
Stable portfolios should have:
1. Low turnover across periods
2. High autocorrelation in weights
3. Minimal allocation drift
4. High cross-period correlation

### Turnover Analysis (Chapter 10)
- Adjusts Sharpe ratio for transaction costs
- Annualizes turnover based on rebalancing frequency
- Cost-effectiveness threshold: <20% Sharpe degradation

### Concentration Analysis (Chapter 11)
- **Herfindahl-Hirschman Index (HHI)**: Sum of squared weights (0-1)
- **Effective N Assets**: 1/HHI
- **Gini Coefficient**: Wealth inequality measure (0-1)
- **Shannon Entropy**: Diversification measure (higher = more diversified)

## Data Models

### SharpeCombinationResult
```python
@dataclass
class SharpeCombinationResult:
    combined_sharpe: float
    method: str
    individual_sharpes: List[float]
    weights: Optional[np.ndarray]
    improvement_pct: float
    is_statistically_significant: bool
    p_value: float
    confidence_interval: Optional[Tuple[float, float]]
    timestamp: datetime
```

### PortfolioStabilityMetrics
```python
@dataclass
class PortfolioStabilityMetrics:
    is_stable: bool
    stability_score: float  # 0-100
    turnover_mean: float
    turnover_std: float
    weights_autocorrelation: float
    allocation_drift_max: float
    cross_period_correlation: float
    num_periods: int
```

## API Contracts

### Input Validation
- Sharpe arrays must be non-empty
- Covariance matrices must be positive semidefinite
- Weight vectors must sum to 1.0

### Error Handling
- Returns sensible defaults on invalid input
- Logs all errors with context
- Uses pseudoinverse for singular matrices

## Error Handling
- All public methods return valid result objects on error
- Invalid inputs return neutral/default values (e.g., SharpeCombinationResult with combined_sharpe=0.0)
- Matrix operations use pseudoinverse fallback for singular matrices
- All exceptions logged with context

## Performance Considerations
- Uses NumPy vectorization for all computations
- Hierarchical clustering can be O(n³) for large n
- Consider using `scipy.cluster.hierarchy.linkage` with method='ward' for large datasets

## Testing Strategy
- Unit tests for each calculator class
- Validate against known examples from López de Prado book
- Test edge cases: empty arrays, singular matrices, zero weights
- Verify mathematical properties: HHI ∈ [0,1], Gini ∈ [0,1]

## Critical Rules (BASE_RULES.md)

### Compliance Status: ✅ PASSED

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports | ✅ PASS | All imports are absolute |
| R104 | No bare except | ✅ PASS | Uses `except Exception as e:` for logging |
| R105 | No print statements | ✅ PASS | Uses `logger` throughout |
| R108 | Exception handling | ✅ PASS | Comprehensive error handling |
| R110 | Docstrings | ✅ PASS | Google-style docstrings for all classes/functions |
| R111 | No circular imports | ✅ PASS | No internal dependencies |

### Notes
- Type hints use `Any` appropriately for flexible Dict return values
- All `Any` types documented in docstrings
- Uses legacy type hint syntax (Optional[T] instead of T \| None) - acceptable for compatibility
- No `from __future__ import annotations` but code is well-typed

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:55:00Z |
| **Audit Status** | PASSED |
| **Auditor** | Ralph GAP Audit Automation |
| **Violations** | 0 critical violations |

---
*Generated on 2026-02-07T05:55:00Z*
