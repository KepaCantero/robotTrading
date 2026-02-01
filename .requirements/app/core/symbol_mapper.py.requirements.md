# symbol_mapper.py

## Purpose
Centralized symbol mapping for multi-broker FIFO tax compliance. Normalizes different broker symbol formats to internal standard format.

---

## Type Definitions / Data Classes

### MappingStatus Enum
```python
class MappingStatus(str, Enum):
    ACTIVE = "active"              # Mapping is active
    DEPRECATED = "deprecated"      # Mapping is deprecated
    PENDING_REVIEW = "pending_review"  # Mapping needs review
    AUTO_DETECTED = "auto_detected"    # Mapping was auto-detected
```

### SymbolMapping DataClass
```python
@dataclass
class SymbolMapping:
    id: UUID                               # REQUIRED - Unique identifier
    internal_symbol: str                   # REQUIRED - Standardized symbol (e.g., "BTC")
    broker_symbol: str                     # REQUIRED - Broker-specific symbol (e.g., "BTCUSDT")
    broker_name: str                       # REQUIRED - Broker name (e.g., "binance")
    broker_type: BrokerType                # REQUIRED - Type of broker
    asset_class: str                       # REQUIRED - Asset class (crypto, forex, stock, etf)
    status: MappingStatus                  # REQUIRED - Current status
    created_at: datetime                   # REQUIRED - Creation timestamp
    updated_at: datetime                   # REQUIRED - Last update timestamp
    is_verified: bool                      # REQUIRED - Verification status
    metadata: Dict                         # OPTIONAL - Additional information
```

**Validation Rules:**
- All symbols normalized to uppercase
- All broker names normalized to lowercase
- internal_symbol cannot be empty
- broker_symbol cannot be empty
- broker_name cannot be empty

### BrokerMappingTables Class
```python
class BrokerMappingTables:
    BINANCE_CRYPTO: Dict[str, str]        # Binance cryptocurrency mappings
    OANDA_FOREX: Dict[str, str]           # OANDA forex mappings
    IBKR_STOCKS_US: Dict[str, str]        # Interactive Brokers US stocks
    DEGIRO_STOCKS_EU: Dict[str, str]      # Degiro European stocks
    KRAKEN_CRYPTO: Dict[str, str]         # Kraken cryptocurrency mappings
    COINBASE_CRYPTO: Dict[str, str]       # Coinbase cryptocurrency mappings
```

### SymbolValidator Class Patterns
```python
PATTERNS = {
    'binance_crypto': r'^[A-Z]{3,10}USDT$'
    'binance_forex': r'^[A-Z]{6}USDT$'
    'oanda_forex': r'^[A-Z]{3}_[A-Z]{3}$'
    'oanda_crypto': r'^[A-Z]{3,10}_USD$'
    'ibkr_stock': r'^[A-Z]{1,5}$'
    'ibkr_crypto': r'^IBKR:[A-Z]{3,10}$'
    'degiro_stock': r'^[A-Z]{4,5}$'
    'kraken_crypto': r'^X?[A-Z]{3,10}ZUSD$'
    'coinbase_crypto': r'^[A-Z]{3,10}-USD$'
}
```

---

## Function Signatures (Contracts)

### `SymbolMapper.__init__(self, db_session: Optional[AsyncSession] = None) -> None`
**Pre:** None
**Post:** SymbolMapper initialized with empty caches
**Raises:** No
**Retry:** No
**Side Effects:** Initializes caches, logs initialization

### `SymbolMapper.map_internal_to_broker(self, internal_symbol: str, broker_name: str, use_default: bool = True) -> str`
**Pre:** internal_symbol is non-empty, broker_name is supported
**Post:** Returns broker-specific symbol format
**Raises:** UnknownSymbolError, ValidationError
**Retry:** No
**Side Effects:** Logs mapping, may update cache

### `SymbolMapper.map_broker_to_internal(self, broker_symbol: str, broker_name: str, use_default: bool = True) -> str`
**Pre:** broker_symbol is non-empty, broker_name is supported
**Post:** Returns normalized internal symbol
**Raises:** UnknownSymbolError, ValidationError, AmbiguousSymbolError
**Retry:** No
**Side Effects:** Logs mapping, may update cache

