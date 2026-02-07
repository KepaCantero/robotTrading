# Requirements: services/signal_scoring_engine.py

## Source File Analysis
- **File Path**: `app/services/signal_scoring_engine.py`
- **Lines of Code**: 429
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
Implements comprehensive signal scoring system with cooldown periods, compound scoring, priority ranking, and portfolio signal filtering. Prevents over-trading and ensures only high-quality signals are executed.

## Dependencies
- Internal:
  - `app.models.signal.Signal`, `SignalType` (Signal entities)
- External:
  - `logging` (Standard library logging)
  - `collections.defaultdict` (Data structures)
  - `datetime` (Time handling)
  - `typing` (Type hints)

## Classes/Functions

### Classes
- `SignalCooldownManager`: Manages cooldown periods per symbol to prevent over-trading
  - `set_cooldown(symbol, minutes)`: Set cooldown period
  - `is_in_cooldown(symbol)`: Check if symbol in cooldown
  - `reset_cooldown(symbol)`: Reset cooldown state

- `SignalCompoundScoreCalculator`: Calculates weighted compound scores
  - `calculate_compound_score(signal, metadata)`: Main scoring algorithm
  - Weights: confidence (30%), volume_ratio (25%), volatility (20%), liquidity (15%), timing (10%)

- `SignalPriorityRanker`: Ranks signals by priority
  - `get_priority(compound_score)`: Returns "high"/"medium"/"low"
  - `rank_signals(signals)`: Sorts signals by priority

- `PortfolioSignalFilter`: Filters conflicting signals
  - `filter_signals(signals, max_signals_per_symbol, filter_conflicts)`: Prevents contradictory positions

- `SignalScoringEngine`: Main orchestrator
  - `process_signals(signals, apply_cooldown)`: Complete scoring pipeline
  - `get_scoring_stats()`: Returns statistics

### Functions
- `get_signal_scoring_engine(cooldown_minutes)`: Singleton factory

## Business Logic

### Signal Scoring Pipeline
1. **Cooldown Check**: Prevents over-trading (configurable, default 10 min)
2. **Compound Scoring**: Multi-factor weighted score (0-100)
3. **Priority Ranking**: High (>80), Medium (50-80), Low (<50)
4. **Portfolio Filtering**: Removes conflicting signals
5. **Final Ranking**: Returns prioritized signal list

### Scoring Formula
```
compound_score = confidence * 0.30 + volume_ratio * 0.25 +
                 volatility * 0.20 + liquidity * 0.15 + timing * 0.10
```

## Data Models
- **Input**: `Signal` objects with confidence, liquidity_score, metadata
- **Output**: Enriched signals with `compound_score` and `priority` in metadata
- **State**: Cooldowns dict, custom_cooldowns dict, active_positions set

## API Contracts

### SignalScoringEngine.process_signals()
```python
def process_signals(
    signals: List[Signal],
    apply_cooldown: bool = True
) -> List[Signal]
```
- **Input**: Raw signals from strategies
- **Output**: Processed signals with scores, ranked by priority
- **Side Effects**: Sets cooldowns when enabled

## Error Handling
- Graceful handling of missing metadata (returns neutral values)
- Logging at debug/info levels for all operations
- No exceptions raised for invalid signals (filtered/logged)

## Performance Considerations
- O(n) complexity for signal processing
- Minimal memory overhead (dictionaries for tracking)
- Cooldown cleanup on expired entries

## Testing Strategy
- Unit tests for each calculator component
- Integration tests for full pipeline
- Edge cases: empty signals, missing metadata, all signals in cooldown
- Verify correct ranking and filtering behavior

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Full type coverage with modern syntax |
| Error Handling | ✅ PASS | Proper exception handling and logging |
| SOLID Principles | ✅ PASS | Single responsibility, dependency injection ready |
| Logging | ✅ PASS | Structured logging with appropriate levels |
| No Hardcoded Secrets | ✅ PASS | No secrets in code |
| Input Validation | ✅ PASS | Validates inputs, handles missing data |
| Async Patterns | ✅ PASS | N/A - synchronous module |
| Documentation | ✅ PASS | Comprehensive docstrings |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
