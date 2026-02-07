# Requirements: app/engines/risk_engine/risk_limits_enforcer.py

## Source File Analysis
- **File Path**: `app/engines/risk_engine/risk_limits_enforcer.py`
- **Lines of Code**: 546
- **Status**: Analysis Complete

## Purpose
Risk Limits Enforcer module implements Hull Chapter 18 automatic risk limit enforcement based on VaR thresholds. Provides position reduction recommendations, trading halt triggers, dynamic position sizing, risk heatmaps, and risk attribution by asset class.

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 18.

## Dependencies

### Internal
- `app.models.portfolio` - Portfolio data models

### External
- `logging` - Structured logging
- `datetime.datetime` - Timestamps
- `typing.Any, Dict, List, Optional` - Type hints
- `numpy` - Numerical operations (std, mean)

## Classes/Functions

### class RiskLimitsEnforcer
**Purpose**: Risk limits enforcer with VaR-based position controls

**Configuration**:
- `var_warning_limit`: Default 2% (VaR warning threshold)
- `var_critical_limit`: Default 3% (VaR critical threshold)
- `var_halt_limit`: Default 5% (VaR halt threshold)
- `max_position_pct`: Default 20% per position
- `max_concentration_pct`: Default 40% for top N positions
- `max_leverage`: Default 2.0x
- `max_drawdown_pct`: Default 15%

**State**:
- `trading_halted`: Boolean flag
- `halt_reason`: String description
- `enforcement_history`: List of enforcement actions

**Methods**:
- `check_var_limits(portfolio, current_var, portfolio_value) -> Dict[str, Any]`: VaR limit checking with action recommendations
- `_calculate_required_reduction(current_var, target_var) -> float`: Calculate position reduction needed (square root scaling)
- `enforce_position_limits(portfolio) -> Dict[str, Any]`: Position size and concentration enforcement
- `generate_risk_heatmap(portfolio, risk_contributions) -> Dict[str, Any]`: Portfolio risk heatmap by position
- `_analyze_risk_distribution(heatmap_data) -> Dict[str, Any]`: Risk distribution analysis
- `attribute_risk_by_asset_class(portfolio, returns_history, asset_class_mapping) -> Dict[str, Any]`: Risk attribution by asset class
- `calculate_dynamic_position_size(base_position_value, current_var_utilization, max_utilization) -> float`: Dynamic position sizing based on VaR
- `_log_enforcement(enforcement_type, result) -> None`: Log enforcement action to history
- `reset_trading_halt() -> None`: Reset trading halt flag
- `get_enforcement_status() -> Dict[str, Any]`: Current enforcement status

## Business Logic

### VaR-Based Enforcement Actions
1. **VaR >= halt_limit (5%)**: HALT_TRADING (CRITICAL)
2. **VaR >= critical_limit (3%)**: REDUCE_POSITIONS (CRITICAL)
3. **VaR >= warning_limit (2%)**: MONITOR (WARNING)
4. **VaR < warning_limit**: NORMAL

### Required Reduction Calculation
Uses square root scaling (VaR scales with sqrt of position size):
```python
reduction_ratio = (target_var / current_var)^2
required_reduction = (1 - reduction_ratio) * 100
```

### Risk Heatmap Generation
- **HIGH Risk**: weight > 15% (red)
- **MEDIUM Risk**: weight > 10% (yellow)
- **LOW Risk**: weight <= 10% (green)

### Risk Distribution Analysis
- **HIGH Concentration**: top_3_risk > 60%
- **MEDIUM Concentration**: top_3_risk > 40%
- **LOW Concentration**: top_3_risk <= 40%

### Dynamic Position Sizing
- Scale factor = 1.0 - (current_var_utilization / max_utilization)
- At max_utilization: scale = 0 (no new positions)
- At 0 utilization: scale = 1.0 (full size)

### Asset Class Mapping (Default)
- Symbols ending in '-USD' → 'crypto'
- Other symbols → 'equities'

## Critical Rules (de BASE_RULES.md)

### TYP-001: Type hints
- ✅ All functions have complete type hints
- Legacy syntax: `Optional[T]` instead of `T | None` (acceptable)

### LOG-001: Structured logging
- ✅ Uses logger.warning for enforcement actions
- ✅ Logs include violation details
- ✅ Error logging with exc_info=True

### ERR-001: Error handling
- ✅ Specific exception types: ValueError, TypeError, AttributeError
- ✅ Try-except with error logging
- ✅ Returns error dict on failure

### RSK-001: Risk validation
- ✅ VaR-based limit enforcement
- ✅ Position size limits
- ✅ Concentration limits
- ✅ Leverage limits
- ✅ Drawdown limits

### RSK-002: Trading halt
- ✅ Automatic trading halt at critical VaR
- ✅ Halt reason tracking
- ✅ Manual reset capability

### TRD-006: Position sizing
- ✅ Dynamic position sizing based on VaR utilization
- ✅ Square root scaling for reduction calculations

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T09:00:00Z |
| **Audit Status** | PASSED |
| **Violations** | 0 |
| **Notes** | Previously audited on 2026-02-06 with PASSED status. Re-confirmed: No violations. Implements Hull Chapter 18 recommendations. All BASE_RULES critical requirements compliant. |

## Notes
- Academic reference: Hull, Options, Futures, and Other Derivatives, Chapter 18
- Trading halt requires manual reset after review
- Enforcement history tracked for audit trail
- Square root scaling for VaR reduction (academic standard)
