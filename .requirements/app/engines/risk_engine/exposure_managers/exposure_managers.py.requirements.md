# Requirements: app/engines/risk_engine/exposure_managers/exposure_managers.py

## Source File Analysis
- **File Path**: `app/engines/risk_engine/exposure_managers/exposure_managers.py`
- **Lines of Code**: 418
- **Status**: Analysis Complete

## Purpose
Exposure Managers module implements portfolio exposure analysis and management. Provides multi-dimensional exposure tracking by asset, sector, and strategy, with leverage monitoring, concentration risk assessment (Herfindahl Index), and violation detection.

## Dependencies

### Internal
- `app.models.portfolio` - Portfolio data models

### External
- `logging` - Structured logging
- `abc.ABC, ABCMeta` - Abstract base classes
- `datetime.datetime` - Timestamps
- `decimal.Decimal` - Precise financial calculations
- `typing.Any, Dict, List, Optional` - Type hints

## Classes/Functions

### class BaseExposureManager(ABC)
**Purpose**: Abstract base class for exposure manager implementations

**Methods**:
- `analyze_exposure(portfolio, **kwargs) -> Dict[str, Any]`: Analyze portfolio exposure

### class ExposureManager(BaseExposureManager)
**Purpose**: Main exposure manager with multi-dimensional analysis

**Configuration**:
- `max_asset_exposure`: Default 20% per asset
- `max_sector_exposure`: Default 30% per sector
- `max_strategy_exposure`: Default 40% per strategy
- `max_total_exposure`: Default 95% total
- `max_leverage`: Default 1.0 (no leverage)
- `warn_leverage`: Default 0.8 (warning threshold)

**Methods**:
- `analyze_exposure(portfolio, strategy_allocations, **kwargs) -> Dict[str, Any]`: Main analysis entry point
- `_analyze_asset_exposure(portfolio) -> Dict[str, Any]`: Per-asset exposure
- `_analyze_sector_exposure(portfolio) -> Dict[str, Any]`: Per-sector exposure
- `_analyze_strategy_exposure(portfolio, strategy_allocations) -> Dict[str, Any]`: Per-strategy exposure
- `_analyze_leverage(portfolio) -> Dict[str, Any]`: Leverage analysis
- `_analyze_concentration(portfolio) -> Dict[str, Any]`: HHI concentration
- `_detect_violations(asset_exposure, sector_exposure, strategy_exposure, leverage_analysis) -> List[Dict]`: Violation detection
- `get_status() -> Dict[str, Any]`: Manager status

## Business Logic

### Exposure Analysis Dimensions
1. **Asset Exposure**: Per-position weight vs limit
2. **Sector Exposure**: Grouped by asset_class
3. **Strategy Exposure**: Grouped by strategy_allocations mapping
4. **Leverage**: Total exposure / equity ratio
5. **Concentration**: Herfindahl-Hirschman Index (HHI)

### Herfindahl-Hirschman Index (HHI)
- HHI = sum(weight_i^2) for all positions
- Effective N = 1 / HHI
- Concentration levels:
  - HHI > 0.5: very_high
  - HHI > 0.3: high
  - HHI > 0.15: medium
  - HHI ≤ 0.15: low

### Violation Detection
- **Severity Calculation**: exposure > limit * 1.5 → HIGH severity
- **Leverage Violation**: critical severity
- **History Tracking**: up to max_violation_history entries

### Top N Concentration Metrics
- top_5_weight: Sum of top 5 positions
- top_10_weight: Sum of top 10 positions

## Critical Rules (de BASE_RULES.md)

### TYP-001: Type hints
- ✅ All functions have complete type hints
- Legacy syntax: `Optional[T]`, `Dict[str, Any]` (acceptable)

### LOG-001: Structured logging
- ✅ Uses logger.error for exceptions
- ✅ Logs include exc_info=True

### ERR-001: Error handling
- ✅ Specific exception types: ValueError, TypeError, KeyError, AttributeError, IndexError
- ✅ Try-except with error logging
- ✅ Returns error dict on failure

### TRD-002: Trading validations
- ✅ Division by zero checks (portfolio.total_equity == 0)
- ✅ Decimal precision for financial calculations
- ✅ Empty collection handling (if weights/exposures)

### RSK-002: Exposure limits
- ✅ Multi-dimensional exposure tracking
- ✅ Configurable limits via constructor
- ✅ Violation history tracking
- ✅ Leverage monitoring with warning threshold

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T09:00:00Z |
| **Audit Status** | PASSED |
| **Violations** | 0 |
| **Notes** | All BASE_RULES critical requirements compliant. Uses legacy type hint syntax (acceptable). Comprehensive exposure analysis with HHI concentration metrics. |

## Notes
- Uses Decimal for exposure calculations (financial precision)
- Proper handling of enum-like asset_class values
- Violation history with configurable max size
- Spanish comments (international project)
