# Requirements: engines/strategy_engines/arbitrage_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/arbitrage_engine.py`
- **Lines of Code**: 931
- **Language**: Python 3.10+
- **Purpose**: Statistical arbitrage, spread trading, and carry trade strategies

## Dependencies
### Internal
- `app.engines.strategy_engines.base.BaseStrategyEngine` - Base class for strategies
- `app.core.centralized_config` - Strategy configuration from YAML
- `app.models.market_data.Quote` - Market data model
- `app.models.portfolio.Portfolio` - Portfolio model
- `app.models.signal.Signal*` - Signal enums and classes
- `app.services.momentum_analysis.TechnicalIndicatorCalculator` - Technical indicators

### External
- `logging` - Structured logging
- `collections` - defaultdict, deque for efficient data structures
- `decimal.Decimal` - Precise financial calculations
- `typing` - Type hints (Dict, List, Optional, Any, Sequence)
- `numpy` - Statistical calculations (corrcoef, std, mean)

## Classes/Functions

### ArbitrageStrategyEngine(BaseStrategyEngine)
Implements three types of arbitrage strategies.

**Arbitrage Types:**
1. `ARBITRAGE_TYPE_STATISTICAL` - Mean reversion on z-score deviations
2. `ARBITRAGE_TYPE_SPREAD` - Pure spread arbitrage on price differences
3. `ARBITRAGE_TYPE_CARRY` - Yield/funding rate differentials

#### Configuration Parameters
**From YAML / Config Dict:**
```python
arbitrage_type: str  # 'statistical', 'spread', 'carry'
lookback_period: int  # Default 60 periods
entry_z_score: Decimal  # Default 2.0 (statistical)
exit_z_score: Decimal  # Default 0.5 (statistical)
min_spread_pct: Decimal  # Default 0.5%
max_spread_pct: Decimal  # Default 10%
min_correlation: Decimal  # Default 0.70
max_exposure: Decimal  # Default 40%
max_position_per_leg: Decimal  # Default 15%
min_signal_confidence: float  # Default 60.0
carry_yield_threshold: Decimal  # Default 2%
funding_rate_threshold: Decimal  # Default 0.01%
stop_loss: Decimal  # From trading_threshold
take_profit: Decimal  # From trading_threshold
max_position_size: Decimal  # From trading_threshold
arbitrage_pairs: List[List[str]]  # Default: SPY-IVV, GLD-IAU, QQQ-TQQQ
```

#### Key Methods

**extract_features(market_data, historical_data) -> Dict[str, Any]**
Extract standardized features for Learning Engine integration.

**Features returned:**
```python
{
    'timestamp': datetime,
    'symbol': str,
    'price': float,
    'arbitrage_type': str,
    'pair': List[str],
    'other_symbol': str,
    'spread': float,
    'spread_pct': float,
    'spread_mean': float,
    'spread_std': float,
    'spread_z_score': float,
    'correlation': float,  # 20-period rolling
    'spread_volatility': float,  # 20-period std
    'half_life_days': float,  # Mean reversion speed
    'relative_spread_position': float,  # 0-1 within range
    'yield_current': float,  # Carry trade only
    'yield_other': float,
    'yield_differential': float,
    'funding_rate': float
}
```

**_generate_signals_impl(market_data) -> List[Signal]**
Main signal generation logic. Updates price history and delegates to type-specific generators.

**_generate_statistical_arbitrage_signals()**
Entry conditions:
- Long spread: z_score < -entry_z_score (buy leg1, sell leg2)
- Short spread: z_score > entry_z_score (sell leg1, buy leg2)
- Filters: correlation >= min_correlation, spread_pct within bounds

**_generate_spread_arbitrage_signals()**
Entry conditions:
- Current price > other * (1 + min_spread_pct): SELL current
- Other price > current * (1 + min_spread_pct): BUY current
- Filters: correlation >= min_correlation

