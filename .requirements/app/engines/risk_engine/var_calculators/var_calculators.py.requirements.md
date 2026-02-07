# Requirements: engines/risk_engine/var_calculators/var_calculators.py

## Source File Analysis
- **File Path**: `app/engines/risk_engine/var_calculators/var_calculators.py`
- **Lines of Code**: 1260
- **Language**: Python 3.10+
- **Purpose**: Value-at-Risk (VaR) calculations with Numba JIT acceleration (Hull Chapter 18)

## Dependencies
### Internal
- None (standalone risk calculation module)

### External
- `logging` - Structured logging
- `typing` - Type hints (Dict, Optional, Any)
- `abc` - Abstract base classes
- `numpy` - Numerical computations, array operations
- `pandas` - DataFrame/Series support
- `numba` - JIT compilation (@jit, @njit, @prange)
- `arch` - GARCH models (optional, with fallback)

## Classes/Functions

### Numba-Accelerated Core Functions

#### calculate_percentile_numba()
**Purpose:** Calculate percentile with 10-25x speedup
**Performance:** ~2-5ms for 10K data points (vs ~50ms pure Python)
**Signature:** `(arr: np.ndarray, percentile: float) -> float`

#### calculate_mean_std_numba()
**Purpose:** Calculate mean and std with 10-20x speedup
**Performance:** ~1-2ms for 10K data points (vs ~20ms pure Python)
**Signature:** `(arr: np.ndarray) -> tuple(mean, std)`

#### calculate_cvar_numba()
**Purpose:** Calculate Conditional VaR (Expected Shortfall) with 10-30x speedup
**Performance:** ~1-3ms for 10K data points (vs ~30ms pure Python)
**Signature:** `(arr: np.ndarray, var_value: float) -> float`

#### monte_carlo_simulation_numba()
**Purpose:** Parallel Monte Carlo simulation with 2-5x speedup on multi-core
**Performance:** ~100-200ms for 10K simulations (vs ~500ms single-threaded)
**Signature:** `(mean_return: float, std_return: float, n_simulations: int) -> np.ndarray`
**Uses:** @njit(parallel=True) with prange for parallel execution

#### calculate_jarque_bera_numba()
**Purpose:** Normality test (Jarque-Bera) with 10-20x speedup
**Performance:** ~5-10ms for 10K data points (vs ~100ms scipy)
**Signature:** `(arr: np.ndarray) -> tuple(jb_statistic, p_value)`

### VaR Calculator Classes

#### BaseVaRCalculator (ABC)
**Purpose:** Abstract base class for all VaR calculators
**Attributes:**
- `confidence_level`: float (default: 0.95)
- `time_horizon`: int (default: 1 day)
**Abstract Method:** `calculate_var(returns, portfolio_value)`

#### HistoricalVaRCalculator
**Purpose:** Empirical distribution VaR with 50-100x Numba speedup
**Method:** `calculate_var(returns, portfolio_value)`
**Returns:**
```python
{
    'var': float,  # VaR at confidence level
    'var_amount': float,  # Absolute VaR if portfolio_value provided
    'cvar': float,  # Conditional VaR (Expected Shortfall)
    'cvar_amount': float,
    'confidence_level': float,
    'observations': int,
    'numba_accelerated': bool
}
```

#### ParametricVaRCalculator
**Purpose:** Normal distribution VaR with 30-50x Numba speedup
**Method:** `calculate_var(returns, portfolio_value)`
**Features:**
- Jarque-Bera normality test before calculation
- Warning if returns non-normal (underestimates risk 15-30%)
- Z-score calculation (scipy.stats or fallback)
**Returns:**
```python
{
    'var': float,
    'mean_return': float,
    'std_return': float,
    'z_score': float,
    'is_normal_distribution': bool,
    'normality_warning': str,  # If non-normal
    'numba_accelerated': bool
}
```

#### MonteCarloVaRCalculator
**Purpose:** Simulation-based VaR with 40-80x speedup (Numba + parallel)
**Attributes:**
- `n_simulations`: int (default: 10000)
**Method:** `calculate_var(returns, portfolio_value)`
**Features:**
- Parallel Monte Carlo with Box-Muller transform
- Fallback to numpy.random if Numba unavailable
**Returns:**
```python
{
    'var': float,
    'n_simulations': int,
    'mean_return': float,
    'std_return': float,
    'parallel_processing': bool,
    'numba_accelerated': bool
}
```

#### GARCHVaRCalculator
**Purpose:** Conditional volatility VaR with 20-40x speedup
**Method:** `calculate_var(returns, portfolio_value)`
**Features:**
- GARCH(1,1) model via arch package
- Fallback to ParametricVaRCalculator if arch unavailable
- Minimum 100 observations required
**Returns:**
```python
{
    'var': float,
    'conditional_volatility': float,
    'method': 'garch',
    'numba_accelerated': bool
}
```

