# Requirements: engines/strategy_engines/modular_momentum_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/modular_momentum_engine.py`
- **Lines of Code**: 632
- **Language**: Python
- **Purpose**: Modular momentum strategy with configurable filters

## Purpose
Implements a modular momentum strategy engine that:
- Uses multiple technical filters (EMA, RSI, StochRSI, Momentum, Volume, ATR)
- Supports presets (balanced, aggressive, conservative)
- Integrates with Learning Engines for adaptive thresholds
- Analyzes market context (trending, ranging, volatile)

## Dependencies

### Internal
- `app.models.market_data.Quote`
- `app.models.portfolio.Portfolio`
- `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType`
- `app.services.momentum_analysis.TechnicalIndicatorCalculator`
- `app.strategies.momentum_modular.modules.filters` (EMAFilter, RSIFilter, etc.)
- `app.strategies.momentum_modular.modules.market_analyzer.MarketAnalyzer`
- `.base.BaseStrategyEngine`

### External
- `logging`
- `collections.deque`
- `datetime`
- `decimal.Decimal`
- `typing` (Any, Dict, List, Optional, Sequence)

## Classes/Functions

### Classes

#### `ModularMomentumStrategyEngine(BaseStrategyEngine)`
**Purpose**: Modular momentum strategy with configurable filter combination

**Key Attributes**:
- `preset`: str - Configuration preset (balanced, aggressive, conservative)
- `filters`: List - Active filter instances
- `combination_mode`: str - Filter combination mode (ALL, MAJORITY, ANY)
- `market_analyzer`: MarketAnalyzer or None (if using ContextEngine)
- `price_history`, `high_history`, `low_history`, `volume_history`, `atr_history`: deques
- `min_success_probability`: float - Minimum confidence threshold
- `learning_config`: Dict or None - Learning engine configuration

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with preset and filters
- `get_strategy_type() -> str`: Returns "modular_momentum"
- `extract_features(market_data, historical_data) -> Dict[str, Any]`: Extract features for ML
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate momentum signals
- `_get_market_context(market_data: Quote) -> Dict[str, Any]`: Get market regime/context
- `_calculate_indicators() -> Dict[str, Any]`: Calculate all technical indicators
- `_evaluate_filters(indicators, market_context) -> Dict`: Evaluate all active filters
- `_determine_signal_type(filter_results, market_context) -> Optional[SignalType]`: Determine signal from filter results
- `_calculate_signal_confidence(filter_results, learning_prediction) -> float`: Calculate confidence
- `get_required_parameters() -> List[str]`: Return required config parameters
- `risk_check(signal: Signal, portfolio: Portfolio) -> bool`: Verify risk criteria
- `apply_learning_adjustments(prediction, signal) -> Signal`: Apply ML adjustments

## Business Logic

### Signal Generation Flow
1. Update historical data (price, high, low, volume)
2. Calculate technical indicators (RSI, EMA, Momentum, Volume, ATR)
3. Analyze market context (using ContextEngine or MarketAnalyzer)
4. Evaluate all active filters for BUY/SELL conditions
5. Determine signal type based on combination mode:
   - ALL: All filters must pass
   - MAJORITY: >50% of filters must pass
   - ANY: At least one filter must pass
6. Calculate confidence from filter results
7. Apply learning adjustments if available

### Filter Evaluation
Each filter returns:
```python
{
    'passed': bool,
    'confidence': float,
    'reason': str
}
```

### Confidence Calculation
- Base: Average confidence from all filters
- If learning prediction available: 60% filters + 40% learning
- Range: 0-100

### Risk Check Logic
- Verify confidence >= min_success_probability * 100
- If learning engine available: reject if action is HOLD

## Data Models
- Uses `Signal` with metadata: indicators, market_context, filter_results, preset
- Filter results dict structure
- Market context dict with: type, confidence, volatility_regime, trend_strength

## API Contracts

