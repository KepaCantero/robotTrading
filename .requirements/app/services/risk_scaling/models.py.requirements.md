# Requirements: services/risk_scaling/models.py

## Source File Analysis
- **File Path**: `app/services/risk_scaling/models.py`
- **Lines of Code**: 407
- **Language**: Python 3
- **Purpose**: Pydantic data models for risk scaling system

## Purpose
Core Pydantic data structures for risk scaling system with validation:
- Scaling factors with bounds checking
- State management models
- Alert and subscription models
- Signal and position adjustment models
- Monitoring and reporting models

## Dependencies
- **Internal**:
  - None (pure data models)
- **External**:
  - `pydantic` - Data validation and serialization
  - `datetime` - Timestamp handling
  - `decimal.Decimal` - Financial precision
  - `enum.Enum` - Type-safe enums
  - `typing` - Type hints
  - `uuid.uuid4` - Unique ID generation

## Classes/Functions

### Enums
- **RiskAlertType** (str, Enum) - Types of risk alerts:
  - VOLATILITY_SPIKE, SHARPE_DECLINE, LOSS_STREAK
  - DRAWDOWN_WARNING, HALT_TRADING, SCALING_EXTREME, CIRCUIT_BREAKER

- **RiskLevel** (str, Enum) - Portfolio risk levels:
  - SAFE, CAUTION, WARNING, CRITICAL, HALT

### Core Data Models

#### RiskScalingFactors (BaseModel)
- **Purpose**: All scaling factors combined
- **Fields**:
  - `volatility_scale`: Decimal (0.5 to 1.5)
  - `sharpe_scale`: Decimal (0.2 to 1.0)
  - `loss_scale`: Decimal (0.5 to 1.0)
  - `drawdown_scale`: Decimal (0.0 to 1.0)
  - `timestamp`: datetime
- **Properties**:
  - `combined_scale`: Product of all factors
  - `is_extreme`: Any factor at extreme value
  - `is_halted`: Trading halted (drawdown_scale = 0)

#### RiskScalingSnapshot (BaseModel)
- **Purpose**: Historical state at point in time
- **Fields**: snapshot_id, timestamp, scaling_factors, current_atr, average_atr, sharpe_ratio, consecutive_losses, current_drawdown, max_drawdown

#### RiskAlert (BaseModel)
- **Purpose**: Single risk alert
- **Fields**: alert_id, alert_type, severity, message, timestamp, portfolio_id, metadata, resolved, resolved_at

#### RiskScalingState (BaseModel)
- **Purpose**: Complete state snapshot for portfolio
- **Fields**: state_id, portfolio_id, scaling_factors, current_atr, sharpe_ratio, consecutive_losses, current_drawdown, max_drawdown, scaling_history, active_alerts, updated_at

### Signal Models

#### AdjustedPositionSizes (BaseModel)
- **Purpose**: Position sizes after risk scaling
- **Fields**: original_size, adjusted_size, scaling_factor, reasons, original_stop_loss, adjusted_stop_loss

#### Signal (BaseModel)
- **Purpose**: Trade signal before scaling
- **Fields**: signal_id, symbol, direction, strength, base_position_size, entry_price, stop_loss_price

#### AdjustedSignal (BaseModel)
- **Purpose**: Signal after risk scaling
- **Fields**: signal_id, symbol, side, original_position_size, adjusted_position_size, is_rejected, rejection_reason, scaling_factors, original_stop_loss, adjusted_stop_loss

### Monitoring Models

#### RiskScalingStatus (BaseModel)
- **Purpose**: Dashboard/API status
- **Fields**: portfolio_id, scaling_factors, risk_level, active_alerts_count, active_alerts, last_update, next_recalc_at

#### AlertSubscription (BaseModel)
- **Purpose**: Alert subscription config
- **Fields**: subscription_id, portfolio_id, alert_types, min_severity, subscribed_at, enabled

#### RiskScalingReport (BaseModel)
- **Purpose**: Human-readable report
- **Fields**: report_id, portfolio_id, timestamp, period, current_combined_scale, all individual scales, metrics, active_alerts, recent_events, summary
- **Methods**: `__str__()` - Formatted report string

## Business Logic

### Scaling Factor Calculation
```python
combined_scale = volatility_scale × sharpe_scale × loss_scale × drawdown_scale
```

### Extreme Value Detection
Any of these conditions triggers `is_extreme = True`:
- volatility_scale <= 0.6 or >= 1.4
- sharpe_scale <= 0.3
- loss_scale <= 0.6
- drawdown_scale <= 0.2

### Halt Condition
`is_halted = True` when `drawdown_scale = 0`

## Data Model Features
- **Strict Mode**: `strict=True` in ConfigDict
- **Validation**: `validate_assignment=True`
- **No Extra Fields**: `extra="forbid"`
- **Type Coercion**: Automatic Decimal conversion
- **UUID Generation**: Automatic unique IDs

## API Contracts
All models support:
- `.model_dump()` - Export to dict
- `.model_validate()` - Validate input
- JSON serialization

## Error Handling
- Pydantic validation raises `ValidationError`
- Field constraints enforced at creation
- Assignment validation with `validate_assignment=True`

## Performance Considerations
- Pydantic v2 is fast
- Minimal overhead from validation
- Efficient property calculations
- No lazy loading issues

## Testing Strategy
- Test Pydantic validation with invalid data
- Test bounds checking (ge, le constraints)
- Test property calculations
- Test JSON serialization

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings in __str__
- FMT-007: default_factory for mutable defaults

### Type Hints
- TYP-001: 100% type coverage
- TYP-002: Modern syntax
- TYP-005: All fields typed with constraints

### Pydantic Best Practices
- Uses Pydantic v2 ConfigDict
- Field validation with ge/le constraints
- Proper use of Field() with descriptions
- UUID generation with default_factory

### Clean Code
- CC-001: Descriptive model names
- CC-007: Models are concise and focused

### Security
- SEC-007: Input validation via Pydantic
- No SQL injection risk (no raw SQL)
- Bounds checking prevents invalid states

## Audit Status
**Status**: PASSED**

### Strengths
1. Excellent use of Pydantic v2 features
2. Comprehensive field validation with constraints
3. Good use of ConfigDict for model config
4. Proper handling of Decimal for financial precision
5. UUID generation with default_factory
6. Clear enum definitions
7. Property methods for derived values
8. Formatted __str__ method for reports

### Minor Observations
1. Some descriptions could be more detailed
2. Could add more custom validators if needed

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready data models
- Proper validation throughout
- Type-safe enums
- Financial precision maintained

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0081*
*Status: PASSED*
