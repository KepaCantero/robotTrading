# Requirements: engines/strategy_engines/mean_reversion_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/mean_reversion_engine.py`
- **Lines of Code**: 426
- **Language**: Python
- **Purpose**: Mean reversion strategy engine using Z-score analysis

## Purpose
Implements a mean reversion strategy that:
- Uses Z-score to detect overbought/oversold conditions
- Generates BUY signals when price is significantly below mean
- Generates SELL signals when price is significantly above mean
- Requires volatility to be within controlled range

## Dependencies

### Internal
- `app.core.centralized_config.get_strategy_config`, `get_trading_threshold`
- `app.models.market_data.Quote`
- `app.models.portfolio.Portfolio`
- `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType`
- `app.services.momentum_analysis.TechnicalIndicatorCalculator`
- `.base.BaseStrategyEngine`

### External
- `logging`
- `collections.deque`
- `decimal.Decimal`
- `typing` (Any, Dict, List, Optional, Sequence)
- `pandas` (pd) - for rolling statistics

## Classes/Functions

### Classes

#### `MeanReversionStrategyEngine(BaseStrategyEngine)`
**Purpose**: Engine for mean reversion trading strategy

**Key Attributes**:
- `z_score_threshold`: Decimal - Z-score threshold for signal generation (default 2.0)
- `lookback_period`: int - Period for rolling mean/std calculation (default 20)
- `volatility_threshold`: Decimal - Max volatility for signals (default 0.02)
- `mean_reversion_speed`: Decimal - Speed of mean reversion
- `atr_floor`: Decimal - Minimum ATR value
- `price_range_multiplier`: Decimal - Multiplier for price range analysis
- `min_z_score`: Decimal - Minimum Z-score for signal (default 1.5)
- `price_history`: deque - Historical prices (maxlen 200)
- `indicator_calculator`: TechnicalIndicatorCalculator

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with config from YAML or defaults
- `get_strategy_type() -> str`: Returns "mean_reversion"
- `extract_features(market_data, historical_data) -> Dict[str, Any]`: Extract Z-score features for ML
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate mean reversion signals
- `_calculate_confidence(abs_z_score, volatility, is_oversold) -> float`: Calculate signal confidence
- `get_required_parameters() -> List[str]`: Return required config parameters
- `risk_check(signal: Signal, portfolio: Portfolio) -> bool`: Verify risk criteria

## Business Logic

### Signal Generation Logic
1. Calculate Z-score: `z_score = (price - mean) / std`
2. BUY condition:
   - `z_score <= -z_score_threshold` (price significantly below mean)
   - `z_score <= -min_z_score` (minimum threshold)
   - `volatility <= volatility_threshold` (controlled volatility)
3. SELL condition:
   - `z_score >= z_score_threshold` (price significantly above mean)
   - `volatility <= volatility_threshold` (controlled volatility)

### Confidence Calculation
- Base confidence: 50.0
- Z-score contribution:
  - >= 3.0: +30
  - >= 2.5: +25
  - >= 2.0: +20
  - >= 1.5: +15
- Volatility contribution (lower is better for mean reversion):
  - < 0.01: +10
  - < 0.02: +5
- Min: 0, Max: 100

### Risk Check Logic
- Verify confidence >= min_signal_confidence (default 50.0)
- Verify volatility <= volatility_threshold * 2 (allow up to 2x threshold)

## Data Models
- Uses `Signal` with metadata: z_score, mean, std, volatility, price_mean_distance
- Uses `Quote` for market data
- Uses `Portfolio` for risk checks

## API Contracts

### Configuration
```yaml
mean_reversion:
  parameters:
    z_score_threshold: 2.0
    lookback_period: 20
    volatility_threshold: 0.02
    min_z_score: 1.5
  stop_loss_pct: 0.05
  take_profit_pct: 0.10
  max_position_size: 0.20
```

## Error Handling

### Exception Handling Pattern
```python
try:
    # Signal generation logic
except (ValueError, TypeError, KeyError, AttributeError) as e:
    logger.error(f"Error generando señal en MeanReversionStrategyEngine: {e}", exc_info=True)
```

**Status**: PASSED - Specific exception types caught with logging

## Performance Considerations
- Price history limited to 200 entries
- Uses pandas rolling calculations for efficiency
- Early return when insufficient historical data

## Testing Strategy

### Unit Tests Needed
1. Test Z-score calculation with various price histories
2. Test signal generation at Z-score thresholds
3. Test confidence calculation with different Z-score/volatility combinations
4. Test risk check with varying confidence and volatility levels

### Integration Tests Needed
1. Test with real market data feed
2. Test interaction with portfolio management
3. Test performance in different market regimes (ranging vs trending)

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
**Status**: PASSED
- All functions have proper type hints
- Uses `Optional`, `Sequence` correctly

### R101: No print() in Production Code
**Status**: PASSED
- Uses `logger.info`, `logger.debug`, `logger.error`
- No print() statements found

### R104: No Bare Except Clauses
**Status**: PASSED
- Exception handling specifies types: `(ValueError, TypeError, KeyError, AttributeError)`

### R105: Proper Exception Handling
**Status**: PASSED
- Exceptions logged with `exc_info=True`
- Returns empty list on failure (graceful degradation)

### R110: Google-style Docstrings
**Status**: PASSED
- Methods have docstrings with Args/Returns
- Spanish comments but clear documentation

### R111: No Circular Imports
**Status**: PASSED
- Clean import structure
- Uses `.base.BaseStrategyEngine` relative import

## Additional GAPS Found

### GAP-001: Duplicate Import of pandas Inside Function
**Location**: Lines 146, 238
**Priority**: P2
**Issue**: `import pandas as pd` inside functions (`extract_features`, `_generate_signals_impl`)
**Fix**: Move to top of file with other imports

### GAP-002: Logging Messages in Spanish
**Location**: Throughout file
**Priority**: P3
**Issue**: Log messages in Spanish mix with English codebase
**Note**: Not a functional issue but may impact international collaboration

### GAP-003: Inconsistent Decimal Conversion
**Location**: Lines 50-83
**Priority**: P2
**Issue**: Extensive use of `Decimal(str(value))` pattern
**Fix**: Could use a utility function for safer conversion

### GAP-004: No Validation of lookback_period
**Location**: Line 51, 70
**Priority**: P1
**Issue**: No validation that lookback_period is positive and reasonable
**Fix**:
```python
self.lookback_period = params.get("lookback_period", 20)
if self.lookback_period <= 0 or self.lookback_period > 500:
    raise ValueError(f"lookback_period must be between 1 and 500, got {self.lookback_period}")
```

### GAP-005: Magic Numbers in Confidence Calculation
**Location**: Lines 372-385
**Priority**: P2
**Issue**: Hardcoded values (30, 25, 20, 15, 10, 5) not well documented
**Fix**: Extract to named constants or document in class docstring

## Audit Status
**Status**: PASSED
**Timestamp**: 2026-02-07T05:30:30Z
**Auditor**: GAP Audit Batch 0063
**Notes**: Well-structured strategy engine with proper type hints and error handling. Minor issues with pandas import location and some hardcoded values.

---
*Requirements updated: 2026-02-07T05:30:30Z*
