# Requirements: engines/strategy_engines/trend_following_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/trend_following_engine.py`
- **Lines of Code**: 459
- **Language**: Python
- **Purpose**: Trend following strategy using ADX and MACD indicators

## Purpose
Implements a trend following strategy that:
- Uses ADX to detect strong trends (>25 threshold)
- Uses MACD crossovers for direction (bullish/bearish)
- Requires volume confirmation for signal generation
- Follows trends in both directions (long and short)

## Dependencies

### Internal
- `app.core.centralized_config.get_strategy_config`, `get_trading_threshold`
- `app.models.market_data.Quote`
- `app.models.portfolio.Portfolio`
- `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType`
- `app.services.momentum_analysis.TechnicalIndicatorCalculator`
- `app.services.signal_scoring_engine.get_signal_scoring_engine`
- `.base.BaseStrategyEngine`

### External
- `logging`
- `collections.deque`
- `decimal.Decimal`
- `typing` (Any, Dict, List, Optional, Sequence)

## Classes/Functions

### Classes

#### `TrendFollowingStrategyEngine(BaseStrategyEngine)`
**Purpose**: Engine for trend following using ADX and MACD

**Key Attributes**:
- `adx_period`: int - ADX calculation period (default 14)
- `adx_threshold`: Decimal - Minimum ADX for strong trend (default 25.0)
- `macd_fast_period`: int - MACD fast period (default 12)
- `macd_slow_period`: int - MACD slow period (default 26)
- `macd_signal_period`: int - MACD signal period (default 9)
- `macd_histogram_threshold`: Decimal - MACD histogram threshold (default 0.0)
- `min_volume_ratio`: Decimal - Minimum volume ratio for confirmation (default 1.2)
- `volume_lookback`: int - Volume average period (default 20)
- `max_exposure`: Decimal - Maximum portfolio exposure (default 0.60)
- `price_history`, `high_history`, `low_history`, `volume_history`: deques
- `indicator_calculator`: TechnicalIndicatorCalculator
- `signal_scorer`: Signal scoring engine instance

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with periods and thresholds
- `get_strategy_type() -> str`: Returns "trend_following"
- `extract_features(market_data, historical_data) -> Dict[str, Any]`: Extract ADX/MACD features
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate trend following signals
- `_calculate_confidence(adx, macd_histogram, volume_ratio) -> float`: Calculate signal confidence
- `get_required_parameters() -> List[str]`: Return required config parameters
- `risk_check(signal: Signal, portfolio: Optional[Portfolio]) -> bool`: Verify exposure and confidence

## Business Logic

### Signal Generation Logic

#### BUY Signal Conditions
1. `adx > adx_threshold` (strong trend present)
2. `macd_line > macd_signal` AND `macd_histogram > macd_histogram_threshold` (bullish crossover)
3. `volume_ratio >= min_volume_ratio` (volume confirmation)

#### SELL Signal Conditions
1. `adx > adx_threshold` (strong trend present)
2. `macd_line < macd_signal` AND `macd_histogram < -macd_histogram_threshold` (bearish crossover)
3. `volume_ratio >= min_volume_ratio` (volume confirmation)

### Confidence Calculation
- ADX contribution (max 40): `(adx / 50.0) * 40.0`
- MACD histogram contribution (max 30): `abs(histogram) * 10.0`
- Volume ratio contribution (max 30): `(volume_ratio - 1.0) * 15.0`
- Min: 0, Max: 100

### Risk Check Logic
- Check portfolio exposure (if available)
- Verify confidence >= 50.0 (hardcoded minimum)
- Verify total exposure < max_exposure

## Data Models
- Uses `Signal` with metadata: adx, macd_line, macd_signal, macd_histogram, volume_ratio
- History deques: maxlen=200 for price/high/low/volume

## API Contracts

### Configuration
```yaml
trend_following:
  parameters:
    adx_period: 14
    adx_threshold: 25.0
    macd_fast_period: 12
    macd_slow_period: 26
    macd_signal_period: 9
    macd_histogram_threshold: 0.0
    min_volume_ratio: 1.2
    volume_lookback: 20
    max_exposure: 0.60
  stop_loss_pct: 0.05
  take_profit_pct: 0.10
  max_position_size: 0.20
```

