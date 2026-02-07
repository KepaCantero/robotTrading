# symbol_mapper.py Requirements

**File:** `app/core/symbol_mapper.py`  
**Purpose:** Centralized Symbol Mapping for Multi-Broker FIFO Tax Compliance  
**Author:** Backend Developer (SRE Integration)  
**Date:** 2026-01-25  
**Status:** PRODUCTION - Critical for Tax Compliance  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.290720

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/core/interfaces/broker_base.py` (BrokerType interface)
  - FIFO tax calculation modules
  - Broker adapter modules

---

## Purpose & Scope

This module provides centralized symbol mapping for multi-broker FIFO tax compliance. Different brokers use different symbol formats:

- Binance: BTCUSDT, ETHUSDT
- OANDA: BTC_USD, ETH_USD
- IBKR: IBKR:BTC, IBKR:ETH
- Degiro: Various formats

**Critical for Production:** Ensures FIFO calculations work across multiple brokers and Modelo 721 tax reporting is accurate.

---

## Classes & Functions

### Classes

| Class | Purpose | Attributes/Methods |
|-------|---------|---------------------|
| `MappingStatus` | Status of symbol mapping | ACTIVE, DEPRECATED, PENDING_REVIEW, AUTO_DETECTED |
| `SymbolMappingError` | Base exception | Base for symbol mapping errors |
| `AmbiguousSymbolError` | Ambiguous mapping error | Raised when symbol maps to multiple internal symbols |
| `UnknownSymbolError` | Unknown symbol error | Raised when broker symbol cannot be mapped |
| `ValidationError` | Validation error | Raised when symbol validation fails |
| `SymbolMapping` | Symbol mapping data class | id, internal_symbol, broker_symbol, broker_name, broker_type, etc. |
| `BrokerMappingTables` | Pre-defined broker mappings | Static mapping tables for common brokers |
| `SymbolValidator` | Validates symbol formats | Pattern validation for each broker |
| `SymbolMapper` | Main symbol mapper | Two-way conversion, caching, database operations |
| `SymbolMapperMixin` | Mixin for broker adapters | Convenience methods for adapters |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `create_symbol_mapper()` | Factory for SymbolMapper | `SymbolMapper` |
| `get_or_create_mapping()` | Get or create symbol mapping | `SymbolMapping` |

---

## File-Specific Requirements

### SYM-001: Bidirectional Mapping Accuracy
**Priority:** P0 (Critical - Tax compliance)

**Requirement:** Internal -> Broker -> Internal conversion must be lossless.

**Acceptance Criteria:**
```python
mapper = SymbolMapper()

# Forward mapping
broker_symbol = mapper.map_internal_to_broker("BTC", "binance")
assert broker_symbol == "BTCUSDT"

# Reverse mapping
internal_symbol = mapper.map_broker_to_internal("BTCUSDT", "binance")
assert internal_symbol == "BTC"  # Must be lossless
```

**Check:** Bidirectional validation passes

---

### SYM-002: Symbol Format Validation
**Priority:** P0 (Critical - Data integrity)

**Requirement:** All broker symbols must match expected format patterns.

**Acceptance Criteria:**
```python
# Binance format: XXXUSDT
SymbolValidator.validate_broker_symbol("BTCUSDT", "binance")  # Pass
SymbolValidator.validate_broker_symbol("BTC-USD", "binance")  # Fail

# OANDA format: XXX_YYY
SymbolValidator.validate_broker_symbol("BTC_USD", "oanda")  # Pass
SymbolValidator.validate_broker_symbol("BTCUSDT", "oanda")  # Fail
```

**Check:** Regex patterns validate correctly

---

### SYM-003: Broker-Specific Extraction
**Priority:** P0 (Critical - Correct mapping)

**Requirement:** Internal symbol extraction must be broker-specific.

**Acceptance Criteria:**
```python
# Binance: Remove USDT suffix
assert SymbolValidator.extract_internal_from_broker("BTCUSDT", "binance") == "BTC"

# OANDA: Extract base from pair
assert SymbolValidator.extract_internal_from_broker("BTC_USD", "oanda") == "BTC"

# IBKR: Remove IBKR: prefix
assert SymbolValidator.extract_internal_from_broker("IBKR:BTC", "ibkr") == "BTC"
```

**Check:** Extraction logic per broker

---

### SYM-004: Mapping Consistency
**Priority:** P0 (Critical - Audit trail)

**Requirement:** All mappings must be bidirectionally consistent.

**Acceptance Criteria:**
```python
mapper = SymbolMapper()
is_valid, error = mapper.validate_mapping("BTC", "BTCUSDT", "binance")
assert is_valid == True
assert error is None
```

**Check:** Validation catches inconsistencies

---

### SYM-005: Cache Performance
**Priority:** P1 (High - Performance)

**Requirement:** Mappings must be cached to avoid repeated lookups.

**Acceptance Criteria:**
```python
mapper = SymbolMapper()
mapper.map_internal_to_broker("BTC", "binance")  # First call - cache miss
mapper.map_internal_to_broker("BTC", "binance")  # Second call - cache hit
assert len(mapper._cache) > 0  # Cache populated
```

**Check:** Cache hit/miss tracking

---

### SYM-006: Transaction Safety
**Priority:** P0 (Critical - Audit trail)

**Requirement:** All mapping operations must be logged for audit.

**Acceptance Criteria:**
```python
# Log message should include:
# - Internal symbol
# - Broker symbol
# - Broker name
# - Operation type (add, map, validate)
```

**Check:** Logging in all mapping methods

---

### SYM-007: Error Handling
**Priority:** P1 (High - Robustness)

**Requirement:** Invalid mappings must raise appropriate exceptions.

**Acceptance Criteria:**
```python
mapper = SymbolMapper()
try:
    mapper.map_broker_to_internal("INVALID", "binance")