### `SymbolMapper.add_mapping(self, internal_symbol: str, broker_symbol: str, broker_name: str, broker_type: BrokerType, asset_class: str = "crypto", is_verified: bool = False, metadata: Optional[Dict] = None) -> SymbolMapping`
**Pre:** All symbols valid, broker_type valid
**Post:** Returns created SymbolMapping object
**Raises:** ValidationError, SymbolMappingError
**Retry:** No
**Side Effects:** Updates caches, logs for audit trail

### `SymbolMapper.get_all_brokers_for_symbol(self, internal_symbol: str) -> Dict[str, str]`
**Pre:** internal_symbol is valid
**Post:** Returns dict of broker_name -> broker_symbol
**Raises:** ValidationError
**Retry:** No
**Side Effects:** Logs number of mappings found

### `SymbolMapper.validate_mapping(self, internal_symbol: str, broker_symbol: str, broker_name: str) -> Tuple[bool, Optional[str]]`
**Pre:** All inputs non-empty
**Post:** Returns (is_valid, error_message)
**Raises:** No (returns validation result)
**Retry:** No
**Side Effects:** Logs validation result

### `SymbolValidator.validate_internal_symbol(cls, symbol: str) -> bool`
**Pre:** symbol is non-empty
**Post:** Returns True if valid format
**Raises:** ValidationError if invalid
**Retry:** No
**Side Effects:** None

### `SymbolValidator.validate_broker_symbol(cls, symbol: str, broker_name: str) -> bool`
**Pre:** symbol and broker_name are non-empty
**Post:** Returns True if valid for broker
**Raises:** ValidationError if invalid
**Retry:** No
**Side Effects:** None

### `SymbolValidator.extract_internal_from_broker(cls, broker_symbol: str, broker_name: str) -> str`
**Pre:** broker_symbol and broker_name are non-empty
**Post:** Returns extracted internal symbol
**Raises:** ValidationError if extraction fails
**Retry:** No
**Side Effects:** None

### `BrokerMappingTables.get_default_mapping(cls, broker_name: str, internal_symbol: str) -> Optional[str]`
**Pre:** broker_name is supported
**Post:** Returns broker symbol or None
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All symbols normalized to uppercase
- [ ] All broker names normalized to lowercase
- [ ] Internal symbols validated (2-10 uppercase letters)
- [ ] Broker symbols validated against broker-specific patterns
- [ ] Two-way mapping: internal <-> broker
- [ ] Cache hit improves performance
- [ ] Validation errors raised for invalid symbols
- [ ] UnknownSymbolError for unmapped symbols (when use_default=False)
- [ ] BrokerMappingTables provide fallback mappings
- [ ] Audit logging for all mapping operations
- [ ] Bidirectional validation in validate_mapping()
- [ ] Support for 6 brokers: binance, oanda, ibkr, degiro, kraken, coinbase

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets in this module |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses Dict, Optional, Tuple |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Custom exceptions |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - All errors logged |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ✅ OK - No broker credentials logged |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Core infrastructure layer |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Only handles symbol mapping |
| CFG-003 | BASE_RULES.md | Validation | ✅ OK - Input validation on all methods |

---

## Dependencies
- **External:** logging, re, dataclasses, datetime, enum, typing, uuid, sqlalchemy
- **Internal:** app.core.interfaces.broker_base (BrokerType)

---

## Required Tests
- **tests/core/test_symbol_mapper.py:**
  - Test map_internal_to_broker() for all 6 brokers
  - Test map_broker_to_internal() for all 6 brokers
  - Test symbol normalization (uppercase, lowercase)
  - Test ValidationError for invalid internal symbols
  - Test ValidationError for invalid broker symbols
  - Test UnknownSymbolError when use_default=False
  - Test cache hit improves performance
  - Test validate_mapping() bidirectional validation
  - Test get_all_brokers_for_symbol() returns all brokers
  - Test add_mapping() creates and caches mapping
  - Test extract_internal_from_broker() for each broker format
  - Test SymbolValidator patterns for all brokers
  - Test BrokerMappingTables fallback mappings

---

## Notes
- **CRITICAL for FIFO tax compliance** - Different brokers use different symbol formats
- **Transaction safety** - All mappings logged for audit purposes
- **Multi-broker support** - Binance, OANDA, IBKR, Degiro, Kraken, Coinbase
- **Symbol formats:**
  - Binance: BTCUSDT, ETHUSDT
  - OANDA: BTC_USD, EUR_USD
  - IBKR: IBKR:BTC, AAPL
  - Kraken: XXBTZUSD
  - Coinbase: BTC-USD
- Internal format: Uppercase, 2-10 characters (e.g., BTC, ETH, AAPL)