### VaR Backtesting Classes

#### VaRBacktester
**Purpose:** Validate VaR models using statistical tests (Hull Chapter 18)

**kupiec_test() - Likelihood Ratio Test**
- H0: Model correct (exceptions at expected rate)
- H1: Model incorrect
- Test statistic: LR = 2 * [log(L1) - log(L0)]
- Critical value: Chi-squared(1) at significance level

**Returns:**
```python
{
    'test_name': 'Kupiec Likelihood Ratio Test',
    'observations': int,
    'exceptions': int,
    'expected_exceptions': float,
    'actual_failure_rate': float,
    'lr_statistic': float,
    'critical_value': float,
    'reject_null': bool,
    'model_valid': bool,
    'interpretation': str
}
```

**christoffersen_test() - Independence Test**
- H0: Exceptions are independent (no clustering)
- H1: Exceptions exhibit autocorrelation
- Uses first-order Markov chain for transitions
- Transition matrix: n_00, n_01, n_10, n_11

**Returns:**
```python
{
    'test_name': 'Christoffersen Independence Test',
    'transitions': {n_00, n_01, n_10, n_11, n_0, n_1},
    'transition_probabilities': {pi_01, pi_11},
    'lr_statistic': float,
    'exceptions_independent': bool,
    'interpretation': str
}
```

**run_comprehensive_backtest()**
- Runs both Kupiec and Christoffersen tests
- Calculates exception statistics
- Provides overall assessment (PASS/CONDITIONAL/FAIL)

## Business Logic

### VaR Calculation Formulas

**Historical VaR:**
```
VaR = percentile(returns, (1 - confidence_level) * 100)
CVaR = mean(returns[returns <= VaR])
```

**Parametric VaR:**
```
VaR = mean - z_score * std
CVaR = mean - std * phi(z) / (1 - confidence_level)
where phi(z) = standard normal PDF at z
```

**Monte Carlo VaR:**
```
simulated_returns = random_normal(mean, std, n_simulations)
VaR = percentile(simulated_returns, (1 - confidence_level) * 100)
```

**GARCH VaR:**
```
conditional_vol = GARCH(1,1).forecast(horizon=1)
VaR = mean - z_score * conditional_vol
```

### Normality Testing

**Jarque-Bera Test:**
```
JB = n/6 * (skewness^2 + (kurtosis - 3)^2 / 4)
p_value = exp(-JB/2)  # Approximation
Reject normality if p_value < 0.05
```

### Backtesting Logic

**Kupiec Test:**
```
LR = 2 * [(n - n1) * log((1 - p_hat)/(1 - p0)) + n1 * log(p_hat/p0)]
where:
  n = total observations
  n1 = number of exceptions
  p_hat = n1/n (actual rate)
  p0 = 1 - confidence_level (expected rate)
```

**Christoffersen Test:**
```
LR = 2 * [log(L1) - log(L0)]
L1 = (1-pi_01)^n_00 * pi_01^n_01 * (1-pi_11)^n_10 * pi_11^n_11
L0 = (1-pi)^(n_00 + n_10) * pi^(n_01 + n_11)
```

## Data Models

### Input Data Structures
```python
returns: np.ndarray  # Historical returns (can be pd.Series or list)
portfolio_value: Optional[float]  # For absolute VaR calculation
```

### Output Data Structures
All VaR calculators return dictionary with:
- `var`: float - VaR as decimal (e.g., -0.02 for -2%)
- `var_amount`: Optional[float] - Absolute VaR in currency units
- `cvar`: float - Conditional VaR
- `cvar_amount`: Optional[float] - Absolute CVaR
- `confidence_level`: float - Confidence level used
- `time_horizon`: int - Time horizon in days
- `method`: str - Calculation method
- Additional method-specific fields

## API Contracts

### calculate_var() Convenience Function
**Purpose:** Quick VaR calculation with method selection

**Args:**
- `returns`: np.ndarray - Historical returns
- `method`: str - 'historical', 'parametric', 'monte_carlo', 'garch'
- `confidence_level`: float - Default 0.95
- `portfolio_value`: Optional[float] - For absolute VaR
- `n_simulations`: int - For Monte Carlo (default 10000)

**Returns:**
- `Dict`: Method-specific VaR results

**Raises:**
- `ValueError`: Unknown method

**Example:**
```python
result = calculate_var(returns, method='historical', confidence_level=0.95)
print(f"VaR: {result['var']:.2%}")
```

### run_var_backtest() Convenience Function
**Purpose:** Quick backtesting of VaR model

**Args:**
- `var_predictions`: np.ndarray - Predicted VaR values
- `actual_returns`: np.ndarray - Actual returns
- `confidence_level`: float - VaR confidence (default 0.95)
- `significance_level`: float - Test significance (default 0.05)

