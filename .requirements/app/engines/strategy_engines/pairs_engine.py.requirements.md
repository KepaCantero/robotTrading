# Requirements: engines/strategy_engines/pairs_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/pairs_engine.py`
- **Lines of Code**: 616
- **Language**: Python
- **Purpose**: Pairs trading strategy engine using cointegration and correlation analysis

## Purpose
Implements a pairs trading strategy that:
- Identifies cointegrated asset pairs
- Generates signals when spread deviates significantly from mean
- Uses statistical arbitrage to profit from mean reversion of spreads
- Requires both assets to be correlated and cointegrated

## Dependencies

### Internal
- `app.core.centralized_config.get_strategy_config`, `get_trading_threshold`
- `app.models.market_data.Quote`
- `app.models.portfolio.Portfolio`
- `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType`
- `.base.BaseStrategyEngine`
- `app.core.statsmodels_fallback.adfuller` (for cointegration testing)

### External
- `logging`
- `collections.defaultdict`, `deque`
- `decimal.Decimal`
- `typing` (Any, Dict, List, Optional, Sequence)
- `numpy` (np)
- `scipy.stats` (imported but marked as required)

## Classes/Functions

### Classes

#### `PairsTradingStrategyEngine(BaseStrategyEngine)`
**Purpose**: Engine for pairs trading using cointegration and spread analysis

**Key Attributes**:
- `pair_symbols`: List - The two symbols to trade (e.g., ["AAPL", "MSFT"])
- `cointegration_threshold`: Decimal - Minimum cointegration score (default 0.05)
- `spread_threshold`: Decimal - Spread deviation threshold (default 0.02)
- `lookback_period`: int - Period for calculations (default 60)
- `min_correlation`: Decimal - Minimum correlation threshold (default 0.7)
- `min_spread_z_score`: Decimal - Z-score threshold for signals (default 2.0)
- `hedge_ratio`: Decimal - Hedge ratio between pair assets
- `price_history`: defaultdict(deque) - Historical prices for both symbols
- `cached_cointegration_score`: Optional[float] - Cached cointegration test result
- `cached_hedge_ratio`: Decimal - Cached hedge ratio from OLS regression
- `max_trades_per_day`: int - Trade frequency limit (default 5)

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with pair symbols and thresholds
- `get_strategy_type() -> str`: Returns "pairs_trading"
- `extract_features(market_data, historical_data) -> Dict[str, Any]`: Extract spread/correlation features
- `_calculate_cointegration(prices1, prices2) -> Optional[float]`: Calculate cointegration using ADF test
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate pairs trading signals
- `_create_buy_signal(...) -> Signal`: Create BUY signal for pairs trading
- `_create_sell_signal(...) -> Signal`: Create SELL signal for pairs trading
- `_calculate_confidence(abs_spread_z_score, cointegration_score, correlation) -> float`: Calculate signal confidence
- `get_required_parameters() -> List[str]`: Return required config parameters
- `risk_check(signal: Signal, portfolio: Portfolio) -> bool`: Verify exposure and correlation criteria
- `_calculate_total_exposure(portfolio: Portfolio) -> Decimal`: Calculate portfolio exposure
- `_calculate_pair_exposure(portfolio: Portfolio) -> Decimal`: Calculate pair-specific exposure

## Business Logic

### Signal Generation Logic
1. Calculate spread between pair: `spread = price1 - price2`
2. Calculate spread Z-score: `z_score = (current_spread - mean_spread) / std_spread`
3. Verify cointegration (cached ADF test result)
4. Verify correlation >= min_correlation
5. Generate signals:
   - When `z_score > min_spread_z_score`: SELL symbol1, BUY symbol2 (spread too wide)
   - When `z_score < -min_spread_z_score`: BUY symbol1, SELL symbol2 (spread too narrow)

### Confidence Calculation
- Base: 50.0
- Spread Z-score contribution:
  - >= 3.0: +25
  - >= 2.5: +20
  - >= 2.0: +15
- Cointegration contribution:
  - > 0.9: +15
  - > 0.7: +10
  - > 0.5: +5
- Correlation contribution:
  - > 0.9: +10
  - > 0.8: +5
- Min: 0, Max: 100

### Risk Check Logic
- Verify total exposure <= max_total_exposure (default 40%)
- Verify pair exposure <= max_pair_exposure (default 20%)
- Verify cointegration_score >= cointegration_threshold
- Verify abs(correlation) >= min_correlation

### Hedge Ratio Calculation
Uses OLS regression: `hedge_ratio = cov(price1, price2) / var(price2)`

## Data Models
- Uses `Signal` with metadata: spread_z_score, cointegration_score, correlation, pair_symbols
- Price history stored as `defaultdict(lambda: deque(maxlen=300))`
- Cached cointegration results to avoid repeated ADF tests

