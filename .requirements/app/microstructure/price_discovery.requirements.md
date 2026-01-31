# price_discovery.py

## Purpose
Price discovery and information aggregation module implementing O'Hara's "Market Microstructure Theory" (Chapters 7-8) concepts for efficient price estimation, information flow analysis, and market efficiency testing.

---

## Type Definitions / Data Classes

### PriceDiscoveryMetrics Class/DataClass
```python
@dataclass
class PriceDiscoveryMetrics:
    timestamp: datetime                      # REQUIRED - Measurement time
    information_share: float                 # REQUIRED - Hasbrouck information share (0-1)
    price_adjustment_speed: float            # REQUIRED - Speed of price adjustment
    pricing_error: float                     # REQUIRED - Deviation from efficient price
    discovery_quality_score: float           # REQUIRED - Composite score (0-100)
    efficiency_level: MarketEfficiency       # REQUIRED - Market efficiency classification
```

**Validation Rules:**
- `information_share` must be between 0 and 1
- `discovery_quality_score` must be between 0 and 100
- `pricing_error` can be negative (observed - efficient)
- `efficiency_level` must be valid MarketEfficiency enum

### EfficientPriceEstimate Class/DataClass
```python
@dataclass
class EfficientPriceEstimate:
    timestamp: datetime                                  # REQUIRED - Estimate time
    observed_price: Decimal                             # REQUIRED - Current market price
    efficient_price: Decimal                            # REQUIRED - Estimated efficient price
    pricing_error: Decimal                              # REQUIRED - Difference (observed - efficient)
    confidence_interval: Tuple[Decimal, Decimal]        # REQUIRED - (lower, upper) 95% CI
    estimation_method: str                              # REQUIRED - Method identifier
```

**Validation Rules:**
- All Decimal values must be positive
- `confidence_interval[0]` <= `efficient_price` <= `confidence_interval[1]`
- `estimation_method` must be one of: 'ROLL', 'HASBROUCK', 'KYLE'

### InformationFlowMetrics Class/DataClass
```python
@dataclass
class InformationFlowMetrics:
    timestamp: datetime                      # REQUIRED - Measurement time
    information_content: float               # REQUIRED - Information content of trades (0-1)
    price_impact: float                     # REQUIRED - Average price impact per trade
    flow_persistence: float                 # REQUIRED - Autocorrelation of signed flow
    information_decay_rate: float            # REQUIRED - Decay rate (0-1)
```

**Validation Rules:**
- `information_content` must be between 0 and 1
- `flow_persistence` must be between 0 and 1
- `information_decay_rate` must be between 0 and 1
- `price_impact` must be non-negative

### MarketIntegrationMetrics Class/DataClass
```python
@dataclass
class MarketIntegrationMetrics:
    timestamp: datetime                      # REQUIRED - Measurement time
    cointegration_coefficient: float         # REQUIRED - Cointegration beta coefficient
    information_share: float                 # REQUIRED - Contribution to discovery (0-1)
    lead_lag_relationship: float            # REQUIRED - Positive if leads, negative if lags
    price_convergence_rate: float           # REQUIRED - Speed of convergence
```

**Validation Rules:**
- `information_share` must be between 0 and 1
- `lead_lag_relationship` range: -1 to +1
- All floats must be finite (no NaN/Inf)

---

## Function Signatures (Contracts)

