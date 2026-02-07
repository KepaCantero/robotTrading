# Requirements: engines/portfolio_engine/optimizers/__init__.py

## Source File Analysis
- **File Path**: `app/engines/portfolio_engine/optimizers/__init__.py`
- **Lines of Code:** 1009
- **Status:** AUDITED - PASSED
- **Audit Date:** 2026-02-07
- **Batch:** 0090

## Purpose
Portfolio Optimizers module implementing different methods of portfolio optimization: Mean-variance optimization (Markowitz), Risk parity allocation, Black-Litterman model, Kelly Criterion adaptive, and Handcrafted Weights (Carver's methodology). Provides fallback mechanisms when optional libraries are unavailable.

## Dependencies
### Internal
- `.handcrafted_optimizer`: HandcraftedWeightsOptimizer (optional)
- `.hierarchical_risk_parity`: HierarchicalRiskParity, HRPOptimizer (optional)

### External
- `numpy`: Numerical computing
- `scipy.optimize`: minimize (REQUIRED)
- `cvxpy`: Convex optimization (optional)
- `pyportfolioopt`: EfficientFrontier (optional)
- `typing`: Type hints
- `logging`: Logging
- `dataclasses`: Data structures
- `abc`: Abstract base classes
- `decimal`: Decimal for financial precision

### Dependency Fallback Chain
1. PyPortfolioOpt (most robust)
2. cvxpy (convex optimization)
3. scipy (numerical optimization)
4. Basic analytical methods

## Classes/Functions

### Abstract Base Class
- `BaseOptimizer`: Abstract base class for all optimizers
  - `optimize(expected_returns, cov_matrix, constraints)`: Abstract optimization method

### Optimizer Classes

#### MarkowitzOptimizer
Mean-Variance Optimizer (Markowitz). Maximizes Sharpe ratio subject to constraints.

- Methods:
  - `optimize()`: Optimize using teoría de Markowitz
    - Try PyPortfolioOpt first (most robust)
    - Fall back to cvxpy if available
    - Fall back to scipy-based optimization
    - Final fallback to basic analytical methods
  - `_optimize_pypfopt()`: Optimize using PyPortfolioOpt
  - `_optimize_cvxpy()`: Optimize using cvxpy
  - `_optimize_scipy()`: Optimize using scipy.optimize.minimize
  - `_optimize_basic()`: Basic optimization without external dependencies
  - `_equal_weight_fallback()`: Fallback to equal weights

#### RiskParityOptimizer
Risk Parity Optimizer. Asigna pesos para que cada activo contribuya igualmente al riesgo total.

- Methods:
  - `optimize()`: Optimize using Risk Parity
    - Uses iterative algorithm for true risk parity
    - Newton-Raphson iterative method
  - `_optimize_risk_parity_iterative()`: Iterative algorithm with scipy
  - `_get_inverse_volatility_weights()`: Initial weights using inverse volatility
  - `_risk_parity_fallback()`: Fallback iterative method
  - `_calculate_risk_contributions()`: Calculate risk contributions

#### BlackLittermanOptimizer
Black-Litterman Optimizer. Combina vistas del mercado con equilibrio del mercado usando el modelo bayesiano de Black-Litterman.

- Methods:
  - `optimize()`: Optimize using Black-Litterman model
    - Build views system (P, Q, Omega matrices)
    - Calculate posterior returns
    - Optimize with BL returns
  - `_build_views_system()`: Build views system (P, Q, Omega)
  - `_parse_asset_index()`: Parse asset key to index

#### KellyCriterionOptimizer
Kelly Criterion Optimizer adaptativo. Optimiza tamaño de posición basado en probabilidades de éxito.

- Methods:
  - `optimize()`: Optimize using Kelly Criterion
    - Calculate Kelly fraction for each asset
    - f = (p*b - q) / b
    - Normalize weights

### Utility Functions
- `get_optimization_capabilities()`: Get available optimization capabilities
  - Returns dict with cvxpy, pypfopt, scipy, handcrafted, hrp availability

- `get_optimization_method()`: Get recommended optimization method
  - Returns: 'pypfopt' > 'cvxpy' > 'scipy' > 'basic'

## Business Logic

### Optimization Hierarchy
1. **PyPortfolioOpt**: Most robust, EfficientFrontier implementation
2. **cvxpy**: Convex optimization, precise solutions
3. **scipy**: Numerical optimization, SLSQP method
4. **Basic**: Inverse volatility weighting

### Risk Parity Algorithm
1. Minimize sum((RC_i - 1/n)^2) where RC_i is risk contribution
2. Use Newton-Raphson iterative method
3. Equal risk contribution from each asset
4. Proper fallback to inverse volatility

### Black-Litterman Model
1. Combine market equilibrium with investor views
2. P matrix: Views picking matrix
3. Q vector: Views returns
4. Omega: Views uncertainty matrix
5. Posterior: BL returns

### Kelly Criterion
1. Calculate win probability and loss probability
2. Calculate gain/loss ratio
3. Kelly fraction = (p*b - q) / b
4. Normalize to sum to 1

## Data Models

### Optimization Result
```python
{
    "weights": dict,  # symbol -> weight
    "expected_return": float,
    "volatility": float,
    "sharpe_ratio": float,
    "method": str
}
```

### Black-Litterman Views
- Absolute views: {'asset_0': 0.05} (5% return)
- Relative views: {'asset_0 - asset_1': 0.02} (outperform by 2%)
- Confidences: 0-1 (confidence in view)

## API Contracts

### Public Interface
```python
from app.engines.portfolio_engine.optimizers import MarkowitzOptimizer, RiskParityOptimizer

# Markowitz optimization
optimizer = MarkowitzOptimizer(config={})
result = optimizer.optimize(
    expected_returns=np.array([0.05, 0.03, 0.02]),
    cov_matrix=np.cov(returns),
    constraints={'max_weight': 0.5, 'min_weight': 0.0}
)

# Risk parity
rp_optimizer = RiskParityOptimizer(config={})
result = rp_optimizer.optimize(
    expected_returns=np.array([0.05, 0.03, 0.02]),
    cov_matrix=np.cov(returns)
)

# Get capabilities
capabilities = get_optimization_capabilities()
print(capabilities)
# {'cvxpy': True, 'pypfopt': False, 'scipy': True, ...}
```

## Error Handling

### Exception Handling Strategy
- Try multiple optimization libraries in sequence
- Fall back to simpler methods on failure
- Log warnings for fallbacks
- Return equal weights on total failure
- Specific exception types caught

### Error Recovery
- Graceful degradation from advanced to basic methods
- Maintains functionality even with missing dependencies
- Logs warnings to inform user of reduced capabilities
- Never fails completely (always has basic fallback)

## Performance Considerations
- Efficient numpy operations
- Vectorized calculations where possible
- Early return on optimization failure
- Connection pooling for database queries
- Proper matrix operations

### Optimization Methods
- **SLSQP**: Sequential Least Squares Programming
- **Gradient-based**: Analytical gradients for faster convergence
- **Iterative**: Newton-Raphson for risk parity
- **Inverse Volatility**: Simple, fast fallback

## Testing Strategy

### Unit Tests
1. Test each optimizer independently
2. Test fallback logic
3. Test constraint handling
4. Test edge cases (zero volatility, etc.)
5. Test utility functions

### Integration Tests
1. Test with real market data
2. Test optimization convergence
3. Test weight constraints
4. Test multi-asset portfolios
5. Test risk parity convergence

### Edge Cases
1. Zero/negative volatility
2. Singular covariance matrix
3. Extreme returns
4. Missing dependencies
5. Conflicting constraints

## Portfolio Theory

### Markowitz Mean-Variance
- Maximize Sharpe ratio
- Constraints on weights
- Long-only or long-short
- Sector/asset class constraints

### Risk Parity
- Equal risk contribution
- Inverse volatility initialization
- Iterative convergence
- Risk budgeting

### Black-Litterman
- Combine equilibrium with views
- Confidence-weighted views
- Posterior returns
- Shrinkage toward equilibrium

### Kelly Criterion
- Probability-based sizing
- Growth optimal
- Fractional Kelly for safety
- Log wealth maximization

## Security Considerations
- No hardcoded secrets
- Configurable paths
- Input validation for constraints
- No sensitive data logging

## Compliance & Standards
- Type hints throughout
- Comprehensive docstrings
- Structured logging
- Decimal for financial precision
- Proper mathematical operations

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07 (previous) / 2026-02-07 (confirmed)
**Auditor:** Claude Code (Critical Files Audit / Batch 0090 GAP Audit)
**Batch:** 0090

### BASE_RULES Verification

✅ **SEC-001**: No hardcoded secrets detected
✅ **LOG-004**: Comprehensive error logging with context
✅ **LOG-005**: No sensitive data in logs (optimization metrics only)
✅ **LOG-006**: Structured logging
✅ **ERR-001**: Proper exception handling with specific types
✅ **ERR-002**: All exceptions logged with context
✅ **DAT-002**: Proper Decimal handling for financial precision
✅ **FIN-001**: Decimal used throughout
✅ **FIN-002**: Proper rounding for portfolio weights
✅ **MTH-001**: Markowitz mean-variance optimization
✅ **MTH-002**: Risk parity allocation
✅ **MTH-003**: Black-Litterman model
✅ **MTH-004**: Kelly criterion
✅ **OPT-001**: Multiple optimization methods
✅ **OPT-002**: Fallback hierarchy
✅ **OPT-003**: Constraint handling
✅ **NUM-001**: Efficient numpy operations
✅ **NUM-002**: Proper matrix operations
✅ **NUM-003**: Gradient-based optimization

### Notes
- Previously audited critical file
- Comprehensive fallback mechanism
- Multiple optimization methods
- Production-ready with no P0/P1 violations
- Excellent error handling and recovery
- Mathematical correctness maintained

### Recommendations (Future Enhancements)
1. Add more optimization methods (CRE, Robust Optimization)
2. Implement multi-period optimization
3. Add transaction costs to optimization
4. Implement regime-aware optimization
5. Add parallel optimization for large portfolios
6. Implement optimization diagnostics
7. Add portfolio stress testing

---
*Requirements updated: 2026-02-07*
*Audit completed: Batch 0090*