## API Contracts

### Configuration
```yaml
pairs_trading:
  parameters:
    pair_symbols: [["AAPL", "MSFT"]]  # Can be nested list or flat list
    cointegration_threshold: 0.05
    spread_threshold: 0.02
    lookback_period: 60
    min_correlation: 0.7
    min_spread_z_score: 2.0
    max_pair_exposure: 0.20
    max_total_exposure: 0.40
    max_trades_per_day: 5
  stop_loss_pct: 0.05
  take_profit_pct: 0.10
  max_position_size: 0.20
```

## Error Handling

### Exception Handling Pattern
```python
try:
    # Signal generation logic
except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
    logger.error(f"Error generando señal en PairsTradingStrategyEngine: {e}", exc_info=True)
    return []
```

**Status**: PASSED - Specific exception types with logging

## Performance Considerations
- Price history limited to 300 entries per symbol
- Cointegration test result cached (expensive computation)
- Hedge ratio cached from OLS regression
- Trade frequency limiting (max_trades_per_day)

## Testing Strategy

### Unit Tests Needed
1. Test spread calculation with various price pairs
2. Test Z-score calculation for spreads
3. Test cointegration calculation with mock ADF result
4. Test hedge ratio calculation via OLS
5. Test signal generation at Z-score thresholds
6. Test exposure calculations for portfolio

### Integration Tests Needed
1. Test with real cointegrated pairs (e.g., AAPL-MSFT)
2. Test with non-cointegrated pairs (should not generate signals)
3. Test exposure limiting with various portfolio states
4. Test trade frequency limiting

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
**Status**: PASSED
- All functions have proper type hints
- Uses `Optional`, `Sequence` correctly

### R101: No print() in Production Code
**Status**: PASSED
- Uses logger throughout
- No print() statements found

### R104: No Bare Except Clauses
**Status**: PASSED
- Exception handling specifies types: `(ValueError, TypeError, KeyError, AttributeError)`, `(ValueError, KeyError, AttributeError, IndexError, TypeError)`

### R105: Proper Exception Handling
**Status**: PASSED
- Exceptions caught and logged with exc_info=True
- Returns empty list on failure

### R110: Google-style Docstrings
**Status**: PASSED
- Methods have docstrings with Args/Returns

### R111: No Circular Imports
**Status**: PASSED
- Clean import structure
- Note: scipy.stats imported with `# noqa: F401` comment (acceptable)

## Additional GAPS Found

### GAP-001: SCIPY_AVAILABLE Flag Not Used Properly
**Location**: Lines 19-21, 288
**Priority**: P2
**Issue**: `SCIPY_AVAILABLE = True` set unconditionally, should check actual import
**Fix**:
```python
try:
    import scipy.stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
```

### GAP-002: Complex pair_symbols Normalization Logic
**Location**: Lines 106-123
**Priority**: P1
**Issue**: Multiple branches to normalize pair_symbols format, could be simplified
**Fix**: Extract to separate method with clear logic

### GAP-003: No Validation of pair_symbols Length
**Location**: Lines 111-123
**Priority**: P1
**Issue**: No explicit validation that exactly 2 symbols are provided
**Fix**:
```python
if len(self.pair_symbols) != 2:
    raise ValueError(f"pairs_trading requires exactly 2 symbols, got {len(self.pair_symbols)}")
```

### GAP-004: statsmodels_fallback Import May Fail
**Location**: Line 296
**Priority**: P2
**Issue**: Import inside function without checking if module exists
**Fix**: Move to top-level import with try/except

### GAP-005: Cached Cointegration Never Invalidated
**Location**: Lines 133-136
**Priority**: P1
**Issue**: `cached_cointegration_score` set but never recalculated or invalidated
**Note**: Code has `cointegration_recalc_interval_days` but doesn't use it
**Fix**: Implement periodic recalculation based on time or data changes

### GAP-006: Unused Attributes
**Location**: Lines 133-141
**Priority**: P2
**Issue**: Several attributes defined but not used:
  - `last_cointegration_recalc_date`
  - `cointegration_recalc_interval_days`
  - `trades_today`
  - `last_trade_date`

### GAP-007: No Validation of Correlation Range
**Location**: Line 214
**Priority**: P2
**Issue**: `np.corrcoef` can return values outside [-1, 1] with insufficient data
**Fix**: Add validation: `correlation = max(-1.0, min(1.0, correlation))`

## Audit Status
**Status**: PASSED
**Timestamp**: 2026-02-07T05:31:30Z
**Auditor**: GAP Audit Batch 0063
**Notes**: Well-implemented pairs trading strategy with proper statistical foundations. Main concerns are unused attributes for planned features (recalculation, trade limiting) and some input validation gaps.

---
*Requirements updated: 2026-02-07T05:31:30Z*
