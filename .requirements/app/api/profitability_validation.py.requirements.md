# profitability_validation.py

## Purpose
REST API endpoints for validating that trading strategies generate positive net profitability after all operational costs including commissions, slippage, market impact, and infrastructure costs.

---

## Type Definitions / Data Classes

### ValidationRequest (Pydantic model)
```python
class ValidationRequest:
    strategy_name: str              # REQUIRED - strategy identifier
    initial_capital: Decimal        # REQUIRED - starting capital (> 0)
    period_start: datetime          # REQUIRED - validation period start
    period_end: datetime            # REQUIRED - validation period end
    trades_data: List[TradeData]   # REQUIRED - executed trades
    criteria: Optional[ValidationCriteria]  # OPTIONAL - custom validation criteria
```

**Validation Rules:**
- `initial_capital` must be positive
- `period_start` must be before `period_end`
- `trades_data` must be non-empty

### ValidationCriteria (Pydantic model)
```python
class ValidationCriteria:
    min_net_profit: Decimal           # REQUIRED - minimum net profit threshold
    min_profit_margin: Decimal        # REQUIRED - minimum profit margin %
    min_roi: Decimal                  # REQUIRED - minimum ROI %
    min_sharpe_ratio: Decimal         # REQUIRED - minimum Sharpe ratio
    max_drawdown_limit: Decimal       # REQUIRED - maximum drawdown allowed
    min_win_rate: Decimal             # REQUIRED - minimum win rate %
    min_profit_factor: Decimal        # REQUIRED - minimum profit factor
    max_cost_impact_ratio: Decimal    # REQUIRED - maximum CIR allowed
```

### ValidationResponse (Pydantic model)
```python
class ValidationResponse:
    strategy_name: str                    # REQUIRED
    validation: ProfitabilityValidation   # REQUIRED - validation result
    timestamp: datetime                   # REQUIRED - ISO format
```

### ProfitabilityValidation (Service model)
```python
class ProfitabilityValidation:
    strategy_name: str                  # REQUIRED
    validation_date: datetime            # REQUIRED
    gross_profit: Decimal                # REQUIRED
    total_costs: Decimal                 # REQUIRED
    net_profit: Decimal                  # REQUIRED
    profit_margin: Decimal               # REQUIRED
    return_on_investment: Decimal        # REQUIRED
    sharpe_ratio: Decimal                # REQUIRED
    max_drawdown: Decimal                # REQUIRED
    win_rate: Decimal                    # REQUIRED
    profit_factor: Decimal               # REQUIRED
    cost_impact_ratio: Decimal           # REQUIRED
    validation_status: ValidationStatus  # REQUIRED (passed/failed/warning/pending)
    risk_level: RiskLevel                # REQUIRED (low/medium/high)
```

### StrategyComparison (Service model)
```python
class StrategyComparison:
    strategies_validated: int                    # REQUIRED - count
    best_strategy: str                          # REQUIRED - winner
    ranking: List[Tuple[str, float]]            # REQUIRED - sorted by score
    comparison_metrics: Dict[str, Decimal]      # REQUIRED - metric comparison
    recommendation: str                          # REQUIRED - text recommendation
```

---

## Function Signatures (Contracts)

### `validate_strategy_profitability(request: ValidationRequest) -> ValidationResponse`
**Pre:** request has valid capital, date range, and non-empty trades_data
**Post:** Returns complete validation result with status
**Raises:** HTTPException(400) on validation errors, HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only validation)

### `validate_multiple_strategies(requests: List[ValidationRequest]) -> List[ValidationResponse]`
**Pre:** requests list is non-empty, max 50 strategies
**Post:** Returns validation results for all strategies (continues on individual failures)
**Raises:** HTTPException(400) if list empty or > 50, HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only validation)

### `compare_strategies(validations: List[ProfitabilityValidation]) -> StrategyComparison`
**Pre:** validations list has at least 2 items
**Post:** Returns comparison with ranking and best strategy
**Raises:** HTTPException(400) if less than 2 validations, HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only comparison)

### `analyze_historical_performance(strategy_name: str, validations: List[ProfitabilityValidation]) -> HistoricalValidation`
**Pre:** validations list non-empty, contains data for strategy_name
**Post:** Returns historical performance analysis
**Raises:** HTTPException(404) if no validations for strategy, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only analysis)

### `generate_validation_report(validations: List[ProfitabilityValidation], include_comparison: bool, include_historical: bool) -> ValidationReport`
**Pre:** validations list non-empty
**Post:** Returns comprehensive validation report
**Raises:** HTTPException(400) if validations empty, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only report generation)

### `get_default_validation_criteria() -> ValidationCriteria`
**Pre:** None
**Post:** Returns default validation thresholds
**Raises:** HTTPException(500) on configuration errors
**Retry:** No
**Side Effects:** None (read-only)

### `health_check() -> JSONResponse`
**Pre:** None
**Post:** Returns health status (200 or 503 on error)
**Raises:** None (returns error status in response)
**Retry:** No
**Side Effects:** None

### `get_metrics_summary() -> JSONResponse`
**Pre:** None
**Post:** Returns list of metrics used in validation
**Raises:** HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] validate_strategy_profitability rejects requests with empty trades_data
- [ ] validate_strategy_profitability rejects initial_capital <= 0
- [ ] validate_strategy_profitability rejects period_start >= period_end
- [ ] validate_multiple_strategies limits batch to 50 strategies
- [ ] validate_multiple_strategies continues on individual failures
- [ ] compare_strategies requires at least 2 validations
- [ ] analyze_historical_performance returns 404 if strategy not found
- [ ] All timestamps use ISO format
- [ ] All responses include success/status indicators
- [ ] Health check returns 503 on service failure

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Has logging |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Comprehensive validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Rate limiting on batch endpoint | ✅ OK - Limits to 50 |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling | ✅ OK - Good error handling |
| API-009 | 09-logging-observability.md | Request logging | ✅ OK - Logs validation requests |
| API-010 | 08-configuration.md | Business logic validation | ✅ OK - Validates dates, capital, trades |

---

## Dependencies
- **External:** fastapi, requests
- **Internal:** app.models.profitability_validation, app.services.profitability_validation_service, app.core.centralized_config

---

## Required Tests
- **test_profitability_validation_endpoints.py:**
  - Test validate_strategy_profitability with valid data
  - Test validate_strategy_profitability rejects empty trades_data
  - Test validate_strategy_profitability rejects invalid capital
  - Test validate_strategy_profitability rejects invalid date range
  - Test validate_multiple_strategies with up to 50 strategies
  - Test validate_multiple_strategies rejects > 50 strategies
  - Test validate_multiple_strategies continues on individual failures
  - Test compare_strategies with 2+ strategies
  - Test compare_strategies rejects single strategy
  - Test analyze_historical_performance with valid data
  - Test analyze_historical_performance returns 404 for unknown strategy
  - Test generate_validation_report includes comparison when requested
  - Test get_default_validation_criteria returns valid criteria
  - Test health_check returns 200 or 503 appropriately

---

## Notes
- Comments and docstrings in Spanish (API endpoints para validación...)
- Uses ProfitabilityValidationService singleton
- No authentication visible
- Batch validation has safety limit of 50 strategies
- Health check returns hardcoded version "1.0.0"
- Consider adding audit logging for validation results
