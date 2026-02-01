# exceptions.py

## Purpose
Core exception hierarchy for AlgoTrading system. Independent exception definitions to avoid circular imports. Provides specific exception types for different error domains.

---

## Type Definitions / Data Classes

### Exception Hierarchy
```python
class AlgoTradingError(Exception)
    message: str                          # REQUIRED - Error message
    error_code: Optional[str] = None      # OPTIONAL - Error code for categorization
    details: Optional[Dict[str, Any]] = None  # OPTIONAL - Additional context

class ConfigurationError(AlgoTradingError)
    # Configuration-related errors

class ValidationError(AlgoTradingError)
    # Data validation errors

class BusinessLogicError(AlgoTradingError)
    # Business logic errors

class MarketDataError(AlgoTradingError)
    # Market data errors

class TradingError(AlgoTradingError)
    # Trading operation errors

class PortfolioError(AlgoTradingError)
    # Portfolio management errors

class SignalError(AlgoTradingError)
    # Signal generation errors

class BacktestError(AlgoTradingError)
    # Backtesting errors

class DatabaseError(AlgoTradingError)
    # Database operation errors
    # Note: Conflicts with sqlalchemy.exc.DatabaseError import

class APIError(AlgoTradingError)
    # External API errors
```

**Validation Rules:**
- message is required
- error_code is optional for categorization
- details can contain any additional context
- All exceptions are picklable (for multiprocessing)

---

## Function Signatures (Contracts)

### `raise_configuration_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises ConfigurationError)
**Raises:** ConfigurationError
**Retry:** No
**Side Effects:** None

### `raise_validation_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises ValidationError)
**Raises:** ValidationError
**Retry:** No
**Side Effects:** None

### `raise_business_logic_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises BusinessLogicError)
**Raises:** BusinessLogicError
**Retry:** No
**Side Effects:** None

### `raise_market_data_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises MarketDataError)
**Raises:** MarketDataError
**Retry:** No
**Side Effects:** None

### `raise_trading_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises TradingError)
**Raises:** TradingError
**Retry:** No
**Side Effects:** None

### `raise_database_error(message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None`
**Pre:** message is non-empty
**Post:** Never returns (raises DatabaseError)
**Raises:** DatabaseError
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All custom exceptions inherit from AlgoTradingError
- [ ] AlgoTradingError inherits from Exception
- [ ] Each exception type has specific domain
- [ ] Exception hierarchy supports selective catching
- [ ] All exceptions are picklable (for multiprocessing)
- [ ] AlgoTradingError carries message, error_code, details
- [ ] Helper functions raise appropriate exceptions
- [ ] No circular imports (independent definitions)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ⚠️ NOT APPLIED - Exceptions carry context |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses Optional, Dict |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Core infrastructure |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Only exception definitions |

**POTENTIAL ISSUES:**
1. **Name conflict**: `DatabaseError` conflicts with `sqlalchemy.exc.DatabaseError` (line 8 imports it but doesn't use it)
2. **Missing validation**: Helper functions don't validate message is non-empty
3. **Overengineering**: Helper functions just raise exceptions - could use direct raising

---

## Dependencies
- **External:** typing
- **Internal:** None (intentionally independent to avoid circular imports)

**Note:** sqlalchemy.exc.DatabaseError is imported but shadows the custom DatabaseError class

---

## Required Tests
- **tests/core/test_exceptions.py:**
  - Test all exceptions can be raised and caught
  - Test exception hierarchy (catching base catches derived)
  - Test exceptions are picklable
  - Test exception messages are preserved
  - Test AlgoTradingError carries message, error_code, details
  - Test helper functions raise correct exceptions
  - Test selective catching (catch ValidationError without catching TradingError)

---

## Notes
- **Simple exception hierarchy** - No additional attributes beyond base AlgoTradingError
- **Independent definitions** - Avoids circular imports
- **Helper functions** - Convenience for raising exceptions with consistent format
- **Name conflict warning** - DatabaseError conflicts with sqlalchemy.exc.DatabaseError
- **Consider adding:**
  - Error codes for machine-readable error types
  - Retry hints (for transient failures)
  - Context information (request ID, user ID, etc.)
  - HTTP status codes (for API errors)
