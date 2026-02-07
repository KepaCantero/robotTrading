# Requirements: services/profitability_validation_service.py

## Source File Analysis
- **File Path**: `app/services/profitability_validation_service.py`
- **Lines of Code**: 805
- **Language**: Python 3
- **Purpose**: Validates trading strategy profitability after all operational costs

## Purpose
This service validates that trading strategies generate net positive profitability after accounting for:
- Commissions (0.1% of trade value)
- Slippage (0.05% of trade value)
- Market impact (0.02% of trade value)
- Infrastructure costs ($1/trade)
- Data fees ($0.5/trade)
- Financing costs

## Dependencies
- **Internal**:
  - `app.core.centralized_config.get_config` - Configuration access
  - `app.models.profitability_validation` - Data models for validation results
  - `app.services.cost_analysis_service.CostAnalysisService` - Cost calculation
- **External**:
  - `statistics` - Standard library for statistical calculations
  - `typing` - Type hints
  - `decimal.Decimal` - Precision decimal arithmetic

## Classes/Functions

### ProfitabilityCalculator
- **Purpose**: Calculates profitability metrics from trade data
- **Key Methods**:
  - `calculate_metrics()` - Computes all profitability metrics
  - `_estimate_costs_from_trades()` - Estimates operational costs
  - `_calculate_trading_metrics()` - Win rate, profit factor, drawdown
  - `_calculate_max_drawdown()` - Maximum portfolio drawdown
  - `_calculate_sharpe_ratio()` - Risk-adjusted return metric

### ProfitabilityValidator
- **Purpose**: Validates metrics against criteria
- **Key Methods**:
  - `validate_profitability()` - Checks 8 validation criteria
  - `generate_recommendation()` - Creates recommendations based on results

### ProfitabilityValidationService
- **Purpose**: Main service orchestrating validation flow
- **Key Methods**:
  - `validate_strategy_profitability()` - Main validation entry point
  - `compare_strategies()` - Compare multiple strategies
  - `analyze_historical_performance()` - Trend analysis
  - `generate_validation_report()` - Comprehensive reporting

## Business Logic

### Validation Criteria (8 Tests)
1. **min_net_profit** - Net profit must meet minimum threshold
2. **min_profit_margin** - Profit margin as % of capital
3. **min_roi** - Return on investment percentage
4. **min_sharpe_ratio** - Risk-adjusted returns (Sharpe >= threshold)
5. **max_drawdown_limit** - Maximum acceptable drawdown
6. **min_win_rate** - Minimum winning trade percentage
7. **min_profit_factor** - Ratio of wins to losses
8. **max_cost_impact_ratio** - Costs as % of gross profit

### Cost Estimation Logic
- Commission: 0.1% of estimated trade value
- Slippage: 0.05% of trade value
- Market Impact: 0.02% of trade value
- Infrastructure: $1.00 per trade
- Data Fees: $0.50 per trade

## Data Models
- Uses models from `app.models.profitability_validation`:
  - `ProfitabilityMetrics` - All calculated metrics
  - `CostBreakdown` - Detailed cost components
  - `ValidationCriteria` - Thresholds for validation
  - `ValidationRequest/Response` - API contracts
  - `ValidationStatus` - PASSED/WARNING/FAILED

## API Contracts

### Input: ValidationRequest
```python
strategy_name: str
period_start: datetime
period_end: datetime
initial_capital: Decimal
trades_data: List[Dict[str, Any]]
criteria: Optional[ValidationCriteria]
```

### Output: ValidationResponse
```python
validation: ProfitabilityValidation
summary: Dict[str, Any]
recommendations: List[str]
next_steps: List[str]
```

## Error Handling
- **Approach**: Returns ValidationStatus.FAILED on validation errors
- **Logging**: Comprehensive logging at INFO and ERROR levels
- **Edge Cases**:
  - Empty trades_data returns zeros
  - Division by zero protected with checks
  - Invalid decimal conversions handled gracefully

## Performance Considerations
- **Complexity**: O(n) where n = number of trades
- **Memory**: Stores all trades in memory for calculations
- **Optimization**: Single pass through trades for cost estimation

## Testing Strategy
- **Unit Tests**:
  - Test metric calculations with known inputs
  - Test cost estimation formulas
  - Test validation criteria logic
- **Integration Tests**:
  - Test with real trade data
  - Test report generation
- **Edge Cases**:
  - Empty trade lists
  - All losing trades
  - Extreme values

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits (checked)
- FMT-006: Uses f-strings for string formatting
- FMT-007: No mutable defaults (all use None and create new objects)

### Type Hints
- TYP-001: All functions have type hints
- TYP-002: Uses modern syntax (Dict, List, Optional)
- TYP-005: Class attributes typed via dataclasses

### SOLID Principles
- SOL-001: Single Responsibility - Calculator/Validator/Service separation
- SOL-005: Dependency Inversion - Uses injected config service

### Clean Code
- CC-001: Descriptive names (calculate_max_drawdown, validate_profitability)
- CC-006: Explicit error handling with try/except
- CC-007: Functions are reasonable length (mostly < 40 lines)

### Security
- SEC-007: Input validation on Decimal conversions
- No hardcoded secrets

### Logging
- LOG-001: Uses logging module with structured messages
- LOG-003: Appropriate levels (info for normal, error for failures)

## Audit Status
**Status**: PASSED

### Strengths
1. Excellent separation of concerns (Calculator/Validator/Service)
2. Comprehensive type hints throughout
3. Proper Decimal usage for financial calculations
4. Clear business logic with well-documented formulas
5. Good error handling with validation
6. Comprehensive validation criteria (8 tests)

### Minor Observations
1. Some functions could benefit from docstrings (low priority)
2. Magic numbers for cost percentages (0.1%, 0.05%, 0.02%) could be constants
3. Statistics module usage for Sharpe ratio is appropriate

### No Critical Gaps Found
- All P0 and P1 BASE_RULES are satisfied
- Code is production-ready
- No security vulnerabilities detected
- No performance bottlenecks identified

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0079*
*Status: PASSED*
