# liquidity.py

## Purpose
Market depth and liquidity analysis module implementing O'Hara's "Market Microstructure Theory" (Chapters 5-6) concepts for measuring liquidity dimensions, spread decomposition, and liquidity risk assessment.

---

## Type Definitions / Data Classes

### LiquidityMetrics Class/DataClass
```python
@dataclass
class LiquidityMetrics:
    timestamp: datetime                      # REQUIRED - Measurement time
    bid_ask_spread_bps: float               # REQUIRED - Spread in basis points
    quoted_depth: Decimal                   # REQUIRED - Total depth at best bid/ask
    effective_spread_bps: float             # REQUIRED - Effective spread for trade size
    depth_slope: float                      # REQUIRED - Slope of order book
    liquidity_score: float                  # REQUIRED - Composite liquidity score (0-100)
    liquidity_regime: str                   # REQUIRED - Classification (HIGH/NORMAL/LOW/POOR)
```

**Validation Rules:**
- `liquidity_score` must be between 0 and 100
- `bid_ask_spread_bps` must be non-negative
- `quoted_depth` must be positive (Decimal > 0)
- `liquidity_regime` must be one of: 'HIGH', 'NORMAL', 'LOW', 'POOR', 'UNKNOWN'

### SpreadDecomposition Class/DataClass
```python
@dataclass
class SpreadDecomposition:
    timestamp: datetime                      # REQUIRED - Decomposition time
    total_spread_bps: float                 # REQUIRED - Total spread
    order_processing_bps: float             # REQUIRED - Fixed costs portion
    inventory_holding_bps: float            # REQUIRED - Inventory risk portion
    adverse_selection_bps: float            # REQUIRED - Information asymmetry portion
    dominant_component: SpreadComponent     # REQUIRED - Largest component enum
```

**Validation Rules:**
- Component values must sum to `total_spread_bps` (within rounding tolerance)
- All spread values must be non-negative
- `dominant_component` must be valid SpreadComponent enum value

### DepthProfile Class/DataClass
```python
@dataclass
class DepthProfile:
    timestamp: datetime                                    # REQUIRED - Profile time
    bid_levels: List[Tuple[Decimal, Decimal]]             # REQUIRED - (price, cumulative_volume) for bids
    ask_levels: List[Tuple[Decimal, Decimal]]             # REQUIRED - (price, cumulative_volume) for asks
    total_bid_depth: Decimal                              # REQUIRED - Total volume on bid side
    total_ask_depth: Decimal                              # REQUIRED - Total volume on ask side
    imbalance_ratio: float                                # REQUIRED - Ratio of bid to ask depth
```

**Validation Rules:**
- `bid_levels` and `ask_levels` must have same length (or one may be empty)
- `imbalance_ratio` must be between -1 and +1
- All Decimal values must be positive

### LiquidityRisk Class/DataClass
```python
@dataclass
class LiquidityRisk:
    timestamp: datetime                      # REQUIRED - Assessment time
    liquidity_gap: Decimal                  # REQUIRED - Gap between available and needed liquidity
    execution_shortfall_risk: float         # REQUIRED - Probability of execution failure (0-1)
    market_impact_estimate: float           # REQUIRED - Estimated market impact in bps
    risk_level: str                         # REQUIRED - Risk classification (LOW/MEDIUM/HIGH)
    recommendations: List[str]              # REQUIRED - List of risk recommendations
```

**Validation Rules:**
- `execution_shortfall_risk` must be between 0 and 1
- `liquidity_gap` must be non-negative
- `risk_level` must be one of: 'LOW', 'MEDIUM', 'HIGH'

---

## Function Signatures (Contracts)

