# models.py

## Purpose
 file for models

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### CryptoAssetType
**Purpose:** Type of cryptocurrency asset....
### CryptoExchange
**Purpose:** Major cryptocurrency exchanges....
### OnChainMetrics
**Purpose:** On-chain metrics for cryptocurrency analysis.

These metrics provide insights into network activity ...
### CryptoAsset
**Purpose:** Cryptocurrency asset for momentum analysis.

This dataclass represents a crypto asset with all relev...
### CryptoMomentumScore
**Purpose:** Momentum score for a cryptocurrency asset.

Attributes:
    symbol: Trading symbol
    raw_momentum:...
### CryptoPosition
**Purpose:** Position in a cryptocurrency asset.

Attributes:
    symbol: Trading symbol
    quantity: Quantity h...
### CryptoPortfolio
**Purpose:** Cryptocurrency momentum portfolio.

Attributes:
    positions: List of positions
    total_value: To...
### CryptoMomentumConfig
**Purpose:** Configuration for the crypto momentum strategy.

Attributes:
    lookback_days: Lookback period for ...
### CryptoScreeningResult
**Purpose:** Result of crypto asset screening.

Attributes:
    passed_assets: List of assets that passed screeni...

---

## Function Signatures (Contracts)

### `OnChainMetrics.network_health_score(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoAsset.is_eligible_for_trading(self, min_market_cap, min_daily_volume, min_liquidity_score, required_exchanges) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoMomentumScore.is_high_momentum(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoMomentumScore.is_low_momentum(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoPosition.calculate_position_metrics(self) -> 'CryptoPosition'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoPortfolio.invested_value(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoPortfolio.btc_position(self) -> Optional[CryptoPosition]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoPortfolio.needs_rebalance(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoMomentumConfig.validate_weights(self) -> 'CryptoMomentumConfig'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoMomentumConfig.get_screening_description(self) -> str`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CryptoScreeningResult.pass_rate(self) -> float`
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
- **test_models.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/crypto_momentum/models.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
