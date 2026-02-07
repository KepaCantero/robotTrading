# Requirements: services/tax_efficiency/engines/spain_tax_engine.py

## Source File Analysis
- **File Path**: `app/services/tax_efficiency/engines/spain_tax_engine.py`
- **Lines of Code**: 401
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
Spain-specific tax calculation engine. Implements progressive capital gains tax (19%/21%/23%), dividend taxation, and Modelo 720 foreign asset reporting.

## Dependencies
- Internal:
  - `app.core.decimal_utils.to_decimal` (Decimal utilities)
  - `.base.TaxEngine` (Base tax engine class)
- External:
  - `logging` (Standard library)
  - `decimal`, `typing` (Standard library)

## Classes/Functions

### Classes
- `SpainTaxEngine`: Spain tax calculations
  - `calculate_capital_gains_tax(gain, holding_period_days)`: Progressive tax
  - `calculate_dividend_tax(dividend)`: Same as capital gains
  - `applies_wash_sale()`: Returns False (Spain has no wash sale rule)
  - `get_tax_rate_by_gain(gain)`: Get rate and bracket info
  - `calculate_tax_with_deductions(gain, deductions)`: Tax with deductions
  - `get_withholding_tax_rate(country)`: Foreign dividend withholding
  - `calculate_total_tax_liability(...)`: Annual tax calculation
  - `get_tax_brackets()`: All brackets for display
  - `check_modelo_720_threshold(foreign_assets_value)`: Reporting check
  - `calculate_compensated_gains(gains, losses)`: Gain/loss offset
  - `estimate_annual_tax(...)`: Tax estimation

## Business Logic

### Progressive Tax Brackets (2024/2025 IRPF Ahorro)
- **19%**: Gains <= EUR 33,007.99
- **21%**: Gains EUR 33,008 - 53,407.99
- **23%**: Gains > EUR 53,408

### Key Differences from US
- **No LT/ST distinction**: Holding period irrelevant
- **Dividends**: Taxed same as capital gains (progressive)
- **No wash sale rule**: Can sell and repurchase immediately
- **EU dividends**: 0% withholding (Parent-Subsidiary Directive)
- **Loss carryforward**: 4 years

### Withholding Tax Rates
- **EU/EEA**: 0%
- **US/UK/Switzerland**: 15% (tax treaties)
- **Others**: 19% (default)

## Data Models
- Input: gains, dividends, deductions (Decimal)
- Output: tax amounts (Decimal)
- Thresholds: BRACKET_1_LIMIT, BRACKET_2_LIMIT

## API Contracts

### SpainTaxEngine.calculate_capital_gains_tax()
```python
def calculate_capital_gains_tax(
    gain: Decimal,
    holding_period_days: int = 0,
) -> Decimal
```
Note: holding_period_days ignored (Spain has no distinction)

### SpainTaxEngine.check_modelo_720_threshold()
```python
def check_modelo_720_threshold(
    foreign_assets_value: Decimal,
) -> Dict
```
Returns threshold check, filing requirement, deadline

## Error Handling
- No explicit exceptions (parameter validation through type system)
- Graceful handling of zero/negative values
- Informative logging of tax calculations

## Performance Considerations
- O(1) calculations
- No external dependencies
- Minimal state (configuration only)

## Testing Strategy
- Unit tests for each bracket calculation
- Edge cases: zero gains, negative gains, boundary values
- Verify withholding tax rates by country
- Test Modelo 720 threshold logic

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Full type coverage with Decimal, Optional |
| Error Handling | ✅ PASS | Graceful handling of edge cases |
| SOLID Principles | ✅ PASS | Inherits from TaxEngine (OCP) |
| Logging | ✅ PASS | Debug logging for calculations |
| No Hardcoded Secrets | ✅ PASS | No secrets in code |
| Input Validation | ✅ PASS | Decimal type ensures valid financial values |
| Async Patterns | ✅ PASS | N/A - synchronous module |
| Documentation | ✅ PASS | Comprehensive docstrings |
| Financial Precision | ✅ PASS | Uses Decimal for all monetary values |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
