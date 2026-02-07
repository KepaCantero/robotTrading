# Requirements: services/position_builder/large_position_builder.py

## Source File Analysis
- **File Path**: `app/services/position_builder/large_position_builder.py`
- **Lines of Code:** 497
- **Status:** AUDIT COMPLETE

## Purpose
T2.2: Large Position Builder - Intelligently builds large positions (€50k+) using 3-5 intraday tranches, avoiding volatility peaks, with increasing size in later windows.

## Dependencies
- Internal:
  - `app.services.smart_order_routing.models.ExecutionPlan`, `OrderTranche`, `TimeWindow`
- External:
  - `logging`, `datetime`, `decimal`, `typing`

## Classes/Functions

### Class: IntraDayExecutionScheduler
- `__init__()`: Initialize scheduler
- `find_good_windows(num_windows, max_total_hours)`: Find optimal execution windows
- `time_window_to_datetime(window)`: Convert TimeWindow to datetime
- `is_in_volatile_period(time_str)`: Check if time is in volatile period

### Module-Level Data
- `GOOD_EXECUTION_WINDOWS`: Post-open (10:30-11:15), post-lunch (13:00-14:15), pre-close (14:30-15:00), after-hours (16:00-16:30)
- `VOLATILITY_PEAKS`: Opening (09:30-10:00), lunch (11:30-13:00), closing (15:00-16:00)

### Main Class: LargePositionBuilder
- `__init__()`: Initialize with scheduler
- `build_position(symbol, target_size, target_avg_price, max_execution_hours, num_tranches)`: Create execution plan
- `_allocate_size_to_windows(symbol, total_size, windows, target_price)`: Allocate size across windows
- `calculate_position_impact(symbol, position_size, daily_volume, num_tranches)`: Estimate impact reduction
- `estimate_build_duration(symbol, num_tranches)`: Estimate time needed

### Module-Level Data
- `MIN_POSITION_SIZE`: €25,000
- `MAX_RECOMMENDED_SIZE`: €500,000
- `DEFAULT_NUM_TRANCHES`: 4
- `TRANCHE_WEIGHTS_BY_COUNT`: Predefined weights (increasing for later tranches)

### Global Functions
- `get_large_position_builder()`: Get singleton instance

## Business Logic
1. **Execution Windows**: Avoids volatility peaks (opening, lunch, closing)
2. **Tranche Sizing**: Increasing weights (20%, 24%, 26%, 30% for 4 tranches)
3. **Impact Reduction**: Sqrt(N) reduction from temporal spreading
4. **Duration Estimation**: 1-7 hours based on tranche count

## Data Models
- ExecutionPlan: symbol, total_size, tranches, strategy, constraints
- OrderTranche: symbol, size, execution_time, window, target_price, status
- TimeWindow: start, end, name

## API Contracts
- Requires target_size ≥ €25,000
- 1-5 tranches supported
- 4-6 hours typical execution window

## Error Handling
- Exception types: `ValueError` for invalid parameters
- Validates position size and tranche count
- Warns for positions above €500,000

## Performance Considerations
- O(n) allocation calculation
- Simple impact estimation formula

## Testing Strategy
- Test window selection
- Test tranche weight allocation
- Test impact reduction calculation
- Test duration estimation
- Test boundary conditions

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0076-0078 GAP Audit)
**Notes:** Well-designed large position execution logic

**Checks Against BASE_RULES.md:**
- ✅ CC-001: Descriptive class and method names
- ✅ CC-003: Simple, focused algorithms
- ✅ CC-006: Explicit error handling (ValueError)
- ✅ LOG-004: Info logging for operations
- ✅ LOG-006: Timing captured (elapsed_ms)
- ✅ ARCH-004: Functions mostly < 20 lines
- ✅ FMT-007: No mutable defaults
- ✅ TRD-003: Position size limits enforced

**Minor Notes:**
- Hardcoded market times (US) - acceptable as reference data
- Impact reduction uses sqrt(N) approximation - standard academic model

---
*Auto-generated on Thu Feb  5 20:33:03 CET 2026*
*Updated: 2026-02-07 for GAP Audit Batch 0078*
