# Requirements: app/domain/services/backtesting/survivorship_bias.py

## Source File Analysis
- **File Path**: `app/domain/services/backtesting/survivorship_bias.py`
- **Lines of Code**: 424
- **Status**: Analysis Complete

## Purpose
Handles survivorship bias in backtesting. Survivorship bias leads to overestimation of returns because failed companies are excluded from historical data.

Reference: López de Prado (2018) "Advances in Financial Machine Learning"

## Dependencies

### Internal
None - Pure domain service

### External
- `dataclasses`: Data class decorators
- `datetime.date`: Date handling
- `decimal.Decimal`: Precise financial calculations
- `enum.Enum`: Enumeration types
- `typing`: Type hints (Dict, List, Optional)
- `numpy`, `pandas`: Data manipulation

## Classes/Functions

### class DelistingReason(str, Enum)
**Values**: BANKRUPTCY, MERGER, ACQUISITION, DELISTING, PRIVATE, LIQUIDATION, OTHER

### class CorporateActionType(str, Enum)
**Values**: STOCK_SPLIT, REVERSE_SPLIT, SPINOFF, DIVIDEND, RIGHTS_OFFERING, MERGER, ACQUISITION, TENDER_OFFER, NAME_CHANGE, SYMBOL_CHANGE

### @dataclass class DelistingEvent
**Purpose**: Record of delisting
- `is_bailout` - Check if resulted in shareholder recovery
- `total_loss` - Calculate loss percentage

### @dataclass class CorporateAction
**Purpose**: Record of corporate action
- `adjust_price()` - Adjust historical price
- `adjust_quantity()` - Adjust position quantity

### class SurvivorshipBiasCorrector
**Purpose**: Corrects survivorship bias in backtesting
- `add_delisting()` - Record delisting event
- `add_corporate_action()` - Record corporate action
- `check_delisting_date()` - Check if delisted
- `adjust_returns_for_delisting()` - Adjust returns for delisting
- `adjust_price_series()` - Adjust prices for corporate actions
- `get_current_symbol()` - Handle symbol changes
- `calculate_survivorship_bias()` - Calculate bias amount

## Business Logic

### Delisting Adjustments
- **Bankruptcy**: -50% to -100% return
- **Merger/Acquisition**: 0-30% premium
- **Other**: -50% default

### Corporate Actions
- Stock splits: Price ÷ ratio, Quantity × ratio
- Reverse splits: Price × ratio, Quantity ÷ ratio
- Spinoffs: Handle new companies
- Symbol changes: Track mappings

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:24:00Z |
| **Audit Status** | PASSED |

**Notes**:
- Critical component for accurate backtesting
- Properly handles delisting events
- Corporate action adjustment is comprehensive
- Good use of pandas for time series manipulation
