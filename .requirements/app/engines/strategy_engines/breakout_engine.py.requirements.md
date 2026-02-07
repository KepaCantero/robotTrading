# Requirements: engines/strategy_engines/breakout_engine.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/breakout_engine.py`
- **Lines of Code**: 461
- **Status**: AUDITED - PASSED
- **Audit Date**: 2026-02-07T10:00:00Z

## Purpose
Breakout detection strategy engine. Identifies range breakouts (support/resistance) with volume confirmation. Features:
- Configurable lookback window for range definition
- Percentage threshold for breakout confirmation
- Volume ratio confirmation (vs. average recent volume)
- Liquidity score and priority score metrics
- Integration with Learning Engines via BaseStrategyEngine

## Dependencies
- Internal:
  - `app.core.centralized_config.get_strategy_config`, `get_trading_threshold` - Configuration management
  - `app.models.market_data.Quote` - Market data model
  - `app.models.portfolio.Portfolio` - Portfolio model
  - `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType` - Signal models
  - `app.services.momentum_analysis.TechnicalIndicatorCalculator` - Technical indicators
  - `.base.BaseStrategyEngine` - Parent class
- External:
  - `logging` - Standard logging
  - `collections.deque` - Efficient rolling window storage
  - `decimal.Decimal` - Precise financial calculations
  - `typing` (Any, Dict, List, Optional, Sequence) - Type hints

## Classes/Functions

### Classes
- `BreakoutStrategyEngine(BaseStrategyEngine)` - Breakout detection strategy

### Abstract Methods Implemented
- `get_strategy_type()` - Returns "breakout"
- `extract_features(market_data, historical_data)` - Extract features for Learning Engine
- `_generate_signals_impl(market_data)` - Generate breakout signals

### Public Methods
- `__init__(config)` - Initialize with strategy parameters
- `get_required_parameters()` - Return list of required config parameters
- `risk_check(signal, portfolio)` - Validate risk criteria

### Private Methods
- `_calculate_breakout_confidence(current_price, range_high, range_low, volume_ratio, direction)` - Calculate signal confidence
- `_map_confidence_to_strength(confidence)` - Map confidence to SignalStrength enum

## Business Logic
1. **Range Detection**: Calculate high/low range over lookback_period
2. **Breakout Detection**: Price exceeds range ± threshold percentage
3. **Volume Confirmation**: Volume ratio >= min_volume_ratio
4. **Confidence Calculation**: Based on distance beyond range + volume strength
5. **Risk Management**: Max exposure limit, min signal confidence

## Data Models
- **Signal Metadata**:
  - `breakout_direction`: "up" or "down"
  - `range_high`, `range_low`, `range_width`: Range metrics
  - `breakout_level`: Price level that triggered breakout
  - `volume_ratio`: Current volume / average volume
  - `lookback_period`: Lookback window size
  - `breakout_threshold_pct`: Threshold percentage

## API Contracts
- **Input**: `Quote` object with market data
- **Output**: `List[Signal]` with BUY/SELL signals

## Configuration Parameters
- `lookback_period`: Period for range calculation (default: 20)
- `breakout_threshold_pct`: Breakout threshold as fraction (default: 0.01 = 1%)
- `min_volume_ratio`: Minimum volume ratio required (default: 1.5)
- `max_exposure`: Maximum portfolio exposure (default: 0.60)
- `min_signal_confidence`: Minimum confidence for risk_check (default: 60.0)
- `stop_loss`, `take_profit`, `max_position_size`: From YAML config

## Error Handling
- Specific exceptions caught: `ValueError`, `TypeError`, `KeyError`, `AttributeError`
- All exceptions logged with `exc_info=True`
- Returns empty list on error

## Performance Considerations
- Uses deque for O(1) append/pop with maxlen
- Efficient sliding window calculations
- ATR calculation only when needed

## Testing Strategy
- Unit tests for breakout detection logic
- Integration tests with mock market data
- Edge cases: Insufficient history, zero price, zero volume
- Test confidence calculation and strength mapping

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
- **Status**: MINOR NOTE - Uses legacy `Optional[T]` syntax instead of modern `T | None`
- **Priority**: P2 (Medium)
- **Impact**: Non-critical - Code is fully functional with Python 3.9+ compatible syntax
- **Recommendation**: Consider migrating to `T | None` for modern Python 3.10+ codebases

### R101: No Print in Production
- **Status**: PASS - No print() statements found
- **Priority**: P0

### R104: No Bare Except
- **Status**: PASS - All except clauses specify exception types
- **Lines**: 76, 364
- **Pattern**: `except (ValueError, TypeError, KeyError, AttributeError)` or similar

### R105: Proper Exception Handling
- **Status**: PASS - Specific exceptions with proper logging
- **Pattern**: All exceptions logged with `logger.error(..., exc_info=True)`

### R108: No Hardcoded Values
- **Status**: PASS - All values configurable via config dict or YAML
- **Note**: Historical constants (0.01, 1.5, 0.60, 60.0) are documented defaults

### R110: Google-Style Docstrings
- **Status**: PASS - Comprehensive docstrings (Spanish language)
- **Coverage**: All public methods documented

### R111: No Circular Imports
- **Status**: PASS - No circular dependencies detected

### CFG-001: Pydantic Settings
- **Status**: PASS - Uses centralized_config for type-safe config

### TRD-002: Risk Validation
- **Status**: PASS - Implements risk_check() with exposure and confidence limits

### TRD-003: Position Limits
- **Status**: PASS - max_position_size from YAML config

### TRD-004: Audit Trail
- **Status**: PASS - Signal metadata includes strategy parameters

### LOG-004: Error Logging
- **Status**: PASS - All exceptions logged with stack traces
- **Lines**: 365

### LOG-005: No Sensitive Data in Logs
- **Status**: PASS - No sensitive data logged

### CC-006: Explicit Error Handling
- **Status**: PASS - Specific exceptions raised/caught

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07T10:00:00Z
**Auditor:** Claude Code (GAP Audit Automation)
**GAPs Found:** 0 critical, 0 P1, 1 P2 (minor)
**Notes:** File fully complies with BASE_RULES. Minor P2 note about legacy type hint syntax (non-critical).

All BASE_RULES verified. File has been analyzed against BASE_RULES.md:
- SEC-001 to SEC-010: PASS (No hardcoded secrets, proper audit logging)
- LOG-004: PASS (Error logging with stack traces)
- LOG-005: PASS (No sensitive data in logs)
- TRD-002: PASS (Risk validation via risk_check)
- TRD-003: PASS (Position limits from config)
- TRD-004: PASS (Audit trail in signal metadata)
- CFG-001: PASS (Pydantic settings via centralized_config)
- R104: PASS (No bare except clauses)
- R105: PASS (Proper exception handling)
- R108: PASS (No hardcoded values - all configurable)
- R110: PASS (Google-style docstrings)
- R111: PASS (No circular imports)
- CC-006: PASS (Explicit error handling)

Code is production-ready. Minor type hint style note is non-critical.
