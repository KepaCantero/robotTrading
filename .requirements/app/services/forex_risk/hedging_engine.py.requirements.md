# Requirements: services/forex_risk/hedging_engine.py

## Source File Analysis
- **File Path**: `app/services/forex_risk/hedging_engine.py`
- **Lines of Code**: 782
- **Status**: Analysis Complete - PASSED
- **Audit Date**: 2026-02-07

## Purpose
Provides sophisticated currency hedging calculations for international portfolios:
- Optimal hedge ratio calculation using minimum variance method
- Hedge instrument selection (forwards, futures, options, ETFs)
- Hedge effectiveness tracking and measurement
- Cost optimization for hedge instruments
- Roll schedule recommendations

## Dependencies

### Internal
- `app.core.decimal_utils.calculate_percentage` - Percentage calculations for cost basis points

### External
- `logging` - Standard Python logging
- `dataclasses` - For dataclass decorators (HedgeInstrument, HedgeRecommendation, HedgeEffectiveness)
- `datetime` - For datetime handling in effectiveness tracking
- `decimal.Decimal` - Precise financial calculations
- `enum.Enum` - For HedgeInstrumentType and HedgeDirection enums
- `typing` - Type hints (Any, Dict, List, Optional)

## Classes/Functions

### Data Classes
1. **HedgeInstrumentType (Enum)** - Types of hedge instruments (FORWARD, FUTURE, OPTION, ETF, FUND)
2. **HedgeDirection (Enum)** - Hedge direction (LONG, SHORT)
3. **HedgeInstrument** - Instrument metadata with contract size, liquidity, spread, tenor options
4. **HedgeRecommendation** - Complete hedging recommendation with optimal ratio, costs, effectiveness
5. **HedgeEffectiveness** - Historical hedge performance metrics

### Main Class: HedgingEngine
1. **calculate_optimal_hedge_ratio()** - Calculate minimum variance hedge ratio
2. **get_recommendation()** - Generate complete hedging recommendation
3. **calculate_effectiveness()** - Measure hedge effectiveness
4. **track_effectiveness()** - Store historical effectiveness
5. **get_effectiveness_history()** - Retrieve historical hedge metrics

## Business Logic

### Hedge Ratio Calculation
- **Minimum Variance Method**: h* = correlation * (sigma_asset / sigma_fx)
- Supports naive (h* = 1.0), partial (h* = 0.5), and minimum variance methods
- Bounds hedge ratio between 0 and 1

### Instrument Selection
- Scores instruments based on: liquidity (40%), spread (40%), exchange-traded (20%)
- Filters by required tenor
- Creates default forward instruments for unsupported currencies

### Effectiveness Measurement
- Variance reduction: (var_unhedged - var_hedged) / var_unhedged
- Basis risk: 1 - effectiveness
- Tracks historical effectiveness for regime change detection

### Cost Estimation
- Spread cost: amount * spread_bps / 10000
- Forward points: ~2% annual interest rate differential * time

## Data Models

### HedgeInstrument
```python
type: HedgeInstrumentType
currency_pair: str
contract_size: Decimal
liquidity: int (0-100)
typical_spread_bps: Decimal
symbol: Optional[str]
tick_size: Optional[Decimal]
tick_value: Optional[Decimal]
tenor_options: List[int]
is_exchange_traded: bool
```

### HedgeRecommendation
```python
currency: str
direction: HedgeDirection
amount_eur: Decimal
optimal_ratio: Decimal
instrument: HedgeInstrument
contracts: Optional[int]
tenor_months: int
expected_cost_eur: Decimal
expected_cost_bps: Decimal
effectiveness: Decimal
roll_schedule: Optional[str]
reasoning: str
priority: str
```

### HedgeEffectiveness
```python
currency: str
hedge_ratio: Decimal
period_start: datetime
period_end: datetime
portfolio_return_eur: Decimal
hedge_return_eur: Decimal
combined_return_eur: Decimal
variance_reduction: Decimal
effectiveness: Decimal
basis_risk: Decimal
```

