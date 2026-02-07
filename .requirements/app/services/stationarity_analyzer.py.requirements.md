# Requirements: services/stationarity_analyzer.py

## Source File Analysis
- **File Path**: `app/services/stationarity_analyzer.py`
- **Lines of Code**: 985
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

**Stationarity and Cointegration Analyzer** - Implements Ernest Chan's methodologies for analyzing time series properties.

Based on "Algorithmic Trading: A Practitioner's Guide" by Ernest P. Chan.

**Key Features**:
1. Augmented Dickey-Fuller (ADF) test for stationarity
2. Half-life of mean reversion calculation
3. Hurst exponent for trend/stationarity detection
4. Optimal lookback period determination
5. Cointegration testing for pair trading
6. Hedge ratio calculation
7. Optimal entry/exit thresholds

---

## BASE_RULES Compliance

See [../BASE_RULES.md](../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **TYP-001**: 100% type coverage with Union types
- **CC-006**: Explicit error handling with ValueError/TypeError
- **TRD-002**: Statistical validation of test results
- **LOG-004**: Errors logged with context
- **ARCH-007**: Composition over inheritance

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies
- `app.core.statsmodels_fallback.adfuller` - ADF test with fallback (optional)

### External Dependencies
- `numpy` - Numerical operations
- `pandas` - Data manipulation
- `logging` - Structured logging
- `dataclasses` - Data structures (dataclass decorators)
- `typing` - Type hints (Dict, List, Optional, Tuple, Union, Any)

---

## Classes/Functions

### 1. `StationarityTestResult` (Dataclass)
**Purpose**: Results from ADF stationarity test

**Attributes**:
- `is_stationary: bool` - Whether series is stationary
- `adf_statistic: float` - ADF test statistic
- `p_value: float` - P-value of test
- `critical_values: Dict[str, float]` - Critical values at 1%, 5%, 10%
- `confidence_level: float` - Test confidence level
- `half_life: Optional[float]` - Half-life of mean reversion
- `hurst_exponent: Optional[float]` - Hurst exponent
- `interpretation: str` - Human-readable interpretation

### 2. `CointegrationTestResult` (Dataclass)
**Purpose**: Results from cointegration test

**Attributes**:
- `is_cointegrated: bool` - Whether series are cointegrated
- `test_statistic: float` - Test statistic
- `p_value: float` - P-value
- `critical_values: Dict[str, float]` - Critical values
- `hedge_ratio: float` - Hedge ratio for pairs trading
- `spread_half_life: float` - Half-life of spread
- `confidence_level: float` - Test confidence level
- `interpretation: str` - Human-readable interpretation
- `mean_reversion_speed: str` - Speed description

### 3. `MeanReversionParameters` (Dataclass)
**Purpose**: Optimal parameters for mean reversion strategy

**Attributes**:
- `optimal_lookback: int` - Optimal lookback period
- `optimal_entry_threshold: float` - Entry z-score
- `optimal_exit_threshold: float` - Exit z-score
- `expected_half_life: float` - Expected half-life
- `sharpe_ratio_estimate: float` - Expected Sharpe ratio
- `recommended_stop_loss: float` - Recommended stop loss
- `recommended_position_size: float` - Recommended position size

### 4. `StationarityAnalyzer` (Class)
**Purpose**: Analyzer for stationarity and mean reversion properties

**Constants**:
- `DEFAULT_CONFIDENCE_LEVEL = 0.95`
- `DEFAULT_ADF_LAG = 1`
- `DEFAULT_ADF_REGRESSION = "c"`

**Methods**:

#### `__init__(confidence_level=0.95, min_observations=30)`
- Initialize analyzer with parameters

#### `test_stationarity(prices, asset_name=None, calculate_half_life=True, calculate_hurst=True)`
- **PRIMARY METHOD**: Test if price series is stationary
- Uses ADF test (Augmented Dickey-Fuller)
- Calculates half-life if requested
- Calculates Hurst exponent if requested
- Returns StationarityTestResult with full analysis

#### `_adf_test(series)`
- Perform ADF test for stationarity
- Uses statsmodels with fallback
- Returns dict with statistic, p-value, critical values

#### `_simplified_adf_test(series)`
- Fallback ADF test when statsmodels unavailable
- Uses OLS regression
- Approximates ADF statistic

#### `calculate_half_life(series)`
- Calculate half-life of mean reversion
- Ernest Chan's formula: `half_life = -ln(2) / theta`
- Where theta from OU process: `dy = theta * (mu - y) * dt + sigma * dW`
- Returns half-life in time periods

#### `calculate_hurst_exponent(series, max_lag=20)`
- Calculate Hurst exponent
- Uses R/S analysis (Rescaled Range)
- Interpretation:
  - H < 0.5: Mean reverting (stationary)
  - H = 0.5: Random walk
  - H > 0.5: Trending
- Returns Hurst exponent (0-1)

#### `find_optimal_lookback(prices, max_lookback=100, min_lookback=5)`
- Find optimal lookback period
- Tests different lookbacks
- Finds period with fastest mean reversion
- Balances signal strength and responsiveness

#### `_interpret_stationarity_result(...)`
- Interpret test results
- Returns human-readable summary

#### `_create_non_stationary_result(...)`
- Create non-stationary result with explanation

### 5. `CointegrationAnalyzer` (Class)
**Purpose**: Analyzer for cointegration between multiple price series

**Methods**:

#### `__init__(confidence_level=0.95, min_observations=30)`
- Initialize analyzer

#### `test_cointegration(y1, y2, asset1_name="Asset1", asset2_name="Asset2")`
- **PRIMARY METHOD**: Test if two series are cointegrated
- Uses Engle-Granger test:
  1. Calculate hedge ratio via OLS: `y2 = alpha + beta * y1`
  2. Calculate spread: `spread = y2 - beta * y1`
  3. Test spread for stationarity using ADF
  4. Calculate half-life of mean reversion
- Returns CointegrationTestResult

#### `_calculate_hedge_ratio(y1, y2)`
- Calculate hedge ratio using OLS regression
- Returns (hedge_ratio, intercept)

#### `calculate_optimal_position_sizes(cointegration_result, price1, price2, capital, risk_per_trade=0.02)`
- Calculate optimal position sizes for pairs trade
- Based on hedge ratio and capital allocation
- Returns (position_size_1, position_size_2)

#### `calculate_entry_exit_thresholds(spread, confidence_multiplier=2.0)`
- Calculate entry/exit thresholds for pairs trading
- Ernest Chan's methodology:
  - Entry: >2 standard deviations
  - Exit: returns to mean (or within 1 std)
- Returns (entry_threshold, exit_threshold)

#### `_interpret_cointegration_result(...)`
- Interpret cointegration test results
- Returns human-readable summary

#### `_create_non_cointegrated_result(...)`
- Create non-cointegrated result with explanation

### 6. Convenience Functions

#### `find_cointegrated_pairs(price_data, confidence_level=0.95, min_half_life=30.0, max_half_life=100.0)`
- Find cointegrated pairs from universe of assets
- Tests all possible pairs
- Filters by half-life
- Returns sorted list of (asset1, asset2, result)

---

## Business Logic

### Stationarity Testing

**Augmented Dickey-Fuller Test**:
- Tests for unit root (non-stationarity)
- H0: Series has unit root (non-stationary)
- H1: Series is stationary
- Reject H0 if p-value < (1 - confidence_level)

**Ernest Chan's Methodology**:
- Use ADF test with lag-1 difference (daily data)
- Focus on p-value < 0.05 for stationarity
- Calculate half-life for mean reversion speed
- Use Hurst exponent to confirm (H < 0.5 = mean reversion)

### Half-Life of Mean Reversion

**Formula**: `half_life = -ln(2) / theta`

Where theta is the coefficient from:
```
dy = theta * (mu - y) + epsilon
dy = -theta * y + theta * mu + epsilon
```

**Interpretation**:
- Short half-life = fast mean reversion (good for trading)
- Long half-life = slow mean reversion (less profitable)
- Infinite half-life = no mean reversion

### Hurst Exponent

**R/S Analysis**:
- Calculates rescaled range for different lags
- Regresses log(R/S) on log(lag)
- Slope = Hurst exponent

**Interpretation**:
- H < 0.4: Strong mean reversion
- 0.4 < H < 0.5: Moderate mean reversion
- H ≈ 0.5: Random walk
- 0.5 < H < 0.6: Random walk behavior
- H > 0.6: Trending

### Cointegration Testing

**Engle-Granger Two-Step Method**:
1. **Step 1**: Calculate hedge ratio via OLS
   ```
   y2 = alpha + beta * y1
   beta = hedge_ratio
   ```

2. **Step 2**: Calculate spread
   ```
   spread = y2 - alpha - beta * y1
   ```

3. **Step 3**: Test spread for stationarity
   - If spread is stationary → cointegrated
   - If spread is non-stationary → not cointegrated

4. **Step 4**: Calculate half-life of spread
   - Determines trading frequency

**Trading Strategy**:
- Entry: When spread deviates by >2 standard deviations
- Exit: When spread returns to mean
- Position sizes based on hedge ratio

### Optimal Lookback

**Methodology**:
- Test different lookback periods
- Find period with fastest mean reversion (lowest half-life)
- Penalize very short lookbacks (noise)
- Penalize very long lookbacks (slow)

---

## Data Models

### Stationarity Test Result
```python
@dataclass
class StationarityTestResult:
    is_stationary: bool
    adf_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    confidence_level: float
    half_life: Optional[float] = None
    hurst_exponent: Optional[float] = None
    interpretation: str = ""
```

### Cointegration Test Result
```python
@dataclass
class CointegrationTestResult:
    is_cointegrated: bool
    test_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    hedge_ratio: float
    spread_half_life: float
    confidence_level: float
    interpretation: str = ""
    mean_reversion_speed: str = ""
```

---

## API Contracts

### Stationarity Testing
```python
analyzer = StationarityAnalyzer(confidence_level=0.95)

# Test stationarity
result = analyzer.test_stationarity(
    prices=price_series,
    asset_name="AAPL",
    calculate_half_life=True,
    calculate_hurst=True
)

print(f"Is stationary: {result.is_stationary}")
print(f"Half-life: {result.half_life:.1f} days")
print(f"Hurst exponent: {result.hurst_exponent:.3f}")
print(result.interpretation)
```

### Half-Life Calculation
```python
half_life = analyzer.calculate_half_life(log_prices)
print(f"Mean reversion half-life: {half_life:.1f} periods")
```

### Hurst Exponent
```python
hurst = analyzer.calculate_hurst_exponent(prices)
if hurst < 0.5:
    print("Mean reverting")
elif hurst > 0.5:
    print("Trending")
else:
    print("Random walk")
```

### Cointegration Testing
```python
analyzer = CointegrationAnalyzer(confidence_level=0.95)

result = analyzer.test_cointegration(
    y1=prices_AAPL,
    y2=prices_MSFT,
    asset1_name="AAPL",
    asset2_name="MSFT"
)

if result.is_cointegrated:
    print(f"Hedge ratio: {result.hedge_ratio:.4f}")
    print(f"Spread half-life: {result.spread_half_life:.1f} days")
    print(result.interpretation)
```

### Finding Cointegrated Pairs
```python
prices = {
    "AAPL": aapl_prices,
    "MSFT": msft_prices,
    "GOOGL": googl_prices,
}

pairs = find_cointegrated_pairs(
    prices,
    min_half_life=10.0,
    max_half_life=60.0
)

for asset1, asset2, result in pairs:
    print(f"{asset1}-{asset2}: half-life={result.spread_half_life:.1f}")
```

### Optimal Lookback
```python
optimal_lookback = analyzer.find_optimal_lookback(
    prices,
    max_lookback=100,
    min_lookback=5
)
print(f"Optimal lookback: {optimal_lookback} days")
```

---

## Error Handling

### Insufficient Data

When observations < min_observations:
- Logged with warning
- Returns non-stationary result
- Explains insufficient data

### Calculation Errors

When calculations fail:
- Caught by try/except
- Logged with error level
- Return sensible defaults (inf for half-life, 0.5 for Hurst)

### OLS Failures

When OLS regression fails:
- Use simple ratio as fallback
- Log warning about fallback

---

## Performance Considerations

1. **Rolling Calculations**: Can be slow for large datasets
   - Consider using numba for optimization
   - Use efficient pandas operations

2. **HMM Fitting**: Can be slow for large datasets
   - n_iter parameter controls iterations
   - Consider subsampling

3. **Pair Testing**: O(n^2) complexity
   - For large universes, consider sampling
   - Parallelize pair tests

---

## Testing Strategy

### Unit Tests Required

1. **Stationarity Tests**:
   - Test ADF test with known stationary series
   - Test ADF test with known non-stationary series
   - Test half-life calculation
   - Test Hurst exponent calculation

2. **Cointegration Tests**:
   - Test with cointegrated series
   - Test with non-cointegrated series
   - Test hedge ratio calculation
   - Test spread calculation

3. **Edge Cases**:
   - Short series (< min_observations)
   - Series with NaN values
   - Zero variance series
   - Perfectly correlated series

### Integration Tests Required

1. Test with real market data
2. Test pairs trading strategy
3. Test mean reversion strategy

### Test Coverage Target: >85%

---

## Configuration

### Default Parameters

```yaml
stationarity_analyzer:
  # General
  confidence_level: 0.95
  min_observations: 30

  # ADF Test
  adf_lag: 1
  adf_regression: "c"  # Constant only

  # Hurst Exponent
  hurst_max_lag: 20

  # Optimal Lookback
  max_lookback: 100
  min_lookback: 5

  # Cointegration
  min_half_life: 10.0
  max_half_life: 100.0

  # Entry/Exit Thresholds
  entry_threshold_multiplier: 2.0  # 2 std dev
  exit_threshold_multiplier: 0.5   # 0.5 std dev
```

---

## Mathematical References

### Augmented Dickey-Fuller Test

Tests the equation:
```
Δy_t = α + β*t + γ*y_{t-1} + δ_1*Δy_{t-1} + ... + δ_p*Δy_{t-p} + ε_t
```

H0: γ = 0 (unit root exists, non-stationary)
H1: γ < 0 (stationary)

### Half-Life from Ornstein-Uhlenbeck Process

**OU Process**:
```
dy = θ * (μ - y) * dt + σ * dW
```

**Discrete form**:
```
y_t - y_{t-1} = θ * (μ - y_{t-1}) + ε_t
y_t - y_{t-1} = θ*μ - θ*y_{t-1} + ε_t
Δy = -θ*y_{t-1} + θ*μ + ε_t
```

**Regression**:
```
Δy = α + β*y_{t-1} + ε
```

Where β = -θ

**Half-Life**:
```
half_life = -ln(2) / θ = -ln(2) / (-β) = ln(2) / β
```

### Hurst Exponent via R/S Analysis

1. Calculate cumulative deviations from mean:
   ```
   Z_t = Σ(y_i - mean_y) for i=1 to t
   ```

2. Calculate range:
   ```
   R(T) = max(Z_t) - min(Z_t)
   ```

3. Calculate standard deviation:
   ```
   S(T) = std(y)
   ```

4. Calculate rescaled range:
   ```
   R/S = R(T) / S(T)
   ```

5. Repeat for different lag T
6. Regress log(R/S) on log(T)
7. Slope = Hurst exponent

---

## Trading Applications

### Mean Reversion Strategy

1. **Find Stationary Series**:
   - Test assets for stationarity
   - Select those with H < 0.5
   - Prefer short half-life (< 30 days)

2. **Calculate Z-Score**:
   ```
   z = (price - mean) / std
   ```

3. **Entry Signals**:
   - SHORT when z > 2 (overbought)
   - LONG when z < -2 (oversold)

4. **Exit Signals**:
   - Cover when z returns to 0

### Pairs Trading

1. **Find Cointegrated Pairs**:
   - Test all pairs for cointegration
   - Filter by half-life (10-60 days ideal)
   - Select best hedge ratio

2. **Calculate Spread**:
   ```
   spread = y2 - hedge_ratio * y1
   ```

3. **Entry Signals**:
   - Long spread when spread < -2*std
   - Short spread when spread > 2*std

4. **Exit Signals**:
   - Exit when spread returns to mean

### Position Sizing

**Based on Hedge Ratio**:
- Size position 2 relative to position 1
- Use hedge ratio from cointegration test

**Based on Volatility**:
- Size inversely proportional to volatility
- Target constant risk across pairs

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0105
**Violations**: 0
**Notes**: Excellent implementation of Ernest Chan's stationarity and cointegration methodologies. Clean code with proper fallback handling for optional dependencies (statsmodels). Comprehensive mathematical documentation. Good error handling throughout with sensible defaults. Half-life and Hurst exponent calculations are correctly implemented.

---
