# Requirements: engines/strategy_engines/ensemble.py

## Source File Analysis
- **File Path**: `app/engines/strategy_engines/ensemble.py`
- **Lines of Code**: 747
- **Language**: Python
- **Purpose**: Strategy ensemble system for combining multiple strategy signals

## Purpose
Implements ensemble methods to combine signals from multiple strategy engines:
- **WeightedEnsemble**: Combines signals with dynamic weights based on performance
- **RegimeBasedSelector**: Selects strategies based on market regime detection
- **VotingEnsemble**: Combines signals via majority voting

## Dependencies

### Internal
- `app.models.market_data.Quote`
- `app.models.signal.Signal`, `SignalSource`, `SignalStrength`, `SignalType`
- `.base.BaseStrategyEngine`

### External
- `logging`
- `abc` (abstractmethod)
- `collections` (defaultdict)
- `datetime`
- `decimal.Decimal`
- `typing` (Any, Dict, List, Optional, Sequence, Tuple)
- `numpy` (np)

## Classes/Functions

### Classes

#### `BaseStrategyEnsemble(BaseStrategyEngine)`
**Purpose**: Abstract base class for strategy ensembles

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize ensemble with strategies dict and weights
- `add_strategy(name: str, strategy: BaseStrategyEngine, weight: float = 1.0)`: Add strategy to ensemble
- `remove_strategy(name: str) -> bool`: Remove strategy from ensemble
- `extract_features(market_data, historical_data) -> Dict[str, Any]`: Extract combined features from all strategies
- `risk_check(signal: Signal, portfolio: Any) -> bool`: Verify risk criteria
- `update_strategy_performance(strategy_name: str, metrics: Dict[str, float])`: Track performance history
- `_combine_signals(strategy_signals, market_data) -> List[Signal]`: Abstract method for signal combination

#### `WeightedEnsemble(BaseStrategyEnsemble)`
**Purpose**: Combine signals using performance-based dynamic weights

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with weight parameters
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate weighted combined signals
- `_combine_signals(strategy_signals, market_data) -> List[Signal]`: Combine by weighted confidence
- `_update_weights() -> None`: Update weights based on historical performance (sharpe, return, inverse_dd)
- `_map_confidence_to_strength(confidence: float) -> SignalStrength`: Static confidence mapper

#### `RegimeBasedSelector(BaseStrategyEnsemble)`
**Purpose**: Select strategies based on detected market regime

**Key Attributes**:
- `REGIME_TRENDING_UP`, `REGIME_TRENDING_DOWN`, `REGIME_MEAN_REVERTING`, `REGIME_HIGH_VOLATILITY`, `REGIME_LOW_VOLATILITY`, `REGIME_UNKNOWN`

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with regime detection parameters
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate signals from regime-selected strategies
- `_detect_regime() -> None`: Detect current market regime using volatility and slope analysis
- `_select_strategies_for_regime() -> List[str]`: Get appropriate strategies for current regime
- `_combine_signals(strategy_signals, market_data) -> List[Signal]`: Combine selected strategy signals
- `get_current_regime() -> Tuple[str, float]`: Get current regime and confidence

#### `VotingEnsemble(BaseStrategyEnsemble)`
**Purpose**: Combine signals via majority voting

**Key Methods**:
- `__init__(config: Dict[str, Any])`: Initialize with voting parameters
- `_generate_signals_impl(market_data: Quote) -> List[Signal]`: Generate voting-based combined signals
- `_combine_signals(strategy_signals, market_data) -> List[Signal]`: Combine by majority vote
- `_map_confidence_to_strength(confidence: float) -> SignalStrength`: Static confidence mapper

## Business Logic

### Weighted Ensemble Logic
1. Collect signals from all strategies
2. Update weights every N signals (configurable)
3. Group signals by symbol and type
4. Calculate weighted confidence: `sum(s.confidence * weight) / sum(weights)`
5. Apply confidence boost for unanimous signals
6. Require minimum number of strategies for signal generation

### Regime Detection Logic
1. Maintain price history (configurable lookback, default 50)
2. Calculate returns and volatility (annualized)
3. Calculate normalized slope (linear regression)
4. Determine regime:
   - High volatility: volatility > threshold (2.5%)
   - Low volatility: volatility < threshold * 0.5
   - Trending up: normalized_slope > threshold (2%)
   - Trending down: normalized_slope < -threshold
   - Mean reverting: none of the above
5. Select strategies mapped to current regime

### Voting Ensemble Logic
1. Collect votes from all strategies
2. Group votes by symbol and signal type
3. Require minimum votes (configurable, default 2)
4. Optionally require majority (>50%)
5. Apply confidence boost for unanimous votes
6. Calculate average confidence from voting strategies

## Data Models
- Uses `Signal` from app.models.signal
- Uses `Quote` from app.models.market_data
- Performance history stored as `Dict[str, List[Dict[str, float]]]`

## API Contracts