### Configuration Structure
```yaml
modular_momentum:
  preset: "balanced"
  presets:
    balanced:
      min_confidence: 0.6
      combination_mode: "MAJORITY"
  modules:
    ema_filter:
      enabled: true
      # filter-specific config
    rsi_filter:
      enabled: true
    # ... other filters
  adaptive_learning:
    enabled: true
    engine_type: "supervised"
```

## Error Handling

### Exception Handling Pattern
```python
try:
    # Feature extraction or signal generation
except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
    logger.warning/f"Error...: {e}")
    # Return empty dict or list
```

**Status**: PASSED - Specific exception types with logging

## Performance Considerations
- All history deques have maxlen (200 for prices/volumes, 100 for ATR)
- Lazy initialization of FeatureExtractor
- Fallback to minimal context if MarketAnalyzer fails
- Early return when insufficient historical data (min 60 bars)

## Testing Strategy

### Unit Tests Needed
1. Test each filter evaluation independently
2. Test combination modes (ALL, MAJORITY, ANY)
3. Test confidence calculation with various filter results
4. Test market context detection
5. Test learning adjustment application

### Integration Tests Needed
1. Test full signal generation with real market data
2. Test preset configurations
3. Test ContextEngine vs MarketAnalyzer fallback
4. Test learning engine integration

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
**Status**: PASSED
- All functions have proper type hints
- Uses `Optional`, `Sequence` correctly

### R101: No print() in Production Code
**Status**: PASSED
- Uses logger throughout
- Has some emoji in logs (✅, ❌) which is acceptable

### R104: No Bare Except Clauses
**Status**: PASSED
- Exception handling specifies types: `(ValueError, KeyError, AttributeError, IndexError, TypeError)`

### R105: Proper Exception Handling
**Status**: PASSED
- Exceptions caught and logged
- Graceful fallback to empty results

### R110: Google-style Docstrings
**Status**: PASSED
- Methods have docstrings with Args/Returns

### R111: No Circular Imports
**Status**: PASSED
- Clean import structure
- Lazy import of FeatureExtractor to avoid circular dependency

## Additional GAPS Found

### GAP-001: Lazy Import with Broad Exception Handling
**Location**: Lines 153-162
**Priority**: P2
**Issue**: Lazy import catches 5 exception types which may hide actual import errors
**Fix**: Consider separating ImportError from other errors

### GAP-002: Emoji in Log Messages
**Location**: Lines 90, 126, 128, 490, 510, 516, 522, 527
**Priority**: P3
**Issue**: Uses emoji (✅, ❌) in log messages
**Note**: Not a functional issue but may not render correctly in all log aggregators

### GAP-003: Fallback Market Context Returns Different Structure
**Location**: Lines 376-383
**Priority**: P2
**Issue**: Minimal fallback doesn't match full context structure exactly
**Fix**: Ensure all context keys are present in fallback

### GAP-004: No Validation of preset Value
**Location**: Line 59
**Priority**: P1
**Issue**: No validation that preset exists in presets_config
**Fix**:
```python
self.preset = config.get("preset", "balanced")
if self.preset not in self.presets_config:
    logger.warning(f"Unknown preset '{self.preset}', using defaults")
    self.current_preset = {}
```

### GAP-005: Complex Combination Logic Could Be Extracted
**Location**: Lines 508-529
**Priority**: P2
**Issue**: Signal determination logic is somewhat complex
**Fix**: Consider extracting to separate method with clearer structure

### GAP-006: Unused Variable in _calculate_indicators
**Location**: Lines 432-438
**Priority**: P2
**Issue**: Atr percentile calculation could fail silently if atr not in sorted_atr
**Fix**: Add explicit check or use alternative method

## Audit Status
**Status**: PASSED
**Timestamp**: 2026-02-07T05:31:00Z
**Auditor**: GAP Audit Batch 0063
**Notes**: Well-designed modular architecture with good separation of concerns. The filter system is flexible and extensible. Minor issues with validation and error handling granularity.

---
*Requirements updated: 2026-02-07T05:31:00Z*
