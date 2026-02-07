# Requirements: services/optimization_chan.py

## Source File Analysis
- **File Path**: `app/services/optimization_chan.py`
- **Lines of Code**: 915
- **Status**: Analysis Complete - PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements portfolio optimization methods as described in Ernest Chan's "Quantitative Trading":
- Mean-Variance Optimization (Markowitz)
- Risk Parity Implementation (Equal Risk Contribution)
- Hierarchical Risk Parity (HRP)
- Maximum Diversification Portfolio
- Minimum Variance Portfolio
- CVaR (Conditional Value at Risk) Optimization

## Dependencies

### Internal
- None (standalone optimization library)

### External
- `logging` - Standard Python logging
- `dataclasses` - For OptimizationResult dataclass
- `typing` - Type hints (Dict, List, Optional, Tuple)
- `numpy` - Array operations and numerical calculations
- `pandas` - DataFrame input handling
- `scipy.optimize.minimize` - Optimization solvers (SLSQP)
- `scipy.cluster.hierarchy.linkage` - Hierarchical clustering for HRP
- `scipy.cluster.hierarchy.dendrogram` - Dendrogram for HRP
- `scipy.spatial.distance.squareform` - Distance matrix conversion
- `cvxpy` - OPTIONAL: Convex optimization (required for some methods)

## Classes/Functions

### Data Class
1. **OptimizationResult** - Complete optimization results with weights, metrics, metadata

### Optimizer Classes

#### MeanVarianceOptimizer
1. **optimize()** - Mean-variance optimization with various objectives
   - max_sharpe: Maximize Sharpe ratio
   - min_variance: Minimize portfolio variance
   - max_diversification: Maximize diversification ratio
   - max_return: Maximize return with risk constraint

#### RiskParityOptimizer
1. **optimize()** - Equal risk contribution optimization
   - Uses analytical gradient for faster convergence
   - Targets equal risk contribution from all assets

#### HierarchicalRiskParityOptimizer
1. **optimize()** - HRP optimization using hierarchical clustering
   - Ward linkage method
   - Recursive bisection for weight allocation
   - More robust than traditional optimization

#### MaximumDiversificationOptimizer
1. **optimize()** - Maximize diversification ratio
   - DR = (weighted avg vol) / portfolio vol

#### CVaROptimizer
1. **optimize()** - Conditional Value at Risk optimization
   - Minimizes expected loss beyond VaR
   - Configurable confidence level (default 95%)

### High-Level Function
1. **optimize_portfolio()** - Unified interface for all optimization methods

### Internal Helpers
1. **_check_cvxpy_available()** - Raises ImportError if cvxpy not available

## Business Logic

### Mean-Variance Optimization (Markowitz)
- Objective: Maximize Sharpe ratio or minimize variance
- Constraints: Fully invested, weight bounds, sector constraints
- Solver: CVXPY (ECOS or SCS fallback)
- Features: Cardinality constraint approximation via L1 norm

### Risk Parity (Equal Risk Contribution)
- Objective: Equal risk contribution from all assets
- Method: Minimize sum of squared deviations from target risk
- Gradient: Analytical gradient for SLSQP solver
- Target: Each asset contributes 1/n of total risk

### Hierarchical Risk Parity (HRP)
- Based on: Lopez de Prado (2016)
- Method: Hierarchical clustering + recursive bisection
- Distance: sqrt(0.5 * (1 - correlation))
- Linkage: Ward method (default)
- Robust to covariance matrix invertibility issues