## Error Handling

### Exception Handling Pattern
```python
# In _generate_signals_impl
try:
    # Signal generation logic
except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
    logger.error(f"Error generando señal en TrendFollowingStrategyEngine: {e}", exc_info=True)

# In extract_features (MACD calculation)
try:
    macd_line, macd_signal, macd_histogram = self.indicator_calculator.calculate_macd(...)
except (TypeError, ValueError) as e:
    logger.debug(f"MACD calculation failed: {e}, using defaults")
    macd_line, macd_signal, macd_histogram = None, None, None

# In risk_check
try:
    # Risk check logic
except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
    logger.error(f"Error en risk_check: {e}", exc_info=True)
    return False
```

**Status**: PASSED - Specific exception types with appropriate logging

## Performance Considerations
- All history deques limited to 200 entries
- Early returns when insufficient data
- Graceful handling of None values from indicator calculations
- SignalScorer integration for additional scoring (though not used in current implementation)

## Testing Strategy

### Unit Tests Needed
1. Test ADX/MACD calculation with various price histories
2. Test signal generation at threshold boundaries
3. Test confidence calculation with different ADX/MACD/volume combinations
4. Test risk check with various portfolio exposures

### Integration Tests Needed
1. Test with trending market data (strong ADX)
2. Test with ranging market data (weak ADX) - should not generate signals
3. Test portfolio exposure limiting
4. Test volume confirmation logic

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
**Status**: PASSED
- All functions have proper type hints
- Uses `Optional` for portfolio parameter

### R101: No print() in Production Code
**Status**: PASSED
- Uses logger throughout
- No print() statements found

### R104: No Bare Except Clauses
**Status**: PASSED
- Exception handling specifies types

### R105: Proper Exception Handling
**Status**: PASSED
- Exceptions caught and logged appropriately
- Different error levels for different contexts (debug for MACD, error for signals)

### R110: Google-style Docstrings
**Status**: PASSED
- Methods have docstrings with Args/Returns

### R111: No Circular Imports
**Status**: PASSED
- Clean import structure

## Additional GAPS Found

### GAP-001: signal_scorer Initialized but Never Used
**Location**: Line 125
**Priority**: P2
**Issue**: `self.signal_scorer = get_signal_scoring_engine()` but never used in signal generation
**Fix**: Either use it for additional scoring or remove initialization

### GAP-002: Complex Config Update Logic
**Location**: Lines 59-67
**Priority**: P2
**Issue**: Tries to update both self.config and config dict, with broad exception handling
**Fix**: Simplify or document why both need updating

### GAP-003: No Validation of Period Parameters
**Location**: Lines 52-56, 93-102
**Priority**: P1
**Issue**: No validation that periods are positive and reasonable
**Fix**:
```python
if not (1 <= self.adx_period <= 100):
    raise ValueError(f"adx_period must be 1-100, got {self.adx_period}")
```

### GAP-004: Hardcoded Confidence Threshold in risk_check
**Location**: Line 450
**Priority**: P2
**Issue**: Magic number 50.0 hardcoded instead of using configurable value
**Fix**: Use `self.config.get("min_confidence", 50.0)`

### GAP-005: Inconsistent Type Hints on portfolio Parameter
**Location**: Line 424
**Priority**: P2
**Issue**: `portfolio: Optional[Portfolio] = None` in signature but doesn't match base class
**Note**: Base class likely requires non-Optional, check consistency

### GAP-006: MACD Calculation Wrapped in Try/Except While ADX is Not
**Location**: Lines 178-187 vs 262-264
**Priority**: P2
**Issue**: Inconsistent error handling between indicator calculations
**Fix**: Either wrap both in try/except or neither (for consistency)

## Audit Status
**Status**: PASSED
**Timestamp**: 2026-02-07T05:32:00Z
**Auditor**: GAP Audit Batch 0063
**Notes**: Well-implemented trend following strategy with proper indicator combination. Main issues are unused signal_scorer and some parameter validation gaps.

---
*Requirements updated: 2026-02-07T05:32:00Z*
