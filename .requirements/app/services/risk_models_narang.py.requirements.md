# Requirements: services/risk_models_narang.py

## Source File Analysis
- **File Path**: `app/services/risk_models_narang.py`
- **Lines of Code**: 616
- **Language**: Python 3
- **Purpose**: Implements Rushikesh (Ricky) Narang's eight rules of trend following

## Purpose
Implementation of Ricky Narang's trend following risk framework from "The Trend Following Bible":
- Rule 1: Volatility is the friend of the trend follower
- Rule 2: Capture the bulk of the trend
- Rule 3: Let profits run, cut losses short
- Rule 4: Risk management is key
- Rule 5: Diversification reduces risk
- Rule 6: Don't predict, react
- Rule 7: Avoid correlation pitfalls
- Rule 8: Psychology matters

## Dependencies
- **Internal**:
  - None (standalone risk model)
- **External**:
  - `pandas` - Data manipulation
  - `numpy` - Numerical computing
  - `typing` - Type hints
  - `logging` - Logging
  - `dataclasses` - Data structures

## Classes/Functions

### NarangRiskModel
- **Purpose**: Implements Narang's 8 rules
- **Key Methods**:
  - `calculate_volatility_adjustment()` - Rule 1: Volatility scaling
  - `calculate_trend_capture_score()` - Rule 2: Trend capture efficiency
  - `calculate_risk_reward_ratio()` - Rule 3: Risk/reward optimization
  - `validate_position_size()` - Rule 4: Position sizing
  - `calculate_diversification_score()` - Rule 5: Diversification metric
  - `generate_trend_signals()` - Rule 6: Reactive trend following
  - `check_correlation_limits()` - Rule 7: Correlation monitoring
  - `assess_psychology_drift()` - Rule 8: Psychology monitoring

### NarangMetrics (dataclass)
- Volatility-adjusted returns
- Trend capture ratio
- Risk/reward ratio
- Diversification score
- Correlation metrics

## Business Logic

### Rule 1: Volatility Scaling
- Adjust position sizes based on volatility
- Higher volatility = smaller positions
- Uses ATR or standard deviation

### Rule 2: Trend Capture
- Measure how much of trend captured
- Compare entry/exit to trend start/end
- Target: Capture 60-70% of trend

### Rule 3: Risk/Reward
- Minimum 2:1 reward/risk ratio
- Trailing stops to let profits run
- Fixed initial stop loss

### Rule 4: Position Sizing
- Maximum 2% risk per trade
- Sector concentration limits
- Portfolio-level risk limits

### Rule 5: Diversification
- Minimum 10 uncorrelated positions
- Maximum 20% per sector
- Correlation matrix monitoring

### Rule 6: Reactive Signals
- Don't predict, react to price
- Use moving averages, breakouts
- No fundamental predictions

### Rule 7: Correlation Limits
- Maximum 0.7 correlation between positions
- Hedge highly correlated positions
- Dynamic correlation monitoring

### Rule 8: Psychology
- Monitor for emotional trading
- Track deviation from strategy
- Alert on pattern changes

## Data Models
- NarangMetrics - All calculated metrics
- NarangSignal - Trading signal with confidence
- NarangReport - Comprehensive report

## API Contracts
```python
def calculate_narang_metrics(
    returns: pd.Series,
    positions: pd.DataFrame,
    trades: List[Dict]
) -> NarangMetrics

def generate_narang_report(
    metrics: NarangMetrics,
    rules_checked: List[int]
) -> NarangReport
```

## Error Handling
- Validates input data
- Handles missing data
- Catches calculation errors

## Performance Considerations
- O(n^2) for correlation calculations
- Efficient pandas operations
- Caching for repeated calculations

## Testing Strategy
- Test each rule independently
- Test full metric calculation
- Test with sample trend following data

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used
- FMT-007: No mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-005: Dataclasses fully typed

### Clean Code
- CC-001: Descriptive names following rule numbers
- CC-006: Error handling
- CC-007: Functions reasonable length

### Security
- SEC-007: Input validation on DataFrames

## Audit Status
**Status**: PASSED

### Strengths
1. Well-structured implementation of Narang's framework
2. Clear mapping to 8 rules
3. Comprehensive type hints
4. Good use of dataclasses
5. Proper error handling
6. All 8 rules implemented

### Minor Observations
1. Could add more documentation on Narang's methodology
2. Some calculations could benefit from more comments

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready risk model
- Well-documented framework

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0080*
*Status: PASSED*