except UnknownSymbolError as e:
    # Expected behavior
    pass

try:
    SymbolValidator.validate_internal_symbol("")
except ValidationError as e:
    # Expected behavior
    pass
```

**Check:** Exceptions are raised correctly

---

### SYM-008: Multi-Broker Support
**Priority:** P1 (High - Flexibility)

**Requirement:** Must support all configured brokers.

**Acceptance Criteria:**
```python
brokers = mapper.get_supported_brokers()
assert "binance" in brokers
assert "oanda" in brokers
assert "ibkr" in brokers
assert "degiro" in brokers
assert "kraken" in brokers
assert "coinbase" in brokers
```

**Check:** All brokers in supported list

---

### SYM-009: Symbol Normalization
**Priority:** P2 (Medium - Data consistency)

**Requirement:** All symbols must be normalized (uppercase, trimmed).

**Acceptance Criteria:**
```python
mapping = SymbolMapping(
    internal_symbol="  btc  ",  # Has spaces and lowercase
    broker_symbol="  btcusdt  ",
    broker_name="binance"
)
assert mapping.internal_symbol == "BTC"  # Normalized
assert mapping.broker_symbol == "BTCUSDT"  # Normalized
```

**Check:** __post_init__ normalizes symbols

---

### SYM-010: Fallback Construction
**Priority:** P2 (Medium - Robustness)

**Requirement:** When mapping doesn't exist, construct using broker-specific rules.

**Acceptance Criteria:**
```python
mapper = SymbolMapper()
symbol = mapper.map_internal_to_broker("NEWCOIN", "binance", use_default=True)
assert symbol == "NEWCOINUSDT"  # Constructed
```

**Check:** Fallback logic in place

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **TRD-004:** Audit trail ✅ (logging for all operations)
- **CC-006:** Explicit error handling ✅ (specific exceptions)
- **DP-004:** Dependency injection ✅ (db_session optional)

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **LOG-002:** Context in logs ✅

### Medium Priority (P2)
- **QL-001:** Complexity reasonable ✅
- **CC-007:** Small methods ✅

---

## Known Issues & Technical Debt

### Issues
1. **No database persistence** - Mappings are in-memory only
2. **No distributed cache** - Multi-instance deployments don't share cache
3. **Hardcoded mapping tables** - Should be in configuration

### Technical Debt
1. **Add database backend** - Persist mappings to database
2. **Add Redis cache** - Share cache across instances
3. **Add mapping API** - REST API for CRUD operations
4. **Add automatic discovery** - Learn mappings from broker data

---

## Testing Requirements

### Unit Tests
- [ ] Test bidirectional mapping accuracy
- [ ] Test symbol format validation
- [ ] Test broker-specific extraction
- [ ] Test mapping consistency validation
- [ ] Test cache performance
- [ ] Test error handling
- [ ] Test symbol normalization
- [ ] Test fallback construction

### Integration Tests
- [ ] Test with real broker data
- [ ] Test FIFO tax calculation with mapped symbols
- [ ] Test multi-broker scenarios
- [ ] Test audit trail logging

---

## Security Considerations

1. **No injection attacks** ✅ (symbol validation)
2. **Audit logging** ✅ (all operations logged)
3. **No unauthorized access** ⚠️ (no authentication yet)

---

## Performance Considerations

1. **Cache hit rate** - Should be > 95% for hot symbols
2. **Mapping lookup** - O(1) with cache ✅
3. **Database queries** - Minimized with caching ✅

---

## Dependencies

**External:**
- `logging` (stdlib)
- `re` (stdlib)
- `dataclasses` (stdlib)
- `datetime` (stdlib)
- `enum` (stdlib)
- `typing` (stdlib)
- `uuid` (stdlib)
- `sqlalchemy` (for AsyncSession type hint)

**Internal:**
- `app.core.interfaces.broker_base` (BrokerType)

---

## Migration Notes

**From unmapped code:**
1. Identify all broker symbol usage
2. Add symbol mapping for all symbols
3. Replace direct symbols with mapped symbols
4. Test FIFO calculations

**To symbol-mapped code:**
1. Import SymbolMapper
2. Use mapper for all broker symbols
3. Enable audit logging
4. Monitor mapping errors

---

## Changelog

### Version 1.0.0 (2026-01-25)
- Initial implementation
- Multi-broker support
- Bidirectional mapping
- Symbol validation
- Caching layer
- Audit logging

---

**Last Updated:** 2026-02-06  
**Next Review:** After database persistence added
