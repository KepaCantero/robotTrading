# Requirements: services/alerting_system/rule_templates.py

## Source File Analysis
- **File Path**: `app/services/alerting_system/rule_templates.py`
- **Lines of Code**: 407
- **Audit Date**: 2026-02-07
- **Status**: PASSED

## Purpose
Factory for creating pre-configured alert rule templates covering portfolio risk, volatility, execution quality, performance metrics, trading quality, and system health monitoring.

## Dependencies

### Internal
- `app.services.alerting_system.models`:
  - `AlertRule`: Main rule configuration
  - `AlertSeverity`: Enum (INFO, WARNING, CRITICAL)
  - `ThresholdRule`: Threshold-based trigger
  - `ChangeRule`: Percentage change trigger
  - `ComparisonOperator`: Enum (GREATER_THAN, LESS_THAN, etc.)
  - `LogicOperator`: Enum (AND, OR)

### External
- `decimal.Decimal`: Precise financial calculations
- `typing.List`: Type hints

## Classes/Functions

### Main Class
- **`AlertRuleTemplates`** (Static factory methods only)

### Portfolio Risk Templates
- `portfolio_drawdown_warning() → AlertRule`: 5% drawdown (WARNING)
- `portfolio_drawdown_critical() → AlertRule`: 10% drawdown (CRITICAL)
- `portfolio_drawdown_halt() → AlertRule`: 15% drawdown (CRITICAL + halt action)

### Volatility Templates
- `volatility_spike() → AlertRule`: 150% of baseline volatility

### Cost & Execution Templates
- `cost_overrun_warning() → AlertRule`: 5% cost overrun (WARNING)
- `cost_overrun_critical() → AlertRule`: 10% cost overrun (CRITICAL)
- `fill_ratio_low() → AlertRule`: Fill ratio < 95%

### Performance Templates
- `sharpe_ratio_deterioration() → AlertRule`: Sharpe decline >20% in 1 hour

### Trading Quality Templates
- `consecutive_losses_warning() → AlertRule`: 2 consecutive losses
- `consecutive_losses_critical() → AlertRule`: 4 consecutive losses + reduce position

### System Health Templates
- `latency_spike() → AlertRule`: System latency > 1000ms
- `error_rate_high() → AlertRule`: Error rate > 5%

### Utility Methods
- `get_all_default_templates() → List[AlertRule]`: Returns all 12 templates
- `get_template_by_id(rule_id: str) → AlertRule`: Get specific template
- `get_templates_by_category(category: str) → List[AlertRule]`: Filter by category
- `get_critical_templates() → List[AlertRule]`: Return all CRITICAL severity rules

## Business Logic

### Alert Categories
1. **portfolio_risk**: Drawdown monitoring at 5%, 10%, 15%
2. **market_conditions**: Volatility spike detection
3. **execution_quality**: Cost overruns, fill ratio
4. **performance**: Sharpe ratio deterioration
5. **trading_quality**: Consecutive losses
6. **system_health**: Latency, error rates

### Threshold Strategy
- **Warning Level**: Early detection, allows investigation
- **Critical Level**: Requires immediate action
- **Halt Level**: 15% drawdown triggers circuit breaker

### Deduplication Windows
- Drawdown warnings: 10 min
- Drawdown critical: 5 min
- Drawdown halt: 1 min (urgent)
- Volatility: 15 min
- Cost: 10 min
- Sharpe: 30 min
- Consecutive losses: 20/10 min
- Latency: 15 min
- Error rate: 5 min

### Tag Metadata
All rules include:
- `category`: Alert classification
- `threshold`: Trigger value description
- `severity_level`: WARNING/CRITICAL/INFO
- `action`: Optional (e.g., "halt_trading", "reduce_position")

## Data Models

### AlertRule Structure (from models.py)
```python
AlertRule(
    rule_id: str,
    name: str,
    description: str,
    severity: AlertSeverity,
    enabled: bool,
    threshold_rules: List[ThresholdRule],
    change_rules: List[ChangeRule],
    logic_operator: LogicOperator,
    deduplicate_minutes: int,
    tags: Dict[str, str]
)
```