### Public Interface
```python
# Add strategy to ensemble
ensemble.add_strategy("momentum", momentum_engine, weight=1.5)

# Remove strategy
ensemble.remove_strategy("momentum")

# Get current regime (RegimeBasedSelector only)
regime, confidence = selector.get_current_regime()
```

### Signal Combination Contract
All ensembles must implement `_combine_signals()` which:
- Takes `Dict[str, List[Signal]]` (strategy_name -> signals)
- Returns `List[Signal]` (combined signals)
- Must handle empty input gracefully
- Must set appropriate metadata (ensemble_type, contributing_strategies)

## Error Handling

### Exception Handling Pattern
```python
try:
    signals = strategy.generate_signals(market_data)
    strategy_signals[name] = signals
except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
    logger.warning(f"Error generating signals from {name}: {e}")
    strategy_signals[name] = []
```

**Gaps Found**:
- Exception handling is good - specific exception types caught
- Errors are logged with context
- Graceful fallback to empty list on failure

## Performance Considerations
- Weight updates occur every N signals (configurable) to avoid recalculation overhead
- Performance history limited to 100 entries per strategy
- Price history limited to `regime_lookback * 2` for regime detection
- NumPy used for efficient array operations in regime detection

## Testing Strategy

### Unit Tests Needed
1. **WeightedEnsemble**:
   - Test weight calculation with different performance metrics
   - Test signal combination with varying weights
   - Test weight decay application

2. **RegimeBasedSelector**:
   - Test regime detection with synthetic price data
   - Test strategy selection for each regime
   - Test confidence calculation for different regime strengths

3. **VotingEnsemble**:
   - Test majority voting logic
   - Test minimum votes requirement
   - Test unanimous boost application

### Integration Tests Needed
1. Test ensemble with multiple real strategy engines
2. Test signal combination across different market conditions
3. Test performance tracking and weight updates over time

## Critical Rules (BASE_RULES.md Compliance)

### R100: Modern Type Hints
**Status**: PARTIAL
- Most functions have type hints
- Missing return types on some methods (e.g., `add_strategy`, `remove_strategy`)
- `Optional` and `Sequence` used correctly

### R101: No print() in Production Code
**Status**: PASSED
- No print() statements found
- Uses `logger.info`, `logger.debug`, `logger.warning` appropriately

### R104: No Bare Except Clauses
**Status**: PASSED
- All except clauses specify exception types
- Pattern: `except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:`

### R105: Proper Exception Handling
**Status**: PASSED
- Exceptions caught and logged with context
- Graceful fallback (empty list) on failure
- Error propagation where appropriate

### R110: Google-style Docstrings
**Status**: PARTIAL
- Most methods have docstrings
- Docstrings include Args/Returns sections
- Some inline comments could be enhanced

### R111: No Circular Imports
**Status**: PASSED
- Imports are clean: `.base.BaseStrategyEngine`
- No circular import patterns detected

## Additional GAPS Found

### GAP-001: Missing Type Hints on Return Values
**Location**: Lines 64, 77
**Priority**: P2
**Issue**: `add_strategy()` and `remove_strategy()` missing return type hints
**Fix**:
```python
def add_strategy(self, name: str, strategy: BaseStrategyEngine, weight: float = 1.0) -> None:
def remove_strategy(self, name: str) -> bool:
```

### GAP-002: Incomplete Error Handling in _combine_signals
**Location**: Lines 267-340 (WeightedEnsemble)
**Priority**: P2
**Issue**: No try-except around signal combination logic
**Fix**: Add exception handling for signal creation failures

### GAP-003: Missing Validation in add_strategy
**Location**: Lines 64-75
**Priority**: P1
**Issue**: No validation that strategy is instance of BaseStrategyEngine
**Fix**:
```python
def add_strategy(self, name: str, strategy: BaseStrategyEngine, weight: float = 1.0) -> None:
    if not isinstance(strategy, BaseStrategyEngine):
        raise TypeError(f"strategy must be BaseStrategyEngine, got {type(strategy)}")
    if weight <= 0:
        raise ValueError(f"weight must be positive, got {weight}")
    # ... rest of method
```

### GAP-004: Hardcoded Defaults in Regime Detection
**Location**: Lines 436-439
**Priority**: P2
**Issue**: Magic numbers for thresholds (0.02, 0.025) not well documented
**Fix**: Extract to named constants with documentation

### GAP-005: No Input Validation on config Parameters
**Location**: Lines 41-60, 215-233
**Priority**: P1
**Issue**: No validation of config values (e.g., weight_decay, min_weight, max_weight ranges)
**Fix**: Add Pydantic validation or explicit checks

## Audit Status
**Status**: PASSED
**Timestamp**: 2026-02-07T05:30:00Z
**Auditor**: GAP Audit Batch 0063
**Notes**: Code is well-structured with good error handling. Minor improvements needed in type hints and input validation. No critical issues found.

---
*Requirements updated: 2026-02-07T05:30:00Z*