**Returns:**
- `Dict`: Comprehensive backtest results

**Example:**
```python
results = run_var_backtest(var_preds, actual_returns, confidence_level=0.95)
print(f"Result: {results['overall_result']}")
```

## Error Handling

### Exception Handling Strategy
- **ValueError**: Empty returns array, invalid inputs
- **TypeError**: Invalid input types (non-numeric)
- **ZeroDivisionError**: Division by zero in calculations
- **FileNotFoundError**: ARCH package not available (GARCH fallback)
- **ImportError**: Scipy not available (fallback to hardcoded z-scores)

### Error Responses
```python
{'error': 'Descriptive error message'}
```

### Fallback Behavior
- GARCHVaRCalculator falls back to ParametricVaRCalculator if arch unavailable
- ParametricVaRCalculator uses hardcoded z-scores if scipy unavailable
- MonteCarloVaRCalculator uses numpy.random if Numba unavailable

### Logging
- WARNING: Normality test rejection (parametric VaR)
- WARNING: ARCH package unavailable (GARCH)
- ERROR: Calculation failures with stack traces
- INFO: Module initialization with Numba/ARCH status

## Performance Considerations

### Numba JIT Compilation
- First call: ~50-100ms (JIT compilation overhead)
- Subsequent calls: 10-100x faster
- Cache enabled: `@jit(cache=True)` for persistent compilation

### Performance Improvements
- Historical VaR: 50-100x speedup
- Parametric VaR: 30-50x speedup
- Monte Carlo VaR: 40-80x speedup (2-5x from parallel processing)
- GARCH VaR: 20-40x speedup (helpers only)

### Parallel Processing
- Monte Carlo uses `@njit(parallel=True)` with `prange`
- Scales linearly with CPU cores (2x on dual-core, 4x on quad-core)
- Only enabled for n_simulations > 1000

### Memory Efficiency
- In-place operations where possible
- No large intermediate allocations
- Efficient array slicing and views

## Testing Strategy

### Unit Tests Required
1. **Numba Functions**
   - Verify correctness vs pure Python implementations
   - Test edge cases (empty array, single element)
   - Benchmark performance improvements

2. **VaR Calculators**
   - Test each calculator with known datasets
   - Verify VaR values match expected ranges
   - Test portfolio_value conversion

3. **Backtesting**
   - Test Kupiec test with synthetic data
   - Test Christoffersen test with clustered exceptions
   - Verify overall assessment logic

### Integration Tests Required
1. End-to-end VaR calculation workflow
2. Backtesting with real VaR predictions
3. Fallback behavior (arch unavailable, scipy unavailable)

### Edge Cases to Test
- Empty returns array
- Single observation
- All identical returns (zero variance)
- Extreme values (NaN, Inf)
- Zero portfolio value

### Performance Tests
- Benchmark: Historical VaR, 10K observations < 10ms
- Benchmark: Parametric VaR, 10K observations < 20ms
- Benchmark: Monte Carlo, 10K simulations < 200ms
- Benchmark: GARCH, 1K observations < 500ms

## Security Considerations

### Input Validation
- Validate returns is numeric array
- Validate confidence_level in (0, 1)
- Validate portfolio_value > 0
- Validate n_simulations > 0

### Numerical Stability
- Handle zero variance (return default VaR)
- Handle empty arrays (return error)
- Handle NaN/Inf values (filter or error)

### Output Sanitization
- Round to 8 decimal places for floats
- Ensure finite values in outputs
- Validate VaR <= 0 (loss is negative)

## Compliance

### Regulatory References
- Hull, "Options, Futures, and Other Derivatives", Chapter 18
- Basel III market risk framework
- FRTB (Fundamental Review of the Trading Book)
- SRC (Standardized Approach for Counterparty Credit Risk)

### Validation Requirements
- Daily backtesting (250 observations minimum)
- Quarterly model validation
- Annual comprehensive review
- Document all model limitations

### Documentation Requirements
- VaR model governance manual
- Backtesting procedure documentation
- Model approval workflow
- Exception handling procedures

## Maintenance

### Version History
- v2.0.0: Numba JIT acceleration (50-100x speedup)
- v1.0.0: Initial implementation

### Module Information
```python
get_var_calculators_info() returns:
{
    'numba_version': str,
    'numba_available': bool,
    'arch_available': bool,
    'methods_available': List[str],
    'performance_improvements': Dict[str, str],
    'jit_compilation': str  # '95% compliance'
}
```

### Future Enhancements
- Add Expected Shortfall (ES) calculations
- Implement incremental VaR
- Add component VaR with marginal contributions
- Implement dynamic VaR with time-varying parameters

---
*Requirements completed on 2026-02-07*
*GAP Audit Status: PASSED*
