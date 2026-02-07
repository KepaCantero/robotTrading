# Requirements: services/regime_detection_chan.py

## Source File Analysis
- **File Path**: `app/services/regime_detection_chan.py`
- **Lines of Code**: 876
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

**Ernest Chan's Market Regime Detection** - Identifies market regimes (bull/bear/neutral) using statistical methods.

Implements methodologies from Ernest Chan's "Quantitative Trading: How to Build Your Own Algorithmic Trading Business".

**Key Features**:
1. Hidden Markov Models (HMM) for regime detection
2. K-Means clustering for trend-volatility regimes
3. Statistical threshold-based detection
4. Momentum-based regime identification
5. Regime transition probability estimation
6. Volatility regime detection (high/low)

---

## BASE_RULES Compliance

See [../BASE_RULES.md](../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **TYP-001**: 100% type coverage with comprehensive type hints
- **CC-006**: Explicit error handling with ValueError/TypeError
- **TRD-002**: Statistical validation of regime detection results
- **LOG-004**: Errors logged with context
- **ARCH-007**: Composition over inheritance (detector classes)

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies
- `app.core.statsmodels_fallback.adfuller` - ADF test with fallback (optional)

### External Dependencies
- `numpy` - Numerical operations
- `pandas` - Data manipulation
- `sklearn.cluster.KMeans` - K-Means clustering
- `sklearn.preprocessing.StandardScaler` - Feature standardization
- `sklearn.mixture.GaussianMixture` - Fallback for HMM
- `hmmlearn.hmm` - Hidden Markov Models (optional, has fallback)
- `logging` - Structured logging
- `dataclasses` - Data structures (RegimeState, RegimeTransition)
- `typing` - Type hints (Dict, List, Optional, Tuple)
- `enum` - Enum for RegimeType

---

## Classes/Functions

### 1. `RegimeType` (Enum)
**Purpose**: Market regime types

**Values**:
- `BULL` - Rising prices, low volatility
- `BEAR` - Falling prices, high volatility
- `NEUTRAL` - Sideways, moderate volatility
- `HIGH_VOLATILITY` - High volatility period
- `LOW_VOLATILITY` - Low volatility period
- `TREND_FOLLOWING` - Trend-following regime
- `MEAN_REVERSION` - Mean-reversion regime

### 2. `RegimeState` (Dataclass)
**Purpose**: Represents a detected regime state

**Attributes**:
- `regime_type: RegimeType` - Type of regime
- `probability: float` - Confidence in detection
- `expected_return: float` - Expected return in this regime
- `expected_volatility: float` - Expected volatility
- `duration_days: int` - Expected duration
- `start_date: pd.Timestamp` - When regime started
- `end_date: Optional[pd.Timestamp]` - When regime ended

### 3. `RegimeTransition` (Dataclass)
**Purpose**: Represents a regime transition

**Attributes**:
- `from_regime: RegimeType` - Source regime
- `to_regime: RegimeType` - Target regime
- `probability: float` - Transition probability
- `expected_duration_days: float` - Expected duration in source

### 4. `MarketRegimeDetector` (Class)
**Purpose**: Market regime detection using multiple methodologies

**Methods**:

#### `__init__(n_regimes: int = 3, method: str = "hmm", lookback_window: int = 60)`
- Initialize detector with configuration
- n_regimes: Number of regimes to detect
- method: 'hmm', 'kmeans', 'threshold', or 'momentum'
- lookback_window: Window for feature calculation

#### `detect_regimes(returns, prices=None, volume=None) -> pd.Series`
- **MAIN METHOD**: Detect market regimes from price/return data
- Returns series of regime labels with same index as returns
- Handles insufficient data gracefully
- Falls back to neutral regime on error

#### `_detect_hmm(returns, prices=None) -> pd.Series`
- Detect regimes using Hidden Markov Model
- HMM assumes observable returns from hidden state variable
- Fits HMM on features, predicts regimes
- Maps regimes to semantic labels (BULL/BEAR/NEUTRAL)

#### `_detect_kmeans(returns, prices=None) -> pd.Series`
- Detect regimes using K-Means clustering
- Clusters periods based on volatility and trend
- Standardizes features before clustering
- Maps clusters to regime types

#### `_detect_threshold(returns, prices=None) -> pd.Series`
- Detect regimes using statistical thresholds
- Uses return magnitude and volatility level
- Classifies based on quantile thresholds
- Simple but effective method

#### `_detect_momentum(returns) -> pd.Series`
- Detect regimes based on momentum characteristics
- Uses autocorrelation and momentum
- Identifies trend-following vs mean-reversion
- Lag-1 autocorrelation determines regime

#### `_prepare_features(returns, prices=None) -> np.ndarray`
- Prepare features for regime detection
- Features: rolling volatility, return, skewness, kurtosis, price momentum
- Removes NaN values
- Returns feature matrix

#### `_map_regimes_to_labels(regime_labels, returns) -> Dict[int, str]`
- Map numeric regime labels to semantic labels
- Sorts by mean return
- Maps lowest to BEAR, highest to BULL

#### `_analyze_regime_transitions(transition_matrix, regime_mapping) -> List[RegimeTransition]`
- Analyze regime transition probabilities
- Returns list of significant transitions
- Calculates expected duration

#### `get_current_regime(returns, prices=None) -> RegimeState`
- Get current market regime with full details
- Returns RegimeState with probability and metrics

#### `backtest_regime_aware_strategy(...)`
- Backtest regime-aware switching strategy
- Combines multiple strategy returns based on regime
- Returns combined strategy returns

### 5. `VolatilityRegimeDetector` (Class)
**Purpose**: Specialized detector for volatility regimes

**Methods**:

#### `__init__(n_regimes: int = 2, lookback_window: int = 20, method: str = "hmm")`
- Initialize volatility regime detector
- Typically 2 regimes: high/low volatility

#### `detect_volatility_regimes(returns) -> pd.Series`
- Detect volatility regimes from returns
- Returns 'high', 'low', or 'medium'
- Uses realized volatility

#### `_detect_hmm_volatility(volatility, original_index) -> pd.Series`
- HMM-based volatility regime detection
- Maps regimes to high/low/medium

#### `_detect_threshold_volatility(volatility, original_index) -> pd.Series`
- Threshold-based volatility regime detection
- Uses percentiles: 33% and 67%

### 6. Convenience Functions

#### `detect_market_regimes(returns, method="hmm", n_regimes=3, **kwargs)`
- High-level function for regime detection
- Creates detector and calls detect_regimes

#### `get_regime_statistics(returns, regimes) -> pd.DataFrame`
- Calculate statistics for each regime
- Returns periods, pct_time, mean_return, volatility, Sharpe, max_drawdown

#### `_calculate_max_drawdown(returns) -> float`
- Calculate maximum drawdown from returns

#### `get_regime_detector(method="hmm", n_regimes=3, **kwargs)`
- Factory function for compliance engine integration
- Returns configured MarketRegimeDetector

---

## Business Logic

### Regime Detection Methods

**1. Hidden Markov Model (HMM)**:
- Assumes observable returns from hidden state variable
- State follows Markov process (future depends only on present)
- Fits Gaussian HMM on features
- Predicts most likely state sequence

**2. K-Means Clustering**:
- Clusters periods by volatility and trend characteristics
- Standardizes features before clustering
- Maps clusters to regimes by mean return

**3. Threshold-Based**:
- Uses return magnitude (bull/bear)
- Uses volatility level (high/low vol)
- Simple but effective classification

**4. Momentum-Based**:
- Uses autocorrelation at lag 1
- Positive autocorr = trend-following
- Negative autocorr = mean-reversion
- Low autocorr = neutral

### Regime Mapping

**3-Regime Mapping** (most common):
- Lowest mean return → BEAR
- Middle mean return → NEUTRAL
- Highest mean return → BULL

**N-Regime Mapping**:
- Sorted by mean return
- First → BEAR
- Last → BULL
- Middle → NEUTRAL

### Volatility Regimes

**2-Regime**:
- Lowest volatility → 'low'
- Highest volatility → 'high'

**3-Regime**:
- Low → 'low'
- Medium → 'medium'
- High → 'high'

### Transition Analysis

**Transition Matrix**: P[i,j] = probability from state i to state j

**Expected Duration**: 1 / (1 - P[i,i])

Significant transitions: P[i,j] > 0.01 (1% threshold)

---

## Data Models

### `RegimeType` Enum
```python
class RegimeType(Enum):
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
```

### `RegimeState` Dataclass
```python
@dataclass
class RegimeState:
    regime_type: RegimeType
    probability: float
    expected_return: float
    expected_volatility: float
    duration_days: int
    start_date: pd.Timestamp
    end_date: Optional[pd.Timestamp] = None
```

### `RegimeTransition` Dataclass
```python
@dataclass
class RegimeTransition:
    from_regime: RegimeType
    to_regime: RegimeType
    probability: float
    expected_duration_days: float
```

---

## API Contracts

### Basic Usage
```python
detector = MarketRegimeDetector(n_regimes=3, method="hmm")

# Detect regimes
regimes = detector.detect_regimes(returns, prices)

# Get current regime
current = detector.get_current_regime(returns, prices)
print(f"Current regime: {current.regime_type.value}")
print(f"Expected return: {current.expected_return:.2%}")
print(f"Expected volatility: {current.expected_volatility:.2%}")
```

### Volatility Regimes
```python
vol_detector = VolatilityRegimeDetector(n_regimes=2)
vol_regimes = vol_detector.detect_volatility_regimes(returns)
```

### Regime-Aware Strategy
```python
combined = detector.backtest_regime_aware_strategy(
    returns=market_returns,
    regime_signals=regimes,
    bull_strategy_returns=bull_returns,
    bear_strategy_returns=bear_returns,
    neutral_strategy_returns=neutral_returns,
)
```

### Regime Statistics
```python
stats = get_regime_statistics(returns, regimes)
print(stats)
#   regime  periods  pct_time  mean_return  volatility  sharpe  max_drawdown
# 0   bear      100      20.0       -0.05        0.20     -1.5        -0.30
# 1   neutral    150      30.0        0.02        0.15      0.5        -0.10
# 2   bull      250      50.0        0.10        0.12      2.0        -0.05
```

---

## Error Handling

### HMM Fallback

When `hmmlearn` is not available:
- Uses `GaussianMixture` as fallback
- Similar interface to `hmmlearn.GaussianHMM`
- Creates simplified transition matrix
- Logs warning about fallback

### Insufficient Data

When returns < lookback_window:
- Raises ValueError with clear message
- Returns neutral regime in detect_regimes (caught)

### Calculation Errors

When calculations fail:
- Logged with error level
- Return neutral regime or default values
- Does not crash the detector

---

## Performance Considerations

1. **Feature Calculation**: Rolling operations can be slow
   - Consider using numba for optimization
   - Cache features for repeated calls

2. **HMM Fitting**: Can be slow for large datasets
   - n_iter parameter controls iterations
   - Consider subsampling for very large data

3. **Memory**: Feature matrix can be large
   - Remove NaN values to reduce size
   - Use float32 instead of float64 if precision allows

---

## Testing Strategy

### Unit Tests Required

1. **Regime Detection**:
   - Test HMM detection with synthetic data
   - Test K-Means detection
   - Test threshold detection
   - Test momentum detection

2. **Regime Mapping**:
   - Test mapping for 3 regimes
   - Test mapping for N regimes
   - Test edge cases (all same return)

3. **Volatility Detection**:
   - Test 2-regime detection
   - Test 3-regime detection
   - Test threshold fallback

4. **Transition Analysis**:
   - Test transition probability calculation
   - Test expected duration calculation

### Integration Tests Required

1. Test with real market data
2. Test regime-aware strategy backtest
3. Test compliance engine integration

### Test Coverage Target: >80%

---

## Configuration

### Default Parameters

```yaml
regime_detection:
  # General
  n_regimes: 3
  lookback_window: 60  # days

  # Methods
  method: "hmm"  # "hmm", "kmeans", "threshold", "momentum"

  # HMM
  hmm_iterations: 1000
  hmm_covariance_type: "full"
  hmm_random_state: 42

  # K-Means
  kmeans_n_init: 10
  kmeans_random_state: 42

  # Thresholds
  return_quantiles: [0.33, 0.67]
  vol_quantile: 0.5

  # Momentum
  autocorr_threshold: 0.1

  # Volatility Detection
  vol_n_regimes: 2
  vol_lookback: 20
  vol_method: "hmm"
```

---

## Mathematical References

### Hidden Markov Model

From **Hamilton (1989)**:

Observable returns `y_t` generated by hidden state `s_t`:
```
y_t | s_t ~ N(μ_s, σ_s^2)
P(s_t | s_{t-1}) = transition_matrix[s_{t-1}, s_t]
```

### Regime Features

**Rolling Volatility**:
```
vol_t = std(returns_{t-lookback+1:t}) * sqrt(252)
```

**Rolling Return**:
```
ret_t = mean(returns_{t-lookback+1:t}) * 252
```

**Skewness**:
```
skew_t = skew(returns_{t-lookback+1:t})
```

**Kurtosis**:
```
kurt_t = kurt(returns_{t-lookback+1:t})
```

### Expected Duration

For self-transition probability `P[i,i]`:
```
expected_duration = 1 / (1 - P[i,i])
```

---

## Trading Applications

### Regime-Dependent Strategy Selection

1. **Bull Regime**: Use trend-following strategies
2. **Bear Regime**: Use defensive strategies or reduce exposure
3. **Neutral Regime**: Use mean-reversion strategies
4. **High Volatility**: Reduce position sizes, widen stops
5. **Low Volatility**: Can increase position sizes

### Risk Management

- Adjust risk limits based on regime
- Wider stops in high volatility
- Tighter stops in low volatility
- Regime-aware position sizing

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0104
**Violations**: 0
**Notes**: Excellent implementation of Ernest Chan's regime detection methodologies. Clean code with proper fallback handling for optional dependencies (hmmlearn). Multiple detection methods provide flexibility. Good mathematical documentation in docstrings. Proper error handling throughout.

---
