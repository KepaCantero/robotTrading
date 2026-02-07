# Requirements: backtesting/robust_engine/models.py

## Source File Analysis
- **File Path**: `app/backtesting/robust_engine/models.py`
- **Lines of Code**: 417
- **Audit Status**: PASSED
- **Audit Date**: 2026-02-07T05:30:00Z

## Purpose
Data models for the Robust Backtesting Engine. Defines all data structures used throughout the robust backtesting system including corporate actions, dividend tracking, survivorship data, and checkpointing structures.

## Dependencies
- Internal: None (pure data models)
- External:
  - `dataclasses` (dataclass, field)
  - `datetime` (date, datetime)
  - `decimal` (Decimal)
  - `enum` (Enum)
  - `typing` (Any, Dict, List, Optional, Tuple)
  - `uuid` (UUID, uuid4)
  - `pydantic` (optional - with fallback to dataclasses)

## Classes/Functions
### Dataclasses
- `CorporateActionType` (Enum): Types of corporate actions (STOCK_SPLIT, MERGER, DIVIDEND, etc.)
- `DelistingReason` (Enum): Reasons for stock delisting
- `CorporateAction`: Base class for all corporate actions
- `StockSplit`: Stock split corporate action with split_ratio and adjustment_factor
- `Merger`: Merger/acquisition action with exchange_ratio and cash_consideration
- `SpinOff`: Spin-off action with distribution_ratio
- `DividendPayment`: Dividend payment with amount, frequency, qualified status
- `DelistedStock`: Information about delisted stocks for survivorship bias correction
- `DelistedReturnData`: Return data for delisted stocks
- `BacktestCheckpoint`: Checkpoint data for resuming interrupted backtests
- `ProgressUpdate`: Real-time progress updates for long-running backtests
- `DividendAction`: Record of dividend action during backtesting
- `DividendTracker`: Tracks all dividend activity
- `DripConfig`: Configuration for dividend reinvestment (DRIP)

## Business Logic
- Corporate action tracking for accurate historical adjustments
- Checkpointing system for resuming long backtests (25+ years)
- Dividend tracking with DRIP support
- Survivorship bias correction data structures
- Progress tracking for long-running operations

## Data Models
All models use `@dataclass` decorator with:
- Proper type hints using modern syntax (e.g., `Optional[date]`, `Dict[str, Any]`)
- Immutable field defaults using `field(default_factory=...)`
- UUID generation for unique identifiers
- Decimal precision for financial calculations

## API Contracts
- `BacktestCheckpoint.to_dict()`: Serialize checkpoint to dictionary
- `BacktestCheckpoint.from_dict()`: Deserialize checkpoint from dictionary
- `ProgressUpdate.progress_percentage()`: Calculate progress percentage
- `DividendTracker.add_dividend()`: Add dividend action to tracker
- `DividendTracker.calculate_yield()`: Calculate dividend yield metrics

## Error Handling
- Uses default_factory for mutable defaults to prevent shared state issues
- Proper validation in `__post_init__` methods
- Safe conversion methods for serialization

## Performance Considerations
- Dataclasses use `__slots__` implicitly for better memory efficiency
- Factory functions for default values prevent mutable default issues
- UUID4 for unique identifier generation

## Testing Strategy
- Test corporate action calculations (split ratios, adjustments)
- Test checkpoint serialization/deserialization
- Test dividend tracker calculations
- Test progress percentage calculations
- Test DRIP configuration validation

## Compliance with BASE_RULES.md
- ✅ FMT-001: Line length ≤ 100 (enforced by Black)
- ✅ FMT-007: No mutable defaults (uses field(default_factory=...))
- ✅ TYP-001: 100% type coverage on all dataclass fields
- ✅ TYP-002: Modern syntax uses Optional[T], Dict[K,V]
- ✅ TYP-003: Any used only in Dict[str, Any] context (documented)
- ✅ ARCH-006: Value objects are immutable dataclasses
- ✅ CC-006: Specific exception handling in validation

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Audited on 2026-02-07T05:30:00Z - Status: PASSED*