## API Contracts

### calculate_optimal_hedge_ratio()
```python
async def calculate_optimal_hedge_ratio(
    exposure_eur: Decimal,
    currency: str,
    method: str = "minimum_variance",
    correlation: Optional[Decimal] = None,
    volatility_asset: Optional[Decimal] = None,
    volatility_fx: Optional[Decimal] = None,
) -> Decimal
```

### get_recommendation()
```python
async def get_recommendation(
    exposure_eur: Decimal,
    currency: str,
    risk_tolerance: Decimal = Decimal("0.8"),
    preferred_tenor_months: int = 3,
    method: str = "minimum_variance",
) -> HedgeRecommendation
```

## Error Handling

### Exception Handling
- No explicit exception handling in current implementation
- Relies on caller to handle Decimal operations and missing data
- Returns default values for unsupported currencies

### Input Validation
- Bounds hedge ratio between 0 and 1
- Validates instrument tenor options
- Checks for zero/negative values in division operations

## Performance Considerations

### Optimization
- Simple mathematical calculations (fast)
- No external API calls (uses default correlations/volatilities)
- Minimal memory footprint

### Scalability
- Stateful: stores effectiveness history per currency
- Limited to 100 historical records per currency

## Testing Strategy

### Unit Tests Needed
1. **Hedge ratio calculation**: Test all methods (naive, partial, minimum variance)
2. **Instrument selection**: Test scoring logic with various instruments
3. **Effectiveness calculation**: Test variance reduction formula
4. **Cost estimation**: Verify spread and forward point calculations
5. **Edge cases**: Zero volatility, negative correlations, unsupported currencies

### Integration Tests Needed
1. **Forex service integration**: Test with real forex data provider
2. **Effectiveness tracking**: Test historical tracking and regime change

## BASE_RULES Compliance

### Formatting & Style
- ✅ FMT-001: Line length follows Python standards
- ✅ FMT-007: No mutable defaults (uses `field(default_factory=...)`)
- ✅ FMT-006: Uses f-strings for string formatting

### Type Hints
- ✅ TYP-001: All functions have type hints
- ✅ TYP-002: Uses modern typing (Optional, List, Dict)
- ✅ TYP-005: All class attributes have type hints (dataclass fields)

### SOLID Principles
- ✅ SOL-001: Single Responsibility - focused on hedging calculations
- ✅ SOL-002: Open/Closed - extensible via DEFAULT_INSTRUMENTS and DEFAULT_CORRELATIONS

### Architecture
- ✅ ARCH-006: Dataclasses for value objects (frozen=True not used but reasonable for DTOs)
- ✅ ARCH-005: Early returns used appropriately

### Security
- ✅ SEC-007: Input validation for hedge ratios and bounds checking

### Logging & Observability
- ✅ LOG-003: Appropriate log levels (debug, info, warning, error)
- ✅ LOG-004: No sensitive data logged (no API keys/secrets)
- ✅ LOG-002: Context included in logs (currency, hedge ratio, costs)

### Documentation
- ✅ Comprehensive docstrings for all classes and methods
- ✅ Mathematical formulas documented in docstrings
- ✅ Usage examples provided

## Audit Status: PASSED

### Summary
This is a well-structured, professional financial module implementing currency hedging calculations. The code follows Python best practices with comprehensive type hints, clear docstrings, and proper mathematical documentation.

### Strengths
1. Clear separation of concerns (data classes vs. business logic)
2. Comprehensive documentation of financial formulas
3. Proper use of Decimal for financial calculations
4. Extensible design with default configurations
5. Well-documented data structures with to_dict() methods

### No Critical Issues Found
- No security vulnerabilities
- No anti-patterns
- No overengineering violations
- Code is production-ready

### Notes
- Module is designed for EUR base currency (Spain-focused)
- Default correlations and volatilities provided for major currencies
- Could benefit from integration with a live forex data provider for real-time values

---
*Audited on 2026-02-07*