### ThresholdRule
```python
ThresholdRule(
    metric_name: str,
    operator: ComparisonOperator,
    threshold: Decimal
)
```

### ChangeRule
```python
ChangeRule(
    metric_name: str,
    change_percent: Decimal,
    window_minutes: int,
    direction: str  # "up" or "down"
)
```

## API Contracts

### Static Factory Methods
All methods return AlertRule instances with sensible defaults:
- No parameters required
- All Decimal values for precision
- Pre-configured severity levels
- Appropriate deduplication windows

### Template Retrieval
```python
# Get all templates
templates = AlertRuleTemplates.get_all_default_templates()

# Get specific template
rule = AlertRuleTemplates.get_template_by_id("portfolio_drawdown_warning")

# Get by category
risk_rules = AlertRuleTemplates.get_templates_by_category("portfolio_risk")

# Get only critical rules
critical = AlertRuleTemplates.get_critical_templates()
```

## Error Handling

### get_template_by_id()
- Raises `ValueError` if rule_id not found
- Returns pre-configured AlertRule

### All Factory Methods
- No external dependencies
- No exceptions raised
- Return complete AlertRule objects

## Performance Considerations

- Static methods: No instance state
- Template lookup via dictionary: O(1)
- Template filtering via list comprehension: O(n)
- All Decimal calculations: Precise but slower than float

## Testing Strategy

### Unit Tests Needed
- Test all 12 template factories return valid AlertRule
- Test get_template_by_id() with valid/invalid IDs
- Test get_templates_by_category() filtering
- Test get_critical_templates() returns only CRITICAL
- Test get_all_default_templates() returns 12 rules
- Verify Decimal precision in thresholds

### Validation Tests Needed
- Verify all rule IDs are unique
- Verify all thresholds use Decimal type
- Verify deduplication windows are appropriate
- Verify severity levels match severity

## Audit Findings

### PASSED Rules
- ✅ FMT-001: Line length ≤ 100 (Black compliant)
- ✅ FMT-007: No mutable defaults (all static methods)
- ✅ TYP-001: Type hints present
- ✅ CC-001: Descriptive names
- ✅ CC-002: DRY (templates centralized, no duplication)
- ✅ CC-003: KISS (simple static factory pattern)
- ✅ SOL-001: Single Responsibility (template creation only)
- ✅ SOL-002: Open/Closed (extensible via new static methods)
- ✅ SOL-005: Dependency Inversion (depends on AlertRule abstraction)
- ✅ DP-002: Factory pattern (template creation)
- ✅ TRD-003: Position limits (consecutive losses action)
- ✅ RSK-003: Drawdown control (3-tier monitoring)
- ✅ RSK-004: Circuit breakers (15% halt)

### Strengths
- Clear categorization of alerts
- Progressive severity (warning → critical → halt)
- Appropriate deduplication windows
- Rich metadata via tags
- No hardcoded values (all use Decimal)
- Comprehensive coverage of risk scenarios

### Recommendations
1. Consider adding validation that thresholds are logically consistent
2. Consider adding template versioning for future updates
3. Consider adding regional/asset-class specific templates
4. Document the rationale for each threshold value

## Compliance with BASE_RULES.md

See ../../BASE_RULES.md for universal rules.

### File-Specific Rules
- RULE-TEMPLATE-001: All templates must use Decimal for thresholds (PASS)
- RULE-TEMPLATE-002: All templates must include deduplication window (PASS)
- RULE-TEMPLATE-003: All templates must include severity level (PASS)
- RULE-TEMPLATE-004: All templates must include category tag (PASS)
- RULE-TEMPLATE-005: Critical templates must include action tag (PASS)

---
**Audit Status**: PASSED
**Audited By**: Claude (Backend Developer Agent)
**Audit Date**: 2026-02-07
**Priority 1 Issues**: 0
