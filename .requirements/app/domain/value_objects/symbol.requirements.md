# symbol.py

## Purpose
Symbol Value Object - Trading symbol representation with asset classification, exchange identification, and factory methods.

---

## Type Definitions / Data Classes

### AssetClass (str, Enum)
```python
class AssetClass(str, Enum):
    EQUITY = "equity"              # Stock/share
    ETF = "etf"                    # Exchange Traded Fund
    INDEX = "index"                # Market index
    FUTURES = "futures"            # Futures contract
    OPTION = "option"              # Option contract
    FOREX = "forex"                # Currency pair
    CRYPTO = "crypto"              # Cryptocurrency
    BOND = "bond"                  # Bond instrument
    COMMODITY = "commodity"        # Commodity instrument
```

### Exchange (str, Enum)
```python
class Exchange(str, Enum):
    # US Exchanges
    NYSE = "NYSE"                  # New York Stock Exchange
    NASDAQ = "NASDAQ"              # NASDAQ
    AMEX = "AMEX"                  # American Stock Exchange

    # Global Exchanges
    LSE = "LSE"                    # London Stock Exchange
    TSE = "TSE"                    # Tokyo Stock Exchange
    SSE = "SSE"                    # Shanghai Stock Exchange
    HKE = "HKE"                    # Hong Kong Stock Exchange
    ASX = "ASX"                    # Australian Securities Exchange
    TSX = "TSX"                    # Toronto Stock Exchange

    # Derivatives Exchanges
    EUREX = "EUREX"                # European Derivatives Exchange
    CME = "CME"                    # Chicago Mercantile Exchange
    CBOE = "CBOE"                  # Chicago Board Options Exchange
    ICE = "ICE"                    # Intercontinental Exchange
    LME = "LME"                    # London Metal Exchange

    # Special Exchanges
    FOREX = "FOREX"                # Foreign Exchange
    CRYPTO = "CRYPTO"              # Cryptocurrency exchanges
```

