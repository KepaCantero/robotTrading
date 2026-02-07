# Requirements: services/fifo/modelo_721_generator.py

## Source File Analysis
- **File Path**: `app/services/fifo/modelo_721_generator.py`
- **Lines of Code**: 755
- **Status**: AUDIT COMPLETE

## Purpose
Generates Modelo 721 reports for Hacienda (Spanish tax authority). Mandatory reporting of cryptocurrency holdings for Spain residents. Due date: January 1 - March 31 of the following year.

## Dependencies
- Internal:
  - `app.core.database` (get_db_transaction)
  - `app.tax.database.fifo_schema` (Account, AssetType, BalanceSnapshot, Lot, LotStatus, TaxReport, Transaction, TransactionType)
- External:
  - `csv`
  - `logging`
  - `asyncio`
  - `dataclasses` (dataclass, field)
  - `datetime` (date, datetime, timezone)
  - `decimal` (Decimal)
  - `pathlib` (Path)
  - `typing`
  - `uuid` (UUID)
  - `sqlalchemy` (extract, select)
  - `sqlalchemy.exc` (DataError, DatabaseError, IntegrityError, OperationalError, ProgrammingError)
  - `sqlalchemy.ext.asyncio` (AsyncSession)

## Classes/Functions

### Data Classes
1. **CryptoBalance** (lines 62-70): Cryptocurrency balance for Modelo 721
2. **TransactionDetail** (lines 74-83): Transaction detail for Modelo 721
3. **CapitalGainLoss** (lines 87-98): Capital gain or loss for tax reporting
4. **Modelo721Report** (lines 102-154): Complete Modelo 721 report
   - Methods: `to_dict()`

### Main Class
1. **Modelo721Generator** (lines 157-734)
   - Purpose: Generate Modelo 721 reports for Hacienda

   **Public Methods:**
   - `__init__()` (lines 170-178): Initialize with user_id
   - `generate_annual_report()` (lines 180-257): Generate Modelo 721 report for tax year
   - `export_to_csv()` (lines 464-495): Export report to CSV format
   - `save_report_to_database()` (lines 667-704): Save report to database
   - `get_previous_year_reports()` (lines 706-734): Get all previous reports for user

   **Private Methods:**
   - `_get_crypto_accounts()` (lines 259-267): Get all crypto accounts for user
   - `_calculate_dec31_snapshot()` (lines 269-330): Calculate Dec 31 balance (CRITICAL requirement)
   - `_get_annual_transactions()` (lines 332-371): Get all transactions for tax year
   - `_calculate_capital_gains()` (lines 373-444): Calculate capital gains/losses
   - `_create_empty_report()` (lines 446-462): Create empty report when no data
   - `_export_hacienda_format()` (lines 497-559): Export in Hacienda official format
   - `_export_detailed_format()` (lines 561-665): Export in detailed format

### Factory Function
1. **get_modelo_721_generator()** (lines 741-754): Singleton pattern

## Business Logic

### CRITICAL Requirements for Modelo 721:
- **Mandatory**: All crypto holdings (no minimum threshold)
- **Due date**: January 1 - March 31
- **Required fields**: Saldo a 31 de diciembre (Dec 31 balance), Valor en EUR (value in Euros), Identificación de exchanges, Fecha y hora de cada transacción

### Report Generation Steps:
1. Get all crypto accounts for user
2. Generate Dec 31 balance snapshots (CRITICAL)
3. Get all transactions for the year
4. Calculate capital gains/losses
5. Calculate totals
6. Get exchanges used
7. Create report with all data

### CSV Export Formats:
1. **Hacienda format**: Official format for submission
   - Columns: Fecha, Operación, Criptomoneda, Número de criptomonedas, Valor en euros, Contraparte
   - Includes: Transactions, Dec 31 holdings, Summary

2. **Detailed format**: Internal analysis
   - Complete breakdown of balances, gains/losses, transactions

## Data Models
Uses database models from fifo_schema:
- Account, AssetType, BalanceSnapshot, Lot, LotStatus, TaxReport, Transaction, TransactionType

## API Contracts
No REST API - service layer module.

## Error Handling
- Exception handling for database errors (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError)
- ValueError for invalid tax year
- IOError for file write failures
- Comprehensive logging

## Performance Considerations
- Async database operations
- Efficient SQL queries with extracts
- Batch operations for large datasets

## Security & Compliance
- Tax reporting compliance (Spanish regulations)
- Audit trail via database persistence
- User-specific report generation
- No hardcoded sensitive data

## Testing Strategy
Recommended test coverage:
1. Unit tests for report generation
2. Dec 31 snapshot calculation tests
3. Capital gains calculation tests
4. CSV export format validation
5. Edge cases: no data, invalid year, missing snapshots

## Compliance with BASE_RULES.md

### PASSING Rules:
- ✅ **ARCH-001**: Layered architecture - service layer correctly positioned
- ✅ **ASYNC-001**: Use async def - database methods are async
- ✅ **ASYNC-002**: Await async calls - properly awaited
- ✅ **ASYNC-003**: Async context managers - uses `async with get_db_transaction()`
- ✅ **CC-001**: Descriptive names - clear method names
- ✅ **CC-006**: Explicit error handling - database exceptions caught
- ✅ **LOG-003**: Appropriate logging levels - info/error
- ✅ **LOG-004**: Error logging - exceptions logged with stack traces
- ✅ **SEC-005**: Audit logging - report saving creates audit trail
- ✅ **TYP-001**: Type hints - comprehensive type coverage
- ✅ **DP-002**: Factory pattern - get_modelo_721_generator() singleton

### GAPS IDENTIFIED:
None - Code quality is high. All BASE_RULES are satisfied.

## Audit Status: PASSED

**Audited By:** Claude (Backend Developer Agent)
**Audit Date:** 2026-02-07
**Batches:** 0099

### Summary
This module demonstrates excellent code quality:
- Comprehensive Modelo 721 tax reporting for Spanish residents
- Critical Dec 31 balance snapshot calculation
- Dual CSV export formats (Hacienda official + detailed)
- Capital gains/losses calculation with long/short-term separation
- Async database operations for performance
- Proper error handling for database operations
- Audit trail via database persistence
- Clear documentation of Spanish tax requirements

No critical gaps found. Module is production-ready and handles critical tax compliance requirements.

---
*Auto-generated on Thu Feb  5 20:33:01 CET 2026*
*Updated for GAP audit on 2026-02-07*
