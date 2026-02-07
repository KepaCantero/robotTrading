# Requirements: services/risk_scaling/limit_adjuster.py

## Source File Analysis
- **File Path**: `app/services/risk_scaling/limit_adjuster.py`
- **Lines of Code**: 421
- **Language**: Python 3
- **Purpose**: Dynamic trading limit adjustment based on market/portfolio conditions

## Purpose
Manages dynamic adjustment of trading limits:
- Stop loss percentages
- Daily loss limits
- Position size limits
- Portfolio leverage limits
- Margin requirements
- Drawdown limits

## Dependencies
- **Internal**:
  - None (standalone limit manager)
- **External**:
  - `logging` - Structured logging
  - `dataclasses` - Data structures
  - `decimal.Decimal` - Financial precision
  - `typing` - Type hints

## Classes/Functions

### TradingLimits (dataclass)
- **Purpose**: Trading limits for position/portfolio
- **Fields**:
  - `stop_loss_pct`: Stop loss as % (e.g., 0.02 = 2%)
  - `daily_loss_limit`: Daily max loss in € or %
  - `max_position_size`: Max size for single position (€)
  - `max_portfolio_leverage`: Max leverage for portfolio
  - `min_margin_requirement`: Minimum margin (e.g., 0.25 = 25%)
  - `max_drawdown_limit`: Portfolio max drawdown before halt

### LimitAdjuster
- **Purpose**: Adjusts limits based on conditions
- **Key Methods**:
  - `get_base_limits()` - Default limits by capital tier
  - `adjust_limits_for_volatility()` - Volatility-based adjustment
  - `adjust_limits_for_drawdown()` - Drawdown-based adjustment
  - `calculate_dynamic_stop_loss()` - Risk-based stop loss
  - `is_within_daily_limit()` - Check daily loss limit
  - `is_within_leverage_limit()` - Check leverage limit
  - `is_within_position_size_limit()` - Check position size
  - `get_comprehensive_limits()` - All limits with adjustments

## Business Logic

### Default Limits by Capital Tier

| Tier   | Stop Loss | Daily Loss | Position | Leverage | Margin | Drawdown |
|--------|-----------|------------|----------|----------|--------|----------|
| Micro  | 2%        | 5%         | 10%      | 1.0x     | 50%    | 10%      |
| Small  | 2.5%      | 8%         | 15%      | 1.0x     | 33%    | 15%      |
| Medium | 3%        | 10%        | 20%      | 1.5x     | 25%    | 20%      |
| Large  | 3.5%      | 15%        | 25%      | 2.0x     | 20%    | 25%      |

### Volatility Multipliers
- very_low (vol < 0.7x avg): 1.2x (expand limits)
- low (0.7-0.9x): 1.1x
- normal (0.9-1.1x): 1.0x (baseline)
- high (1.1-1.5x): 0.8x (contract)
- extreme (> 1.5x): 0.5x (severe contraction)

### Drawdown Multipliers
- healthy (< 5%): 1.0x
- caution (5-10%): 0.8x
- warning (10-15%): 0.6x
- critical (15-20%): 0.3x
- halt (> 20%): 0.0x (stop trading)

### Dynamic Stop Loss Calculation
```python
max_loss = capital × risk_per_trade_pct × volatility_adjustment
price_distance = max_loss / position_size
stop_loss = entry_price - price_distance
```

## Data Models
- TradingLimits (dataclass) - All trading limits
- DEFAULT_LIMITS_BY_TIER - Default configurations
- VOLATILITY_MULTIPLIERS - Volatility adjustment table
- DRAWDOWN_MULTIPLIERS - Drawdown adjustment table

## API Contracts
```python
def get_comprehensive_limits(
    capital_tier: str,
    capital: Decimal,
    current_volatility: Decimal,
    average_volatility: Decimal,
    current_drawdown_pct: Decimal
) -> Dict[str, Any]
```

Returns:
```python
{
    "stop_loss_pct": Decimal,
    "daily_loss_limit_pct": Decimal,
    "max_position_pct": Decimal,
    "max_leverage": Decimal,
    "margin_requirement": Decimal,
    "max_drawdown_pct": Decimal,
    "daily_loss_limit_eur": Decimal,
    "max_position_eur": Decimal,
    "volatility_adjustment": str,
    "drawdown_adjustment": str
}
```

## Error Handling
- Validates division by zero (average_volatility)
- Validates positive values (capital, position_size)
- Handles edge cases (multiplier = 0)
- Logs warnings when limits exceeded

## Performance Considerations
- O(1) calculations
- No external dependencies
- Minimal memory footprint
- Singleton pattern via `get_limit_adjuster()`

## Testing Strategy
- Test limit calculations for each tier
- Test volatility adjustments
- Test drawdown adjustments
- Test stop loss calculations
- Test limit checks

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used
- FMT-007: No mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-005: Dataclass fields typed

### Design Patterns
- DP-005: Singleton pattern for global instance
- DP-003: Strategy pattern (tier-based strategies)

### Clean Code
- CC-001: Descriptive names
- CC-006: Error handling with validation
- CC-007: Functions reasonable length

### Security
- SEC-007: Input validation on Decimals
- No hardcoded secrets

### Logging
- LOG-001: Structured logging
- LOG-003: Info for normal, warning for exceeded limits
- LOG-004: Contextual information

### Financial Best Practices
- Uses Decimal for precision
- Risk-based stop loss calculation
- Tiered limits by capital size
- Circuit breaker on drawdown

## Audit Status
**Status**: PASSED**

### Strengths
1. Excellent tier-based limit system
2. Dynamic adjustment for volatility and drawdown
3. Risk-based stop loss calculation
4. Comprehensive limit checking (3 types)
5. Proper Decimal usage throughout
6. Singleton pattern for efficiency
7. Clear multiplier tables
8. Good documentation of formulas
9. Circuit breaker implementation

### Minor Observations
1. Multiplier values could be configurable
2. Could add more capital tiers if needed
3. Magic numbers in limits could be constants

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready limit adjuster
- Financial best practices followed
- Proper risk management implementation

### Use Cases
- Signal execution: Check position size limit
- Portfolio management: Check leverage limit
- Daily monitoring: Check daily loss limit
- Risk management: Get comprehensive limits

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0081*
*Status: PASSED*