### Symbol (frozen=True)
```python
@dataclass(frozen=True)
class Symbol:
    ticker: str                      # REQUIRED - Trading ticker
    exchange: Exchange               # Default: NASDAQ - Trading exchange
    asset_class: AssetClass          # Default: EQUITY - Asset classification
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by ticker and exchange, no identity)
- Hashable (can be used in sets and dicts)

**Invariants (enforced in __post_init__):**
- `ticker` must be non-empty
- `ticker` normalized to uppercase and stripped

---

## Function Signatures (Contracts)

### `Symbol.__post_init__() -> None`
**Pre:** None
**Post:** Symbol validated and ticker normalized
**Raises:** `ValueError` if ticker is empty
**Retry:** No
**Side Effects:** Normalizes ticker (uppercase, strip) via object.__setattr__

### `is_us_equity (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == EQUITY AND exchange in (NYSE, NASDAQ, AMEX)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_etf (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == ETF
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_index (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == INDEX
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_futures (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == FUTURES
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_option (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == OPTION
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_forex (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == FOREX
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_crypto (property) -> bool`
**Pre:** None
**Post:** Returns True if asset_class == CRYPTO
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `stock(ticker: str, exchange: Exchange = Exchange.NASDAQ) -> Symbol` (classmethod)
**Pre:** ticker non-empty
**Post:** Returns Symbol with asset_class = EQUITY
**Raises:** `ValueError` if ticker empty
**Retry:** No
**Side Effects:** None (factory method)

### `etf(ticker: str, exchange: Exchange = Exchange.NYSE) -> Symbol` (classmethod)
**Pre:** ticker non-empty
**Post:** Returns Symbol with asset_class = ETF
**Raises:** `ValueError` if ticker empty
**Retry:** No
**Side Effects:** None (factory method)

### `index(ticker: str) -> Symbol` (classmethod)
**Pre:** ticker non-empty
**Post:** Returns Symbol with asset_class = INDEX, exchange = NYSE
**Raises:** `ValueError` if ticker empty
**Retry:** No
**Side Effects:** None (factory method)

### `futures(ticker: str, exchange: Exchange = Exchange.CME) -> Symbol` (classmethod)
**Pre:** ticker non-empty
**Post:** Returns Symbol with asset_class = FUTURES
**Raises:** `ValueError` if ticker empty
**Retry:** No
**Side Effects:** None (factory method)

### `forex(pair: str) -> Symbol` (classmethod)
**Pre:** pair non-empty
**Post:** Returns Symbol with asset_class = FOREX, ticker uppercase
**Raises:** `ValueError` if pair empty
**Retry:** No
**Side Effects:** None (factory method, normalizes to uppercase)

### `crypto(ticker: str) -> Symbol` (classmethod)
**Pre:** ticker non-empty
**Post:** Returns Symbol with asset_class = CRYPTO, ticker uppercase
**Raises:** `ValueError` if ticker empty
**Retry:** No
**Side Effects:** None (factory method, normalizes to uppercase)

### `option(underlying: str, expiry: str, strike: float, is_call: bool, exchange: Exchange = Exchange.CBOE) -> Symbol` (classmethod)
**Pre:** underlying non-empty, expiry format YYYYMMDD, strike > 0
**Post:** Returns Symbol with asset_class = OPTION, simplified OCC format ticker
**Raises:** `ValueError` if underlying empty
**Retry:** No
**Side Effects:** None (factory method)

**Option Format:** `UNDERLYINGYYYYMMDD{STRIKE_CENTS}C/P`
- Strike in cents, 8-digit padded (e.g., $150.50 = 00015050)
- Type: "C" for call, "P" for put

**Example:** AAPL option, expiry 20250321, strike $150, call → `AAPL2025032100015000C`

### `Symbol.__eq__(other) -> bool`
**Pre:** None
**Post:** Returns True if other is Symbol AND ticker equal AND exchange equal
**Raises:** None
**Retry:** No
**Side Effects:** None (pure comparison)

### `Symbol.__hash__() -> int`
**Pre:** None
**Post:** Returns hash of (ticker, exchange)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure function)

### `Symbol.__str__() -> str`
**Pre:** None
**Post:** Returns "TICKER.EXCHANGE"
**Raises:** None
**Retry:** No
**Side Effects:** None (string conversion)

### `Symbol.__repr__() -> str`
**Pre:** None
**Post:** Returns "Symbol(ticker='...', exchange=..., asset_class=...)"
**Raises:** None
**Retry:** No
**Side Effects:** None (debug representation)

---

## Acceptance Criteria
- [ ] **AC-001:** ticker must be non-empty
- [ ] **AC-002:** ticker is normalized to uppercase
- [ ] **AC-003:** Value object is immutable (frozen=True)
- [ ] **AC-004:** is_us_equity = EQUITY + (NYSE or NASDAQ or AMEX)
- [ ] **AC-005:** is_etf = asset_class == ETF
- [ ] **AC-006:** is_index = asset_class == INDEX
- [ ] **AC-007:** is_futures = asset_class == FUTURES
- [ ] **AC-008:** is_option = asset_class == OPTION
- [ ] **AC-009:** is_forex = asset_class == FOREX
- [ ] **AC-010:** is_crypto = asset_class == CRYPTO
- [ ] **AC-011:** Hashable for use in sets/dicts
- [ ] **AC-012:** Equality based on ticker + exchange
- [ ] **AC-013:** Option format: UNDERLYINGYYYYMMDD + 8-digit strike + C/P
- [ ] **AC-014:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Symbol Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Ticker required | Symbol standard | Non-empty ticker | ✅ OK - __post_init__ |
| Ticker normalization | Symbol standard | Uppercase, stripped | ✅ OK - __post_init__ |
| Asset class classification | Trading | 9 asset types | ✅ OK - AssetClass enum |
| Exchange identification | Trading | 16 exchanges | ✅ OK - Exchange enum |
| US equity detection | Trading | EQUITY + US exchange | ✅ OK - is_us_equity |
| Hashable | Value object | Can use in sets/dicts | ✅ OK - __hash__ |
| Equality | Value object | ticker + exchange | ✅ OK - __eq__ |
| Factory methods | Clean code | stock(), etf(), etc. | ✅ OK - 7 factories |
| Option format | OCC standard | Simplified OCC | ✅ OK - option() |
| Forex normalization | Trading | Uppercase pair | ✅ OK - forex() |
| Crypto normalization | Trading | Uppercase ticker | ✅ OK - crypto() |
| String representation | Clean code | TICKER.EXCHANGE | ✅ OK - __str__ |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for value object patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `enum` (std), `typing` (std)
- **Internal:** None (value object)

---

## Required Tests
- **test_symbol_value_object.py:**
  - `test_create_valid_symbol()` - Valid symbol created
  - `test_empty_ticker()` - Raises ValueError
  - `test_ticker_normalized_uppercase()` - Lowercase → uppercase
  - `test_ticker_stripped()` - Whitespace stripped
  - `test_is_us_equity_nyse()` - True
  - `test_is_us_equity_nasdaq()` - True
  - `test_is_us_equity_amex()` - True
  - `test_is_us_equity_lse()` - False (not US)
  - `test_is_etf_true()` - asset_class == ETF
  - `test_is_etf_false()` - asset_class != ETF
  - `test_is_index_true()` - asset_class == INDEX
  - `test_is_futures_true()` - asset_class == FUTURES
  - `test_is_option_true()` - asset_class == OPTION
  - `test_is_forex_true()` - asset_class == FOREX
  - `test_is_crypto_true()` - asset_class == CRYPTO
  - `test_stock_factory()` - Creates EQUITY symbol
  - `test_etf_factory()` - Creates ETF symbol (NYSE default)
  - `test_index_factory()` - Creates INDEX symbol (NYSE)
  - `test_futures_factory()` - Creates FUTURES symbol (CME default)
  - `test_forex_factory_uppercase()` - Pair normalized to uppercase
  - `test_crypto_factory_uppercase()` - Ticker normalized to uppercase
  - `test_option_factory_call()` - Format with C suffix
  - `test_option_factory_put()` - Format with P suffix
  - `test_option_strike_padding()` - Strike padded to 8 digits
  - `test_eq_same_values()` - True
  - `test_eq_different_ticker()` - False
  - `test_eq_different_exchange()` - False
  - `test_hashable()` - Can use in set/dict
  - `test_str_representation()` - "TICKER.EXCHANGE"
  - `test_repr_representation()` - "Symbol(ticker='...')"
  - `test_immutability()` - Cannot modify after creation

---

## Notes
- **Critical:** Symbol is a VALUE OBJECT (immutable, defined by ticker and exchange, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Ticker Normalization:** All tickers automatically converted to uppercase and stripped of whitespace
- **Asset Classes:** 9 asset types covering major financial instruments (equities, ETFs, indices, futures, options, forex, crypto, bonds, commodities)
- **Exchanges:** 16 exchanges covering US, global, derivatives, and special markets
- **US Equity Detection:** is_us_equity checks for EQUITY asset class on NYSE, NASDAQ, or AMEX
- **Factory Methods:** Convenient constructors for common symbol types:
  - stock() - Equity (default NASDAQ)
  - etf() - ETF (default NYSE)
  - index() - Index (NYSE fixed)
  - futures() - Futures contract (default CME)
  - forex() - Currency pair (FOREX exchange, auto-uppercase)
  - crypto() - Cryptocurrency (CRYPTO exchange, auto-uppercase)
  - option() - Option contract (default CBOE, simplified OCC format)
- **Option Format:** Simplified OCC (Options Clearing Corporation) format
  - Structure: UNDERLYING + EXPIRY(YYYYMMDD) + STRIKE_CENTS(8-digit) + TYPE(C/P)
  - Example: AAPL March 21, 2025 $150 Call → AAPL2025032100015000C
  - Strike in cents, padded to 8 digits (e.g., $150.50 = 00015050)
- **Equality:** Two Symbol instances are equal if both ticker AND exchange are equal
- **Hashable:** Implements __hash__ so Symbol can be used in sets and as dict keys
- **String Representations:**
  - __str__: "TICKER.EXCHANGE" for display
  - __repr__: "Symbol(ticker='...', exchange=..., asset_class=...)" for debugging
- **Usage Pattern:** Symbol provides type-safe, validated trading instrument identifiers throughout the domain

---

**File Reference:** `app/domain/value_objects/symbol.py`
**Last Audited:** 2026-02-01