### `LiquidityAnalyzer.__init__(lookback_periods: int = 20, depth_levels: int = 5) -> None`
**Pre:** lookback_periods > 0, depth_levels > 0
**Post:** Analyzer initialized with empty historical metrics
**Raises:** ValueError if parameters are non-positive
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.measure_market_depth(order_book: Dict[str, List[Tuple[Decimal, Decimal]]], target_size: Optional[Decimal] = None) -> DepthProfile`
**Pre:** order_book contains 'bids' and 'asks' keys with valid data
**Post:** Returns DepthProfile with cumulative depth calculations
**Raises:** ValueError if order_book is empty or malformed
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.calculate_liquidity_score(spread_bps: float, depth: Decimal, volatility: float, volume: float) -> float`
**Pre:** spread_bps >= 0, depth > 0, volatility >= 0, volume >= 0
**Post:** Returns score between 0 and 100
**Raises:** Returns 0 for invalid inputs
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.classify_liquidity_regime(liquidity_score: float) -> str`
**Pre:** 0 <= liquidity_score <= 100
**Post:** Returns 'HIGH', 'NORMAL', 'LOW', or 'POOR'
**Raises:** ValueError if score out of range
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.decompose_spread(spread_bps: float, price_variance: float, order_flow_imbalance: float, volume: float, volatility: float) -> SpreadDecomposition`
**Pre:** spread_bps > 0, all floats valid
**Post:** Components sum to total_spread_bps (within tolerance)
**Raises:** ValueError if spread_bps <= 0
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.calculate_effective_spread(execution_price: float, bid_price: float, ask_price: float, side: str) -> float`
**Pre:** execution_price, bid_price, ask_price > 0, side in ['BUY', 'SELL']
**Post:** Returns effective spread in basis points
**Raises:** ValueError if prices invalid or side unknown
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.measure_market_resilience(price_history: pd.DataFrame, shock_times: List[datetime], recovery_window_seconds: int = 60) -> float`
**Pre:** price_history has datetime index, shock_times not empty
**Post:** Returns resilience score 0-100 (higher = faster recovery)
**Raises:** Returns 0.0 if insufficient data
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.assess_liquidity_risk(required_size: Decimal, available_depth: Decimal, volatility: float, average_daily_volume: float, urgency: str = 'NORMAL') -> LiquidityRisk`
**Pre:** required_size > 0, available_depth >= 0, urgency in ['LOW', 'NORMAL', 'HIGH']
**Post:** Returns LiquidityRisk with gap calculation and recommendations
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `LiquidityAnalyzer.calculate_liquidity_metrics(symbol: str, order_book: Dict, price_history: pd.DataFrame, volume: float, target_size: Optional[Decimal] = None) -> LiquidityMetrics`
**Pre:** order_book valid, price_history has 'close' column
**Post:** Returns LiquidityMetrics, stores in history
**Raises:** Returns default metrics if insufficient data
**Retry:** No
**Side Effects:** Stores metrics in _historical_metrics list

### `LiquidityAnalyzer.generate_liquidity_report(symbol: str, order_book: Dict, price_history: pd.DataFrame, volume: float, required_size: Optional[Decimal] = None) -> Dict`
**Pre:** All inputs valid
**Post:** Returns comprehensive report dictionary
**Raises:** Returns partial report on errors
**Retry:** No
**Side Effects:** None

### `get_liquidity_analyzer(lookback_periods: int = 20, depth_levels: int = 5) -> LiquidityAnalyzer`
**Pre:** lookback_periods > 0, depth_levels > 0
**Post:** Returns singleton LiquidityAnalyzer instance
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates singleton if not exists

---

## Acceptance Criteria
- [ ] AC-LIQ-001: All dataclass fields have type hints (verify with mypy --strict)
- [ ] AC-LIQ-002: All public methods have docstrings with Args/Returns/Raises
- [ ] AC-LIQ-003: Liquidity_score always returns 0-100 range (test boundary values)
- [ ] AC-LIQ-004: Spread components sum to total within 0.01% tolerance
- [ ] AC-LIQ-005: Decimal precision maintained for all monetary/size values
- [ ] AC-LIQ-006: Empty order_book returns default metrics (not exception)
- [ ] AC-LIQ-007: All enums have explicit values documented
- [ ] AC-LIQ-008: _historical_metrics respects lookback_periods limit

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | 05-architecture.md | Domain layer has no framework dependencies | ✅ OK - Pure Python dataclasses |
| TYP-001 | 02-type-hints.md | 100% type coverage on all functions | ✅ OK - All functions typed |
| SOL-001 | 03-solid-principles.md | Single Responsibility per class | ✅ OK - LiquidityAnalyzer focused on liquidity |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ⚠️ NOT APPLIED - No logging in current code |
| TRD-001 | Trading rules | Validate numerical inputs (prices, volumes) | ⚠️ PARTIAL - Some validation missing |
| QL-001 | Code quality | Cyclomatic complexity < 10 per function | ✅ OK - Functions are simple |
| CC-002 | Clean code | No code duplication | ⚠️ GAP - depth_slope calc duplicated in _calculate_depth_slope |
| FMT-007 | Formatting | No mutable defaults | ✅ OK - Uses None for optionals |
| SEC-007 | Security | Input validation at boundaries | ⚠️ GAP - No validation on order_book structure |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas (data science), decimal (precision)
- **Internal:** None (pure domain module)

---

## Required Tests
- **tests/microstructure/test_liquidity.py:**
  - Test LiquidityMetrics dataclass validation
  - Test calculate_liquidity_score with edge cases (0 depth, extreme volatility)
  - Test decompose_spread component normalization
  - Test measure_market_depth with empty order_book
  - Test assess_liquidity_risk recommendations generation
  - Test _calculate_effective_spread_for_size walks order book correctly
  - Test classify_liquidity_regime boundary conditions (59.99, 60.0)
  - Test singleton behavior of get_liquidity_analyzer
  - Test _historical_metrics size limit enforcement
  - Test measure_market_resilience with no shock_times

---

## Notes
- Implements Stoll (2000) spread decomposition into order processing, inventory holding, and adverse selection
- Market resilience measures recovery speed from shocks (O'Hara 5.4)
- Liquidity score uses weighted dimensions: tightness (30%), depth (30%), immediacy (20%), resilience (20%)
- Critical trading risk assessment: HIGH risk when shortfall_risk > 0.5 or gap > 50% of required size
