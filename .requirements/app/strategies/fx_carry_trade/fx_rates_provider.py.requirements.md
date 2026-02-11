# fx_rates_provider.py

## Purpose
 file for fx rates provider

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### FXDataSource
**Purpose:** Protocol for FX market data sources.

Defines the interface for raw FX market data including spot ra...
### FXInterestRateProviderProtocol
**Purpose:** Protocol for interest rate data providers.

Specialized protocol for accessing interest rate data us...
### FXRateProvider
**Purpose:** Protocol for FX rate data providers.

Defines the interface for accessing FX market data. Implementa...
### InMemoryFXRateProvider
**Purpose:** In-memory implementation of FX rate provider.

Stores FX rates and interest rates in memory for test...
### CompositeFXRateProvider
**Purpose:** Composite provider that aggregates multiple rate providers.

Queries multiple providers in sequence ...
### MockFXDataSource
**Purpose:** Mock FX data source for testing.

Provides a simple in-memory data source that generates realistic
F...
### CachedFXRateProvider
**Purpose:** Cached FX rate provider that wraps another provider.

Caches results from an underlying provider to ...
### FXRateProviderImpl
**Purpose:** FX Rate Provider implementation using a mock data source.

This implementation wraps a MockFXDataSou...
### FXInterestRateProviderImpl
**Purpose:** FX Interest Rate Provider implementation using a mock data source.

This implementation wraps a Mock...

---

## Function Signatures (Contracts)

### `FXDataSource.get_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXDataSource.get_forward_points(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXDataSource.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXInterestRateProviderProtocol.get_quote(self, currency, as_of, term) -> InterestRateQuote`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProvider.get_spot_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProvider.get_forward_rate(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProvider.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProvider.get_available_pairs(self) -> list[FXPair]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProvider.get_available_currencies(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.spot_rates(self) -> dict[tuple[FXPair, date], Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.forward_rates(self) -> dict[tuple[FXPair, date, int], Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.interest_rates(self) -> dict[tuple[str, date, int], Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.add_spot_rate(self, pair, rate, as_of) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.add_forward_rate(self, pair, rate, as_of, months) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.add_interest_rate(self, currency, rate, as_of, months) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_spot_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_forward_rate(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_available_pairs(self) -> list[FXPair]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_available_currencies(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_rate_quote(self, pair, as_of) -> FXRateQuote`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_fx_summary(self, as_of) -> dict[str, dict[str, Decimal]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.get_interest_rate_summary(self, as_of) -> dict[str, dict[int, Decimal]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `InMemoryFXRateProvider.clear_data(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CompositeFXRateProvider.get_spot_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CompositeFXRateProvider.get_forward_rate(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CompositeFXRateProvider.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CompositeFXRateProvider.get_available_pairs(self) -> list[FXPair]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CompositeFXRateProvider.get_available_currencies(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `MockFXDataSource.get_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `MockFXDataSource.get_forward_points(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `MockFXDataSource.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.get_spot_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.get_forward_rate(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.get_available_pairs(self) -> list[FXPair]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.get_available_currencies(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CachedFXRateProvider.clear_cache(self) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProviderImpl.get_spot_rate(self, pair, as_of) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProviderImpl.get_forward_rate(self, pair, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProviderImpl.get_interest_rate(self, currency, as_of, months) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProviderImpl.get_available_pairs(self) -> list[FXPair]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXRateProviderImpl.get_available_currencies(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXInterestRateProviderImpl.get_quote(self, currency, as_of, term) -> InterestRateQuote`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD


---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_fx_rates_provider.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/fx_carry_trade/fx_rates_provider.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