**_generate_carry_trade_signals()**
Entry conditions:
- yield_differential > carry_yield_threshold: BUY current (high yield)
- yield_differential < -carry_yield_threshold: SELL current (low yield)

**_estimate_half_life(spreads) -> Optional[float]**
OLS regression: spread_diff = theta * spread_lag + epsilon
Half-life = -ln(2) / ln(1 + theta) if theta < 0 (mean-reverting)

**_calculate_confidence() -> float**
Base confidence 50%, bonuses:
- Statistical: +25/+20/+15/+10 for |z| >= 3.0/2.5/2.0/1.5
- Statistical: +15/+10/+5 for |corr| >= 0.95/0.90/0.80
- Spread: +30/+20/+10 for |corr| >= 0.95/0.90/0.80
- Carry: +20 base premium

**risk_check(signal, portfolio) -> bool**
Validates:
- Total exposure < max_exposure
- Signal confidence >= min_signal_confidence
- Symbol exposure < max_position_per_leg

**get_spread_statistics(pair_key) -> Optional[Dict]**
Returns spread statistics for a given pair.

## Business Logic

### Statistical Arbitrage Logic
```
1. Calculate spread = price_A - price_B
2. Calculate z_score = (spread - mean) / std
3. Entry: |z_score| > entry_z_score
4. Exit: |z_score| < exit_z_score
5. Position: Long spread (buy A, sell B) or Short spread (sell A, buy B)
```

### Spread Arbitrage Logic
```
1. Calculate spread_pct = |price_A - price_B| / price_B
2. If spread_pct > min_spread_pct and spread_pct < max_spread_pct:
   - Sell overpriced asset, buy underpriced asset
3. Filter by correlation >= min_correlation
```

### Carry Trade Logic
```
1. Calculate yield_differential = yield_A - yield_B
2. If |yield_differential| > carry_yield_threshold:
   - Buy high-yield asset, sell low-yield asset
3. Monitor funding_rate for futures/derivatives
```

### Half-Life Estimation
```
spread_lag = spread[t-1]
spread_diff = spread[t] - spread[t-1]
theta = cov(spread_diff, spread_lag) / var(spread_lag)
half_life = -ln(2) / ln(1 + theta)  # if theta < 0
```

## Data Models

### Input Data Structures
```python
market_data: Quote
{
    symbol: str,
    close: Decimal,  # or bid, last
    bid: Decimal,
    ask: Decimal,
    timestamp: datetime,
    volume: float
}

portfolio: Portfolio
{
    positions: List[Position],
    cash: Decimal,
    total_equity: Decimal
}
```

### Internal State
```python
price_history: Dict[str, deque]  # maxlen=300
volume_history: Dict[str, deque]
spread_history: Dict[str, deque]
yield_data: Dict[str, float]
funding_rates: Dict[str, float]
active_arbitrage_positions: Dict[str, Dict]
```

### Output Data Structures
```python
Signal
{
    symbol: str,
    signal_type: SignalType (BUY/SELL),
    strength: SignalStrength (WEAK/MODERATE/STRONG/VERY_STRONG),
    price: Decimal,
    timestamp: datetime,
    confidence: float,  # 0-100
    liquidity_score: float,
    priority_score: float,
    source: SignalSource.ARBITRAGE,
    volume: Decimal,
    metadata: Dict
}
```

## API Contracts

### set_yield_data(symbol, yield_rate)
Set annualized yield rate for carry trades.

**Args:**
- `symbol`: str - Asset symbol
- `yield_rate`: float - Annualized yield (e.g., 0.05 for 5%)

### set_funding_rate(symbol, funding_rate)
Set funding rate for derivatives.

**Args:**
- `symbol`: str - Asset symbol
- `funding_rate`: float - Funding rate (e.g., 0.0001 for 0.01%)

### get_active_arbitrage_positions() -> Dict
Get currently active arbitrage positions.

### get_spread_statistics(pair_key) -> Optional[Dict]
Get statistics for a specific pair.