### `PriceDiscoveryAnalyzer.__init__(lookback_periods: int = 100, min_observations: int = 30) -> None`
**Pre:** lookback_periods > 0, min_observations > 0
**Post:** Analyzer initialized with empty error history
**Raises:** ValueError if parameters <= 0
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.estimate_efficient_price_roll(price_history: pd.DataFrame) -> EfficientPriceEstimate`
**Pre:** price_history has 'close' column, len >= 2
**Post:** Returns estimate with Roll model (bid-ask bounce adjustment)
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.calculate_information_share_hasbrouck(price_series: pd.Series, trade_series: pd.Series) -> float`
**Pre:** Both series aligned, len >= min_observations
**Post:** Returns information share 0-1
**Raises:** Returns 0.5 if insufficient data
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.measure_price_adjustment_speed(price_history: pd.DataFrame, event_times: List[datetime], adjustment_window_seconds: int = 300) -> float`
**Pre:** price_history has datetime index, event_times not empty
**Post:** Returns speed score 0-100 (higher = faster adjustment)
**Raises:** Returns 0.0 if no valid events
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.calculate_pricing_error(observed_prices: pd.Series, fundamental_value: float) -> Tuple[float, float]`
**Pre:** observed_prices not empty, fundamental_value > 0
**Post:** Returns (mean_error, std_error) as percentages
**Raises:** Returns (0.0, 0.0) if invalid input
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.test_market_efficiency(price_history: pd.DataFrame) -> MarketEfficiency`
**Pre:** price_history has 'close' column, len >= 30
**Post:** Returns efficiency classification
**Raises:** Returns INEFFICIENT if insufficient data
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.analyze_information_flow(price_history: pd.DataFrame, trade_data: pd.DataFrame) -> InformationFlowMetrics`
**Pre:** price_history has 'close', trade_data has ['timestamp', 'side', 'size', 'price']
**Post:** Returns flow metrics with correlations
**Raises:** Returns zero metrics if trade_data empty
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.compare_markets_price_discovery(market1_prices: pd.Series, market2_prices: pd.Series) -> MarketIntegrationMetrics`
**Pre:** Both series have same length/index
**Post:** Returns cointegration and lead-lag analysis
**Raises:** Returns defaults on cointegration test failure
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.calculate_discovery_quality_score(information_share: float, adjustment_speed: float, pricing_error: float, efficiency_level: MarketEfficiency) -> float`
**Pre:** 0 <= information_share <= 1, all floats finite
**Post:** Returns score 0-100
**Raises:** Clamps to [0, 100] range
**Retry:** No
**Side Effects:** None

### `PriceDiscoveryAnalyzer.generate_price_discovery_report(symbol: str, price_history: pd.DataFrame, trade_data: Optional[pd.DataFrame] = None) -> Dict`
**Pre:** price_history valid, symbol non-empty
**Post:** Returns comprehensive report dictionary
**Raises:** Returns partial report on errors
**Retry:** No
**Side Effects:** None

### `get_price_discovery_analyzer(lookback_periods: int = 100, min_observations: int = 30) -> PriceDiscoveryAnalyzer`
**Pre:** lookback_periods > 0, min_observations > 0
**Post:** Returns singleton instance
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates singleton if not exists

---

## Acceptance Criteria
- [ ] AC-PD-001: All dataclasses have __post_init__ or field validators
- [ ] AC-PD-002: Cointegration test fallback uses scipy (no statsmodels dependency required)
- [ ] AC-PD-003: information_share always clamped to [0, 1]
- [ ] AC-PD-004: Empty trade_data returns zero metrics (not exceptions)
- [ ] AC-PD-005: discovery_quality_score maximum is 100 (test extreme inputs)
- [ ] AC-PD-006: All time series operations handle index alignment
- [ ] AC-PD-007: MarketEfficiency enum values documented with theory
- [ ] AC-PD-008: Confidence interval ordering (lower <= value <= upper)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | 05-architecture.md | Domain layer has no framework dependencies | ✅ OK - Pure Python |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK - All functions typed |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Focused on price discovery |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ NOT APPLIED - No logging |
| TRD-003 | Trading rules | Validate statistical test assumptions | ⚠️ GAP - No validation of normality |
| QL-001 | Code quality | Complexity < 10 | ✅ OK - Functions focused |
| CC-006 | Clean code | Explicit error handling | ⚠️ GAP - Generic Exception catch |
| ASYNC-001 | Async patterns | No blocking in async functions | ⚠️ NOT APPLIED - No async |
| SEC-007 | Security | Input validation for DataFrames | ⚠️ GAP - No column validation |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas, scipy (fallback for statsmodels)
- **Internal:** None (pure domain module)

---

## Required Tests
- **tests/microstructure/test_price_discovery.py:**
  - Test estimate_efficient_price_roll with bid-ask bounce
  - Test cointegration fallback with scipy implementation
  - Test measure_price_adjustment_speed with synthetic shocks
  - Test test_market_efficiency classification boundaries
  - Test analyze_information_flow correlation calculations
  - Test compare_markets_price_discovery cointegration
  - Test calculate_discovery_quality_score weighting
  - Test generate_price_discovery_report structure
  - Test empty DataFrames return defaults (not exceptions)
  - Test singleton behavior

---

## Notes
- Implements Hasbrouck (1991) information share for price discovery contribution
- Roll (1984) efficient price model accounts for bid-ask bounce in observed prices
- Fallback cointegration test uses scipy when statsmodels unavailable
- Market efficiency tests: autocorrelation, variance ratio, runs test
- Price adjustment speed measures time to reach 95% of total move after information events
