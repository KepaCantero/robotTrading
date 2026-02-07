# Requirements: services/strategy_recommender/strategy_recommender.py

## Source File Analysis
- **File Path**: `app/services/strategy_recommender/strategy_recommender.py`
- **Lines of Code**: 433
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
Recommends trading strategies based on objective-driven scoring. Uses different weight combinations for investment objectives (maximize capital, dividends, preservation, balanced growth, income).

## Dependencies
- Internal:
  - `.models.*` (StrategyRecommender data models)
- External:
  - `logging` (Standard library)
  - `datetime`, `decimal`, `typing` (Standard library)

## Classes/Functions

### Classes
- `StrategyRecommender`: Main recommendation engine
  - `recommend(request)`: Generate strategy recommendation
  - `get_recommendation_history(limit)`: Historical recommendations
  - `get_recommender_status()`: Operational statistics

### Functions
- `get_strategy_recommender()`: Singleton factory

## Business Logic

### Objective Weights
- **maximizar_capital**: Sharpe 60%, Return 30%, Sortino 10%
- **maximizar_dividendos**: Dividend 50%, Sharpe 30%, Preservation 20%
- **capital_preservation**: Drawdown inverse 50%, Sharpe 40%, Return 10%
- **balanced_growth**: Sharpe 40%, Return 30%, Drawdown 30%
- **income_generation**: Dividend 50%, Consistency 30%, Sharpe 20%

### Score Thresholds
- **STRONG_BUY**: >= 85
- **BUY**: >= 70
- **HOLD**: >= 50
- **REVIEW**: >= 30
- **NOT_RECOMMENDED**: < 30

### Normalization Targets
- Sharpe ratio: 1.5+ → 100 points
- Annual return: 15%+ → 100 points
- Max drawdown: <10% → 100 points (inverse scoring)
- Sortino ratio: 2.0+ → 100 points
- Dividend yield: 4%+ → 100 points
- Win rate: 55%+ → 100 points

## Data Models
- **StrategyRecommendationRequest**: Input metrics
- **StrategyRecommendation**: Output with score, status, suggestions
- **ObjectiveWeights**: Weight configuration per objective
- **StrategyScore**: Component score with contribution

## API Contracts

### StrategyRecommender.recommend()
```python
async def recommend(
    request: StrategyRecommendationRequest,
) -> StrategyRecommendation
```

## Error Handling
- Catches ValueError, TypeError, KeyError, AttributeError
- Returns failed recommendation with error_message
- Comprehensive logging of all operations

## Performance Considerations
- O(1) recommendation calculation
- In-memory history storage
- Minimal computational overhead

## Testing Strategy
- Unit tests for each objective's scoring
- Edge cases: missing metrics, zero values, extreme values
- Verify weight normalization
- Test suggestion generation logic

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Full type coverage with Optional, Dict, List |
| Error Handling | ✅ PASS | Comprehensive exception catching |
| SOLID Principles | ✅ PASS | Single responsibility - recommendation only |
| Logging | ✅ PASS | Info/error logging with emojis (acceptable) |
| No Hardcoded Secrets | ✅ PASS | No secrets in code |
| Input Validation | ✅ PASS | Handles None values gracefully |
| Async Patterns | ✅ PASS | Proper async/await usage |
| Documentation | ✅ PASS | Comprehensive docstrings |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