**Returns:**
```python
{
    'mean': float,
    'std': float,
    'min': float,
    'max': float,
    'current': float,
    'z_score': float
}
```
or None if insufficient history.

## Error Handling

### Exception Handling Strategy
- **ValueError**: Invalid numerical inputs, division by zero
- **TypeError**: Type conversion failures
- **KeyError**: Missing data in dictionaries
- **AttributeError**: Missing object attributes
- **IndexError**: Empty sequences

### Error Responses
- Empty list returned on signal generation errors
- Logged errors with stack traces
- Defensive defaults for missing data

### Logging
- ERROR: Signal generation failures with stack traces
- DEBUG: Risk check failures
- DEBUG: Yield/funding rate updates
- INFO: Initialization with configuration

## Performance Considerations

### Data Structure Optimization
- `deque` with maxlen for O(1) append/pop from both ends
- Automatic trimming of history (maxlen=300)
- Efficient pair lookup (linear search over pairs list)

### Computational Complexity
- Signal generation: O(p) where p = lookback_period
- Correlation calculation: O(min(20, n))
- Spread calculation: O(min(300, n))
- Half-life estimation: O(n) for OLS regression

### Memory Efficiency
- Fixed-size deques prevent unbounded growth
- Rolling windows with maxlen
- Lazy calculation (only when needed)

## Testing Strategy

### Unit Tests Required
1. **Feature Extraction**
   - Test all features are calculated correctly
   - Test edge cases (insufficient history)
   - Verify correlation calculation

2. **Signal Generation**
   - Test statistical arbitrage signals
   - Test spread arbitrage signals
   - Test carry trade signals
   - Test entry/exit conditions

3. **Risk Checks**
   - Test exposure limits
   - Test confidence filtering
   - Test position limits

4. **Half-Life Estimation**
   - Test with mean-reverting series
   - Test with trending series (should return None)
   - Verify OLS regression correctness

### Integration Tests Required
1. End-to-end signal generation workflow
2. Integration with portfolio for risk checks
3. Configuration from YAML
4. Learning Engine feature extraction

### Edge Cases to Test
- Empty price history
- Single observation
- Zero variance spread
- Zero correlation
- Missing yield data for carry trades
- Insufficient history for half-life

### Performance Tests
- Benchmark: Signal generation < 50ms per update
- Benchmark: Feature extraction < 20ms per quote
- Benchmark: Risk check < 5ms per signal

## Security Considerations

### Input Validation
- Validate price > 0
- Validate spread_pct >= 0
- Validate confidence in [0, 100]
- Validate correlation in [-1, 1]

### Numerical Stability
- Handle zero std (return default 1e-8)
- Handle zero volume (return 0)
- Handle division by zero in spread_pct

### Configuration Security
- Validate all thresholds from YAML
- Sanitize arbitrage_pairs list
- Validate min/max spread bounds (min < max)

## Compliance

### Trading Best Practices
- Diversified pairs (default 3 pairs)
- Position limits per leg (15% default)
- Total exposure limit (40% default)
- Correlation filter (0.70 minimum)
- Confidence threshold (60% minimum)

### Risk Management
- Stop loss from global configuration
- Take profit from global configuration
- Maximum position size enforcement
- Exposure tracking per symbol

### Documentation Requirements
- Strategy methodology document
- Backtesting results for all pairs
- Live trading performance tracking
- Model validation procedures

## Maintenance

### Version History
- v1.0.0: Initial implementation with three arbitrage types

### Configuration Management
- YAML configuration for parameters
- Centralized config integration
- Trading thresholds from global config

### Future Enhancements
- Add cointegration testing for pairs
- Implement optimal entry timing
- Add multi-leg arbitrage (3+ assets)
- Implement dynamic hedge ratios
- Add PnL tracking for arbitrage positions

---
*Requirements completed on 2026-02-07*
*GAP Audit Status: PASSED*
