# Requirements: microstructure/liquidity.py

## Source File Analysis
- **File Path**: `app/microstructure/liquidity.py`
- **Lines of Code**: 975
- **Language**: Python 3.10+
- **Purpose**: Market depth and liquidity analysis (O'Hara "Market Microstructure Theory" Chapters 5-6)

## Dependencies
### Internal
- None (standalone microstructure analysis module)

### External
- `logging` - Structured logging
- `datetime` - Timestamp management
- `decimal.Decimal` - Precise financial calculations
- `enum.Enum` - Type-safe enums
- `dataclasses.dataclass` - Data model definitions
- `numpy` - Numerical computations
- `pandas` - Time series analysis

## Classes/Functions

### Enums

#### LiquidityDimension
Dimensions of liquidity measurement:
- `DEPTH` - Volume available at prices
- `TIGHTNESS` - Bid-ask spread
- `RESILIENCE` - Speed of recovery from shocks
- `IMMEDIACY` - Speed of execution

#### SpreadComponent
Components of bid-ask spread (Stoll 2000):
- `ORDER_PROCESSING` - Fixed costs of trading (30-50% of spread)
- `INVENTORY_HOLDING` - Inventory risk premium
- `ADVERSE_SELECTION` - Information asymmetry cost

### Data Classes

#### LiquidityMetrics
Comprehensive liquidity metrics snapshot.

**Attributes:**
```python
timestamp: datetime
bid_ask_spread_bps: float  # Current spread in basis points
quoted_depth: Decimal  # Total depth at best bid/ask
effective_spread_bps: float  # Effective spread for trade size
depth_slope: float  # Slope of order book
liquidity_score: float  # Composite 0-100 score
liquidity_regime: str  # HIGH/NORMAL/LOW/POOR
```

**Methods:**
- `to_dict() -> Dict` - Convert to dictionary

#### SpreadDecomposition
Decomposition of bid-ask spread into components.

**Attributes:**
```python
timestamp: datetime
total_spread_bps: float
order_processing_bps: float  # Fixed costs portion
inventory_holding_bps: float  # Inventory risk portion
adverse_selection_bps: float  # Information asymmetry portion
dominant_component: SpreadComponent  # Largest component
```

**Methods:**
- `to_dict() -> dict` - Convert to dictionary

#### DepthProfile
Market depth profile at multiple price levels.

**Attributes:**
```python
timestamp: datetime
bid_levels: List[Tuple[Decimal, Decimal]]  # (price, cumulative_volume)
ask_levels: List[Tuple[Decimal, Decimal]]
total_bid_depth: Decimal
total_ask_depth: Decimal
imbalance_ratio: float  # (bid - ask) / (bid + ask)
```

**Methods:**
- `to_dict() -> dict` - Convert to dictionary

#### LiquidityRisk
Liquidity risk assessment.

**Attributes:**
```python
timestamp: datetime
liquidity_gap: Decimal  # Available - Required depth
execution_shortfall_risk: float  # Probability of not executing
market_impact_estimate: float  # Expected bps impact
risk_level: str  # HIGH/MEDIUM/LOW
recommendations: List[str]
```

**Methods:**
- `to_dict() -> dict` - Convert to dictionary

### Main Classes

#### LiquidityAnalyzer
Analyzes market depth and liquidity characteristics (O'Hara Chapter 5).

**Constructor:**
```python
__init__(lookback_periods: int = 20, depth_levels: int = 5)
```

**Key Methods:**

**measure_market_depth(order_book, target_size) -> DepthProfile**
Calculates depth profile for order book at multiple levels.

**calculate_liquidity_score(spread_bps, depth, volatility, volume) -> float**
Composite score (0-100) with weights:
- Tightness: 30% (inverse of spread)
- Depth: 30% (log scale)
- Immediacy: 20% (volume-based)
- Resilience: 20% (inverse of volatility)

**classify_liquidity_regime(liquidity_score) -> str**
Classification:
- HIGH: score >= 80
- NORMAL: score >= 60
- LOW: score >= 40
- POOR: score < 40

**decompose_spread(spread_bps, price_variance, order_flow_imbalance, volume, volatility) -> SpreadDecomposition**
Stoll (2000) decomposition:
```
Order Processing = spread * 0.35
Inventory Holding = min(spread * 0.4, vol * sqrt(var) * 10000)
Adverse Selection = spread * |OFI| * 0.5 * min(1, 100000/volume)
Normalize to sum to total spread
```

**calculate_effective_spread(execution_price, bid_price, ask_price, side) -> float**
Effective spread measures actual execution cost:
```
BUY: 2 * (execution - midpoint) / midpoint
SELL: 2 * (midpoint - execution) / midpoint
Return in bps (* 10000)
```

**measure_market_resilience(price_history, shock_times, recovery_window_seconds) -> float**
Speed of recovery from shocks (O'Hara 5.4):
- Find pre-shock reference price
- Find time when price returns to within 1% of reference
- Score = 100 - avg_recovery_time (higher = faster)

**assess_liquidity_risk(required_size, available_depth, volatility, avg_daily_volume, urgency) -> LiquidityRisk**
Risk assessment with Almgren-Chriss market impact:
```
participation_rate = required_size / avg_daily_volume
market_impact = volatility * sqrt(participation_rate) * 10000
shortfall_risk = (1 - depth_ratio) * (1 + volatility * 10)
```

**calculate_liquidity_metrics(symbol, order_book, price_history, volume, target_size) -> LiquidityMetrics**
Main entry point for comprehensive analysis.

**generate_liquidity_report(symbol, order_book, price_history, volume, required_size) -> dict**
Complete liquidity analysis with all metrics and recommendations.

**get_liquidity_trend() -> str**
Trend analysis from historical metrics:
- IMPROVING: recent avg > older avg * 1.05
- DETERIORATING: recent avg < older avg * 0.95
- STABLE: within 5%

#### LiquidityMonitor
Monitors liquidity conditions in real-time with alerts.

**Constructor:**
```python
__init__(liquidity_threshold: float = 50.0, alert_window_minutes: int = 5)
```

**Key Methods:**

**check_liquidity_alert(current_metrics) -> Optional[dict]**
Checks alert conditions:
- Liquidity score < threshold (HIGH if < 30, MEDIUM if < 50)
- Bid-ask spread > 10 bps

Returns alert dict or None if no alerts.

### Convenience Functions

**get_liquidity_analyzer(lookback_periods=20, depth_levels=5) -> LiquidityAnalyzer**
Singleton pattern for analyzer instance.

**get_liquidity_monitor(liquidity_threshold=50.0, alert_window_minutes=5) -> LiquidityMonitor**
Singleton pattern for monitor instance.

## Business Logic

### Liquidity Score Formula
```python
tightness_score = max(0, 100 - spread_bps * 2)
depth_score = min(100, log1p(depth / 1000) * 20)
volume_score = min(100, log1p(volume / 10000) * 15)
resilience_score = max(0, 100 - volatility * 500)

composite = (
    tightness_score * 0.30 +
    depth_score * 0.30 +
    volume_score * 0.20 +
    resilience_score * 0.20
)
```

### Spread Decomposition Logic
Based on Stoll (2000) three-component model:
1. Order processing: Fixed operational costs
2. Inventory holding: Risk premium for position risk
3. Adverse selection: Cost of informed traders

Components are scaled to sum to total spread.

### Effective Spread Logic
Measures actual execution cost vs midpoint:
- Buy: Pay more than midpoint (adverse)
- Sell: Receive less than midpoint (adverse)
- Returns in basis points for comparability

### Market Resilience Logic
Measures how quickly prices recover after shocks:
1. Identify shock times (provided by caller)
2. Measure time to return to within 1% of pre-shock level
3. Faster recovery = higher resilience score

### Liquidity Risk Logic
Combines multiple risk factors:
1. Liquidity gap (required - available)
2. Execution shortfall risk (probability based on depth ratio)
3. Market impact (Almgren-Chriss model)

Risk levels:
- HIGH: shortfall_risk > 0.5 or gap > 50% of required
- MEDIUM: shortfall_risk > 0.2 or gap > 20% of required
- LOW: otherwise

## Data Models

### Input Data Structures
```python
order_book: Dict[str, List[Tuple[Decimal, Decimal]]]
{
    'bids': [(price1, size1), (price2, size2), ...],  # Descending price
    'asks': [(price1, size1), (price2, size2), ...]   # Ascending price
}

price_history: pd.DataFrame
# Index: datetime
# Columns: ['close', ...]

target_size: Decimal  # Size to calculate depth for
```

### Output Data Structures
All data classes have `to_dict()` method returning serializable dictionaries with string keys and primitive values.

## API Contracts

### LiquidityAnalyzer.calculate_liquidity_metrics()
**Purpose:** Main entry point for liquidity analysis

**Args:**
- `symbol`: str - Trading symbol
- `order_book`: Dict[str, List[Tuple[Decimal, Decimal]]] - Current order book
- `price_history`: pd.DataFrame - Historical prices
- `volume`: float - Current volume
- `target_size`: Optional[Decimal] - Target size for effective spread

**Returns:**
- `LiquidityMetrics` object

**Raises:**
- ValueError: Invalid input data
- KeyError: Missing order book data

### LiquidityAnalyzer.generate_liquidity_report()
**Purpose:** Complete liquidity analysis with recommendations

**Args:**
- `symbol`: str - Trading symbol
- `order_book`: Dict - Current order book
- `price_history`: pd.DataFrame - Price history
- `volume`: float - Trading volume
- `required_size`: Optional[Decimal] - Size for risk assessment

**Returns:**
```python
{
    'symbol': str,
    'timestamp': str,
    'metrics': Dict,  # From LiquidityMetrics.to_dict()
    'depth_profile': Dict,  # From DepthProfile.to_dict()
    'spread_decomposition': Dict,  # From SpreadDecomposition.to_dict()
    'liquidity_risk': Dict,  # From LiquidityRisk.to_dict()
    'trend': str,  # 'IMPROVING', 'STABLE', 'DETERIORATING'
    'recommendations': List[str]
}
```

### LiquidityMonitor.check_liquidity_alert()
**Purpose:** Check for liquidity alerts

**Args:**
- `current_metrics`: LiquidityMetrics - Current metrics

**Returns:**
- `Optional[Dict]` - Alert dict or None

**Alert Structure:**
```python
{
    'type': str,  # 'LOW_LIQUIDITY', 'WIDE_SPREAD'
    'severity': str,  # 'HIGH', 'MEDIUM'
    'message': str,
    'timestamp': str
}
```

## Error Handling

### Exception Handling Strategy
- **ValueError**: Invalid numerical inputs
- **TypeError**: Type conversion failures
- **KeyError**: Missing order book data
- **AttributeError**: Missing DataFrame columns

### Error Responses
- Return default values when data insufficient
- Return LiquidityMetrics with zero values when order book empty
- Return None from alerts when no conditions met

### Logging
- ERROR: Calculation failures with stack traces
- WARNING: Missing optional data
- INFO: Module initialization

## Performance Considerations

### Optimization Targets
- Order book processing: O(d) where d = depth_levels (default 5)
- Liquidity score: O(1) once inputs calculated
- Spread decomposition: O(1)
- Resilience measurement: O(s) where s = number of shocks

### Memory Efficiency
- Fixed-size history buffer (lookback_periods default 20)
- Deque would be more efficient but list used for simplicity
- No large intermediate allocations

### Computational Complexity
- measure_market_depth: O(d)
- calculate_liquidity_score: O(1)
- decompose_spread: O(1)
- measure_market_resilience: O(s * w) where w = recovery_window
- assess_liquidity_risk: O(1)
- generate_liquidity_report: O(d + s)

## Testing Strategy

### Unit Tests Required
1. **LiquidityMetrics**
   - Test data class initialization
   - Test to_dict() conversion
   - Test regime classification boundaries

2. **LiquidityAnalyzer**
   - Test measure_market_depth with synthetic order books
   - Test calculate_liquidity_score scoring formula
   - Test decompose_spread component calculations
   - Test assess_liquidity_risk risk levels
   - Test measure_market_resilience with synthetic shocks

3. **LiquidityMonitor**
   - Test alert triggering at thresholds
   - Test severity levels
   - Test multiple concurrent alerts

### Integration Tests Required
1. End-to-end liquidity report generation
2. Integration with real market data feeds
3. Alert triggering and handling workflow

### Edge Cases to Test
- Empty order book
- Single level order book
- Zero spread
- Zero volume
- Zero depth
- Empty price history
- No shock times for resilience

### Performance Tests
- Benchmark: measure_market_depth < 10ms
- Benchmark: calculate_liquidity_metrics < 50ms
- Benchmark: generate_liquidity_report < 100ms

## Security Considerations

### Input Validation
- Validate order book has non-empty bids/asks
- Validate prices > 0
- Validate sizes >= 0
- Validate spread_bps >= 0
- Validate volume >= 0

### Numerical Stability
- Handle zero depth in ratio calculations
- Handle zero total depth in imbalance calculation
- Handle zero variance in spread decomposition

### Output Sanitization
- Round floats to reasonable precision
- Ensure liquidity_score in [0, 100]
- Ensure regime in allowed values
- Ensure risk_level in allowed values

## Compliance

### Academic References
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 5-6
- Stoll, H.R. (2000) "Friction"
- Kyle, A.S. (1985) "Continuous Auctions and Insider Trading"
- Amihud, Y. & Mendelson, H. (1980) "Dealership Market"

### Documentation Requirements
- Liquidity measurement methodology
- Spread decomposition assumptions
- Market impact model documentation
- Alert threshold rationale

## Maintenance

### Version History
- v1.0.0: Initial implementation with O'Hara Chapters 5-6 concepts

### Module Information
All classes/functions exported via `__all__`:
```python
__all__ = [
    "LiquidityDimension",
    "SpreadComponent",
    "LiquidityMetrics",
    "SpreadDecomposition",
    "DepthProfile",
    "LiquidityRisk",
    "LiquidityAnalyzer",
    "LiquidityMonitor",
    "get_liquidity_analyzer",
    "get_liquidity_monitor",
]
```

### Future Enhancements
- Add intraday liquidity patterns
- Implement liquidity forecasting
- Add market impact optimization
- Implement liquidity-aware execution algorithms
- Add cross-asset liquidity analysis

---
*Requirements completed on 2026-02-07*
*GAP Audit Status: PASSED*