### Maximum Diversification
- Objective: Maximize diversification ratio
- DR = (sum(w_i * sigma_i)) / sqrt(w' * Sigma * w)
- Penalizes correlated assets

### CVaR Optimization
- Based on: Rockafellar & Uryasev (2000)
- Objective: Minimize expected shortfall beyond VaR
- Method: Linear programming with auxiliary variables
- Confidence: Default 95% (configurable)

## Data Models

### OptimizationResult
```python
weights: np.ndarray
expected_return: float
volatility: float
sharpe_ratio: float
method: str
risk_contributions: Optional[np.ndarray]
diversification_ratio: Optional[float]
turnover: Optional[float]
metadata: Optional[Dict]
```

## API Contracts

### MeanVarianceOptimizer.optimize()
```python
def optimize(
    returns: pd.DataFrame,
    objective: str = "max_sharpe",
    risk_free_rate: float = 0.0,
    weight_constraints: Optional[Dict[str, float]] = None,
    sector_constraints: Optional[Dict[str, Tuple[List[int], float]]] = None,
) -> OptimizationResult
```

### RiskParityOptimizer.optimize()
```python
def optimize(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.0,
    weight_constraints: Optional[Dict[str, float]] = None,
    tolerance: float = 1e-8,
    max_iterations: int = 1000,
) -> OptimizationResult
```

### optimize_portfolio() (High-level)
```python
def optimize_portfolio(
    returns: pd.DataFrame,
    method: str = "mean_variance",
    **kwargs,
) -> OptimizationResult
```

## Error Handling

### Exception Handling
- **ImportError**: Raised if cvxpy required but not available
- **ValueError, TypeError**: Caught, logged, equal-weight fallback returned
- **cp.SolverError**: Caught, logged, equal-weight fallback returned

### Fallback Strategy
- Returns equal-weight portfolio on optimization failure
- Logs error with details
- Ensures method always returns valid result

### Input Validation
- Checks cvxpy availability before use
- Validates objective parameter
- Handles invalid correlation matrices

## Performance Considerations

### Optimization Solvers
- CVXPY: ECOS (fast) with SCS fallback
- SciPy: SLSQP for risk parity
- Hierarchical methods: O(n^3) for clustering

### Scalability
- Mean-variance: Convex optimization (fast for <1000 assets)
- Risk parity: Iterative (moderate speed)
- HRP: Clustering (scales well)
- CVaR: Linear programming (scales well)

### Memory Management
- Efficient numpy operations
- No memory leaks in iterative methods

## Testing Strategy

### Unit Tests Needed
1. **Mean-variance**: Test all objectives (max_sharpe, min_variance, max_diversification)
2. **Risk parity**: Test equal risk convergence
3. **HRP**: Test clustering and weight allocation
4. **CVaR**: Test expected shortfall calculation
5. **Fallback**: Test equal-weight fallback on failure

### Integration Tests Needed
1. **Real market data**: Test with actual return series
2. **Comparison**: Compare results across methods
3. **Constraints**: Test weight and sector constraints
4. **Robustness**: Test with singular covariance matrices

## BASE_RULES Compliance

### Formatting & Style
- ✅ FMT-001: Line length follows Python standards
- ✅ FMT-007: No mutable defaults
- ✅ FMT-006: Uses f-strings

### Type Hints
- ✅ TYP-001: All functions have type hints
- ✅ TYP-002: Modern syntax (Optional, Dict, Tuple)
- ✅ TYP-005: All class attributes typed

### SOLID Principles
- ✅ SOL-001: Single Responsibility - Each optimizer has one method
- ✅ SOL-002: Open/Closed - Extensible via new optimizer classes
- ✅ SOL-005: Dependency injection (config parameters)

### Architecture
- ✅ ARCH-006: Dataclass for value object
- ✅ ARCH-005: Early returns for error conditions
- ✅ Clean separation: Each optimizer is independent

### Documentation
- ✅ Comprehensive docstrings with formulas
- ✅ References to academic papers (Chan, Lopez de Prado, Rockafellar)
- ✅ Usage examples provided

### Error Handling
- ✅ Graceful fallback on failure
- ✅ Comprehensive exception handling
- ✅ Informative error messages

## Audit Status: PASSED

### Summary
This is an excellent implementation of modern portfolio optimization methods. The code follows quantitative finance best practices with references to key papers (Ernest Chan, Lopez de Prado, Rockafellar & Uryasev). The fallback strategy ensures robustness.

### Strengths
1. **Multiple Methods**: Mean-variance, risk parity, HRP, max diversification, CVaR
2. **Academic Rigor**: References to key papers in portfolio optimization
3. **Robustness**: Equal-weight fallback on optimization failure
4. **Flexibility**: Weight constraints, sector constraints, cardinality
5. **Clean API**: Unified optimize_portfolio() interface
6. **Analytical Gradient**: Risk parity uses analytical gradient for speed

### Compliance Notes
- cvxpy is OPTIONAL but required for some methods (checked at runtime)
- Equal-weight fallback ensures method always returns valid result
- Annualizes returns and volatility (252 trading days)
- Risk parity uses SLSQP solver with analytical gradient

### Algorithm Notes
- **Mean-Variance**: Convex optimization via CVXPY
- **Risk Parity**: Iterative optimization with analytical gradient
- **HRP**: Hierarchical clustering (Ward) + recursive bisection
- **CVaR**: Linear programming with auxiliary variables (z, gamma)

### No Critical Issues Found
- No security vulnerabilities
- No anti-patterns
- No overengineering violations
- Code is production-ready

### Notes
- Default constraints: min_weight=0.0, max_weight=1.0
- Risk-free rate default: 0.0 (configurable)
- Solvers: ECOS (fast), SCS (fallback)
- HRP uses Ward linkage (configurable)
- CVaR confidence default: 95% (configurable)

---
*Audited on 2026-02-07*
